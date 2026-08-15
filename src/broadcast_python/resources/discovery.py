from typing import Any

from .base import BaseResource


class Discovery(BaseResource):
    """Introspection endpoints.

    Built for agents and CLIs that need to discover what a token can do before
    acting, and equally useful as a deploy-time smoke check.
    """

    def whoami(self) -> Any:
        """Token label, type (channel_scoped or admin_cross_channel), per-resource
        permissions, and the resolved channel."""
        return self._get("/api/v1/whoami")

    def status(self) -> Any:
        """Channel sender config, subscriber counts, and per-feature transmission
        readiness. Worth calling before a send — ``readiness["broadcasts"]`` false
        means the channel has no usable email server or sender identity."""
        return self._get("/api/v1/status")

    def prime(self) -> Any:
        """Full capability manifest: platform version, token permissions, channel
        status, the endpoint list the token can reach, rate limit, and usage tips."""
        return self._get("/api/v1/prime")

    def skill(self) -> str:
        """Plain-text agent skill manifest (Markdown with YAML front matter),
        including the safety rules agents are expected to follow.

        Returns a ``str``, not a dict — this endpoint serves ``text/plain``.
        """
        return self._get("/api/v1/skill", raw=True)

    def openapi(self) -> str:
        """This installation's own OpenAPI document, as YAML.

        Returns a ``str``, not a dict — this endpoint serves
        ``application/yaml``.

        The server URL inside the document is rewritten by the installation to
        the host that served it, so the result feeds a client generator or an
        API explorer without hand-editing. Preferable to a spec copied from
        elsewhere: a 2.28 install serves the 2.28 surface, so the document
        cannot drift from the routes it describes.
        """
        return self._get("/api/v1/openapi", raw=True)
