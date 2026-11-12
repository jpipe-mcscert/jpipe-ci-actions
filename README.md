# jpipe-ci-actions

Run [jPipe](https://www.jpipe.org) justifications in CI, on GitHub Actions or GitLab CI.

Run [jPipe](https://www.jpipe.org) justifications in CI with
[jPipe Runner](https://github.com/jpipe-mcscert/jpipe-runner): the action runs a
justification against its Python step libraries, fails the job when it does not hold,
and reports which claims hold on the pull request, in the job summary, and as an
artifact.

> [!NOTE]
> **GitHub first.** The GitHub Action runs jPipe Runner 4. The GitLab CI/CD component
> (`templates/jpipe-runner.yml`) is still a scaffold that runs nothing
> ([ADR-0002](docs/adr/0002-runner-4-github-first.md)).

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
why, every diagnostic with its fix, and the text report. The same comment is the job's
summary, and the JSON report, the text report, the log and the diagrams are uploaded as
an artifact.

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

Not yet: the component is a scaffold ([ADR-0002](docs/adr/0002-runner-4-github-first.md)).

```yaml
include:
  - component: gitlab.com/mcscert/jpipe-ci-actions/jpipe-runner@<version>
    inputs:
      working-directory: path/to/model
```

### Inputs

| Input | Default | |
|---|---|---|
| `justification` | required | The justification: the JSON file the jPipe compiler writes, relative to `working-directory`. |
| `library` | required | The step libraries, one per line: Python files, or globs of files. |
| `python-path` | | Directories the step libraries import modules from, one per line. |
| `working-directory` | `.` | Directory to run from: the paths the evidence observes are relative to it. |
| `strict` | `false` | Count validation warnings as errors, and fail a skipped justification. |
| `dry-run` | `false` | Validate the step libraries against the justification, and call no step. |
| `diagram-format` | `svg` | Format of the diagram of the run: `svg`, `png`, `pdf`, `dot`, `jpg`, `jpeg` or `gif`; empty for none. |
| `dataflow` | `false` | Also draw the dataflow diagram: the files and variables the steps declare. |
| `python-executable` | | Python interpreter to run jPipe Runner with; by default the action sets up Python 3.11. |
| `runner-version` | `4.0.0` | jPipe Runner to install: a release on PyPI (`4.0.0`), or a git ref of its repository. |
| `artifact-name` | `jpipe-runner-<job>` | Name of the artifact; set it to run the action twice in one job. |
| `comment` | `true` | Comment on the pull request. |
| `embed-image` | `false` | Commit the diagram to `image-branch`, and show it in the comment. |
| `image-repo` | this repository | Repository (`owner/name`) the diagram is committed to. |
| `image-branch` | `jpipe-runner-diagrams` | Branch the diagram is committed to, created as an orphan. |
| `image-path` | `diagrams` | Folder the diagram is committed to, under one named after this repository. |
| `image-commit-message` | | Message of the commit that adds the diagram. |
| `github-token` | `github.token` | Token that comments (`pull-requests: write`) and commits the diagram (`contents: write`). |
| `github-readonly-token` | `github-token` | Read-only token that gets the diagram's URL in a private `image-repo`. |

### Outputs

| Output | |
|---|---|
| `result` | jPipe Runner's exit code: 0 holds, 1 fails, 2 usage error, 3 nothing could run, 4 a file could not be read or written. |
| `verdict` | `pass`, `fail`, `skip`, `valid` (a dry run) or `invalid`; empty when there is no report. |
| `report` | Path to the JSON report, if one was written. |
| `diagram`, `dataflow` | Paths to the diagrams, if they were drawn. |
| `comment-id` | ID of the pull request comment, if one was posted. |

**Embedding the diagram.** GitHub shows a comment's images through a proxy that fetches
them anonymously, and an artifact needs a login: so `embed-image` commits the diagram to
a branch, and shows it from there. For a private repository, the URL holds a token that
expires: the image may stop showing after a while, and the comment always links to the
artifact as well.

### Coming from jpipe-runner's action

The action that lived at jpipe-runner's root (`uses: jpipe-mcscert/jpipe-runner@v3.x`)
ran jPipe Runner 3, and keeps working at its tags, up to v3.6.0; on the GitHub
Marketplace it is *jPipe Runner*, and this one is *jPipe CI*. This one runs jPipe
Runner 4: change the `uses:` line, port the step libraries
([migration guide](https://github.com/jpipe-mcscert/jpipe-runner/blob/main/docs/migration-v3-v4.md)),
and rename the inputs: `jd_file` is `justification`, `working_directory` is
`working-directory`, `python_path` is `python-path`, `python_exec_path` is
`python-executable`, `dry_run` is `dry-run`, `embed_image` and the `image_*` inputs are
`embed-image` and `image-*`, and `version` is `runner-version`. `variable` and
`config-file` are gone with the runner's options, and `diagram` and `format` gave way to
`diagram-format` and `dataflow`.

## Repository layout

| Path | Role |
|------|------|
| `action.yml` | The GitHub Action |
| `templates/jpipe-runner.yml` | The GitLab CI/CD component, the counterpart of `action.yml` |
| `scripts/` | Behaviour shared by both, free of platform-specific variables |
| `github/` | Behaviour of the GitHub Action alone: committing the diagram, finding its URL |
| `example/` | A justification and its step library, which CI runs the action on |
| `.github/workflows/ci.yml` | Lints the repository, runs the action on the example, and checks that hostile inputs run nothing |
| `.github/workflows/mirror.yml` | Pushes `main` and the tags to the GitLab mirror |
| `.github/workflows/release.yml` | Drafts a release, run by hand: see Releasing |
| `.gitlab-ci.yml` | Runs on the GitLab mirror: tests the component, publishes Catalog releases |
| `docs/adr/` | Architecture decision records |

[ADR-0001](docs/adr/0001-one-repository-two-front-ends.md) explains the layout and the
rules that keep the two front ends in step; [ADR-0002](docs/adr/0002-runner-4-github-first.md)
why the action runs jPipe Runner 4, and GitHub comes first.

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

1. Merge a pull request that turns `## [Unreleased]` in `CHANGELOG.md` into
   `## [1.2.3] - YYYY-MM-DD`, and opens a new, empty `## [Unreleased]` above it.
2. Once CI has passed on `main`, run *Actions → Release → Run workflow* on `main`, with
   the version. It checks the version, the changelog, the action's metadata against the
   Marketplace's rules, and CI's result, then drafts a release whose notes are the
   version's section of the changelog. Nothing is published yet.
3. Open the draft (the run's summary links it), click **Edit**, tick **Publish this
   Action to the GitHub Marketplace**, and click **Publish release**. Only the web
   interface can list a release on the Marketplace, which is why the workflow stops at a
   draft.

Publishing creates the tag: *Mirror to GitLab* pushes it to GitLab, whose pipeline
publishes the component to the CI/CD Catalog.

## License

[MIT](LICENSE).
