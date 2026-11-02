"""固定计划的局部 TLS broker；worker 不持有凭据、账本或网络。

lifecycle: permanent
只接受 task/slot，不接受 URL、模型、请求体、凭据或预算。当前仅本地 TLS 可执行。
"""

from __future__ import annotations

from contextlib import contextmanager, suppress
import http.client
import json
import os
import socket
import socketserver
import threading
from typing import TYPE_CHECKING

from scripts.devops.controlled_api_binding import HTTPS_CHANNEL
from scripts.devops.controlled_api_https import Credential, TLSFixture, post_once
from scripts.devops.controlled_api_policy import ControlError, positive_int, validate_plan
from scripts.devops.controlled_api_runner import _decode, _result
from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes

MAX_MESSAGE = 1024

if TYPE_CHECKING:
    from pathlib import Path

    from scripts.devops.controlled_api_budget import Budget


def _reject_secret(raw: bytes, credential: Credential) -> None:
    if credential.value.encode() in raw:
        raise ControlError("CREDENTIAL_IN_RESPONSE")


def _parse_frame(raw: bytes) -> dict:
    if len(raw) > MAX_MESSAGE or not raw.endswith(b"\n"):
        raise ControlError("INVALID_BROKER_FRAME")
    return _decode(raw)


class Broker:
    """Controller 绑定固定账本和候选；一次 claim 后所有异常都保留最大预留。"""

    def __init__(
        self,
        budget: Budget,
        task: str,
        plans: list[dict],
        credential: Credential,
        fixture: TLSFixture | None,
        *,
        timeout: float = 5,
    ):
        self.budget = budget
        self.task = task
        self.plans = tuple(canonical_json(validate_plan(plan)) for plan in plans)
        self.credential = credential
        self.fixture = fixture
        self.timeout = timeout
        budget.evidence(task)  # 未建账时不启动可发送入口。

    def execute(self, message: dict) -> dict:
        """消息只能选择冻结槽；不返回原始响应或秘密。"""
        if not isinstance(message, dict) or set(message) != {"task", "slot"}:
            raise ControlError("UNAUTHORIZED_BROKER_MESSAGE")
        slot = positive_int(message["slot"])
        if message["task"] != self.task or slot > len(self.plans):
            raise ControlError("UNAUTHORIZED_BROKER_MESSAGE")
        if self.fixture is None:
            raise ControlError("LIVE_BILLING_AND_DEPLOYMENT_ADMISSION_NOT_PROVEN")
        self.fixture.validate()
        self.credential.fixture_header()
        plan = json.loads(self.plans[slot - 1])
        self.budget.claim(self.task, slot, plan)
        raw = b""
        try:
            raw = post_once(plan, self.credential, fixture=self.fixture, timeout=self.timeout)
            _reject_secret(raw, self.credential)
            result = _result(raw, plan)
            _reject_secret(canonical_json(result), self.credential)
            # 非正式结果，与 source/请求/模型/执行身份一起持久化。写失败不授权、不退款。
            evidence = self.budget.evidence(self.task)
            artifact = {
                "schema": "controlled-api-unqualified-result/v1",
                "channel": HTTPS_CHANNEL,
                "reviewer_identity": f"{HTTPS_CHANNEL}/{plan['policy']['provider']}",
                "provider": plan["policy"]["provider"],
                "qualification_status": "NOT_RUN",
                "source": evidence["source"],
                "execution": evidence["execution"],
                "slot": slot,
                "request_sha256": plan["request_sha256"],
                "policy_sha256": plan["policy_sha256"],
                "model": plan["policy"]["model"],
                "response_sha256": sha256_bytes(raw),
                "result": result,
                "current_approval_eligible": False,
                "qualification_required": True,
            }
            target = self.budget.root / f"result-{self.task}-{slot}.json"
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(canonical_json(artifact))
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(self.budget.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException as exc:
            category = "RESPONSE_OR_PERSISTENCE_INVALID"
            if isinstance(exc, TimeoutError):
                category = "TIMEOUT"
            elif isinstance(exc, (OSError, http.client.HTTPException)):
                category = "TRANSPORT_OR_PERSISTENCE_FAILURE"
            self.budget.finish(
                self.task,
                slot,
                complete=False,
                category=category,
                response_sha256=sha256_bytes(raw),
            )
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise ControlError(category) from None
        self.budget.finish(
            self.task,
            slot,
            complete=True,
            category="VALID_LOCAL_TLS_RESPONSE",
            response_sha256=sha256_bytes(raw),
        )
        return self.budget.evidence(self.task)


@contextmanager
def serve(broker: Broker, directory: Path):
    """在全新私有 socket 目录提供固定任务服务；不复用未知现有路径。"""
    directory.mkdir(mode=0o700, exist_ok=False)
    path = directory / "broker.sock"

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(5)
            try:
                raw = self.rfile.readline(MAX_MESSAGE + 1)
                data = broker.execute(_parse_frame(raw))
                reply = {"ok": True, "evidence": data}
            except Exception:
                reply = {"ok": False, "category": "BROKER_EXECUTION_REJECTED"}
            with suppress(OSError):
                self.wfile.write(canonical_json(reply))

    with socketserver.ThreadingUnixStreamServer(str(path), Handler) as server:
        path.chmod(0o600)
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        thread.start()
        try:
            yield path
        finally:
            server.shutdown()
            thread.join()


def request_slot(path: Path, task: str, slot: int) -> dict:
    """worker 仅使用 AF_UNIX，不从环境读取凭据、不自行访问 TLS 目标。"""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(path))
        connection.sendall(canonical_json({"task": task, "slot": slot}))
        with connection.makefile("rb") as stream:
            reply = _decode(stream.readline(100_000))
        if reply.get("ok") is not True:
            raise ControlError("BROKER_EXECUTION_REJECTED")
        return reply["evidence"]
