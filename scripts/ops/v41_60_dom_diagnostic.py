#!/usr/bin/env python3
"""
V41.60: DOM 结构深度采样诊断
====================================
用途: 对比法甲（成功）vs 英超/德甲（失败）的 HTML 结构差异
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from playwright.async_api import async_playwright

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class V41_60_DOMDiagnostic:
    """V41.60: DOM 结构诊断器"""

    # 联赛 URL 配置
    LEAGUE_URLS = {
        "Ligue 1": "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/",
        "Premier League": "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
        "Bundesliga": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
    }

    async def diagnose_league(self, league_name: str, url: str) -> dict[str, Any]:
        """诊断单个联赛的 DOM 结构

        Args:
            league_name: 联赛名称
            url: 联赛 URL

        Returns:
            诊断结果字典
        """
        logger.info("=" * 80)
        logger.info(f"🔍 诊断联赛: {league_name}")
        logger.info(f"   URL: {url}")
        logger.info("=" * 80)

        results = {
            "league": league_name,
            "url": url,
            "total_links": 0,
            "football_links": 0,
            "hash_links": 0,
            "sample_hash_links": [],
            "page_title": "",
            "dom_structure": {}
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            try:
                # 访问页面
                logger.info("📖 正在加载页面...")
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)  # 等待 JS 渲染

                # 获取页面标题
                results["page_title"] = await page.title()
                logger.info(f"   页面标题: {results['page_title']}")

                # 分析所有链接
                logger.info("\n🔗 分析链接结构...")

                # 1. 统计所有链接
                all_links = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a');
                        return {
                            total: links.length,
                            sample: Array.from(links).slice(0, 5).map(a => ({
                                href: a.getAttribute('href'),
                                text: a.textContent?.trim().slice(0, 30)
                            }))
                        };
                    }
                """)
                results["total_links"] = all_links["total"]
                logger.info(f"   总链接数: {results['total_links']}")

                # 2. 统计包含 /football/ 的链接
                football_links = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href*="/football/"]');
                        return {
                            total: links.length,
                            sample: Array.from(links).slice(0, 5).map(a => ({
                                href: a.getAttribute('href'),
                                text: a.textContent?.trim().slice(0, 30)
                            }))
                        };
                    }
                """)
                results["football_links"] = football_links["total"]
                logger.info(f"   /football/ 链接数: {results['football_links']}")

                # 3. 统计匹配 8 位 hash 的链接
                hash_links = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href*="/football/"]');
                        const hashLinks = [];

                        links.forEach(link => {
                            const href = link.getAttribute('href');
                            // 匹配 8 位 hash 结尾的链接
                            if (href && href.match(/-[a-zA-Z0-9]{8}\\/?$/)) {
                                hashLinks.push({
                                    href: href,
                                    text: link.textContent?.trim().slice(0, 50)
                                });
                            }
                        });

                        return {
                            total: hashLinks.length,
                            sample: hashLinks.slice(0, 10)
                        };
                    }
                """)
                results["hash_links"] = hash_links["total"]
                results["sample_hash_links"] = hash_links["sample"]
                logger.info(f"   8位hash链接数: {results['hash_links']}")

                if results["hash_links"] > 0:
                    logger.info("\n   示例 hash 链接:")
                    for i, link in enumerate(results["sample_hash_links"][:5], 1):
                        logger.info(f"      {i}. {link['href']}")
                        if link.get('text'):
                            logger.info(f"         文本: {link['text']}")
                else:
                    logger.warning("\n   ⚠️  未找到任何 hash 链接！")
                    logger.warning("   需要进一步分析页面结构...")

                    # 额外诊断：检查页面是否有其他比赛数据结构
                    await self._diagnose_alternative_structure(page, results)

                # 4. 分析 DOM 结构
                logger.info("\n🏗️  分析 DOM 结构...")
                results["dom_structure"] = await page.evaluate("""
                    () => {
                        const structure = {};

                        // 检查常见的比赛容器
                        const selectors = [
                            'div[class*="event"]',
                            'div[class*="match"]',
                            'div[class*="row"]',
                            'tr[class*="event"]',
                            'tr[class*="match"]',
                            'table[class*="matches"]',
                            'div[id*="matches"]',
                            'div[id*="tournament"]'
                        ];

                        selectors.forEach(sel => {
                            try {
                                const elements = document.querySelectorAll(sel);
                                if (elements.length > 0) {
                                    structure[sel] = {
                                        count: elements.length,
                                        sample_class: elements[0].className,
                                        sample_id: elements[0].id || ''
                                    };
                                }
                            } catch (e) {
                                // 忽略选择器错误
                            }
                        });

                        return structure;
                    }
                """)

                if results["dom_structure"]:
                    logger.info("   发现的 DOM 结构:")
                    for selector, info in results["dom_structure"].items():
                        logger.info(f"      {selector}: {info['count']} 个元素")
                        if info.get('sample_class'):
                            logger.info(f"         类名示例: {info['sample_class'][:50]}")

            except Exception as e:
                logger.error(f"❌ 诊断失败: {e}")
                import traceback
                traceback.print_exc()

            finally:
                await browser.close()

        return results

    async def _diagnose_alternative_structure(self, page, results: dict[str, Any]):
        """诊断替代的页面结构（当找不到 hash 链接时）"""
        logger.info("\n🔬 执行深度结构分析...")

        # 检查是否有表格数据
        table_info = await page.evaluate("""
            () => {
                const tables = document.querySelectorAll('table');
                const tableData = [];

                tables.forEach((table, idx) => {
                    const rows = table.querySelectorAll('tr');
                    tableData.push({
                        index: idx,
                        total_rows: rows.length,
                        has_links: table.querySelectorAll('a').length,
                        class_name: table.className,
                        id: table.id || ''
                    });
                });

                return tableData;
            }
        """)

        if table_info:
            logger.info("   发现的表格:")
            for table in table_info[:5]:
                logger.info(f"      表格 {table['index']}: {table['total_rows']} 行, "
                           f"{table['has_links']} 个链接")

    async def run_all_diagnostics(self) -> None:
        """运行所有联赛的诊断"""
        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║         V41.60: DOM 结构深度采样诊断                        ║")
        logger.info("╚════════════════════════════════════════════════════════════╝")
        logger.info("")

        all_results = []

        for league_name, url in self.LEAGUE_URLS.items():
            result = await self.diagnose_league(league_name, url)
            all_results.append(result)
            logger.info("")
            await asyncio.sleep(2)  # 避免请求过快

        # 生成对比报告
        self._generate_comparison_report(all_results)

    def _generate_comparison_report(self, results: list[dict[str, Any]]) -> None:
        """生成对比报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 对比分析报告")
        logger.info("=" * 80)

        # 表格对比
        logger.info("\n┌─────────────────────┬────────────┬──────────────┬──────────────┐")
        logger.info("│ 联赛                │ 总链接数   │ /football/   │ 8位hash链接  │")
        logger.info("├─────────────────────┼────────────┼──────────────┼──────────────┤")

        for result in results:
            logger.info(f"│ {result['league']:<19} │ {result['total_links']:>10} │ "
                       f"{result['football_links']:>12} │ {result['hash_links']:>12} │")

        logger.info("└─────────────────────┴────────────┴──────────────┴──────────────┘")

        # 问题联赛分析
        logger.info("\n🔍 问题联赛分析:")
        for result in results:
            if result["hash_links"] == 0:
                logger.info(f"\n  ⚠️  {result['league']} - 提取失败")
                logger.info(f"     页面标题: {result['page_title']}")
                if result.get("dom_structure"):
                    logger.info("     发现的 DOM 结构:")
                    for selector, info in result["dom_structure"].items():
                        logger.info(f"       - {selector}: {info['count']} 个")

        # 成功联赛分析
        logger.info("\n✅ 成功联赛分析:")
        for result in results:
            if result["hash_links"] > 0:
                logger.info(f"\n  🎯 {result['league']} - 提取成功 ({result['hash_links']} 场)")
                logger.info(f"     示例链接:")
                for link in result["sample_hash_links"][:3]:
                    logger.info(f"       - {link['href']}")


async def main():
    """主函数"""
    diagnostic = V41_60_DOMDiagnostic()
    await diagnostic.run_all_diagnostics()


if __name__ == "__main__":
    asyncio.run(main())
