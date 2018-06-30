# Latex On HTTP Docker container.
FROM debian:stretch
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"

# Install Texlive: latest release.
COPY ./container/texlive.profile /tmp/
COPY ./container/install_texlive.sh /tmp/
RUN /tmp/install_texlive.sh /tmp/texlive.profile

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

# Create app directory.
RUN mkdir -p /app/latex-on-http
WORKDIR /app/latex-on-http/

# Copy application source code.
# (TODO Or use a mount point? Or use pip install?)
COPY ./Makefile ./requirements.txt /app/latex-on-http/
COPY ./latex-on-http/ /app/latex-on-http/latex-on-http/

RUN make install

EXPOSE 8080
CMD ["make", "start"]
