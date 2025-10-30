#!/usr/bin/env python3
"""
自动化覆盖率监控脚本
Automated Coverage Monitoring Script

持续跟踪测试覆盖率变化，提供实时监控和报告。
"""

import subprocess
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse


class CoverageMonitor:
    """覆盖率监控器"""

    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.coverage_file = self.project_root / ".coverage_data.json"
        self.history_file = self.project_root / "coverage_history.json"

    def get_current_coverage(self):
        """获取当前覆盖率（简化版）"""
        try:
            # Phase E: 包含新的高级测试文件
            phase_e_tests = [
                "tests/unit/domain/test_advanced_business_logic.py",
                "tests/unit/edge_cases/test_boundary_and_exception_handling.py",
                "tests/unit/performance/test_advanced_performance.py"
            ]

            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "--cov=src",
                "--cov-report=json:.coverage_report.json",
                "--tb=short",
                "-q",
                *phase_e_tests
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                report_file = self.project_root / ".coverage_report.json"
                if report_file.exists():
                    with open(report_file) as f:
                        report = json.load(f)
                    totals = report.get("totals", {})
                    return totals.get("percent_covered", 0.0)
            except Exception:
            pass

        return 0.0

    def print_summary(self):
        """打印覆盖率摘要"""
        coverage = self.get_current_coverage()
        
        print("\n" + "="*50)
        print("📊 测试覆盖率摘要")
        print("="*50)
        print(f"📈 当前覆盖率: {coverage:.2f}%")
        
        if coverage >= 5.0:
            print("✅ 覆盖率已达到最低要求 (5.0%)")
        else:
            print("⚠️ 覆盖率低于最低要求 (5.0%)")
        
        print("="*50)

    def setup_quality_gates(self, minimum_coverage=5.0):
        """设置质量门禁"""
        current_coverage = self.get_current_coverage()
        
        print(f"\n🚪 质量门禁检查 (最低要求: {minimum_coverage}%)")
        print("-" * 40)
        
        passed = current_coverage >= minimum_coverage
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} 覆盖率: {current_coverage:.2f}% (要求: {minimum_coverage}%)")
        
        print("-" * 40)
        if passed:
            print("🎉 质量门禁检查通过！")
            return True
        else:
            print("⚠️ 质量门禁检查失败")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化覆盖率监控")
    parser.add_argument("--quality-gates", action="store_true", help="执行质量门禁检查")
    
    args = parser.parse_args()
    
    print("🚀 启动自动化覆盖率监控...")
    
    monitor = CoverageMonitor()
    monitor.print_summary()
    
    if args.quality_gates:
        monitor.setup_quality_gates()
    
    print("\n✅ 覆盖率监控完成")


if __name__ == "__main__":
    main()
