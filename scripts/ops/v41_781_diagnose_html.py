#!/usr/bin/env python3
"""V41.781: HTML 结构诊断工具 - 调试 OddsPortal 哈希提取问题."""

import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def main():
    """诊断 OddsPortal HTML 结构."""

    url = "https://www.oddsportal.com/football/england/premier-league/results/"

    print("=" * 70)
    print("V41.781: OddsPortal HTML 结构诊断")
    print("=" * 70)
    print(f"目标 URL: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("正在加载页面...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)  # 等待 JavaScript 渲染

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # 统计链接
        all_links = soup.find_all("a", href=True)
        football_links = soup.find_all("a", href=re.compile(r"/football/"))

        print(f"📊 页面统计:")
        print(f"   总链接数: {len(all_links)}")
        print(f"   football 链接: {len(football_links)}")

        # 查找包含哈希的链接
        hash_pattern_8 = re.compile(r"/([A-Za-z0-9]{8})/?$")
        hash_pattern_10 = re.compile(r"/([A-Za-z0-9]{10})/?$")

        hash_links_8 = [a for a in football_links if hash_pattern_8.search(a.get("href", ""))]
        hash_links_10 = [a for a in football_links if hash_pattern_10.search(a.get("href", ""))]

        print(f"   8字符哈希链接: {len(hash_links_8)}")
        print(f"   10字符哈希链接: {len(hash_links_10)}")

        # 显示样本链接
        print(f"\n🔗 样本链接 (前 10 个 football 链接):")
        for i, link in enumerate(football_links[:10], 1):
            href = link.get("href", "")
            text = link.get_text(strip=True)[:50]
            print(f"   {i}. {href}")
            print(f"      文本: {text}")

        # 测试 TEAM_PATTERN
        TEAM_PATTERN = re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-[A-Za-z0-9]{8,10}/")
        team_matches = [a for a in football_links if TEAM_PATTERN.search(a.get("href", ""))]
        print(f"\n🎯 TEAM_PATTERN 匹配: {len(team_matches)} 个")

        if team_matches:
            print(f"   样本 (前 5 个):")
            for i, link in enumerate(team_matches[:5], 1):
                href = link.get("href", "")
                print(f"   {i}. {href}")
        else:
            print(f"   ⚠️ TEAM_PATTERN 未匹配到任何链接!")

            # 尝试更宽松的模式
            print(f"\n🔍 尝试诊断:")
            for link in football_links[:20]:
                href = link.get("href", "")
                if "premier-league" in href.lower():
                    print(f"   示例: {href}")
                    # 分析结构
                    parts = href.split("/")
                    print(f"      结构: {parts}")

        await browser.close()

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
