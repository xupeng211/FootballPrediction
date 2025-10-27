#!/usr/bin/env python3
"""
开发者CLI工具集
Developer CLI Toolkit

基于Issue #98方法论，提供统一的开发工具界面
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DevCLI:
    """开发者CLI工具集 - 基于Issue #98方法论"""

    def __init__(self):
        self.project_root = project_root
        self.commands = {
            "quality": self.run_quality_check,
            "fix": self.run_auto_fix,
            "review": self.run_code_review,
            "test": self.run_tests,
            "coverage": self.run_coverage,
            "monitor": self.run_monitoring,
            "report": self.generate_report,
            "setup": self.setup_development,
            "status": self.check_status,
            "improve": self.run_improvement_cycle
        }

    def run_quality_check(self, args):
        """运行质量检查"""
        print("🔍 运行代码质量检查...")

        # 运行质量守护工具
        cmd = [sys.executable, "scripts/quality_guardian.py", "--check-only"]
        if args.verbose:
            cmd.append("--verbose")

        self._run_command(cmd, "质量检查")

    def run_auto_fix(self, args):
        """运行自动修复"""
        print("🔧 运行智能自动修复...")

        cmd = [sys.executable, "scripts/smart_quality_fixer.py"]
        if args.syntax_only:
            cmd.append("--syntax-only")
        if args.dry_run:
            cmd.append("--dry-run")

        self._run_command(cmd, "自动修复")

    def run_code_review(self, args):
        """运行代码审查"""
        print("🔍 运行AI代码审查...")

        cmd = [sys.executable, "scripts/automated_code_reviewer.py"]
        if args.format:
            cmd.extend(["--output-format", args.format])
        if args.severity:
            cmd.extend(["--severity-filter", args.severity])

        self._run_command(cmd, "代码审查")

    def run_tests(self, args):
        """运行测试"""
        print("🧪 运行测试...")

        if args.quick:
            # 快速测试
            cmd = ["python", "-m", "pytest", "tests/unit/utils/", "-v", "--tb=short"]
        elif args.integration:
            # 集成测试
            cmd = ["python", "-m", "pytest", "tests/integration/", "-v", "--tb=short"]
        elif args.module:
            # 特定模块测试
            cmd = ["python", "-m", "pytest", f"tests/{args.module}/", "-v", "--tb=short"]
        else:
            # 完整测试
            cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

        if args.coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])

        self._run_command(cmd, "测试")

    def run_coverage(self, args):
        """运行覆盖率分析"""
        print("📊 运行测试覆盖率分析...")

        if args.target:
            # 目标模块覆盖率
            cmd = ["make", "coverage-targeted", f"MODULE={args.target}"]
        elif args.report:
            # 生成覆盖率报告
            cmd = ["make", "coverage"]
        else:
            # 快速覆盖率检查
            cmd = ["python", "-m", "pytest", "tests/unit/utils/",
                   "--cov=src/utils", "--cov-report=term-missing"]

        self._run_command(cmd, "覆盖率分析")

    def run_monitoring(self, args):
        """运行监控"""
        print("📊 启动监控系统...")

        if args.continuous:
            # 持续改进引擎
            cmd = [sys.executable, "scripts/continuous_improvement_engine.py",
                   "--automated", "--interval", str(args.interval or 30)]
        else:
            # 改进监控
            cmd = [sys.executable, "scripts/improvement_monitor.py"]

        self._run_command(cmd, "监控")

    def generate_report(self, args):
        """生成报告"""
        print("📋 生成开发报告...")

        if args.quality:
            # 质量报告
            cmd = [sys.executable, "scripts/quality_guardian.py", "--report-only"]
        elif args.improvement:
            # 改进报告
            cmd = [sys.executable, "scripts/continuous_improvement_engine.py", "--history"]
        else:
            # 综合报告
            self._generate_comprehensive_report()
            return

        self._run_command(cmd, "报告生成")

    def setup_development(self, args):
        """设置开发环境"""
        print("⚙️ 设置开发环境...")

        if args.full:
            # 完整环境设置
            commands = [
                ["make", "install"],
                ["make", "up"],
                ["make", "env-check"],
                ["make", "test-quick"]
            ]

            for cmd in commands:
                self._run_command(cmd, f"环境设置: {' '.join(cmd)}")
        else:
            # 基础环境检查
            self._run_command(["make", "env-check"], "环境检查")

    def check_status(self, args):
        """检查项目状态"""
        print("📊 检查项目状态...")

        # 检查Docker状态
        print("\n🐳 Docker服务状态:")
        self._run_command(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                        "Docker状态", check=False)

        # 检查环境变量
        print("\n🔧 环境状态:")
        self._run_command(["make", "env-check"], "环境检查")

        # 检查测试状态
        print("\n🧪 测试状态:")
        self._run_command(["make", "test-env-status"], "测试环境状态")

        # 检查质量状态
        print("\n📈 质量状态:")
        if (self.project_root / "smart_quality_fix_report.json").exists():
            print("✅ 质量报告存在")
        else:
            print("❌ 质量报告不存在，建议运行质量检查")

        if (self.project_root / "automated_code_review_report.json").exists():
            print("✅ 代码审查报告存在")
        else:
            print("❌ 代码审查报告不存在，建议运行代码审查")

    def run_improvement_cycle(self, args):
        """运行改进周期"""
        print("🚀 运行完整改进周期...")

        # 基于Issue #98方法论的改进周期
        cycle_steps = [
            ("1️⃣ 质量检查", ["python3", "scripts/quality_guardian.py", "--check-only"]),
            ("2️⃣ 智能修复", ["python3", "scripts/smart_quality_fixer.py"]),
            ("3️⃣ 代码审查", ["python3", "scripts/automated_code_reviewer.py"]),
            ("4️⃣ 测试验证", ["python", "-m", "pytest", "tests/unit/utils/", "-x", "--maxfail=10"]),
            ("5️⃣ 覆盖率检查", ["python", "-m", "pytest", "tests/unit/utils/",
                               "--cov=src/utils", "--cov-report=term-missing"]),
            ("6️⃣ 报告生成", ["python3", "scripts/improvement_monitor.py"])
        ]

        print("🔄 开始Issue #98智能改进周期...")

        for step_name, cmd in cycle_steps:
            print(f"\n{step_name}")
            print("-" * 40)

            if not self._run_command(cmd, step_name, check=True):
                print(f"⚠️ {step_name} 失败，但继续执行下一步...")
            else:
                print(f"✅ {step_name} 完成")

        print("\n🎉 改进周期完成！")
        print("📊 建议查看生成的报告了解改进效果")

    def _run_command(self, cmd: List[str], description: str, check: bool = True) -> bool:
        """运行命令"""
        try:
            print(f"🔧 执行: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                check=check,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ {description} 成功")
                return True
            else:
                print(f"❌ {description} 失败 (退出码: {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            print(f"⏰ {description} 超时")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} 执行失败: {e}")
            return False
        except Exception as e:
            print(f"❌ {description} 异常: {e}")
            return False

    def _generate_comprehensive_report(self):
        """生成综合报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_status": {},
            "quality_metrics": {},
            "recommendations": [],
            "issue_98_methodology_applied": True
        }

        # 收集各种报告数据
        reports_to_collect = [
            ("quality", "smart_quality_fix_report.json"),
            ("review", "automated_code_review_report.json"),
            ("improvement", "improvement_report.json")
        ]

        for report_type, filename in reports_to_collect:
            report_path = self.project_root / filename
            if report_path.exists():
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        report[f"{report_type}_data"] = data
                except Exception as e:
                    logger.error(f"读取报告失败 {filename}: {e}")

        # 保存综合报告
        report_file = self.project_root / "comprehensive_dev_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"📋 综合报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"保存综合报告失败: {e}")

    def create_parser(self) -> argparse.ArgumentParser:
        """创建命令行解析器"""
        parser = argparse.ArgumentParser(
            description="开发者CLI工具集 - 基于Issue #98方法论",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例用法:
  %(prog)s quality                    # 运行质量检查
  %(prog)s fix --syntax-only          # 仅修复语法错误
  %(prog)s review --format json       # JSON格式代码审查
  %(prog)s test --coverage            # 运行带覆盖率的测试
  %(prog)s improve                    # 运行完整改进周期
  %(prog)s status                     # 检查项目状态
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='可用命令')

        # 质量检查命令
        quality_parser = subparsers.add_parser('quality', help='运行代码质量检查')
        quality_parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

        # 自动修复命令
        fix_parser = subparsers.add_parser('fix', help='运行智能自动修复')
        fix_parser.add_argument('--syntax-only', action='store_true', help='仅修复语法错误')
        fix_parser.add_argument('--dry-run', action='store_true', help='试运行模式')

        # 代码审查命令
        review_parser = subparsers.add_parser('review', help='运行AI代码审查')
        review_parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
        review_parser.add_argument('--severity', help='过滤问题严重程度')

        # 测试命令
        test_parser = subparsers.add_parser('test', help='运行测试')
        test_group = test_parser.add_mutually_exclusive_group()
        test_group.add_argument('--quick', action='store_true', help='快速测试')
        test_group.add_argument('--integration', action='store_true', help='集成测试')
        test_group.add_argument('--module', help='测试特定模块')
        test_parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')

        # 覆盖率命令
        coverage_parser = subparsers.add_parser('coverage', help='运行覆盖率分析')
        coverage_group = coverage_parser.add_mutually_exclusive_group()
        coverage_group.add_argument('--target', help='目标模块覆盖率')
        coverage_group.add_argument('--report', action='store_true', help='生成完整报告')

        # 监控命令
        monitor_parser = subparsers.add_parser('monitor', help='启动监控系统')
        monitor_parser.add_argument('--continuous', action='store_true', help='持续监控')
        monitor_parser.add_argument('--interval', type=int, help='监控间隔(秒)')

        # 报告命令
        report_parser = subparsers.add_parser('report', help='生成报告')
        report_group = report_parser.add_mutually_exclusive_group()
        report_group.add_argument('--quality', action='store_true', help='质量报告')
        report_group.add_argument('--improvement', action='store_true', help='改进报告')

        # 设置命令
        setup_parser = subparsers.add_parser('setup', help='设置开发环境')
        setup_parser.add_argument('--full', action='store_true', help='完整环境设置')

        # 状态命令
        status_parser = subparsers.add_parser('status', help='检查项目状态')

        # 改进命令
        improve_parser = subparsers.add_parser('improve', help='运行改进周期')

        return parser

    def run(self):
        """运行CLI"""
        parser = self.create_parser()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return

        if args.command in self.commands:
            try:
                self.commands[args.command](args)
            except KeyboardInterrupt:
                print("\n👋 用户中断操作")
                sys.exit(130)
            except Exception as e:
                logger.error(f"命令执行失败: {e}")
                sys.exit(1)
        else:
            print(f"❌ 未知命令: {args.command}")
            parser.print_help()
            sys.exit(1)


def main():
    """主函数"""
    print("🚀 开发者CLI工具集")
    print("基于Issue #98智能质量修复方法论")
    print("=" * 50)

    cli = DevCLI()
    cli.run()


if __name__ == "__main__":
    main()