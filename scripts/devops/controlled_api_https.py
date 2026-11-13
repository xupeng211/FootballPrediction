"""受控 broker 的单次 TLS 传输；真实 Provider admission 无条件关闭。

lifecycle: permanent
本地 TLS fixture 验证生产所需的连接机制，不授予供应商计费保证或审核资格。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
import http.client
import ipaddress
import socket
import ssl
from typing import TYPE_CHECKING

from scripts.devops.controlled_api_policy import ControlError, validate_plan
from scripts.devops.controlled_api_runner import MAX_RESPONSE_BYTES
from scripts.devops.independent_review_protocol import canonical_json

PROVIDER_HOSTS = {"openai": "api.openai.com", "deepseek": "api.deepseek.com"}
MAX_PORT = 65535

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class TLSFixture:
    """只接受 loopback 的显式测试配置；不能把官方主机重定向到测试 CA。"""

    address: str
    port: int
    ca_file: Path
    hostname: str = "localhost"

    def validate(self) -> None:
        """任何非本地或未知目标在创建 socket 前拒绝。"""
        if (
            self.hostname != "localhost"
            or self.address != "127.0.0.1"
            or not ipaddress.ip_address(self.address).is_loopback
            or type(self.port) is not int
            or not 0 < self.port <= MAX_PORT
        ):
            raise ControlError("LOCAL_TLS_FIXTURE_REQUIRED")


@dataclass(frozen=True)
class Credential:
    """只由可信 broker 持有；不从环境或 worker 消息加载。"""

    value: str = field(repr=False)

    def fixture_header(self) -> str:
        """离线测试只接受显式合成凭据，避免误送现有用户凭据。"""
        if (
            not self.value.startswith("fixture-")
            or not self.value.isascii()
            or not self.value.replace("-", "").isalnum()
        ):
            raise ControlError("SYNTHETIC_CREDENTIAL_REQUIRED")
        return "Bearer " + self.value


class PinnedTLS(http.client.HTTPSConnection):
    """单个 IPv4 socket，固定 TLS hostname，忽略代理/DNS，不重连。"""

    def __init__(self, fixture: TLSFixture, timeout: float):
        fixture.validate()
        context = ssl.create_default_context(cafile=str(fixture.ca_file))
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_alpn_protocols(["http/1.1"])
        super().__init__(fixture.hostname, fixture.port, timeout=timeout, context=context)
        self.address = fixture.address

    def connect(self):
        """不探测其他地址；任何 TLS 错误保持失败。"""
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(self.timeout)
        try:
            raw.connect((self.address, self.port))
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def post_once(
    plan: dict, credential: Credential, *, fixture: TLSFixture | None, timeout: float = 5
) -> bytes:
    """只调用一次 request；无真实付费入口、SDK、重定向或自动重试。"""
    plan = validate_plan(plan)
    if fixture is None:
        # 不存在由环境、预算计数或调用者布尔开关替代供应商保证的入口。
        raise ControlError("LIVE_BILLING_AND_DEPLOYMENT_ADMISSION_NOT_PROVEN")
    fixture.validate()
    authorization = credential.fixture_header()
    connection = PinnedTLS(fixture, timeout)
    try:
        connection.request(
            "POST",
            plan["policy"]["path"],
            body=canonical_json(plan["body"]),
            headers={
                "Host": fixture.hostname,
                "Authorization": authorization,
                "Content-Type": "application/json",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        if response.status != HTTPStatus.OK:
            raise ControlError("HTTP_STATUS_REJECTED")
        expected = response.length
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if expected is not None and len(raw) < expected:
            raise http.client.IncompleteRead(raw, expected - len(raw))
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ControlError("RESPONSE_TOO_LARGE")
        return raw
    finally:
        connection.close()
