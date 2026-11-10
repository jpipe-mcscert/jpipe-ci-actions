"""Steps that pass only on Python 3.12: they check that python-executable is used."""

import sys
from pathlib import Path

from jpipe_runner import Fail, Outcome, Pass, evidence, strategy


@evidence("python_version:e", observes={"readme": "README.txt"}, produces=["minor"])
def the_version_is_recorded(readme: Path) -> Outcome:
    return Pass(minor=sys.version_info.minor)


@strategy("python_version:s", consumes=["minor"])
def the_version_is_3_12(minor: int) -> Outcome:
    return Pass() if minor == 12 else Fail(f"the steps ran on Python 3.{minor}, not 3.12")
