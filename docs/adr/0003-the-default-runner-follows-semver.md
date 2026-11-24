# 3. The default runner follows the runner's semantic version

Date: 2026-11-24

## Status

Accepted

## Context

`runner-version` installs a jPipe Runner release from PyPI, `4.0.0` by default in 1.x
([ADR-0002](0002-runner-4-github-first.md)). A workflow that leaves it unset runs whatever
runner the action's release pins, so moving the default changes what that workflow runs:
the default is part of the action's interface, as much as its inputs are.

The runner follows semantic versioning, with one exception. 4.1.0 broke consumers of
4.0.0: it removed `--dataflow`, and made the paths an evidence observes relative to the
step library's file. `--dataflow` should have been removed before 4.0.0 was released.
4.3.0 added an error, `JP016`, for a composed model compiled by an older jPipe, and a
warning, `JP027`, which a strict run counts as an error.

`ci.yml` runs the action with the default runner and with the latest release on PyPI,
every week as well as on every change (#7).

## Decision

- **The default moves as the runner's version does.** A minor or patch release of the
  runner is a minor or patch release of the action that moves the default to it; a major
  release of the runner is a major release of the action.
- **2.0.0 absorbs the breaking changes of 4.0.0 to 4.5.0** and moves the default to
  4.5.0. Those of 4.1.0 are the runner's exception, and those of 4.3.0 count as such too,
  since they come in the same jump; the CHANGELOG and the README (*Upgrading from 1.x*) list
  them for users.
- **The CI job on the latest runner says when a move is safe** for the action itself:
  when it passes on a new release, the default can follow. Whether the release is safe for
  users' libraries is the runner's CHANGELOG's to say.

## Consequences

- A user who pins the action's major version gets the runner's minor and patch releases
  with the action's, and no runner break without an action major.
- A runner minor release that breaks its consumers, as 4.1.0 and 4.3.0 did, cannot be the
  default until the action's next major release, unless it is recorded here as another
  exception.
- `runner-version` still pins any release, or a git ref, for a user who wants another one.
