#!/usr/bin/env python3
"""
Phase F: 集成测试环境设置工具
Phase F Integration Test Environment Setup Tool

这是Phase F企业级集成阶段的环境配置工具，包括：
- 集成测试环境验证
- 依赖检查和安装
- 测试数据库初始化
- 外部服务模拟配置

基于Issue #149的成功经验，提供完整的集成测试环境支持。
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 模块可用性检查 - Phase E验证的成功策略
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    pytest = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

try:
    import sqlalchemy
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    sqlalchemy = None


class PhaseFIntegrationSetup:
    """Phase F集成测试环境设置器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests" / "integration"
        self.setup_log = []
        self.start_time = datetime.now()

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.setup_log.append(log_entry)
        print(log_entry)

    def check_python_version(self) -> bool:
        """检查Python版本"""
        self.log("检查Python版本...")
        version = sys.version_info
        if version >= (3, 8):
            self.log(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            self.log(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro} (需要3.8+)", "ERROR")
            return False

    def check_required_dependencies(self) -> Dict[str, bool]:
        """检查必需依赖"""
        self.log("检查必需依赖...")
        dependencies = {
            "pytest": PYTEST_AVAILABLE,
            "requests": REQUESTS_AVAILABLE,
            "asyncpg": ASYNCPG_AVAILABLE,
            "aiohttp": AIOHTTP_AVAILABLE,
            "httpx": HTTPX_AVAILABLE,
            "sqlalchemy": SQLALCHEMY_AVAILABLE
        }

        for dep, available in dependencies.items():
            status = "✅" if available else "❌"
            self.log(f"  {status} {dep}")

        missing_deps = [dep for dep, available in dependencies.items() if not available]
        if missing_deps:
            self.log(f"❌ 缺失依赖: {', '.join(missing_deps)}", "ERROR")
            return dependencies
        else:
            self.log("✅ 所有必需依赖已安装")
            return dependencies

    def install_missing_dependencies(self, dependencies: Dict[str, bool]) -> bool:
        """安装缺失的依赖"""
        missing_deps = [dep for dep, available in dependencies.items() if not available]

        if not missing_deps:
            return True

        self.log(f"安装缺失依赖: {', '.join(missing_deps)}...")

        try:
            # 创建临时requirements文件
            temp_req_file = self.project_root / "temp_phase_f_requirements.txt"
            with open(temp_req_file, 'w') as f:
                for dep in missing_deps:
                    f.write(f"{dep}\n")

            # 安装依赖
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(temp_req_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # 清理临时文件
            temp_req_file.unlink(missing_ok=True)

            if result.returncode == 0:
                self.log("✅ 依赖安装成功")
                return True
            else:
                self.log(f"❌ 依赖安装失败: {result.stderr}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log("❌ 依赖安装超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ 依赖安装异常: {e}", "ERROR")
            return False

    def verify_test_structure(self) -> bool:
        """验证测试结构"""
        self.log("验证测试文件结构...")

        required_files = [
            "tests/integration/api_comprehensive.py",
            "tests/integration/database_advanced.py",
            "tests/integration/external_services.py"
        ]

        structure_valid = True
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.log(f"  ✅ {file_path}")
            else:
                self.log(f"  ❌ {file_path} (文件不存在)", "ERROR")
                structure_valid = False

        return structure_valid

    def setup_test_database(self) -> bool:
        """设置测试数据库"""
        self.log("设置测试数据库...")

        if not SQLALCHEMY_AVAILABLE:
            self.log("⚠️ SQLAlchemy不可用，跳过数据库设置")
            return True

        try:
            # 使用SQLite内存数据库进行测试
            from sqlalchemy import create_engine, text
            from sqlalchemy.ext.declarative import declarative_base
            from sqlalchemy import Column, Integer, String, DateTime

            Base = declarative_base()

            # 创建测试表
            class TestTeam(Base):
                __tablename__ = "test_teams"
                id = Column(Integer, primary_key=True)
                name = Column(String(100), nullable=False)
                league = Column(String(100))

            class TestMatch(Base):
                __tablename__ = "test_matches"
                id = Column(Integer, primary_key=True)
                home_team_id = Column(Integer)
                away_team_id = Column(Integer)
                match_date = Column(DateTime)

            # 创建内存数据库引擎
            engine = create_engine("sqlite:///:memory:", echo=False)
            Base.metadata.create_all(engine)

            # 测试数据库连接
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1

            self.log("✅ 测试数据库设置成功")
            return True

        except Exception as e:
            self.log(f"❌ 测试数据库设置失败: {e}", "ERROR")
            return False

    def check_external_services(self) -> Dict[str, bool]:
        """检查外部服务可用性"""
        self.log("检查外部服务可用性...")

        services = {
            "github_api": self._check_github_api(),
            "internet_connection": self._check_internet_connection(),
            "docker_services": self._check_docker_services()
        }

        for service, available in services.items():
            status = "✅" if available else "❌"
            self.log(f"  {status} {service}")

        return services

    def _check_github_api(self) -> bool:
        """检查GitHub API可用性"""
        if not REQUESTS_AVAILABLE:
            return False

        try:
            response = requests.get("https://api.github.com/", timeout=5)
            return response.status_code == 200
        except:
            return False

    def _check_internet_connection(self) -> bool:
        """检查网络连接"""
        if not REQUESTS_AVAILABLE:
            return False

        try:
            response = requests.get("https://httpbin.org/get", timeout=5)
            return response.status_code == 200
        except:
            return False

    def _check_docker_services(self) -> bool:
        """检查Docker服务"""
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def run_integration_tests(self) -> Dict[str, Any]:
        """运行集成测试"""
        self.log("运行集成测试...")

        if not PYTEST_AVAILABLE:
            self.log("❌ pytest不可用，无法运行测试", "ERROR")
            return {"status": "failed", "reason": "pytest不可用"}

        # 构建pytest命令
        test_dir = self.test_dir
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            "-v",
            "--tb=short",
            "--durations=10"
        ]

        try:
            self.log(f"执行命令: {' '.join(cmd)}")
            start_time = time.time()

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            end_time = time.time()
            duration = end_time - start_time

            # 解析测试结果
            output_lines = result.stdout.split('\n')
            summary_line = next((line for line in output_lines if '=' in line and 'passed' in line or 'failed' in line), "")

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "summary": summary_line
            }

        except subprocess.TimeoutExpired:
            self.log("❌ 测试执行超时", "ERROR")
            return {"status": "failed", "reason": "测试执行超时"}
        except Exception as e:
            self.log(f"❌ 测试执行异常: {e}", "ERROR")
            return {"status": "failed", "reason": str(e)}

    def generate_setup_report(self) -> str:
        """生成设置报告"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        report = f"""# Phase F: 集成测试环境设置报告

**设置时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
**完成时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
**总耗时**: {total_duration:.2f}秒

## 📋 设置日志

"""
        for log_entry in self.setup_log:
            report += f"{log_entry}\n"

        return report

    def run_complete_setup(self) -> bool:
        """运行完整设置流程"""
        self.log("🚀 开始Phase F集成测试环境设置...")
        self.log("📋 基于Issue #149最佳实践进行环境配置")

        # 1. 检查Python版本
        if not self.check_python_version():
            return False

        # 2. 检查依赖
        dependencies = self.check_required_dependencies()
        missing_deps = [dep for dep, available in dependencies.items() if not available]

        if missing_deps:
            if not self.install_missing_dependencies(dependencies):
                return False

        # 3. 验证测试结构
        if not self.verify_test_structure():
            return False

        # 4. 设置测试数据库
        if not self.setup_test_database():
            return False

        # 5. 检查外部服务
        self.check_external_services()

        # 6. 生成设置报告
        report = self.generate_setup_report()
        report_file = self.project_root / "phase_f_setup_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.log(f"📄 设置报告已生成: {report_file}")
        self.log("🎉 Phase F集成测试环境设置完成！")

        return True

    def setup_ci_environment(self) -> bool:
        """设置CI环境"""
        self.log("🔧 设置CI/CD环境...")

        # 创建CI配置文件
        ci_config = {
            "phase_f_integration_tests": {
                "enabled": True,
                "timeout": 300,
                "retry_attempts": 2,
                "required_coverage": {
                    "api": 60,
                    "database": 70,
                    "external_services": 80
                }
            }
        }

        config_file = self.project_root / "config" / "phase_f_ci.json"
        config_file.parent.mkdir(exist_ok=True)

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(ci_config, f, indent=2, ensure_ascii=False)

        self.log(f"✅ CI配置已生成: {config_file}")
        return True


def main():
    """主函数"""
    print("🚀 Phase F: 集成测试环境设置工具")
    print("=" * 50)

    import argparse
    parser = argparse.ArgumentParser(description="Phase F集成测试环境设置")
    parser.add_argument("--check-only", action="store_true", help="仅检查环境，不执行设置")
    parser.add_argument("--run-tests", action="store_true", help="运行集成测试")
    parser.add_argument("--setup-ci", action="store_true", help="设置CI环境")
    parser.add_argument("--report", action="store_true", help="生成设置报告")

    args = parser.parse_args()

    setup = PhaseFIntegrationSetup()

    if args.check_only:
        setup.check_python_version()
        setup.check_required_dependencies()
        setup.verify_test_structure()
        setup.check_external_services()
        return

    if args.setup_ci:
        setup.setup_ci_environment()
        return

    if args.run_tests:
        test_result = setup.run_integration_tests()
        print("\n📊 测试结果:")
        print(f"状态: {test_result['status']}")
        print(f"耗时: {test_result.get('duration', 0):.2f}秒")
        if 'summary' in test_result:
            print(f"摘要: {test_result['summary']}")
        return

    if args.report:
        report = setup.generate_setup_report()
        print("\n📄 设置报告:")
        print(report)
        return

    # 默认执行完整设置
    success = setup.run_complete_setup()

    if success:
        print("\n✅ Phase F环境设置成功！")
        print("💡 下一步建议:")
        print("  1. 运行: python3 scripts/phase_f_integration_setup.py --run-tests")
        print("  2. 查看报告: cat phase_f_setup_report.md")
        print("  3. 设置CI: python3 scripts/phase_f_integration_setup.py --setup-ci")
    else:
        print("\n❌ Phase F环境设置失败！")
        print("💡 建议检查:")
        print("  1. Python版本 >= 3.8")
        print("  2. 网络连接正常")
        print("  3. 依赖安装权限")
        sys.exit(1)


if __name__ == "__main__":
    main()