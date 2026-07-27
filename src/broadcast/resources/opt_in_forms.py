from datetime import date, datetime
from typing import Any, Optional, Union

from .base import BaseResource, compact

Id = Union[str, int]


class OptInForms(BaseResource):
    def list(self, **params: Any) -> Any:
        """Up to 250 per page with ``pagination`` metadata. Variants are excluded.

        Optional filters: ``filter`` (label substring), ``widget_type``, ``enabled``.
        """
        return self._get("/api/v1/opt_in_forms", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/opt_in_forms/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        """Attributes are wrapped under ``opt_in_form:``.

        Nested settings dicts (``theme_settings``, ``automation_settings``,
        ``security_settings``, ``trigger_settings``, ``widget_settings``) and
        the block arrays are passed through verbatim.
        """
        return self._post("/api/v1/opt_in_forms", {"opt_in_form": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        return self._patch("/api/v1/opt_in_forms/{}".format(id), {"opt_in_form": attrs})

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/opt_in_forms/{}".format(id))

    def analytics(
        self,
        id: Id,  # noqa: A002
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
    ) -> Any:
        """Performance analytics. Dates accept ``date``, ``datetime``, or ISO-8601
        strings; the server defaults to the last 30 days."""
        params = compact(
            {
                "start_date": _coerce_date(start_date) if start_date is not None else None,
                "end_date": _coerce_date(end_date) if end_date is not None else None,
            }
        )
        return self._get("/api/v1/opt_in_forms/{}/analytics".format(id), params)

    def create_variant(self, id: Id, name: Optional[str] = None, weight: Optional[int] = None) -> Any:  # noqa: A002
        body = compact({"name": name, "weight": weight})
        return self._post("/api/v1/opt_in_forms/{}/variants".format(id), body)

    def duplicate(self, id: Id, label: Optional[str] = None) -> Any:  # noqa: A002
        return self._post("/api/v1/opt_in_forms/{}/duplicate".format(id), compact({"label": label}))


def _coerce_date(value: Union[str, date, datetime]) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)
