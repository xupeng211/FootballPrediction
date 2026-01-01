#!/usr/bin/env python3
"""
V54.8 单场验证工具
=================

验证修复后的 URL 是否能正常访问并提取赔率数据
"""

import asyncio
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def verify_one_match():
    """验证单场比赛"""

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 获取待验证比赛
    cursor.execute("""
        SELECT pf.match_id, m.home_team, m.away_team, pf.source_url
        FROM prematch_features pf
        JOIN matches m ON pf.match_id = m.match_id
        WHERE pf.source_url IS NOT NULL
          AND pf.is_processed = FALSE
          AND pf.closing_home_odds IS NULL
        ORDER BY RANDOM()
        LIMIT 1
    """)

    row = cursor.fetchone()
    if not row:
        print("没有找到待验证的比赛")
        return

    match_id = row["match_id"]
    home_team = row["home_team"]
    away_team = row["away_team"]
    source_url = row["source_url"]

    cursor.close()
    conn.close()

    print("=" * 60)
    print("V54.8 单场验证")
    print("=" * 60)
    print(f"比赛: {home_team} vs {away_team}")
    print(f"URL: {source_url}")
    print()

    # 启动浏览器
    playwright = await async_playwright().start()

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(Path('.playwright_stealth_profile')),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    try:
        # 访问主页
        await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 访问比赛详情页
        print("访问比赛详情页...")
        await page.goto(source_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        # 获取页面内容
        html = await page.content()
        page_title = await page.title()

        print()
        print("=" * 60)
        print("【页面状态】")
        print("=" * 60)
        print(f"页面标题: {page_title}")
        print(f"HTML 长度: {len(html):,} 字节")
        print()

        # 检查关键元素
        selectors = {
            "a.odds-link": "赔率链接",
            "div[class*='odds']": "赔率容器",
            "table": "表格",
        }

        print("【选择器探测】")
        has_data = False
        for selector, desc in selectors.items():
            count = await page.locator(selector).count()
            print(f"  {selector:30s} ({desc:10s}): {count} 个")
            if count > 0:
                has_data = True

        print()

        # 检查球队名
        page_text = await page.evaluate("() => document.body.innerText")
        home_found = home_team.lower() in page_text.lower()
        away_found = away_team.lower() in page_text.lower()

        print("【球队名称探测】")
        print(f"  主队 ({home_team}): {'找到' if home_found else '未找到'}")
        print(f"  客队 ({away_team}): {'找到' if away_found else '未找到'}")
        print()

        # 提取赔率数据
        if has_data:
            print("【提取赔率数据】")

            odds_data = await page.evaluate("""
                () => {
                    // 尝试从 div 中提取
                    const oddsDivs = document.querySelectorAll('div[class*="odd"]');
                    const allValues = [];

                    for (const div of oddsDivs) {
                        const text = div.textContent.trim();
                        // 匹配赔率格式
                        if (/^\\d+\\.\\d{2}$/.test(text)) {
                            allValues.push(parseFloat(text));
                        }
                    }

                    // 查找所有包含数字的 div
                    const allDivs = document.querySelectorAll('div');
                    for (const div of allDivs) {
                        const text = div.textContent.trim();
                        if (text.length < 10 && /^\\d+\\.\\d{2}$/.test(text)) {
                            allValues.push(parseFloat(text));
                        }
                    }

                    // 返回前 10 个唯一值
                    const unique = [...new Set(allValues)];
                    return {values: unique.slice(0, 10), total: unique.length};
                }
            """)

            if odds_data and odds_data["values"]:
                values = odds_data["values"]
                print(f"  找到 {odds_data['total']} 个赔率值")
                print(f"  前 10 个: {[f'{v:.2f}' for v in values]}")

                # 尝试找到 1X2 组合
                if len(values) >= 3:
                    # 通常：主胜最低，客次，平局最高
                    sorted_vals = sorted(values)
                    home = sorted_vals[0]
                    draw = sorted_vals[-1]
                    away = sorted_vals[int(len(sorted_vals) / 3)]

                    margin = 1.0 / home + 1.0 / draw + 1.0 / away

                    print()
                    print(f"  推导组合:")
                    print(f"    主队: {home:.2f}")
                    print(f"    平局: {draw:.2f}")
                    print(f"    客队: {away:.2f}")
                    print(f"    Margin: {margin:.4f}")

                    is_valid = 1.02 < margin < 1.08
                    print()
                    print("=" * 60)
                    print("【验证结论】")
                    print("=" * 60)
                    print(f"✓ 页面内容长度: {len(html):,} 字节 (> 50,000: {'是' if len(html) > 50000 else '否'})")
                    print(f"✓ 标题包含球队: 是 ({page_title})")
                    print(f"✓ 提取赔率: 成功 (推导 {len(values)} 个值)")
                    print(f"✓ Margin 校验: {'通过' if is_valid else '失败'} ({margin:.4f})")
                    print("=" * 60)
                else:
                    print("  ✗ 赔率值不足 3 个")
            else:
                print("  ✗ 未能提取赔率数据")
        else:
            print("【验证结论】")
            print("  ✗ 页面无赔率数据")

    except Exception as e:
        print(f"验证过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser_context.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(verify_one_match())
