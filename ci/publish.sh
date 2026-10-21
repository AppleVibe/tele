#!/usr/bin/env bash
# publish.sh win64|linux64|macos
# signs the update feed of one platform and adds its files to the release. the first platform to finish creates
# the release and fills the feeds of the others with the previous release's, so their clients keep seeing that one.
# needs TAG, BASE, COUNTER, UPSTREAM_TAG, PREVIOUS_TAG, UPDATE_KEY, GH_TOKEN, GH_REPO, the platform's files in the
# current directory and the tele checkout in ./tele
set -euo pipefail

platform=$1
case "$platform" in
  win64) entry=tele.exe files=("tele-$TAG-win64.zip") ;;
  linux64) entry=tele files=("tele-$TAG-linux64.zip" "tele-$TAG-linux64-symbols.zip") ;;
  macos) entry=tele.app/Contents/MacOS/tele files=("tele-$TAG-macos.zip" "tele-$TAG-macos.dmg" "tele-$TAG-macos-symbols.zip") ;;
  *)
    echo "usage: $0 win64|linux64|macos" >&2
    exit 2
    ;;
esac
platforms=(win64 linux64 macos)
url="$GITHUB_SERVER_URL/$GH_REPO"

for file in "${files[@]}"; do
  test -f "$file"
done

zip="tele-$TAG-$platform.zip"
[ -n "$(unzip -Z1 "$zip" "$entry")" ]
printf '{"tag":"%s","base":%s,"counter":%s,"url":"%s","zip_sha256":"%s","exe_sha256":"%s"}' \
  "$TAG" "$BASE" "$COUNTER" \
  "$url/releases/download/$TAG/$zip" \
  "$(sha256sum < "$zip" | cut -c1-64)" \
  "$(unzip -p "$zip" "$entry" | sha256sum | cut -c1-64)" > "feed-$platform.json"
openssl pkeyutl -sign -rawin -inkey <(printf '%s\n' "$UPDATE_KEY") -in "feed-$platform.json" -out "feed-$platform.sig"
openssl pkeyutl -verify -rawin -pubin -inkey tele/ci/update-public-key.pem -in "feed-$platform.json" -sigfile "feed-$platform.sig"
printf '{"feed":"%s","signature":"%s"}\n' "$(base64 -w0 "feed-$platform.json")" "$(base64 -w0 "feed-$platform.sig")" > "tele-update-$platform.json"

python3 tele/ci/notes.py --repo tele --tag "$TAG" --previous "$PREVIOUS_TAG" --upstream "$UPSTREAM_TAG" \
  --url "$url" --rev "$GITHUB_SHA" --out notes.md --json tele-changelog.json

assets() {
  gh release view "$TAG" --json assets --jq '.assets[].name'
}

has() {
  grep -qxF "$1" <<< "$(assets)"
}

# true when the release has an asset with this file's name and sha256
unchanged() {
  local name digest
  name=$(basename "$1")
  digest="sha256:$(sha256sum < "$1" | cut -c1-64)"
  gh api "repos/$GH_REPO/releases/tags/$TAG" --jq ".assets[] | select(.name == \"$name\") | .digest" \
    | grep -qxF "$digest"
}

# uploads a file unless the release already has one by that name. another platform's job can upload the same name
# at the same time, so a failed upload is fine when the asset is there afterwards
add() {
  local name
  name=$(basename "$1")
  if has "$name"; then
    return 0
  fi
  if ! gh release upload "$TAG" "$1"; then
    has "$name"
  fi
}

# uploads over whatever is there. a placeholder uploaded between clobber's check and the upload makes the upload
# fail, the next attempt clobbers it
replace() {
  local attempt
  for attempt in 1 2 3; do
    if gh release upload "$TAG" --clobber "$@"; then
      return 0
    fi
    echo "upload attempt $attempt failed"
    sleep 10
  done
  return 1
}

name() {
  case "$1" in
    win64) echo windows ;;
    linux64) echo linux ;;
    macos) echo macos ;;
  esac
}

join() {
  local IFS=,
  local text="$*"
  echo "${text//,/, }"
}

# the full notes once every platform is in, before that a line about the rollout
body() {
  local list=$1 ready=() building=() other
  for other in "${platforms[@]}"; do
    if grep -qxF "tele-$TAG-$other.zip" <<< "$list"; then
      ready+=("$(name "$other")")
    else
      building+=("$(name "$other")")
    fi
  done
  if [ ${#building[@]} -eq 0 ]; then
    cat notes.md
  elif [ ${#ready[@]} -eq 0 ]; then
    echo "tele ${TAG#*-tele.} is rolling out. still building: $(join "${building[@]}")."
  else
    echo "tele ${TAG#*-tele.} is rolling out. ready: $(join "${ready[@]}"). still building: $(join "${building[@]}")."
  fi
}

# created without assets and not as the latest release yet: the platform jobs can finish at the same time, and
# clients shouldn't see the release before every feed is in place
if gh release view "$TAG" > /dev/null 2>&1; then
  target=$(gh release view "$TAG" --json targetCommitish --jq .targetCommitish)
  if [ "$target" != "$GITHUB_SHA" ]; then
    echo "::error::$TAG already exists for $target, this run publishes $GITHUB_SHA"
    exit 1
  fi
else
  body "" > body.md
  if ! gh release create "$TAG" --latest=false --target "$GITHUB_SHA" \
    --title "tele ${TAG#*-tele.} · $UPSTREAM_TAG" --notes-file body.md; then
    gh release view "$TAG" > /dev/null
    echo "another platform created $TAG first"
  fi
fi

add tele-changelog.json
# gh uploads the files of one call in parallel: the zips go up first, so a live feed never points at a missing zip.
# a re-run skips files the release already has byte for byte, so it doesn't take a live zip away for a while
changed=()
for file in "${files[@]}"; do
  if ! unchanged "$file"; then
    changed+=("$file")
  fi
done
if [ ${#changed[@]} -gt 0 ]; then
  replace "${changed[@]}"
fi
replace "tele-update-$platform.json"

if [ -n "$PREVIOUS_TAG" ]; then
  mkdir -p previous
  for other in "${platforms[@]}"; do
    feed="tele-update-$other.json"
    if [ "$other" = "$platform" ] || has "$feed"; then
      continue
    fi
    if gh release download "$PREVIOUS_TAG" --pattern "$feed" --dir previous --clobber; then
      add "previous/$feed"
    else
      echo "::warning::$PREVIOUS_TAG has no $feed, $(name "$other") clients find no update feed until $(name "$other") is published"
    fi
  done
fi

# even the first release must have every real or previous signed feed before becoming latest
complete=true
list=$(assets)
for other in "${platforms[@]}"; do
  if ! grep -qxF "tele-update-$other.json" <<< "$list"; then
    complete=false
  fi
done
latest=$(gh release view --json tagName --jq .tagName 2> /dev/null || true)
if [ "$complete" != true ]; then
  echo "::warning::$TAG waits for every platform feed before becoming latest"
elif [ -z "$latest" ] || { [ "$latest" = "$PREVIOUS_TAG" ] && [[ "$latest" =~ ^v[0-9.]*-tele\.([0-9]+)$ ]] && [ "${BASH_REMATCH[1]}" -lt "$COUNTER" ]; }; then
  gh release edit "$TAG" --latest > /dev/null
elif [ "$latest" != "$TAG" ]; then
  echo "::warning::$latest stays the latest release; $TAG cannot supersede it"
fi

# two platforms can update the text at the same time with what each of them saw, so check it again after writing
written=
for attempt in 1 2 3 4 5; do
  body "$(assets)" > body.md
  if [ "$(cat body.md)" = "$written" ]; then
    break
  fi
  gh release edit "$TAG" --notes-file body.md > /dev/null
  written=$(cat body.md)
done
echo "published $(name "$platform") in $TAG"
