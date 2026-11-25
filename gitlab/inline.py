"""Write scripts/ and gitlab/job/ into the GitLab component, which cannot read this
repository's files.

    python gitlab/inline.py           rewrite the block in templates/jpipe-runner.yml
    python gitlab/inline.py --check   fail if the block differs from scripts/

A component is one YAML file, inlined into the consumer's pipeline: its job runs in the
consumer's project, where scripts/ is not checked out (docs/adr/0004). So the template
carries a copy of each file of scripts/, shared with the action, and of gitlab/job/, the
GitLab front end's own, which the job writes to a temporary directory, ``$JPIPE_SCRIPTS``,
before it runs them. The copy is written here, between the markers, and never by hand:
those directories stay where the logic lives.

Each file is a quoted here-document, which the shell copies as it is: nothing in it is
expanded. GitLab interpolates ``$[[`` everywhere in the template, so a file holding it is
refused, as is one holding the here-document's delimiter on a line of its own, or a
character YAML cannot hold.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = (ROOT / "scripts", ROOT / "gitlab" / "job")
TEMPLATE = ROOT / "templates" / "jpipe-runner.yml"
BEGIN = "# >>> scripts/: written by gitlab/inline.py, do not edit"
END = "# <<< scripts/"
DELIMITER = "JPIPE_SCRIPT_END"
# What YAML cannot hold in a block scalar: write such a character as an escape instead.
UNPRINTABLE = re.compile("[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f-\\x84\\x86-\\x9f\\ufffe\\uffff]")


def files() -> list[Path]:
    """The files the job needs: every script of the sources, by name, which must differ."""
    found = [
        path
        for source in SOURCES
        for path in sorted(source.iterdir())
        if path.is_file() and path.suffix in (".sh", ".py")
    ]
    names = [path.name for path in found]
    if len(set(names)) != len(names):
        raise SystemExit(f"two scripts share a name, and the job writes them to one place: {names}")
    return found


def block() -> list[str]:
    """The shell that writes the scripts to $JPIPE_SCRIPTS, one line per item."""
    lines = ['JPIPE_SCRIPTS="$(mktemp -d)"']
    for path in files():
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(ROOT)
        if "$[[" in text:
            raise SystemExit(f"{name}: holds $[[, which GitLab would interpolate")
        if (character := UNPRINTABLE.search(text)) is not None:
            raise SystemExit(f"{name}: holds {character.group()!r}, which YAML cannot hold")
        if DELIMITER in text.splitlines():
            raise SystemExit(f"{name}: holds {DELIMITER} on a line of its own")
        lines.append(f"cat > \"$JPIPE_SCRIPTS/{path.name}\" <<'{DELIMITER}'")
        lines.extend(text.rstrip("\n").splitlines())
        lines.append(DELIMITER)
    return lines


def inlined(template: str) -> str:
    """``template`` with the block between the markers written from scripts/."""
    lines = template.splitlines()
    begin = [i for i, line in enumerate(lines) if line.strip() == BEGIN]
    end = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(begin) != 1 or len(end) != 1 or begin[0] > end[0]:
        raise SystemExit(f"{TEMPLATE.relative_to(ROOT)}: expected one {BEGIN!r}, then one {END!r}")
    first, last = begin[0], end[0]
    indent = lines[first][: len(lines[first]) - len(lines[first].lstrip())]
    # A block scalar keeps the indentation of its first line: an empty line is left empty,
    # rather than made of spaces.
    body = [f"{indent}{line}" if line else "" for line in block()]
    return "\n".join([*lines[: first + 1], *body, *lines[last:]]) + "\n"


def main(argv: list[str]) -> int:
    if argv not in ([], ["--check"]):
        print("usage: inline.py [--check]", file=sys.stderr)
        return 2
    current = TEMPLATE.read_text(encoding="utf-8")
    wanted = inlined(current)
    if argv == ["--check"]:
        if current != wanted:
            print(
                f"{TEMPLATE.relative_to(ROOT)} does not hold scripts/ and gitlab/job/ as they are:"
                " run python gitlab/inline.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TEMPLATE.relative_to(ROOT)} holds scripts/ and gitlab/job/ as they are")
        return 0
    TEMPLATE.write_text(wanted, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
