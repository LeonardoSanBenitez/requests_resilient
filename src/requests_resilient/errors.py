"""Exception types for requests-resilient."""

from __future__ import annotations


class MaxRetriesExceededError(Exception):
    """Raised when the maximum number of retries has been exceeded."""

    def __init__(self, message: str, last_exception: BaseException | None = None) -> None:
        super().__init__(message)
        self.last_exception = last_exception
