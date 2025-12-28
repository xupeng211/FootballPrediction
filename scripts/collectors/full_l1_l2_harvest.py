#!/usr/bin/env python3
"""
V36.0 全量 L1/L2 采集器 (Production-Grade Refactor)
====================================================
完整采集 5 大联赛 × 5 赛季的所有比赛数据

V36.0 重构内容:
- 集成 ProductionL1Collector (Pydantic Schema 校验)
- 指数退避重试 + 熔断器 + 速率限制
- 完全废弃旧的 fotmob_collector_l1_l2.py 调用逻辑
- 保留 L2 采集功能（使用独立方法）

FotMob League ID 对照:
- 47: Premier League
- 55: La Liga
- 54: Bundesliga
- 61: Ligue 1
- 135: Serie A

作者: ML Architect
版本: V36.0 (Production-Grade)
日期: 2025-12-28
Phase: Industrial Production Refactor
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import asyncpg

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.production_l1_collector import ProductionL1Collector
from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# 联赛配置 (V36.0 - Pydantic 白名单对齐)
# 根据 FotMob API 官方 League ID 配置
LEAGUE_CONFIGS = [
    {"id": 47, "name": "Premier League", "code": "PL"},    # ✅ 380 场/赛季
    {"id": 55, "name": "La Liga", "code": "LL"},          # ✅ 380 场/赛季
    {"id": 54, "name": "Bundesliga", "code": "BL"},       # ✅ 306 场/赛季
    {"id": 61, "name": "Ligue 1", "code": "L1"},           # ✅ 380 场/赛季
    {"id": 135, "name": "Serie A", "code": "SA"},         # ✅ 380 场/赛季
]

# 赛季配置 (FotMob 格式)
SEASONS = {
    "20/21": "2021",
    "21/22": "2122",
    "22/23": "2223",
    "23/24": "2324",
    "24/25": "2425",
}


class L1L2Harvester:
    """
    V36.0 L1/L2 采集协调器

    负责协调 L1 采集 (ProductionL1Collector) 和 L2 采集 (原始 API)
    """

    def __init__(self, db_pool: asyncpg.Pool, max_l2_concurrency: int = 2):
        """
        初始化采集协调器

        Args:
            db_pool: 数据库连接池
            max_l2_concurrency: L2 采集最大并发数
        """
        self.db_pool = db_pool
        self.max_l2_concurrency = max_l2_concurrency
        self.l1_collector = None  # 将在 __aenter__ 中初始化
        self.stats = {
            "l1_attempted": 0,
            "l1_success": 0,
            "l1_failed": 0,
            "l1_saved": 0,
            "l2_attempted": 0,
            "l2_success": 0,
            "l2_failed": 0,
        }

    async def __aenter__(self):
        """进入上下文，初始化 ProductionL1Collector"""
        self.l1_collector = ProductionL1Collector(
            max_concurrent=5,
            max_requests_per_second=2,  # FotMob 限流保护
        )
        await self.l1_collector.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，关闭 ProductionL1Collector"""
        if self.l1_collector:
            await self.l1_collector.__aexit__(exc_type, exc_val, exc_tb)

    async def _save_l1_match_index(self, match: dict[str, Any]) -> bool:
        """
        保存 L1 比赛索引到数据库

        Args:
            match: Pydantic L1MatchData 转换后的字典

        Returns:
            是否保存成功
        """
        try:
            async with self.db_pool.acquire() as conn:
                # 检查是否已存在
                existing = await conn.fetchval(
                    "SELECT match_id FROM matches WHERE match_id = $1",
                    match["match_id"]
                )

                if existing:
                    # 更新现有记录
                    await conn.execute(
                        """
                        UPDATE matches SET
                            league_id = $2,
                            league_name = $3,
                            season_id = $4,
                            season_name = $5,
                            home_team = $6,
                            away_team = $7,
                            home_team_id = $8,
                            away_team_id = $9,
                            status = $10,
                            match_time = $11,
                            home_score = $12,
                            away_score = $13,
                            updated_at = NOW()
                        WHERE match_id = $1
                        """,
                        match["match_id"],
                        match["league_id"],
                        match["league_name"],
                        match["season_id"],
                        match["season_name"],
                        match["home_team"],
                        match["away_team"],
                        match["home_team_id"],
                        match["away_team_id"],
                        match["status"],
                        match["match_time_utc"] or None,
                        match["home_score"],
                        match["away_score"],
                    )
                else:
                    # 插入新记录
                    await conn.execute(
                        """
                        INSERT INTO matches (
                            match_id, league_id, league_name, season_id, season_name,
                            home_team, away_team, home_team_id, away_team_id,
                            status, match_time, home_score, away_score,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
                        """,
                        match["match_id"],
                        match["league_id"],
                        match["league_name"],
                        match["season_id"],
                        match["season_name"],
                        match["home_team"],
                        match["away_team"],
                        match["home_team_id"],
                        match["away_team_id"],
                        match["status"],
                        match["match_time_utc"] or None,
                        match["home_score"],
                        match["away_score"],
                    )

                self.stats["l1_saved"] += 1
                return True

        except Exception as e:
            logger.error(f"❌ L1保存失败 {match.get('match_id', 'unknown')}: {e}")
            return False

    async def save_all_l1_matches(self, matches: list[Any]) -> int:
        """
        保存所有 L1 比赛到数据库

        Args:
            matches: Pydantic L1MatchData 对象列表

        Returns:
            成功保存的比赛数量
        """
        saved_count = 0
        for match in matches:
            # L1MatchData 对象有 to_dict() 方法
            match_dict = match.to_dict() if hasattr(match, 'to_dict') else match
            if await self._save_l1_match_index(match_dict):
                saved_count += 1

        logger.info(f"✅ L1 保存完成: {saved_count}/{len(matches)} 场比赛")
        return saved_count

    async def _filter_new_matches(self, match_ids: list[str]) -> list[str]:
        """
        过滤出需要采集 L2 的新比赛

        Args:
            match_ids: 比赛ID列表（格式：{external_id}_{season}）

        Returns:
            需要采集的比赛ID列表
        """
        if not match_ids:
            return []

        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT DISTINCT match_id
                    FROM raw_match_data
                    WHERE match_id = ANY($1)
                """
                existing = await conn.fetch(query, match_ids)
                existing_ids = set(row["match_id"] for row in existing)
                new_ids = [mid for mid in match_ids if mid not in existing_ids]
                return new_ids

        except Exception as e:
            logger.error(f"❌ 过滤新比赛失败: {e}")
            return match_ids  # 失败时返回全部，避免遗漏

    async def _save_l2_raw_data(self, match_id: str, data: dict[str, Any]) -> bool:
        """保存 L2 原始数据到数据库"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO raw_match_data (match_id, data, fetched_at, updated_at)
                    VALUES ($1, $2, NOW(), NOW())
                    ON CONFLICT (match_id) DO UPDATE
                    SET data = $2, updated_at = NOW()
                    """,
                    match_id,
                    data,
                )
                return True
        except Exception as e:
            logger.error(f"❌ L2保存失败 {match_id}: {e}")
            return False

    async def collect_l2_match_data(self, match_id: str) -> dict[str, Any] | None:
        """
        采集单场比赛的 L2 数据

        Args:
            match_id: 比赛ID（格式：{external_id}_{season}）

        Returns:
            L2 数据字典，失败返回 None
        """
        # 提取 external_id
        external_id = match_id.split("_")[0]

        # 构建 FotMob API URL
        url = f"https://www.fotmob.com/api/matchDetails?matchId={external_id}"

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.stats["l2_success"] += 1
                        return data
                    else:
                        logger.warning(f"⚠️  L2采集失败 {match_id}: HTTP {response.status}")
                        self.stats["l2_failed"] += 1
                        return None

        except Exception as e:
            logger.error(f"❌ L2采集异常 {match_id}: {e}")
            self.stats["l2_failed"] += 1
            return None

    async def _update_collection_status_batch(self, match_ids: list[str], status: str):
        """批量更新采集状态（占位方法，保持接口兼容）"""
        pass


async def full_harvest(l2_limit: int = 10000, silent_mode: bool = True):
    """
    全量 L1/L2 采集

    Args:
        l2_limit: L2 采集数量限制
        silent_mode: 静默生产模式（减少日志输出）
    """
    log_level = logging.WARNING if silent_mode else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    # 创建专用进度日志器（始终输出关键进度）
    progress_logger = logging.getLogger("progress")
    progress_logger.setLevel(logging.INFO)
    progress_logger.addHandler(logging.StreamHandler())
    progress_logger.propagate = False

    progress_logger.info("=" * 60)
    progress_logger.info("🌍 V36.0 全量 L1/L2 采集 - Production-Grade")
    progress_logger.info(f"📊 目标: {len(LEAGUE_CONFIGS)} 大联赛 × {len(SEASONS)} 赛季")
    progress_logger.info("=" * 60)

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
        async with L1L2Harvester(db_pool, max_l2_concurrency=2) as harvester:
            all_matches = []
            total_combinations = len(LEAGUE_CONFIGS) * len(SEASONS)
            completed = 0
            last_progress = 0

            # 步骤 1: L1 采集所有联赛-赛季组合（使用 ProductionL1Collector）
            progress_logger.info("📋 步骤 1: L1 全量采集 (Pydantic 校验)")

            for league in LEAGUE_CONFIGS:
                for season_name, season_code in SEASONS.items():
                    completed += 1
                    progress = int(completed / total_combinations * 100)

                    if progress >= last_progress + 10 or completed == total_combinations:
                        progress_logger.info(f"⏳ L1 进度: {progress}% ({completed}/{total_combinations})")
                        last_progress = progress

                    try:
                        # V36.0: 使用 ProductionL1Collector（带 Pydantic 校验）
                        matches = await harvester.l1_collector.collect_league_season(
                            league_id=league["id"],
                            season_code=season_code,
                            season_name=season_name,
                        )

                        all_matches.extend(matches)
                        harvester.stats["l1_success"] += len(matches)

                    except Exception as e:
                        harvester.stats["l1_failed"] += 1
                        logger.error(f"✗ {league['name']} {season_name} 失败: {e}")

            harvester.stats["l1_attempted"] = total_combinations

            progress_logger.info("=" * 60)
            progress_logger.info(f"✅ L1 采集完成: {len(all_matches)} 场比赛")
            progress_logger.info("=" * 60)

            # 步骤 2: 保存 L1 数据到数据库
            progress_logger.info("💾 步骤 2: 保存 L1 数据到数据库...")

            saved_count = await harvester.save_all_l1_matches(all_matches)
            progress_logger.info(f"✅ L1 保存完成: {saved_count}/{len(all_matches)} 场")

            # 步骤 3: L2 并发采集
            progress_logger.info("=" * 60)
            progress_logger.info(f"📊 步骤 3: L2 并发采集 (限制: {l2_limit} 场)")
            progress_logger.info("=" * 60)

            # 提取 match_id (使用 match_id + season 作为唯一键)
            match_ids = []
            for m in all_matches[:l2_limit]:
                match_id = m.match_id if hasattr(m, 'match_id') else m.get("match_id")
                season = m.season_name if hasattr(m, 'season_name') else m.get("season", "unknown")
                if match_id:
                    match_ids.append(f"{match_id}_{season}")

            # 只采集新比赛（过滤已存在的）
            progress_logger.info("🔍 筛选新比赛...")
            new_match_ids = await harvester._filter_new_matches(match_ids)
            progress_logger.info(f"🎯 待采集: {len(new_match_ids)}/{len(match_ids)} 场新比赛")

            if new_match_ids:
                # 并发采集（带进度跟踪）
                total_l2 = len(new_match_ids)
                l2_completed = 0
                last_l2_progress = 0

                async def l2_with_progress(mid: str):
                    nonlocal l2_completed, last_l2_progress
                    # 采集 L2 数据
                    data = await harvester.collect_l2_match_data(mid)
                    if data:
                        # 保存到数据库
                        await harvester._save_l2_raw_data(mid, data)
                    l2_completed += 1
                    l2_progress = int(l2_completed / total_l2 * 100)
                    if l2_progress >= last_l2_progress + 10 or l2_completed == total_l2:
                        progress_logger.info(f"⏳ L2 进度: {l2_progress}% ({l2_completed}/{total_l2})")
                        last_l2_progress = l2_progress
                    return data

                # 批量并发采集
                tasks = [l2_with_progress(mid) for mid in new_match_ids]
                l2_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 统计结果
                harvester.stats["l2_attempted"] = total_l2

                progress_logger.info("=" * 60)
                progress_logger.info("📊 L2 采集统计")
                progress_logger.info(f"   总计: {total_l2}")
                progress_logger.info(f"   成功: {harvester.stats['l2_success']}")
                progress_logger.info(f"   失败: {harvester.stats['l2_failed']}")
                progress_logger.info("=" * 60)
            else:
                progress_logger.info("ℹ️  无新比赛需要采集")

            progress_logger.info("=" * 60)
            progress_logger.info("🎉 V36.0 全量 L1/L2 采集完成! (Production-Grade)")
            progress_logger.info("=" * 60)

            # 输出完整统计
            progress_logger.info("📊 完整统计报告")
            for key, value in harvester.stats.items():
                progress_logger.info(f"   {key}: {value}")

            # 输出 L1 采集器摘要报告
            progress_logger.info("\n" + harvester.l1_collector.get_summary_report())

            return harvester.stats

    finally:
        await db_pool.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V36.0 全量 L1/L2 采集器 (Production-Grade)")
    parser.add_argument("--l2-limit", type=int, default=10000, help="L2 采集数量限制 (默认: 10000)")
    parser.add_argument("--verbose", action="store_true", help="启用详细日志输出")

    args = parser.parse_args()

    exit_code = asyncio.run(full_harvest(l2_limit=args.l2_limit, silent_mode=not args.verbose))
    sys.exit(exit_code if exit_code is not None else 0)
