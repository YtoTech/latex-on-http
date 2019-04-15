set -e

# Enable contrib and non-free packages.
# For MS fonts.
# echo "deb http://deb.debian.org/debian stretch contrib non-free" >> /etc/apt/sources.list

# Accepts Microsoft EULA.
# echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# Could install any from https://packages.debian.org/stable/fonts/
# TODO Pull them all?

# TODO Dynamically pull fonts from https://fonts.google.com/?

# apt-get update -qq && apt-get install -y \
#     fontconfig \
#     fonts-cmu \
#     fonts-liberation \
#     ttf-mscorefonts-installer \
#     fonts-dejavu \
#     fonts-ebgaramond \
#     fonts-font-awesome \
#     fonts-gfs-baskerville \
#     fonts-gfs-didot \
#     fonts-inconsolata \
#     fonts-jura \
#     fonts-lato \
#     fonts-linuxlibertine \
#     fonts-noto \
#     fonts-roboto

# Alpine

# Only in edge for now, not published in 3.9
# https://pkgs.alpinelinux.org/package/edge/testing/x86_64/ttf-font-awesome
# ttf-font-awesome \

apk --no-cache add \
    fontconfig \
    msttcorefonts-installer \
    ttf-liberation \
    ttf-linux-libertine \
    ttf-opensans \
    ttf-freefont \
    ttf-dejavu \
    ttf-inconsolata \
    ttf-ubuntu-font-family \
    ttf-droid \
    font-noto

# https://unix.stackexchange.com/questions/438257/how-to-install-microsoft-true-type-font-on-alpine-linux
update-ms-fonts && fc-cache -f
