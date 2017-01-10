# Latex-On-Http

> Compiles Latex documents through an HTTP API.

This is an experimental project.

TODO:
* Compile a raw Latex file (as file upload or as json value?)
* Includes files to use (images, fonts) during the Latex file compilation
  * Multi-part upload
    * See http://flask.pocoo.org/docs/0.12/api/#flask.Request.files
  * Create temporary folder with all files
  * Try compiles
  * Then clean the mess
  * Put a limit on file uploaded size and number of files
  * Certainly not secure at all, but who cares?
* Allows to choose the Latex compiler (pdflatex, lualatex, xetex)
* Use Pandoc?
  * http://pandoc.org/MANUAL.html#creating-a-pdf
  * As a preprocessor
* Put live on latex.ytotech.com
  * Create a landing page with rationale
  * https://fonts.google.com/specimen/Droid+Serif
  * https://v4-alpha.getbootstrap.com/
  * Add usage examples with wget, Python (requests), Javascript, Ruby, PHP.
  * Add click-and-see example on the browser, with code snippet
  * Add HTML form to upload a file to compile (with the other project files?)

Inspired by:
* https://www.overleaf.com/
* https://github.com/aslushnikov/latex-online
* https://github.com/sharelatex/clsi-sharelatex
* http://mrzool.cc/writing/typesetting-automation/
