import unittest

from broadcast_python.response import Response, Warning_, RateLimit, build_response


class TestResponse(unittest.TestCase):
    """Python's dict subclassing makes the Ruby design work directly here.

    ``Response`` subclasses ``dict``, so ``result["id"]`` reads the body while
    ``result.status`` reads transport metadata — the same two namespaces the
    Ruby gem gets from ``Response < Hash``. Unlike the Node client, no
    workaround is needed: attribute and item access are separate in Python.
    """

    def test_behaves_as_the_parsed_body(self):
        result = build_response({"id": 42, "email": "a@b.com"}, 200, {})
        self.assertEqual(result["id"], 42)
        self.assertEqual(result, {"id": 42, "email": "a@b.com"})
        self.assertIsInstance(result, dict)

    def test_body_keys_named_status_and_warnings_are_reachable(self):
        result = build_response(
            {"status": "draft", "warnings": [{"code": "x", "param": "y", "message": "z"}]},
            201,
            {},
        )
        # The body's own values, by item access.
        self.assertEqual(result["status"], "draft")
        self.assertEqual(result["warnings"], [{"code": "x", "param": "y", "message": "z"}])
        # Transport metadata, by attribute access.
        self.assertEqual(result.status, 201)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].code, "x")

    def test_parses_warnings(self):
        result = build_response(
            {
                "warnings": [
                    {"code": "unrecognized_parameter", "param": "subscriber.foo", "message": "Unknown"},
                    {"code": "parameter_ignored", "param": None, "message": "Ignored"},
                ]
            },
            200,
            {},
        )
        self.assertEqual(len(result.warnings), 2)
        self.assertEqual(str(result.warnings[0]), "[unrecognized_parameter] subscriber.foo: Unknown")
        self.assertEqual(str(result.warnings[1]), "[parameter_ignored] Ignored")

    def test_skips_non_dict_warning_entries(self):
        result = build_response({"warnings": ["a string", None, {"code": "ok", "message": "m"}]}, 200, {})
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].code, "ok")

    def test_has_warnings(self):
        self.assertFalse(build_response({"id": 1}, 200, {}).has_warnings)
        self.assertFalse(build_response({"warnings": []}, 200, {}).has_warnings)
        self.assertTrue(build_response({"warnings": [{"code": "a", "message": "b"}]}, 200, {}).has_warnings)

    def test_parses_rate_limit_headers(self):
        result = build_response(
            {},
            200,
            {
                "x-ratelimit-limit": "120",
                "x-ratelimit-remaining": "118",
                "x-ratelimit-reset": "2026-07-26T12:00:00Z",
            },
        )
        self.assertIsInstance(result.rate_limit, RateLimit)
        self.assertEqual(result.rate_limit.limit, 120)
        self.assertEqual(result.rate_limit.remaining, 118)
        self.assertIsNotNone(result.rate_limit.reset)

    def test_rate_limit_is_none_without_the_header(self):
        self.assertIsNone(build_response({}, 200, {}).rate_limit)

    def test_unparseable_reset_becomes_none(self):
        result = build_response({}, 200, {"x-ratelimit-limit": "120", "x-ratelimit-reset": "not-a-time"})
        self.assertIsNone(result.rate_limit.reset)
        self.assertEqual(result.rate_limit.limit, 120)

    def test_header_lookup_is_case_insensitive(self):
        result = build_response({}, 200, {"X-RateLimit-Limit": "5"})
        self.assertEqual(result.rate_limit.limit, 5)

    def test_detects_an_idempotent_replay(self):
        self.assertTrue(build_response({}, 201, {"idempotency-replayed": "true"}).idempotent_replay)
        self.assertFalse(build_response({}, 201, {}).idempotent_replay)

    def test_non_dict_bodies_pass_through_unwrapped(self):
        result = build_response([{"id": 1}], 200, {})
        self.assertEqual(result, [{"id": 1}])
        self.assertNotIsInstance(result, Response)

    def test_warning_without_param_omits_it(self):
        warning = Warning_(code="c", param=None, message="m")
        self.assertEqual(str(warning), "[c] m")


if __name__ == "__main__":
    unittest.main()
