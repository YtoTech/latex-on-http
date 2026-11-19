---
title: Calling from CI pipelines
layout: base.njk
active: "/guides/ci/"
---

{% import "macros.njk" as macros %}

<div class="prose">

LaTeX-on-HTTP removes the need to maintain a TeXLive image on your CI runners:
the pipeline simply calls the HTTP API and uploads the resulting PDF as an
artifact. This is especially attractive when runners are ephemeral or
resource-constrained.

## GitLab CI

The simplest case: your LaTeX sources are in the repository (or accessible
through an URL), and the pipeline passes them with the `url` resource mode.

`.gitlab-ci.yml`:

```yaml
compile-pdf:
  stage: deploy
  image: curlimages/curl:latest
  variables:
    LATEX_ON_HTTP_URL: "https://latex.ytotech.com"
  script:
    - ./compile.sh documents/Dossier_Eleve.tex
  artifacts:
    paths:
      - Dossier_Eleve.pdf
```

`compile.sh` (passing the source by URL):

```bash
#!/bin/bash
set -o errexit

curl --fail-with-body --silent --show-error \
    -X POST "$LATEX_ON_HTTP_URL/builds/sync" \
    -H "Content-Type: application/json" \
    -d '{
        "compiler": "pdflatex",
        "resources": [
            {
                "main": true,
                "url": "'"$CI_PROJECT_URL"'/-/raw/'"$CI_COMMIT_SHA"'/documents/Dossier_Eleve.tex"
            }
        ]
    }' \
    > Dossier_Eleve.pdf
```

### Private files, bash-only

When sources are private (the server cannot fetch them), send their content
base64-encoded with the `file` resource mode. Bash only:

```bash
#!/bin/bash
set -o errexit

payload=$(cat <<EOF
{
    "compiler": "pdflatex",
    "resources": [
        {
            "main": true,
            "file": "$(base64 -w 0 < Dossier_Eleve.tex)"
        }
    ]
}
EOF
)

curl --fail-with-body --silent --show-error \
    -X POST "$LATEX_ON_HTTP_URL/builds/sync" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    > Dossier_Eleve.pdf
```

{{ macros.callout("note", "<p><code>--fail-with-body</code> (curl ≥ 7.76) makes the job fail on HTTP
errors while still printing the JSON error payload — so compilation logs stay
visible in the CI output. On older curls, use <code>--fail</code> plus a
separate <code>--write-out</code>, or check the exit code manually.</p>") }}

## GitHub Actions

```yaml
jobs:
  compile-pdf:
    runs-on: ubuntu-latest
    env:
      LATEX_ON_HTTP_URL: https://latex.ytotech.com
    steps:
      - uses: actions/checkout@v4

      - name: Build payload with base64-encoded sources
        run: |
          cat > payload.json <<EOF
          {
            "compiler": "pdflatex",
            "resources": [
              {
                "main": true,
                "file": "$(base64 -w 0 < report.tex)"
              }
            ]
          }
          EOF

      - name: Compile the PDF
        run: |
          curl --fail-with-body --silent --show-error \
            -X POST "$LATEX_ON_HTTP_URL/builds/sync" \
            -H "Content-Type: application/json" \
            -d @payload.json \
            --output report.pdf

      - uses: actions/upload-artifact@v4
        with:
          name: report
          path: report.pdf
```

## Tips for CI usage

- **Fail fast on LaTeX errors**: with `halt_on_error: true`, the compilation
  stops at the first error instead of forcing through, and the endpoint
  answers `400` — which fails the pipeline step.
- **Debug logs**: `options.response.log_files_on_failure` is enabled by
  default; `curl --fail-with-body` prints the payload so the LaTeX error
  appears in the job log.
- **Pin the service**: set the instance URL as a CI variable
  (`$LATEX_ON_HTTP_URL`) rather than hardcoding it, and consider
  `/texlive/information` to assert the TeXLive version your documents expect.
- **Self-hosted instances**: point the variable at your own deployment to keep
  unpublished sources inside your network (the server only fetches `url`
  resources it can reach — prefer inline `content`/`file` resources for
  private documents).

</div>
