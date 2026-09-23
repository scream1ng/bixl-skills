#!/bin/sh
# ./release.sh <skill-folder> <version> <notes>
# Tags <skill>-<version> and publishes a zip of that folder with SKILL.md at its root.
set -e
skill=$1; version=$2; notes=$3
[ -n "$notes" ] || { echo "usage: ./release.sh <skill> <version> <notes>" >&2; exit 1; }
tag="$skill-$version"; zip="$(mktemp -d)/$tag.zip"
(cd "$skill" && zip -qr "$zip" . -x '*__pycache__*' '*.pyc' '*.DS_Store' '*.fixture-cache*')
git tag -a "$tag" -m "$skill $version"
git push origin "$tag"
gh release create "$tag" "$zip" --title "$skill $version" --notes "$notes"
