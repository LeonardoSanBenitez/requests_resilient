"""Retry configuration and backoff strategies."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable

import requests


def _default_is_retryable(response: requests.Response) -> bool:
    """Return True if the response should trigger a retry.

    Retries on 5xx server errors and 429 Too Many Requests.
    """
    return response.status_code >= 500 or response.status_code == 429


def parse_retry_after(value: object, now: datetime | None = None) -> float | None:
    """Parse a ``Retry-After`` header value into a delay in seconds.

    RFC 9110 allows two forms, and real servers send both:

    * ``delay-seconds`` — a non-negative integer, e.g. ``Retry-After: 120``
    * ``HTTP-date``     — e.g. ``Retry-After: Wed, 21 Oct 2026 07:28:00 GMT``

    Args:
        value: The raw header value. Anything that is not a string (missing
            header, or a mock in a test) yields ``None`` rather than raising.
        now: Reference time for the date form; defaults to the current UTC
            time. Injectable so the behaviour is testable without freezing
            the clock.

    Returns:
        The delay in seconds, never negative; ``0.0`` for a date already in
        the past. ``None`` if the value is absent or unparseable, which means
        "no usable hint, fall back to the configured backoff".

    A malformed header is deliberately not an error: a server sending
    ``Retry-After: soon`` should degrade to normal backoff, not break the
    caller's request.
    """
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None

    # delay-seconds. RFC says integer; some servers send a float, so accept both
    # and let the caller benefit rather than punishing them for a lax server.
    try:
        seconds = float(raw)
    except ValueError:
        pass
    else:
        if seconds != seconds or seconds in (float("inf"), float("-inf")):  # NaN / inf
            return None
        return max(0.0, seconds)

    # HTTP-date
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:  # older Pythons returned None instead of raising
        return None
    if when.tzinfo is None:  # obsolete formats may omit the zone; RFC says GMT
        when = when.replace(tzinfo=timezone.utc)

    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0.0, (when - reference).total_seconds())


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
        respect_retry_after: If True (default), a ``Retry-After`` header on a
                          retryable response overrides the computed backoff.
                          The server knows when it will be ready and we do not.
        retry_after_max:  Longest ``Retry-After`` delay (seconds) this client is
                          willing to wait. If a server asks for longer, the
                          response is handed back to the caller instead of
                          blocking. See :meth:`wait_before_retry`.
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
    respect_retry_after: bool = True
    retry_after_max: float = 120.0

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

    def wait_before_retry(
        self,
        attempt: int,
        response: requests.Response | None = None,
    ) -> float | None:
        """Seconds to wait before *attempt*, or ``None`` to stop retrying.

        This is :meth:`wait_for_attempt` plus the server's opinion. When the
        previous response carried a usable ``Retry-After`` and
        ``respect_retry_after`` is set, that value wins outright: it is not
        combined with the exponential backoff and no jitter is applied,
        because the server named a time and second-guessing it is how a
        client earns a hard rate-limit ban.

        Args:
            attempt: 1-indexed retry number, as in :meth:`wait_for_attempt`.
            response: The most recent response, if the previous attempt
                produced one. Pass ``None`` after a connection error — a
                stale header must not steer the next wait.

        Returns:
            The number of seconds to sleep, or ``None`` when the server asked
            for longer than ``retry_after_max``.

        Returning ``None`` rather than silently capping the sleep is a
        deliberate choice. Sleeping *less* than the server asked for
        practically guarantees another 429, and blocking a library call for
        an hour because a header said so is worse than handing the response
        back: the caller can read the header, and decide to queue the work,
        fail the job, or wait. Raise ``retry_after_max`` if blocking is what
        you want.
        """
        if response is not None and self.respect_retry_after:
            # Never raise out of the retry path because of the response object. A real
            # ``requests.Response`` always has ``.headers``, but this library is handed
            # test doubles and duck-typed fakes, and crashing on one would be a worse
            # failure than missing a hint.
            headers = getattr(response, "headers", None)
            raw: object = None
            if headers is not None and hasattr(headers, "get"):
                raw = headers.get("Retry-After")
            hinted = parse_retry_after(raw)
            if hinted is not None:
                if hinted > self.retry_after_max:
                    return None
                return hinted
        return self.wait_for_attempt(attempt)
