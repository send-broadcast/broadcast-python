"""Error hierarchy, mirroring broadcast-ruby's lib/broadcast/errors.rb.

Note the shape: ``ValidationError`` and ``TimeoutError`` descend from
``BroadcastError``, NOT from ``APIError``. That is deliberate and matches the
Ruby gem — catching ``APIError`` gets you transport and status failures and
leaves validation to be handled explicitly.
"""

from typing import Any, List, Optional


class BroadcastError(Exception):
    """Base class for everything this package raises."""


class ConfigurationError(BroadcastError):
    pass


class APIError(BroadcastError):
    pass


class AuthenticationError(APIError):
    pass


class AuthorizationError(APIError):
    pass


class NotFoundError(APIError):
    pass


class ConflictError(APIError):
    """409 — an in-flight request is already using this Idempotency-Key.

    The original request is still processing; retrying after a short pause will
    either replay its stored response or run fresh if it failed.
    """


class RateLimitError(APIError):
    """429. ``retry_after`` is the seconds the server asked us to wait."""

    def __init__(self, message: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(BroadcastError):
    pass


class TimeoutError(BroadcastError):  # noqa: A001 - mirrors the Ruby gem's name
    pass


class DeliveryError(BroadcastError):
    pass


class WarningError(BroadcastError):
    """Raised instead of returning when ``warnings_mode`` is ``"raise"`` and a
    2xx response carried warnings.

    The request DID succeed — the write happened. Callers catching this must
    not assume anything was rolled back.
    """

    def __init__(self, warnings: List[Any], response: Any = None):
        self.warnings = warnings
        self.response = response
        joined = "; ".join(str(w) for w in warnings)
        super().__init__("API returned {} warning(s): {}".format(len(warnings), joined))
