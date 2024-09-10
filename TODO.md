
# Junk notes / WIP

## TODOs

* Isolation / security for compilation jobs/runs
    * Write a test that breaks isolation (eg indue fs access)
        * Needs to enable --shell-escape?
    * Docker
        * Siblings for each run https://github.com/overleaf/clsi
    * firejail
        * https://firejail.wordpress.com/
        * https://firejail.wordpress.com/documentation-2/basic-usage/
        * https://firejail.wordpress.com/documentation-2/building-custom-profiles/
        * https://firejail.wordpress.com/documentation-2/firefox-guide/
        * https://github.com/netblue30/firejail/issues/1956
        * https://github.com/netblue30/firejail/issues/1210
        * https://github.com/netblue30/firejail/blob/master/etc/profile-a-l/latex-common.profile
    * AppArmor
        * https://gitlab.com/apparmor/apparmor/-/wikis/Profiling_with_tools
        * https://docs.docker.com/engine/security/apparmor/#nginx-example-profile
        * https://github.com/phalaaxx/aaprofiles/blob/master/opt.telegram.Telegram
        * https://tbhaxor.com/writing-apparmor-profile-from-scratch/
    * seccomp?
        * See overleaf/clsi Seccomp profile
    * Systemd unit
        * https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Sandboxing
        * https://gist.github.com/ageis/f5595e59b1cddb1513d1b425a323db04
        * See ReadOnlyPaths
        * Sample: sudo mv borgmatic.service borgmatic.timer /etc/systemd/system/
        * One shot unit template
            * https://www.baeldung.com/linux/systemd-multiple-parameters
            * https://superuser.com/questions/728951/systemd-giving-my-service-multiple-arguments
* Introspection
    * Add deeper Latex introspection
    * Compilation options introspection
        * Latex compiler, with for each tree of available options
        * Bibliography / bibtex/biblatex, etc.
* Font catalog:
    * Also list fonts from Latex Font catalogue? (for use with pdflatex)
        * https://tug.org/FontCatalogue/
    * Tell font types: T1, OpenType, TrueType, etc.
    * Add usage instructions for each? (in the generated doc?)
    * TODO Dynamically pull fonts from https://fonts.google.com/?
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
    * Add Tectonic engine
        * https://github.com/tectonic-typesetting/tectonic
        * https://tectonic-typesetting.github.io/en-US/install.html
        * https://tex.stackexchange.com/questions/372408/what-use-is-tectonic
    * Add package documentation / introspection
        * cf http://texdoc.net/
* Upgrade filesystem layer
    * work with tar, git, etc.
        * allows to extract a git hierarchy from git/GitHub/GitLab links
            * https://github.com/posquit0/Awesome-CV/blob/master/examples/resume.tex
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
* "Registered" (user) cache
    * for registered (and permitted) users, create endpoints to upload cached resources
        * they could then be referenced by their hash in resources
        * or put in a dedicated "shared" directory accessible from compilation?
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
* Allows to choose the LaTex compiler (pdflatex, lualatex, xetex)
    * Support more compilers?
        * https://github.com/thomasWeise/docker-texlive#31-compiler-scripts
    * Support Arara https://gitlab.com/islandoftex/arara
        * Also:
        * https://framagit.org/spalax/spix
        * https://github.com/wtsnjp/llmk
        * https://github.com/petrhosek/rubber
        * https://github.com/aclements/latexrun (explicit use)
        * & all https://www.ctan.org/topic/compilation
    * Allows non-pdf output (DVI, etc.).
* Add SILE support
    * https://github.com/sile-typesetter/sile
* Compilation options
    * Timeout
    * Shell escape mode
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
* Combined Markdown/Yaml document creation
    * See https://github.com/Wandmalfarbe/pandoc-latex-template
    * Allows to takes pandoc templates
* Find a dedicated domain-name
    * Put API under api.domain.com, doc developer.domain.com and keep domain.com for home
    * Create a landing page with rationale (simple, directly let play with the toy)
    * https://fonts.google.com/specimen/Droid+Serif
        * Better --> https://github.com/DecliningLotus/fontsource
    * https://v4-alpha.getbootstrap.com/
    * Add usage examples with wget, Python (requests), Javascript, Ruby, PHP.
        * Add click-and-see example on the browser, with code snippet
        * Like https://stripe.com/docs/api
        * TODO Samples for CV, letter, invoice, etc.
    * https://github.com/NebulousLabs/Sia/blob/master/doc/whitepaper.tex
    * Add HTML form to upload a file to compile (with the other project files?)
        * Example of multipart API
            * Bit like https://www.overleaf.com/devs
    * Tech-API oriented landing page (inspiration https://fixer.io/)
* Fire Latex
    * Templates layer
    * Automate invoicing
        * https://help.shopify.com/manual/apps/apps-by-shopify/order-printer
    * CV templating
        * Create from jsonresume https://jsonresume.org/schema/
