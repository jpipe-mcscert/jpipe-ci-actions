#!/usr/bin/env bash
# Install jpipe-runner into the Python that will run it.
#
# Environment:
#   JPIPE_PYTHON          Python interpreter to install into (default: python3)
#   JPIPE_RUNNER_VERSION  A release on PyPI (4.0.0), or a git ref of the jpipe-runner
#                         repository (main, a branch, a commit), installed from GitHub.
#                         Default: 4.0.0.
#
# Platform-neutral: no GitHub or GitLab variables (docs/adr/0001).
set -euo pipefail

python="${JPIPE_PYTHON:-python3}"
version="${JPIPE_RUNNER_VERSION:-4.0.0}"
repository="https://github.com/jpipe-mcscert/jpipe-runner.git"

# A PEP 440 release (4.0.0, 4.1.0rc1) comes from PyPI; anything else is a git ref.
if [[ "$version" =~ ^[0-9]+(\.[0-9]+)*((a|b|rc)[0-9]+)?$ ]]; then
  requirement="jpipe-runner==${version}"
else
  requirement="jpipe-runner @ git+${repository}@${version}"
fi

echo "Installing ${requirement} with $("$python" --version 2>&1) ($python)"
# -q -q keeps pip's progress out of the log; warnings and errors still print.
"$python" -m pip install -q -q --disable-pip-version-check --no-input "$requirement"
"$python" -m jpipe_runner --version
