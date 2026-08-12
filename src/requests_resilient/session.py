"""ResilientSession: a requests.Session subclass with automatic retry logic."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from requests_resilient.errors import MaxRetriesExceededError
from requests_resilient.retry import RetryConfig

logger = logging.getLogger(__name__)

# HTTP methods that are safe to retry without side-effects.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


class ResilientSession(requests.Session):
    """A ``requests.Session`` that transparently retries failed requests.

    Drop-in replacement for ``requests.Session``. All keyword arguments
    accepted by ``requests.Session.request`` are forwarded unchanged.

    Parameters:
        retry_config:   Controls retry count, backoff and retry conditions.
        retry_on_post:  By default only idempotent methods are retried.  Set
                        this to True to also retry POST / PATCH requests.

    Example::

        session = ResilientSession()
        resp = session.get("https://api.example.com/data")

        # Custom config
        cfg = RetryConfig(max_retries=5, backoff_base=0.5)
        session = ResilientSession(retry_config=cfg)
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        retry_on_post: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.retry_config: RetryConfig = retry_config or RetryConfig()
        self.retry_on_post: bool = retry_on_post

    def request(  # type: ignore[override]
        self,
        method: str,
        url: str | bytes,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a request with automatic retry on transient failures.

        Raises:
            MaxRetriesExceededError: When all attempts are exhausted.
        """
        cfg = self.retry_config
        upper = method.upper()
        url_str: str = url.decode() if isinstance(url, bytes) else url
        retryable_method = upper in _IDEMPOTENT_METHODS or (
            self.retry_on_post and upper in {"POST", "PATCH"}
        )

        last_exc: BaseException | None = None
        response: requests.Response | None = None
        # The response whose Retry-After should steer the next wait. Deliberately
        # separate from `response`: after a connection error there is no fresh
        # response, and the previous one's header must not be reused.
        hint_source: requests.Response | None = None

        for attempt in range(cfg.max_retries):
            # Wait before retries (not before the first attempt).
            if attempt > 0:
                wait = cfg.wait_before_retry(attempt, hint_source)
                if wait is None:
                    # Server asked to wait longer than this client is willing to
                    # block. Hand the response back rather than sleeping on it.
                    logger.debug(
                        "Retry-After on %s %s exceeds retry_after_max=%.1fs — returning response",
                        upper,
                        url,
                        cfg.retry_after_max,
                    )
                    assert response is not None  # hint_source is set only from a response
                    return response
                logger.debug(
                    "Retry %d/%d for %s %s — waiting %.2fs",
                    attempt,
                    cfg.max_retries - 1,
                    upper,
                    url,
                    wait,
                )
                time.sleep(wait)

            try:
                response = super().request(method, url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                hint_source = None
                if not (retryable_method and cfg.retry_on_exception):
                    raise MaxRetriesExceededError(
                        f"Request {upper} {url_str} failed: {exc}", last_exception=exc
                    ) from exc
                logger.debug("Connection/timeout error on attempt %d: %s", attempt + 1, exc)
                continue

            hint_source = response

            if not cfg.is_retryable(response):
                return response

            if not retryable_method:
                # Non-idempotent method: don't silently retry.
                return response

            logger.debug(
                "Response %d is retryable (attempt %d/%d)",
                response.status_code,
                attempt + 1,
                cfg.max_retries,
            )
            last_exc = None  # response-level retry, not exception-based

        # All attempts exhausted.
        if response is not None:
            return response
        raise MaxRetriesExceededError(
            f"All {cfg.max_retries} attempts failed for {upper} {url_str}",
            last_exception=last_exc,
        )
