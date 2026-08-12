"""requests-resilient — automatic retry for the requests library.

Quick start::

    import requests_resilient

    # Drop-in for requests.get / .post / etc.
    resp = requests_resilient.get("https://api.example.com/v1/items")

    # Or create a session for connection pooling / shared headers:
    from requests_resilient import ResilientSession, RetryConfig

    cfg = RetryConfig(max_retries=5, backoff_base=0.5, jitter=True)
    session = ResilientSession(retry_config=cfg)
    resp = session.get("https://api.example.com/v1/items")
"""

from requests_resilient.errors import MaxRetriesExceededError
from requests_resilient.retry import RetryConfig, parse_retry_after
from requests_resilient.session import ResilientSession
from requests_resilient.synchronous import (
    configure,
    delete,
    download_file,
    get,
    head,
    options,
    patch,
    post,
    put,
)

__all__ = [
    # Core classes
    "ResilientSession",
    "RetryConfig",
    "parse_retry_after",
    # Errors
    "MaxRetriesExceededError",
    # Convenience functions
    "configure",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "download_file",
]

__version__ = "0.3.0"
