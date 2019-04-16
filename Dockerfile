# Latex-on-HTTP final Docker container.
# 
# This is:
# - a Texlive distribution;
# - a selection of fonts;
# - a selection of TexLive packages;
# - a Python runtime/distribution;
# - the Latex-on-HTTP application, with its dependencies.


# TODO Publish to Docker Hub. (all less the Python app?)

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
COPY ./Makefile ./Pipfile ./Pipfile.lock /app/latex-on-http/
COPY ./latexonhttp/ /app/latex-on-http/latexonhttp/

# Install app dependencies.
RUN make install

EXPOSE 8080
CMD ["make", "start"]
