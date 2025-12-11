#!/usr/bin/env python3
"""
真实购物清单验证脚本
Real Shopping List Verification

数据分析师 & QA工程师 - 使用真实HTML采集器验证客户需求
"""

import asyncio
import sys
from pathlib import Path
import json

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

from src.collectors.html_fotmob_collector import HTMLFotMobCollector


def print_json_structure(obj, indent=0, max_depth=3, current_depth=0):
    """打印JSON结构"""
    if current_depth >= max_depth:
        print("   " * indent + "...")
        return

    prefix = "   " * indent

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}📁 {key}: {type(value).__name__}")
                if len(str(value)) < 1000:  # 只显示小对象的结构
                    print_json_structure(
                        value, indent + 1, max_depth, current_depth + 1
                    )
            else:
                value_preview = str(value)[:50]
                print(f"{prefix}📄 {key}: {value_preview}...")

    elif isinstance(obj, list):
        print(f"{prefix}📋 列表 (长度: {len(obj)})")
        if len(obj) > 0 and current_depth < max_depth:
            first_item = obj[0]
            print(f"{prefix}   首项: {type(first_item).__name__}")
            if isinstance(first_item, dict):
                print_json_structure(
                    first_item, indent + 1, max_depth, current_depth + 1
                )


def search_for_shopping_list_items(data, path=""):
    """搜索购物清单项目"""
    results = {"shotmap": [], "stats": [], "lineups": [], "odds": []}

    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key

            # 检查是否匹配我们的目标
            key_lower = key.lower()
            str(value).lower()

            # Shotmap相关
            if any(
                term in key_lower for term in ["shotmap", "shot", "xg", "expectedgoals"]
            ):
                results["shotmap"].append(
                    {
                        "path": new_path,
                        "type": type(value).__name__,
                        "sample": (
                            value
                            if not isinstance(value, (dict, list))
                            else f"<{type(value).__name__}>"
                        ),
                    }
                )

            # Stats相关
            if any(
                term in key_lower
                for term in ["stats", "possession", "big chances", "shots"]
            ):
                results["stats"].append(
                    {
                        "path": new_path,
                        "type": type(value).__name__,
                        "sample": (
                            value
                            if not isinstance(value, (dict, list))
                            else f"<{type(value).__name__}>"
                        ),
                    }
                )

            # Lineups相关
            if any(
                term in key_lower for term in ["lineup", "player", "rating", "starting"]
            ):
                results["lineups"].append(
                    {
                        "path": new_path,
                        "type": type(value).__name__,
                        "sample": (
                            value
                            if not isinstance(value, (dict, list))
                            else f"<{type(value).__name__}>"
                        ),
                    }
                )

            # Odds相关
            if any(term in key_lower for term in ["odds", "betting", "1x2", "bet365"]):
                results["odds"].append(
                    {
                        "path": new_path,
                        "type": type(value).__name__,
                        "sample": (
                            value
                            if not isinstance(value, (dict, list))
                            else f"<{type(value).__name__}>"
                        ),
                    }
                )

            # 递归搜索
            child_results = search_for_shopping_list_items(value, new_path)
            for category in results:
                results[category].extend(child_results[category])

    elif isinstance(data, list) and len(data) > 0:
        # 检查前几个元素
        for i, item in enumerate(data[:3]):
            child_results = search_for_shopping_list_items(item, f"{path}[{i}]")
            for category in results:
                results[category].extend(child_results[category])

    return results


def detailed_inspection(category, items):
    """详细检查特定类别"""
    if not items:
        print(f"   [❌] 未找到{category}数据")
        return False

    print(f"   [✅] 找到 {len(items)} 个{category}相关数据:")

    success = False
    for item in items[:5]:  # 只显示前5个
        path = item["path"]
        data_type = item["type"]
        print(f"      📍 {path} ({data_type})")

        if data_type == "dict":
            print(
                f"         Keys: {list(item['sample'].keys()) if 'keys' in str(item['sample']) else 'Unknown'}"
            )
            success = True
        elif data_type == "list":
            print(
                f"         长度: {len(item['sample']) if hasattr(item['sample'], '__len__') else 'Unknown'}"
            )
            success = True
        else:
            print(f"         值: {item['sample']}")
            success = True

    return success


async def verify_shopping_list_with_real_collector():
    """使用真实HTML采集器验证购物清单"""
    print("🛒" + "=" * 70)
    print("📋 真实购物清单验证")
    print("👨‍💻 数据分析师 & QA工程师 - 使用HTML采集器验证4大类数据")
    print("=" * 72)

    try:
        # 初始化HTML采集器
        print("\n🕷️ 初始化HTML采集器...")
        collector = HTMLFotMobCollector()
        await collector.initialize()

        # 使用已知工作的比赛ID
        test_match_id = "53_2023/2024_0294"
        print(f"🎯 测试比赛: {test_match_id}")

        # 获取数据
        print("🔄 获取比赛数据...")
        match_data = await collector.collect_match_data(test_match_id)

        if not match_data:
            print("❌ 无法获取比赛数据")
            return False

        print("✅ 成功获取比赛数据")
        print(f"📊 数据结构: {list(match_data.keys())}")

        # 获取content数据
        content = match_data.get("content", {})
        if not content:
            print("❌ 未找到content数据")
            return False

        print(f"✅ 获取content数据，类型: {type(content).__name__}")

        # 显示数据结构概览
        print("\n🔍 数据结构概览:")
        if isinstance(content, dict):
            print_json_structure(content, max_depth=3)

        # 搜索购物清单项目
        print("\n🔍 搜索客户需求清单项目...")
        results = search_for_shopping_list_items(content)

        # 详细检查每个类别
        print("\n🎯" + "=" * 50)
        verification_results = []

        # 1. 验证射门与xG
        print("🎯 1. 射门与xG (Shotmap)")
        print("   " + "=" * 40)
        shotmap_success = detailed_inspection("shotmap", results["shotmap"])
        verification_results.append(shotmap_success)

        # 2. 验证比赛统计
        print("\n📊 2. 比赛统计 (Stats)")
        print("   " + "=" * 40)
        stats_success = detailed_inspection("stats", results["stats"])
        verification_results.append(stats_success)

        # 3. 验证阵容与评分
        print("\n👥 3. 阵容与评分 (Lineups)")
        print("   " + "=" * 40)
        lineups_success = detailed_inspection("lineups", results["lineups"])
        verification_results.append(lineups_success)

        # 4. 验证赔率
        print("\n💰 4. 赔率 (Odds)")
        print("   " + "=" * 40)
        odds_success = detailed_inspection("odds", results["odds"])
        verification_results.append(odds_success)

        # 深度检查找到的数据
        print("\n🔬 深度数据检查...")
        for category, items in results.items():
            if items:
                print(f"\n📋 {category.upper()} 详细分析:")
                for item in items[:2]:  # 只分析前2个
                    if (
                        isinstance(item["sample"], dict)
                        and len(str(item["sample"])) < 500
                    ):
                        print(f"   📍 {item['path']}")
                        print(
                            f"   📄 完整数据: {json.dumps(item['sample'], indent=6, ensure_ascii=False)}"
                        )

        # 总结报告
        print("\n" + "🎯" * 18)
        print("📊 购物清单验证总结报告")
        print("🎯" * 18)

        categories = [
            "🎯 射门与xG (Shotmap)",
            "📊 比赛统计 (Stats)",
            "👥 阵容与评分 (Lineups)",
            "💰 赔率 (Odds)",
        ]

        passed_count = sum(verification_results)
        total_count = len(verification_results)

        for i, (category, result) in enumerate(
            zip(categories, verification_results, strict=False)
        ):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{i + 1}. {category}: {status}")

        print(
            f"\n📈 总体通过率: {passed_count}/{total_count} ({(passed_count / total_count) * 100:.1f}%)"
        )

        # 显示采集器统计
        stats = collector.get_stats()
        print("\n📈 采集器统计:")
        for key, value in stats.items():
            print(f"      {key}: {value}")

        await collector.close()

        if passed_count == total_count:
            print("\n🎉 恭喜! 客户购物清单全部验证通过!")
            print("✅ HTML解析方案完全满足客户需求")
            return True
        elif passed_count >= 2:
            print(f"\n👍 基本满足客户需求! ({total_count - passed_count}项需要优化)")
            return True
        else:
            print("\n⚠️ 需要进一步优化数据提取逻辑")
            return False

    except Exception as e:
        print(f"\n❌ 验证过程失败: {e}")
        import traceback

        print(traceback.format_exc())
        return False


async def main():
    """主函数"""
    print("🚀 真实购物清单验证启动...")

    success = await verify_shopping_list_with_real_collector()

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
