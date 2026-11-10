"""scripts/run.sh and scripts/install.sh, run against a stub Python.

The stub records the arguments it is given, one per line, and writes what jpipe-runner
would write: the JSON report and the diagrams it is asked for. So each test can check the
exact command the script builds, and the outputs it reports, without installing
jpipe-runner. The command is an array, never evaluated: a value with spaces or shell
syntax reaches the runner as one literal argument, and runs nothing.
"""

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "run.sh"
INSTALL = ROOT / "scripts" / "install.sh"

# Called as `<stub> -m jpipe_runner <arguments>` by run.sh, or `<stub> -m pip ...` and
# `<stub> -m jpipe_runner --version` by install.sh.
STUB = r"""#!/usr/bin/env bash
if [[ "$1" == "-c" ]]; then exec python3 "$@"; fi
printf '%s\n' "$@" >> "$ARGUMENTS"
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[$i]}" in
    --report) printf '{"verdict": "%s"}' "${STUB_VERDICT:-pass}" > "${args[$((i + 1))]}" ;;
    --diagram|--dataflow) : > "${args[$((i + 1))]}" ;;
  esac
done
echo "the text report"
echo "a log line" >&2
exit "${STUB_EXIT:-0}"
"""


class Scripts(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.stub = self.tmp / "python"
        self.stub.write_text(STUB)
        self.stub.chmod(self.stub.stat().st_mode | stat.S_IXUSR)
        self.arguments = self.tmp / "arguments.txt"
        self.outputs = self.tmp / "outputs.txt"
        self.output_dir = self.tmp / "out"

    def _run(self, **variables: str) -> subprocess.CompletedProcess[str]:
        environment = {
            **os.environ,
            "ARGUMENTS": str(self.arguments),
            "JPIPE_PYTHON": str(self.stub),
            "JPIPE_JUSTIFICATION": "release.json",
            "JPIPE_LIBRARY": "steps.py",
            "JPIPE_OUTPUT_DIR": str(self.output_dir),
            "JPIPE_OUTPUTS": str(self.outputs),
            **variables,
        }
        return subprocess.run(
            ["bash", str(RUN)], env=environment, cwd=self.tmp, capture_output=True, text=True
        )

    def _argv(self) -> list[str]:
        return self.arguments.read_text().splitlines()

    def _outputs(self) -> dict[str, str]:
        lines = self.outputs.read_text().splitlines()
        return dict(line.split("=", 1) for line in lines)

    # --- run.sh: the command -----------------------------------------------------------

    def test_the_command_runs_the_justification_with_its_libraries_and_report(self) -> None:
        self._run()

        out = self.output_dir
        self.assertEqual(
            self._argv(),
            ["-m", "jpipe_runner", "--library", "steps.py", "--report", f"{out}/report.json",
             "--colour", "never", "release.json"],
        )

    def test_each_line_is_one_argument_kept_as_it_is(self) -> None:
        self._run(
            JPIPE_LIBRARY="steps.py\n\n'checks/**/*.py'\nmy steps.py\n",
            JPIPE_PYTHON_PATH="src\nhelpers dir",
        )

        argv = self._argv()
        self.assertEqual(argv.count("--library"), 3)
        for value in ("'checks/**/*.py'", "my steps.py", "helpers dir"):
            self.assertIn(value, argv)
        self.assertEqual(argv.count("--python-path"), 2)

    def test_a_value_with_shell_syntax_is_passed_literally_and_runs_nothing(self) -> None:
        payload = "steps.py'; touch INJECTED #$(touch INJECTED2)"
        self._run(JPIPE_LIBRARY=payload, JPIPE_JUSTIFICATION="x.json; touch INJECTED3")

        self.assertIn(payload, self._argv())
        self.assertIn("x.json; touch INJECTED3", self._argv())
        self.assertEqual(sorted(p.name for p in self.tmp.glob("INJECTED*")), [])

    def test_a_glob_reaches_the_runner_unexpanded(self) -> None:
        (self.tmp / "a.py").touch()
        self._run(JPIPE_LIBRARY="*.py")

        self.assertIn("*.py", self._argv())
        self.assertNotIn("a.py", self._argv())

    def test_strict_and_dry_run_are_flags(self) -> None:
        self._run(JPIPE_STRICT="true", JPIPE_DRY_RUN="true")

        self.assertIn("--strict", self._argv())
        self.assertIn("--dry-run", self._argv())

    def test_the_diagrams_are_named_after_the_justification_and_the_suffix(self) -> None:
        self._run(JPIPE_DIAGRAM_FORMAT="svg", JPIPE_DATAFLOW="true", JPIPE_SUFFIX="abc123")

        out = self.output_dir
        argv = self._argv()
        self.assertEqual(argv[argv.index("--diagram") + 1], f"{out}/release-abc123.svg")
        self.assertEqual(argv[argv.index("--dataflow") + 1], f"{out}/release-abc123-dataflow.svg")
        self.assertEqual(self._outputs()["diagram"], f"{out}/release-abc123.svg")
        self.assertEqual(self._outputs()["dataflow"], f"{out}/release-abc123-dataflow.svg")

    def test_no_diagram_without_a_format(self) -> None:
        self._run(JPIPE_DIAGRAM_FORMAT="", JPIPE_DATAFLOW="true")

        self.assertNotIn("--diagram", self._argv())
        self.assertNotIn("--dataflow", self._argv())
        self.assertEqual(self._outputs()["diagram"], "")

    # --- run.sh: the outputs -----------------------------------------------------------

    def test_the_outputs_say_what_the_run_wrote(self) -> None:
        process = self._run(STUB_VERDICT="fail", STUB_EXIT="1")

        outputs = self._outputs()
        out = self.output_dir
        self.assertEqual(process.returncode, 0, "the runner's code is an output, not the script's")
        self.assertEqual(outputs["result"], "1")
        self.assertEqual(outputs["verdict"], "fail")
        self.assertEqual(outputs["report"], f"{out}/report.json")
        self.assertEqual((out / "report.txt").read_text(), "the text report\n")
        self.assertEqual((out / "log.txt").read_text(), "a log line\n")
        self.assertIn("the text report", process.stdout)

    def test_a_run_that_wrote_no_report_has_no_verdict(self) -> None:
        silent = self.tmp / "silent"
        silent.write_text("#!/usr/bin/env bash\necho 'usage: ...' >&2\nexit 2\n")
        silent.chmod(silent.stat().st_mode | stat.S_IXUSR)
        self._run(JPIPE_PYTHON=str(silent), JPIPE_DIAGRAM_FORMAT="svg")

        outputs = self._outputs()
        self.assertEqual(outputs["result"], "2")
        self.assertEqual(outputs["verdict"], "")
        self.assertEqual(outputs["report"], "")
        self.assertEqual(outputs["diagram"], "")

    # --- install.sh --------------------------------------------------------------------

    def _install(self, version: str) -> list[str]:
        environment = {
            **os.environ,
            "ARGUMENTS": str(self.arguments),
            "JPIPE_PYTHON": str(self.stub),
            "JPIPE_RUNNER_VERSION": version,
        }
        subprocess.run(["bash", str(INSTALL)], env=environment, check=True, capture_output=True)
        return self._argv()

    def test_a_release_is_installed_from_pypi(self) -> None:
        self.assertIn("jpipe-runner==4.0.0", self._install("4.0.0"))

    def test_a_pre_release_is_installed_from_pypi(self) -> None:
        self.assertIn("jpipe-runner==4.1.0rc1", self._install("4.1.0rc1"))

    def test_a_git_ref_is_installed_from_github(self) -> None:
        self.assertIn(
            "jpipe-runner @ git+https://github.com/jpipe-mcscert/jpipe-runner.git@main",
            self._install("main"),
        )


if __name__ == "__main__":
    unittest.main()
