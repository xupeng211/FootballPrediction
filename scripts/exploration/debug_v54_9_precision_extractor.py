#!/usr/bin/env python3
"""
V54.9 精准定位提取器 - DOM 行内一致性解析
==============================================

核心创新：
1. 使用 Playwright locator.has_text() 精准定位包含目标文本的父容器
2. 在该容器内提取 3 个赔率链接（保证行内一致性）
3. Margin 校验：1.02 < 1/P1 + 1/P2 + 1/P3 < 1.08

Author: Senior Backend Architect (DOM Precision Expert)
Version: V54.9 Precision Extractor
Date: 2026-01-01
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import psycopg2
from playwright.async_api import async_playwright, Locator
from playwright_stealth import Stealth

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class ExtractionStatus(Enum):
    """提取状态"""
    SUCCESS = "success"
    NO_CONTAINER = "no_container"
    INSUFFICIENT_ODDS = "insufficient_odds"
    MARGIN_INVALID = "margin_invalid"
    PAGE_ERROR = "page_error"


@dataclass
class ExtractionResult:
    """提取结果"""
    match_id: str
    home_team: str
    away_team: str
    status: ExtractionStatus
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    margin: Optional[float] = None
    error_detail: Optional[str] = None


class V54_9PrecisionExtractor:
    """V54.9 精准定位提取器"""

    def __init__(self):
        self.stealth = Stealth()

    async def extract_match_odds(
        self,
        page,
        home_team: str,
        away_team: str
    ) -> ExtractionResult:
        """
        精准定位提取赔率

        核心逻辑：
        1. 使用 locator.filter(has_text=...) 定位包含主队名的容器
        2. 在该容器内寻找 3 个赔率链接
        3. 校验 Margin
        """
        match_id = f"{home_team}_vs_{away_team}"

        try:
            # === 第一阶段：精准定位父容器 ===
            # 策略：查找包含主队名 OR 客队名的文本节点
            # 优先级：div > tr > td

            # 尝试多种定位策略
            container = await self._locate_container(page, home_team, away_team)

            if container is None:
                return ExtractionResult(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    status=ExtractionStatus.NO_CONTAINER,
                    error_detail="无法定位包含球队名的容器"
                )

            # === 第二阶段：在容器内提取赔率 ===
            odds_data = await self._extract_odds_from_container(container)

            if odds_data is None or len(odds_data) < 3:
                return ExtractionResult(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    status=ExtractionStatus.INSUFFICIENT_ODDS,
                    error_detail=f"容器内赔率不足: {len(odds_data) if odds_data else 0}"
                )

            # 提取前 3 个赔率值
            p1, p2, p3 = odds_data[:3]

            # === 第三阶段：Margin 校验 ===
            margin = 1.0 / p1 + 1.0 / p2 + 1.0 / p3

            if not (1.02 < margin < 1.08):
                return ExtractionResult(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    status=ExtractionStatus.MARGIN_INVALID,
                    home_odds=p1,
                    draw_odds=p2,
                    away_odds=p3,
                    margin=margin,
                    error_detail=f"Margin = {margin:.4f} 超出范围 (1.02, 1.08)"
                )

            # 成功提取
            return ExtractionResult(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                status=ExtractionStatus.SUCCESS,
                home_odds=p1,
                draw_odds=p2,
                away_odds=p3,
                margin=margin
            )

        except Exception as e:
            logger.error(f"提取赔率时出错: {e}")
            return ExtractionResult(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                status=ExtractionStatus.PAGE_ERROR,
                error_detail=str(e)
            )

    async def _locate_container(
        self,
        page,
        home_team: str,
        away_team: str
    ) -> Optional[Locator]:
        """
        精准定位包含球队名的父容器

        策略：
        1. 使用 filter(has_text=...) 查找包含球队名的元素
        2. 向上遍历找到包含赔率链接的父容器
        """
        # 标准化球队名（移除空格、特殊字符）
        home_normalized = home_team.lower().replace(" ", "").replace("-", "")
        away_normalized = away_team.lower().replace(" ", "").replace("-", "")

        # 策略 1: 查找包含完整比赛信息的 div
        # 例如：包含 "Arsenal vs Chelsea" 或 "Arsenal - Chelsea"
        for separator in [" vs ", " - ", ":"]:
            search_text = f"{home_team} {separator} {away_team}"

            # 使用 has_text 精准定位
            container = page.locator("div").filter(has_text=search_text).first
            count = await container.count()

            if count > 0:
                # 验证容器内是否有赔率链接
                links = container.locator("a[href*='odds']")
                if await links.count() >= 3:
                    logger.info(f"✓ 策略1命中: 包含 '{search_text}' 的 div 容器")
                    return container

        # 策略 2: 查找包含主队名的容器，然后验证是否也包含客队
        for team_name in [home_team, away_team]:
            containers = page.locator("div").filter(has_text=team_name)
            count = await containers.count()

            for i in range(min(count, 10)):  # 最多检查 10 个
                container = containers.nth(i)
                text = await container.inner_text()

                # 检查是否同时包含两个队名
                if home_normalized in text.lower() and away_normalized in text.lower():
                    # 验证是否有赔率链接
                    links = container.locator("a[href*='odds'], a[data-link]")
                    if await links.count() >= 3:
                        logger.info(f"✓ 策略2命中: 包含双方队名的容器")
                        return container

        # 策略 3: 查找 tr 表格行
        for team_name in [home_team, away_team]:
            rows = page.locator("tr").filter(has_text=team_name)
            count = await rows.count()

            for i in range(min(count, 5)):
                row = rows.nth(i)
                text = await row.inner_text()

                if home_normalized in text.lower() and away_normalized in text.lower():
                    links = row.locator("a[href*='odds'], a[class*='odds'], a[data-link]")
                    if await links.count() >= 3:
                        logger.info(f"✓ 策略3命中: tr 表格行")
                        return row

        # 策略 4: 通过 XPath 查找包含文本的最近祖先
        # 使用 JavaScript 在页面中查找
        # 修复：Playwright evaluate 不支持多个参数，需要使用单个表达式
        js_code = f"""
        (() => {{
            const homeTeam = "{home_team}";
            const awayTeam = "{away_team}";

            // 查找所有文本节点
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null
            );

            let node;
            const homeLower = homeTeam.toLowerCase();
            const awayLower = awayTeam.toLowerCase();

            while (node = walker.nextNode()) {{
                const text = node.textContent.trim();

                // 检查是否包含双方队名
                if (text.length > 10 && text.length < 200) {{
                    const textLower = text.toLowerCase();

                    // 检查队名
                    const hasHome = homeLower.split(' ').some(p =>
                        p && textLower.includes(p)
                    );
                    const hasAway = awayLower.split(' ').some(p =>
                        p && textLower.includes(p)
                    );

                    if (hasHome && hasAway) {{
                        // 向上找到包含赔率链接的父元素
                        let parent = node.parentElement;
                        let depth = 0;

                        while (parent && depth < 10) {{
                            const links = parent.querySelectorAll('a[href*="odds"], a[data-link], a[class*="odds"]');

                            if (links.length >= 3) {{
                                // 返回 XPath
                                return getXPathForElement(parent);
                            }}

                            parent = parent.parentElement;
                            depth++;
                        }}
                    }}
                }}
            }}

            return null;

            function getXPathForElement(el) {{
                if (el.id !== '')
                    return 'id("' + el.id + '")';

                const parts = [];
                let current = el;

                while (current && current.nodeType === Node.ELEMENT_NODE) {{
                    let index = 0;
                    let sibling = current.previousSibling;

                    while (sibling) {{
                        if (sibling.nodeType === Node.ELEMENT_NODE &&
                            sibling.tagName === current.tagName) {{
                            index++;
                        }}
                        sibling = sibling.previousSibling;
                    }}

                    const tagName = current.tagName.toLowerCase();
                    const pathIndex = index > 0 ? `[${{index + 1}}]` : '';
                    parts.unshift(`${{tagName}}${{pathIndex}}`);

                    current = current.parentElement;
                }}

                return '//' + parts.join('/');
            }}
        }})()
        """
        container_locator = await page.evaluate(js_code)

        if container_locator:
            logger.info(f"✓ 策略4命中: XPath 定位")
            return page.locator(f"xpath={container_locator}")

        return None

    async def _extract_odds_from_container(
        self,
        container: Locator
    ) -> Optional[list[float]]:
        """
        从容器内提取赔率值

        策略：
        1. 查找所有元素（不限于链接）
        2. 提取包含数字格式的文本
        3. 返回前 3 个有效赔率值
        """
        # 使用 JavaScript 在容器内查找所有赔率值
        # 这种方法对 Vue.js 渲染的 DOM 更有效
        odds_data = await container.evaluate("""
            (element) => {
                const oddsSet = new Set();

                // 查找所有直接文本节点和元素
                const allElements = element.querySelectorAll('*');
                const textPattern = /^\\s*\\d+\\.\\d{2}\\s*$/;

                for (const el of allElements) {
                    const text = el.textContent || '';
                    const trimmed = text.trim();

                    if (textPattern.test(trimmed)) {
                        const value = parseFloat(trimmed);
                        // 合理的赔率范围：1.01 - 50.00
                        if (value >= 1.01 && value <= 50.00) {
                            oddsSet.add(value);
                        }
                    }

                    if (oddsSet.size >= 20) break;
                }

                return Array.from(oddsSet).sort((a, b) => a - b);
            }
        """)

        return odds_data if odds_data else None


async def run_batch_test(limit: int = 26) -> dict:
    """
    执行批量测试

    返回统计结果（Silent Mode）
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cursor = conn.cursor()

    # 获取测试数据
    cursor.execute("""
        SELECT pf.match_id, m.home_team, m.away_team, pf.source_url
        FROM prematch_features pf
        JOIN matches m ON pf.match_id = m.match_id
        WHERE pf.source_url IS NOT NULL
          AND pf.is_processed = FALSE
          AND pf.closing_home_odds IS NULL
        ORDER BY pf.id DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    logger.info(f"=== V54.9 精准定位测试开始 ===")
    logger.info(f"测试样本: {len(rows)} 场比赛")
    logger.info("")

    # 初始化 Playwright
    playwright = await async_playwright().start()
    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(Path('.playwright_stealth_profile')),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    # 访问主页
    await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    extractor = V54_9PrecisionExtractor()

    # 统计变量
    results = {
        "total": len(rows),
        "success": 0,
        "no_container": 0,
        "insufficient_odds": 0,
        "margin_invalid": 0,
        "page_error": 0,
        "margins": [],
        "logic_success_rate": 0.0,
        "avg_margin": 0.0
    }

    # 逐场处理
    for idx, (match_id, home_team, away_team, source_url) in enumerate(rows, 1):
        logger.info(f"[{idx}/{len(rows)}] 处理: {home_team} vs {away_team}")

        try:
            await page.goto(source_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(8)

            # 对于 Vue.js SPA，需要等待数据加载完成
            # 尝试等待页面中出现包含数字的链接
            try:
                # 等待至少一个包含数字格式的链接
                await page.wait_for_selector("a:has-text(/\\d+\\.\\d{2}/)", timeout=15000)
                await asyncio.sleep(3)
            except Exception:
                # 继续尝试，有些页面可能没有赔率数据
                pass

            result = await extractor.extract_match_odds(page, home_team, away_team)

            # 统计结果
            results[f"{result.status.value}"] = results.get(f"{result.status.value}", 0) + 1

            if result.status == ExtractionStatus.SUCCESS:
                results["success"] += 1
                results["margins"].append(result.margin)
                logger.info(f"  ✓ 成功: Margin = {result.margin:.4f}")
            else:
                logger.warning(f"  ✗ {result.status.value}: {result.error_detail}")

        except Exception as e:
            logger.error(f"  ✗ 处理异常: {e}")
            results["page_error"] += 1

        # 避免请求过快
        await asyncio.sleep(2)

    # 计算统计指标
    results["logic_success_rate"] = (results["success"] / results["total"] * 100
                                     if results["total"] > 0 else 0.0)

    if results["margins"]:
        results["avg_margin"] = sum(results["margins"]) / len(results["margins"])

    await browser_context.close()
    await playwright.stop()

    return results


async def main():
    """主函数"""
    results = await run_batch_test(limit=26)

    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.9 逻辑精准化补丁 - 执行报告")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"【测试样本】 {results['total']} 场比赛")
    logger.info("")
    logger.info(f"【逻辑成功率】 {results['logic_success_rate']:.2f}%")
    logger.info(f"  - 成功提取: {results['success']} 场")
    logger.info(f"  - 无容器定位: {results.get('no_container', 0)} 场")
    logger.info(f"  - 赔率不足: {results.get('insufficient_odds', 0)} 场")
    logger.info(f"  - Margin 异常: {results.get('margin_invalid', 0)} 场")
    logger.info(f"  - 页面错误: {results.get('page_error', 0)} 场")
    logger.info("")
    if results['avg_margin'] > 0:
        logger.info(f"【平均 Margin】 {results['avg_margin']:.4f}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.9 逻辑精准化补丁已就绪")
    logger.info("=" * 60)

    # 保存详细结果（Silent Mode：不输出具体数值）
    output_path = Path("logs/debug_v54_9/precision_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "V54.9",
            "report_time": "2026-01-01T00:00:00",
            "statistics": {
                "total_samples": results["total"],
                "logic_success_rate_pct": results["logic_success_rate"],
                "avg_margin": results["avg_margin"],
                "status_breakdown": {
                    "success": results["success"],
                    "no_container": results.get("no_container", 0),
                    "insufficient_odds": results.get("insufficient_odds", 0),
                    "margin_invalid": results.get("margin_invalid", 0),
                    "page_error": results.get("page_error", 0),
                }
            }
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"详细报告已保存: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
