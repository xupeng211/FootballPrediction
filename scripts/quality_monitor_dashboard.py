#!/usr/bin/env python3
"""
质量监控仪表板
Quality Monitoring Dashboard

提供项目质量状况的实时监控和报告
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class QualityMonitorDashboard:
    """质量监控仪表板"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.report_file = self.project_root / "quality_status_report.json"
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "ruff_errors": 0,
            "test_coverage": 0.0,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "syntax_errors": 0,
            "status": "unknown"
        }

    def run_ruff_check(self) -> Dict[str, Any]:
        """运行Ruff代码检查"""
        print("🔍 运行Ruff代码检查...")
        try:
            result = subprocess.run(
                ["make", "lint"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # 统计错误数量
                error_lines = [line for line in result.stdout.split('\n')
                              if ':' in line and any(code in line for code in ['E', 'F', 'W'])]
                ruff_errors = len(error_lines)
            else:
                ruff_errors = 0

            return {
                "success": result.returncode == 0,
                "errors": ruff_errors,
                "output": result.stdout[-1000:] if result.stdout else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "errors": -1, "output": "Ruff检查超时"}
        except Exception as e:
            return {"success": False, "errors": -1, "output": str(e)}

    def run_test_coverage(self) -> Dict[str, Any]:
        """运行测试覆盖率检查"""
        print("📊 运行测试覆盖率检查...")
        try:
            # 运行基础测试获取覆盖率
            result = subprocess.run(
                [
                    "python", "-m", "pytest",
                    "tests/unit/utils/test_helpers.py",
                    "tests/unit/utils/test_validators.py",
                    "--cov=src.utils",
                    "--cov-report=json",
                    "--cov-report=term-missing",
                    "--tb=no",
                    "-q"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            # 读取覆盖率JSON报告
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                coverage_percent = coverage_data.get("totals", {}).get("percent_covered", 0.0)
            else:
                coverage_percent = 0.0

            # 解析测试结果
            output_lines = result.stdout.split('\n')
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            tests_skipped = 0

            for line in output_lines:
                if "passed" in line and "failed" in line:
                    parts = line.split()
                    for part in parts:
                        if "passed" in part:
                            tests_passed = int(part.split("passed")[0])
                        elif "failed" in part:
                            tests_failed = int(part.split("failed")[0])
                        elif "skipped" in part:
                            tests_skipped = int(part.split("skipped")[0])
                    tests_run = tests_passed + tests_failed + tests_skipped
                    break

            return {
                "success": result.returncode == 0,
                "coverage": coverage_percent,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "tests_skipped": tests_skipped,
                "output": result.stdout[-500:] if result.stdout else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "coverage": 0.0, "output": "测试超时"}
        except Exception as e:
            return {"success": False, "coverage": 0.0, "output": str(e)}

    def check_syntax_errors(self) -> Dict[str, Any]:
        """检查语法错误"""
        print("✅ 检查语法错误...")
        try:
            # 尝试导入关键模块检查语法
            test_modules = [
                "src.adapters.factory_simple",
                "src.utils.helpers",
                "src.utils.validators"
            ]

            syntax_errors = 0
            for module in test_modules:
                try:
                    result = subprocess.run(
                        [sys.executable, "-c", f"import {module}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        syntax_errors += 1
                except Exception:
                    syntax_errors += 1

            return {
                "success": syntax_errors == 0,
                "errors": syntax_errors
            }
        except Exception as e:
            return {"success": False, "errors": -1, "output": str(e)}

    def calculate_overall_status(self) -> str:
        """计算整体状态"""
        ruff_errors = self.metrics["ruff_errors"]
        coverage = self.metrics["test_coverage"]
        tests_failed = self.metrics["tests_failed"]
        syntax_errors = self.metrics["syntax_errors"]

        if syntax_errors > 0:
            return "critical"  # 语法错误
        elif tests_failed > 0:
            return "warning"   # 测试失败
        elif ruff_errors > 1000:
            return "warning"   # 大量代码质量问题
        elif coverage < 20:
            return "poor"      # 低覆盖率
        elif coverage < 50:
            return "fair"      # 中等覆盖率
        elif coverage < 80:
            return "good"      # 良好覆盖率
        else:
            return "excellent" # 优秀状态

    def generate_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        print("🚀 生成质量监控报告...")

        # 运行各项检查
        ruff_result = self.run_ruff_check()
        test_result = self.run_test_coverage()
        syntax_result = self.check_syntax_errors()

        # 更新指标
        self.metrics.update({
            "ruff_errors": ruff_result.get("errors", 0),
            "test_coverage": test_result.get("coverage", 0.0),
            "tests_run": test_result.get("tests_run", 0),
            "tests_passed": test_result.get("tests_passed", 0),
            "tests_failed": test_result.get("tests_failed", 0),
            "tests_skipped": test_result.get("tests_skipped", 0),
            "syntax_errors": syntax_result.get("errors", 0),
            "status": self.calculate_overall_status()
        })

        # 保存报告
        with open(self.report_file, 'w') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

        return self.metrics

    def display_dashboard(self):
        """显示质量监控仪表板"""
        print("\n" + "="*60)
        print("🎯 项目质量监控仪表板")
        print("="*60)
        print(f"📅 检查时间: {self.metrics['timestamp']}")
        print(f"🏆 整体状态: {self.metrics['status'].upper()}")
        print("-"*60)

        # 代码质量
        ruff_status = "✅" if self.metrics['ruff_errors'] < 100 else "⚠️" if self.metrics['ruff_errors'] < 1000 else "❌"
        print(f"📝 代码质量 (Ruff): {ruff_status} {self.metrics['ruff_errors']:,} 个问题")

        # 测试状态
        test_status = "✅" if self.metrics['tests_failed'] == 0 else "⚠️" if self.metrics['tests_failed'] < 10 else "❌"
        print(f"🧪 测试状态: {test_status} {self.metrics['tests_passed']:,} 通过 / {self.metrics['tests_failed']:,} 失败 / {self.metrics['tests_skipped']:,} 跳过")

        # 覆盖率
        coverage_icon = "🎉" if self.metrics['test_coverage'] >= 80 else "👍" if self.metrics['test_coverage'] >= 50 else "📈" if self.metrics['test_coverage'] >= 20 else "📉"
        print(f"📊 测试覆盖率: {coverage_icon} {self.metrics['test_coverage']:.1f}%")

        # 语法检查
        syntax_status = "✅" if self.metrics['syntax_errors'] == 0 else "❌"
        print(f"✨ 语法检查: {syntax_status} {self.metrics['syntax_errors']} 个错误")

        print("-"*60)

        # 状态说明
        if self.metrics['status'] == 'excellent':
            print("🎉 项目质量优秀！可以安心部署。")
        elif self.metrics['status'] == 'good':
            print("👍 项目质量良好，建议继续提升覆盖率。")
        elif self.metrics['status'] == 'fair':
            print("📈 项目质量中等，需要关注代码质量。")
        elif self.metrics['status'] == 'poor':
            print("📉 项目质量较差，需要重点关注测试覆盖率。")
        elif self.metrics['status'] == 'warning':
            print("⚠️ 项目存在警告，建议优先修复测试失败。")
        else:
            print("🚨 项目存在严重问题，需要立即修复！")

        print("="*60)

    def run_continuous_monitoring(self, interval: int = 300):
        """运行持续监控"""
        print(f"🔄 启动持续质量监控 (间隔: {interval}秒)")
        print("按 Ctrl+C 停止监控")

        try:
            while True:
                self.generate_report()
                self.display_dashboard()

                import time
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n👋 质量监控已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="项目质量监控仪表板")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="启动持续监控")
    parser.add_argument("--interval", "-i", type=int, default=300,
                       help="监控间隔（秒，默认300秒）")
    parser.add_argument("--project-root", "-p", type=str,
                       help="项目根目录路径")

    args = parser.parse_args()

    # 创建监控仪表板
    dashboard = QualityMonitorDashboard(args.project_root)

    if args.continuous:
        dashboard.run_continuous_monitoring(args.interval)
    else:
        dashboard.generate_report()
        dashboard.display_dashboard()


if __name__ == "__main__":
    main()