from typing import Any, Dict, List, Optional, Union

from .base import BaseResource, compact

Id = Union[str, int]


class Users(BaseResource):
    """Manage installation users and their permissions.

    Every operation here requires an **admin API token** — a channel token
    gets ``403 {"error": "Admin API token required for user management"}``.
    Reads need the ``users_read`` scope, writes need ``users_write``.

    Sudo users are **read-only** through this API: update, deactivate,
    activate, delete, and permission writes on a sudo user all raise
    ``AuthorizationError`` (403). Sudo access itself can never be granted
    through the API, whether creating or updating a user or writing system
    permissions.
    """

    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        q: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List users. ``q`` searches email/name, ``status`` is ``"active"``
        or ``"inactive"``."""
        params = compact({"limit": limit, "offset": offset, "q": q, "status": status})
        return self._get("/api/v1/users", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/users/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        """Create a user. Requires either ``password`` or
        ``send_password_reset=True``."""
        return self._post("/api/v1/users", {"user": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        """Update a user. Raises ``AuthorizationError`` if the user is sudo."""
        return self._patch("/api/v1/users/{}".format(id), {"user": attrs})

    def deactivate(self, id: Id) -> Any:  # noqa: A002
        return self._post("/api/v1/users/{}/deactivate".format(id))

    def activate(self, id: Id) -> Any:  # noqa: A002
        """Reactivate a user. Also clears any account lockout."""
        return self._post("/api/v1/users/{}/activate".format(id))

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/users/{}".format(id))

    def channel_permissions(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/users/{}/channel_permissions".format(id))

    def set_channel_permissions(
        self,
        id: Id,  # noqa: A002
        broadcast_channel_id: Id,
        permissions: Optional[Dict[str, bool]] = None,
        role: Optional[str] = None,
        preset_id: Optional[Id] = None,
    ) -> Any:
        """Replace the user's whole permission record for one channel.

        This is a PUT: it replaces the record rather than merging into it, so
        passing ``permissions`` sets any flag not named to ``False``. Pass
        exactly one of ``permissions``, ``role``, or ``preset_id``.
        """
        body = _one_of(permissions=permissions, role=role, preset_id=preset_id)
        return self._put("/api/v1/users/{}/channel_permissions/{}".format(id, broadcast_channel_id), body)

    def remove_channel_permissions(self, id: Id, broadcast_channel_id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/users/{}/channel_permissions/{}".format(id, broadcast_channel_id))

    def bulk_channel_permissions(
        self,
        id: Id,  # noqa: A002
        broadcast_channel_ids: List[Id],
        permissions: Optional[Dict[str, bool]] = None,
        role: Optional[str] = None,
        preset_id: Optional[Id] = None,
    ) -> Any:
        """Apply the same permission record to several channels at once.

        Pass exactly one of ``permissions``, ``role``, or ``preset_id``.
        Returns ``{"applied": [...], "failed": [...]}`` — a failure on one
        channel does not roll back the others.
        """
        body = _one_of(permissions=permissions, role=role, preset_id=preset_id)
        body["broadcast_channel_ids"] = broadcast_channel_ids
        return self._post("/api/v1/users/{}/channel_permissions/bulk".format(id), body)

    def system_permissions(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/users/{}/system_permissions".format(id))

    def update_system_permissions(self, id: Id, permissions: Dict[str, bool]) -> Any:  # noqa: A002
        """Update only the named system permission flags.

        ``sudo_access`` is never present and sending it raises a 422 —
        sudo can never be granted through the API.
        """
        return self._patch("/api/v1/users/{}/system_permissions".format(id), {"permissions": permissions})


def _one_of(**kwargs: Any) -> Dict[str, Any]:
    given = {k: v for k, v in kwargs.items() if v is not None}
    if len(given) != 1:
        raise ValueError(
            "Pass exactly one of {} (got {})".format(", ".join(kwargs.keys()), len(given))
        )
    return given
