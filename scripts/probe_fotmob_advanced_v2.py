#!/usr/bin/env python3
"""
FotMob API 高级探测脚本 V2
基于翻译 API 成功的发现，深入分析认证机制
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from urllib.parse import quote

try:
    from curl_cffi.requests import AsyncSession
except ImportError:
    print("❌ 错误: curl_cffi 库未安装")
    print("请运行: docker-compose exec app pip install curl_cffi")
    sys.exit(1)


class FotMobAdvancedProbeV2:
    """FotMob API 高级探测器 V2"""

    def __init__(self):
        self.session = None

        # 基础 Headers (基于成功的翻译 API)
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

    async def initialize_session(self):
        """初始化会话并访问主页"""
        print("🔧 初始化会话...")
        self.session = AsyncSession(impersonate="chrome120")

        # 访问主页建立会话
        print("📡 访问主页建立会话...")
        home_response = await self.session.get("https://www.fotmob.com/")
        print(f"主页状态码: {home_response.status_code}")

        # 测试翻译 API 确认基础连接
        translation_test = await self.session.get(
            "https://www.fotmob.com/api/translationmapping?locale=en",
            headers=self.base_headers
        )
        print(f"翻译 API 测试: {translation_test.status_code}")

    async def test_different_date_formats(self):
        """测试不同的日期格式"""
        print("\n🕒 测试不同日期格式...")

        # 生成各种日期格式
        dates_to_test = [
            # 标准格式
            (datetime.now() - timedelta(days=1)).strftime("%Y%m%d"),
            (datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
            (datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),

            # 带分隔符的格式
            (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),

            # 特殊日期
            "20241124",  # 固定日期
            "20241201",  # 另一个固定日期
        ]

        for date_str in dates_to_test:
            print(f"\n📅 测试日期: {date_str}")
            await self.test_matches_api(date_str)

    async def test_matches_api(self, date_str):
        """测试指定日期的 matches API"""
        api_url = f"https://www.fotmob.com/api/matches?date={date_str}"

        # 测试不同的 headers 组合
        headers_variants = [
            # 基础版本
            self.base_headers.copy(),

            # 添加更多浏览器特征头
            {**self.base_headers, **{
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"'
            }},

            # 添加可能的认证头
            {**self.base_headers, **{
                "x-client-version": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3",
                "x-platform": "web"
            }},
        ]

        for i, headers in enumerate(headers_variants, 1):
            print(f"  🔧 尝试 headers 变体 {i}")

            try:
                response = await self.session.get(api_url, headers=headers, timeout=15)

                print(f"    📊 状态码: {response.status_code}")

                if response.status_code == 200:
                    print("    🎉 成功!")
                    try:
                        data = response.json()
                        json_preview = json.dumps(data, ensure_ascii=False)
                        print(f"    📄 数据长度: {len(json_preview)} 字符")
                        print(f"    📝 数据前100字符: {json_preview[:100]}...")

                        # 分析数据结构
                        if isinstance(data, dict):
                            print("    🏗️ 数据结构:")
                            for key in list(data.keys())[:5]:
                                value = data[key]
                                if isinstance(value, list):
                                    print(f"      {key}: list[{len(value)}]")
                                elif isinstance(value, dict):
                                    print(f"      {key}: dict[{len(value)}]")
                                else:
                                    print(f"      {key}: {type(value).__name__}")

                        return True

                    except json.JSONDecodeError:
                        print("    ❌ JSON 解析失败")
                        print(f"    📄 原始响应: {response.text[:100]}...")
                        return False

                elif response.status_code == 401:
                    print(f"    🚫 401 认证失败")
                    # 分析 401 响应头
                    headers_info = dict(response.headers)
                    print(f"    📋 关键头信息:")
                    for key in ['x-client-version', 'x-cache', 'x-amz-cf-id']:
                        if key in headers_info:
                            print(f"      {key}: {headers_info[key]}")

                elif response.status_code == 403:
                    print(f"    🚫 403 禁止访问")

                else:
                    print(f"    ⚠️ 其他状态码: {response.status_code}")
                    if response.text:
                        print(f"    📄 响应预览: {response.text[:50]}...")

            except Exception as e:
                print(f"    ❌ 请求异常: {e}")

        return False

    async def explore_alternative_endpoints(self):
        """探索其他可能的 API 端点"""
        print("\n🔍 探索其他 API 端点...")

        alternative_endpoints = [
            "/api/leagues",
            "/api/teams",
            "/api/matchesToday",
            "/api/liveMatches",
            "/api/matches?date=today",
            "/api/fixtures",
        ]

        for endpoint in alternative_endpoints:
            print(f"\n📡 测试端点: {endpoint}")
            url = f"https://www.fotmob.com{endpoint}"

            try:
                response = await self.session.get(url, headers=self.base_headers, timeout=10)
                print(f"  📊 状态码: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"  ✅ 成功! 数据类型: {type(data).__name__}")
                        if isinstance(data, (list, dict)):
                            print(f"  📊 数据大小: {len(data)}")
                    except:
                        print(f"  📄 响应长度: {len(response.text)}")

            except Exception as e:
                print(f"  ❌ 失败: {e}")

    async def close_session(self):
        """关闭会话"""
        if self.session:
            await self.session.aclose()


async def main():
    """主函数"""
    print("🚀 FotMob API 高级探测工具 V2")
    print("=" * 60)

    probe = FotMobAdvancedProbeV2()

    try:
        # 初始化会话
        await probe.initialize_session()

        # 测试不同日期格式
        success = await probe.test_different_date_formats()

        if not success:
            # 探索其他端点
            await probe.explore_alternative_endpoints()

        print("\n" + "=" * 60)
        if success:
            print("🎉 探测成功! 发现了可用的 API 端点")
        else:
            print("❌ 主要端点失败，但可能存在其他可用的端点")

    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await probe.close_session()


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        sys.exit(1)