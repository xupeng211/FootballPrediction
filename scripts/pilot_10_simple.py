#!/usr/bin/env python3
"""
10场试跑脚本 - 简化版
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def run_pilot_10():
    """执行10场试跑"""
    logger.info("🚀 启动10场试跑数据采集")

    try:
        # 在Docker容器中执行数据采集
        import subprocess

        # 使用我们之前验证过的真实API响应结构
        cmd = [
            "docker-compose", "exec", "app", "python", "-c", '''
import sys
sys.path.append("/app/src")
from collectors.fotmob_api_collector import FotMobAPICollector
import asyncio
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_data_quality():
    """测试数据质量"""
    collector = FotMobAPICollector(max_concurrent=1, timeout=30, max_retries=2)
    await collector.initialize()

    test_match_ids = [
        "4329053", "4329067", "4329078", "4329089", "4329090",
        "4329091", "4329092", "4329093", "4329094", "4329095"
    ]

    success_count = 0
    results = []

    for i, match_id in enumerate(test_match_ids, 1):
        logger.info(f"🔍 测试比赛 {i}/10: {match_id}")

        try:
            match_data = await collector.collect_match_details(match_id)

            if match_data:
                # 验证关键数据
                match_info = match_data.match_info or {}
                stats_json = match_data.stats_json or {}
                environment_json = match_data.environment_json or {}
                odds_json = match_data.odds_snapshot_json or {}

                home_team = match_info.get("home_team_name", "Unknown")
                away_team = match_info.get("away_team_name", "Unknown")

                # 提取xG数据
                home_xg, away_xg = None, None
                xg_data = stats_json.get("xg", {})
                if xg_data and "xg" in xg_data:
                    xg_values = xg_data["xg"]
                    if len(xg_values) >= 2:
                        home_xg, away_xg = xg_values[0], xg_values[1]

                # 提取控球率数据
                home_possession, away_possession = None, None
                possession_data = stats_json.get("possession", {})
                if possession_data and "possession" in possession_data:
                    possession_values = possession_data["possession"]
                    if len(possession_values) >= 2:
                        home_possession, away_possession = possession_values[0], possession_values[1]

                # 提取裁判信息
                referee_name = None
                if environment_json:
                    referee = environment_json.get("referee", {})
                    referee_name = referee.get("name")

                # 提取赔率信息
                odds_count = 0
                if odds_json:
                    odds_count = len([k for k in odds_json.keys() if k != "snapshot_time"])

                # 提取统计数据类别
                stats_categories = len([k for k, v in stats_json.items() if v])

                result = {
                    "match_id": match_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "score": f"{match_data.home_score}-{match_data.away_score}",
                    "venue": match_data.venue,
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                    "home_possession": home_possession,
                    "away_possession": away_possession,
                    "referee": referee_name,
                    "odds_count": odds_count,
                    "stats_categories": stats_categories,
                    "status": match_data.status
                }

                results.append(result)
                success_count += 1

                logger.info(f"✅ {match_id}: {home_team} vs {away_team}")
                if home_xg and away_xg:
                    logger.info(f"   📊 xG: {home_xg} - {away_xg} ✅")
                if referee_name:
                    logger.info(f"   🌍 裁判: {referee_name} ✅")
                if odds_count > 0:
                    logger.info(f"   💰 赔率: {odds_count} 个数据源 ✅")
                logger.info(f"   📈 统计类别: {stats_categories} 个 ✅")

            else:
                logger.warning(f"❌ {match_id}: 未获取到数据")

        except Exception as e:
            logger.error(f"💥 {match_id}: 异常 - {e}")

        # 避免限流
        await asyncio.sleep(1.0)

        if success_count >= 5:  # 测试5场即可
            break

    await collector.close()

    # 生成详细报告
    logger.info("\\n" + "="*80)
    logger.info("📊 10场试跑数据质量报告")
    logger.info("="*80)

    for i, result in enumerate(results, 1):
        logger.info(f"\\n🎯 比赛 {i}: {result['home_team']} vs {result['away_team']}")
        logger.info("   " + "-"*70)
        logger.info(f"   🆔 Match ID: {result['match_id']}")
        logger.info(f"   ⚽ 比分: {result['score']}")
        logger.info(f"   🏟️ 场地: {result['venue'] or 'Unknown'}")
        logger.info(f"   📊 xG: 主队 {result['home_xg'] or 'N/A'} - 客队 {result['away_xg'] or 'N/A'} {'✅' if result['home_xg'] else '❌'}")
        logger.info(f"   📊 控球率: 主队 {result['home_possession'] or 'N/A'}% - 客队 {result['away_possession'] or 'N/A'}% {'✅' if result['home_possession'] else '❌'}")
        logger.info(f"   🌍 裁判: {result['referee'] or 'N/A'} {'✅' if result['referee'] else '❌'}")
        logger.info(f"   💰 赔率: {result['odds_count']} 个数据源 {'✅' if result['odds_count'] > 0 else '❌'}")
        logger.info(f"   📈 统计类别: {result['stats_categories']} 个 {'✅' if result['stats_categories'] > 0 else '❌'}")

    logger.info("\\n" + "="*80)
    logger.info("🎯 试跑总结")
    logger.info("="*80)
    logger.info(f"📊 测试比赛数: {len(test_match_ids)}")
    logger.info(f"✅ 成功采集: {success_count} 场")
    logger.info(f"❌ 采集失败: {len(test_match_ids) - success_count} 场")

    # 关键数据质量评估
    with_xg = len([r for r in results if r['home_xg']])
    with_referee = len([r for r in results if r['referee']])
    with_odds = len([r for r in results if r['odds_count'] > 0])
    with_stats = len([r for r in results if r['stats_categories'] > 0])

    logger.info(f"📊 数据质量评估:")
    logger.info(f"   📈 xG数据: {with_xg}/{success_count} ({(with_xg/success_count*100):.1f}%)")
    logger.info(f"   🌍 裁判数据: {with_referee}/{success_count} ({(with_referee/success_count*100):.1f}%)")
    logger.info(f"   💰 赔率数据: {with_odds}/{success_count} ({(with_odds/success_count*100):.1f}%)")
    logger.info(f"   📈 统计数据: {with_stats}/{success_count} ({(with_stats/success_count*100):.1f}%)")

asyncio.run(test_data_quality())
            '''
        ]

        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # 输出结果
        print("🚀 10场试跑执行日志:")
        print("=" * 60)
        print(result.stdout)

        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr)

        print("=" * 60)
        print("✅ 10场试跑完成")

    except subprocess.TimeoutExpired:
        print("⏰ 执行超时")
    except Exception as e:
        print(f"❌ 执行异常: {e}")

if __name__ == "__main__":
    asyncio.run(run_pilot_10())
