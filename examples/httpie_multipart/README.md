# Compile a project with multiple files using multipart/form-data

These examples use [HTTPie](https://github.com/httpie/httpie), a terminal HTTP client, to

## Multipart base example

We specify the resources to compile by passing a JSON formatted multipart form entry `resources`:

```bash
http --multipart --download --output hello.pdf -v POST https://latex.ytotech.com/builds/sync \
    compiler=pdflatex \
    resources='[{"main": true, "content": "\\documentclass{article}\n \\begin{document}\n Hello World\n \\end{document}"}]'
```

Here this will compile a unique resource, containing an hello world, and tell HTTPie to download the resulting PDF to a file `hello.pdf`.

## Adding local files to payload

Assuming you have a `sample.tex` local file to compile, you can then use:

```bash
http --download --output sample.pdf --multipart -f -v POST https://latex.ytotech.com/builds/sync \
    file1@sample.tex \
    compiler=xelatex \
    resources='[{"main": true, "multipart": "file1"}]'
```

Note that `file1` in `file1@sample.tex` (which tell HTTPie to upload `sample.tex` as a multipart entry named `file1`) match to the `file1` in the resources specification.

Following this example, you can then add as many files as you need to the multipart form, declaring each them in a resource entry to be used for the compilation.
