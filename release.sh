#!/bin/sh
# ./release.sh <skill-folder> <version> <notes>
#   e.g. ./release.sh draft-drawing v1.1 "- Bend notes on the assembly sheet"
#
# Run `python -m unittest discover -s tests` in the skill's folder first.
# This then, for that skill alone:
#   1. zips the folder with SKILL.md at the zip ROOT (no wrapper folder), so the
#      file can be uploaded straight to an assistant;
#   2. repoints the README download link at the new tag, commits and pushes it;
#   3. tags <skill>-<version> and publishes a release with the zip attached.
# Tags are per skill. GitHub's own "Source code" zip always holds every skill in
# the repo; the attached zip is the one to hand out.
#
# A new skill: add its folder, a README section with a `**[Download ...]**` line
# for sed to find, then release it the same way.
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
