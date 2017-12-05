# Latex On HTTP Docker container.
#
# TODO Try an installation based on Alpine.
FROM debian:jessie
MAINTAINER Yoan Tournade <yoan@ytotech.com>

COPY ./container/install_texlive.sh /tmp/install_texlive.sh
RUN /tmp/install_texlive.sh

COPY ./container/install_python.sh /tmp/install_python.sh
RUN /tmp/install_python.sh

# Clean APT cache.
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./container/install_latex_packages.sh /tmp/install_latex_packages.sh
RUN /tmp/install_latex_packages.sh

# Create app directory.
RUN \
    mkdir -p /home/latex-on-http

# Copy application source code.
# (TODO Or use a mount point? Or use pip install?)
COPY ./Makefile ./requirements.txt /home/latex-on-http/
COPY ./latex-on-http/ /home/latex-on-http/latex-on-http/

WORKDIR /home/latex-on-http/
RUN make install

EXPOSE 8080
CMD ["make", "start"]
