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
DEFAULT_PREFERRED_PROXY_HOST = "127.0.0.1"
IPV4_OCTET_COUNT = 4
IPV4_OCTET_MAX = 255
LEGACY_BRIDGE_PROXY_OCTETS = (172, 25, 16, 1)


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

    match = re.match(r"^(?:https?|socks5h?)://([^/:]+)", str(server_template))
    return match.group(1) if match else None


def _normalize_proxy_protocol(protocol: str | None) -> str:
    """规范化代理协议，统一将 socks5h 收敛为 socks5。"""
    normalized = str(protocol or "").strip().lower()
    if normalized == "socks5h":
        return "socks5"
    return normalized or "socks5"


def _normalize_proxy_host(host: str | None) -> str | None:
    """清洗代理主机字符串。"""
    if host is None:
        return None

    normalized = str(host).strip()
    return normalized or None


def _is_legacy_bridge_proxy_host(host: str | None) -> bool:
    """识别历史 WSL 网桥地址，避免继续回退到旧桥接 IP。"""
    normalized = _normalize_proxy_host(host)
    if not normalized:
        return False

    parts = normalized.split(".")
    if len(parts) != IPV4_OCTET_COUNT:
        return False

    try:
        octets = [int(part) for part in parts]
    except ValueError:
        return False

    return (
        all(0 <= octet <= IPV4_OCTET_MAX for octet in octets)
        and tuple(octets) == LEGACY_BRIDGE_PROXY_OCTETS
    )


def resolve_shared_proxy_pool_config() -> dict[str, Any]:
    """解析跨语言共享的代理池配置。"""
    file_config = _read_proxy_pool_file()
    protocol = _normalize_proxy_protocol(
        os.environ.get("PROXY_PROTOCOL") or file_config.get("protocol") or "socks5"
    )
    explicit_server_template = (os.environ.get("PROXY_SERVER") or "").strip()
    file_server_template = str(file_config.get("serverTemplate") or "").strip()
    server_template = explicit_server_template or file_server_template

    ports = parse_proxy_ports(os.environ.get("PROXY_PORTS"))
    if not ports:
        ports = _expand_proxy_port_range(
            os.environ.get("PROXY_PORT_START"),
            os.environ.get("PROXY_PORT_END"),
        )
    if not ports:
        ports = parse_proxy_ports(file_config.get("ports"))

    file_host = _normalize_proxy_host(file_config.get("host"))
    host = (
        _normalize_proxy_host(os.environ.get("PROXY_HOST"))
        or _normalize_proxy_host(_extract_proxy_host(explicit_server_template))
        or (None if _is_legacy_bridge_proxy_host(file_host) else file_host)
        or DEFAULT_PREFERRED_PROXY_HOST
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

    resolved_template = (
        server_template
        if server_template and not os.environ.get("PROXY_HOST")
        else f"{protocol}://{host}:{{port}}"
    )

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
    """返回默认代理主机。"""
    return str(resolve_shared_proxy_pool_config()["host"])


def default_proxy_ports() -> list[int]:
    """返回默认代理端口列表。"""
    return list(resolve_shared_proxy_pool_config()["ports"])


def default_proxy_ports_csv() -> str:
    """返回默认代理端口 CSV。"""
    return ",".join(str(port) for port in default_proxy_ports())


def default_proxy_protocol() -> str:
    """返回默认代理协议。"""
    return str(resolve_shared_proxy_pool_config()["protocol"])


def default_proxy_server_template() -> str:
    """返回默认代理地址模板。"""
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
        """判断端口是否已弃用。"""
        return port in self.deprecated_proxy_ports

    def validate_port(self, port: int) -> bool:
        """验证端口是否仍可被使用。"""
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
        """统一回填共享代理主机。"""
        return default_proxy_host()

    @field_validator("proxy_protocol", mode="before")
    @classmethod
    def normalize_proxy_protocol(cls, _: Any) -> str:
        """统一回填共享代理协议。"""
        return default_proxy_protocol()

    @field_validator("proxy_ports", mode="before")
    @classmethod
    def normalize_proxy_ports(cls, _: Any) -> str:
        """统一回填共享代理端口列表。"""
        return default_proxy_ports_csv()

    @field_validator("proxy_server_template", mode="before")
    @classmethod
    def normalize_proxy_server_template(cls, _: Any) -> str:
        """统一回填共享代理模板。"""
        return default_proxy_server_template()

    def model_post_init(self, __context: Any) -> None:
        """统一覆盖来自 .env 的遗留代理字段，确保共享代理池是唯一真理源。"""
        parent_post_init = getattr(super(), "model_post_init", None)
        if callable(parent_post_init):
            parent_post_init(__context)

        resolved = resolve_shared_proxy_pool_config()
        self.proxy_wsl2_host = str(resolved["host"])
        self.proxy_protocol = str(resolved["protocol"])
        self.proxy_ports = ",".join(str(port) for port in resolved["ports"])
        self.proxy_server_template = str(resolved["server_template"])

    def build_proxy_config(self) -> ProxyConfig:
        """构建 ProxyConfig 视图，始终以共享代理池解析结果为准。"""
        resolved = resolve_shared_proxy_pool_config()
        return ProxyConfig(
            wsl2_bridge_host=str(resolved["host"]),
            protocol=str(resolved["protocol"]),
            server_template=str(resolved["server_template"]),
            proxy_ports=list(resolved["ports"]),
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
