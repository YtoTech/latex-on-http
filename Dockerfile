# LaTeX-On-HTTP final Docker container.
# 
# This is:
# - a Texlive distribution;
# - a selection of fonts;
# - a selection of TexLive packages;
# - libmq, with development headers;
# - a Python runtime/distribution;
# - the LaTeX-On-HTTP application, with its dependencies.

# TODO Publish the final image.

# Start from our docker-texlive distribution.
# https://hub.docker.com/r/yoant/docker-texlive
FROM yoant/latexonhttp-python:debian
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

# Set locales.
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

# Create app directory.
RUN mkdir -p /app/latex-on-http
WORKDIR /app/latex-on-http/

# Copy application source code.
COPY app.py Makefile pyproject.toml poetry.lock /app/latex-on-http/
COPY ./latexonhttp/ /app/latex-on-http/latexonhttp/

# TODO curl -LsSf https://astral.sh/uv/install.sh | sh
# Install app dependencies.
RUN make install

# Add migration tool.
RUN apt-get update -qq && apt-get install -y \
    curl \
    && curl -fsSL \
        https://raw.githubusercontent.com/pressly/goose/master/install.sh |\
        sh \
    && apt-get autoremove --purge -y && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /app/latex-on-http/tools/migrations
COPY ./tools/migrations/ /app/latex-on-http/tools/
ENV GOOSE_MIGRATION_DIR /app/latex-on-http/tools/migrations
ENV GOOSE_DRIVER postgres

COPY ./tools/entrypoint.sh ./tools/

EXPOSE 8080
ENTRYPOINT ["/bin/bash", "tools/entrypoint.sh"]
CMD ["prod"]
