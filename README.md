# Latex-On-HTTP

> Compiles Latex documents through an HTTP API.

# Open Alpha @ latex.ytotech.com

Available on https://latex.ytotech.com as an open-alpha.

This alpha is open to everyone to test the API, collect as much feedbacks as possible and help develop the service. Send your feedbacks to y@yoantournade.com 

## Notice

As noted above, the API is very likely to change along the way. There will be **no special notice** before changes are rolled out.

There is also no guanrantee of availibility; the service can be dropped at any time.

In the future, there are high chances the service will be limited in the open/anonymous usage mode, requiring to be authenticated to compile several times (and eventually requiring credits).

## Available packages and fonts

Use https://latex.ytotech.com/packages and https://latex.ytotech.com/fonts to see currently available packages and fonts.

You miss something?
Open a PR for [adding font(s)](https://github.com/YtoTech/latex-on-http/blob/master/container/tl-distrib-debian.Dockerfile#L34) or [Latex/CTAN packages](https://github.com/YtoTech/latex-on-http/blob/master/container/install_latex_packages.sh#L22)!


## Hello world

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
                "url": "https://www.ytotech.com/static/images/ytotech_logo.png"
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
and the second Latex file as a base64 encoded string (`file` resource mode, which expects the file content as base64).

Also note how the first document is flag with the `main` property and how the dependencies relative paths are specified to reconstruct the file arborescence server-side for the compilation with multiple files to work.

# API

This project is in an experimental phase and the API is *very likely* to change.

# Compiling Latex

### `POST:/builds/sync`

Compile a Latex document, waiting for the end of the build to get back the file.

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
            "url": "https://www.ytotech.com/static/images/ytotech_logo.png"
        },
        {
            "path": "page2.tex",
            "file": "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl"
        }
    ]
}
```

* `compiler` defaults to `pdflatex`. Available compilers: `latex`, `lualatex`, `lualatex`, `xelatex` & `pdflatex`.
* `resources` entries:
    * These are the files uploaded and to be compiled;
    * There must be an entry for the [main Latex document](https://en.wikibooks.org/wiki/LaTeX/Modular_Documents), tagged with the `main: true` value; if there is only one entry, it is considered the main document;
    * Resource entries that are not the main document must be specified a `path`, relative to main document; these files can then been referred in the Latex sources;
    * There are several resource content formats:
        * String format, with `content` (value must be encoded as a valid Json string);
        * Inline file format, with `file` (value must be [base64](https://en.wikipedia.org/wiki/Base64) encoded)
        * URL to a file, with `url` (the resource pointed by the URL will be downloaded and decoded with UTF-8).


> Response

A PDF file if the compilation succeeds, else a Json payload with the error logs.

## Inspecting build environment (fonts, packages)

### `GET:/fonts`

Explore available fonts that can be used directly in Latex compilations.

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

Explore installed Latex packages that can be used in compilations.

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

Get information on a Latex package, including whether it is installed or not.

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

----------------------------------

## Credits

Inspired by:
* [Overleaf](https://www.overleaf.com/) and [Sharelatex](https://fr.sharelatex.com/) for the idea that Latex can be made a web-accessible tool
* ... and for their open-source cloud Latex compiling architectures ([clsi-sharelatex](https://github.com/sharelatex/clsi-sharelatex) and [clsi-overlead](https://github.com/overleaf/clsi))
* [Latex-Online](https://github.com/aslushnikov/latex-online) from aslushnikov for a CLI-oriented online Latex compiler
* mrzool for its [great Latex templates](http://mrzool.cc/writing/typesetting-automation/) and integration with Pandoc
