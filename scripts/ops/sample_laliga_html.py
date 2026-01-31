#!/usr/bin/env python3
"""
V36.5 La Liga Live Sampling - 西甲现场"活体采样"

目的：手动抓取一场西甲比赛的完整 HTML，用于分析赔率数据结构

比赛：Rayo Vallecano vs Real Betis
URL: https://www.oddsportal.com/football/spain/laliga/rayo-vallecano-betis-jHoWn3KH/
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 确保在项目根目录
os.chdir('/home/user/projects/FootballPrediction')


async def sample_laliga_match():
    """采样西甲比赛 HTML"""

    # 目标 URL（来自审计日志中的 malformed 记录）
    target_url = "https://www.oddsportal.com/football/spain/laliga/rayo-vallecano-betis-jHoWn3KH/"

    output_file = Path("logs/laliga_debug.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🔬 V36.5 La Liga Live Sampling")
    print("=" * 70)
    print(f"目标 URL: {target_url}")
    print(f"输出文件: {output_file}")
    print("")

    async with async_playwright() as p:
        # 启动浏览器（使用 Ghost Protocol 指纹）
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # 创建上下文
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )

        page = await context.new_page()

        try:
            print("🌐 导航到目标页面...")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

            # 等待页面加载
            await asyncio.sleep(5)

            print("✅ 页面加载完成")
            print("")

            # 获取页面内容
            html_content = await page.content()

            # 保存完整 HTML
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"💾 HTML 已保存到: {output_file}")
            print(f"   文件大小: {len(html_content):,} 字节")

            # 尝试各种 CSS 选择器
            print("")
            print("🔍 测试 CSS 选择器...")

            selectors_to_test = [
                # 主要选择器
                ".odds-text",
                ".odds-cell",
                "[data-odd]",
                ".p0",  # Pinnacle 标识
                "#odds-data",
                ".table-main",
                "#fixture-data",
                ".odds-content",
                "[class*='odd']",
                "[id*='odd']",
                ".betting",
                ".odds",
            ]

            results = {}
            for selector in selectors_to_test:
                try:
                    elements = await page.query_selector_all(selector)
                    count = len(elements)
                    results[selector] = count

                    if count > 0:
                        print(f"  ✅ {selector}: {count} 个元素")
                    else:
                        print(f"  ❌ {selector}: 未找到")
                except Exception as e:
                    print(f"  ⚠️  {selector}: 错误 - {e}")

            # 保存选择器测试结果
            selector_results_file = Path("logs/laliga_selector_test.json")
            with open(selector_results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)

            print("")
            print(f"💾 选择器测试结果已保存到: {selector_results_file}")

            # 尝试获取页面标题
            title = await page.title()
            print("")
            print(f"📄 页面标题: {title}")

            # 检查是否有 Cloudflare 拦截
            cloudflare_titles = [
                "Just a moment...",
                "Attention Required!",
                "Access Denied",
                "Cloudflare"
            ]
            if any(title.lower() in cf_title.lower() for cf_title in cloudflare_titles):
                print("")
                print("⚠️  检测到 Cloudflare 拦截！")
                print("   页面可能被反爬虫机制拦截")

        except PlaywrightTimeoutError:
            print("❌ 页面加载超时")
            raise
        except Exception as e:
            print(f"❌ 采样失败: {e}")
            raise
        finally:
            await browser.close()

    print("")
    print("=" * 70)
    print("🎉 西甲现场采样完成！")
    print("=" * 70)
    print("")
    print("📊 采样结果:")
    print(f"   HTML 文件: {output_file}")
    print(f"   选择器测试: {selector_results_file}")
    print("")
    print("下一步：基于 laliga_debug.html 进行 TDD 测试开发")


if __name__ == "__main__":
    asyncio.run(sample_laliga_match())
