#!/usr/bin/env python3
"""
OddsPortal爬虫集成模块
OddsPortal Scraper Integration Module

将OddsPortal爬虫集成到现有的数据源管理系统中
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.collectors.data_sources import DataSourceAdapter, MatchData, OddsData, TeamData
from src.collectors.oddsportal_scraper import OddsPortalMatch, OddsPortalScraper
from src.core.logging_system import get_logger

logger = get_logger(__name__)


class OddsPortalIntegration:
    """OddsPortal集成器"""

    def __init__(self, config_path: str = "config/oddsportal_config.yaml"):
        """初始化OddsPortal集成"""
        self.config = self._load_config(config_path)
        self.scraper = OddsPortalScraper()
        self.logger = logger

    def _load_config(self, config_path: str) -> dict[str, Any]:
        """加载配置文件"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # 返回默认配置
                return {
                    "scraper": {
                        "delay_min": 1.0,
                        "delay_max": 3.0,
                        "retry_count": 3,
                        "timeout": 30
                    },
                    "data_source": {
                        "name": "oddsportal",
                        "priority": 1,
                        "enabled": True
                    }
                }
        except Exception as e:
            self.logger.warning(f"加载配置文件失败: {e}")
            return {}

    async def collect_match_data(self, match_ids: list[str]) -> list[MatchData]:
        """收集比赛数据"""
        matches = []

        for match_id in match_ids:
            try:
                # 获取比赛详情
                match = await self.scraper.get_match_details(match_id)
                if match:
                    match_data = self._convert_match_data(match)
                    matches.append(match_data)

                # 添加延迟避免被封
                await asyncio.sleep(self.config.get("scraper", {}).get("delay_min", 1.0))

            except Exception as e:
                self.logger.error(f"获取比赛数据失败 {match_id}: {e}")

        return matches

    async def collect_odds_data(self, match_ids: list[str]) -> list[OddsData]:
        """收集赔率数据"""
        odds_list = []

        for match_id in match_ids:
            try:
                # 获取赔率数据
                odds = await self.scraper.get_match_odds(match_id)
                if odds:
                    odds_data = self._convert_odds_data(match_id, odds)
                    odds_list.append(odds_data)

                # 添加延迟避免被封
                await asyncio.sleep(self.config.get("scraper", {}).get("delay_min", 1.0))

            except Exception as e:
                self.logger.error(f"获取赔率数据失败 {match_id}: {e}")

        return odds_list

    async def collect_team_data(self, team_ids: list[str]) -> list[TeamData]:
        """收集队伍数据"""
        teams = []

        for team_id in team_ids:
            try:
                # 获取队伍详情
                team = await self.scraper.get_team_details(team_id)
                if team:
                    team_data = self._convert_team_data(team)
                    teams.append(team_data)

                # 添加延迟避免被封
                await asyncio.sleep(self.config.get("scraper", {}).get("delay_min", 1.0))

            except Exception as e:
                self.logger.error(f"获取队伍数据失败 {team_id}: {e}")

        return teams

    def _convert_match_data(self, match: OddsPortalMatch) -> MatchData:
        """转换比赛数据格式"""
        return MatchData(
            match_id=match.match_id,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
            competition_id=match.competition_id,
            match_time=match.match_time,
            status=match.status,
            score=match.score
        )

    def _convert_odds_data(self, match_id: str, odds: dict) -> OddsData:
        """转换赔率数据格式"""
        return OddsData(
            match_id=match_id,
            home_win=odds.get("home_win"),
            draw=odds.get("draw"),
            away_win=odds.get("away_win"),
            over_2_5=odds.get("over_2_5"),
            under_2_5=odds.get("under_2_5"),
            btts_yes=odds.get("btts_yes"),
            btts_no=odds.get("btts_no"),
            source="oddsportal",
            collection_time=datetime.now()
        )

    def _convert_team_data(self, team: dict) -> TeamData:
        """转换队伍数据格式"""
        return TeamData(
            team_id=team.get("team_id"),
            name=team.get("name"),
            country=team.get("country"),
            founded=team.get("founded"),
            stadium=team.get("stadium")
        )


class OddsPortalAdapter(DataSourceAdapter):
    """OddsPortal数据源适配器"""

    def __init__(self):
        super().__init__("oddsportal", priority=1)
        self.integration = OddsPortalIntegration()

    async def fetch_matches(self, **kwargs) -> list[MatchData]:
        """获取比赛数据"""
        match_ids = kwargs.get("match_ids", [])
        return await self.integration.collect_match_data(match_ids)

    async def fetch_odds(self, **kwargs) -> list[OddsData]:
        """获取赔率数据"""
        match_ids = kwargs.get("match_ids", [])
        return await self.integration.collect_odds_data(match_ids)

    async def fetch_teams(self, **kwargs) -> list[TeamData]:
        """获取队伍数据"""
        team_ids = kwargs.get("team_ids", [])
        return await self.integration.collect_team_data(team_ids)

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单的连接测试
            await self.integration.scraper.get_match_details("test")
            return True
        except Exception as e:
            self.logger.error(f"OddsPortal健康检查失败: {e}")
            return False


# 工厂函数
def create_oddsportal_adapter() -> OddsPortalAdapter:
    """创建OddsPortal适配器实例"""
    return OddsPortalAdapter()


def create_oddsportal_integration(config_path: str = "config/oddsportal_config.yaml") -> OddsPortalIntegration:
    """创建OddsPortal集成实例"""
    return OddsPortalIntegration(config_path)


# 导出接口
__all__ = [
    "OddsPortalIntegration",
    "OddsPortalAdapter",
    "create_oddsportal_adapter",
    "create_oddsportal_integration"
]
