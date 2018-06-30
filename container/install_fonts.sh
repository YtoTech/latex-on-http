set -e

apt-get update -qq && apt-get install -y \
    fontconfig \
    fonts-liberation \
    cm-super

# Enable contrib for MS fonts.
# RUN echo "deb http://deb.debian.org/debian stable contrib non-free" >> /etc/apt/sources.list
# Then install -> ttf-mscorefonts-installer \
