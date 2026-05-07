"""Module-level convenience functions mirroring the ``requests`` top-level API.

These are thin wrappers around a shared :class:`ResilientSession` instance.
For production use where you want full control over connection pools, headers,
or auth, prefer creating your own :class:`ResilientSession` directly.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import requests

from requests_resilient.retry import RetryConfig
from requests_resilient.session import ResilientSession

# Module-level default session — created lazily.
_default_session: ResilientSession | None = None


def _session() -> ResilientSession:
    global _default_session
    if _default_session is None:
        _default_session = ResilientSession()
    return _default_session


def configure(retry_config: RetryConfig | None = None, retry_on_post: bool = False) -> None:
    """Replace the module-level default session with new settings.

    Call this once at application startup if you need non-default retry
    behaviour for the convenience functions.
    """
    global _default_session
    _default_session = ResilientSession(
        retry_config=retry_config,
        retry_on_post=retry_on_post,
    )


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def get(url: str, **kwargs: Any) -> requests.Response:
    """Send a GET request with automatic retry."""
    return _session().get(url, **kwargs)


def post(url: str, **kwargs: Any) -> requests.Response:
    """Send a POST request.  Retries only if ``retry_on_post=True`` in config."""
    return _session().post(url, **kwargs)


def put(url: str, **kwargs: Any) -> requests.Response:
    """Send a PUT request with automatic retry."""
    return _session().put(url, **kwargs)


def patch(url: str, **kwargs: Any) -> requests.Response:
    """Send a PATCH request."""
    return _session().patch(url, **kwargs)


def delete(url: str, **kwargs: Any) -> requests.Response:
    """Send a DELETE request with automatic retry."""
    return _session().delete(url, **kwargs)


def head(url: str, **kwargs: Any) -> requests.Response:
    """Send a HEAD request with automatic retry."""
    return _session().head(url, **kwargs)


def options(url: str, **kwargs: Any) -> requests.Response:
    """Send an OPTIONS request with automatic retry."""
    return _session().options(url, **kwargs)


# ---------------------------------------------------------------------------
# Utility: file download
# ---------------------------------------------------------------------------

def download_file(url: str, dest: str | Path | None = None) -> Path:
    """Download *url* to *dest* (or the URL's filename in the cwd).

    Streams the response to avoid loading large files into memory.

    Returns:
        The path to the downloaded file.
    """
    dest_path = Path(dest) if dest is not None else Path(url.split("/")[-1])
    resp = _session().get(url, stream=True)
    with dest_path.open("wb") as f:
        shutil.copyfileobj(resp.raw, f)
    return dest_path
