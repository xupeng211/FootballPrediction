#!/usr/bin/env python3
"""
检查大404响应
Check Large 404 Response

Next.js架构专家 - 检查404响应中的大文件内容
"""

import requests
import json


def check_large_404():
    """检查大404响应"""
    print("🔍" + "=" * 60)
    print("📋 检查大404响应")
    print("👨‍💻 Next.js架构专家 - 分析404响应中的大数据")
    print("=" * 62)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    # 检查那个大响应
    test_url = "https://www.fotmob.com/api/matchDetails/4189362"

    print(f"\n📡 检查大响应: {test_url}")

    try:
        response = session.get(test_url, timeout=30)
        print(f"   📊 状态码: {response.status_code}")
        print(f"   📏 响应大小: {len(response.content)} bytes")
        print(f"   📄 Content-Type: {response.headers.get('content-type', 'Unknown')}")

        content_type = response.headers.get("content-type", "").lower()

        if "text/html" in content_type:
            print("   📄 HTML内容分析:")
            html = response.text

            # 查找Next.js数据
            if "__NEXT_DATA__" in html:
                print("      ✅ 包含Next.js数据!")
                # 提取并分析
                import re

                pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    try:
                        next_data = json.loads(matches[0])
                        print(f"      📋 Next.js Keys: {list(next_data.keys())}")

                        # 检查pageProps
                        if "pageProps" in next_data:
                            page_props = next_data["pageProps"]
                            print(f"      📋 pageProps Keys: {list(page_props.keys())}")

                            # 检查是否包含比赛数据
                            content = page_props.get("content", {})
                            if content:
                                print("      ✅ 找到content数据!")
                                content_str = json.dumps(
                                    content, ensure_ascii=False
                                ).lower()

                                shopping_items = {
                                    "shotmap": "shotmap" in content_str,
                                    "stats": "stats" in content_str,
                                    "lineups": "lineup" in content_str,
                                    "odds": "odds" in content_str,
                                    "xg": "xg" in content_str,
                                    "rating": "rating" in content_str,
                                }

                                found_items = [
                                    item
                                    for item, found in shopping_items.items()
                                    if found
                                ]
                                if found_items:
                                    print(f"      🛒 购物清单项目: {found_items}")
                                    print("      🎉 找到比赛数据!")

                                    # 保存数据
                                    with open(
                                        "large_404_nextjs_data.json",
                                        "w",
                                        encoding="utf-8",
                                    ) as f:
                                        json.dump(
                                            next_data, f, indent=2, ensure_ascii=False
                                        )
                                    print(
                                        "      💾 数据已保存到: large_404_nextjs_data.json"
                                    )

                    except json.JSONDecodeError:
                        print("      ❌ Next.js JSON解析失败")

            # 检查是否包含API响应
            if "api" in html.lower():
                print("      🔍 发现API相关内容")

            # 查找JSON数据
            json_patterns = re.findall(r'\{[^{}]*"match"[^{}]*\}', html)
            if json_patterns:
                print(f"      📋 发现 {len(json_patterns)} 个可能的JSON数据块")

        elif "application/json" in content_type:
            print("   📄 JSON内容分析:")
            try:
                data = response.json()
                print("      ✅ JSON解析成功!")
                print(f"      📋 数据结构: {type(data)}")

                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"      📋 Keys: {keys}")

                    # 检查是否包含比赛数据
                    data_str = json.dumps(data, ensure_ascii=False).lower()
                    if any(
                        keyword in data_str
                        for keyword in ["match", "shotmap", "xg", "lineup"]
                    ):
                        print("      🎉 可能包含比赛数据!")

                        # 保存数据
                        with open(
                            "large_404_json_data.json", "w", encoding="utf-8"
                        ) as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        print("      💾 数据已保存到: large_404_json_data.json")

            except json.JSONDecodeError:
                print("      ❌ JSON解析失败")
                content_preview = response.text[:500]
                print(f"      📄 内容预览: {content_preview}...")

        else:
            print("   📄 其他类型内容:")
            content_preview = response.text[:200]
            print(f"      📄 内容预览: {content_preview}...")

    except Exception as e:
        print(f"   ❌ 检查失败: {e}")


def main():
    """主函数"""
    print("🚀 检查大404响应启动...")

    check_large_404()

    print("\n📊 检查完成")


if __name__ == "__main__":
    main()
