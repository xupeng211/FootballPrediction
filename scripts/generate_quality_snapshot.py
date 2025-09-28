#!/usr/bin/env python3
"""
质量快照生成脚本

汇总多种质量指标，生成统一快照并更新历史记录。
"""

import json
import csv
import os
import sys
import glob
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess


class QualitySnapshotGenerator:
    """质量快照生成器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.reports_dir = self.project_root / "docs" / "_reports"
        self.snapshot_file = self.reports_dir / "QUALITY_SNAPSHOT.json"
        self.history_file = self.reports_dir / "QUALITY_HISTORY.csv"

        # 确保目录存在
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def collect_coverage_data(self) -> Dict[str, Any]:
        """收集覆盖率数据"""
        coverage_data = {
            "coverage_percent": 0.0,
            "total_lines": 0,
            "covered_lines": 0,
            "missed_lines": 0
        }

        try:
            # 尝试从 coverage.json 读取
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    cov_data = json.load(f)
                    totals = cov_data.get("totals", {})
                    coverage_data.update({
                        "coverage_percent": totals.get("percent_covered", 0.0),
                        "total_lines": totals.get("num_statements", 0),
                        "covered_lines": totals.get("covered_lines", 0),
                        "missed_lines": totals.get("missing_lines", 0)
                    })
            else:
                # 尝试运行 pytest-cov
                try:
                    result = subprocess.run(
                        ["python", "-m", "pytest", "--cov=src", "--cov-report=json"],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root
                    )
                    if result.returncode == 0 and coverage_file.exists():
                        return self.collect_coverage_data()
                except:
                    pass
        except Exception as e:
            print(f"收集覆盖率数据失败: {e}")

        return coverage_data

    def collect_mutation_data(self) -> Dict[str, Any]:
        """收集突变测试数据"""
        mutation_data = {
            "mutation_score": 0.0,
            "total_mutants": 0,
            "killed_mutants": 0,
            "survived_mutants": 0
        }

        try:
            mutation_dir = self.reports_dir / "mutation"
            if mutation_dir.exists():
                mutation_files = glob.glob(str(mutation_dir / "*.json"))
                if mutation_files:
                    with open(mutation_files[0], 'r') as f:
                        mut_data = json.load(f)
                        mutation_data.update({
                            "mutation_score": mut_data.get("mutation_score", 0.0),
                            "total_mutants": mut_data.get("total_mutants", 0),
                            "killed_mutants": mut_data.get("killed_mutants", 0),
                            "survived_mutants": mut_data.get("survived_mutants", 0)
                        })
        except Exception as e:
            print(f"收集突变测试数据失败: {e}")

        return mutation_data

    def collect_flaky_data(self) -> Dict[str, Any]:
        """收集Flaky测试数据"""
        flaky_data = {
            "flaky_rate": 0.0,
            "total_tests": 0,
            "flaky_tests": 0,
            "flaky_test_list": []
        }

        try:
            flaky_dir = self.reports_dir / "flaky"
            if flaky_dir.exists():
                flaky_files = glob.glob(str(flaky_dir / "*.json"))
                if flaky_files:
                    with open(flaky_files[0], 'r') as f:
                        flaky_info = json.load(f)
                        total_tests = flaky_info.get("total_tests", 0)
                        flaky_tests = flaky_info.get("flaky_tests", 0)
                        flaky_rate = (flaky_tests / total_tests * 100) if total_tests > 0 else 0.0

                        flaky_data.update({
                            "flaky_rate": flaky_rate,
                            "total_tests": total_tests,
                            "flaky_tests": flaky_tests,
                            "flaky_test_list": flaky_info.get("flaky_test_list", [])
                        })
        except Exception as e:
            print(f"收集Flaky测试数据失败: {e}")

        return flaky_data

    def collect_performance_data(self) -> Dict[str, Any]:
        """收集性能基准数据"""
        perf_data = {
            "performance_regressions": 0,
            "performance_improvements": 0,
            "benchmark_count": 0,
            "avg_performance_delta": 0.0
        }

        try:
            perf_dir = self.reports_dir / "performance"
            if perf_dir.exists():
                perf_files = glob.glob(str(perf_dir / "*.json"))
                if perf_files:
                    with open(perf_files[0], 'r') as f:
                        perf_info = json.load(f)
                        perf_data.update({
                            "performance_regressions": perf_info.get("regressions", 0),
                            "performance_improvements": perf_info.get("improvements", 0),
                            "benchmark_count": perf_info.get("benchmark_count", 0),
                            "avg_performance_delta": perf_info.get("avg_delta", 0.0)
                        })
        except Exception as e:
            print(f"收集性能数据失败: {e}")

        return perf_data

    def collect_auto_tests_data(self) -> Dict[str, Any]:
        """收集自动生成测试数据"""
        auto_tests_data = {
            "auto_tests_added": 0,
            "auto_test_files": [],
            "total_test_methods": 0
        }

        try:
            auto_tests_dir = self.project_root / "tests" / "auto_generated"
            if auto_tests_dir.exists():
                test_files = list(auto_tests_dir.glob("test_*.py"))
                auto_tests_data["auto_tests_added"] = len(test_files)
                auto_tests_data["auto_test_files"] = [f.name for f in test_files]

                # 统计测试方法数量
                total_methods = 0
                for test_file in test_files:
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 简单统计以 def test_ 开头的方法
                            test_methods = [line for line in content.split('\n') if line.strip().startswith('def test_')]
                            total_methods += len(test_methods)
                    except:
                        pass
                auto_tests_data["total_test_methods"] = total_methods
        except Exception as e:
            print(f"收集自动测试数据失败: {e}")

        return auto_tests_data

    def collect_ai_fix_data(self) -> Dict[str, Any]:
        """收集AI修复成功率数据"""
        ai_fix_data = {
            "ai_fix_attempts": 0,
            "ai_fix_successes": 0,
            "ai_fix_pass_rate": 0.0,
            "recent_fix_reports": []
        }

        try:
            # 从持续修复报告中汇总
            fix_reports = glob.glob(str(self.reports_dir / "CONTINUOUS_FIX_REPORT_*.md"))
            if fix_reports:
                attempts = 0
                successes = 0
                recent_reports = []

                for report_file in sorted(fix_reports)[-5:]:  # 最近5个报告
                    try:
                        with open(report_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 简单解析成功/失败
                            if "成功修复" in content or "SUCCESS" in content:
                                successes += 1
                            attempts += 1
                            recent_reports.append(Path(report_file).name)
                    except:
                        pass

                pass_rate = (successes / attempts * 100) if attempts > 0 else 0.0
                ai_fix_data.update({
                    "ai_fix_attempts": attempts,
                    "ai_fix_successes": successes,
                    "ai_fix_pass_rate": pass_rate,
                    "recent_fix_reports": recent_reports[-3:]  # 最近3个
                })
        except Exception as e:
            print(f"收集AI修复数据失败: {e}")

        return ai_fix_data

    def generate_snapshot(self) -> Dict[str, Any]:
        """生成质量快照"""
        print("🔍 开始收集质量指标...")

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "run_env": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform,
                "project_root": str(self.project_root)
            },
            "coverage": self.collect_coverage_data(),
            "mutation": self.collect_mutation_data(),
            "flaky": self.collect_flaky_data(),
            "performance": self.collect_performance_data(),
            "auto_tests": self.collect_auto_tests_data(),
            "ai_fix": self.collect_ai_fix_data()
        }

        # 计算汇总指标
        snapshot["summary"] = {
            "overall_score": self.calculate_overall_score(snapshot),
            "coverage_percent": snapshot["coverage"]["coverage_percent"],
            "mutation_score": snapshot["mutation"]["mutation_score"],
            "flaky_rate": snapshot["flaky"]["flaky_rate"],
            "performance_regressions": snapshot["performance"]["performance_regressions"],
            "auto_tests_added": snapshot["auto_tests"]["auto_tests_added"],
            "ai_fix_pass_rate": snapshot["ai_fix"]["ai_fix_pass_rate"]
        }

        print(f"✅ 质量快照生成完成")
        print(f"   - 覆盖率: {snapshot['summary']['coverage_percent']:.1f}%")
        print(f"   - Mutation Score: {snapshot['summary']['mutation_score']:.1f}%")
        print(f"   - Flaky Rate: {snapshot['summary']['flaky_rate']:.1f}%")
        print(f"   - 性能回归: {snapshot['summary']['performance_regressions']}")
        print(f"   - 自动测试: {snapshot['summary']['auto_tests_added']}")
        print(f"   - AI修复成功率: {snapshot['summary']['ai_fix_pass_rate']:.1f}%")

        return snapshot

    def calculate_overall_score(self, snapshot: Dict[str, Any]) -> float:
        """计算总体质量分数"""
        try:
            coverage_score = snapshot["coverage"]["coverage_percent"]
            mutation_score = snapshot["mutation"]["mutation_score"]
            flaky_penalty = min(snapshot["flaky"]["flaky_rate"], 50)  # Flaky最多扣50分
            perf_penalty = min(snapshot["performance"]["performance_regressions"] * 5, 30)  # 性能回归最多扣30分
            ai_bonus = min(snapshot["ai_fix"]["ai_fix_pass_rate"], 20)  # AI修复最多加20分

            overall_score = (coverage_score * 0.4 + mutation_score * 0.3 +
                          ai_bonus * 0.2 - flaky_penalty * 0.05 - perf_penalty * 0.02)

            return max(0, min(100, overall_score))
        except:
            return 0.0

    def save_snapshot(self, snapshot: Dict[str, Any]):
        """保存快照到JSON文件"""
        with open(self.snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        print(f"💾 快照已保存到: {self.snapshot_file}")

    def update_history(self, snapshot: Dict[str, Any]):
        """更新历史记录CSV"""
        file_exists = self.history_file.exists()

        with open(self.history_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 写入表头（如果文件不存在）
            if not file_exists:
                headers = [
                    "timestamp", "coverage", "mutation_score", "flaky_rate",
                    "perf_regressions", "auto_tests_added", "ai_fix_pass_rate", "run_env"
                ]
                writer.writerow(headers)

            # 写入数据行
            row = [
                snapshot["timestamp"],
                snapshot["summary"]["coverage_percent"],
                snapshot["summary"]["mutation_score"],
                snapshot["summary"]["flaky_rate"],
                snapshot["summary"]["performance_regressions"],
                snapshot["summary"]["auto_tests_added"],
                snapshot["summary"]["ai_fix_pass_rate"],
                json.dumps(snapshot["run_env"])
            ]
            writer.writerow(row)

        print(f"📊 历史记录已更新到: {self.history_file}")

    def run(self, dry_run: bool = False):
        """执行快照生成"""
        print("🚀 开始生成质量快照...")

        snapshot = self.generate_snapshot()

        if not dry_run:
            self.save_snapshot(snapshot)
            self.update_history(snapshot)
        else:
            print("🔍 DRY RUN - 快照内容:")
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))

        return snapshot


def main():
    parser = argparse.ArgumentParser(description="生成质量快照")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不保存文件")
    parser.add_argument("--project-root", help="项目根目录路径")
    args = parser.parse_args()

    generator = QualitySnapshotGenerator(args.project_root)
    generator.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()