"""HTTP transport.

Owns request building, response/error mapping, retries, redirects, and warning
dispatch, so ``Broadcast`` stays a thin facade over configuration and resources.

Built on ``urllib`` from the standard library so the package has no runtime
dependencies and cannot conflict with a pinned ``requests`` or ``httpx``
elsewhere in the environment.
"""

import json
import socket
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse

from .configuration import Configuration
from .errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    WarningError,
)
from .response import build_response
from .version import VERSION

MAX_REDIRECTS = 3
REDIRECT_CODES = (301, 302, 307, 308)

ERROR_MAPPING = {
    401: (AuthenticationError, "Authentication failed"),
    403: (AuthorizationError, "Not authorized"),
    404: (NotFoundError, "Resource not found"),
    409: (ConflictError, "A request with this Idempotency-Key is still being processed"),
    422: (ValidationError, "Validation failed"),
}


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Stops urllib following redirects on our behalf.

    Every request carries ``Authorization: Bearer <token>``. urllib's default
    handler would follow a redirect to any host and take the token with it.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Connection:
    def __init__(self, config: Configuration):
        self.config = config

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        headers: Optional[Dict[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        url = self._build_url(path, method, payload)
        return self._retry_with_backoff(
            lambda: self._execute(method, url, payload, headers or {}, raw, 0)
        )

    # --- Request building ---------------------------------------------------

    def _build_url(self, path: str, method: str, payload: Any) -> str:
        url = "{}{}".format(self.config.host, path)
        if method == "GET" and _present(payload):
            url = "{}?{}".format(url, urlencode(_flatten_params(payload)))
        return url

    def _execute(
        self, method: str, url: str, payload: Any, extra_headers: Dict[str, Any], raw: bool, redirects: int
    ) -> Any:
        body = None
        if method != "GET" and _present(payload):
            body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Authorization", "Bearer {}".format(self.config.api_token))
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "broadcast-python/{}".format(VERSION))
        for key, value in (extra_headers or {}).items():
            if value is None:
                continue
            request.add_header(str(key), str(value))

        self._debug_request(method, url, body)

        opener = self.config.opener or _default_opener()
        try:
            response = opener.open(request, timeout=self.config.timeout)
        except HTTPError as error:
            status = error.code
            headers = dict(error.headers.items()) if error.headers else {}
            if status in REDIRECT_CODES:
                return self._follow_redirect(headers, status, method, url, extra_headers, raw, redirects)
            self._raise_for_status(status, _safe_read(error), headers)
            raise  # unreachable; _raise_for_status always raises
        except URLError as error:
            raise _transport_error(error)
        except socket.timeout as error:
            raise TimeoutError("Request timeout: {}".format(error))

        status = getattr(response, "status", None) or getattr(response, "code", 200)
        headers = _headers_of(response)
        payload_bytes = response.read()
        self._debug_response(status)

        if status in REDIRECT_CODES:
            return self._follow_redirect(headers, status, method, url, extra_headers, raw, redirects)

        return self._build_success(status, payload_bytes, headers, raw)

    # --- Redirects ----------------------------------------------------------
    #
    # A redirect nearly always means a misconfigured `host` (http vs https, a
    # bare apex that redirects to www, a stale domain). Two things are never
    # followed: writes, because replaying a send against an unexpected origin is
    # worse than failing; and anything that changes host, because the request
    # carries the API token.

    def _follow_redirect(self, headers, status, method, url, extra_headers, raw, redirects):
        location = _header(headers, "location")

        if method != "GET":
            raise APIError(
                "Host redirected {} {} to {}. Set `host` to the final URL — "
                "writes are not followed automatically.".format(method, url, location or "(no Location header)")
            )
        if location is None:
            raise APIError("Redirect from {} had no Location header".format(url))
        if redirects >= MAX_REDIRECTS:
            raise APIError("Too many redirects ({}) starting at {}".format(MAX_REDIRECTS, url))

        target = urljoin(url, location)
        if (urlparse(target).hostname or "").lower() != (urlparse(url).hostname or "").lower():
            raise APIError(
                "Host redirected {} to a different host ({}). Not following it — "
                "the request carries your API token. Set `host` to the correct "
                "instance URL.".format(url, target)
            )

        # The query string is already baked into the current URL.
        return self._execute("GET", target, None, extra_headers, raw, redirects + 1)

    # --- Responses ----------------------------------------------------------

    def _build_success(self, status: int, payload: bytes, headers: Dict[str, str], raw: bool) -> Any:
        if raw:
            return _raw_body(payload, headers)

        result = build_response(_parse_success_body(payload), status, headers)
        self._handle_warnings(result)
        return result

    def _raise_for_status(self, status: int, payload: bytes, headers: Dict[str, str]) -> None:
        message = _parse_error(payload)

        if status == 429:
            retry_after = _header(headers, "retry-after")
            raise RateLimitError(
                message or "Rate limit exceeded",
                retry_after=int(retry_after) if retry_after and str(retry_after).isdigit() else None,
            )

        mapping = ERROR_MAPPING.get(status)
        if mapping:
            error_class, default = mapping
            raise error_class(message or default)

        if status >= 500:
            raise APIError(message or "Server error ({})".format(status))

        raise APIError(message or "Unexpected response: {}".format(status))

    def _handle_warnings(self, result: Any) -> None:
        warnings = getattr(result, "warnings", None)
        if not warnings:
            return

        if self.config.warnings_mode == "raise":
            raise WarningError(warnings, result)
        if self.config.warnings_mode == "log" and self.config.logger is not None:
            for warning in warnings:
                self.config.logger.warning("[broadcast] {}".format(warning))

    # --- Retries ------------------------------------------------------------

    def _retry_with_backoff(self, operation):
        attempts = 0
        while True:
            attempts += 1
            try:
                return operation()
            except Exception as error:  # noqa: BLE001 - re-raised unless retryable
                if attempts >= self.config.retry_attempts or not _retryable(error):
                    raise
                self._sleep(self._delay_for(error, attempts))

    def _delay_for(self, error: Exception, attempts: int) -> float:
        """Honour Retry-After, but never sleep longer than max_retry_delay."""
        if isinstance(error, RateLimitError) and error.retry_after is not None:
            return min(error.retry_after, self.config.max_retry_delay)
        return min(self.config.retry_delay * attempts, self.config.max_retry_delay)

    def _sleep(self, seconds: float) -> None:
        (self.config.sleep or time.sleep)(seconds)

    # --- Debug logging ------------------------------------------------------

    def _debug_request(self, method: str, url: str, body: Optional[bytes]) -> None:
        if not self.config.debug or self.config.logger is None:
            return
        # Never log the Authorization header or the body: bodies carry
        # subscriber email addresses and credential fields.
        self.config.logger.debug(
            "[broadcast] -> {} {}{}".format(method, url, " (body redacted)" if body else "")
        )

    def _debug_response(self, status: int) -> None:
        if not self.config.debug or self.config.logger is None:
            return
        self.config.logger.debug("[broadcast] <- {}".format(status))


# --- Helpers ---------------------------------------------------------------


def _default_opener():
    return urllib.request.build_opener(_NoRedirects)


def _present(payload: Any) -> bool:
    return isinstance(payload, dict) and len(payload) > 0


def _flatten_params(params: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Arrays repeat as ``key[]``, dicts flatten to ``key[sub]``.

    Booleans are lowercased: Python's ``str(True)`` is ``"True"``, which Rails
    does not read as true.
    """
    result: List[Tuple[str, str]] = []

    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            result.extend(("{}[]".format(key), _stringify(v)) for v in value)
        elif isinstance(value, dict):
            result.extend(("{}[{}]".format(key, k), _stringify(v)) for k, v in value.items())
        else:
            result.append((str(key), _stringify(value)))

    return result


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _raw_body(payload: bytes, headers: Dict[str, str]) -> Any:
    """Raw endpoints serve text (/api/v1/skill) and binary file assets alike.

    Decoding a PNG as text would corrupt it, so only decode when the server
    actually declared a charset.
    """
    content_type = _header(headers, "content-type") or ""
    if "charset=" in content_type.lower():
        return payload.decode("utf-8", errors="replace")
    return payload


def _parse_success_body(payload: bytes) -> Any:
    text = payload.decode("utf-8", errors="replace").strip() if payload else ""
    if text == "":
        return {}
    try:
        return json.loads(text)
    except ValueError:
        # A 2xx that isn't JSON (an HTML error page from a proxy, say). Surface
        # it as an empty body rather than exploding — raw=True is the deliberate
        # way to read non-JSON endpoints.
        return {}


def _parse_error(payload: bytes) -> Optional[str]:
    try:
        body = json.loads(payload.decode("utf-8", errors="replace"))
    except (ValueError, AttributeError):
        return None
    if not isinstance(body, dict):
        return None

    if isinstance(body.get("error"), str):
        return body["error"]
    return _format_errors(body.get("errors"))


def _format_errors(errors: Any) -> Optional[str]:
    """ActiveModel errors arrive as ``{"field": ["msg", ...]}``."""
    if errors is None:
        return None
    if isinstance(errors, list):
        return ", ".join(str(e) for e in errors)
    if not isinstance(errors, dict):
        return None

    parts = []
    for field, messages in errors.items():
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        parts.append("{} {}".format(field, ", ".join(str(m) for m in messages)))
    return "; ".join(parts)


def _headers_of(response: Any) -> Dict[str, str]:
    headers = getattr(response, "headers", {}) or {}
    try:
        return dict(headers.items())
    except AttributeError:
        return dict(headers)


def _header(headers: Dict[str, str], name: str) -> Optional[str]:
    for key, value in (headers or {}).items():
        if str(key).lower() == name:
            return value
    return None


def _safe_read(error: HTTPError) -> bytes:
    """Read and close an error body.

    HTTPError is a file-like object; leaving it open leaks the underlying
    socket and raises ResourceWarning under -W error.
    """
    try:
        return error.read()
    except Exception:  # noqa: BLE001 - a body we cannot read is just no message
        return b""
    finally:
        try:
            error.close()
        except Exception:  # noqa: BLE001
            pass


def _transport_error(error: URLError) -> Exception:
    """DNS/TCP/TLS failures and timeouts alike arrive as URLError.

    They are transient often enough to be worth a retry, and TimeoutError is the
    class the retry loop honours.
    """
    return TimeoutError("Request timeout: {}".format(error.reason if hasattr(error, "reason") else error))


def _retryable(error: Exception) -> bool:
    if isinstance(error, (TimeoutError, RateLimitError)):
        return True
    # Only 5xx. A 422 is deterministic — retrying it is pure latency.
    if isinstance(error, APIError) and "Server error" in str(error):
        return True
    return False
