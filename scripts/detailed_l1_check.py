#!/usr/bin/env python3
"""
详细检查L1数据
Detailed L1 Data Check

数据架构师 - 详细检查找到的比赛数据结构
"""

import requests
import json
import re


def detailed_l1_check():
    """详细检查L1数据"""
    print("🔬" + "=" * 70)
    print("📊 详细L1数据检查")
    print("👨‍💻 数据架构师 - 深度检查比赛数据结构")
    print("=" * 72)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    # 使用有数据的日期
    date = "20241204"
    url = f"https://www.fotmob.com/matches?date={date}"

    print(f"\n📅 检查日期: {date}")
    print(f"📡 URL: {url}")

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

                # 深度检查fallback数据
                if "props" in nextjs_data and "pageProps" in nextjs_data["props"]:
                    page_props = nextjs_data["props"]["pageProps"]

                    if "fallback" in page_props:
                        fallback = page_props["fallback"]
                        print("\n🎯 Fallback数据分析:")
                        print(f"   总Keys: {len(fallback)}")
                        print(f"   Keys: {list(fallback.keys())}")

                        # 详细检查每个key
                        for key, value in fallback.items():
                            print(f"\n📋 Key: {key}")
                            print(f"   类型: {type(value).__name__}")

                            if isinstance(value, dict):
                                print(f"   Keys: {list(value.keys())}")

                                # 特别检查包含matches的key
                                if "matches" in value:
                                    matches_data = value["matches"]
                                    print("   🎯 发现matches数据!")
                                    print(f"      类型: {type(matches_data).__name__}")
                                    print(
                                        f"      长度: {len(matches_data) if isinstance(matches_data, list) else 'N/A'}"
                                    )

                                    if (
                                        isinstance(matches_data, list)
                                        and len(matches_data) > 0
                                    ):
                                        print("      🏆 第一场比赛分析:")
                                        first_match = matches_data[0]

                                        if isinstance(first_match, dict):
                                            print(
                                                f"         Keys: {list(first_match.keys())}"
                                            )

                                            # 检查关键信息
                                            essential_keys = [
                                                "id",
                                                "homeTeam",
                                                "awayTeam",
                                                "status",
                                                "tournamentId",
                                            ]
                                            for essential_key in essential_keys:
                                                if essential_key in first_match:
                                                    print(
                                                        f"         ✅ {essential_key}: {first_match[essential_key]}"
                                                    )
                                                else:
                                                    print(
                                                        f"         ❌ {essential_key}: 缺失"
                                                    )

                                            # 检查嵌套的team数据
                                            if (
                                                "homeTeam" in first_match
                                                and isinstance(
                                                    first_match["homeTeam"], dict
                                                )
                                            ):
                                                home_team = first_match["homeTeam"]
                                                print(
                                                    f"         🔵 主队: {home_team.get('name', 'Unknown')} (ID: {home_team.get('id', 'Unknown')})"
                                                )

                                            if (
                                                "awayTeam" in first_match
                                                and isinstance(
                                                    first_match["awayTeam"], dict
                                                )
                                            ):
                                                away_team = first_match["awayTeam"]
                                                print(
                                                    f"         🔴 客队: {away_team.get('name', 'Unknown')} (ID: {away_team.get('id', 'Unknown')})"
                                                )

                                            # 检查联赛信息
                                            if (
                                                "tournament" in first_match
                                                and isinstance(
                                                    first_match["tournament"], dict
                                                )
                                            ):
                                                tournament = first_match["tournament"]
                                                print(
                                                    f"         🏆 联赛: {tournament.get('name', 'Unknown')}"
                                                )

                                            # 显示完整的第一场比赛数据
                                            print("         📊 完整数据:")
                                            print(
                                                f"            {json.dumps(first_match, indent=12, ensure_ascii=False)}"
                                            )

                                            return True

                            elif isinstance(value, list):
                                print(f"   长度: {len(value)}")
                                if len(value) > 0 and isinstance(value[0], dict):
                                    print(f"   首项Keys: {list(value[0].keys())}")

                            else:
                                print(f"   值: {str(value)[:100]}...")

                # 检查其他可能的数据位置
                print("\n🔍 搜索其他数据位置...")
                search_alternative_locations(nextjs_data)

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback

        print(traceback.format_exc())

    return False


def search_alternative_locations(data):
    """搜索其他可能的数据位置"""
    locations_to_check = ["query", "buildId", "props.context", "props.url"]

    for location in locations_to_check:
        keys = location.split(".")
        current = data

        try:
            for key in keys:
                current = current[key]

            print(f"📍 {location}: {type(current).__name__}")
            if isinstance(current, (dict, list)):
                data_size = len(str(current))
                if data_size > 1000:
                    print(f"   大小: {data_size:,} 字符")
                    if isinstance(current, dict):
                        print(f"   Keys: {list(current.keys())[:5]}")

        except (KeyError, TypeError):
            continue


def check_api_directly():
    """直接检查API"""
    print("\n🔌 尝试直接API调用...")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.fotmob.com/matches",
        }
    )

    # 基于HTML中发现的API模式
    api_urls = [
        "https://www.fotmob.com/api/allLeagues?country=World",
        "https://www.fotmob.com/api/matches?date=20241204",
        "https://www.fotmob.com/api/leagues?id=47&season=2023/2024",  # Premier League
    ]

    for api_url in api_urls:
        print(f"\n📡 测试API: {api_url}")

        try:
            response = session.get(api_url, timeout=15)
            print(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print("   ✅ API响应成功")
                    print(f"   数据类型: {type(data)}")

                    if isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())[:10]}")

                        # 检查是否包含比赛数据
                        if any(
                            key in data
                            for key in ["matches", "games", "fixtures", "events"]
                        ):
                            print("   🎯 可能包含比赛数据!")

                    elif isinstance(data, list):
                        print(f"   列表长度: {len(data)}")
                        if len(data) > 0 and isinstance(data[0], dict):
                            print(f"   首项Keys: {list(data[0].keys())[:5]}")

                except json.JSONDecodeError:
                    content = response.text[:200]
                    print(f"   ❌ JSON解析失败，内容预览: {content}")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")


if __name__ == "__main__":
    print("🚀 详细L1数据检查启动...")

    # 详细检查
    success = detailed_l1_check()

    if not success:
        # 尝试API调用
        check_api_directly()

    print("\n" + "=" * 72)
    if success:
        print("🎉 数据架构师结论: L1 HTML解析可行!")
        print("✅ 发现完整比赛数据结构，可以开发HTML L1采集器")
    else:
        print("🎯 数据架构师结论: 需要进一步研究")
        print("⚠️ 当前L1 HTML数据结构复杂，建议保持混合架构")
