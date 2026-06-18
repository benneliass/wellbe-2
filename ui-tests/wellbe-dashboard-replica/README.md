# WellBe dashboard replica

Standalone coded replica of the WellBe launcher ("front door"), aligned to the
**WellBe Design System**: Plus Jakarta Sans, the teal `#0EA5A4` / slate palette,
token-based radii and shadows, the official logo orb, and the launcher's
frosted-glass + ambient-gradient treatment.

## Open it

Open this file in a browser:

```text
ui-tests/wellbe-dashboard-replica/index.html
```

Or serve the folder locally:

```sh
python3 -m http.server 4173 --directory ui-tests/wellbe-dashboard-replica
```

Then visit:

```text
http://localhost:4173
```

## Edit it

- Structure and labels live in `index.html`.
- Design-system tokens (colors, type, radii, shadows, spacing) live in `tokens.css` — the
  single source of truth, copied from the WellBe Design System. Edit tokens there, not inline.
- Layout, glass effects, and responsive behavior live in `styles.css` (consumes the tokens).
- `logo.png` is the official WellBe brand mark, used for both the nav mark and the hero orb.
- The prototype uses only local HTML/CSS/SVG plus the Plus Jakarta Sans webfont (loaded via
  `tokens.css`); no build step and no JS dependencies.
