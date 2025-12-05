#!/usr/bin/env python3
"""
从FotMob首页查找当前比赛
Find Current Matches from FotMob Homepage

从首页提取当前正在进行的比赛ID
"""

import requests
import json
import re
from typing import List


def find_current_matches():
    """从首页查找当前比赛"""
    print("🔍" + "=" * 60)
    print("📋 从FotMob首页查找当前比赛")
    print("👨‍💻 寻找真实可用的比赛ID")
    print("=" * 62)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    try:
        # 访问FotMob首页
        url = "https://www.fotmob.com"
        print(f"\n📡 访问首页: {url}")

        response = session.get(url, timeout=30)
        print(f"   📊 状态码: {response.status_code}")
        print(f"   📏 响应大小: {len(response.text):,} 字符")

        if response.status_code == 200:
            html = response.text

            # 查找Next.js数据
            if "__NEXT_DATA__" in html:
                print("   ✅ 发现Next.js数据")

                # 提取Next.js数据
                pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
                matches = re.findall(pattern, html, re.DOTALL)

                if matches:
                    try:
                        nextjs_data = json.loads(matches[0])
                        print("   ✅ Next.js数据解析成功")

                        # 保存首页数据
                        with open(
                            "homepage_nextjs_data.json", "w", encoding="utf-8"
                        ) as f:
                            json.dump(nextjs_data, f, indent=2, ensure_ascii=False)
                        print("   💾 数据已保存到: homepage_nextjs_data.json")

                        # 查找比赛相关数据
                        props = nextjs_data.get("props", {})
                        page_props = props.get("pageProps", {})

                        if page_props:
                            print(f"   📋 PageProps Keys: {list(page_props.keys())}")

                            # 查找可能的比赛数据
                            for key, value in page_props.items():
                                if isinstance(value, dict) or isinstance(value, list):
                                    value_str = json.dumps(value).lower()
                                    if any(
                                        keyword in value_str
                                        for keyword in [
                                            "match",
                                            "game",
                                            "fixture",
                                            "id",
                                        ]
                                    ):
                                        print(f"   🎯 {key}: 可能包含比赛数据")

                                        # 查找比赛ID
                                        match_ids = extract_match_ids_from_data(value)
                                        if match_ids:
                                            print(f"      🏆 发现比赛ID: {match_ids}")
                        else:
                            print("   ⚠️ PageProps为空")

                            # 检查其他结构
                            print("   🔍 检查其他数据结构:")
                            for key, value in props.items():
                                if isinstance(value, dict) and value:
                                    print(
                                        f"      Props.{key}: {list(value.keys())[:5]}"
                                    )

                    except json.JSONDecodeError as e:
                        print(f"   ❌ Next.js数据解析失败: {e}")

            # 在HTML中查找比赛ID模式
            print("\n🔍 在HTML内容中搜索比赛ID模式...")

            # 查找可能的比赛ID模式
            patterns = [
                r"/match/(\d+)",
                r'"matchId":\s*"(\d+)"',
                r'"id":\s*"(\d+)"',
                r"match/(\d+)",
                r'"match":\s*{[^}]*"id":\s*"(\d+)"',
            ]

            found_ids = []
            for pattern in patterns:
                matches = re.findall(pattern, html)
                if matches:
                    print(f"   📋 模式 {pattern[:30]}...: 找到 {len(matches)} 个")
                    found_ids.extend(matches)

            # 去重并过滤可能的比赛ID
            unique_ids = list(set(found_ids))
            likely_match_ids = [
                mid for mid in unique_ids if len(mid) >= 6 and len(mid) <= 8
            ]

            if likely_match_ids:
                print(f"   🏆 可能的比赛ID: {likely_match_ids[:10]}")
                return likely_match_ids[:5]  # 返回前5个最可能的

        else:
            print(f"   ❌ 首页访问失败: {response.status_code}")

    except Exception as e:
        print(f"   ❌ 访问失败: {e}")

    return []


def extract_match_ids_from_data(data) -> list[str]:
    """从数据中提取比赛ID"""
    match_ids = []

    if isinstance(data, dict):
        for key, value in data.items():
            # 查找可能的比赛ID键
            if key.lower() in ["id", "matchid", "match_id", "gameid", "fixtureid"]:
                if isinstance(value, str) and value.isdigit() and len(value) >= 6:
                    match_ids.append(value)
                elif isinstance(value, int) and value >= 100000:
                    match_ids.append(str(value))

            # 递归搜索
            if isinstance(value, (dict, list)):
                match_ids.extend(extract_match_ids_from_data(value))

    elif isinstance(data, list):
        for item in data:
            match_ids.extend(extract_match_ids_from_data(item))

    return match_ids


def test_found_match_ids(match_ids: list[str]):
    """测试找到的比赛ID"""
    print("\n🧪 测试找到的比赛ID...")
    print("=" * 50)

    if not match_ids:
        print("   ⚠️ 没有找到可测试的比赛ID")
        return None

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    for match_id in match_ids:
        print(f"\n🎯 测试比赛ID: {match_id}")
        url = f"https://www.fotmob.com/match/{match_id}"

        try:
            response = session.get(url, timeout=15)
            print(f"   📊 状态码: {response.status_code}")
            print(f"   📏 大小: {len(response.text):,} 字符")

            if response.status_code == 200:
                print("   ✅ 200 - 可能是有效比赛!")

                # 检查内容
                content_lower = response.text.lower()
                football_keywords = ["lineup", "shot", "goal", "xg", "possession"]
                found_keywords = [kw for kw in football_keywords if kw in content_lower]

                if found_keywords:
                    print(f"   🎉 发现关键词: {found_keywords}")
                    print(f"   🏆🏆🏆 找到有效比赛: {match_id}!")
                    return match_id
                else:
                    print("   ⚠️ 未发现足球关键词")

            elif response.status_code == 404:
                print("   ❌ 404 - 页面不存在")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")

    return None


def main():
    """主函数"""
    print("🚀 查找当前比赛启动...")

    # 1. 从首页查找比赛ID
    match_ids = find_current_matches()

    # 2. 测试找到的比赛ID
    if match_ids:
        valid_match_id = test_found_match_ids(match_ids)

        if valid_match_id:
            print("\n" + "🎉" * 20)
            print(f"🏆 成功找到有效比赛ID: {valid_match_id}")
            print("🚀 可以使用此ID测试数据采集器")
            print("🎉" * 20)
            return valid_match_id

    print("\n❌ 未找到有效的比赛ID")
    print("💡 建议手动访问FotMob网站获取当前比赛ID")
    return None


if __name__ == "__main__":
    valid_id = main()
    if valid_id:
        print(f"\n📝 找到有效ID: {valid_id}")
    else:
        print("\n⚠️ 需要手动获取比赛ID")
