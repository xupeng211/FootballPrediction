#!/usr/bin/env python3
"""
V74.1 Click Interceptor - 网络拦截 + 点击模拟策略

核心策略：
1. 监听所有网络请求和导航
2. 点击比赛元素
3. 捕获跳转后的 URL
4. 返回原页面继续
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from playwright.async_api import async_playwright, Page, Route

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v74_click_interceptor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def intercept_and_click(url: str, league: str, season: str, max_matches: int = 20):
    """通过点击拦截获取真实 URL"""
    logger.info(f"=" * 60)
    logger.info(f"V74.1 Click Interceptor - {league} {season}")
    logger.info(f"URL: {url}")
    logger.info(f"目标: 提取 {max_matches} 个比赛 URL")
    logger.info(f"=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=200
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        # 存储捕获的 URL
        captured_urls = []
        navigated_urls = set()

        # 监听导航事件
        async def on_navigation(navigation):
            url = navigation.url
            if '/football/' in url and len(url.split('-')[-1].strip('/')) == 7:
                # 这是一个比赛页面 URL
                match_id = url.split('-')[-1].strip('/')
                if match_id not in navigated_urls:
                    navigated_urls.add(match_id)
                    logger.info(f"  ✓ 捕获 URL: {url.split('/')[-2]}-{match_id}")

        page.on('load', on_navigation)

        try:
            # 访问 Results 页面
            logger.info("正在加载 Results 页面...")
            await page.goto(url, wait_until='networkidle', timeout=60000)

            # 等待渲染
            await asyncio.sleep(5)

            # 滚动到页面中间
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            await asyncio.sleep(2)

            # 尝试多种选择器找到可点击的比赛元素
            selectors = [
                # 包含比分或球队名称的元素
                "*:has-text('–')",
                "*:has-text(':')",
                "[class*='row']",
                "tbody tr",
                "div[class*='match']",
                "a[href*='/football/']",
            ]

            clickable_elements = []

            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    logger.info(f"选择器 '{selector}' 找到 {len(elements)} 个元素")

                    for elem in elements[:50]:  # 限制检查数量
                        try:
                            text = await elem.inner_text()

                            # 检查是否包含比分或球队名
                            if '–' in text or ':' in text:
                                # 进一步验证这是否是比赛行
                                if any(char.isdigit() for char in text):
                                    clickable_elements.append({
                                        'element': elem,
                                        'selector': selector,
                                        'text': text[:100]
                                })
                        except Exception:
                            continue

                    if clickable_elements:
                        logger.info(f"找到 {len(clickable_elements)} 个可点击元素")
                        break

                except Exception as e:
                    logger.warning(f"选择器 '{selector}' 失败: {e}")

            # 现在尝试点击这些元素
            logger.info(f"\\n开始点击元素以捕获 URL...")

            results_page_url = page.url

            for i, elem_info in enumerate(clickable_elements[:max_matches]):
                try:
                    elem = elem_info['element']

                    # 记录当前 URL
                    before_url = page.url

                    # 点击元素
                    logger.info(f"[{i+1}/{min(max_matches, len(clickable_elements))}] 点击元素...")
                    await elem.click(timeout=5000)

                    # 等待导航
                    await asyncio.sleep(2)

                    # 检查是否导航到新页面
                    after_url = page.url

                    if after_url != before_url and '/football/' in after_url:
                        # 成功导航到比赛页面
                        match_id = after_url.split('-')[-1].strip('/')

                        # 提取完整的 URL
                        full_url = after_url

                        captured_urls.append({
                            'match_id': match_id,
                            'url': full_url,
                            'text': elem_info['text']
                        })

                        logger.info(f"  ✓ 成功! URL: ...{match_id}")

                        # 返回 Results 页面
                        await page.goto(results_page_url, wait_until='networkidle', timeout=30000)
                        await asyncio.sleep(2)

                        # 重新获取元素（因为页面已刷新）
                        elements = await page.query_selector_all(elem_info['selector'])
                        if len(elements) > i:
                            elem = elements[i]

                    else:
                        logger.info(f"  ✗ 未导航到比赛页面")

                except Exception as e:
                    logger.warning(f"  ✗ 点击失败: {e}")
                    # 尝试返回 Results 页面
                    try:
                        await page.goto(results_page_url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(1)
                    except:
                        pass

                    # 如果捕获的 URL 已够多，提前退出
                    if len(captured_urls) >= max_matches:
                        break

            # 保存结果
            logger.info(f"\\n=" * 60)
            logger.info(f"拦截完成！")
            logger.info(f"总计捕获: {len(captured_urls)} 个 URL")
            logger.info(f"=" * 60)

            # 保存到文件
            output_file = Path('audit_temp/v74_captured_urls.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'league': league,
                    'season': season,
                    'timestamp': datetime.now().isoformat(),
                    'total_captured': len(captured_urls),
                    'urls': captured_urls
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"详细结果已保存: {output_file}")

            # 打印所有捕获的 URL
            for url_info in captured_urls[:10]:
                logger.info(f"  - {url_info['url']}")

            return captured_urls

        finally:
            await browser.close()


async def main():
    """主函数"""
    test_url = "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"

    results = await intercept_and_click(test_url, "Bundesliga", "24/25", max_matches=10)

    logger.info(f"\\n任务完成！捕获 {len(results)} 个比赛 URL")


if __name__ == "__main__":
    asyncio.run(main())
