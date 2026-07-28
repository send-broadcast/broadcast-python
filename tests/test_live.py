"""Smoke test against a real Broadcast instance.

Skipped unless BROADCAST_LIVE_TEST=1, because it needs a token and a reachable
host:

    BROADCAST_LIVE_TEST=1 BROADCAST_HOST=http://localhost:3000 \\
    BROADCAST_API_TOKEN=... python -m unittest tests.test_live

The mocked suite proves the client builds the right requests. Only this proves
the server agrees — a header stripped by a proxy, a renamed field, or a route
that moved are all invisible to a stub.

Read-only by design: it must be safe to point at production.
"""

import os
import unittest

from broadcast_python import AuthenticationError, Broadcast

LIVE = os.environ.get("BROADCAST_LIVE_TEST") == "1"


@unittest.skipUnless(LIVE, "set BROADCAST_LIVE_TEST=1 to run")
class TestLiveSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Broadcast(
            host=os.environ.get("BROADCAST_HOST"),
            api_token=os.environ.get("BROADCAST_API_TOKEN"),
        )

    def test_whoami_identifies_the_token(self):
        result = self.client.whoami()
        self.assertTrue(result.get("token_type") or result.get("type"), result)
        self.assertEqual(result.status, 200)

    def test_status_reports_channel_readiness(self):
        self.assertIsInstance(self.client.status(), dict)

    def test_prime_returns_a_capability_manifest(self):
        result = self.client.prime()
        self.assertTrue(
            result.get("version") or result.get("platform") or result.get("endpoints"),
            "prime returned no manifest fields",
        )

    def test_skill_returns_plain_text(self):
        result = self.client.skill()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_subscribers_list_paginates(self):
        result = self.client.subscribers.list(page=1)
        self.assertTrue(isinstance(result, (dict, list)))

    def test_rate_limit_headers_are_parsed(self):
        result = self.client.whoami()
        if result.rate_limit is not None:
            self.assertGreater(result.rate_limit.limit, 0)

    def test_a_bad_token_is_rejected(self):
        bad = Broadcast(
            host=os.environ.get("BROADCAST_HOST"),
            api_token="definitely-not-a-real-token",
            retry_attempts=1,
        )
        with self.assertRaises(AuthenticationError):
            bad.whoami()


if __name__ == "__main__":
    unittest.main()
