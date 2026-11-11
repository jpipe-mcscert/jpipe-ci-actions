# 2. The action runs jpipe-runner 4, on GitHub first

Date: 2026-11-10

## Status

Accepted

## Context

The GitHub Action moves here from jpipe-runner's root (jpipe-mcscert/jpipe-runner#130,
#131). There it drove jpipe-runner 3: its inputs were v3's options (`variable`,
`config-file`, a `diagram` pattern, `format`), and its pull request comment was cut out
of v3's console output by removing its ASCII banners, which any change to them broke
(jpipe-mcscert/jpipe-runner#132).

jpipe-runner 4, a rewrite, is released on PyPI (4.0.0). Its command line differs
from v3's, and it writes a JSON report, a versioned contract for programs, with an exit
code a pipeline can act on (0 holds, 1 fails, 2 usage, 3 nothing ran, 4 I/O). v3 stays
usable in CI as `jpipe-mcscert/jpipe-runner@v3.6.0`, an immutable tag.

ADR-0001 asks for the GitLab component to keep its inputs in parity with the action, and
leaves open how `scripts/` reaches a GitLab job.

## Decision

- **The action runs jpipe-runner 4 only.** Its first release is not a move of the v3
  action pinned to runner 3, which would have been rewritten for v4 weeks later.
  `runner-version` installs a release from PyPI (`4.0.0` by default), or a git ref from
  the runner's repository, to try a change before it is released.
- **The comment is built from the JSON report** (`scripts/comment.py`), never from the
  runner's text output, whose layout may change. The text report and the log are shown
  folded, for people.
- **Inputs are named in kebab-case**, as GitHub's own actions and GitLab inputs are:
  `justification`, `library`, `python-path`, `working-directory`, `embed-image`, …
- **GitHub-only behaviour lives in `github/`**: committing the diagram to a branch, and
  finding a URL a comment can show it from. `scripts/` stays platform-neutral: it reads
  `JPIPE_*` variables and writes its outputs to a file the front end names.
- **The GitLab component stays a scaffold for this release.** The inputs of `action.yml`
  are not mirrored in `templates/jpipe-runner.yml` yet, a departure from ADR-0001's parity
  rule that ends when the component runs the runner, which also settles how `scripts/`
  reaches a GitLab job.

## Consequences

- A v3 workflow changes its `uses:` line and its inputs at once: jpipe-runner's migration
  guide maps them.
- The comment, the job summary and the outputs (`result`, `verdict`, `report`, …) follow
  the JSON report's schema, not the runner's text.
- Until the GitLab component catches up, the README says that it does nothing yet.
