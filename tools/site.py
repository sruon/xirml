"""Builds the GitHub Pages site into _site/: every tracked Markdown page as HTML, keeping its path (README.md becomes
index.html), the gallery images, docs/images and the bundled fonts.

    pip install markdown
    python tools/site.py [--out _site]

The home page is the hero, the gallery (parsed from docs/gallery/index.md, which tools/gallery.py writes), live specimens
of the bundled fonts, the documentation links, then the README. Links between pages are rewritten from .md to .html;
links to other files in the repository point at GitHub. The stylesheet is tools/site/site.css, served as site.css.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/sruon/xirml"
DOCS = [("docs/theme-authoring.html", "Make a theme", "Walk through how the FF8 theme was made."),
        ("docs/themes.html", "Theme reference", "Theme files, tokens and settings."),
        ("docs/fonts.html", "Fonts", "Bundled fonts, adding your own, and the icon font."),
        ("docs/contracts.html", "Contracts", "How menus are read, and how to fix one that isn't."),
        ("tools/theme-editor/index.html", "Theme editor", "Edit theme colours in the browser with a live preview."),
        ("ui/cursors/index.html", "Cursors", "Where the hand and glove pointers come from."),
        ("docs/gallery/index.html", "Gallery page", "Every panel in every theme.")]
NAV = [("index.html#gallery", "Gallery"), ("index.html#fonts", "Fonts"), ("index.html#docs", "Documentation"), (REPO, "GitHub")]
WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700}
# family, role, files in ui/fonts (the weight is the file name's suffix)
FONTS = [("Cinzel", "titles (default)", ["Cinzel-Bold.ttf"]),
         ("Marcellus", "titles", ["Marcellus-Regular.ttf"]),
         ("Cormorant Garamond", "titles", ["CormorantGaramond-Bold.ttf"]),
         ("Philosopher", "titles", ["Philosopher-Bold.ttf"]),
         ("Noto Sans JP", "body, numbers (default)", ["NotoSansJP-Regular.ttf", "NotoSansJP-Medium.ttf", "NotoSansJP-SemiBold.ttf"]),
         ("IBM Plex Sans JP", "body, numbers", ["IBMPlexSansJP-Regular.ttf", "IBMPlexSansJP-Medium.ttf", "IBMPlexSansJP-SemiBold.ttf"]),
         ("M PLUS 2", "body, numbers", ["MPLUS2-Regular.ttf", "MPLUS2-Medium.ttf", "MPLUS2-SemiBold.ttf"]),
         ("M PLUS Rounded 1c", "body, numbers", ["MPLUSRounded1c-Regular.ttf", "MPLUSRounded1c-Medium.ttf", "MPLUSRounded1c-Bold.ttf"]),
         ("Zen Kaku Gothic New", "body, numbers", ["ZenKakuGothicNew-Regular.ttf", "ZenKakuGothicNew-Medium.ttf", "ZenKakuGothicNew-Bold.ttf"])]
PANGRAM = "Sphinx of black quartz, judge my vow"
NUMERALS = "0123456789 &middot; HP 1,234 / 1,234 &middot; TP 3000 &middot; 23:59"
SWATCHES = ["gold", "gold-hi", "gold-deep", "ink"]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>{title}</title>
<link rel="stylesheet" href="{up}site.css">
</head>
<body class="{cls}">
<header class="top"><a class="brand" href="{up}index.html">xirml</a><nav>{nav}</nav></header>
{main}
<footer>xirml is GPL-3.0. The bundled fonts are OFL 1.1. <a href="{repo}">Source on GitHub</a>.</footer>
</body>
</html>
"""


def pages():
    files = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return [Path(f) for f in files]


def target(md):
    return md.with_name("index.html") if md.name == "README.md" else md.with_suffix(".html")


def rewrite(body, md, known):
    """Relative links: .md pages become .html, other repository files point at GitHub."""
    def link(match):
        href = match.group(1)
        if re.match(r"^(https?:|mailto:|#)", href):
            return match.group(0)
        path, _, anchor = href.partition("#")
        resolved = Path(os.path.normpath(md.parent / path))
        if resolved.suffix == ".md" and resolved in known:
            rel = Path(*([".."] * (len(md.parts) - 1))) / target(resolved)
            return f'href="{rel.as_posix()}{"#" + anchor if anchor else ""}"'
        if resolved.suffix in (".png", ".jpg", ".svg"):
            return match.group(0)
        return f'href="{REPO}/blob/main/{resolved.as_posix()}"'
    return re.sub(r'href="([^"]+)"', link, body)


def render(md):
    text = (ROOT / md).read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), md.stem)
    return title, markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])


def tokens(theme, manifests):
    """The theme's resolved palette: base, then each parent, then the theme; var(--name) references substituted."""
    chain, name = [], theme
    while name and name in manifests:
        chain.insert(0, ROOT / "ui" / "themes" / name / "theme.rcss")
        name = manifests[name].get("extends")
    values = {}
    for file in [ROOT / "ui" / "base" / "theme.rcss", *chain]:
        if file.is_file():
            values.update(re.findall(r"^\s*--([\w-]+):\s*(.*?);", file.read_text(encoding="utf-8"), re.M))
    for _ in range(5):
        values = {k: re.sub(r"var\(--([\w-]+)\)", lambda m: values.get(m.group(1), m.group(0)), v) for k, v in values.items()}
    return values


def gallery(text):
    """The theme cards from docs/gallery/index.md: `## Name`, a description line, the sheet image(s)."""
    manifests = {folder.name: json.loads((folder / "theme.json").read_text(encoding="utf-8"))
                 for folder in (ROOT / "ui" / "themes").iterdir() if (folder / "theme.json").is_file()}
    ids = {manifest.get("name", theme): theme for theme, manifest in manifests.items()}
    cards, current = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            current = {"name": line[3:].strip(), "description": "", "images": []}
            cards.append(current)
        elif current is None or not line.strip():
            continue
        elif line.startswith("!["):
            current["images"] += re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        elif not current["description"] and not line.startswith("`"):
            current["description"] = line.strip()
    out = []
    for card in cards:
        theme = ids.get(card["name"])
        palette = tokens(theme, manifests) if theme else {}
        dots = "".join(f'<i style="background:{html.escape(palette[name])}"></i>' for name in SWATCHES if name in palette)
        glass = f' style="background:linear-gradient({html.escape(palette.get("glass-top", "#1c1e27"))},{html.escape(palette.get("glass-bottom", "#0b0c11"))})"' if palette else ""
        images = "".join(f'<a href="docs/gallery/{src}"><img src="docs/gallery/{src}" alt="{html.escape(alt)}" loading="lazy"></a>'
                         for alt, src in card["images"])
        out.append(f'<article class="theme"{glass}><header><h3>{html.escape(card["name"])}</h3>'
                   f'<p>{html.escape(card["description"])}</p><span class="dots">{dots}</span></header>{images}</article>')
    return "".join(out)


def specimens():
    out = []
    for family, role, files in FONTS:
        weights = sorted(WEIGHTS[Path(f).stem.rsplit("-", 1)[1]] for f in files)
        name = html.escape(family)
        rows = "".join(f'<p style="font-family:\'{name}\';font-weight:{w}">{PANGRAM} <span>{w}</span></p>' for w in weights)
        out.append(f'<article class="face"><h3 style="font-family:\'{name}\';font-weight:{weights[-1]}">{name}</h3>'
                   f'<small>{html.escape(role)}</small>{rows}'
                   f'<p class="num" style="font-family:\'{name}\';font-weight:{weights[-1]}">{NUMERALS}</p></article>')
    out.append('<article class="face"><h3>Xirml Icons</h3><small>icons</small><p>The plugin\'s icon font, with glyphs for gear slots, party roles, '
               'settings and hints. Templates pick them by name. See <a href="docs/fonts.html#icons">Fonts</a>.</p></article>')
    return "".join(out)


def faces():
    """@font-face for every bundled file; urls are relative to site.css at the site root."""
    return "".join(f"@font-face{{font-family:'{family}';font-weight:{WEIGHTS[Path(f).stem.rsplit('-', 1)[1]]};"
                   f"font-display:swap;src:url(ui/fonts/{f}) format('truetype')}}\n" for family, _, files in FONTS for f in files)


def home(body):
    body = re.sub(r"<h1[^>]*>.*?</h1>\s*", "", body, count=1)
    body = re.sub(r"<!-- pictures -->.*?<!-- /pictures -->\s*", "", body, flags=re.S)  # the home page shows the gallery itself
    lead = re.search(r"<p>(.*?)</p>", body, re.S)
    tagline = lead.group(1).split(". ")[0].rstrip(".") + "."
    docs = "".join(f'<a href="{href}"><b>{html.escape(name)}</b><span>{html.escape(blurb)}</span></a>' for href, name, blurb in DOCS)
    return f"""<main class="home">
<section class="hero"><h1>xirml</h1><p>{tagline}</p>
<p class="actions"><a class="button" href="#install">Install</a><a class="button ghost" href="{REPO}">GitHub</a></p></section>
<section id="gallery"><h2>Gallery</h2><p class="intro">Rendered from the current version. Click an image for full size.</p>{gallery((ROOT / "docs" / "gallery" / "index.md").read_text(encoding="utf-8"))}</section>
<section id="fonts"><h2>Fonts</h2><p class="intro">Every bundled font, drawn from its own file. All OFL 1.1.</p><div class="faces">{specimens()}</div></section>
<section id="docs"><h2>Documentation</h2><div class="docs">{docs}</div></section>
<section id="about" class="readme"><h2>About</h2>{body}</section>
</main>"""


def build(out):
    shutil.rmtree(out, ignore_errors=True)
    known = set(pages())
    for md in known:
        title, body = render(md)
        body = rewrite(body, md, known)
        depth = len(md.parts) - 1
        up = "../" * depth
        here = target(md).as_posix()
        nav = "".join(f'<a href="{href if href.startswith("http") else up + href}">{html.escape(name)}</a>' for href, name in NAV)
        if md == Path("README.md"):
            main = home(body)
        else:
            side = "".join(f'<a href="{up + href}"{" class=\"here\"" if href == here else ""}>{html.escape(name)}</a>' for href, name, _ in DOCS)
            main = f'<div class="wrap"><aside><nav>{side}</nav></aside><article>{body}</article></div>'
        dest = out / target(md)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(PAGE.format(title=html.escape(title), up=up, cls="doc" if main.startswith("<div") else "index", nav=nav, main=main, repo=REPO),
                        encoding="utf-8")
    for src in [*(ROOT / "docs" / "gallery").rglob("*.png"), *(ROOT / "docs" / "images").glob("*.*"), *(ROOT / "ui" / "fonts").glob("*.ttf")]:
        dest = out / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    (out / "site.css").write_text(faces() + (ROOT / "tools" / "site" / "site.css").read_text(encoding="utf-8"), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    print(f"{len(known)} pages -> {out}")


if __name__ == "__main__":
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--out", default=str(ROOT / "_site"))
    build(Path(arguments.parse_args().out))
