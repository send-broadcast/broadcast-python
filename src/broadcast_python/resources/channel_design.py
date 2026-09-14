from typing import Any

from .base import BaseResource


class ChannelDesign(BaseResource):
    """The brand kit of the token's channel (Settings -> Design). Read-only.

    Requires the ``templates_read`` permission: the kit is design metadata for
    templates. There is no channel argument; the server reads the channel the
    token resolves to (for an admin token, the one set with ``with_channel`` or
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
