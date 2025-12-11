#!/usr/bin/env python3
"""
FotMob API Token 刷新器
FotMob API Token Refresher

逆向安全工程师 - 动态获取最新的API鉴权tokens
使用Playwright拦截网络请求，提取x-mas和x-foo头
"""

import asyncio
import sys
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright, Page, Request, Browser
except ImportError:
    print("❌ 需要安装 playwright:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)


class FotMobTokenExtractor:
    """FotMob Token 提取器"""

    def __init__(self):
        self.captured_tokens = {}
        self.found_api_request = False
        self.target_api_patterns = [
            r"/api/.*",
            r".*/api/.*",
            r"https://www\.fotmob\.com/api/.*",
        ]

    async def extract_tokens(self) -> Optional[dict[str, str]]:
        """
        主要执行函数 - 提取最新tokens

        Returns:
            Dict: 包含 'x-mas' 和 'x-foo' 的字典，失败返回None
        """
        print("🕵️" + "=" * 70)
        print("🔐 FotMob API Token 刷新器")
        print("👨‍💻 逆向安全工程师 - 动态Token提取")
        print("=" * 72)

        try:
            async with async_playwright() as p:
                print("\n🚀 启动无头浏览器...")

                # 启动浏览器
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )

                print("✅ 浏览器启动成功")

                # 创建页面上下文
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )

                page = await context.new_page()

                # 设置网络请求拦截
                await self.setup_request_interception(page)

                print("\n🌐 访问 FotMob 首页...")
                print("   URL: https://www.fotmob.com")

                # 访问首页
                try:
                    response = await page.goto(
                        "https://www.fotmob.com",
                        wait_until="networkidle",
                        timeout=30000,
                    )

                    print(f"   状态码: {response.status}")
                    print(f"   URL: {response.url}")

                except Exception as e:
                    print(f"   ❌ 页面加载失败: {e}")
                    await browser.close()
                    return None

                if not response.ok:
                    print(f"   ❌ HTTP错误: {response.status}")
                    await browser.close()
                    return None

                print("✅ 页面加载成功")

                # 等待API请求
                print("\n🔍 等待API请求...")
                print("   监听目标: /api/* 请求")
                print("   超时: 30秒")

                # 等待捕获API请求
                max_wait_time = 30  # 30秒超时
                wait_interval = 0.5
                elapsed_time = 0

                while not self.found_api_request and elapsed_time < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    elapsed_time += wait_interval

                    # 进度显示
                    if int(elapsed_time) % 5 == 0:
                        print(f"   等待中... {int(elapsed_time)}/{max_wait_time}秒")

                # 如果没找到，尝试主动触发API请求
                if not self.found_api_request:
                    print("\n🎯 未找到API请求，尝试主动触发...")
                    await self.trigger_api_requests(page)

                    # 再等待15秒
                    for i in range(15):
                        await asyncio.sleep(1)
                        if self.found_api_request:
                            break
                        if i % 3 == 0:
                            print(f"   主动触发中... {i + 1}/15秒")

                await browser.close()

                # 返回结果
                if self.captured_tokens:
                    print("\n🎉 Token提取成功!")
                    print(f"   捕获的headers: {len(self.captured_tokens)} 个")

                    return self.captured_tokens
                else:
                    print("\n❌ Token提取失败")
                    print("   未找到有效的API请求")
                    return None

        except Exception as e:
            print(f"\n❌ 提取过程异常: {e}")
            import traceback

            print(f"🔍 详细错误: {traceback.format_exc()}")
            return None

    async def setup_request_interception(self, page: Page):
        """设置请求拦截"""

        async def handle_request(request: Request):
            """处理网络请求"""
            url = request.url

            # 检查是否为API请求
            if any(
                re.search(pattern, url, re.IGNORECASE)
                for pattern in self.target_api_patterns
            ):
                self.found_api_request = True

                print("\n🎯 发现API请求!")
                print(f"   URL: {url}")
                print(f"   方法: {request.method}")

                # 提取headers
                headers = request.headers

                # 查找关键tokens
                x_mas = headers.get("x-mas")
                x_foo = headers.get("x-foo")

                if x_mas and x_foo:
                    print("   ✅ 找到完整tokens:")
                    print(f"   x-mas: {x_mas[:80]}...")
                    print(f"   x-foo: {x_foo}")

                    self.captured_tokens = {
                        "x-mas": x_mas,
                        "x-foo": x_foo,
                        "user-agent": headers.get("user-agent", ""),
                        "extracted_at": datetime.now().isoformat(),
                        "source_url": url,
                    }
                else:
                    print("   ⚠️ 缺少tokens:")
                    print(f"   x-mas: {'找到' if x_mas else '未找到'}")
                    print(f"   x-foo: {'找到' if x_foo else '未找到'}")

                    # 记录所有headers用于调试
                    print(f"   所有headers: {dict(headers)}")

                # 记录所有API请求用于分析
                if not hasattr(self, "api_requests"):
                    self.api_requests = []

                self.api_requests.append(
                    {
                        "url": url,
                        "method": request.method,
                        "headers": dict(headers),
                        "has_tokens": bool(x_mas and x_foo),
                    }
                )

        # 设置请求监听
        page.on("request", handle_request)

        print("✅ 请求拦截器已设置")

    async def trigger_api_requests(self, page: Page):
        """主动触发API请求"""
        try:
            print("🎯 尝试触发API请求...")

            # 方法1: 滚动页面触发懒加载
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 0)")

            # 方法2: 尝试点击一些元素
            try:
                # 查找可能的链接或按钮
                selectors = [
                    'a[href*="/matches"]',
                    'a[href*="/leagues"]',
                    "button",
                    '[role="button"]',
                    ".match",
                    ".league",
                ]

                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"   找到 {len(elements)} 个 '{selector}' 元素")
                        # 点击第一个元素
                        try:
                            await elements[0].click()
                            await asyncio.sleep(2)
                            break
                        except:
                            continue

            except Exception as e:
                print(f"   点击元素失败: {e}")

            # 方法3: 直接访问API端点
            try:
                api_urls = [
                    "https://www.fotmob.com/api/leagues",
                    "https://www.fotmob.com/api/matches?date=20241205",
                    "https://www.fotmob.com/api/translations",
                ]

                for api_url in api_urls:
                    try:
                        print(f"   直接访问: {api_url}")
                        await page.goto(
                            api_url, wait_until="domcontentloaded", timeout=10000
                        )
                        await asyncio.sleep(1)

                        # 如果成功，会触发request拦截
                        if self.captured_tokens:
                            break

                    except Exception:
                        continue

            except Exception as e:
                print(f"   直接API访问失败: {e}")

        except Exception as e:
            print(f"   触发API请求失败: {e}")

    def save_tokens_to_env(self, tokens: dict[str, str]) -> bool:
        """保存tokens到.env文件"""
        try:
            env_file = Path(".env")

            print("\n💾 保存tokens到 .env 文件...")
            print(f"   文件路径: {env_file.absolute()}")

            # 读取现有内容
            existing_content = ""
            if env_file.exists():
                with open(env_file, encoding="utf-8") as f:
                    existing_content = f.read()

            # 准备新内容
            new_lines = [
                f"# FotMob API Tokens - 自动更新于 {datetime.now().isoformat()}",
                f"FOTMOB_X_MAS={tokens['x-mas']}",
                f"FOTMOB_X_FOO={tokens['x-foo']}",
                "",
            ]

            new_content = "\n".join(new_lines) + existing_content

            # 写入文件
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(new_content)

            print("✅ Tokens已保存到 .env")
            print(f"   FOTMOB_X_MAS: {tokens['x-mas'][:50]}...")
            print(f"   FOTMOB_X_FOO: {tokens['x-foo']}")

            return True

        except Exception as e:
            print(f"❌ 保存tokens失败: {e}")
            return False

    def generate_collector_code(self, tokens: dict[str, str]) -> str:
        """生成更新后的采集器代码片段"""
        code = f"""
# 更新后的鉴权头 - {datetime.now().isoformat()}
headers = {{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.fotmob.com/",
    "Origin": "https://www.fotmob.com",
    # 🔑 最新鉴权头 - 动态获取
    "x-mas": "{tokens["x-mas"]}",
    "x-foo": "{tokens["x-foo"]}",
}}
        """
        return code.strip()


async def main():
    """主函数"""
    print("🔐 FotMob Token 刷新器启动...")

    # 创建提取器
    extractor = FotMobTokenExtractor()

    # 执行提取
    tokens = await extractor.extract_tokens()

    if tokens:
        print("\n🎉 Token提取成功!")
        print("=" * 50)

        # 显示tokens
        print("📋 提取的Tokens:")
        print(f"   x-mas: {tokens['x-mas']}")
        print(f"   x-foo: {tokens['x-foo']}")
        print(f"   提取时间: {tokens['extracted_at']}")
        print(f"   来源URL: {tokens['source_url']}")

        # 保存到.env
        save_success = extractor.save_tokens_to_env(tokens)

        # 生成代码
        collector_code = extractor.generate_collector_code(tokens)

        print("\n📝 更新采集器代码:")
        print(collector_code)

        print("\n🚀 下一步操作:")
        print("1. 更新 src/collectors/enhanced_fotmob_collector.py")
        print("2. 使用新的headers替换现有鉴权头")
        print("3. 重启L2采集任务")

        if save_success:
            print("4. .env文件已更新，可直接读取环境变量")

        return True

    else:
        print("\n❌ Token提取失败")
        print("🔍 可能的原因:")
        print("   1. 网络连接问题")
        print("   2. FotMob API结构变化")
        print("   3. 需要更长的等待时间")
        print("   4. 浏览器被检测")

        print("\n🛠️ 建议的解决方案:")
        print("   1. 检查网络连接")
        print("   2. 使用非无头模式调试: headless=False")
        print("   3. 增加等待时间")
        print("   4. 手动访问 FotMob 确认服务正常")

        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
