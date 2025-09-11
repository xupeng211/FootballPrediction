#!/usr/bin/env python3
"""
物化视图查询示例

展示如何使用创建的物化视图进行高效的数据分析查询。

主要内容：
1. 球队近期战绩查询示例
2. 赔率趋势分析查询示例
3. 性能对比（物化视图 vs 常规查询）
4. 业务分析场景示例

使用方法：
    python scripts/materialized_views_examples.py
    python scripts/materialized_views_examples.py --demo team_performance
    python scripts/materialized_views_examples.py --demo odds_analysis
    python scripts/materialized_views_examples.py --benchmark
"""

import argparse
import asyncio
import logging
import time
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.config import get_database_config

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MaterializedViewExamples:
    """物化视图查询示例类"""

    def __init__(self):
        """初始化"""
        self.config = get_database_config()

    async def _get_async_engine(self):
        """获取异步数据库引擎"""
        database_url = (
            f"postgresql+asyncpg://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
        )
        return create_async_engine(database_url, echo=False)

    async def _execute_query(
        self, query: str, params: dict = None
    ) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        engine = await self._get_async_engine()

        try:
            async with engine.begin() as conn:
                result = await conn.execute(text(query), params or {})
                rows = result.fetchall()

                # 转换为字典格式
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]

        finally:
            await engine.dispose()

    async def team_performance_examples(self):
        """球队近期战绩查询示例"""
        print("\n🏆 球队近期战绩查询示例")
        print("=" * 60)

        # 示例1: 获取最活跃的球队（近期比赛最多）
        print("\n1. 最活跃的球队（近30天比赛最多）:")
        query1 = """
        SELECT
            team_name,
            (recent_home_matches + recent_away_matches) as total_recent_matches,
            (recent_home_wins + recent_away_wins) as total_wins,
            (recent_home_goals_for + recent_away_goals_for) as total_goals_scored,
            (recent_home_goals_against + recent_away_goals_against) as total_goals_conceded,
            ROUND(
                (recent_home_wins + recent_away_wins)::decimal /
                NULLIF(recent_home_matches + recent_away_matches, 0) * 100, 2
            ) as win_percentage
        FROM mv_team_recent_performance
        WHERE (recent_home_matches + recent_away_matches) > 0
        ORDER BY total_recent_matches DESC, win_percentage DESC
        LIMIT 10;
        """

        results1 = await self._execute_query(query1)
        for i, team in enumerate(results1, 1):
            print(
                f"  {i:2d}. {team['team_name']:<20} | "
                f"比赛: {team['total_recent_matches']:2d} | "
                f"胜率: {team['win_percentage'] or 0:5.1f}% | "
                f"进球: {team['total_goals_scored']:2d} | "
                f"失球: {team['total_goals_conceded']:2d}"
            )

        # 示例2: 主场表现最佳的球队
        print("\n2. 主场表现最佳的球队:")
        query2 = """
        SELECT
            team_name,
            recent_home_matches,
            recent_home_wins,
            recent_home_goals_for,
            recent_home_goals_against,
            ROUND(
                recent_home_wins::decimal / NULLIF(recent_home_matches, 0) * 100, 2
            ) as home_win_percentage,
            ROUND(
                recent_home_goals_for::decimal / NULLIF(recent_home_matches, 0), 2
            ) as avg_home_goals_per_match
        FROM mv_team_recent_performance
        WHERE recent_home_matches >= 3
        ORDER BY home_win_percentage DESC, avg_home_goals_per_match DESC
        LIMIT 5;
        """

        results2 = await self._execute_query(query2)
        for i, team in enumerate(results2, 1):
            print(
                f"  {i}. {team['team_name']:<20} | "
                f"主场: {team['recent_home_matches']:2d}场 | "
                f"胜率: {team['home_win_percentage'] or 0:5.1f}% | "
                f"场均进球: {team['avg_home_goals_per_match'] or 0:4.2f}"
            )

        # 示例3: 攻防平衡分析
        print("\n3. 攻防平衡分析:")
        query3 = """
        SELECT
            team_name,
            (recent_home_goals_for + recent_away_goals_for) as total_goals_for,
            (recent_home_goals_against + recent_away_goals_against) as total_goals_against,
            (recent_home_goals_for + recent_away_goals_for) -
            (recent_home_goals_against + recent_away_goals_against) as goal_difference,
            CASE
                WHEN (recent_home_matches + recent_away_matches) = 0 THEN 0
                ELSE ROUND(
                    ((recent_home_goals_for + recent_away_goals_for)::decimal /
                     (recent_home_matches + recent_away_matches)), 2
                )
            END as avg_goals_scored,
            CASE
                WHEN (recent_home_matches + recent_away_matches) = 0 THEN 0
                ELSE ROUND(
                    ((recent_home_goals_against + recent_away_goals_against)::decimal /
                     (recent_home_matches + recent_away_matches)), 2
                )
            END as avg_goals_conceded
        FROM mv_team_recent_performance
        WHERE (recent_home_matches + recent_away_matches) >= 3
        ORDER BY goal_difference DESC
        LIMIT 8;
        """

        results3 = await self._execute_query(query3)
        for i, team in enumerate(results3, 1):
            print(
                f"  {i}. {team['team_name']:<20} | "
                f"净胜球: {team['goal_difference']:+3d} | "
                f"场均进球: {team['avg_goals_scored']:4.2f} | "
                f"场均失球: {team['avg_goals_conceded']:4.2f}"
            )

    async def odds_analysis_examples(self):
        """赔率趋势分析查询示例"""
        print("\n📊 赔率趋势分析查询示例")
        print("=" * 60)

        # 示例1: 赔率最稳定的比赛（波动性最小）
        print("\n1. 赔率最稳定的比赛（波动性最小）:")
        query1 = """
        SELECT
            ot.match_id,
            ht.team_name as home_team,
            at.team_name as away_team,
            ot.match_time,
            ot.avg_home_odds,
            ot.avg_draw_odds,
            ot.avg_away_odds,
            ot.home_odds_volatility,
            ot.draw_odds_volatility,
            ot.away_odds_volatility,
            (ot.home_odds_volatility + ot.draw_odds_volatility + ot.away_odds_volatility) as total_volatility
        FROM mv_odds_trends ot
        JOIN teams ht ON ot.home_team_id = ht.id
        JOIN teams at ON ot.away_team_id = at.id
        WHERE ot.market_type = '1x2'
          AND ot.bookmaker_count >= 3
          AND ot.match_time >= CURRENT_DATE
        ORDER BY total_volatility ASC
        LIMIT 5;
        """

        results1 = await self._execute_query(query1)
        for i, match in enumerate(results1, 1):
            print(f"  {i}. {match['home_team']:<15} vs {match['away_team']:<15}")
            print(f"     时间: {match['match_time']}")
            print(
                f"     平均赔率: {match['avg_home_odds']:5.2f} | {match['avg_draw_odds']:5.2f} | {match['avg_away_odds']:5.2f}"
            )
            print(f"     波动性: {match['total_volatility'] or 0:6.4f}")
            print()

        # 示例2: 最有价值的投注机会（隐含概率分析）
        print("\n2. 最有价值的投注机会:")
        query2 = """
        SELECT
            ot.match_id,
            ht.team_name as home_team,
            at.team_name as away_team,
            ot.match_time,
            ot.home_implied_probability,
            ot.draw_implied_probability,
            ot.away_implied_probability,
            CASE
                WHEN ot.home_implied_probability = GREATEST(ot.home_implied_probability, ot.draw_implied_probability, ot.away_implied_probability)
                THEN 'HOME'
                WHEN ot.draw_implied_probability = GREATEST(ot.home_implied_probability, ot.draw_implied_probability, ot.away_implied_probability)
                THEN 'DRAW'
                ELSE 'AWAY'
            END as favored_outcome,
            GREATEST(ot.home_implied_probability, ot.draw_implied_probability, ot.away_implied_probability) as max_probability
        FROM mv_odds_trends ot
        JOIN teams ht ON ot.home_team_id = ht.id
        JOIN teams at ON ot.away_team_id = at.id
        WHERE ot.market_type = '1x2'
          AND ot.bookmaker_count >= 3
          AND ot.match_time >= CURRENT_DATE
          AND ot.match_time <= CURRENT_DATE + INTERVAL '7 days'
        ORDER BY max_probability DESC
        LIMIT 8;
        """

        results2 = await self._execute_query(query2)
        for i, match in enumerate(results2, 1):
            print(f"  {i}. {match['home_team']:<15} vs {match['away_team']:<15}")
            print(
                f"     偏向结果: {match['favored_outcome']:4s} | "
                f"最高概率: {match['max_probability'] or 0:5.1%}"
            )
            print(
                f"     概率分布: 主队 {match['home_implied_probability'] or 0:5.1%} | "
                f"平局 {match['draw_implied_probability'] or 0:5.1%} | "
                f"客队 {match['away_implied_probability'] or 0:5.1%}"
            )
            print()

        # 示例3: 博彩公司一致性分析
        print("\n3. 博彩公司一致性分析:")
        query3 = """
        SELECT
            ot.match_id,
            ht.team_name as home_team,
            at.team_name as away_team,
            ot.bookmaker_count,
            ot.home_odds_volatility,
            ot.draw_odds_volatility,
            ot.away_odds_volatility,
            CASE
                WHEN ot.home_odds_volatility < 0.1 AND ot.draw_odds_volatility < 0.1 AND ot.away_odds_volatility < 0.1
                THEN '一致性很高'
                WHEN ot.home_odds_volatility < 0.2 AND ot.draw_odds_volatility < 0.2 AND ot.away_odds_volatility < 0.2
                THEN '一致性较高'
                ELSE '存在分歧'
            END as consensus_level
        FROM mv_odds_trends ot
        JOIN teams ht ON ot.home_team_id = ht.id
        JOIN teams at ON ot.away_team_id = at.id
        WHERE ot.market_type = '1x2'
          AND ot.bookmaker_count >= 5
          AND ot.match_time >= CURRENT_DATE
        ORDER BY ot.bookmaker_count DESC, (ot.home_odds_volatility + ot.draw_odds_volatility + ot.away_odds_volatility) ASC
        LIMIT 6;
        """

        results3 = await self._execute_query(query3)
        for i, match in enumerate(results3, 1):
            print(f"  {i}. {match['home_team']:<15} vs {match['away_team']:<15}")
            print(
                f"     博彩公司数: {match['bookmaker_count']:2d} | 一致性: {match['consensus_level']}"
            )
            print(
                f"     赔率标准差: 主 {match['home_odds_volatility'] or 0:5.3f} | "
                f"平 {match['draw_odds_volatility'] or 0:5.3f} | "
                f"客 {match['away_odds_volatility'] or 0:5.3f}"
            )
            print()

    async def performance_benchmark(self):
        """性能基准测试：物化视图 vs 常规查询"""
        print("\n⚡ 性能基准测试")
        print("=" * 60)

        # 测试1: 球队近期战绩查询
        print("\n1. 球队近期战绩查询性能对比:")

        # 使用物化视图的查询
        mv_query = """
        SELECT
            team_name,
            (recent_home_matches + recent_away_matches) as total_matches,
            (recent_home_wins + recent_away_wins) as total_wins
        FROM mv_team_recent_performance
        WHERE (recent_home_matches + recent_away_matches) > 0
        ORDER BY total_wins DESC
        LIMIT 10;
        """

        # 等效的常规查询
        regular_query = """
        WITH team_stats AS (
            SELECT
                t.id as team_id,
                t.team_name,
                COUNT(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished'
                           AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_home_matches,
                COUNT(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished'
                           AND m.home_score > m.away_score
                           AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_home_wins,
                COUNT(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished'
                           AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_away_matches,
                COUNT(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished'
                           AND m.away_score > m.home_score
                           AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_away_wins
            FROM teams t
            LEFT JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            GROUP BY t.id, t.team_name
        )
        SELECT
            team_name,
            (recent_home_matches + recent_away_matches) as total_matches,
            (recent_home_wins + recent_away_wins) as total_wins
        FROM team_stats
        WHERE (recent_home_matches + recent_away_matches) > 0
        ORDER BY total_wins DESC
        LIMIT 10;
        """

        # 执行性能测试
        await self._performance_test("物化视图查询", mv_query)
        await self._performance_test("常规查询", regular_query)

        # 测试2: 赔率趋势查询
        print("\n2. 赔率趋势查询性能对比:")

        mv_odds_query = """
        SELECT
            match_id,
            avg_home_odds,
            avg_draw_odds,
            avg_away_odds,
            bookmaker_count
        FROM mv_odds_trends
        WHERE market_type = '1x2'
          AND bookmaker_count >= 3
        ORDER BY match_time DESC
        LIMIT 20;
        """

        regular_odds_query = """
        WITH latest_odds AS (
            SELECT
                match_id,
                AVG(home_odds) as avg_home_odds,
                AVG(draw_odds) as avg_draw_odds,
                AVG(away_odds) as avg_away_odds,
                COUNT(DISTINCT bookmaker) as bookmaker_count
            FROM odds
            WHERE market_type = '1x2'
              AND collected_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY match_id
        )
        SELECT
            lo.match_id,
            lo.avg_home_odds,
            lo.avg_draw_odds,
            lo.avg_away_odds,
            lo.bookmaker_count
        FROM latest_odds lo
        JOIN matches m ON lo.match_id = m.id
        WHERE lo.bookmaker_count >= 3
        ORDER BY m.match_time DESC
        LIMIT 20;
        """

        await self._performance_test("物化视图赔率查询", mv_odds_query)
        await self._performance_test("常规赔率查询", regular_odds_query)

    async def _performance_test(self, test_name: str, query: str):
        """执行性能测试"""
        print(f"   {test_name}:")

        # 执行多次测试取平均值
        times = []
        for i in range(3):
            start_time = time.time()
            results = await self._execute_query(query)
            end_time = time.time()
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)
        print(f"     平均执行时间: {avg_time*1000:.2f}ms")
        print(f"     返回行数: {len(results) if 'results' in locals() else 0}")
        print(f"     执行次数: {len(times)}")
        print()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="物化视图查询示例")
    parser.add_argument(
        "--demo",
        choices=["team_performance", "odds_analysis", "all"],
        default="all",
        help="选择要运行的示例",
    )
    parser.add_argument("--benchmark", action="store_true", help="运行性能基准测试")

    args = parser.parse_args()

    examples = MaterializedViewExamples()

    try:
        if args.benchmark:
            await examples.performance_benchmark()
        elif args.demo == "team_performance":
            await examples.team_performance_examples()
        elif args.demo == "odds_analysis":
            await examples.odds_analysis_examples()
        else:  # all
            await examples.team_performance_examples()
            await examples.odds_analysis_examples()

            if input("\n是否运行性能基准测试? (y/N): ").lower() == "y":
                await examples.performance_benchmark()

    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
