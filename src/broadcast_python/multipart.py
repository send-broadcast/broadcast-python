"""multipart/form-data bodies, built by hand on the standard library.

urllib has no multipart encoder, and the package takes no runtime
dependencies, so the body is assembled here. It is built from bytes (not a
stream) on every attempt, which keeps a retry safe.
"""

import uuid
from typing import Any, Dict, NamedTuple, Tuple


class FilePart(NamedTuple):
    """A file in a multipart request: the bytes, and the filename and content
    type sent with them."""

    data: bytes
    filename: str
    content_type: str

    def __repr__(self) -> str:
        # Never the bytes: a repr ends up in logs and tracebacks.
        return "FilePart({!r}, {}, {} bytes)".format(self.filename, self.content_type, len(self.data))


def build(fields: Dict[str, Any]) -> Tuple[bytes, str]:
    """Returns the body and the Content-Type header. ``None`` values are left
    out; booleans are sent as ``true``/``false``, as Rails reads them."""
    boundary = "BroadcastPython{}".format(uuid.uuid4().hex)
    body = bytearray()

    for name, value in fields.items():
        if value is None:
            continue

        body += "--{}\r\n".format(boundary).encode("ascii")
        if isinstance(value, FilePart):
            body += 'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'.format(
                _quote(name), _quote(value.filename)
            ).encode("utf-8")
            body += "Content-Type: {}\r\n\r\n".format(value.content_type).encode("utf-8")
            body += value.data
        else:
            body += 'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(_quote(name)).encode("utf-8")
            body += _stringify(value).encode("utf-8")
        body += b"\r\n"

    body += "--{}--\r\n".format(boundary).encode("ascii")
    return bytes(body), "multipart/form-data; boundary={}".format(boundary)


def _quote(value: Any) -> str:
    """A quote or a line break in a name would end the header early."""
    return str(value).replace("\r", " ").replace("\n", " ").replace('"', "%22")


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
