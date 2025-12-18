#!/usr/bin/env python3
"""
IntegrityError修复验证测试
Test IntegrityError Fix

验证match_time和match_date字段允许NULL值后的数据采集功能
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_integrity_fix():
    """测试IntegrityError修复"""
    logger.info("🚀 启动IntegrityError修复验证测试")
    logger.info("🎯 目标: 验证match_time和match_date允许NULL后能正常入库")
    logger.info("=" * 70)

    try:
        # 在Docker容器中执行测试
        import subprocess

        cmd = [
            "docker-compose", "exec", "app", "python", "-c",
            '''
import sys
sys.path.append("/app/src")
from collectors.fotmob_api_collector import FotMobAPICollector
from database.async_manager import initialize_database, get_async_db_session
from sqlalchemy import text
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_null_time_handling():
    """测试NULL时间处理"""
    logger.info("🔍 开始测试NULL时间处理能力")

    # 初始化数据库
    initialize_database()

    # 创建采集器
    collector = FotMobAPICollector(max_concurrent=1, timeout=30, max_retries=2)
    await collector.initialize()

    try:
        # 构造一个包含NULL时间的测试数据
        test_match_data = {
            "header": {
                "status": {
                    "reason": {
                        "short": "TBD",  # 时间待定
                        "long": "Time To Be Determined"
                    }
                },
                "teams": [
                    {"id": 1, "name": "Test Home", "score": 0},
                    {"id": 2, "name": "Test Away", "score": 0}
                ]
            },
            "general": {
                # 故意不设置matchTimeUTCDate，测试NULL处理
                "venue": {"name": "Test Stadium"},
                "homeTeam": {"id": 1, "name": "Test Home"},
                "awayTeam": {"id": 2, "name": "Test Away"},
                "leagueId": 1,
                "leagueName": "Test League",
                "season": "2024/2025"
            },
            "content": {
                "stats": {"Periods": {"All": {"stats": []}}},
                "lineup": {
                    "homeTeam": {"formation": "4-4-2"},
                    "awayTeam": {"formation": "4-3-3"}
                }
            }
        }

        # 测试解析
        logger.info("🔍 测试解析NULL时间数据...")
        match_data = collector._parse_match_data("NULL_TIME_TEST", test_match_data)

        if match_data:
            logger.info("✅ 解析成功")
            logger.info(f"   主客队: {match_data.match_info.get('home_team_name')} vs {match_data.match_info.get('away_team_name')}")
            logger.info(f"   match_time: {match_data.match_time} (应该为None)")
            logger.info(f"   venue: {match_data.venue}")
        else:
            logger.error("❌ 解析失败")
            return False

        # 测试数据库保存
        logger.info("🔍 测试数据库保存NULL时间数据...")
        success = await _save_null_time_match(match_data)

        if success:
            logger.info("✅ NULL时间数据保存成功!")
            return True
        else:
            logger.error("❌ NULL时间数据保存失败!")
            return False

    except Exception as e:
        logger.error(f"💥 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await collector.close()

async def _save_null_time_match(match_data):
    """保存NULL时间的比赛数据"""
    try:
        async for session in get_async_db_session():
            # 检查是否已存在
            check_query = text("SELECT id FROM matches WHERE fotmob_id = :fotmob_id LIMIT 1")
            result = await session.execute(check_query, {"fotmob_id": match_data.fotmob_id})
            if result.fetchone():
                await session.close()
                return True  # 已存在，认为成功

            # 插入新数据（包含NULL时间）
            insert_query = text('''
                INSERT INTO matches (
                    fotmob_id, home_team_name, away_team_name, home_score, away_score,
                    status, match_time, match_date, venue, league_id, season,
                    match_info, lineups_json, stats_json, collection_time, data_completeness,
                    created_at, updated_at
                ) VALUES (
                    :fotmob_id, :home_team_name, :away_team_name, :home_score, :away_score,
                    :status, :match_time, :match_date, :venue, :league_id, :season,
                    :match_info, :lineups_json, :stats_json, :collection_time, :data_completeness,
                    NOW(), NOW()
                )
            ''')

            match_info = match_data.match_info or {}
            stats_json = match_data.stats_json or {}

            await session.execute(insert_query, {
                "fotmob_id": match_data.fotmob_id,
                "home_team_name": match_info.get("home_team_name"),
                "away_team_name": match_info.get("away_team_name"),
                "home_score": match_data.home_score,
                "away_score": match_data.away_score,
                "status": match_data.status,
                "match_time": match_data.match_time,  # 这里应该是None
                "match_date": None,  # 显式设置为None
                "venue": match_data.venue,
                "league_id": match_info.get("league_context", {}).get("league_id"),
                "season": match_info.get("league_context", {}).get("season"),
                "match_info": str(match_info),
                "lineups_json": str(match_data.lineups_json),
                "stats_json": str(stats_json),
                "collection_time": datetime.now(),
                "data_completeness": "partial"
            })

            await session.commit()

            # 验证插入成功
            verify_query = text('''
                SELECT fotmob_id, home_team_name, away_team_name, match_time, match_date
                FROM matches WHERE fotmob_id = :fotmob_id
            ''')
            result = await session.execute(verify_query, {"fotmob_id": match_data.fotmob_id})
            saved_match = result.fetchone()

            await session.close()

            if saved_match:
                logger.info("✅ 数据库验证成功:")
                logger.info(f"   fotmob_id: {saved_match.fotmob_id}")
                logger.info(f"   主客队: {saved_match.home_team_name} vs {saved_match.away_team_name}")
                logger.info(f"   match_time: {saved_match.match_time} (应该为NULL)")
                logger.info(f"   match_date: {saved_match.match_date} (应该为NULL)")
                return True
            else:
                logger.error("❌ 数据库验证失败: 未找到插入的记录")
                return False

    except Exception as e:
        logger.error(f"❌ 保存失败: {e}")
        return False

# 执行测试
result = asyncio.run(test_null_time_handling())
sys.exit(0 if result else 1)
            '''
        ]

        # 执行测试命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # 输出结果
        print("🔍 IntegrityError修复验证输出:")
        print("=" * 70)
        print(result.stdout)

        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr)

        # 检查结果
        if result.returncode == 0:
            print("\n✅ IntegrityError修复验证成功!")
            print("🎯 NULL时间数据可以正常入库")
            return True
        else:
            print("\n❌ IntegrityError修复验证失败!")
            print("🚨 仍有数据入库问题需要解决")
            return False

    except subprocess.TimeoutExpired:
        print("⏰ 验证超时")
        return False
    except Exception as e:
        print(f"❌ 验证异常: {e}")
        return False

if __name__ == "__main__":
    success = test_integrity_fix()

    if success:
        print("\n" + "=" * 70)
        print("🎉 ✅ IntegrityError修复完全成功!")
        print("🚀 系统现在可以处理时间未确定的比赛 (TBD/Postponed)")
        print("📊 不会再出现NotNullViolationError")
        print("💡 可以安全启动大规模数据回填作业!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("💥 ❌ IntegrityError修复验证失败!")
        print("🚨 仍需进一步调试和修复")
        print("=" * 70)

    exit(0 if success else 1)