# Making a theme: FF8 walkthrough

This is how the `ff8` theme was put together. Do the same for yours.

It's four files, about 180 lines in total:

| File | Lines | Holds |
|---|---|---|
| `theme.json` | 10 | Name, description, picker order, parent theme |
| `theme.rcss` | 125 | Colours for text, windows, gauges, chat, compass |
| `theme.rml` | 14 | Which stylesheets load, and in what order |
| `components.rcss` | 33 | Gradient direction, title style, gauge frame |

## 1. Find references

I used the Final Fantasy VIII page on [Game UI Database](https://www.gameuidatabase.com/gameData.php?id=1896) (95
screenshots). The item menu, status screen and config screen cover pretty much everything.

Colours were picked straight from those screenshots:

| What | Colour | Token |
|---|---|---|
| Window fill, left edge to a third in to right edge | `#404040`, `#636164`, `#524e50` | `--ff8-left`, `--ff8-mid`, `--ff8-right` |
| Bevel: outer line, light top and left, dark bottom and right | `#282828`, `#848285`, `#383838` | `--ff8-bevel-outer`, `-light`, `-dark` |
| Text and its drop shadow | `#e6e4e5`, `#373538` | `--ink`, `--text-shadow` |
| Small window titles (HELP, COMMAND) | `#acaaad` | `--ff8-label`, `--ink-dim` |
| Gauge fill, dark edge to lit middle | `#696ad6` to `#bcbbff` | `--hp-start`, `--hp-end`, `--gold` |
| Gauge track and silver frame | `#272926`, `#c4c2c5` | `--gauge-track`, `--ff8-gauge-frame` |
| The one warm colour (level star) | `#fbfd6e` | `--gold-warm`, `--rare`, `--item-usable` |

The theme uses no images from the game, only colours and CSS.

## 2. Colours

`theme.json` names the theme and picks the theme it builds on:

```json
{
  "schema": 1,
  "name": "FF8",
  "description": "Brushed grey windows with a bevel, after the 1999 menus.",
  "extends": "ff7",
  "order": 45,
  "bundled": true,
  "preview": { "top": "#636164", "bottom": "#404040", "rule": "#848285" },
  "capabilities": { "windowStyleArt": false }
}
```

FF7 already has solid bevelled windows, a glove pointer and shadowed text, so it was the obvious parent. If your theme
looks more like a recoloured Classic, extend `classic`.

`theme.rcss` is a single `body { }` rule of `--name: value;` lines with the colours you want to change. With just
`theme.json` and `theme.rcss`, FF8 already showed up as grey bevelled windows with the glove, and appeared in the
theme picker with its `preview` colours. That took a few minutes, and for a lot of themes it's all you need.

To find what to change, read the parent's `theme.rcss` from top to bottom. It's split into sections: text, accents,
window, controls, gauges, job roles, item rarity, target names, status framing, chat, compass and cursor.

## 3. Things colours can't do

Three things in the screenshots needed actual CSS:

- the window gradient goes left to right (FF7's goes top to bottom)
- window titles are small grey capitals
- gauges have a silver frame

That CSS goes in `ui/themes/ff8/components.rcss`. To load it, the theme needs its own `theme.rml`:

```xml
<template name="theme">
<head>
<link type="text/rcss" href="../../base/theme.rcss"/>
<link type="text/rcss" href="../ff7/theme.rcss"/>
<link type="text/rcss" href="theme.rcss"/>
<link type="text/rcss" href="../../base/components.rcss"/>
<link type="text/rcss" href="../ff7/components.rcss"/>
<link type="text/rcss" href="components.rcss"/>
<link type="text/rcss" href="xirml:highlight/theme-frame.rcss"/>
<link type="text/rcss" href="xirml:pointer"/>
<link type="text/rcss" href="xirml:rows"/>
</head>
<body></body>
</template>
```

Order matters, later sheets win. Colours first (base, then FF7, then FF8), then component styles in the same order,
then the cursor highlight, pointer and row style.

## 4. Try it

Copy the folder to `config\xirml\ui\themes\` and run `/xirml theme ff8`. After each edit, `/xirml reload`. You can
also tweak colours live from the Theme page in the settings panel, which saves them back to `theme.rcss`.

Before calling it done, look at the inventory, equipment, party list, chat, settings panel and at least one menu.

## 5. Gotchas

- A child theme's `components.rcss` won't load unless the child has its own `theme.rml`, and that file has to link the
  parent's `components.rcss` too (`../ff7/components.rcss`). Forget either and nothing complains, the file is just
  ignored.
- Menus style their own heading in `ui/templates/contract.rml`, which loads after your theme. To restyle it you need a
  more specific selector. FF8 uses `body.contract .screen-slot.role-heading .screen-field.role-title`. Other panels
  pick up `.panel-title` from the theme normally.
- The parent's own tokens come along. FF7's styles read `--ff7-bevel-light`, `--ff7-bevel-dark` and so on, so FF8 sets
  those in one block, pointing at its own colours.
- You're limited to the bundled fonts. FF8's pixel font isn't available, so FF8 keeps FF7's rounded one.
