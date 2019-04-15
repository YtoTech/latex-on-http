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
FROM yoant/latexonhttp-tl-distrib:debian
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

# Install Python 3.
# --> TODO Create another image adding python (Debian & Alpine)
COPY ./container/install_python.sh /tmp/
RUN /tmp/install_python.sh

# Clean APT cache.
RUN apt-get autoremove --purge -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set locales.
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

# Create app directory.
RUN mkdir -p /app/latex-on-http
WORKDIR /app/latex-on-http/

# Copy application source code.
# (TODO Or use a mount point? Or use pip install?)
COPY ./Makefile ./Pipfile ./Pipfile.lock /app/latex-on-http/
COPY ./latexonhttp/ /app/latex-on-http/latexonhttp/

RUN make install

EXPOSE 8080
CMD ["make", "start"]
