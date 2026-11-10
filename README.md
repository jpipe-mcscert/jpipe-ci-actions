# jpipe-ci-actions

Run [jPipe](https://www.jpipe.org) justifications in CI, on GitHub Actions or GitLab CI.

> [!WARNING]
> **Scaffold.** The repository has its structure but no behaviour yet: the action and
> the component only print a notice. The runner action moves here from
> [jpipe-runner](https://github.com/jpipe-mcscert/jpipe-runner) in
> [jpipe-runner#130](https://github.com/jpipe-mcscert/jpipe-runner/issues/130).

## Usage

### GitHub Actions

```yaml
- uses: actions/checkout@v7
- uses: jpipe-mcscert/jpipe-ci-actions@<version>
  with:
    working-directory: path/to/model
```

### GitLab CI

```yaml
include:
  - component: gitlab.com/mcscert/jpipe-ci-actions/jpipe-runner@<version>
    inputs:
      working-directory: path/to/model
```

Both take the same inputs and are released under the same version number.

## Repository layout

| Path | Role |
|------|------|
| `action.yml` | The GitHub Action |
| `templates/jpipe-runner.yml` | The GitLab CI/CD component, the counterpart of `action.yml` |
| `scripts/` | Behaviour shared by both, free of platform-specific variables |
| `.github/workflows/ci.yml` | Lints the repository and runs the action from the checkout |
| `.github/workflows/mirror.yml` | Pushes `main` and the tags to the GitLab mirror |
| `.gitlab-ci.yml` | Runs on the GitLab mirror: tests the component, publishes Catalog releases |
| `docs/adr/` | Architecture decision records |

[ADR-0001](docs/adr/0001-one-repository-two-front-ends.md) explains the layout and the
rules that keep the two front ends in step.

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
   Seed it once from a clone, as a Maintainer, with GitHub's `main` (the same commit, so
   the mirror only adds to it later):
   `git fetch origin && git push git@gitlab.com:mcscert/jpipe-ci-actions.git origin/main:refs/heads/main`
4. On GitLab, *Settings → Repository → Protected branches*: in the `main` row, open
   *Allowed to push and merge* and tick the deploy key. Do the same under *Protected
   tags* if any tag is protected.
5. On GitHub, *Settings → Secrets and variables → Actions*: add the private key
   `gitlab_mirror` as the secret `GITLAB_MIRROR_SSH_KEY`. Then delete both files.
6. On GitLab, *Settings → General → Visibility*: turn on **CI/CD Catalog project**.
7. Run *Mirror to GitLab* once by hand (*Actions → Mirror to GitLab → Run workflow*, on
   `main`) to check that the mirror can push.

Releasing: push a tag of the form `1.2.3` (no `v` prefix: the GitLab CI/CD Catalog only
publishes plain semantic versions). The mirror pushes it to GitLab, whose pipeline
publishes the component.

## License

[MIT](LICENSE).
