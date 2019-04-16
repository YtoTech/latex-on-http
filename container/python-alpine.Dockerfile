# Latex-on-HTTP intermediate Docker container,
# with the TexLive (& other compilers) distribution and Python runtime.
# 
# This is:
# - a Texlive distribution (yoant/docker-texlive);
# - a selection of fonts;
# - a selection of TexLive packages;
# - a Python runtime/distribution.
FROM yoant/latexonhttp-tl-distrib:alpine
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

RUN apk --no-cache add \
    python3 \
    git \
    make \
    python3-dev \
    libffi-dev \
    gcc \
    musl-dev

# Update pip and install Pipenv.
RUN pip3 install -U \
  pip \
  pipenv
