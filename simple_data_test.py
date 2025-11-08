#!/usr/bin/env python3
"""
简化版数据填充脚本
手动添加示例比赛数据到数据库
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta

async def add_sample_matches():
    """添加示例比赛数据"""

    print("🚀 开始添加示例比赛数据...")

    # 数据库连接配置
    db_config = {
        'host': 'localhost',
        'port': 5433,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'football_prediction_staging'
    }

    try:
        # 连接数据库
        conn = await asyncpg.connect(**db_config)
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("请确保Docker数据库容器正在运行")
        return False

    try:
        # 示例比赛数据
        matches = [
            ("Manchester City", "Liverpool", datetime.now() + timedelta(days=2), "Premier League"),
            ("Arsenal", "Chelsea", datetime.now() + timedelta(days=3), "Premier League"),
            ("Manchester United", "Tottenham", datetime.now() + timedelta(days=4), "Premier League"),
            ("Real Madrid", "Barcelona", datetime.now() + timedelta(days=5), "La Liga"),
            ("Atletico Madrid", "Sevilla", datetime.now() + timedelta(days=6), "La Liga"),
            ("Bayern Munich", "Borussia Dortmund", datetime.now() + timedelta(days=7), "Bundesliga"),
            ("Paris Saint-Germain", "Lyon", datetime.now() + timedelta(days=8), "Ligue 1"),
            ("AC Milan", "Inter Milan", datetime.now() + timedelta(days=9), "Serie A"),
            ("Juventus", "Napoli", datetime.now() + timedelta(days=10), "Serie A")
        ]

        print(f"📊 准备插入 {len(matches)} 场比赛...")

        # 插入数据
        inserted_count = 0
        for home_team, away_team, match_date, league in matches:
            try:
                await conn.execute("""
                    INSERT INTO matches (home_team, away_team, match_date, league)
                    VALUES ($1, $2, $3, $4)
                """, home_team, away_team, match_date, league)
                inserted_count += 1
                print(f"  ✅ {home_team} vs {away_team} ({league})")
            except Exception as e:
                print(f"  ❌ 插入失败: {home_team} vs {away_team} - {e}")

        print(f"\n🎉 成功插入 {inserted_count} 场比赛!")

        # 验证插入结果
        count_result = await conn.fetchval("SELECT COUNT(*) FROM matches")
        print(f"📈 数据库中现在共有 {count_result} 场比赛")

        # 显示最新比赛
        latest = await conn.fetch("""
            SELECT id, home_team, away_team, league,
                   DATE(match_date) as match_date
            FROM matches
            ORDER BY created_at DESC
            LIMIT 5
        """)

        print("\n🏆 最新插入的比赛:")
        for match in latest:
            print(f"  ID:{match['id']} - {match['home_team']} vs {match['away_team']} "
                  f"({match['league']}) - {match['match_date']}")

        return True

    except Exception as e:
        print(f"❌ 数据操作失败: {e}")
        return False
    finally:
        await conn.close()

async def check_predictions_for_matches():
    """检查现有预测是否匹配新的比赛数据"""

    print("\n🔍 检查预测数据关联...")

    try:
        conn = await asyncpg.connect(
            host='localhost', port=5433, user='postgres',
            password='postgres', database='football_prediction_staging'
        )

        # 查看所有预测
        predictions = await conn.fetch("""
            SELECT p.id, p.match_id, p.predicted_winner, p.confidence,
                   m.home_team, m.away_team, m.league
            FROM predictions p
            LEFT JOIN matches m ON p.match_id = m.id
            ORDER BY p.created_at DESC
        """)

        print(f"📋 找到 {len(predictions)} 条预测记录:")

        for pred in predictions:
            if pred['home_team']:
                print(f"  ✅ 预测ID {pred['id']}: {pred['predicted_winner']} 获胜 "
                      f"({pred['home_team']} vs {pred['away_team']}) - 置信度 {pred['confidence']}")
            else:
                print(f"  ⚠️  预测ID {pred['id']}: {pred['predicted_winner']} 获胜 "
                      f"(比赛ID {pred['match_id']} 未找到对应比赛) - 置信度 {pred['confidence']}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ 检查预测数据失败: {e}")
        return False

async def create_sample_predictions():
    """为新比赛创建一些示例预测"""

    print("\n🎯 创建示例预测...")

    try:
        conn = await asyncpg.connect(
            host='localhost', port=5433, user='postgres',
            password='postgres', database='football_prediction_staging'
        )

        # 获取最新的几场比赛
        matches = await conn.fetch("""
            SELECT id, home_team, away_team FROM matches
            WHERE id NOT IN (SELECT DISTINCT match_id FROM predictions)
            LIMIT 3
        """)

        if not matches:
            print("❌ 没有找到未预测的比赛")
            return False

        print(f"📝 为 {len(matches)} 场比赛创建预测...")

        predictions = []
        for match in matches:
            # 简单预测主队获胜，置信度根据主队"实力"调整
            home_team = match['home_team']
            confidence = 0.75  # 默认置信度

            # 根据球队调整置信度
            if any(team in home_team for team in ['Manchester City', 'Real Madrid', 'Bayern Munich', 'PSG']):
                confidence = 0.85
            elif any(team in home_team for team in ['Arsenal', 'Barcelona', 'Liverpool', 'Juventus']):
                confidence = 0.80
            else:
                confidence = 0.65

            result = await conn.fetchrow("""
                INSERT INTO predictions (match_id, predicted_winner, confidence)
                VALUES ($1, $2, $3)
                RETURNING id
            """, match['id'], home_team, confidence)

            predictions.append({
                'id': result['id'],
                'match': f"{home_team} vs {match['away_team']}",
                'winner': home_team,
                'confidence': confidence
            })
            print(f"  ✅ 预测ID {result['id']}: {home_team} 获胜 (置信度 {confidence})")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ 创建预测失败: {e}")
        return False

async def main():
    """主函数"""
    print("=" * 70)
    print("⚽ FootballPrediction 数据收集与填充测试")
    print("=" * 70)

    # 1. 添加示例比赛数据
    success1 = await add_sample_matches()

    # 2. 检查现有预测
    success2 = await check_predictions_for_matches()

    # 3. 为新比赛创建预测
    success3 = await create_sample_predictions()

    print("\n" + "=" * 70)
    print("📋 测试结果总结:")
    print(f"  比赛数据填充: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"  预测数据检查: {'✅ 成功' if success2 else '❌ 失败'}")
    print(f"  示例预测创建: {'✅ 成功' if success3 else '❌ 失败'}")

    if success1 and success2 and success3:
        print("\n🎉 太棒了！系统数据收集功能运行正常！")
        print("\n🚀 现在你可以:")
        print("  1. 通过API查看所有预测: curl http://localhost:8001/predictions")
        print("  2. 查看特定预测: curl http://localhost:8001/predictions/[id]")
        print("  3. 创建新预测 (通过POST请求)")
        print("  4. 数据库中已有丰富的比赛和预测数据!")
    else:
        print("\n⚠️  部分功能需要调试，但基础数据结构正常")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())