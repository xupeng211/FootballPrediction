#!/usr/bin/env python3
"""
深度分析L1数据结构
Deep Analysis of L1 Data Structure

数据架构师 - 深度分析L1 HTML数据的实际结构
"""

import requests
import json
import re

def extract_and_analyze_l1():
    """深度分析L1数据结构"""
    print("🔬" + "="*70)
    print("📊 L1数据结构深度分析")
    print("👨‍💻 数据架构师 - 深度解析HTML数据结构")
    print("="*72)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    url = "https://www.fotmob.com/matches?date=20241201"
    print(f"\n📡 分析L1页面: {url}")

    try:
        response = session.get(url, timeout=30)

        if response.status_code in [200, 404]:
            html = response.text

            # 提取Next.js数据
            pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL)

            if matches:
                nextjs_data = json.loads(matches[0])
                print("✅ Next.js数据解析成功")

                # 深度分析props数据结构
                if "props" in nextjs_data:
                    props = nextjs_data["props"]
                    print("\n🎯 Props数据结构分析:")
                    print(f"   Keys: {list(props.keys())}")

                    # 检查页面props
                    if "pageProps" in props:
                        page_props = props["pageProps"]
                        print(f"   pageProps Keys: {list(page_props.keys())}")

                        # 查找matches相关数据
                        find_all_matches_data(page_props, "")

                    else:
                        print("   ❌ 未找到pageProps")

                # 分析其他可能的数据位置
                print("\n🔍 全面搜索比赛数据...")
                search_all_paths(nextjs_data)

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        print(traceback.format_exc())

def find_all_matches_data(obj, path=""):
    """递归查找所有matches相关数据"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key

            # 检查是否是matches相关的key
            key_lower = key.lower()
            if any(term in key_lower for term in ["match", "league", "fixture", "game", "event", "data", "content"]):
                print(f"\n📋 发现潜在数据路径: {new_path}")
                print(f"   类型: {type(value).__name__}")

                if isinstance(value, dict):
                    print(f"   Keys: {list(value.keys())[:10]}")  # 只显示前10个

                    # 检查是否包含比赛列表
                    if any(league_term in str(value.keys()).lower() for league_term in ["premier", "la liga", "bundesliga", "serie a"]):
                        print("   ⚽ 可能包含联赛数据!")

                        # 尝试统计比赛数量
                        count_matches_in_structure(value, new_path)

                elif isinstance(value, list):
                    print(f"   长度: {len(value)}")
                    if len(value) > 0 and isinstance(value[0], dict):
                        print(f"   首个元素Keys: {list(value[0].keys())[:5]}")

                        if len(value) > 0:
                            count_matches_in_structure(value, new_path)

            # 递归搜索
            find_all_matches_data(value, new_path)

    elif isinstance(obj, list) and len(obj) > 0:
        # 对于列表，只检查前几个元素以避免过深递归
        for i, item in enumerate(obj[:3]):
            find_all_matches_data(item, f"{path}[{i}]")

def count_matches_in_structure(obj, path):
    """尝试统计结构中的比赛数量"""
    match_count = 0

    if isinstance(obj, dict):
        # 查找可能的比赛列表
        for key, value in obj.items():
            if isinstance(value, list):
                key_lower = key.lower()
                if any(term in key_lower for term in ["match", "fixture", "game", "event"]):
                    match_count += len(value)
                    print(f"   📊 {key}: {len(value)} 个项目")
                else:
                    # 检查列表项是否是比赛数据
                    if value and isinstance(value[0], dict):
                        sample = value[0]
                        if any(match_field in str(sample.keys()).lower() for match_field in ["team", "club", "home", "away", "score", "time"]):
                            match_count += len(value)
                            print(f"   📊 {key}: {len(value)} 个潜在比赛数据")

    elif isinstance(obj, list):
        # 直接检查列表
        if obj and isinstance(obj[0], dict):
            sample = obj[0]
            if any(match_field in str(sample.keys()).lower() for match_field in ["team", "club", "home", "away", "score", "time"]):
                match_count = len(obj)
                print(f"   📊 列表包含: {len(obj)} 个潜在比赛数据")

    if match_count > 0:
        print(f"   🎯 {path} 总计: {match_count} 个比赛数据")

def search_all_paths(obj, max_depth=3, current_depth=0, path=""):
    """全面搜索所有路径，找到包含实际数据的路径"""
    if current_depth > max_depth:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key

            # 检查这个路径是否包含大量数据
            if isinstance(value, (dict, list)):
                data_size = len(str(value))
                if data_size > 10000:  # 大于10KB的数据可能包含比赛列表
                    print(f"📦 大数据路径: {new_path} ({data_size:,} 字符)")

                    if isinstance(value, dict):
                        print(f"   Keys数量: {len(value)}")

                        # 显示一些key示例
                        sample_keys = list(value.keys())[:5]
                        print(f"   示例Keys: {sample_keys}")

                    elif isinstance(value, list):
                        print(f"   列表长度: {len(value)}")

                        if len(value) > 0 and isinstance(value[0], dict):
                            sample_item_keys = list(value[0].keys())[:5]
                            print(f"   首项Keys: {sample_item_keys}")

            # 递归搜索
            search_all_paths(value, max_depth, current_depth + 1, new_path)

    elif isinstance(obj, list) and len(obj) > 0 and current_depth < max_depth:
        # 检查列表的前几个元素
        for i in range(min(3, len(obj))):
            search_all_paths(obj[i], max_depth, current_depth + 1, f"{path}[{i}]")

if __name__ == "__main__":
    extract_and_analyze_l1()
