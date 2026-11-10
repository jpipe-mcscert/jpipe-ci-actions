# jpipe-ci-actions — Project Guide for Claude

One repository, two front ends for running jPipe justifications in CI: a GitHub Action
(`action.yml`) and a GitLab CI/CD component (`templates/jpipe-runner.yml`). GitHub is the
source of truth; `.github/workflows/mirror.yml` pushes `main` and the tags to
`gitlab.com/mcscert/jpipe-ci-actions`, which is never pushed to directly. Read
[ADR-0001](docs/adr/0001-one-repository-two-front-ends.md) before changing the layout.

## Rules

- **Parity.** A change to an input of `action.yml` is not done until
  `templates/jpipe-runner.yml` has the same change (same name, same default), unless the
  input only makes sense on one platform; say so in a comment next to it.
- **Shared logic goes in `scripts/`**, reading plain environment variables (`JPIPE_*`).
  No `GITHUB_*` or `CI_*` variables there; platform-specific steps stay in their front
  end, and their scripts in `github/` (later `gitlab/`).
- **For now the GitLab component is a scaffold** that does not mirror the action's inputs
  ([ADR-0002](docs/adr/0002-runner-4-github-first.md)): the parity rule above applies
  again once it runs the runner.
- **The action reads jPipe Runner's JSON report**, never its text output, whose layout
  may change: `scripts/comment.py` builds the comment from it. Test fixtures in
  `tests/fixtures/` are real reports; regenerate them with the runner when its report
  schema changes.
- `python -m unittest discover -s tests` tests the scripts; CI runs it.
- **Never interpolate a GitLab input into `script`.** `$[[ inputs.x ]]` becomes shell
  source there, so `$(...)` in a value runs. Pass it through a job variable with
  `expand: false` and quote the variable. Same on GitHub: pass `${{ inputs.x }}` to a
  `run:` step through `env:`, never inline.
- **Write GitLab `script` lines as block scalars (`- |`).** A plain YAML line containing
  `: ` parses as a mapping, and GitLab then refuses the whole pipeline.
- **Release tags are plain semver** (`1.2.3`, no `v`): the GitLab CI/CD Catalog rejects
  anything else.
- Shell scripts (`scripts/`, `github/`) must pass `shellcheck`; workflows must pass
  `actionlint`.
- Keep `CHANGELOG.md` (Keep a Changelog) in step; one entry covers both platforms.
