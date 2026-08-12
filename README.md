# Requests Resilient

Wrapper around the `requests` python library to make it resilient to network failures.

Drop-in for the `requests` top-level API: swap the import and requests retry themselves on
transient failures, with exponential backoff and jitter.

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

## Asynchronous requests

**Removed in v0.3.0.** There is no `async_get`. For async HTTP with retry, use `httpx` with
`tenacity`, or run the synchronous call in a thread so it does not block the event loop:

```python
import asyncio
import requests_resilient

r = await asyncio.to_thread(requests_resilient.get, 'https://google.com')
```
