"""The installation-wide suppression list.

Addresses on it never receive mail from any channel. All operations require an
admin (system) API token — a channel token gets a 401.

There is deliberately no ``check`` here: checking is a per-channel question
(it reads the channel list too), so it lives on ``suppressions``.
"""

from typing import Any, List

from .base import BaseResource


class GlobalSuppressions(BaseResource):
    def list(self, **params: Any) -> Any:
        """List global suppressions (250 per page, with ``pagination``
        metadata; pass ``page``). Optional ``email`` filters by partial
        match."""
        return self._get("/api/v1/global_suppressions.json", params)

    def add(self, email: str) -> Any:
        """Add an address to the global list. Already-suppressed is a success
        (200 instead of 201)."""
        return self._post("/api/v1/global_suppressions.json", {"email": email})

    def remove(self, email: str) -> Any:
        """Remove an address from the global list only. Channels that
        suppressed the same address on their own account keep their block."""
        return self._delete("/api/v1/global_suppressions.json", {"email": email})

    def bulk_add(self, emails: List[str]) -> Any:
        """Add up to 10,000 addresses at once. Idempotent. Returns ``added``,
        ``already_suppressed``, and ``invalid`` counts."""
        return self._post("/api/v1/global_suppressions/bulk.json", {"emails": emails})

    def bulk_remove(self, emails: List[str]) -> Any:
        """Remove up to 10,000 addresses at once. Returns ``removed`` and
        ``not_found`` counts."""
        return self._delete("/api/v1/global_suppressions/bulk.json", {"emails": emails})
