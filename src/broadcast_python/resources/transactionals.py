from typing import Any, Dict, Optional, Union

from .base import BaseResource

Id = Union[str, int]

MAX_IDEMPOTENCY_KEY_LENGTH = 255


class Transactionals(BaseResource):
    def create(
        self,
        to: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        reply_to: Optional[str] = None,
        preheader: Optional[str] = None,
        template_id: Optional[Id] = None,
        include_unsubscribe_link: Optional[bool] = None,
        double_opt_in: Optional[Any] = None,
        confirmation_template_id: Optional[Id] = None,
        subscriber: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        **extra: Any
    ) -> Any:
        """Send a transactional email.

        One of ``subject``/``body`` or ``template_id`` is required;
        ``template_id`` resolves subject and body server-side, and
        ``subject``/``body`` override the template.

        Idempotency
        -----------
        Pass ``idempotency_key`` to make a retry safe. The server stores the
        response for 24 hours keyed on (token, key) and replays it rather than
        sending a second email. Check ``result.idempotent_replay`` to tell a
        replay from a fresh send.

        The key is part of a fingerprint over method + full path + body:

        - same key, same payload, still running -> :class:`ConflictError` (409)
        - same key, *different* payload         -> :class:`ValidationError` (422)

        That 422 means "this key was already used for something else", not that
        the email was invalid — do not retry it with the same key.
        """
        payload: Dict[str, Any] = {"to": to}
        for key, value in (
            ("subject", subject),
            ("body", body),
            ("preheader", preheader),
            ("reply_to", reply_to),
            ("template_id", template_id),
            ("include_unsubscribe_link", include_unsubscribe_link),
            ("double_opt_in", double_opt_in),
            ("confirmation_template_id", confirmation_template_id),
            ("subscriber", subscriber),
        ):
            if value is not None:
                payload[key] = value
        payload.update(extra)

        headers = _idempotency_headers(idempotency_key)
        return self._post("/api/v1/transactionals.json", payload, headers=headers)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/transactionals/{}.json".format(id))


def _idempotency_headers(key: Optional[str]) -> Dict[str, str]:
    if key is None:
        return {}

    trimmed = str(key).strip()
    if trimmed == "":
        return {}

    if len(trimmed) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise ValueError(
            "idempotency_key must be {} characters or fewer (got {})".format(
                MAX_IDEMPOTENCY_KEY_LENGTH, len(trimmed)
            )
        )

    return {"Idempotency-Key": trimmed}
