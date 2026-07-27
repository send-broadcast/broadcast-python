"""Shared plumbing for resource classes.

The HTTP helpers are underscore-prefixed so a resource can expose ``get`` and
``delete`` as its public API without shadowing them.
"""

from typing import Any, Dict, Optional


class BaseResource:
    def __init__(self, client: Any):
        self._client = client

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None, raw: bool = False) -> Any:
        return self._client.request("GET", path, params or {}, raw=raw)

    def _post(self, path: str, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> Any:
        return self._client.request("POST", path, body or {}, headers=headers)

    def _patch(self, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        return self._client.request("PATCH", path, body or {})

    def _delete(self, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        return self._client.request("DELETE", path, body)

    def _warn(self, message: str) -> None:
        """Emit through the configured logger, else stderr."""
        logger = self._client.config.logger
        if logger is not None:
            logger.warning(message)
        else:
            import sys

            print(message, file=sys.stderr)


def compact(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Drop None values so an omitted argument never reaches the wire."""
    return {k: v for k, v in mapping.items() if v is not None}
