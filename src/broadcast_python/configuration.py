"""Client configuration and validation."""

import os
from typing import Any, Callable, Optional, Union

from .errors import ConfigurationError

#: How to handle the ``warnings`` array the API returns on successful writes.
#:
#: ``log``    — warn through ``logger`` if one is set (default)
#: ``raise``  — raise :class:`WarningError`; note the write already happened
#: ``ignore`` — leave them on the response for the caller to inspect
WARNINGS_MODES = ("log", "raise", "ignore")

#: Env vars use the same names as the Broadcast CLI's ``~/.config/broadcast/config``,
#: so a machine set up for the CLI can drive this client with no extra config.
ENV_HOST = "BROADCAST_HOST"
ENV_TOKEN = "BROADCAST_API_TOKEN"


class Configuration:
    """Settings for a :class:`broadcast.client.Broadcast` instance.

    Durations are in **seconds**, matching the Ruby gem.
    """

    __slots__ = (
        "api_token",
        "host",
        "timeout",
        "open_timeout",
        "retry_attempts",
        "retry_delay",
        "max_retry_delay",
        "warnings_mode",
        "logger",
        "debug",
        "broadcast_channel_id",
        "opener",
        "sleep",
    )

    def __init__(
        self,
        api_token: Optional[str] = None,
        host: Optional[str] = None,
        timeout: int = 30,
        open_timeout: int = 10,
        retry_attempts: int = 3,
        retry_delay: float = 1,
        max_retry_delay: float = 30,
        warnings_mode: str = "log",
        logger: Any = None,
        debug: bool = False,
        broadcast_channel_id: Optional[Union[str, int]] = None,
        opener: Any = None,
        sleep: Optional[Callable[[float], None]] = None,
    ):
        self.api_token = api_token if api_token is not None else os.environ.get(ENV_TOKEN)
        # No default host. Broadcast is self-hosted-first — every instance lives
        # at its own domain, so any built-in guess is wrong for nearly everyone.
        self.host = host if host is not None else os.environ.get(ENV_HOST)

        self.timeout = timeout
        self.open_timeout = open_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        # Ceiling for a server-supplied Retry-After. Without it a long
        # rate-limit window would block the caller for as long as the server asked.
        self.max_retry_delay = max_retry_delay

        self.warnings_mode = warnings_mode
        self.logger = logger
        self.debug = debug
        self.broadcast_channel_id = broadcast_channel_id

        # Injectable for tests, so the suite neither opens sockets nor sleeps.
        self.opener = opener
        self.sleep = sleep

    def validate(self) -> None:
        if _blank(self.api_token):
            raise ConfigurationError("api_token is required")
        if _blank(self.host):
            raise ConfigurationError(_host_missing_message())

        self.host = str(self.host).strip().rstrip("/")
        self._validate_host_scheme()
        self._validate_warnings_mode()

    def _validate_host_scheme(self) -> None:
        if str(self.host).startswith(("http://", "https://")):
            return
        raise ConfigurationError(
            "host must include a scheme (http:// or https://), got {!r}".format(self.host)
        )

    def _validate_warnings_mode(self) -> None:
        if self.warnings_mode in WARNINGS_MODES:
            return
        raise ConfigurationError(
            "warnings_mode must be one of {}, got {!r}".format(
                ", ".join(WARNINGS_MODES), self.warnings_mode
            )
        )


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _host_missing_message() -> str:
    return (
        "host is required — point it at your Broadcast instance, e.g. "
        "Broadcast(api_token='...', host='https://mail.example.com'). "
        "You can also set the {} environment variable.".format(ENV_HOST)
    )
