from typing import Any, Union

from .base import BaseResource

Id = Union[str, int]


class Topics(BaseResource):
    """Subscriber topics: kinds of email subscribers opt in to or out of.

    A topic reads a top-level custom_data key (true, false, or no value) or a
    tag. Topics use the token's subscriber permissions.
    """

    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/topics.json", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/topics/{}.json".format(id), {})

    def create(self, **attrs: Any) -> Any:
        return self._post("/api/v1/topics", {"topic": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        return self._patch("/api/v1/topics/{}".format(id), {"topic": attrs})

    def delete(self, id: Id) -> Any:  # noqa: A002
        """Refused (422) while a broadcast or sequence uses the topic."""
        return self._delete("/api/v1/topics/{}".format(id))
