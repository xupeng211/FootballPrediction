#!/usr/bin/env python3
"""V120.0 Crawler Settings Configuration Module.

This module provides centralized configuration management for the crawler system.
It loads settings from crawler_settings.yaml and allows environment variable overrides.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

import yaml

# Default configuration file path
DEFAULT_CONFIG_PATH = Path(__file__).parent / "crawler_settings.yaml"


@dataclass
class HybridEngineConfig:
    """混合引擎配置"""
    # Laser Mode 参数
    track_tolerance: int = 30

    # Gravity Mode 参数
    delta_y_start: int = -10
    delta_y_end: int = 40

    # 模式切换阈值
    min_entities_trigger: int = 2


@dataclass
class NetworkConfig:
    """网络韧性协议配置"""
    request_delay_min: float = 8.0
    request_delay_max: float = 15.0
    max_workers: int = 4
    max_retry_attempts: int = 3
    base_retry_delay: float = 2.0
    exponential_backoff: bool = True


@dataclass
class DataQualityConfig:
    """数据质量契约配置"""
    # 完整性评分
    min_integrity_score: float = 1.00
    max_integrity_score: float = 1.08
    ideal_integrity_score: float = 1.05

    # 数据分布
    min_value: float = 1.01
    max_value: float = 50.00
    allow_identical: bool = False

    # 死信队列
    max_retries: int = 5


@dataclass
class TaskQueueConfig:
    """任务队列配置"""
    pending_status: str = "PENDING"
    searching_status: str = "SEARCHING"
    success_status: str = "SUCCESS"
    failed_status: str = "FAILED"
    fetch_size: int = 50


@dataclass
class CrawlerSettings:
    """V120.0 爬虫配置总类

    集中管理所有爬虫相关配置，支持从 YAML 文件加载和环境变量覆盖。
    """
    # 子配置
    hybrid: HybridEngineConfig = field(default_factory=HybridEngineConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    data_quality: DataQualityConfig = field(default_factory=DataQualityConfig)
    task_queue: TaskQueueConfig = field(default_factory=TaskQueueConfig)

    # 原始配置字典 (用于调试)
    _raw_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load_from_yaml(cls, config_path: Path | None = None) -> "CrawlerSettings":
        """从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径，默认为 DEFAULT_CONFIG_PATH

        Returns:
            CrawlerSettings 实例
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_PATH

        if not config_path.exists():
            # 如果配置文件不存在，使用默认配置
            return cls()

        with open(config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        settings = cls()
        settings._raw_config = raw_config

        # 解析 hybrid_engine 配置
        if "hybrid_engine" in raw_config:
            hybrid_config = raw_config["hybrid_engine"]

            # Laser Mode 配置
            if "laser" in hybrid_config:
                laser = hybrid_config["laser"]
                settings.hybrid.track_tolerance = laser.get("track_tolerance", 30)

            # Gravity Mode 配置
            if "gravity" in hybrid_config:
                gravity = hybrid_config["gravity"]
                settings.hybrid.delta_y_start = gravity.get("delta_y_start", -10)
                settings.hybrid.delta_y_end = gravity.get("delta_y_end", 40)

            # 模式切换配置
            if "mode_switch" in hybrid_config:
                mode_switch = hybrid_config["mode_switch"]
                settings.hybrid.min_entities_trigger = mode_switch.get("min_entities_trigger", 2)

        # 解析 network 配置
        if "network" in raw_config:
            network_config = raw_config["network"]

            if "request_delay" in network_config:
                delay = network_config["request_delay"]
                settings.network.request_delay_min = delay.get("min", 8.0)
                settings.network.request_delay_max = delay.get("max", 15.0)

            if "concurrency" in network_config:
                concurrency = network_config["concurrency"]
                settings.network.max_workers = concurrency.get("max_workers", 4)

            if "retry" in network_config:
                retry = network_config["retry"]
                settings.network.max_retry_attempts = retry.get("max_attempts", 3)
                settings.network.base_retry_delay = retry.get("base_delay", 2.0)
                settings.network.exponential_backoff = retry.get("exponential_backoff", True)

        # 解析 data_quality 配置
        if "data_quality" in raw_config:
            quality_config = raw_config["data_quality"]

            if "integrity_score" in quality_config:
                integrity = quality_config["integrity_score"]
                settings.data_quality.min_integrity_score = integrity.get("min", 1.00)
                settings.data_quality.max_integrity_score = integrity.get("max", 1.08)
                settings.data_quality.ideal_integrity_score = integrity.get("ideal", 1.05)

            if "distribution" in quality_config:
                distribution = quality_config["distribution"]
                settings.data_quality.min_value = distribution.get("min_value", 1.01)
                settings.data_quality.max_value = distribution.get("max_value", 50.00)
                settings.data_quality.allow_identical = distribution.get("allow_identical", False)

            if "dead_letter" in quality_config:
                dead_letter = quality_config["dead_letter"]
                settings.data_quality.max_retries = dead_letter.get("max_retries", 5)

        # 解析 task_queue 配置
        if "task_queue" in raw_config:
            queue_config = raw_config["task_queue"]

            if "status" in queue_config:
                status = queue_config["status"]
                settings.task_queue.pending_status = status.get("pending", "PENDING")
                settings.task_queue.searching_status = status.get("searching", "SEARCHING")
                settings.task_queue.success_status = status.get("success", "SUCCESS")
                settings.task_queue.failed_status = status.get("failed", "FAILED")

            if "batch" in queue_config:
                batch = queue_config["batch"]
                settings.task_queue.fetch_size = batch.get("fetch_size", 50)

        # 应用环境变量覆盖
        settings._apply_env_overrides()

        return settings

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖

        支持的环境变量:
        - CRAWLER_REQUEST_DELAY_MIN
        - CRAWLER_REQUEST_DELAY_MAX
        - CRAWLER_MAX_WORKERS
        - CRAWLER_LOG_LEVEL
        """
        # 网络配置
        if "CRAWLER_REQUEST_DELAY_MIN" in os.environ:
            try:
                self.network.request_delay_min = float(os.environ["CRAWLER_REQUEST_DELAY_MIN"])
            except ValueError:
                pass

        if "CRAWLER_REQUEST_DELAY_MAX" in os.environ:
            try:
                self.network.request_delay_max = float(os.environ["CRAWLER_REQUEST_DELAY_MAX"])
            except ValueError:
                pass

        if "CRAWLER_MAX_WORKERS" in os.environ:
            try:
                self.network.max_workers = int(os.environ["CRAWLER_MAX_WORKERS"])
            except ValueError:
                pass

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于调试）

        Returns:
            配置字典
        """
        return {
            "hybrid_engine": {
                "track_tolerance": self.hybrid.track_tolerance,
                "delta_y_start": self.hybrid.delta_y_start,
                "delta_y_end": self.hybrid.delta_y_end,
                "min_entities_trigger": self.hybrid.min_entities_trigger,
            },
            "network": {
                "request_delay_min": self.network.request_delay_min,
                "request_delay_max": self.network.request_delay_max,
                "max_workers": self.network.max_workers,
                "max_retry_attempts": self.network.max_retry_attempts,
                "base_retry_delay": self.network.base_retry_delay,
                "exponential_backoff": self.network.exponential_backoff,
            },
            "data_quality": {
                "min_integrity_score": self.data_quality.min_integrity_score,
                "max_integrity_score": self.data_quality.max_integrity_score,
                "min_value": self.data_quality.min_value,
                "max_value": self.data_quality.max_value,
                "max_retries": self.data_quality.max_retries,
            },
            "task_queue": {
                "pending_status": self.task_queue.pending_status,
                "searching_status": self.task_queue.searching_status,
                "success_status": self.task_queue.success_status,
                "failed_status": self.task_queue.failed_status,
                "fetch_size": self.task_queue.fetch_size,
            },
        }


# 全局配置单例
_crawler_settings_instance: CrawlerSettings | None = None


def get_crawler_settings() -> CrawlerSettings:
    """获取爬虫配置单例

    Returns:
        CrawlerSettings 实例
    """
    global _crawler_settings_instance

    if _crawler_settings_instance is None:
        _crawler_settings_instance = CrawlerSettings.load_from_yaml()

    return _crawler_settings_instance


def reload_crawler_settings() -> CrawlerSettings:
    """重新加载配置（用于热更新）

    Returns:
        新的 CrawlerSettings 实例
    """
    global _crawler_settings_instance
    _crawler_settings_instance = CrawlerSettings.load_from_yaml()
    return _crawler_settings_instance
