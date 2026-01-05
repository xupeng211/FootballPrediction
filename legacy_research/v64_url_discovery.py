#!/usr/bin/env python3
"""
V64.0 URL Discovery - 动态抓取真实的 OddsPortal Match URL

使用 V57.0 的 Stage 1 方法：
1. 访问 results 页面
2. 使用 JavaScript 提取所有比赛的 URL path
3. 构造完整的 match URL
"""

import asyncio
import logging
import random
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# Results 页面配置
RESULTS_PAGES = [
    "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
    "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
]


async def discover_match_urls(results_url: str, max_matches: int = 5) -> list[dict]:
    """从 results 页面抓取真实的 match URL

    Args:
        results_url: Results 页面 URL
        max_matches: 最多抓取多少场比赛

    Returns:
        包含 match_id, url, home_team, away_team 的字典列表
    """
    logger.info(f"[Discovery] 抓取: {results_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        try:
            # 访问 results 页面
            await page.goto(
                results_url,
                wait_until='domcontentloaded',
                timeout=30000
            )

            # 等待页面加载
            await asyncio.sleep(3)

            # 使用 V57.0 的 JavaScript 提取 URL path
            discovery_script = """
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href*="/football/"]');

                    for (const link of links) {
                        const href = link.getAttribute('href');
                        const text = link.textContent || '';

                        // 过滤：只提取比赛链接（包含比分格式如 2-1）
                        if (href &&
                            !href.includes('/standings') &&
                            text.match(/\\d+\\s*–\\s*\\d+/)) {

                            results.push({
                                urlPath: href,
                                text: text.trim()
                            });
                        }
                    }

                    return results.slice(0, 20);  // 返回前 20 个
                }
            """

            discovered = await page.evaluate(discovery_script)
            logger.info(f"[Discovery] 找到 {len(discovered)} 场比赛")

            matches = []
            for item in discovered[:max_matches]:
                url_path = item['urlPath']
                text = item['text']

                # 解析球队名称
                # 格式: "Mainz - Bayern Munich 2-1"
                parts = text.split('–')
                if len(parts) >= 2:
                    teams_part = parts[0].strip()
                    # 移除比分部分
                    teams = teams_part.split('-')
                    if len(teams) >= 2:
                        home_team = teams[0].strip()
                        away_team = teams[1].strip()

                        # 构造完整 URL
                        full_url = f"https://www.oddsportal.com{url_path}"

                        matches.append({
                            'match_id': f"discovered_{len(matches)}",
                            'url': full_url,
                            'url_path': url_path,
                            'home_team': home_team,
                            'away_team': away_team,
                            'league': results_url.split('/')[4] if len(results_url.split('/')) > 4 else 'unknown'
                        })

            logger.info(f"[Discovery] 解析成功 {len(matches)} 场比赛")

            return matches

        except Exception as e:
            logger.error(f"[Discovery] 错误: {e}")
            return []

        finally:
            await browser.close()


async def main():
    """主程序：抓取真实的 match URL"""
    logger.info("=" * 60)
    logger.info("V64.0 URL Discovery - 动态抓取真实 URL")
    logger.info("=" * 60)

    all_matches = []

    for results_url in RESULTS_PAGES:
        matches = await discover_match_urls(results_url, max_matches=3)
        all_matches.extend(matches)

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"总计发现 {len(all_matches)} 场比赛")
    logger.info("=" * 60)

    for m in all_matches:
        logger.info(f"\n📋 {m['home_team']} vs {m['away_team']}")
        logger.info(f"   URL: {m['url']}")
        logger.info(f"   League: {m['league']}")

    # 保存到文件
    import json
    with open('logs/v64_discovered_urls.json', 'w') as f:
        json.dump(all_matches, f, indent=2)
    logger.info(f"\n✅ 已保存到: logs/v64_discovered_urls.json")


if __name__ == "__main__":
    asyncio.run(main())
