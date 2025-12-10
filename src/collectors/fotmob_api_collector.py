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
from typing import Optional, , Any, , 
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

        # 🔧 修复: 使用正确的 RateLimiter 构造参数
        # 创建速率限制配置 - 根据并发数设置合理的速率
        rate_config = {
            "fotmob.com": {
                "rate": float(max_concurrent),  # 每秒请求数
                "burst": max_concurrent * 2,    # 突发容量
                "max_wait_time": 30.0           # 最大等待时间
            },
            "default": {
                "rate": 1.0,
                "burst": 1,
                "max_wait_time": 30.0
            }
        }

        self.rate_limiter = RateLimiter(config=rate_config)
        self.proxy_pool = ProxyPool(provider='default') if enable_proxy else None

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

            # 配置代理（如果启用）
            # 注意：暂时禁用代理以避免异步调用问题
            # if self.proxy_pool:
            #     proxy = await self.proxy_pool.get_proxy()
            #     if proxy:
            #         proxies = {
            #             "http://": proxy,
            #             "https://": proxy,
            #         }

            # 完全禁用httpx的自动压缩处理
            headers_for_init = self._get_default_headers()
            # 不设置Accept-Encoding，让httpx自动处理

            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers=headers_for_init,
                follow_redirects=True
            )

            logger.info("✅ FotMob API采集器初始化完成")

    def _get_default_headers(self) -> dict[str, str]:
        """获取默认请求头"""
        import os

        headers = {
            "User-Agent": self.ua_manager.get_random_user_agent(),
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

        # 🔐 添加FotMob API认证头
        x_mas_token = os.getenv("FOTMOB_X_MAS_TOKEN")
        x_foo_token = os.getenv("FOTMOB_X_FOO_TOKEN")

        if x_mas_token:
            headers["x-mas"] = x_mas_token
        if x_foo_token:
            headers["x-foo"] = x_foo_token

        return headers

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
        # 🔧 修复: 新的 RateLimiter 需要指定域名参数
        async with self.rate_limiter.acquire("fotmob.com"):
            try:
                # 构建请求头
                headers = self._get_default_headers()
                if random.random() < 0.1:  # 10%概率切换UA
                    headers["User-Agent"] = self.ua_manager.get_random_user_agent()
                    self.stats["ua_switches"] += 1

                # 发起请求（代理已在客户端初始化时配置）
                response = await self._client.get(
                    url, headers=headers, follow_redirects=True
                )

                self.stats["requests_made"] += 1
                self.stats["total_data_size"] += len(response.content)

                if response.status_code == 200:
                    try:
                        logger.info(f"🔍 正在解析JSON响应，状态码: {response.status_code}, 响应长度: {len(response.content)}")
                        logger.info(f"📋 响应头Content-Encoding: {response.headers.get('content-encoding', 'None')}")
                        logger.info(f"🔍 前10字节十六进制: {response.content[:10].hex()}")

                        # 🔧 让httpx自动处理解压缩，直接使用response.json()
                        try:
                            logger.info("🔧 使用httpx自动解压缩和JSON解析...")
                            data = response.json()
                            logger.info(f"✅ httpx自动JSON解析成功，数据类型: {typing.Type(data)}")
                        except Exception as httpx_error:
                            logger.warning(f"⚠️ httpx自动解析失败: {httpx_error}")
                            logger.info("🔧 尝试手动解析...")

                            # 手动检查是否真的是压缩数据
                            content_encoding = response.headers.get('content-encoding', '').lower()
                            if content_encoding == 'br':
                                # Brotli压缩数据
                                import brotli
                                logger.info("🔧 手动Brotli解压缩...")
                                decompressed_data = brotli.decompress(response.content).decode('utf-8')
                                data = json.loads(decompressed_data)
                                logger.info("✅ Brotli解压缩和JSON解析成功")
                            else:
                                # 尝试直接解析
                                raw_text = response.content.decode('utf-8')
                                data = json.loads(raw_text)
                                logger.info("✅ 直接UTF-8解析成功")

                        logger.info(f"✅ JSON解析成功，数据类型: {typing.Type(data)}")
                        self.stats["successful_requests"] += 1
                        return data, APIResponseStatus.SUCCESS
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ JSON解析失败: {match_id}, 错误: {e}")
                        logger.warning(f"📄 响应内容前100字符: {response.text[:100]}")
                        self.stats["failed_requests"] += 1
                        return None, APIResponseStatus.SERVER_ERROR
                    except Exception as e:
                        logger.warning(f"⚠️ 解析时发生未知错误: {match_id}, 错误类型: {typing.Type(e).__name__}, 信息: {e}")
                        self.stats["failed_requests"] += 1
                        return None, APIResponseStatus.SERVER_ERROR

                elif response.status_code == 429:
                    logger.warning(f"🚫 请求被限制: {match_id}")
                    self.stats["rate_limited"] += 1
                    # 🔧 修复: 新的 RateLimiter 没有 increase_delay 方法
                    # RateLimiter 会自动处理令牌限制，无需手动调整
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

            # 基础信息解析（使用正确的API数据路径）
            # 从header.teams获取主客队信息和比分
            teams = header.get("teams", [])
            home_team_info = teams[0] if len(teams) > 0 else {}
            away_team_info = teams[1] if len(teams) > 1 else {}

            # 从header.status获取比赛状态
            status_info = header.get("status", {})

            match_data = MatchDetailData(
                fotmob_id=fotmob_id,
                # 比分从header.teams获取
                home_score=home_team_info.get("score", 0),
                away_score=away_team_info.get("score", 0),
                # 状态从header.status获取
                status=status_info.get("reason", {}).get("short", "scheduled"),
                # 🔧 修复: 直接使用正确的字段路径
                match_time=general.get("matchTimeUTCDate"),  # 直接从general获取
                venue=general.get("venue", {}).get("name"),
                attendance=general.get("attendance"),
                referee=general.get("referee", {}).get("name"),
                weather=general.get("weather", {}).get("condition"),
            )

            # 🔧 修复2: 立即处理主客队信息，确保基础映射正确
            # 从header.teams中提取主客队信息（优先使用header数据）
            header_teams = header.get("teams", [])
            if len(header_teams) >= 2:
                header_home_team = header_teams[0]
                header_away_team = header_teams[1]

                # 立即提取主客队基础信息用于debug
                home_team_name = header_home_team.get("name")
                away_team_name = header_away_team.get("name")
                home_team_id = header_home_team.get("id")
                away_team_id = header_away_team.get("id")

                logger.info(f"🔍 Header提取主客队: 主队={home_team_name}({home_team_id}), 客队={away_team_name}({away_team_id})")
            else:
                # 如果header中没有，从general中提取作为fallback
                home_team_name = general.get("homeTeam", {}).get("name")
                away_team_name = general.get("awayTeam", {}).get("name")
                home_team_id = general.get("homeTeam", {}).get("id")
                away_team_id = general.get("awayTeam", {}).get("id")

                logger.info(f"🔍 General提取主客队: 主队={home_team_name}({home_team_id}), 客队={away_team_name}({away_team_id})")

            # 🎯 维度1: 全量技术统计 (Black Box Approach)
            match_data.stats_json = self._extract_full_match_stats(content)

            # 🎯 维度2: 阵容与体能快照 (包含评分和伤停)
            match_data.lineups_json = self._extract_full_lineups(content)

            # 🎯 维度3: 战意上下文 (排名、轮次) - 传入提取的主客队信息
            match_data.match_info = self._extract_motivation_context(general, content, home_team_name, away_team_name, home_team_id, away_team_id)

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
        🎯 维度1: 全量技术统计提取 (修复版 - 正确处理列表结构)
        从 content.stats.Periods.All.stats 中提取实际统计数据

        API真实结构: content.stats.Periods.All.stats = [
            {"key": "expected_goals", "stats": [{"key": "xg", "stats": [2.21, 1.85]}]},
            {"key": "ball_possession_shared", "stats": [{"key": "possession", "stats": [58, 42]}]}
        ]
        """
        try:
            # 获取统计数据结构
            stats = content.get("stats", {})
            periods = stats.get("Periods", {})
            all_stats = periods.get("All", {})
            stats_data = all_stats.get("stats", [])

            logger.debug(f"🔍 stats_data 类型: {typing.Type(stats_data)}")
            if isinstance(stats_data, list) and len(stats_data) > 0:
                logger.debug(f"🔍 stats_data 第一项结构: {stats_data[0] if stats_data else 'Empty'}")

            # 🔥 核心修复: 确认 stats_data 是列表，直接遍历
            if not isinstance(stats_data, list):
                logger.warning(f"⚠️ stats_data 不是列表: {typing.Type(stats_data)}, 尝试兼容处理")
                # 如果是字典，尝试获取其values
                if isinstance(stats_data, dict):
                    stats_data = list(stats_data.values())
                else:
                    stats_data = []

            # 构建统计数据字典
            match_stats = {
                "possession": {},
                "shots": {},
                "passes": {},
                "dribbles": {},
                "aerial_duels": {},
                "tackles": {},
                "cards": {},
                "offsides": {},
                "corners": {},
                "free_kicks": {},
                "player_rating": {},
                "xg": {},
                "big_chances": {},
                "expected_assists": {},
                "post_shot_xg": {},
            }

            # 🔥 核心修复: 直接遍历列表，而不是假设其为字典
            for stat_category in stats_data:
                if not isinstance(stat_category, dict):
                    continue

                category_key = stat_category.get("key", "")
                category_stats = stat_category.get("stats", [])

                logger.debug(f"🔍 处理类别: {category_key}, 子项数: {len(category_stats) if isinstance(category_stats, list) else 0}")

                # 根据类别key映射到我们的统计类别
                target_category = self._map_stat_category(category_key)

                # 处理每个统计项
                if isinstance(category_stats, list):
                    for stat_item in category_stats:
                        if isinstance(stat_item, dict):
                            stat_key = stat_item.get("key", "")
                            stat_values = stat_item.get("stats", [])

                            # 提取主客队数值
                            if len(stat_values) >= 2:
                                home_value = stat_values[0]
                                away_value = stat_values[1]

                                # 存储到对应的类别
                                if target_category in match_stats:
                                    match_stats[target_category][stat_key] = [home_value, away_value]

                                    # 🔍 特殊记录xG数据，用于向后兼容
                                    if target_category == "xg":
                                        logger.info(f"✅ 找到xG数据: {stat_key} = 主队{home_value}, 客队{away_value}")

            logger.debug(f"📊 全量技术统计提取成功，字段数: {len(match_stats)}")

            # 🔍 调试信息：显示提取到的关键数据
            if match_stats.get("xg"):
                logger.info(f"🎯 xG数据提取: {match_stats['xg']}")
            if match_stats.get("possession"):
                logger.info(f"🎯 控球率数据提取: {match_stats['possession']}")

            return match_stats

        except Exception as e:
            logger.warning(f"⚠️ 全量技术统计提取失败: {e}")
            import traceback
            logger.debug(f"🔍 详细错误信息: {traceback.format_exc()}")
            return {}

    def _map_stat_category(self, category_key: str) -> str:
        """
        🔧 统计类别映射函数
        将API返回的category_key映射到我们的统计类别
        """
        # 🔥 关键映射关系 (基于真实API结构)
        category_mapping = {
            # xG相关
            "expected_goals": "xg",
            "expected_goals_on_target": "post_shot_xg",
            "xg": "xg",
            "xgot": "post_shot_xg",

            # 控球率
            "ball_possession_shared": "possession",
            "possession": "possession",
            "BallPossession": "possession",

            # 射门
            "total_shots": "shots",
            "shots": "shots",
            "shots_on_target": "shots",

            # 传球
            "total_passes": "passes",
            "passes": "passes",
            "accurate_passes": "passes",

            # 抢断
            "tackles": "tackles",
            "total_tackles": "tackles",

            # 角球
            "corners": "corners",
            "total_corners": "corners",

            # 球员评分
            "player_rating": "player_rating",
            "ratings": "player_rating",

            # 期望助攻
            "expected_assists": "expected_assists",
            "xa": "expected_assists",

            # 越位
            "offsides": "offsides",
            "total_offsides": "offsides",
        }

        # 先尝试精确匹配
        if category_key in category_mapping:
            return category_mapping[category_key]

        # 模糊匹配
        category_lower = category_key.lower()
        for pattern, target in category_mapping.items():
            if pattern.lower() in category_lower or category_lower in pattern.lower():
                return target

        # 默认归类到球员评分
        logger.debug(f"🔍 未知统计类别: {category_key}, 归类到player_rating")
        return "player_rating"

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

            logger.debug("👥 完整阵容提取成功")
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

    def _extract_motivation_context(self, general: dict[str, Any], content: dict[str, Any],
                                  home_team_name: str = None, away_team_name: str = None,
                                  home_team_id: str = None, away_team_id: str = None) -> dict[str, Any]:
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

            # 🔧 修复：优先使用传入的主客队信息，fallback到general
            motivation_context["home_team_name"] = home_team_name or general.get("homeTeam", {}).get("name")
            motivation_context["away_team_name"] = away_team_name or general.get("awayTeam", {}).get("name")
            motivation_context["home_team_id"] = home_team_id or general.get("homeTeam", {}).get("id")
            motivation_context["away_team_id"] = away_team_id or general.get("awayTeam", {}).get("id")

            # 🔍 调试日志：显示主客队信息提取情况
            logger.info(f"🎯 战意上下文主客队: 主队={motivation_context['home_team_name']}({motivation_context['home_team_id']}), 客队={motivation_context['away_team_name']}({motivation_context['away_team_id']})")

            logger.debug("🎯 战意上下文提取成功")
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
                logger.debug("💰 赔率快照提取成功")
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

            # 🔧 修复: 使用正确的JSON路径提取环境数据
            match_facts = content.get("matchFacts", {})
            info_box = match_facts.get("infoBox", {})

            # 🏛️ 裁判信息 (Referee) - 修复路径
            referee_data = info_box.get("Referee", {})
            environment_data["referee"] = {
                "id": referee_data.get("id"),
                "name": referee_data.get("text", referee_data.get("name")),  # 优先使用text字段
                "country": referee_data.get("country"),  # 国籍（用于分析执法风格）
                "cards_this_season": referee_data.get("cardsThisSeason", {}),  # 本季执法统计
            }

            # 🏟️ 场地信息 (Venue) - 修复路径
            venue_data = info_box.get("Stadium", {})
            environment_data["venue"] = {
                "id": venue_data.get("id"),
                "name": venue_data.get("name"),
                "city": venue_data.get("city"),
                "country": venue_data.get("country"),
                "capacity": venue_data.get("capacity"),  # 容量（用于计算上座率）
                "attendance": match_facts.get("attendance"),  # 实际观众人数
                "surface": venue_data.get("surface"),  # 草皮类型
                "coordinates": {
                    "lat": venue_data.get("lat"),
                    "lng": venue_data.get("lng")
                }
            }

            # 🎯 赔率数据 (Odds) - 新增提取
            poll_data = match_facts.get("poll", {})
            odds_data = poll_data.get("oddspoll", {})
            if odds_data:
                environment_data["odds"] = {
                    "poll_name": odds_data.get("PollName"),
                    "poll_title": odds_data.get("PollTitle"),
                    "facts": odds_data.get("Facts", [])
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
            general.get("status", {})
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
                "primary_formation": formation.get("typing.Type", "unknown"),  # 主阵型
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

            # 🔧 修复: xG数据从新的stats_json结构中提取（不再使用旧stats结构）
            if match_data.stats_json and "xg" in match_data.stats_json:
                xg_stats = match_data.stats_json["xg"]
                # 优先使用expected_goals，如果不存在则尝试其他xG相关字段
                if "expected_goals" in xg_stats:
                    xg_values = xg_stats["expected_goals"]
                    if isinstance(xg_values, list) and len(xg_values) >= 2:
                        match_data.xg_home = float(xg_values[0])
                        match_data.xg_away = float(xg_values[1])
                        logger.info(f"✅ xG数据赋值成功: 主队={match_data.xg_home}, 客队={match_data.xg_away}")
                    else:
                        logger.warning(f"⚠️ xG数据格式异常: {xg_values}")
                else:
                    # 尝试其他可能的xG字段
                    for xg_key in ["xg", "xgot", "post_shot_xg"]:
                        if xg_key in xg_stats:
                            xg_values = xg_stats[xg_key]
                            if isinstance(xg_values, list) and len(xg_values) >= 2:
                                match_data.xg_home = float(xg_values[0])
                                match_data.xg_away = float(xg_values[1])
                                logger.info(f"✅ 使用 {xg_key} 赋值xG数据: 主队={match_data.xg_home}, 客队={match_data.xg_away}")
                                break
            else:
                # 降级到旧的stats结构（向后兼容）
                xg_data = stats.get("xg", {})
                if xg_data:
                    match_data.xg_home = xg_data.get("home", 0.0)
                    match_data.xg_away = xg_data.get("away", 0.0)
                    logger.info(f"✅ 使用旧stats结构赋值xG数据: 主队={match_data.xg_home}, 客队={match_data.xg_away}")
                else:
                    logger.warning("⚠️ 未找到任何xG数据，保持默认值0.0")

            # 🔧 修复: referee数据从environment_json中提取
            if match_data.environment_json and "referee" in match_data.environment_json:
                referee_info = match_data.environment_json["referee"]
                match_data.referee = referee_info.get("name")
                if match_data.referee:
                    logger.info(f"✅ 裁判数据赋值成功: {match_data.referee}")
                else:
                    logger.warning("⚠️ 裁判数据为空")
            elif general.get("referee", {}).get("name"):
                # 降级到general结构
                match_data.referee = general.get("referee", {}).get("name")
                logger.info(f"✅ 使用general结构赋值裁判数据: {match_data.referee}")
            else:
                logger.warning("⚠️ 未找到任何裁判数据")

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
            # match_data.match_metadata = self._extract_metadata(data)  # 暂时注释，避免data未定义错误

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
                    "typing.Type": event.get("typing.Type"),
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

    def _extract_match_time_with_fallback(self, general: dict[str, Any], header: dict[str, Any]) -> Optional[datetime]:
        """
        🔧 修复3: 增强时间解析的容错性
        从多个字段提取比赛时间，支持TBD/Postponed比赛

        Args:
            general: API返回的general信息
            header: API返回的header信息

        Returns:
            datetime对象或None（如果时间未确定）
        """
        try:
            # 尝试从多个字段获取时间信息
            time_sources = [
                ("general.matchTimeUTCDate", general.get("matchTimeUTCDate")),
                ("general.matchTimeDate", general.get("matchTimeDate")),
                ("header.matchTimeUTCDate", header.get("matchTimeUTCDate")),
                ("general.startDate.date", general.get("startDate", {}).get("date")),
                ("general.startDate.time", general.get("startDate", {}).get("time")),
            ]

            # 记录所有找到的时间源
            found_times = []
            for source_name, time_value in time_sources:
                if time_value:
                    found_times.append((source_name, time_value))
                    logger.debug(f"🔍 找到时间源 {source_name}: {time_value}")

            # 尝试解析找到的第一个有效时间
            for source_name, time_value in found_times:
                try:
                    if isinstance(time_value, str):
                        # 尝试解析ISO格式时间
                        if 'T' in time_value or time_value.count('-') >= 2:
                            from datetime import datetime
                            # 处理不同的时间格式
                            if '+' in time_value:
                                # ISO 8601 with timezone
                                time_value = time_value.split('+')[0].strip()
                            if 'Z' in time_value:
                                # UTC时间
                                time_value = time_value.replace('Z', '').strip()

                            parsed_time = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                            logger.info(f"✅ 时间解析成功: {source_name} -> {parsed_time}")
                            return parsed_time.replace(tzinfo=None)  # 移除时区信息以匹配数据库

                except ValueError as e:
                    logger.warning(f"⚠️ 时间解析失败 {source_name}: {time_value} - {e}")
                    continue

            # 如果所有时间解析都失败，检查是否有TBD/Postponed状态
            status_info = header.get("status", {})
            status_text = status_info.get("reason", {}).get("short", "")
            status_long = status_info.get("reason", {}).get("long", "")

            if any(keyword in (status_text or "").lower() for keyword in ["tbd", "to be determined", "postponed", "cancelled"]):
                logger.info(f"⏰ 比赛时间未确定: {status_text} - {status_long}")
                return None

            # 如果没有时间但也没有明确的状态，记录警告
            logger.warning(f"⚠️ 无法解析比赛时间，状态: {status_text}")

            # 将时间信息存储在match_info中作为备注

            return None

        except Exception as e:
            logger.error(f"❌ 时间解析异常: {e}")
            return None

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
