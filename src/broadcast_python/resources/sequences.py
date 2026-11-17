from typing import Any, Union

from .base import BaseResource

Id = Union[str, int]


class Sequences(BaseResource):
    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/sequences", params)

    def get(self, id: Id, include_steps: bool = False) -> Any:  # noqa: A002
        return self._get("/api/v1/sequences/{}".format(id), {"include_steps": True} if include_steps else {})

    def create(self, **attrs: Any) -> Any:
        """Nests the attributes under ``sequence``: the server reads ``params.require(:sequence)``,
        and Rails drops non-column keys (such as ``taggify_list``) from a flat body.
        A call that already passes ``sequence={...}`` is sent as is.
        """
        return self._post("/api/v1/sequences", self._wrap("sequence", attrs))

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        """Nests the attributes under ``sequence``: the server reads ``params.require(:sequence)``,
        and Rails drops non-column keys (such as ``taggify_list``) from a flat body.
        A call that already passes ``sequence={...}`` is sent as is.
        """
        return self._patch("/api/v1/sequences/{}".format(id), self._wrap("sequence", attrs))

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/sequences/{}".format(id))

    # --- Subscriber enrollment ---
    #
    # Both nest the attributes under ``subscriber``, because the API reads them
    # with ``params.require(:subscriber)``. Sent flat, the server answers 400.

    def add_subscriber(self, sequence_id: Id, **attrs: Any) -> Any:
        """Enrolls a subscriber: ``add_subscriber(id, email=..., first_name=..., last_name=...)``.

        The client wraps the fields in ``subscriber``. A call that already passes
        ``subscriber={...}`` is sent as is.
        """
        body = attrs if isinstance(attrs.get("subscriber"), dict) else {"subscriber": attrs}
        return self._post("/api/v1/sequences/{}/add_subscriber".format(sequence_id), body)

    def remove_subscriber(self, sequence_id: Id, email: str) -> Any:
        body = {"subscriber": {"email": email}}
        return self._delete("/api/v1/sequences/{}/remove_subscriber".format(sequence_id), body)

    def list_subscribers(self, sequence_id: Id, page: int = 1) -> Any:
        return self._get("/api/v1/sequences/{}/list_subscribers".format(sequence_id), {"page": page})

    # --- Steps ---
    #
    # Steps hang off the sequences resource rather than a top-level one,
    # matching the nested routes.

    def list_steps(self, sequence_id: Id) -> Any:
        return self._get("/api/v1/sequences/{}/steps".format(sequence_id))

    def get_step(self, sequence_id: Id, step_id: Id) -> Any:
        return self._get("/api/v1/sequences/{}/steps/{}".format(sequence_id, step_id))

    def create_step(self, sequence_id: Id, **attrs: Any) -> Any:
        """Nests the attributes under ``sequence_step``: the server reads ``params.require(:sequence_step)``,
        and Rails drops non-column keys (such as ``taggify_list``) from a flat body.
        A call that already passes ``sequence_step={...}`` is sent as is.
        """
        body = self._wrap("sequence_step", attrs)
        return self._post("/api/v1/sequences/{}/steps".format(sequence_id), body)

    def update_step(self, sequence_id: Id, step_id: Id, **attrs: Any) -> Any:
        """Nests the attributes under ``sequence_step``: the server reads ``params.require(:sequence_step)``,
        and Rails drops non-column keys (such as ``taggify_list``) from a flat body.
        A call that already passes ``sequence_step={...}`` is sent as is.
        """
        body = self._wrap("sequence_step", attrs)
        return self._patch("/api/v1/sequences/{}/steps/{}".format(sequence_id, step_id), body)

    def move_step(self, sequence_id: Id, step_id: Id, under_id: Id) -> Any:
        """Reorders a step to sit directly after ``under_id``."""
        body = {"under_id": under_id}
        return self._post("/api/v1/sequences/{}/steps/{}/move".format(sequence_id, step_id), body)

    def delete_step(self, sequence_id: Id, step_id: Id) -> Any:
        return self._delete("/api/v1/sequences/{}/steps/{}".format(sequence_id, step_id))
