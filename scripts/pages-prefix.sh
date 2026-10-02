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
  -e "s|url('/assets/|url('${CORE}/assets/|g"

# Sanity check: no bare root refs may remain.
if grep -rlE "(href|src)=[\"']/(assets|css)/" public/ 2>/dev/null | grep -v "minutepapillons-org" | grep -q .; then
  echo "ERROR: unprefixed refs remain in public/:" >&2
  grep -rnE "(href|src)=[\"']/(assets|css)/" public/ | grep -v "${CORE}" | head >&2
  exit 1
fi

echo "public/ prefixed with /${CORE}/ — ready for subpath deploy."
