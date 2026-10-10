#!/usr/bin/env python3
"""Local theme editor for xirml themes: edits ui/themes/<id>/theme.rcss and previews with xirml_preview.

    python tools/theme-editor/server.py [--preview <xirml_preview.exe>] [--port 8765]

Standard library only. Pillow, when installed, crops the preview to the panel.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

try:
    from PIL import Image
except ImportError:
    Image = None

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
UI = ROOT / "ui"
BASE = UI / "base" / "theme.rcss"
THEMES = UI / "themes"

ID = re.compile(r"[a-z0-9_-]{1,32}")
TOKEN_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
PANEL_ID = re.compile(r"[a-z0-9_/-]{1,64}")

# Crop boxes in the 3456x1944 scene, measured from renders of modern, classic and ff8 with 30px of margin.
# A panel that is not listed, or a theme that makes a panel much larger, shows the whole scene instead.
PANELS = {
    "inventory": (0, 105, 1194, 1596),
    "equipment": (1212, 102, 2070, 1410),
    "party": (2754, 1017, 3456, 1944),
    "target": (2756, 1614, 3456, 1836),
    "buffs": (1944, 114, 2697, 314),
    "chat": (15, 1377, 3099, 1929),
    "compass": (18, 1182, 668, 1413),
    "settings": (1194, 236, 2262, 1076),
    "live/menuwind": (2940, 111, 3456, 1041),
}

PREVIEW = ""
WRITE_LOCK = threading.Lock()
RENDER_LOCK = threading.Lock()


class PreviewError(Exception):
    pass


# --- token files: one body { --name: value; } rule, RmlUi custom properties ---------------------------------------------------------

TOKEN_LINE = re.compile(r"[ \t\r]*--([A-Za-z0-9_-]+)[ \t]*:[ \t]*([^;\n]*?)[ \t]*;(.*)")
REFERENCE = re.compile(r"var\(--([A-Za-z0-9_-]+)\)")


def parse(text):
    """`--name: value;` lines with their offsets, each under the last one-line /* comment */ above it."""
    lines, section = [], ""
    for found in re.finditer(r"[^\n]*\n|[^\n]+", text):
        line = found.group()
        stripped = line.strip(" \t\r\n")
        if stripped.startswith("/*"):
            close = stripped.find("*/", 2)
            if close != -1 and close + 2 == len(stripped):
                section = stripped[2:close].strip()
            continue
        token = TOKEN_LINE.match(line)
        if token:
            comment = re.search(r"/\*(.*?)\*/", token.group(3))
            lines.append({
                "name": token.group(1), "value": token.group(2), "section": section,
                "comment": comment.group(1).strip() if comment else "",
                "begin": found.start(), "end": found.end(),
                "value_begin": found.start() + token.start(2), "value_end": found.start() + token.end(2),
            })
    return lines


def expand(value, find):
    """Substitutes var(--name) with find(name)."""
    return REFERENCE.sub(lambda ref: find(ref.group(1)), value)


def settle(written):
    """Every token's value, like the plugin: a reference is what the named token ends up as, whichever layer wrote it
    last. Returns the values and, for each token that cannot resolve, why (its value is then left as written)."""
    values, errors = {}, {}

    def value(name, open_names):
        if name not in values:
            if name not in written:
                raise LookupError(f"unknown token --{name}")
            if name in open_names:
                raise LookupError(f"--{name} is defined through itself")
            values[name] = expand(written[name], lambda other: value(other, open_names + (name,)))
        return values[name]

    for name in written:
        try:
            value(name, ())
        except LookupError as error:
            errors[name] = str(error)
    return {name: values.get(name, raw) for name, raw in written.items()}, errors


def apply_edit(theme, inherited, name, value):
    """The theme file's text with one token set (or removed when value is None).

    A token already in the file keeps its line and comment. A new one goes after the file's last token of the same
    section, the section being the one it has in `inherited` (base and ancestors), else at the end under that heading.
    """
    eol = "\r\n" if "\r\n" in theme or ("\n" not in theme and "\r\n" in inherited) else "\n"
    lines = parse(theme)
    hits = [line for line in lines if line["name"] == name]
    for line in reversed(hits):
        if value is None:
            theme = theme[:line["begin"]] + theme[line["end"]:]
        else:
            theme = theme[:line["value_begin"]] + value + theme[line["value_end"]:]
    if hits or value is None:
        return theme

    sections = {}
    for line in parse(inherited):
        sections.setdefault(line["name"], line["section"])
    section = sections.get(name, "")
    at = None
    for line in lines:
        if section and sections.get(line["name"]) == section:
            at = line["end"]
    if theme and not theme.endswith("\n"):
        if at == len(theme):
            at += len(eol)
        theme += eol
    if at is None and section:
        # no token of the section left in the file, but its heading may be (after a reset): reuse it
        heading = re.search(r"^[ \t]*" + re.escape(f"/* {section} */") + r"[ \t\r]*\n", theme, re.MULTILINE)
        at = heading.end() if heading else None
    text = f"\t--{name}: {value};{eol}"
    if at is not None:
        return theme[:at] + text + theme[at:]
    close = theme.rfind("}")
    if close == -1:
        theme, close = theme + f"body {{{eol}}}{eol}", len(theme) + len(f"body {{{eol}")
    head = theme[:close].rstrip(" \t\r\n") + eol
    return head + eol + f"\t/* {section or 'added'} */{eol}" + text + theme[close:]


# --- themes on disk ----------------------------------------------------------------------------------------------------

def read(path):
    return path.read_bytes().decode("utf-8")


def write(path, text):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(text.encode("utf-8"))
    os.replace(temporary, path)


def theme_dir(theme_id):
    """The only place a write may land: a validated id directly under ui/themes."""
    if not isinstance(theme_id, str) or not ID.fullmatch(theme_id):
        raise ValueError("a theme id is 1 to 32 characters of a-z, 0-9, - and _")
    return THEMES / theme_id


def list_themes():
    themes = {}
    for folder in sorted(THEMES.iterdir()):
        if not (folder.is_dir() and ID.fullmatch(folder.name) and (folder / "theme.rcss").is_file()):
            continue
        info = {"id": folder.name, "name": folder.name, "description": "", "extends": "", "order": 0}
        try:
            manifest = json.loads(read(folder / "theme.json"))
            if not isinstance(manifest, dict):
                raise ValueError("expected an object")
            for key, kind in (("name", str), ("description", str), ("extends", str), ("order", int)):
                if isinstance(manifest.get(key), kind):
                    info[key] = manifest[key]
        except FileNotFoundError:
            pass
        except (ValueError, OSError) as error:
            info["error"] = f"theme.json: {error}"
        themes[folder.name] = info
    return themes


def chain_of(theme_id, themes):
    """Ancestors first, the theme last."""
    chain = []
    while theme_id:
        if theme_id in chain or len(chain) >= 16:
            raise ValueError(f"theme inheritance loops or is too deep at '{theme_id}'")
        if theme_id not in themes:
            raise ValueError(f"theme '{theme_id}' was not found")
        chain.append(theme_id)
        theme_id = themes[theme_id]["extends"]
    return chain[::-1]


def theme_view(theme_id):
    """Every token the theme resolves, grouped by section, with where its value comes from."""
    themes = list_themes()
    chain = chain_of(theme_id, themes)
    layers = [("base", read(BASE))] + [(layer, read(THEMES / layer / "theme.rcss")) for layer in chain]
    tokens = {}
    for source, text in layers:
        for line in parse(text):
            first = tokens.get(line["name"])
            group = first["group"] if first else line["section"] if source == "base" else f"{source}: {line['section']}"
            tokens[line["name"]] = {
                "name": line["name"], "raw": line["value"], "source": source, "own": source == theme_id, "group": group,
                "comment": first["comment"] if first and first["comment"] else line["comment"],
            }
    values, errors = settle({name: token["raw"] for name, token in tokens.items()})
    for name, token in tokens.items():
        token["value"], token["error"] = values[name], errors.get(name, "")
    groups = {}
    for token in tokens.values():
        groups.setdefault(token.pop("group") or "other", []).append(token)
    return {**themes[theme_id], "chain": chain, "groups": [{"title": title, "tokens": rows} for title, rows in groups.items()]}


def set_token(theme_id, name, value):
    folder = theme_dir(theme_id)
    if not isinstance(name, str) or not TOKEN_NAME.fullmatch(name):
        raise ValueError("a token name is letters, digits, - and _")
    if value is not None:
        if not isinstance(value, str) or not value.strip() or len(value) > 4096 or re.search(r"[;\r\n]", value):
            raise ValueError("a value is one line of text without ';' (use reset to remove an override)")
        value = value.strip()
    with WRITE_LOCK:
        chain = chain_of(theme_id, list_themes())
        inherited = "\n".join([read(BASE)] + [read(THEMES / layer / "theme.rcss") for layer in chain[:-1]])
        path = folder / "theme.rcss"
        if value is None:
            value = committed(path).get(name)  # the theme's own value, as last committed; None removes the override
        write(path, apply_edit(read(path), inherited, name, value))
    return theme_view(theme_id)


def committed(path):
    """The token values of a theme file as last committed, or nothing when it is not in git."""
    try:
        text = subprocess.run(["git", "show", "HEAD:" + path.relative_to(ROOT).as_posix()], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", timeout=10).stdout
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}
    return {line["name"]: line["value"] for line in parse(text)}


def create_theme(theme_id, name, description, extends):
    folder = theme_dir(theme_id)
    if not isinstance(name, str) or not 1 <= len(name.strip().encode("utf-8")) <= 96:
        raise ValueError("a name is 1 to 96 bytes")
    if not isinstance(description, str) or len(description.encode("utf-8")) > 1024:
        raise ValueError("a description is at most 1024 bytes")
    manifest = {"schema": 1, "name": name.strip(), "description": description.strip()}
    if extends:
        if extends not in list_themes():
            raise ValueError(f"theme '{extends}' was not found")
        manifest["extends"] = extends
    manifest["order"] = 100
    eol = "\r\n" if "\r\n" in read(BASE) else "\n"
    with WRITE_LOCK:
        try:
            folder.mkdir()
        except FileExistsError:
            raise ValueError(f"ui/themes/{theme_id} already exists") from None
        write(folder / "theme.json", json.dumps(manifest, indent=2, ensure_ascii=False).replace("\n", eol) + eol)
        write(folder / "theme.rcss", f"body {{{eol}}}{eol}")
        write(folder / "theme.rml", theme_rml(extends or "modern", eol))
    return theme_view(theme_id)


def theme_rml(parent, eol):
    """The parent's theme.rml with its own sheets addressed through its folder and the new theme's tokens linked last."""
    text = read(THEMES / parent / "theme.rml").replace("\r\n", "\n")
    text = re.sub(r'href="(theme|components)\.rcss"', lambda m: f'href="../{parent}/{m.group(1)}.rcss"', text)
    last = max(m.end() for m in re.finditer(r'<link[^>]*theme\.rcss"/>\n', text))
    text = text[:last] + '<link type="text/rcss" href="theme.rcss"/>\n' + text[last:]
    return text.replace("\n", eol)


# --- the previewer -----------------------------------------------------------------------------------------------------

def preview_status():
    if not PREVIEW:
        return False, "No previewer set. Start the server with --preview <path to xirml_preview.exe> or set XIRML_PREVIEW."
    if not os.path.isfile(PREVIEW):
        return False, f"The previewer was not found at {PREVIEW}."
    return True, PREVIEW


def render(theme_id, panel, whole, extra=()):
    """PNG bytes of the panel in the theme, cropped to the panel when possible; extra: more previewer arguments."""
    theme_dir(theme_id)
    if not PANEL_ID.fullmatch(panel):
        raise ValueError("a panel id is a-z, 0-9, -, _ and /")
    ok, message = preview_status()
    if not ok:
        raise PreviewError(message)
    with RENDER_LOCK, tempfile.TemporaryDirectory(prefix="xirml-theme-editor-") as shots:
        command = [PREVIEW, "--ui", str(UI), "--panel", panel, "--theme", theme_id, "--shots", shots, "--shot", *extra]
        for attempt in range(3):
            try:
                run = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=60, cwd=shots,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                failed, output = run.returncode != 0, (run.stderr.strip() + "\n" + run.stdout.strip()).strip()
                problem = output or f"the previewer exited with code {run.returncode} and said nothing"
            except (OSError, subprocess.TimeoutExpired) as error:
                failed, output, problem = True, "", f"could not run the previewer: {error}"
            # A failure the previewer explains is final. A silent one may be the exe mid-rebuild: wait and retry.
            if not failed or output or attempt == 2:
                break
            time.sleep(3)
        if failed:
            raise PreviewError(problem)
        last = run.stdout.strip().splitlines()[-1].strip() if run.stdout.strip() else ""
        shot = Path(last) if last and os.path.isfile(last) else next(Path(shots).glob("*.png"), None)
        if shot is None:
            raise PreviewError("the previewer wrote no PNG\n" + output)
        if panel != "inventory" and shot.name.startswith("preview_inventory_"):
            raise PreviewError(f"the previewer does not know the panel '{panel}' (it rendered the inventory instead)")
        box = None if whole else PANELS.get(panel)
        if Image is None or box is None:
            return shot.read_bytes()
        with Image.open(shot) as image:
            cropped = io.BytesIO()
            image.crop(tuple(min(edge, limit) for edge, limit in zip(box, image.size * 2))).save(cropped, "PNG", compress_level=1)
            return cropped.getvalue()


# --- http --------------------------------------------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def handle_request(self, post):
        # Only this machine's own page may talk to the server: no DNS rebinding, no cross-site form posts.
        port = self.server.server_address[1]
        if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return self.reply(403, {"error": "unexpected Host header"})
        url = urlsplit(self.path)
        query = {key: values[0] for key, values in parse_qs(url.query).items()}
        try:
            if post:
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    return self.reply(415, {"error": "send application/json"})
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 1 << 20)))
                if not isinstance(body, dict):
                    raise ValueError("expected a JSON object")
                if url.path == "/api/theme":
                    return self.reply(200, create_theme(body.get("id"), body.get("name"), body.get("description", ""), body.get("extends", "")))
                if url.path == "/api/token":
                    return self.reply(200, set_token(body.get("theme"), body.get("name"), body.get("value")))
            elif url.path == "/":
                return self.reply(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/themes":
                ok, message = preview_status()
                themes = sorted(list_themes().values(), key=lambda theme: (theme["order"], theme["id"]))
                return self.reply(200, {"themes": themes, "panels": list(PANELS), "preview": {"ok": ok, "message": message}, "crop": Image is not None})
            elif url.path == "/api/theme":
                theme_dir(query.get("id"))
                return self.reply(200, theme_view(query["id"]))
            elif url.path == "/api/render":
                return self.reply(200, render(query.get("theme"), query.get("panel", "inventory"), query.get("full") == "1"), "image/png")
            self.reply(404, {"error": "not found"})
        except PreviewError as error:
            self.reply(502, {"error": str(error)})
        except (ValueError, OSError) as error:
            self.reply(400, {"error": str(error)})

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)


def selftest():
    lines = parse("/*\n a header: `--not: this;`\n*/\nbody {\n\t/* text */\n\t--ink: #fff;  /* primary */\r\n\t--gold : #e8c98a ;\n\t/* glass */\n\t--tint: var(--gold)1a;\n}\n")
    assert [(line["name"], line["value"], line["section"]) for line in lines] == [
        ("ink", "#fff", "text"), ("gold", "#e8c98a", "text"), ("tint", "var(--gold)1a", "glass")], lines
    assert lines[0]["comment"] == "primary"
    assert expand("var(--gold)99 0 var(--gold)", {"gold": "#abc"}.__getitem__) == "#abc99 0 #abc"
    values, errors = settle({"tint": "var(--gold)1a", "gold": "#111", "a": "var(--b)", "b": "var(--a)", "c": "var(--nope)"})
    assert values["tint"] == "#1111a" and values["a"] == "var(--b)" and values["c"] == "var(--nope)", values
    assert errors == {"a": "--a is defined through itself", "b": "--b is defined through itself", "c": "unknown token --nope"}, errors
    base = "body {\n\t/* text */\n\t--ink: #fff;\n\t/* glass */\n\t--tint: #000;\n}\n"
    theme = apply_edit("body {\n}\n", base, "tint", "#111")
    assert theme == "body {\n\n\t/* glass */\n\t--tint: #111;\n}\n", repr(theme)
    theme = apply_edit(theme, base, "ink", "#eee")
    assert theme == "body {\n\n\t/* glass */\n\t--tint: #111;\n\n\t/* text */\n\t--ink: #eee;\n}\n", repr(theme)
    kept = apply_edit("body {\n\t/* mine */\n\t--tint: #111; /* why */\n\t--other: 1;\n}\n", base, "tint", "#222")
    assert kept == "body {\n\t/* mine */\n\t--tint: #222; /* why */\n\t--other: 1;\n}\n", repr(kept)
    assert apply_edit(kept, base, "tint", None) == "body {\n\t/* mine */\n\t--other: 1;\n}\n"
    added = apply_edit(kept, base, "tint2", "1")
    assert added == "body {\n\t/* mine */\n\t--tint: #222; /* why */\n\t--other: 1;\n\n\t/* added */\n\t--tint2: 1;\n}\n", repr(added)
    rml = theme_rml("ff7", "\n")
    assert '"../ff7/theme.rcss"/>\n<link type="text/rcss" href="theme.rcss"/>' in rml and 'href="components.rcss"' not in rml, rml
    for bad in ("", "..", "a/b", "A", "a" * 33, "a\n", None):
        try:
            theme_dir(bad)
            raise AssertionError(f"{bad!r} must not be a theme id")
        except ValueError:
            pass
    view = theme_view("modern")
    assert any(token["name"] == "gold" for group in view["groups"] for token in group["tokens"])
    print("ok")


def main():
    global PREVIEW
    arguments = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    arguments.add_argument("--preview", default=os.environ.get("XIRML_PREVIEW", ""), help="path to xirml_preview.exe (or set XIRML_PREVIEW)")
    arguments.add_argument("--port", type=int, default=8765)
    arguments.add_argument("--selftest", action="store_true", help="check the token file handling and exit")
    options = arguments.parse_args()
    if options.selftest:
        return selftest()
    PREVIEW = os.path.abspath(options.preview) if options.preview else ""
    server = ThreadingHTTPServer(("127.0.0.1", options.port), Handler)
    print(f"xirml theme editor: http://127.0.0.1:{options.port}/", flush=True)
    print(f"themes: {THEMES}", flush=True)
    print(f"preview: {preview_status()[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
