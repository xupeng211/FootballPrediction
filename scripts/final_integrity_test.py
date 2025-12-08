#!/usr/bin/env python3
"""
最终系统完整性测试脚本
Final System Integrity Test Script

修复验证:
1. SQLAlchemy text() 语法修复
2. 配置文件存在性验证
3. backfill_full_history.py 启动测试
4. 基础功能完整性验证

Author: QA Engineer
Version: 1.0.0
Date: 2025-01-08
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class IntegrityTestResults:
    """完整性测试结果"""
    def __init__(self):
        self.tests = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []

    def add_test(self, test_name: str, passed: bool, error: str = None):
        """添加测试结果"""
        self.tests[test_name] = {
            "passed": passed,
            "error": error
        }
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            if error:
                self.errors.append(f"{test_name}: {error}")

    def get_summary(self) -> str:
        """获取测试总结"""
        return f"""
📊 完整性测试总结
================
总测试数: {self.total_tests}
✅ 通过: {self.passed_tests}
❌ 失败: {self.failed_tests}
📈 通过率: {(self.passed_tests / self.total_tests * 100):.1f}%
"""

    def print_detailed_results(self):
        """打印详细结果"""
        logger.info("=" * 60)
        logger.info("🧪 详细测试结果:")
        for test_name, result in self.tests.items():
            status = "✅ 通过" if result["passed"] else "❌ 失败"
            logger.info(f"  {test_name}: {status}")
            if not result["passed"] and result["error"]:
                logger.info(f"    错误: {result['error']}")

class SystemIntegrityTester:
    """系统完整性测试器"""

    def __init__(self):
        self.results = IntegrityTestResults()
        self.project_root = project_root

    async def test_config_file_existence(self) -> bool:
        """测试配置文件存在性"""
        try:
            logger.info("🔍 测试配置文件存在性...")

            config_file = self.project_root / "config" / "target_leagues.json"
            if not config_file.exists():
                return False, f"配置文件不存在: {config_file}"

            # 验证文件格式
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            if "leagues" not in config_data:
                return False, "配置文件缺少 'leagues' 字段"

            if not isinstance(config_data["leagues"], list):
                return False, "配置文件 'leagues' 字段不是列表"

            league_count = len(config_data["leagues"])
            logger.info(f"✅ 配置文件验证成功，包含 {league_count} 个联赛")
            return True, f"配置文件有效，包含 {league_count} 个联赛"

        except json.JSONDecodeError as e:
            return False, f"配置文件 JSON 格式错误: {e}"
        except Exception as e:
            return False, f"配置文件检查失败: {e}"

    async def test_sqlalchemy_text_syntax(self) -> bool:
        """测试 SQLAlchemy text() 语法"""
        try:
            logger.info("🔍 测试 SQLAlchemy text() 语法...")

            # 导入必要的模块
            from sqlalchemy import text
            from database.async_manager import get_db_session, initialize_database

            # 初始化数据库
            initialize_database()

            # 测试各种 SQL 语句语法
            test_queries = [
                "SELECT 1 as test_column",
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'matches'",
                "SELECT id FROM matches LIMIT 1",  # 🔧 修复: 使用存在的列
            ]

            async with get_db_session() as session:
                for query in test_queries:
                    result = await session.execute(text(query))
                    result.fetchone()  # 执行查询

            logger.info("✅ SQLAlchemy text() 语法测试成功")
            return True, "所有 SQL 语句语法正确"

        except ImportError as e:
            return False, f"导入模块失败: {e}"
        except Exception as e:
            return False, f"SQLAlchemy 语法测试失败: {e}"

    async def test_backfill_script_initialization(self) -> bool:
        """测试回填脚本初始化"""
        try:
            logger.info("🔍 测试回填脚本初始化...")

            # 设置环境变量
            if not os.getenv("DATABASE_URL"):
                os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/football_prediction"

            # 导入回填引擎
            from scripts.backfill_full_history import IndustrialBackfillEngine

            # 创建引擎并初始化
            engine = IndustrialBackfillEngine()
            await engine.initialize()

            # 清理资源
            await engine.cleanup()

            logger.info("✅ 回填脚本初始化成功")
            return True, "回填引擎初始化和清理成功"

        except ImportError as e:
            return False, f"导入回填脚本失败: {e}"
        except Exception as e:
            return False, f"回填脚本初始化失败: {e}"

    async def test_config_loading_in_backfill(self) -> bool:
        """测试回填脚本中的配置加载"""
        try:
            logger.info("🔍 测试回填脚本配置加载...")

            from scripts.backfill_full_history import IndustrialBackfillEngine

            # 创建引擎
            engine = IndustrialBackfillEngine()
            await engine.initialize()

            # 加载联赛配置
            leagues = await engine.load_league_config()

            if not leagues:
                await engine.cleanup()
                return False, "加载的联赛配置为空"

            # 验证配置结构
            valid_leagues = 0
            for league in leagues:
                if "id" in league and "name" in league:
                    valid_leagues += 1

            if valid_leagues == 0:
                await engine.cleanup()
                return False, "没有有效的联赛配置"

            await engine.cleanup()
            logger.info(f"✅ 配置加载成功，包含 {valid_leagues} 个有效联赛")
            return True, f"成功加载 {valid_leagues} 个有效联赛"

        except Exception as e:
            return False, f"配置加载测试失败: {e}"

    async def test_database_connectivity(self) -> bool:
        """测试数据库连接性"""
        try:
            logger.info("🔍 测试数据库连接性...")

            from database.async_manager import get_db_session, initialize_database
            from sqlalchemy import text  # 🔧 修复: 导入 text 函数

            # 初始化数据库
            initialize_database()

            # 测试连接
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1 as connection_test"))
                test_result = result.fetchone()

                if not test_result or test_result[0] != 1:
                    return False, "数据库连接测试查询失败"

            logger.info("✅ 数据库连接正常")
            return True, "数据库连接测试成功"

        except Exception as e:
            return False, f"数据库连接测试失败: {e}"

    async def test_fotmob_collector_initialization(self) -> bool:
        """测试 FotMob 采集器初始化"""
        try:
            logger.info("🔍 测试 FotMob 采集器初始化...")

            from collectors.fotmob_api_collector import FotMobAPICollector

            # 创建采集器实例
            collector = FotMobAPICollector(
                max_concurrent=2,
                timeout=30,
                max_retries=3,
                base_delay=1.0,
                enable_proxy=False,
                enable_jitter=True
            )

            # 初始化
            await collector.initialize()

            # 清理资源
            await collector.close()

            logger.info("✅ FotMob 采集器初始化成功")
            return True, "FotMob 采集器初始化和清理成功"

        except Exception as e:
            return False, f"FotMob 采集器初始化失败: {e}"

    async def run_all_tests(self) -> bool:
        """运行所有完整性测试"""
        logger.info("🚀 开始系统完整性测试")
        logger.info("=" * 60)

        # 测试列表
        tests = [
            ("配置文件存在性", self.test_config_file_existence),
            ("数据库连接性", self.test_database_connectivity),
            ("SQLAlchemy text() 语法", self.test_sqlalchemy_text_syntax),
            ("FotMob 采集器初始化", self.test_fotmob_collector_initialization),
            ("回填脚本初始化", self.test_backfill_script_initialization),
            ("回填脚本配置加载", self.test_config_loading_in_backfill),
        ]

        # 执行测试
        for test_name, test_func in tests:
            try:
                passed, message = await test_func()
                self.results.add_test(test_name, passed, message if not passed else None)

                if passed:
                    logger.info(f"✅ {test_name}: 通过")
                else:
                    logger.error(f"❌ {test_name}: 失败 - {message}")

            except Exception as e:
                logger.error(f"❌ {test_name}: 异常 - {e}")
                self.results.add_test(test_name, False, f"测试异常: {e}")

        # 打印详细结果
        self.results.print_detailed_results()
        logger.info(self.results.get_summary())

        # 返回总体结果
        return self.results.failed_tests == 0

async def main():
    """主函数"""
    print("🔧 系统完整性修复验证")
    print("=" * 60)

    tester = SystemIntegrityTester()

    try:
        success = await tester.run_all_tests()

        if success:
            print("\n🎉 所有 Blocking Errors 已修复！系统完整性验证通过！")
            print("✅ 可以安全启动大规模回填任务")
            return 0
        else:
            print("\n❌ 仍有错误需要修复")
            print("🚨 请解决上述问题后再启动大规模回填")
            return 1

    except Exception as e:
        logger.error(f"❌ 完整性测试异常: {e}")
        print(f"\n❌ 测试过程中发生异常: {e}")
        return 1

if __name__ == "__main__":
    # 🔧 修复: 使用 asyncio.run() 来处理顶层 await
    sys.exit(asyncio.run(main()))