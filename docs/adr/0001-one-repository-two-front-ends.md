# 1. One repository, two front ends

Date: 2026-11-09

## Status

Accepted

## Context

jPipe justifications are checked in CI. Users run either GitHub Actions or GitLab CI,
and both should get the same feature from the same release. The GitHub Action used to
live in `jpipe-runner` (`action.yml` at its root); jpipe-mcscert/jpipe-runner#130 moves
it out.

The two platforms package reusable CI differently:

- A **GitHub Action** is an `action.yml` in a GitHub repository. Placed at the root, it
  is used as `jpipe-mcscert/jpipe-ci-actions@<ref>` and can be listed on the Marketplace.
  Its steps can call files shipped with it through `github.action_path`.
- A **GitLab CI/CD component** is a `templates/<name>.yml` file (or
  `templates/<name>/template.yml`) in a GitLab project marked as a Catalog resource. It
  is used as `include: component: <host>/<project>/<name>@<version>`. It is inlined into
  the consumer's pipeline, so its job runs in the consumer's project and **cannot see the
  component's other files**.

## Decision

- One repository hosts both front ends: `action.yml` for GitHub, `templates/` for GitLab.
- **GitHub is the source of truth.** The GitLab project is a pull mirror of it; nobody
  pushes to GitLab directly.
- Front ends stay thin. Behaviour shared by both lives in `scripts/`, written against
  plain environment variables, with no platform variables. Each front end maps its inputs
  to those variables. Platform-only features (a PR comment on GitHub, an MR note on
  GitLab) stay in their front end.
- **Inputs are kept in parity**: every input of `action.yml` has a counterpart of the
  same name in `templates/jpipe-runner.yml`, with the same default, except for inputs
  that only make sense on one platform.
- Release tags are **plain semantic versions** (`1.0.0`, no `v`), because the GitLab
  CI/CD Catalog only publishes those. One tag on GitHub reaches GitLab through the mirror
  and serves both platforms. GitLab users can pin a partial version (`@1`); GitHub users
  pin the full tag, or a moving major tag if we add one (it must not look like a semantic
  version, so the GitLab release job ignores it).
- `.github/workflows/ci.yml` tests the action on GitHub; `.gitlab-ci.yml` tests the
  component on the mirror (it includes itself at `$CI_COMMIT_SHA`) and publishes the
  Catalog release when a release tag arrives.

## Open question

How `scripts/` reaches a GitLab job. The candidates are a container image that bundles the
scripts (and the runner) and is used as the job's `image`, or downloading the scripts at
the component's own version (`$[[ component.sha ]]`). Until this is settled, the GitLab
template inlines its commands.

## Consequences

- One CHANGELOG and one version number cover both platforms.
- A change to one front end is incomplete until the other matches it, or the difference
  is documented as platform-only.
- The mirror needs one-time manual setup on GitLab (see README, *Maintainers*), and
  pipelines for mirror updates must be enabled, or tags will not be released there.
