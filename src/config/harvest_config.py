#!/usr/bin/env python3
"""
FotMob 全球采集配置管理器 - V26.6
=====================================

核心功能：
    1. 加载 YAML 配置文件
    2. 提供联赛启用/禁用状态查询
    3. 生成采集任务列表
    4. 兼容 V26.5 安全锁和哨兵系统

Author: Data Engineering Expert
Version: V26.6
Date: 2026-01-06
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class LeagueConfig:
    """联赛配置数据类"""

    league_id: int
    name: str
    name_zh: str
    country: str
    tier: int
    enabled: bool
    seasons: list[str]

    def is_enabled(self) -> bool:
        """检查联赛是否启用"""
        return self.enabled

    def get_seasons(self) -> list[str]:
        """获取赛季列表"""
        return self.seasons


@dataclass
class HarvestStrategyConfig:
    """采集策略配置"""

    backfill_years: int = 3
    batch_size: int = 50
    batch_delay: int = 10
    enable_sentry: bool = True

    # 哨兵配置
    sentry_window_size: int = 100
    sentry_success_rate_threshold: float = 0.7
    sentry_consecutive_failure_threshold: int = 5
    sentry_pause_duration_hours: int = 12


class HarvestConfigManager:
    """
    全球采集配置管理器

    功能：
    1. 加载 YAML 配置文件
    2. 提供联赛启用/禁用状态查询
    3. 生成采集任务列表
    4. 兼容 V26.5 安全锁和哨兵系统
    """

    def __init__(self, config_path: str | None = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径（默认使用标准路径）
        """
        if config_path is None:
            config_path = "config/global_harvest_list.yaml"

        self.config_path = Path(config_path)
        self.leagues: dict[int, LeagueConfig] = {}
        self.strategy: HarvestStrategyConfig | None = None
        self.version: str = ""
        self.last_updated: str = ""

        self._load_config()

    def _load_config(self) -> None:
        """加载 YAML 配置文件"""
        if not self.config_path.exists():
            logger.error(f"❌ 配置文件不存在: {self.config_path}")
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # 解析联赛配置
            for league_data in config_data.get("leagues", []):
                league_config = LeagueConfig(
                    league_id=league_data["league_id"],
                    name=league_data["name"],
                    name_zh=league_data["name_zh"],
                    country=league_data["country"],
                    tier=league_data["tier"],
                    enabled=league_data.get("enabled", True),
                    seasons=league_data.get("seasons", []),
                )
                self.leagues[league_config.league_id] = league_config

            # 解析采集策略配置
            strategy_data = config_data.get("harvest_strategy", {})
            self.strategy = HarvestStrategyConfig(
                backfill_years=strategy_data.get("backfill_years", 3),
                batch_size=strategy_data.get("batch_size", 50),
                batch_delay=strategy_data.get("batch_delay", 10),
                enable_sentry=strategy_data.get("enable_sentry", True),
                sentry_window_size=strategy_data.get("sentry", {}).get("window_size", 100),
                sentry_success_rate_threshold=strategy_data.get("sentry", {}).get(
                    "success_rate_threshold", 0.7
                ),
                sentry_consecutive_failure_threshold=strategy_data.get("sentry", {}).get(
                    "consecutive_failure_threshold", 5
                ),
                sentry_pause_duration_hours=strategy_data.get("sentry", {}).get(
                    "pause_duration_hours", 12
                ),
            )

            # 解析版本信息
            self.version = config_data.get("version", "Unknown")
            self.last_updated = config_data.get("last_updated", "Unknown")

            logger.info(f"✅ 配置加载成功: {len(self.leagues)} 个联赛, 版本 {self.version}")

        except yaml.YAMLError as e:
            logger.exception(f"❌ YAML 解析失败: {e}")
            raise
        except Exception as e:
            logger.exception(f"❌ 配置加载失败: {e}")
            raise

    def get_enabled_leagues(self) -> list[LeagueConfig]:
        """
        获取所有启用的联赛

        Returns:
            启用的联赛列表
        """
        return [league for league in self.leagues.values() if league.is_enabled()]

    def get_leagues_by_tier(self, tier: int) -> list[LeagueConfig]:
        """
        根据质量等级获取联赛列表

        Args:
            tier: 质量等级（1=Premium, 2=Standard, 3=Basic）

        Returns:
            该等级的联赛列表
        """
        return [
            league
            for league in self.leagues.values()
            if league.tier == tier and league.is_enabled()
        ]

    def get_leagues_by_country(self, country_code: str) -> list[LeagueConfig]:
        """
        根据国家代码获取联赛列表

        Args:
            country_code: ISO 3166-1 alpha-2 国家代码

        Returns:
            该国家的联赛列表
        """
        return [
            league
            for league in self.leagues.values()
            if league.country == country_code and league.is_enabled()
        ]

    def get_league_config(self, league_id: int) -> LeagueConfig | None:
        """
        根据 league_id 获取联赛配置

        Args:
            league_id: FotMob league ID

        Returns:
            联赛配置对象，如果未找到返回 None
        """
        return self.leagues.get(league_id)

    def is_league_enabled(self, league_id: int) -> bool:
        """
        检查联赛是否启用

        Args:
            league_id: FotMob league ID

        Returns:
            是否启用
        """
        league_config = self.get_league_config(league_id)
        return league_config.is_enabled() if league_config else False

    def get_harvest_tasks(self) -> list[dict]:
        """
        生成采集任务列表

        Returns:
            采集任务列表，每个任务包含 league_id, name, seasons 等信息
        """
        tasks = []

        for league in self.get_enabled_leagues():
            for season in league.get_seasons():
                tasks.append(
                    {
                        "league_id": league.league_id,
                        "name": league.name,
                        "name_zh": league.name_zh,
                        "country": league.country,
                        "tier": league.tier,
                        "season": season,
                    }
                )

        logger.info(f"📋 生成 {len(tasks)} 个采集任务")
        return tasks

    def get_strategy_config(self) -> HarvestStrategyConfig:
        """
        获取采集策略配置

        Returns:
            采集策略配置对象
        """
        if self.strategy is None:
            logger.warning("⚠️ 采集策略配置未找到，使用默认配置")
            return HarvestStrategyConfig()
        return self.strategy

    def print_summary(self) -> None:
        """打印配置摘要"""
        enabled_leagues = self.get_enabled_leagues()



        # 按大洲分组统计
        continents = {
            "欧洲": ["GB", "ES", "DE", "IT", "FR", "PT", "NL", "BE", "TR", "GR", "RU", "UA"],
            "美洲": ["US", "BR", "AR", "MX"],
            "亚洲": ["JP", "CN", "KR", "SA", "AE", "AU", "IN"],
            "非洲": ["ZA", "EG", "NG"],
        }

        for countries in continents.values():
            continent_leagues = [
                league for league in enabled_leagues if league.country in countries
            ]
            if continent_leagues:
                for league in continent_leagues:
                    "✅" if league.is_enabled() else "❌"



# 单例实例
_config_manager: HarvestConfigManager | None = None


def get_config_manager(config_path: str | None = None) -> HarvestConfigManager:
    """
    获取配置管理器单例

    Args:
        config_path: 配置文件路径（仅首次调用有效）

    Returns:
        配置管理器单例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = HarvestConfigManager(config_path)
    return _config_manager


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    manager = get_config_manager()
    manager.print_summary()

    # 生成采集任务
    tasks = manager.get_harvest_tasks()
    for _task in tasks[:10]:
        pass
