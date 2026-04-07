from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.config.common import logger

PROXY_POOL_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "proxy_pool.json"


def _read_proxy_pool_file() -> dict[str, Any]:
    """读取共享代理池配置文件。"""
    try:
        with PROXY_POOL_CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        logger.warning("共享代理池配置不存在: %s", PROXY_POOL_CONFIG_PATH)
    except json.JSONDecodeError as exc:
        logger.warning("共享代理池配置解析失败: %s", exc)

    return {}


def parse_proxy_ports(value: Any) -> list[int]:
    """解析逗号分隔或数组形式的代理端口。"""
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        candidates = value.split(",")
    else:
        return []

    ports: list[int] = []
    for candidate in candidates:
        try:
            port = int(str(candidate).strip())
        except (TypeError, ValueError):
            continue

        if port > 0:
            ports.append(port)

    return ports


def _expand_proxy_port_range(start: Any, end: Any) -> list[int]:
    """根据起止端口展开端口列表。"""
    try:
        range_start = int(start)
        range_end = int(end)
    except (TypeError, ValueError):
        return []

    if range_end < range_start:
        return []

    return list(range(range_start, range_end + 1))


def _extract_proxy_host(server_template: str | None) -> str | None:
    """从 serverTemplate 中提取主机名。"""
    if not server_template:
        return None

    match = re.match(r"^https?://([^/:]+)", str(server_template))
    return match.group(1) if match else None


def resolve_shared_proxy_pool_config() -> dict[str, Any]:
    """解析跨语言共享的代理池配置。"""
    file_config = _read_proxy_pool_file()
    protocol = os.environ.get("PROXY_PROTOCOL") or file_config.get("protocol") or "http"
    server_template = os.environ.get("PROXY_SERVER") or file_config.get("serverTemplate") or ""

    ports = parse_proxy_ports(os.environ.get("PROXY_PORTS"))
    if not ports:
        ports = _expand_proxy_port_range(
            os.environ.get("PROXY_PORT_START"),
            os.environ.get("PROXY_PORT_END"),
        )
    if not ports:
        ports = parse_proxy_ports(file_config.get("ports"))

    host = (
        os.environ.get("WSL2_PROXY_HOST")
        or os.environ.get("PROXY_HOST")
        or _extract_proxy_host(server_template)
        or file_config.get("host")
        or "127.0.0.1"
    )

    try:
        default_port = int(
            os.environ.get("PROXY_PORT")
            or file_config.get("defaultPort")
            or (ports[0] if ports else 0)
        )
    except (TypeError, ValueError):
        default_port = ports[0] if ports else 0

    if not ports and default_port:
        ports = [default_port]

    resolved_template = server_template or f"{protocol}://{host}:{{port}}"

    return {
        "protocol": protocol,
        "host": host,
        "ports": ports,
        "default_port": default_port,
        "server_template": resolved_template,
        "config_path": str(PROXY_POOL_CONFIG_PATH),
    }


def get_shared_proxy_pool_config() -> dict[str, Any]:
    """公开的共享代理池配置访问器。"""
    return resolve_shared_proxy_pool_config().copy()


def default_proxy_host() -> str:
    return str(resolve_shared_proxy_pool_config()["host"])


def default_proxy_ports() -> list[int]:
    return list(resolve_shared_proxy_pool_config()["ports"])


def default_proxy_ports_csv() -> str:
    return ",".join(str(port) for port in default_proxy_ports())


def default_proxy_protocol() -> str:
    return str(resolve_shared_proxy_pool_config()["protocol"])


def default_proxy_server_template() -> str:
    return str(resolve_shared_proxy_pool_config()["server_template"])


@dataclass
class ProxyConfig:
    """统一代理配置。"""

    wsl2_bridge_host: str = field(default_factory=default_proxy_host)
    protocol: str = field(default_factory=default_proxy_protocol)
    server_template: str = field(default_factory=default_proxy_server_template)
    auto_detect_wsl2: bool = True
    proxy_ports: list[int] = field(default_factory=default_proxy_ports)
    deprecated_proxy_ports: list[int] = field(default_factory=list)
    health_check_timeout: float = 2.0
    health_check_retry: int = 3
    circuit_breaker_threshold: int = 5
    response_time_excellent: int = 1000
    response_time_good: int = 2000
    response_time_acceptable: int = 5000

    def __post_init__(self) -> None:
        resolved = resolve_shared_proxy_pool_config()
        if not self.wsl2_bridge_host:
            self.wsl2_bridge_host = resolved["host"]
        if not self.protocol:
            self.protocol = resolved["protocol"]
        if not self.server_template:
            self.server_template = resolved["server_template"]
        if not self.proxy_ports:
            self.proxy_ports = list(resolved["ports"])

    def get_proxy_url(self, port: int | None = None) -> str | None:
        """获取代理 URL。"""
        resolved_port = port or (self.proxy_ports[0] if self.proxy_ports else None)
        if resolved_port is None:
            return None

        if self.server_template and "{port}" in self.server_template:
            return self.server_template.replace("{port}", str(resolved_port))

        return f"{self.protocol}://{self.wsl2_bridge_host}:{resolved_port}"

    def get_all_proxy_urls(self) -> list[str]:
        """获取所有代理 URL。"""
        return [
            proxy_url
            for port in self.proxy_ports
            if (proxy_url := self.get_proxy_url(port)) is not None
        ]

    def is_port_deprecated(self, port: int) -> bool:
        return port in self.deprecated_proxy_ports

    def validate_port(self, port: int) -> bool:
        return not self.is_port_deprecated(port) and port in self.proxy_ports


class ProxySettingsMixin(BaseModel):
    """统一代理字段与归一化逻辑。"""

    proxy_wsl2_host: str = Field(default_factory=default_proxy_host, description="代理主机")
    proxy_protocol: str = Field(default_factory=default_proxy_protocol, description="代理协议")
    proxy_ports: str = Field(
        default_factory=default_proxy_ports_csv,
        description="可用代理端口列表（来自共享 proxy_pool.json 或环境变量）",
    )
    proxy_server_template: str = Field(
        default_factory=default_proxy_server_template,
        description="代理地址模板",
    )
    proxy_deprecated_ports: str = Field(default="", description="已弃用的代理端口")
    proxy_health_timeout: float = Field(default=2.0, description="代理健康检查超时时间")
    proxy_circuit_breaker_threshold: int = Field(default=5, description="代理熔断器触发阈值")

    @field_validator("proxy_wsl2_host", mode="before")
    @classmethod
    def normalize_proxy_wsl2_host(cls, _: Any) -> str:
        return default_proxy_host()

    @field_validator("proxy_protocol", mode="before")
    @classmethod
    def normalize_proxy_protocol(cls, _: Any) -> str:
        return default_proxy_protocol()

    @field_validator("proxy_ports", mode="before")
    @classmethod
    def normalize_proxy_ports(cls, _: Any) -> str:
        return default_proxy_ports_csv()

    @field_validator("proxy_server_template", mode="before")
    @classmethod
    def normalize_proxy_server_template(cls, _: Any) -> str:
        return default_proxy_server_template()

    def build_proxy_config(self) -> ProxyConfig:
        """构建 ProxyConfig 视图。"""
        return ProxyConfig(
            wsl2_bridge_host=self.proxy_wsl2_host,
            protocol=self.proxy_protocol,
            server_template=self.proxy_server_template,
            proxy_ports=parse_proxy_ports(self.proxy_ports),
            deprecated_proxy_ports=parse_proxy_ports(self.proxy_deprecated_ports),
            health_check_timeout=self.proxy_health_timeout,
            circuit_breaker_threshold=self.proxy_circuit_breaker_threshold,
        )


__all__ = [
    "PROXY_POOL_CONFIG_PATH",
    "ProxyConfig",
    "ProxySettingsMixin",
    "default_proxy_host",
    "default_proxy_ports",
    "default_proxy_ports_csv",
    "default_proxy_protocol",
    "default_proxy_server_template",
    "get_shared_proxy_pool_config",
    "parse_proxy_ports",
    "resolve_shared_proxy_pool_config",
]
