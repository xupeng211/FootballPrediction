#!/usr/bin/env python3
"""
V41.51: 数据库身份验证脚本
===========================

验证系统连接到正确的数据库实例 (football_db)，并检查核心表是否存在。
确保 Docker 环境和 WSL2 本地环境看到的是同一个真实数据库。

Usage:
    python scripts/ops/v41_51_db_identity_check.py
    python scripts/ops/v41_51_db_identity_check.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseIdentityChecker:
    """V41.51: 数据库身份验证器"""

    # V41.51: 单数据库准则
    REQUIRED_DB_NAME = "football_db"

    # 核心表列表（这些表必须存在）
    REQUIRED_TABLES = {
        "matches",
        "matches_mapping",
        "metrics_multi_source_data",
    }

    def __init__(self, verbose: bool = False):
        """
        初始化验证器

        Args:
            verbose: 是否显示详细信息
        """
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def check(self, name: str, status: str, message: str):
        """
        记录检查结果

        Args:
            name: 检查项名称
            status: 状态 (pass/warn/fail)
            message: 详细信息
        """
        self.results.append((name, status, message))

        if status == "pass":
            self.passed += 1
            icon = "✅"
        elif status == "warn":
            self.warnings += 1
            icon = "⚠️"
        else:  # fail
            self.failed += 1
            icon = "❌"

        logger.info(f"{icon} {name}: {message}")

        if self.verbose and status != "pass":
            logger.info(f"   详情: {message}")

    def run_checks(self) -> int:
        """
        运行所有检查

        Returns:
            0 如果所有检查通过，否则返回 1
        """
        logger.info("🚀 V41.51 数据库身份验证开始")
        logger.info("=" * 60)

        # 1. 配置文件检查
        self._check_config()

        # 2. 数据库连接检查
        conn = self._check_connection()
        if conn is None:
            self._print_summary()
            return 1

        try:
            # 3. 数据库身份检查
            self._check_database_identity(conn)

            # 4. 核心表检查
            self._check_required_tables(conn)

            # 5. 数据统计
            self._check_data_statistics(conn)

        finally:
            conn.close()

        self._print_summary()
        return 0 if self.failed == 0 else 1

    def _check_config(self):
        """检查配置文件"""
        try:
            settings = get_settings()
            db_name = settings.database.name

            if db_name == self.REQUIRED_DB_NAME:
                self.check(
                    "配置文件检查",
                    "pass",
                    f"DB_NAME={db_name}"
                )
            else:
                self.check(
                    "配置文件检查",
                    "fail",
                    f"期望 DB_NAME={self.REQUIRED_DB_NAME}, 实际 {db_name}"
                )
        except Exception as e:
            self.check("配置文件检查", "fail", str(e))

    def _check_connection(self):
        """检查数据库连接"""
        try:
            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor
            )
            self.check(
                "数据库连接",
                "pass",
                f"{settings.database.host}:{settings.database.port}/{settings.database.name}"
            )
            return conn
        except Exception as e:
            self.check("数据库连接", "fail", str(e))
            return None

    def _check_database_identity(self, conn):
        """检查数据库身份"""
        try:
            with conn.cursor() as cursor:
                # 获取当前数据库名称
                cursor.execute("SELECT current_database();")
                current_db = cursor.fetchone()["current_database"]

                if current_db == self.REQUIRED_DB_NAME:
                    self.check(
                        "数据库身份",
                        "pass",
                        f"已连接到 {current_db}"
                    )
                else:
                    self.check(
                        "数据库身份",
                        "fail",
                        f"期望 {self.REQUIRED_DB_NAME}, 实际 {current_db}"
                    )
        except Exception as e:
            self.check("数据库身份", "fail", str(e))

    def _check_required_tables(self, conn):
        """检查核心表是否存在"""
        try:
            with conn.cursor() as cursor:
                # 查询所有表
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                existing_tables = {row["table_name"] for row in cursor.fetchall()}

                # 检查每个核心表
                for table in self.REQUIRED_TABLES:
                    if table in existing_tables:
                        self.check(f"表 {table}", "pass", "存在")
                    else:
                        self.check(f"表 {table}", "fail", "缺失")

                # 统计信息
                total_tables = len(existing_tables)
                self.check(
                    "表总数",
                    "pass" if total_tables >= 15 else "warn",
                    f"{total_tables} 个表"
                )
        except Exception as e:
            self.check("核心表检查", "fail", str(e))

    def _check_data_statistics(self, conn):
        """检查数据统计"""
        try:
            with conn.cursor() as cursor:
                # 检查 matches 表记录数
                cursor.execute("SELECT COUNT(*) as count FROM matches;")
                matches_count = cursor.fetchone()["count"]

                if matches_count >= 9000:
                    self.check("matches 表数据", "pass", f"{matches_count} 场比赛")
                elif matches_count >= 1000:
                    self.check("matches 表数据", "warn", f"{matches_count} 场比赛 (期望 >9000)")
                else:
                    self.check("matches 表数据", "warn", f"{matches_count} 场比赛")

                # 检查 metrics_multi_source_data 表记录数
                cursor.execute("SELECT COUNT(*) as count FROM metrics_multi_source_data;")
                metrics_count = cursor.fetchone()["count"]

                self.check(
                    "metrics_multi_source_data 表",
                    "pass" if metrics_count > 0 else "warn",
                    f"{metrics_count} 条记录"
                )
        except Exception as e:
            self.check("数据统计", "warn", f"无法获取统计: {e}")

    def _print_summary(self):
        """打印汇总信息"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 验证汇总:")
        logger.info(f"   通过: {self.passed}")
        logger.info(f"   警告: {self.warnings}")
        logger.info(f"   失败: {self.failed}")
        logger.info("=" * 60)

        if self.failed == 0 and self.warnings == 0:
            logger.info("")
            logger.info("🎉 V41.51 数据库大一统验证通过！")
            logger.info("   系统已正确配置为连接 football_db 数据库")
            logger.info("")
            logger.info("   您可以安全运行:")
            logger.info("   python main.py --action align-hashes --run-harvest")
        elif self.failed == 0:
            logger.info("")
            logger.info("⚠️ V41.51 验证通过，但存在警告")
            logger.warning("   请检查上述警告项")
        else:
            logger.info("")
            logger.error("❌ V41.51 验证失败")
            logger.error("   请解决上述问题后再运行数据采集")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="V41.51 数据库身份验证")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细信息"
    )
    args = parser.parse_args()

    checker = DatabaseIdentityChecker(verbose=args.verbose)
    exit_code = checker.run_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
