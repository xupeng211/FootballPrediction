"""
FotMob 比赛详情采集器

采集比赛详情数据，包括：
- xG (Expected Goals) 数据
- 阵容信息
- 详细统计数据
"""

import asyncio
import json
import logging
from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime

from curl_cffi.requests import AsyncSession


@dataclass
class MatchStats:
    """比赛统计数据"""

    home_team: str
    away_team: str
    home_score: int
    away_score: int
    home_xg: float | None = None
    away_xg: float | None = None
    possession_home: float | None = None
    possession_away: float | None = None
    shots_home: int | None = None
    shots_away: int | None = None
    shots_on_target_home: int | None = None
    shots_on_target_away: int | None = None


@dataclass
class Player:
    """球员信息"""

    id: int | None = None
    name: str = ""
    position: str = ""
    shirt_number: int | None = None
    is_starter: bool = False


@dataclass
class TeamLineup:
    """球队阵容"""

    team_id: int | None = None
    team_name: str = ""
    formation: str | None = None
    players: list[Player] = None

    def __post_init__(self):
        if self.players is None:
            self.players = []


@dataclass
class MatchDetails:
    """比赛详情"""

    match_id: int
    home_team: str
    away_team: str
    match_date: str
    status: dict[str, Any]
    home_score: int = 0
    away_score: int = 0
    stats: MatchStats | None = None
    home_lineup: TeamLineup | None = None
    away_lineup: TeamLineup | None = None
    raw_data: dict[str, Any] | None = None


class FotmobDetailsCollector:
    """FotMob 详情采集器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

    async def _init_session(self):
        """初始化HTTP会话"""
        if self.session is None:
            # 🛡️ 使用更现代的Chrome版本进行TLS指纹伪装
            self.session = AsyncSession(
                impersonate="chrome124",
                headers={
                    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not_A Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                },
            )
            # 访问主页建立会话
            try:
                await self.session.get("https://www.fotmob.com/", timeout=10)
                self.logger.info("FotMob HTTP会话初始化成功 (Chrome124 伪装)")
            except Exception as e:
                self.logger.error(f"FotMob HTTP会话初始化失败: {e}")
                raise

    async def collect_match_details(self, match_id: str) -> MatchDetails | None:
        """
        采集比赛详情

        Args:
            match_id: 比赛ID

        Returns:
            MatchDetails 对象或 None
        """
        self.logger.info(f"开始采集比赛详情，match_id: {match_id}")

        try:
            await self._init_session()

            # 使用已验证的工作接口
            raw_data = await self._fetch_match_data(match_id)

            if not raw_data:
                self.logger.warning(f"无法获取比赛 {match_id} 的数据")
                return None

            # 解析基础信息
            match_details = self._parse_basic_info(raw_data, match_id)

            if not match_details:
                self.logger.warning(f"解析比赛 {match_id} 基础信息失败")
                return None

            # 尝试解析统计数据
            stats = self._parse_stats(raw_data)
            if stats:
                match_details.stats = stats

            # 尝试解析阵容数据
            home_lineup, away_lineup = self._parse_lineups(raw_data)
            if home_lineup:
                match_details.home_lineup = home_lineup
            if away_lineup:
                match_details.away_lineup = away_lineup

            # 保存原始数据
            match_details.raw_data = raw_data

            self.logger.info(f"比赛 {match_id} 详情采集完成")
            return match_details

        except Exception as e:
            self.logger.error(f"采集比赛 {match_id} 详情时发生错误: {e}")
            return None

    async def _fetch_match_data(self, match_id: str) -> dict[str, Any] | None:
        """获取比赛原始数据"""
        url = f"https://www.fotmob.com/api/match?id={match_id}"

        try:
            response = await self.session.get(
                url, headers=self.base_headers, timeout=15
            )

            if response.status_code == 200:
                # 修复curl_cffi的响应处理
                try:
                    if hasattr(response, "json"):
                        if asyncio.iscoroutinefunction(response.json):
                            data = await response.json()
                        else:
                            data = response.json()
                    else:
                        # 如果没有json方法，尝试解析文本
                        data = json.loads(response.text)

                    self.logger.debug(f"成功获取比赛 {match_id} 数据")
                    return data
                except Exception as json_error:
                    self.logger.error(f"解析JSON响应时出错: {json_error}")
                    # 尝试直接返回文本内容
                    return (
                        {"raw_response": response.text}
                        if hasattr(response, "text")
                        else None
                    )

            elif response.status_code == 401:
                self.logger.warning(f"比赛 {match_id} 需要认证")
                return None
            elif response.status_code == 404:
                self.logger.warning(f"比赛 {match_id} 不存在")
                return None
            else:
                self.logger.warning(
                    f"比赛 {match_id} 请求失败，状态码: {response.status_code}"
                )
                return None

        except Exception as e:
            self.logger.error(f"请求比赛 {match_id} 数据时发生异常: {e}")
            return None

    def _parse_basic_info(
        self, raw_data: dict[str, Any], match_id: str
    ) -> MatchDetails | None:
        """解析基础比赛信息"""
        try:
            home_info = raw_data.get("home", {})
            away_info = raw_data.get("away", {})

            if not home_info or not away_info:
                self.logger.warning(f"比赛 {match_id} 缺少主客队信息")
                return None

            match_details = MatchDetails(
                match_id=int(match_id),
                home_team=home_info.get("name", ""),
                away_team=away_info.get("name", ""),
                match_date=raw_data.get("matchDate", ""),
                status=raw_data.get("status", {}),
                home_score=int(home_info.get("score", 0)),
                away_score=int(away_info.get("score", 0)),
            )

            return match_details

        except Exception as e:
            self.logger.error(f"解析基础信息时发生错误: {e}")
            return None

    def _parse_stats(self, raw_data: dict[str, Any]) -> MatchStats | None:
        """解析统计数据"""
        try:
            # FotMob的统计数据可能在stats字段中
            stats_data = raw_data.get("stats")

            if not stats_data:
                # 如果stats为空，尝试从其他地方寻找xG数据
                return self._extract_xg_from_alternative_sources(raw_data)

            if isinstance(stats_data, dict):
                home_info = raw_data.get("home", {})
                away_info = raw_data.get("away", {})

                stats = MatchStats(
                    home_team=home_info.get("name", ""),
                    away_team=away_info.get("name", ""),
                    home_score=int(home_info.get("score", 0)),
                    away_score=int(away_info.get("score", 0)),
                )

                # 尝试提取xG数据
                # 这里需要根据实际的数据结构来解析
                # 暂时返回基础的统计数据结构
                return stats

        except Exception as e:
            self.logger.error(f"解析统计数据时发生错误: {e}")

        return None

    def _extract_xg_from_alternative_sources(
        self, raw_data: dict[str, Any]
    ) -> MatchStats | None:
        """从其他数据源提取xG信息"""
        # 尝试从不同的数据结构中提取xG
        # 这是一个占位符，实际实现需要根据真实的数据结构
        try:
            home_info = raw_data.get("home", {})
            away_info = raw_data.get("away", {})

            # 基础统计，xG暂时为空
            stats = MatchStats(
                home_team=home_info.get("name", ""),
                away_team=away_info.get("name", ""),
                home_score=int(home_info.get("score", 0)),
                away_score=int(away_info.get("score", 0)),
            )

            return stats

        except Exception as e:
            self.logger.error(f"从替代源提取xG时发生错误: {e}")
            return None

    def _parse_lineups(
        self, raw_data: dict[str, Any]
    ) -> tuple[TeamLineup | None, TeamLineup | None]:
        """解析阵容数据"""
        try:
            home_lineup = None
            away_lineup = None

            # FotMob的阵容数据可能在lineup字段或其他位置
            # 这里提供一个基础框架，实际实现需要根据真实数据结构调整

            home_info = raw_data.get("home", {})
            away_info = raw_data.get("away", {})

            # 创建基础阵容结构
            if home_info:
                home_lineup = TeamLineup(
                    team_id=home_info.get("id"),
                    team_name=home_info.get("name", ""),
                    formation=None,  # 需要从数据中提取
                    players=[],  # 需要从数据中提取
                )

            if away_info:
                away_lineup = TeamLineup(
                    team_id=away_info.get("id"),
                    team_name=away_info.get("name", ""),
                    formation=None,
                    players=[],
                )

            return home_lineup, away_lineup

        except Exception as e:
            self.logger.error(f"解析阵容数据时发生错误: {e}")
            return None, None

    async def batch_collect(self, match_ids: list[str]) -> list[MatchDetails]:
        """批量采集比赛详情"""
        self.logger.info(f"开始批量采集 {len(match_ids)} 场比赛详情")

        results = []
        semaphore = asyncio.Semaphore(3)  # 限制并发数

        async def collect_with_semaphore(match_id: str) -> MatchDetails | None:
            async with semaphore:
                return await self.collect_match_details(match_id)

        tasks = [collect_with_semaphore(match_id) for match_id in match_ids]
        collected_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(collected_results):
            if isinstance(result, Exception):
                self.logger.error(f"采集比赛 {match_ids[i]} 时发生异常: {result}")
            elif result is not None:
                results.append(result)

        self.logger.info(f"批量采集完成，成功采集 {len(results)} 场比赛")
        return results

    async def close(self):
        """关闭会话"""
        if self.session:
            # curl_cffi的AsyncSession没有aclose方法，直接设为None
            self.session = None
            self.logger.info("FotMob HTTP会话已关闭")


# 便捷函数
async def collect_match_details(match_id: str) -> MatchDetails | None:
    """便捷的单一比赛详情采集函数"""
    collector = FotmobDetailsCollector()
    try:
        return await collector.collect_match_details(match_id)
    finally:
        await collector.close()


async def collect_multiple_matches(match_ids: list[str]) -> list[MatchDetails]:
    """便捷的批量比赛详情采集函数"""
    collector = FotmobDetailsCollector()
    try:
        return await collector.batch_collect(match_ids)
    finally:
        await collector.close()
