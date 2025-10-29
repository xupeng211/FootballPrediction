#!/usr/bin/env python3
"""
类型安全修复进度跟踪脚本
实时跟踪和报告修复进度
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# 进度数据文件
PROGRESS_FILE = "type_fix_progress.json"
REPORT_FILE = "type_fix_report.md"


class TypeFixTracker:
    def __init__(self):
        self.progress_file = Path(PROGRESS_FILE)
        self.report_file = Path(REPORT_FILE)

    def get_current_stats(self) -> Dict:
        """获取当前的错误统计"""
        print("🔍 扫描当前错误状态...")

        # 获取 ANN401 统计
        ann401_result = subprocess.run(
            ["mypy", "src/", "--show-error-codes", "--no-error-summary"],
            capture_output=True,
            text=True,
        )

        ann401_count = ann401_result.stderr.count("ANN401")

        # 获取总 MyPy 错误
        total_errors = len([line for line in ann401_result.stderr.split("\n") if "error:" in line])

        # 按错误类型统计
        error_types = {}
        for line in ann401_result.stderr.split("\n"):
            if "[" in line and "]" in line:
                error_code = line.split("[")[-1].split("]")[0]
                error_types[error_code] = error_types.get(error_code, 0) + 1

        # 获取警告统计
        warnings = len([line for line in ann401_result.stderr.split("\n") if "warning:" in line])

        # 按目录统计
        errors_by_dir = {}
        for line in ann401_result.stderr.split("\n"):
            if ":" in line and "src/" in line:
                file_path = line.split(":")[0]
                if "src/" in file_path:
                    dir_path = "/".join(file_path.split("/")[:2])
                    errors_by_dir[dir_path] = errors_by_dir.get(dir_path, 0) + 1

        return {
            "timestamp": datetime.now().isoformat(),
            "ann401_count": ann401_count,
            "total_mypy_errors": total_errors,
            "total_warnings": warnings,
            "error_types": error_types,
            "errors_by_dir": errors_by_dir,
            "success": total_errors == 0,
        }

    def load_history(self) -> List[Dict]:
        """加载历史进度数据"""
        if self.progress_file.exists():
            with open(self.progress_file) as f:
                return json.load(f)
        return []

    def save_progress(self, stats: Dict):
        """保存进度数据"""
        history = self.load_history()

        # 添加当前统计（如果与上次不同）
        if not history or history[-1]["timestamp"] != stats["timestamp"]:
            history.append(stats)

        # 只保留最近30条记录
        history = history[-30:]

        with open(self.progress_file, "w") as f:
            json.dump(history, f, indent=2)

    def calculate_trend(self, history: List[Dict]) -> Dict:
        """计算趋势"""
        if len(history) < 2:
            return {"ann401_trend": 0, "errors_trend": 0}

        current = history[-1]
        previous = history[-2]

        return {
            "ann401_trend": previous["ann401_count"] - current["ann401_count"],
            "errors_trend": previous["total_mypy_errors"] - current["total_mypy_errors"],
            "time_diff": self._parse_time(current["timestamp"])
            - self._parse_time(previous["timestamp"]),
        }

    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

    def format_duration(self, td: timedelta) -> str:
        """格式化时间差"""
        if td.total_seconds() < 60:
            return f"{int(td.total_seconds())}秒"
        elif td.total_seconds() < 3600:
            return f"{int(td.total_seconds() / 60)}分钟"
        else:
            return f"{int(td.total_seconds() / 3600)}小时"

    def print_summary(self, stats: Dict, trend: Dict):
        """打印摘要"""
        print("\n" + "=" * 60)
        print("📊 类型安全修复进度报告")
        print("=" * 60)

        # 当前状态
        print(f"\n📅 时间: {stats['timestamp'][:19].replace('T', ' ')}")

        # ANN401 进度
        ann401_color = (
            "🟢" if stats["ann401_count"] == 0 else "🟡" if stats["ann401_count"] < 100 else "🔴"
        )
        print(f"\n{ann401_color} ANN401 类型注解: {stats['ann401_count']:,} 个")
        if trend["ann401_trend"] != 0:
            arrow = "↑" if trend["ann401_trend"] > 0 else "↓"
            print(f"   趋势: {arrow} {abs(trend['ann401_trend'])} 个")

        # 总错误进度
        errors_color = (
            "🟢"
            if stats["total_mypy_errors"] == 0
            else "🟡" if stats["total_mypy_errors"] < 50 else "🔴"
        )
        print(f"\n{errors_color} MyPy 总错误: {stats['total_mypy_errors']:,} 个")
        if trend["errors_trend"] != 0:
            arrow = "↑" if trend["errors_trend"] > 0 else "↓"
            print(f"   趋势: {arrow} {abs(trend['errors_trend'])} 个")

        # 警告
        print(f"\n⚠️  警告: {stats['total_warnings']:,} 个")

        # 错误类型分布
        if stats["error_types"]:
            print("\n📈 错误类型分布:")
            for error_type, count in sorted(
                stats["error_types"].items(), key=lambda x: x[1], reverse=True
            )[:5]:
                print(f"   {error_type}: {count:,} 个")

        # 目录分布
        if stats["errors_by_dir"]:
            print("\n📁 错误分布:")
            for dir_path, count in sorted(
                stats["errors_by_dir"].items(), key=lambda x: x[1], reverse=True
            )[:5]:
                print(f"   {dir_path}: {count:,} 个")

        # 成功状态
        if stats["success"]:
            print("\n🎉 恭喜！所有类型错误已修复！")

        print("=" * 60)

    def generate_report(self, history: List[Dict]):
        """生成 Markdown 报告"""
        if not history:
            return

        # 创建报告内容
        report = []
        report.append("# 类型安全修复进度报告\n")
        report.append(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 进度表格
        report.append("## 📊 修复进度\n")
        report.append("| 时间 | ANN401 | MyPy错误 | 警告 |")
        report.append("|------|--------|----------|------|")

        for stats in history[-10:]:  # 最近10条记录
            time = stats["timestamp"][:10]
            report.append(
                f"| {time} | {stats['ann401_count']:,} | {stats['total_mypy_errors']:,} | {stats['total_warnings']:,} |"
            )

        # 统计图表
        report.append("\n## 📈 统计图表\n")

        # 计算总体进度
        if len(history) > 1:
            first = history[0]
            current = history[-1]

            ann401_progress = (
                (first["ann401_count"] - current["ann401_count"]) / first["ann401_count"] * 100
                if first["ann401_count"] > 0
                else 100
            )
            errors_progress = (
                (first["total_mypy_errors"] - current["total_mypy_errors"])
                / first["total_mypy_errors"]
                * 100
                if first["total_mypy_errors"] > 0
                else 100
            )

            report.append(f"- ANN401 修复进度: {ann401_progress:.1f}%")
            report.append(f"- MyPy错误修复进度: {errors_progress:.1f}%")

        # 错误类型分析
        if history:
            latest = history[-1]
            if latest["error_types"]:
                report.append("\n## 🏷️ 错误类型分析\n")
                for error_type, count in sorted(
                    latest["error_types"].items(), key=lambda x: x[1], reverse=True
                ):
                    report.append(f"- **{error_type}**: {count:,} 个")

        # 写入文件
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report))

        print(f"\n📝 报告已生成: {self.report_file}")

    def show_batch_status(self):
        """显示批次处理状态"""
        print("\n📦 批次处理状态:")

        # ANN401 批次
        ann401_dir = Path("ann401_batches")
        if ann401_dir.exists():
            latest = sorted(ann401_dir.glob("*"))[-1] if ann401_dir.glob("*") else None
            if latest:
                print(f"   ANN401: {latest.name}")

        # MyPy 批次
        mypy_dir = Path("mypy_batches")
        if mypy_dir.exists():
            latest = sorted(mypy_dir.glob("*"))[-1] if mypy_dir.glob("*") else None
            if latest:
                print(f"   MyPy: {latest.name}")

    def main(self):
        """主函数"""
        # 获取当前统计
        stats = self.get_current_stats()

        # 加载历史
        history = self.load_history()

        # 计算趋势
        trend = self.calculate_trend(history) if history else {"ann401_trend": 0, "errors_trend": 0}

        # 保存进度
        self.save_progress(stats)

        # 打印摘要
        self.print_summary(stats, trend)

        # 显示批次状态
        self.show_batch_status()

        # 生成报告
        self.generate_report(history)

        # 提示
        if stats["ann401_count"] > 0 or stats["total_mypy_errors"] > 0:
            print("\n💡 提示:")
            print("  - 运行 './scripts/fix_ann401_batch.sh' 开始修复 ANN401")
            print("  - 运行 './scripts/fix_mypy_batch.sh attr-defined' 修复属性错误")
            print("  - 查看详细报告: cat type_fix_report.md")


if __name__ == "__main__":
    # 支持命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("用法: python scripts/track_type_fixes.py [选项]")
            print("选项:")
            print("  --help     显示帮助")
            print("  --report   只生成报告")
            print("  --reset    重置进度文件")
            sys.exit(0)
        elif sys.argv[1] == "--report":
            tracker = TypeFixTracker()
            history = tracker.load_history()
            tracker.generate_report(history)
            sys.exit(0)
        elif sys.argv[1] == "--reset":
            Path(PROGRESS_FILE).unlink(missing_ok=True)
            Path(REPORT_FILE).unlink(missing_ok=True)
            print("进度文件已重置")
            sys.exit(0)

    # 正常运行
    tracker = TypeFixTracker()
    tracker.main()
