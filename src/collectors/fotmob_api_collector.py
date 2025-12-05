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
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
    """比赛详情数据结构"""
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
            enable_jitter=enable_jitter
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
            limits = httpx.Limits(max_connections=self.max_concurrent, max_keepalive_connections=20)

            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers=self._get_default_headers()
            )

            logger.info("✅ FotMob API采集器初始化完成")

    def _get_default_headers(self) -> dict[str, str]:
        """获取默认请求头"""
        return {
            'User-Agent': self.ua_manager.get_current_ua(),
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
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
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException, httpx.NetworkError))
    )
    async def _make_request(self, url: str, match_id: str) -> tuple[Optional[dict], APIResponseStatus]:
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
                headers['User-Agent'] = self.ua_manager.switch_ua()
                self.stats["ua_switches"] += 1

            # 发起请求
            response = await self._client.get(
                url,
                headers=headers,
                proxy=proxy,
                follow_redirects=True
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

    def _parse_match_data(self, fotmob_id: str, data: dict[str, Any]) -> MatchDetailData:
        """解析API返回的JSON数据"""
        # 解析通用信息
        general = data.get("general", {})
        content = data.get("content", {})

        # 解析基本信息
        match_data = MatchDetailData(
            fotmob_id=fotmob_id,
            home_score=general.get("homeTeam", {}).get("score", 0),
            away_score=general.get("awayTeam", {}).get("score", 0),
            status="finished" if general.get("status", {}).get("finished", False) else "",
            match_time=general.get("statusStr"),
            venue=general.get("venue", {}).get("name"),
            attendance=general.get("attendance"),
            referee=general.get("referee", {}).get("name"),
            weather=general.get("weather", {}).get("condition"),
            home_yellow_cards=content.get("stats", {}).get("cards", {}).get("homeTeam", {}).get("yellowCards", 0),
            away_yellow_cards=content.get("stats", {}).get("cards", {}).get("awayTeam", {}).get("yellowCards", 0),
            home_red_cards=content.get("stats", {}).get("cards", {}).get("homeTeam", {}).get("redCards", 0),
            away_red_cards=content.get("stats", {}).get("cards", {}).get("awayTeam", {}).get("redCards", 0),
            home_team_rating=general.get("homeTeam", {}).get("rating", 0.0),
            away_team_rating=general.get("awayTeam", {}).get("rating", 0.0),
        )

        # 解析xG数据
        xg_data = content.get("stats", {}).get("xg", {})
        if xg_data:
            match_data.xg_home = xg_data.get("home", 0.0)
            match_data.xg_away = xg_data.get("away", 0.0)

        # 解析球员评分
        ratings = content.get("stats", {}).get("playerRating", {})
        if ratings:
            home_ratings = [r.get("rating", 0.0) for r in ratings.get("homeTeam", []) if r.get("rating")]
            away_ratings = [r.get("rating", 0.0) for r in ratings.get("awayTeam", []) if r.get("rating")]

            if home_ratings:
                match_data.home_avg_player_rating = sum(home_ratings) / len(home_ratings)
            if away_ratings:
                match_data.away_avg_player_rating = sum(away_ratings) / len(away_ratings)

        # 解析big chances
        stats = content.get("stats", {})
        shots_stats = stats.get("shots", {})
        if shots_stats:
            match_data.home_big_chances = shots_stats.get("homeTeam", {}).get("bigChances", 0)
            match_data.away_big_chances = shots_stats.get("awayTeam", {}).get("bigChances", 0)

        # 解析结构化数据
        match_data.lineups = self._extract_lineups(content)
        match_data.stats = self._extract_stats(content)
        match_data.events = self._extract_events(content)
        match_data.match_metadata = self._extract_metadata(data)

        return match_data

    def _extract_lineups(self, content: dict[str, Any]) -> Optional[dict[str, Any]]:
        """提取阵容数据"""
        try:
            lineups = content.get("lineup", {})
            return {
                "home_team": lineups.get("homeTeam"),
                "away_team": lineups.get("awayTeam"),
                "formation": {
                    "home": lineups.get("homeTeam", {}).get("formation"),
                    "away": lineups.get("awayTeam", {}).get("formation")
                }
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

    def _extract_events(self, content: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
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
                "processing_status": "completed"
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
        logger.info(f"📊 批量采集完成: {len(results)}/{len(fotmob_ids)} ({success_rate:.1f}%)")

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
