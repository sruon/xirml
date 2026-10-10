"""Renders every theme's main panels with xirml_preview into one sheet per theme, docs/gallery/<theme>.png, and writes the
index page. It also writes the README's pictures: docs/gallery/themes.png (each theme's inventory side by side) and
docs/gallery/<theme>-card.png (its inventory, party list and settings in one row), and docs/gallery/styles.png (the
menu under each list cursor highlight and row style).

    python tools/gallery.py --preview <xirml_preview.exe> [--out docs/gallery]

The panels and their crop boxes are the theme editor's; the scenes sit on a plain dark field (no game backdrop). Themes
that draw the client's own window art (capabilities.windowStyleArt) are skipped: they need a game install. Needs Pillow.
The gallery workflow runs this on every change to ui/ or data/ and commits the result.
"""
import argparse
import io
import json
import os
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent / "theme-editor"))
import server  # noqa: E402

SCALE = 0.5  # the renders are at the harness's 3x; half keeps the text readable and the sheet under 2 MB
WIDTH = 1700  # sheet width in px; the chat panel at half scale is 1542 wide
GAP = 28
BACKGROUND = (20, 20, 24)
LABEL = (150, 150, 158)


def sheet(panels):
    """One image of the panels laid out in rows, each labelled with its panel id."""
    scaled = [(name, image.resize((round(image.width * SCALE), round(image.height * SCALE)), Image.LANCZOS)) for name, image in panels]
    rows, row, x = [], [], GAP
    for name, image in scaled:
        if row and x + image.width + GAP > WIDTH:
            rows.append(row)
            row, x = [], GAP
        row.append((name, image))
        x += image.width + GAP
    rows.append(row)
    height = GAP + sum(max(image.height for _, image in row) + 20 + GAP for row in rows)
    out = Image.new("RGB", (WIDTH, height), BACKGROUND)
    draw = ImageDraw.Draw(out)
    y = GAP
    for row in rows:
        x = GAP
        for name, image in row:
            out.paste(image, (x, y))
            draw.text((x, y + image.height + 4), name, fill=LABEL)
            x += image.width + GAP
        y += max(image.height for _, image in row) + 20 + GAP
    return out


CARD = ("inventory", "party", "settings")
# the pointers draw the client's own art (arrow) or need it loaded (hand), which the gallery's runner doesn't have
STYLES = [("highlight", "--cursor", ("theme", "bar", "subtle", "game")),
          ("rows", "--rows", ("flat", "raised", "outlined", "tiles"))]
STYLE_THEME, STYLE_PANEL = "modern", "live/menuwind"
STRIP_SCALE = 0.4


def trim(image):
    """The panel without the preview scene's flat grey around it (the corner pixel's colour), or its faint drop shadow."""
    field = Image.new(image.mode, image.size, image.getpixel((0, 0)))
    box = ImageChops.difference(image, field).convert("L").point(lambda value: 255 if value > 32 else 0).getbbox()
    return image.crop(box) if box else image


def strip(images, scale=SCALE, labels=None):
    """The images in one row on the dark field, trimmed of their grey, each with an optional label under it."""
    images = [trim(image) for image in images]
    scaled = [image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS) for image in images]
    below = 22 if labels else 0
    out = Image.new("RGB", (GAP + sum(image.width + GAP for image in scaled), 2 * GAP + max(image.height for image in scaled) + below), BACKGROUND)
    draw = ImageDraw.Draw(out)
    x = GAP
    for index, image in enumerate(scaled):
        out.paste(image, (x, GAP))
        if labels:
            draw.text((x, GAP + image.height + 6), labels[index], fill=LABEL)
        x += image.width + GAP
    return out


def main():
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--preview", default=os.environ.get("XIRML_PREVIEW", ""), help="path to xirml_preview.exe")
    arguments.add_argument("--out", default=str(server.ROOT / "docs" / "gallery"))
    options = arguments.parse_args()
    server.PREVIEW = os.path.abspath(options.preview)
    out = Path(options.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    manifests = {folder.name: json.loads((folder / "theme.json").read_text(encoding="utf-8"))
                 for folder in server.THEMES.iterdir() if (folder / "theme.json").is_file()}
    themes = sorted((name for name, manifest in manifests.items() if not manifest.get("capabilities", {}).get("windowStyleArt")),
                    key=lambda name: manifests[name].get("order", 0))
    skipped = sorted(set(manifests) - set(themes))
    failed = 0
    inventories = []
    rows = ["# Gallery", "", "Every panel in every theme, rendered by `tools/gallery.py`." + (
            f" Missing: {', '.join(f'`{t}`' for t in skipped)}, which needs the window art from a game install." if skipped else ""), ""]
    for theme in themes:
        rows += [f"## {manifests[theme].get('name', theme)}", "", manifests[theme].get("description", ""), ""]
        panels = []
        for panel in server.PANELS:
            try:
                panels.append((panel, Image.open(io.BytesIO(server.render(theme, panel, False))).convert("RGB")))
                print(f"{theme}/{panel}")
            except (server.PreviewError, ValueError) as error:
                failed += 1
                rows.append(f"`{panel}`: did not render ({str(error).splitlines()[0]})")
                print(f"{theme}/{panel}: {error}", file=sys.stderr)
        if panels:
            sheet(panels).save(out / f"{theme}.png", optimize=True)
            rows.append(f"![{theme}]({theme}.png)")
            rendered = dict(panels)
            if all(name in rendered for name in CARD):
                strip([rendered[name] for name in CARD]).save(out / f"{theme}-card.png", optimize=True)
            if "inventory" in rendered:
                inventories.append((manifests[theme].get("name", theme), rendered["inventory"]))
        rows.append("")
    groups = []
    for group, flag, values in STYLES:
        try:
            shots = [Image.open(io.BytesIO(server.render(STYLE_THEME, STYLE_PANEL, False, (flag, value)))).convert("RGB") for value in values]
            groups.append(strip(shots, labels=[f"{group}: {value}" for value in values]))
        except (server.PreviewError, ValueError) as error:
            failed += 1
            print(f"styles/{group}: {error}", file=sys.stderr)
    if groups:
        styles = Image.new("RGB", (max(image.width for image in groups), sum(image.height for image in groups)), BACKGROUND)
        y = 0
        for image in groups:
            styles.paste(image, (0, y))
            y += image.height
        styles.save(out / "styles.png", optimize=True)
    if inventories:
        strip([image for _, image in inventories], STRIP_SCALE, [name for name, _ in inventories]).save(out / "themes.png", optimize=True)
    (out / "index.md").write_text("\n".join(rows), encoding="utf-8")
    print(f"{len(themes)} themes, {failed} panels failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
