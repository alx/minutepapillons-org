#!/usr/bin/env bash
# Rewrite root-absolute references in the built site (public/) for a
# subpath deployment (GitHub project Pages).
#
# Source files keep root-absolute URLs (WordPress mirror convention) so
# `hugo serve` / `hugo build` locally always work at "/". This script is
# the only place that injects the deployment subpath.
#
# Usage: scripts/pages-prefix.sh /subpath/
#   e.g. scripts/pages-prefix.sh /minutepapillons-org
set -euo pipefail

SUB="${1:?usage: pages-prefix.sh /subpath/}"
CORE="${SUB#/}"; CORE="${CORE%/}"
cd "$(dirname "$0")/.."

if grep -rq "/${CORE}/assets/" public/ 2>/dev/null; then
  echo "public/ already contains /${CORE}/ refs — refusing to double-prefix." >&2
  exit 1
fi

# WordPress-style versioned assets: the WP mirror kept literal "?ver=..." in
# some asset FILENAMES (e.g. style.min.css?ver=7.1.1.css) and the HTML refs
# encode them as %3Fver=... . GitHub Pages cannot route those: server-side the
# "?" starts a query string, so the request 404s. Strip the version suffix at
# deploy time only (source/public keep the WP-mirror convention).
find public -type f -name '*[?]*' -print0 | while IFS= read -r -d '' f; do
  case "$f" in
    *'?ver='*) ;;
    *) echo "ERROR: unexpected '?' in filename: $f" >&2; exit 1 ;;
  esac
  clean="${f%%[?]ver=*}"
  if [ -e "$clean" ]; then
    echo "ERROR: rename would clobber existing $clean" >&2; exit 1
  fi
  mv "$f" "$clean"
  echo "renamed -> $clean"
done

find public -type f \( -name '*.html' -o -name '*.css' \) -print0 | xargs -0 sed -i \
  -e 's|%3Fver=[0-9.]*\.[A-Za-z0-9]*||g'

# Order matters: the href rule runs FIRST so it prefixes href="/assets/..
# in one step and the asset rules (which require a quote right before the
# path) can never re-match the already-prefixed string.
find public -type f \( -name '*.html' -o -name '*.css' \) -print0 | xargs -0 sed -i \
  -e "s|href=\"/|href=\"/${CORE}/|g" \
  -e "s|\"/assets/|\"/${CORE}/assets/|g" \
  -e "s|'/assets/|'/${CORE}/assets/|g" \
  -e "s|\"/css/|\"/${CORE}/css/|g" \
  -e "s|'/css/|'/${CORE}/css/|g" \
  -e "s|url(/assets/|url(/${CORE}/assets/|g" \
  -e "s|url(\"/assets/|url(\"${CORE}/assets/|g" \
  -e "s|url('/assets/|url('${CORE}/assets/|g" \
  -e "s|, /assets/|, /${CORE}/assets/|g"

# Sanity check: no bare root refs may remain (any occurrence of /assets/ or
# /css/ preceded by a quote, comma, or opening paren must be prefixed).
if grep -rnE "[\"',] */(assets|css)/" public/ 2>/dev/null | grep -v "/${CORE}/" | grep -q .; then
  echo "ERROR: unprefixed refs remain in public/:" >&2
  grep -rnE "[\"',] */(assets|css)/" public/ | grep -v "/${CORE}/" | head >&2
  exit 1
fi

echo "public/ prefixed with /${CORE}/ — ready for subpath deploy."
