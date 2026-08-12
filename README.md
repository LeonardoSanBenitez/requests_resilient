# Requests Resilient

Wrapper around the `requests` python library to make it resilient to network failures.

Drop-in for the `requests` top-level API: swap the import and requests retry themselves on
transient failures, with exponential backoff, jitter, and respect for a server's `Retry-After`.

# Getting started

## Synchronous requests

```python
import requests_resilient

r = requests_resilient.get('https://google.com')
print(r.status_code)  # int, 200
print(r.text)  # str
```

For connection pooling, shared headers or auth, create a session instead of using the
module-level functions:

```python
from requests_resilient import ResilientSession, RetryConfig

session = ResilientSession(retry_config=RetryConfig(max_retries=5, backoff_base=0.5))
r = session.get('https://api.example.com/v1/items')
```

## What gets retried

By default: 5xx responses, 429 Too Many Requests, and connection/timeout errors — and only on
idempotent methods (GET, HEAD, OPTIONS, PUT, DELETE). POST and PATCH are left alone unless you
pass `retry_on_post=True`, because retrying a non-idempotent request can duplicate a side effect.

## Rate limits: `Retry-After`

When a retryable response carries a `Retry-After` header, that value is used as the wait instead
of the computed backoff. Both wire formats from RFC 9110 are understood — `Retry-After: 120` and
`Retry-After: Wed, 21 Oct 2026 07:28:00 GMT` — and a malformed value falls back to the normal
backoff rather than raising.

The server's value is honoured exactly: no jitter, and not added to the exponential backoff.
It named a time, and retrying earlier than it asked is how a client earns a hard ban.

```python
from requests_resilient import ResilientSession, RetryConfig

# Wait up to 5 minutes when a server asks us to; beyond that, hand the response back.
session = ResilientSession(retry_config=RetryConfig(retry_after_max=300.0))

# Or ignore the header entirely and always use the configured backoff.
session = ResilientSession(retry_config=RetryConfig(respect_retry_after=False))
```

If a server asks for **longer** than `retry_after_max` (default 120s), the response is returned to
you rather than blocking the call. Sleeping less than the server asked practically guarantees
another 429, and silently blocking a library call for an hour is worse than letting you decide:
the response still carries the header, so you can queue the work, fail the job, or wait.

The parser is exported if you want it on its own:

```python
from requests_resilient import parse_retry_after

parse_retry_after('120')                              # 120.0
parse_retry_after('Wed, 21 Oct 2026 07:28:00 GMT')    # seconds from now, never negative
parse_retry_after('soon')                             # None -> no usable hint
```

## Asynchronous requests

**Removed in v0.3.0.** There is no `async_get`. For async HTTP with retry, use `httpx` with
`tenacity`, or run the synchronous call in a thread so it does not block the event loop:

```python
import asyncio
import requests_resilient

r = await asyncio.to_thread(requests_resilient.get, 'https://google.com')
```
