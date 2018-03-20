# Latex-On-Http
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FYtoTech%2Flatex-on-http.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2FYtoTech%2Flatex-on-http?ref=badge_shield)


> Compiles Latex documents through an HTTP API.

This is an experimental project.

https://latex.ytotech.com/compilers/latex

Run tests:
```
make install-dev
make test
```

Run directly in host:
```
make install
make start
```

Using Docker:
```
make docker-build
make docker-start
```

TODO:
* Put a limit on file uploaded size and number of files
* Document the Rest API
* Create client libraries (or samples codes)
    * For the moment in my get paid project
    * So we can manage the sending of files
    * So we can use it in a terminal like a local Latex installation
    * In:
        * Javascript
            * Node
            * In browser? (rather pointless? Just give a sample code)
        * Python
* Allows to choose the Latex compiler (pdflatex, lualatex, xetex)
* Use Pandoc?
  * http://pandoc.org/MANUAL.html#creating-a-pdf
  * As a preprocessor -> another method
  * https://github.com/jez/pandoc-starter
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

Deploy:

```
docker build -t latex-on-http .
docker run -d -p 127.0.0.1:80:80 --name latex-on-http latex-on-http
```

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


## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FYtoTech%2Flatex-on-http.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2FYtoTech%2Flatex-on-http?ref=badge_large)