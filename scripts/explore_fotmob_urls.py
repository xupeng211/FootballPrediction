#!/usr/bin/env python3
"""
FotMob URL 探索器
FotMob URL Explorer

网页爬虫专家 - 探索正确的URL格式
"""

import requests
import re
from typing import List, Dict


def explore_fotmob_structure():
    """探索FotMob网站结构"""
    print("🔍" + "=" * 60)
    print("🌐 FotMob URL 结构探索")
    print("👨‍💻 网页爬虫专家 - 寻找正确URL格式")
    print("=" * 62)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    # 尝试不同的URL格式
    url_formats = [
        "https://www.fotmob.com/match/4189362",
        "https://www.fotmob.com/en/match/4189362",
        "https://fotmob.com/match/4189362",
        "https://www.fotmob.com/matches/4189362",
        "https://www.fotmob.com/fixtures/4189362",
        "https://fotmob.com/match/4189362/man-united-vs-manchester-city",
    ]

    working_urls = []

    for url in url_formats:
        print(f"\n📡 测试URL: {url}")
        try:
            response = session.get(url, timeout=15)
            print(f"   状态码: {response.status_code}")
            print(f"   内容长度: {len(response.text)}")

            if response.status_code == 200:
                working_urls.append(url)
                print("   ✅ SUCCESS! URL可用")

                # 分析页面结构
                html = response.text
                analyze_page_structure(html, url)

            elif response.status_code == 404:
                print("   ❌ 404 Not Found")
            elif response.status_code == 302:
                location = response.headers.get("location", "Unknown")
                print(f"   🔄 302 Redirect: {location}")
            else:
                print(f"   ⚠️ 其他状态: {response.status_code}")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")

    # 尝试从首页找到最近的比赛
    print("\n🏠 从首页寻找比赛链接...")
    try:
        response = session.get("https://www.fotmob.com", timeout=15)
        if response.status_code == 200:
            html = response.text

            # 寻找比赛链接模式
            match_patterns = [
                r'href=["\'][^"\']*match/([^"\']+)["\']',
                r'href=["\'][^"\']*m/([^"\']+)["\']',
                r'/match/([^"\']+)["\']',
            ]

            found_matches = set()
            for pattern in match_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                found_matches.update(matches)

            if found_matches:
                print(f"   ✅ 找到比赛ID: {list(found_matches)[:10]}")
                return list(found_matches)[:3]  # 返回前3个
            else:
                print("   ❌ 未找到比赛链接")

    except Exception as e:
        print(f"   ❌ 首页访问失败: {e}")

    return working_urls


def analyze_page_structure(html: str, url: str):
    """分析页面结构"""
    print("   📋 页面结构分析:")

    # 检查是否是Next.js
    if "__NEXT_DATA__" in html:
        print("      🟢 Next.js SSR页面")
    elif "window.__INITIAL_STATE__" in html:
        print("      🟢 客户端状态注入")

    # 检查是否包含数据
    data_indicators = ["props", "content", "match", "fixture", "game"]
    html_lower = html.lower()

    found_indicators = []
    for indicator in data_indicators:
        if f'"{indicator}"' in html_lower:
            found_indicators.append(indicator)

    if found_indicators:
        print(f"      📊 发现数据指示器: {found_indicators}")


def test_recent_matches(match_ids: list[str]):
    """测试最近的比赛"""
    print("\n🎯 测试最近比赛:")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        }
    )

    for match_id in match_ids:
        url = f"https://www.fotmob.com/match/{match_id}"
        print(f"\n📡 测试: {url}")

        try:
            response = session.get(url, timeout=10)
            print(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                html = response.text

                # 快速检查是否包含数据
                if "__NEXT_DATA__" in html or "content" in html:
                    print("   ✅ 包含数据结构")

                    # 简单检查xG相关
                    if "xg" in html.lower() or "expected" in html.lower():
                        print("   🎯 可能包含xG数据")
                        return True, url, html
                    else:
                        print("   ⚠️ 未发现明显的ML特征数据")
                else:
                    print("   ❌ 未发现数据结构")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")

    return False, None, None


def main():
    """主函数"""
    print("🚀 FotMob URL 探索器启动...")

    # 第一步：探索URL结构
    working_urls = explore_fotmob_structure()

    # 第二步：如果没找到可用的URL，尝试从首页获取比赛
    if not working_urls:
        match_ids = explore_fotmob_structure()
        if match_ids:
            print("\n🎯 测试获取的比赛ID...")
            success, working_url, html = test_recent_matches(match_ids)

            if success:
                print("\n🎉 找到可用的比赛页面!")
                print(f"   URL: {working_url}")
                print(f"   HTML大小: {len(html)} 字符")

                # 快速分析
                if "__NEXT_DATA__" in html:
                    print("   ✅ Next.js SSR - 可以提取JSON数据")
                if "xg" in html.lower():
                    print("   ✅ 包含xG相关数据")

                return True

    print("\n❌ 未找到可用的FotMob比赛页面")
    print("🔍 建议:")
    print("   1. 检查网络连接")
    print("   2. 确认FotMob服务可用性")
    print("   3. 尝试其他比赛ID")
    print("   4. 考虑使用代理或VPN")

    return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
