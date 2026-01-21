#!/usr/bin/env python3
"""
V41.243 LeagueRouter - 动态联赛路由系统
========================================

核心功能：
    - 自动将数据库 league_name 映射到 OddsPortal URL 结构
    - 支持全球联赛、杯赛、世界杯
    - 零硬编码架构，配置化发现

Architecture:
    league_name → normalize → country → league_type → oddsportal_url

Usage:
    router = LeagueRouter()
    url = router.resolve_url("Premier League", "2024/2025")
    # -> "https://www.oddsportal.com/football/england/premier-league/results/"

Author: V41.243 Skynet Team
Date: 2026-01-20
Version: V41.243 "Skynet Protocol"
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re
import sys

import yaml

logger = logging.getLogger("LeagueRouter")


# =============================================================================
# 联赛元数据模型
# =============================================================================


@dataclass
class LeagueMetadata:
    """联赛元数据"""

    name: str  # 数据库中的联赛名
    oddsportal_path: str  # OddsPortal 路径 (如 "/football/england/premier-league/")
    country: str  # 国家/地区
    league_type: str  # league/cup/tournament
    alt_names: list[str]  # 别名列表


# =============================================================================
# URL 模板生成器
# =============================================================================


class URLTemplateBuilder:
    """
    OddsPortal URL 模板构建器

    OddsPortal URL 格式：
    - 联赛: /football/{country}/{league-slug}/results/
    - 杯赛: /football/{country}/{cup-slug}/results/
    - 世界杯: /football/world/{tournament-slug}/results/
    """

    BASE_URL = "https://www.oddsportal.com"

    # 国家代码映射（标准化）
    COUNTRY_MAPPING = {
        "england": "england",
        "premier league": "england",
        "la liga": "spain",
        "spain": "spain",
        "bundesliga": "germany",
        "germany": "germany",
        "serie a": "italy",
        "italy": "italy",
        "ligue 1": "france",
        "france": "france",
        "eredivisie": "netherlands",
        "netherlands": "netherlands",
        "primeira liga": "portugal",
        "portugal": "portugal",
        "brazil": "brazil",
        "argentina": "argentina",
        "mls": "usa",
        "usa": "usa",
        "china": "china",
        "japan": "japan",
        "korea": "korea",
        "australia": "australia",
        "mexico": "mexico",
        "russia": "russia",
        "turkey": "turkey",
        "scotland": "scotland",
        "belgium": "belgium",
        "switzerland": "switzerland",
        "austria": "austria",
        "denmark": "denmark",
        "norway": "norway",
        "sweden": "sweden",
        "poland": "poland",
        "greece": "greece",
        "czech": "czech-republic",
        "ukraine": "ukraine",
    }

    # 联赛名称 slug 映射（标准化）
    LEAGUE_SLUG_MAPPING = {
        "premier league": "premier-league",
        "la liga": "laliga",
        "bundesliga": "bundesliga",
        "serie a": "serie-a",
        "ligue 1": "ligue-1",
        "eredivisie": "eredivisie",
        "primeira liga": "liga-portugal",
        "fa cup": "fa-cup",
        "dfb-pokal": "dfb-pokal",
        "copa del rey": "copa-del-rey",
        " coppa italia": "coppa-italia",
        "euro": "euro-2024",  # 动态年份
        "world cup": "world-cup",
        "champions league": "uefa-champions-league",
        "europa league": "uefa-europa-league",
        "conference league": "uefa-conference-league",
    }

    @classmethod
    def slugify(cls, name: str) -> str:
        """
        将联赛名称转换为 URL slug

        Examples:
            "Premier League" -> "premier-league"
            "FA Cup" -> "fa-cup"
            "Copa del Rey" -> "copa-del-rey"
        """
        # 转小写
        slug = name.lower().strip()

        # 查找预定义映射
        if slug in cls.LEAGUE_SLUG_MAPPING:
            return cls.LEAGUE_SLUG_MAPPING[slug]

        # 默认处理：空格和斜杠替换为连字符
        slug = re.sub(r"[\s/]+", "-", slug)
        return re.sub(r"[^\w\-]", "", slug)  # 移除特殊字符

    @classmethod
    def detect_country(cls, league_name: str) -> str:
        """
        从联赛名称检测国家

        Examples:
            "Premier League" -> "england"
            "La Liga" -> "spain"
            "Bundesliga" -> "germany"
        """
        league_lower = league_name.lower().strip()

        # 查找预定义映射
        if league_lower in cls.COUNTRY_MAPPING:
            return cls.COUNTRY_MAPPING[league_lower]

        # 尝试从别名推断
        for key, value in cls.COUNTRY_MAPPING.items():
            if key in league_lower:
                return value

        # 默认返回 "world"
        return "world"

    @classmethod
    def build_results_url(cls, country: str, league_slug: str) -> str:
        """
        构建 OddsPortal results 页面 URL

        Args:
            country: 国家代码 (england, spain, world)
            league_slug: 联赛 slug (premier-league, laliga, world-cup)

        Returns:
            完整的 URL
        """
        return f"{cls.BASE_URL}/football/{country}/{league_slug}/results/"


# =============================================================================
# 动态联赛路由器
# =============================================================================


class LeagueRouter:
    """
    V41.243 动态联赛路由器

    功能：
        1. 接收数据库中的 league_name
        2. 自动解析国家、联赛类型
        3. 生成 OddsPortal URL
        4. 支持回退搜索策略

    零硬编码设计：
        - 通过 COUNTRY_MAPPING 和 LEAGUE_SLUG_MAPPING 配置
        - 新增联赛只需添加映射，无需修改代码
    """

    def __init__(self, config_path: str | None = None):
        """
        初始化路由器

        Args:
            config_path: 可选的自定义配置文件路径
        """
        self.config_path = config_path
        self.url_builder = URLTemplateBuilder()

        # 加载自定义配置（如果提供）
        self.custom_mappings = {}
        if config_path:
            self._load_custom_config(config_path)

        logger.info("V41.243 LeagueRouter initialized")

    def _load_custom_config(self, config_path: str) -> None:
        """加载自定义 YAML 配置"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    self.custom_mappings = config.get("league_mappings", {})
                    logger.info(
                        f"Loaded {len(self.custom_mappings)} custom mappings from {config_path}"
                    )
        except Exception as e:
            logger.warning(f"Failed to load custom config: {e}")

    def resolve_url(self, league_name: str, season: str | None = None) -> str | None:
        """
        解析联赛名称为 OddsPortal URL

        Args:
            league_name: 数据库中的联赛名称
            season: 可选的赛季信息（用于某些特殊格式）

        Returns:
            OddsPortal results 页面 URL，如果无法解析则返回 None
        """
        # 1. 检查自定义映射
        if league_name in self.custom_mappings:
            custom_path = self.custom_mappings[league_name].get("oddsportal_path")
            if custom_path:
                url = f"{URLTemplateBuilder.BASE_URL}{custom_path}"
                logger.debug(f"Custom mapping: {league_name} -> {url}")
                return url

        # 2. 检测国家
        country = self.url_builder.detect_country(league_name)
        logger.debug(f"Detected country: {country} for league: {league_name}")

        # 3. 生成联赛 slug
        league_slug = self.url_builder.slugify(league_name)
        logger.debug(f"Generated slug: {league_slug} for league: {league_name}")

        # 4. 构建 URL
        url = self.url_builder.build_results_url(country, league_slug)
        logger.info(f"Resolved: {league_name} -> {url}")

        return url

    def resolve_with_fallback(
        self, league_name: str, home_team: str, away_team: str, season: str | None = None
    ) -> list[str]:
        """
        带回退策略的 URL 解析

        策略层级：
        1. 标准联赛路由
        2. 杯赛路由
        3. 队名搜索（最后手段）

        Args:
            league_name: 联赛名称
            home_team: 主队
            away_team: 客队
            season: 赛季

        Returns:
            URL 列表（按优先级排序）
        """
        urls = []

        # 策略 1: 标准联赛路由
        standard_url = self.resolve_url(league_name, season)
        if standard_url:
            urls.append(standard_url)

        # 策略 2: 杯赛变体（添加 "-cup" 后缀）
        if "cup" not in league_name.lower():
            cup_url = self.resolve_url(f"{league_name} Cup", season)
            if cup_url and cup_url not in urls:
                urls.append(cup_url)

        # 策略 3: 队名搜索（兜底）
        # 格式: /football/search/{team-vs-team}/
        home_slug = self.url_builder.slugify(home_team)
        away_slug = self.url_builder.slugify(away_team)
        search_url = f"{URLTemplateBuilder.BASE_URL}/football/search/{home_slug}-{away_slug}/"
        urls.append(search_url)

        logger.debug(f"Fallback URLs for {league_name}: {len(urls)} candidates")
        return urls

    def discover_all_leagues(self) -> dict[str, str]:
        """
        从数据库发现所有联赛并生成 URL 映射

        Returns:
            {league_name: oddsportal_url} 字典
        """
        import psycopg2

        from src.config_unified import get_config

        config = get_config()
        conn = psycopg2.connect(
            host=config.database.host,
            database=config.database.name,
            user=config.database.user,
            password=config.database.password.get_secret_value(),
        )

        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT league_name FROM matches ORDER BY league_name")
        leagues = [row[0] for row in cursor.fetchall()]
        conn.close()

        league_urls = {}
        for league in leagues:
            url = self.resolve_url(league)
            if url:
                league_urls[league] = url

        logger.info(f"Discovered {len(league_urls)}/{len(leagues)} league URLs")
        return league_urls


# =============================================================================
# CLI 测试入口
# =============================================================================


def main():
    """CLI 测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description="V41.243 LeagueRouter Test")
    parser.add_argument("league", help="League name to resolve")
    parser.add_argument("--season", help="Season (optional)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    # 创建路由器
    router = LeagueRouter()

    # 解析 URL
    url = router.resolve_url(args.league, args.season)

    if url:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
