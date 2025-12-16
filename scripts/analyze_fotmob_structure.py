#!/usr/bin/env python3
"""
分析FotMob数据结构

深度分析fotmob_match_data.json的数据结构，寻找统计数据位置
"""

import json
from pathlib import Path

def analyze_data_structure():
    """分析FotMob数据结构"""
    print("🔍 开始分析FotMob数据结构...")
    print("=" * 80)

    # 加载测试数据
    test_data_path = Path("fotmob_match_data.json")
    if not test_data_path.exists():
        print(f"❌ 测试数据文件不存在: {test_data_path}")
        return False

    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"✅ 成功加载测试数据: {test_data_path}")
    print(f"   文件大小: {test_data_path.stat().st_size / 1024:.1f} KB")

    # 分析顶级结构
    print(f"\n📋 顶级数据结构:")
    if isinstance(test_data, dict):
        for i, (key, value) in enumerate(test_data.items(), 1):
            value_type = type(value).__name__
            if isinstance(value, dict):
                print(f"   {i:2d}. {key}: {value_type} ({len(value)} 个字段)")
            elif isinstance(value, list):
                print(f"   {i:2d}. {key}: {value_type} ({len(value)} 个元素)")
            else:
                value_preview = str(value)[:50]
                print(f"   {i:2d}. {key}: {value_type} = {value_preview}")

    # 提取content部分
    if "content" not in test_data:
        print("❌ 测试数据中缺少content字段")
        return False

    content = test_data["content"]
    print(f"\n📊 Content 数据结构分析:")
    print(f"   类型: {type(content).__name__}")

    if isinstance(content, dict):
        print(f"   字段数量: {len(content)}")

        # 足球关键词
        football_keywords = [
            "stat", "data", "performance", "metrics", "figures",
            "numbers", "analysis", "summary", "overview", "match",
            "team", "player", "shot", "goal", "pass", "tackle",
            "possess", "corner", "card", "foul", "offside"
        ]

        print(f"\n🎯 潜在统计数据字段:")
        stats_candidates = []

        for key, value in content.items():
            key_lower = key.lower()
            is_football_related = any(keyword in key_lower for keyword in football_keywords)

            if is_football_related:
                stats_candidates.append((key, value))
                value_type = type(value).__name__
                if isinstance(value, dict):
                    print(f"   ✅ {key}: {value_type} ({len(value)} 个字段)")

                    # 显示前几个子字段
                    sub_fields = list(value.keys())[:5]
                    print(f"      子字段: {', '.join(sub_fields)}")

                    # 查找足球统计相关的子字段
                    football_sub_fields = [
                        sub_key for sub_key in value.keys()
                        if any(keyword in sub_key.lower() for keyword in football_keywords)
                    ]
                    if football_sub_fields:
                        print(f"      🏈 足球统计字段: {', '.join(football_sub_fields[:3])}")

                elif isinstance(value, list):
                    print(f"   ✅ {key}: {value_type} ({len(value)} 个元素)")
                    if len(value) > 0:
                        first_item = value[0]
                        if isinstance(first_item, dict):
                            print(f"      首个元素字段数: {len(first_item)}")
                            sub_fields = list(first_item.keys())[:5]
                            print(f"      首个元素字段: {', '.join(sub_fields)}")
                else:
                    value_preview = str(value)[:100]
                    print(f"   ✅ {key}: {value_type} = {value_preview}")

        print(f"\n🔍 深度分析候选统计数据...")

        # 深度分析每个候选字段
        for key, value in stats_candidates:
            print(f"\n📊 深度分析字段: {key}")
            analyze_deep_structure(value, key, max_depth=3)

    print(f"\n🎯 数据结构分析完成")
    return True

def analyze_deep_structure(obj, path="", max_depth=3, current_depth=0):
    """递归分析数据结构"""
    indent = "  " * current_depth

    if current_depth >= max_depth:
        print(f"{indent}   (达到最大深度 {max_depth})")
        return

    if isinstance(obj, dict):
        print(f"{indent}📋 字典: {len(obj)} 个字段")

        # 足球关键词
        football_keywords = [
            "big chance", "pass", "tackle", "shot", "goal", "possess",
            "corner", "card", "foul", "offside", "xg", "expected"
        ]

        football_fields = []
        for key, value in obj.items():
            key_lower = key.lower()
            if any(keyword in key_lower for keyword in football_keywords):
                football_fields.append(key)

        if football_fields:
            print(f"{indent}   ⚽ 足球相关字段: {', '.join(football_fields[:5])}")

        # 显示前几个字段
        for i, (key, value) in enumerate(obj.items(), 1):
            if i > 5:  # 只显示前5个字段
                print(f"{indent}   ... 还有 {len(obj) - 5} 个字段")
                break

            current_path = f"{path}.{key}" if path else key
            value_type = type(value).__name__

            if isinstance(value, (str, int, float)):
                value_preview = str(value)[:50]
                print(f"{indent}   {i:2d}. {key}: {value_type} = {value_preview}")
            else:
                print(f"{indent}   {i:2d}. {key}: {value_type}")

    elif isinstance(obj, list):
        print(f"{indent}📋 列表: {len(obj)} 个元素")
        if len(obj) > 0:
            first_item = obj[0]
            item_type = type(first_item).__name__
            print(f"{indent}   首个元素类型: {item_type}")

            if isinstance(first_item, dict):
                print(f"{indent}   首个元素字段数: {len(first_item)}")

                # 递归分析第一个元素
                analyze_deep_structure(first_item, f"{path}[0]", max_depth, current_depth + 1)
            else:
                value_preview = str(first_item)[:50]
                print(f"{indent}   首个元素值: {value_preview}")
    else:
        value_preview = str(obj)[:100]
        print(f"{indent}📋 基础类型: {type(obj).__name__} = {value_preview}")

def main():
    """主函数"""
    print("🚀 FotMob数据结构分析工具")
    print("🎯 目标: 深度分析数据结构，寻找统计数据位置")
    print()

    success = analyze_data_structure()

    print("\n" + "=" * 80)
    if success:
        print("🏆 数据结构分析完成！")
        print("✨ 现在可以基于分析结果优化统计数据提取逻辑")
    else:
        print("❌ 数据结构分析失败")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)