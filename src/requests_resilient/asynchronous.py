"""Async support was removed in v0.3.0.

For async HTTP with retry, consider:
- ``httpx`` with ``tenacity`` for a production-grade combination
- ``asyncio.to_thread(requests_resilient.get, url)`` to run sync requests
  in a thread pool without blocking the event loop
"""
