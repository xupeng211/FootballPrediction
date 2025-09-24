#!/usr/bin/env python3
"""
简化的集成测试环境检查脚本
用于Phase 4集成测试的基础环境验证
"""

import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleIntegrationChecker:
    """简化的集成测试环境检查器"""

    def __init__(self):
        self.services_status = {}
        self.start_time = time.time()

    def check_python_dependencies(self) -> bool:
        """检查Python依赖"""
        try:
            required_packages = [
                "fastapi",
                "sqlalchemy",
                "psycopg2",
                "redis",
                "pytest",
                "pytest-asyncio",
                "pytest-cov",
            ]

            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package.replace("-", "_"))
                except ImportError:
                    missing_packages.append(package)

            if missing_packages:
                self.services_status["python_deps"] = {
                    "status": "unhealthy",
                    "error": f"Missing packages: {missing_packages}",
                    "response_time": time.time() - self.start_time,
                }
                logger.error(f"❌ Missing Python dependencies: {missing_packages}")
                return False
            else:
                self.services_status["python_deps"] = {
                    "status": "healthy",
                    "response_time": time.time() - self.start_time,
                    "details": f"All {len(required_packages)} required packages available",
                }
                logger.info("✅ Python dependencies check successful")
                return True

        except Exception as e:
            self.services_status["python_deps"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Python dependencies check failed: {e}")
            return False

    def check_test_files_exist(self) -> bool:
        """检查测试文件是否存在"""
        try:
            required_test_files = [
                "tests/unit/api/test_data_phase3.py",
                "tests/unit/api/test_features_improved_phase3.py",
                "tests/unit/features/test_feature_store_external.py",
                "tests/unit/data/test_streaming_collector_external.py",
            ]

            missing_files = []
            for test_file in required_test_files:
                file_path = Path(test_file)
                if not file_path.exists():
                    missing_files.append(test_file)

            if missing_files:
                self.services_status["test_files"] = {
                    "status": "unhealthy",
                    "error": f"Missing test files: {missing_files}",
                    "response_time": time.time() - self.start_time,
                }
                logger.error(f"❌ Missing test files: {missing_files}")
                return False
            else:
                self.services_status["test_files"] = {
                    "status": "healthy",
                    "response_time": time.time() - self.start_time,
                    "details": f"All {len(required_test_files)} test files exist",
                }
                logger.info("✅ Test files check successful")
                return True

        except Exception as e:
            self.services_status["test_files"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Test files check failed: {e}")
            return False

    def check_config_files_exist(self) -> bool:
        """检查配置文件是否存在"""
        try:
            required_config_files = [
                "docker-compose.yml",
                "feature_store.yaml",
                "pytest.ini",
            ]

            missing_files = []
            for config_file in required_config_files:
                file_path = Path(config_file)
                if not file_path.exists():
                    missing_files.append(config_file)

            if missing_files:
                self.services_status["config_files"] = {
                    "status": "unhealthy",
                    "error": f"Missing config files: {missing_files}",
                    "response_time": time.time() - self.start_time,
                }
                logger.error(f"❌ Missing config files: {missing_files}")
                return False
            else:
                self.services_status["config_files"] = {
                    "status": "healthy",
                    "response_time": time.time() - self.start_time,
                    "details": f"All {len(required_config_files)} config files exist",
                }
                logger.info("✅ Config files check successful")
                return True

        except Exception as e:
            self.services_status["config_files"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Config files check failed: {e}")
            return False

    def check_project_structure(self) -> bool:
        """检查项目结构"""
        try:
            required_dirs = [
                "src/api",
                "src/database",
                "src/models",
                "src/features",
                "src/monitoring",
                "tests/unit",
                "tests/integration",
                "scripts",
            ]

            missing_dirs = []
            for dir_path in required_dirs:
                path = Path(dir_path)
                if not path.exists() or not path.is_dir():
                    missing_dirs.append(dir_path)

            if missing_dirs:
                self.services_status["project_structure"] = {
                    "status": "unhealthy",
                    "error": f"Missing directories: {missing_dirs}",
                    "response_time": time.time() - self.start_time,
                }
                logger.error(f"❌ Missing directories: {missing_dirs}")
                return False
            else:
                self.services_status["project_structure"] = {
                    "status": "healthy",
                    "response_time": time.time() - self.start_time,
                    "details": f"All {len(required_dirs)} required directories exist",
                }
                logger.info("✅ Project structure check successful")
                return True

        except Exception as e:
            self.services_status["project_structure"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Project structure check failed: {e}")
            return False

    def run_basic_checks(self) -> Dict[str, bool]:
        """运行基础检查"""
        logger.info("🚀 Starting basic integration test environment checks...")

        checks = {
            "python_deps": self.check_python_dependencies(),
            "test_files": self.check_test_files_exist(),
            "config_files": self.check_config_files_exist(),
            "project_structure": self.check_project_structure(),
        }

        return checks

    def print_status_report(self):
        """打印状态报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 Basic Integration Test Environment Status")
        logger.info("=" * 60)

        for service, status_info in self.services_status.items():
            status = status_info.get("status", "unknown")
            response_time = status_info.get("response_time", 0)

            if status == "healthy":
                details = status_info.get("details", "")
                logger.info(
                    f"✅ {service.replace('_', ' ').title():<20}: Healthy ({response_time:.2f}s) - {details}"
                )
            else:
                error = status_info.get("error", "Unknown error")
                logger.error(
                    f"❌ {service.replace('_', ' ').title():<20}: Unhealthy - {error}"
                )

        # 计算健康服务数量
        healthy_count = sum(
            1
            for info in self.services_status.values()
            if info.get("status") == "healthy"
        )
        total_count = len(self.services_status)

        logger.info(
            f"\n📈 Basic Environment Health: {healthy_count}/{total_count} components healthy"
        )

        if healthy_count == total_count:
            logger.info("🎉 All basic components are ready!")
        elif healthy_count >= total_count * 0.75:  # 75%以上组件健康
            logger.info("⚠️  Most basic components are ready")
        else:
            logger.error("🚨 Critical basic component issues detected")

    def is_ready_for_integration_tests(self) -> bool:
        """检查是否准备好进行基础集成测试"""
        healthy_count = sum(
            1
            for info in self.services_status.values()
            if info.get("status") == "healthy"
        )
        total_count = len(self.services_status)

        return healthy_count >= total_count * 0.8  # 80%以上组件健康


def main():
    """主函数"""
    checker = SimpleIntegrationChecker()

    # 运行基础检查
    checks = checker.run_basic_checks()

    # 打印状态报告
    checker.print_status_report()

    # 检查是否准备好进行集成测试
    if checker.is_ready_for_integration_tests():
        logger.info("✅ Basic environment is ready for integration tests")
        logger.info(
            "📝 Note: External services (PostgreSQL, Redis, Kafka) require Docker environment"
        )
        return 0
    else:
        logger.error("❌ Basic environment is not ready for integration tests")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Integration test check interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
