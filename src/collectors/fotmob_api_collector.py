#!/usr/bin/env python3
"""
FotMob API 数据采集器 - L2 详情补全版本
FotMob API Data Collector - L2 Details Enhancement Version

使用 FotMob MatchDetails API 直接获取 JSON 数据，替代已失效的 HTML 解析方式
"""

import asyncio
import json
import logging
import random
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .user_agent import UserAgentManager
from .rate_limiter import RateLimiter
from .proxy_pool import ProxyPool

logger = logging.getLogger(__name__)


class APIResponseStatus(Enum):
    """API响应状态"""

    SUCCESS = "success"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"


@dataclass
class MatchDetailData:
    """比赛详情数据结构 - Greedy Mode 增强版"""

    fotmob_id: str
    home_score: int
    away_score: int
    status: str
    match_time: Optional[str] = None
    venue: Optional[str] = None
    attendance: Optional[int] = None
    referee: Optional[str] = None
    weather: Optional[str] = None
    home_yellow_cards: int = 0
    away_yellow_cards: int = 0
    home_red_cards: int = 0
    away_red_cards: int = 0
    home_team_rating: float = 0.0
    away_team_rating: float = 0.0
    home_avg_player_rating: float = 0.0
    away_avg_player_rating: float = 0.0
    home_big_chances: int = 0
    away_big_chances: int = 0
    xg_home: float = 0.0
    xg_away: float = 0.0
    lineups: Optional[dict[str, Any]] = None
    stats: Optional[dict[str, Any]] = None
    events: Optional[list[dict[str, Any]]] = None
    match_metadata: Optional[dict[str, Any]] = None

    # 🔥 Greedy Mode 新增字段
    stats_json: Optional[dict[str, Any]] = None  # 全量技术统计
    lineups_json: Optional[dict[str, Any]] = None  # 完整阵容数据
    odds_snapshot_json: Optional[dict[str, Any]] = None  # 赔率快照
    match_info: Optional[dict[str, Any]] = None  # 战意上下文

    # 🌟 Super Greedy Mode 新增字段 - 环境暗物质
    environment_json: Optional[dict[str, Any]] = None  # 裁判、场地、天气、主帅、阵型


class FotMobAPICollector:
    """FotMob API 数据采集器 - L2 详情补全版本"""

    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: int = 30,
        max_retries: int = 5,
        base_delay: float = 1.0,
        enable_proxy: bool = True,
        enable_jitter: bool = True,
    ):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.enable_proxy = enable_proxy
        self.enable_jitter = enable_jitter

        # 核心组件
        self.ua_manager = UserAgentManager()
        self.rate_limiter = RateLimiter(
            base_delay=base_delay,
            max_delay=base_delay * 10,
            enable_jitter=enable_jitter,
        )
        self.proxy_pool = ProxyPool() if enable_proxy else None

        # HTTP客户端
        self._client = None
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 统计信息
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited": 0,
            "matches_collected": 0,
            "ua_switches": 0,
            "proxy_switches": 0,
            "retry_count": 0,
            "total_data_size": 0,
        }

    async def initialize(self):
        """初始化HTTP客户端"""
        if self._client is None:
            timeout = httpx.Timeout(self.timeout)
            limits = httpx.Limits(
                max_connections=self.max_concurrent, max_keepalive_connections=20
            )

            self._client = httpx.AsyncClient(
                timeout=timeout, limits=limits, headers=self._get_default_headers()
            )

            logger.info("✅ FotMob API采集器初始化完成")

    def _get_default_headers(self) -> dict[str, str]:
        """获取默认请求头"""
        return {
            "User-Agent": self.ua_manager.get_current_ua(),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("🔒 API采集器已关闭")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=60),
        retry=retry_if_exception_type(
            (httpx.RequestError, httpx.TimeoutException, httpx.NetworkError)
        ),
    )
    async def _make_request(
        self, url: str, match_id: str
    ) -> tuple[Optional[dict], APIResponseStatus]:
        """发起API请求"""
        await self.rate_limiter.acquire()

        try:
            # 选择代理（如果启用）
            proxy = None
            if self.proxy_pool:
                proxy = self.proxy_pool.get_proxy()

            # 构建请求头
            headers = self._get_default_headers()
            if random.random() < 0.1:  # 10%概率切换UA
                headers["User-Agent"] = self.ua_manager.switch_ua()
                self.stats["ua_switches"] += 1

            # 发起请求
            response = await self._client.get(
                url, headers=headers, proxy=proxy, follow_redirects=True
            )

            self.stats["requests_made"] += 1
            self.stats["total_data_size"] += len(response.content)

            if response.status_code == 200:
                try:
                    data = response.json()
                    self.stats["successful_requests"] += 1
                    return data, APIResponseStatus.SUCCESS
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ JSON解析失败: {match_id}")
                    self.stats["failed_requests"] += 1
                    return None, APIResponseStatus.SERVER_ERROR

            elif response.status_code == 429:
                logger.warning(f"🚫 请求被限制: {match_id}")
                self.stats["rate_limited"] += 1
                # 增加延迟时间
                self.rate_limiter.increase_delay()
                return None, APIResponseStatus.RATE_LIMIT

            elif response.status_code == 404:
                logger.warning(f"❌ 资源不存在: {match_id}")
                self.stats["failed_requests"] += 1
                return None, APIResponseStatus.NOT_FOUND

            else:
                logger.warning(f"⚠️ HTTP错误 {response.status_code}: {match_id}")
                self.stats["failed_requests"] += 1
                return None, APIResponseStatus.SERVER_ERROR

        except httpx.TimeoutException:
            logger.warning(f"⏰ 请求超时: {match_id}")
            self.stats["failed_requests"] += 1
            return None, APIResponseStatus.NETWORK_ERROR

        except httpx.RequestError as e:
            logger.warning(f"🌐 网络错误 {match_id}: {e}")
            self.stats["failed_requests"] += 1
            return None, APIResponseStatus.NETWORK_ERROR

        except Exception as e:
            logger.error(f"❌ 未知错误 {match_id}: {e}")
            self.stats["failed_requests"] += 1
            return None, APIResponseStatus.NETWORK_ERROR

    async def collect_match_details(self, fotmob_id: str) -> Optional[MatchDetailData]:
        """采集单个比赛详情"""
        async with self._semaphore:
            url = f"https://www.fotmob.com/api/matchDetails?matchId={fotmob_id}"

            data, status = await self._make_request(url, fotmob_id)

            if status == APIResponseStatus.SUCCESS and data:
                try:
                    return self._parse_match_data(fotmob_id, data)
                except Exception as e:
                    logger.error(f"❌ 解析数据失败 {fotmob_id}: {e}")
                    return None
            else:
                logger.warning(f"⚠️ API请求失败 {fotmob_id}: {status.value}")
                return None

    def _parse_match_data(
        self, fotmob_id: str, data: dict[str, Any]
    ) -> MatchDetailData:
        """
        🔥 Greedy Mode 解析API返回的JSON数据 - 全量数据采集
        实现四大维度的完整提取：技术统计、阵容体能、战意上下文、赔率快照
        """
        try:
            # 解析主要数据结构
            general = data.get("general", {})
            content = data.get("content", {})
            header = data.get("header", {})

            # 基础信息解析（向后兼容）
            match_data = MatchDetailData(
                fotmob_id=fotmob_id,
                home_score=general.get("homeTeam", {}).get("score", 0),
                away_score=general.get("awayTeam", {}).get("score", 0),
                status=(
                    "finished" if general.get("status", {}).get("finished", False) else "scheduled"
                ),
                match_time=general.get("statusStr"),
                venue=general.get("venue", {}).get("name"),
                attendance=general.get("attendance"),
                referee=general.get("referee", {}).get("name"),
                weather=general.get("weather", {}).get("condition"),
            )

            # 🎯 维度1: 全量技术统计 (Black Box Approach)
            match_data.stats_json = self._extract_full_match_stats(content)

            # 🎯 维度2: 阵容与体能快照 (包含评分和伤停)
            match_data.lineups_json = self._extract_full_lineups(content)

            # 🎯 维度3: 战意上下文 (排名、轮次)
            match_data.match_info = self._extract_motivation_context(general, content)

            # 🎯 维度4: 赔率快照
            match_data.odds_snapshot_json = self._extract_odds_snapshot(data)

            # 🌟 维度5: 环境暗物质 (Super Greedy Mode)
            match_data.environment_json = self._extract_environment_data(data)

            # 🔥 向后兼容的字段提取（保持原有逻辑）
            self._extract_legacy_stats(match_data, content, general)

            logger.info(f"✅ Super Greedy Mode解析完成: {fotmob_id}")
            return match_data

        except Exception as e:
            logger.error(f"❌ Greedy Mode解析失败 {fotmob_id}: {e}")
            # 即使解析失败，也返回基础数据
            return self._parse_fallback_data(fotmob_id, data)

    def _extract_full_match_stats(self, content: dict[str, Any]) -> dict[str, Any]:
        """
        🎯 维度1: 全量技术统计提取 (Black Box Approach)
        完整保留 content.matchStats，不做拆解，保证数据完整性
        """
        try:
            # 获取完整的matchStats数据
            match_stats = content.get("matchStats", {})

            if not match_stats:
                # 如果matchStats为空，尝试从其他统计路径获取
                stats = content.get("stats", {})
                match_stats = {
                    "possession": stats.get("possession", {}),
                    "shots": stats.get("shots", {}),
                    "passes": stats.get("passes", {}),
                    "dribbles": stats.get("dribbles", {}),
                    "aerial_duels": stats.get("aerialDuels", {}),
                    "tackles": stats.get("tackles", {}),
                    "cards": stats.get("cards", {}),
                    "offsides": stats.get("offsides", {}),
                    "corners": stats.get("corners", {}),
                    "free_kicks": stats.get("freeKicks", {}),
                    "player_rating": stats.get("playerRating", {}),
                    "xg": stats.get("xg", {}),
                    "big_chances": stats.get("bigChances", {}),
                    "expected_assists": stats.get("expectedAssists", {}),
                    "post_shot_xg": stats.get("postShotXG", {}),
                }

            logger.debug(f"📊 全量技术统计提取成功，字段数: {len(match_stats)}")
            return match_stats

        except Exception as e:
            logger.warning(f"⚠️ 全量技术统计提取失败: {e}")
            return {}

    def _extract_full_lineups(self, content: dict[str, Any]) -> dict[str, Any]:
        """
        🎯 维度2: 完整阵容数据提取 (包含评分、伤停信息)
        重点关注：首发、替补、伤停名单，以及球员评分
        """
        try:
            lineup_data = content.get("lineup", {})

            # 构建完整的阵容信息
            full_lineups = {
                "home_team": self._extract_team_lineup(lineup_data.get("homeTeam", {}), "home"),
                "away_team": self._extract_team_lineup(lineup_data.get("awayTeam", {}), "away"),
                "formations": {
                    "home": lineup_data.get("homeTeam", {}).get("formation"),
                    "away": lineup_data.get("awayTeam", {}).get("formation"),
                },
                "team_colors": {
                    "home": lineup_data.get("homeTeam", {}).get("teamColors"),
                    "away": lineup_data.get("awayTeam", {}).get("teamColors"),
                }
            }

            # 检查是否有伤停名单（对战意分析至关重要）
            unavailable = content.get("unavailablePlayers", {})
            if unavailable:
                full_lineups["unavailable"] = {
                    "home_team": unavailable.get("homeTeam", []),
                    "away_team": unavailable.get("awayTeam", [])
                }

            logger.debug(f"👥 完整阵容提取成功")
            return full_lineups

        except Exception as e:
            logger.warning(f"⚠️ 完整阵容提取失败: {e}")
            return {}

    def _extract_team_lineup(self, team_lineup: dict[str, Any], side: str) -> dict[str, Any]:
        """提取单个队伍的完整阵容信息"""
        return {
            "starters": team_lineup.get("starters", []),
            "bench": team_lineup.get("bench", []),
            "substitutes": team_lineup.get("substitutes", []),
            "missing_players": team_lineup.get("missingPlayers", []),
            "manager": team_lineup.get("manager", {}),
            "captain": team_lineup.get("captain", {}),
        }

    def _extract_motivation_context(self, general: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        """
        🎯 维度3: 战意上下文提取 (排名、轮次)
        这些信息对预测模型中的战意分析至关重要
        """
        try:
            motivation_context = {}

            # 赛前排名信息
            league_table = general.get("leagueTable", {})
            if league_table:
                motivation_context["league_table"] = {
                    "home_team_position": league_table.get("homeTeamPosition"),
                    "away_team_position": league_table.get("awayTeamPosition"),
                    "home_team_points": league_table.get("homeTeamPoints"),
                    "away_team_points": league_table.get("awayTeamPoints"),
                    "home_team_gd": league_table.get("homeTeamGD"),
                    "away_team_gd": league_table.get("awayTeamGD"),
                }

            # 比赛轮次信息
            round_info = general.get("round", {})
            if not round_info:
                round_info = content.get("matchFacts", {}).get("round", {})

            if round_info:
                motivation_context["round_info"] = {
                    "round_name": round_info.get("roundName"),
                    "round_number": round_info.get("roundNumber"),
                    "stage": round_info.get("stage"),  # Group Stage, Knockout, etc.
                    "leg": round_info.get("leg"),      # First leg, Second leg
                }

            # 联赛和赛季信息
            motivation_context["league_context"] = {
                "league_id": general.get("leagueId"),
                "league_name": general.get("leagueName"),
                "season": general.get("season"),
                "tournament_stage": general.get("tournamentStage"),
            }

            # 比赛重要性标识
            motivation_context["match_importance"] = {
                "is_derby": general.get("isDerby", False),
                "is_final": general.get("isFinal", False),
                "is_semifinal": general.get("isSemiFinal", False),
                "is_quarterfinal": general.get("isQuarterFinal", False),
            }

            logger.debug(f"🎯 战意上下文提取成功")
            return motivation_context

        except Exception as e:
            logger.warning(f"⚠️ 战意上下文提取失败: {e}")
            return {}

    def _extract_odds_snapshot(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        🎯 维度4: 赔率快照提取
        捕获赛前赔率信息，对市场预期分析很重要
        """
        try:
            odds_data = {}

            # 从header中获取赔率信息
            header = data.get("header", {})
            if header.get("odds"):
                odds_data["header_odds"] = header.get("odds")

            # 从content中获取赔率信息
            content = data.get("content", {})
            if content.get("matchFacts", {}).get("odds"):
                odds_data["match_facts_odds"] = content.get("matchFacts", {}).get("odds")

            # 从通用信息中获取赔率
            general = data.get("general", {})
            if general.get("odds"):
                odds_data["general_odds"] = general.get("odds")

            # 记录赔率获取时间
            if odds_data:
                odds_data["snapshot_time"] = datetime.now().isoformat()
                logger.debug(f"💰 赔率快照提取成功")
            else:
                logger.debug("📊 未找到赔率数据")

            return odds_data

        except Exception as e:
            logger.warning(f"⚠️ 赔率快照提取失败: {e}")
            return {}

    def _extract_environment_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        🌟 维度5: 环境暗物质提取 (Super Greedy Mode)
        捕获裁判、场地、天气、主帅、阵型等环境因素
        """
        environment_data = {}

        try:
            general = data.get("general", {})
            content = data.get("content", {})

            # 🏛️ 裁判信息 (Referee)
            referee_data = general.get("referee", {})
            environment_data["referee"] = {
                "id": referee_data.get("id"),
                "name": referee_data.get("name"),
                "country": referee_data.get("country"),  # 国籍（用于分析执法风格）
                "cards_this_season": referee_data.get("cardsThisSeason", {}),  # 本季执法统计
            }

            # 🏟️ 场地信息 (Venue)
            venue_data = general.get("venue", {})
            environment_data["venue"] = {
                "id": venue_data.get("id"),
                "name": venue_data.get("name"),
                "city": venue_data.get("city"),
                "country": venue_data.get("country"),
                "capacity": venue_data.get("capacity"),  # 容量（用于计算上座率）
                "attendance": general.get("attendance"),  # 实际观众人数
                "surface": venue_data.get("surface"),  # 草皮类型
                "coordinates": {
                    "lat": venue_data.get("lat"),
                    "lng": venue_data.get("lng")
                }
            }

            # 🌤️ 天气信息 (Weather)
            weather_data = general.get("weather", {})
            environment_data["weather"] = {
                "temperature": weather_data.get("temp"),  # 温度
                "condition": weather_data.get("condition"),  # 天气状况
                "wind_speed": weather_data.get("wind"),  # 风速
                "humidity": weather_data.get("humidity"),  # 湿度
                "pitch_condition": weather_data.get("pitchCondition")  # 场地状况
            }

            # 👕 主帅信息 (Managers) - 从lineup中提取
            lineup_data = content.get("lineup", {})
            environment_data["managers"] = {
                "home_team": self._extract_team_manager(lineup_data.get("home", {})),
                "away_team": self._extract_team_manager(lineup_data.get("away", {}))
            }

            # 🎯 阵型信息 (Formations) - 从lineup中提取
            environment_data["formations"] = {
                "home_team": self._extract_team_formation(lineup_data.get("home", {})),
                "away_team": self._extract_team_formation(lineup_data.get("away", {}))
            }

            # 📅 比赛时间上下文
            match_time = general.get("status", {})
            environment_data["time_context"] = {
                "match_date": general.get("startDate", {}).get("date"),
                "match_time": general.get("startDate", {}).get("time"),
                "local_timezone": general.get("startDate", {}).get("timezone"),
                "is_weekend": self._check_if_weekend(general.get("startDate", {}).get("date")),
                "season_stage": self._determine_season_stage(general)  # 赛季阶段
            }

            # 💰 经济因素
            environment_data["economic_factors"] = {
                "ticket_price_range": venue_data.get("ticketPrice"),  # 票价区间
                "tv_broadcast": general.get("broadcast", {}),  # 转播信息
                "prize_money": self._extract_prize_money_context(general)  # 奖金背景
            }

            logger.debug(f"🌟 环境数据提取完成，包含 {len(environment_data)} 个维度")
            return environment_data

        except Exception as e:
            logger.warning(f"⚠️ 环境数据提取失败: {e}")
            return {}

    def _extract_team_manager(self, team_lineup: dict[str, Any]) -> dict[str, Any]:
        """提取队伍主帅信息"""
        try:
            manager_info = team_lineup.get("manager", {})
            return {
                "id": manager_info.get("id"),
                "name": manager_info.get("name"),
                "age": manager_info.get("age"),
                "nationality": manager_info.get("nationality"),
                "appointment_date": manager_info.get("appointmentDate"),  # 上任日期
                "contract_until": manager_info.get("contractUntil"),  # 合同到期日
                "previous_clubs": manager_info.get("previousClubs", []),  # 曾执教球队
                "playing_style": manager_info.get("style")  # 执教风格
            }
        except Exception as e:
            logger.debug(f"主帅信息提取失败: {e}")
            return {}

    def _extract_team_formation(self, team_lineup: dict[str, Any]) -> dict[str, Any]:
        """提取队伍阵型信息"""
        try:
            # 从首发阵容中推断阵型
            starters = team_lineup.get("starters", [])
            formation = team_lineup.get("formation", {})

            # 统计各位置球员数量
            position_count = {}
            for player in starters:
                position = player.get("position", "SUB")
                position_count[position] = position_count.get(position, 0) + 1

            return {
                "primary_formation": formation.get("type", "unknown"),  # 主阵型
                "position_distribution": position_count,  # 位置分布
                "total_starters": len(starters),  # 首发人数
                "formation_changes": formation.get("changes", []),  # 阵型变化
                "tactical_approach": formation.get("style")  # 战术风格
            }
        except Exception as e:
            logger.debug(f"阵型信息提取失败: {e}")
            return {}

    def _check_if_weekend(self, date_str: Optional[str]) -> bool:
        """检查比赛是否在周末进行"""
        if not date_str:
            return False
        try:
            from datetime import datetime
            # 简化的周末检查逻辑
            # 实际实现中应该使用更精确的日期解析
            return "Saturday" in date_str or "Sunday" in date_str or "周六" in date_str or "周日" in date_str
        except:
            return False

    def _determine_season_stage(self, general: dict[str, Any]) -> str:
        """判断赛季阶段"""
        try:
            # 这里可以根据联赛信息判断赛季阶段
            round_info = general.get("round", {})
            round_number = round_info.get("roundNumber", 0)
            total_rounds = round_info.get("totalRounds", 38)

            if round_number == 0:
                return "unknown"
            elif round_number <= total_rounds * 0.3:
                return "early"
            elif round_number <= total_rounds * 0.7:
                return "mid"
            else:
                return "late"
        except:
            return "unknown"

    def _extract_prize_money_context(self, general: dict[str, Any]) -> dict[str, Any]:
        """提取奖金背景信息"""
        try:
            # 不同级别的比赛有不同的奖金结构
            league_info = general.get("league", {})

            return {
                "competition_level": league_info.get("level", "unknown"),  # 比赛级别
                "has_champions league qualification": league_info.get("championsLeagueSpots", 0) > 0,
                "has_relegation_threat": league_info.get("relegationSpots", 0) > 0,
                "prize_pool": league_info.get("prizePool"),  # 奖金池
            }
        except:
            return {}

    def _extract_legacy_stats(self, match_data: MatchDetailData, content: dict[str, Any], general: dict[str, Any]):
        """
        🔥 向后兼容字段提取（保持原有逻辑）
        确保原有功能不受影响
        """
        try:
            # 解析基础统计信息（保持原有逻辑）
            stats = content.get("stats", {})

            # 牌照统计
            cards_data = stats.get("cards", {})
            match_data.home_yellow_cards = cards_data.get("homeTeam", {}).get("yellowCards", 0)
            match_data.away_yellow_cards = cards_data.get("awayTeam", {}).get("yellowCards", 0)
            match_data.home_red_cards = cards_data.get("homeTeam", {}).get("redCards", 0)
            match_data.away_red_cards = cards_data.get("awayTeam", {}).get("redCards", 0)

            # 团队评分
            match_data.home_team_rating = general.get("homeTeam", {}).get("rating", 0.0)
            match_data.away_team_rating = general.get("awayTeam", {}).get("rating", 0.0)

            # xG数据（兼容性）
            xg_data = stats.get("xg", {})
            if xg_data:
                match_data.xg_home = xg_data.get("home", 0.0)
                match_data.xg_away = xg_data.get("away", 0.0)

            # 球员评分（兼容性）
            ratings = stats.get("playerRating", {})
            if ratings:
                home_ratings = [
                    r.get("rating", 0.0)
                    for r in ratings.get("homeTeam", [])
                    if r.get("rating")
                ]
                away_ratings = [
                    r.get("rating", 0.0)
                    for r in ratings.get("awayTeam", [])
                    if r.get("rating")
                ]

                if home_ratings:
                    match_data.home_avg_player_rating = sum(home_ratings) / len(home_ratings)
                if away_ratings:
                    match_data.away_avg_player_rating = sum(away_ratings) / len(away_ratings)

            # Big chances（兼容性）
            shots_stats = stats.get("shots", {})
            if shots_stats:
                match_data.home_big_chances = shots_stats.get("homeTeam", {}).get("bigChances", 0)
                match_data.away_big_chances = shots_stats.get("awayTeam", {}).get("bigChances", 0)

            # 保持原有的结构化数据提取（用于向后兼容）
            match_data.lineups = self._extract_lineups(content)
            match_data.stats = self._extract_stats(content)
            match_data.events = self._extract_events(content)
            match_data.match_metadata = self._extract_metadata(data)

        except Exception as e:
            logger.warning(f"⚠️ 向后兼容字段提取失败: {e}")

    def _parse_fallback_data(self, fotmob_id: str, data: dict[str, Any]) -> MatchDetailData:
        """
        降级解析：当完整解析失败时的fallback
        """
        try:
            general = data.get("general", {})

            return MatchDetailData(
                fotmob_id=fotmob_id,
                home_score=general.get("homeTeam", {}).get("score", 0),
                away_score=general.get("awayTeam", {}).get("score", 0),
                status="scheduled",
                match_time=general.get("statusStr"),
                venue=general.get("venue", {}).get("name"),
                stats_json={},
                lineups_json={},
                odds_snapshot_json={},
                match_info={},
            )
        except Exception as e:
            logger.error(f"❌ 降级解析也失败 {fotmob_id}: {e}")
            return MatchDetailData(fotmob_id=fotmob_id)

    def _extract_lineups(self, content: dict[str, Any]) -> Optional[dict[str, Any]]:
        """提取阵容数据"""
        try:
            lineups = content.get("lineup", {})
            return {
                "home_team": lineups.get("homeTeam"),
                "away_team": lineups.get("awayTeam"),
                "formation": {
                    "home": lineups.get("homeTeam", {}).get("formation"),
                    "away": lineups.get("awayTeam", {}).get("formation"),
                },
            }
        except Exception as e:
            logger.warning(f"⚠️ 阵容数据提取失败: {e}")
            return None

    def _extract_stats(self, content: dict[str, Any]) -> Optional[dict[str, Any]]:
        """提取技术统计数据"""
        try:
            stats = content.get("stats", {})
            return {
                "possession": stats.get("possession", {}),
                "shots": stats.get("shots", {}),
                "passes": stats.get("passes", {}),
                "dribbles": stats.get("dribbles", {}),
                "aerial_duels": stats.get("aerialDuels", {}),
                "tackles": stats.get("tackles", {}),
                "cards": stats.get("cards", {}),
                "offsides": stats.get("offsides", {}),
                "corners": stats.get("corners", {}),
                "free_kicks": stats.get("freeKicks", {}),
                "player_rating": stats.get("playerRating", {}),
                "xg": stats.get("xg", {}),
                "big_chances": stats.get("bigChances", {}),
            }
        except Exception as e:
            logger.warning(f"⚠️ 统计数据提取失败: {e}")
            return None

    def _extract_events(
        self, content: dict[str, Any]
    ) -> Optional[list[dict[str, Any]]]:
        """提取比赛事件数据"""
        try:
            events = content.get("timeline", {}).get("event", [])
            return [
                {
                    "id": event.get("id"),
                    "type": event.get("type"),
                    "player": event.get("player", {}),
                    "team": event.get("team"),
                    "minute": event.get("minute"),
                    "added_time": event.get("addedTime"),
                    "is_home": event.get("isHome", False),
                    "text": event.get("text"),
                    "card_type": event.get("cardType"),
                    "player_assist": event.get("playerAssist", {}),
                }
                for event in events
            ]
        except Exception as e:
            logger.warning(f"⚠️ 事件数据提取失败: {e}")
            return None

    def _extract_metadata(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """提取元数据"""
        try:
            return {
                "api_version": "v2",
                "collection_time": datetime.now().isoformat(),
                "raw_response_size": len(str(data)),
                "data_source": "fotmob_api_v2",
                "processing_status": "completed",
            }
        except Exception as e:
            logger.warning(f"⚠️ 元数据提取失败: {e}")
            return None

    async def collect_batch(self, fotmob_ids: list[str]) -> list[MatchDetailData]:
        """批量采集比赛详情"""
        results = []

        logger.info(f"🚀 开始批量采集 {len(fotmob_ids)} 场比赛详情")

        tasks = [self.collect_match_details(fotmob_id) for fotmob_id in fotmob_ids]

        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                if result:
                    results.append(result)
                    self.stats["matches_collected"] += 1
                    logger.info(f"✅ 成功采集: {result.fotmob_id}")
                else:
                    logger.warning("❌ 采集失败")
            except Exception as e:
                logger.error(f"❌ 批量采集异常: {e}")

        success_rate = len(results) / len(fotmob_ids) * 100 if fotmob_ids else 0
        logger.info(
            f"📊 批量采集完成: {len(results)}/{len(fotmob_ids)} ({success_rate:.1f}%)"
        )

        return results

    def get_stats(self) -> dict[str, Any]:
        """获取采集统计信息"""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited": 0,
            "matches_collected": 0,
            "ua_switches": 0,
            "proxy_switches": 0,
            "retry_count": 0,
            "total_data_size": 0,
        }
