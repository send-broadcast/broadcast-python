from typing import Any, Dict, List

from .base import BaseResource


class Subscribers(BaseResource):
    def list(self, **params: Any) -> Any:
        """List subscribers, 250 per page with ``pagination`` metadata.

        Filters, all optional and combinable: ``is_active``, ``source``,
        ``created_after``, ``created_before``, ``tags`` (AND logic), ``email``
        (partial, case-insensitive), ``confirmation_status``, ``custom_data``
        (JSONB containment).

        An unparseable ``created_after``/``created_before`` is *ignored* by the
        server rather than rejected, and comes back as a ``parameter_ignored``
        warning — so a bad timestamp silently widens the result set unless you
        check ``result.warnings``.
        """
        return self._get("/api/v1/subscribers.json", params)

    def find(self, email: str) -> Any:
        return self._get("/api/v1/subscribers/find.json", {"email": email})

    def create(self, **attrs: Any) -> Any:
        """Create or upsert a subscriber.

        Attributes are wrapped under ``subscriber:`` on the wire, except
        ``double_opt_in`` and ``confirmation_template_id``, which the API
        expects at the top level.

        ``confirmed_at`` is admin-token only — it backdates the confirmation
        timestamp when migrating an already-confirmed list off another provider.
        It is ignored (with a warning) on update.

        ``unsubscribed_at`` is never settable here; use :meth:`unsubscribe`.
        """
        double_opt_in = attrs.pop("double_opt_in", None)
        confirmation_template_id = attrs.pop("confirmation_template_id", None)

        payload: Dict[str, Any] = {"subscriber": attrs}
        if double_opt_in is not None:
            payload["double_opt_in"] = double_opt_in
        if confirmation_template_id is not None:
            payload["confirmation_template_id"] = confirmation_template_id

        return self._post("/api/v1/subscribers.json", payload)

    def update(self, email: str, **attrs: Any) -> Any:
        return self._patch("/api/v1/subscribers.json", {"email": email, "subscriber": attrs})

    def add_tags(self, email: str, tags: List[str]) -> Any:
        return self._post("/api/v1/subscribers/add_tag.json", {"email": email, "tags": tags})

    def remove_tags(self, email: str, tags: List[str]) -> Any:
        return self._delete("/api/v1/subscribers/remove_tag.json", {"email": email, "tags": tags})

    def activate(self, email: str) -> Any:
        return self._post("/api/v1/subscribers/activate.json", {"email": email})

    def deactivate(self, email: str) -> Any:
        return self._post("/api/v1/subscribers/deactivate.json", {"email": email})

    def unsubscribe(self, email: str) -> Any:
        return self._post("/api/v1/subscribers/unsubscribe.json", {"email": email})

    def resubscribe(self, email: str) -> Any:
        return self._post("/api/v1/subscribers/resubscribe.json", {"email": email})

    def redact(self, email: str) -> Any:
        """Irreversible: scrubs personal data while keeping aggregate counts."""
        return self._post("/api/v1/subscribers/redact.json", {"email": email})
