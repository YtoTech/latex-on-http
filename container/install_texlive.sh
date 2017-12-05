apt-get update -qq
# TODO How do we select the list of Latex packages to install?
# (texlive-full is heavy!)
# texlive-lang-all: Heavy one, but we got all languages.
apt-get install -y \
    biber \
    xzdec \
    fontconfig \
    latex-xcolor \
    preview-latex-style \
    texlive-bibtex-extra \
    texlive-fonts-extra \
    texlive-generic-extra \
    texlive-lang-all \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-luatex \
    texlive-math-extra \
    texlive-xetex \
    texlive-science \
    fonts-liberation \
    cm-super

# TODO Separate fonts install from core Latex install?
# Fonts: fonts-liberation, cm-super.
# Enable contrib for MS fonts.
# RUN echo "deb http://deb.debian.org/debian stable contrib non-free" >> /etc/apt/sources.list
# Then install -> ttf-mscorefonts-installer \
