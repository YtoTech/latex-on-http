set -e

apt-get update -qq && apt-get install -y \
    wget \
    libswitch-perl

# Based on :
# - https://www.tug.org/texlive/quickinstall.html
# - https://github.com/camilstaps/docker-texlive/blob/master/Dockerfile
# - https://tex.stackexchange.com/questions/1092/how-to-install-vanilla-texlive-on-debian-or-ubuntu

cd /tmp

wget -qO- http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz | tar xz \
    && ./install-tl*/install-tl -profile $1

# Cleanup
rm -rf /tmp/install-tl-*
