#!/usr/bin/env python3
"""
验证Catch-All统计数据提取功能

测试新添加的match_detailed_stats字段是否成功提取Big Chances、Passes等详细统计数据
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent / "FootballPrediction" / "src"))

from collectors.enhanced_fotmob_collector import EnhancedFotMobCollector

def test_catch_all_stats_extraction():
    """测试Catch-All统计数据提取"""
    print("🚀 开始测试Catch-All统计数据提取")
    print("=" * 80)

    # 加载测试数据
    test_data_path = Path("fotmob_match_data.json")
    if not test_data_path.exists():
        print(f"❌ 测试数据文件不存在: {test_data_path}")
        return False

    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"✅ 成功加载测试数据: {test_data_path}")

    # 提取content部分
    if "content" not in test_data:
        print("❌ 测试数据中缺少content字段")
        return False

    content = test_data["content"]

    # 创建collector实例并测试深度统计提取
    collector = EnhancedFotMobCollector()

    print("\n🔬 开始Catch-All统计提取测试...")
    deep_stats = collector._extract_deep_stats(content)

    print("\n📊 Catch-All统计提取结果:")
    print(f"   射图谱数据: {len(deep_stats['match_shotmap'])} 个射门")
    print(f"   势头数据: {len(deep_stats['match_momentum'])} 个数据点")
    print(f"   主队教练: {deep_stats['home_coach']}")
    print(f"   客队教练: {deep_stats['away_coach']}")
    print(f"   主队板凳评分: {deep_stats['home_bench_rating']}")
    print(f"   客队板凳评分: {deep_stats['away_bench_rating']}")
    print(f"   详细统计数据: {len(deep_stats['match_detailed_stats'])} 个字段")

    # 详细分析详细统计数据
    detailed_stats = deep_stats['match_detailed_stats']
    if detailed_stats:
        print("\n🎯 详细统计数据内容分析:")
        print(f"   数据源结构: {type(detailed_stats)}")

        if isinstance(detailed_stats, dict):
            print(f"   统计字段数量: {len(detailed_stats)}")

            # 查找关键统计指标
            key_stats = [
                "Big Chances", "Passes", "Passes Accuracy", "Tackles",
                "Possession", "Shots", "Shots on Target", "xG", "Goals",
                "Assists", "Yellow Cards", "Red Cards", "Fouls", "Corners",
                "Offsides", "Saves", "Crosses", "Interceptions", "Aerials"
            ]

            found_stats = []
            for stat in key_stats:
                # 模糊匹配统计字段名
                matching_keys = [k for k in detailed_stats.keys()
                               if stat.lower() in k.lower() or k.lower() in stat.lower()]
                if matching_keys:
                    found_stats.extend(matching_keys)
                    print(f"   ✅ 找到相关统计: {stat} -> {matching_keys}")

            # 显示所有可用的统计字段
            print(f"\n📋 所有可用统计字段 ({len(detailed_stats)}个):")
            for i, key in enumerate(detailed_stats.keys(), 1):
                value = detailed_stats[key]
                value_preview = str(value)[:100] if value is not None else "None"
                print(f"   {i:2d}. {key}: {value_preview}")

            # 检查是否包含关键统计
            success_indicators = [
                "Big Chances" in str(detailed_stats),
                any("pass" in str(k).lower() for k in detailed_stats.keys()),
                any("tackle" in str(k).lower() for k in detailed_stats.keys()),
                any("shot" in str(k).lower() for k in detailed_stats.keys()),
                any("possess" in str(k).lower() for k in detailed_stats.keys()),
            ]

            catch_all_success = any(success_indicators)

            print(f"\n🎯 Catch-All提取成功指标:")
            print(f"   包含Big Chances: {'✅' if success_indicators[0] else '❌'}")
            print(f"   包含Passes相关: {'✅' if success_indicators[1] else '❌'}")
            print(f"   包含Tackles相关: {'✅' if success_indicators[2] else '❌'}")
            print(f"   包含Shots相关: {'✅' if success_indicators[3] else '❌'}")
            print(f"   包含Possession相关: {'✅' if success_indicators[4] else '❌'}")

            if catch_all_success:
                print("\n🎉 Catch-All统计数据提取成功！")
                print("✨ 成功捕获到详细的足球统计数据")
                return True
            else:
                print("\n⚠️ Catch-All统计数据提取部分成功")
                print("🔧 需要进一步分析数据结构")
                return False
        else:
            print(f"   ❌ 详细统计数据格式异常: {type(detailed_stats)}")
            return False
    else:
        print("   ❌ 没有提取到详细统计数据")
        return False

def analyze_data_structure(content):
    """分析FotMob数据结构，寻找统计数据位置"""
    print("\n🔍 分析FotMob数据结构...")

    def analyze_object(obj, path="", max_depth=5, current_depth=0):
        if current_depth >= max_depth:
            return

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                # 检查是否是统计相关的字段
                if any(keyword in key.lower() for keyword in [
                    'stat', 'data', 'performance', 'metrics', 'figures',
                    'numbers', 'analysis', 'summary', 'overview'
                ]):
                    print(f"🎯 发现统计相关字段: {current_path} ({type(value)})")

                    if isinstance(value, (dict, list)):
                        if isinstance(value, dict):
                            print(f"   包含 {len(value)} 个子字段")
                            # 显示前几个子字段
                            for sub_key in list(value.keys())[:5]:
                                print(f"     - {sub_key}")
                        elif isinstance(value, list):
                            print(f"   包含 {len(value)} 个列表项")

                # 递归分析
                analyze_object(value, current_path, max_depth, current_depth + 1)

        elif isinstance(obj, list) and len(obj) > 0:
            print(f"📋 列表 {path}: {len(obj)} 个元素")
            # 分析第一个元素
            analyze_object(obj[0], f"{path}[0]", max_depth, current_depth + 1)

    analyze_object(content)
    print("🔍 数据结构分析完成")

def main():
    """主函数"""
    print("🚀 Catch-All统计数据提取验证启动")
    print("🎯 目标: 验证match_detailed_stats字段成功提取Big Chances、Passes等详细统计")
    print()

    # 加载测试数据进行结构分析
    test_data_path = Path("fotmob_match_data.json")
    if test_data_path.exists():
        with open(test_data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        if "content" in test_data:
            print("📊 先分析数据结构...")
            analyze_data_structure(test_data["content"])
            print("\n" + "=" * 80)

    success = test_catch_all_stats_extraction()

    print("\n" + "=" * 80)
    if success:
        print("🏆 Catch-All统计数据提取验证通过！")
        print("✨ match_detailed_stats字段成功捕获详细足球统计")
    else:
        print("❌ Catch-All统计数据提取验证失败")
        print("🔧 需要进一步调试数据提取逻辑")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)