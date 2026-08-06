#!/usr/bin/env bash
# Re-sign every block and regenerate the signed index.json.
#
#   ./rebuild.sh                               # demo key, URLs derived from origin
#   ./rebuild.sh my-registry.key my-keyid      # your key, URLs derived from origin
#   ./rebuild.sh my-registry.key my-keyid https://example.org/blocks
#
# The base URL must point at the directory that CONTAINS the block folders;
# each entry is published as <baseurl>/<id>/<id>.epb.
#
# Requires: pip install cryptography
set -euo pipefail
# block_sign.py writes index.json into the CWD and the block globs are relative,
# so work from the repository root — but remember where the caller was, to
# resolve a relative key path they typed.
INVOKED_FROM=$PWD
cd "$(dirname "$0")"

KEY=${1:-keys/demo-registry.key}
KEYID=${2:-demo-registry-2026}

case "$KEY" in
  /*) ;;
  *) [ -f "$INVOKED_FROM/$KEY" ] && KEY="$INVOKED_FROM/$KEY" ;;
esac

derive_baseurl() {
  local url branch slug
  url=$(git remote get-url origin 2>/dev/null) || {
    echo "no 'origin' remote — pass the base URL as the third argument" >&2; exit 1; }
  # git@github.com:owner/repo.git  |  https://github.com/owner/repo.git
  slug=$(printf '%s' "$url" | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')
  # symbolic-ref (not rev-parse) so this still names the branch before the
  # first commit exists, rather than resolving to the literal "HEAD".
  branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo main)
  printf 'https://raw.githubusercontent.com/%s/%s/blocks' "$slug" "$branch"
}

BASEURL=${3:-$(derive_baseurl)}

test -f "$KEY" || {
  echo "no such key: ${1:-$KEY}" >&2
  echo "  looked in $INVOKED_FROM and $PWD" >&2
  echo "  (block_sign.py keygen writes the key into the directory you ran it from)" >&2
  exit 1
}

echo "key     : $KEY  (keyid: $KEYID)"
echo "base url: $BASEURL"
echo

python3 tools/validate_blocks.py

echo
# The output name MUST be <id>.epb — that is what the generated index points
# at; block_sign.py would otherwise default to block.epb and every install
# would 404.
for d in blocks/*/; do
  id=$(basename "$d")
  python3 tools/block_sign.py sign "$KEY" "$KEYID" "$d/block.json" "$d/$id.epb"
done

echo
python3 tools/block_sign.py index "$KEY" "$KEYID" "$BASEURL" blocks/*/

echo
echo "Commit and push, then load this in the portal's Blocks tab:"
echo "  ${BASEURL%/blocks}/index.json"
