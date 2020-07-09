# Compiling Latex documents in GitLab CI pipelines

Vincent-Xavier JUMEL uses the LaTeX-On-HTTP API to compiles Latex documents during a deploy stage
with GitLab CI for an [educational project](https://framagit.org/formation-nsi/projet-algo-du).

It consists of:
1. calling a simple bash script from the GitLab CI stage (see [`.gitlab-ci.yml`](https://framagit.org/formation-nsi/projet-algo-du/blob/a5b70eb90df23f4eef4b4adc35e4697e6417118c/.gitlab-ci.yml#L65))
2. calling the LaTeX-On-HTTP API with cURL in the bash script and piping the result to a file (see [`compile_dossier_eleve.sh`](https://framagit.org/formation-nsi/projet-algo-du/blob/a5b70eb90df23f4eef4b4adc35e4697e6417118c/documents/compile_dossier_eleve.sh)):

```bash
#!/bin/bash

curl -v -X POST https://latex.ytotech.com/builds/sync \
    -H "Content-Type:application/json" \
    -d '{
        "compiler": "pdflatex",
        "resources": [
            {
                "main": true,
                "url": "https://framagit.org/formation-nsi/projet-algo-du/raw/master/documents/Dossier_Eleve.tex"
            }
        ]
    }' \
> Dossier_Eleve.pdf
```

As all the Latex source files are freely accessible through GitLab, it is simply passed using the `url` resource mode.

## Compiling private-files with bash-only

To compile private files - if using the `url` resource mode is not an option for you -, you can still make it work resorting only to bash and cURL.

One way is to use the `file` mode (with the file content passed as a base64 string in the Json payload). For that you can cat the file content and pipe it to base64 and insert the whole string in the payload used by cURL:
```bash
#!/bin/bash

curl -v -X POST https://latex.ytotech.com/builds/sync \
    -H "Content-Type:application/json" \
    -d '{
        "compiler": "pdflatex",
        "resources": [
            {
                "main": true,
                "file": "'$(cat Dossier_Eleve.tex | base64 -w 0)'"
            }
        ]
    }' \
> Dossier_Eleve.pdf
```

See `compile.sh` for a more comprehensible code.

## Credits

Vincent-Xavier JUMEL ([GitLab](https://framagit.org/vincentxavier); [website](https://blog.thetys-retz.net/))
