# Compiling Latex documents in GitLab CI pipelines

Vincent-Xavier JUMEL uses the Latex-on-HTTP API to compiles Latex documents during a deploy stage
with GitLab CI for an [educational project](https://framagit.org/formation-nsi/projet-algo-du).

It consists of:
1. calling a simple bash script from the GitLab CI stage (see [`.gitlab-ci.yml`](https://framagit.org/formation-nsi/projet-algo-du/blob/a5b70eb90df23f4eef4b4adc35e4697e6417118c/.gitlab-ci.yml#L65))
2. calling the Latex-on-HTTP API with Curl in the bash script and piping the result to a file (see [`compile_dossier_eleve.sh`](https://framagit.org/formation-nsi/projet-algo-du/blob/a5b70eb90df23f4eef4b4adc35e4697e6417118c/documents/compile_dossier_eleve.sh)):

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

## Credits

Vincent-Xavier JUMEL ([GitLab](https://framagit.org/vincentxavier); [website](https://blog.thetys-retz.net/))
