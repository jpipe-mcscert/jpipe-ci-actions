"""scripts/comment.py, on reports jpipe-runner 4 wrote.

The fixtures are real: the JSON and text reports of runs of jpipe-runner's release
example (passing, failing, a dry run, a refused model) and of a step that raised.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

import comment  # noqa: E402


def _report(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _render(name: str, result: int, **options: str) -> str:
    return comment.render(
        result=result,
        report=_report(name),
        text=(FIXTURES / f"{name}.txt").read_text(encoding="utf-8"),
        log=options.pop("log", ""),
        **options,
    )


class Comment(unittest.TestCase):
    def test_a_justification_that_holds(self) -> None:
        markdown = _render("pass", 0)

        self.assertTrue(markdown.startswith("### ✔ The justification `release` holds (exit code 0)"))
        self.assertIn("4 elements (4 passed).", markdown)
        self.assertNotIn("| Why |", markdown)

    def test_a_justification_that_fails_says_what_did_not_pass_and_why(self) -> None:
        markdown = _render("fail", 1)

        self.assertIn("### ✘ The justification `release` does not hold (exit code 1)", markdown)
        self.assertIn("4 elements (1 failed, 2 skipped, 1 passed).", markdown)
        self.assertIn(
            "| ✘ | The test suite passes | `release:e1` | mock/junit.xml: 2 tests failed |", markdown
        )
        self.assertIn(
            "| - | All release gates pass | `release:s` | not run: release:e1 did not pass |",
            markdown,
        )

    def test_a_step_that_raised_shows_its_diagnostic_and_fix(self) -> None:
        markdown = _render("raised", 1)

        self.assertIn("2 elements (1 failed, 1 skipped); 1 diagnostic (1 error).", markdown)
        self.assertIn("- `JP022` error [`S1`]: the step raised ZeroDivisionError", markdown)
        self.assertIn("  Fix: Return Fail(reason) when the check does not hold", markdown)

    def test_a_dry_run_is_valid(self) -> None:
        markdown = _render("valid", 0)

        self.assertIn("is valid: a dry run, no step was called (exit code 0)", markdown)

    def test_a_refused_model_could_not_run(self) -> None:
        markdown = _render("invalid", 3)

        self.assertIn("### ✘ The justification could not run (exit code 3)", markdown)
        self.assertIn("- `JP001` error: not JSON", markdown)

    def test_a_run_without_a_report_shows_the_log(self) -> None:
        markdown = comment.render(
            result=4, report=None, text="", log="jpipe-runner: error: x.json: No such file"
        )

        self.assertTrue(markdown.startswith("### ✘ jpipe-runner stopped before it could report"))
        self.assertIn("<summary>Log</summary>", markdown)
        self.assertIn("x.json: No such file", markdown)

    def test_the_text_report_is_folded(self) -> None:
        markdown = _render("fail", 1)

        self.assertIn("<details><summary>Text report</summary>\n\n```text\nJustification: release", markdown)

    def test_the_diagram_is_folded_when_the_justification_holds(self) -> None:
        markdown = _render("pass", 0, image_url="https://img/x.svg", artifact_url="https://a/1")

        self.assertIn(
            "<details><summary>Diagram</summary>\n\n"
            "![The justification, with the run over it](https://img/x.svg)\n\n"
            "[Download the diagram](https://a/1)\n\n</details>",
            markdown,
        )

    def test_the_diagram_is_shown_when_it_does_not(self) -> None:
        markdown = _render("fail", 1, image_url="https://img/x.svg")

        self.assertIn("\n\n![The justification, with the run over it](https://img/x.svg)\n\n", markdown)
        self.assertNotIn("<summary>Diagram</summary>", markdown)

    def test_without_an_image_the_artifact_is_linked(self) -> None:
        markdown = _render("pass", 0, artifact_url="https://a/1")

        self.assertIn("[Download the diagram](https://a/1)", markdown)
        self.assertNotIn("![", markdown)

    def test_a_reason_cannot_break_the_table(self) -> None:
        report = _report("fail")
        report["elements"][0]["reason"] = "a | b\nc"

        markdown = comment.render(result=1, report=report, text="", log="")

        self.assertIn("| a \\| b c |", markdown)

    def test_a_long_text_report_is_cut(self) -> None:
        markdown = comment.render(result=0, report=_report("pass"), text="x" * 50_000, log="")

        self.assertLess(len(markdown), 30_000)
        self.assertIn("(cut: see the job's log)", markdown)


if __name__ == "__main__":
    unittest.main()
