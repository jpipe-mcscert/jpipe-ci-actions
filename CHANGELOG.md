# Changelog

All notable changes to this project are documented in this file. One version covers both
the GitHub Action and the GitLab CI/CD component.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **The GitHub Action runs jPipe Runner 4**
  ([ADR-0002](docs/adr/0002-runner-4-github-first.md)). It moves here from
  jpipe-runner's root, where it ran jPipe Runner 3 (jpipe-mcscert/jpipe-runner#130), and
  is rebuilt on the runner's JSON report (jpipe-mcscert/jpipe-runner#132). It installs the
  runner (`runner-version`: a PyPI release, or a git ref, `main` until 4.0.0 is out),
  runs a justification against its step libraries, fails the job with the runner's exit
  code, and reports: a pull request comment with the verdict, the elements that did not
  pass and why, every diagnostic with its fix, and the text report; the same as the job's
  summary; and the reports and diagrams as an artifact. `embed-image` commits the diagram
  to a branch and shows it in the comment, from a private repository too.
- Inputs: `justification`, `library`, `python-path`, `working-directory`, `strict`,
  `dry-run`, `diagram-format`, `dataflow`, `python-executable`, `runner-version`,
  `artifact-name`, `comment`, `embed-image`, `image-repo`, `image-branch`, `image-path`,
  `image-commit-message`, `github-token`, `github-readonly-token`. Outputs: `result`,
  `verdict`, `report`, `diagram`, `dataflow`, `comment-id`. The README maps the inputs of
  jpipe-runner's v3 action to these.

### Not yet
- The GitLab CI/CD component is still a scaffold, and does not mirror the action's inputs.
