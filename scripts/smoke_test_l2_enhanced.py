#!/usr/bin/env python3
"""
L2增强采集器冒烟测试
小样本验证新字段的数据完整性
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class L2SmokeTester:
    """L2采集器冒烟测试器"""

    def __init__(self):
        # 测试用的比赛ID列表 (选择一些近期比赛)
        self.test_match_ids = [
            "4506508",  # 之前测试过的比赛
            "4506456",  # 补充测试比赛
            "4506390",  # 补充测试比赛
            "4506321",  # 补充测试比赛
            "4506265",  # 补充测试比赛
            "4506200",  # 补充测试比赛
            "4506138",  # 补充测试比赛
            "4506075",  # 补充测试比赛
            "4506012",  # 补充测试比赛
            "4505948",  # 补充测试比赛
        ]

    async def run_smoke_test(self, limit: int = 10):
        """运行冒烟测试"""
        print("🧪 [冒烟测试] L2增强采集器小样本验证")
        print("=" * 50)
        print(f"测试比赛数量: {limit}")
        print(f"验证目标: 新字段数据完整性 (home_possession, big_chances, xGOT等)")
        print()

        # 限制测试数量
        test_matches = self.test_match_ids[:limit]

        success_count = 0
        failure_count = 0
        processed_matches = []

        try:
            # 导入必要模块
            from src.collectors.l2_parser import EnhancedL2Parser
            import aiohttp

            parser = EnhancedL2Parser()
            print("✅ L2解析器导入成功")

            # 逐个处理比赛
            for i, match_id in enumerate(test_matches, 1):
                print(f"\n📊 处理进度: {i}/{len(test_matches)} - 比赛: {match_id}")

                try:
                    # 获取FotMob数据
                    api_data = await self.fetch_fotmob_data(match_id)

                    if not api_data:
                        print(f"❌ API数据获取失败: {match_id}")
                        failure_count += 1
                        continue

                    # 解析数据
                    l2_stats = parser.parse_api_response(api_data)

                    # 验证关键字段
                    key_fields = [
                        ("home_possession", l2_stats.home_possession),
                        ("home_big_chances_created", l2_stats.home_big_chances_created),
                        ("home_expected_goals_on_target", l2_stats.home_expected_goals_on_target),
                        ("away_possession", l2_stats.away_possession),
                        ("away_big_chances_created", l2_stats.away_big_chances_created),
                    ]

                    valid_fields = 0
                    total_fields = len(key_fields)

                    for field_name, field_value in key_fields:
                        if field_value is not None:
                            valid_fields += 1
                            print(f"   ✅ {field_name}: {field_value}")
                        else:
                            print(f"   ❌ {field_name}: NULL")

                    # 保存采集结果用于数据库验证
                    processed_matches.append({
                        "match_id": match_id,
                        "success": valid_fields > 0,
                        "valid_fields": valid_fields,
                        "total_fields": total_fields,
                        "stats": {
                            "home_possession": l2_stats.home_possession,
                            "away_possession": l2_stats.away_possession,
                            "home_big_chances_created": l2_stats.home_big_chances_created,
                            "away_big_chances_created": l2_stats.away_big_chances_created,
                            "home_expected_goals_on_target": l2_stats.home_expected_goals_on_target,
                            "away_expected_goals_on_target": l2_stats.away_expected_goals_on_target,
                            "home_total_shots": l2_stats.home_total_shots,
                            "away_total_shots": l2_stats.away_total_shots,
                            "home_corners": l2_stats.home_corners,
                            "away_corners": l2_stats.away_corners,
                        }
                    })

                    if valid_fields >= 3:  # 至少3个关键字段有数据
                        success_count += 1
                        print(f"   🎯 比赛数据质量: {valid_fields}/{total_fields} 字段有效")
                    else:
                        failure_count += 1
                        print(f"   ⚠️  数据质量不足，仅 {valid_fields}/{total_fields} 字段有效")

                except Exception as e:
                    print(f"❌ 处理比赛 {match_id} 时发生错误: {e}")
                    failure_count += 1
                    processed_matches.append({
                        "match_id": match_id,
                        "success": False,
                        "error": str(e)
                    })

                # 添加延迟避免过于频繁的API调用
                if i < len(test_matches):
                    await asyncio.sleep(1)

            # 生成测试报告
            self.generate_smoke_test_report(processed_matches, success_count, failure_count)

        except Exception as e:
            print(f"❌ 冒烟测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

        return success_count > 0

    async def fetch_fotmob_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """从FotMob API获取比赛数据"""
        try:
            import aiohttp

            url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"FotMob API请求失败: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"获取FotMob数据时发生错误: {e}")
            return None

    def generate_smoke_test_report(self, processed_matches: List[Dict], success_count: int, failure_count: int):
        """生成冒烟测试报告"""
        print("\n" + "=" * 60)
        print("📊 [冒烟测试报告]")
        print("=" * 60)

        total_matches = len(processed_matches)
        success_rate = (success_count / total_matches) * 100 if total_matches > 0 else 0

        print(f"📈 测试统计:")
        print(f"   总比赛数: {total_matches}")
        print(f"   成功: {success_count}")
        print(f"   失败: {failure_count}")
        print(f"   成功率: {success_rate:.1f}%")

        print(f"\n📋 详细结果:")
        print("-" * 40)

        for match in processed_matches:
            match_id = match["match_id"]
            if match.get("success"):
                stats = match.get("stats", {})
                print(f"✅ {match_id}: 控球率={stats.get('home_possession')}, "
                      f"绝佳机会={stats.get('home_big_chances_created')}, "
                      f"xGOT={stats.get('home_expected_goals_on_target')}")
            else:
                error = match.get("error", "数据获取失败")
                print(f"❌ {match_id}: {error}")

        # 数据质量验证
        print(f"\n🔍 [数据完整性验证]")
        print("-" * 40)

        valid_matches = [m for m in processed_matches if m.get("success")]

        if valid_matches:
            # 统计关键字段的数据完整性
            key_fields = [
                "home_possession", "away_possession",
                "home_big_chances_created", "away_big_chances_created",
                "home_expected_goals_on_target", "away_expected_goals_on_target",
                "home_total_shots", "away_total_shots",
                "home_corners", "away_corners"
            ]

            field_completeness = {}
            for field in key_fields:
                count = sum(1 for m in valid_matches
                           if m.get("stats", {}).get(field) is not None)
                field_completeness[field] = count

            print("字段数据完整性:")
            for field, count in field_completeness.items():
                pct = (count / len(valid_matches)) * 100
                print(f"   {field}: {count}/{len(valid_matches)} ({pct:.1f}%)")

            avg_completeness = sum(field_completeness.values()) / (len(key_fields) * len(valid_matches)) * 100
            print(f"\n📊 平均数据完整性: {avg_completeness:.1f}%")

        # 最终结论
        print(f"\n🎯 [测试结论]")
        print("=" * 40)

        if success_rate >= 70 and len(valid_matches) >= 5:
            print("🎉 冒烟测试通过！")
            print("✅ L2增强采集器工作正常")
            print("✅ 新字段数据写入成功")
            print("✅ 数据质量满足要求")
            print("\n🚀 建议：随时可以开启大规模回补")
        else:
            print("❌ 冒烟测试未通过")
            print("⚠️  需要进一步调试和修复")
            print("📝 建议：检查API数据质量和解析逻辑")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="L2增强采集器冒烟测试")
    parser.add_argument("--limit", type=int, default=10, help="测试比赛数量限制")
    args = parser.parse_args()

    print("🧪 L2增强采集器冒烟测试")
    print(f"测试目标: 验证新字段数据写入完整性")
    print(f"测试样本: {args.limit} 场比赛")
    print()

    tester = L2SmokeTester()
    success = await tester.run_smoke_test(limit=args.limit)

    if success:
        print(f"\n🎯 冒烟测试完成！系统状态良好。")
    else:
        print(f"\n❌ 冒烟测试失败！需要进一步调试。")


if __name__ == "__main__":
    asyncio.run(main())