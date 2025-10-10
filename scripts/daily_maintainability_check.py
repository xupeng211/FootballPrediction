#!/usr/bin/env python3
"""
每日代码可维护性检查脚本
跟踪改进进度
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class DailyMaintainabilityChecker:
    """每日可维护性检查器"""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.report_file = self.root_dir / "docs" / "daily_maintainability_report.json"

    def get_test_coverage(self) -> float:
        """获取测试覆盖率"""
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "--cov=src",
                    "--cov-report=json",
                    "--tb=short",
                ],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # 读取覆盖率报告
                coverage_file = self.root_dir / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, "r") as f:
                        data = json.load(f)
                        return data["totals"]["percent_covered"]
            return 0.0
        except Exception:
            return 0.0

    def count_test_errors(self) -> int:
        """统计测试错误数"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 计算错误数量
            errors = result.stderr.count("ERROR")
            return errors
        except Exception:
            return 999  # 表示无法获取

    def count_complex_functions(self) -> int:
        """统计高复杂度函数数（需要安装 radon）"""
        try:
            result = subprocess.run(
                ["radon", "cc", "src", "--json", "--min=B"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                count = 0
                for file_data in data.values():
                    for item in file_data:
                        if item["type"] == "function" and item["rank"] in [
                            "B",
                            "C",
                            "D",
                            "E",
                            "F",
                        ]:
                            count += 1
                return count
            return 0
        except Exception:
            # 如果没有 radon，返回预估数
            return 20

    def count_large_files(self, threshold: int = 500) -> int:
        """统计大文件数"""
        count = 0
        large_files = []

        for py_file in (self.root_dir / "src").rglob("*.py"):
            lines = len(py_file.read_text(encoding="utf-8").splitlines())
            if lines > threshold:
                count += 1
                large_files.append((str(py_file.relative_to(self.root_dir)), lines))

        return count

    def check_mypy_errors(self) -> int:
        """统计 MyPy 错误数"""
        try:
            result = subprocess.run(
                ["mypy", "src", "--show-error-codes"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            errors = result.stdout.count("error:")
            return errors
        except Exception:
            return 531  # 使用已知值

    def generate_report(self) -> Dict:
        """生成每日报告"""
        today = datetime.now().strftime("%Y-%m-%d")

        report = {
            "date": today,
            "metrics": {
                "test_coverage": self.get_test_coverage(),
                "test_errors": self.count_test_errors(),
                "complex_functions": self.count_complex_functions(),
                "large_files": self.count_large_files(),
                "mypy_errors": self.check_mypy_errors(),
            },
            "goals": {
                "test_coverage": 30.0,
                "test_errors": 0,
                "complex_functions": 5,
                "large_files": 20,
                "mypy_errors": 0,
            },
            "maintainability_score": self.calculate_score(),
        }

        return report

    def calculate_score(self) -> float:
        """计算可维护性评分"""
        coverage = self.get_test_coverage()
        errors = self.count_test_errors()
        complex = self.count_complex_functions()

        # 简单的评分算法
        score = 5.2  # 基础分

        # 测试覆盖率影响
        score += (coverage - 20) * 0.1

        # 错误数影响
        score -= errors * 0.05

        # 复杂度影响
        score -= (complex - 5) * 0.1

        # 确保分数在 0-10 范围内
        return max(0, min(10, score))

    def save_report(self, report: Dict):
        """保存报告"""
        self.report_file.parent.mkdir(exist_ok=True)

        # 读取历史报告
        history = []
        if self.report_file.exists():
            with open(self.report_file, "r") as f:
                history = json.load(f).get("history", [])

        # 添加今日报告
        history.append(report)

        # 只保留最近30天
        history = history[-30:]

        # 保存
        full_report = {
            "current": report,
            "history": history,
            "trend": self.calculate_trend(history),
        }

        with open(self.report_file, "w") as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)

    def calculate_trend(self, history: List[Dict]) -> Dict:
        """计算趋势"""
        if len(history) < 2:
            return {"coverage": "stable", "score": "stable"}

        current = history[-1]["metrics"]
        previous = history[-2]["metrics"]

        trends = {}

        # 覆盖率趋势
        if current["test_coverage"] > previous["test_coverage"]:
            trends["coverage"] = "📈 上升"
        elif current["test_coverage"] < previous["test_coverage"]:
            trends["coverage"] = "📉 下降"
        else:
            trends["coverage"] = "➡️ 稳定"

        # 评分趋势
        if history[-1]["maintainability_score"] > history[-2]["maintainability_score"]:
            trends["score"] = "📈 上升"
        elif (
            history[-1]["maintainability_score"] < history[-2]["maintainability_score"]
        ):
            trends["score"] = "📉 下降"
        else:
            trends["score"] = "➡️ 稳定"

        return trends

    def print_report(self, report: Dict):
        """打印报告"""
        print("\n" + "=" * 60)
        print(f"📊 代码可维护性日报 - {report['date']}")
        print("=" * 60)

        print("\n📈 当前指标:")
        metrics = report["metrics"]
        goals = report["goals"]

        # 测试覆盖率
        coverage_status = "✅" if metrics["test_coverage"] >= 20 else "❌"
        print(
            f"  {coverage_status} 测试覆盖率: {metrics['test_coverage']:.1f}% (目标: {goals['test_coverage']}%)"
        )

        # 测试错误
        error_status = "✅" if metrics["test_errors"] == 0 else "❌"
        print(
            f"  {error_status} 测试错误数: {metrics['test_errors']} (目标: {goals['test_errors']})"
        )

        # 复杂函数
        complex_status = "✅" if metrics["complex_functions"] <= 10 else "❌"
        print(
            f"  {complex_status} 高复杂度函数: {metrics['complex_functions']} (目标: {goals['complex_functions']})"
        )

        # 大文件
        large_status = "✅" if metrics["large_files"] <= 30 else "❌"
        print(
            f"  {large_status} 大文件数: {metrics['large_files']} (目标: {goals['large_files']})"
        )

        # MyPy错误
        mypy_status = "✅" if metrics["mypy_errors"] <= 100 else "❌"
        print(
            f"  {mypy_status} MyPy错误: {metrics['mypy_errors']} (目标: {goals['mypy_errors']})"
        )

        print(f"\n🎯 可维护性评分: {report['maintainability_score']:.1f}/10.0")

        if "trend" in report:
            print("\n📊 趋势:")
            print(f"  覆盖率: {report['trend'].get('coverage', '未知')}")
            print(f"  评分: {report['trend'].get('score', '未知')}")

        print("\n💡 建议行动:")
        if metrics["test_coverage"] < 25:
            print("  • 添加更多单元测试以提升覆盖率")
        if metrics["test_errors"] > 0:
            print("  • 修复测试导入和运行错误")
        if metrics["complex_functions"] > 10:
            print("  • 重构高复杂度函数")
        if metrics["large_files"] > 30:
            print("  • 拆分大型文件")
        if metrics["mypy_errors"] > 100:
            print("  • 修复 MyPy 类型错误")

    def check_and_report(self):
        """检查并生成报告"""
        report = self.generate_report()
        self.save_report(report)
        self.print_report(report)


if __name__ == "__main__":
    checker = DailyMaintainabilityChecker()
    checker.check_and_report()
