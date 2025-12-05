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
    """增强的球员信息 - 全量收割版"""

    id: int | None = None
    name: str = ""
    position: str = ""
    shirt_number: int | None = None
    is_starter: bool = False
    # 全量收割新增字段
    rating: float | None = None  # 球员评分 (关键)
    minutes_played: int | None = None  # 出场时间
    goals: int | None = None  # 进球数
    assists: int | None = None  # 助攻数
    shots: int | None = None  # 射门数
    shots_on_target: int | None = None  # 射正数
    yellow_cards: int | None = None  # 黄牌
    red_cards: int | None = None  # 红牌
    fouls: int | None = None  # 犯规
    fouled_against: int | None = None  # 被犯规
    passes_completed: int | None = None  # 传球成功数
    passes_attempted: int | None = None  # 传球尝试数
    pass_accuracy: float | None = None  # 传球成功率
    duels_won: int | None = None  # 对抗胜利数
    duels_lost: int | None = None  # 对抗失败数
    aerials_won: int | None = None  # 空中对抗胜利数
    aerials_lost: int | None = None  # 空中对抗失败数


@dataclass
class Odds:
    """赔率数据 - 全量收割版"""

    home_win: float | None = None  # 主胜赔率
    draw: float | None = None  # 平局赔率
    away_win: float | None = None  # 客胜赔率
    over_25: float | None = None  # 大2.5球赔率
    under_25: float | None = None  # 小2.5球赔率
    both_teams_score: bool | None = None  # 双方都进球
    over_under: dict[str, float] | None = None  # 其他大小球赔率
    asian_handicap: dict[str, float] | None = None  # 让球盘赔率
    total_goals: dict[str, float] | None = None  # 总进球数赔率
    providers: dict[str, Any] | None = None  # 各博彩公司赔率


@dataclass
class MatchMetadata:
    """比赛元数据 - 全量收割版"""

    referee: str | None = None  # 裁判姓名 (关键)
    stadium: str | None = None  # 球场名称
    attendance: int | None = None  # 观众人数
    weather: dict[str, Any] | None = None  # 天气信息
    match_day: str | None = None  # 比赛日
    round: str | None = None  # 轮次
    competition_stage: str | None = None  # 淘汰赛阶段
    venue_capacity: int | None = None  # 场馆容量
    city: str | None = None  # 城市
    country: str | None = None  # 国家


@dataclass
class MatchEvent:
    """比赛事件 - 全量收割版"""

    id: int | None = None
    minute: int | None = None  # 发生时间
    team_id: int | None = None  # 球队ID
    player_id: int | None = None  # 球员ID
    player_name: str | None = None  # 球员姓名
    event_type: str | None = None  # 事件类型: goal, card, substitution等
    sub_type: str | None = None  # 子类型: yellow_card, red_card, own_goal等
    is_assist: bool = False  # 是否为助攻
    assist_player_id: int | None = None  # 助攻球员ID
    assist_player_name: str | None = None  # 助攻球员姓名
    coordinate_x: float | None = None  # 事件坐标X
    coordinate_y: float | None = None  # 事件坐标Y
    timestamp: str | None = None  # 时间戳


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
    """增强的比赛详情 - 全量收割版"""

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
    # 全量收割新增字段
    odds: Odds | None = None  # 赔率数据 (关键)
    match_metadata: MatchMetadata | None = None  # 比赛元数据 (关键)
    events: list[MatchEvent] | None = None  # 详细事件流 (关键)
    raw_data: dict[str, Any] | None = None

    def __post_init__(self):
        if self.events is None:
            self.events = []


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
            # 🔧 修复认证和反爬虫问题
            self.session = AsyncSession(
                impersonate="chrome131",  # 使用最新Chrome版本
                headers={
                    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-arch": '"x86"',
                    "sec-ch-ua-bitness": '"64"',
                },
                timeout=30.0
            )

            # 🔍 多步认证流程
            try:
                # 第一步：访问主页建立基础会话
                self.logger.info("第一步：建立基础会话...")
                await self.session.get("https://www.fotmob.com/", timeout=15)

                # 第二步：访问比赛列表页激活API访问权限
                self.logger.info("第二步：激活API访问权限...")
                await self.session.get("https://www.fotmob.com/matches", timeout=15)

                # 第三步：等待几秒让认证生效
                await asyncio.sleep(2)

                self.logger.info("FotMob HTTP会话初始化成功 (Chrome131 + 多步认证)")
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

    async def get_match_details(self, match_id: str) -> Optional[dict[str, Any]]:
        """
        获取比赛详情数据 (修复API认证和端点问题)

        Args:
            match_id: FotMob 比赛 ID

        Returns:
            比赛详情数据，包含结构化的阵容、射门和统计信息
            如果获取失败返回 None
        """
        # 🔧 尝试多个API端点，寻找有效的接口
        endpoints = [
            f"https://www.fotmob.com/api/matchDetails?matchId={match_id}",
            f"https://www.fotmob.com/api/match?id={match_id}",
            f"https://www.fotmob.com/api/matches?matchId={match_id}",
            # 新的可能端点
            f"https://www.fotmob.com/api/matchDetails/{match_id}",
            f"https://fotmob.com/api/matchDetails?matchId={match_id}",
        ]

        await self._init_session()

        for i, url in enumerate(endpoints, 1):
            self.logger.info(f"尝试端点 {i}/{len(endpoints)}: {url}")

            try:
                response = await self.session.get(url, headers=self.base_headers, timeout=30.0)

                self.logger.info(f"端点 {i} 响应: HTTP {response.status_code}")

                if response.status_code == 200:
                    # ✅ 成功！
                    self.logger.info(f"✅ 端点 {i} 成功!")

                    # 处理响应数据
                    try:
                        if hasattr(response, "json"):
                            if asyncio.iscoroutinefunction(response.json):
                                data = await response.json()
                            elif callable(response.json):
                                data = response.json()
                            else:
                                data = response.json
                        else:
                            data = json.loads(response.text)

                        # 验证数据结构
                        if isinstance(data, dict) and "content" in data:
                            self.logger.info("✅ 数据结构验证成功")

                            # 提取并结构化数据
                            structured_data = self._structure_match_data(data)
                            self.logger.info(f"Successfully fetched details for match {match_id} using endpoint {i}")
                            return structured_data
                        else:
                            self.logger.warning(f"⚠️ 端点 {i} 返回的数据结构不正确: {type(data)}")
                            continue

                    except json.JSONDecodeError as e:
                        self.logger.warning(f"⚠️ 端点 {i} JSON解析失败: {e}")
                        continue

                elif response.status_code == 401:
                    self.logger.warning(f"⚠️ 端点 {i} 认证失败 (401)")
                elif response.status_code == 403:
                    self.logger.warning(f"⚠️ 端点 {i} 访问被禁止 (403)")
                elif response.status_code == 404:
                    self.logger.warning(f"⚠️ 端点 {i} 不存在 (404)")
                else:
                    self.logger.warning(f"⚠️ 端点 {i} HTTP错误: {response.status_code}")

            except Exception as e:
                self.logger.warning(f"⚠️ 端点 {i} 请求异常: {e}")

        # 所有端点都失败了
        self.logger.error(f"❌ 所有API端点都无法访问比赛 {match_id}")
        return None

    def _structure_match_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        结构化原始比赛数据

        Args:
            raw_data: FotMob API 返回的原始数据

        Returns:
            结构化的比赛数据
        """
        # 提取基础数据
        match_info = self._extract_match_info(raw_data)
        shots = self._extract_shot_data(raw_data)

        # 计算真实的xG数据（基于FotMob射门图）
        xg_data = self._calculate_team_xg(shots, match_info)

        # 提取统计数据并合并xG
        base_stats_list = self._extract_match_stats(raw_data)
        # 将基础统计数据转换为字典格式，然后与xG数据合并
        stats_dict = {}
        for stat in base_stats_list if isinstance(base_stats_list, list) else []:
            if isinstance(stat, dict):
                stats_dict.update(stat)

        enhanced_stats = {**stats_dict, **xg_data}

        # 全量收割 - 提取所有高价值数据
        structured = {
            "matchId": self._extract_match_id(raw_data),
            "match_info": match_info,
            "lineup": self._extract_enhanced_lineup_data(raw_data),  # 增强阵容 - 包含评分
            "shots": shots,
            "stats": enhanced_stats,  # 包含真实xG数据
            "odds": self._extract_odds_data(raw_data),  # 赔率数据 (新增)
            "match_metadata": self._extract_match_metadata(raw_data),  # 比赛元数据 (新增)
            "events": self._extract_match_events(raw_data),  # 详细事件流 (新增)
            "fetched_at": datetime.utcnow().isoformat()
        }

        return structured

    def _extract_match_id(self, data: dict[str, Any]) -> str:
        """提取比赛 ID"""
        try:
            return data.get("match", {}).get("matchId", "")
        except Exception:
            return ""

    def _extract_match_info(self, data: dict[str, Any]) -> dict[str, Any]:
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

    def _extract_lineup_data(self, data: dict[str, Any]) -> dict[str, Any]:
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

    def _process_team_lineup(self, team_lineup: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """处理单个球队的阵容数据"""
        return {
            "starters": self._process_players(team_lineup.get("starters", [])),
            "substitutes": self._process_players(team_lineup.get("substitutes", []))
        }

    def _process_players(self, players: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def _extract_shot_data(self, data: dict[str, Any]) -> list[dict[str, Any]]:
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

    def _calculate_team_xg(self, shots: list[dict[str, Any]], match_info: dict[str, Any]) -> dict[str, Any]:
        """
        基于FotMob射门图计算真实的xG数据

        Args:
            shots: 射门数据列表
            match_info: 比赛基础信息（包含主客队信息）

        Returns:
            包含xg_home和xg_away的字典
        """
        try:
            home_team = match_info.get("home_team", "")
            away_team = match_info.get("away_team", "")

            xg_home = 0.0
            xg_away = 0.0

            # 统计每支球队的xG总和
            for shot in shots:
                xg_value = float(shot.get("xg", 0.0))
                shot_team = shot.get("team", "")

                # 通过队名判断是主队还是客队的射门
                if shot_team == home_team:
                    xg_home += xg_value
                elif shot_team == away_team:
                    xg_away += xg_value
                else:
                    # 如果队名不匹配，记录警告并跳过
                    self.logger.warning(f"Shot team '{shot_team}' doesn't match home/away teams ({home_team} vs {away_team})")
                    continue

            # 格式化xG值（保留2位小数）
            xg_data = {
                "xg_home": round(xg_home, 2),
                "xg_away": round(xg_away, 2)
            }

            self.logger.info(f"Calculated xG: Home {xg_home:.2f}, Away {xg_away:.2f} from {len(shots)} shots")
            return xg_data

        except Exception as e:
            self.logger.error(f"Error calculating xG from shotmap: {str(e)}")
            # 如果计算失败，返回空值而不是假数据
            return {"xg_home": None, "xg_away": None}

    def _extract_match_stats(self, data: dict[str, Any]) -> list[dict[str, Any]]:
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
    def headers(self) -> dict[str, str]:
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

    # ==================== 全量收割数据提取方法 ====================

    def _extract_enhanced_lineup_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        增强的阵容数据提取 - 包含球员评分和详细统计
        Returns:
            {
                "home": {
                    "starters": [增强球员列表],
                    "substitutes": [增强替补列表]
                },
                "away": {
                    "starters": [增强球员列表],
                    "substitutes": [增强替补列表]
                }
            }
        """
        try:
            lineup_content = data.get("content", {}).get("lineup", {})
            lineup_stats = data.get("content", {}).get("stats", {})

            lineup_data = {
                "home": self._process_enhanced_team_lineup(
                    lineup_content.get("home", {}),
                    lineup_stats.get("home", [])
                ),
                "away": self._process_enhanced_team_lineup(
                    lineup_content.get("away", {}),
                    lineup_stats.get("away", [])
                )
            }
            return lineup_data
        except Exception as e:
            self.logger.error(f"Error extracting enhanced lineup data: {str(e)}")
            return {"home": {"starters": [], "substitutes": []}, "away": {"starters": [], "substitutes": []}}

    def _process_enhanced_team_lineup(self, team_lineup: dict[str, Any], team_stats: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """处理增强的单个球队阵容数据"""
        processed = {
            "starters": self._process_enhanced_players(team_lineup.get("starters", []), team_stats),
            "substitutes": self._process_enhanced_players(team_lineup.get("substitutes", []), team_stats)
        }
        return processed

    def _process_enhanced_players(self, players: list[dict[str, Any]], team_stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """处理增强的球员数据，提取评分和详细统计"""
        processed_players = []

        # 创建统计数据的快速查找字典
        stats_dict = {}
        for stat in team_stats:
            if stat.get("statsType") == "player" and "playerStats" in stat:
                for player_stat in stat["playerStats"]:
                    player_id = player_stat.get("playerId")
                    if player_id:
                        stats_dict[player_id] = player_stat.get("stats", {})

        for player in players:
            try:
                player_id = player.get("id")

                # 从统计数据中获取详细信息
                player_stats = stats_dict.get(player_id, {})

                enhanced_player = {
                    "id": player_id,
                    "name": player.get("name", ""),
                    "position": player.get("position", {}).get("name", ""),
                    "shirt_number": player.get("shirtNo", player.get("shirtNumber")),
                    "is_starter": True,  # 这个参数需要根据调用上下文调整

                    # 全量收割关键字段
                    "rating": player_stats.get("rating"),  # 球员评分 (关键)
                    "minutes_played": player_stats.get("minutesPlayed"),  # 出场时间
                    "goals": player_stats.get("goals"),  # 进球数
                    "assists": player_stats.get("assists"),  # 助攻数
                    "shots": player_stats.get("shotsTotal"),  # 射门数
                    "shots_on_target": player_stats.get("shotsOnTarget"),  # 射正数
                    "yellow_cards": player_stats.get("yellowCards"),  # 黄牌
                    "red_cards": player_stats.get("redCards"),  # 红牌
                    "fouls": player_stats.get("fouls"),  # 犯规
                    "fouled_against": player_stats.get("fouledAgainst"),  # 被犯规
                    "passes_completed": player_stats.get("passesCompleted"),  # 传球成功数
                    "passes_attempted": player_stats.get("passesAttempted"),  # 传球尝试数
                    "pass_accuracy": player_stats.get("passAccuracy"),  # 传球成功率
                    "duels_won": player_stats.get("duelsWon"),  # 对抗胜利数
                    "duels_lost": player_stats.get("duelsLost"),  # 对抗失败数
                    "aerials_won": player_stats.get("aerialsWon"),  # 空中对抗胜利数
                    "aerials_lost": player_stats.get("aerialsLost"),  # 空中对抗失败数
                }

                processed_players.append(enhanced_player)
            except Exception as e:
                self.logger.warning(f"Error processing enhanced player data: {str(e)}")
                continue

        return processed_players

    def _extract_odds_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        提取赔率数据 - 1x2、大小球、让球盘等
        """
        try:
            odds_content = data.get("content", {}).get("matchFacts", {}).get("odds", {})
            if not odds_content:
                return {}

            # 提取主要赔率
            primary_odds = odds_content.get("primary", {})
            all_odds = odds_content.get("all", [])

            extracted_odds = {
                "home_win": primary_odds.get("homeWin"),
                "draw": primary_odds.get("draw"),
                "away_win": primary_odds.get("awayWin"),
                "over_25": primary_odds.get("over25"),
                "under_25": primary_odds.get("under25"),
                "both_teams_score": primary_odds.get("bothTeamsToScore"),
            }

            # 提取所有博彩公司的赔率
            providers = {}
            for provider in all_odds:
                provider_name = provider.get("provider", {}).get("name")
                if provider_name:
                    providers[provider_name] = {
                        "home_win": provider.get("homeWin"),
                        "draw": provider.get("draw"),
                        "away_win": provider.get("awayWin"),
                        "over_25": provider.get("over25"),
                        "under_25": provider.get("under25"),
                    }

            if providers:
                extracted_odds["providers"] = providers

            return extracted_odds
        except Exception as e:
            self.logger.error(f"Error extracting odds data: {str(e)}")
            return {}

    def _extract_match_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        提取比赛元数据 - 裁判、球场、观众等
        """
        try:
            match_facts = data.get("content", {}).get("matchFacts", {})
            general = match_facts.get("general", {})

            metadata = {
                "referee": general.get("referee", {}).get("name"),  # 裁判姓名 (关键)
                "stadium": general.get("stadium", {}).get("name"),  # 球场名称
                "attendance": general.get("attendance"),  # 观众人数
                "city": general.get("city"),
                "country": general.get("country"),
                "match_day": general.get("matchDay"),
                "round": general.get("round"),
                "competition_stage": general.get("stage"),
            }

            return metadata
        except Exception as e:
            self.logger.error(f"Error extracting match metadata: {str(e)}")
            return {}

    def _extract_match_events(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        提取详细比赛事件流 - 进球、卡牌、换人等
        """
        try:
            events_content = data.get("content", {}).get("lineup", {})
            home_events = events_content.get("home", {}).get("events", [])
            away_events = events_content.get("away", {}).get("events", [])

            all_events = []

            # 处理主队事件
            for event in home_events:
                processed_event = self._process_match_event(event, "home")
                if processed_event:
                    all_events.append(processed_event)

            # 处理客队事件
            for event in away_events:
                processed_event = self._process_match_event(event, "away")
                if processed_event:
                    all_events.append(processed_event)

            # 按时间排序
            all_events.sort(key=lambda x: x.get("minute", 0))

            return all_events
        except Exception as e:
            self.logger.error(f"Error extracting match events: {str(e)}")
            return []

    def _process_match_event(self, event: dict[str, Any], team_side: str) -> dict[str, Any]:
        """处理单个比赛事件"""
        try:
            processed_event = {
                "id": event.get("id"),
                "minute": event.get("minute"),
                "team_side": team_side,  # 标记是主队还是客队事件
                "player_name": event.get("player", {}).get("name"),
                "event_type": event.get("eventType"),
                "sub_type": event.get("subEventType"),
                "is_assist": event.get("isAssist", False),
                "assist_player_name": event.get("assistPlayer", {}).get("name"),
                "coordinate_x": event.get("coordinate", {}).get("x"),
                "coordinate_y": event.get("coordinate", {}).get("y"),
                "timestamp": event.get("timestamp"),
            }

            return processed_event
        except Exception as e:
            self.logger.warning(f"Error processing match event: {str(e)}")
            return {}


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
