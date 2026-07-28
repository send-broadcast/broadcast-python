from typing import Any, Union

from .base import BaseResource

Id = Union[str, int]


class WebhookEndpoints(BaseResource):
    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/webhook_endpoints", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/webhook_endpoints/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        """The ``secret`` is returned once, on create, and never again."""
        return self._post("/api/v1/webhook_endpoints", {"webhook_endpoint": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        return self._patch("/api/v1/webhook_endpoints/{}".format(id), {"webhook_endpoint": attrs})

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/webhook_endpoints/{}".format(id))

    def test(self, id: Id, event_type: str = "test.webhook") -> Any:  # noqa: A002
        return self._post("/api/v1/webhook_endpoints/{}/test".format(id), {"event_type": event_type})

    def deliveries(self, id: Id, **params: Any) -> Any:  # noqa: A002
        return self._get("/api/v1/webhook_endpoints/{}/deliveries".format(id), params)
