# Install additionnals Latex packages from CTAN here.
# As we use Debian texlive package, that is the 2015 Latex, we need to specify
# to tlmgr to use a 2015 repository.
# TODO (Use Vanilla 2016 Latex instead)
# LateX 3 support: expl3.
# https://tex.stackexchange.com/questions/53318/how-do-i-get-expl3-from-ctan
tlmgr init-usertree \
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
    expl3 \
    l3kernel \
    l3packages \
    l3experimental \
  && tlmgr update --self --all --reinstall-forcibly-removed
