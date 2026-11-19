---
permalink: false
---

# Documentation logo

The wordmark and favicon are generated with LaTeX + TikZ, using Computer
Modern (Latin Modern) and the two YtoTech brand colours:

- red `#b14040` for “LaTeX”
- blue `#383866` for “on HTTP”

Sources:

- `latex-on-http.tex` — the compact stacked product wordmark: `LaTeX` over
  `on HTTP`, separated by a red rule, with a smaller indented sans-serif tagline
- `ytotech.tex` — the YtoTech wordmark, recreated from the logo included in
  the repository (`samples/quotes/mrzool-inspired/logo.png`)
- `favicon.tex` — the square favicon

The `\DarkLogo` flag in the wordmark sources switches to the lighter tints
used by the dark theme.

Generate the SVG assets into `docs/site/assets/`:

```bash
./build.sh
```

The output is committed, so the documentation build itself only needs Node.js
and does not require a TeX installation.
