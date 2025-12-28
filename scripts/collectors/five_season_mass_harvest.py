#!/usr/bin/env python3
"""
V36.2 五大联赛五年全量采集器 (Five-Season Mass Harvest)
========================================================

自动化采集 5 大联赛 × 5 赛季的全部历史数据

目标:
- 5 大联赛: Premier League, La Liga, Bundesliga, Ligue 1, Serie A
- 5 赛季: 2020/2021, 2021/2022, 2022/2023, 2023/2024, 2024/2025
- 预期总量: 9000+ 场比赛

作者: ML Architect
版本: V36.2 (Five-Season Edition)
日期: 2025-12-29
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.production_l1_collector import ProductionL1Collector
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

# 赛季配置 (V36.1 修复后的格式)
SEASONS = [
    {"display": "20/21", "api": "2020/2021"},
    {"display": "21/22", "api": "2021/2022"},
    {"display": "22/23", "api": "2022/2023"},
    {"display": "23/24", "api": "2023/2024"},
    {"display": "24/25", "api": "2024/2025"},
]


class FiveSeasonHarvester:
    """V36.2 五赛季全量采集器"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.l1_collector = None
        self.stats = {
            "total_combinations": len(LEAGUE_CONFIGS) * len(SEASONS),
            "completed": 0,
            "total_matches": 0,
            "total_saved": 0,
            "by_season": {},
        }

    async def __aenter__(self):
        self.l1_collector = ProductionL1Collector(
            max_concurrent=5,
            max_requests_per_second=2,
        )
        await self.l1_collector.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.l1_collector:
            await self.l1_collector.__aexit__(exc_type, exc_val, exc_tb)

    async def _save_l1_match_index(self, match: dict[str, Any]) -> bool:
        """保存 L1 比赛索引到数据库"""
        try:
            async with self.db_pool.acquire() as conn:
                # 检查是否已存在
                existing = await conn.fetchval(
                    "SELECT match_id FROM matches WHERE match_id = $1",
                    match["match_id"]
                )

                # 解析 match_time_utc
                match_date = None
                if match.get("match_time_utc"):
                    try:
                        match_date = datetime.fromisoformat(match["match_time_utc"].replace("Z", "+00:00"))
                    except Exception:
                        pass

                # 类型转换
                league_id = int(match["league_id"]) if match.get("league_id") else None
                home_team_id = int(match["home_team_id"]) if match.get("home_team_id") else None
                away_team_id = int(match["away_team_id"]) if match.get("away_team_id") else None

                if existing:
                    await conn.execute(
                        """
                        UPDATE matches SET
                            league_id = $2, league_name = $3, season = $4,
                            home_team = $5, away_team = $6,
                            home_team_id = $7, away_team_id = $8,
                            status = $9, match_date = $10,
                            home_score = $11, away_score = $12,
                            updated_at = NOW()
                        WHERE match_id = $1
                        """,
                        match["match_id"], league_id, match["league_name"],
                        match["season_name"], match["home_team"], match["away_team"],
                        home_team_id, away_team_id, match["status"],
                        match_date, match["home_score"], match["away_score"],
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO matches (
                            match_id, league_id, league_name, season,
                            home_team, away_team, home_team_id, away_team_id,
                            status, match_date, home_score, away_score,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                        """,
                        match["match_id"], league_id, match["league_name"],
                        match["season_name"], match["home_team"], match["away_team"],
                        home_team_id, away_team_id, match["status"],
                        match_date, match["home_score"], match["away_score"],
                    )

                return True
        except Exception as e:
            logger.error(f"❌ L1保存失败 {match.get('match_id', 'unknown')}: {e}")
            return False

    async def save_all_l1_matches(self, matches: list[Any], season_display: str) -> int:
        """保存所有 L1 比赛到数据库"""
        saved_count = 0
        for match in matches:
            match_dict = match.to_dict() if hasattr(match, 'to_dict') else match
            if await self._save_l1_match_index(match_dict):
                saved_count += 1
        return saved_count

    async def harvest_season(self, season_display: str, season_api: str) -> dict:
        """采集单个赛季的所有联赛"""
        season_stats = {
            "season": season_display,
            "matches_collected": 0,
            "matches_saved": 0,
            "by_league": {},
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 开始采集: {season_display} 赛季")
        logger.info(f"{'='*60}")

        for league in LEAGUE_CONFIGS:
            self.stats["completed"] += 1
            progress = int(self.stats["completed"] / self.stats["total_combinations"] * 100)
            logger.info(f"⏳ 总进度: {progress}% ({self.stats['completed']}/{self.stats['total_combinations']})")

            try:
                matches = await self.l1_collector.collect_league_season(
                    league_id=league["id"],
                    season_code=season_api,
                    season_name=season_display,
                )

                saved = await self.save_all_l1_matches(matches, season_display)

                season_stats["matches_collected"] += len(matches)
                season_stats["matches_saved"] += saved
                season_stats["by_league"][league["name"]] = len(matches)

                logger.info(f"✅ {league['name']} {season_display}: {len(matches)} 场")

            except Exception as e:
                logger.error(f"❌ {league['name']} {season_display} 失败: {e}")
                season_stats["by_league"][league["name"]] = 0

        self.stats["total_matches"] += season_stats["matches_collected"]
        self.stats["total_saved"] += season_stats["matches_saved"]
        self.stats["by_season"][season_display] = season_stats

        return season_stats

    async def generate_audit_report(self) -> str:
        """生成数据资产审计报告"""
        report = []
        report.append("\n")
        report.append("╔" + "═"*78 + "╗")
        report.append("║" + " "*20 + "五大联赛五年数据资产审计表" + " "*22 + "║")
        report.append("╠" + "═"*78 + "╣")
        report.append("║" + " "*5 + "赛季" + " "*8 + "| PL  | LL  | BL  | L1  | SA  |  小计" + " "*18 + "║")
        report.append("╠" + "═"*78 + "╣")

        total_all = 0
        for season in SEASONS:
            disp = season["display"]
            stats = self.stats["by_season"].get(disp, {})
            by_league = stats.get("by_league", {})

            pl = by_league.get("Premier League", 0)
            ll = by_league.get("La Liga", 0)
            bl = by_league.get("Bundesliga", 0)
            l1 = by_league.get("Ligue 1", 0)
            sa = by_league.get("Serie A", 0)
            subtotal = stats.get("matches_collected", 0)
            total_all += subtotal

            report.append(f"║  {disp:<14} | {pl:>4} | {ll:>4} | {bl:>4} | {l1:>4} | {sa:>4} | {subtotal:>6}" + " "*24 + "║")

        report.append("╠" + "═"*78 + "╣")
        report.append(f"║  {'总计':<14} | {'':>4} | {'':>4} | {'':>4} | {'':>4} | {'':>4} | {total_all:>6}" + " "*24 + "║")
        report.append("╚" + "═"*78 + "╝")
        report.append("")
        report.append("📊 注: PL=Premier League, LL=La Liga, BL=Bundesliga, L1=Ligue 1, SA=Serie A")
        report.append("⚠️  Serie A 数据受 FotMob API 限制，部分赛季可能不足 380 场")

        return "\n".join(report)


async def five_season_harvest():
    """五年全量采集主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    progress_logger = logging.getLogger("progress")
    progress_logger.setLevel(logging.INFO)
    progress_logger.addHandler(logging.StreamHandler())
    progress_logger.propagate = False

    progress_logger.info("="*60)
    progress_logger.info("🌍 V36.2 五大联赛五年全量采集")
    progress_logger.info(f"📊 目标: {len(LEAGUE_CONFIGS)} 大联赛 × {len(SEASONS)} 赛季")
    progress_logger.info("="*60)

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
        async with FiveSeasonHarvester(db_pool) as harvester:
            # 逐赛季采集
            for season in SEASONS:
                await harvester.harvest_season(season["display"], season["api"])

            # 生成审计报告
            progress_logger.info("\n" + await harvester.generate_audit_report())

            # 输出 L1 采集器摘要
            progress_logger.info("\n" + harvester.l1_collector.get_summary_report())

            return harvester.stats

    finally:
        await db_pool.close()


if __name__ == "__main__":
    exit_code = asyncio.run(five_season_harvest())
    sys.exit(0 if exit_code else 1)
