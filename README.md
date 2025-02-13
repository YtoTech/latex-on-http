# LaTeX-On-HTTP

> Compiles LaTeX documents through an HTTP API.

See [TUG2020 introduction](https://www.youtube.com/watch?v=tGD4upJIUgc) to LaTeX-on-HTTP genesis.

# Live @ latex.ytotech.com

Available on https://latex.ytotech.com as an open beta.

Try the interactive demo: https://latex-http-demo.ytotech.com

# Getting started

## Hello world GET Querystring API (experimental)

You can pass your LaTeX document to compile in a `content` GET parameter:

[https://latex.ytotech.com/builds/sync?content=\documentclass{article} \begin{document} Hello World LaTeX-On-HTTP \end{document}](https://latex.ytotech.com/builds/sync?content=%5Cdocumentclass%7Barticle%7D%20%5Cbegin%7Bdocument%7D%20Hello%20World%20LaTeX-On-HTTP%20%5Cend%7Bdocument%7D)

You can also pass your document by url using `url` parameter:

https://latex.ytotech.com/builds/sync?url=https://raw.githubusercontent.com/YtoTech/latex-on-http/master/examples/templates/moderncv.tex

It is possible to specify the LaTeX compiler with `compiler` parameter:

https://latex.ytotech.com/builds/sync?compiler=xelatex&url=https://raw.githubusercontent.com/YtoTech/latex-on-http/master/examples/gitlab_ci/Dossier_Eleve.tex

When you need to add annex resources (for eg. other LaTeX files or image files), you can specify them using `resource-path[]`, `resource-value[]` and `resource-type[]` parameters:


[https://latex.ytotech.com/builds/sync?content=content=\documentclass{article} \usepackage{graphicx} \begin{document} Hello World \includegraphics[height%3D2cm%2Cwidth%3D7cm%2Ckeepaspectratio%3Dtrue]{logo.png} \end{document}&resource-type[]=url&resource-path[]=logo.png&resource-value[]=https://www.ytotech.com/images/ytotech_logo.png](https://latex.ytotech.com/builds/sync?content=%5Cdocumentclass%7Barticle%7D%20%5Cusepackage%7Bgraphicx%7D%20%5Cbegin%7Bdocument%7D%20Hello%20World%20%5Cincludegraphics%5Bheight%3D2cm%2Cwidth%3D7cm%2Ckeepaspectratio%3Dtrue%5D%7Blogo.png%7D%20%5Cend%7Bdocument%7D&resource-type[]=url&resource-path[]=logo.png&resource-value[]=https://www.ytotech.com/images/ytotech_logo.png)


## Hello world POST JSON API

With Curl:

```sh
curl -v -X POST https://latex.ytotech.com/builds/sync \
    -H "Content-Type:application/json" \
    -d '{
        "compiler": "lualatex",
        "resources": [
            {
                "main": true,
                "content": "\\documentclass{article}\n \\usepackage{graphicx}\n  \\begin{document}\n Hello World\\\\\n \\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\n \\include{page2}\n \\end{document}"
            },
            {
                "path": "logo.png",
                "url": "https://www.ytotech.com/images/ytotech_logo.png"
            },
            {
                "path": "page2.tex",
                "file": "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl"
            }
        ]
    }' \
    > hello_world.pdf
```

In this example the main document is passed as a plain-string (Json-encoded `content` resource mode), the logo image file with an url (`url` resource mode)
and the second LaTeX file as a base64 encoded string (`file` resource mode, which expects the file content as base64).

Also note how the first document is flag with the `main` property and how the dependencies relative paths are specified to reconstruct the file arborescence server-side for the compilation with multiple files to work.

## Hello world Multipart API

With [HTTPie](https://github.com/jakubroztocil/httpie):

```sh
http --multipart --download --output hello.pdf -v POST https://latex.ytotech.com/builds/sync \
    compiler=pdflatex \
    resources='[{"main": true, "content": "\\documentclass{article}\n \\begin{document}\n Hello World\n \\end{document}"}]'
```

This multi-part API allows to send resource files to be compiled in a multipart HTTP query.

[See more](https://github.com/YtoTech/latex-on-http/tree/master/examples/httpie_multipart).

## Available packages and fonts

Use https://latex.ytotech.com/packages and https://latex.ytotech.com/fonts to see currently available packages and fonts.

You miss something?
Open a PR for [adding font(s)](https://github.com/YtoTech/latex-on-http/blob/master/container/tl-distrib-debian.Dockerfile#L34) or [Latex/CTAN packages](https://github.com/YtoTech/latex-on-http/blob/master/container/install_latex_packages.sh#L22)!

# Using CLI

## lol

[kpym](https://github.com/kpym) has created a CLI tool named [lol](https://github.com/kpym/lol) for using LaTeX-on-HTTP:

```sh
lol -s ytotech -c xelatex main.tex imgs/*.png
```

### Installing `lol`

To install it, download the [latest release](https://github.com/kpym/lol/releases) for your platform and add it to your PATH.

For eg. on most Linux distributions this should work (considering `$HOME/.local/bin` is in your PATH):

```sh
wget https://github.com/kpym/lol/releases/download/v0.1.3/lol_0.1.3_Linux_64bit.tar.gz
tar -xf lol_0.1.3_Linux_64bit.tar.gz
chmod +x ./lol
mv ./lol ~/.local/bin
lol -h
```

# API

This project is in an experimental phase and the API is *very likely* to change.

# Compiling LaTeX

### `POST:/builds/sync`

Compile a LaTeX document, waiting for the end of the build to get back the file.

>  Request

`POST:/builds/sync` 

Payload (json)
```json
{
    "compiler": "lualatex",
    "resources": [
        {
            "main": true,
            "content": "\\documentclass{article}\n \\usepackage{graphicx}\n  \\begin{document}\n Hello World\\\\\n \\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\n \\include{page2}\n \\end{document}"
        },
        {
            "path": "logo.png",
            "url": "https://www.ytotech.com/images/ytotech_logo.png"
        },
        {
            "path": "page2.tex",
            "file": "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl"
        }
    ]
}
```

* `compiler` defaults to `pdflatex`. Available compilers: `pdflatex`, `xelatex`, `lualatex`, `platex`, `uplatex` and `context`.
* `resources` entries:
    * These are the files uploaded and to be compiled;
    * There must be an entry for the [main LaTeX document](https://en.wikibooks.org/wiki/LaTeX/Modular_Documents), tagged with the `main: true` value; if there is only one entry, it is considered the main document;
    * Resource entries that are not the main document must be specified a `path`, relative to main document; these files can then been referred in the LaTeX sources;
    * There are several resource content formats:
        * String format, with `content` (value must be encoded as a valid Json string);
        * Inline file format, with `file` (value must be [base64](https://en.wikipedia.org/wiki/Base64) encoded)
        * URL to a file, with `url` (the resource pointed by the URL will be downloaded and decoded with UTF-8).
* `options` properties:
    * `options.bibliography.command` defaults to `bibtex`. Available bibliography commands: `bibtex` and `biber`.


> Response

A PDF file if the compilation succeeds, else a Json payload with the error logs.

## Inspecting build environment (texlive, fonts, packages)

### `GET:/texlive/information`

See information on TeXLive installation used in LaTeX compilations.

>  Request

`GET:/texlive/information`


>  Response

A Json payload with a TeXLive installation specification.

Sample
```json
{
  "texlive": {
    "installation_path": "/usr/local/texlive", 
    "modules": [
      {
        "name": "TLConfig", 
        "value": "52745"
      }, 
      ["..."]
    ], 
    "version": "2019"
  }, 
  "tlmgr": {
    "revision": "52931", 
    "revision_date": "2019-11-27 00:04:18 +0100"
  }
}
```

### `GET:/fonts`

Explore available fonts that can be used directly in LaTeX compilations.

>  Request

`GET:/fonts`

>  Response

A Json payload with a list of fonts.

Sample
```json
{
  "fonts": [
    {
      "family": "Courier New",
      "name": "Courier New",
      "styles": [
        "Regular"
      ]
    },
    ["..."]
}
```

### `GET:/packages`

Explore installed LaTeX packages that can be used in compilations.

>  Request

`GET:/packages`

>  Response

A Json payload with a list of packages.

Sample
```json
{
  "packages": [
    {
      "installed": true, 
      "name": "12many", 
      "shortdesc": "Generalising mathematical index sets", 
      "url_ctan": "https://ctan.org/pkg/12many", 
      "url_info": "/packages/12many"
    }, 
    ["..."]
}
```

### `GET:/packages/<packgeName>`

Get information on a LaTeX package, including whether it is installed or not.

>  Request

`GET:/packages/<packageName>`

>  Response

A Json payload with information on the package.

Sample for `/packages/12many`
```json
{
  "package": {
    "cat-date": [
      "2016-06-24T19:18:15+02:00"
    ],
    "cat-license": "lppl",
    "cat-topics": [
      "maths"
    ],
    "cat-version": "0.3",
    "category": "Package",
    "collection": "collection-mathscience",
    "installed": true,
    "longdesc": "In the discrete branches of mathematics and the computer sciences, it will only take some seconds before you're faced with a set like {1,...,m}. Some people write $1\\ldotp\\ldotp m$, others $\\{j:1\\leq j\\leq m\\}$, and the journal you're submitting to might want something else entirely. The 12many package provides an interface that makes changing from one to another a one-line change.",
    "package": "12many",
    "relocatable": false,
    "revision": "15878",
    "shortdesc": "Generalising mathematical index sets",
    "sizes": {
      "run": "5k"
    },
    "url_ctan": "https://ctan.org/pkg/12many"
  }
}
```

# Docker

## Images

Prebuilt Docker images exist to run the service on your own:
* The Python+TexLive near complete LaTeX-on-HTTP image: [yoant/latexonhttp-python](https://hub.docker.com/r/yoant/latexonhttp-python)
* The base TexLive image: [yoant/docker-texlive](https://hub.docker.com/r/yoant/docker-texlive)

## Run the service

You can use the default [`docker-compose.yml`](https://github.com/YtoTech/latex-on-http/blob/master/docker-compose.yml):

```sh
docker-compose up
```

The service will be available on http://localhost:2345.


----------------------------------

## Credits

Inspired by:
* [Overleaf](https://www.overleaf.com/) and [Sharelatex](https://fr.sharelatex.com/) for the idea that LaTeX can be made a web-accessible tool
* ... and for their open-source cloud LaTeX compiling architectures ([clsi-sharelatex](https://github.com/sharelatex/clsi-sharelatex) and [clsi-overlead](https://github.com/overleaf/clsi))
* [Latex-Online](https://github.com/aslushnikov/latex-online) from aslushnikov for a CLI-oriented online LaTeX compiler
* mrzool for its [great LaTeX templates](http://mrzool.cc/writing/typesetting-automation/) and integration with Pandoc
