#!/usr/bin/env python3
"""
测试 Nightly 测试设置
验证所有组件是否正确配置
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NightlySetupTester:
    """Nightly 设置测试器"""

    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }

    def log(self, status: str, message: str):
        """记录测试结果"""
        self.results[status].append(message)
        icon = "✅" if status == "passed" else "❌" if status == "failed" else "⚠️"
        logger.info(f"{icon} {message}")

    async def test_file_structure(self):
        """测试文件结构"""
        logger.info("测试文件结构...")

        required_files = [
            ".github/workflows/nightly-tests.yml",
            "config/nightly_tests.json",
            "scripts/nightly_test_monitor.py",
            "scripts/schedule_nightly_tests.py",
            "scripts/run_e2e_tests.py",
            "scripts/load_staging_data.py",
            "docker-compose.test.yml",
            "docker-compose.staging.yml"
        ]

        for file_path in required_files:
            if Path(file_path).exists():
                self.log("passed", f"文件存在: {file_path}")
            else:
                self.log("failed", f"文件缺失: {file_path}")

    async def test_directories(self):
        """测试目录结构"""
        logger.info("测试目录结构...")

        required_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/e2e",
            "tests/performance",
            "reports",
            "logs"
        ]

        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists():
                self.log("passed", f"目录存在: {dir_path}")
            else:
                path.mkdir(parents=True, exist_ok=True)
                self.log("warnings", f"目录已创建: {dir_path}")

    async def test_config(self):
        """测试配置文件"""
        logger.info("测试配置文件...")

        config_path = Path("config/nightly_tests.json")
        if not config_path.exists():
            self.log("failed", "配置文件不存在")
            return

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # 检查必需的配置项
            required_keys = [
                "quality_gate",
                "notifications",
                "test_schedule",
                "test_types"
            ]

            for key in required_keys:
                if key in config:
                    self.log("passed", f"配置项存在: {key}")
                else:
                    self.log("failed", f"配置项缺失: {key}")

            # 检查质量门禁配置
            if "quality_gate" in config:
                qg = config["quality_gate"]
                if qg.get("min_success_rate", 0) > 0:
                    self.log("passed", f"成功率阈值: {qg['min_success_rate']}%")
                if qg.get("required_coverage", 0) > 0:
                    self.log("passed", f"覆盖率要求: {qg['required_coverage']}%")

        except json.JSONDecodeError as e:
            self.log("failed", f"配置文件JSON格式错误: {e}")
        except Exception as e:
            self.log("failed", f"读取配置文件失败: {e}")

    async def test_dependencies(self):
        """测试Python依赖"""
        logger.info("测试Python依赖...")

        required_packages = [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-html",
            "pytest-json-report",
            "aiohttp",
            "schedule"
        ]

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                self.log("passed", f"包已安装: {package}")
            except ImportError:
                self.log("failed", f"包未安装: {package}")

    async def test_docker(self):
        """测试Docker环境"""
        logger.info("测试Docker环境...")

        import subprocess

        try:
            # 检查Docker命令
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log("passed", f"Docker已安装: {result.stdout.strip()}")
            else:
                self.log("failed", "Docker未正确安装")
        except Exception as e:
            self.log("failed", f"Docker检查失败: {e}")

        try:
            # 检查Docker Compose
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log("passed", f"Docker Compose已安装: {result.stdout.strip()}")
            else:
                self.log("warnings", "Docker Compose未安装（可选）")
        except Exception:
            self.log("warnings", "Docker Compose未安装（可选）")

    async def test_environment_variables(self):
        """测试环境变量"""
        logger.info("测试环境变量...")

        # 检查可选但推荐的环境变量
        optional_vars = {
            "GITHUB_TOKEN": "GitHub通知",
            "SLACK_WEBHOOK_URL": "Slack通知",
            "SMTP_HOST": "邮件通知",
            "DATABASE_URL": "数据库连接"
        }

        for var, desc in optional_vars.items():
            if os.getenv(var):
                self.log("passed", f"环境变量已设置: {var} ({desc})")
            else:
                self.log("warnings", f"环境变量未设置: {var} ({desc})")

    async def test_scripts(self):
        """测试脚本可执行性"""
        logger.info("测试脚本...")

        scripts = [
            "scripts/nightly_test_monitor.py",
            "scripts/schedule_nightly_tests.py",
            "scripts/run_e2e_tests.py",
            "scripts/load_staging_data.py"
        ]

        for script in scripts:
            path = Path(script)
            if path.exists():
                if os.access(script, os.X_OK):
                    self.log("passed", f"脚本可执行: {script}")
                else:
                    # 尝试添加执行权限
                    os.chmod(script, 0o755)
                    self.log("warnings", f"已添加执行权限: {script}")
            else:
                self.log("failed", f"脚本不存在: {script}")

    async def test_makefile(self):
        """测试Makefile命令"""
        logger.info("测试Makefile命令...")

        import subprocess

        commands = [
            "nightly-test",
            "nightly-status",
            "nightly-report"
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    ["make", "-n", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.log("passed", f"Makefile命令存在: make {cmd}")
                else:
                    self.log("failed", f"Makefile命令无效: make {cmd}")
            except Exception as e:
                self.log("failed", f"测试Makefile命令失败: make {cmd} - {e}")

    async def run_quick_test(self):
        """运行快速测试验证"""
        logger.info("运行快速测试验证...")

        import subprocess

        # 运行单元测试的快速版本
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short", "--maxfail=1", "-x"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.log("passed", "快速单元测试通过")
            else:
                # 检查是否有测试文件
                test_files = list(Path("tests/unit").glob("**/*.py"))
                if test_files:
                    self.log("failed", f"快速测试失败 (找到{len(test_files)}个测试文件)")
                else:
                    self.log("warnings", "没有找到单元测试文件")
        except subprocess.TimeoutExpired:
            self.log("warnings", "测试超时（可能测试较多）")
        except Exception as e:
            self.log("failed", f"运行测试失败: {e}")

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📋 Nightly 测试设置验证报告")
        print("="*60)

        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["warnings"])
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        warnings = len(self.results["warnings"])

        print(f"\n📊 总体结果: {total} 项检查")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  警告: {warnings}")

        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\n📈 完成度: {success_rate:.1f}%")

        if self.results["failed"]:
            print("\n❌ 失败项:")
            for item in self.results["failed"]:
                print(f"  - {item}")

        if self.results["warnings"]:
            print("\n⚠️  警告项:")
            for item in self.results["warnings"]:
                print(f"  - {item}")

        if not self.results["failed"] and not self.results["warnings"]:
            print("\n🎉 所有检查都通过了！Nightly 测试已准备就绪。")
        elif not self.results["failed"]:
            print("\n✅ 基本设置完成，但有一些建议优化的地方。")
        else:
            print("\n⚠️  存在一些问题需要解决才能正常运行 Nightly 测试。")

        print("\n📚 下一步:")
        print("1. 如果有失败项，请先解决")
        print("2. 运行 'make nightly-test' 进行本地测试")
        print("3. 配置环境变量以启用通知功能")
        print("4. 查看 docs/nightly_tests_guide.md 获取详细指南")

        print("\n" + "="*60)

        # 保存报告
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "success_rate": success_rate,
            "details": self.results
        }

        report_path = Path("reports/nightly-setup-report.json")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📄 详细报告已保存到: {report_path}")

        return success_rate >= 80 and not self.results["failed"]

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始验证 Nightly 测试设置...")

        await self.test_file_structure()
        await self.test_directories()
        await self.test_config()
        await self.test_dependencies()
        await self.test_docker()
        await self.test_environment_variables()
        await self.test_scripts()
        await self.test_makefile()
        await self.run_quick_test()

        return self.generate_report()


async def main():
    """主函数"""
    tester = NightlySetupTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
