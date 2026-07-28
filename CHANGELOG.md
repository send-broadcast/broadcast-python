# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-28

Published to PyPI as `broadcast-python`; the import module is `broadcast_python`,
because a package named `broadcast` already occupies that name on PyPI.

Released through PyPI trusted publishing (OIDC) rather than an API token — no
credential for this package exists anywhere. Verified from the registry: the
installed artifact imports, ships `py.typed`, exposes all 18 migration
collections and 32 event types, and computes a webhook signature identical to
the Ruby, PHP and Node SDKs.


First release. Feature parity with `broadcast-ruby` v0.3.0 — the reference
implementation — verified at **104/104 API operations** by the coverage report
in the `broadcast` repo.

### Transport
- Required explicit `host`, with `BROADCAST_HOST` / `BROADCAST_API_TOKEN` env
  fallbacks matching the Broadcast CLI's config keys
- Bearer auth, `User-Agent: broadcast-python/<version>`
- Response warnings surfaced, with `log` / `raise` / `ignore` modes
- `Idempotency-Key` request header and `idempotent_replay` detection
- `X-RateLimit-*` parsing; 429 retry honouring `Retry-After`, bounded by
  `max_retry_delay`
- Retries on timeout and 5xx with linear backoff; 422 is never retried
- Typed errors for 401/403/404/409/422/429/5xx
- Redirects followed on GET only, never across hosts — the request carries a
  bearer token, and urllib's default handler would take it along
- Raw response path for `text/plain` (`/api/v1/skill`) and binary file assets
- Channel scoping via `broadcast_channel_id` and the `with_channel` context manager
- Debug logging that never emits credentials or request bodies

### Resources
Subscribers, broadcasts (incl. statistics), sequences (incl. steps), segments,
templates, opt-in forms, email servers, webhook endpoints, transactionals,
autopilot, discovery, and the 20 migration/export operations.

### Non-negotiables carried over from the Ruby gem
- **Credential redaction guard** on email servers and autopilot, so a
  fetch-modify-save cannot overwrite a real credential with bullet characters
- Webhook HMAC-SHA256 verification with a 5-minute window and constant-time
  comparison
- No credentials or subscriber emails in debug output

### Notes
- No runtime dependencies. The transport is `urllib` from the standard library,
  so installing this cannot conflict with a pinned `requests` or `httpx`.
- The test suite uses `unittest`, so it runs with no test dependencies either.
- `broadcast.TimeoutError` shadows neither the builtin nor `socket.timeout`; it
  is named for parity with the Ruby gem and pinned by a test.
