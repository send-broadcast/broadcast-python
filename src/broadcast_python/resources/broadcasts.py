from typing import Any, Union

from .base import BaseResource

Id = Union[str, int]


class Broadcasts(BaseResource):
    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/broadcasts", params)

    def get(self, id: Id) -> Any:  # noqa: A002 - mirrors the API's parameter name
        return self._get("/api/v1/broadcasts/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        """Nests the attributes under ``broadcast``: the server reads ``params.require(:broadcast)``,
        and Rails drops non-column keys (such as ``taggify_list``) from a flat body.
        A call that already passes ``broadcast={...}`` is sent as is.
        """
        return self._post("/api/v1/broadcasts", self._wrap("broadcast", attrs))

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        """Nests the attributes under ``broadcast``: the server reads ``params.require(:broadcast)``,
        and Rails drops non-column keys (such as ``taggify_list``) from a flat body.
        A call that already passes ``broadcast={...}`` is sent as is.
        """
        return self._patch("/api/v1/broadcasts/{}".format(id), self._wrap("broadcast", attrs))

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/broadcasts/{}".format(id))

    def send(self, id: Id) -> Any:  # noqa: A002
        """Sends immediately. There is no undo — the API has no unsend."""
        return self._post("/api/v1/broadcasts/{}/send_broadcast".format(id))

    def schedule(self, id: Id, scheduled_send_at: str, scheduled_timezone: str) -> Any:  # noqa: A002
        body = {"scheduled_send_at": scheduled_send_at, "scheduled_timezone": scheduled_timezone}
        # Verb and path stay on one line: the coverage scanner is line-based,
        # and wrapping the path onto its own line reads as unimplemented.
        return self._post("/api/v1/broadcasts/{}/schedule_broadcast".format(id), body)

    def cancel_schedule(self, id: Id) -> Any:  # noqa: A002
        return self._post("/api/v1/broadcasts/{}/cancel_schedule".format(id))

    def statistics(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/broadcasts/{}/statistics".format(id))

    def statistics_timeline(self, id: Id, **params: Any) -> Any:  # noqa: A002
        return self._get("/api/v1/broadcasts/{}/statistics/timeline".format(id), params)

    def statistics_links(self, id: Id, **params: Any) -> Any:  # noqa: A002
        return self._get("/api/v1/broadcasts/{}/statistics/links".format(id), params)
