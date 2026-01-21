#!/usr/bin/env python3
"""
V36.0 生产级 L1 采集器
======================
工业级数据采集架构，集成 Pydantic Schema 校验

核心改进:
1. Pydantic Schema 强制校验，防止元数据污染
2. 指数退避重试机制
3. 并发控制和速率限制
4. 结构化监控日志 (CollectionSummary)

作者: ML Architect
日期: 2025-12-28
Phase: Production-Grade Refactor
Version: V36.0
"""

import asyncio
import logging

import aiohttp

from src.api.collectors.resilience import (
    CircuitBreaker,
    ConcurrentLimiter,
    RateLimiter,
    retry_with_exponential_backoff,
)
from src.api.collectors.schemas.l1_match_schema import L1CollectionSummary, L1MatchData, LeagueId

logger = logging.getLogger(__name__)


class ProductionL1Collector:
    """
    V36.0 生产级 L1 采集器

    核心特性:
    - Pydantic Schema 强制校验
    - 指数退避重试
    - 并发控制和速率限制
    - 结构化监控日志
    """

    # FotMob API League ID 白名单（与 Schema 保持一致）
    VALID_LEAGUE_IDS = {47, 55, 54, 61, 135, 42}

    def __init__(
        self,
        max_concurrent: int = 5,
        max_requests_per_second: int = 2,
        timeout: int = 30,
        retry_max_attempts: int = 3,
    ):
        """
        初始化生产级采集器

        Args:
            max_concurrent: 最大并发数
            max_requests_per_second: 每秒最大请求数
            timeout: 请求超时时间
            retry_max_attempts: 最大重试次数
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        # 弹性机制
        self.rate_limiter = RateLimiter(max_requests=max_requests_per_second, time_window=1.0)
        self.concurrent_limiter = ConcurrentLimiter(max_concurrent=max_concurrent)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=aiohttp.ClientError,
        )

        # 采集摘要
        self.summary = L1CollectionSummary()

        # HTTP 会话
        self.session: aiohttp.ClientSession | None = None

        logger.info("🏭 V36.0 生产级 L1 采集器已初始化")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        self.session = aiohttp.ClientSession(
            timeout=timeout, connector=connector, headers=self._get_headers()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> dict[str, str]:
        """获取请求头（隐身模式）"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
        }

    @retry_with_exponential_backoff(
        max_attempts=3,
        base_delay=1.0,
        retry_on=(aiohttp.ClientError, asyncio.TimeoutError),
    )
    async def _fetch_league_matches(
        self,
        league_id: int,
        season_code: str,
    ) -> dict:
        """
        获取联赛比赛数据（带重试和熔断保护）

        Args:
            league_id: 联赛 ID
            season_code: 赛季代码

        Returns:
            API 响应 JSON

        Raises:
            aiohttp.ClientError: 网络错误
            asyncio.TimeoutError: 超时
        """
        # 检查熔断器
        if self.circuit_breaker.is_open():
            raise aiohttp.ClientError("🚨 熔断器已打开，暂停请求")

        # 速率限制
        await self.rate_limiter.acquire()

        # 构建请求 URL
        url = "https://www.fotmob.com/api/leagues"
        params = {"id": league_id, "season": season_code}

        async with self.concurrent_limiter:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    self.circuit_breaker.record_success()
                    return await response.json()
                if response.status == 404:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=404,
                        message=f"League {league_id} not found",
                    )
                if response.status >= 500:
                    # 服务器错误，记录失败并触发熔断器
                    self.circuit_breaker.record_failure(
                        aiohttp.ClientError(f"HTTP {response.status}")
                    )
                    raise aiohttp.ClientError(f"Server error: HTTP {response.status}")
                raise aiohttp.ClientError(f"Unexpected status: HTTP {response.status}")

    def _parse_and_validate_match(
        self,
        match_data: dict,
        league_id: str,
        season_code: str,
        season_name: str,
    ) -> L1MatchData | None:
        """
        解析并校验比赛数据（Pydantic 强制校验）

        这是防止元数据污染的核心方法

        Args:
            match_data: FotMob API 返回的比赛数据
            league_id: 联赛 ID
            season_code: 赛季代码 (e.g., "2324")
            season_name: 赛季名称

        Returns:
            L1MatchData 对象，如果校验失败返回 None
        """
        try:
            # 提取基础信息
            match_id = str(match_data.get("id"))
            if not match_id:
                return None

            # 提取球队信息
            home = match_data.get("home", {})
            away = match_data.get("away", {})

            # 提取状态
            status_obj = match_data.get("status", {})
            is_finished = status_obj.get("finished", False)
            is_started = status_obj.get("started", False)

            # 提取比分（在确定状态之前提取，用于智能修复）
            home_score = status_obj.get("homeScore")
            away_score = status_obj.get("awayScore")

            # V36.0 智能修复： FotMob API 有时返回 finished=True 但没有比分
            # 这种情况下，将状态降级为 scheduled，避免 Pydantic 校验失败
            if is_finished:
                if home_score is None or away_score is None:
                    # 数据不完整：finished 状态但没有比分
                    # 降级为 scheduled，等待后续采集补充
                    status = "scheduled"
                else:
                    status = "finished"
            elif is_started:
                status = "ongoing"
            else:
                status = "scheduled"

            # V36.0 关键防御：Pydantic Schema 校验
            # 这将自动进行：
            # 1. League ID 白名单校验
            # 2. League Name 与 ID 一致性校验
            # 3. 类型校验
            # 4. 业务逻辑校验（比分一致性等）
            return L1MatchData(
                match_id=match_id,
                league_id=league_id,
                league_name=LeagueId.get_league_name(league_id),  # 从 ID 获取标准名称
                season_id=season_code,
                season_name=season_name,
                home_team=home.get("name", "Unknown"),
                away_team=away.get("name", "Unknown"),
                home_team_id=int(home.get("id", 0)),
                away_team_id=int(away.get("id", 0)),
                status=status,
                match_time_utc=status_obj.get("utcTime", ""),
                home_score=home_score,
                away_score=away_score,
            )

        except ValueError as e:
            # Pydantic 校验失败，记录错误并拒绝数据
            logger.exception(f"❌ Pydantic 校验失败: {e}")
            logger.debug(f"   问题数据: {match_data}")
            return None
        except Exception as e:
            logger.exception(f"❌ 解析异常: {e}")
            return None

    async def collect_league_season(
        self,
        league_id: int,
        season_code: str,
        season_name: str,
    ) -> list[L1MatchData]:
        """
        采集指定联赛和赛季的所有比赛

        Args:
            league_id: 联赛 ID
            season_code: 赛季代码 (e.g., "2324")
            season_name: 赛季显示名称 (e.g., "23/24")

        Returns:
            通过 Pydantic 校验的比赛列表
        """
        # V36.0: 预检查 League ID 白名单
        if not LeagueId.is_valid_id(league_id):
            raise ValueError(
                f"❌ 非法 League ID: {league_id}。合法 IDs: {LeagueId.__members__.keys()}"
            )

        league_name = LeagueId.get_league_name(str(league_id))
        logger.info(f"🎯 开始采集: {league_name} - {season_name}")

        try:
            # 获取数据
            data = await self._fetch_league_matches(league_id, season_code)
        except Exception as e:
            # 记录失败
            self.summary.add_failure(str(league_id), type(e).__name__)
            logger.exception(f"❌ 采集失败: {league_name} - {season_name}: {e}")
            return []

        # 解析并校验比赛数据
        matches = []
        try:
            fixtures = data.get("fixtures", {})
            all_matches = fixtures.get("allMatches", [])

            for match_data in all_matches:
                validated = self._parse_and_validate_match(
                    match_data, str(league_id), season_code, season_name
                )
                if validated:
                    matches.append(validated)
                    self.summary.add_success(str(league_id))
                else:
                    self.summary.add_failure(str(league_id), "ValidationError")

        except Exception as e:
            logger.exception(f"❌ 解析数据失败: {e}")
            return []

        logger.info(f"✅ {league_name} - {season_name}: {len(matches)} 场通过校验")

        return matches

    def get_summary_report(self) -> str:
        """获取采集摘要报告"""
        self.summary.finalize()
        return self.summary.to_report()


# ============================================================================
# 使用示例
# ============================================================================


async def main():
    """生产级采集示例"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    async with ProductionL1Collector() as collector:
        # 采集多个联赛
        leagues = [
            {"id": 47, "season": "2324", "name": "23/24"},  # Premier League
            {"id": 55, "season": "2324", "name": "23/24"},  # La Liga
            {"id": 54, "season": "2324", "name": "23/24"},  # Bundesliga
            {"id": 61, "season": "2324", "name": "23/24"},  # Ligue 1
            {"id": 135, "season": "2324", "name": "23/24"},  # Serie A
        ]

        all_matches = []
        for league in leagues:
            matches = await collector.collect_league_season(
                league_id=league["id"],
                season_code=league["season"],
                season_name=league["name"],
            )
            all_matches.extend(matches)

        # 输出摘要报告

        logger.info(f"✅ 总计采集 {len(all_matches)} 场比赛")


if __name__ == "__main__":
    asyncio.run(main())
