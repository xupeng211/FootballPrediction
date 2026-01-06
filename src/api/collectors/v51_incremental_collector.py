#!/usr/bin/env python3
"""
V57.0 增量采集器 (Incremental Collector)
========================================
V57.0 生产体系组件 - FotMob L2 数据增量采集

核心功能：
1. 检查数据库中最新的 match_time
2. 仅抓取该时间之后的比赛（增量收割）
3. 支持直接入库（解决外键约束）
4. 基于 Phase 2.5 验证的 API 调用逻辑
5. 断点续传 + 熔断恢复

Author: Senior Backend Architect
Version: V57.0 (Production Unified)
Date: 2026-01-02
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
import random
import time

import aiohttp
import psycopg2

from src.api.collectors.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# HTTP 错误异常（带状态码，用于熔断器判断）
# ============================================================================


class HTTPClientError(Exception):
    """HTTP 客户端错误（带状态码）"""

    def __init__(self, status: int, message: str = ""):
        self.status = status
        self.message = message or f"HTTP {status}"
        super().__init__(self.message)


# ============================================================================
# 目标联赛配置
# ============================================================================

TARGET_LEAGUES = [
    (47, "Premier League", "英超"),
    (48, "Championship", "英冠"),
    (87, "La Liga", "西甲"),
    (82, "Bundesliga", "德甲"),
    (73, "Serie A", "意甲"),
    (71, "Ligue 1", "法甲"),
]

CURRENT_SEASON = "2425"  # 2024/2025


@dataclass
class CollectStatistics:
    """采集统计"""

    target_count: int = 0
    fetched_l1: int = 0
    fetched_full: int = 0
    saved_matches: int = 0
    saved_raw_data: int = 0
    extracted_features: int = 0
    failed_count: int = 0
    elapsed_seconds: float = 0.0

    # HTTP 统计
    http_200: int = 0
    http_404: int = 0
    http_errors: int = 0

    # P0 系统自愈统计 (V57.0)
    zombie_matches_fixed: int = 0  # 修复的僵尸比赛数（从非finished变为finished）
    status_updated_count: int = 0   # 总体状态更新次数

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "target_count": self.target_count,
            "fetched_l1": self.fetched_l1,
            "fetched_full": self.fetched_full,
            "saved_matches": self.saved_matches,
            "saved_raw_data": self.saved_raw_data,
            "extracted_features": self.extracted_features,
            "failed_count": self.failed_count,
            "elapsed_seconds": self.elapsed_seconds,
            "http_200": self.http_200,
            "http_404": self.http_404,
            "http_errors": self.http_errors,
            "zombie_matches_fixed": self.zombie_matches_fixed,
            "status_updated_count": self.status_updated_count,
        }


class IncrementalCollector:
    """
    V57.0 增量采集器

    核心特性：
    1. 检查数据库最新 match_time，只抓取更新的比赛
    2. 基于 Phase 2.5 验证的 API 调用逻辑
    3. 自动处理外键约束（先 matches 后 raw_match_data）
    4. 完整的错误处理和日志记录
    """

    # V57.0: 拟人化反爬盔甲
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    def __init__(
        self,
        base_url: str = "https://www.fotmob.com/api",
        target_count: int = 50,
        request_timeout: int = 30,
        enable_circuit_breaker: bool = True,
    ):
        """
        初始化增量采集器

        Args:
            base_url: FotMob API 基础 URL
            target_count: 目标采集数量
            request_timeout: 请求超时时间
            enable_circuit_breaker: 是否启用熔断器（默认启用）
        """
        self.base_url = base_url
        self.target_count = target_count
        self.request_timeout = request_timeout

        # 统计数据
        self.stats = CollectStatistics(target_count=target_count)

        # 数据库连接参数
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

        # P0 安全加固: 熔断器
        self.enable_circuit_breaker = enable_circuit_breaker
        if enable_circuit_breaker:
            cb_config = CircuitBreakerConfig(
                failure_threshold=5,
                cooldown_seconds=600,  # 10分钟
                half_open_max_calls=3,
                success_threshold=2,
                timeout_seconds=request_timeout,
                critical_http_codes={403, 429, 500, 502, 503, 504},
            )
            self.circuit_breaker = CircuitBreaker("v51_fotmob_api", cb_config)
            logger.info(f"🛡️ 熔断器已启用: {cb_config.failure_threshold}次失败触发, {cb_config.cooldown_seconds}秒冷却")
        else:
            self.circuit_breaker = None
            logger.warning("⚠️ 熔断器未启用")

        logger.info("🎯 V57.0 增量采集器已初始化")

    def _get_latest_match_time(self) -> datetime | None:
        """
        获取数据库中最新的比赛时间

        Returns:
            最新比赛的 match_date，如果没有数据则返回 None
        """
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT MAX(match_date) as latest_time
                FROM matches
                WHERE match_date IS NOT NULL
            """)
            result = cur.fetchone()
            return result[0] if result and result[0] else None
        finally:
            cur.close()
            conn.close()

    async def _fetch_live_matches(self, since: datetime | None = None) -> list[dict]:
        """
        从 FotMob API 获取最新的比赛数据

        Args:
            since: 只获取此时间之后的比赛

        Returns:
            比赛数据列表
        """
        logger.info("=" * 60)
        logger.info("V57.0 增量采集: 网络抓取")
        logger.info("=" * 60)

        if since:
            logger.info(f"增量模式: 获取 {since.strftime('%Y-%m-%d')} 之后的比赛")
        else:
            logger.info("全量模式: 获取所有比赛")

        logger.info(f"目标: 获取 {self.target_count} 场比赛")

        # P0 安全加固: 检查熔断器状态
        if self.circuit_breaker and not self.circuit_breaker.can_proceed():
            remaining = self.circuit_breaker.get_cooldown_remaining()
            logger.error(f"🔴 熔断器已打开，暂停采集 {remaining:.0f} 秒")
            logger.info("💡 建议: 稍后重试或检查 API 状态")
            return []

        all_matches = []
        base_url = self.base_url

        async with aiohttp.ClientSession() as session:
            for league_id, _league_name_en, league_name_cn in TARGET_LEAGUES:
                if len(all_matches) >= self.target_count:
                    logger.info(f"✅ 已达到目标数量 {self.target_count}，停止扫描")
                    break

                url = f"{base_url}/leagues?id={league_id}&season={CURRENT_SEASON}"

                try:
                    # P0 安全加固: 使用熔断器保护 HTTP 请求
                    if self.circuit_breaker:
                        async with self.circuit_breaker:
                            await self._fetch_league_data(
                                session, url, league_id, league_name_cn, all_matches, since
                            )
                    else:
                        await self._fetch_league_data(
                            session, url, league_id, league_name_cn, all_matches, since
                        )

                except CircuitBreakerOpenError as e:
                    logger.error(f"🔴 熔断器已打开: 剩余 {e.cooldown_remaining:.0f} 秒")
                    logger.warning("⚠️ 停止采集，避免进一步触发 API 封禁")
                    break

                except HTTPClientError as e:
                    # HTTP 错误已被熔断器记录
                    logger.warning(f"HTTP 错误: {e.status}")
                    continue

                except Exception as e:
                    self.stats.http_errors += 1
                    logger.error(f"扫描 {league_name_cn} 失败: {e}")
                    continue

                # 短暂休息
                await asyncio.sleep(0.5)

        logger.info(f"\n✓ 网络抓取完成: {len(all_matches)} 场比赛")

        # 限制到目标数量
        all_matches = all_matches[: self.target_count]
        self.stats.fetched_l1 = len(all_matches)

        return all_matches

    async def _fetch_league_data(
        self,
        session: aiohttp.ClientSession,
        url: str,
        league_id: int,
        league_name_cn: str,
        all_matches: list[dict],
        since: datetime | None,
    ) -> None:
        """
        获取单个联赛数据（由熔断器保护）

        Args:
            session: aiohttp 会话
            url: 请求 URL
            league_name_cn: 联赛中文名称
            all_matches: 所有比赛列表（引用）
            since: 增量模式起始时间

        Raises:
            HTTPClientError: HTTP 错误（带状态码）
        """
        start_time = time.time()
        headers = {"User-Agent": random.choice(self.USER_AGENTS)}

        async with session.get(url, timeout=self.request_timeout, headers=headers) as response:
            elapsed = time.time() - start_time
            logger.info(f"  HTTP {response.status} | {elapsed * 1000:.0f}ms")

            if response.status == 200:
                self.stats.http_200 += 1
                data = await response.json()

                # 解析比赛数据
                fixtures = data.get("fixtures", {})
                all_matches_data = fixtures.get("allMatches", [])

                # 转换为统一格式
                for match_data in all_matches_data:
                    match_id = match_data.get("id")
                    if not match_id:
                        continue

                    # 解析状态
                    status_obj = match_data.get("status", {})
                    is_finished = status_obj.get("finished", False)
                    is_started = status_obj.get("started", False)

                    if is_finished:
                        status = "finished"
                    elif is_started:
                        status = "ongoing"
                    else:
                        status = "scheduled"

                    # 解析时间
                    match_time_utc = status_obj.get("utcTime", "")
                    match_time = None
                    if match_time_utc:
                        try:
                            match_time = datetime.fromisoformat(match_time_utc.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    # 增量过滤：只获取 since 之后的比赛
                    if since and match_time and match_time <= since:
                        continue

                    home_team = match_data.get("home", {})
                    away_team = match_data.get("away", {})

                    all_matches.append(
                        {
                            "match_id": match_id,
                            "league_id": league_id,  # 使用传入的 league_id 参数
                            "league_name": league_name_cn,
                            "season": CURRENT_SEASON,
                            "home_team": home_team.get("name", "Unknown"),
                            "away_team": away_team.get("name", "Unknown"),
                            "home_team_id": int(home_team.get("id", 0)),
                            "away_team_id": int(away_team.get("id", 0)),
                            "status": status,
                            "match_time_utc": match_time_utc,
                            "home_score": status_obj.get("homeScore"),
                            "away_score": status_obj.get("awayScore"),
                        }
                    )

                recent_count = sum(1 for m in all_matches if m.get("match_time"))
                logger.info(f"✓ {league_name_cn}: 找到 {recent_count} 场最近比赛")

            elif response.status in {403, 429, 500, 502, 503, 504}:
                # 关键错误：抛出带状态码的异常，触发熔断器
                self.stats.http_errors += 1
                raise HTTPClientError(response.status, f"API 返回 {response.status}")

            else:
                self.stats.http_errors += 1
                logger.warning(f"  API 返回 {response.status}")

    async def _fetch_full_match_details(self, match_ids: list[int]) -> dict[int, dict]:
        """
        下载完整的比赛详情 JSON

        Args:
            match_ids: 比赛 ID 列表

        Returns:
            {match_id: full_json} 映射
        """
        logger.info("\n" + "=" * 60)
        logger.info("下载完整原始 JSON")
        logger.info("=" * 60)
        logger.info(f"目标: 下载 {len(match_ids)} 场比赛的完整数据")

        # P0 安全加固: 检查熔断器状态
        if self.circuit_breaker and not self.circuit_breaker.can_proceed():
            remaining = self.circuit_breaker.get_cooldown_remaining()
            logger.error(f"🔴 熔断器已打开，暂停采集 {remaining:.0f} 秒")
            return {}

        base_url = self.base_url
        full_match_data = {}

        async with aiohttp.ClientSession() as session:
            for i, match_id in enumerate(match_ids):
                url = f"{base_url}/matchDetails?matchId={match_id}"

                try:
                    # P0 安全加固: 使用熔断器保护 HTTP 请求
                    if self.circuit_breaker:
                        async with self.circuit_breaker:
                            data = await self._fetch_match_detail(session, url, i, match_id, len(match_ids))
                            if data:
                                full_match_data[match_id] = data
                    else:
                        data = await self._fetch_match_detail(session, url, i, match_id, len(match_ids))
                        if data:
                            full_match_data[match_id] = data

                except CircuitBreakerOpenError as e:
                    logger.error(f"🔴 熔断器已打开: 剩余 {e.cooldown_remaining:.0f} 秒")
                    logger.warning("⚠️ 停止采集，避免进一步触发 API 封禁")
                    break

                except HTTPClientError as e:
                    # HTTP 错误已被熔断器记录
                    logger.warning(f"  Match {match_id}: HTTP {e.status}")
                    continue

                except Exception as e:
                    self.stats.http_errors += 1
                    logger.error(f"  下载 Match {match_id} 失败: {e}")
                    continue

                # 随机延迟，避免触发限流
                await asyncio.sleep(0.2 + 0.3 * (i % 3))

        logger.info(f"\n✓ 成功下载 {len(full_match_data)}/{len(match_ids)} 场比赛")
        self.stats.fetched_full = len(full_match_data)

        return full_match_data

    async def _fetch_match_detail(
        self,
        session: aiohttp.ClientSession,
        url: str,
        index: int,
        match_id: int,
        total_count: int,
    ) -> dict | None:
        """
        获取单场比赛详情（由熔断器保护）

        Args:
            session: aiohttp 会话
            url: 请求 URL
            index: 当前索引
            match_id: 比赛 ID
            total_count: 总数

        Returns:
            比赛详情 JSON，失败返回 None

        Raises:
            HTTPClientError: HTTP 错误（带状态码）
        """
        start_time = time.time()
        headers = {"User-Agent": random.choice(self.USER_AGENTS)}

        async with session.get(url, timeout=self.request_timeout, headers=headers) as response:
            elapsed = time.time() - start_time

            if response.status == 200:
                self.stats.http_200 += 1
                data = await response.json()

                logger.info(
                    f"  [{index + 1}/{total_count}] Match {match_id}: "
                    f"HTTP {response.status} | {elapsed * 1000:.0f}ms"
                )
                return data

            if response.status in {403, 429, 500, 502, 503, 504}:
                # 关键错误：抛出带状态码的异常，触发熔断器
                self.stats.http_errors += 1
                raise HTTPClientError(response.status, f"Match {match_id} 返回 {response.status}")

            self.stats.http_errors += 1
            logger.warning(f"  [{index + 1}/{total_count}] Match {match_id}: HTTP {response.status}")
            return None

    def _import_matches_to_db(self, match_l1_data: list[dict]) -> int:
        """
        V57.0: 比分驱动的状态自愈 + 批量提交优化
        =========================================================
        核心修复: 只要 L1 索引返回有效比分，强制将状态更新为 finished

        自愈逻辑:
        1. 当 home_score IS NOT NULL AND away_score IS NOT NULL 时
           -> 强制更新 home_score, away_score
           -> 强制更新 status = 'finished'
        2. 否则保持数据库中原有值

        Args:
            match_l1_data: Rich L1 比赛数据列表

        Returns:
            插入/更新的记录数
        """
        logger.info("\n" + "=" * 60)
        logger.info("V57.0 导入比赛到 matches 表 (比分驱动自愈)")
        logger.info("=" * 60)

        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        # ============================================
        # 准备批量数据
        # ============================================
        batch_data = []
        zombie_flags = []  # 单独存储 has_valid_score 用于统计
        imported = 0
        zombie_fixed = 0  # 统计修复的僵尸比赛

        for match_data in match_l1_data:
            try:
                match_id = match_data.get("match_id")
                if not match_id:
                    continue

                # 解析时间
                match_time = None
                match_time_utc = match_data.get("match_time_utc", "")
                if match_time_utc:
                    try:
                        match_time = datetime.fromisoformat(match_time_utc.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                # 获取比分（核心判断依据）
                home_score = match_data.get("home_score")
                away_score = match_data.get("away_score")

                # ===== V57.0 核心逻辑: 比分驱动状态自愈 =====
                # 判断 L1 是否返回了有效比分
                has_valid_score = (
                    home_score is not None
                    and away_score is not None
                    and isinstance(home_score, int)
                    and isinstance(away_score, int)
                )

                # 如果有有效比分，强制状态为 finished；否则使用 L1 返回的 status
                final_status = "finished" if has_valid_score else match_data.get("status", "scheduled")

                # 准备数据库数据（11 个字段：match_id + external_id + 9 个其他字段）
                batch_data.append((
                    str(match_id),  # match_id (主键)
                    str(match_id),  # external_id (用于 UPSERT 冲突检测)
                    match_data.get("league_id"),
                    match_data.get("league_name", "Unknown"),
                    match_data.get("season"),
                    match_time,
                    final_status,
                    match_data.get("home_team", "Unknown"),
                    match_data.get("away_team", "Unknown"),
                    home_score,
                    away_score,
                ))

                # 单独存储 has_valid_score 用于统计
                zombie_flags.append(has_valid_score)

            except Exception as e:
                logger.error(f"预处理 Match {match_data.get('match_id')} 失败: {e}")

        # ============================================
        # V57.0 批量 UPSERT (使用 executemany 优化性能)
        # ============================================
        batch_size = 100
        total_batches = (len(batch_data) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(batch_data), batch_size):
            current_batch = batch_data[batch_idx:batch_idx + batch_size]
            current_flags = zombie_flags[batch_idx:batch_idx + batch_size]

            # 执行批量 UPSERT
            cur.executemany(
                """
                INSERT INTO matches (
                    match_id, external_id, league_id, league_name, season, match_date, status,
                    home_team, away_team, home_score, away_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id) DO UPDATE SET
                    -- ===== V57.0 核心修复: 比分驱动状态自愈 =====
                    -- 当新数据有比分时，强制更新；否则保留旧值
                    home_score = CASE
                        WHEN EXCLUDED.home_score IS NOT NULL AND EXCLUDED.away_score IS NOT NULL
                        THEN EXCLUDED.home_score
                        ELSE matches.home_score
                    END,
                    away_score = CASE
                        WHEN EXCLUDED.home_score IS NOT NULL AND EXCLUDED.away_score IS NOT NULL
                        THEN EXCLUDED.away_score
                        ELSE matches.away_score
                    END,
                    -- ===== 状态自愈: 有比分时强制为 finished =====
                    status = CASE
                        WHEN EXCLUDED.home_score IS NOT NULL AND EXCLUDED.away_score IS NOT NULL
                        THEN 'finished'
                        ELSE COALESCE(EXCLUDED.status, matches.status)
                    END,
                    -- 其他字段正常更新
                    league_id = COALESCE(EXCLUDED.league_id, matches.league_id),
                    league_name = COALESCE(EXCLUDED.league_name, matches.league_name),
                    season = COALESCE(EXCLUDED.season, matches.season),
                    match_date = COALESCE(EXCLUDED.match_date, matches.match_date),
                    home_team = COALESCE(EXCLUDED.home_team, matches.home_team),
                    away_team = COALESCE(EXCLUDED.away_team, matches.away_team),
                    updated_at = CURRENT_TIMESTAMP
                """,
                current_batch
            )

            imported += len(current_batch)

            # 统计本批次修复的僵尸比赛数
            for has_score in current_flags:
                if has_score:
                    zombie_fixed += 1

            # 进度日志
            batch_num = batch_idx // batch_size + 1
            if total_batches > 5:  # 只有超过5批才显示进度
                logger.info(f"  批量提交进度: {batch_num}/{total_batches} ({len(current_batch)} 场)")

        conn.commit()
        cur.close()
        conn.close()

        # 更新统计
        self.stats.saved_matches = imported
        self.stats.zombie_matches_fixed = zombie_fixed
        self.stats.status_updated_count = zombie_fixed

        # ============================================
        # V57.0 自愈能力报告
        # ============================================
        logger.info(f"✓ 导入/更新 {imported} 场比赛到 matches 表")

        if zombie_fixed > 0:
            logger.info("")
            logger.info("╔════════════════════════════════════════════════════════════╗")
            logger.info("║           V57.0 系统自愈报告 (比分驱动状态修复)              ║")
            logger.info("╚════════════════════════════════════════════════════════════╝")
            logger.info(f"🔄 本次运行共修复/唤醒: {zombie_fixed} 场僵尸比赛")
            logger.info("   这些比赛从 'scheduled'/'ongoing' 被修正为 'finished'")
            logger.info("╚════════════════════════════════════════════════════════════╝")
        else:
            logger.info("ℹ️  无需修复: 所有比赛状态已是最新")

        return imported

    def _save_raw_match_data(self, raw_data_map: dict[int, dict]) -> int:
        """
        将原始 JSON 存入 raw_match_data 表

        Args:
            raw_data_map: {match_id: full_json} 映射

        Returns:
            插入记录数
        """
        logger.info("\n" + "=" * 60)
        logger.info("原始 JSON 存入 raw_match_data 表")
        logger.info("=" * 60)

        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        inserted = 0
        updated = 0

        for match_id, raw_json in raw_data_map.items():
            try:
                # 检查是否已存在
                cur.execute("SELECT id FROM raw_match_data WHERE external_id = %s", (str(match_id),))
                existing = cur.fetchone()

                # 使用 psycopg2.extras.Json 处理 JSONB
                from psycopg2.extras import Json
                raw_json_data = Json(raw_json)

                if existing:
                    cur.execute(
                        """
                        UPDATE raw_match_data
                        SET raw_data = %s, source = %s, updated_at = NOW()
                        WHERE external_id = %s
                    """,
                        (raw_json_data, "live_crawl_v51", str(match_id)),
                    )
                    updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO raw_match_data (external_id, raw_data, source, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """,
                        (str(match_id), raw_json_data, "live_crawl_v51"),
                    )
                    inserted += 1

            except Exception as e:
                logger.error(f"保存 Match {match_id} 失败: {e}")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✓ 数据库写入完成: 插入 {inserted}, 更新 {updated}")
        self.stats.saved_raw_data = inserted + updated

        return inserted + updated

    async def collect(self, incremental: bool = True) -> CollectStatistics:
        """
        执行增量采集

        Args:
            incremental: 是否启用增量模式

        Returns:
            采集统计信息
        """
        start_time = time.time()

        # 步骤 0: 检查数据库最新时间（增量模式）
        latest_time = None
        if incremental:
            latest_time = self._get_latest_match_time()
            if latest_time:
                logger.info(f"📅 数据库最新比赛时间: {latest_time}")

        # 步骤 1: 网络抓取
        live_matches = await self._fetch_live_matches(since=latest_time if incremental else None)

        if not live_matches:
            logger.warning("未获取到任何比赛数据")
            return self.stats

        # 步骤 2: 下载完整原始 JSON
        match_ids = [m["match_id"] for m in live_matches]
        full_match_data = await self._fetch_full_match_details(match_ids)

        # 步骤 3: 先导入比赛到 matches 表（外键约束）
        self._import_matches_to_db(live_matches)

        # 步骤 4: 存入 raw_match_data 表
        self._save_raw_match_data(full_match_data)

        self.stats.elapsed_seconds = time.time() - start_time

        return self.stats


# ============================================================================
# 便捷函数
# ============================================================================


async def quick_incremental_collect(target_count: int = 50) -> CollectStatistics:
    """
    V57.0 快速增量采集

    Args:
        target_count: 目标采集数量

    Returns:
        采集统计信息
    """
    collector = IncrementalCollector(target_count=target_count)
    stats = await collector.collect(incremental=True)

    # 打印摘要
    print("\n" + "=" * 60)
    print("V57.0 增量采集摘要 (比分驱动自愈)")
    print("=" * 60)
    print(f"目标数量: {stats.target_count}")
    print(f"获取 L1: {stats.fetched_l1}")
    print(f"下载完整: {stats.fetched_full}")
    print(f"入库 matches: {stats.saved_matches}")
    print(f"入库 raw_data: {stats.saved_raw_data}")
    print(f"耗时: {stats.elapsed_seconds:.2f} 秒")
    print(f"HTTP 200: {stats.http_200}")
    print(f"HTTP 错误: {stats.http_errors}")

    # V57.0: 僵尸比赛修复统计
    if stats.zombie_matches_fixed > 0:
        print(f"🔄 僵尸比赛修复: {stats.zombie_matches_fixed} 场")

    print("=" * 60)

    return stats


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    )

    async def test():
        """测试函数"""
        stats = await quick_incremental_collect(target_count=10)
        print(f"\n✅ 测试完成! 统计: {stats.to_dict()}")

    asyncio.run(test())
