# AI contribution: 50% or more AI-generated


class HouseholdUnavailable(RuntimeError):
    """Registration can be retried after a temporary failure."""


class DuplicateLockTimeout(HouseholdUnavailable):
    """The duplicate check could not acquire its advisory locks in time."""
