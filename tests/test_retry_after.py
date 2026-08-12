"""Tests for Retry-After support: the parser, the policy, and the session wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock

import pytest
import requests

from requests_resilient.retry import RetryConfig, parse_retry_after
from requests_resilient.session import ResilientSession


def _make_response(status_code: int, headers: dict[str, str] | None = None) -> mock.Mock:
    r = mock.Mock(spec=requests.Response)
    r.status_code = status_code
    r.text = ""
    r.headers = headers if headers is not None else {}
    return r


class TestParseRetryAfter:
    """The wire format is two formats and servers get both of them wrong."""

    def test_delay_seconds(self) -> None:
        assert parse_retry_after("120") == 120.0
        assert parse_retry_after("0") == 0.0

    def test_surrounding_whitespace_is_tolerated(self) -> None:
        assert parse_retry_after("  30  ") == 30.0

    def test_float_seconds_accepted_though_rfc_says_integer(self) -> None:
        assert parse_retry_after("1.5") == 1.5

    def test_negative_delay_clamps_to_zero(self) -> None:
        assert parse_retry_after("-5") == 0.0

    def test_http_date_in_the_future(self) -> None:
        now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
        later = "Wed, 21 Oct 2026 07:30:00 GMT"
        assert parse_retry_after(later, now=now) == pytest.approx(120.0)

    def test_http_date_in_the_past_clamps_to_zero(self) -> None:
        now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
        assert parse_retry_after("Wed, 21 Oct 2026 07:00:00 GMT", now=now) == 0.0

    def test_naive_reference_time_is_treated_as_utc(self) -> None:
        naive = datetime(2026, 10, 21, 7, 28, 0)
        assert parse_retry_after("Wed, 21 Oct 2026 07:30:00 GMT", now=naive) == pytest.approx(120.0)

    @pytest.mark.parametrize("bad", ["", "   ", "soon", "next tuesday", "NaN", "inf", "-inf"])
    def test_unparseable_returns_none(self, bad: str) -> None:
        """A lax server must degrade to normal backoff, not break the request."""
        assert parse_retry_after(bad) is None

    @pytest.mark.parametrize("bad", [None, 120, 1.5, object(), mock.Mock()])
    def test_non_string_returns_none(self, bad: object) -> None:
        """Missing header, or a bare Mock from someone else's test suite."""
        assert parse_retry_after(bad) is None


class TestWaitBeforeRetry:
    def test_retry_after_overrides_backoff(self) -> None:
        cfg = RetryConfig(backoff_base=1.0, backoff_factor=2.0, jitter=True)
        resp = _make_response(429, {"Retry-After": "7"})
        # Exactly 7: not combined with backoff, and no jitter applied to it.
        assert cfg.wait_before_retry(attempt=3, response=resp) == 7.0

    def test_falls_back_to_backoff_when_header_absent(self) -> None:
        cfg = RetryConfig(backoff_base=2.0, backoff_factor=1.0, jitter=False)
        resp = _make_response(503, {})
        assert cfg.wait_before_retry(attempt=1, response=resp) == 2.0

    def test_falls_back_to_backoff_when_header_is_junk(self) -> None:
        cfg = RetryConfig(backoff_base=2.0, backoff_factor=1.0, jitter=False)
        resp = _make_response(503, {"Retry-After": "whenever"})
        assert cfg.wait_before_retry(attempt=1, response=resp) == 2.0

    def test_no_response_uses_backoff(self) -> None:
        cfg = RetryConfig(backoff_base=3.0, backoff_factor=1.0, jitter=False)
        assert cfg.wait_before_retry(attempt=1, response=None) == 3.0

    def test_response_object_without_headers_falls_back_instead_of_raising(self) -> None:
        """Regression: the pre-0.4 test doubles have no ``.headers`` at all.

        Adding Retry-After support must not make the retry path raise on a
        response-like object that lacks the attribute — that would turn a
        missing hint into a crash inside the very code meant to absorb faults.
        """
        cfg = RetryConfig(backoff_base=4.0, backoff_factor=1.0, jitter=False)
        headerless = mock.Mock(spec=["status_code"])
        headerless.status_code = 503
        assert cfg.wait_before_retry(attempt=1, response=headerless) == 4.0

    def test_respect_flag_disables_the_header(self) -> None:
        cfg = RetryConfig(
            backoff_base=2.0, backoff_factor=1.0, jitter=False, respect_retry_after=False
        )
        resp = _make_response(429, {"Retry-After": "600"})
        assert cfg.wait_before_retry(attempt=1, response=resp) == 2.0

    def test_returns_none_when_over_the_cap(self) -> None:
        cfg = RetryConfig(retry_after_max=120.0)
        resp = _make_response(429, {"Retry-After": "3600"})
        assert cfg.wait_before_retry(attempt=1, response=resp) is None

    def test_exactly_at_the_cap_is_honoured(self) -> None:
        """The cap is a maximum, not an exclusive bound."""
        cfg = RetryConfig(retry_after_max=120.0)
        resp = _make_response(429, {"Retry-After": "120"})
        assert cfg.wait_before_retry(attempt=1, response=resp) == 120.0


class TestSessionHonoursRetryAfter:
    def test_sleeps_for_the_time_the_server_asked_for(self) -> None:
        session = ResilientSession(retry_config=RetryConfig(max_retries=3, backoff_base=99.0))
        throttled = _make_response(429, {"Retry-After": "5"})
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", side_effect=[throttled, ok]):
            with mock.patch("time.sleep") as sleeper:
                resp = session.get("https://example.com")

        assert resp.status_code == 200
        sleeper.assert_called_once_with(5.0)

    def test_returns_response_instead_of_blocking_past_the_cap(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=3, retry_after_max=60.0)
        )
        throttled = _make_response(429, {"Retry-After": "3600"})
        ok = _make_response(200)

        with mock.patch.object(
            requests.Session, "request", side_effect=[throttled, ok]
        ) as mock_req:
            with mock.patch("time.sleep") as sleeper:
                resp = session.get("https://example.com")

        # The caller gets the 429 back, with its header intact, and nothing slept.
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "3600"
        sleeper.assert_not_called()
        mock_req.assert_called_once()

    def test_stale_header_does_not_steer_the_wait_after_a_connection_error(self) -> None:
        """A Retry-After from two attempts ago must not drive the next sleep.

        Sequence: 429 with Retry-After 5 -> connection error -> success. The wait
        before attempt 2 comes from the header; the wait before attempt 3 must come
        from the backoff, because the attempt that just failed produced no response.
        """
        session = ResilientSession(
            retry_config=RetryConfig(
                max_retries=3, backoff_base=1.0, backoff_factor=1.0, jitter=False
            )
        )
        throttled = _make_response(429, {"Retry-After": "5"})
        ok = _make_response(200)

        with mock.patch.object(
            requests.Session,
            "request",
            side_effect=[throttled, requests.ConnectionError("boom"), ok],
        ):
            with mock.patch("time.sleep") as sleeper:
                resp = session.get("https://example.com")

        assert resp.status_code == 200
        assert [c.args[0] for c in sleeper.call_args_list] == [5.0, 1.0]

    def test_honours_retry_after_on_503_too(self) -> None:
        session = ResilientSession(retry_config=RetryConfig(max_retries=3, backoff_base=99.0))
        unavailable = _make_response(503, {"Retry-After": "2"})
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", side_effect=[unavailable, ok]):
            with mock.patch("time.sleep") as sleeper:
                resp = session.get("https://example.com")

        assert resp.status_code == 200
        sleeper.assert_called_once_with(2.0)

    def test_non_retryable_response_with_header_is_untouched(self) -> None:
        """A 200 carrying Retry-After (some APIs do) must not trigger a wait."""
        session = ResilientSession(retry_config=RetryConfig(max_retries=3))
        ok = _make_response(200, {"Retry-After": "30"})

        with mock.patch.object(requests.Session, "request", return_value=ok) as mock_req:
            with mock.patch("time.sleep") as sleeper:
                resp = session.get("https://example.com")

        assert resp.status_code == 200
        mock_req.assert_called_once()
        sleeper.assert_not_called()
