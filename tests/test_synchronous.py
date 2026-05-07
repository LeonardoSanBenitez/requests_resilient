"""Tests for module-level convenience functions in requests_resilient."""

from __future__ import annotations

import io
from pathlib import Path
from unittest import mock

import pytest
import requests

import requests_resilient
from requests_resilient.errors import MaxRetriesExceededError
from requests_resilient.retry import RetryConfig
from requests_resilient.session import ResilientSession


def _make_response(status_code: int) -> mock.Mock:
    r = mock.Mock(spec=requests.Response)
    r.status_code = status_code
    r.raw = io.BytesIO(b"content")
    return r


class TestConvenienceFunctions:
    def setup_method(self) -> None:
        # Reset the module-level session between tests.
        import requests_resilient.synchronous as sync_mod
        sync_mod._default_session = None

    def test_get_returns_response(self) -> None:
        ok = _make_response(200)
        with mock.patch.object(ResilientSession, "get", return_value=ok):
            resp = requests_resilient.get("https://example.com")
        assert resp.status_code == 200

    def test_post_returns_response(self) -> None:
        ok = _make_response(201)
        with mock.patch.object(ResilientSession, "post", return_value=ok):
            resp = requests_resilient.post("https://example.com", json={"key": "val"})
        assert resp.status_code == 201

    def test_put_returns_response(self) -> None:
        ok = _make_response(200)
        with mock.patch.object(ResilientSession, "put", return_value=ok):
            resp = requests_resilient.put("https://example.com")
        assert resp.status_code == 200

    def test_delete_returns_response(self) -> None:
        ok = _make_response(204)
        with mock.patch.object(ResilientSession, "delete", return_value=ok):
            resp = requests_resilient.delete("https://example.com/1")
        assert resp.status_code == 204

    def test_head_returns_response(self) -> None:
        ok = _make_response(200)
        with mock.patch.object(ResilientSession, "head", return_value=ok):
            resp = requests_resilient.head("https://example.com")
        assert resp.status_code == 200

    def test_options_returns_response(self) -> None:
        ok = _make_response(200)
        with mock.patch.object(ResilientSession, "options", return_value=ok):
            resp = requests_resilient.options("https://example.com")
        assert resp.status_code == 200

    def test_patch_returns_response(self) -> None:
        ok = _make_response(200)
        with mock.patch.object(ResilientSession, "patch", return_value=ok):
            resp = requests_resilient.patch("https://example.com")
        assert resp.status_code == 200


class TestConfigure:
    def setup_method(self) -> None:
        import requests_resilient.synchronous as sync_mod
        sync_mod._default_session = None

    def test_configure_sets_custom_retry_config(self) -> None:
        cfg = RetryConfig(max_retries=7)
        requests_resilient.configure(retry_config=cfg)

        import requests_resilient.synchronous as sync_mod
        assert sync_mod._default_session is not None
        assert sync_mod._default_session.retry_config.max_retries == 7

    def test_configure_retry_on_post(self) -> None:
        requests_resilient.configure(retry_on_post=True)
        import requests_resilient.synchronous as sync_mod
        assert sync_mod._default_session is not None
        assert sync_mod._default_session.retry_on_post is True


class TestDownloadFile:
    def setup_method(self) -> None:
        import requests_resilient.synchronous as sync_mod
        sync_mod._default_session = None

    def test_downloads_file(self, tmp_path: Path) -> None:
        dest = tmp_path / "file.bin"
        ok = _make_response(200)
        ok.raw = io.BytesIO(b"hello world")

        with mock.patch.object(ResilientSession, "get", return_value=ok):
            result = requests_resilient.download_file("https://example.com/file.bin", dest=dest)

        assert result == dest
        assert dest.read_bytes() == b"hello world"

    def test_default_filename_from_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        ok = _make_response(200)
        ok.raw = io.BytesIO(b"data")

        with mock.patch.object(ResilientSession, "get", return_value=ok):
            result = requests_resilient.download_file("https://example.com/report.csv")

        assert result.name == "report.csv"
        assert (tmp_path / "report.csv").exists()
