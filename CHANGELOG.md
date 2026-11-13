# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/): patch releases fix behaviour,
minor releases add to the public API without changing what already exists, and major releases may
change it with a documented migration.

## 0.3.2 - 2026-11-13

### Fixed
- Credentials in a URL's user-info part (`https://user:password@host/`) no longer appear in debug
  log records or in `MaxRetriesExceededError` messages; they are replaced by `***@`. The request
  itself is sent unchanged.

### Changed
- Packaging: the license is declared as the SPDX expression `MIT`, and the package metadata links
  the changelog and the issue tracker. Building from source now needs setuptools 77 or newer.
- Tested on Python 3.13 as well as 3.10 to 3.12.

### Notes
- The repository now has a contributing guide, a security policy with a threat model
  (`SECURITY.md`), a code of conduct, and a policy on AI tools (`docs/policies/ai.md`).
- No change to the public API.

## 0.3.1 — 2026-08-12

### Added
- `Retry-After` is now honoured on retryable responses (429, 503). Both RFC 9110 forms are
  understood: delay-seconds (`Retry-After: 120`) and HTTP-date
  (`Retry-After: Wed, 21 Oct 2026 07:28:00 GMT`). A malformed value falls back to the normal
  backoff instead of raising.
- `RetryConfig.respect_retry_after` (default `True`) and `RetryConfig.retry_after_max`
  (default 120 seconds). When a server asks for longer than the cap, the response is returned to
  the caller rather than blocking the call.
- `parse_retry_after()` is exported for use on its own.
- `RetryConfig.wait_before_retry(attempt, response)`, which combines the server's instruction with
  the configured backoff. `wait_for_attempt()` is unchanged and still available.

### Fixed
- The README — and therefore the PyPI landing page — documented `async_get`, which was removed in
  0.3.0. It now documents the supported alternatives, and what is retried by default.

### Notes
- The server's `Retry-After` value is used exactly: no jitter is applied and it is not added to
  the exponential backoff.
- No breaking changes. Existing configurations behave as before except that a `Retry-After`
  header, previously ignored, is now respected; set `respect_retry_after=False` for the old
  behaviour.

## 0.3.0

- Typed rewrite with `ResilientSession`, `RetryConfig`, exponential backoff with jitter, and
  retry-on-exception support.
- Async support (`async_get` and friends) was removed.
