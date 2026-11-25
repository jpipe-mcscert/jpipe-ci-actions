"""Run the GitLab component's job here, as GitLab would, to test it before it reaches GitLab.

    python gitlab/run-job.py [--input NAME=VALUE ...]

GitLab runs the component only on the mirror, which gets main once a release is merged
(docs/adr/0001). This runs the job of templates/jpipe-runner.yml in the current
directory, a checkout of this repository standing for the consumer's project: it gives
each input its value, or its default, as GitLab interpolates them; sets the job's
variables, with the CI/CD variables the job reads; and runs the job's script in one bash,
under `set -eo pipefail`, as GitLab's runner does. It exits with the job's exit code.

It needs PyYAML. It stands in for GitLab only as far as the job reads it: the interpolation
of whole values and of text, variables with or without `expand`, and the script.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "jpipe-runner.yml"
INPUT = re.compile(r"\$\[\[\s*inputs\.([\w-]+)\s*\]\]")
VARIABLE = re.compile(r"\$(?:\{(\w+)\}|(\w+))")


def inputs(spec: dict[str, Any], given: dict[str, str]) -> dict[str, str]:
    """Each input's value: the one given, or its default. Refuses what GitLab refuses."""
    values = {}
    for name in given.keys() - spec.keys():
        raise SystemExit(f"unknown input: {name}")
    for name, declared in spec.items():
        if name in given:
            value = given[name]
        elif "default" in declared:
            value = declared["default"]
        else:
            raise SystemExit(f"missing required input: {name}")
        if "options" in declared and value not in declared["options"]:
            raise SystemExit(f"input {name}: {value!r} is not one of {declared['options']}")
        values[name] = value
    return values


def interpolated(node: Any, values: dict[str, str]) -> Any:
    """``node`` with every input in it: a whole value is replaced, text is substituted."""
    if isinstance(node, dict):
        return {interpolated(k, values): interpolated(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [interpolated(item, values) for item in node]
    if isinstance(node, str):
        if (whole := INPUT.fullmatch(node.strip())) is not None:
            return values[whole.group(1)]
        return INPUT.sub(lambda match: str(values[match.group(1)]), node)
    return node


def main(argv: list[str]) -> int:
    given = {}
    while argv:
        if argv[0] != "--input" or len(argv) < 2 or "=" not in argv[1]:
            print("usage: run-job.py [--input NAME=VALUE ...]", file=sys.stderr)
            return 2
        name, _, value = argv[1].partition("=")
        given[name] = value
        argv = argv[2:]
    header, body = yaml.safe_load_all(TEMPLATE.read_text(encoding="utf-8"))
    values = inputs(header["spec"]["inputs"], given)
    ((name, job),) = interpolated(body, values).items()

    project = Path.cwd()
    env = dict(os.environ)
    # The commit: as the environment gives it, or as git does; a checkout without git
    # has none.
    sha = env.get("CI_COMMIT_SHA") or (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        ).stdout.strip()
        if shutil.which("git")
        else ""
    )
    env.update(CI_PROJECT_DIR=str(project), CI_COMMIT_SHA=sha or "0" * 40, CI_JOB_NAME=name)
    for variable, declared in job.get("variables", {}).items():
        # Every variable of the template says whether GitLab expands it: with `expand:
        # false`, its value is passed as it is; otherwise, $VAR and ${VAR} in it are
        # replaced with their values, or nothing.
        if not isinstance(declared, dict) or not isinstance(declared.get("expand"), bool):
            raise SystemExit(f"variable {variable}: declare whether it expands (expand:)")
        value = str(declared["value"])
        if declared["expand"]:
            value = VARIABLE.sub(lambda match: env.get(match.group(1) or match.group(2), ""), value)
        env[variable] = value

    print(f"Running job {name!r} in {job['image']!r} (here: this machine)", flush=True)
    script = "set -eo pipefail\n" + "\n".join(job["script"])
    code = subprocess.run(["bash", "-c", script], env=env, cwd=project, check=False).returncode
    print(f"Job {name!r} exited with code {code}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
