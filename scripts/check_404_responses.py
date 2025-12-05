#!/usr/bin/env python3
"""
检查404响应内容
Check 404 Response Content

Next.js架构专家 - 分析404响应中是否包含有用数据
"""

import requests
import json


def check_404_content():
    """检查404响应内容"""
    print("🔍" + "=" * 60)
    print("📋 检查404响应内容")
    print("👨‍💻 Next.js架构专家 - 分析404响应中的数据")
    print("=" * 62)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
    )

    build_id = "V6df9pvcCLyM_o24OmC9G"
    match_id = "4189362"

    # 测试有数据的URL
    test_urls = [
        f"https://www.fotmob.com/_next/data/{build_id}/matches/{match_id}.json",
        f"https://www.fotmob.com/_next/data/{build_id}/match-details/{match_id}.json",
    ]

    for i, url in enumerate(test_urls, 1):
        print(f"\n🔄 测试URL {i}: {url}")

        try:
            response = session.get(url, timeout=30)
            print(f"   📊 状态码: {response.status_code}")
            print(f"   📏 响应大小: {len(response.content)} bytes")
            print(
                f"   📄 Content-Type: {response.headers.get('content-type', 'Unknown')}"
            )

            if len(response.content) > 1000:  # 有内容
                print("   📄 响应内容预览:")

                # 尝试解析JSON
                try:
                    data = response.json()
                    print("   ✅ JSON解析成功!")
                    print(f"   📋 数据结构: {type(data)}")

                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"   📋 Keys: {keys}")

                        # 检查是否包含比赛数据
                        content_keys = ["content", "pageProps", "data", "match"]
                        found_content = any(key in keys for key in content_keys)
                        print(f"   🎯 包含比赛数据: {found_content}")

                        if found_content:
                            print("   🔍 详细分析:")
                            for key in content_keys:
                                if key in data:
                                    content_data = data[key]
                                    print(f"      {key}: {type(content_data)}")

                                    if isinstance(content_data, dict):
                                        content_keys_inner = list(content_data.keys())
                                        print(
                                            f"         Keys: {content_keys_inner[:10]}"
                                        )

                                        # 检查购物清单项目
                                        content_str = json.dumps(
                                            content_data, ensure_ascii=False
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
                                            print(
                                                f"         🛒 购物清单项目: {found_items}"
                                            )

                    elif isinstance(data, list):
                        print(f"   📋 列表长度: {len(data)}")
                        if data and isinstance(data[0], dict):
                            print(f"   📋 首项Keys: {list(data[0].keys())[:10]}")

                    # 保存数据
                    filename = f"404_response_{i}.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"   💾 数据已保存到: {filename}")

                except json.JSONDecodeError:
                    print("   ❌ JSON解析失败")
                    content_preview = response.text[:500]
                    print(f"   📄 文本内容: {content_preview}...")

            else:
                print("   ❌ 响应内容太少")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")


def main():
    """主函数"""
    print("🚀 检查404响应内容启动...")

    check_404_content()

    print("\n📊 分析完成")


if __name__ == "__main__":
    main()
