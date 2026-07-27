"""Python client for the Broadcast email platform.

    from broadcast import Broadcast

    client = Broadcast(api_token="...", host="https://mail.example.com")
    client.subscribers.create(email="ada@example.com")

Works with any Broadcast instance — self-hosted or SaaS. No runtime
dependencies: the transport is built on the standard library's urllib.
"""

from . import webhook
from .client import Broadcast
from .configuration import ENV_HOST, ENV_TOKEN, WARNINGS_MODES, Configuration
from .errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    BroadcastError,
    ConfigurationError,
    ConflictError,
    DeliveryError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    WarningError,
)
from .resources.email_servers import REDACTED_FIELDS
from .resources.migration import COLLECTIONS
from .resources.transactionals import MAX_IDEMPOTENCY_KEY_LENGTH
from .response import RateLimit, Response, Warning_
from .version import VERSION
from .webhook import EVENT_TYPES

__version__ = VERSION

__all__ = [
    "Broadcast",
    "Configuration",
    "WARNINGS_MODES",
    "ENV_HOST",
    "ENV_TOKEN",
    "Response",
    "Warning_",
    "RateLimit",
    "BroadcastError",
    "ConfigurationError",
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ValidationError",
    "TimeoutError",
    "DeliveryError",
    "WarningError",
    "webhook",
    "EVENT_TYPES",
    "REDACTED_FIELDS",
    "COLLECTIONS",
    "MAX_IDEMPOTENCY_KEY_LENGTH",
    "VERSION",
    "__version__",
]
