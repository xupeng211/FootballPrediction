#!/usr/bin/env python3
"""
V37.1 全量采集前最终自检脚本
===========================
在启动全量采集前执行，确保环境就绪

检查项目:
1. 数据库连接是否为 Docker 的 PG 15？
2. Pydantic 模型是否能加载 24/25 最新的 API 数据？
3. 磁盘剩余空间是否大于 20GB？
4. 数据库 Schema 是否包含 collection_audit_logs 表？
5. L2 采集器配置是否正确？

作者: ML Architect
日期: 2025-12-29
Phase: Production-Grade
Version: V37.1
"""

import asyncio
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
import asyncpg
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.schemas.l2_match_schema import (
    L2CollectionSummary,
    L2DataQuality,
    L2MatchDetailSchema,
)
from src.config_unified import get_settings


class Colors:
    """终端颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class PreHarvestFinalCheck:
    """V37.1 全量采集前最终自检"""

    def __init__(self):
        self.results = []
        self.pass_count = 0
        self.fail_count = 0
        self.warn_count = 0

    def _print_header(self, title: str):
        """打印标题"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    def _print_result(self, name: str, status: str, message: str = ""):
        """打印结果"""
        icon = {"✅ PASS": "✅", "❌ FAIL": "❌", "⚠️  WARN": "⚠️ "}.get(status, "•")
        color = {"✅ PASS": Colors.GREEN, "❌ FAIL": Colors.RED, "⚠️  WARN": Colors.YELLOW}.get(status, Colors.RESET)

        print(f"  {color}{icon} {name}{Colors.RESET}")
        if message:
            print(f"     {message}")

        self.results.append({"name": name, "status": status, "message": message})
        if status == "✅ PASS":
            self.pass_count += 1
        elif status == "❌ FAIL":
            self.fail_count += 1
        else:
            self.warn_count += 1

    async def check_database_connection(self):
        """检查 1: 数据库连接"""
        self._print_header("检查 1: 数据库连接")

        try:
            settings = get_settings()

            # 连接数据库
            conn = await asyncpg.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            # 获取版本信息
            version = await conn.fetchval("SELECT version()")
            await conn.close()

            # 检查是否为 PG 15
            is_pg15 = "PostgreSQL 15" in version

            self._print_result(
                "数据库连接",
                "✅ PASS" if is_pg15 else "⚠️  WARN",
                f"版本: {version[:50]}..."
            )

            # 检查数据库是否存在 raw_match_data 表
            conn = await asyncpg.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'raw_match_data'
                )
                """
            )

            await conn.close()

            self._print_result(
                "raw_match_data 表",
                "✅ PASS" if table_exists else "❌ FAIL",
            )

        except Exception as e:
            self._print_result("数据库连接", "❌ FAIL", str(e))

    async def check_audit_logs_table(self):
        """检查 2: collection_audit_logs 表"""
        self._print_header("检查 2: collection_audit_logs 审计表")

        try:
            settings = get_settings()
            conn = await asyncpg.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'collection_audit_logs'
                )
                """
            )

            await conn.close()

            if table_exists:
                self._print_result("collection_audit_logs 表", "✅ PASS")
            else:
                self._print_result(
                    "collection_audit_logs 表",
                    "⚠️  WARN",
                    "表不存在，请运行: python src/database/migrations/create_collection_audit_logs.sql.py"
                )

        except Exception as e:
            self._print_result("collection_audit_logs 表", "❌ FAIL", str(e))

    async def check_pydantic_model_with_api(self):
        """检查 3: Pydantic 模型是否能加载最新 API 数据"""
        self._print_header("检查 3: Pydantic 模型兼容性 (24/25 赛季)")

        try:
            # 测试 API 端点 - 24/25 赛季最新比赛
            test_match_id = "4935409"  # 24/25 赛季的一场英超比赛
            url = f"https://www.fotmob.com/api/matchDetails?matchId={test_match_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        self._print_result(
                            "FotMob API 连接",
                            "❌ FAIL",
                            f"HTTP {response.status}"
                        )
                        return

                    data = await response.json()

            # 尝试解析数据
            from src.api.collectors.production_l2_collector import ProductionL2Collector

            # 模拟解析
            content = data.get("content", {})
            stats_obj = content.get("stats", None)
            stats_data = None

            if stats_obj:
                periods = stats_obj.get("Period", [])
                if periods:
                    full_match = periods[0]
                    stats_data = {
                        "xg": self._extract_stat_list(full_match.get("xG")),
                        "shots_on_target": self._extract_stat_list(full_match.get("shotsOnTarget")),
                    }

            # 创建 Schema 实例
            schema = L2MatchDetailSchema(
                match_id=test_match_id,
                stats=stats_data,
                raw_data=data,
            )

            self._print_result(
                "Pydantic 模型兼容性",
                "✅ PASS",
                f"数据质量: {schema.data_quality.value}"
            )

        except Exception as e:
            self._print_result("Pydantic 模型兼容性", "❌ FAIL", str(e))

    def _extract_stat_list(self, stat_obj):
        """提取统计数据列表"""
        if stat_obj is None:
            return None
        try:
            return [float(stat_obj.get("home", 0)), float(stat_obj.get("away", 0))]
        except (ValueError, TypeError):
            return None

    def check_disk_space(self):
        """检查 4: 磁盘剩余空间"""
        self._print_header("检查 4: 磁盘剩余空间")

        try:
            # 检查 / 目录剩余空间
            total, used, free = shutil.disk_usage("/")

            free_gb = free / (1024 ** 3)

            if free_gb >= 20:
                self._print_result(
                    "磁盘剩余空间",
                    "✅ PASS",
                    f"{free_gb:.1f} GB 可用"
                )
            elif free_gb >= 10:
                self._print_result(
                    "磁盘剩余空间",
                    "⚠️  WARN",
                    f"{free_gb:.1f} GB 可用 (建议 > 20GB)"
                )
            else:
                self._print_result(
                    "磁盘剩余空间",
                    "❌ FAIL",
                    f"{free_gb:.1f} GB 可用 (需要 > 10GB)"
                )

        except Exception as e:
            self._print_result("磁盘剩余空间", "❌ FAIL", str(e))

    def check_environment_variables(self):
        """检查 5: 环境变量配置"""
        self._print_header("检查 5: 环境变量配置")

        # 检查 .env 文件
        env_file = project_root / ".env"
        if env_file.exists():
            self._print_result(".env 文件", "✅ PASS")
            load_dotenv()
        else:
            self._print_result(".env 文件", "⚠️  WARN", "未找到 .env 文件，使用环境变量")

        # 检查关键环境变量
        settings = get_settings()

        checks = [
            ("DB_HOST", settings.database.host),
            ("DB_NAME", settings.database.name),
            ("DB_USER", settings.database.user),
            ("DB_PASSWORD", "***" if settings.database.password else ""),
        ]

        for name, value in checks:
            if value:
                self._print_result(f"环境变量 {name}", "✅ PASS")
            else:
                self._print_result(f"环境变量 {name}", "❌ FAIL", "未设置")

    def check_project_structure(self):
        """检查 6: 项目结构完整性"""
        self._print_header("检查 6: 项目结构完整性")

        required_paths = [
            "src/api/collectors/production_l2_collector.py",
            "src/api/collectors/schemas/l2_match_schema.py",
            "scripts/collectors/full_l1_l2_harvest.py",
            "deploy/docker/Dockerfile",
            "deploy/docker/init_db.sql",
        ]

        for path in required_paths:
            full_path = project_root / path
            if full_path.exists():
                self._print_result(f"文件 {path}", "✅ PASS")
            else:
                self._print_result(f"文件 {path}", "❌ FAIL", "文件不存在")

    def check_l2_collector_config(self):
        """检查 7: L2 采集器配置"""
        self._print_header("检查 7: L2 采集器配置")

        try:
            from src.api.collectors.production_l2_collector import ProductionL2Collector

            # 检查默认配置
            if hasattr(ProductionL2Collector, 'BATCH_SIZE'):
                batch_size = ProductionL2Collector.BATCH_SIZE
                if batch_size == 50:
                    self._print_result("L2 BATCH_SIZE", "✅ PASS", f"{batch_size} 场/批")
                else:
                    self._print_result("L2 BATCH_SIZE", "⚠️  WARN", f"{batch_size} (预期 50)")

            # 检查 API URL
            api_url = ProductionL2Collector.API_URL
            if "fotmob.com" in api_url:
                self._print_result("FotMob API URL", "✅ PASS")
            else:
                self._print_result("FotMob API URL", "❌ FAIL", f"错误的 URL: {api_url}")

        except Exception as e:
            self._print_result("L2 采集器配置", "❌ FAIL", str(e))

    async def run_all_checks(self):
        """运行所有检查"""
        print(f"\n{Colors.BOLD}V37.1 全量采集前最终自检{Colors.RESET}")
        print(f"{Colors.BOLD}执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")

        await self.check_database_connection()
        await self.check_audit_logs_table()
        await self.check_pydantic_model_with_api()
        self.check_disk_space()
        self.check_environment_variables()
        self.check_project_structure()
        self.check_l2_collector_config()

        self._print_summary()

    def _print_summary(self):
        """打印摘要"""
        self._print_header("检查摘要")

        total = self.pass_count + self.fail_count + self.warn_count
        pass_rate = (self.pass_count / total * 100) if total > 0 else 0

        print(f"\n  总检查项: {total}")
        print(f"  {Colors.GREEN}✅ 通过: {self.pass_count}{Colors.RESET}")
        print(f"  {Colors.YELLOW}⚠️  警告: {self.warn_count}{Colors.RESET}")
        print(f"  {Colors.RED}❌ 失败: {self.fail_count}{Colors.RESET}")
        print(f"  通过率: {pass_rate:.1f}%")

        if self.fail_count == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 所有检查通过！可以启动全量采集。{Colors.RESET}\n")
            return 0
        else:
            print(f"\n  {Colors.RED}{Colors.BOLD}⛔ 有 {self.fail_count} 项检查失败！请修复后重试。{Colors.RESET}\n")
            return 1


async def main():
    """主函数"""
    checker = PreHarvestFinalCheck()
    exit_code = await checker.run_all_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
