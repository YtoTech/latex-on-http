Documentation web fonts
=======================

The documentation site uses locally-hosted open-source fonts so the pages keep
their voice offline and without third-party requests.

Body text
---------

Computer Modern Unicode Sans Serif (CMU Sans Serif), the OpenType/METATYPE1
revival of Knuth's Computer Modern.

  cmusans10-regular.woff2       <- cmunss.ttf  (CMU Sans Serif Medium)
  cmusans10-oblique.woff2       <- cmunsi.ttf  (CMU Sans Serif Oblique)
  cmusans10-bold.woff2          <- cmunsx.ttf  (CMU Sans Serif Bold)
  cmusans10-boldoblique.woff2   <- cmunso.ttf  (CMU Sans Serif BoldOblique)

Source: https://www.fontsquirrel.com/fonts/computer-modern
License: SIL Open Font License 1.1 (SIL-OPEN-FONT-LICENSE.txt)

Code / monospace
----------------

JetBrains Mono, a modern variable-width monospace typeface designed for code
readability. It contrasts with CMU Sans Serif while remaining clear at small
sizes.

  jetbrainsmono-variable.woff2        <- JetBrainsMono[wght].ttf
  jetbrainsmono-italic-variable.woff2 <- JetBrainsMono-Italic[wght].ttf

Source: https://github.com/JetBrains/JetBrainsMono
License: SIL Open Font License 1.1 (OFL-JetBrainsMono.txt)

Conversion
----------

TrueType fonts were converted to WOFF2 with fontTools:

  python3 -m fontTools.ttLib.woff2 compress input.ttf -o output.woff2
