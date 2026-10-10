# Contracts

Each game menu xirml redraws has a contract in `data/contracts/en-US.json`. The contract lists the menu's buttons,
where its text and pictures are, and what each of them means. Every frame, xirml checks the menu against it. If
everything on screen is accounted for, you get the xirml panel. If anything isn't, you keep the game's own menu and
xirml tells you why.

## When a menu keeps the old look

The first time a menu is turned down for a given reason, you get a line in chat like this one:

```text
[xirml] 'tskill1' stays native: art no field claims: an icon at 33,51
```

xirml also saves that frame to `logs\xirml_dumps\<id>_rejected_<n>.txt`, with the reason on the first line. That file is
what a fix is made from, so attach it to your issue or pull request.

A menu with no contract at all says `'<id>' stays native: no contract describes it yet`, once per session. Its dump in
`logs\xirml_dumps\<id>.txt` lists the menu's buttons and their art, which is where a new contract starts.

## Format

```json
{
  "id": "prty1",
  "document": "contract.rml",
  "layout": "menu-column",
  "controls": [
    { "button": 0, "shapes": [{ "library": "menu    comwin  ", "index": 6 }] },
    { "button": 1, "area": [16, 6, 104, 22], "shapes": [{ "library": "menu    windowps", "index": 78 }] }
  ],
  "slots": [
    { "button": 1, "role": "row", "fields": [
      { "source": "text", "area": [2, -2, 82, 16], "anchor": -1, "role": "label", "label": "Seek Party" }
    ] }
  ]
}
```

`controls` are the menu's buttons, numbered as the game numbers them, with their position and the art they draw.
Button 0 is the window frame. They come from the game's menu data. If the buttons differ, it's a different layout.

`slots` are the rows of the panel, in order. Each one belongs to a button, or to the frame (button 0). Its `role` is
what the template styles: `heading`, `row`, `section`, `choice`, `item-slot`, `message` and so on.

`fields` are the parts of a slot. `source` is what to read: `text`, `image`, `number`, `gauge`, `entry` (a text box),
`mark`, `art` or `frame`. `area` is where to look, in window pixels, measured from the slot's button (`"anchor": -1`),
another button, or the frame.

A field marked `optional` can be empty. Any other field has to be there or the frame is turned down.

`alternatives` holds other layouts of the same menu. xirml picks the one whose buttons match and whose content fits. If
two layouts both fit a frame, the frame is turned down, so make sure each layout rejects what the others accept.

Some menus change while you look at them. These flags handle that:

| Flag | On | Meaning |
|---|---|---|
| `"relocates": true` | a control | The button moves or resizes between states, so its position isn't checked |
| `"runtime": true` | a control | The game draws this button itself, like a toggle. Its label is read off the screen |
| `"index": "any"` | a shape | The window sizes itself to its text and picks a matching frame. Any frame from that library is fine |
| `"reserve": true` | a slot | The slot keeps its place when empty, as in an item grid |
| `"plain": true` | a text field | Only plain text, no sprite labels. Lets a list layout turn down a layout with sprite headings |

## Layouts and roles

`layout` and every `role` become CSS classes on the panel, styled in `ui/templates/contract.rml`. A new role needs a
rule there. `"layout": "item-grid actions-right"` is two classes: an item grid with its actions on the right.

## Sending a fix

- Add a field for whatever was left unclaimed. Don't make fields `optional` just to silence a rejection.
- Read positions from the saved frame. The dump lists every text and drawing with its coordinates.
- One menu per pull request, with the rejected frame it fixes.
