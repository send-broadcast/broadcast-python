from typing import Any, Dict

from .base import BaseResource


class ChannelDesign(BaseResource):
    """The brand kit of the token's channel (Settings -> Brand Kit).

    Reading requires the ``templates_read`` permission (the kit is design
    metadata for templates) or, from Broadcast 2.46.0, ``channel_settings_read``.
    Changing it requires ``channel_settings_write`` (Broadcast 2.46.0 or later).
    There is no channel argument; the server reads the channel the token
    resolves to (for an admin token, the one set with ``with_channel`` or
    ``broadcast_channel_id``).
    """

    def get(self) -> Any:
        """The channel's brand kit, fully resolved (defaults filled in).

        Returns ``colors``, ``typography`` (``font`` key and the email-safe
        ``font_stack``), ``layout`` (``width``, ``radius``), and ``brand``
        (``logo_url`` as a public URL or None, ``logo_width``, ``website_url``,
        ``social_links``, ``social_icon_style``). Block emails built with the
        drag-and-drop editor inherit these values.
        """
        return self._get("/api/v1/channel/design")

    def update(self, design: Dict[str, Any]) -> Any:
        """Change the brand kit (Broadcast 2.46.0 or later).

        Partial: send only what changes, in the shape ``get()`` returns. An
        empty string or None puts a value back to its default;
        ``social_links`` replaces the list; ``font_stack`` and ``width`` are
        read-only. Set the logo with the ``logo_url`` of an image in the
        channel's file library (the server never fetches a URL). Returns the
        whole kit after the change; read ``result.warnings`` for anything the
        server ignored.
        """
        return self._patch("/api/v1/channel/design", {"channel_design": design})
