#!/usr/bin/env python3
"""V41.600 Target Scanner - 目标扫描器

扫描数据库，筛选出所有缺少【初盘+变盘历史】的五大联赛历史比赛 ID。

Usage:
    python scripts/ops/v41_600_target_scanner.py [--league "Premier League"] [--season 2024-2025]

Author: V41.600 Global Harvest Team
Date: 2026-01-21
"""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 五大联赛
BIG_FIVE_LEAGUES = [
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
]

# 目标博彩公司
TARGET_BOOKMAKERS = [
    "Entity_P",  # Pinnacle
    "Entity_WH", # William Hill
    "Entity_LB", # Ladbrokes
    "Entity_B3", # Bet365
]


@dataclass
class MatchTarget:
    """收割目标"""
    match_id: str
    league_name: str
    season: str
    home_team: str
    away_team: str
    match_date: str
    missing_reason: str  # "no_odds", "no_initial", "no_movement", "incomplete"
    existing_bookmakers: list[str] = field(default_factory=list)
    priority: int = 0  # 0=high, 1=medium, 2=low


@dataclass
class ScanReport:
    """扫描报告"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_matches_scanned: int = 0
    targets_found: int = 0
    by_league: dict[str, int] = field(default_factory=dict)
    by_season: dict[str, int] = field(default_factory=dict)
    by_reason: dict[str, int] = field(default_factory=dict)
    targets: list[MatchTarget] = field(default_factory=list)


class TargetScanner:
    """V41.600: 目标扫描器

    扫描数据库，找出需要收割的比赛。
    """

    def __init__(
        self,
        leagues: list[str] | None = None,
        seasons: list[str] | None = None,
        target_bookmakers: list[str] | None = None
    ):
        """初始化扫描器

        Args:
            leagues: 目标联赛列表
            seasons: 目标赛季列表
            target_bookmakers: 目标博彩公司列表
        """
        self.leagues = leagues or BIG_FIVE_LEAGUES
        self.seasons = seasons
        self.target_bookmakers = target_bookmakers or TARGET_BOOKMAKERS

        # 数据库连接
        settings = get_settings()
        self.db_config = settings.database

        self.report = ScanReport()

    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.db_config.host,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value(),
            cursor_factory=RealDictCursor
        )

    def scan_missing_odds(self) -> list[MatchTarget]:
        """扫描缺失赔率的比赛

        Returns:
            目标比赛列表
        """
        targets = []

        logger.info(f"\n{'='*70}")
        logger.info("V41.600 TARGET SCANNER")
        logger.info(f"{'='*70}")
        logger.info(f"目标联赛: {', '.join(self.leagues)}")
        if self.seasons:
            logger.info(f"目标赛季: {', '.join(self.seasons)}")
        logger.info(f"目标博彩公司: {', '.join(self.target_bookmakers)}")
        logger.info(f"{'='*70}\n")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 构建查询
                league_filter = ",".join(f"'{l}'" for l in self.leagues)
                season_filter = ""
                if self.seasons:
                    season_list = ",".join(f"'{s}'" for s in self.seasons)
                    season_filter = f"AND m.season IN ({season_list})"

                # 查询: 找出有 match 但没有或赔率数据不完整的比赛
                query = f"""
                SELECT
                    m.match_id,
                    m.league_name,
                    m.season,
                    m.home_team,
                    m.away_team,
                    m.match_date::text as match_date,
                    COUNT(DISTINCT msd.source_name) as bookmaker_count,
                    COUNT(CASE WHEN msd.init_h IS NOT NULL THEN 1 END) as has_initial_count,
                    COUNT(CASE WHEN msd.opening_time_h IS NOT NULL THEN 1 END) as has_movement_count,
                    STRING_AGG(DISTINCT msd.source_name, ', ') as bookmakers
                FROM matches m
                LEFT JOIN metrics_multi_source_data msd
                    ON m.match_id = msd.match_id
                    AND msd.source_name IN ({','.join(f"'{b}'" for b in self.target_bookmakers)})
                WHERE m.league_name IN ({league_filter})
                    {season_filter}
                    AND m.is_finished = true
                GROUP BY m.match_id, m.league_name, m.season, m.home_team, m.away_team, m.match_date
                HAVING COUNT(msd.source_name) < {len(self.target_bookmakers)}
                    OR COUNT(CASE WHEN msd.init_h IS NOT NULL THEN 1 END) = 0
                    OR COUNT(CASE WHEN msd.opening_time_h IS NOT NULL THEN 1 END) = 0
                ORDER BY m.match_date DESC, m.league_name, m.season;
                """

                logger.info("执行查询...")
                cur.execute(query)

                for row in cur:
                    match_id = row["match_id"]
                    league = row["league_name"]
                    season = row["season"]

                    # 判断缺失原因
                    bookmaker_count = row["bookmaker_count"] or 0
                    has_initial = row["has_initial_count"] or 0
                    has_movement = row["has_movement_count"] or 0
                    existing_bookmakers = row["bookmakers"].split(", ") if row["bookmakers"] else []

                    missing_reason = "incomplete"
                    if bookmaker_count == 0:
                        missing_reason = "no_odds"
                    elif has_initial == 0:
                        missing_reason = "no_initial"
                    elif has_movement == 0:
                        missing_reason = "no_movement"

                    # 优先级: 完全没有数据 > 没有初盘 > 没有变盘 > 不完整
                    priority = 0 if missing_reason == "no_odds" else 1 if missing_reason == "no_initial" else 2

                    target = MatchTarget(
                        match_id=match_id,
                        league_name=league,
                        season=season,
                        home_team=row["home_team"],
                        away_team=row["away_team"],
                        match_date=row["match_date"],
                        missing_reason=missing_reason,
                        existing_bookmakers=existing_bookmakers,
                        priority=priority
                    )
                    targets.append(target)

        self.report.total_matches_scanned = len(targets)
        self.report.targets = targets

        # 统计
        for t in targets:
            self.report.by_league[t.league_name] = self.report.by_league.get(t.league_name, 0) + 1
            self.report.by_season[t.season] = self.report.by_season.get(t.season, 0) + 1
            self.report.by_reason[t.missing_reason] = self.report.by_reason.get(t.missing_reason, 0) + 1

        self.report.targets_found = len(targets)

        return targets

    def print_report(self):
        """打印扫描报告"""
        report = self.report

        print(f"\n{'='*70}")
        print(f"V41.600 TARGET SCAN REPORT")
        print(f"{'='*70}")
        print(f"扫描时间: {report.timestamp}")
        print(f"\n📊 执行摘要:")
        print(f"  目标比赛数: {report.targets_found}")
        print(f"  目标联赛: {len(report.by_league)}")
        print(f"  目标赛季: {len(report.by_season)}")

        print(f"\n🏆 按联赛统计:")
        for league, count in sorted(report.by_league.items(), key=lambda x: -x[1]):
            print(f"  {league:20} {count:6} 场")

        print(f"\n📅 按赛季统计:")
        for season, count in sorted(report.by_season.items(), reverse=True):
            print(f"  {season:15} {count:6} 场")

        print(f"\n🔍 按缺失原因统计:")
        reason_map = {
            "no_odds": "完全无数据",
            "no_initial": "缺初盘",
            "no_movement": "缺变盘历史",
            "incomplete": "数据不完整"
        }
        for reason, count in sorted(report.by_reason.items(), key=lambda x: -x[1]):
            print(f"  {reason_map.get(reason, reason):15} {count:6} 场")

        # 示例目标
        if report.targets:
            print(f"\n🎯 示例目标 (前 10 个):")
            for i, t in enumerate(report.targets[:10], 1):
                existing = f" [{','.join(t.existing_bookmakers)}]" if t.existing_bookmakers else ""
                print(f"  {i:2}. {t.match_id:20} | {t.league_name:20} | {t.season:10} | {t.home_team} vs {t.away_team}")

        print(f"\n{'='*70}\n")

    def save_targets(self, output_file: str = "data/v41_600_targets.json"):
        """保存目标列表到文件

        Args:
            output_file: 输出文件路径
        """
        import json

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": self.report.timestamp,
            "total_targets": len(self.report.targets),
            "by_league": self.report.by_league,
            "by_season": self.report.by_season,
            "by_reason": self.report.by_reason,
            "targets": [
                {
                    "match_id": t.match_id,
                    "league_name": t.league_name,
                    "season": t.season,
                    "home_team": t.home_team,
                    "away_team": t.away_team,
                    "match_date": t.match_date,
                    "missing_reason": t.missing_reason,
                    "existing_bookmakers": t.existing_bookmakers,
                    "priority": t.priority,
                }
                for t in self.report.targets
            ]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"目标列表已保存: {output_file}")


def main():
    """主函数"""
    parser = ArgumentParser(description="V41.600 Target Scanner")
    parser.add_argument(
        "--league",
        type=str,
        action="append",
        help="目标联赛 (可多次指定，默认五大联赛)"
    )
    parser.add_argument(
        "--season",
        type=str,
        action="append",
        help="目标赛季 (可多次指定，默认全部)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/v41_600_targets.json",
        help="输出文件路径"
    )

    args = parser.parse_args()

    # 创建扫描器
    scanner = TargetScanner(
        leagues=args.league,
        seasons=args.season
    )

    # 执行扫描
    scanner.scan_missing_odds()

    # 打印报告
    scanner.print_report()

    # 保存目标列表
    scanner.save_targets(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
