"""Write a JUnit XML report of a run, for test report widgets.

    python junit.py REPORT JUNIT --result CODE

reads jpipe-runner's JSON report and writes JUNIT: one test case per element of the
justification, which fails or is skipped with its reason and its diagnostics, and one for
validation, which errors when nothing could run, and lists the diagnostics about no
element. A run that exited with CODE other than 0, without a report this action reads or
with no element failed, gets one more test case that errors with the exit code: a widget
never shows a run that failed the job as one that passed.

GitLab shows the file in the merge request (`artifacts:reports:junit`); on GitHub, a test
report action can read it. Platform-neutral, standard library only (docs/adr/0001).
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from typing import Any

import report as reports

# Characters XML 1.0 cannot hold, even escaped: lone surrogates among them, which a
# step's reason can hold when it read bytes that are not UTF-8.
_UNSAFE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _text(value: str) -> str:
    return _UNSAFE.sub("\ufffd", value)


def _diagnostic(diagnostic: dict[str, Any]) -> str:
    where = f" [{diagnostic['element']}]" if diagnostic["element"] else ""
    line = f"{diagnostic['code']} {diagnostic['severity']}{where}: {diagnostic['message']}"
    return f"{line}\n  Fix: {diagnostic['fix']}" if diagnostic["fix"] else line


def _case(suite: ET.Element, name: str, classname: str) -> ET.Element:
    return ET.SubElement(suite, "testcase", name=_text(name), classname=_text(classname))


def _outcome(case: ET.Element, tag: str, message: str, details: list[str]) -> None:
    """Mark ``case`` failed, errored or skipped, with ``message`` and ``details``. The
    message is in the text too: GitLab shows the text, not the attribute."""
    outcome = ET.SubElement(case, tag, message=_text(message))
    outcome.text = _text("\n".join([message, *details]))


def document(report: dict[str, Any] | None, result: int, unreadable: str = "") -> ET.Element:
    """The JUnit document of a run that exited with ``result``."""
    name = (report or {}).get("justification") or "jpipe-runner"
    root = ET.Element("testsuites", name="jpipe-runner")
    suite = ET.SubElement(root, "testsuite", name=_text(name))
    if report is None:
        why = unreadable or "it wrote no report: see the job log"
        message = f"jpipe-runner exited with code {result}; {why}"
        _outcome(_case(suite, "jpipe-runner", name), "error", message, [])
        return _counted(root, suite)

    diagnostics = report["diagnostics"]
    ids = {element["id"] for element in report["elements"]}
    general = [_diagnostic(d) for d in diagnostics if d["element"] not in ids]
    validation = _case(suite, "validation", name)
    if report["verdict"] == "invalid":
        _outcome(validation, "error", "nothing ran", [_diagnostic(d) for d in diagnostics])
    elif general:
        ET.SubElement(validation, "system-out").text = _text("\n".join(general))

    not_run = "a dry run calls no step" if report["verdict"] == "valid" else "nothing ran"
    for element in report["elements"]:
        case = _case(suite, f"{element['label']} [{element['id']}]", f"{name}.{element['kind']}")
        # A skip can be reused as well as a pass; a failure is always run again.
        details = [_diagnostic(d) for d in diagnostics if d["element"] == element["id"]]
        if element.get("reused"):
            details.insert(0, "reused from the baseline of an incremental run")
        status, reason = element["status"], element["reason"] or ""
        if status == "fail":
            _outcome(case, "failure", reason or "failed", details)
        elif status == "skip":
            _outcome(case, "skipped", reason or "skipped", details)
        elif status is None:
            _outcome(case, "skipped", not_run, details)
        elif details:
            ET.SubElement(case, "system-out").text = _text("\n".join(details))
    # A run can fail the job with no element failed: a strict run that skipped, or a
    # report written but not the diagram. The widget must not show it as a success.
    if result != 0 and not any(
        case.find(tag) is not None for case in suite for tag in ("failure", "error")
    ):
        why = "a strict run fails a skipped justification" if report["strict"] else "see the job log"
        message = f"jpipe-runner exited with code {result}; {why}"
        _outcome(_case(suite, "jpipe-runner", name), "error", message, [])
    return _counted(root, suite)


def _counted(root: ET.Element, suite: ET.Element) -> ET.Element:
    """Set the counts JUnit readers expect on the suite and the root."""
    cases = suite.findall("testcase")
    counts = {
        "tests": len(cases),
        "failures": sum(1 for case in cases if case.find("failure") is not None),
        "errors": sum(1 for case in cases if case.find("error") is not None),
        "skipped": sum(1 for case in cases if case.find("skipped") is not None),
    }
    for element in (suite, root):
        for key, count in counts.items():
            element.set(key, str(count))
    return root


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Write a JUnit XML report of a run.")
    parser.add_argument("report", help="jpipe-runner's JSON report; one that is not there is no report")
    parser.add_argument("junit", help="the JUnit XML file to write")
    parser.add_argument("--result", type=int, required=True, help="jpipe-runner's exit code")
    options = parser.parse_args(argv)
    unreadable = ""
    try:
        report = reports.load(options.report)
    except reports.Unreadable as error:
        report, unreadable = None, f"{error}"
    tree = ET.ElementTree(document(report, options.result, unreadable))
    ET.indent(tree)
    tree.write(options.junit, encoding="utf-8", xml_declaration=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
