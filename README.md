# broadcast-python

Python client for [Broadcast](https://sendbroadcast.net), the email marketing
platform. Works with any Broadcast instance — self-hosted or SaaS.

Covers **104/104 API operations**, verified against the API's generated OpenAPI
document.

```bash
pip install broadcast-python
```

Python 3.9+. **No runtime dependencies** — the transport is built on the
standard library's `urllib`, so it cannot conflict with a pinned `requests` or
`httpx` elsewhere in your environment.

---

## Quick start

```python
from broadcast_python import Broadcast

client = Broadcast(
    api_token="...",                  # or BROADCAST_API_TOKEN
    host="https://mail.example.com",  # or BROADCAST_HOST — required
)

client.subscribers.create(email="ada@example.com", first_name="Ada")

client.transactionals.create(
    to="ada@example.com",
    subject="Welcome",
    body="<p>Glad you are here.</p>",
)
```

### `host` is required

There is no default. Broadcast is self-hosted-first, so every instance lives at
its own domain and any built-in guess would be wrong for nearly everyone.

`BROADCAST_HOST` and `BROADCAST_API_TOKEN` are the same names the Broadcast CLI
uses in `~/.config/broadcast/config`, so a machine set up for the CLI needs no
extra configuration.

---

## Configuration

```python
Broadcast(
    api_token="...",
    host="https://...",
    timeout=30,              # read timeout, seconds
    open_timeout=10,
    retry_attempts=3,
    retry_delay=1,           # base backoff, multiplied by attempt number
    max_retry_delay=30,      # ceiling on a server-sent Retry-After
    warnings_mode="log",     # "log" | "raise" | "ignore"
    logger=logging.getLogger(__name__),
    debug=False,
    broadcast_channel_id=42, # admin/system tokens
)
```

A typo in a setting name raises `TypeError` rather than being silently ignored.

---

## Responses

`Response` subclasses `dict`, so a result behaves exactly like the parsed body
while carrying transport metadata as attributes:

```python
result = client.subscribers.create(email="ada@example.com")

result["id"]                     # the body
result.status                    # 201
result.warnings                  # [Warning_(code=..., param=..., message=...)]
result.rate_limit.remaining
result.idempotent_replay         # True if the API replayed a stored response
```

Item access reads the body, attribute access reads metadata — so a body field
named `status` (which broadcasts have) stays reachable as `result["status"]`.

---

## Warnings

A 2xx response can carry warnings: the API accepted your request but ignored
part of it. A mistyped filter silently widens a result set unless you look.

```python
# "log" (default) — warn through `logger`, return normally
# "raise"         — raise WarningError. NOTE: the write already happened.
# "ignore"        — say nothing; read them off result.warnings
```

---

## Errors

```
BroadcastError
├── ConfigurationError
├── APIError
│   ├── AuthenticationError   401
│   ├── AuthorizationError    403
│   ├── NotFoundError         404
│   ├── ConflictError         409  idempotency replay still in flight
│   └── RateLimitError        429  carries .retry_after
├── ValidationError           422
├── TimeoutError
├── DeliveryError
└── WarningError                   carries .warnings and .response
```

`ValidationError` and `TimeoutError` are siblings of `APIError`, not children —
matching the Ruby gem. Note `broadcast_python.TimeoutError` is **not** the builtin
`TimeoutError`.

Timeouts, 429s, and 5xx are retried with backoff. A 422 is not: it is
deterministic, so retrying is pure latency.

---

## Resources

### Subscribers

```python
client.subscribers.list(page=1, is_active=True, tags=["vip"])
client.subscribers.find("ada@example.com")
client.subscribers.create(email="ada@example.com", tags=["vip"])
client.subscribers.update("ada@example.com", first_name="Ada")
client.subscribers.add_tags("ada@example.com", ["beta"])
client.subscribers.remove_tags("ada@example.com", ["beta"])
client.subscribers.activate("ada@example.com")
client.subscribers.deactivate("ada@example.com")
client.subscribers.unsubscribe("ada@example.com")
client.subscribers.resubscribe("ada@example.com")
client.subscribers.redact("ada@example.com")   # irreversible
```

`created_after` / `created_before` that fail to parse are **ignored** by the
server rather than rejected — they return a `parameter_ignored` warning, so a
bad timestamp silently widens your result set. Check `result.warnings`.

### Broadcasts

```python
client.broadcasts.create(subject="Weekly", body="<p>Hi</p>")
client.broadcasts.send(id)                       # no undo
client.broadcasts.schedule(id, scheduled_send_at="2026-08-01T09:00:00Z", scheduled_timezone="UTC")
client.broadcasts.cancel_schedule(id)
client.broadcasts.statistics(id)
client.broadcasts.statistics_timeline(id)
client.broadcasts.statistics_links(id)
```

### Sequences

```python
client.sequences.get(id, include_steps=True)
client.sequences.add_subscriber(id, email="ada@example.com")
client.sequences.remove_subscriber(id, "ada@example.com")
client.sequences.create_step(id, subject="Day 1")
client.sequences.move_step(id, step_id, under_id)
```

### Segments, templates, opt-in forms

```python
client.segments.create(name="VIPs")
client.templates.create(label="Welcome", subject="Hi", body="...")
client.opt_in_forms.analytics(id, start_date=date(2026, 1, 1))
client.opt_in_forms.create_variant(id, name="B", weight=50)
client.opt_in_forms.duplicate(id, label="Copy")
```

Reading a segment recounts its members server-side, so `segments.get` is not free.

### Email servers

**Credential redaction guard.** The API returns credentials bullet-masked
(`••••••••`). A naive fetch-modify-save would write those bullets back and
destroy a working SMTP password. `update()` strips any credential field whose
value matches the redaction pattern and warns:

```python
server = client.email_servers.get(id)
server["smtp_password"]                      # '••••••••'
client.email_servers.update(id, name="Renamed", smtp_password=server["smtp_password"])
# -> sends only {"name": "Renamed"}, warns about the dropped field
```

### Autopilot

```python
client.autopilots.create(name="Weekly", ai_model="openai/gpt-4o")
client.autopilots.activate(id)
client.autopilots.trigger_run(id)     # 202 — async, poll runs()
client.autopilots.runs(id, limit=10)
```

`activate` requires an active source, an API key, and a model. Sources and tone
samples have **no API endpoints** — they live in the web UI, so an autopilot
created entirely over the API cannot be activated until a source is added there.

### Transactional email

```python
client.transactionals.create(
    to="ada@example.com",
    subject="Receipt",
    body="<p>Thanks</p>",
    idempotency_key="receipt-{}".format(order.id),
)
```

The server stores the response for 24 hours keyed on (token, key) and replays it
rather than sending a second email. The key is part of a fingerprint over
method + path + body:

- same key, same payload, still running → `ConflictError` (409)
- same key, **different** payload → `ValidationError` (422)

That 422 means "this key was already used for something else", not that the
email was invalid. Do not retry it with the same key.

This is the only endpoint that accepts `Idempotency-Key`.

### Discovery

```python
client.whoami()   # token identity and permissions
client.status()   # channel readiness — check before a send
client.prime()    # full capability manifest
client.skill()    # plain-text agent skill manifest (a str)
```

### Migration / export

Read-only. **Admin tokens only**, and every call needs a `broadcast_channel_id`.

```python
client = Broadcast(..., broadcast_channel_id=42)

client.migration.manifest()

for sub in client.migration.each_record("subscribers"):
    ...   # auto-pages; advances by the limit the server actually applied

data = client.migration.download_file_asset(id)   # bytes
```

On a demo instance this entire API returns **403 for every request**, valid
token or not — deliberately, so a public demo cannot be used as a token oracle.
It surfaces as `AuthorizationError`.

---

## Channel scoping

```python
with client.with_channel(123):
    client.email_servers.list()   # scoped to channel 123
```

The previous scope is restored on exit, including when the block raises. The
override lives on the client instance, so concurrent use across threads will
interleave — use one client per thread, or pass `broadcast_channel_id`
explicitly.

---

## Webhooks

```python
from broadcast_python import webhook

valid = webhook.verify(
    raw_body,                        # the raw bytes, not a re-serialised dict
    request.headers["X-Broadcast-Signature"],
    request.headers["X-Broadcast-Timestamp"],
    os.environ["WEBHOOK_SECRET"],
)
if not valid:
    return HttpResponse(status=401)
```

HMAC-SHA256 over `timestamp.payload`, `v1,<base64>` header format, 5-minute
timestamp tolerance, constant-time comparison. `verify` returns `False` for
every rejection rather than distinguishing them.

Pass the **raw** request body. Re-serialising a parsed dict changes the bytes
and verification will fail.

`broadcast_python.EVENT_TYPES` lists all 32 event names.

---

## Development

```bash
python -m unittest discover -s tests    # mocked HTTP, no network

BROADCAST_LIVE_TEST=1 BROADCAST_HOST=http://localhost:3000 \
BROADCAST_API_TOKEN=... python -m unittest tests.test_live
```

The suite uses only the standard library — no pytest required.

---

## License

MIT
