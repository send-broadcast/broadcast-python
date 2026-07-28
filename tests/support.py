"""A urllib opener double, so the suite never opens a socket or sleeps."""

import io
import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError


class StubResponse:
    """Quacks like the object urllib.request.OpenerDirector.open returns."""

    def __init__(self, status: int, body: bytes, headers: Dict[str, str]):
        self.status = status
        self.code = status
        self._body = body
        self.headers = headers

    def read(self) -> bytes:
        return self._body

    def getheader(self, name: str, default: Any = None) -> Any:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return default

    def getheaders(self):
        return list(self.headers.items())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class RecordedCall(dict):
    pass


class StubOpener:
    """Replays queued responses and records every request it was given."""

    def __init__(self, stubs):
        self.queue: List[Dict[str, Any]] = list(stubs) if isinstance(stubs, list) else [stubs]
        self.calls: List[RecordedCall] = []

    def open(self, request, timeout=None):  # noqa: A002 - urllib's signature
        body = request.data.decode("utf-8") if request.data else None
        self.calls.append(
            RecordedCall(
                method=request.get_method(),
                url=request.full_url,
                headers={k.lower(): v for k, v in request.headers.items()},
                body=json.loads(body) if body else None,
                raw_body=body,
            )
        )

        stub = self.queue.pop(0) if len(self.queue) > 1 else self.queue[0]

        if stub.get("raises") is not None:
            raise stub["raises"]

        status = stub.get("status", 200)
        headers = stub.get("headers", {"content-type": "application/json"})

        if "text" in stub:
            payload = stub["text"].encode("utf-8") if isinstance(stub["text"], str) else stub["text"]
        else:
            payload = json.dumps(stub.get("body", {})).encode("utf-8")

        if status >= 400:
            # A real BytesIO, not a stub: HTTPError is a file-like object and
            # its finaliser calls close(), which a hand-rolled double lacks.
            raise HTTPError(request.full_url, status, "error", headers, io.BytesIO(payload))

        return StubResponse(status, payload, headers)

    @property
    def last(self) -> RecordedCall:
        return self.calls[-1]


class SleepSpy:
    def __init__(self):
        self.delays: List[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def make_client(stubs=None, **overrides):
    """A Broadcast client wired to a StubOpener."""
    from broadcast_python.client import Broadcast

    opener = StubOpener(stubs if stubs is not None else {"body": {}})
    sleep = SleepSpy()

    settings = dict(
        api_token="test-token",
        host="https://mail.example.com",
        retry_delay=0,
        opener=opener,
        sleep=sleep,
    )
    settings.update(overrides)

    client = Broadcast(**settings)
    return client, opener, sleep
