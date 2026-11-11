#!/usr/bin/env bash
# Commit a diagram to a branch of a GitHub repository, so that a pull request comment can
# show it (GitHub only).
#
# GitHub shows a comment's images through a proxy that fetches them anonymously, so an
# artifact, which needs a login, cannot be shown: the diagram is committed to a branch,
# whose raw URL can (github/image-url.sh). The branch is an orphan, created on first use,
# so that it shares no history with the project.
#
# Environment:
#   GITHUB_TOKEN          Token allowed to push to IMAGE_REPO
#   IMAGE_FILE            The diagram to commit
#   IMAGE_REPO            Repository (owner/name) to commit to
#   IMAGE_BRANCH          Branch to commit to
#   IMAGE_FOLDER          Folder of the branch the diagram goes in
#   IMAGE_COMMIT_MESSAGE  Message of the commit
set -euo pipefail

: "${GITHUB_TOKEN:?a token that can push to $IMAGE_REPO is required to embed the diagram}"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

git clone --quiet --no-checkout \
  "https://x-access-token:${GITHUB_TOKEN}@github.com/${IMAGE_REPO}.git" "$workdir/repo"
cd "$workdir/repo"
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

if git fetch --quiet origin "$IMAGE_BRANCH" 2> /dev/null; then
  git checkout --quiet -B "$IMAGE_BRANCH" FETCH_HEAD
else
  echo "Creating the branch ${IMAGE_BRANCH} in ${IMAGE_REPO}"
  git checkout --quiet --orphan "$IMAGE_BRANCH"
  git rm -rf --quiet --cached . > /dev/null 2>&1 || true
fi

mkdir -p "$IMAGE_FOLDER"
cp -- "$IMAGE_FILE" "$IMAGE_FOLDER/"
git add -- "$IMAGE_FOLDER/$(basename "$IMAGE_FILE")"
if git diff --cached --quiet; then
  echo "The diagram is already on ${IMAGE_BRANCH}: nothing to commit."
  exit 0
fi
git commit --quiet -m "$IMAGE_COMMIT_MESSAGE"

# Another job may push to the branch at the same time: rebase on it, and try again.
for attempt in 1 2 3; do
  if git push --quiet origin "HEAD:refs/heads/${IMAGE_BRANCH}"; then
    echo "Committed $(basename "$IMAGE_FILE") to ${IMAGE_REPO}@${IMAGE_BRANCH}:${IMAGE_FOLDER}"
    exit 0
  fi
  echo "The push was refused (attempt ${attempt}/3); rebasing on ${IMAGE_BRANCH}"
  git pull --quiet --rebase origin "$IMAGE_BRANCH"
done
echo "::error::Could not push the diagram to ${IMAGE_REPO}@${IMAGE_BRANCH}"
exit 1
