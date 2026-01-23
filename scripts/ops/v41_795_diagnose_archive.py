#!/usr/bin/env python3
"""V41.795 诊断工具 - 检查归档页 HTML 结构."""

import asyncio
import re
from playwright.async_api import async_playwright


def build_archive_url(league: str, season: str) -> str:
    """构建归档 URL."""
    slug = "premier-league"  # Simplified for Premier League
    season_suffix = season.replace("/", "-")
    return f"https://www.oddsportal.com/football/england/{slug}-{season_suffix}/results/"


async def main():
    """诊断归档页结构."""
    url = build_archive_url("Premier League", "2024/2025")

    print(f"🔍 诊断 URL: {url}")
    print(f"   验证 '-2024-2025' in URL: {'-2024-2025' in url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("\n🔄 正在加载页面...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        content = await page.content()

        # 分析 HTML
        print(f"\n📊 HTML 内容分析:")
        print(f"   - 内容长度: {len(content)} 字符")

        # 查找所有链接
        all_links = re.findall(r'href="([^"]+)"', content)
        print(f"   - 总链接数: {len(all_links)}")

        # 查找 football 相关链接
        football_links = [link for link in all_links if '/football/' in link]
        print(f"   - football 链接: {len(football_links)}")

        # 查找分页链接
        pagination_links = [link for link in football_links if '#page/' in link]
        print(f"   - 分页链接: {len(pagination_links)}")

        if pagination_links:
            print(f"\n📄 分页链接示例:")
            for link in pagination_links[:5]:
                print(f"   - {link}")

        # 查找匹配链接
        match_pattern = re.compile(r'/football/[^/]+/[^/]+/[^/]+-[^/]+-[A-Za-z0-9]{8,10}/')
        match_links = [link for link in football_links if match_pattern.search(link)]
        print(f"\n   - 比赛链接: {len(match_links)}")

        if match_links:
            print(f"\n🎯 比赛链接示例:")
            for link in match_links[:5]:
                print(f"   - {link}")
        else:
            # 尝试其他模式
            alt_pattern = re.compile(r'/football/[^/]+/[^/]+/[^/]+-[^/]+/')
            alt_links = [link for link in football_links if alt_pattern.search(link)]
            print(f"\n   - 替代模式链接: {len(alt_links)}")

            if alt_links:
                print(f"\n🎯 替代链接示例:")
                for link in alt_links[:5]:
                    print(f"   - {link}")

        # 保存完整 HTML 用于离线分析
        with open("/tmp/v41_795_archive_debug.html", "w") as f:
            f.write(content)
        print(f"\n💾 完整 HTML 已保存到: /tmp/v41_795_archive_debug.html")

        await browser.close()

    print("\n✅ 诊断完成")


if __name__ == "__main__":
    asyncio.run(main())
