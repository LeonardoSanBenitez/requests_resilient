"""Tests for ResilientSession — all HTTP calls mocked."""

from __future__ import annotations

from unittest import mock

import pytest
import requests

from requests_resilient.errors import MaxRetriesExceededError
from requests_resilient.retry import RetryConfig
from requests_resilient.session import ResilientSession


def _make_response(status_code: int, text: str = "") -> mock.Mock:
    r = mock.Mock(spec=requests.Response)
    r.status_code = status_code
    r.text = text
    return r


class TestResilientSessionSuccess:
    def test_successful_get_returns_response(self) -> None:
        session = ResilientSession(retry_config=RetryConfig(max_retries=3))
        ok_response = _make_response(200)

        with mock.patch.object(requests.Session, "request", return_value=ok_response) as mock_req:
            resp = session.get("https://example.com")

        assert resp.status_code == 200
        mock_req.assert_called_once()

    def test_returns_4xx_without_retry(self) -> None:
        """4xx responses are not retried by default."""
        session = ResilientSession(retry_config=RetryConfig(max_retries=3))
        not_found = _make_response(404)

        with mock.patch.object(requests.Session, "request", return_value=not_found) as mock_req:
            resp = session.get("https://example.com")

        assert resp.status_code == 404
        mock_req.assert_called_once()

    def test_retries_on_500_then_succeeds(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=3, backoff_base=0.0, jitter=False)
        )
        fail = _make_response(500)
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", side_effect=[fail, ok]) as mock_req:
            with mock.patch("time.sleep"):
                resp = session.get("https://example.com")

        assert resp.status_code == 200
        assert mock_req.call_count == 2

    def test_retries_on_429(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=3, backoff_base=0.0, jitter=False)
        )
        rate_limited = _make_response(429)
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", side_effect=[rate_limited, ok]):
            with mock.patch("time.sleep"):
                resp = session.get("https://example.com")

        assert resp.status_code == 200

    def test_exhausts_retries_returns_last_response(self) -> None:
        """When all retries are exhausted and we have a response, return it."""
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=2, backoff_base=0.0, jitter=False)
        )
        always_500 = _make_response(500)

        with mock.patch.object(requests.Session, "request", return_value=always_500):
            with mock.patch("time.sleep"):
                resp = session.get("https://example.com")

        assert resp.status_code == 500


class TestResilientSessionExceptions:
    def test_connection_error_raises_after_retries(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=2, backoff_base=0.0, jitter=False)
        )

        with mock.patch.object(
            requests.Session, "request", side_effect=requests.ConnectionError("down")
        ):
            with mock.patch("time.sleep"):
                with pytest.raises(MaxRetriesExceededError):
                    session.get("https://example.com")

    def test_timeout_retried_then_succeeds(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=3, backoff_base=0.0, jitter=False)
        )
        ok = _make_response(200)

        with mock.patch.object(
            requests.Session,
            "request",
            side_effect=[requests.Timeout("slow"), ok],
        ):
            with mock.patch("time.sleep"):
                resp = session.get("https://example.com")

        assert resp.status_code == 200

    def test_connection_error_not_retried_for_non_idempotent_method(self) -> None:
        """POST is not retried on connection error unless retry_on_post=True."""
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=3, backoff_base=0.0, jitter=False)
        )

        with mock.patch.object(
            requests.Session, "request", side_effect=requests.ConnectionError("down")
        ):
            with pytest.raises(MaxRetriesExceededError):
                session.post("https://example.com", json={})

    def test_post_retried_when_retry_on_post_enabled(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=3, backoff_base=0.0, jitter=False),
            retry_on_post=True,
        )
        ok = _make_response(200)

        with mock.patch.object(
            requests.Session,
            "request",
            side_effect=[requests.ConnectionError("down"), ok],
        ):
            with mock.patch("time.sleep"):
                resp = session.post("https://example.com")

        assert resp.status_code == 200

    def test_max_retries_exceeded_error_carries_last_exception(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=2, backoff_base=0.0, jitter=False)
        )
        exc = requests.ConnectionError("network down")

        with mock.patch.object(requests.Session, "request", side_effect=exc):
            with mock.patch("time.sleep"):
                with pytest.raises(MaxRetriesExceededError) as exc_info:
                    session.get("https://example.com")

        assert exc_info.value.last_exception is exc


class TestResilientSessionBackoff:
    def test_sleep_called_between_retries(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(
                max_retries=3,
                backoff_base=1.0,
                backoff_factor=1.0,
                jitter=False,
            )
        )
        fail = _make_response(500)
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", side_effect=[fail, fail, ok]):
            with mock.patch("time.sleep") as mock_sleep:
                session.get("https://example.com")

        # Two retries = two sleeps
        assert mock_sleep.call_count == 2

    def test_no_sleep_before_first_attempt(self) -> None:
        session = ResilientSession(
            retry_config=RetryConfig(max_retries=1, backoff_base=5.0, jitter=False)
        )
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", return_value=ok):
            with mock.patch("time.sleep") as mock_sleep:
                session.get("https://example.com")

        mock_sleep.assert_not_called()


class TestResilientSessionCustomRetryable:
    def test_custom_is_retryable(self) -> None:
        """Custom is_retryable function is honoured."""
        cfg = RetryConfig(
            max_retries=3,
            backoff_base=0.0,
            jitter=False,
            is_retryable=lambda r: r.status_code == 404,  # unusual but valid test
        )
        session = ResilientSession(retry_config=cfg)
        not_found = _make_response(404)
        ok = _make_response(200)

        with mock.patch.object(requests.Session, "request", side_effect=[not_found, ok]):
            with mock.patch("time.sleep"):
                resp = session.get("https://example.com")

        assert resp.status_code == 200
