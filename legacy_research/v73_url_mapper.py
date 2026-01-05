#!/usr/bin/env python3
"""
V73.0 URL Mapper - 修复版选择器

基于 V71.0 探测结果，OddsPortal 使用 Vue.js 动态渲染，
需要等待特定选择器出现。
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v73_url_mapper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    from src.config_unified import get_settings
    settings = get_settings()

    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )


async def scan_oddsportal_results(league: str, db_season: str, results_url: str):
    """
    扫描单个 Results 页面（修复版）
    """
    logger.info(f"扫描 {league} {db_season}")
    logger.info(f"URL: {results_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 使用非 headless 便于调试
            slow_mo=200
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            # 访问页面
            await page.goto(results_url, wait_until='networkidle', timeout=60000)

            # 等待 Vue.js 渲染完成
            logger.info("等待页面渲染...")
            await asyncio.sleep(3)

            # 滚动页面触发懒加载
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(2)

            # 尝试多种选择器策略
            selectors_to_try = [
                # 策略 1: 比赛表格行
                "table tbody tr",
                # 策略 2: 包含比分的链接
                "a[href*='/football/'][class*='']",
                # 策略 3: 通用数据行
                "[class*='row']",
                # 策略 4: 直接查找所有包含比分的元素
                "*:has-text(':')",
            ]

            url_data = []

            for selector in selectors_to_try:
                try:
                    logger.info(f"尝试选择器: {selector}")
                    elements = await page.query_selector_all(selector)

                    logger.info(f"找到 {len(elements)} 个元素")

                    for elem in elements[:100]:  # 限制检查数量
                        try:
                            text = await elem.inner_text()
                            href = await elem.get_attribute('href')

                            if text and ':' in text:
                                # 检查是否包含比分格式 (如 "2:1" 或 "2-1")
                                if any(c.isdigit() for c in text):
                                    # 尝试从 URL 中提取 href
                                    if not href:
                                        # 尝试从子元素中查找链接
                                        link = await elem.query_selector('a')
                                        if link:
                                            href = await link.get_attribute('href')

                                    if href and '/football/' in href:
                                        url_data.append({
                                            'href': href,
                                            'text': text.strip()
                                        })
                        except Exception as e:
                            continue

                    if url_data:
                        logger.info(f"选择器 {selector} 成功提取 {len(url_data)} 条数据")
                        break

                except Exception as e:
                    logger.warning(f"选择器 {selector} 失败: {e}")
                    continue

            # 输出发现的比赛
            logger.info(f"共发现 {len(url_data)} 场比赛")

            for i, item in enumerate(url_data[:10]):  # 只打印前 10 个
                logger.info(f"  [{i}] {item['href'][:60]}... | {item['text'][:50]}")

            # 保存到文件用于调试
            with open('audit_temp/v73_discovered_urls.txt', 'a') as f:
                f.write(f"\n# {league} {db_season} - {datetime.now()}\n")
                for item in url_data:
                    f.write(f"{item['href']}|{item['text']}\n")

            return url_data

        finally:
            await browser.close()


async def main():
    """主函数 - 测试单个页面"""
    logger.info("=" * 60)
    logger.info("V73.0 URL Mapper - 修复版")
    logger.info("=" * 60)

    # 测试单个页面
    test_url = "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"

    results = await scan_oddsportal_results("Bundesliga", "24/25", test_url)

    logger.info(f"完成！发现 {len(results)} 场比赛")
    logger.info(f"详细日志已保存到 logs/v73_url_mapper.log")
    logger.info(f"发现的 URL 已保存到 audit_temp/v73_discovered_urls.txt")


if __name__ == "__main__":
    asyncio.run(main())
