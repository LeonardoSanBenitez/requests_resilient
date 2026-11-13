# Security policy

## Reporting a vulnerability

Please do not open a public issue. Report it privately through GitHub:
<https://github.com/LeonardoSanBenitez/requests_resilient/security/advisories/new>.

This is a one-maintainer project. I aim to acknowledge a report within 14 days and to agree a
fix and disclosure date with you after that. If you get no answer in that time, email
lsbenitezpereira@gmail.com.

## Supported versions

Only the latest released minor version receives security fixes. The project is pre-1.0, so a fix
ships as a new release of the current minor line, not as a backport.

## Threat model

`requests_resilient` sits between your code and an HTTP client, and decides whether to send a
request again and how long to wait first. That gives a misbehaving server, or a bug in this
library, two things to attack: how long your program blocks, and how many requests it sends.
The lists below say what is treated as a security problem and what is not, so that a report can
be judged quickly.

### In scope

- **Unbounded blocking driven by the server.** A `Retry-After` header must never make the
  library sleep for longer than `RetryConfig.retry_after_max` (120 seconds by default). Beyond
  the cap the response is returned to you. Any way around that cap is a security bug.
- **Retry amplification.** The library must never send more attempts than
  `RetryConfig.max_retries` for a single call. A bug that lets one call turn into more requests
  than configured turns your client into a load generator against someone else's service.
- **Replay of non-idempotent requests.** POST and PATCH must not be retried unless you opted in
  with `retry_on_post=True`. Any path that resends them without that opt-in is a security bug.
- **Credentials in logs or error messages.** Nothing the library logs or puts into an exception
  message may contain request headers, request bodies, or the user-info part of a URL
  (`https://user:password@host/`).

### Out of scope

- Behaviour that only happens because you configured it: a very large `retry_after_max` or
  `max_retries`, or `retry_on_post=True` on an endpoint that is not safe to repeat.
- Vulnerabilities in `requests`, `urllib3`, or the TLS stack. Please report those to their
  projects.
- Resource exhaustion that follows from your own concurrency, such as starting many threads
  that each retry.
- Secrets placed in the path or query string of a URL. URLs are logged at `DEBUG` level, as
  `urllib3` itself does; keep credentials in headers.
