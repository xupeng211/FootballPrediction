#!/usr/bin/env python3
"""
深度数据分析脚本
Deep Data Analysis Script

数据分析师 & QA工程师 - 深度解析HTML数据结构
"""

import requests
import json
import re


def deep_analyze_data(match_id: str):
    """深度分析数据结构"""
    print("🔬" + "=" * 70)
    print("🔍 深度数据分析")
    print(f"👨‍💻 数据分析师 & QA工程师 - 深度解析比赛 {match_id}")
    print("=" * 72)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    try:
        url = f"https://www.fotmob.com/match/{match_id}"
        response = session.get(url, timeout=30)

        if response.status_code in [200, 404]:
            html = response.text

            # 提取Next.js数据
            pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL)

            if matches:
                nextjs_data = json.loads(matches[0])
                print("✅ Next.js数据提取成功")

                # 深度分析props数据结构
                if "props" in nextjs_data:
                    props = nextjs_data["props"]
                    analyze_structure(props, "props", max_depth=4)

                    # 特别分析pageProps
                    if "pageProps" in props:
                        page_props = props["pageProps"]
                        analyze_structure(page_props, "pageProps", max_depth=5)

                        # 查找API数据
                        if "fallback" in page_props:
                            fallback = page_props["fallback"]
                            print("\n🎯 Fallback数据分析:")
                            print(f"   Keys数量: {len(fallback)}")

                            for key, value in fallback.items():
                                if (
                                    isinstance(value, (dict, list))
                                    and len(str(value)) > 1000
                                ):
                                    print(
                                        f"   📦 大数据: {key} ({len(str(value)):,} 字符)"
                                    )

                                    if isinstance(value, dict):
                                        analyze_structure(
                                            value, f"fallback.{key}", max_depth=3
                                        )
                                    elif isinstance(value, list) and value:
                                        print(
                                            f"      首项类型: {type(value[0]).__name__}"
                                        )

                    # 搜索所有可能的数据
                    print("\n🔍 全面搜索比赛相关数据...")
                    search_all_data(nextjs_data)

        else:
            print(f"❌ HTTP错误: {response.status_code}")

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback

        print(traceback.format_exc())


def analyze_structure(obj, path: str, max_depth: int = 3, current_depth: int = 0):
    """分析数据结构"""
    if current_depth > max_depth:
        return

    indent = "   " * current_depth
    print(f"{indent}📍 {path}: {type(obj).__name__}")

    if isinstance(obj, dict):
        # 只显示重要keys
        keys = list(obj.keys())
        if len(keys) <= 5:
            print(f"{indent}   Keys: {keys}")
        else:
            print(f"{indent}   Keys: {keys[:5]}... (+{len(keys)-5})")

        # 递归分析重要的子项
        important_keys = [
            "content",
            "data",
            "stats",
            "shotmap",
            "lineups",
            "odds",
            "matches",
            "matchData",
        ]
        for key in important_keys:
            if key in obj and isinstance(obj[key], (dict, list)):
                analyze_structure(
                    obj[key], f"{path}.{key}", max_depth, current_depth + 1
                )

    elif isinstance(obj, list):
        print(f"{indent}   长度: {len(obj)}")
        if len(obj) > 0:
            first_item = obj[0]
            if isinstance(first_item, dict):
                item_keys = list(first_item.keys())
                if len(item_keys) <= 3:
                    print(f"{indent}   首项Keys: {item_keys}")
                else:
                    print(f"{indent}   首项Keys: {item_keys[:3]}...")

                # 检查是否包含关键数据
                data_indicators = [
                    "id",
                    "name",
                    "rating",
                    "xg",
                    "expectedGoals",
                    "team",
                    "player",
                ]
                found_indicators = [
                    ind for ind in data_indicators if ind in str(first_item).lower()
                ]
                if found_indicators:
                    print(f"{indent}   🎯 包含指示器: {found_indicators}")


def search_all_data(obj, path: str = "", max_depth: int = 3, current_depth: int = 0):
    """搜索所有数据"""
    if current_depth > max_depth:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key

            # 检查是否是我们要找的数据
            key_lower = key.lower()
            obj_str = str(value).lower()

            # 搜索目标数据
            target_patterns = {
                "shotmap": ["shotmap", "shot", "xg", "expectedgoals"],
                "stats": ["stats", "statistics", "possession", "big chances"],
                "lineups": ["lineup", "player", "rating", "starting"],
                "odds": ["odds", "betting", "1x2", "bet365"],
            }

            for category, patterns in target_patterns.items():
                if any(pattern in key_lower for pattern in patterns):
                    print(f"\n🎯 发现{category}数据: {new_path}")
                    print(f"   类型: {type(value).__name__}")

                    if isinstance(value, dict):
                        print(f"   Keys: {list(value.keys())[:5]}")

                        # 查找具体值
                        if category == "stats" and "possession" in obj_str:
                            print("   ✅ 包含控球率数据")
                        if category == "lineups" and "rating" in obj_str:
                            print("   ✅ 包含球员评分数据")

                    elif isinstance(value, list):
                        print(f"   长度: {len(value)}")
                        if len(value) > 0:
                            first_item = value[0]
                            if isinstance(first_item, dict):
                                print(f"   首项Keys: {list(first_item.keys())[:3]}")

            # 递归搜索
            search_all_data(value, new_path, max_depth, current_depth + 1)

    elif isinstance(obj, list) and len(obj) > 0 and current_depth < max_depth:
        # 只检查前几个元素
        for i, item in enumerate(obj[:3]):
            search_all_data(item, f"{path}[{i}]", max_depth, current_depth + 1)


def test_known_working_match():
    """测试已知工作的比赛"""
    print("\n🎯 测试已知工作的比赛ID...")

    # 使用之前HTML采集器测试成功的比赛ID
    known_matches = ["53_2023/2024_0294"]  # 这个之前测试过有效

    for match_id in known_matches:
        deep_analyze_data(match_id)


if __name__ == "__main__":
    print("🚀 深度数据分析启动...")

    # 测试已知工作的比赛
    test_known_working_match()

    # 也测试一些其他比赛
    print("\n" + "=" * 72)
    deep_analyze_data("4189362")
