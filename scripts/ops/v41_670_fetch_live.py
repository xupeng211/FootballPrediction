#!/usr/bin/env python3
"""V41.670 获取实时加密数据 - 用于验证解密."""

import asyncio
from playwright.async_api import async_playwright
import re
import json
from pathlib import Path


async def fetch_encrypted_response():
    """从 OddsPortal 获取加密的 ajax-all-events 响应."""

    print("V41.670 获取实时加密数据")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 显示浏览器以便调试
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # 存储响应
        encrypted_responses = []

        # 拦截 ajax-all-events 请求
        async def handle_response(response):
            url = response.url
            if "ajax-all-events" in url:
                print(f"\n捕获到 ajax-all-events 响应!")
                print(f"URL: {url[:100]}")
                print(f"状态: {response.status}")

                # 获取响应头
                headers = response.headers
                print(f"Content-Type: {headers.get('content-type', 'N/A')}")

                try:
                    # 获取响应文本
                    text = await response.text()
                    print(f"响应长度: {len(text)} 字符")
                    print(f"前 100 字符: {text[:100]}")

                    # 保存响应
                    encrypted_responses.append({
                        "url": url,
                        "status": response.status,
                        "headers": dict(headers),
                        "body": text,
                    })
                except Exception as e:
                    print(f"获取响应失败: {e}")

        page.on("response", handle_response)

        # 访问英超联赛页
        print("\n访问英超联赛页...")
        await page.goto("https://www.oddsportal.com/football/england/premier-league/", timeout=60000)

        # 等待页面加载
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(5)

        print("\n等待加密响应...")
        await asyncio.sleep(10)

        await context.close()
        await browser.close()

        # 保存响应
        if encrypted_responses:
            output_file = Path("config/stealth/v41_670_live_response.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(encrypted_responses, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"\n响应已保存至: {output_file}")

            return encrypted_responses[0]["body"]
        else:
            print("\n未捕获到加密响应")
            return None


if __name__ == "__main__":
    response = asyncio.run(fetch_encrypted_response())
    if response:
        print(f"\n获取的加密响应:")
        print(response[:200])
