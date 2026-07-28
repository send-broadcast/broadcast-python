from typing import Any, Optional, Union

from .base import BaseResource

Id = Union[str, int]


class Segments(BaseResource):
    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/segments.json", params)

    def get(self, id: Id, page: Optional[int] = None) -> Any:  # noqa: A002
        """Reading a segment recounts its members server-side, so this is not free."""
        return self._get("/api/v1/segments/{}.json".format(id), {"page": page} if page else {})

    def create(self, **attrs: Any) -> Any:
        return self._post("/api/v1/segments", {"segment": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        return self._patch("/api/v1/segments/{}".format(id), {"segment": attrs})

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/segments/{}".format(id))
