#!/usr/bin/env python3
"""
覆盖率仪表板工具
实时监控和分析测试覆盖率进展
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CoverageSnapshot:
    """覆盖率快照"""
    timestamp: str
    total_coverage: float
    total_statements: int
    covered_statements: int
    missing_statements: int
    src_files_count: int
    covered_files_count: int
    top_files: list[dict[str, Any]]


class CoverageDashboard:
    """覆盖率仪表板"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.data_file = self.project_root / "coverage_data.json"
        self.coverage_file = self.project_root / "coverage.json"

    def get_current_coverage(self) -> CoverageSnapshot | None:
        """获取当前覆盖率数据"""
        if not self.coverage_file.exists():
            return None

        try:
            with open(self.coverage_file, encoding='utf-8') as f:
                data = json.load(f)

            totals = data['totals']
            files = data['files']

            # 筛选src目录的文件
            src_files = {k: v for k, v in files.items() if k.startswith('src/')}

            # 按覆盖率排序
            top_files = sorted(
                [
                    {'file': k, 'coverage': v['summary']['percent_covered'], 'statements': v['summary']['num_statements']}
                    for k, v in src_files.items()
                    if v['summary']['percent_covered'] > 0
                ],
                key=lambda x: x['coverage'],
                reverse=True
            )[:10]

            return CoverageSnapshot(
                timestamp=datetime.now().isoformat(),
                total_coverage=totals['percent_covered'],
                total_statements=totals['num_statements'],
                covered_statements=totals['covered_lines'],
                missing_statements=totals['missing_lines'],
                src_files_count=len(src_files),
                covered_files_count=len([f for f in src_files.values() if f['summary']['percent_covered'] > 0]),


                top_files=top_files
            )

        except Exception:
            return None

    def save_snapshot(self, snapshot: CoverageSnapshot):
        """保存覆盖率快照"""
        try:
            # 读取历史数据
            history = []
            if self.data_file.exists():
                with open(self.data_file, encoding='utf-8') as f:
                    history = json.load(f)

            # 添加新快照
            history.append(asdict(snapshot))

            # 保持最近100条记录
            history = history[-100:]

            # 保存数据
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)


        except Exception:
            pass

    def load_history(self) -> list[CoverageSnapshot]:
        """加载历史覆盖率数据"""
        try:
            if not self.data_file.exists():
                return []

            with open(self.data_file, encoding='utf-8') as f:
                data = json.load(f)

            return [CoverageSnapshot(**item) for item in data]

        except Exception:
            return []

    def show_dashboard(self):
        """显示仪表板"""

        # 获取当前覆盖率
        current = self.get_current_coverage()
        if not current:
            return

        # 加载历史数据
        history = self.load_history()


        # 计算进展
        if len(history) >= 2:
            previous = history[-2]
            current.total_coverage - previous.total_coverage
            current.covered_statements - previous.covered_statements


            # 显示趋势
            if len(history) >= 5:
                recent = history[-5:]
                sum(
                    recent[i].total_coverage - recent[i-1].total_coverage
                    for i in range(1, len(recent))
                ) / (len(recent) - 1)


        # 目标进度
        targets = [5, 10, 15, 25, 50]
        for target in targets:
            if current.total_coverage >= target:
                pass
            else:
                target - current.total_coverage

        # 覆盖率最高的文件
        if current.top_files:
            for _i, file_info in enumerate(current.top_files[:5], 1):
                file_info['file'].replace('src/', '')
                file_info['coverage']
                file_info['statements']

        # 历史趋势
        if len(history) >= 3:
            for snapshot in history[-5:]:
                snapshot.timestamp[:19].replace('T', ' ')

    def generate_report(self, output_file: str = None):
        """生成详细报告"""
        current = self.get_current_coverage()
        if not current:
            return

        history = self.load_history()

        report_lines = [
            "# 覆盖率报告",
            f"生成时间: {current.timestamp}",
            "",
            "## 当前状态",
            f"- 总覆盖率: {current.total_coverage:.2f}%",
            f"- 语句覆盖: {current.covered_statements:,} / {current.total_statements:,}",
            f"- 文件覆盖: {current.covered_files_count:,} / {current.src_files_count:,}",
            "",
            "## 进展分析"
        ]

        if len(history) >= 2:
            previous = history[-2]
            coverage_change = current.total_coverage - previous.total_coverage
            statements_change = current.covered_statements - previous.covered_statements

            report_lines.extend([
                f"- 覆盖率变化: {coverage_change:+.2f}%",
                f"- 新增覆盖语句: {statements_change:+,}",
                ""
            ])

        # 添加文件详情
        report_lines.extend([
            "## 覆盖率最高的文件",
            ""
        ])

        for i, file_info in enumerate(current.top_files[:10], 1):
            filename = file_info['file']
            coverage = file_info['coverage']
            statements = file_info['statements']
            report_lines.append(f"{i}. {filename} - {coverage:.1f}% ({statements} 语句)")

        # 保存报告
        report_content = "\n".join(report_lines)

        if output_file:
            output_path = Path(output_file)
        else:
            output_path = self.project_root / "coverage_report.md"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
        except Exception:
            pass

    def watch_mode(self, interval: int = 30):
        """监控模式"""

        try:
            while True:
                # 清屏

                # 显示仪表板
                self.show_dashboard()

                # 保存快照
                current = self.get_current_coverage()
                if current:
                    self.save_snapshot(current)

                # 等待下次检查
                time.sleep(interval)

        except KeyboardInterrupt:
            pass


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="覆盖率仪表板工具")
    parser.add_argument("--save", action="store_true", help="保存当前覆盖率快照")
    parser.add_argument("--history", action="store_true", help="显示历史趋势")
    parser.add_argument("--report", nargs="?", const="", help="生成详细报告")
    parser.add_argument("--watch", type=int, nargs="?", const=30, help="监控模式")
    parser.add_argument("--dashboard", action="store_true", help="显示仪表板")

    args = parser.parse_args()

    dashboard = CoverageDashboard()

    if args.watch is not None:
        dashboard.watch_mode(args.watch)
    elif args.save:
        current = dashboard.get_current_coverage()
        if current:
            dashboard.save_snapshot(current)
    elif args.history:
        history = dashboard.load_history()
        if history:
            for _i, snapshot in enumerate(history, 1):
                snapshot.timestamp[:19].replace('T', ' ')
        else:
            pass
    elif args.report is not None:
        output_file = args.report if args.report else None
        dashboard.generate_report(output_file)
    else:
        # 默认显示仪表板
        dashboard.show_dashboard()


if __name__ == "__main__":
    main()
