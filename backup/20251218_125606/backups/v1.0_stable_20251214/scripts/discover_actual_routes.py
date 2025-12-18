#!/usr/bin/env python3
"""
发现实际的路由模式
Discover Actual Route Patterns

Next.js架构专家 - 通过分析现有页面发现真实的路由模式
"""

import requests
import json
import re


def analyze_page_routes():
    """分析页面中的路由信息"""
    print("🔍" + "=" * 60)
    print("📋 发现实际的路由模式")
    print("👨‍💻 Next.js架构专家 - 分析页面路由信息")
    print("=" * 62)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    # 访问比赛页面
    match_id = "4189362"
    url = f"https://www.fotmob.com/match/{match_id}"

    print(f"\n📡 访问比赛页面: {url}")

    try:
        response = session.get(url, timeout=30)
        print(f"   📊 状态码: {response.status_code}")

        if response.status_code in [200, 404]:
            html = response.text

            # 查找所有相关的脚本和链接
            print("\n🔍 分析页面中的路由信息...")

            # 1. 查找动态导入的路由
            dynamic_routes = re.findall(r'/api/[^\s"\']+', html)
            if dynamic_routes:
                print(f"   📋 发现动态路由: {len(dynamic_routes)} 个")
                for route in dynamic_routes[:10]:
                    print(f"      🔗 {route}")

            # 2. 查找fetch调用
            fetch_patterns = [
                r'fetch\(["\']([^"\']+)["\']',
                r'api/[^\s"\']+',
                r'/_next/static/chunks/[^\s"\']+\.js',
            ]

            found_apis = []
            for pattern in fetch_patterns:
                matches = re.findall(pattern, html)
                found_apis.extend(matches)

            if found_apis:
                print(f"   📋 发现API调用: {len(found_apis)} 个")
                for api in list(set(found_apis))[:15]:
                    print(f"      🔗 {api}")

            # 3. 查找路由配置
            router_patterns = [
                r'"route":\s*"([^"]*)"',
                r'"path":\s*"([^"]*)"',
                r'href=["\']([^"\']+)["\']',
            ]

            routes = []
            for pattern in router_patterns:
                matches = re.findall(pattern, html)
                routes.extend(matches)

            if routes:
                print(f"   📋 发现路由: {len(routes)} 个")
                for route in list(set(routes))[:20]:
                    if any(
                        keyword in route.lower()
                        for keyword in ["match", "api", "data", "json"]
                    ):
                        print(f"      🛣️  {route}")

            # 4. 查找可能的端点
            endpoint_patterns = [
                r'https?://[^"\s]*fotmob[^"\s]*api[^"\s]*',
                r'https?://[^"\s]*fotmob[^"\s]*data[^"\s]*',
            ]

            endpoints = []
            for pattern in endpoint_patterns:
                matches = re.findall(pattern, html)
                endpoints.extend(matches)

            if endpoints:
                print(f"   📋 发现端点: {len(endpoints)} 个")
                for endpoint in list(set(endpoints))[:10]:
                    print(f"      🌐 {endpoint}")

            # 5. 分析特定的数据加载模式
            print("\n🔍 分析数据加载模式...")

            # 查找特定的数据获取模式
            data_patterns = [
                r"matchDetails",
                r"matchFacts",
                r"lineups",
                r"shotmap",
                r"stats",
                r"odds",
            ]

            for pattern in data_patterns:
                if pattern.lower() in html.lower():
                    print(f"   ✅ 发现 {pattern} 相关代码")

                    # 尝试找到相关的API调用
                    context_pattern = rf".{{0,200}}{pattern}.{{0,200}}"
                    matches = re.findall(
                        context_pattern, html, re.IGNORECASE | re.DOTALL
                    )
                    if matches:
                        print("      上下文示例:")
                        for match in matches[:2]:
                            # 提取可能的URL
                            url_matches = re.findall(r'https?://[^\s"\']+', match)
                            if url_matches:
                                print(f"         🔗 {url_matches[0]}")

            return True

    except Exception as e:
        print(f"   ❌ 分析失败: {e}")
        return False


def test_alternative_endpoints():
    """测试替代的端点"""
    print("\n🔄 测试替代的端点...")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.fotmob.com/",
        }
    )

    # 可能的API端点
    possible_endpoints = [
        "https://www.fotmob.com/api/matchDetails",
        "https://www.fotmob.com/api/matchFacts",
        "https://www.fotmob.com/api/lineups",
        "https://api.fotmob.com/matchDetails",
        "https://fotmob.com/api/matchDetails",
    ]

    match_id = "4189362"

    for endpoint in possible_endpoints:
        print(f"\n📡 测试端点: {endpoint}")

        try:
            # 尝试不同的参数格式
            test_urls = [
                f"{endpoint}?matchId={match_id}",
                f"{endpoint}/{match_id}",
                f"{endpoint}?id={match_id}",
            ]

            for test_url in test_urls:
                print(f"   🔗 {test_url}")

                try:
                    response = session.get(test_url, timeout=15)
                    print(f"      📊 状态码: {response.status_code}")
                    print(f"      📏 大小: {len(response.content)} bytes")

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print("      ✅ JSON解析成功!")

                            if isinstance(data, dict):
                                keys = list(data.keys())
                                print(f"      📋 Keys: {keys[:10]}")

                                # 检查是否包含比赛数据
                                data_str = json.dumps(data, ensure_ascii=False).lower()
                                if any(
                                    keyword in data_str
                                    for keyword in ["shotmap", "xg", "lineup", "stats"]
                                ):
                                    print("      🎉 发现比赛数据!")
                                    return True

                        except json.JSONDecodeError:
                            print("      ❌ JSON解析失败")

                    elif response.status_code == 401:
                        print("      ⚠️ 需要认证")
                    elif response.status_code == 404:
                        print("      ❌ 端点不存在")

                except Exception as e:
                    print(f"      ❌ 请求失败: {e}")

        except Exception as e:
            print(f"   ❌ 端点测试失败: {e}")

    return False


def main():
    """主函数"""
    print("🚀 发现实际路由模式启动...")

    # 1. 分析页面路由
    routes_found = analyze_page_routes()

    # 2. 测试替代端点
    endpoints_found = test_alternative_endpoints()

    print("\n" + "🎯" * 15)
    print("📊 路由分析总结")
    print("🎯" * 15)

    if routes_found:
        print("✅ 页面路由分析完成")
    else:
        print("❌ 页面路由分析失败")

    if endpoints_found:
        print("✅ 找到可用的API端点!")
    else:
        print("❌ 未找到可用的API端点")

    if routes_found or endpoints_found:
        print("\n🚀 建议基于发现的信息进一步开发数据采集器")
        return True
    else:
        print("\n⚠️ 需要探索其他方法或数据源")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
