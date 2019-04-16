# Latex-On-HTTP

> Compiles Latex documents through an HTTP API.

# API

This project is in an experimental phase and the API is *very* likely to change.

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
    ...
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
    ...
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

# Open Alpha @ latex.ytotech.com

Available on https://latex.ytotech.com as an open-alpha, with no guarantee of service.

This alpha is open to everyone to test the API, collect as much feedbacks as possible and help develop the service. Send your feedbacks to yoan@ytotech 

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

```
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

----------------------------------

# Junk notes / WIP

## TODOs

* Document the Rest API
* Build sync/async API
    * Main endpoint: create compilation tasks/builds in async POST:/builds
    * Add an  emdpoint for waiting on a compilation task/build GET/POST:/builds/wait
        * Add a parameter to the main endpoint to redirect? (to /wait)
        * Or create a specialized endpoint for creating and waiing POST:/builds/sync
    * Add other notification mechanism
        * Webhooks: a POST parameter to the build with an URL to callback on completion
    * Internally use a custon ZeroMQ-based task/pipeline & sync system
        * So we can easily use another language/env for running builds
        * So we can hook ourselves on the builds (for analytics, cache management, etc.)
* Add usage management
    * put a limit on file uploaded size and number of files
    * create module to trace usage statistics
        * upload volume
        * cached volume (input, output)
        * number of compilation
        * compilation time
        * by IP / by user
        * on a short-live db? (Redis)
    * rate limiting module
        * for IP / users after a certain amount of comsumption
* Latex TexLive management
    * add an endpoint to get info on TexLive distribution used/available
    * make a multi-TexLive version env?
        * letting choose the TexLive distribution as the compiler?
* Latex package dynamic install / on demand
    * Add Tectonic engine https://github.com/tectonic-typesetting/tectonic
* Upgrade filesystem layer
    * work with tar, git, etc.
* Caching layer
    * allocate a file caching space by instance / user ?
    * cache on inputs
        * hash input files
        * follows file inputs distribution
            * uses a memcache / Redis ?
        * dynamically insert / remove from cache following usage?
        * endpoint to discover cache files hashes (so clients can optimize)
    * cache on outputs ?
        * when hash of input hashes match -> same output
* Create client libraries (or samples codes)
    * For the moment in my get paid project
    * So we can manage the sending of files
        * with cache management / optimization -> sending just hash of cache files
    * So we can use it in a terminal like a local Latex installation
    * In:
        * Javascript
            * Node
            * In browser? (rather pointless? Just give a sample code)
        * Python
    * Add usage examples in examples folder
        * Javascript (Browser / Node)
        * Python
        * PHP
        * Ruby
        * Java
        * Go
        * .NET
* Allows to choose the Latex compiler (pdflatex, lualatex, xetex)
    * Support more compilers?
    * https://github.com/thomasWeise/docker-texlive#31-compiler-scripts
* Use Pandoc?
  * http://pandoc.org/MANUAL.html#creating-a-pdf
  * As a preprocessor -> another method
  * https://github.com/jez/pandoc-starter
  * https://github.com/thomasWeise/docker-pandoc
* Find a dedicated domain-name
    * Put API under api.domain.com, doc developer.domain.com and keep domain.com for home
    * Create a landing page with rationale (simple, directly let play with the toy)
    * https://fonts.google.com/specimen/Droid+Serif
    * https://v4-alpha.getbootstrap.com/
    * Add usage examples with wget, Python (requests), Javascript, Ruby, PHP.
        * Add click-and-see example on the browser, with code snippet
        * Like https://stripe.com/docs/api
        * TODO Samples for CV, letter, invoice, etc.
    * https://github.com/NebulousLabs/Sia/blob/master/doc/whitepaper.tex
    * Add HTML form to upload a file to compile (with the other project files?)
    * Tech-API oriented landing page (inspiration https://fixer.io/)
* Fire Latex
    * Templates layer
    * Automate invoicing
        * https://help.shopify.com/manual/apps/apps-by-shopify/order-printer

----------------------------------

## Credits

Inspired by:
* https://www.overleaf.com/
* https://github.com/aslushnikov/latex-online
* https://github.com/sharelatex/clsi-sharelatex
* http://mrzool.cc/writing/typesetting-automation/
