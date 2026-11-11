#!/usr/bin/env bash
# Print a URL a pull request comment can show a committed diagram from (GitHub only).
#
# A public repository's raw URL can be fetched anonymously, as GitHub's image proxy does.
# A private repository has no such URL: the contents API gives a download URL that holds
# a token, which expires. It works because the proxy caches the image when the comment is
# first shown; a later fetch may fail. On any doubt the repository is taken to be private,
# since a public raw URL into a private repository is a broken image. Prints nothing when
# no URL can be found, and the comment links to the artifact instead.
#
# Environment:
#   GITHUB_TOKEN  Token that can read IMAGE_REPO
#   IMAGE_REPO    Repository (owner/name) the diagram was committed to
#   IMAGE_BRANCH  Branch it was committed to
#   IMAGE_PATH    Its path in that branch
set -uo pipefail

api="https://api.github.com"
auth="Authorization: Bearer ${GITHUB_TOKEN:-}"

# Percent-encoded, so that a space, '#', '?' or '&' in a name cannot break the URL. In a
# path, each segment is encoded and its slashes kept; in a query, the slashes are encoded.
segments() { jq -rn --arg value "$1" '$value | split("/") | map(@uri) | join("/")'; }
query() { jq -rn --arg value "$1" '$value | @uri'; }

private="true"
if repository="$(curl -fsS -H "$auth" "${api}/repos/${IMAGE_REPO}")"; then
  [[ "$(jq -r '.private' <<< "$repository")" == "false" ]] && private="false"
else
  echo "::warning::Could not read the visibility of ${IMAGE_REPO}: taking it to be private" >&2
fi

if [[ "$private" == "false" ]]; then
  echo "https://raw.githubusercontent.com/${IMAGE_REPO}/$(segments "$IMAGE_BRANCH")/$(segments "$IMAGE_PATH")"
  exit 0
fi

# The contents API may not serve a file pushed a moment ago: try a few times.
for attempt in 1 2 3; do
  if contents="$(curl -fsS -H "$auth" "${api}/repos/${IMAGE_REPO}/contents/$(segments "$IMAGE_PATH")?ref=$(query "$IMAGE_BRANCH")")"; then
    url="$(jq -r '.download_url // empty' <<< "$contents")"
    if [[ -n "$url" ]]; then
      echo "$url"
      exit 0
    fi
  fi
  (( attempt < 3 )) && sleep 3
done
echo "::warning::Could not get a URL for ${IMAGE_PATH} on ${IMAGE_BRANCH}: the comment links to the artifact instead" >&2
exit 0
