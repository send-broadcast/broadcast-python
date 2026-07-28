"""Read-only export endpoints under ``/api/migration/v1``.

Two things differ from the v1 API:

1. **Admin tokens only.** Channel-scoped tokens are rejected outright.
2. **broadcast_channel_id is required on every call.** Set it once via
   ``Broadcast(broadcast_channel_id=...)`` or ``client.with_channel(id)`` and it
   is attached automatically; otherwise pass it per call.

On a demo instance (``DEMO_MODE``) this entire API returns 403 for every
request, valid token or not, so a public demo cannot be used as a token oracle.
That surfaces here as :class:`AuthorizationError`.

Every list endpoint pages with ``limit`` (1..250, default 250) and ``offset``,
returning ``{"data": [...], "pagination": {...}}``.
"""

from typing import Any, Iterator, Union

from .base import BaseResource

Id = Union[str, int]

#: Endpoints that are a plain paginated list of the channel's records.
COLLECTIONS = (
    "channels",
    "subscribers",
    "templates",
    "segments",
    "sequences",
    "email_servers",
    "opt_in_forms",
    "broadcasts",
    "outbound_receipts",
    "webhook_endpoints",
    "tokens",
    "suppressions",
    "tags",
    "users",
    "link_redirects",
    "link_clicks",
    "subscriber_histories",
    "file_assets",
)


class Migration(BaseResource):
    def manifest(self, **params: Any) -> Any:
        """Export summary: format version, channel identity, per-resource counts,
        and recent-history totals. Call this first to size an export.

        ``days_history`` windows the time-bounded counts; the server clamps to 1..365.
        """
        return self._get("/api/migration/v1/manifest", params)

    def download_file_asset(self, id: Id, **params: Any) -> bytes:  # noqa: A002
        """Binary contents of a stored file asset — bytes, not JSON."""
        return self._get("/api/migration/v1/file_assets/{}/download".format(id), params, raw=True)

    def each_record(self, collection: str, limit: int = 250, **params: Any) -> Iterator[Any]:
        """Page through a collection, yielding each record.

            for sub in client.migration.each_record("subscribers"):
                ...

        Stops when the server reports ``has_more: False``, and advances by the
        limit the server actually applied rather than the one requested — the
        server clamps to 250, so trusting the request would skip records.
        """
        offset = 0
        while True:
            page = getattr(self, collection)(limit=limit, offset=offset, **params)
            records = page.get("data") or []
            for record in records:
                yield record

            pagination = page.get("pagination") or {}
            if not pagination.get("has_more"):
                return

            # `pagination.get("limit") or len(records)` would be wrong: Python's
            # `or` falls back on any falsy value, so a server-reported limit of
            # 0 would become len(records) and the loop would never terminate.
            # Ruby's `||` only falls back on nil, which is why the reference
            # implementation can spell it that way and this one cannot.
            advanced = pagination.get("limit")
            if advanced is None:
                advanced = len(records)

            try:
                advanced = int(advanced)
            except (TypeError, ValueError):
                return
            if advanced <= 0:
                return

            offset += advanced


def _make_collection_method(name: str):
    def method(self, **params: Any) -> Any:
        return self._get("/api/migration/v1/{}".format(name), params)

    method.__name__ = name
    method.__qualname__ = "Migration.{}".format(name)
    method.__doc__ = "Paginated export of the channel's {}.".format(name.replace("_", " "))
    return method


# Generated rather than hand-written: 18 near-identical methods invite the kind
# of copy-paste drift this whole SDK family exists to prevent. Declared in
# .api-coverage.yml so the coverage report still counts them.
for _collection in COLLECTIONS:
    setattr(Migration, _collection, _make_collection_method(_collection))
