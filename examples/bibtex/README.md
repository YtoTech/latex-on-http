# Bibliography and specifying Bibtex command

By default, the Bibtex command is used to compile bibliography files.

You can override this behaviour by specifying an alternative command for the bibliography, using the `options.bibliography.command` parameter.

Example using `Curl` and the Multipart API:

```bash
#!/bin/bash

curl -v -X POST https://latex.ytotech.com/builds/sync \
    -F "biblatex_sample.tex=@biblatex_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=pdflatex" \
    -F "options.bibliography.command=biber" \
    -o biblatex_sample.pdf
```

See `compile.sh` for a more comprehensible code.

For more on bibliography management in Latex, see [Learn-Latex.org course](https://www.learnlatex.org/en/lesson-12).

## Credits

Samples from the [Learn-Latex.org project](https://github.com/learnlatex/learnlatex.github.io/blob/master/en/lesson-12.md).
