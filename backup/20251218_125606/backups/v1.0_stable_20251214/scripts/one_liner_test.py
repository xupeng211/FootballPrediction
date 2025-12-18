#!/usr/bin/env python3
"""
One-liner测试脚本 - 在Docker容器内快速验证FotMob L2详情采集器修复
"""

# 单行命令测试
# docker-compose exec app python -c "
# import asyncio;
# from src.data.collectors.fotmob_details_collector import collect_match_details;
# result = asyncio.run(collect_match_details('4186358'));
# print('✅ 测试成功' if result else '❌ 测试失败')
# "

# 更详细的测试命令
# docker-compose exec app python scripts/one_liner_test.py

import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def quick_test():
    """快速测试L2详情采集器"""
    print("🚀 快速测试FotMob L2详情采集器...")

    try:
        from src.data.collectors.fotmob_details_collector import collect_match_details

        # 测试比赛ID (英超比赛)
        test_match_id = "4186358"

        print(f"📊 测试比赛 {test_match_id}")

        # 执行采集
        result = await collect_match_details(test_match_id)

        if result:
            print("✅ L2详情采集器修复成功!")
            print(f"  比赛: {result.home_team} vs {result.away_team}")
            print(f"  比分: {result.home_score} - {result.away_score}")

            if result.odds:
                print(
                    f"  市场概率: 主胜 {result.odds.home_win:.2f}, 平局 {result.odds.draw:.2f}, 客胜 {result.odds.away_win:.2f}"
                )
            else:
                print("  市场概率: 未获取到数据")

            return True
        else:
            print("❌ L2详情采集器测试失败")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)
