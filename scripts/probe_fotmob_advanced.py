#!/usr/bin/env python3
"""
FotMob API 高级探测脚本
使用 curl_cffi 库模拟浏览器 TLS 指纹，绕过反爬保护
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta

try:
    from curl_cffi.requests import AsyncSession
except ImportError:
    print("❌ 错误: curl_cffi 库未安装")
    print("请运行: docker-compose exec app pip install curl_cffi")
    sys.exit(1)


class FotMobAdvancedProbe:
    """FotMob API 高级探测器"""

    def __init__(self):
        # 完整的浏览器 Headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

        # API URL (使用过去日期避免缓存问题)
        past_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        self.target_url = f"https://www.fotmob.com/api/matches?date={past_date}"

        print(f"🎯 目标 URL: {self.target_url}")
        print(f"📅 使用日期: {past_date} (7天前)")

    async def probe_with_impersonation(self):
        """使用浏览器伪装进行探测"""
        print("\n🕵️‍♂️ 开始高级探测...")

        try:
            # 创建具有 TLS 指纹模拟能力的会话
            async with AsyncSession(impersonate="chrome110") as session:
                print("✅ 已创建 Chrome 110 伪装会话")

                # 发送请求
                print("📡 正在发送请求...")
                response = await session.get(
                    self.target_url,
                    headers=self.headers,
                    timeout=30
                )

                print(f"📊 响应状态码: {response.status_code}")
                print(f"📋 响应头: {dict(response.headers)}")

                if response.status_code == 200:
                    print("🎉 成功获取数据!")

                    try:
                        data = response.json()
                        json_str = json.dumps(data, ensure_ascii=False, indent=2)

                        print(f"📄 JSON 数据长度: {len(json_str)} 字符")
                        print("📝 数据前100个字符:")
                        print(json_str[:100] + "..." if len(json_str) > 100 else json_str)

                        # 检查数据结构
                        if isinstance(data, dict):
                            print("🏗️ 数据结构:")
                            for key, value in data.items():
                                if isinstance(value, (list, dict)):
                                    print(f"  {key}: {type(value).__name__} (长度: {len(value)})")
                                else:
                                    print(f"  {key}: {type(value).__name__}")

                        return True

                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 解析失败: {e}")
                        print("📄 原始响应前200字符:")
                        print(response.text[:200])
                        return False

                elif response.status_code in [401, 403]:
                    print(f"🚫 访问被拒绝 ({response.status_code})")
                    print("📄 响应内容:")
                    print(response.text[:500] if response.text else "无响应体")

                    # 分析可能的拦截方式
                    self.analyze_blocking_mechanism(response)
                    return False

                else:
                    print(f"⚠️ 其他状态码: {response.status_code}")
                    print("📄 响应内容:")
                    print(response.text[:200] if response.text else "无响应体")
                    return False

        except Exception as e:
            print(f"❌ 请求失败: {type(e).__name__}: {e}")
            return False

    def analyze_blocking_mechanism(self, response):
        """分析拦截机制"""
        print("\n🔍 分析拦截机制:")

        headers = dict(response.headers)

        # 检查常见的反爬头
        anti_bot_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "cf-ray",  # Cloudflare
            "server",
            "x-frame-options"
        ]

        print("📋 检测到的防护头:")
        for header in anti_bot_headers:
            if header in headers:
                print(f"  {header}: {headers[header]}")

        # 检查响应体特征
        if response.text:
            if "cloudflare" in response.text.lower():
                print("🛡️ 检测到 Cloudflare 保护")
            if "captcha" in response.text.lower():
                print("🤖 检测到验证码要求")
            if "rate limit" in response.text.lower():
                print("⏱️ 检测到频率限制")


async def main():
    """主函数"""
    print("🚀 FotMob API 高级探测工具")
    print("=" * 50)

    probe = FotMobAdvancedProbe()
    success = await probe.probe_with_impersonation()

    print("\n" + "=" * 50)
    if success:
        print("🎉 探测成功! 可以继续开发爬虫逻辑")
    else:
        print("❌ 探测失败，需要进一步分析或使用其他技术")

    return success


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