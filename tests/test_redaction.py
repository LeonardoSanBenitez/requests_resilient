"""Credentials in a URL's user-info part must never reach logs or exception messages."""

from __future__ import annotations

import logging
from unittest import mock

import pytest
import requests

from requests_resilient.errors import MaxRetriesExceededError
from requests_resilient.retry import RetryConfig
from requests_resilient.session import ResilientSession, redact_url

SECRET_URL = "https://alice:s3cret-pw@api.example.com/v1/items?page=2"


def _response(status_code: int, headers: dict[str, str] | None = None) -> mock.Mock:
    r = mock.Mock(spec=requests.Response)
    r.status_code = status_code
    r.headers = headers or {}
    return r


def _session(**cfg: object) -> ResilientSession:
    return ResilientSession(retry_config=RetryConfig(backoff_base=0.0, jitter=False, **cfg))  # type: ignore[arg-type]


class TestRedactUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            (SECRET_URL, "https://***@api.example.com/v1/items?page=2"),
            ("https://token@api.example.com/", "https://***@api.example.com/"),
            ("http://u:p@host:8080/x", "http://***@host:8080/x"),
            ("https://api.example.com/v1?q=1", "https://api.example.com/v1?q=1"),
            ("not a url", "not a url"),
            ("", ""),
        ],
    )
    def test_redacts_only_userinfo(self, url: str, expected: str) -> None:
        assert redact_url(url) == expected


class TestNoCredentialsInLogs:
    def test_retry_logs_do_not_contain_password(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="requests_resilient"):
            with mock.patch.object(requests.Session, "request", side_effect=[_response(503), _response(200)]):
                with mock.patch("time.sleep"):
                    _session(max_retries=3).get(SECRET_URL)

        assert caplog.records, "the retry path must have logged something, or this test checks nothing"
        text = "\n".join(r.getMessage() for r in caplog.records)
        assert "api.example.com/v1/items" in text
        assert "s3cret-pw" not in text
        assert "alice" not in text

    def test_retry_after_cap_log_does_not_contain_password(self, caplog: pytest.LogCaptureFixture) -> None:
        too_long = _response(429, {"Retry-After": "9999"})
        with caplog.at_level(logging.DEBUG, logger="requests_resilient"):
            with mock.patch.object(requests.Session, "request", side_effect=[too_long]):
                _session(max_retries=3).get(SECRET_URL)

        text = "\n".join(r.getMessage() for r in caplog.records)
        assert "retry_after_max" in text
        assert "s3cret-pw" not in text

    def test_bytes_url_is_redacted_too(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="requests_resilient"):
            with mock.patch.object(requests.Session, "request", side_effect=[_response(503), _response(200)]):
                with mock.patch("time.sleep"):
                    _session(max_retries=3).request("GET", SECRET_URL.encode())

        text = "\n".join(r.getMessage() for r in caplog.records)
        assert caplog.records and "s3cret-pw" not in text


class TestNoCredentialsInErrors:
    def test_exhausted_connection_errors(self) -> None:
        with mock.patch.object(requests.Session, "request", side_effect=requests.ConnectionError("down")):
            with mock.patch("time.sleep"):
                with pytest.raises(MaxRetriesExceededError) as info:
                    _session(max_retries=2).get(SECRET_URL)

        assert "api.example.com" in str(info.value)
        assert "s3cret-pw" not in str(info.value)

    def test_non_retryable_method_connection_error(self) -> None:
        with mock.patch.object(requests.Session, "request", side_effect=requests.ConnectionError("down")):
            with pytest.raises(MaxRetriesExceededError) as info:
                _session(max_retries=3).post(SECRET_URL)

        assert "api.example.com" in str(info.value)
        assert "s3cret-pw" not in str(info.value)
