# 4. The GitLab component carries scripts/ inline

Date: 2026-11-24

## Status

Accepted. It answers [ADR-0001](0001-one-repository-two-front-ends.md)'s open question,
and ends [ADR-0002](0002-runner-4-github-first.md)'s scaffold (#17).

## Context

The action's steps call `scripts/` (`install.sh`, `run.sh`, `report.py`, …) from
`github.action_path`: GitHub downloads the whole repository at the action's version. A
GitLab component is one file, `templates/jpipe-runner.yml`, which GitLab inlines into the
consumer's pipeline. Its job runs in a clone of the consumer's project, where none of
this repository's files are. GitLab's documentation asks for components to be
"self-contained and not depend on external files".

The options weighed:

1. **An image built at each tag**, holding `scripts/` and the runner. The scripts match
   the component's version, but the job's image must also hold the packages the step
   libraries import: consumers would lose their own image, or install their packages
   into ours, and the release pipeline would build and publish an image.
2. **Downloading `scripts/` when the job starts**, at the component's commit
   (`$[[ component.sha ]]`, GitLab 18.7). The template stays small, but the job needs
   gitlab.com at run time, the project's path must be written into the template (GitLab
   gives a component no value for it), and unauthenticated archive downloads from
   gitlab.com are limited to 5 a minute, which busy shared runners can reach.
3. **A Python package** holding the scripts, installed beside the runner: one more
   package to publish, or the same download as option 2. `install.sh` and `run.sh` are
   bash.
4. **Inlining**, as the scaffold did by hand.

## Decision

- **The template carries a copy of `scripts/`**, which the job writes to a temporary
  directory, `$JPIPE_SCRIPTS`, and then runs as the action does. Each file is a quoted
  here-document in the first item of the job's `script`, between two markers.
- **The copy is generated, never edited**: `gitlab/inline.py` writes it from `scripts/`,
  and `ci.yml` fails when the template's copy differs (`inline.py --check`). The logic
  stays in `scripts/` alone. The generator refuses a file that holds `$[[`, which GitLab
  would interpolate.
- **GitHub's CI runs the component's job** before GitLab does, in the job's default
  image: `gitlab/run-job.py` gives the template its inputs as GitLab does, and runs the
  job's script. GitLab runs the component only once a release reaches `main` (ADR-0001).
- `gitlab/` holds this tooling. Behaviour that is GitLab's alone stays in the template,
  as GitHub's stays in `action.yml` and `github/`.

## Consequences

- The job needs nothing but its image, bash and Python, and the network for PyPI: no
  registry, no download from this repository, no rate limit. The copy always matches the
  version the consumer pinned, and works from a copy of the component on another GitLab.
- The template is long (about 30 KB, most of it the copy). A change to `scripts/` comes
  with its regenerated template in the same commit, or CI fails.
- A component input reaches the scripts as a job variable with `expand: false`, under the
  name the scripts read (`JPIPE_*`): the parity rule of ADR-0001 holds again.
