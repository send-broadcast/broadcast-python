import base64
import hashlib
import hmac
import json
import unittest

from broadcast import webhook
from broadcast.webhook import (
    BROADCAST_EVENTS,
    EMAIL_EVENTS,
    EVENT_TYPES,
    SEQUENCE_EVENTS,
    SUBSCRIBER_EVENTS,
    SYSTEM_EVENTS,
)

SECRET = "whsec_test_secret"
PAYLOAD = json.dumps({"type": "email.delivered", "data": {"id": 1}})
NOW = 1_800_000_000


def sign(payload, timestamp, secret=SECRET):
    digest = hmac.new(
        secret.encode("utf-8"), "{}.{}".format(timestamp, payload).encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("ascii")


class TestVerify(unittest.TestCase):
    def test_accepts_a_correctly_signed_payload(self):
        self.assertTrue(webhook.verify(PAYLOAD, "v1," + sign(PAYLOAD, NOW), str(NOW), SECRET, NOW))

    def test_rejects_a_different_secret(self):
        signature = "v1," + sign(PAYLOAD, NOW, "wrong-secret")
        self.assertFalse(webhook.verify(PAYLOAD, signature, str(NOW), SECRET, NOW))

    def test_rejects_a_tampered_payload(self):
        signature = "v1," + sign(PAYLOAD, NOW)
        tampered = json.dumps({"type": "email.delivered", "data": {"id": 999}})
        self.assertFalse(webhook.verify(tampered, signature, str(NOW), SECRET, NOW))

    def test_rejects_a_stale_timestamp(self):
        old = NOW - 301
        self.assertFalse(webhook.verify(PAYLOAD, "v1," + sign(PAYLOAD, old), str(old), SECRET, NOW))

    def test_accepts_the_edge_of_the_window(self):
        edge = NOW - 300
        self.assertTrue(webhook.verify(PAYLOAD, "v1," + sign(PAYLOAD, edge), str(edge), SECRET, NOW))

    def test_rejects_a_future_timestamp(self):
        future = NOW + 301
        self.assertFalse(webhook.verify(PAYLOAD, "v1," + sign(PAYLOAD, future), str(future), SECRET, NOW))

    def test_rejects_a_signature_without_the_v1_prefix(self):
        self.assertFalse(webhook.verify(PAYLOAD, sign(PAYLOAD, NOW), str(NOW), SECRET, NOW))

    def test_rejects_an_empty_signature_after_the_prefix(self):
        self.assertFalse(webhook.verify(PAYLOAD, "v1,", str(NOW), SECRET, NOW))

    def test_rejects_none_arguments_rather_than_raising(self):
        signature = "v1," + sign(PAYLOAD, NOW)
        self.assertFalse(webhook.verify(None, signature, str(NOW), SECRET, NOW))
        self.assertFalse(webhook.verify(PAYLOAD, None, str(NOW), SECRET, NOW))
        self.assertFalse(webhook.verify(PAYLOAD, signature, None, SECRET, NOW))
        self.assertFalse(webhook.verify(PAYLOAD, signature, str(NOW), None, NOW))

    def test_rejects_a_wrong_length_signature_without_raising(self):
        self.assertFalse(webhook.verify(PAYLOAD, "v1,c2hvcnQ=", str(NOW), SECRET, NOW))

    def test_rejects_a_non_numeric_timestamp(self):
        signature = "v1," + sign(PAYLOAD, NOW)
        self.assertFalse(webhook.verify(PAYLOAD, signature, "not-a-number", SECRET, NOW))

    def test_defaults_to_the_current_time(self):
        import time

        current = int(time.time())
        self.assertTrue(webhook.verify(PAYLOAD, "v1," + sign(PAYLOAD, current), str(current), SECRET))


class TestComputeSignature(unittest.TestCase):
    def test_matches_an_independent_implementation(self):
        self.assertEqual(webhook.compute_signature(PAYLOAD, NOW, SECRET), sign(PAYLOAD, NOW))


class TestEventTypes(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(EMAIL_EVENTS), 8)
        self.assertEqual(len(SUBSCRIBER_EVENTS), 7)
        self.assertEqual(len(BROADCAST_EVENTS), 8)
        self.assertEqual(len(SEQUENCE_EVENTS), 7)
        self.assertEqual(len(SYSTEM_EVENTS), 2)
        self.assertEqual(len(EVENT_TYPES), 32)

    def test_no_duplicates(self):
        self.assertEqual(len(set(EVENT_TYPES)), len(EVENT_TYPES))

    def test_exact_server_side_names(self):
        for name in (
            "email.delivery_delayed",
            "broadcast.partial_failure",
            "sequence.subscriber_completed",
            "message.attempt.exhausted",
            "test.webhook",
        ):
            self.assertIn(name, EVENT_TYPES)


if __name__ == "__main__":
    unittest.main()
