"""Python client for the Broadcast email platform.

    from broadcast_python import Broadcast

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
    "COLLECTIONS",
    "ENV_HOST",
    "ENV_TOKEN",
    "EVENT_TYPES",
    "MAX_IDEMPOTENCY_KEY_LENGTH",
    "REDACTED_FIELDS",
    "VERSION",
    "WARNINGS_MODES",
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "Broadcast",
    "BroadcastError",
    "Configuration",
    "ConfigurationError",
    "ConflictError",
    "DeliveryError",
    "NotFoundError",
    "RateLimit",
    "RateLimitError",
    "Response",
    "TimeoutError",
    "ValidationError",
    "WarningError",
    "Warning_",
    "__version__",
    "webhook",
]
