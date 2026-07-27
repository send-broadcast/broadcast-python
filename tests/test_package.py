import pathlib
import re
import unittest

import broadcast
from broadcast import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    BroadcastError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from broadcast.version import VERSION

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestPackaging(unittest.TestCase):
    def test_version_matches_pyproject(self):
        # The User-Agent is built from VERSION. If it drifts from the packaged
        # version, server-side client attribution credits the wrong release.
        text = (ROOT / "pyproject.toml").read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(VERSION, match.group(1))
        self.assertEqual(broadcast.__version__, VERSION)

    def test_declares_no_runtime_dependencies(self):
        # The client is built on urllib so it cannot conflict with a pinned
        # requests or httpx in the host environment.
        text = (ROOT / "pyproject.toml").read_text()
        self.assertRegex(text, r"dependencies\s*=\s*\[\s*\]")

    def test_ships_a_py_typed_marker(self):
        self.assertTrue((ROOT / "src" / "broadcast" / "py.typed").exists())


class TestPublicSurface(unittest.TestCase):
    def test_exports_the_client(self):
        self.assertTrue(callable(broadcast.Broadcast))

    def test_error_hierarchy_nests_as_the_ruby_gem_does(self):
        self.assertTrue(issubclass(AuthenticationError, APIError))
        self.assertTrue(issubclass(AuthorizationError, APIError))
        self.assertTrue(issubclass(NotFoundError, APIError))
        self.assertTrue(issubclass(ConflictError, APIError))
        self.assertTrue(issubclass(RateLimitError, APIError))
        # ValidationError and TimeoutError are siblings of APIError, not children.
        self.assertFalse(issubclass(ValidationError, APIError))
        self.assertFalse(issubclass(TimeoutError, APIError))
        self.assertTrue(issubclass(ValidationError, BroadcastError))

    def test_broadcast_timeout_error_does_not_shadow_the_builtin(self):
        # Ours is deliberately named TimeoutError to match the Ruby gem, but it
        # must not be confused with the builtin one an except clause might catch.
        import builtins

        self.assertIsNot(TimeoutError, builtins.TimeoutError)

    def test_every_resource_is_reachable(self):
        client = broadcast.Broadcast(api_token="t", host="https://mail.example.com")
        for name in (
            "subscribers", "sequences", "broadcasts", "segments", "templates",
            "webhook_endpoints", "transactionals", "opt_in_forms", "email_servers",
            "autopilots", "discovery", "migration",
        ):
            self.assertTrue(hasattr(client, name), "missing resource: {}".format(name))

    def test_migration_exposes_all_eighteen_collections(self):
        client = broadcast.Broadcast(api_token="t", host="https://mail.example.com")
        for collection in broadcast.COLLECTIONS:
            self.assertTrue(
                callable(getattr(client.migration, collection, None)),
                "missing collection: {}".format(collection),
            )
        self.assertEqual(len(broadcast.COLLECTIONS), 18)

    def test_all_exports_resolve(self):
        for name in broadcast.__all__:
            self.assertTrue(hasattr(broadcast, name), "__all__ names a missing export: {}".format(name))


if __name__ == "__main__":
    unittest.main()
