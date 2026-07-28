from typing import Any, Union

from .base import BaseResource

Id = Union[str, int]


class Sequences(BaseResource):
    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/sequences", params)

    def get(self, id: Id, include_steps: bool = False) -> Any:  # noqa: A002
        return self._get("/api/v1/sequences/{}".format(id), {"include_steps": True} if include_steps else {})

    def create(self, **attrs: Any) -> Any:
        return self._post("/api/v1/sequences", attrs)

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        return self._patch("/api/v1/sequences/{}".format(id), attrs)

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/sequences/{}".format(id))

    # --- Subscriber enrollment ---

    def add_subscriber(self, sequence_id: Id, **attrs: Any) -> Any:
        return self._post("/api/v1/sequences/{}/add_subscriber".format(sequence_id), attrs)

    def remove_subscriber(self, sequence_id: Id, email: str) -> Any:
        return self._delete("/api/v1/sequences/{}/remove_subscriber".format(sequence_id), {"email": email})

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
        return self._post("/api/v1/sequences/{}/steps".format(sequence_id), attrs)

    def update_step(self, sequence_id: Id, step_id: Id, **attrs: Any) -> Any:
        return self._patch("/api/v1/sequences/{}/steps/{}".format(sequence_id, step_id), attrs)

    def move_step(self, sequence_id: Id, step_id: Id, under_id: Id) -> Any:
        """Reorders a step to sit directly after ``under_id``."""
        body = {"under_id": under_id}
        return self._post("/api/v1/sequences/{}/steps/{}/move".format(sequence_id, step_id), body)

    def delete_step(self, sequence_id: Id, step_id: Id) -> Any:
        return self._delete("/api/v1/sequences/{}/steps/{}".format(sequence_id, step_id))
