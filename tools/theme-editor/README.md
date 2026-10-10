# Theme editor

Edit a theme's colours in your browser and see each change in the real renderer.

## Running it

```text
python tools/theme-editor/server.py --preview <path to xirml_preview.exe>
```

Then open `http://127.0.0.1:8765/`. Use `--port <n>` for a different port, or set `XIRML_PREVIEW` instead of passing
`--preview`. You can still edit without the previewer, you just won't get the picture.

Only Python 3 is required. Install Pillow if you want the preview cropped to the panel you're working on.

## What you can do

- Pick a theme from `ui/themes/`, or create one: give it an id, a name, a description and a parent theme
- Browse every token the theme ends up with, grouped like `ui/base/theme.rcss`, with where each value comes from (base,
  a parent, or this theme). There's a filter box
- Change a value and it's written to the theme's `theme.rcss`. Existing lines and comments are left alone, new tokens
  go next to their section. `reset` puts back the last committed value, or removes the line if the theme never set it
- Colour values get a colour picker. It has no alpha slider, so any alpha in the value is kept
- After each edit the panel is re-rendered. If the previewer fails you see its error instead. `whole scene` shows the
  full screen, and `other…` takes any panel id, such as `live/menuwind`

## Good to know

- Tokens can reference other tokens. Change `--gold` and everything defined from it changes too, like `--glass-tint`
  (`var(--gold)1a`). Those rows still say `base` because that's where they're written
- A reference to a token that doesn't exist breaks the whole theme in the plugin. The editor flags the row and shows
  the error
- Crop boxes are fixed per panel (`PANELS` in `server.py`). If your theme makes a panel much bigger, use `whole scene`
- The server only listens on 127.0.0.1 and only writes inside `ui/themes/<id>/`
- `python tools/theme-editor/server.py --selftest` tests the token file handling
