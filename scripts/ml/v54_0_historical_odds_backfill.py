#!/usr/bin/env python3
"""
V54.0 全量历史赔率回填引擎
===========================

功能:
1. 五大联赛 2020-2025 历史赔率回填
2. 增量采集 - 仅抓取缺失赔率的比赛
3. 分批次处理 - 每批 100 场
4. 优先级排序 - 2024/25 赛季优先
5. 双向特征 - Opening + Closing + Drift
6. 严格校验 - 1.02 < Margin < 1.08

Author: Chief Data Engineer
Version: V54.0
Date: 2026-01-01
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.collectors.odds_scraper_playwright import OddsPortalScraper, OddsMatch
from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# V54.0 赛季配置
# ============================================================

@dataclass
class SeasonConfig:
    """赛季配置"""
    league_name: str
    league_path: str
    seasons: list[tuple[str, str]]  # (start_year, end_year)


# 五大联赛赛季配置
SEASON_CONFIGS = [
    SeasonConfig(
        league_name="Premier League",
        league_path="england/premier-league",
        seasons=[
            ("2024", "2025"),
            ("2023", "2024"),
            ("2022", "2023"),
            ("2021", "2022"),
            ("2020", "2021"),
        ]
    ),
    SeasonConfig(
        league_name="La Liga",
        league_path="spain/la-liga",
        seasons=[
            ("2024", "2025"),
            ("2023", "2024"),
            ("2022", "2023"),
            ("2021", "2022"),
            ("2020", "2021"),
        ]
    ),
    SeasonConfig(
        league_name="Bundesliga",
        league_path="germany/bundesliga",
        seasons=[
            ("2024", "2025"),
            ("2023", "2024"),
            ("2022", "2023"),
            ("2021", "2022"),
            ("2020", "2021"),
        ]
    ),
    SeasonConfig(
        league_name="Serie A",
        league_path="italy/serie-a",
        seasons=[
            ("2024", "2025"),
            ("2023", "2024"),
            ("2022", "2023"),
            ("2021", "2022"),
            ("2020", "2021"),
        ]
    ),
    SeasonConfig(
        league_name="Ligue 1",
        league_path="france/ligue-1",
        seasons=[
            ("2024", "2025"),
            ("2023", "2024"),
            ("2022", "2023"),
            ("2021", "2022"),
            ("2020", "2021"),
        ]
    ),
]


# ============================================================
# V54.0 回填引擎
# ============================================================

class V54HistoricalBackfillEngine:
    """V54.0 历史赔率回填引擎"""

    BATCH_SIZE = 100  # 每批处理 100 场

    def __init__(self):
        self.settings = get_settings()
        self.scraper = None

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def get_missing_matches(
        self,
        league_name: str,
        start_date: str,
        end_date: str,
        limit: int | None = None
    ) -> list[dict]:
        """
        获取缺失赔率的比赛列表

        Args:
            league_name: 联赛名称
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量（用于分批）

        Returns:
            缺失赔率的比赛列表
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT
                m.match_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date
            FROM matches m
            LEFT JOIN prematch_features pf ON m.match_id = pf.match_id
            WHERE m.league_name = %s
              AND m.match_date >= %s
              AND m.match_date <= %s
              AND pf.closing_home_odds IS NULL
            ORDER BY m.match_date DESC
            {limit_clause}
        """

        cursor.execute(query, (league_name, start_date, end_date))
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    def count_missing_matches(
        self,
        league_name: str,
        start_date: str,
        end_date: str
    ) -> int:
        """统计缺失赔率的比赛数量"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM matches m
            LEFT JOIN prematch_features pf ON m.match_id = pf.match_id
            WHERE m.league_name = %s
              AND m.match_date >= %s
              AND m.match_date <= %s
              AND pf.closing_home_odds IS NULL
        """, (league_name, start_date, end_date))

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result["count"] if result else 0

    async def process_batch(
        self,
        matches: list[dict],
        batch_num: int,
        total_batches: int
    ) -> dict:
        """
        处理一批比赛

        Args:
            matches: 比赛列表
            batch_num: 批次号
            total_batches: 总批次数

        Returns:
            处理统计
        """
        stats = {
            "batch_num": batch_num,
            "total_matches": len(matches),
            "success": 0,
            "failed": 0,
            "with_opening": 0,
        }

        logger.info(f"")
        logger.info(f"【批次 {batch_num}/{total_batches}】")
        logger.info(f"目标: {stats['total_matches']} 场比赛")

        for i, match in enumerate(matches, 1):
            match_info = {
                "match_id": match["match_id"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "league_name": match["league_name"],
                "match_date": match["match_date"],
            }

            odds_match = await self.scraper.fetch_match_odds_from_oddsportal(match_info)

            if odds_match and odds_match.is_valid:
                # 保存到数据库
                saved_stats = self.scraper.save_odds_to_prematch_features([odds_match])

                if saved_stats.get("saved", 0) > 0:
                    stats["success"] += 1

                    # 检查是否有初盘
                    if all([
                        odds_match.opening_home_odds,
                        odds_match.opening_draw_odds,
                        odds_match.opening_away_odds
                    ]):
                        stats["with_opening"] += 1
                else:
                    stats["failed"] += 1
            else:
                stats["failed"] += 1

            # 进度报告
            if i % 10 == 0:
                logger.info(f"  进度: {i}/{len(matches)}")

            # 批内延迟
            if i < len(matches):
                await asyncio.sleep(0.5)

        return stats

    async def backfill_season(
        self,
        config: SeasonConfig,
        start_year: str,
        end_year: str
    ) -> dict:
        """
        回填单个赛季

        Args:
            config: 赛季配置
            start_year: 开始年份
            end_year: 结束年份

        Returns:
            回填统计
        """
        season_key = f"{start_year}/{end_year}"
        start_date = f"{start_year}-07-01"  # 赛季通常在 7-8 月开始
        end_date = f"{end_year}-06-30"

        # 统计缺失数量
        missing_count = self.count_missing_matches(
            config.league_name,
            start_date,
            end_date
        )

        if missing_count == 0:
            logger.info(f"[✓] {config.league_name} {season_key}: 无缺失数据")
            return {
                "league": config.league_name,
                "season": season_key,
                "total": 0,
                "success": 0,
            }

        logger.info(f"")
        logger.info(f"【{config.league_name} {season_key}】")
        logger.info(f"缺失赔率: {missing_count} 场")

        # 计算批次数
        total_batches = (missing_count + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        stats = {
            "league": config.league_name,
            "season": season_key,
            "total": missing_count,
            "success": 0,
            "failed": 0,
            "with_opening": 0,
        }

        # 分批处理
        for batch_num in range(1, total_batches + 1):
            # 获取本批数据
            matches = self.get_missing_matches(
                config.league_name,
                start_date,
                end_date,
                limit=self.BATCH_SIZE
            )

            if not matches:
                break

            # 处理批次
            batch_stats = await self.process_batch(matches, batch_num, total_batches)

            stats["success"] += batch_stats["success"]
            stats["failed"] += batch_stats["failed"]
            stats["with_opening"] += batch_stats["with_opening"]

            # 批间延迟
            if batch_num < total_batches:
                await asyncio.sleep(2)

        return stats

    async def run_full_backfill(self) -> dict:
        """
        运行全量回填

        Returns:
            总体统计
        """
        logger.info("=" * 60)
        logger.info("【V54.0 历史赔率回填引擎】")
        logger.info("=" * 60)
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        # 启动采集器
        self.scraper = OddsPortalScraper(headless=True)
        await self.scraper.start()

        # 加载球队映射
        self.scraper.load_team_mapping()

        all_stats = []
        grand_total = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "with_opening": 0,
        }

        # 按优先级遍历所有联赛和赛季
        for config in SEASON_CONFIGS:
            for start_year, end_year in config.seasons:
                try:
                    season_stats = await self.backfill_season(config, start_year, end_year)
                    all_stats.append(season_stats)

                    grand_total["total"] += season_stats["total"]
                    grand_total["success"] += season_stats.get("success", 0)
                    grand_total["failed"] += season_stats.get("failed", 0)
                    grand_total["with_opening"] += season_stats.get("with_opening", 0)

                except Exception as e:
                    logger.error(f"赛季回填失败 [{config.league_name} {start_year}/{end_year}]: {e}")

        # 关闭采集器
        await self.scraper.close()

        return {
            "seasons": all_stats,
            "grand_total": grand_total,
        }


# ============================================================
# 主函数
# ============================================================

async def main():
    """主函数"""
    engine = V54HistoricalBackfillEngine()

    result = await engine.run_full_backfill()

    # 输出审计报告
    print()
    print("=" * 60)
    print("【V54.0 回填审计报告】")
    print("=" * 60)
    print()

    for stats in result["seasons"]:
        if stats["total"] > 0:
            print(f"{stats['league']} {stats['season']}:")
            print(f"  目标: {stats['total']} 场")
            print(f"  成功: {stats.get('success', 0)} 场")
            print(f"  失败: {stats.get('failed', 0)} 场")
            print(f"  双向特征: {stats.get('with_opening', 0)} 场")
            print()

    gt = result["grand_total"]
    print("=" * 60)
    print("【总计统计】")
    print("=" * 60)
    print(f"目标总场次: {gt['total']}")
    print(f"成功采集: {gt['success']} ({gt['success']/gt['total']*100 if gt['total'] > 0 else 0:.1f}%)")
    print(f"采集失败: {gt['failed']}")
    print(f"双向特征: {gt['with_opening']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
