"""一次请求的 DeepSeek 传输门；不重试、不跟随重定向、不接收路由覆盖。

Lifecycle: permanent
Owner: engineering workflow governance
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from hashlib import sha256
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import multiprocessing
import os
import secrets
import ssl
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from scripts.devops.independent_review_protocol import IndependentReviewProtocolError

PROVIDER_ENDPOINT = "https://api.deepseek.com/anthropic"
PROVIDER_HOST = "api.deepseek.com"
PROVIDER_PATH = "/anthropic/v1/messages?beta=true"
POLICY = "deepseek-single-request/v1"
MAX_REQUEST_BYTES = 512 * 1024
MAX_DECODED_REQUEST_BYTES = 60_000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SYSTEM_CA_FILE = "/etc/ssl/certs/ca-certificates.crt"
OUTPUT_LIMIT = 4096
EXPECTED_EVENT_COUNT = 3
SUCCESS_STATUS = 200


class TransportError(RuntimeError):
    """没有完整且受限的传输证据就不能产生 verdict。"""


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


class SingleRequestTransport(AbstractContextManager):
    """固定 TLS 上游；一轮 CLI 只能消耗一个不可补充的 provider request。"""

    def __init__(self, *, secret: str, prompt: str, timeout: int, attempt_path: Path):
        self._secret = secret
        self._prompt = prompt
        self._deadline = time.monotonic() + timeout
        self._local_token = secrets.token_hex(32)
        self._attempt_path = attempt_path
        self._file = attempt_path.open("xb")
        attempt_path.chmod(0o600)
        self._attempted = False
        self._failed = False
        self._evidence: dict[str, Any] | None = None
        self._connection: http.client.HTTPSConnection | None = None
        self._server = HTTPServer(("127.0.0.1", 0), self._handler())
        self._server.timeout = 0.1
        # Linux task process: parent can terminate/reap even blocked DNS/TLS.
        self._process = multiprocessing.get_context("fork").Process(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        self._record({"event": "START", "policy": POLICY})

    @property
    def cli_endpoint(self) -> str:
        """本轮专用 loopback 地址，不是 provider 路由配置。"""
        return f"http://127.0.0.1:{self._server.server_port}/anthropic"

    @property
    def cli_token(self) -> str:
        """仅用于本机请求认证；不把真实 provider secret 交给 CLI。"""
        return self._local_token

    def _record(self, value: dict[str, Any]) -> None:
        self._file.write(_json(value))
        self._file.flush()
        os.fsync(self._file.fileno())

    def _remaining(self) -> float:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TransportError("transport deadline exhausted")
        return remaining

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        transport = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                pass  # 禁止打印 provider/credential/prompt。

            def _request_body(self) -> bytes:
                if (
                    self.path != PROVIDER_PATH
                    or self.headers.get("Transfer-Encoding") is not None
                    or self.headers.get("Authorization") != f"Bearer {transport._local_token}"
                ):
                    raise TransportError("unapproved local request")
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or not lengths[0].isdigit():
                    raise TransportError("request length missing")
                length = int(lengths[0])
                if not 0 < length <= MAX_REQUEST_BYTES:
                    raise TransportError("request budget exceeded")
                body = self.rfile.read(length)
                if len(body) != length:
                    raise TransportError("request truncated")
                return body

            def do_POST(self) -> None:
                self.connection.settimeout(max(0.1, transport._deadline - time.monotonic()))
                try:
                    body = self._request_body()
                    response = transport._forward(body)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Content-Length", str(len(response)))
                    self.end_headers()
                    self.wfile.write(response)
                except (OSError, ValueError, http.client.HTTPException, TransportError):
                    transport._failed = True
                    transport._record({"event": "REJECTED", "attempted": transport._attempted})
                    # 不把上游 3xx 或 Location 暴露给会自动重定向的 CLI。
                    self.send_error(502, "bounded transport rejected")

        return Handler

    def _validate_body(self, body: bytes) -> None:
        if self._attempted or self._failed:
            raise TransportError("provider request quota exhausted")
        payload = json.loads(body)
        if (
            not isinstance(payload, dict)
            or payload.get("model") != "deepseek-flash"
            or payload.get("max_tokens") != OUTPUT_LIMIT
            or payload.get("stream") is not True
            or len(json.dumps(payload, ensure_ascii=False).encode()) > MAX_DECODED_REQUEST_BYTES
        ):
            raise TransportError("provider input budget/model mismatch")
        messages = payload.get("messages")
        if not isinstance(messages, list) or not any(
            message.get("role") == "user"
            and isinstance(message.get("content"), list)
            and any(
                part.get("type") == "text" and part.get("text") == self._prompt
                for part in message["content"]
                if isinstance(part, dict)
            )
            for message in messages
            if isinstance(message, dict)
        ):
            raise TransportError("canonical prompt absent from physical request")

    def _forward(self, body: bytes) -> bytes:
        self._validate_body(body)
        self._attempted = True  # 在 DNS/TLS/request 之前消耗额度；异常也不恢复。
        request_hash = sha256(body).hexdigest()
        self._record({"event": "ATTEMPT", "request_sha256": request_hash, "outcome": "UNKNOWN"})
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cafile=SYSTEM_CA_FILE)
        connection = http.client.HTTPSConnection(
            PROVIDER_HOST, timeout=self._remaining(), context=context
        )
        self._connection = connection
        try:
            connection.request(
                "POST",
                PROVIDER_PATH,
                body=body,
                headers={
                    "Authorization": f"Bearer {self._secret}",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "structured-outputs-2025-11-13",
                },
            )
            response = connection.getresponse()
            if (
                response.status != SUCCESS_STATUS
                or response.getheader("Content-Type", "").split(";")[0] != "text/event-stream"
            ):
                raise TransportError("non-success or redirected upstream")
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise TransportError("encoded upstream response")
            parts = bytearray()
            while True:
                if connection.sock is not None:
                    connection.sock.settimeout(self._remaining())
                part = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - len(parts)))
                if not part:
                    break
                parts.extend(part)
                if len(parts) > MAX_RESPONSE_BYTES:
                    raise TransportError("response budget exceeded")
            result = bytes(parts)
            content_length = response.getheader("Content-Length")
            if content_length is not None and (
                not content_length.isdigit() or int(content_length) != len(result)
            ):
                raise TransportError("truncated upstream HTTP body")
            if self._secret.encode() in result or self._local_token.encode() in result:
                raise TransportError("credential reflected by upstream")
            if b"event: message_stop" not in result:
                raise TransportError("incomplete upstream stream")
            self._evidence = {
                "policy": POLICY,
                "endpoint": PROVIDER_ENDPOINT,
                "physical_attempts": 1,
                "request_sha256": request_hash,
                "request_bytes": len(body),
                "prompt_sha256": sha256(self._prompt.encode()).hexdigest(),
                "response_sha256": sha256(result).hexdigest(),
                "response_bytes": len(result),
                "output_limit": OUTPUT_LIMIT,
                "redirects": 0,
                "retries": 0,
            }
            self._record({"event": "COMPLETE", **self._evidence})
            return result
        finally:
            connection.close()
            self._connection = None

    def evidence(self) -> dict[str, Any]:
        """只接受单一已完成 attempt，不推测失败 usage。"""
        events = [json.loads(line) for line in self._attempt_path.read_bytes().splitlines()]
        if len(events) != EXPECTED_EVENT_COUNT or [event.get("event") for event in events] != [
            "START",
            "ATTEMPT",
            "COMPLETE",
        ]:
            raise TransportError("no complete single-request evidence")
        evidence = dict(events[-1])
        evidence.pop("event")
        return {
            **evidence,
            "attempt_log": self._attempt_path.name,
            "attempt_log_sha256": sha256(self._attempt_path.read_bytes()).hexdigest(),
        }

    def __enter__(self) -> SingleRequestTransport:
        self._process.start()
        return self

    def __exit__(self, *_args) -> None:
        self._process.terminate()
        self._process.join(timeout=2)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout=2)
        if self._process.is_alive():
            raise TransportError("transport process could not be reaped")
        self._server.server_close()
        self._secret = self._local_token = self._prompt = ""
        self._file.close()


def validate_transport(evidence: Any, log: bytes, prompt: bytes) -> None:
    """读取侧验证物理 attempt artifact；不接受 receipt 自填的次数。"""
    try:
        events = [json.loads(line) for line in log.splitlines()]
        complete = dict(events[-1])
        complete.pop("event")
        if (
            not isinstance(evidence, dict)
            or len(events) != EXPECTED_EVENT_COUNT
            or [event.get("event") for event in events] != ["START", "ATTEMPT", "COMPLETE"]
            or events[0].get("policy") != POLICY
            or events[1].get("request_sha256") != complete.get("request_sha256")
            or {
                key: value
                for key, value in evidence.items()
                if key not in {"attempt_log", "attempt_log_sha256"}
            }
            != complete
            or evidence.get("attempt_log_sha256") != sha256(log).hexdigest()
            or evidence.get("policy") != POLICY
            or evidence.get("endpoint") != PROVIDER_ENDPOINT
            or evidence.get("physical_attempts") != 1
            or evidence.get("prompt_sha256") != sha256(prompt).hexdigest()
            or evidence.get("output_limit") != OUTPUT_LIMIT
            or evidence.get("redirects") != 0
            or evidence.get("retries") != 0
            or not 0 < evidence.get("request_bytes", 0) <= MAX_REQUEST_BYTES
            or not 0 < evidence.get("response_bytes", 0) <= MAX_RESPONSE_BYTES
        ):
            raise ValueError("invalid bounded transport evidence")  # noqa: TRY301
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise IndependentReviewProtocolError(
            "bounded physical attempt evidence is invalid"
        ) from exc
