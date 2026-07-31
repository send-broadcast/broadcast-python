from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional, Union

from .configuration import Configuration
from .connection import Connection
from .resources.autopilots import Autopilots
from .resources.broadcasts import Broadcasts
from .resources.discovery import Discovery
from .resources.email_servers import EmailServers
from .resources.global_suppressions import GlobalSuppressions
from .resources.migration import Migration
from .resources.opt_in_forms import OptInForms
from .resources.segments import Segments
from .resources.sequences import Sequences
from .resources.subscribers import Subscribers
from .resources.suppressions import Suppressions
from .resources.templates import Templates
from .resources.transactionals import Transactionals
from .resources.webhook_endpoints import WebhookEndpoints

Id = Union[str, int]


class Broadcast:
    """Client for the Broadcast API.

        client = Broadcast(api_token="...", host="https://mail.example.com")
        client.subscribers.create(email="ada@example.com")
    """

    def __init__(self, **settings: Any):
        self.config = Configuration(**settings)
        self.config.validate()
        self._connection = Connection(self.config)
        self._channel_override: Optional[Id] = None

        self.subscribers = Subscribers(self)
        self.sequences = Sequences(self)
        self.broadcasts = Broadcasts(self)
        self.segments = Segments(self)
        self.templates = Templates(self)
        self.webhook_endpoints = WebhookEndpoints(self)
        self.transactionals = Transactionals(self)
        self.opt_in_forms = OptInForms(self)
        self.email_servers = EmailServers(self)
        self.autopilots = Autopilots(self)
        self.discovery = Discovery(self)
        #: The current channel's suppression list (plus ``check``, which
        #: reads the global list too).
        self.suppressions = Suppressions(self)
        #: The installation-wide suppression list. Requires an admin (system)
        #: API token.
        self.global_suppressions = GlobalSuppressions(self)
        #: Read-only export endpoints. Requires an admin (system) API token.
        self.migration = Migration(self)

    # --- Channel scoping (admin/system tokens) ---

    @contextmanager
    def with_channel(self, broadcast_channel_id: Id) -> Iterator["Broadcast"]:
        """Scope every request inside the block to a channel.

            with client.with_channel(123):
                client.email_servers.list()

        The previous scope is restored on exit, including when the block raises.
        The override lives on the client instance, so concurrent use of the same
        instance across threads will interleave — use one client per thread, or
        pass ``broadcast_channel_id`` explicitly.
        """
        previous = self._channel_override
        self._channel_override = broadcast_channel_id
        try:
            yield self
        finally:
            self._channel_override = previous

    # --- Transactional email (convenience shims) ---

    def send_email(
        self,
        to: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Any:
        """Thin wrapper around ``transactionals.create``. Use that directly for
        ``template_id``, ``double_opt_in``, ``preheader``, ``idempotency_key``."""
        return self.transactionals.create(to=to, subject=subject, body=body, reply_to=reply_to)

    def get_email(self, id: Id) -> Any:  # noqa: A002
        return self.transactionals.get(id)

    # --- Discovery (convenience shims) ---

    def whoami(self) -> Any:
        return self.discovery.whoami()

    def status(self) -> Any:
        return self.discovery.status()

    def prime(self) -> Any:
        return self.discovery.prime()

    def skill(self) -> str:
        return self.discovery.skill()

    # --- Internal ---

    def request(
        self,
        method: str,
        path: str,
        body_or_params: Any = None,
        headers: Optional[Dict[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        payload = self._inject_channel_scope(body_or_params)
        return self._connection.request(method, path, payload, headers=headers, raw=raw)

    @property
    def _active_channel_id(self) -> Optional[Id]:
        if self._channel_override is not None:
            return self._channel_override
        return self.config.broadcast_channel_id

    def _inject_channel_scope(self, body_or_params: Any) -> Any:
        """Auto-include broadcast_channel_id when configured and not already set."""
        channel_id = self._active_channel_id
        if channel_id is None:
            return body_or_params

        payload = dict(body_or_params) if isinstance(body_or_params, dict) else {}
        if payload.get("broadcast_channel_id") is not None:
            return payload

        payload["broadcast_channel_id"] = channel_id
        return payload
