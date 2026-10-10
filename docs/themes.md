# Theme reference

## Where things live

| File | What's in it |
|---|---|
| `ui/base/theme.rcss` | Every token and its default value, in one `body { --name: value; }` rule: colours, glass, fonts, sizes, radii, spacing, glows, animation timing |
| `ui/base/components.rcss` | The building blocks templates use: panels, headers, titles, counters, lists, rows, icon slots, scrollbars, item cards, chips, key hints, gauges, party rows, buff tiles, equipment cells. Styled with tokens only |
| `ui/templates/*.rml` | Panel layouts and data bindings. No colours or fonts here |
| `ui/fonts/fonts.json` | The fonts a `--font-*` token can name (see [fonts.md](fonts.md)) |
| `ui/cursors/` | Row highlights (`highlight-<style>.rcss`), pointers (`pointer-<kind>.rcss`) and pointer images (`<name>.png`, used as `xiframe:<name>`). Drop a file in to add a choice |
| `ui/themes/<id>/theme.json` | The theme's name, description, picker order, parent and capabilities |
| `ui/themes/<id>/theme.rml` | The theme's stylesheet list, in load order |

## Tokens

Tokens are CSS custom properties. Every element inherits them from `body`. A token can use another one with
`var(--name)`, and you can add alpha to a six-digit colour: `var(--gold)99` is gold at alpha 0x99. References resolve
where the token is used, so redefining `--gold` in your theme also changes every token built from it. Component styles
and inline `style` attributes use tokens the same way. Font tokens name the family without quotes:
`--font-body: Noto Sans JP;`.

Some groups worth knowing:

- gauge colours: `--hp-*`, `--mp-*`, `--tp-*`, `--low-*`, `--gauge-track`, `--gauge-trail`
- gauge animation: `--motion-gauge`, `--motion-trail`, `--delay-trail`
- job role colours for party badges: `--role-tank`, `--role-healer`, `--role-support`, `--role-dps`
- item rarity: `--rare`, `--ex`
- buff and debuff edges: `--buff-edge`, `--debuff-edge`
- icon sizes: `--buff-size`, `--cell-size`
- panel animations: `--motion-open`, `--motion-scroll`, `--motion-swap`, `--ease`

Fonts are set with `--font-body`, `--font-title`, `--font-numbers` and `--font-nameplate`, which name families from
`ui/fonts/fonts.json`. `--weight-body`, `--weight-strong`, `--weight-numbers` and `--weight-chat` pick the closest face
in each family. Nameplates are drawn with `--weight-nameplate` (600).

The game's text colours map to the classes `tone-plain`, `tone-dim`, `tone-gold`, `tone-red`, `tone-green`,
`tone-blue` and `tone-violet`, defined in `components.rcss`.

## Picking a theme

Run `/xirml theme <name>`, click its swatch in Settings, or set `theme = <name>` in `settings.ini`. The bundled themes
are ordinary folders, nothing about them is hardcoded.

Your own theme goes in `ui/themes/<name>/`. Copying a bundled theme is the quickest way to start, and
[theme-authoring.md](theme-authoring.md) walks through a full one. Folder names can use lowercase letters, digits,
`-` and `_`, up to 32 characters.

Your `theme.rcss` only needs the tokens you change. `theme.rml` loads `ui/base/theme.rcss`, then each parent's
`theme.rcss`, then yours, so yours wins. Component styles come next, then the cursor highlight, pointer and row style.
A child theme's `theme.rml` replaces its parent's, so it has to list the parent's sheets itself (see
`themes/ff8/theme.rml`). If a token is used but never defined, RmlUi logs it.

## Example: a blue Classic

`ui/themes/my-blue/theme.json`:

```json
{
  "schema": 1,
  "name": "My Blue",
  "description": "Classic framing with a cooler accent.",
  "extends": "classic",
  "order": 100,
  "preview": { "top": "#123754", "bottom": "#061726", "rule": "#9bc8ee" },
  "capabilities": { "windowStyleArt": true }
}
```

`ui/themes/my-blue/theme.rcss`:

```css
body {
	--gold: #9bc8ee;
}
```

`ui/themes/my-blue/theme.rml`, which is Classic's list with your sheet added after Classic's:

```xml
<template name="theme">
<head>
<link type="text/rcss" href="../../base/theme.rcss"/>
<link type="text/rcss" href="../classic/theme.rcss"/>
<link type="text/rcss" href="theme.rcss"/>
<link type="text/rcss" href="../../base/components.rcss"/>
<link type="text/rcss" href="../../base/frame.rcss"/>
<link type="text/rcss" href="../classic/components.rcss"/>
<link type="text/rcss" href="xirml:highlight/theme-frame.rcss"/>
<link type="text/rcss" href="xirml:pointer"/>
<link type="text/rcss" href="xirml:rows"/>
</head>
<body></body>
</template>
```

Reload and it shows up in Settings with its name, description and swatch. The swatch is a gradient from `top` to
`bottom` with a `rule` line, each `#rrggbb` or `#rrggbbaa`. Leave out `preview` and you get the default swatch.

### theme.json fields

`schema` and `name` are required. `description`, `extends`, `order`, `bundled`, `preview` and
`capabilities.windowStyleArt` are optional. Lower `order` comes first in the picker. If `windowStyleArt` is missing it's
inherited from the parent. `bundled` defaults to false, and duplicating a theme clears it. A folder without
`theme.json` still works and is listed under its folder name.

The JSON is strict: unknown fields, wrong types, a missing parent or a loop of parents are all reported. If you break a
theme while editing, xirml keeps the last version that worked. Changes to the manifest, tokens and stylesheets are
picked up automatically.

## Cursor settings

Two settings change the list cursor in any theme. They load after the theme's component styles.

`cursor` (`/xirml cursor <style>`) picks the row highlight from `ui/cursors/highlight-<style>.rcss`: `bar`, `subtle` or
`game`. `theme` uses the theme's own: a soft fill in Classic (`ui/cursors/theme-frame.rcss`), a gold bar in Modern.
`game` is the game's orange selection bar. An unknown style falls back to the theme's.

`cursor_pointer` (`/xirml pointer <kind>`) picks what's drawn left of the selected row, from
`ui/cursors/pointer-<kind>.rcss`: `hand` or `arrow`. `hand` is xirml's own pointer (`--cursor-hand`), the default in
Classic. `arrow` is the game's menu arrow, full size in the inventory and smaller in menus. Leave the setting empty and
the theme's `--cursor-pointer` token decides. Rows only indent when there's a pointer.

For the closest thing to the original look, use `cursor = game` and `cursor_pointer = arrow` (Highlight: Game,
Pointer: Game in Settings).

## Bundled themes

| Theme | Notes |
|---|---|
| `modern` | The base look, with no changes. Its folder has no tokens |
| `classic` | The game's deep blue window style (style 5, `ROM/0/19.DAT`), redrawn. The navy cloud texture comes from your game install and is tinted with a gradient. The rules, corner squares and pointing hand are drawn by xirml. Cooler accents, an orange active chat tab. The only theme that needs the game's window art |
| `ff7` | Final Fantasy VII's menus, from the Game UI Database (game 1894). Solid windows going from `#0a1cba` to `#04085a`, grey bevel with 4 dp corners, white text with a hard shadow, cyan labels next to white values. Thin gauges: blue HP, green MP, pink TP like the Limit bar, yellow at low HP. M PLUS Rounded 1c everywhere, nameplates included. The pointer is `xiframe:glove`, a white version of xirml's hand. Built from tokens and `themes/ff7/components.rcss`, no game art |
| `ff8` | Final Fantasy VIII's menus, from the Game UI Database (game 1896). Brushed grey windows, dark on the left, with a square bevel. Light grey text with a hard shadow, small grey capitals for window titles, blue-violet gauges in a silver frame, the white glove. Extends `ff7` |
| `phoenix` | Classic's framing redone in dark red and ember, after phoenix-xi.com. No game art |

## Classic tokens

Set in `ui/themes/classic/theme.rcss`:

| Token | Controls |
|---|---|
| `--frame-rule`, `--frame-side` | Top and bottom line colour, and the fainter sides. The side colour also sets the corner squares |
| `--frame-top`, `--frame-bottom` | Tint over the game's texture, top and bottom. `#ffffff` leaves it at full brightness |
| `--font-frame-title`, `--size-frame-title`, `--frame-title`, `--frame-title-outline`, `--frame-title-top` | The title that sits on the top line |
| `--cursor-hand`, `--cursor-hand-size`, `--cursor-hand-left`, `--cursor-hand-lift`, `--cursor-fill`, `--cursor-fill-end` | The pointing hand and the highlight behind it |
| `--chat-tab-active`, `--chat-tab-active-bg` | The active chat tab |

The framed look itself (title on the line, hand cursor) is in `ui/base/frame.rcss`. The frame is drawn by the
`xiframe(rule side top bottom)` decorator in xirml-core (`src/render/frame.cpp`), using `--frame-rule`, `--frame-side`,
`--frame-top` and `--frame-bottom`.

## Phoenix tokens

Set in `ui/themes/phoenix/theme.rcss`:

| Token | Controls |
|---|---|
| `--royal` | Frame line, cursor edge, active tab |
| `--peach` | Inner hairline |
| `--glass-border` | Outer hairline |
| `--frame-gap` | Dark gap between the two hairlines |
| `--glass-tint` | Ember glow from the bottom |
| `--ember-corner` | Glow in the corners |
| `--title-outline` | Gap in the top line around the title |
| `--gold`, `--gold-hi` | Ember accents |

Phoenix draws its frame with gradients and inset shadows in `ui/themes/phoenix/components.rcss`, and its highlight is
`ui/cursors/theme-phoenix.rcss`. It doesn't use `xiframe`, so it needs no game art, and its nameplates are upright like
Modern's.

## Fonts in Settings

On the Theme page you pick a font for each role: body, titles, numbers and names. Each choice shows a sample in its
own face. Picking one changes it on every panel right away. Save writes it to your theme's `theme.rcss` (keeping the
line's position and comment, or adding it at the end of the rule), Revert throws it away.

From chat: `/xirml font body|title|numbers|nameplate <name>`. Case, spaces and quotes don't matter.

## Upgrading an old theme

Themes used to write tokens as `$name`. To convert one:

1. In `theme.rcss`, wrap everything in `body { }` and turn `$name: value;` into `--name: value;`. References become
   `var(--name)`, so `${gold}99` is now `var(--gold)99`. Remove quotes around font names.
2. Add a `theme.rml` that loads `../../base/theme.rcss`, each parent's `theme.rcss` and then yours, followed by the
   component styles. Copying a bundled one is easiest. Documents only see tokens if they link `xirml:theme`.
3. Move `$preview-top`, `$preview-bottom` and `$preview-rule` into `theme.json` under `preview`.
