apt-get update
# TODO How do we select the list of Latex packages to install?
# (texlive-full is heavy!)
# texlive-lang-all: Heavy one, but we got all languages.
apt-get install -y \
    biber \
    wget \
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
    texlive-science
