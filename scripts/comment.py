"""Write the Markdown that reports a run, from the JSON report jpipe-runner wrote.

    python comment.py --result 1 --report report.json --text report.txt --log log.txt \
        [--image-url URL] [--artifact-url URL] [--commit SHA] [--run-url URL] \
        [--baseline TEXT] > comment.md

The comment says what the run concluded (the verdict), how many elements ended how, what
an incremental run ran again and why, the elements that did not pass and why, and every diagnostic with its fix; then the diagram,
the text report and the log, folded, and the commit and the run it reports. A comment that
later runs edit must say which run it shows. It reads the JSON report, the runner's contract
for programs, rather than its text output, whose layout may change. When there is no
report (a usage error, or a file that could not be read), it shows the runner's log; when
the report has a schema this action does not read (report.py), it says so, and shows the
text report and the log.

Platform-neutral, standard library only (docs/adr/0001).
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import report as reports

# GitHub refuses a comment longer than 65,536 characters, and the pull request then gets
# no report. Every part that grows with the model or the run has its own share, so that
# together they stay under it, with room left for the headline, the summary and the links:
# the elements that did not pass and the diagnostics are listed up to 12,000 characters
# each, what an incremental run ran again up to 8,000, and the folded text report and log
# are cut at 12,000 each.
_LISTED_LIMIT = 12_000
_SELECTION_LIMIT = 8_000
_FOLDED_LIMIT = 12_000

_HEADLINES = {
    "pass": "✔ {subject} holds",
    "fail": "✘ {subject} does not hold",
    "skip": "{subject} was skipped",
    "valid": "✔ {subject} is valid: a dry run, no step was called",
    "invalid": "✘ {subject} could not run",
}


def render(
    *,
    result: int,
    report: dict[str, Any] | None,
    text: str,
    log: str,
    image_url: str = "",
    artifact_url: str = "",
    unreadable: str = "",
    commit: str = "",
    run_url: str = "",
    baseline: str = "",
) -> str:
    """The comment for a run that exited with ``result`` and wrote ``report``, if any.

    ``unreadable`` says why a report that was written could not be read, and ``baseline``
    names the baseline of an incremental run for people, such as a commit.
    """
    parts = [_headline(result, report, unreadable)]
    if report is not None:
        parts.append(_summary(report))
        parts.append(_selection(report, baseline or "the baseline"))
        parts.extend(section for section in (_stopped(report), _diagnostics(report)) if section)
    parts.append(_diagram(result, image_url, artifact_url))
    parts.append(_folded("Text report", text))
    parts.append(_folded("Log", log))
    parts.append(_origin(commit, run_url))
    return "\n\n".join(part for part in parts if part) + "\n"


def _headline(result: int, report: dict[str, Any] | None, unreadable: str) -> str:
    if unreadable:
        return f"### jpipe-runner exited with code {result}\n\nIt ran, but {unreadable}."
    if report is None:
        return f"### ✘ jpipe-runner stopped before it could report (exit code {result})"
    # A refused model has no name: it could not be read.
    name = report["justification"]
    subject = f"The justification `{name}`" if name else "The justification"
    return f"### {_HEADLINES[report['verdict']].format(subject=subject)} (exit code {result})"


def _summary(report: dict[str, Any]) -> str:
    """The counts, in the order and the words of the runner's own summary."""
    summary = report["summary"]
    ended = [
        f"{summary[key]} {label}"
        for key, label in (("fail", "failed"), ("skip", "skipped"), ("pass", "passed"))
        if summary[key]
    ]
    line = _counted(summary["elements"], "element")
    if ended:
        line += f" ({', '.join(ended)})"
    found = [
        _counted(summary[key], label)
        for key, label in (("errors", "error"), ("warnings", "warning"))
        if summary[key]
    ]
    if found:
        line += f"; {_counted(summary['errors'] + summary['warnings'], 'diagnostic')}"
        line += f" ({', '.join(found)})"
    if report["strict"]:
        line += "; a strict run"
    return line + "."


def _selection(report: dict[str, Any], baseline: str) -> str:
    """What an incremental run ran again, and why; nothing for a full run."""
    selection = report.get("selection")
    if not selection:
        return ""
    rerun = selection["rerun"]
    if not rerun:
        return f"Incremental run: nothing changed since {baseline}, every element reused."
    if not any(element.get("reused") for element in report["elements"]):
        reasons = set(rerun.values())
        if reasons == {"there is no baseline"}:
            return "Incremental run without a baseline: every element ran."
        if len(reasons) == 1:  # such as the baseline's model, or no baseline at all
            return f"Incremental run: every element ran again ({reasons.pop()})."
        head = f"Incremental run: every element ran again since {baseline}."
    else:
        total = report["summary"]["elements"]
        head = (
            f"Incremental run: {len(rerun)} of {total} elements ran again, "
            f"the rest reused from {baseline}."
        )
    labels = {element["id"]: element["label"] for element in report["elements"]}
    rows = [
        f"| {_cell(labels.get(element, ''))} | `{element}` | {_cell(why)} |"
        for element, why in rerun.items()
    ]
    rows, more = _bounded(rows, "element", _SELECTION_LIMIT)
    table = "\n".join(["| Element | Id | Why it ran again |", "|---|---|---|", *rows])
    body = f"{table}\n\n{more}" if more else table
    return f"{head}\n\n<details><summary>What ran again</summary>\n\n{body}\n\n</details>"


def _counted(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _stopped(report: dict[str, Any]) -> str:
    """The elements that did not pass, and why."""
    rows = [
        f"| {'✘' if element['status'] == 'fail' else '-'} | {_cell(element['label'])} "
        f"| `{element['id']}` | {_cell(element['reason'] or '')} |"
        for element in report["elements"]
        if element["status"] in ("fail", "skip")
    ]
    if not rows:
        return ""
    rows, more = _bounded(rows, "element")
    table = "\n".join(["| | Element | Id | Why |", "|---|---|---|---|", *rows])
    return f"{table}\n\n{more}" if more else table


def _diagnostics(report: dict[str, Any]) -> str:
    items = []
    for diagnostic in report["diagnostics"]:
        where = f" [`{diagnostic['element']}`]" if diagnostic["element"] else ""
        item = f"- `{diagnostic['code']}` {diagnostic['severity']}{where}: {diagnostic['message']}"
        if diagnostic["fix"]:
            item += f"\n  Fix: {diagnostic['fix']}"
        items.append(item)
    items, more = _bounded(items, "diagnostic")
    return "\n".join([*items, *([f"\n{more}"] if more else [])])


def _bounded(items: list[str], noun: str, limit: int = _LISTED_LIMIT) -> tuple[list[str], str]:
    """The first ``items`` that fit in ``limit``, and a line saying what was left out."""
    size = 0
    for kept, item in enumerate(items):
        size += len(item) + 1
        if size > limit:
            left = _counted(len(items) - kept, noun)
            return items[:kept], f"… {left} not shown: see the JSON report in the artifact."
    return items, ""


def _diagram(result: int, image_url: str, artifact_url: str) -> str:
    link = f"[Download the diagram]({artifact_url})" if artifact_url else ""
    if not image_url:
        return link
    image = f"![The justification's diagram, with the run over it]({image_url})"
    body = "\n\n".join(part for part in (image, link) if part)
    if result == 0:
        return f"<details><summary>Diagram</summary>\n\n{body}\n\n</details>"
    return body


def _origin(commit: str, run_url: str) -> str:
    """The commit and the run the comment reports."""
    parts = [f"commit `{commit[:12]}`" if commit else "", f"[this run]({run_url})" if run_url else ""]
    parts = [part for part in parts if part]
    return f"<sub>Reported on {' by '.join(parts)}.</sub>" if parts else ""


def _folded(title: str, content: str) -> str:
    content = content.strip("\n")
    if not content:
        return ""
    if len(content) > _FOLDED_LIMIT:
        content = content[:_FOLDED_LIMIT] + "\n… (cut: see the job's log)"
    fence = "````" if "```" in content else "```"
    return f"<details><summary>{title}</summary>\n\n{fence}text\n{content}\n{fence}\n\n</details>"


def _cell(text: str) -> str:
    """``text`` in a Markdown table cell: one line, its pipes escaped."""
    return " ".join(text.split()).replace("|", "\\|")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8") if path and Path(path).is_file() else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--result", type=int, required=True, help="jpipe-runner's exit code")
    parser.add_argument("--report", default="", help="the JSON report, if one was written")
    parser.add_argument("--text", default="", help="the text report")
    parser.add_argument("--log", default="", help="what jpipe-runner logged on stderr")
    parser.add_argument("--image-url", default="", help="a URL the diagram can be shown from")
    parser.add_argument("--artifact-url", default="", help="a URL the diagram can be downloaded from")
    parser.add_argument("--commit", default="", help="the commit the run checked")
    parser.add_argument("--run-url", default="", help="a URL of the CI run")
    parser.add_argument("--baseline", default="", help="the baseline of an incremental run, for people")
    options = parser.parse_args(argv)
    try:
        report, unreadable = reports.load(options.report), ""
    except reports.Unreadable as error:
        report, unreadable = None, str(error)
    sys.stdout.write(
        render(
            result=options.result,
            report=report,
            text=_read(options.text),
            log=_read(options.log),
            image_url=options.image_url,
            artifact_url=options.artifact_url,
            commit=options.commit,
            run_url=options.run_url,
            baseline=options.baseline,
            unreadable=unreadable,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
