#!/usr/bin/env python3
"""
V51.0 增量采集器 (Incremental Collector)
==========================================
核心功能：
1. 检查数据库中最新的 match_time
2. 仅抓取该时间之后的比赛（增量收割）
3. 支持直接入库（解决外键约束）
4. 基于 Phase 2.5 验证的 API 调用逻辑

Author: Senior Backend Architect
Version: V51.0
Date: 2025-12-28
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import psycopg2

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


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
        }


class IncrementalCollector:
    """
    V51.0 增量采集器

    核心特性：
    1. 检查数据库最新 match_time，只抓取更新的比赛
    2. 基于 Phase 2.5 验证的 API 调用逻辑
    3. 自动处理外键约束（先 matches 后 raw_match_data）
    4. 完整的错误处理和日志记录
    """

    # V51.0: 拟人化反爬盔甲
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
    ):
        """
        初始化增量采集器

        Args:
            base_url: FotMob API 基础 URL
            target_count: 目标采集数量
            request_timeout: 请求超时时间
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

        logger.info("🎯 V51.0 增量采集器已初始化")

    def _get_latest_match_time(self) -> datetime | None:
        """
        获取数据库中最新的比赛时间

        Returns:
            最新比赛的 match_time，如果没有数据则返回 None
        """
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT MAX(match_time) as latest_time
                FROM matches
                WHERE match_time IS NOT NULL
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
        logger.info("V51.0 增量采集: 网络抓取")
        logger.info("=" * 60)

        if since:
            logger.info(f"增量模式: 获取 {since.strftime('%Y-%m-%d')} 之后的比赛")
        else:
            logger.info("全量模式: 获取所有比赛")

        logger.info(f"目标: 获取 {self.target_count} 场比赛")

        all_matches = []
        base_url = self.base_url

        async with aiohttp.ClientSession() as session:
            for league_id, league_name_en, league_name_cn in TARGET_LEAGUES:
                if len(all_matches) >= self.target_count:
                    logger.info(f"✅ 已达到目标数量 {self.target_count}，停止扫描")
                    break

                url = f"{base_url}/leagues?id={league_id}&season={CURRENT_SEASON}"

                try:
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
                                    except:
                                        pass

                                # 增量过滤：只获取 since 之后的比赛
                                if since and match_time and match_time <= since:
                                    continue

                                home_team = match_data.get("home", {})
                                away_team = match_data.get("away", {})

                                all_matches.append(
                                    {
                                        "match_id": match_id,
                                        "league_id": league_id,
                                        "league_name": league_name_en,
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

                        else:
                            self.stats.http_errors += 1
                            logger.warning(f"  API 返回 {response.status}")

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

        base_url = self.base_url
        full_match_data = {}

        async with aiohttp.ClientSession() as session:
            for i, match_id in enumerate(match_ids):
                url = f"{base_url}/matchDetails?matchId={match_id}"

                try:
                    start_time = time.time()
                    headers = {"User-Agent": random.choice(self.USER_AGENTS)}

                    async with session.get(url, timeout=self.request_timeout, headers=headers) as response:
                        elapsed = time.time() - start_time

                        if response.status == 200:
                            self.stats.http_200 += 1
                            data = await response.json()
                            full_match_data[match_id] = data

                            logger.info(
                                f"  [{i + 1}/{len(match_ids)}] Match {match_id}: "
                                f"HTTP {response.status} | {elapsed * 1000:.0f}ms"
                            )
                        else:
                            self.stats.http_errors += 1
                            logger.warning(f"  [{i + 1}/{len(match_ids)}] Match {match_id}: HTTP {response.status}")

                    # 随机延迟，避免触发限流
                    await asyncio.sleep(0.2 + 0.3 * (i % 3))

                except Exception as e:
                    self.stats.http_errors += 1
                    logger.error(f"  下载 Match {match_id} 失败: {e}")

        logger.info(f"\n✓ 成功下载 {len(full_match_data)}/{len(match_ids)} 场比赛")
        self.stats.fetched_full = len(full_match_data)

        return full_match_data

    def _import_matches_to_db(self, match_l1_data: list[dict]) -> int:
        """
        先将比赛数据导入 matches 表（raw_match_data 表有外键约束）

        Args:
            match_l1_data: Rich L1 比赛数据列表

        Returns:
            插入记录数
        """
        logger.info("\n" + "=" * 60)
        logger.info("导入比赛到 matches 表")
        logger.info("=" * 60)

        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        imported = 0

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
                    except:
                        pass

                # 获取比分
                home_score = match_data.get("home_score")
                away_score = match_data.get("away_score")

                cur.execute(
                    """
                    INSERT INTO matches (
                        external_id, league_id, league_name, season, match_time, status,
                        home_team, away_team, home_score, away_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (external_id) DO UPDATE SET
                        home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
                        away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
                        status = COALESCE(EXCLUDED.status, matches.status),
                        match_time = COALESCE(EXCLUDED.match_time, matches.match_time),
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        str(match_id),
                        match_data.get("league_id"),
                        match_data.get("league_name", "Unknown"),
                        match_data.get("season"),
                        match_time,
                        match_data.get("status"),
                        match_data.get("home_team", "Unknown"),
                        match_data.get("away_team", "Unknown"),
                        home_score,
                        away_score,
                    ),
                )
                imported += 1

            except Exception as e:
                logger.error(f"导入 Match {match_data.get('match_id')} 失败: {e}")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✓ 导入 {imported} 场比赛到 matches 表")
        self.stats.saved_matches = imported

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

                raw_json_str = json.dumps(raw_json, ensure_ascii=False)

                if existing:
                    cur.execute(
                        """
                        UPDATE raw_match_data
                        SET raw_data = %s, api_source = %s, created_at = NOW()
                        WHERE external_id = %s
                    """,
                        (raw_json_str, "live_crawl_v51", str(match_id)),
                    )
                    updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO raw_match_data (external_id, raw_data, api_source, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """,
                        (str(match_id), raw_json_str, "live_crawl_v51"),
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
    快速增量采集

    Args:
        target_count: 目标采集数量

    Returns:
        采集统计信息
    """
    collector = IncrementalCollector(target_count=target_count)
    stats = await collector.collect(incremental=True)

    # 打印摘要
    print("\n" + "=" * 60)
    print("V51.0 增量采集摘要")
    print("=" * 60)
    print(f"目标数量: {stats.target_count}")
    print(f"获取 L1: {stats.fetched_l1}")
    print(f"下载完整: {stats.fetched_full}")
    print(f"入库 matches: {stats.saved_matches}")
    print(f"入库 raw_data: {stats.saved_raw_data}")
    print(f"耗时: {stats.elapsed_seconds:.2f} 秒")
    print(f"HTTP 200: {stats.http_200}")
    print(f"HTTP 错误: {stats.http_errors}")
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
