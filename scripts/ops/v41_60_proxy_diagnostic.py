#!/usr/bin/env python3
"""
V41.60: 代理环境诊断 - 模拟真实收割环境
==============================================
用途: 使用代理访问页面，诊断收割失败的根本原因
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


class V41_60_ProxyDiagnostic:
    """V41.60: 代理环境诊断器"""

    # WSL2 代理配置
    WSL2_PROXY_HOST = "172.25.16.1"
    PROXY_PORTS = list(range(7890, 7900))  # 7890-7899

    # 联赛 URL 配置
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

    async def diagnose_with_proxy(
        self,
        league_name: str,
        url: str,
        proxy_port: int
    ) -> dict:
        """使用代理诊断联赛页面

        Args:
            league_name: 联赛名称
            url: 联赛 URL
            proxy_port: 代理端口

        Returns:
            诊断结果字典
        """
        logger.info("=" * 80)
        logger.info(f"🔍 诊断联赛: {league_name}")
        logger.info(f"   URL: {url}")
        logger.info(f"   代理: {self.WSL2_PROXY_HOST}:{proxy_port}")
        logger.info("=" * 80)

        result = {
            "league": league_name,
            "proxy_port": proxy_port,
            "proxy_working": False,
            "page_loaded": False,
            "total_links": 0,
            "hash_links": 0,
            "error": None
        }

        # 检查代理端口
        if not await self.check_proxy_port(proxy_port):
            result["error"] = f"代理端口 {proxy_port} 不可用"
            logger.warning(f"   ⚠️  {result['error']}")
            return result

        result["proxy_working"] = True
        logger.info("   ✅ 代理端口可用")

        async with async_playwright() as p:
            browser = None
            try:
                # 使用代理启动浏览器
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

                # 访问页面
                logger.info("   📖 正在加载页面...")
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # 等待动态内容加载
                await asyncio.sleep(5)

                result["page_loaded"] = True
                logger.info(f"   ✅ 页面加载成功: {await page.title()}")

                # 统计链接
                links = await page.evaluate("""
                    () => {
                        const hashLinks = document.querySelectorAll('a[href*="/football/"]');
                        let hashCount = 0;

                        hashLinks.forEach(link => {
                            const href = link.getAttribute('href');
                            if (href && href.match(/-[a-zA-Z0-9]{8}\\/?$/)) {
                                hashCount++;
                            }
                        });

                        return {
                            total: hashLinks.length,
                            hash: hashCount
                        };
                    }
                """)

                result["total_links"] = links["total"]
                result["hash_links"] = links["hash"]

                logger.info(f"   📊 链接统计:")
                logger.info(f"      /football/ 链接: {result['total_links']}")
                logger.info(f"      8位 hash 链接: {result['hash_links']}")

                if result["hash_links"] > 0:
                    logger.info(f"   ✅ {league_name} 提取成功！")
                else:
                    logger.warning(f"   ⚠️  {league_name} 提取失败（0 个 hash）")

                    # 深度诊断：检查页面内容
                    page_content = await page.evaluate("""
                        () => {
                            return {
                                body_text: document.body?.innerText?.slice(0, 200) || '',
                                has_tables: document.querySelectorAll('table').length,
                                has_divs: document.querySelectorAll('div').length
                            };
                        }
                    """)

                    logger.info(f"   🔬 页面内容分析:")
                    logger.info(f"      Body 文本: {page_content['body_text'][:100]}...")
                    logger.info(f"      表格数: {page_content['has_tables']}")
                    logger.info(f"      Div 数: {page_content['has_divs']}")

            except Exception as e:
                result["error"] = str(e)
                logger.error(f"   ❌ 诊断失败: {e}")

            finally:
                if browser:
                    await browser.close()

        return result

    async def run_proxy_diagnostics(self):
        """运行代理诊断"""
        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║         V41.60: 代理环境诊断                                ║")
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
            result = await self.diagnose_with_proxy(league_name, url, proxy_port)
            all_results.append(result)
            logger.info("")
            await asyncio.sleep(2)

        # 生成报告
        self._generate_report(all_results)

    def _generate_report(self, results: list[dict]):
        """生成诊断报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 代理环境诊断报告")
        logger.info("=" * 80)

        logger.info("\n┌─────────────────────┬──────────┬────────────┬──────────────┐")
        logger.info("│ 联赛                │ 代理端口  │ 页面加载   │ hash 链接数  │")
        logger.info("├─────────────────────┼──────────┼────────────┼──────────────┤")

        for result in results:
            page_status = "✅" if result["page_loaded"] else "❌"
            logger.info(f"│ {result['league']:<19} │ {result['proxy_port']:>8} │ "
                       f"{page_status:>10} │ {result['hash_links']:>12} │")

        logger.info("└─────────────────────┴──────────┴────────────┴──────────────┘")

        # 问题分析
        logger.info("\n🔍 问题分析:")

        failed_results = [r for r in results if r["hash_links"] == 0 and r["page_loaded"]]
        if failed_results:
            logger.info("\n⚠️  页面加载成功但提取失败的联赛:")
            for result in failed_results:
                logger.info(f"   - {result['league']}")
                if result.get("error"):
                    logger.info(f"     错误: {result['error']}")
        else:
            logger.info("\n✅ 所有联赛在代理环境下都能成功提取！")

        # 成功联赛
        success_results = [r for r in results if r["hash_links"] > 0]
        if success_results:
            logger.info("\n🎯 提取成功的联赛:")
            for result in success_results:
                logger.info(f"   - {result['league']}: {result['hash_links']} 个 hash")


async def main():
    """主函数"""
    diagnostic = V41_60_ProxyDiagnostic()
    await diagnostic.run_proxy_diagnostics()


if __name__ == "__main__":
    asyncio.run(main())
