"""Read the JSON report jpipe-runner wrote, when this action knows its schema.

    python report.py verdict report.json

prints the report's verdict, or nothing, with a warning on stderr, when the report cannot
be read: it is not JSON, or its schema has a major version this action does not read.
comment.py reads the report through ``load``.

Within a major version, a minor one only adds fields, and a new major version may rename
or remove one (jpipe-runner's docs/report-schema.md, Versioning). The fields this action
reads are in every major version listed in ``SUPPORTED``.

Platform-neutral, standard library only (docs/adr/0001).
"""

import json
import sys
from pathlib import Path
from typing import Any

# 1.0: jpipe-runner 4.0; 2.0: 4.1 to 4.4; 2.1: 4.5.
SUPPORTED = ("1", "2")


class Unreadable(Exception):
    """A report this action cannot read; its message says why, for the comment."""


def load(path: str) -> dict[str, Any] | None:
    """The report at ``path``; None if there is none. Raises Unreadable."""
    if not path or not Path(path).is_file():
        return None
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"its JSON report could not be read: {error}") from error
    version = str(report.get("schema_version", "")) if isinstance(report, dict) else ""
    if version.partition(".")[0] not in SUPPORTED:
        known = " and ".join(f"{major}.x" for major in SUPPORTED)
        raise Unreadable(
            f"its JSON report has schema version `{version or 'unknown'}`, and this action"
            f" reads {known} only: a newer release of jpipe-ci-actions may read it"
        )
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "verdict":
        print("usage: report.py verdict REPORT", file=sys.stderr)
        return 2
    try:
        report = load(argv[1])
    except Unreadable as error:
        print(f"warning: jpipe-runner ran, but {error}", file=sys.stderr)
        return 0
    if report is not None:
        print(report["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
