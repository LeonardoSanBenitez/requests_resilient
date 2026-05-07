"""Retry configuration and backoff strategies."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

import requests


def _default_is_retryable(response: requests.Response) -> bool:
    """Return True if the response should trigger a retry.

    Retries on 5xx server errors and 429 Too Many Requests.
    """
    return response.status_code >= 500 or response.status_code == 429


@dataclass
class RetryConfig:
    """Configuration for retry behaviour.

    Attributes:
        max_retries:      Maximum number of attempts (1 means no retries).
        backoff_base:     Base wait time in seconds between retries.
        backoff_factor:   Multiplier for exponential backoff. Set to 1.0 for
                          constant delay.
        backoff_max:      Upper cap on computed wait time (seconds).
        jitter:           If True, adds a uniform random fraction of the
                          computed wait to avoid thundering herd.
        is_retryable:     Callable that receives a ``requests.Response`` and
                          returns True when the response warrants a retry.
                          Defaults to retrying on 5xx and 429.
        retry_on_exception: If True, also retry on connection/timeout errors.
    """

    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_factor: float = 2.0
    backoff_max: float = 60.0
    jitter: bool = True
    is_retryable: Callable[[requests.Response], bool] = field(
        default_factory=lambda: _default_is_retryable
    )
    retry_on_exception: bool = True

    def wait_for_attempt(self, attempt: int) -> float:
        """Compute the wait time (seconds) before the given attempt number.

        ``attempt`` is 1-indexed: attempt 1 is the first retry (after the
        initial request failed).

        Returns 0.0 for attempt 0 (before the first request).
        """
        if attempt <= 0:
            return 0.0
        raw = min(self.backoff_base * (self.backoff_factor ** (attempt - 1)), self.backoff_max)
        if self.jitter:
            raw = raw * (0.5 + random.random() * 0.5)
        return raw
