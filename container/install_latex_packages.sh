set -e

# Update tlmgr first, else an out-of-date version can cause a failure.
tlmgr update --self --all --reinstall-forcibly-removed

# Install additionnals Latex packages from CTAN.
tlmgr init-usertree

# Configures mirrors / repository.
echo "Automatically determined mirror:"
tlmgr option repository
# Alternatively hard-set mirror.
# tlmgr option repository http://mirror.ctan.org/systems/texlive/tlnet

# LateX 3 support:
#  https://ctan.org/pkg/l3kernel

# TODO More babel langugages support.
# TODO Makes languages support during installation configurable:
# map Latex languages and packages to install for each languages.

tlmgr install \
    anyfontsize \
    babel \
    babel-french \
    fontspec \
    geometry \
    spreadtab \
    fp \
    xstring \
    arydshln \
    titlesec \
    enumitem \
    xunicode \
    xltxtra \
    hyperref \
    polyglossia \
    wallpaper \
    footmisc \
    l3kernel \
    l3packages \
    l3experimental

