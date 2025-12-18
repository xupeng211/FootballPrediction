#!/usr/bin/env python3
"""
覆盖率趋势追踪系统
监控和分析测试覆盖率变化趋势
"""

import json
import os
import sys
import subprocess
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import re


class CoverageTracker:
    """覆盖率趋势追踪器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.data_file = self.project_root / ".coverage_trends.json"
        self.coverage_xml = self.project_root / "coverage.xml"
        self.load_trend_data()

    def load_trend_data(self):
        """加载趋势数据"""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.trend_data = json.load(f)
        else:
            self.trend_data = {
                "history": [],
                "module_trends": {},
                "targets": {
                    "overall": 25.0,
                    "inference_service": 90.0,
                    "core_services": 80.0,
                },
            }

    def save_trend_data(self):
        """保存趋势数据"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.trend_data, f, indent=2, ensure_ascii=False)

    def parse_coverage_xml(self) -> Dict:
        """解析覆盖率XML文件"""
        if not self.coverage_xml.exists():
            return {}

        try:
            tree = ET.parse(self.coverage_xml)
            root = tree.getroot()

            coverage_data = {}

            # 总体覆盖率
            for coverage_elem in root.findall(".//coverage"):
                lines_valid = int(coverage_elem.get("lines-valid", 0))
                lines_covered = int(coverage_elem.get("lines-covered", 0))
                if lines_valid > 0:
                    coverage_data["total"] = (lines_covered / lines_valid) * 100

            # 模块级覆盖率
            for package in root.findall(".//package"):
                package_name = package.get("name")
                for classes in package.findall("classes"):
                    for class_elem in classes.findall("class"):
                        class_name = class_elem.get("name", "").split(".")[-1]
                        full_name = f"{package_name}.{class_name}"

                        lines_valid = int(class_elem.get("lines-valid", 0))
                        lines_covered = int(class_elem.get("lines-covered", 0))
                        branches_valid = int(class_elem.get("branches-valid", 0))
                        branches_covered = int(class_elem.get("branches-covered", 0))

                        if lines_valid > 0:
                            line_coverage = (lines_covered / lines_valid) * 100
                            branch_coverage = (
                                (branches_covered / branches_valid * 100)
                                if branches_valid > 0
                                else 0
                            )

                            coverage_data[full_name] = {
                                "line_coverage": line_coverage,
                                "branches_coverage": branch_coverage,
                                "lines_covered": lines_covered,
                                "lines_valid": lines_valid,
                                "branches_covered": branches_covered,
                                "branches_valid": branches_valid,
                            }

            return coverage_data

        except Exception as e:
            print(f"❌ 解析覆盖率XML失败: {e}")
            return {}

    def run_coverage_analysis(self) -> Dict:
        """运行覆盖率分析"""
        try:
            # 清理旧文件
            if self.coverage_xml.exists():
                os.remove(self.coverage_xml)

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "tests/unit/test_services_core.py",
                    "tests/unit/test_inference_service_error_handling_v2.py",
                    "tests/unit/test_inference_service_boundary_conditions_v2.py",
                    "tests/unit/test_config_extended.py",
                    "tests/unit/test_database_simple.py",
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=term-missing",
                    "-q",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # 解析XML获取详细覆盖率
                coverage_data = self.parse_coverage_xml()

                # 从终端输出提取关键信息
                terminal_output = result.stdout

                return {
                    "success": True,
                    "xml_data": coverage_data,
                    "terminal_output": terminal_output,
                }
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_module_coverage(self, coverage_data: Dict) -> Dict:
        """提取关键模块覆盖率"""
        module_coverage = {}

        # 查找推理服务覆盖率
        for module_name, data in coverage_data.items():
            if "inference_service_v2" in module_name:
                module_coverage["inference_service_v2"] = data["line_coverage"]
            elif "collection_service" in module_name:
                module_coverage["collection_service"] = data["line_coverage"]
            elif "config" in module_name:
                module_coverage["config"] = data["line_coverage"]
            elif "database" in module_name:
                module_coverage["database"] = data["line_coverage"]

        # 如果找不到具体模块，使用总体覆盖率
        if "total" in coverage_data:
            module_coverage["total"] = coverage_data["total"]

        return module_coverage

    def record_coverage_snapshot(self):
        """记录覆盖率快照"""
        timestamp = datetime.datetime.now().isoformat()

        print("🔍 运行覆盖率分析...")
        analysis_result = self.run_coverage_analysis()

        if not analysis_result["success"]:
            print(f"❌ 覆盖率分析失败: {analysis_result.get('error', 'Unknown error')}")
            return None

        coverage_data = analysis_result.get("xml_data", {})
        module_coverage = self.extract_module_coverage(coverage_data)

        snapshot = {
            "timestamp": timestamp,
            "overall_coverage": coverage_data.get("total", 0),
            "module_coverage": module_coverage,
            "raw_data": coverage_data,
        }

        # 添加到历史记录
        self.trend_data["history"].append(snapshot)

        # 保持最近60条记录（30天，每天两次）
        if len(self.trend_data["history"]) > 60:
            self.trend_data["history"] = self.trend_data["history"][-60:]

        # 更新模块趋势
        for module, coverage in module_coverage.items():
            if module not in self.trend_data["module_trends"]:
                self.trend_data["module_trends"][module] = []

            self.trend_data["module_trends"][module].append(
                {"timestamp": timestamp, "coverage": coverage}
            )

            # 保持每个模块最近30条记录
            if len(self.trend_data["module_trends"][module]) > 30:
                self.trend_data["module_trends"][module] = self.trend_data[
                    "module_trends"
                ][module][-30:]

        self.save_trend_data()
        return snapshot

    def calculate_trend_stats(self, values: List[float]) -> Dict:
        """计算趋势统计"""
        if not values:
            return {}

        return {
            "latest": values[-1],
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "trend": values[-1] - values[0] if len(values) > 1 else 0,
            "count": len(values),
        }

    def display_coverage_trends(self):
        """显示覆盖率趋势"""
        if not self.trend_data["history"]:
            print("❌ 没有覆盖率数据可用")
            return

        print("📈 测试覆盖率趋势分析")
        print("=" * 80)

        # 最新快照
        latest = self.trend_data["history"][-1]
        overall_cov = latest["overall_coverage"]
        target_cov = self.trend_data["targets"]["overall"]

        print(f"📊 当前状态")
        print(f"   总体覆盖率: {overall_cov:.1f}% (目标: {target_cov}%)")

        if overall_cov >= target_cov:
            print("   \033[92m✅ 已达到覆盖率目标\033[0m")
        else:
            gap = target_cov - overall_cov
            print(f"   \033[93m⚠️  距离目标还差 {gap:.1f}%\033[0m")

        print()

        # 模块覆盖率
        print("🔧 模块覆盖率")
        print("-" * 40)

        module_cov = latest.get("module_coverage", {})
        for module, coverage in module_cov.items():
            target = self.trend_data["targets"].get(module, 0)

            if coverage >= target:
                status = "\033[92m✅\033[0m"
            else:
                status = "\033[93m⚠️\033[0m"

            print(f"   {module:20} {coverage:6.1f}% {status}")

        print()

        # 趋势分析
        if len(self.trend_data["history"]) > 1:
            print("📊 趋势分析")
            print("-" * 40)

            # 总体趋势
            overall_values = [h["overall_coverage"] for h in self.trend_data["history"]]
            stats = self.calculate_trend_stats(overall_values)

            trend_str = ""
            if stats["trend"] > 0:
                trend_str = f"\033[92m↗️ +{stats['trend']:.1f}%\033[0m"
            elif stats["trend"] < 0:
                trend_str = f"\033[91m↘️ {stats['trend']:.1f}%\033[0m"
            else:
                trend_str = "\033[93m➡️ 0.0%\033[0m"

            print(f"   总体覆盖率趋势: {trend_str}")
            print(f"   平均覆盖率: {stats['average']:.1f}%")
            print(f"   最高覆盖率: {stats['max']:.1f}%")
            print(f"   最低覆盖率: {stats['min']:.1f}%")

            print()

            # 模块趋势
            for module, values in self.trend_data["module_trends"].items():
                coverage_values = [v["coverage"] for v in values]
                stats = self.calculate_trend_stats(coverage_values)

                trend_str = ""
                if stats["trend"] > 0:
                    trend_str = f"\033[92m↗️ +{stats['trend']:.1f}%\033[0m"
                elif stats["trend"] < 0:
                    trend_str = f"\033[91m↘️ {stats['trend']:.1f}%\033[0m"
                else:
                    trend_str = "\033[93m➡️ 0.0%\033[0m"

                print(f"   {module:20} {stats['latest']:6.1f}% {trend_str}")

        print()

        # 历史记录
        print("📅 最近记录")
        print("-" * 40)
        print("时间戳\t\t\t总体覆盖率\t推理服务\t数据库\t配置")
        print("-" * 60)

        for snapshot in self.trend_data["history"][-10:]:
            timestamp = snapshot["timestamp"][:19].replace("T", " ")
            overall = snapshot["overall_coverage"]

            module_cov = snapshot.get("module_coverage", {})
            inference = module_cov.get("inference_service_v2", 0)
            database = module_cov.get("database", 0)
            config = module_cov.get("config", 0)

            print(
                f"{timestamp}\t{overall:8.1f}%\t\t{inference:8.1f}%\t{database:8.1f}%\t{config:6.1f}%"
            )

        print()
        print("=" * 80)

    def generate_coverage_report(self, output_file: str = None):
        """生成覆盖率趋势报告"""
        if not self.trend_data["history"]:
            print("❌ 没有覆盖率数据可用于生成报告")
            return

        output_path = (
            Path(output_file)
            if output_file
            else self.project_root / "coverage-trend-report.md"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 测试覆盖率趋势报告\n\n")
            f.write(
                f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            # 最新状态
            latest = self.trend_data["history"][-1]
            f.write("## 当前覆盖率状态\n\n")
            f.write(f"- **总体覆盖率**: {latest['overall_coverage']:.1f}%\n")

            module_cov = latest.get("module_coverage", {})
            for module, coverage in module_cov.items():
                f.write(f"- **{module}**: {coverage:.1f}%\n")

            # 趋势分析
            if len(self.trend_data["history"]) > 1:
                f.write("\n## 趋势分析\n\n")

                overall_values = [
                    h["overall_coverage"] for h in self.trend_data["history"]
                ]
                stats = self.calculate_trend_stats(overall_values)

                f.write(f"- **趋势变化**: {stats['trend']:+.1f}%\n")
                f.write(f"- **平均覆盖率**: {stats['average']:.1f}%\n")
                f.write(f"- **最高覆盖率**: {stats['max']:.1f}%\n")
                f.write(f"- **最低覆盖率**: {stats['min']:.1f}%\n")

            # 建议和目标
            f.write("\n## 改进建议\n\n")

            overall_target = self.trend_data["targets"]["overall"]
            if latest["overall_coverage"] < overall_target:
                gap = overall_target - latest["overall_coverage"]
                f.write(f"### 优先级1: 达到覆盖率目标\n\n")
                f.write(f"- 当前距离目标还差 {gap:.1f}%\n")
                f.write("- 重点覆盖以下模块:\n")

                # 找出覆盖率最低的模块
                low_coverage_modules = []
                for module, coverage in module_cov.items():
                    if coverage < 70:  # 低于70%的模块
                        low_coverage_modules.append((module, coverage))

                low_coverage_modules.sort(key=lambda x: x[1])  # 按覆盖率排序
                for module, coverage in low_coverage_modules:
                    f.write(f"  - {module}: {coverage:.1f}%\n")

            f.write("\n### 优先级2: 持续改进\n\n")
            f.write("- 每日监控覆盖率变化\n")
            f.write("- 在CI/CD中设置覆盖率门禁\n")
            f.write("- 定期审查和优化测试策略\n")

            # 详细历史数据
            f.write("\n## 历史数据\n\n")
            f.write("| 时间 | 总体覆盖率 |")

            # 添加模块表头
            if module_cov:
                for module in sorted(module_cov.keys()):
                    f.write(f" {module} |")
            f.write("\n")

            # 分隔线
            f.write("|------|------------|")
            for _ in module_cov:
                f.write("---|")
            f.write("\n")

            # 数据行
            for snapshot in self.trend_data["history"][-15:]:  # 最近15条
                timestamp = snapshot["timestamp"][:19].replace("T", " ")
                overall = snapshot["overall_coverage"]
                f.write(f"| {timestamp} | {overall:.1f}% |")

                snap_module_cov = snapshot.get("module_coverage", {})
                for module in sorted(module_cov.keys()):
                    coverage = snap_module_cov.get(module, 0)
                    f.write(f" {coverage:.1f}% |")

                f.write("\n")

            f.write(f"\n---\n\n*报告由覆盖率趋势追踪系统生成*")

        print(f"📄 覆盖率趋势报告已生成: {output_path}")

    def set_target(self, module: str, target: float):
        """设置覆盖率目标"""
        self.trend_data["targets"][module] = target
        self.save_trend_data()
        print(f"✅ 已设置 {module} 覆盖率目标为 {target}%")

    def show_targets(self):
        """显示当前目标"""
        print("🎯 当前覆盖率目标")
        print("-" * 30)
        for module, target in self.trend_data["targets"].items():
            print(f"   {module:20}: {target:.1f}%")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="覆盖率趋势追踪系统")
    parser.add_argument("--project-root", help="项目根目录路径")
    parser.add_argument("--analyze", action="store_true", help="执行覆盖率分析")
    parser.add_argument("--report", help="生成趋势报告到指定文件")
    parser.add_argument("--trends", action="store_true", help="显示趋势分析")
    parser.add_argument(
        "--set-target",
        nargs=2,
        metavar=("MODULE", "TARGET"),
        help="设置模块覆盖率目标 (模块名 目标值)",
    )
    parser.add_argument("--show-targets", action="store_true", help="显示当前目标")
    parser.add_argument("--continuous", action="store_true", help="持续监控模式")

    args = parser.parse_args()

    tracker = CoverageTracker(args.project_root)

    if args.analyze:
        print("🔄 执行覆盖率分析...")
        snapshot = tracker.record_coverage_snapshot()
        if snapshot:
            tracker.display_coverage_trends()

    elif args.trends:
        tracker.display_coverage_trends()

    elif args.report:
        tracker.generate_coverage_report(args.report)

    elif args.set_target:
        module, target_str = args.set_target
        try:
            target = float(target_str)
            tracker.set_target(module, target)
        except ValueError:
            print(f"❌ 无效的目标值: {target_str}")

    elif args.show_targets:
        tracker.show_targets()

    elif args.continuous:
        print("🔄 启动持续监控模式...")
        print("按 Ctrl+C 退出")
        try:
            while True:
                snapshot = tracker.record_coverage_snapshot()
                if snapshot:
                    tracker.display_coverage_trends()

                # 等待30分钟
                print("⏰ 30分钟后刷新...")
                import time

                time.sleep(1800)  # 30分钟
        except KeyboardInterrupt:
            print("\n👋 监控已停止")

    else:
        # 默认显示趋势
        tracker.display_coverage_trends()


if __name__ == "__main__":
    main()
