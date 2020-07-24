# mrzool inspired Quote/Proposal template

A quote/proposal template.

Inspired from mrzool Invoice Boilerplate template; source: https://github.com/mrzool/invoice-boilerplate

## Compile (locally) with Pandoc

Update the `details.yml`, then compile both `details.yml` and `template-pandoc.tex` with Pandoc.

To output PDF:
```sh
make output-local-pandoc-pdf
```

To output a TeX file:
```sh
make output-local-pandoc-tex
```

## Compile (locally) with XeLaTex

Compile the `template-raw.tex` with XeLaTex:
```sh
make output-local-xelatex-pdf
```


## Compile with LaTeX-on-HTTP

Compile the `template-raw.tex` with LaTeX-on-HTTP (using Curl):
```sh
make output-cloud-latexonhttp-pdf
```
