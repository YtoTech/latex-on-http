# Latex-on-HTTP intermediate Docker container,
# with the complete TexLive (& other compilers) distribution.
# 
# This is:
# - a Texlive distribution (yoant/docker-texlive);
# - a selection of fonts;
# - a selection of TexLive packages.

# TODO Publish to Docker Hub. (all less the Python app?)

#--------------------------------
# Start from our docker-texlive distribution.
# https://hub.docker.com/r/yoant/docker-texlive
FROM yoant/docker-texlive:debian
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"


#--------------------------------
# Install fonts.
#--------------------------------

RUN echo "deb http://deb.debian.org/debian stretch contrib non-free" >> /etc/apt/sources.list

# Accepts Microsoft EULA.
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# Could install any from https://packages.debian.org/stable/fonts/
# TODO Pull them all?

# TODO Dynamically pull fonts from https://fonts.google.com/?

RUN apt-get update -qq && apt-get install -y \
    fontconfig \
    fonts-cmu \
    fonts-liberation \
    ttf-mscorefonts-installer \
    fonts-dejavu \
    fonts-ebgaramond \
    fonts-font-awesome \
    fonts-gfs-baskerville \
    fonts-gfs-didot \
    fonts-inconsolata \
    fonts-jura \
    fonts-lato \
    fonts-linuxlibertine \
    fonts-noto \
    fonts-roboto


#--------------------------------
# Install Latex packages.
#--------------------------------

# TODO Make this process more dynamic with a list of packages?
COPY ./container/install_latex_packages.sh /tmp/
RUN /tmp/install_latex_packages.sh

# Notes: we need tlmgr dependencies installed, because we use it at runtime
# (for listing packages, etc.)


#--------------------------------
# Clean
#--------------------------------

# Clean APT cache.
RUN apt-get autoremove --purge -y && apt-get clean && rm -rf /var/lib/apt/lists/*
