"""
V41.262 Harvester V2 Configuration Models
=========================================

Pydantic 配置模型 - 提供类型安全和参数校验

所有配置项都从 config/harvester_v2.yaml 加载，
确保零硬编码、全参数化。

Author: V41.262 Architecture Team
Date: 2026-01-20
Version: V41.262 "Standardized Delivery"
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
import yaml


class ProxyConfig(BaseModel):
    """代理配置"""

    wsl2_bridge_host: str
    ports: list[int] = Field(default_factory=lambda: [7892, 7893, 7894])
    health_check_enabled: bool = True
    health_check_timeout_seconds: int = 5
    ban_duration_seconds: int = 1800
    max_failures: int = 10

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: list[int]) -> list[int]:
        """验证代理端口"""
        if not v:
            raise ValueError("代理端口列表不能为空")
        if any(p < 1024 or p > 65535 for p in v):
            raise ValueError("代理端口必须在 1024-65535 范围内")
        return v


class RetryConfig(BaseModel):
    """重试配置"""

    max_attempts: int = Field(ge=1, le=10, default=4)
    base_delay_seconds: float = Field(ge=0.1, le=60.0, default=2.0)
    max_delay_seconds: float = Field(ge=1.0, le=300.0, default=60.0)
    backoff_multiplier: float = Field(ge=1.0, le=10.0, default=2.0)

    @model_validator(mode="after")
    def validate_delays(self) -> RetryConfig:
        """验证延迟配置的合理性"""
        if self.base_delay_seconds >= self.max_delay_seconds:
            raise ValueError("base_delay_seconds 必须小于 max_delay_seconds")
        return self


class ValueRangesConfig(BaseModel):
    """数值范围配置"""

    odds_min: float = Field(ge=1.01, le=1000.0, default=1.01)  # V41.272: 调优至 1.01，依赖物理约束
    odds_max: float = Field(le=10000.0, default=1000.0)
    xg_diff_threshold: float = Field(ge=0.0, default=1.3)
    xg_diff_strong_threshold: float = Field(ge=0.0, default=1.5)

    @model_validator(mode="after")
    def validate_thresholds(self) -> ValueRangesConfig:
        """验证阈值配置的合理性"""
        if self.xg_diff_strong_threshold <= self.xg_diff_threshold:
            raise ValueError("xg_diff_strong_threshold 必须大于 xg_diff_threshold")
        return self


class DataIntegrityConfig(BaseModel):
    """数据完整性配置"""

    min_div_count: int = Field(ge=0, default=10)
    min_entities: int = Field(ge=0, default=1)
    value_ranges: ValueRangesConfig = Field(default_factory=ValueRangesConfig)


class DeepSearchConfig(BaseModel):
    """深度搜索配置"""

    search_url_template: str = "https://www.oddsportal.com/search/{query}/"
    request_delay: float = Field(ge=0.5, le=10.0, default=2.0)
    timeout: int = Field(ge=5, le=120, default=30)
    hash_pattern: str = r"/([a-f0-9]{8})/?$"
    detail_page_pattern: str = r"/football/[a-z]+/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+/"


class ConcurrencyConfig(BaseModel):
    """并发配置"""

    default_workers: int = Field(ge=1, le=20, default=2)
    max_workers: int = Field(ge=1, le=50, default=5)
    task_timeout: int = Field(ge=60, le=3600, default=600)

    @model_validator(mode="after")
    def validate_workers(self) -> ConcurrencyConfig:
        """验证并发配置的合理性"""
        if self.max_workers < self.default_workers:
            raise ValueError("max_workers 必须大于等于 default_workers")
        return self


class AuditorConfig(BaseModel):
    """审计器配置"""

    navigation_strategy: Literal["domcontentloaded", "networkidle", "load"] = "domcontentloaded"
    navigation_timeout: int = Field(ge=1000, le=300000, default=90000)
    wait_after_load: int = Field(ge=0, le=60000, default=5000)
    network_idle_timeout: int = Field(ge=1000, le=120000, default=30000)
    scroll_iterations: int = Field(ge=0, le=20, default=5)
    scroll_delay_ms: int = Field(ge=100, le=5000, default=800)
    container_width_ratio: float = Field(ge=0.1, le=1.0, default=0.3)


class DatabaseConfig(BaseModel):
    """数据库配置"""

    start_date: str = "2024-01-01"
    query_limit: int = Field(ge=1, le=10000, default=100)
    batch_size: int = Field(ge=1, le=1000, default=10)


class LoggingConfig(BaseModel):
    """日志配置"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    output_dir: str = "logs"
    screenshot_dir: str = "logs"


class HarvesterV2Config(BaseModel):
    """
    V41.262 收割引擎 V2 主配置

    从 config/harvester_v2.yaml 加载所有配置项，
    提供完整的类型安全和参数校验。
    """

    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    data_integrity: DataIntegrityConfig = Field(default_factory=DataIntegrityConfig)
    deep_search: DeepSearchConfig = Field(default_factory=DeepSearchConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    auditor: AuditorConfig = Field(default_factory=AuditorConfig)
    target_patterns: list[str] = Field(default_factory=lambda: ["Opening", "Closing", "Movement"])
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, config_path: str | Path = "config/harvester_v2.yaml") -> HarvesterV2Config:
        """
        从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            HarvesterV2Config 实例
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump()


# =============================================================================
# 单例模式配置访问器
# =============================================================================

_config_instance: HarvesterV2Config | None = None


def get_harvester_config(config_path: str | Path = "config/harvester_v2.yaml") -> HarvesterV2Config:
    """
    获取收割引擎配置（单例模式）

    Args:
        config_path: 配置文件路径

    Returns:
        HarvesterV2Config 实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = HarvesterV2Config.from_yaml(config_path)
    return _config_instance


def reload_config(config_path: str | Path = "config/harvester_v2.yaml") -> HarvesterV2Config:
    """
    重新加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        HarvesterV2Config 实例
    """
    global _config_instance
    _config_instance = HarvesterV2Config.from_yaml(config_path)
    return _config_instance
