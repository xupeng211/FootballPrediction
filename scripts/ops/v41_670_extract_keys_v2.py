#!/usr/bin/env python3
"""V41.670 密钥提取 V2 - 直接浏览器方法."""

import asyncio
from playwright.async_api import async_playwright
import re
from pathlib import Path

async def main():
    """使用浏览器获取所有 JS 资产并搜索密钥."""
    print("V41.670 V2 - 直接浏览器方法")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # 捕获所有 JS 文件
        js_files = []

        async def capture_js(route):
            request = route.request
            url = request.url
            if ".js" in url and "thirdparty" not in url.lower():
                filename = url.split('/')[-1].split('?')[0]
                js_files.append((url, filename))
            await route.continue_()

        await page.route("**/*", capture_js)

        print("访问 OddsPortal 首页...")
        await page.goto("https://www.oddsportal.com/", timeout=60000)

        # 等待页面加载
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(5)

        # 搜索页面中的加密相关字符串
        content = await page.content()

        print("\n搜索加密相关字符串...")

        # 搜索可能的密钥模式
        patterns = {
            "包含 'salt' 的行": re.findall(r'.{0,100}salt.{0,100}', content, re.IGNORECASE),
            "包含 'password' 的行": re.findall(r'.{0,100}password.{0,100}', content, re.IGNORECASE),
            "长字符串常量": re.findall(r'["\']([a-zA-Z0-9_+/]{40,100})["\']', content),
        }

        for name, matches in patterns.items():
            print(f"\n{name}: {len(matches)} 个匹配")
            for i, match in enumerate(matches[:5]):
                print(f"  {i+1}. {match[:100]}...")

        print(f"\n捕获到 {len(js_files)} 个 JS 文件")
        for url, filename in js_files[:10]:
            print(f"  - {filename}")

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
