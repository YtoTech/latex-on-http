# LaTeX-On-HTTP intermediate Docker container,
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
FROM yoant/docker-texlive:alpine-2024
LABEL maintainer="Yoan Tournade <yoan@ytotech.com>"


#--------------------------------
# Install fonts.
#--------------------------------

# Only in edge for now, not published in 3.9
# https://pkgs.alpinelinux.org/package/edge/testing/x86_64/ttf-font-awesome
# ttf-font-awesome \

RUN apk --no-cache add \
    fontconfig \
    msttcorefonts-installer \
    ttf-liberation \
    ttf-linux-libertine \
    ttf-opensans \
    ttf-freefont \
    ttf-dejavu \
    ttf-inconsolata \
    ttf-freefont \
    ttf-droid \
    font-noto

# https://unix.stackexchange.com/questions/438257/how-to-install-microsoft-true-type-font-on-alpine-linux
RUN update-ms-fonts && fc-cache -f


#--------------------------------
# Install additionnal runtimes.
#--------------------------------

RUN apk --no-cache add \
    ghostscript


#--------------------------------
# Install Latex packages.
#--------------------------------

# TODO Make this process more dynamic with a list of packages?
COPY ./container/install_latex_packages.sh /tmp/
RUN /tmp/install_latex_packages.sh
