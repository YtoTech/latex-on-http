# LaTeX-On-HTTP final Docker container.
# 
# This is:
# - a Texlive distribution;
# - a selection of fonts;
# - a selection of TexLive packages;
# - libmq, with development headers;
# - a Python runtime/distribution;
# - the LaTeX-On-HTTP application, with its dependencies;
# - the statically-built documentation site, served from /docs/.

# Build the documentation site (Eleventy / Node, kept out of the final image).
# The site lives in a `docs/site/` subdirectory here, mirroring the repository
# layout: the Eleventy config writes its output to `../_build` relative to the
# config file, i.e. /docs-src/_build.
FROM node:24-alpine AS docs-builder
WORKDIR /docs-src/site
COPY docs/site/package.json docs/site/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY docs/site/ ./
RUN npm run build

# TODO Publish the final image.

# Start from our docker-texlive distribution.
# https://hub.docker.com/r/yoant/docker-texlive
FROM yoant/latexonhttp-python:debian
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

# Set locales.
ENV LC_ALL="C.UTF-8"
ENV LANG="C.UTF-8"

# Create app directory.
RUN mkdir -p /app/latex-on-http
WORKDIR /app/latex-on-http/

# Copy application source code.
COPY app.py Makefile pyproject.toml uv.lock /app/latex-on-http/
COPY ./latexonhttp/ /app/latex-on-http/latexonhttp/

# Install app dependencies.
RUN uv venv && uv sync --no-dev

# Copy the prebuilt documentation site, served from the /docs/ route.
COPY --from=docs-builder /docs-src/_build/ /app/latex-on-http/docs/_build/

# Add migration tool.
RUN apt-get update -qq && apt-get install -y \
    bubblewrap \
    python3-pygments \
    curl \
    && curl -fsSL \
        https://raw.githubusercontent.com/pressly/goose/master/install.sh |\
        sh \
    && apt-get autoremove --purge -y && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /app/latex-on-http/tools/migrations
COPY ./tools/migrations/ /app/latex-on-http/tools/migrations/
ENV GOOSE_MIGRATION_DIR="/app/latex-on-http/tools/migrations"
ENV GOOSE_DRIVER="postgres"

COPY ./tools/entrypoint.sh ./tools/

EXPOSE 8080
ENTRYPOINT ["/bin/bash", "tools/entrypoint.sh"]
CMD ["prod"]
