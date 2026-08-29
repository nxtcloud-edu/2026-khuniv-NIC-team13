"""Workflow-specific exception types used by routing and retry policy."""


class InvalidSubmissionError(Exception):
    """A confirmed invalid user submission that should not be retried."""
