
# Junk notes / WIP

## TODOs

* Tmp site https://nicedoc.io/ytotech/latex-on-http
* Find/create a std Hy formatter (like black for Python)
    * Uniformize Hy code formatting
    * Follow style guide http://docs.hylang.org/en/stable/style-guide.html
* Build sync/async API
    * Main endpoint: create compilation tasks/builds in async POST:/builds
        * Allows to see progress of a build https://github.com/aslushnikov/latex-online/issues/29#issuecomment-303569813
    * Add an endpoint for waiting on a compilation task/build GET/POST:/builds/wait
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
    * CLI API inspiration
        * https://github.com/aslushnikov/latex-online/blob/master/util/latexonline
        * Uses https://github.com/chalk/chalk for the swag
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
* Compilation options
    * Timeout
* Build output structure
    * Generic "outputFiles"
        * https://github.com/overleaf/clsi#example-response
* Compilation infrastructure
    * Fanout the compiler processes / nodes
* Output format selection
    * Allows to select output other than PDF when available (mapping by compilers / with right parameters)
    * See usage request here https://github.com/aslushnikov/latex-online/issues/20
    * Default to PDF
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
    * CV templating
        * Create from jsonresume https://jsonresume.org/schema/
