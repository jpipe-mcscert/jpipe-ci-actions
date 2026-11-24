# Changelog

All notable changes to this project are documented in this file. One version covers both
the GitHub Action and the GitLab CI/CD component.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`jobs` runs independent steps together**: up to that many at a time, or one per CPU
  with `auto`, when the argument does not order them (jPipe Runner's `--jobs`, 4.4.0 or
  later). Empty by default: one step at a time. The step libraries must be written for it
  (#13).
- **`verbosity` sets what jPipe Runner logs**: `quiet`, `normal` (the default), `verbose`
  or `debug`. The log, in the comment and the artifact, then says which Python ran the
  steps, the libraries a glob matched and `sys.path`, which a library that cannot be
  imported (`JP020`) needs. A re-run with debug logging turned on uses `debug`, unless the
  workflow set a verbosity (#9).

### Changed
- **⚠️ Breaking: the action installs jPipe Runner 4.5.0 by default**, where it installed
  4.0.0. `runner-version: 4.0.0` keeps the old one. The runner's breaking changes since
  4.0.0 reach workflows that leave `runner-version` unset (README, *Upgrading from 1.x*):
  - the paths an evidence observes are relative to the step library's file, no longer to
    `working-directory`: a library outside it fails with `JP019` until its paths are
    rewritten (4.1.0);
  - a composed model compiled by jPipe older than 4.0.0 stops with `JP016`, and must be
    compiled again (4.3.0);
  - `JP027` is a new warning, which `strict: true` counts as an error (4.3.0).

  From now on the default follows the runner's semantic version: a minor or patch release
  of the runner moves it in a minor or patch release of the action, and a major one in a
  major release ([ADR-0003](docs/adr/0003-the-default-runner-follows-semver.md), #11).
- **The pull request keeps one comment per workflow and artifact name.** Each run added
  a new comment, and a pull request pushed ten times collected ten reports. A run now
  edits the comment the action wrote before, found by a hidden marker on its first line,
  and `comment-id` is that comment's id; GitHub keeps the earlier reports in the
  comment's edit history. The comment, and the job summary, end with the commit and the
  run they report, and a run whose commit is no longer the pull request's head leaves
  the comment alone. Comments written by earlier releases have no marker: the first run
  after upgrading adds one more comment, which later runs edit (#10).

### Fixed
- **A PNG, PDF, JPEG or GIF diagram shows its status symbols** (✔ ✘ ◌ ⚠), which jPipe
  Runner draws since 4.1.0. Graphviz draws them with a font installed on the machine, and
  without one that has them they came out as empty boxes: for a format other than `svg`,
  the action now installs DejaVu Sans when it is missing (#14).
- **A report the action cannot read no longer costs the comment.** The action reads the
  JSON report of schema versions 1.x and 2.x, those of jPipe Runner 4.0 to 4.5. A report
  of another version, from a future runner, or one that is not JSON, crashed the comment
  step: the pull request got no comment, and the job no summary. The comment now gives
  the exit code, says that the action cannot read the report, and shows the text report
  and the log; the job gets a warning, and `verdict` is empty (#8).
- **The action runs in a matrix without `artifact-name`.** Every job of a matrix took
  the default artifact name, `jpipe-runner-<job>`, and an artifact name must be unique
  in a run, so every job after the first failed to upload its reports. In a matrix, the
  default name now ends with the job's index in it: `jpipe-runner-<job>-<index>`. A job
  outside a matrix keeps its name. **A matrix job that uploaded alone**, its action step
  skipped in the other jobs, **is renamed** too: a later job that downloads
  `jpipe-runner-<job>` must set `artifact-name`. So must a reusable workflow called from
  a matrix, which sees only its own job (#22).
- **`runner-version` installs post and dev releases from PyPI**, such as `4.4.0.post1`
  or `4.5.0.dev1`. It took them for git refs of jpipe-runner's repository, which do not
  exist, and the installation failed.

### Removed
- **⚠️ Breaking: the `dataflow` input and output.** jPipe Runner 4.1.0 removed
  `--dataflow`: it draws one diagram, the dataflow, and `--diagram` draws it. With
  `runner-version` set to 4.1.0 or later, `dataflow: true` made the runner refuse its
  command line (exit code 2), and the job failed without a report. With runner 4.1.0 or
  later, the `diagram` output is the dataflow; with 4.0.0, it is the argument alone, and
  the dataflow is no longer drawn. A workflow that still sets `dataflow` gets GitHub's
  "unexpected input" warning, and one that reads `outputs.dataflow` gets nothing (#6,
  #12).

## [1.0.0] - 2026-11-11

### Added
- **The GitHub Action runs jPipe Runner 4**
  ([ADR-0002](docs/adr/0002-runner-4-github-first.md)). It is named *jPipe CI*; *jPipe
  Runner* stays the name of the v3 action, in jpipe-runner's repository (up to v3.6.0).
  It moves here from jpipe-runner's root, where it ran jPipe Runner 3
  (jpipe-mcscert/jpipe-runner#130), and is rebuilt on the runner's JSON report
  (jpipe-mcscert/jpipe-runner#132). It installs the runner (`runner-version`: a PyPI
  release, `4.0.0` by default, or a git ref of its repository), runs a justification
  against its step libraries, fails the job with the runner's exit code, and reports: a
  pull request comment with the verdict, the elements that did not pass and why, every
  diagnostic with its fix, and the text report; the same as the job's summary; and the
  reports and diagrams as an artifact. `embed-image` commits the diagram to a branch and
  shows it in the comment, from a private repository too.
- Inputs: `justification`, `library`, `python-path`, `working-directory`, `strict`,
  `dry-run`, `diagram-format`, `dataflow`, `python-executable`, `runner-version`,
  `artifact-name`, `comment`, `embed-image`, `image-repo`, `image-branch`, `image-path`,
  `image-commit-message`, `github-token`, `github-readonly-token`. Outputs: `result`,
  `verdict`, `report`, `diagram`, `dataflow`, `comment-id`. The README maps the inputs of
  jpipe-runner's v3 action to these.

### Not yet
- The GitLab CI/CD component is still a scaffold, and does not mirror the action's inputs.
