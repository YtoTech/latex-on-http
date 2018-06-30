# Latex On HTTP Docker container.
# TODO Build base Texlive package to https://hub.docker.com/,
# so we can speed up installation (just pulling lots of Gb).
# Use buster so we have Python 3.6+.
FROM debian:buster
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

# Install Texlive: latest release.
COPY ./container/texlive.profile /tmp/
COPY ./container/install_texlive.sh /tmp/
# TODO Make textlive.profile a template, so we can configure the installation path.
RUN /tmp/install_texlive.sh /tmp/texlive.profile
# Add Texlive binaries to path.
ENV PATH="/usr/local/texlive/bin/x86_64-linux:${PATH}"

# Install fonts.
COPY ./container/install_fonts.sh /tmp/
RUN /tmp/install_fonts.sh

# Install Python 3.
COPY ./container/install_python.sh /tmp/
RUN /tmp/install_python.sh

# Clean APT cache.
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Latext packages.
# TODO Make this process dynamic with 
COPY ./container/install_latex_packages.sh /tmp/
RUN /tmp/install_latex_packages.sh

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
