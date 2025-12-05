#!/usr/bin/env python3
"""
探索Next.js数据URL模式
Explore Next.js Data URL Patterns

Next.js架构专家 - 尝试不同的URL格式来获取静态数据
"""

import requests
import json
import re
from typing import List, Optional, Dict, Any

class NextJSUrlExplorer:
    """Next.js URL 探索器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def get_build_id(self) -> Optional[str]:
        """获取buildId"""
        try:
            response = self.session.get("https://www.fotmob.com/", timeout=30)
            if response.status_code == 200:
                html = response.text

                # 从__NEXT_DATA__提取buildId
                next_data_pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
                matches = re.findall(next_data_pattern, html, re.DOTALL)

                if matches:
                    next_data = json.loads(matches[0])
                    if 'buildId' in next_data:
                        return next_data['buildId']
        except Exception:
            pass
        return None

    def test_url_patterns(self, build_id: str, match_id: str) -> list[dict[str, str]]:
        """测试不同的URL模式"""
        patterns = [
            # 标准Next.js格式
            f"https://www.fotmob.com/_next/data/{build_id}/match/{match_id}.json",
            f"https://www.fotmob.com/_next/data/{build_id}/match/{match_id}.json?matchId={match_id}",

            # 不带查询参数的格式
            f"https://www.fotmob.com/_next/data/{build_id}/en/match/{match_id}.json",
            f"https://www.fotmob.com/_next/data/{build_id}/en/match/{match_id}.json?matchId={match_id}",

            # 使用slug格式
            f"https://www.fotmob.com/_next/data/{build_id}/matches/{match_id}.json",
            f"https://www.fotmob.com/_next/data/{build_id}/matches/{match_id}.json?matchId={match_id}",

            # 不同的路径格式
            f"https://www.fotmob.com/_next/data/{build_id}/api/match/{match_id}.json",
            f"https://www.fotmob.com/_next/data/{build_id}/match-details/{match_id}.json",

            # 带参数的格式
            f"https://www.fotmob.com/_next/data/{build_id}/match/{match_id}.json?id={match_id}",
            f"https://www.fotmob.com/_next/data/{build_id}/match/{match_id}.json?slug={match_id}",

            # 尝试不同的域名
            f"https://fotmob.com/_next/data/{build_id}/match/{match_id}.json",
            f"https://fotmob.com/_next/data/{build_id}/match/{match_id}.json?matchId={match_id}",

            # 使用m.fotmob.com
            f"https://m.fotmob.com/_next/data/{build_id}/match/{match_id}.json",
        ]

        results = []

        for i, url in enumerate(patterns, 1):
            print(f"\n🔄 测试模式 {i}/{len(patterns)}")
            print(f"   📡 {url}")

            try:
                response = self.session.get(url, timeout=15)
                print(f"   📊 状态码: {response.status_code}")
                print(f"   📏 大小: {len(response.content)} bytes")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print("   ✅ JSON解析成功!")

                        # 分析数据结构
                        if isinstance(data, dict):
                            keys = list(data.keys())
                            print(f"   📋 Keys: {keys}")

                            # 检查是否包含比赛数据
                            has_content = any('content' in str(k).lower() for k in keys)
                            has_page_props = 'pageProps' in keys
                            has_match = any('match' in str(k).lower() for k in keys)

                            if has_content or has_page_props or has_match:
                                print("   🎉 可能包含比赛数据!")
                                results.append({
                                    'url': url,
                                    'status': response.status_code,
                                    'size': len(response.content),
                                    'keys': keys,
                                    'data': data
                                })
                            else:
                                print("   ⚠️ 可能不包含比赛数据")

                    except json.JSONDecodeError:
                        print("   ❌ JSON解析失败")
                        content_preview = response.text[:100]
                        print(f"   📄 内容预览: {content_preview}...")

                elif response.status_code == 404:
                    print("   ❌ 404 Not Found")
                else:
                    print(f"   ❌ HTTP错误: {response.status_code}")

            except Exception as e:
                print(f"   ❌ 请求失败: {e}")

        return results

    def analyze_existing_page(self, match_id: str) -> dict[str, Any]:
        """分析现有页面寻找线索"""
        print("\n🔍 分析现有页面寻找线索...")

        try:
            # 访问比赛页面
            url = f"https://www.fotmob.com/match/{match_id}"
            response = self.session.get(url, timeout=30)

            if response.status_code in [200, 404]:
                html = response.text

                # 查找所有_next相关的URL
                next_urls = re.findall(r'/_next/[^"\s]+\.json', html)
                unique_urls = list(set(next_urls))

                print(f"   📋 发现 {len(unique_urls)} 个_next JSON链接:")
                for url in unique_urls[:10]:  # 只显示前10个
                    print(f"      🔗 {url}")

                # 分析这些URL的模式
                patterns = {}
                for url in unique_urls:
                    if '/_next/data/' in url:
                        # 提取buildId模式
                        parts = url.split('/_next/data/')
                        if len(parts) > 1:
                            rest = parts[1]
                            build_part = rest.split('/')[0]
                            if build_part not in patterns:
                                patterns[build_part] = []
                            patterns[build_part].append(url)

                print("\n   🏗️ 发现的Build ID模式:")
                for build_id, urls in patterns.items():
                    print(f"      {build_id}: {len(urls)} 个URL")
                    if urls:
                        sample = urls[0]
                        path_after_build = sample.split(f'/_next/data/{build_id}/')[1]
                        print(f"         示例路径: /{path_after_build}")

                return {
                    'next_urls': unique_urls,
                    'patterns': patterns
                }

        except Exception as e:
            print(f"   ❌ 分析失败: {e}")
            return {}

def main():
    """主函数"""
    print("🚀" + "="*70)
    print("🔍 探索Next.js数据URL模式")
    print("👨‍💻 Next.js架构专家 - 找到正确的静态数据URL格式")
    print("="*72)

    explorer = NextJSUrlExplorer()

    # 获取buildId
    build_id = explorer.get_build_id()
    if not build_id:
        print("❌ 无法获取buildId")
        return False

    print(f"✅ 获取到buildId: {build_id}")

    # 测试比赛ID
    test_match = "4189362"

    # 1. 测试不同的URL模式
    print(f"\n🎯 测试URL模式 - 比赛: {test_match}")
    results = explorer.test_url_patterns(build_id, test_match)

    if results:
        print(f"\n🎉 找到 {len(results)} 个可能的URL格式!")

        # 保存成功的URL
        for i, result in enumerate(results):
            filename = f"nextjs_success_{i}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result['data'], f, indent=2, ensure_ascii=False)
            print(f"   💾 保存到: {filename}")

        return True

    # 2. 分析现有页面寻找线索
    print("\n🔍 分析现有页面寻找更多线索...")
    page_analysis = explorer.analyze_existing_page(test_match)

    if page_analysis.get('patterns'):
        print("\n🎯 基于页面分析，建议尝试以下模式:")
        for build_id, urls in page_analysis['patterns'].items():
            print(f"   Build ID: {build_id}")
            for url in urls[:3]:  # 只显示前3个
                print(f"      示例: https://www.fotmob.com{url}")

    print("\n📊 URL模式探索完成")

    # 最终结论
    if results:
        print("\n✅ Next.js静态数据提取可行性高!")
        print("🚀 建议基于成功的URL模式开发采集器")
        return True
    else:
        print("\n⚠️ 需要进一步分析或尝试其他方法")
        print("💡 建议:")
        print("   1. 检查页面分析结果中的URL模式")
        print("   2. 尝试不同的比赛ID格式")
        print("   3. 考虑动态buildId或缓存机制")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
