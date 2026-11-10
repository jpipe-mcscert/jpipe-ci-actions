"""A strategy that raises: the run fails (JP022), and the comment shows why."""

from pathlib import Path

from jpipe_runner import Outcome, Pass, evidence, strategy


@evidence("raised:e", observes={"file": "value.txt"}, produces=["value"])
def the_value_is_read(file: Path) -> Outcome:
    return Pass(value=int(file.read_text(encoding="utf-8")))


@strategy("raised:s", consumes=["value"])
def the_value_is_judged(value: int) -> Outcome:
    raise RuntimeError(
        "This is an intentional exception raised by the test to verify that the action "
        "adds the error message to the pull request comment."
    )
