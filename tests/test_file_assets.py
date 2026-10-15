"""File Assets (Broadcast 2.48.0): the channel's file library.

Uploads are the one place the client sends multipart/form-data rather than
JSON, so these tests read the raw body bytes the transport produced.
"""

import base64
import io
import logging
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from broadcast_python import ValidationError
from support import make_client

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def path_of(url):
    return urlparse(url).path


def query_of(url):
    return parse_qs(urlparse(url).query)


class TestFileAssetsReads(unittest.TestCase):
    def test_list(self):
        client, opener, _ = make_client({"body": {"data": [{"id": 1, "filename": "logo.png"}], "total": 1}})
        result = client.file_assets.list(filter="logo", limit=10, offset=20)

        self.assertEqual((opener.last["method"], path_of(opener.last["url"])), ("GET", "/api/v1/file_assets"))
        self.assertEqual(query_of(opener.last["url"]), {"filter": ["logo"], "limit": ["10"], "offset": ["20"]})
        self.assertEqual(result["data"][0]["filename"], "logo.png")
        self.assertEqual(result["total"], 1)

    def test_get(self):
        client, opener, _ = make_client({"body": {"id": 7, "url": "https://mail.example.com/files/abc-logo.png"}})
        result = client.file_assets.get(7)

        self.assertEqual((opener.last["method"], path_of(opener.last["url"])), ("GET", "/api/v1/file_assets/7"))
        self.assertEqual(result["url"], "https://mail.example.com/files/abc-logo.png")


class TestFileAssetsUpload(unittest.TestCase):
    def assert_multipart(self, call):
        self.assertEqual((call["method"], path_of(call["url"])), ("POST", "/api/v1/file_assets"))
        self.assertTrue(
            call["headers"]["content-type"].startswith("multipart/form-data; boundary="),
            call["headers"]["content-type"],
        )
        self.assertIsNone(call["body"])

    def test_upload_from_a_path(self):
        handle, path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(handle, "wb") as f:
            f.write(PNG)
        self.addCleanup(os.remove, path)

        client, opener, _ = make_client({"status": 201, "body": {"id": 9}})
        result = client.file_assets.upload(path)

        self.assert_multipart(opener.last)
        data = opener.last["data"]
        name = os.path.basename(path)
        self.assertIn('name="file"; filename="{}"'.format(name).encode(), data)
        self.assertIn(b"Content-Type: image/png", data)
        self.assertIn(PNG, data)
        self.assertTrue(data.endswith(b"--\r\n"))
        self.assertEqual(result["id"], 9)

    def test_upload_from_a_binary_file_object_uses_its_name(self):
        handle, path = tempfile.mkstemp(suffix=".jpg")
        with os.fdopen(handle, "wb") as f:
            f.write(b"\xff\xd8\xff")
        self.addCleanup(os.remove, path)

        client, opener, _ = make_client({"status": 201, "body": {"id": 10}})
        with open(path, "rb") as f:
            client.file_assets.upload(f)

        data = opener.last["data"]
        self.assertIn('filename="{}"'.format(os.path.basename(path)).encode(), data)
        self.assertIn(b"Content-Type: image/jpeg", data)
        self.assertIn(b"\xff\xd8\xff", data)

    def test_upload_from_bytes_with_a_filename_and_restriction(self):
        client, opener, _ = make_client({"status": 201, "body": {"id": 11}})
        client.file_assets.upload(b"GIF89a", filename="banner.gif", channel_restricted=True)

        self.assert_multipart(opener.last)
        data = opener.last["data"]
        self.assertIn(b'filename="banner.gif"', data)
        self.assertIn(b"Content-Type: image/gif", data)
        self.assertIn(b'name="channel_restricted"\r\n\r\ntrue\r\n', data)

    def test_upload_content_type_can_be_given(self):
        client, opener, _ = make_client({"status": 201, "body": {"id": 12}})
        client.file_assets.upload(io.BytesIO(PNG), filename="logo", content_type="image/png")
        self.assertIn(b"Content-Type: image/png", opener.last["data"])

    def test_upload_of_bytes_or_an_unnamed_stream_needs_a_filename(self):
        client, opener, _ = make_client()
        with self.assertRaises(ValueError):
            client.file_assets.upload(PNG)
        with self.assertRaises(ValueError):
            client.file_assets.upload(io.BytesIO(PNG))
        self.assertEqual(opener.calls, [])

    def test_upload_sends_the_idempotency_key(self):
        client, opener, _ = make_client(
            {"status": 201, "body": {"id": 13}, "headers": {"content-type": "application/json", "Idempotency-Replayed": "true"}}
        )
        result = client.file_assets.upload(PNG, filename="logo.png", idempotency_key="logo-1")

        self.assertEqual(opener.last["headers"]["idempotency-key"], "logo-1")
        self.assertTrue(result.idempotent_replay)

    def test_upload_with_a_channel_scope_sends_it_as_a_form_field(self):
        client, opener, _ = make_client({"status": 201, "body": {"id": 14}}, broadcast_channel_id=42)
        client.file_assets.upload(PNG, filename="logo.png")
        self.assertIn(b'name="broadcast_channel_id"\r\n\r\n42\r\n', opener.last["data"])

    def test_upload_base64_sends_json(self):
        data = base64.b64encode(PNG).decode("ascii")
        client, opener, _ = make_client({"status": 201, "body": {"id": 15}})
        result = client.file_assets.upload_base64(filename="logo.png", data=data, content_type="image/png")

        self.assertEqual((opener.last["method"], path_of(opener.last["url"])), ("POST", "/api/v1/file_assets"))
        self.assertEqual(opener.last["headers"]["content-type"], "application/json")
        self.assertEqual(opener.last["body"], {"filename": "logo.png", "data": data, "content_type": "image/png"})
        self.assertEqual(result["id"], 15)

    def test_upload_errors_surface_as_validation_errors(self):
        client, _, _ = make_client({"status": 422, "body": {"error": "data is not valid base64"}})
        with self.assertRaises(ValidationError) as caught:
            client.file_assets.upload_base64(filename="x.png", data="!!")
        self.assertIn("not valid base64", str(caught.exception))

    def test_debug_log_does_not_dump_file_bytes(self):
        logger = logging.getLogger("broadcast-file-assets-test")
        client, _, _ = make_client({"status": 201, "body": {"id": 1}}, debug=True, logger=logger)
        with self.assertLogs(logger, level="DEBUG") as logs:
            client.file_assets.upload(PNG * 100, filename="logo.png")
        self.assertNotIn("IHDR", "\n".join(logs.output))


class TestFileAssetsDelete(unittest.TestCase):
    def test_delete(self):
        client, opener, _ = make_client({"body": {"message": "File asset deleted successfully"}})
        result = client.file_assets.delete(7)

        self.assertEqual((opener.last["method"], path_of(opener.last["url"])), ("DELETE", "/api/v1/file_assets/7"))
        self.assertEqual(result["message"], "File asset deleted successfully")

    def test_deleting_a_brand_kit_logo_raises_validation_error(self):
        message = "This file is the channel's Brand Kit logo. Choose another logo (or none) in Settings > Brand Kit"
        client, _, _ = make_client({"status": 422, "body": {"error": message}})
        with self.assertRaises(ValidationError) as caught:
            client.file_assets.delete(7)
        self.assertIn("Brand Kit logo", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
