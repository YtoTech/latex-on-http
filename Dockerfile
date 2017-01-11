# Latex On HTTP Docker container.
#
# Try an installation based on Alpine.
FROM debian:latest
MAINTAINER Yoan Tournade <yoan@ytotech.com>

# TODO Install Vanilla Latex?
# http://tex.stackexchange.com/questions/1092/how-to-install-vanilla-texlive-on-debian-or-ubuntu
RUN apt-get update \
  && apt-get install -y \
    # TODO How do we select the list of Latex packages to install?
    # (texlive-full is heavy!)
    texlive-fonts-extra \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-luatex \
    texlive-math-extra \
    texlive-xetex

# Enable contrib for MS fonts.
# RUN echo "deb http://deb.debian.org/debian stable contrib non-free" >> /etc/apt/sources.list
# Then install -> ttf-mscorefonts-installer \

# Temporarily separate Latex installation from other dependencies,
# so we don't have to re-fetch all Latex dependencies if we change things below.
RUN apt-get install -y \
    # TODO We need Python (go for Python 3!)
    python3 \
    python-pip \
    # TODO To install with Latex. (the two followings)
    wget \
    xzdec \
    # Add some fonts.
    fonts-liberation \
    cm-super \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Virtualenv
RUN pip install \
  virtualenv

# TODO After Latex installation.
# Install additionnals Latex packages from CTAN here.
RUN tlmgr init-usertree \
  # As we use Debian texlive package, that is the 2015 Latex, we need to specify
  # to tlmgr to use a 2015 repository.
  # TODO (Use Vanilla 2016 Latex instead)
  && tlmgr option repository ftp://tug.org/historic/systems/texlive/2015/tlnet-final \
  && tlmgr install \
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
    footmisc

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
COPY ./run.sh ./requirements.txt /home/latex-on-http/
COPY ./latex-on-http/ /home/latex-on-http/latex-on-http/

WORKDIR /home/latex-on-http/
CMD ["/bin/bash", "/home/latex-on-http/run.sh"]
