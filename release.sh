#!/bin/sh
# ./release.sh <skill-folder> <version> <notes>
# Tags <skill>-<version>, publishes a zip of that folder with SKILL.md at its root,
# and points the README download link at it.
set -e
skill=$1; version=$2; notes=$3
[ -n "$notes" ] || { echo "usage: ./release.sh <skill> <version> <notes>" >&2; exit 1; }
tag="$skill-$version"; zip="$(mktemp -d)/$tag.zip"
(cd "$skill" && zip -qr "$zip" . -x '*__pycache__*' '*.pyc' '*.DS_Store' '*.fixture-cache*')
sed -i '' "s|^\*\*\[Download $skill-.*|**[Download $tag.zip](../../releases/download/$tag/$tag.zip)** — \`SKILL.md\` at the zip root; unzip into a folder named \`$skill\`.|" README.md
git commit -q -m "README: $tag download link" README.md
git push -q origin HEAD
git tag -a "$tag" -m "$skill $version"
git push -q origin "$tag"
gh release create "$tag" "$zip" --title "$skill $version" --notes "$notes"
