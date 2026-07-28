import os
import unittest
from contextlib import contextmanager

from broadcast_python.configuration import ENV_HOST, ENV_TOKEN, Configuration
from broadcast_python.errors import ConfigurationError


@contextmanager
def env(**overrides):
    """Temporarily set (or clear, with None) environment variables."""
    saved = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestConfiguration(unittest.TestCase):
    def test_defaults_match_the_ruby_reference(self):
        with env(**{ENV_HOST: None, ENV_TOKEN: None}):
            config = Configuration()
            self.assertEqual(config.timeout, 30)
            self.assertEqual(config.open_timeout, 10)
            self.assertEqual(config.retry_attempts, 3)
            self.assertEqual(config.retry_delay, 1)
            self.assertEqual(config.max_retry_delay, 30)
            self.assertEqual(config.warnings_mode, "log")
            self.assertFalse(config.debug)
            self.assertIsNone(config.api_token)
            self.assertIsNone(config.host)
            self.assertIsNone(config.broadcast_channel_id)

    def test_reads_host_and_token_from_cli_env_vars(self):
        with env(**{ENV_HOST: "https://mail.example.com", ENV_TOKEN: "env-token"}):
            config = Configuration()
            self.assertEqual(config.host, "https://mail.example.com")
            self.assertEqual(config.api_token, "env-token")

    def test_explicit_settings_beat_the_environment(self):
        with env(**{ENV_HOST: "https://env.example.com", ENV_TOKEN: "env-token"}):
            config = Configuration(host="https://explicit.example.com", api_token="explicit")
            self.assertEqual(config.host, "https://explicit.example.com")
            self.assertEqual(config.api_token, "explicit")

    def test_requires_an_api_token(self):
        config = Configuration(host="https://mail.example.com", api_token="")
        with self.assertRaises(ConfigurationError) as ctx:
            config.validate()
        self.assertIn("api_token is required", str(ctx.exception))

    def test_requires_a_host_and_says_how_to_set_it(self):
        with env(**{ENV_HOST: None}):
            config = Configuration(api_token="token")
            with self.assertRaises(ConfigurationError) as ctx:
                config.validate()
            self.assertIn("host is required", str(ctx.exception))
            self.assertIn(ENV_HOST, str(ctx.exception))

    def test_strips_whitespace_and_trailing_slash_from_host(self):
        config = Configuration(api_token="t", host="  https://mail.example.com/  ")
        config.validate()
        self.assertEqual(config.host, "https://mail.example.com")

    def test_rejects_a_host_with_no_scheme(self):
        config = Configuration(api_token="t", host="mail.example.com")
        with self.assertRaises(ConfigurationError) as ctx:
            config.validate()
        self.assertIn("must include a scheme", str(ctx.exception))

    def test_accepts_http_as_well_as_https(self):
        config = Configuration(api_token="t", host="http://localhost:3000")
        config.validate()
        self.assertEqual(config.host, "http://localhost:3000")

    def test_rejects_an_unknown_warnings_mode(self):
        config = Configuration(api_token="t", host="https://a.com", warnings_mode="explode")
        with self.assertRaises(ConfigurationError) as ctx:
            config.validate()
        self.assertIn("warnings_mode must be one of", str(ctx.exception))

    def test_accepts_each_valid_warnings_mode(self):
        for mode in ("log", "raise", "ignore"):
            config = Configuration(api_token="t", host="https://a.com", warnings_mode=mode)
            config.validate()
            self.assertEqual(config.warnings_mode, mode)

    def test_rejects_an_unknown_keyword(self):
        # A typo in a setting name should fail loudly, not be silently ignored
        # and leave the caller wondering why their timeout had no effect.
        with self.assertRaises(TypeError):
            Configuration(api_token="t", host="https://a.com", timout=5)


if __name__ == "__main__":
    unittest.main()
