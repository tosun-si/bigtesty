class BigTestyError(Exception):
    """Base error of BigTesty."""


class SpecError(BigTestyError):
    """Invalid project config or test file."""


class FailedScenariosError(BigTestyError):
    """At least one scenario failed."""
