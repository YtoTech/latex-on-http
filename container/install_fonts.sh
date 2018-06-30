set -e

# Enable contrib and non-free packages.
# For MS fonts.
echo "deb http://deb.debian.org/debian stretch contrib non-free" >> /etc/apt/sources.list

# RUN echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula \
#     select true | debconf-set-selections

# Could install any from https://packages.debian.org/stable/fonts/
# TODO Pull them all?

# TODO Dynamically pull fonts from https://fonts.google.com/?

apt-get update -qq && apt-get install -y \
    fontconfig \
    fonts-cmu \
    fonts-liberation \
    ttf-mscorefonts-installer \
    fonts-dejavu \
    fonts-ebgaramond \
    fonts-font-awesome \
    fonts-gfs-baskerville \
    fonts-gfs-didot \
    fonts-inconsolata \
    fonts-jura \
    fonts-lato \
    fonts-linuxlibertine \
    fonts-noto \
    fonts-roboto \
    octicons

