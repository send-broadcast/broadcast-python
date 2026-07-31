"""The current channel's suppression list.

Addresses on it never receive broadcasts, sequences, or transactionals from
this channel. The installation-wide list is a separate resource — see
``global_suppressions`` — but ``check`` reads across both on purpose: it
answers the question an integration actually asks, "will this address receive
mail?".
"""

from typing import Any, List

from .base import BaseResource


class Suppressions(BaseResource):
    def list(self, **params: Any) -> Any:
        """List the channel's suppressions (250 per page, with ``pagination``
        metadata; pass ``page``). Optional ``email`` filters by partial,
        case-insensitive match."""
        return self._get("/api/v1/suppressions.json", params)

    def add(self, email: str) -> Any:
        """Add an address to the channel's suppression list.

        Adding an address that is already suppressed is a success (the server
        answers 200 instead of 201), so callers do not have to check first.
        """
        return self._post("/api/v1/suppressions.json", {"email": email})

    def remove(self, email: str) -> Any:
        """Remove an address from the channel's suppression list. Returns
        ``removed: False`` (not an error) when the address was not on it.
        Does not touch the global list."""
        return self._delete("/api/v1/suppressions.json", {"email": email})

    def bulk_add(self, emails: List[str]) -> Any:
        """Add up to 10,000 addresses at once. Idempotent: a retried batch
        cannot duplicate. Returns ``added``, ``already_suppressed``, and
        ``invalid`` counts."""
        return self._post("/api/v1/suppressions/bulk.json", {"emails": emails})

    def bulk_remove(self, emails: List[str]) -> Any:
        """Remove up to 10,000 addresses at once. Returns ``removed`` and
        ``not_found`` counts."""
        return self._delete("/api/v1/suppressions/bulk.json", {"emails": emails})

    def check(self, email: str) -> Any:
        """Will this address receive mail? Reads across both the global and
        the channel list — a globally blocked address reports
        ``suppressed: True`` here even though it is absent from the channel's
        own list. The response's ``scope`` says which list matched."""
        return self._get("/api/v1/suppressions/check.json", {"email": email})
