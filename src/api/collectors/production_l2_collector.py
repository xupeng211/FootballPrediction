#!/usr/bin/env python3
"""
V37.0 工业级 L2 详情采集器
=========================
生产级弹性架构 + Pydantic 校验 + 批量写入

核心改进:
1. 共享 L1 的弹性机制（重试、熔断、限流）
2. L2MatchDetailSchema Pydantic 校验
3. 批量 Upsert（每 50 场一次提交）
4. ID 格式修正：使用纯数字 match_id（与 L1 一致）
5. 独立的 asyncio.Semaphore 并发控制

作者: ML Architect
日期: 2025-12-29
Phase: Production-Grade Refactor
Version: V37.0
"""

import asyncio
import json
import logging
import time

import aiohttp
import asyncpg

from src.api.collectors.resilience import (
    CircuitBreaker,
    ConcurrentLimiter,
    RateLimiter,
    retry_with_exponential_backoff,
)
from src.api.collectors.schemas.l2_match_schema import (
    L2CollectionSummary,
    L2DataQuality,
    L2MatchDetailSchema,
)

logger = logging.getLogger(__name__)


class ProductionL2Collector:
    """
    V37.0 工业级 L2 详情采集器

    核心特性:
    1. 共享 L1 的弹性机制（重试、熔断、限流）
    2. Pydantic Schema 强制校验
    3. 批量 Upsert（每 50 场一次提交）
    4. ID 格式修正：使用纯数字 match_id
    """

    # FotMob API 端点
    API_URL = "https://www.fotmob.com/api/matchDetails"

    # 批量写入大小
    BATCH_SIZE = 50

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        max_concurrent: int = 3,  # L2 采集并发数略低于 L1
        max_requests_per_second: int = 2,
        timeout: int = 30,
    ):
        """
        初始化 L2 采集器

        Args:
            db_pool: 数据库连接池
            max_concurrent: 最大并发数（建议 3，低于 L1）
            max_requests_per_second: 每秒最大请求数
            timeout: 请求超时时间
        """
        self.db_pool = db_pool
        self.timeout = timeout

        # 弹性机制（复用 L1 的实现）
        self.rate_limiter = RateLimiter(max_requests=max_requests_per_second, time_window=1.0)
        self.concurrent_limiter = ConcurrentLimiter(max_concurrent=max_concurrent)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=aiohttp.ClientError,
        )

        # 采集摘要
        self.summary = L2CollectionSummary()

        # HTTP 会话
        self.session: aiohttp.ClientSession | None = None

        logger.info("🏭 V37.0 工业级 L2 采集器已初始化")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=self.concurrent_limiter.max_concurrent)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector, headers=self._get_headers())
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
    async def _fetch_match_details(self, match_id: str) -> dict:
        """
        获取单场比赛的 L2 详情（带重试和熔断保护）

        Args:
            match_id: 纯数字比赛 ID（与 L1 一致）

        Returns:
            FotMob API 返回的 JSON 数据
        """
        # 检查熔断器
        if self.circuit_breaker.is_open():
            raise aiohttp.ClientError("🚨 熔断器已打开，暂停请求")

        # 速率限制
        await self.rate_limiter.acquire()

        # 构建 URL
        url = f"{self.API_URL}?matchId={match_id}"

        async with self.concurrent_limiter:
            async with self.session.get(url) as response:
                if response.status == 200:
                    self.circuit_breaker.record_success()
                    return await response.json()
                elif response.status == 404:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=404,
                        message=f"Match {match_id} not found",
                    )
                elif response.status >= 500:
                    self.circuit_breaker.record_failure(aiohttp.ClientError(f"HTTP {response.status}"))
                    raise aiohttp.ClientError(f"Server error: HTTP {response.status}")
                else:
                    raise aiohttp.ClientError(f"Unexpected status: HTTP {response.status}")

    def _parse_and_validate_l2_data(
        self,
        raw_data: dict,
        match_id: str,
    ) -> L2MatchDetailSchema | None:
        """
        解析并校验 L2 数据（Pydantic 强制校验）

        V139.1: 即使 data_quality 为 WARNING 级别（无 stats），仍返回数据用于 URL 匹配。

        Args:
            raw_data: FotMob API 返回的原始数据
            match_id: 比赛 ID

        Returns:
            L2MatchDetailSchema 对象，校验失败返回 None。
            注意: WARNING 级别数据会返回，包含 match_id、team_colors 等基础信息。
        """
        try:
            # 提取核心统计数据
            content = raw_data.get("content", {})
            stats_obj = content.get("stats", None)

            stats_data = None
            if stats_obj:
                # V37.5 容错修复：优先找 Periods（复数），备选 Period（单数）
                periods = stats_obj.get("Periods") or stats_obj.get("Period")
                if periods:
                    # FotMob API 结构：Periods -> All -> stats (数组)
                    full_match = periods.get("All") if isinstance(periods, dict) else None
                    if full_match and "stats" in full_match:
                        stats_data = self._extract_stats_from_periods(full_match["stats"])

            # 提取球队颜色
            general = raw_data.get("general", {})
            team_colors = general.get("teamColors", None)

            # 检查阵容数据
            has_lineup = bool(content.get("lineup", {}))
            has_shotmap = bool(content.get("shotmap", {}))

            # Pydantic 校验
            validated = L2MatchDetailSchema(
                match_id=match_id,
                stats=stats_data,
                team_colors=team_colors,
                has_lineup=has_lineup,
                has_shotmap=has_shotmap,
                raw_data=raw_data,  # 保存完整原始数据
            )

            # 记录数据质量 (V139.1: WARNING 级别数据仍会返回用于 URL 匹配)
            if validated.data_quality == L2DataQuality.WARNING:
                logger.info(f"⚠️ 关键特征缺失: {match_id} - 降级存储，仍可用于 URL 匹配")
            elif validated.data_quality == L2DataQuality.PARTIAL:
                logger.info(f"ℹ️ 部分特征缺失: {match_id}")

            return validated  # V139.1: 始终返回，即使为 WARNING 级别

        except Exception as e:
            logger.error(f"❌ 解析异常 {match_id}: {e}")
            return None

    def _extract_stats_from_periods(self, stats_array: list) -> dict | None:
        """
        V37.5: 从 FotMob Periods stats 数组中提取核心特征

        FotMob API 结构:
        [
          {"key": "top_stats", "stats": [
            {"key": "expected_goals", "stats": ["2.17", "0.59"]},
            {"key": "ShotsOnTarget", "stats": [4, 3]},
            {"key": "BallPossesion", "stats": [56, 44]}
          ]},
          ...
        ]

        Args:
            stats_array: Periods.All.stats 数组

        Returns:
            包含 xg, shots_on_target, possession 的字典
        """
        if not stats_array:
            return None

        # 目标特征映射：FotMob key -> 我们的字段名
        target_keys = {
            "expected_goals": "xg",
            "ShotsOnTarget": "shots_on_target",
            "BallPossesion": "possession",
        }

        result = {}

        # 扁平化搜索所有 stat groups
        for stat_group in stats_array:
            for stat_item in stat_group.get("stats", []):
                key = stat_item.get("key", "")
                if key in target_keys:
                    stats_value = stat_item.get("stats", [])
                    if isinstance(stats_value, list) and len(stats_value) >= 2:
                        # 转换为 float
                        try:
                            result[target_keys[key]] = [
                                float(stats_value[0]),
                                float(stats_value[1]),
                            ]
                        except (ValueError, TypeError):
                            result[target_keys[key]] = None

        # 只有至少有一个特征时才返回
        return result if result else None

    def _extract_stat_list(self, stat_obj: dict | None) -> list[float] | None:
        """
        提取统计数据列表 [home, away]

        FotMob API 格式: {"home": 1.5, "away": 1.2}
        """
        if stat_obj is None:
            return None
        try:
            return [float(stat_obj.get("home", 0)), float(stat_obj.get("away", 0))]
        except (ValueError, TypeError):
            return None

    async def _batch_upsert_l2_data(
        self,
        batch: list[tuple[str, dict]],
    ) -> int:
        """
        批量 Upsert L2 数据到数据库

        Args:
            batch: (match_id, validated_dict) 元组列表

        Returns:
            成功插入的记录数
        """
        if not batch:
            return 0

        try:
            start_time = time.time()
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    for match_id, validated_dict in batch:
                        json_data = json.dumps(validated_dict, ensure_ascii=False)
                        await conn.execute(
                            """
                            INSERT INTO raw_match_data (match_id, raw_data, source)
                            VALUES ($1, $2::jsonb, 'fotmob')
                            ON CONFLICT (match_id) DO UPDATE
                            SET raw_data = EXCLUDED.raw_data, updated_at = NOW()
                            """,
                            match_id,
                            json_data,
                        )

            db_time = time.time() - start_time
            self.summary.add_db_time(db_time)
            logger.debug(f"💾 批量 Upsert: {len(batch)} 场, 耗时 {db_time:.3f} 秒")
            return len(batch)

        except Exception as e:
            logger.error(f"❌ 批量 Upsert 失败: {e}")
            return 0

    async def collect_and_validate_match(
        self,
        match_id: str,
    ) -> L2MatchDetailSchema | None:
        """
        采集并校验单场比赛的 L2 数据

        Args:
            match_id: 纯数字比赛 ID

        Returns:
            L2MatchDetailSchema 对象，失败返回 None
        """
        api_start = time.time()
        try:
            # 获取原始数据
            raw_data = await self._fetch_match_details(match_id)
            api_time = time.time() - api_start

            # 解析并校验
            validated = self._parse_and_validate_l2_data(raw_data, match_id)
            if validated:
                self.summary.add_success(validated.data_quality, api_time)
            else:
                self.summary.add_failure()

            return validated

        except Exception as e:
            logger.error(f"❌ L2 采集失败 {match_id}: {e}")
            self.summary.add_failure()
            return None

    async def collect_batch(
        self,
        match_ids: list[str],
        batch_size: int = 50,
        progress_callback=None,
    ) -> L2CollectionSummary:
        """
        批量采集 L2 数据（带批量 Upsert）

        Args:
            match_ids: 纯数字比赛 ID 列表
            batch_size: 批量写入大小
            progress_callback: 进度回调函数

        Returns:
            采集摘要
        """
        logger.info(f"📊 开始批量采集 L2 数据: {len(match_ids)} 场比赛")

        batch = []
        completed = 0
        total = len(match_ids)
        last_progress = 0

        for match_id in match_ids:
            # 采集并校验
            validated = await self.collect_and_validate_match(match_id)

            if validated:
                # 加入批量写入队列
                batch.append((match_id, validated.to_dict()))

            completed += 1

            # 进度报告
            if progress_callback:
                progress = int(completed / total * 100)
                if progress >= last_progress + 10 or completed == total:
                    progress_callback(completed, total, progress)
                    last_progress = progress

            # 达到批量大小或最后一批时，执行 Upsert
            if len(batch) >= batch_size or completed == total:
                if batch:
                    saved = await self._batch_upsert_l2_data(batch)
                    logger.info(f"⏳ 进度: {completed}/{total} | 批量保存: {saved} 场")
                    batch = []

        self.summary.finalize()
        logger.info("✅ L2 批量采集完成")
        return self.summary

    def get_summary_report(self) -> str:
        """获取采集摘要报告"""
        self.summary.finalize()
        return self.summary.to_report()


# ============================================================================
# 使用示例
# ============================================================================


async def main():
    """生产级 L2 采集示例"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    from src.config_unified import get_settings

    # 创建数据库连接池
    settings = get_settings()
    db_pool = await asyncpg.create_pool(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    try:
        async with ProductionL2Collector(db_pool) as collector:
            # 示例：采集 100 场比赛
            match_ids = [str(i) for i in range(4813374, 4813474)]

            await collector.collect_batch(match_ids, batch_size=50)
            print(collector.get_summary_report())

    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
