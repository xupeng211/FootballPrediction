#!/usr/bin/env python3
"""
V37.0 全量 L1/L2 采集器 (Production-Grade Refactor)
====================================================
完整采集 5 大联赛 × 5 赛季的所有比赛数据

V37.0 重构内容:
- L1: 集成 ProductionL1Collector (Pydantic Schema 校验)
- L2: 集成 ProductionL2Collector (工业级弹性架构)
- ID 格式修正: 使用纯数字 match_id（与 L1 一致）
- 批量 Upsert: 每 50 场一次数据库提交
- 数据质量分级: FULL/PARTIAL/WARNING

FotMob League ID 对照:
- 47: Premier League
- 87: La Liga
- 54: Bundesliga
- 53: Ligue 1
- 55: Serie A

作者: ML Architect
版本: V37.0 (Production-Grade)
日期: 2025-12-29
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
from src.api.collectors.production_l2_collector import ProductionL2Collector
from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# 联赛配置 (V36.2 - 修复正确的 FotMob League ID)
# 根据 config/target_leagues.json 官方映射
LEAGUE_CONFIGS = [
    {"id": 47, "name": "Premier League", "code": "PL"},    # ✅ 380 场/赛季
    {"id": 87, "name": "La Liga", "code": "LL"},          # V36.2 修复：从 55 改为 87
    {"id": 54, "name": "Bundesliga", "code": "BL"},       # ✅ 306 场/赛季
    {"id": 53, "name": "Ligue 1", "code": "L1"},           # V36.2 修复：从 61 改为 53
    {"id": 55, "name": "Serie A", "code": "SA"},           # V36.2 修复：从 135 改为 55（意甲）
]

# 赛季配置 (FotMob API 格式)
# V36.1 修复：使用完整格式 (YYYY/YYYY)，aiohttp 会自动 URL 编码为 YYYY%2FYYYY
SEASONS = {
    "20/21": "2020/2021",
    "21/22": "2021/2022",
    "22/23": "2022/2023",
    "23/24": "2023/2024",
    "24/25": "2024/2025",
}


class L1L2Harvester:
    """
    V37.0 L1/L2 采集协调器

    负责协调 L1 采集 (ProductionL1Collector) 和 L2 采集 (ProductionL2Collector)
    """

    def __init__(self, db_pool: asyncpg.Pool, max_l2_concurrency: int = 3):
        """
        初始化采集协调器

        Args:
            db_pool: 数据库连接池
            max_l2_concurrency: L2 采集最大并发数（建议 3）
        """
        self.db_pool = db_pool
        self.max_l2_concurrency = max_l2_concurrency
        self.l1_collector = None  # 将在 __aenter__ 中初始化
        self.l2_collector = None  # 将在 __aenter__ 中初始化
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
        """进入上下文，初始化 ProductionL1Collector 和 ProductionL2Collector"""
        # 初始化 L1 采集器
        self.l1_collector = ProductionL1Collector(
            max_concurrent=5,
            max_requests_per_second=2,  # FotMob 限流保护
        )
        await self.l1_collector.__aenter__()

        # V37.0: 初始化 L2 采集器
        self.l2_collector = ProductionL2Collector(
            db_pool=self.db_pool,
            max_concurrent=self.max_l2_concurrency,
            max_requests_per_second=2,
            timeout=30,
        )
        await self.l2_collector.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，关闭采集器"""
        if self.l1_collector:
            await self.l1_collector.__aexit__(exc_type, exc_val, exc_tb)
        if self.l2_collector:
            await self.l2_collector.__aexit__(exc_type, exc_val, exc_tb)

    async def _save_l1_match_index(self, match: dict[str, Any]) -> bool:
        """
        保存 L1 比赛索引到数据库

        V25.1 Schema 字段映射:
        - match_id → match_id (PRIMARY KEY)
        - league_id → league_id (扩展字段)
        - league_name → league_name
        - season_name → season (显示名称，如 "23/24")
        - home_team → home_team
        - away_team → away_team
        - home_team_id → home_team_id (扩展字段)
        - away_team_id → away_team_id (扩展字段)
        - status → status
        - match_time_utc → match_date
        - home_score → home_score
        - away_score → away_score

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

                # 解析 match_time_utc 为 TIMESTAMP
                match_date = None
                if match.get("match_time_utc"):
                    try:
                        from datetime import datetime
                        # 尝试解析 ISO 格式时间
                        match_date = datetime.fromisoformat(match["match_time_utc"].replace("Z", "+00:00"))
                    except Exception:
                        match_date = None

                # 类型转换：Pydantic 使用 str，数据库使用 INTEGER
                league_id = int(match["league_id"]) if match.get("league_id") else None
                home_team_id = int(match["home_team_id"]) if match.get("home_team_id") else None
                away_team_id = int(match["away_team_id"]) if match.get("away_team_id") else None

                if existing:
                    # 更新现有记录
                    await conn.execute(
                        """
                        UPDATE matches SET
                            league_id = $2,
                            league_name = $3,
                            season = $4,
                            home_team = $5,
                            away_team = $6,
                            home_team_id = $7,
                            away_team_id = $8,
                            status = $9,
                            match_date = $10,
                            home_score = $11,
                            away_score = $12,
                            updated_at = NOW()
                        WHERE match_id = $1
                        """,
                        match["match_id"],
                        league_id,
                        match["league_name"],
                        match["season_name"],  # 使用 season_name 作为 season
                        match["home_team"],
                        match["away_team"],
                        home_team_id,
                        away_team_id,
                        match["status"],
                        match_date,
                        match["home_score"],
                        match["away_score"],
                    )
                else:
                    # 插入新记录
                    await conn.execute(
                        """
                        INSERT INTO matches (
                            match_id, league_id, league_name, season,
                            home_team, away_team, home_team_id, away_team_id,
                            status, match_date, home_score, away_score,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                        """,
                        match["match_id"],
                        league_id,
                        match["league_name"],
                        match["season_name"],  # 使用 season_name 作为 season
                        match["home_team"],
                        match["away_team"],
                        home_team_id,
                        away_team_id,
                        match["status"],
                        match_date,
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
        V37.0: 过滤出需要采集 L2 的新比赛

        Args:
            match_ids: 比赛ID列表（纯数字格式，与 L1 一致）

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


async def full_harvest(l2_limit: int = 10000, silent_mode: bool = True, season_filter: str | None = None):
    """
    V37.0 全量 L1/L2 采集

    Args:
        l2_limit: L2 采集数量限制
        silent_mode: 静默生产模式（减少日志输出）
        season_filter: 赛季过滤器（格式: "2324" 对应 "23/24"），None 表示采集所有赛季
    """
    log_level = logging.WARNING if silent_mode else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    # 创建专用进度日志器（始终输出关键进度）
    progress_logger = logging.getLogger("progress")
    progress_logger.setLevel(logging.INFO)
    progress_logger.addHandler(logging.StreamHandler())
    progress_logger.propagate = False

    # 应用赛季过滤器
    target_seasons = SEASONS.copy()
    if season_filter:
        # V36.1 支持多种格式: "23/24", "2023/2024", "2324"
        if "/" in season_filter:
            # 支持 "23/24" 或 "2023/2024" 格式
            if len(season_filter) == 5:  # "23/24"
                target_seasons = {k: v for k, v in SEASONS.items() if k == season_filter}
            else:  # "2023/2024"
                target_seasons = {k: v for k, v in SEASONS.items() if v == season_filter}
        else:
            # 支持 "2324" 格式（向后兼容）
            # 转换为 "2023/2024" 格式进行匹配
            converted = f"20{season_filter[:2]}/20{season_filter[2:]}" if len(season_filter) == 4 else season_filter
            target_seasons = {k: v for k, v in SEASONS.items() if v == converted}

        if not target_seasons:
            progress_logger.error(f"❌ 赛季 '{season_filter}' 无效！可用赛季: {list(SEASONS.keys())}")
            return None

        progress_logger.info(f"🎯 赛季过滤: {list(target_seasons.keys())}")

    progress_logger.info("=" * 60)
    progress_logger.info("🌍 V37.0 全量 L1/L2 采集 - Production-Grade")
    progress_logger.info(f"📊 目标: {len(LEAGUE_CONFIGS)} 大联赛 × {len(target_seasons)} 赛季")
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
        # V37.0: 增加 L2 并发数到 3
        async with L1L2Harvester(db_pool, max_l2_concurrency=3) as harvester:
            all_matches = []
            total_combinations = len(LEAGUE_CONFIGS) * len(target_seasons)
            completed = 0
            last_progress = 0

            # 步骤 1: L1 采集所有联赛-赛季组合（使用 ProductionL1Collector）
            progress_logger.info("📋 步骤 1: L1 全量采集 (Pydantic 校验)")

            for league in LEAGUE_CONFIGS:
                for season_name, season_code in target_seasons.items():
                    completed += 1
                    progress = int(completed / total_combinations * 100)

                    if progress >= last_progress + 10 or completed == total_combinations:
                        progress_logger.info(f"⏳ L1 进度: {progress}% ({completed}/{total_combinations})")
                        last_progress = progress

                    try:
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

            # 步骤 3: L2 批量采集（V37.0: 使用 ProductionL2Collector）
            progress_logger.info("=" * 60)
            progress_logger.info(f"📊 步骤 3: L2 批量采集 (限制: {l2_limit} 场)")
            progress_logger.info("=" * 60)

            # V37.0: 提取纯数字 match_id（与 L1 一致，不再使用 {id}_{season} 格式）
            match_ids = []
            for m in all_matches[:l2_limit]:
                match_id = m.match_id if hasattr(m, 'match_id') else m.get("match_id")
                if match_id:
                    match_ids.append(str(match_id))

            # 只采集新比赛（过滤已存在的）
            progress_logger.info("🔍 筛选新比赛...")
            new_match_ids = await harvester._filter_new_matches(match_ids)
            progress_logger.info(f"🎯 待采集: {len(new_match_ids)}/{len(match_ids)} 场新比赛")

            if new_match_ids:
                # V37.0: 使用 ProductionL2Collector 批量采集（带进度回调）
                def progress_callback(completed: int, total: int, progress: int):
                    progress_logger.info(f"⏳ L2 进度: {progress}% ({completed}/{total})")

                summary = await harvester.l2_collector.collect_batch(
                    match_ids=new_match_ids,
                    batch_size=50,  # 每 50 场批量 Upsert
                    progress_callback=progress_callback,
                )

                # 更新统计
                harvester.stats["l2_attempted"] = summary.total_attempted
                harvester.stats["l2_success"] = summary.total_success
                harvester.stats["l2_failed"] = summary.total_failed

                # 输出 L2 采集摘要报告
                progress_logger.info("\n" + harvester.l2_collector.get_summary_report())
            else:
                progress_logger.info("ℹ️  无新比赛需要采集")

            progress_logger.info("=" * 60)
            progress_logger.info("🎉 V37.0 全量 L1/L2 采集完成! (Production-Grade)")
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

    parser = argparse.ArgumentParser(
        description="V37.0 全量 L1/L2 采集器 (Production-Grade)",
        epilog=f"""
示例用法:
  python %(prog)s                              # 采集所有赛季
  python %(prog)s --season 23/24               # 仅采集 23/24 赛季
  python %(prog)s --season 23/24 --verbose     # 仅采集 23/24 赛季（详细日志）
  python %(prog)s --l2-limit 100               # L2 仅采集 100 场

可用赛季: {list(SEASONS.keys())}
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--season", type=str, default=None,
                        help="赛季过滤 (格式: '23/24' 或 '2023/2024')，默认采集所有赛季")
    parser.add_argument("--l2-limit", type=int, default=10000, help="L2 采集数量限制 (默认: 10000)")
    parser.add_argument("--verbose", action="store_true", help="启用详细日志输出")

    args = parser.parse_args()

    exit_code = asyncio.run(full_harvest(
        l2_limit=args.l2_limit,
        silent_mode=not args.verbose,
        season_filter=args.season
    ))
    sys.exit(exit_code if exit_code is not None else 0)
