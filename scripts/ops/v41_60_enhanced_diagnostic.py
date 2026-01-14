#!/usr/bin/env python3
"""
V41.60: 增强版诊断 - 模拟真实收割环境
========================================
用途: 完全模拟实际收割流程，包括等待策略和页面状态检查
"""

import asyncio
import sys
import os
from pathlib import Path

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


class V41_60_EnhancedDiagnostic:
    """V41.60: 增强版诊断器 - 完全模拟收割环境"""

    # WSL2 代理配置
    WSL2_PROXY_HOST = "172.25.16.1"
    PROXY_PORTS = list(range(7890, 7900))

    # 联赛 URL 配置（与实际收割一致）
    LEAGUE_URLS = {
        "Premier League": "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
        "Bundesliga": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
        "Ligue 1": "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/",
    }

    async def check_proxy_port(self, port: int) -> bool:
        """检查代理端口是否健康"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((self.WSL2_PROXY_HOST, port))
                return result == 0
        except Exception:
            return False

    async def diagnose_with_harvest_simulation(
        self,
        league_name: str,
        url: str,
        proxy_port: int
    ) -> dict:
        """完全模拟实际收割流程的诊断

        Args:
            league_name: 联赛名称
            url: 联赛 URL
            proxy_port: 代理端口

        Returns:
            诊断结果字典
        """
        logger.info("=" * 80)
        logger.info(f"🎯 模拟收割: {league_name}")
        logger.info(f"   URL: {url}")
        logger.info(f"   代理: {self.WSL2_PROXY_HOST}:{proxy_port}")
        logger.info("=" * 80)

        result = {
            "league": league_name,
            "proxy_port": proxy_port,
            "steps": [],
            "final_hash_count": 0,
            "success": False
        }

        async def log_step(step_name: str, details: str = ""):
            """记录诊断步骤"""
            step = {"name": step_name, "details": details}
            result["steps"].append(step)
            logger.info(f"   [{len(result['steps'])}] {step_name}")
            if details:
                logger.info(f"       {details}")

        await log_step("启动浏览器", f"代理端口 {proxy_port}")

        async with async_playwright() as p:
            browser = None
            try:
                # 使用代理启动浏览器（与实际收割一致）
                browser = await p.chromium.launch(
                    headless=True,
                    proxy={
                        "server": f"http://{self.WSL2_PROXY_HOST}:{proxy_port}"
                    }
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # 步骤 1: 访问页面
                await log_step("访问页面", f"URL: {url}")
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # 步骤 2: 初始等待（与实际收割一致）
                await log_step("初始等待", "等待 3 秒（networkidle 后）")
                await asyncio.sleep(3)

                # 步骤 3: 检查页面标题
                title = await page.title()
                await log_step("页面标题", title)

                # 步骤 4: 第一次提取尝试（收割代码的逻辑）
                hash_count_1st = await self._count_hash_links(page)
                await log_step("第一次提取尝试", f"找到 {hash_count_1st} 个 hash 链接")

                if hash_count_1st > 0:
                    result["success"] = True
                    result["final_hash_count"] = hash_count_1st
                    await log_step("✅ 提取成功", f"共 {hash_count_1st} 场比赛")
                else:
                    # 步骤 5: 深度分析页面状态
                    await log_step("深度页面分析", "检查为什么没有找到 hash")

                    page_analysis = await page.evaluate("""
                        () => {
                            const analysis = {
                                // 检查是否有赛季选择器
                                has_season_selector: false,
                                // 检查是否有比赛表格
                                has_match_table: false,
                                // 页面文本摘要
                                body_preview: '',
                                // 检查 Vue app
                                vue_app_mounted: false,
                            };

                            // 检查赛季选择器
                            const seasonElements = document.querySelectorAll('[class*="season"]');
                            analysis.has_season_selector = seasonElements.length > 0;

                            // 检查表格
                            const tables = document.querySelectorAll('table');
                            analysis.has_match_table = tables.length > 0;

                            // 页面文本
                            if (document.body) {
                                analysis.body_preview = document.body.innerText.slice(0, 300);
                            }

                            // 检查 Vue
                            const vueApp = document.querySelector('#app');
                            analysis.vue_app_mounted = vueApp !== null;

                            return analysis;
                        }
                    """)

                    await log_step("页面分析结果", "")
                    if page_analysis["has_season_selector"]:
                        logger.info(f"       ⚠️  检测到赛季选择器（可能是初始状态）")
                    if page_analysis["has_match_table"]:
                        logger.info(f"       ✅ 检测到比赛表格")
                    if page_analysis["vue_app_mounted"]:
                        logger.info(f"       ✅ Vue app 已挂载")

                    logger.info(f"       页面文本预览: {page_analysis['body_preview'][:100]}...")

                    # 步骤 6: 尝试滚动页面（触发动态加载）
                    await log_step("尝试滚动触发加载", "滚动到页面底部")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                    hash_count_after_scroll = await self._count_hash_links(page)
                    await log_step("滚动后提取", f"找到 {hash_count_after_scroll} 个 hash 链接")

                    if hash_count_after_scroll > 0:
                        result["success"] = True
                        result["final_hash_count"] = hash_count_after_scroll
                        await log_step("✅ 滚动后提取成功", f"共 {hash_count_after_scroll} 场比赛")
                    else:
                        # 步骤 7: 尝试点击特定元素
                        await log_step("尝试点击触发", "查找可点击元素")
                        clicked = await self._try_click_elements(page)
                        await asyncio.sleep(3)

                        hash_count_after_click = await self._count_hash_links(page)
                        await log_step("点击后提取", f"找到 {hash_count_after_click} 个 hash 链接")

                        result["final_hash_count"] = hash_count_after_click
                        if hash_count_after_click > 0:
                            result["success"] = True
                            await log_step("✅ 点击后提取成功", f"共 {hash_count_after_click} 场比赛")
                        else:
                            await log_step("❌ 所有尝试失败", "无法提取比赛数据")

                # 最终结果
                if result["success"]:
                    logger.info(f"\n   🎉 {league_name} 诊断成功！")
                else:
                    logger.warning(f"\n   ⚠️  {league_name} 诊断失败")

            except Exception as e:
                await log_step("❌ 异常", str(e))
                import traceback
                traceback.print_exc()

            finally:
                if browser:
                    await browser.close()

        return result

    async def _count_hash_links(self, page) -> int:
        """统计 8 位 hash 链接数量"""
        count = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[href*="/football/"]');
                let hashCount = 0;

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (href && href.match(/-[a-zA-Z0-9]{8}\\/?$/)) {
                        hashCount++;
                    }
                });

                return hashCount;
            }
        """)
        return count

    async def _try_click_elements(self, page) -> bool:
        """尝试点击可能触发内容加载的元素"""
        selectors_to_try = [
            'button:has-text("Results")',
            'a:has-text("Results")',
            '[class*="show-more"]',
            '[class*="load-more"]',
            'div[class*="season"]',
            'select[name="season"]',
        ]

        for selector in selectors_to_try:
            try:
                element = await page.query_selector(selector)
                if element:
                    # 检查元素是否可见
                    is_visible = await element.is_visible()
                    if is_visible:
                        logger.info(f"       找到可点击元素: {selector}")
                        await element.click()
                        return True
            except Exception:
                continue

        return False

    async def run_enhanced_diagnostics(self):
        """运行增强版诊断"""
        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║         V41.60: 增强版诊断（模拟收割流程）                  ║")
        logger.info("╚════════════════════════════════════════════════════════════╝")
        logger.info("")

        # 找到第一个可用的代理端口
        proxy_port = None
        for port in self.PROXY_PORTS:
            if await self.check_proxy_port(port):
                proxy_port = port
                break

        if not proxy_port:
            logger.error("❌ 未找到可用的代理端口")
            return

        logger.info(f"🔌 使用代理端口: {proxy_port}")
        logger.info("")

        all_results = []

        for league_name, url in self.LEAGUE_URLS.items():
            result = await self.diagnose_with_harvest_simulation(league_name, url, proxy_port)
            all_results.append(result)
            logger.info("")
            await asyncio.sleep(2)

        # 生成最终报告
        self._generate_final_report(all_results)

    def _generate_final_report(self, results: list[dict]):
        """生成最终诊断报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 V41.60 最终诊断报告")
        logger.info("=" * 80)

        logger.info("\n┌─────────────────────┬────────────┬──────────────┐")
        logger.info("│ 联赛                │ 最终状态   │ Hash 数量    │")
        logger.info("├─────────────────────┼────────────┼──────────────┤")

        for result in results:
            status = "✅ 成功" if result["success"] else "❌ 失败"
            logger.info(f"│ {result['league']:<19} │ {status:>10} │ {result['final_hash_count']:>12} │")

        logger.info("└─────────────────────┴────────────┴──────────────┘")

        # 失败联赛的详细步骤分析
        failed_results = [r for r in results if not r["success"]]
        if failed_results:
            logger.info("\n🔍 失败联赛的详细步骤:")
            for result in failed_results:
                logger.info(f"\n  ⚠️  {result['league']}:")
                for i, step in enumerate(result["steps"], 1):
                    logger.info(f"     {i}. {step['name']}")
                    if step.get("details"):
                        logger.info(f"        {step['details']}")

        # 成功联赛
        success_results = [r for r in results if r["success"]]
        if success_results:
            logger.info("\n🎯 成功联赛:")
            for result in success_results:
                logger.info(f"   ✅ {result['league']}: {result['final_hash_count']} 场")

        # 推荐行动
        logger.info("\n💡 推荐行动:")
        if len(success_results) == len(results):
            logger.info("   ✅ 所有联赛诊断成功，可以继续收割")
        elif len(success_results) > 0:
            logger.info(f"   ⚠️  {len(success_results)}/{len(results)} 联赛成功")
            logger.info("   建议: 对失败联赛进行进一步分析或使用不同的收割策略")
        else:
            logger.info("   🚨 所有联赛诊断失败")
            logger.info("   建议: 检查代理配置、网络连接或 OddsPortal 网站变化")


async def main():
    """主函数"""
    diagnostic = V41_60_EnhancedDiagnostic()
    await diagnostic.run_enhanced_diagnostics()


if __name__ == "__main__":
    asyncio.run(main())
