#!/bin/sh
# Regenerate the documentation logos and favicon from their TikZ sources.
#
# Requires a TeX installation with TikZ + the Latin Modern fonts, and
# dvisvgm. The generated SVG files are committed, so this script is only
# needed when the artwork changes.
set -eu

cd "$(dirname "$0")"
here=$(pwd)
out="$here/../../assets"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

build_wordmark() {
  source=$1
  variant=$2
  target=$3
  base=$(basename "$source" .tex)
  job="$base-$variant"

  if [ "$variant" = "dark" ]; then
    input="\\def\\DarkLogo{}\\input{$source}"
  else
    input="\\input{$source}"
  fi

  latex -interaction=nonstopmode -halt-on-error \
    -output-directory="$work" -jobname="$job" "$input" >/dev/null
  dvisvgm --no-fonts --exact-bbox --optimize \
    "$work/$job.dvi" -o "$out/img/$target" >/dev/null
  echo "Regenerated $out/img/$target"
}

mkdir -p "$out/img"

build_wordmark latex-on-http.tex light latex-on-http-logo.svg
build_wordmark latex-on-http.tex dark latex-on-http-logo-dark.svg
build_wordmark ytotech.tex light ytotech-logo.svg
build_wordmark ytotech.tex dark ytotech-logo-dark.svg

latex -interaction=nonstopmode -halt-on-error \
  -output-directory="$work" 'favicon.tex' >/dev/null
# Keep the full 64×64 TeX bounding box here: older dvisvgm releases can
# shrink --exact-bbox to the glyph only, dropping the coloured background.
dvisvgm --no-fonts --optimize \
  "$work/favicon.dvi" -o "$out/favicon.svg" >/dev/null
echo "Regenerated $out/favicon.svg"
