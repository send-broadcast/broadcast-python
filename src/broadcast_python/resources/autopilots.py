import re
from typing import Any, Dict, Union

from .base import BaseResource

Id = Union[str, int]

#: The API renders a configured key bullet-masked and never returns the real
#: value. Writing a masked value back would replace a working credential with
#: bullets, so :meth:`Autopilots.update` strips it — the same guard as
#: :mod:`email_servers`.
REDACTED_KEY_PATTERN = re.compile(r"\A•+\Z")


class Autopilots(BaseResource):
    """Autopilot — AI-generated newsletters.

    Requires the ``autopilot_read`` / ``autopilot_write`` token permissions.

    Sources and tone samples have no API endpoints; they are configured in the
    web UI. Since :meth:`activate` requires an active source, an autopilot
    created entirely over the API cannot be activated until a source is added
    there.
    """

    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/autopilots", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/autopilots/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        """Attributes are wrapped under ``autopilot:``.

        ``name`` is required and unique per channel. ``openrouter_api_key`` is
        write-only. Scheduling takes ``schedule_frequency`` (daily, weekly,
        biweekly, monthly), ``schedule_day_of_week``, ``schedule_day_of_month``,
        ``schedule_time``, ``schedule_timezone``. ``segment_ids`` restricts the
        newsletter's audience.
        """
        return self._post("/api/v1/autopilots", {"autopilot": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        """Pass the real key to rotate it, or omit the field. A masked key is dropped."""
        return self._patch("/api/v1/autopilots/{}".format(id), {"autopilot": self._scrub_key(attrs)})

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/autopilots/{}".format(id))

    # --- Lifecycle ---

    def activate(self, id: Id) -> Any:  # noqa: A002
        """Requires at least one active source, an API key, and a model.

        Raises :class:`ValidationError` naming the missing prerequisites
        otherwise, comma-joined.
        """
        return self._post("/api/v1/autopilots/{}/activate".format(id))

    def pause(self, id: Id) -> Any:  # noqa: A002
        return self._post("/api/v1/autopilots/{}/pause".format(id))

    def deactivate(self, id: Id) -> Any:  # noqa: A002
        return self._post("/api/v1/autopilots/{}/deactivate".format(id))

    def trigger_run(self, id: Id) -> Any:  # noqa: A002
        """Returns 202 — generation is asynchronous, so poll :meth:`runs`."""
        return self._post("/api/v1/autopilots/{}/trigger_run".format(id))

    def runs(self, id: Id, **params: Any) -> Any:  # noqa: A002
        """Generation runs, most recent first. Supports ``limit`` and ``offset``."""
        return self._get("/api/v1/autopilots/{}/runs".format(id), params)

    def _scrub_key(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        key = attrs.get("openrouter_api_key")
        if not isinstance(key, str) or not REDACTED_KEY_PATTERN.match(key):
            return attrs

        self._warn(
            "[broadcast-python] Dropped redacted openrouter_api_key from update payload — "
            "pass the real key or omit the field"
        )
        return {k: v for k, v in attrs.items() if k != "openrouter_api_key"}
