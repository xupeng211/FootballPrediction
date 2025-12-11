#!/usr/bin/env python3
"""
深度分析FotMob URL模式和参数
Deep analysis of FotMob URL patterns and parameters
"""

import requests
import re
import json


def test_various_url_patterns():
    """测试不同的URL模式"""
    base_date = "20240217"

    # 不同的URL模式尝试
    url_patterns = [
        # 基础模式
        f"https://www.fotmob.com/matches?date={base_date}",
        # 带时区
        f"https://www.fotmob.com/matches?date={base_date}&timezone=Europe/London",
        f"https://www.fotmob.com/matches?date={base_date}&tz=Europe/London",
        # 带地区
        f"https://www.fotmob.com/matches?date={base_date}&ccode3=GBR",
        f"https://www.fotmob.com/matches?date={base_date}&country=GB",
        f"https://www.fotmob.com/matches?date={base_date}&locale=en-GB",
        # 组合参数
        f"https://www.fotmob.com/matches?date={base_date}&timezone=Europe/London&ccode3=GBR",
        f"https://www.fotmob.com/matches?date={base_date}&tz=Europe/London&country=GB",
        f"https://www.fotmob.com/matches?date={base_date}&timezone=GMT&ccode3=GBR",
        # 英超特定
        f"https://www.fotmob.com/matches?date={base_date}&timezone=Europe/London&ccode3=GBR&league=47",
        f"https://www.fotmob.com/en-GB/matches?date={base_date}",
        f"https://www.fotmob.com/uk/matches?date={base_date}",
        # API格式
        f"https://www.fotmob.com/api/matches?date={base_date}",
        f"https://www.fotmob.com/api/matches?date={base_date}&timezone=Europe/London&ccode3=GBR",
        # 其他可能模式
        f"https://www.fotmob.com/matches/{base_date}",
        f"https://www.fotmob.com/fixtures?date={base_date}",
        f"https://www.fotmob.com/fixtures/{base_date}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    print("🔬 测试不同的FotMob URL模式...")
    print("=" * 70)

    best_urls = []

    for i, url in enumerate(url_patterns, 1):
        try:
            print(f"\n{i:2d}. {url}")
            response = requests.get(url, headers=headers, timeout=10, verify=False)

            status_info = (
                f"Status: {response.status_code}, Size: {len(response.text):,}"
            )

            if response.status_code == 200:
                print(f"     ✅ {status_info}")

                # 检查是否包含比赛数据
                has_nextjs = "__NEXT_DATA__" in response.text
                size_varies = len(response.text) > 350000 or len(response.text) < 300000
                has_matches = (
                    "match" in response.text.lower()
                    and "premier" in response.text.lower()
                )

                if has_nextjs:
                    print("     📊 Next.js: ✓")
                if size_varies:
                    print("     📏 大小变化: ✓")
                if has_matches:
                    print("     ⚽ 比赛关键词: ✓")

                # 评分系统
                score = 0
                if has_nextjs:
                    score += 3
                if size_varies:
                    score += 2
                if has_matches:
                    score += 2
                if response.status_code == 200:
                    score += 1

                best_urls.append(
                    {
                        "url": url,
                        "score": score,
                        "size": len(response.text),
                        "has_nextjs": has_nextjs,
                        "has_matches": has_matches,
                    }
                )

                print(f"     🎯 评分: {score}/8")

            else:
                print(f"     ❌ {status_info}")

        except Exception as e:
            print(f"     ❌ 异常: {e}")

    # 显示最佳URL
    print(f"\n{'=' * 70}")
    print("🏆 最佳URL排名:")
    best_urls.sort(key=lambda x: x["score"], reverse=True)

    for i, url_info in enumerate(best_urls[:5], 1):
        url = url_info["url"]
        score = url_info["score"]
        size = url_info["size"]
        print(f"{i}. [{score}/8] {size:,} bytes")
        print(f"   {url}")
        print()

    return best_urls[0] if best_urls else None


def analyze_response_content(url):
    """分析特定URL的响应内容"""
    print(f"\n🔍 深度分析最佳URL: {url}")
    print("-" * 50)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)

        if response.status_code != 200:
            print(f"❌ HTTP错误: {response.status_code}")
            return

        print(f"✅ 响应大小: {len(response.text):,} 字符")

        # 检查关键指标
        indicators = {
            "Next.js数据": "__NEXT_DATA__" in response.text,
            "比赛关键词": any(
                word in response.text.lower() for word in ["match", "fixture", "game"]
            ),
            "英超关键词": any(
                word in response.text.lower()
                for word in ["premier", "manchester", "london", "arsenal"]
            ),
            "JSON数据": "{" in response.text and "}" in response.text,
            "fallback": "fallback" in response.text,
            "matches": '"matches"' in response.text or "'matches'" in response.text,
        }

        print("\n📊 内容指标:")
        for indicator, found in indicators.items():
            status = "✅" if found else "❌"
            print(f"   {status} {indicator}")

        # 尝试提取Next.js数据
        if "__NEXT_DATA__" in response.text:
            print("\n🔬 分析Next.js数据结构...")

            nextjs_data = extract_nextjs_data(response.text)
            if nextjs_data:
                print("✅ Next.js数据解析成功")

                # 检查数据路径
                props = nextjs_data.get("props", {})
                pageProps = props.get("pageProps", {})
                fallback = pageProps.get("fallback", {})

                print(f"   📁 props字段数: {len(props)}")
                print(f"   📁 pageProps字段数: {len(pageProps)}")
                print(f"   📁 fallback键数: {len(fallback)}")

                if fallback:
                    print(f"   🔑 fallback键: {list(fallback.keys())[:3]}")

                    # 检查是否有比赛数据
                    matches_found = 0
                    for key, value in fallback.items():
                        if isinstance(value, dict) and "matches" in value:
                            matches_count = len(value.get("matches", []))
                            matches_found += matches_count
                            print(f"   ⚽ {key}: {matches_count} 场比赛")

                    print(f"   📊 总比赛数: {matches_found}")
                else:
                    print("   ❌ fallback为空")
            else:
                print("❌ Next.js数据解析失败")

    except Exception as e:
        print(f"❌ 分析异常: {e}")


def extract_nextjs_data(html):
    """提取Next.js数据"""
    patterns = [
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        r"window\.__NEXT_DATA__\s*=\s*(\{.*?\});?\s*<\/script>",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        if matches:
            try:
                nextjs_data_str = matches[0].strip()
                if nextjs_data_str.startswith("window.__NEXT_DATA__"):
                    nextjs_data_str = (
                        nextjs_data_str.replace("window.__NEXT_DATA__", "")
                        .replace("=", "")
                        .strip()
                    )
                    if nextjs_data_str.endswith(";"):
                        nextjs_data_str = nextjs_data_str[:-1]
                return json.loads(nextjs_data_str)
            except json.JSONDecodeError:
                continue
    return None


def main():
    """主函数"""
    print("🌐 FotMob URL模式深度分析")
    print("🎯 寻找能返回真实比赛数据的URL格式")
    print("=" * 70)

    # 测试各种URL模式
    best_url_info = test_various_url_patterns()

    if best_url_info:
        # 深度分析最佳URL
        analyze_response_content(best_url_info["url"])

        print(f"\n{'=' * 70}")
        print("🎯 结论:")
        print(f"最佳URL: {best_url_info['url']}")
        print(f"评分: {best_url_info['score']}/8")
        print("建议: 使用此URL格式进行数据采集")

    else:
        print(f"\n{'=' * 70}")
        print("❌ 未找到有效的URL模式")
        print("建议: 需要进一步调试或采用其他方法")


if __name__ == "__main__":
    main()
