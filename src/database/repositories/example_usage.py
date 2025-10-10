"""
Repository使用示例

演示如何使用Repository模式进行数据访问。
"""

import asyncio
from datetime import datetime, timedelta
from typing import List

from src.database.connection import get_async_db_session
from . import MatchRepository, PredictionRepository, UserRepository, TeamRepository
from .base import RepositoryConfig


async def example_match_repository():
    """演示MatchRepository的使用"""
    print("\n=== MatchRepository 示例 ===")

    async with get_async_db_session() as session:
        # 创建仓储
        match_repo = MatchRepository(
            session, RepositoryConfig(enable_query_logging=True)
        )

        # 1. 获取即将到来的比赛
        print("\n1. 获取即将到来的比赛：")
        upcoming = await match_repo.get_upcoming_matches(days=7, limit=5)
        for match in upcoming:
            print(
                f"  - {match.home_team.name} vs {match.away_team.name} at {match.match_time}"
            )

        # 2. 获取指定球队的比赛
        print("\n2. 获取球队最近比赛：")
        team_matches = await match_repo.get_team_matches(team_id=1, limit=5)
        for match in team_matches:
            print(
                f"  - {match.home_team.name} {match.home_score}:{match.away_score} {match.away_team.name}"
            )

        # 3. 分页查询
        print("\n3. 分页查询所有比赛：")
        page_result = await match_repo.paginate(page=1, page_size=5)
        print(f"  总数: {page_result.total}, 当前页: {page_result.page}")
        print(f"  是否有下一页: {page_result.has_next}")

        # 4. 搜索比赛
        print("\n4. 搜索包含'Manchester'的比赛：")
        search_results = await match_repo.search_matches("Manchester", limit=3)
        for match in search_results:
            print(f"  - {match.home_team.name} vs {match.away_team.name}")

        # 5. 获取每日比赛统计
        print("\n5. 最近7天比赛统计：")
        daily_stats = await match_repo.get_daily_match_count(days=7)
        for stat in daily_stats:
            print(f"  - {stat['date']}: {stat['count']} 场比赛")


async def example_prediction_repository():
    """演示PredictionRepository的使用"""
    print("\n=== PredictionRepository 示例 ===")

    async with get_async_db_session() as session:
        # 创建仓储
        pred_repo = PredictionRepository(session)

        # 1. 获取高置信度预测
        print("\n1. 高置信度预测：")
        high_conf = await pred_repo.get_high_confidence_predictions(
            threshold=0.8, limit=5
        )
        for pred in high_conf:
            print(
                f"  - 比赛{pred.match_id}: {pred.predicted_result} (置信度: {pred.confidence:.2f})"
            )

        # 2. 获取模型性能
        print("\n2. 模型性能统计：")
        model_perf = await pred_repo.get_all_model_performance(days=30)
        for perf in model_perf[:3]:
            print(
                f"  - {perf['model_name']}: 准确率 {perf['accuracy']:.2%}, "
                f"预测数 {perf['total_predictions']}"
            )

        # 3. 获取用户预测统计
        print("\n3. 用户预测统计：")
        user_stats = await pred_repo.get_prediction_statistics(user_id=1, days=30)
        print(f"  - 总预测数: {user_stats['total_predictions']}")
        print(f"  - 准确率: {user_stats['accuracy']:.2%}")


async def example_user_repository():
    """演示UserRepository的使用"""
    print("\n=== UserRepository 示例 ===")

    async with get_async_db_session() as session:
        # 创建仓储
        user_repo = UserRepository(session)

        # 1. 获取活跃用户
        print("\n1. 最近活跃用户：")
        active_users = await user_repo.get_active_users(limit=5)
        for user in active_users:
            print(f"  - {user.username} (最后登录: {user.last_login})")

        # 2. 获取用户活动汇总
        print("\n2. 用户活动汇总：")
        activity_summary = await user_repo.get_user_activity_summary(days=30)
        print(f"  - 总用户数: {activity_summary['total_users']}")
        print(f"  - 活跃用户: {activity_summary['active_users']}")
        print(f"  - 活跃率: {activity_summary['activity_rate']:.2%}")

        # 3. 获取顶级预测者
        print("\n3. 预测准确率最高的用户：")
        top_predictors = await user_repo.get_top_predictors(days=30, limit=3)
        for predictor in top_predictors:
            print(
                f"  - {predictor['username']}: "
                f"准确率 {predictor['accuracy']:.2%} "
                f"({predictor['correct_predictions']}/{predictor['total_predictions']})"
            )


async def example_team_repository():
    """演示TeamRepository的使用"""
    print("\n=== TeamRepository 示例 ===")

    async with get_async_db_session() as session:
        # 创建仓储
        team_repo = TeamRepository(session)

        # 1. 搜索球队
        print("\n1. 搜索包含'United'的球队：")
        teams = await team_repo.search_teams("United", limit=5)
        for team in teams:
            print(f"  - {team.name} ({team.country})")

        # 2. 获取球队统计
        print("\n2. 球队统计信息：")
        team_stats = await team_repo.get_team_statistics(team_id=1, last_matches=5)
        if team_stats:
            stats = team_stats["statistics"]
            print(f"  - {team_stats['team_name']}")
            print(f"  - 近5场: {stats['won']}胜{stats['drawn']}平{stats['lost']}负")
            print(f"  - 进球: {stats['goals_for']}, 失球: {stats['goals_against']}")

        # 3. 获取交锋记录
        print("\n3. 历史交锋记录：")
        h2h = await team_repo.get_team_head_to_head(team1_id=1, team2_id=2, limit=5)
        if h2h["total_matches"] > 0:
            print(f"  - 总交锋: {h2h['total_matches']}场")
            print(f"  - 球队1胜: {h2h['team1_wins']}")
            print(f"  - 球队2胜: {h2h['team2_wins']}")
            print(f"  - 平局: {h2h['draws']}")


async def example_advanced_operations():
    """演示高级操作"""
    print("\n=== 高级操作示例 ===")

    async with get_async_db_session() as session:
        match_repo = MatchRepository(session)
        pred_repo = PredictionRepository(session)

        # 1. 批量更新比分
        print("\n1. 批量更新比赛比分：")
        # 模拟更新一些比赛的比分
        updates = [
            {"match_id": 1, "home_score": 2, "away_score": 1},
            {"match_id": 2, "home_score": 1, "away_score": 1},
        ]

        for update in updates:
            success = await match_repo.update_match_scores(
                update["match_id"], update["home_score"], update["away_score"]
            )
            print(
                f"  - 比赛ID {update['match_id']}: "
                f"{'更新成功' if success else '更新失败'}"
            )

        # 2. 批量创建预测
        print("\n2. 批量创建预测：")
        predictions_data = [
            {
                "match_id": 3,
                "user_id": 1,
                "model_name": "ml_model_v1",
                "predicted_result": "home_win",
                "confidence": 0.75,
                "predicted_odds": 2.1,
            },
            {
                "match_id": 4,
                "user_id": 1,
                "model_name": "ml_model_v1",
                "predicted_result": "draw",
                "confidence": 0.60,
                "predicted_odds": 3.2,
            },
        ]

        created_predictions = await pred_repo.bulk_create_predictions(predictions_data)
        print(f"  - 成功创建 {len(created_predictions)} 个预测")

        # 3. 事务操作示例
        print("\n3. 事务操作示例：")
        try:
            # 开始事务
            # 创建新比赛
            # 创建相关预测
            # 提交事务
            print("  - 事务操作成功")
        except Exception as e:
            # 回滚事务
            print(f"  - 事务回滚: {e}")


async def main():
    """主函数"""
    print("Repository模式使用示例")
    print("=" * 50)

    try:
        # 运行各种示例
        await example_match_repository()
        await example_prediction_repository()
        await example_user_repository()
        await example_team_repository()
        await example_advanced_operations()

        print("\n" + "=" * 50)
        print("示例运行完成！")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
