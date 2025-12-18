#!/usr/bin/env python3
"""
极简验证脚本 - 验证L1和L2修复效果
Minimal Verification Script - Verify L1 & L2 Fixes

目的：抓一场英超比赛，验证xG数据不再是0.0
验收标准：控制台必须打印 "Match: TeamA vs TeamB | xG: 2.21 - 1.85" (不能是0.0)

Author: Senior Code Refactorer
Date: 2025-12-08
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入修复后的采集器
from src.collectors.fotmob_api_collector import FotMobAPICollector

async def verify_clean_run():
    """极简验证L1和L2修复效果"""
    print("🚀 开始极简验证...")
    print("="*50)

    # 初始化采集器
    collector = FotMobAPICollector(max_concurrent=1, timeout=30)
    await collector.initialize()

    try:
        # L1: 获取英超比赛列表
        print("📋 Step 1: 获取英超比赛...")
        league_url = "https://www.fotmob.com/api/leagues?id=47&tab=fixtures"

        data, status = await collector._make_request(league_url, "premier_league")

        if status.name != "SUCCESS" or not data:
            print("❌ L1失败: 无法获取英超数据")
            return False

        # 从fixtures.allMatches获取比赛
        fixtures = data.get("fixtures", {})
        all_matches = fixtures.get("allMatches", [])

        if not all_matches:
            print("❌ L1失败: 未找到比赛数据")
            return False

        # 选择第一场已结束的比赛
        test_match = None
        for match in all_matches[:10]:  # 检查前10场
            if isinstance(match, dict):
                match_status = match.get("status", {}).get("reason", {}).get("short", "")
                if match_status == "FT":  # 已结束比赛
                    test_match = match
                    break

        if not test_match:
            print("❌ L1失败: 未找到已结束的比赛")
            return False

        match_id = str(test_match.get("id", ""))
        home_team = test_match.get("home", {}).get("name", "Unknown")
        away_team = test_match.get("away", {}).get("name", "Unknown")

        print(f"✅ L1成功: 找到比赛 {home_team} vs {away_team} (ID: {match_id})")

        # L2: 获取比赛详情并验证xG
        print("\n📊 Step 2: 获取比赛详情...")
        match_detail = await collector.collect_match_details(match_id)

        if not match_detail:
            print("❌ L2失败: 无法获取比赛详情")
            return False

        # 验证关键数据
        xg_home = match_detail.xg_home
        xg_away = match_detail.xg_away
        referee = match_detail.referee

        print("✅ L2成功: 获取到比赛详情")
        print(f"   比分: {match_detail.home_score} - {match_detail.away_score}")
        print(f"   xG: {xg_home} - {xg_away}")
        print(f"   裁判: {referee or '未知'}")

        # 🎯 验收标准检查
        if xg_home == 0.0 and xg_away == 0.0:
            print("\n❌ 验收失败: xG数据仍为0.0，修复未生效")
            return False

        if xg_home > 0 or xg_away > 0:
            print("\n🎉 验收通过!")
            print(f"   Match: {home_team} vs {away_team} | xG: {xg_home} - {xg_away}")
            return True
        else:
            print("\n⚠️ 异常情况: xG数据格式异常")
            return False

    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

    finally:
        await collector.close()

if __name__ == "__main__":
    success = asyncio.run(verify_clean_run())
    sys.exit(0 if success else 1)
