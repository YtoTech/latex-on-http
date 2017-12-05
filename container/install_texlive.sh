apt-get update
# TODO How do we select the list of Latex packages to install?
# (texlive-full is heavy!)
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
    # Heavy one, but we got all languages.
    texlive-lang-all \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-luatex \
    texlive-math-extra \
    texlive-xetex \
    texlive-science
