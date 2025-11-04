from datetime import datetime

#!/usr/bin/env python3
"""
OddsPortal爬虫集成模块
OddsPortal Scraper Integration Module

将OddsPortal爬虫集成到现有的数据源管理系统中
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from src.collectors.data_sources import DataSourceAdapter, MatchData, OddsData, TeamData
from src.collectors.oddsportal_scraper import OddsPortalMatch, OddsPortalScraper
from src.core.logging_system import get_logger

logger = get_logger(__name__)


class OddsPortalIntegration:
    """类文档字符串"""

    pass  # 添加pass语句
    """OddsPortal爬虫集成管理器"""

    def __init__(self, config_path: str | None = None):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """
        初始化OddsPortal集成

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.scraper = None
        self.is_initialized = False
        self.logger = get_logger(self.__class__.__name__)

        # 验证配置
        self._validate_config()

    def _load_config(self, config_path: str | None = None) -> dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent
                / "config"
                / "oddsportal_config.yaml"
            )

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded OddsPortal configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(
                f"Configuration file not found: {config_path}, using defaults"
            )
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise

    def _get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "basic": {
                "enabled": True,
                "name": "OddsPortal",
                "type": "web_scraper",
                "base_url": "https://www.oddsportal.com",
            },
            "request": {
                "timeout": 30,
                "max_retries": 3,
                "rate_limit": {"requests_per_minute": 60, "min_request_interval": 1.0},
            },
            "scraping": {
                "modes": {
                    "today_matches": {"enabled": True},
                    "live_matches": {"enabled": True},
                    "league_matches": {"enabled": True},
                }
            },
        }

    def _validate_config(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """验证配置"""
        required_sections = ["basic", "request", "scraping"]
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")

        if not self.config["basic"].get("enabled", False):
            logger.warning("OddsPortal integration is disabled in configuration")

    async def initialize(self):
        """初始化爬虫"""
        if self.is_initialized:
            return None
        try:
            # 从配置创建爬虫
            scraper_config = {
                "base_url": self.config["basic"]["base_url"],
                "timeout": self.config["request"]["timeout"],
                "max_retries": self.config["request"]["max_retries"],
                "rate_limit": self.config["request"]["rate_limit"],
            }

            self.scraper = OddsPortalScraper(scraper_config)
            await self.scraper._init_session()

            self.is_initialized = True
            self.logger.info("OddsPortal scraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize OddsPortal scraper: {e}")
            raise

    async def cleanup(self):
        """清理资源"""
        if self.scraper and self.scraper.session:
            await self.scraper.session.close()
            self.logger.info("OddsPortal scraper cleaned up")

    async def scrape_today_matches(self) -> list[MatchData]:
        """抓取今日比赛数据"""
        if not self.is_initialized:
            await self.initialize()

        if not self.config["scraping"]["modes"]["today_matches"]["enabled"]:
            logger.info("Today matches scraping is disabled")
            return []

        try:
            self.logger.info("Starting today matches scraping")
            matches = await self.scraper.scrape_today_matches()

            # 转换为MatchData格式
            match_data_list = []
            for match in matches:
                match_data = self._convert_to_match_data(match)
                if match_data:
                    match_data_list.append(match_data)

            self.logger.info(f"Scraped {len(match_data_list)} today matches")
            return match_data_list

        except Exception as e:
            self.logger.error(f"Error scraping today matches: {e}")
            return []

    async def scrape_live_matches(self) -> list[MatchData]:
        """抓取实时比赛数据"""
        if not self.is_initialized:
            await self.initialize()

        if not self.config["scraping"]["modes"]["live_matches"]["enabled"]:
            logger.info("Live matches scraping is disabled")
            return []

        try:
            self.logger.info("Starting live matches scraping")
            matches = await self.scraper.scrape_live_matches()

            # 转换为MatchData格式
            match_data_list = []
            for match in matches:
                match_data = self._convert_to_match_data(match)
                if match_data:
                    match_data_list.append(match_data)

            self.logger.info(f"Scraped {len(match_data_list)} live matches")
            return match_data_list

        except Exception as e:
            self.logger.error(f"Error scraping live matches: {e}")
            return []

    async def scrape_league_matches(self, league_key: str) -> list[MatchData]:
        """抓取指定联赛的比赛数据"""
        if not self.is_initialized:
            await self.initialize()

        if not self.config["scraping"]["modes"]["league_matches"]["enabled"]:
            logger.info("League matches scraping is disabled")
            return []

        try:
            league_config = self.config["leagues"].get(league_key)
            if not league_config or not league_config.get("enabled", False):
                logger.warning(f"League {league_key} is not enabled or configured")
                return []

            self.logger.info(
                f"Starting league matches scraping for {league_config['name']}"
            )
            matches = await self.scraper.scrape_league_matches(
                league_config["url"], league_config["name"]
            )

            # 转换为MatchData格式
            match_data_list = []
            for match in matches:
                match_data = self._convert_to_match_data(match)
                if match_data:
                    match_data_list.append(match_data)

            self.logger.info(
                f"Scraped {len(match_data_list)} matches for {league_config['name']}"
            )
            return match_data_list

        except Exception as e:
            self.logger.error(f"Error scraping league matches for {league_key}: {e}")
            return []

    def _convert_to_match_data(self, match: OddsPortalMatch) -> MatchData | None:
        """将OddsPortalMatch转换为MatchData"""
        try:
            # 创建比赛数据（MatchData不包含odds字段）
            match_id = (
                int(match.match_id)
                if match.match_id.isdigit()
                else hash(match.match_id) % 1000000
            )

            match_data = MatchData(
                id=match_id,
                home_team=match.home_team,
                away_team=match.away_team,
                league=match.league,
                match_date=match.match_date,
                status=match.status,
                home_score=match.home_score,
                away_score=match.away_score,
            )

            return match_data

        except Exception as e:
            self.logger.error(f"Error converting match data: {e}")
            return None

    async def get_source_info(self) -> dict[str, Any]:
        """获取数据源信息"""
        return {
            "name": self.config["basic"]["name"],
            "type": self.config["basic"]["type"],
            "base_url": self.config["basic"]["base_url"],
            "supported_sports": self.config["basic"]["supported_sports"],
            "enabled": self.config["basic"]["enabled"],
            "configured_leagues": len(
                [
                    league
                    for league in self.config.get("leagues", {}).values()
                    if league.get("enabled", False)
                ]
            ),
        }

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.is_initialized:
                await self.initialize()

            # 简单测试:获取今日比赛数量
            await self.scrape_today_matches()
            return True

        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        try:
            # 测试连接
            connection_ok = await self.test_connection()

            # 检查配置状态
            config_ok = self._validate_config() is None

            # 检查初始化状态
            init_ok = self.is_initialized

            return {
                "status": (
                    "healthy"
                    if all([connection_ok, config_ok, init_ok])
                    else "unhealthy"
                ),
                "connection": connection_ok,
                "configuration": config_ok,
                "initialization": init_ok,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


class OddsPortalAdapter(DataSourceAdapter):
    """OddsPortal适配器,实现DataSourceAdapter接口"""

    def __init__(self, config_path: str | None = None, api_key: str | None = None):
        super().__init__(api_key)
        self.integration = OddsPortalIntegration(config_path)
        self.logger = get_logger(self.__class__.__name__)

    async def get_matches(
        self,
        league_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[MatchData]:
        """获取比赛列表"""
        try:
            # OddsPortal使用联赛名称而非ID
            if league_id:
                # 将ID映射到联赛名称（简化实现）
                league_mapping = {
                    39: "premier_league",
                    140: "la_liga",
                    78: "bundesliga",
                    135: "serie_a",
                    61: "ligue_1",
                }
                league_key = league_mapping.get(league_id)
                if league_key:
                    matches = await self.integration.scrape_league_matches(league_key)
                else:
                    matches = await self.integration.scrape_today_matches()
            else:
                matches = await self.integration.scrape_today_matches()

            # 应用日期过滤
            if date_from or date_to:
                filtered_matches = []
                for match in matches:
                    match_date = match.match_date.date()
                    if date_from and match_date < date_from.date():
                        continue
                    if date_to and match_date > date_to.date():
                        continue
                    filtered_matches.append(match)
                matches = filtered_matches

            return matches

        except Exception as e:
            self.logger.error(f"Error fetching matches: {e}")
            return []

    async def get_teams(self, league_id: int | None = None) -> list[TeamData]:
        """获取球队列表"""
        try:
            # 从比赛数据中提取球队信息
            matches = await self.get_matches(league_id)
            teams_set = set()
            teams_list = []

            for match in matches:
                if match.home_team not in teams_set:
                    teams_set.add(match.home_team)
                    teams_list.append(
                        TeamData(
                            id=hash(match.home_team) % 1000000, name=match.home_team
                        )
                    )
                if match.away_team not in teams_set:
                    teams_set.add(match.away_team)
                    teams_list.append(
                        TeamData(
                            id=hash(match.away_team) % 1000000, name=match.away_team
                        )
                    )

            return teams_list

        except Exception as e:
            self.logger.error(f"Error fetching teams: {e}")
            return []

    async def get_odds(self, match_id: int) -> list[OddsData]:
        """获取赔率数据"""
        try:
            # 获取所有比赛并创建赔率数据
            matches = await self.integration.scrape_today_matches()

            for match in matches:
                if match.id == match_id:
                    # 从原始OddsPortalMatch创建OddsData
                    odds_portal_match = None
                    for (
                        op_match
                    ) in await self.integration.scraper.scrape_today_matches():
                        if (
                            op_match.match_id == str(match_id)
                            or hash(op_match.match_id) % 1000000 == match_id
                        ):
                            odds_portal_match = op_match
                            break

                    if odds_portal_match and odds_portal_match.odds_home_win:
                        odds_data = OddsData(
                            match_id=match_id,
                            home_win=odds_portal_match.odds_home_win,
                            draw=odds_portal_match.odds_draw,
                            away_win=odds_portal_match.odds_away_win,
                            source="oddsportal",
                            over_under=odds_portal_match.over_under,
                            asian_handicap=odds_portal_match.asian_handicap,
                        )
                        return [odds_data]

            return []

        except Exception as e:
            self.logger.error(f"Error fetching odds for match {match_id}: {e}")
            return []

    # 保留原有的便利方法
    async def fetch_matches(
        self, league: str | None = None, limit: int | None = None
    ) -> list[MatchData]:
        """获取比赛数据（便利方法）"""
        try:
            if league:
                matches = await self.integration.scrape_league_matches(league)
            else:
                matches = await self.integration.scrape_today_matches()

            if limit and len(matches) > limit:
                matches = matches[:limit]

            return matches

        except Exception as e:
            self.logger.error(f"Error fetching matches: {e}")
            return []

    async def test_connection(self) -> bool:
        """测试连接"""
        return await self.integration.test_connection()

    async def get_source_info(self) -> dict[str, Any]:
        """获取数据源信息"""
        return await self.integration.get_source_info()


# 全局实例
_oddsportal_instance: OddsPortalIntegration | None = None


async def get_oddsportal_integration() -> OddsPortalIntegration:
    """获取OddsPortal集成实例（单例）"""
    global _oddsportal_instance

    if _oddsportal_instance is None:
        _oddsportal_instance = OddsPortalIntegration()
        await _oddsportal_instance.initialize()

    return _oddsportal_instance


async def main():
    """主函数,用于测试"""
    integration = OddsPortalIntegration()

    try:
        # 初始化
        await integration.initialize()

        # 健康检查
        health = await integration.health_check()
        print(f"Health check: {json.dumps(health, indent=2)}")

        # 获取数据源信息
        info = await integration.get_source_info()
        print(f"Source info: {json.dumps(info, indent=2)}")

        # 抓取今日比赛（测试少量数据）
        print("Testing today matches scraping...")
        matches = await integration.scrape_today_matches()
        print(f"Found {len(matches)} today matches")

        # 显示前3个比赛
        for i, match in enumerate(matches[:3]):
            print(
                f"Match {i + 1}: {match.home_team} vs {match.away_team} ({match.league})"
            )

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await integration.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
