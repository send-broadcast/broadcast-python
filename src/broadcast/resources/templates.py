from typing import Any, Union

from .base import BaseResource

Id = Union[str, int]


class Templates(BaseResource):
    def list(self, **params: Any) -> Any:
        return self._get("/api/v1/templates", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/templates/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        """Create a template. Attributes are wrapped under ``template:``.

        Content: ``label``, ``subject``, ``preheader``, ``body``, ``html_body``.

        Confirmation templates (double opt-in): ``template_purpose``,
        ``confirmation_text``, ``default_confirmation``, and
        ``confirmation_page_settings`` — per-state page copy keyed by state,
        each taking ``{"heading": ..., "body": ...}``.

        Anything the server does not recognise comes back as an
        ``unrecognized_parameter`` warning rather than an error.
        """
        return self._post("/api/v1/templates", {"template": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        return self._patch("/api/v1/templates/{}".format(id), {"template": attrs})

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/templates/{}".format(id))
