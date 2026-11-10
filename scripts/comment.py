"""Write the Markdown that reports a run, from the JSON report jpipe-runner wrote.

    python comment.py --result 1 --report report.json --text report.txt --log log.txt \
        [--image-url URL] [--artifact-url URL] > comment.md

The comment says what the run concluded (the verdict), how many elements ended how, the
elements that did not pass and why, and every diagnostic with its fix; then the diagram,
and the text report and the log, folded. It reads the JSON report, the runner's contract
for programs, rather than its text output, whose layout may change. When there is no
report (a usage error, or a file that could not be read), it shows the runner's log.

Platform-neutral, standard library only (docs/adr/0001).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# GitHub refuses a comment longer than 65,536 characters; the folded text report and log
# are cut to leave room for the rest.
_FOLDED_LIMIT = 20_000

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
) -> str:
    """The comment for a run that exited with ``result`` and wrote ``report``, if any."""
    parts = [_headline(result, report)]
    if report is not None:
        parts.append(_summary(report))
        parts.extend(section for section in (_stopped(report), _diagnostics(report)) if section)
    parts.append(_diagram(result, image_url, artifact_url))
    parts.append(_folded("Text report", text))
    parts.append(_folded("Log", log))
    return "\n\n".join(part for part in parts if part) + "\n"


def _headline(result: int, report: dict[str, Any] | None) -> str:
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
    return "\n".join(["| | Element | Id | Why |", "|---|---|---|---|", *rows])


def _diagnostics(report: dict[str, Any]) -> str:
    items = []
    for diagnostic in report["diagnostics"]:
        where = f" [`{diagnostic['element']}`]" if diagnostic["element"] else ""
        item = f"- `{diagnostic['code']}` {diagnostic['severity']}{where}: {diagnostic['message']}"
        if diagnostic["fix"]:
            item += f"\n  Fix: {diagnostic['fix']}"
        items.append(item)
    return "\n".join(items)


def _diagram(result: int, image_url: str, artifact_url: str) -> str:
    link = f"[Download the diagram]({artifact_url})" if artifact_url else ""
    if not image_url:
        return link
    image = f"![The justification, with the run over it]({image_url})"
    body = "\n\n".join(part for part in (image, link) if part)
    if result == 0:
        return f"<details><summary>Diagram</summary>\n\n{body}\n\n</details>"
    return body


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
    options = parser.parse_args(argv)
    report_text = _read(options.report)
    report = json.loads(report_text) if report_text else None
    sys.stdout.write(
        render(
            result=options.result,
            report=report,
            text=_read(options.text),
            log=_read(options.log),
            image_url=options.image_url,
            artifact_url=options.artifact_url,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
