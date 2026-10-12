from typing import Any, Dict

from .base import BaseResource


class ChannelSettings(BaseResource):
    """The settings of the token's channel (Broadcast 2.46.0 or later).

    Grouped like the Settings pages: ``general``, ``sender``,
    ``unsubscribe_page`` (with the privacy policy and legal notice links) and
    ``confirmation_page``. Reading requires ``channel_settings_read`` and
    changing requires ``channel_settings_write``. There is no channel
    argument; the server reads the channel the token resolves to.
    """

    def get(self) -> Any:
        """Every channel setting, with defaults resolved."""
        return self._get("/api/v1/channel/settings")

    def update(self, settings: Dict[str, Any]) -> Any:
        """Change channel settings.

        Partial: send only the groups and keys that change. Nested text and
        colours merge, an empty string or None removes a value, and
        ``languages`` replaces the list. Returns every setting after the
        change; read ``result.warnings`` for anything the server ignored or
        changed.
        """
        return self._patch("/api/v1/channel/settings", {"channel_settings": settings})
