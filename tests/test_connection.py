import socket
import unittest
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from broadcast_python.errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    WarningError,
)
from support import make_client


def query(url):
    return parse_qs(urlparse(url).query)


class TestRequestBuilding(unittest.TestCase):
    def test_sends_bearer_auth_content_type_and_user_agent(self):
        client, opener, _ = make_client()
        client.discovery.whoami()

        headers = opener.last["headers"]
        self.assertEqual(headers["authorization"], "Bearer test-token")
        self.assertEqual(headers["content-type"], "application/json")
        self.assertRegex(headers["user-agent"], r"^broadcast-python/\d+\.\d+\.\d+$")

    def test_builds_the_url_from_host_and_path(self):
        client, opener, _ = make_client()
        client.discovery.whoami()
        self.assertEqual(opener.last["url"], "https://mail.example.com/api/v1/whoami")

    def test_get_params_become_a_query_string_not_a_body(self):
        client, opener, _ = make_client()
        client.subscribers.list(page=2, is_active=True)

        self.assertIsNone(opener.last["body"])
        self.assertEqual(query(opener.last["url"])["page"], ["2"])
        # Ruby sends true/false lowercase; Python's str(True) is "True".
        self.assertEqual(query(opener.last["url"])["is_active"], ["true"])

    def test_array_params_repeat_with_bracket_suffix(self):
        client, opener, _ = make_client()
        client.subscribers.list(tags=["a", "b"])
        self.assertEqual(query(opener.last["url"])["tags[]"], ["a", "b"])

    def test_dict_params_flatten(self):
        client, opener, _ = make_client()
        client.subscribers.list(custom_data={"plan": "pro"})
        self.assertEqual(query(opener.last["url"])["custom_data[plan]"], ["pro"])

    def test_none_params_are_dropped(self):
        client, opener, _ = make_client()
        client.subscribers.list(page=1, source=None)
        self.assertNotIn("source", query(opener.last["url"]))

    def test_empty_params_add_no_query_string(self):
        client, opener, _ = make_client()
        client.discovery.whoami()
        self.assertEqual(urlparse(opener.last["url"]).query, "")

    def test_writes_send_a_json_body(self):
        client, opener, _ = make_client({"status": 201, "body": {}})
        client.subscribers.create(email="a@b.com")

        self.assertEqual(opener.last["method"], "POST")
        self.assertEqual(opener.last["body"], {"subscriber": {"email": "a@b.com"}})

    def test_extra_headers_are_merged(self):
        client, opener, _ = make_client()
        client.transactionals.create(to="a@b.com", subject="s", body="b", idempotency_key="k1")
        self.assertEqual(opener.last["headers"]["idempotency-key"], "k1")


class TestResponses(unittest.TestCase):
    def test_parses_json_and_attaches_metadata(self):
        client, _, _ = make_client(
            {"status": 201, "body": {"id": 7}, "headers": {"content-type": "application/json", "x-ratelimit-limit": "120"}}
        )
        result = client.subscribers.create(email="a@b.com")

        self.assertEqual(result["id"], 7)
        self.assertEqual(result.status, 201)
        self.assertEqual(result.rate_limit.limit, 120)

    def test_empty_body_becomes_an_empty_dict(self):
        client, _, _ = make_client({"status": 204, "text": ""})
        self.assertEqual(client.broadcasts.delete(1), {})

    def test_non_json_2xx_becomes_an_empty_dict(self):
        client, _, _ = make_client({"status": 200, "text": "<html>proxy</html>", "headers": {"content-type": "text/html"}})
        self.assertEqual(client.discovery.whoami(), {})

    def test_raw_returns_text_when_a_charset_is_declared(self):
        client, _, _ = make_client(
            {"status": 200, "text": "# Skill", "headers": {"content-type": "text/plain; charset=utf-8"}}
        )
        result = client.discovery.skill()
        self.assertIsInstance(result, str)
        self.assertIn("# Skill", result)

    def test_raw_returns_bytes_without_a_charset(self):
        client, _, _ = make_client(
            {"status": 200, "text": b"\x89PNG\r\n", "headers": {"content-type": "image/png"}}
        )
        result = client.migration.download_file_asset(1)
        self.assertIsInstance(result, bytes)


class TestErrorMapping(unittest.TestCase):
    CASES = [
        (401, AuthenticationError, "Authentication failed"),
        (403, AuthorizationError, "Not authorized"),
        (404, NotFoundError, "Resource not found"),
        (409, ConflictError, "still being processed"),
        (422, ValidationError, "Validation failed"),
    ]

    def test_status_codes_map_to_typed_errors_with_defaults(self):
        for status, error_class, default in self.CASES:
            with self.subTest(status=status):
                client, _, _ = make_client({"status": status, "text": "not json"})
                with self.assertRaises(error_class) as ctx:
                    client.discovery.whoami()
                self.assertIn(default, str(ctx.exception))

    def test_prefers_the_api_error_message(self):
        client, _, _ = make_client({"status": 404, "body": {"error": "Subscriber not found"}})
        with self.assertRaises(NotFoundError) as ctx:
            client.discovery.whoami()
        self.assertEqual(str(ctx.exception), "Subscriber not found")

    def test_formats_an_activemodel_errors_hash(self):
        client, _, _ = make_client(
            {"status": 422, "body": {"errors": {"email": ["is invalid", "is taken"], "name": ["is required"]}}}
        )
        with self.assertRaises(ValidationError) as ctx:
            client.subscribers.create(email="x")
        self.assertEqual(str(ctx.exception), "email is invalid, is taken; name is required")

    def test_formats_an_errors_array(self):
        client, _, _ = make_client({"status": 422, "body": {"errors": ["too short", "too rude"]}})
        with self.assertRaises(ValidationError) as ctx:
            client.subscribers.create(email="x")
        self.assertEqual(str(ctx.exception), "too short, too rude")

    def test_429_carries_retry_after(self):
        client, _, _ = make_client(
            {"status": 429, "body": {"error": "Slow down"}, "headers": {"retry-after": "7", "content-type": "application/json"}},
            retry_attempts=1,
        )
        with self.assertRaises(RateLimitError) as ctx:
            client.discovery.whoami()
        self.assertEqual(ctx.exception.retry_after, 7)

    def test_5xx_names_the_status(self):
        client, _, _ = make_client({"status": 503, "text": ""}, retry_attempts=1)
        with self.assertRaises(APIError) as ctx:
            client.discovery.whoami()
        self.assertIn("Server error (503)", str(ctx.exception))


class TestRedirects(unittest.TestCase):
    def test_follows_a_same_host_get_redirect(self):
        client, opener, _ = make_client(
            [
                {"status": 301, "text": "", "headers": {"location": "https://mail.example.com/api/v1/whoami/"}},
                {"status": 200, "body": {"ok": True}},
            ]
        )
        self.assertTrue(client.discovery.whoami()["ok"])
        self.assertEqual(len(opener.calls), 2)

    def test_resolves_a_relative_location(self):
        client, opener, _ = make_client(
            [
                {"status": 302, "text": "", "headers": {"location": "/api/v2/whoami"}},
                {"status": 200, "body": {"ok": True}},
            ]
        )
        client.discovery.whoami()
        self.assertEqual(opener.calls[1]["url"], "https://mail.example.com/api/v2/whoami")

    def test_refuses_a_cross_host_redirect_because_the_token_would_travel(self):
        client, opener, _ = make_client(
            [{"status": 301, "text": "", "headers": {"location": "https://evil.example.net/api/v1/whoami"}}]
        )
        with self.assertRaises(APIError) as ctx:
            client.discovery.whoami()
        self.assertIn("different host", str(ctx.exception))
        self.assertIn("carries your API token", str(ctx.exception))
        self.assertEqual(len(opener.calls), 1)

    def test_host_comparison_is_case_insensitive(self):
        client, _, _ = make_client(
            [
                {"status": 301, "text": "", "headers": {"location": "https://MAIL.EXAMPLE.COM/api/v1/whoami"}},
                {"status": 200, "body": {"ok": True}},
            ]
        )
        self.assertTrue(client.discovery.whoami()["ok"])

    def test_never_follows_a_redirect_on_a_write(self):
        client, opener, _ = make_client(
            [{"status": 308, "text": "", "headers": {"location": "https://mail.example.com/api/v1/subscribers.json"}}]
        )
        with self.assertRaises(APIError) as ctx:
            client.subscribers.create(email="a@b.com")
        self.assertIn("writes are not followed automatically", str(ctx.exception))
        self.assertEqual(len(opener.calls), 1)

    def test_redirect_without_a_location_fails_clearly(self):
        client, _, _ = make_client([{"status": 301, "text": "", "headers": {}}])
        with self.assertRaises(APIError) as ctx:
            client.discovery.whoami()
        self.assertIn("no Location header", str(ctx.exception))

    def test_gives_up_after_three_redirects(self):
        client, _, _ = make_client(
            [{"status": 301, "text": "", "headers": {"location": "https://mail.example.com/a"}}] * 5
        )
        with self.assertRaises(APIError) as ctx:
            client.discovery.whoami()
        self.assertIn("Too many redirects (3)", str(ctx.exception))


class TestRetries(unittest.TestCase):
    def test_retries_a_5xx_then_succeeds(self):
        client, opener, _ = make_client([{"status": 500, "text": ""}, {"status": 200, "body": {"ok": True}}])
        self.assertTrue(client.discovery.whoami()["ok"])
        self.assertEqual(len(opener.calls), 2)

    def test_gives_up_after_retry_attempts(self):
        client, opener, _ = make_client({"status": 500, "text": ""}, retry_attempts=3)
        with self.assertRaises(APIError):
            client.discovery.whoami()
        self.assertEqual(len(opener.calls), 3)

    def test_retries_a_429_then_succeeds(self):
        client, opener, _ = make_client(
            [
                {"status": 429, "text": "", "headers": {"retry-after": "0"}},
                {"status": 200, "body": {"ok": True}},
            ]
        )
        self.assertTrue(client.discovery.whoami()["ok"])
        self.assertEqual(len(opener.calls), 2)

    def test_does_not_retry_a_422(self):
        client, opener, _ = make_client({"status": 422, "body": {"error": "nope"}})
        with self.assertRaises(ValidationError):
            client.subscribers.create(email="x")
        self.assertEqual(len(opener.calls), 1)

    def test_caps_a_long_retry_after_at_max_retry_delay(self):
        client, _, sleep = make_client(
            [
                {"status": 429, "text": "", "headers": {"retry-after": "3600"}},
                {"status": 200, "body": {"ok": True}},
            ],
            max_retry_delay=5,
            retry_delay=1,
        )
        client.discovery.whoami()
        self.assertEqual(sleep.delays, [5])

    def test_a_socket_timeout_becomes_timeout_error(self):
        client, _, _ = make_client({"raises": URLError(socket.timeout("timed out"))}, retry_attempts=1)
        with self.assertRaises(TimeoutError) as ctx:
            client.discovery.whoami()
        self.assertIn("Request timeout", str(ctx.exception))

    def test_a_connection_failure_is_retried_then_raised(self):
        client, opener, _ = make_client({"raises": URLError("connection refused")}, retry_attempts=2)
        with self.assertRaises(TimeoutError):
            client.discovery.whoami()
        self.assertEqual(len(opener.calls), 2)


class TestWarnings(unittest.TestCase):
    WARNED = {
        "body": {
            "id": 1,
            "warnings": [{"code": "unrecognized_parameter", "param": "subscriber.foo", "message": "Unknown"}],
        }
    }

    def test_log_mode_warns_and_returns(self):
        messages = []
        logger = type("L", (), {"warning": lambda self, m: messages.append(m)})()
        client, _, _ = make_client(self.WARNED, warnings_mode="log", logger=logger)

        result = client.subscribers.create(email="a@b.com")
        self.assertEqual(result["id"], 1)
        self.assertEqual(len(messages), 1)
        self.assertIn("unrecognized_parameter", messages[0])

    def test_raise_mode_raises_and_carries_the_response(self):
        client, _, _ = make_client(self.WARNED, warnings_mode="raise")
        with self.assertRaises(WarningError) as ctx:
            client.subscribers.create(email="a@b.com")

        self.assertEqual(len(ctx.exception.warnings), 1)
        # The write already happened — the response must be reachable.
        self.assertEqual(ctx.exception.response["id"], 1)

    def test_ignore_mode_is_silent(self):
        messages = []
        logger = type("L", (), {"warning": lambda self, m: messages.append(m)})()
        client, _, _ = make_client(self.WARNED, warnings_mode="ignore", logger=logger)

        result = client.subscribers.create(email="a@b.com")
        self.assertEqual(messages, [])
        self.assertEqual(len(result.warnings), 1)


if __name__ == "__main__":
    unittest.main()
