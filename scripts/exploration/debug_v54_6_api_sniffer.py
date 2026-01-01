#!/usr/bin/env python3
"""
V54.6 API 嗅探器 - 监听网络请求
================================

监听页面发出的所有 XHR/Fetch 请求，找到实际的数据 API
"""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_DATA_DIR = Path(".playwright_stealth_profile")


async def sniff_api():
    playwright = await async_playwright().start()

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )

    # 存储捕获的请求
    captured_requests = []

    def log_request(request):
        # 只记录 API 请求
        if (request.resource_type in ["xhr", "fetch"] or
            "api" in request.url.lower() or
            "ajax" in request.url.lower()):
            captured_requests.append({
                "method": request.method,
                "url": request.url,
                "type": request.resource_type,
            })

    browser_context.on("request", log_request)

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    try:
        print("V54.6 API 嗅探器启动")
        print("=" * 60)
        print()

        # 访问主页
        print("步骤 1: 访问主页...")
        await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 访问 Results 页面
        print("步骤 2: 访问 Results 页面...")
        target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

        # 等待并尝试触发数据加载
        print("步骤 3: 等待数据加载（滚动页面）...")
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)

        # 额外等待
        await asyncio.sleep(5)

        # 检查页面是否仍为空
        page_text = await page.evaluate("() => document.body.textContent")
        print(f"\n页面文本长度: {len(page_text):,}")

        # 查找是否有球队名
        has_teams = any(team in page_text.lower() for team in ["manchester", "liverpool", "chelsea", "arsenal"])
        print(f"包含知名球队: {'是' if has_teams else '否'}")

        print()
        print("=" * 60)
        print("捕获的 API 请求:")
        print("=" * 60)
        print(f"总数: {len(captured_requests)}")
        print()

        if captured_requests:
            for req in captured_requests[:20]:
                print(f"{req['method']:6s} {req['type']:10s}")
                print(f"      {req['url'][:100]}")
                print()

            # 保存完整列表
            output_path = Path("logs/debug_v54_6") / "captured_requests.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(captured_requests, f, indent=2)
            print(f"完整列表已保存: {output_path}")
        else:
            print("(未捕获到 API 请求)")
            print()
            print("结论: 页面可能不使用 API，或数据已预渲染在 HTML 中")

    finally:
        await browser_context.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(sniff_api())
