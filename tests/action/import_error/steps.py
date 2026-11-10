"""A library that raises when it is imported: nothing runs (JP020, exit code 3)."""

raise RuntimeError(
    "This is an intentional exception raised during import to verify that the action "
    "adds the error message to the pull request comment."
)
