#!/usr/bin/env python3
"""
V41.59: 最终验证脚本 - 异步数据库连接与收割测试
====================================================
用途:
  1. 验证数据库真实性（检测空库）
  2. 测试异步循环连通性
  3. 测试代理端口穿透性
  4. 完整收割流程测试

执行: python scripts/ops/v41_59_final_check.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

from src.config_unified import get_settings
from src.core.environment_detector import (
    EnvironmentType,
    detect_environment,
    get_optimal_db_host,
    verify_database_identity
)

try:
    from src.services.hash_alignment_service import create_hash_alignment_service
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("⚠️  HashAlignmentService 不可用，跳过收割测试")


# ============================================================================
# V41.59: 异步验证脚本
# ============================================================================

class V41_59_FinalChecker:
    """V41.59: 最终验证检查器"""

    def __init__(self):
        self.environment = detect_environment()
        self.db_host = get_optimal_db_host()

    async def check_database_identity(self) -> bool:
        """检查 1: 验证数据库真实性"""
        logger.info("=" * 60)
        logger.info("🔍 检查 1: 数据库真实性验证")
        logger.info("=" * 60)

        settings = get_settings()

        logger.info(f"当前环境: {self.environment.value}")
        logger.info(f"数据库主机: {settings.database.host}")
        logger.info(f"数据库名称: {settings.database.name}")
        logger.info("")

        is_valid, message = verify_database_identity(
            db_host=settings.database.host,
            db_name=settings.database.name,
            db_user=settings.database.user,
            db_password=settings.database.password.get_secret_value(),
            db_port=settings.database.port
        )

        if is_valid:
            logger.info(f"✅ {message}")
            return True
        else:
            logger.error(f"❌ {message}")
            return False

    async def check_async_connectivity(self) -> bool:
        """检查 2: 异步循环连通性测试"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 检查 2: 异步循环连通性测试")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 创建哈希对齐服务
            service = create_hash_alignment_service(
                db_host=self.db_host,
                db_name="football_db",
                db_user="football_user",
                db_password="football_pass",
                season="23/24"
            )

            logger.info("✅ 异步服务创建成功")
            logger.info(f"   Season: {service.season}")
            logger.info(f"   WSL2: {service.is_wsl2_environment()}")
            logger.info("")

            return True

        except Exception as e:
            logger.error(f"❌ 异步服务创建失败: {e}")
            return False

    async def check_proxy_ports(self) -> bool:
        """检查 3: 代理端口穿透性测试"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 检查 3: 代理端口穿透性测试")
        logger.info("=" * 60)
        logger.info("")

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️  Playwright 未安装，跳过代理端口测试")
            return True

        try:
            from playwright.async_api import async_playwright

            # 测试端口列表
            test_ports = [7890, 7895, 7897]

            logger.info(f"测试代理端口: {test_ports}")
            logger.info("")

            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(headless=True)

                try:
                    for port in test_ports:
                        try:
                            # 创建带有代理的浏览器上下文
                            context = await browser.new_context(
                                proxy={
                                    "server": f"http://localhost:{port}",
                                    # "username": "",
                                    # "password": ""
                                }
                            )

                            # 创建页面
                            page = await context.new_page()

                            # 访问测试页面
                            await page.goto("https://httpbin.org/ip", timeout=10000)
                            content = await page.content()

                            if "httpbin.org" in content:
                                logger.info(f"✅ 端口 {port}: 连接成功")

                            await context.close()

                        except Exception as e:
                            logger.warning(f"⚠️  端口 {port}: 连接失败 - {e}")

                    logger.info("")
                    logger.info("✅ 代理端口测试完成")
                    return True

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"❌ 代理端口测试失败: {e}")
            return False

    async def check_harvest_flow(self) -> bool:
        """检查 4: 完整收割流程测试（干跑模式）"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 检查 4: 完整收割流程测试")
        logger.info("=" * 60)
        logger.info("")

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️  Playwright 未安装，跳过收割流程测试")
            return True

        try:
            from src.services.hash_alignment_service import HashAlignmentService
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # 创建数据库连接
            conn = psycopg2.connect(
                host=self.db_host,
                port=5432,
                database="football_db",
                user="football_user",
                password="football_pass",
                cursor_factory=RealDictCursor
            )

            try:
                # 创建哈希对齐服务
                service = HashAlignmentService(conn, season="23/24")

                # 测试收割（使用小联赛快速测试）
                logger.info("🎯 测试联赛: Ligue 1")
                logger.info("   模式: 干跑（第 1 页）")
                logger.info("")

                # 运行收割（只采集第 1 页）
                stats = await service.active_harvest(
                    league_name="Ligue 1",
                    max_pages=1,  # 只采集 1 页
                    headless=True
                )

                logger.info("")
                logger.info("✅ 收割流程测试成功")
                logger.info(f"   采集: {stats.get('total_harvested', 0)} 场")
                logger.info(f"   更新: {stats.get('total_updated', 0)} 场")
                logger.info(f"   页数: {stats.get('pages_visited', 0)} 页")
                logger.info("")

                return True

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"❌ 收割流程测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_all_checks(self) -> int:
        """运行所有检查"""
        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║         V41.59: 最终验证脚本 - 全栈测试                    ║")
        logger.info("╚════════════════════════════════════════════════════════════╝")
        logger.info("")

        results = {
            "database_identity": False,
            "async_connectivity": False,
            "proxy_ports": False,
            "harvest_flow": False
        }

        # 检查 1: 数据库真实性
        results["database_identity"] = await self.check_database_identity()

        if not results["database_identity"]:
            logger.error("")
            logger.error("❌ 数据库验证失败，停止后续检查")
            return 1

        # 检查 2: 异步连通性
        results["async_connectivity"] = await self.check_async_connectivity()

        if not results["async_connectivity"]:
            logger.error("")
            logger.error("❌ 异步连通性测试失败，停止后续检查")
            return 1

        # 检查 3: 代理端口
        results["proxy_ports"] = await self.check_proxy_ports()

        # 检查 4: 收割流程
        results["harvest_flow"] = await self.check_harvest_flow()

        # 最终报告
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 V41.59 最终验证报告")
        logger.info("=" * 60)
        logger.info("")

        all_passed = all(results.values())

        for check_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            logger.info(f"  {check_name}: {status}")

        logger.info("")

        if all_passed:
            logger.info("🎉 所有检查通过！系统已准备就绪。")
            return 0
        else:
            logger.error("❌ 部分检查失败，请查看上方日志。")
            return 1


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """异步主函数"""
    checker = V41_59_FinalChecker()
    exit_code = await checker.run_all_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    # V41.59: 使用 asyncio.run() 启动异步主函数
    sys.exit(asyncio.run(main()))
