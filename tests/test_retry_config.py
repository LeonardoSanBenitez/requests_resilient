"""Tests for RetryConfig and backoff calculation."""

from __future__ import annotations

import math
from unittest import mock

import pytest

from requests_resilient.retry import RetryConfig, _default_is_retryable


class TestDefaultIsRetryable:
    def _make_response(self, status_code: int) -> mock.Mock:
        r = mock.Mock()
        r.status_code = status_code
        return r

    def test_5xx_is_retryable(self) -> None:
        for code in [500, 502, 503, 504]:
            assert _default_is_retryable(self._make_response(code)) is True

    def test_429_is_retryable(self) -> None:
        assert _default_is_retryable(self._make_response(429)) is True

    def test_2xx_not_retryable(self) -> None:
        for code in [200, 201, 204]:
            assert _default_is_retryable(self._make_response(code)) is False

    def test_4xx_not_retryable_except_429(self) -> None:
        for code in [400, 401, 403, 404, 422]:
            assert _default_is_retryable(self._make_response(code)) is False

    def test_3xx_not_retryable(self) -> None:
        assert _default_is_retryable(self._make_response(301)) is False


class TestRetryConfigWait:
    def test_attempt_zero_returns_zero(self) -> None:
        cfg = RetryConfig(jitter=False)
        assert cfg.wait_for_attempt(0) == 0.0

    def test_negative_attempt_returns_zero(self) -> None:
        cfg = RetryConfig(jitter=False)
        assert cfg.wait_for_attempt(-1) == 0.0

    def test_constant_backoff(self) -> None:
        cfg = RetryConfig(backoff_base=1.0, backoff_factor=1.0, jitter=False)
        assert cfg.wait_for_attempt(1) == 1.0
        assert cfg.wait_for_attempt(2) == 1.0
        assert cfg.wait_for_attempt(3) == 1.0

    def test_exponential_backoff(self) -> None:
        cfg = RetryConfig(backoff_base=1.0, backoff_factor=2.0, backoff_max=100.0, jitter=False)
        assert cfg.wait_for_attempt(1) == 1.0   # base * 2^0
        assert cfg.wait_for_attempt(2) == 2.0   # base * 2^1
        assert cfg.wait_for_attempt(3) == 4.0   # base * 2^2
        assert cfg.wait_for_attempt(4) == 8.0

    def test_backoff_max_caps_wait(self) -> None:
        cfg = RetryConfig(backoff_base=1.0, backoff_factor=2.0, backoff_max=5.0, jitter=False)
        assert cfg.wait_for_attempt(10) == 5.0

    def test_jitter_stays_within_range(self) -> None:
        cfg = RetryConfig(backoff_base=2.0, backoff_factor=2.0, backoff_max=100.0, jitter=True)
        for _ in range(50):
            w = cfg.wait_for_attempt(1)
            assert 1.0 <= w <= 2.0  # jitter is [0.5, 1.0] * raw

    def test_jitter_disabled_is_deterministic(self) -> None:
        cfg = RetryConfig(backoff_base=1.0, backoff_factor=2.0, jitter=False)
        values = {cfg.wait_for_attempt(2) for _ in range(10)}
        assert len(values) == 1

    def test_custom_max_retries(self) -> None:
        cfg = RetryConfig(max_retries=1)
        assert cfg.max_retries == 1
