"""
A minimal ASGI request driver.

Starlette's own ``TestClient`` needs httpx, which is not available in this
environment, and this sandbox does not permit binding sockets. A FastAPI app is
just an ASGI callable, though, so requests can be driven straight into it. This
harness exercises the real routing, dependency injection, Pydantic validation
and JSON serialisation — everything except the TCP layer itself.

Usage:

    from tools.asgi_client import Client
    from backend.main import app

    client = Client(app)
    response = client.get("/api/health")
    print(response.status, response.json())
"""

from __future__ import annotations

import asyncio
import json as jsonlib
from dataclasses import dataclass, field
from urllib.parse import urlencode


@dataclass
class Response:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def json(self):
        return jsonlib.loads(self.body.decode())

    @property
    def text(self) -> str:
        return self.body.decode()

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class Client:
    """Drives an ASGI app, including its lifespan startup and shutdown."""

    def __init__(self, app):
        self.app = app
        self._lifespan_started = False

    # -- lifespan ---------------------------------------------------------
    def startup(self) -> None:
        if self._lifespan_started:
            return
        asyncio.run(self._run_lifespan("startup"))
        self._lifespan_started = True

    async def _run_lifespan(self, phase: str) -> None:
        """Run the lifespan handler up to the given phase.

        The app is re-entered for each phase because we are not holding a
        persistent event loop; startup work here is idempotent (``init_db``
        only seeds an empty database), so this is safe.
        """
        messages = [{"type": f"lifespan.{phase}"}]
        sent: list[dict] = []
        done = asyncio.Event()

        async def receive():
            if messages:
                return messages.pop(0)
            await done.wait()
            return {"type": "lifespan.shutdown"}

        async def send(message):
            sent.append(message)
            if message["type"].endswith((".complete", ".failed")):
                done.set()

        task = asyncio.create_task(self.app({"type": "lifespan"}, receive, send))
        try:
            await asyncio.wait_for(done.wait(), timeout=30)
        finally:
            task.cancel()

        for message in sent:
            if message["type"].endswith(".failed"):
                raise RuntimeError(f"lifespan failed: {message}")

    # -- requests ---------------------------------------------------------
    def request(self, method: str, path: str, params: dict | None = None,
                json: dict | None = None, headers: dict | None = None) -> Response:
        self.startup()
        return asyncio.run(self._request(method, path, params, json, headers))

    def get(self, path: str, params: dict | None = None, headers: dict | None = None) -> Response:
        return self.request("GET", path, params=params, headers=headers)

    def post(self, path: str, json: dict | None = None, params: dict | None = None,
             headers: dict | None = None) -> Response:
        return self.request("POST", path, params=params, json=json, headers=headers)

    def patch(self, path: str, json: dict | None = None, params: dict | None = None,
              headers: dict | None = None) -> Response:
        return self.request("PATCH", path, params=params, json=json, headers=headers)

    async def _request(self, method: str, path: str, params: dict | None, json: dict | None,
                       extra_headers: dict | None = None) -> Response:
        body = jsonlib.dumps(json).encode() if json is not None else b""
        headers = [(b"host", b"testserver")]
        if json is not None:
            headers.append((b"content-type", b"application/json"))
            headers.append((b"content-length", str(len(body)).encode()))
        for key, value in (extra_headers or {}).items():
            headers.append((key.lower().encode(), str(value).encode()))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": urlencode(params or {}, doseq=True).encode(),
            "root_path": "",
            "headers": headers,
            "client": ("127.0.0.1", 0),
            "server": ("testserver", 80),
        }

        request_body = {"sent": False}

        async def receive():
            if not request_body["sent"]:
                request_body["sent"] = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        chunks: list[bytes] = []
        result = {"status": 500, "headers": {}}

        async def send(message):
            if message["type"] == "http.response.start":
                result["status"] = message["status"]
                result["headers"] = {
                    k.decode().lower(): v.decode() for k, v in message.get("headers", [])
                }
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await self.app(scope, receive, send)
        return Response(status=result["status"], headers=result["headers"], body=b"".join(chunks))
