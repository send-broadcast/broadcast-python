"""Inbound webhook verification."""

import base64
import hashlib
import hmac
import time
from typing import Optional

TIMESTAMP_TOLERANCE = 300  # 5 minutes

#: Every event type a webhook endpoint can subscribe to, mirroring
#: WebhookEndpoint::AVAILABLE_EVENT_TYPES server-side. Use these when creating
#: an endpoint — an unknown event type is dropped silently.
EMAIL_EVENTS = (
    "email.sent",
    "email.delivered",
    "email.delivery_delayed",
    "email.complained",
    "email.bounced",
    "email.opened",
    "email.clicked",
    "email.failed",
)

SUBSCRIBER_EVENTS = (
    "subscriber.created",
    "subscriber.updated",
    "subscriber.deleted",
    "subscriber.subscribed",
    "subscriber.unsubscribed",
    "subscriber.bounced",
    "subscriber.complained",
)

BROADCAST_EVENTS = (
    "broadcast.scheduled",
    "broadcast.queueing",
    "broadcast.sending",
    "broadcast.sent",
    "broadcast.failed",
    "broadcast.partial_failure",
    "broadcast.aborted",
    "broadcast.paused",
)

SEQUENCE_EVENTS = (
    "sequence.subscriber_added",
    "sequence.subscriber_completed",
    "sequence.subscriber_moved",
    "sequence.subscriber_removed",
    "sequence.subscriber_paused",
    "sequence.subscriber_resumed",
    "sequence.subscriber_error",
)

#: Delivery-machinery events, not content events.
SYSTEM_EVENTS = ("message.attempt.exhausted", "test.webhook")

EVENT_TYPES = EMAIL_EVENTS + SUBSCRIBER_EVENTS + BROADCAST_EVENTS + SEQUENCE_EVENTS + SYSTEM_EVENTS


def verify(
    payload: str,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
    secret: Optional[str],
    now: Optional[int] = None,
) -> bool:
    """Verify an inbound webhook.

    Returns ``False`` rather than raising for every rejection — a missing
    header, a stale timestamp, a bad signature. A handler should answer 401 for
    all of them identically, and distinguishing them invites leaking which check
    failed.

    ``payload`` must be the raw request body, exactly as received.
    Re-serialising a parsed object changes the bytes and verification fails.
    """
    if payload is None or signature_header is None or timestamp_header is None or secret is None:
        return False

    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError):
        return False

    current_time = int(time.time()) if now is None else int(now)
    if not timestamp_valid(timestamp, current_time):
        return False

    actual = extract_signature(signature_header)
    if actual is None:
        return False

    return secure_compare(compute_signature(payload, timestamp, secret), actual)


def compute_signature(payload: str, timestamp: int, secret: str) -> str:
    signed_content = "{}.{}".format(timestamp, payload)
    digest = hmac.new(
        secret.encode("utf-8") if isinstance(secret, str) else secret,
        signed_content.encode("utf-8") if isinstance(signed_content, str) else signed_content,
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def timestamp_valid(timestamp: int, current_time: Optional[int] = None) -> bool:
    current_time = int(time.time()) if current_time is None else current_time
    return abs(current_time - timestamp) <= TIMESTAMP_TOLERANCE


def extract_signature(header: str) -> Optional[str]:
    if not header.startswith("v1,"):
        return None
    signature = header[len("v1,"):]
    return signature or None


def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
