#!/usr/bin/env python3
"""V20.0 动态联赛元数据管理器.

架构设计:
- 自动从 FotMob API 抓取联赛元数据
- 维护赛季别名映射 (API格式 vs 存储格式)
- 提供联赛ID的动态查询能力
- 支持元数据缓存与自动刷新

作者: Data Architecture Team
日期: 2025-12-24
版本: V20.0
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class LeagueMetadata:
    """联赛元数据实体."""

    def __init__(self, league_id: int, name: str, country: str, tier: str = "unknown") -> None:
        """初始化联赛元数据."""
        self.league_id = league_id
        self.name = name
        self.country = country
        self.tier = tier
        self.season_aliases: dict[str, str] = {}  # API格式 -> 存储格式
        self.available_seasons: list[str] = []
        self.last_updated: datetime | None = None

    def add_season_mapping(self, api_format: str, storage_format: str) -> None:
        """添加赛季别名映射."""
        self.season_aliases[api_format] = storage_format

    def get_storage_season(self, api_season: str) -> str | None:
        """将API赛季格式转换为存储格式."""
        return self.season_aliases.get(api_season)

    def to_dict(self) -> dict:
        """序列化为字典."""
        return {
            "league_id": self.league_id,
            "name": self.name,
            "country": self.country,
            "tier": self.tier,
            "season_aliases": self.season_aliases,
            "available_seasons": self.available_seasons,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class MetadataManager:
    """动态联赛元数据管理器.

    核心职责:
    1. 从 allLeagues API 抓取最新联赛信息
    2. 维护赛季格式映射
    3. 提供联赛ID的动态查询
    4. 支持元数据持久化与缓存
    """

    # 五大联赛基准名称（用于模糊匹配）
    BIG_FIVE_LEAGUES = {
        "Premier League": {"country": "England", "tier": "tier_1_premium"},
        "LaLiga": {
            "country": "Spain",
            "tier": "tier_1_premium",
            "aliases": ["La Liga", "LaLiga"],
        },
        "Serie A": {"country": "Italy", "tier": "tier_1_premium"},
        "Bundesliga": {"country": "Germany", "tier": "tier_1_premium"},
        "Ligue 1": {"country": "France", "tier": "tier_1_premium"},
    }

    # 赛季格式映射模板
    SEASON_FORMAT_TEMPLATES = {
        "api_to_storage": {
            "2021/2022": "2122",
            "2022/2023": "2223",
            "2023/2024": "2324",
            "2024/2025": "2425",
            "2025/2026": "2526",
        },
        "storage_to_api": {
            "2122": "2021/2022",
            "2223": "2022/2023",
            "2324": "2023/2024",
            "2425": "2024/2025",
            "2526": "2025/2026",
        },
    }

    def __init__(self, cache_dir: str = "data/metadata") -> None:
        """初始化元数据管理器."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.leagues: dict[int, LeagueMetadata] = {}
        self.name_to_id: dict[str, int] = {}
        self.cache_expiry = timedelta(hours=24)  # 缓存24小时

        # FotMob API 端点
        self.all_leagues_url = "https://www.fotmob.com/api/allLeagues"

        logger.info("=== V20.0 动态联赛元数据管理器初始化 ===")

    def fetch_all_leagues(self) -> dict:
        """从 FotMob API 抓取所有联赛元数据.

        Returns:
            API响应的JSON数据

        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            response = requests.get(self.all_leagues_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"抓取 allLeagues API 失败: {e}")
            return {}

    def discover_big_five_leagues(self, api_data: dict) -> list[LeagueMetadata]:
        """从 API 数据中发现五大联赛

        API 结构:
        {
            "popular": [{"id": 47, "name": "Premier League", ...}],
            "countries": [{"name": "England", "leagues": [...]}]
        }

        Args:
            api_data: allLeagues API 响应

        Returns:
            发现的五大联赛元数据列表

        """
        discovered = []
        found_ids = set()

        if not api_data:
            logger.warning("API 数据为空，无法发现联赛")
            return discovered

        # 1. 从 popular 列表中查找
        popular = api_data.get("popular", [])
        for league_item in popular:
            league_id = league_item.get("id", 0)
            league_name = league_item.get("name", "")
            ccode = league_item.get("ccode", "")

            # 检查是否是五大联赛之一
            for target_name, target_info in self.BIG_FIVE_LEAGUES.items():
                aliases = target_info.get("aliases", [target_name])
                if any(alias.lower() in league_name.lower() for alias in aliases):
                    if league_id not in found_ids:
                        metadata = self._create_metadata(league_id, league_name, target_info)
                        discovered.append(metadata)
                        found_ids.add(league_id)
                        logger.info(f"✅ 发现联赛 (popular): {league_name} (ID: {league_id})")
                    break

        # 2. 从 countries 列表中查找（补充 popular 中遗漏的）
        countries = api_data.get("countries", [])
        for country_item in countries:
            country_name = country_item.get("name", "")
            leagues = country_item.get("leagues", [])

            for league_item in leagues:
                league_id = league_item.get("id", 0)
                league_name = league_item.get("name", "")

                if league_id in found_ids:
                    continue

                for target_name, target_info in self.BIG_FIVE_LEAGUES.items():
                    if target_info["country"] == country_name:
                        aliases = target_info.get("aliases", [target_name])
                        if any(alias.lower() in league_name.lower() for alias in aliases):
                            metadata = self._create_metadata(league_id, league_name, target_info)
                            discovered.append(metadata)
                            found_ids.add(league_id)
                            logger.info(f"✅ 发现联赛 (countries): {league_name} (ID: {league_id})")
                            break

        return discovered

    def _create_metadata(self, league_id: int, league_name: str, target_info: dict) -> LeagueMetadata:
        """创建联赛元数据并获取可用赛季

        Args:
            league_id: 联赛ID
            league_name: 联赛名称
            target_info: 目标联赛信息

        Returns:
            LeagueMetadata 对象

        """
        metadata = LeagueMetadata(
            league_id=league_id,
            name=league_name,
            country=target_info["country"],
            tier=target_info["tier"],
        )

        # 获取可用赛季
        seasons = self._fetch_league_seasons(league_id)
        metadata.available_seasons = seasons

        # 建立赛季映射
        for season in seasons:
            storage_format = self.SEASON_FORMAT_TEMPLATES["api_to_storage"].get(season)
            if storage_format:
                metadata.add_season_mapping(season, storage_format)

        return metadata

    def _fetch_league_seasons(self, league_id: int) -> list[str]:
        """获取联赛的可用赛季

        Args:
            league_id: 联赛ID

        Returns:
            赛季列表

        """
        try:
            url = f"https://www.fotmob.com/api/leagues?id={league_id}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            # 从 allAvailableSeasons 获取赛季
            seasons = data.get("allAvailableSeasons", [])
            return [s for s in seasons if s]  # 过滤空值

        except Exception as e:
            logger.warning(f"获取联赛 {league_id} 赛季失败: {e}")
            return []

    def load_cache(self) -> bool:
        """从缓存加载元数据"""
        cache_file = self.cache_dir / "leagues_metadata.json"

        if not cache_file.exists():
            return False

        try:
            with open(cache_file, encoding="utf-8") as f:
                cache_data = json.load(f)

            # 检查缓存是否过期
            last_update = datetime.fromisoformat(cache_data.get("last_update", ""))
            if datetime.now() - last_update > self.cache_expiry:
                logger.info("缓存已过期，需要刷新")
                return False

            # 重建元数据对象
            for league_data in cache_data.get("leagues", []):
                metadata = LeagueMetadata(
                    league_id=league_data["league_id"],
                    name=league_data["name"],
                    country=league_data["country"],
                    tier=league_data["tier"],
                )
                metadata.season_aliases = league_data["season_aliases"]
                metadata.available_seasons = league_data["available_seasons"]
                metadata.last_updated = last_update

                self.leagues[metadata.league_id] = metadata
                self.name_to_id[metadata.name] = metadata.league_id

            logger.info(f"✅ 从缓存加载 {len(self.leagues)} 个联赛元数据")
            return True

        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return False

    def save_cache(self):
        """保存元数据到缓存"""
        cache_file = self.cache_dir / "leagues_metadata.json"

        cache_data = {
            "last_update": datetime.now().isoformat(),
            "leagues": [m.to_dict() for m in self.leagues.values()],
        }

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 元数据已缓存到 {cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def refresh_metadata(self, force: bool = False) -> bool:
        """刷新联赛元数据

        Args:
            force: 是否强制刷新（忽略缓存）

        Returns:
            是否成功刷新

        """
        if not force and self.load_cache():
            return True

        logger.info("🔄 从 FotMob API 刷新联赛元数据...")

        api_data = self.fetch_all_leagues()
        if not api_data:
            return False

        discovered = self.discover_big_five_leagues(api_data)

        if not discovered:
            logger.error("❌ 未能发现任何五大联赛")
            return False

        # 更新内部状态
        self.leagues.clear()
        self.name_to_id.clear()

        for metadata in discovered:
            metadata.last_updated = datetime.now()
            self.leagues[metadata.league_id] = metadata
            self.name_to_id[metadata.name] = metadata.league_id

        # 保存缓存
        self.save_cache()

        return True

    def get_league_id(self, league_name: str) -> int | None:
        """根据联赛名称获取 ID（支持模糊匹配）

        Args:
            league_name: 联赛名称

        Returns:
            联赛ID，未找到返回 None

        """
        # 精确匹配
        if league_name in self.name_to_id:
            return self.name_to_id[league_name]

        # 模糊匹配
        league_lower = league_name.lower()
        for name, league_id in self.name_to_id.items():
            if league_lower in name.lower() or name.lower() in league_lower:
                return league_id

        return None

    def get_league_metadata(self, league_id: int) -> LeagueMetadata | None:
        """获取联赛元数据"""
        return self.leagues.get(league_id)

    def convert_season_format(self, league_id: int, season: str, target_format: str = "storage") -> str | None:
        """转换赛季格式

        Args:
            league_id: 联赛ID
            season: 输入赛季字符串
            target_format: 目标格式 ('storage' 或 'api')

        Returns:
            转换后的赛季字符串

        """
        if target_format == "storage":
            # API -> Storage (需要联赛元数据)
            metadata = self.leagues.get(league_id)
            if not metadata:
                # 尝试从模板直接查找
                return self.SEASON_FORMAT_TEMPLATES["api_to_storage"].get(season)
            return metadata.get_storage_season(season)
        # Storage -> API (直接从模板查找)
        return self.SEASON_FORMAT_TEMPLATES["storage_to_api"].get(season)

    def get_big_five_config(self) -> dict[int, dict]:
        """获取五大联赛配置字典（用于兼容现有代码）

        Returns:
            {league_id: {'name': str, 'country': str, 'tier': str}}

        """
        return {
            league_id: {
                "name": metadata.name,
                "country": metadata.country,
                "tier": metadata.tier,
            }
            for league_id, metadata in self.leagues.items()
        }

    def print_registry(self):
        """打印当前元数据注册表"""
        logger.info("\n=== 联赛元数据注册表 ===")
        for league_id, metadata in self.leagues.items():
            logger.info(f"\n📋 {metadata.name} (ID: {league_id})")
            logger.info(f"   国家: {metadata.country}")
            logger.info(f"   等级: {metadata.tier}")
            logger.info(f"   可用赛季: {metadata.available_seasons}")
            logger.info(f"   赛季映射: {metadata.season_aliases}")


# 单例实例
_metadata_manager_instance: MetadataManager | None = None


def get_metadata_manager() -> MetadataManager:
    """获取元数据管理器单例"""
    global _metadata_manager_instance
    if _metadata_manager_instance is None:
        _metadata_manager_instance = MetadataManager()
        _metadata_manager_instance.refresh_metadata()
    return _metadata_manager_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    manager = get_metadata_manager()
    manager.print_registry()

    # 测试查询
    print("\n=== 测试查询 ===")
    print(f"Ligue 1 ID: {manager.get_league_id('Ligue 1')}")
    print(f"Premier League ID: {manager.get_league_id('Premier League')}")
    print(f"Season 2223 -> API: {manager.convert_season_format(53, '2223', 'api')}")
