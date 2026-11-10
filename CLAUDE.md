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
- **Shared logic goes in `scripts/`**, reading plain environment variables. No
  `GITHUB_*` or `CI_*` variables there; platform-specific steps stay in their front end.
- **Release tags are plain semver** (`1.2.3`, no `v`): the GitLab CI/CD Catalog rejects
  anything else.
- Shell scripts must pass `shellcheck`; workflows must pass `actionlint`.
- Keep `CHANGELOG.md` (Keep a Changelog) in step; one entry covers both platforms.
