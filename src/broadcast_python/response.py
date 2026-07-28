"""The value returned by every JSON API call.

``Response`` subclasses ``dict`` rather than wrapping it, so everything that
works against a parsed body still works — ``result["id"]``, ``isinstance(...,
dict)``, ``**result``, equality against a plain dict. Transport metadata the API
sends alongside the body is exposed as attributes.

Python keeps item access and attribute access separate, so this reproduces the
Ruby gem's design exactly: ``result["status"]`` is the body's field and
``result.status`` is the HTTP status. (The Node client cannot do this — see its
README.)

    result = client.subscribers.create(email="a@b.com", foo="bar")
    result["id"]                   # 42
    result.warnings                # [Warning_(code='unrecognized_parameter', ...)]
    result.rate_limit.remaining    # 118
    result.status                  # 201
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, NamedTuple, Optional


class Warning_(NamedTuple):
    """A single entry from the API's ``warnings`` array.

    The API raises these on successful 2xx responses when it accepted the
    request but ignored part of it — an unrecognised parameter, a parameter that
    only applies in another mode, a value the server overrode.

    ``param`` is a dot-path to the offending parameter (e.g. ``subscriber.foo``).
    The API never includes submitted values, so a warning is safe to log.

    Named with a trailing underscore to avoid shadowing the builtin ``Warning``.
    """

    code: Optional[str]
    param: Optional[str]
    message: Optional[str]

    def __str__(self) -> str:
        if self.param:
            return "[{}] {}: {}".format(self.code, self.param, self.message)
        return "[{}] {}".format(self.code, self.message)


class RateLimit(NamedTuple):
    """Parsed ``X-RateLimit-*`` headers.

    ``reset`` is the time the current window rolls over, not a duration.
    """

    limit: int
    remaining: Optional[int]
    reset: Optional[datetime]


class Response(dict):
    """A parsed JSON object body plus its transport metadata."""

    __slots__ = ("_rate_limit", "_warnings", "headers", "status")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status: Optional[int] = None
        self.headers: Dict[str, str] = {}
        self._warnings: Optional[List[Warning_]] = None
        self._rate_limit: Any = _UNSET

    def _attach(self, status: int, headers: Dict[str, str]) -> "Response":
        self.status = status
        # Lower-cased once here so every lookup below is case-insensitive.
        self.headers = {str(k).lower(): v for k, v in (headers or {}).items()}
        return self

    @property
    def warnings(self) -> List[Warning_]:
        if self._warnings is None:
            entries = self.get("warnings")
            entries = entries if isinstance(entries, list) else []
            self._warnings = [
                Warning_(code=e.get("code"), param=e.get("param"), message=e.get("message"))
                for e in entries
                if isinstance(e, dict)
            ]
        return self._warnings

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def rate_limit(self) -> Optional[RateLimit]:
        if self._rate_limit is _UNSET:
            # A present-but-unparseable limit means the whole block is
            # untrustworthy, so report no rate limit rather than a RateLimit
            # whose `limit` is None despite being typed int.
            limit = _int_or_none(self.headers.get("x-ratelimit-limit"))
            if limit is None:
                self._rate_limit = None
            else:
                self._rate_limit = RateLimit(
                    limit=limit,
                    remaining=_int_or_none(self.headers.get("x-ratelimit-remaining")),
                    reset=_parse_time(self.headers.get("x-ratelimit-reset")),
                )
        return self._rate_limit

    @property
    def idempotent_replay(self) -> bool:
        """True when the API replayed a stored response for a repeated
        Idempotency-Key rather than performing the write again."""
        return self.headers.get("idempotency-replayed") == "true"


class _Unset:
    pass


_UNSET = _Unset()


def build_response(parsed: Any, status: int, headers: Dict[str, str]) -> Any:
    """Wrap a parsed JSON body when it is an object; pass anything else through.

    A bare array body is returned as a plain list and carries no metadata,
    matching the Ruby gem.
    """
    if not isinstance(parsed, dict):
        return parsed

    return Response(parsed)._attach(status, headers)


def _int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # fromisoformat did not accept a trailing Z until 3.11.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        pass
    # Some proxies send a unix timestamp instead of ISO-8601.
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None
