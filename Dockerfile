# Latex On HTTP Docker container.
#
# Try an installation based on Alpine.
FROM debian:jessie
MAINTAINER Yoan Tournade <yoan@ytotech.com>

# TODO Get inspiration from
# https://github.com/thomasWeise/docker-texlive/blob/master/image/Dockerfile
# https://github.com/harshjv/docker-texlive-2015
# https://hub.docker.com/r/mtneug/texlive/
# This one seems to include latest Texlive install.
# https://hub.docker.com/r/rchurchley/texlive/


# TODO Or try install Vanilla Latex?
# https://tex.stackexchange.com/questions/1092/how-to-install-vanilla-texlive-on-debian-or-ubuntu
# https://www.tug.org/texlive/debian.html

RUN apt-get update \
  && apt-get install -y \
    # TODO How do we select the list of Latex packages to install?
    # (texlive-full is heavy!)
    biber \
    wget \
    xzdec \
    fontconfig \
    latex-xcolor \
    preview-latex-style \
    texlive-bibtex-extra \
    texlive-fonts-extra \
    texlive-generic-extra \
    # Heavy one, but we got all languages.
    texlive-lang-all \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-luatex \
    texlive-math-extra \
    texlive-xetex \
    texlive-science

# Enable contrib for MS fonts.
# RUN echo "deb http://deb.debian.org/debian stable contrib non-free" >> /etc/apt/sources.list
# Then install -> ttf-mscorefonts-installer \

# Temporarily separate Latex installation from other dependencies,
# so we don't have to re-fetch all Latex dependencies if we change things below.
RUN apt-get install -y \
    # TODO We need Python (go for Python 3!)
    python3 \
    python3-pip \
    # Add some fonts.
    fonts-liberation \
    cm-super \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Virtualenv
RUN pip3 install -U \
  pip \
  virtualenv

# TODO After Latex installation.
# Install additionnals Latex packages from CTAN here.
RUN tlmgr init-usertree \
  # As we use Debian texlive package, that is the 2015 Latex, we need to specify
  # to tlmgr to use a 2015 repository.
  # TODO (Use Vanilla 2016 Latex instead)
  && tlmgr option repository ftp://tug.org/historic/systems/texlive/2015/tlnet-final \
  && tlmgr install \
    anyfontsize \
    babel \
    babel-french \
    fontspec \
    geometry \
    ragged2e \
    spreadtab \
    fp \
    xstring \
    arydshln \
    hhline \
    titlesec \
    enumitem \
    xunicode \
    xltxtra \
    hyperref \
    polyglossia \
    wallpaper \
    footmisc \
    # LateX 3 support
    # https://tex.stackexchange.com/questions/53318/how-do-i-get-expl3-from-ctan
    expl3 \
    l3kernel \
    l3packages \
    l3experimental \
  && tlmgr update --self --all --reinstall-forcibly-removed


# TODO Then install Flask & co? (requirements.txt)
# See https://github.com/gliderlabs/docker-alpine/blob/master/docs/usage.md
# RUN sh /check.sh

# This is an HTTP app.
EXPOSE 80

# Create app directory.
RUN \
    mkdir -p /home/latex-on-http

# Copy application source code.
# (TODO Or use a mount point? Or use pip install?)
COPY ./Makefile ./requirements.txt /home/latex-on-http/
COPY ./latex-on-http/ /home/latex-on-http/latex-on-http/

cd /home/latex-on-http/
make install

WORKDIR /home/latex-on-http/
CMD ["make", "start"]
