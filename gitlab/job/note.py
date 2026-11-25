"""Post the run on the merge request, as a note the next run of the job edits.

    python note.py COMMENT

posts COMMENT, comment.py's Markdown, on the merge request of a merge request pipeline,
or edits the note the job posted before. The GitLab counterpart of the action's comment on
GitHub; the component's job runs it (templates/jpipe-runner.yml).

Environment: JPIPE_NOTE_TOKEN, a token with the api scope (CI_JOB_TOKEN cannot post
notes), which the job gives this script alone; and GitLab's CI_API_V4_URL,
CI_MERGE_REQUEST_PROJECT_ID (or CI_PROJECT_ID), CI_MERGE_REQUEST_IID, CI_JOB_NAME,
CI_COMMIT_SHA and CI_MERGE_REQUEST_SOURCE_BRANCH_SHA. It never fails the job: what it
cannot do, it warns about.

GitLab's alone, standard library only: the template carries it, as it carries scripts/
(docs/adr/0004).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class GitLab:
    """GitLab's REST API, as the token sees it."""

    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token

    def call(self, method: str, path: str, body: dict[str, str] | None = None) -> tuple[Any, str]:
        """The JSON GitLab answers, and the page after it, if any."""
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"{self._url}{path}", data=data, method=method)
        request.add_header("PRIVATE-TOKEN", self._token)
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return (json.loads(text) if text else None), response.headers.get("X-Next-Page", "")

    def every(self, path: str) -> list[Any]:
        """Every item of a paginated list."""
        items, page = [], "1"
        while page:
            separator = "&" if "?" in path else "?"
            batch, page = self.call("GET", f"{path}{separator}per_page=100&page={page}")
            items.extend(batch)
        return items


def warn(message: str) -> None:
    print(f"warning: {message}")


def post(gitlab: GitLab, notes: str, marker: str, body: str, head: str, mr: str) -> None:
    """Post ``body`` on the merge request, or edit the note this job posted before."""
    # Pipelines of successive pushes can end out of order: a run whose commit is no longer
    # the merge request's head leaves the note to the run of the head.
    current = gitlab.call("GET", mr)[0]["sha"]
    if head and current != head:
        print(f"No note: the merge request's head is now {current}, whose run reports it")
        return
    # Only a note of the token's own user is edited, never one someone else wrote with the
    # marker. A token that cannot say who it is posts a new note.
    try:
        user = gitlab.call("GET", "/user")[0]["id"]
    except (urllib.error.URLError, ValueError, KeyError, TypeError) as error:
        warn(f"posting a new note: the token's user is unknown ({error})")
        user = None
    mine = [
        note
        for note in (gitlab.every(f"{notes}?sort=asc&order_by=created_at") if user else [])
        if note["author"]["id"] == user
        and not note.get("system")
        # A note edited on the web may end its lines with \r\n.
        and note["body"].replace("\r", "").startswith(marker)
    ]
    if mine:
        gitlab.call("PUT", f"{notes}/{mine[0]['id']}", {"body": body})
        print(f"Edited note {mine[0]['id']} on the merge request")
    else:
        note = gitlab.call("POST", notes, {"body": body})[0]
        print(f"Posted note {note['id']} on the merge request")
    # Two runs at once can each find no note, and each post one: the oldest is kept, and
    # the others go, so the merge request is back to one.
    for extra in mine[1:]:
        try:
            gitlab.call("DELETE", f"{notes}/{extra['id']}")
            print(f"Deleted note {extra['id']}, a second note of this job")
        except urllib.error.URLError as error:
            warn(f"could not delete note {extra['id']}: {error}")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: note.py COMMENT", file=sys.stderr)
        return 2
    env = os.environ
    token, iid = env.get("JPIPE_NOTE_TOKEN", ""), env.get("CI_MERGE_REQUEST_IID", "")
    if not token:
        print("No note: gitlab-token is not set")
        return 0
    if not iid:
        print("No note: not a merge request pipeline")
        return 0
    # One note per job, edited by each later run of it: the marker that starts it finds
    # it. Encoded, so that no job name ends the HTML comment.
    marker = f"<!-- jpipe-ci-actions {urllib.parse.quote(env.get('CI_JOB_NAME', ''), safe='')} -->"
    body = f"{marker}\n{Path(argv[0]).read_text(encoding='utf-8')}"
    # A merge request from a fork runs in the fork: the merge request is the target's.
    project = env.get("CI_MERGE_REQUEST_PROJECT_ID") or env.get("CI_PROJECT_ID", "")
    project = urllib.parse.quote(project, safe="")
    mr = f"/projects/{project}/merge_requests/{urllib.parse.quote(iid, safe='')}"
    # In a merged results pipeline, the commit is the merge's: the head is the source's.
    head = env.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA") or env.get("CI_COMMIT_SHA", "")
    try:
        post(GitLab(env.get("CI_API_V4_URL", ""), token), f"{mr}/notes", marker, body, head, mr)
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as error:
        warn(f"could not post the note on the merge request: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
