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
from typing import Any, Optional, Dict, List
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
            # 核心请求头 - 模拟最新 Chrome 131
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",

            # 浏览器安全头 - 最新 Chrome 指纹
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',

            # 来源和引用 - 模拟真实浏览
            "Referer": "https://www.fotmob.com/matches",
            "Origin": "https://www.fotmob.com",

            # Fetch API 相关头
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",

            # 缓存控制
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",

            # 连接管理
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",

            # DNT (Do Not Track) - 可选
            # "DNT": "1",
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

    async def get_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        获取比赛详情数据 (兼容测试用的新接口)

        Args:
            match_id: FotMob 比赛 ID

        Returns:
            比赛详情数据，包含结构化的阵容、射门和统计信息
            如果获取失败返回 None
        """
        # 调用现有的 matchDetails API endpoint
        url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

        try:
            await self._init_session()

            self.logger.info(f"Fetching match details for match_id: {match_id}")
            response = await self.session.get(url, headers=self.base_headers, timeout=30.0)

            if response.status_code == 200:
                # 处理响应数据
                if hasattr(response, "json"):
                    if asyncio.iscoroutinefunction(response.json):
                        data = await response.json()
                    elif callable(response.json):
                        data = response.json()
                    else:
                        # 如果json是属性而不是方法
                        data = response.json
                else:
                    data = json.loads(response.text)

                # 提取并结构化数据
                structured_data = self._structure_match_data(data)
                self.logger.info(f"Successfully fetched details for match {match_id}")
                return structured_data
            else:
                self.logger.error(f"HTTP {response.status_code} when fetching match {match_id}")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching match details for {match_id}: {str(e)}")
            return None

    def _structure_match_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        结构化原始比赛数据

        Args:
            raw_data: FotMob API 返回的原始数据

        Returns:
            结构化的比赛数据
        """
        structured = {
            "matchId": self._extract_match_id(raw_data),
            "match_info": self._extract_match_info(raw_data),
            "lineup": self._extract_lineup_data(raw_data),
            "shots": self._extract_shot_data(raw_data),
            "stats": self._extract_match_stats(raw_data),
            "fetched_at": datetime.utcnow().isoformat()
        }

        return structured

    def _extract_match_id(self, data: Dict[str, Any]) -> str:
        """提取比赛 ID"""
        try:
            return data.get("match", {}).get("matchId", "")
        except Exception:
            return ""

    def _extract_match_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取比赛基本信息"""
        try:
            match = data.get("match", {})
            return {
                "home_team": match.get("home", {}).get("name", ""),
                "away_team": match.get("away", {}).get("name", ""),
                "home_score": match.get("home", {}).get("score", 0),
                "away_score": match.get("away", {}).get("score", 0),
                "status": match.get("status", {}),
                "start_time": match.get("status", {}).get("startTimeStr", ""),
                "finished": match.get("status", {}).get("finished", False)
            }
        except Exception as e:
            self.logger.error(f"Error extracting match info: {str(e)}")
            return {}

    def _extract_lineup_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取阵容数据

        Returns:
            {
                "home": {
                    "starters": [球员列表],
                    "substitutes": [替补列表]
                },
                "away": {
                    "starters": [球员列表],
                    "substitutes": [替补列表]
                }
            }
        """
        try:
            lineup_content = data.get("content", {}).get("lineup", {})
            lineup_data = {
                "home": self._process_team_lineup(lineup_content.get("home", {})),
                "away": self._process_team_lineup(lineup_content.get("away", {}))
            }
            return lineup_data
        except Exception as e:
            self.logger.error(f"Error extracting lineup data: {str(e)}")
            return {"home": {"starters": [], "substitutes": []}, "away": {"starters": [], "substitutes": []}}

    def _process_team_lineup(self, team_lineup: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """处理单个球队的阵容数据"""
        return {
            "starters": self._process_players(team_lineup.get("starters", [])),
            "substitutes": self._process_players(team_lineup.get("substitutes", []))
        }

    def _process_players(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理球员数据列表"""
        processed_players = []
        for player in players:
            processed_player = {
                "id": player.get("id"),
                "name": player.get("name", ""),
                "position": player.get("position", ""),
                "shirtNumber": player.get("shirtNumber"),
                "captain": player.get("captain", False)
            }
            processed_players.append(processed_player)
        return processed_players

    def _extract_shot_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提取射门数据

        Returns:
            射门数据列表，包含 xG 值、射门类型等信息
        """
        try:
            shotmap_content = data.get("content", {}).get("shotmap", {})
            shots = shotmap_content.get("shots", [])

            processed_shots = []
            for shot in shots:
                processed_shot = {
                    "id": shot.get("id"),
                    "team": shot.get("team"),
                    "player": shot.get("player", {}),
                    "minute": shot.get("minute"),
                    "xg": shot.get("xg", 0.0),
                    "situation": shot.get("situation"),
                    "shotType": shot.get("shotType"),
                    "isGoal": shot.get("isGoal", False),
                    "bodyPart": shot.get("bodyPart")
                }
                processed_shots.append(processed_shot)

            return processed_shots
        except Exception as e:
            self.logger.error(f"Error extracting shot data: {str(e)}")
            return []

    def _extract_match_stats(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提取比赛统计数据

        Returns:
            统计数据列表，如控球率、射门数等
        """
        try:
            stats_content = data.get("content", {}).get("stats", {})
            stats = stats_content.get("stats", [])

            processed_stats = []
            for stat_group in stats:
                stat_type = stat_group.get("type", "")
                stat_values = stat_group.get("stats", [])

                for stat in stat_values:
                    processed_stat = {
                        "type": stat_type,
                        "statType": stat.get("type", ""),
                        "value": stat.get("value", "")
                    }
                    processed_stats.append(processed_stat)

            return processed_stats
        except Exception as e:
            self.logger.error(f"Error extracting match stats: {str(e)}")
            return []

    # 添加 headers 属性以兼容测试
    @property
    def headers(self) -> Dict[str, str]:
        """获取 HTTP 头部"""
        return self.base_headers

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
