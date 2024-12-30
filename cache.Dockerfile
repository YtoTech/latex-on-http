# LaTeX-On-HTTP cache process Docker container.
# 
# This is:
# - a Python runtime/distribution;
# - libmq, with development headers;
# - the cache application, with its dependencies.

# TODO Publish the final image?

FROM docker.io/python:3.13-alpine
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

# Set locales.
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

# Install libmq, but also packages required for pip install.
RUN apk add --no-cache \
    libzmq \
    zeromq-dev \
    cython \
    make \
    git \
    python3-dev \
    gcc \
    musl-dev \
    libffi-dev

RUN pip3 install -U \
  pip \
  pipenv

# Create app directory.
RUN mkdir -p /app/latex-on-http
WORKDIR /app/latex-on-http/

# Copy application source code.
COPY app_cache.py Makefile Pipfile Pipfile.lock /app/latex-on-http/
COPY ./latexonhttp/ /app/latex-on-http/latexonhttp/

# Install app dependencies.
RUN make install

EXPOSE 8080
CMD ["make", "start-cache"]
