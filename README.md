# jpipe-ci-actions

Run [jPipe](https://www.jpipe.org) justifications in CI, on GitHub Actions or GitLab CI.

Run [jPipe](https://www.jpipe.org) justifications in CI with
[jPipe Runner](https://github.com/jpipe-mcscert/jpipe-runner): the action runs a
justification against its Python step libraries, fails the job when it does not hold,
and reports which claims hold. The GitHub Action reports on the pull request, in the job
summary, and as an artifact; the GitLab CI/CD component, in the job log and as the job's
artifacts.

## Usage

### GitHub Actions

```yaml
permissions:
  contents: read
  pull-requests: write # to comment on the pull request

jobs:
  justify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: jpipe-mcscert/jpipe-ci-actions@<version>
        with:
          working-directory: release
          justification: justification.json # compiled with `jpipe process -f JSON`
          library: steps.py
```

The job fails when the justification does not hold, with jPipe Runner's exit code. On a
pull request, the action comments with the verdict, the elements that did not pass and
why, every diagnostic with its fix, and the text report. Later runs edit that comment
rather than add one: the pull request keeps one comment per workflow and artifact name,
which names the commit and the run it reports, and GitHub keeps the earlier reports in
the comment's history. A run whose commit is no longer the pull request's head leaves
the comment alone. Runs that overlap can still finish out of order: to keep the newest,
give the job a `concurrency` group keyed on the pull request, with
`cancel-in-progress: true`. The
same comment is the job's summary, and the JSON report, the text report, the log and the
diagram are uploaded as an artifact.

The step libraries run on the action's Python: by default the action sets up Python
3.11. When they import packages, install those first, and give the action that
interpreter:

```yaml
      - id: python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - uses: jpipe-mcscert/jpipe-ci-actions@<version>
        with:
          justification: justification.json
          library: steps.py
          python-executable: ${{ steps.python.outputs.python-path }}
```

### GitLab CI

The component adds one job, `jpipe-runner`, to the `test` stage:

```yaml
include:
  - component: gitlab.com/mcscert/jpipe-ci-actions/jpipe-runner@<version>
    inputs:
      working-directory: release
      justification: release.json
      library: steps/*.py
```

The job runs in `python:3.11-slim` by default. If the step libraries import packages, give
an image that has them, with bash and Python, as `image`. The job installs jPipe Runner,
and Graphviz with `apt-get` when a diagram needs it. It fails with the runner's exit
code, and keeps the reports, the log and the diagram as the job's artifacts, under
`.jpipe-runner/`, even when it fails. Its JUnit report shows the run in the merge request's
test summary and the pipeline's *Tests* tab: one test case per element, which fails or is
skipped with its reason and diagnostics, and one for validation.

The component's inputs are those of the action, with the same names and defaults, except
the GitHub-only ones (below). GitLab adds three of its own:

| Input | Default | |
|---|---|---|
| `stage` | `test` | Pipeline stage the job runs in. |
| `job-name` | `jpipe-runner` | Name of the job. Include the component once per justification, each with its own `job-name`. |
| `image` | `python:3.11-slim` | Image the job runs in: it needs bash and Python, with the packages the step libraries import. |

GitLab checks the type of an input, and every input here is a string: quote a value YAML
would read otherwise, such as `strict: "true"` or `jobs: "4"`. A job's debug logging (`CI_DEBUG_TRACE`) sets `verbosity` to
`debug`, as a re-run with debug logging does on GitHub. `incremental` needs `baseline` on
GitLab: the component keeps no baseline of its own yet, and runs in full without one.

### Inputs

| Input | Default | |
|---|---|---|
| `justification` | required | The justification: the JSON file the jPipe compiler writes, relative to `working-directory`. |
| `library` | required | The step libraries, one per line: Python files, or globs of files. |
| `python-path` | | Directories the step libraries import modules from, one per line. |
| `working-directory` | `.` | Directory to run from: `justification`, `library` and `python-path` are relative to it. The paths the evidence observes are relative to the step library's file. |
| `strict` | `false` | Count validation warnings as errors, and fail a skipped justification. |
| `dry-run` | `false` | Validate the step libraries against the justification, and call no step. |
| `jobs` | | How many steps to run at a time when the argument does not order them: a number, or `auto` for one per CPU; empty for one at a time. The step libraries must be written for it ([steps that run together](https://github.com/jpipe-mcscert/jpipe-runner/blob/main/docs/authoring.md#steps-that-run-together)): a step that writes a file another evidence observes can fail with `JP019`, now and then. Needs jPipe Runner 4.4.0 or later. |
| `incremental` | `false` | On a pull request, run again only what changed since the base branch's last report, and reuse the rest from it; on a push, run in full and save the report for the pull requests. See [Incremental runs](#incremental-runs). Needs jPipe Runner 4.5.0 or later. |
| `baseline` | | With `incremental`, the JSON report to run from, on any event, relative to `working-directory`, instead of the one a push saved. One that does not exist runs everything. |
| `diagram-format` | `svg` | Format of the diagram of the run: `svg`, `png`, `pdf`, `dot`, `jpg`, `jpeg` or `gif`; empty for none. For a format other than `svg`, the action installs DejaVu Sans if it is missing, for the status symbols (with `apt-get`; elsewhere it warns). |
| `verbosity` | | What jPipe Runner logs: `quiet` (errors only), `normal` (warnings and errors), `verbose` (what the run does, such as the Python that runs the steps) or `debug` (details, such as the libraries a glob matched and `sys.path`). Empty is `normal`, or `debug` on a re-run with debug logging turned on. |
| `python-executable` | | Python interpreter to run jPipe Runner with; by default the action sets up Python 3.11, and the GitLab job runs the image's `python3`. |
| `runner-version` | `4.5.0` | jPipe Runner to install: a release on PyPI (`4.5.0`), or a git ref of its repository. |
| `artifact-name` | `jpipe-runner-<job>` | Name of the artifact; set it to run the action twice in one job. On GitLab, the name of the job's artifacts archive. In a matrix, the default is `jpipe-runner-<job>-<index>`, the job's index in the matrix; name it after a matrix value instead (`jpipe-${{ matrix.os }}`) to tell the artifacts apart, and to keep each job's comment on the pull request when the matrix changes. Set it in a reusable workflow called from a matrix, which sees only its own job. |
| `comment` | `true` | Comment on the pull request, and edit that comment on later runs. GitHub only, as are the inputs below. |
| `embed-image` | `false` | Commit the diagram to `image-branch`, and show it in the comment. |
| `image-repo` | this repository | Repository (`owner/name`) the diagram is committed to. |
| `image-branch` | `jpipe-runner-diagrams` | Branch the diagram is committed to, created as an orphan. |
| `image-path` | `diagrams` | Folder the diagram is committed to, under one named after this repository. |
| `image-commit-message` | | Message of the commit that adds the diagram. |
| `github-token` | `github.token` | Token that comments (`pull-requests: write`) and commits the diagram (`contents: write`). |
| `github-readonly-token` | `github-token` | Read-only token that gets the diagram's URL in a private `image-repo`. |

### Outputs

The outputs are the action's; the GitLab job has its exit code and its artifacts.

| Output | |
|---|---|
| `result` | jPipe Runner's exit code: 0 holds, 1 fails, 2 usage error, 3 nothing could run, 4 a file could not be read or written. |
| `verdict` | `pass`, `fail`, `skip`, `valid` (a dry run) or `invalid`; empty when there is no report, or one whose schema this action does not read. |
| `report` | Path to the JSON report, if one was written. |
| `diagram` | Path to the diagram, if one was drawn. |
| `junit` | Path to the JUnit XML report of the run, in the artifact too: one test case per element, which fails or is skipped with its reason and diagnostics, and one for validation. A test report action can show it. |
| `comment-id` | ID of the pull request comment, if one was posted or edited. |

**Embedding the diagram.** GitHub shows a comment's images through a proxy that fetches
them anonymously, and an artifact needs a login: so `embed-image` commits the diagram to
a branch, and shows it from there. For a private repository, the URL holds a token that
expires: the image may stop showing after a while, and the comment always links to the
artifact as well.

### Incremental runs

With `incremental: true`, jPipe Runner runs again only what changed since a baseline, an
earlier run's JSON report, and takes every other element from it, with the whole
argument's verdict ([how the runner chooses](https://github.com/jpipe-mcscert/jpipe-runner/blob/main/docs/cli.md#incremental-runs)).
The comment says what ran again, and why.

The action keeps the baseline in the GitHub Actions cache, one per workflow file and
artifact name:

- **On a push**, the run is a full one, so that the branch is always checked whole, and
  its report is saved as the baseline of the pull requests into that branch, unless it is
  a dry run, which calls no step.
- **On a pull request**, the run starts from the last baseline of the base branch, or, if
  it has none yet, of the repository's default branch, and saves nothing: a pull request
  cannot write those branches' caches, so a fork cannot plant a baseline. With neither,
  the run is a full one.
- **On another event**, such as a schedule, the run is a full one, and saves nothing.

A dry run calls no step, so `incremental` leaves it as it is: it neither starts from a
baseline nor saves one.

To keep the baseline elsewhere, such as an artifact downloaded from another run, give its
path as `baseline`: the run starts from it on any event, and the action neither restores
nor saves one.

**An incremental run is only as sound as the step libraries' declarations.** A file a step
reads without declaring it is never seen to change, and the element is reused; the full
run of the push that merges the pull request checks it again.

### Upgrading from 1.x

2.0.0 installs jPipe Runner 4.5.0 by default, where 1.x installed 4.0.0. To upgrade the
action without changing runners at first, set `runner-version: 4.0.0`. To use the new
default, check the step libraries and the models against the runner's breaking changes
since 4.0.0 ([CHANGELOG](https://github.com/jpipe-mcscert/jpipe-runner/blob/main/CHANGELOG.md)):

- **The paths an evidence observes are relative to the step library's file** (4.1.0), no
  longer to `working-directory`. A library that is not in `working-directory` fails with
  `JP019`, naming the path it looked for, until its paths are rewritten.
- **A composed model compiled by jPipe older than 4.0.0 must be compiled again** (4.3.0):
  the runner stops with `JP016`.
- **`JP027` is a new warning** (4.3.0): a step that never reads a value it consumes, or an
  artifact it observes. With `strict: true`, a library that ran may now fail.

Three changes concern workflows, whatever the runner:

- **The `dataflow` input and output are gone.** With runner 4.1.0 or later, the runner
  draws one diagram, the dataflow, and the `diagram` output is its path.

- **In a matrix, the default artifact name ends with the job's index**,
  `jpipe-runner-<job>-<index>`. A job that downloads `jpipe-runner-<job>` must set
  `artifact-name`.
- **The action edits its comment on the pull request** rather than adding one per run.
  It does not recognise the comments 1.x wrote: the first run after the upgrade adds one.

### Coming from jpipe-runner's action

The action that lived at jpipe-runner's root (`uses: jpipe-mcscert/jpipe-runner@v3.x`)
ran jPipe Runner 3, and keeps working at its tags, up to v3.6.0; it is named *jPipe
Runner*, and this one *jPipe CI*. This one runs jPipe Runner 4: change the `uses:` line, port the step libraries
([migration guide](https://github.com/jpipe-mcscert/jpipe-runner/blob/main/docs/migration-v3-v4.md)),
and rename the inputs: `jd_file` is `justification`, `working_directory` is
`working-directory`, `python_path` is `python-path`, `python_exec_path` is
`python-executable`, `dry_run` is `dry-run`, `embed_image` and the `image_*` inputs are
`embed-image` and `image-*`, and `version` is `runner-version`. `variable` and
`config-file` are gone with the runner's options, and `diagram` and `format` gave way to
`diagram-format`.

## Repository layout

| Path | Role |
|------|------|
| `action.yml` | The GitHub Action |
| `templates/jpipe-runner.yml` | The GitLab CI/CD component, the counterpart of `action.yml`, with a generated copy of `scripts/` |
| `scripts/` | Behaviour shared by both, free of platform-specific variables |
| `github/` | Behaviour of the GitHub Action alone: committing the diagram, finding its URL |
| `gitlab/` | `inline.py` copies `scripts/` into the component; `run-job.py` runs its job outside GitLab, for CI |
| `example/` | A justification and its step library, which CI runs the action on |
| `.github/workflows/ci.yml` | Lints the repository, runs the action on the example with the default and the latest jPipe Runner (and, without failing, the runner's `dev` branch), runs the inputs the example leaves unset (`jobs`, `verbosity`, a PNG diagram) on the slim image too, and incremental runs, checks that hostile inputs run nothing, and that a pull request keeps one comment; runs the GitLab component's job, and checks that its copy of `scripts/` is current; weekly as well |
| `.github/workflows/mirror.yml` | Pushes `main` and the tags to the GitLab mirror |
| `.github/workflows/release.yml` | Adds the GitHub release page when a version tag is pushed |
| `.gitlab-ci.yml` | Runs on the GitLab mirror: runs the component on the example and with hostile inputs, publishes Catalog releases |
| `docs/adr/` | Architecture decision records |

[ADR-0001](docs/adr/0001-one-repository-two-front-ends.md) explains the layout and the
rules that keep the two front ends in step; [ADR-0002](docs/adr/0002-runner-4-github-first.md)
why the action runs jPipe Runner 4, and GitHub comes first; [ADR-0003](docs/adr/0003-the-default-runner-follows-semver.md)
how its default runner follows the runner's releases; [ADR-0004](docs/adr/0004-the-gitlab-component-carries-scripts-inline.md)
how the GitLab component gets `scripts/`.

## Maintainers

GitHub is the source of truth. [`mirror.yml`](.github/workflows/mirror.yml) pushes `main`
and every tag to [gitlab.com/mcscert/jpipe-ci-actions](https://gitlab.com/mcscert/jpipe-ci-actions),
which is never pushed to directly.

One-time setup of the mirror:

1. Generate a key pair dedicated to the mirror (no passphrase):
   `ssh-keygen -t ed25519 -N "" -C "jpipe-ci-actions mirror" -f gitlab_mirror`
2. On GitLab, *Settings → Repository → Deploy keys*: add `gitlab_mirror.pub` and tick
   **Grant write permissions to this key**.
3. If the GitLab project is empty, it has no `main` yet, so there is nothing to protect.
   Seed it once with GitHub's `main` (the same commit, so the mirror only adds to it
   later), as a GitLab Maintainer, from a clone of the **GitHub** repository (its
   `origin` must be GitHub; a GitLab clone is empty and has nothing to push):
   `git fetch origin && git push git@gitlab.com:mcscert/jpipe-ci-actions.git origin/main:refs/heads/main`
4. On GitLab, *Settings → Repository → Protected branches*: in the `main` row, open
   *Allowed to push and merge* and tick the deploy key. Do the same under *Protected
   tags* if any tag is protected.
5. On GitHub, *Settings → Secrets and variables → Actions*: add the private key
   `gitlab_mirror` as the secret `GITLAB_MIRROR_SSH_KEY`. Then delete both files.
6. On GitLab, *Settings → General → Visibility*: turn on **CI/CD Catalog project**.
7. Run *Mirror to GitLab* once by hand (*Actions → Mirror to GitLab → Run workflow*, on
   `main`) to check that the mirror can push.

### Releasing

One version covers the action and the component. Its tag is plain semver, `1.2.3`, with
no `v`: the GitLab CI/CD Catalog publishes nothing else.

1. Cut `release/1.2.3` from `dev`. On it, turn `## [Unreleased]` in `CHANGELOG.md` into
   `## [1.2.3] - YYYY-MM-DD`, and open a new, empty `## [Unreleased]` above it.
2. Open the release pull request from `release/1.2.3` into `main`. It does not go into
   `dev` first: its diff is the whole release.
3. Once a maintainer has merged it, wait for *Mirror to GitLab* to carry `main` to
   GitLab, and for GitLab's pipeline on it to pass: it is the first to test the
   component since the last release. Then tag the merge commit on `main` and push the
   tag: `git fetch origin && git tag 1.2.3 origin/main && git push origin 1.2.3`.
4. Merge `main` back into `dev`, so that `dev` has the release commit and the next
   release merges cleanly.

The tag is the release. On GitHub the action is usable at it at once
(`uses: jpipe-mcscert/jpipe-ci-actions@1.2.3`), and `release.yml` adds a release page
with the version's section of the changelog. *Mirror to GitLab* pushes the tag to
GitLab, whose pipeline publishes the component to the CI/CD Catalog.

The action is not listed on the GitHub Marketplace. To list a version, edit its release
on GitHub and tick **Publish this Action to the GitHub Marketplace**.

## Contributing

Work follows the jPipe
[contributing guide](https://github.com/jpipe-mcscert/.github/blob/main/CONTRIBUTING.md):
`dev` is the default branch, work branches are cut from it and come back through a pull
request, and `main` holds released code, which reaches it from a release branch.

The GitLab component holds a copy of `scripts/`: after changing a script, run
`python3 gitlab/inline.py` and commit the template with it, or CI fails.

## License

[MIT](LICENSE).
