# Fonts

Four tokens choose the fonts:

- `--font-body` for everything that doesn't have its own token
- `--font-title` for panel titles and the compass letters
- `--font-numbers` for counts, stack sizes, party HP/MP/TP, levels, sheet values and the clock
- `--font-nameplate` for names above characters

By default that's Noto Sans JP for body, numbers and names, and Cinzel for titles. Change them on the Theme page in
Settings or with `/xirml font body|title|numbers|nameplate <name>`. Saving writes the tokens to your theme's
`theme.rcss`.

Nameplates can use any body font. They're drawn with the face closest to `--weight-nameplate` (600), and every plate is
redrawn when you switch.

## Adding a font: `ui/fonts/fonts.json`

Every font a `--font-*` token can name is listed here, with its files and weights. xirml reads it on startup and
offers those fonts in Settings. To ship a font with your theme, put the files in `ui/fonts/` and add an entry. No
plugin change needed.

```json
{ "version": 1, "families": [
  { "family": "Noto Sans JP", "fallback": true, "faces": [ { "file": "NotoSansJP-Regular.ttf", "weight": 400 }, { "file": "NotoSansJP-Medium.ttf", "weight": 500 } ] },
  { "family": "Cinzel", "title": true, "faces": [ { "file": "Cinzel-Bold.ttf", "weight": 700 } ] },
  { "family": "Georgia", "system": true, "faces": [ { "file": "georgiaz.ttf", "weight": 700, "style": "italic" } ] } ] }
```

| Field | Meaning |
|---|---|
| `family` | The name tokens use. Case, spaces and quotes don't matter, and it overrides whatever the file calls itself |
| `faces` | 1 to 16 entries, each a `file` (just the name, no folders), a `weight` from 100 to 900 and an optional `style` (`normal` or `italic`) |
| `title` | Offer it for titles. Otherwise it's offered for body, numbers and names |
| `system` | Load the files from `%WINDIR%\Fonts`. Skipped if the first file isn't there |
| `fallback` | The font used for game symbols and for any character another font is missing. Defaults to the first family |
| `tabular` | All ten digits have the same width (within 0.5% of the em), so numbers line up in columns. Settings marks these fonts |

A few rules:

- Only fonts with an upright face show up in Settings and `/xirml font`. RmlUi won't fall back from italic to upright,
  so Georgia Bold Italic is only used for Classic's frame titles (`--font-frame-title`).
- A face's `weight` is matched to Noto Sans JP by measuring stroke thickness (see below), not taken from the file. M PLUS
  Rounded 1c and Zen Kaku Gothic New have no SemiBold, and their Bold measures like Noto's SemiBold, so it's listed as 600.
- The file is strict JSON, up to 64 families. An unknown field, a wrong type or a bad file name rejects the whole file.
  If it's missing or broken, the log says so and Settings has no fonts to offer.

## Bundled fonts

| Family | Offered for | Files | Size | Licence | Digits (0-9 advance widths) |
|---|---|---|---|---|---|
| Noto Sans JP (default) | body, numbers | Regular, Medium, SemiBold (Latin subset; Medium a static instance of the variable font) | 106 + 106 + 106 KB | OFL 1.1 | aligned |
| M PLUS 2 | body, numbers | Regular, Medium, SemiBold (static instances of the variable font, Latin subset) | 50 + 50 + 50 KB | OFL 1.1 | aligned (633/634 units, 0.1% of the em) |
| M PLUS Rounded 1c | body, numbers | Regular, Medium, Bold as 600 (Latin subset) | 86 + 87 + 89 KB | OFL 1.1 | aligned |
| Zen Kaku Gothic New | body, numbers | Regular, Medium, Bold as 600 (Latin subset) | 52 + 51 + 51 KB | OFL 1.1 | proportional (1 is 383 units, 8 is 509) |
| IBM Plex Sans JP | body, numbers | Regular, Medium, SemiBold (Latin subset) | 94 + 94 + 94 KB | OFL 1.1 | aligned (SemiBold 629/630 units) |
| Atkinson Hyperlegible | body | Regular, Bold as 600 (Latin subset) | 44 + 45 KB | OFL 1.1 | proportional (1 is 402 units, 0 is 648) |
| Fira Sans | body | Regular, Medium, SemiBold (Latin subset) | 107 + 106 + 114 KB | OFL 1.1 | proportional (433-558 units) |
| Nunito | body, numbers | Regular, Medium, SemiBold (static instances of the variable font, Latin subset) | 45 + 45 + 45 KB | OFL 1.1 | aligned |
| JetBrains Mono | body, numbers | Regular, Medium, SemiBold (static instances of the variable font, Latin subset) | 62 + 62 + 62 KB | OFL 1.1 | aligned (monospaced) |
| Cinzel (default) | titles | Bold | 29 KB | OFL 1.1 | proportional |
| Marcellus | titles | Regular (its only weight, Latin subset) | 40 KB | OFL 1.1 | proportional |
| Cormorant Garamond | titles | Bold (static instance, subset) | 63 KB | OFL 1.1 | proportional |
| Philosopher | titles | Bold (Latin subset) | 76 KB | OFL 1.1 | proportional |
| IM Fell English | titles | Regular (its only upright weight, Latin subset) | 143 KB | OFL 1.1 | proportional |
| Almendra | titles | Bold (Latin subset) | 33 KB | OFL 1.1 | proportional |
| Segoe UI | body, numbers | Windows: `segoeui.ttf` (400), `seguisb.ttf` (Semibold 600) | 0.9 + 0.9 MB in memory once picked | Windows | proportional |
| Georgia | frame titles only (`--font-frame-title`) | Windows: `georgiaz.ttf` (Bold Italic 700) | 0.2 MB, with classic | Windows | not offered |

The fonts come from google/fonts (`ofl/<family>`), each with its licence next to it as `ui/fonts/OFL-<Family>.txt`. M
PLUS Rounded 1c's folder there has no OFL.txt, but its name table says OFL 1.1, so its licence file is the OFL text with
its copyright line.

Windows fonts are only offered if the file is in `%WINDIR%\Fonts`. In a `.ttc` collection the face is found by family
name (or a name starting with it) and OS/2 weight.

FFXI's own title font isn't available. It's a sprite sheet (`menu    menu2fon`), not a font file RmlUi can load.

Some static weights were cut from variable fonts with fonttools:

```
fonttools varLib.instancer "MPLUS2[wght].ttf" wght=400 --update-name-table -o MPLUS2-Regular.ttf
fonttools varLib.instancer "MPLUS2[wght].ttf" wght=600 --update-name-table -o MPLUS2-SemiBold.ttf
fonttools varLib.instancer "CormorantGaramond[wght].ttf" wght=700 --update-name-table -o CormorantGaramond-Bold.ttf
```

## Memory

xirml only loads the faces it needs: for each font, the ones closest to the weights it's used at. The body font uses
`--weight-body`, `--weight-chat` and `--weight-strong`. The numbers font uses `--weight-numbers` and `--weight-strong`.
On a tie the lighter face wins.

Out of the box that's three files: Noto Medium, Noto SemiBold and Cinzel. Choosing another font loads its faces at
that moment. RmlUi can't unload a font, so anything you've picked stays in memory until you `/unload xirml` and
`/load xirml` again. A bundled body font costs 0.1 to 0.2 MB, Segoe UI 1.9 MB.

Noto Sans JP, at the face closest to `--weight-body`, fills in for the game's symbols (♪, ◇, arrows) in title fonts and
for any character a font lacks.

The "aligned digits" mark in Settings is checked with FreeType when xirml starts. RmlUi can't turn on tabular figures,
so with a proportional font a column of numbers wiggles as the values change. Pick an aligned font for
`--font-numbers`.

The samples in the font list are drawn straight from the files with FreeType, so browsing the list doesn't load
anything into RmlUi.

## How the default weights were chosen

The game's own text was measured as stroke thickness over cap height, then compared with Noto at different weights:

| Role | Source | Cap px | Stem/cap (median run) | Stroke/cap (2 area/outline) | Ink coverage | Contrast |
|---|---|---|---|---|---|---|
| body | native: help line | 34 | 0.174 | 0.136 | 0.65 | 175 |
| body | before: Noto 400 | 26 | 0.115 | 0.103 | 0.43 | 181 |
| body | after: Noto 500 | 26 | 0.153 | 0.122 | 0.50 | 183 |
| numbers | native: status window | 28 | 0.250 | 0.140 | 0.49 | 113 |
| numbers | before: 600 / 400 | 23 | 0.174 | 0.112 | 0.40 | 193 |
| numbers | after: 600 | 23 | 0.174 | 0.131 | 0.45 | 193 |
| labels (body) | native: status labels | 28 | 0.250 | 0.166 | 0.60 | 132 |
| labels (body) | before: Noto 400 | 22 | 0.136 | 0.109 | 0.41 | 143 |
| labels (body) | after: Noto 500 | 24 | 0.167 | 0.127 | 0.50 | 143 |
| chat | native: chat log | 30 | 0.230 | 0.145 | 0.63 | 168 |
| chat | before: Noto 400 | 27 | 0.111 | 0.069 | 0.39 | 159 |
| chat | after: Noto 500 | 27 | 0.148 | 0.085 | 0.46 | 159 |

Each font was also rendered with FreeType at the in-game size (12dp at 3x) and measured the same way. Noto 400 comes
out at 0.095 here and 0.102 in game, close enough to trust:

| Family | 400 | 500 | 600 | 700 |
|---|---|---|---|---|
| Noto Sans JP | 0.095 | 0.117 | 0.128 | 0.143 |
| M PLUS 2 | 0.086 | 0.116 | 0.133 | 0.146 |
| M PLUS Rounded 1c | 0.083 | 0.112 | | 0.134 |
| Zen Kaku Gothic New | 0.070 | 0.102 | | 0.128 |
| IBM Plex Sans JP | 0.090 | 0.118 | 0.131 | 0.148 |

The game's body text measures 0.136, numbers 0.140 and chat 0.145 (0.107 to 0.145 across screenshots), and all of it
is a light core with a dark outline. So:

- Body and chat use 500. Noto Medium (0.117) gets most of the way from Regular (0.095) towards the game (0.136), and
  stays well below `--weight-strong` (600), so names, headings and the selected row still stand out.
- Numbers use 600. The game's digits are the heaviest text on screen (0.140), and SemiBold (0.128 to 0.131) is the
  closest face. It's loaded anyway for bold text, so it costs nothing extra. Party HP/MP/TP, sheet bonuses, gauge
  values and target HP% now all match, like in the game.
- Titles stay as they are. Cinzel Bold (0.130) is the heaviest Cinzel there is. The game's small italic window titles
  (0.27) are a different style altogether. For heavier titles, pick a heavier `--font-title`.
- Every font uses its closest face. Medium is the 500 in all bundled body fonts. Where there's no SemiBold, Bold stands
  in as 600 (0.134 and 0.128). Windows fonts keep their own weights: Segoe UI has 400 and 600, and 500 text uses 400.
- Setting `--weight-body` back to 400 loads Noto Regular when you pick it, about 1.4 MB. The Theme page offers 400 to 700.

## Icons

Templates ask for icons by name, like `<span class="icon">{{ 'search' | icon }}</span>`. Names are read from the icon
font when xirml starts, so adding a glyph means updating the font build script and rebuilding the font. An unknown
name shows up as an RmlUi warning, an empty one draws nothing.

The `.icon` class (in `components.rcss`) sets the font and keeps the surrounding text colour, so icons follow the theme.

| Glyphs | Source | Licence | Used in |
|---|---|---|---|
| main sub range ammo head neck ear body hands ring back waist legs feet | game-icons.net (Lorc, Delapouite, Lucasms) | CC BY 3.0 | empty equipment and check cells (`{{ c.label \| icon }}`) |
| tank healer support dps | game-icons.net (Lorc, Zeromancer) | CC BY 3.0 | party list, before the job; off by default, `--role-icons: inline-block` turns them on |
| close search appearance panels nameplates theme layout diagnostics warning | Material Symbols Rounded, filled | Apache 2.0 | settings: close button, navigation, search, warnings |
| enter mouse more rare ex | Material Symbols Rounded, filled | Apache 2.0 | key hints, mouse hint, the card's "more" marker, Rare/Ex pills |
| signal-1 signal-2 signal-3 | Material Symbols Rounded, filled | Apache 2.0 | network status bars (3 at 80% and up, 2 at 50% and up) |

Attribution for every icon, and the Apache 2.0 notice, are in `ui/fonts/LICENSE-XirmlIcons.txt`.
