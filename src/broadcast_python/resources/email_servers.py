import re
from typing import Any, Dict, Optional, Union

from .base import BaseResource, compact

Id = Union[str, int]

#: Fields the API returns bullet-masked. Round-tripping one of these from a
#: fetch into an update would replace a working credential with bullets, so
#: :meth:`EmailServers.update` strips them. This is a data-loss guard.
REDACTED_FIELDS = (
    "smtp_password",
    "aws_access_key_id",
    "aws_secret_access_key",
    "outbound_aws_access_key_id",
    "outbound_aws_secret_access_key",
    "postmark_api_token",
    "inboxroad_api_token",
    "smtp_com_api_key",
)

#: Matches the API's redaction shape: 8 bullets, or 4-char prefix + bullets + 4-char suffix.
REDACTED_PATTERN = re.compile(r"\A(?:•{8}|.{0,4}•+.{0,4})\Z")


class EmailServers(BaseResource):
    def list(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._get("/api/v1/email_servers", compact({"limit": limit, "offset": offset}))

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/email_servers/{}".format(id))

    def create(self, **attrs: Any) -> Any:
        return self._post("/api/v1/email_servers", {"email_server": attrs})

    def update(self, id: Id, **attrs: Any) -> Any:  # noqa: A002
        """Update an email server.

        CAUTION: API responses redact credential fields with bullet characters.
        Never echo a fetched response back into update — this method scrubs
        values matching the redaction pattern, but you should pass only the
        fields you actually want to change.
        """
        return self._patch("/api/v1/email_servers/{}".format(id), {"email_server": self._scrub(attrs)})

    def delete(self, id: Id) -> Any:  # noqa: A002
        return self._delete("/api/v1/email_servers/{}".format(id))

    def test_connection(self, id: Id) -> Any:  # noqa: A002
        return self._post("/api/v1/email_servers/{}/test_connection".format(id))

    def copy_to_channel(self, id: Id, target_channel_id: Id) -> Any:  # noqa: A002
        """Requires an admin/system token. In SaaS mode the target channel is
        scoped to the token creator's account."""
        body = {"target_channel_id": target_channel_id}
        return self._post("/api/v1/email_servers/{}/copy_to_channel".format(id), body)

    def _scrub(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        scrubbed = {}
        for key, value in attrs.items():
            if key in REDACTED_FIELDS and isinstance(value, str) and REDACTED_PATTERN.match(value):
                self._warn(
                    "[broadcast-python] Dropped redacted {} from update payload — "
                    "pass the real credential or omit the field".format(key)
                )
                continue
            scrubbed[key] = value
        return scrubbed
