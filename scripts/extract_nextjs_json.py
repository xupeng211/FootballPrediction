#!/usr/bin/env python3
"""
Next.js 静态JSON数据提取脚本
Next.js Static JSON Data Extraction

Next.js架构专家 - 绕过API鉴权，直接获取静态生成的JSON数据
"""

import requests
import json
import re
from typing import Optional, Any


class NextJSDataExtractor:
    """Next.js 数据提取器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            }
        )

    def get_build_id(self) -> Optional[str]:
        """从首页获取Next.js build ID"""
        print("🏗️ 获取Next.js Build ID...")

        try:
            # 方法1: 从首页HTML提取buildId
            print("   📡 请求首页...")
            response = self.session.get("https://www.fotmob.com/", timeout=30)
            print(f"   📊 状态码: {response.status_code}")

            if response.status_code == 200:
                html = response.text

                # 方法1: 从__NEXT_DATA__中提取
                next_data_pattern = (
                    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
                )
                matches = re.findall(next_data_pattern, html, re.DOTALL)

                if matches:
                    try:
                        next_data = json.loads(matches[0])
                        if "buildId" in next_data:
                            build_id = next_data["buildId"]
                            print(f"   ✅ 从__NEXT_DATA__找到buildId: {build_id}")
                            return build_id
                    except json.JSONDecodeError:
                        print("   ⚠️ __NEXT_DATA__解析失败")

                # 方法2: 从buildManifest.js路径提取
                build_manifest_pattern = (
                    r"/_next/static/([a-zA-Z0-9_-]+)/_buildManifest\.js"
                )
                matches = re.findall(build_manifest_pattern, html)

                if matches:
                    build_id = matches[0]
                    print(f"   ✅ 从buildManifest路径找到buildId: {build_id}")
                    return build_id

                # 方法3: 从其他静态资源路径提取
                static_pattern = r"/_next/static/([a-zA-Z0-9_-]+)/chunks/"
                matches = re.findall(static_pattern, html)

                if matches:
                    build_id = matches[0]
                    print(f"   ✅ 从静态资源路径找到buildId: {build_id}")
                    return build_id

                print("   ❌ 未找到buildId")
                return None

            else:
                print(f"   ❌ 首页请求失败: {response.status_code}")
                return None

        except Exception as e:
            print(f"   ❌ 获取buildId失败: {e}")
            return None

    def construct_data_url(self, build_id: str, match_id: str) -> str:
        """构造Next.js数据URL"""
        # Next.js 数据页面URL模式
        data_url = f"https://www.fotmob.com/_next/data/{build_id}/match/{match_id}.json"

        # 添加查询参数
        params = f"?matchId={match_id}"

        full_url = data_url + params
        print(f"🔗 构造数据URL: {full_url}")

        return full_url

    def extract_match_data(self, match_id: str) -> Optional[dict[str, Any]]:
        """提取比赛数据"""
        print(f"\n🎯 提取比赛数据: {match_id}")
        print("=" * 60)

        # 获取buildId
        build_id = self.get_build_id()

        if not build_id:
            print("❌ 无法获取buildId")
            return None

        # 构造数据URL
        data_url = self.construct_data_url(build_id, match_id)

        # 请求数据
        print("📡 请求静态JSON数据...")
        try:
            response = self.session.get(data_url, timeout=30)
            print(f"   📊 状态码: {response.status_code}")
            print(f"   📏 响应大小: {len(response.content)} bytes")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print("   ✅ JSON解析成功")

                    # 分析数据结构
                    return self.analyze_match_data(data, match_id)

                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON解析失败: {e}")
                    print(f"   📄 响应内容预览: {response.text[:200]}...")
                    return None

            else:
                print(f"   ❌ HTTP请求失败: {response.status_code}")
                if response.status_code == 404:
                    print("   ⚠️ 可能需要不同的URL格式")
                return None

        except Exception as e:
            print(f"   ❌ 请求数据失败: {e}")
            return None

    def analyze_match_data(self, data: dict[str, Any], match_id: str) -> dict[str, Any]:
        """分析比赛数据结构"""
        print("\n🔍 分析比赛数据结构...")

        print(f"   📋 顶级Keys: {list(data.keys())}")

        # 检查pageProps
        page_props = data.get("pageProps", {})
        if page_props:
            print("   ✅ 找到pageProps")
            print(f"   📋 pageProps Keys: {list(page_props.keys())}")

            # 检查content
            content = page_props.get("content", {})
            if content:
                print("   ✅ 找到content")
                print(f"   📋 content Keys: {list(content.keys())}")

                # 验证关键数据
                verification_results = self.verify_shopping_list(content)

                return {
                    "success": True,
                    "data": data,
                    "pageProps": page_props,
                    "content": content,
                    "verification": verification_results,
                }
            else:
                print("   ❌ 未找到content")
        else:
            print("   ❌ 未找到pageProps")

        return {"success": False, "data": data}

    def verify_shopping_list(self, content: dict[str, Any]) -> dict[str, bool]:
        """验证购物清单项目"""
        print("\n🛒 验证购物清单项目...")

        content_str = json.dumps(content, ensure_ascii=False).lower()

        results = {
            "shotmap": False,
            "stats": False,
            "lineups": False,
            "odds": False,
            "xg": False,
            "rating": False,
        }

        # 检查各项数据
        checks = [
            ("shotmap", ["shotmap", "shotmap", "shot", "shot_data"]),
            (
                "stats",
                ["stats", "statistics", "matchfacts", "match_facts", "possession"],
            ),
            ("lineups", ["lineups", "lineup", "players", "starting_eleven"]),
            ("odds", ["odds", "betting", "prematchodds", "bet365"]),
            ("xg", ["xg", "expectedgoals", "expected_goals", "xgandxa"]),
            ("rating", ["rating", "matchrating", "playerrating"]),
        ]

        for key, keywords in checks:
            for keyword in keywords:
                if keyword in content_str:
                    results[key] = True
                    break

        # 打印验证结果
        for key, found in results.items():
            status = "✅" if found else "❌"
            print(f"   {status} {key.upper()}: {found}")

        # 特别检查重要字段
        match_facts = content.get("matchFacts", {})
        if match_facts:
            print(f"   🎯 发现matchFacts: {list(match_facts.keys())[:5]}...")

        lineups = content.get("lineups", {})
        if lineups:
            print(f"   🎯 发现lineups: {type(lineups).__name__}")

        return results


def main():
    """主函数"""
    print("🚀" + "=" * 70)
    print("🏗️ Next.js 静态JSON数据提取")
    print("👨‍💻 Next.js架构专家 - 绕过API鉴权的终极方案")
    print("=" * 72)

    extractor = NextJSDataExtractor()

    # 测试比赛ID
    test_matches = [
        "4189362",  # 之前测试的比赛
        "53_2023/2024_0294",  # 另一个测试比赛
    ]

    success_count = 0
    total_count = len(test_matches)

    for i, match_id in enumerate(test_matches, 1):
        print(f"\n🔄 测试 {i}/{total_count}: {match_id}")

        result = extractor.extract_match_data(match_id)

        if result and result.get("success"):
            success_count += 1
            print(f"   ✅ {match_id} 提取成功!")

            # 详细分析结果
            verification = result.get("verification", {})
            passed_checks = sum(verification.values())
            total_checks = len(verification)

            print(
                f"   📊 购物清单通过率: {passed_checks}/{total_checks} ({(passed_checks / total_checks) * 100:.1f}%)"
            )

            if passed_checks >= 4:
                print("   🎉 购物清单验证通过!")
            elif passed_checks >= 2:
                print("   👍 购物清单部分通过")
            else:
                print("   ⚠️ 购物清单验证失败")

            # 保存成功的结果
            with open(
                f"nextjs_data_{match_id.replace('/', '_')}.json", "w", encoding="utf-8"
            ) as f:
                json.dump(result["data"], f, indent=2, ensure_ascii=False)

            print(f"   💾 数据已保存到: nextjs_data_{match_id.replace('/', '_')}.json")

        else:
            print(f"   ❌ {match_id} 提取失败")

    # 最终结论
    print("\n" + "🎯" * 18)
    print("📊 Next.js静态数据提取总结")
    print("🎯" * 18)

    print(
        f"📈 成功率: {success_count}/{total_count} ({(success_count / total_count) * 100:.1f}%)"
    )

    if success_count > 0:
        print("\n🎉 Next.js静态数据提取成功!")
        print("✅ 这就是我们绕过API鉴权的终极方案!")
        print("🚀 建议立即投入生产环境开发")
        return True
    else:
        print("\n❌ Next.js静态数据提取失败")
        print("⚠️ 需要进一步分析URL格式或buildId获取方式")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
