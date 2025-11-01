#!/usr/bin/env python3
"""
测试覆盖率追踪工具
用于追踪覆盖率提升进度
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class CoverageTracker:
    """覆盖率追踪器"""

    def __init__(self, report_dir: str = "docs/_reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True, parents=True)
        self.trend_file = self.report_dir / "coverage_trend.json"
        self.history_file = self.report_dir / "coverage_history.json"

    def load_trend(self) -> List[Dict]:
        """加载覆盖率趋势数据"""
        if self.trend_file.exists():
            with open(self.trend_file, "r") as f:
                return json.load(f)
        return []

    def save_trend(self, trend_data: List[Dict]):
        """保存覆盖率趋势数据"""
        with open(self.trend_file, "w") as f:
            json.dump(trend_data, f, indent=2, ensure_ascii=False)

    def load_history(self) -> Dict:
        """加载历史数据"""
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                return json.load(f)
        return {}

    def save_history(self, history_data: Dict):
        """保存历史数据"""
        with open(self.history_file, "w") as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)

    def run_coverage(self) -> Optional[Dict]:
        """运行覆盖率测试"""
        try:
            # 使用pytest-cov生成覆盖率报告
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit",
                "--cov=src",
                "--cov-report=json:coverage.json",
                "--cov-report=term-missing",
                "-q",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())

            if result.returncode != 0:
                print(f"❌ 测试运行失败: {result.stderr}")
                return None

            # 读取覆盖率报告
            if Path("coverage.json").exists():
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)
                Path("coverage.json").unlink()  # 清理临时文件
                return coverage_data

            return None

        except Exception as e:
            print(f"❌ 运行覆盖率测试失败: {e}")
            return None

    def extract_module_coverage(self, coverage_data: Dict) -> Dict[str, float]:
        """提取各模块的覆盖率"""
        module_coverage = {}

        if "files" in coverage_data:
            for file_path, file_data in coverage_data["files"].items():
                # 将文件路径转换为模块名
                module_name = (
                    str(Path(file_path).relative_to("src")).replace("/", ".").replace(".py", "")
                )
                module_coverage[module_name] = file_data["summary"]["percent_covered"]

        return module_coverage

    def update_trend(self, coverage_data: Dict):
        """更新覆盖率趋势"""
        trend = self.load_trend()

        # 创建新的记录
        record = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
            "covered_lines": coverage_data.get("totals", {}).get("covered_lines", 0),
            "num_statements": coverage_data.get("totals", {}).get("num_statements", 0),
            "missing_lines": coverage_data.get("totals", {}).get("missing_lines", 0),
            "modules": self.extract_module_coverage(coverage_data),
        }

        # 添加新记录
        trend.append(record)

        # 保留最近30条记录
        if len(trend) > 30:
            trend = trend[-30:]

        self.save_trend(trend)
        return record

    def generate_report(self, latest_record: Dict):
        """生成覆盖率报告"""
        report = {
            "latest": latest_record,
            "trend": self.load_trend()[-10:],  # 最近10条记录
            "targets": {
                "current_phase": "Phase 4A",
                "current_target": 50,
                "next_target": 60,
                "final_target": 80,
            },
            "module_status": self.analyze_module_status(latest_record.get("modules", {})),
        }

        # 保存报告
        report_file = self.report_dir / "COVERAGE_TRACKING_REPORT.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def analyze_module_status(self, modules: Dict[str, float]) -> Dict:
        """分析模块状态"""
        if not modules:
            return {}

        # 按覆盖率分类模块
        high_coverage = {k: v for k, v in modules.items() if v >= 80}
        medium_coverage = {k: v for k, v in modules.items() if 50 <= v < 80}
        low_coverage = {k: v for k, v in modules.items() if v < 50}

        return {
            "total_modules": len(modules),
            "high_coverage": len(high_coverage),
            "medium_coverage": len(medium_coverage),
            "low_coverage": len(low_coverage),
            "average_coverage": sum(modules.values()) / len(modules) if modules else 0,
            "modules_needing_attention": list(low_coverage.keys())[:10],  # 需要关注的前10个模块
        }

    def print_summary(self, record: Dict, report: Dict):
        """打印摘要信息"""
        print("\n" + "=" * 60)
        print("📊 测试覆盖率追踪报告")
        print("=" * 60)

        print(f"\n📅 时间: {record['date']}")
        print(f"🎯 总覆盖率: {record['total_coverage']:.1f}%")
        print(f"📝 覆盖行数: {record['covered_lines']}/{record['num_statements']}")
        print(f"❌ 未覆盖行数: {record['missing_lines']}")

        # 目标进度
        current = record["total_coverage"]
        targets = report["targets"]

        print("\n🎯 目标进度:")
        print(f"  当前阶段: {targets['current_phase']}")
        print(f"  当前目标: {targets['current_target']}%")
        print(f"  下一个目标: {targets['next_target']}%")
        print(f"  最终目标: {targets['final_target']}%")

        # 进度条
        progress = min(current / targets["current_target"] * 100, 100)
        bar_length = 50
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\n📈 当前阶段进度: [{bar}] {progress:.1f}%")

        # 模块状态
        module_status = report["module_status"]
        if module_status:
            print("\n📦 模块状态:")
            print(f"  总模块数: {module_status['total_modules']}")
            print(f"  高覆盖率(≥80%): {module_status['high_coverage']}")
            print(f"  中等覆盖率(50-80%): {module_status['medium_coverage']}")
            print(f"  低覆盖率(<50%): {module_status['low_coverage']}")
            print(f"  平均覆盖率: {module_status['average_coverage']:.1f}%")

            if module_status["modules_needing_attention"]:
                print("\n⚠️  需要关注的模块:")
                for module in module_status["modules_needing_attention"][:5]:
                    coverage = report.get("module_coverage", {}).get(module, 0)
                    print(f"  - {module}: {coverage:.1f}%")

        # 趋势
        trend = report["trend"]
        if len(trend) >= 2:
            previous = trend[-2]
            change = current - previous["total_coverage"]
            change_str = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"
            print(f"\n📊 趋势: {change_str} (相比上次)")

        print("\n" + "=" * 60)

    def track(self):
        """执行追踪"""
        print("🚀 开始运行覆盖率测试...")

        # 运行覆盖率测试
        coverage_data = self.run_coverage()
        if not coverage_data:
            print("❌ 无法获取覆盖率数据")
            return

        # 更新趋势
        latest_record = self.update_trend(coverage_data)

        # 生成报告
        report = self.generate_report(latest_record)

        # 打印摘要
        self.print_summary(latest_record, report)

        print(f"\n📄 详细报告已保存到: {self.report_dir}/COVERAGE_TRACKING_REPORT.json")

        return latest_record


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试覆盖率追踪工具")
    parser.add_argument("--report-dir", default="docs/_reports", help="报告目录")
    parser.add_argument("--show-history", action="store_true", help="显示历史趋势")

    args = parser.parse_args()

    tracker = CoverageTracker(args.report_dir)

    if args.show_history:
        # 显示历史趋势
        trend = tracker.load_trend()
        if trend:
            print("\n📈 历史覆盖率趋势:")
            for record in trend[-10:]:
                print(f"  {record['date']}: {record['total_coverage']:.1f}%")
        else:
            print("暂无历史数据")
    else:
        # 运行追踪
        tracker.track()


if __name__ == "__main__":
    main()
