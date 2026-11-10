#!/usr/bin/env bash
# Platform-neutral entry point shared by the GitHub Action and the GitLab component.
#
# Scaffold only: prints a notice and succeeds. The real logic arrives with the
# extraction of the runner action (jpipe-mcscert/jpipe-runner#130).
#
# Keep this script free of GitHub- or GitLab-specific variables: each front end maps
# its own inputs to environment variables before calling it.
set -euo pipefail

echo "jpipe-ci-actions: scaffold, no behaviour yet (running in $(pwd))."
