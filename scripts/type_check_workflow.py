#!/usr/bin/env python3
"""
类型检查工作流
Type Checking Workflow

自动化类型检查、报告和跟踪的脚本。
"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class TypeChecker:
    """类型检查器"""

    def __init__(self, project_root: str = "."):
        """初始化类型检查器

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.report_dir = self.project_root / "reports" / "type-checking"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_mypy(self, full_check: bool = False) -> Dict[str, any]:
        """运行 MyPy 类型检查

        Args:
            full_check: 是否运行完整检查

        Returns:
            检查结果
        """
        cmd = ["mypy", "src/"]
        if not full_check:
            cmd.append("--no-error-summary")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

        # 解析输出
        errors = []
        warnings = []
        for line in result.stdout.split("\n"):
            if ": error:" in line:
                errors.append(line)
            elif ": note:" in line or ": warning:" in line:
                warnings.append(line)

        return {
            "success": result.returncode == 0,
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def generate_report(self, results: Dict[str, any]) -> str:
        """生成类型检查报告

        Args:
            results: MyPy 检查结果

        Returns:
            报告文件路径
        """
        timestamp = datetime.now().isoformat()
        report_file = self.report_dir / f"type_check_{timestamp.replace(':', '-')}.json"

        # 按文件分组错误
        errors_by_file = {}
        for error in results["errors"]:
            if ":" in error:
                file_path = error.split(":")[0]
                if file_path not in errors_by_file:
                    errors_by_file[file_path] = []
                errors_by_file[file_path].append(error)

        # 创建报告
        report = {
            "timestamp": timestamp,
            "summary": {
                "total_errors": results["error_count"],
                "total_warnings": results["warning_count"],
                "success": results["success"],
            },
            "errors_by_file": errors_by_file,
            "top_error_files": sorted(
                [(f, len(e)) for f, e in errors_by_file.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "error_types": self._analyze_error_types(results["errors"]),
        }

        # 保存报告
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        return str(report_file)

    def _analyze_error_types(self, errors: List[str]) -> Dict[str, int]:
        """分析错误类型分布

        Args:
            errors: 错误列表

        Returns:
            错误类型统计
        """
        error_types = {}
        for error in errors:
            if "[" in error and "]" in error:
                error_code = error.split("[")[1].split("]")[0]
                error_types[error_code] = error_types.get(error_code, 0) + 1
        return error_types

    def check_improvement(self) -> Dict[str, any]:
        """检查改进情况

        Returns:
            改进报告
        """
        # 获取最近的报告
        reports = sorted(self.report_dir.glob("type_check_*.json"))
        if len(reports) < 2:
            return {"message": "需要至少两个报告进行比较"}

        # 读取最近的两个报告
        with open(reports[-1]) as f:
            latest = json.load(f)
        with open(reports[-2]) as f:
            previous = json.load(f)

        # 计算改进
        error_diff = previous["summary"]["total_errors"] - latest["summary"]["total_errors"]
        warning_diff = previous["summary"]["total_warnings"] - latest["summary"]["total_warnings"]

        return {
            "previous_timestamp": previous["timestamp"],
            "latest_timestamp": latest["timestamp"],
            "error_improvement": error_diff,
            "warning_improvement": warning_diff,
            "total_errors": latest["summary"]["total_errors"],
            "total_warnings": latest["summary"]["total_warnings"],
        }

    def create_dashboard(self) -> str:
        """创建类型检查仪表板

        Returns:
            仪表板文件路径
        """
        dashboard_file = self.report_dir / "dashboard.html"

        # 读取最新报告
        reports = sorted(self.report_dir.glob("type_check_*.json"))
        if not reports:
            return "No reports found"

        with open(reports[-1]) as f:
            latest_report = json.load(f)

        # 生成 HTML 报告
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Type Checking Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; }}
        .metric-label {{ color: #666; }}
        .error-list {{ max-height: 500px; overflow-y: auto; }}
        .error-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .error-file {{ font-weight: bold; color: #d32f2f; }}
        .improvement {{ color: { 'green' if latest_report['summary']['total_errors'] < 50 else 'red' }; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Type Checking Dashboard</h1>
        <p>Generated at: {latest_report['timestamp']}</p>
    </div>

    <div class="summary">
        <div class="metric">
            <div class="metric-value {latest_report['summary']['total_errors']}">{latest_report['summary']['total_errors']}</div>
            <div class="metric-label">Total Errors</div>
        </div>
        <div class="metric">
            <div class="metric-value">{latest_report['summary']['total_warnings']}</div>
            <div class="metric-label">Total Warnings</div>
        </div>
        <div class="metric">
            <div class="metric-value improvement">{len(latest_report['errors_by_file'])}</div>
            <div class="metric-label">Files with Errors</div>
        </div>
    </div>

    <h2>Top Error Files</h2>
    <div class="error-list">
        {"".join([f'<div class="error-item"><span class="error-file">{file}</span>: {count} errors</div>'
                  for file, count in latest_report['top_error_files']])}
    </div>

    <h2>Error Types</h2>
    <div class="error-list">
        {"".join([f'<div class="error-item">{error_type}: {count}</div>'
                  for error_type, count in latest_report['error_types'].items()])}
    </div>

    <script>
        // 自动刷新
        setTimeout(() => location.reload(), 300000); // 5分钟刷新
    </script>
</body>
</html>
        """

        with open(dashboard_file, "w") as f:
            f.write(html_content)

        return str(dashboard_file)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="类型检查工作流")
    parser.add_argument("--full", action="store_true", help="运行完整检查")
    parser.add_argument("--dashboard", action="store_true", help="生成仪表板")
    parser.add_argument("--improvement", action="store_true", help="检查改进情况")
    args = parser.parse_args()

    checker = TypeChecker()

    if args.improvement:
        improvement = checker.check_improvement()
        print("\n=== 改进报告 ===")
        print(f"错误改进: {improvement['error_improvement']:+d}")
        print(f"警告改进: {improvement['warning_improvement']:+d}")
        print(f"当前错误: {improvement['total_errors']}")
        print(f"当前警告: {improvement['total_warnings']}")
    else:
        # 运行类型检查
        print("运行 MyPy 类型检查...")
        results = checker.run_mypy(full_check=args.full)

        # 生成报告
        report_file = checker.generate_report(results)
        print(f"\n报告已生成: {report_file}")
        print(f"错误数: {results['error_count']}")
        print(f"警告数: {results['warning_count']}")

        # 生成仪表板
        dashboard_file = checker.create_dashboard()
        print(f"仪表板已生成: {dashboard_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
