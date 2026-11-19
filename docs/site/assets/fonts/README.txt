Latin Modern web fonts
======================

The documentation site uses Latin Modern, the descendant of Knuth's Computer
Modern, so the pages share the typographic voice of the LaTeX ecosystem.

The .woff2 files in this directory were converted from the OpenType fonts
shipped with TeX Live:

  lmroman10-regular.woff2     <- lmroman10-regular.otf
  lmroman10-italic.woff2      <- lmroman10-italic.otf
  lmroman10-bold.woff2        <- lmroman10-bold.otf
  lmroman10-bolditalic.woff2  <- lmroman10-bolditalic.otf
  lmmono10-regular.woff2      <- lmmono10-regular.otf
  lmmono10-italic.woff2       <- lmmono10-italic.otf
  lmmonolt10-bold.woff2       <- lmmonolt10-bold.otf

Conversion command:

  python3 -m fontTools.ttLib.woff2 compress input.otf -o output.woff2

Latin Modern is released under the GUST Font License (GUST-FONT-LICENSE.txt),
which is legally identical to the LaTeX Project Public License v1.3c or later.
