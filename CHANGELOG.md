# CHANGELOG

## 2026-11-16 (ENDLEAF-R80)

* ENDLEAF-R80-MARGINS: a landscape page uses pinned margins on any paper:
  left and right 20 mm, top (paper edge to the text block top) 20 mm,
  bottom 22 mm, so A4 landscape has a 257 x 168 mm text block.
  `endleaf-page.tex` defines `\EndleafLandL`, `\EndleafLandR`,
  `\EndleafLandT` and `\EndleafLandB`; `endleaf-fit.tex` uses the same
  names (with a fallback of the same numbers), so a named landscape page and
  an auto-turned one get the same text block on the same paper. The sysml
  canvas and plain picture landscape line on A4 grows from about 220 mm to
  257 mm and the landscape height to 168 mm. Portrait and A3 portrait are
  unchanged.
* ENDLEAF-R80-CAPTION: inside a figure or table float, `\elfit@bounded`
  fits a diagram fence plus a caption reserve into the text height (the
  landscape height for a fence turned inside a float). The reserve is
  `\ElfitCaptionHeight` plus `\abovecaptionskip` when that optional hook is
  defined, else three `\normalsize` lines plus `\abovecaptionskip`; outside
  a float it is 0. The height scale never goes below the 7 pt floor. Width
  fit and the `ENDLEAF_SHELLFIT`, `ENDLEAF_SHELLTURN` and `ENDLEAF_SHELLPAGE`
  log lines are unchanged.
* ENDLEAF-R80-TALL-WARN: a fence still taller than that bound at the floor
  is set at the floor and logs `ENDLEAF_SHELLTALL n height avail`; the
  worker reports it as a `layout_too_tall` job warning (packages
  `["diagram"]`, message with the page and the mm over).
  `tests/colophon/test_r80_landscape.py` covers the TeX source and the
  warning.

## 2026-10-29 (ENDLEAF-R75)

* ENDLEAF-R75: the worker image installs circuitikz 1.8.7 (2026/09/12) from
  CTAN into `/usr/local/share/texmf` (TEXMFLOCAL), replacing the 1.6.0 that
  Debian `texlive-pictures` ships. `CIRCUITIKZ_VERSION`, `CIRCUITIKZ_SHA256`
  and `CIRCUITIKZ_URL` are build args; the build fails on a sha256 mismatch,
  when the first `circuitikz.sty` is not the local one, or when
  `\pgfcircversion` is not the pinned version. `packageSetHash` is unchanged.
* `tests/colophon/test_circuitikz_187.py` compiles the 73 path symbols, 109
  aliases and 22 node shapes missing on 1.6.0 (plus spring, damper and
  crossing) and fails on any missing shape or key.
* IEC logic gate marks follow the picture font (10 pt in the circuits
  template) and the TikZ `circuits.logic.IEC` marks are `\scriptstyle`
  (7 pt), so the preamble sets nothing for them.

## 2026-10-29 (ENDLEAF-R74)

* ENDLEAF-R74-SYMBOLS: circuitikz `spring`, `damper`, `crossing` and `xing`
  draw again on the worker. The PID library is loaded after circuitikz in
  `colophon-v1-preamble.tex` and defines styles of the same names, which
  replaced circuitikz's; the preamble now makes circuitikz's definitions
  again after the library. PID symbols keep their numbers.
* ENDLEAF-R74-TEXT: circuitikz's tiny and six-point bold fonts are 7 pt in
  `colophon-v1-preamble.tex` and `endleaf-kinds.tex` (thermistor and varistor
  letters, ecapacitor plus, chip pin numbers).
* ENDLEAF-R74-FIT: `endleaf-fit.tex` scales a plain picture that is wider
  than the portrait line and taller than a landscape text block to the
  portrait line (text at or above 7 pt) instead of turning a blank landscape
  page; logs `ENDLEAF_PICSCALE`. `endleaf-layout.tex` logs `ENDLEAF_PICTURN`
  only for a real turn.
* ENDLEAF-R74-INDENT: a plain picture box starts its paragraph without the
  indent, which had added about 12 pt to a picture that fitted its line.
  `packageSetHash` is unchanged (no new packages).

## 2026-10-22 (ENDLEAF-R66)

* ENDLEAF-R66: a `stocklabel` template. The gate writes the body from
  validated fields (one `\EndleafStockLabel` per label, one label per page,
  the QR as merged module rectangles); `endleaf-label.tex` owns the layout:
  the QR at the left, full printable height, then the name (bold, 16 pt down
  to 9 pt in 0.5 pt steps), one spec line (7 pt; drops package, then current,
  then 6.5 and 6 pt) and `Stock #<id>` (6 pt). Nothing is truncated.
* ENDLEAF-R66-QR (owner 2026-10-22 17:30): the gate sends the smallest QR
  version that holds the payload; the template sets the module to the
  printable height over the symbol's modules, so every symbol spans the full
  printable height. The gate refuses a module under 0.33867 mm.
* ENDLEAF-R66-SIZE: the job takes `labelSize` (`widthMm`, `heightMm`,
  `marginXMm`, `marginYMm`) instead of `pageSize` for this template; the
  template sets `\paperwidth`, `\paperheight`, `\pdfpagewidth` and
  `\pdfpageheight`. `pageSize` and `orientation` are refused on it.
* ENDLEAF-R66-FIELDS: the label fonts are TeX Gyre Heros without the TeX
  ligature mapping (`--`, `---`, quotes print as typed).
* ENDLEAF-R66-FIT: each label line logs `ENDLEAF_LABELFIT`; the sandbox
  sends `labelFit` rows and the distinct missing-glyph count in the
  `X-Endleaf-Layout` map. Sizes and flags only, never label text.
  `packageSetHash` is unchanged (no new packages).

## 2026-10-22 (ENDLEAF-R64-ROWS)

* Every TeX-path template (not only fulldoc) sends its overfull boxes in the
  layout map: `overfullTotal` (never dropped) plus at most 50 rows, largest
  first, `{line, pt, axis, page?, table?}`. hbox and vbox are both listed;
  `page` is the next shipout after the warning, omitted when none follows;
  `table` gives `firstLine`, `n`, per-column `share` and `rules` when the line
  range starts or sits in a tabular/longtable. A body without marks sends a
  map with only these keys. A table wider than 20 columns is sent without
  its `table` field. maxRows 50 is measured: 50 worst-case rows, each with a
  20-column table, encode to 5224 bytes, under half of the 12000-byte map cap;
  past the cap the lists drop and `overfullTotal` stays. Shipout pages are read
  with every box dump masked, so bracketed page text is never a page. Markdown
  jobs (document-shell) still compile inside Pandoc and send none (ENDLEAF-R65,
  parked).

## 2026-10-09 (ENDLEAF-R62)

* ENDLEAF-R62-FONT: a picture-level font size now reaches node text. The
  type stack set `every node/.append style={font=\sffamily}`; `font=`
  replaces the node font, so `\begin{tikzpicture}[font=\large]` set its
  nodes at 10 pt (measured: 9.96 pt high in the PDF, and ENDLEAF_PICFIT
  reported 10). Nodes now take a new `endleaf sans` key that appends
  `\sffamily` to the font in force, so picture-level sizes and families are
  kept and the Endleaf sans still applies. Applies to every template that
  inputs `endleaf-type.tex`. A node's own `font=` still replaces the picture
  font, as in plain TikZ. `packageSetHash` is unchanged (no new packages).

## 2026-10-09 (ENDLEAF-R61)

* ENDLEAF-R61-FIT: `endleaf-layout.tex` logs one `ENDLEAF_PICFIT` line per
  picture (plain TikZ or a sysml canvas): the last layout mark id, the kind,
  the picture's rendered width, the text line it must fit, and the smallest
  text size set in its node text. Only node text counts: a `selectfont` hook
  is gated by `every text node part` begin and end code, because TikZ selects
  10 pt internally many times. Limits: a size switch inside node text (for
  example `{\large A}`) counts the node's starting size, so the minimum errs
  small, never large; math sub- and superscripts are not measured; a picture
  that replaces `every text node part` itself reports no text.
* The `layout_overhang` warning is now one item per picture at least 1 pt
  past the line, with `partId`, `overMm`, `scaleToFit` (line / width, 2
  decimals, rounded down), `minTextPt` (smallest text at that scale, 0.1 pt,
  rounded down; absent when the picture sets no text), `belowTypeFloor`
  (under 7 pt) and `fix`: "scale inside the source to S", or "redraw or
  split; scaling would put text at X pt". The message carries every field, so
  a gate that reads only `code`, `packages` and `message` still shows them.
  At most 10 pictures, then a count. Logs without `ENDLEAF_PICFIT` (other
  templates) keep the R59 aggregate warning.
* The layout map gains optional lists: `fits` [[id, width, line, minSize]],
  `overfull` [[bodyLine, pt]] (Overfull \hbox lines inside the body, at most
  40; body-relative as in ENDLEAF-R58) and `labels` [[label, number, page]]
  from the final aux (at most 400). Over the 12000-byte cap they are dropped
  in the order labels, overfull, fits before the map is. The R60 gate's
  decoder ignores unknown keys, so this worker can roll first.
  `endleaf-fit.tex` stays the pinned vendored copy; `packageSetHash` is
  unchanged.

## 2026-10-09 (ENDLEAF-R60)

* ENDLEAF-R60-LAYOUT: `fulldoc` inputs the new `endleaf-layout.tex`. The
  Endleaf gate puts zero-size marks in the body it compiles
  (`\EndleafMark{id}{s|e|r}` in a paragraph or heading, `\EndleafVMark` at
  a float's edges and around raw parts). At shipout each mark logs its page,
  vertical position and orientation; a picture inside a float logs its
  shipped size; the text block is logged once. The worker turns the final
  pass's lines into a JSON map, deflates and base64url-encodes it (at most
  12000 bytes; larger maps are dropped) and returns it in the
  `X-Endleaf-Layout` response header. No header when the body has no marks.
* The marks typeset nothing: a test shows the same text with and without
  them. Kernel primitives only, so `packageSetHash` is unchanged.
  `endleaf-fit.tex` is not edited (it stays the pinned vendored copy); the
  layout file wraps its picture-closing macros after it is loaded.
* Bodies from a gate with marks start with `\providecommand` fallbacks, so
  they still compile on an older worker (no header then). Roll this worker
  before the gate that reads the header.

## 2026-10-09 (ENDLEAF-R59)

* ENDLEAF-R59-KINDS: `fulldoc` inputs the new `endleaf-kinds.tex`, so
  `tikzcd`, `forest`, `tikztimingtable` and `bytefield` render inside a
  fulldoc figure. The file is the colophon-v1 kind packages less the unsold
  `tikz-3dplot` and `tikz-feynman`; a test keeps the two lists in step.
  `packageSetHash` is unchanged. Cost: about +0.06 s per pass, no new fonts.
* ENDLEAF-R59-TEMPLATES: owned templates `tikzcd`, `forest`, `automata`,
  `mindmap`, `tikztiming` and `bytefield` (the circuits preamble).
* ENDLEAF-R59-FLOAT: a landscape sysml canvas inside a fulldoc figure is a
  page-only float shipped alone on a landscape page. No forced `\newpage` or
  `\clearpage`, so the portrait page before it is filled with the text that
  follows; later figures keep their order.
* ENDLEAF-R59-OVERHANG: `ENDLEAF_OVERHANG` and `ENDLEAF_WIDE_PICTURE` log
  lines become a `layout_overhang` entry in the job record `warnings`.
* ENDLEAF-R59-TYPE: bytefield bit numbers are `\scriptsize` sans (7 pt, was
  5 pt); pgfplots tick labels use the Endleaf sans (TeX Gyre Heros) digits.
* Roll this worker before the gate that sends the six kinds as templates.

## 2026-10-09 (ENDLEAF-R58)

* ENDLEAF-R58-BODYLINE: compose records the job.tex line where the caller's
  body starts. A TeX error inside the body is reported as `diagnostic.file`
  `"body"` with `line` counted from the body's first line (1-based). An error
  in the worker preamble, after the body or in another file keeps its file
  (`job.tex`, …) and line unchanged. The Endleaf gate maps body lines of a
  compiled Document to its parts; roll this worker before that gate.

## 2026-10-08 (ENDLEAF-R57)

The requirements live in the Endleaf model
(`sysml-models/models/requirements-endleaf.sysml`). This entry records
the worker side before the code that satisfies it.

* ENDLEAF-R57-PASSES: the second identical XeLaTeX pass also runs when
  a TeX PDF body uses `\eqref`, `\cite` or `\tableofcontents`, not
  only `\ref` / `\pageref`. Live 2026-10-08 a fulldoc body with
  `\cite` and `thebibliography` but no `\ref` rendered `[?]`; the same
  body with one `\ref` rendered `[1]`. No bibliography program runs.
* ENDLEAF-R57-WARN: after a successful TeX PDF render the sandbox counts
  Overfull and Underfull boxes, undefined references and undefined
  citations in the final log. The job record carries `texWarnings`
  (`overfull`, `underfull`, `undefinedRef`, `undefinedCite`) only when
  one is above zero. Markdown jobs (Pandoc) carry none.
* ENDLEAF-R57-CAUSE: a render error's first diagnostic gets
  `diagnostic.cause`, one of eleven codes, from a pattern table adapted
  in our own words from the awesome-latex-skills error catalog (MIT;
  see NOTICE). No match leaves `cause` unset.
* ENDLEAF-R57-CITE: the fulldoc example and kind fixture cite one
  `thebibliography` entry; the fixture asserts `[1]` and no `[?]`.
* No new TeX package. `packageSetHash` is unchanged.

## 2026-10-08 (ENDLEAF-R56)

* ENDLEAF-R56-WIRE (Endleaf requirements): every field the HTTP worker
  parses reaches the sandbox parse. Live 2026-10-08 the runner rebuilt
  the sandbox stdin from body, templateId, outputFormat and lane only,
  so `pageSize` never reached the render and every PDF was A4. The
  runner now sends `colophon.enums.job_payload(job)`, the inverse of
  `parse_job`.
* ENDLEAF-R56-SIZES: `pageSize` takes `a3` as well as `a4` (default)
  and `letter`; optional `orientation` is `portrait` or `landscape`.
  Bad values are one line: `pageSize must be a4, letter or a3` /
  `orientation must be portrait or landscape`. New kernel file
  `colophon-v1/endleaf-page.tex` runs at the end of the article class
  (`\AddToHook{class/article/after}`), resizes A3 from the a4paper
  layout, turns the page for landscape (paper and PDF page swap), keeps
  the class margins and gives the extra paper to the text block.
  Omitted orientation leaves A4 and Letter portrait as the class set
  them. Not a package; `packageSetHash` is unchanged.
* ENDLEAF-R56-FIT: `endleaf-fit.tex` names the size in its errors and,
  when the job names an orientation, keeps that page and refuses a
  canvas that does not fit instead of turning it. Omitted orientation
  keeps the sysml auto-landscape rule on every size.
* ENDLEAF-R56-CONTRACT: `tests/colophon/fixtures/contract/worker-job-contract.json`
  is byte-identical to the Endleaf gate fixture. `tests/colophon/test_job_wire.py`
  posts it to `POST /v1/jobs` through the real runner and checks the
  PDF MediaBox for all six size and orientation pairs.

## 2026-10-08

* Optional job field `pageSize`: `a4` (default) or `letter`. Owned
  preambles take `__PAPER__` (`a4paper` / `letterpaper`). Lane Pandoc
  templates take `$papersize$paper`, and the PDF plan always passes
  `-V papersize=…`. The shared engine preamble sets kernel
  `\pdfpagewidth` / `\pdfpageheight` from the class paper so XeLaTeX
  does not keep the driver default (often letter). Any other value is
  `rejectInvalidInput` field `pageSize` with a one-line message.
  Shell-escape stays off. `packageSetHash` is unchanged.
* `sysml-tikz.sty` v0.6 (Endleaf ENDLEAF-R55, SYSMLTIKZ-R33). A sheet
  whose text overlaps is a render error, not an ok PDF. At the end of
  each picture the style checks every stereotype, name, type, port
  label and edge label against other text (1 mm gutter on one row),
  port squares (1 pt clear), part outlines, other connectors and end
  heads, and every connector against port squares. The first hit is
  one line, `Package sysml-tikz Error: layout_overlap: <a> on <b>
  (+N more)` or `line_into_port: line <name> into port <id>`. Empty
  `lx` and `ly` on `\sysmlport` put the label outside the part beside
  the square (SYSMLTIKZ-R33-OUTSIDE). Regression fixtures
  `tests/colophon/fixtures/sysml/ei-source-*.tex`. Fonts, package set,
  `packageSetHash`, quotas and page geometry are unchanged. sha256
  `84b3ad643c5ec84c0bb8af57f1043abbc1793129d0ecf12bd66517254bf09d56`.
* `colophon/diagnostics.py` joins a TeX error line that the log broke
  at 79 characters, so `errorText` carries the whole one-line message.

## 2026-10-04

* Vendored Endleaf SYSMLTIKZ-R32-CLEAR into `sysml-tikz.sty` (PR 58,
  `cursor/flow-item-port-clear-b4ef`). The style now measures the same
  `sysml edge label` node the mark will use. A 0 pt `\setbox0` under
  `\pgfinterruptpicture` (TikZ nullfont) no longer accepts a seat and
  then glues the real word to a port. If that box cannot sit clear of
  both ports, the job is
  `Package sysml-tikz Error: flow item cannot sit clear of both ports`
  and the mark is not drawn. No warning, no shrink, no glue. Connection
  names stay off the edge. A gap that does clear both ports still
  compiles, including the vehicle C2 `transferredTorque` case and
  `at=mid`. Fonts, package set, `packageSetHash`, quotas,
  landscape-at-declared-size, the 7 pt floor, upright item text, and
  the human header are unchanged. sha256
  `ee94b2a9cb136c04d2f7549316d3e74cadc59e61f227f4a48efef2630bd8c4bf`.

## 2026-10-03

* sysml-tikz item text stays page-upright when a connector is written
  right to left. `decorations.markings` rotate the canvas to the
  segment, and `endleaf-fit` sets `transform shape`, so the node was
  rotating with the path. The mark stays; the rotation is dropped.
  The printed `sysmlfigure` header is a title and optional revision
  id. view, overrides, depth, and body size stay worker keys and are
  not printed. Fit still uses the declared type size. Fonts, package
  set, `packageSetHash`, quotas, and ENDLEAF-R49 page-size rules are
  unchanged.
* ENDLEAF-R49. Vendored Endleaf `prototypes/endleaf-fit/endleaf-fit.tex`
  and `prototypes/endleaf-fit/sysml-preamble.tex` at
  `59178c12e760140162f9fe18021766ee7628f73f` (PR 55) to
  `colophon/share/tex/latex/colophon-v1/endleaf-fit.tex` and
  `colophon/share/templates/owned/sysml/preamble.tex`. A sysml canvas
  wider than the portrait A4 text line at the declared body size is
  landscape A4, and type stays at that size. 7 pt is a floor, not a
  fit target. The millimetre unit is not shrunk. If the canvas still
  will not fit, the render is an error. The sysml preamble does not
  wrap the body in a portrait minipage (that group restored portrait
  page size at shipout). Neither file is a package, so
  `packageSetHash` stays
  `73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98`.

## 2026-10-01

* Shared type stack `endleaf-type.tex`: TeX Gyre Pagella body, Heros
  diagram labels, Cursor mono. Owned preambles, lane Pandoc wrappers, and
  the fenced-TikZ lock input it after fontspec/xeCJK. `fulldoc` and
  `document-shell` (and the lane wrappers) are explicit 10 pt. The image
  installs Debian `tex-gyre`. This input is not a package, so
  `packageSetHash` stays
  `73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98`.
  `pdffonts` on a live PDF should show Pagella/Heros/Cursor, not CMR for
  body type.

## 2026-09-29

* A TeX PDF body that contains `\ref` or `\pageref` runs XeLaTeX twice.
  The second pass reads `job.aux` beside `job.tex`, so those references
  resolve. Bodies without those commands stay one pass. Shell-escape
  stays off, and `packageSetHash` is unchanged.
* `templateId` `fulldoc` is a PDF-only TeX kind. The preamble is A4
  `article` with fontspec, xeCJK, Noto Sans CJK TC, TikZ, `sysml-tikz`,
  CircuiTikZ, siunitx, pgfplots (`compat=1.18`), chemfig, mhchem,
  pgfgantt, tikz-dimline, tikzscale, and `endleaf-floorplan`. It does
  not load geometry, needspace, float, caption, or the unsold packages
  in `colophon-v1-preamble.tex`. HTML and DOCX are `outputFormat`.
  A compile of more than 16 pages is `failCapHit` with
  `fulldoc exceeds maxPages 16 (got N pages)`. `GET /version` limits
  are unchanged.
* `sysml` and `fulldoc` keep a `sysmlfigure` header and its canvas in
  one minipage. Inside a fulldoc `figure` or `table`, the picture and
  the caption share a minipage. The float macros are wrapped, so the
  body is not collected. A `sysmlcanvas` is scaled uniformly, text
  included, down to 7 pt. Only a remainder past that floor shrinks the
  coordinate unit, and the same fit is applied to the height so the
  header and the canvas stay inside `\textheight`. The caption reports
  the fitted type size. A plain `tikzpicture` or `circuitikz` that is
  wider than the line logs `ENDLEAF_WIDE_PICTURE` and is not scaled.
  `\@fpsep` is 12 pt with no fil, so float pages stack at the top.
  `\resizebox` is not used.
* Every PDF sets the document-info Creator, Producer and Keywords
  with `\special{pdf:docinfo...}` (ENDLEAF-R40-CREDIT). Subject is
  left unset unless the caller sets it. The credit is not page text
  and does not load hyperref. `packageSetHash` stays
  `73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98`.
* `sysml-tikz.sty` is re-vendored from Endleaf
  `prototypes/sysml-layout/sysml-tikz.sty` at
  `65baacff166cdee7b3393bc27a01e5d80ad1262f`
  (sha256 `aa1d42ababc4d4e813f1943fa89a11fee021ae0a491715a2d5b6933a17315952`).
  Mid-path marks use arc length. `packageSetHash` stays
  `73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98`.

## 2026-09-28

* `sysml-tikz.sty` is re-vendored from Endleaf
  `prototypes/sysml-layout/sysml-tikz.sty` at
  `37c4e28fe1150f6963526b3d54bc30ed5af9281e`
  (sha256 `da80c8d3ba9efcfac0fb4bba9c4e87caf885deb50fc8061842f307943cc337e0`).
  `\sysmlconnection[from=..., to=...]` is a plain solid line.
  `\sysmlflow` draws a filled triangle. `\sysmlbinding` draws a solid
  line with `=` and no arrowhead. `packageSetHash` stays
  `73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98`.

* `sysml-tikz.sty` is installed in the image texmf tree. Documents load
  it with `\usepackage{sysml-tikz}`. The file is Endleaf
  `prototypes/sysml-layout/sysml-tikz.sty` at
  `06149a8dbd99e92a66cc380255717f1b3f2ded5f`
  (sha256 `a0978d8dd9cb711356c2f9c19992af8a05581722ae179ef5881272fb32f726d9`).
  It requires only `tikz`. `\sysmlport` records direction by id.
  `\sysmlconnection[from=..., to=...]` draws an open arrowhead only for
  out-to-in, on the in-port end. A two-argument call has no arrowhead.
  The shared preamble and the document-shell allowlist include
  `sysml-tikz`. `templateId` `sysml` is the TeX kind. `packageSetHash`
  is `73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98`
  (package names only, so this re-vendor does not change it).

## 2026-09-27-endleaf

* The product is Endleaf by Inkmirage (formerly Colophon). This repository
  stays `chouswei/latex-on-http`. The Python module stays `colophon`
  (`python -m colophon`). `\input{colophon-v1-preamble.tex}` is unchanged.
* `colophon-floorplan` is now `endleaf-floorplan`. `packageSetHash` is
  `f2946ed8f9682cc0e0dffa468d29fdc25ae2feb85e7d9d1291414dc1cf2a310d`
  (was `c6676798e00bd9655bf3391f0c0f21dec100684d5c6783a6e0b2c3f8ae078c01`).
  The hash changed because that one package name changed. No package was
  added or removed. `openin_any` stays `p`.
* Settings are `ENDLEAF_*`. `COLOPHON_*` is still read when the new name is
  unset, and each use logs a deprecation line.
* Floor-plan internals are `\elfloorplan@…`. LaTeX rejects a `\newcommand`
  name that starts with `\end`, so `\endleaffloorplan@` could not load.
  The package and file stay `endleaf-floorplan`, and `packageSetHash`
  stays `f2946ed8f9682cc0e0dffa468d29fdc25ae2feb85e7d9d1291414dc1cf2a310d`.

## 2026-09-26

* TeX is started on a relative name from the job directory. `openin_any`
  and `openout_any` stay `p`. The image CJK check compiles `cjk.tex` from
  `/tmp`, not `/tmp/cjk.tex`. Pandoc's absolute `input.tex` is rewritten
  to that basename by `xelatex-nonescape`. Fenced TikZ compiles
  `tikz-image.tex` in its temp directory. Owned templates are read by
  kpathsea name.
* Fork behaviour: Endleaf by Inkmirage render worker. Jobs run in throwaway rootless
  Podman sandboxes. The listener binds only to one address inside
  `ENDLEAF_BIND_ALLOWED_CIDR`, and refuses a public (`is_global`) address.
  Host-side LaTeX is disabled. See NOTICE.
* `GET /version` returns the git commit or tag baked at build time, plus
  `packageSet` and `packageSetHash` from the package list written at image
  build.
* Floor-plan TikZ styles and the listed tlmgr packages are in the image.
  Shell-escape, `\write18`, minted, TikZ `external`, Asymptote, gnuplot,
  epstopdf, the `svg` package, automatic tikz-feynman layout, and fenced
  Mermaid or D2 are refused before compilation. There is no Asymptote,
  Mermaid, D2, Chromium, or Node binary.
* `colophon-v1-preamble.tex` is the shared engine preamble for the TeX
  wrapper, the Pandoc template, and TikZ fences. Room area comes from the
  corner numbers. Dimension labels do not change under `scale=`.
* A job result carries a result class, wall time, cgroup `memory.peak` and
  `pids.peak`, and on a render error the first diagnostic. `memory.mode`
  is `cgroup` or `rlimit` when the sandbox reports it.
* Each job sets an `RLIMIT_AS` ceiling (`ENDLEAF_RLIMIT_AS_BYTES`,
  default `2147483648:2147483648`). Podman 4.4 and newer get
  `--ulimit as=<soft>:<hard>`. Podman below 4.4, including rootless 4.3.1,
  rejects that flag. The worker then passes `--hooks-dir` and annotation
  `io.endleaf.rlimit.as`, and a precreate hook writes OCI `RLIMIT_AS` for
  crun. `/usr/bin/podman` is not replaced. `--memory` and `--memory-swap` are
  passed only when the memory controller is present. Preflight requires
  `cpu` and `pids`; a missing memory controller is a warning and the job
  uses rlimit mode. A missing `cpu` controller refuses startup. An
  allocation failure (`not enough memory`, `memory exhausted`,
  `Cannot allocate memory`, xdvipdfmx `Out of memory`, Pandoc
  `Heap exhausted`) is `failCapHit`, the same outcome as an early SIGKILL.
  `RLIMIT_AS` is per process, so the worst case is 256 × 2 GiB; one job
  at a time, few TeX processes, and the MemAvailable shed bound it.
  Other caps are unchanged (60 s, 20 MiB output, 256 pids, 512 MiB tmpfs,
  no network, shell-escape off, load shed at loadavg 3 or MemAvailable
  4096 MiB). The default ceiling fits the measured XeLaTeX and LuaLaTeX
  jobs. A wall clock at or after 60 s is `failTimeout` for every exit
  code, including Podman 4.3's timeout exit 255. An earlier 255 stays a
  render error.
* `GET /v1/host-load` is the token-gated load report. JSON keys are
  `loadAvg1m`, `memAvailableMiB`, `busy`, `stale`, `intervalSec`,
  `readable`, and `reportedAt` (UTC, ISO-8601 with a `+00:00` offset).
  `busy` means a job holds the worker, not that the load average is high.
  `stale: true` is a shed. `readable: false` is HTTP 503. There is no
  `/load` path. `POST /v1/jobs/abort` kills the running container.
* Fenced TikZ diagrams load fontspec and xeCJK with Noto Sans CJK TC, the
  same fonts as the document path, so zh-TW labels in a fence are in the
  PDF image used for PDF, HTML, and DOCX. `\input`, `\include`, and
  `\openin` of an absolute path or `..` are `rejectInvalidInput` field
  `openin`. The image sets `openin_any = p` and `openout_any = p`.
  Runaway loops stay on the 60 s wall cap (`failTimeout`). More than five
  TikZ fences is field `fences`. `GET /version` publishes `limits`
  (`cpu`, `memMiB`, `wallSec`, `outputMiB`, `pidsMax`, `tmpfsMiB`,
  `inputMiB`, `maxFencesPerJob`, `retryAfterSec`). Inline siunitx and
  mhchem still return `warnings` on `X-Endleaf-Job`: objects with
  `code` `notationPdfOnly`, `packages`, and `message`. P&ID `pos` sets
  both TikZ's path time and `\flowpos`. Floor-plan lengths use the
  coordinate numbers, so a 3 m wall reads 3.00 m. Scale bar and north
  arrow are pics as well as styles. Owned examples match the playbook
  review replacements, including a Gantt chart with no `\\` after the
  last bar.
* ENDLEAF-R27. A job sends `templateId` and `body`. The worker owns
  the preamble and still refuses a caller `\documentclass` or raw
  preamble. An unknown `templateId` is `rejectInvalidInput` field
  `templateId`. The engine is XeLaTeX.
  `compiler` other than `xelatex`, and `\directlua`, are refused.
  An output over 20 MiB is `failCapHit`. The cap probe is 3000
  uncompressed pages (`dvipdfmx:config z 0`).
* Rootless storage on the Pi must be `driver=overlay` with
  `mount_program=fuse-overlayfs`. The vfs default used about 57 GB.
* Endleaf v1 renders LaTeX kinds only. Chromium, puppeteer, mermaid-cli
  (`mmdc`), d2, and their pandoc-ext/diagram engines are not in the worker.
  A Mermaid or D2 fence is `rejectInvalidInput`. Those kind fixtures are
  gone, so they no longer emit job meters. The TikZ engine stays for
  P&ID, circuits, plots, chemistry, Gantt, and floor plans.
* The required fixture set is the document shell plus P&ID, circuits,
  plots, chemistry, Gantt, and floor plans. `tikz-cd`, `forest`,
  `automata`, `mindmap`, `tikz-3dplot`, `tikz-feynman`, `tikz-timing`, and
  `bytefield` stay installed with a smoke compile and are not a sold kind.
* HTML and DOCX render fenced diagrams as images. Inline `siunitx` and
  `mhchem` stay PDF-only: those formats keep the source text and return
  a `notationPdfOnly` warning. The result class stays `ok`.
* Image: Debian `texlive-lang-cjk` provides `xeCJK.sty`. Pandoc PDF uses the
  `xelatex` engine name (the no-shell-escape wrapper is first on `PATH`).
  HTML responses embed diagram resources. SVG diagrams in PDF go through
  `rsvg-convert`.

## 2026-04-10-3

* Add CHANGELOG link

## 2026-04-10-2

* Option `options.compiler.force` as default to match old behavior

## 2026-04-10-1

* Add `options.compiler.force` to try to fore compilation (Latexmk `-f` option)
and always return the generated PDF
* Remove `options.bibliography.command`, as Latexmk select automatically either `bibtex` or `biber`
* Add `options.compiler.bibliography` to enable or disable automatic Latexmk bibliography compilation step (default to true)
* Add `commands` property on error output when `options.response.commands` is enabled, which detail of each command runned and its outputs

## 2026-03-17-1

* TeXLive 2026 base image

## 2025-09-23-3

* Bump Python dependencies

## 2025-09-23-2

* Kill all children processes on timeout
* Do not return partial PDF on timeout
* Add option `options.compiler.halt_on_error`
* Add option `options.compiler.silent`

## 2025-09-23-1

* Fix timeout for compilation, with proper error return
* Return compilation log files on failure (default true with option `options.response.log_files_on_failure`)

## 2025-08-06-1

* Switch to TexLive 2025
* Use `latexmk` as default runner instead of `latexrun`
* Add PostgreSQL database in prevision of job status

## 2025-02-13-1

* Fix build with XelaTeX [#43](https://github.com/YtoTech/latex-on-http/issues/43)

## 2024-06-28-2

* Run all commands in same directory to simplify path resolution for `filecontents` and uploaded resources

## 2024-06-28-1

* Set `cwd` for latexrun.py so the `filecontents` directives can work as expected #42

## 2023-06-12-1

* Timeout long LaTeX compilations and prevent zombie processes (the timeout is of 100 seconds for now)

## 2022-12-07-1

* Add clearer input spec (payload) validation

## 2022-08-03-1

* Add ghostscript runtime to the base Docker image

## 2022-07-31-1

* Make sync cache socket more reliable with lazy pirate pattern (prevent dead-lock on server crash)

## 2022-07-30-4

* Fix missing import on `app_cache.py`

## 2022-07-30-1

* Fix caching API

## 2022-05-23-1

* Fix Sentry Flask integration import

## 2022-05-17-3

* Add an environment variable `SENTRY_DSN` for Sentry tracking

## 2022-05-17-2

* Forget Alpine as Context seems [not to run](https://mailman.ntg.nl/pipermail/ntg-context/2021/101979.html) on it, keep to Debian

## 2022-05-17-1

* Use Alpine as default base image

## 2022-05-16-2

* Fix some Hy implementations after `1.0a4` bump 

## 2022-05-16-1

* Update Hy to `1.0a4`, as a consequence LaTeX-on-HTTP now require Python 3.7+
