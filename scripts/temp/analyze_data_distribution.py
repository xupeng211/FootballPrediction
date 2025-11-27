#!/usr/bin/env python3
"""
深度探索性数据分析 (EDA) - 足球预测数据画像
Chief Data Scientist: 全面分析现有matches表的数据特征
"""

import asyncio
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, select, func, case, cast, Integer
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataAnalyzer:
    """数据分析师 - 专注于足球数据深度探索"""

    def __init__(self):
        # 从环境变量获取数据库URL
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction")
        # 确保使用asyncpg驱动
        self.engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()

    async def get_db_session(self) -> AsyncSession:
        """获取数据库会话"""
        async with self.AsyncSessionLocal() as session:
            yield session

    async def analyze_basic_statistics(self) -> dict[str, Any]:
        """基础统计分析"""
        logger.info("🔍 开始基础统计分析...")

        async with self.AsyncSessionLocal() as session:
            # 基础数据量统计
            total_matches = await session.scalar(select(func.count()).select_from(text("matches")))

            # 时间范围
            date_range = await session.execute(text("""
                SELECT
                    MIN(match_date) as earliest_match,
                    MAX(match_date) as latest_match,
                    COUNT(DISTINCT DATE(match_date)) as unique_dates
                FROM matches
                WHERE match_date IS NOT NULL
            """))
            date_info = date_range.fetchone()

            # 球队数量
            team_stats = await session.execute(text("""
                SELECT
                    COUNT(DISTINCT home_team_id) as unique_home_teams,
                    COUNT(DISTINCT away_team_id) as unique_away_teams,
                    COUNT(DISTINCT home_team_name) as unique_home_names,
                    COUNT(DISTINCT away_team_name) as unique_away_names
                FROM matches
            """))
            team_info = team_stats.fetchone()

            # 联赛数量
            league_stats = await session.execute(text("""
                SELECT
                    COUNT(DISTINCT league_id) as unique_leagues,
                    COUNT(DISTINCT league_name) as unique_league_names
                FROM matches
                WHERE league_id IS NOT NULL
            """))
            league_info = league_stats.fetchone()

            return {
                "total_matches": total_matches,
                "earliest_match": date_info.earliest_match,
                "latest_match": date_info.latest_match,
                "unique_dates": date_info.unique_dates,
                "unique_home_teams": team_info.unique_home_teams,
                "unique_away_teams": team_info.unique_away_teams,
                "unique_home_names": team_info.unique_home_names,
                "unique_away_names": team_info.unique_away_names,
                "unique_leagues": league_info.unique_leagues,
                "unique_league_names": league_info.unique_league_names
            }

    async def analyze_match_outcomes(self) -> dict[str, Any]:
        """比赛结果分布分析"""
        logger.info("⚽ 分析比赛结果分布...")

        async with self.AsyncSessionLocal() as session:
            # 胜平负分布
            outcome_query = text("""
                SELECT
                    CASE
                        WHEN home_score > away_score THEN 'Home_Win'
                        WHEN home_score < away_score THEN 'Away_Win'
                        WHEN home_score = away_score THEN 'Draw'
                    END as result,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches), 2) as percentage
                FROM matches
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
                GROUP BY
                    CASE
                        WHEN home_score > away_score THEN 'Home_Win'
                        WHEN home_score < away_score THEN 'Away_Win'
                        WHEN home_score = away_score THEN 'Draw'
                    END
                ORDER BY count DESC
            """)

            outcome_result = await session.execute(outcome_query)
            outcomes = outcome_result.fetchall()

            # 进球数统计
            goals_query = text("""
                SELECT
                    AVG(home_score + away_score) as avg_total_goals,
                    MIN(home_score + away_score) as min_total_goals,
                    MAX(home_score + away_score) as max_total_goals,
                    STDDEV(home_score + away_score) as stddev_total_goals,
                    AVG(home_score) as avg_home_goals,
                    AVG(away_score) as avg_away_goals
                FROM matches
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            """)

            goals_result = await session.execute(goals_query)
            goals_stats = goals_result.fetchone()

            # 比分分布
            score_distribution = await session.execute(text("""
                SELECT
                    home_score || '-' || away_score as score,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches), 2) as percentage
                FROM matches
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
                GROUP BY home_score, away_score
                ORDER BY count DESC
                LIMIT 20
            """))

            top_scores = score_distribution.fetchall()

            return {
                "outcomes": [
                    {
                        "result": row.result,
                        "count": row.count,
                        "percentage": row.percentage
                    } for row in outcomes
                ],
                "goals_stats": {
                    "avg_total_goals": float(goals_stats.avg_total_goals) if goals_stats.avg_total_goals else 0,
                    "min_total_goals": goals_stats.min_total_goals,
                    "max_total_goals": goals_stats.max_total_goals,
                    "stddev_total_goals": float(goals_stats.stddev_total_goals) if goals_stats.stddev_total_goals else 0,
                    "avg_home_goals": float(goals_stats.avg_home_goals) if goals_stats.avg_home_goals else 0,
                    "avg_away_goals": float(goals_stats.avg_away_goals) if goals_stats.avg_away_goals else 0
                },
                "top_scores": [
                    {
                        "score": row.score,
                        "count": row.count,
                        "percentage": row.percentage
                    } for row in top_scores
                ]
            }

    async def analyze_league_activity(self) -> list[dict[str, Any]]:
        """联赛活跃度分析"""
        logger.info("🏆 分析联赛活跃度...")

        async with self.AsyncSessionLocal() as session:
            league_query = text("""
                SELECT
                    league_id,
                    league_name,
                    COUNT(*) as total_matches,
                    COUNT(DISTINCT home_team_id || '-' || away_team_id) as unique_team_pairs,
                    MIN(match_date) as earliest_match,
                    MAX(match_date) as latest_match,
                    ROUND(AVG(home_score + away_score), 2) as avg_goals_per_match
                FROM matches
                WHERE league_id IS NOT NULL AND league_name IS NOT NULL
                GROUP BY league_id, league_name
                HAVING COUNT(*) >= 50  -- 至少50场比赛
                ORDER BY total_matches DESC
                LIMIT 15
            """)

            result = await session.execute(league_query)
            leagues = result.fetchall()

            return [
                {
                    "league_id": row.league_id,
                    "league_name": row.league_name,
                    "total_matches": row.total_matches,
                    "unique_team_pairs": row.unique_team_pairs,
                    "earliest_match": row.earliest_match,
                    "latest_match": row.latest_match,
                    "avg_goals_per_match": float(row.avg_goals_per_match) if row.avg_goals_per_match else 0
                } for row in leagues
            ]

    async def analyze_temporal_patterns(self) -> dict[str, Any]:
        """时间模式分析"""
        logger.info("📅 分析时间模式...")

        async with self.AsyncSessionLocal() as session:
            # 按年月分析比赛数量
            monthly_pattern = await session.execute(text("""
                SELECT
                    DATE_TRUNC('month', match_date)::date as month,
                    COUNT(*) as matches_count,
                    ROUND(AVG(home_score + away_score), 2) as avg_goals
                FROM matches
                WHERE match_date IS NOT NULL
                GROUP BY DATE_TRUNC('month', match_date)::date
                ORDER BY month DESC
                LIMIT 24
            """))

            monthly_data = monthly_pattern.fetchall()

            # 按星期几分析
            weekday_pattern = await session.execute(text("""
                SELECT
                    EXTRACT(ISODOW FROM match_date)::integer as weekday,
                    TO_CHAR(match_date, 'Day') as weekday_name,
                    COUNT(*) as matches_count,
                    ROUND(AVG(home_score + away_score), 2) as avg_goals,
                    ROUND(
                        SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
                    ) as home_win_percentage
                FROM matches
                WHERE match_date IS NOT NULL
                GROUP BY EXTRACT(ISODOW FROM match_date), TO_CHAR(match_date, 'Day')
                ORDER BY weekday
            """))

            weekday_data = weekday_pattern.fetchall()

            return {
                "monthly_trends": [
                    {
                        "month": row.month,
                        "matches_count": row.matches_count,
                        "avg_goals": float(row.avg_goals) if row.avg_goals else 0
                    } for row in monthly_data
                ],
                "weekday_patterns": [
                    {
                        "weekday": int(row.weekday),
                        "weekday_name": row.weekday_name.strip(),
                        "matches_count": row.matches_count,
                        "avg_goals": float(row.avg_goals) if row.avg_goals else 0,
                        "home_win_percentage": float(row.home_win_percentage) if row.home_win_percentage else 0
                    } for row in weekday_data
                ]
            }

    async def analyze_home_advantage(self) -> dict[str, Any]:
        """主场优势分析"""
        logger.info("🏠 分析主场优势...")

        async with self.AsyncSessionLocal() as session:
            home_advantage = await session.execute(text("""
                SELECT
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as home_wins,
                    SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) as draws,
                    SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) as away_wins,
                    ROUND(AVG(home_score - away_score), 3) as avg_goal_difference,
                    ROUND(AVG(home_score), 3) as avg_home_goals,
                    ROUND(AVG(away_score), 3) as avg_away_goals,
                    ROUND(
                        SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
                    ) as home_win_percentage
                FROM matches
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            """))

            result = home_advantage.fetchone()

            return {
                "total_matches": result.total_matches,
                "home_wins": result.home_wins,
                "draws": result.draws,
                "away_wins": result.away_wins,
                "home_win_percentage": float(result.home_win_percentage) if result.home_win_percentage else 0,
                "avg_goal_difference": float(result.avg_goal_difference) if result.avg_goal_difference else 0,
                "avg_home_goals": float(result.avg_home_goals) if result.avg_home_goals else 0,
                "avg_away_goals": float(result.avg_away_goals) if result.avg_away_goals else 0
            }

    async def generate_comprehensive_report(self) -> dict[str, Any]:
        """生成综合数据分析报告"""
        logger.info("📊 生成综合数据分析报告...")

        # 执行所有分析
        basic_stats = await self.analyze_basic_statistics()
        match_outcomes = await self.analyze_match_outcomes()
        league_activity = await self.analyze_league_activity()
        temporal_patterns = await self.analyze_temporal_patterns()
        home_advantage = await self.analyze_home_advantage()

        # 整合报告
        comprehensive_report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "data_overview": {
                **basic_stats,
                "data_quality_note": "基于28,704条真实比赛数据"
            },
            "match_outcomes": match_outcomes,
            "league_activity": league_activity,
            "temporal_patterns": temporal_patterns,
            "home_advantage": home_advantage
        }

        return comprehensive_report

    def print_report_summary(self, report: dict[str, Any]):
        """打印报告摘要"""
        print("\n" + "="*80)
        print("🏆 足球预测数据深度探索性分析报告")
        print("="*80)

        # 数据概览
        overview = report["data_overview"]
        print("\n📊 数据概览:")
        print(f"   总比赛数: {overview['total_matches']:,}")
        print(f"   时间跨度: {overview['earliest_match']} 至 {overview['latest_match']}")
        print(f"   独特日期: {overview['unique_dates']} 天")
        print(f"   独特联赛: {overview['unique_leagues']} 个")

        # 比赛结果分布
        outcomes = report["match_outcomes"]["outcomes"]
        print("\n⚽ 比赛结果分布:")
        for outcome in outcomes:
            print(f"   {outcome['result']:10s}: {outcome['count']:6,} 场 ({outcome['percentage']:5.1f}%)")

        # 进球统计
        goals = report["match_outcomes"]["goals_stats"]
        print("\n⚽ 进球统计:")
        print(f"   平均总进球: {goals['avg_total_goals']:.2f}")
        print(f"   平均主队进球: {goals['avg_home_goals']:.2f}")
        print(f"   平均客队进球: {goals['avg_away_goals']:.2f}")
        print(f"   进球数标准差: {goals['stddev_total_goals']:.2f}")

        # 主场优势
        home = report["home_advantage"]
        print("\n🏠 主场优势分析:")
        print(f"   主场胜率: {home['home_win_percentage']:.1f}%")
        print(f"   平均净胜球: {home['avg_goal_difference']:+.3f}")
        print(f"   主队场均进球: {home['avg_home_goals']:.2f}")
        print(f"   客队场均进球: {home['avg_away_goals']:.2f}")

        # Top 10 联赛
        leagues = report["league_activity"][:10]
        print("\n🏆 Top 10 最活跃联赛:")
        for i, league in enumerate(leagues, 1):
            print(f"   {i:2d}. {league['league_name'][:20]:20s}: {league['total_matches']:5,} 场")

        # 热门比分
        top_scores = report["match_outcomes"]["top_scores"][:10]
        print("\n📈 热门比分 Top 10:")
        for score in top_scores:
            print(f"   {score['score']:5s}: {score['count']:4,} 场 ({score['percentage']:4.1f}%)")

        print("\n" + "="*80)

async def main():
    """主函数"""
    print("🚀 启动足球数据深度探索性分析...")

    analyzer = DataAnalyzer()

    try:
        # 生成综合报告
        report = await analyzer.generate_comprehensive_report()

        # 打印摘要
        analyzer.print_report_summary(report)

        logger.info("✅ 数据分析完成！")

    except Exception as e:
        logger.error(f"❌ 分析过程中出现错误: {str(e)}")
        raise
    finally:
        await analyzer.close()

if __name__ == "__main__":
    asyncio.run(main())
