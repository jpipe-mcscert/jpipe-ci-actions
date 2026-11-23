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
  may change: `scripts/comment.py` builds the comment from it.
- **Testing is running the action**, not unit tests: `ci.yml` runs it on `example/` with
  the real runner, and with hostile inputs to guard against command injection. Don't add
  tests of what the runner or GitHub do, nor of the comment's exact wording.
- **Never interpolate a GitLab input into `script`.** `$[[ inputs.x ]]` becomes shell
  source there, so `$(...)` in a value runs. Pass it through a job variable with
  `expand: false` and quote the variable. Same on GitHub: pass `${{ inputs.x }}` to a
  `run:` step through `env:`, never inline.
- **Write GitLab `script` lines as block scalars (`- |`).** A plain YAML line containing
  `: ` parses as a mapping, and GitLab then refuses the whole pipeline.
- Shell scripts (`scripts/`, `github/`) must pass `shellcheck`; workflows must pass
  `actionlint`.
- Keep `CHANGELOG.md` (Keep a Changelog) in step; one entry covers both platforms.

## Branches and pull requests

This repository follows the jPipe workflow, described once for the organization in
[CONTRIBUTING.md](https://github.com/jpipe-mcscert/.github/blob/main/CONTRIBUTING.md):
`dev` is the default and integration branch, work branches are cut from it and come back
through a pull request, and a release is a pull request from a `release/X.Y.Z` branch,
cut from `dev`, into `main`, after which `main` is merged back into `dev`. Its *For AI
assistants* section applies here. Specific to this repository:

- `ci.yml` runs on pushes to `main` and `dev`, and on every pull request.
- Only `main` and the tags reach the GitLab mirror (`mirror.yml`); `dev` and work
  branches stay on GitHub. The GitLab pipeline therefore tests the component only once a
  release is merged into `main`.
- **Release tags are plain semver** (`1.2.3`, no `v`), unlike the org guide's `vX.Y.Z`:
  the GitLab CI/CD Catalog rejects anything else, and `release.yml` runs on plain semver
  tags only. The pushed tag is the release: `release.yml` adds the GitHub release
  page, and the mirror carries the tag to GitLab, which publishes it to the Catalog. The
  steps are in the README, *Releasing*.
