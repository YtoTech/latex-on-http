# Latex-On-Http

> Compiles Latex documents through an HTTP API.

# API

/compilers or /builds
/fonts
/packages

# Open Alpha @ latex.ytotech.com

Available on https://latex.ytotech.com

TODO PR for addind fonts or Latex/CTAN packages. (link to relevant Docker build files)

----------------------------------

# Junk / notes / WIP

This is an experimental project.


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
        * TODO Samples for CV, letter, invoice, etc.
    * https://github.com/NebulousLabs/Sia/blob/master/doc/whitepaper.tex
    * Add HTML form to upload a file to compile (with the other project files?)
    * Tech-API oriented landing page (inspiration https://fixer.io/)
* Fire Latex
    * Templates layer
    * Automate invoicing
        * https://help.shopify.com/manual/apps/apps-by-shopify/order-printer


Hello World:

`POST /compilers/latex`

```
{
    "resources": [
        {
            "content": "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}"
        }
    ]
}
```

With Curl:

```
curl -v -X POST http://localhost/compilers/latex \
    -H "Content-Type:application/json" \
    -d '{
        "resources": [
            {
                "content": "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}"
            }
        ]
    }' \
    > hello_world.pdf
```

Inspired by:
* https://www.overleaf.com/
* https://github.com/aslushnikov/latex-online
* https://github.com/sharelatex/clsi-sharelatex
* http://mrzool.cc/writing/typesetting-automation/
