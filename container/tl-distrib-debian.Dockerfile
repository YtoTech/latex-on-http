# LaTeX-On-HTTP intermediate Docker container,
# with the complete TexLive (& other compilers) distribution.
# 
# This is:
# - a Texlive distribution (yoant/docker-texlive);
# - a selection of fonts;
# - a selection of TexLive packages.

# For inspiration:
# https://gitlab.com/islandoftex/images/texlive

#--------------------------------
# Start from our docker-texlive distribution.
# https://hub.docker.com/r/yoant/docker-texlive
FROM yoant/docker-texlive:debian-2024
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"


#--------------------------------
# Install fonts.
#--------------------------------

RUN echo "deb http://deb.debian.org/debian bookworm contrib non-free" >> /etc/apt/sources.list

# Accepts Microsoft EULA.
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# Could install any from https://packages.debian.org/stable/fonts/
# TODO Pull them all?

# TODO Dynamically pull fonts from https://fonts.google.com/?

# https://github.com/potyt/fonts/tree/master/macfonts

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
    fonts-roboto \
    && apt-get autoremove --purge -y && apt-get clean && rm -rf /var/lib/apt/lists/*


#--------------------------------
# Install additionnal runtimes.
#--------------------------------

RUN apt-get update -qq && apt-get install -y \
    ghostscript \
    && apt-get autoremove --purge -y && apt-get clean && rm -rf /var/lib/apt/lists/*


#--------------------------------
# Install Latex packages.
#--------------------------------

# TODO Make this process more dynamic with a list of packages?
COPY ./container/install_latex_packages.sh /tmp/
RUN /tmp/install_latex_packages.sh

# Notes: we need tlmgr dependencies installed, because we use it at runtime
# (for listing packages, etc.)
