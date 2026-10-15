import os
from typing import IO, Any, Optional, Tuple, Union

from ..multipart import FilePart
from .base import BaseResource, compact
from .transactionals import _idempotency_headers

Id = Union[str, int]

CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
}


class FileAssets(BaseResource):
    """The channel's file library (Broadcast 2.48.0 or later): images (PNG,
    JPEG, GIF, under 10 MB) with public URLs that never expire. Use a file's
    ``url`` in emails, or as the brand kit logo::

        file = client.file_assets.upload("logo.png")
        client.channel_design.update({"brand": {"logo_url": file["url"]}})

    Reading needs ``file_assets_read``; uploading and deleting need
    ``file_assets_write``.
    """

    def list(self, **params: Any) -> Any:
        """Files the channel can see, newest first. ``filter`` searches file
        names (closest matches first); ``limit`` and ``offset`` page.

        Returns ``{"data": [...], "total": n}``.
        """
        return self._get("/api/v1/file_assets", params)

    def get(self, id: Id) -> Any:  # noqa: A002
        return self._get("/api/v1/file_assets/{}".format(id), {})

    def upload(
        self,
        file: Union[str, "os.PathLike[str]", bytes, IO[bytes]],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        channel_restricted: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Upload a file as multipart/form-data.

        ``file`` is a path, a binary file object, or bytes. Bytes, and a file
        object without a ``name``, need ``filename``. The content type follows
        the file extension unless ``content_type`` is given.

        ``channel_restricted=True`` links the file to this channel only (the
        default is every channel, as in the web app). ``idempotency_key``
        makes a retry safe; see ``transactionals.create``.
        """
        data, name = _read_file(file, filename)
        part = FilePart(data, name, content_type or _content_type_for(name))
        fields = compact({"file": part, "channel_restricted": channel_restricted})

        headers = _idempotency_headers(idempotency_key)
        return self._client.request("POST", "/api/v1/file_assets", fields, headers=headers, multipart=True)

    def upload_base64(
        self,
        filename: str,
        data: str,
        content_type: Optional[str] = None,
        channel_restricted: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Upload base64-encoded bytes in a JSON body, for callers that
        already hold base64 (or cannot send multipart)."""
        payload = compact(
            {
                "filename": filename,
                "data": data,
                "content_type": content_type,
                "channel_restricted": channel_restricted,
            }
        )
        return self._post("/api/v1/file_assets", payload, headers=_idempotency_headers(idempotency_key))

    def delete(self, id: Id) -> Any:  # noqa: A002
        """A file that is a channel's brand kit logo is refused with
        ``ValidationError`` (422): choose another logo first."""
        return self._delete("/api/v1/file_assets/{}".format(id))


def _read_file(file: Any, filename: Optional[str]) -> Tuple[bytes, str]:
    if isinstance(file, (bytes, bytearray)):
        if filename is None:
            raise ValueError("filename is required when uploading bytes")
        return bytes(file), filename

    if hasattr(file, "read"):
        name = filename
        if name is None and isinstance(getattr(file, "name", None), str):
            name = os.path.basename(file.name)
        if name is None:
            raise ValueError("filename is required when uploading from a file object without a name")
        return file.read(), name

    path = os.fspath(file)
    with open(path, "rb") as f:
        return f.read(), filename or os.path.basename(path)


def _content_type_for(name: str) -> str:
    return CONTENT_TYPES.get(os.path.splitext(name)[1].lower(), "application/octet-stream")
