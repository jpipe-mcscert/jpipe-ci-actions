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
  - component: $CI_SERVER_FQDN/<group>/jpipe-ci-actions/jpipe-runner@<version>
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
| `.gitlab-ci.yml` | Runs on the GitLab mirror: tests the component, publishes Catalog releases |
| `docs/adr/` | Architecture decision records |

[ADR-0001](docs/adr/0001-one-repository-two-front-ends.md) explains the layout and the
rules that keep the two front ends in step.

## Maintainers

GitHub is the source of truth. The GitLab project is a pull mirror and is never pushed to
directly.

One-time setup of the mirror, on GitLab:

1. Create the project, then under *Settings → Repository → Mirroring repositories* add
   `https://github.com/jpipe-mcscert/jpipe-ci-actions.git` as a **pull** mirror.
2. Enable *Trigger pipelines for mirror updates*, so tags pushed to GitHub run
   `.gitlab-ci.yml` and get released.
3. Under *Settings → General → Visibility*, turn on **CI/CD Catalog project**.

Releasing: push a tag of the form `1.2.3` (no `v` prefix: the GitLab CI/CD Catalog only
publishes plain semantic versions). The mirror picks it up and publishes the component.

## License

[MIT](LICENSE).
