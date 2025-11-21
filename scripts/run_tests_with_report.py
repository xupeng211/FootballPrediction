#!/usr/bin/env python3
"""
统一测试运行和报告生成脚本
Unified Test Runner and Report Generator

功能：
- 运行所有测试并生成统一报告
- 集成覆盖率分析
- 输出多种格式的报告
- 支持不同测试标记组合
- 使用coverage.json作为输入进行分析
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, List, Any, Optional
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestRunner:
    """统一测试运行器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_file = project_root / "coverage.json"
        self.report_dir = project_root / "test_reports"
        self.report_dir.mkdir(exist_ok=True)

    def run_tests(self, test_markers: Optional[str] = None,
                  test_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行测试并收集结果"""
        logger.info("Starting test execution...")

        # 构建pytest命令
        cmd = [
            "python", "-m", "pytest",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--tb=short",
            "--maxfail=20",
            "-v"
        ]

        if test_markers:
            cmd.extend(["-m", test_markers])

        if test_paths:
            cmd.extend(test_paths)
        else:
            cmd.append("tests/")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return {
                "success": False,
                "stdout": "",
                "stderr": "Test execution timed out after 10 minutes",
                "returncode": -1
            }

    def load_coverage_data(self) -> Optional[Dict[str, Any]]:
        """加载覆盖率数据"""
        if not self.coverage_file.exists():
            logger.warning(f"Coverage file not found: {self.coverage_file}")
            return None

        try:
            with open(self.coverage_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load coverage data: {e}")
            return None

    def analyze_coverage_gaps(self, coverage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析覆盖率缺口"""
        gaps = []
        files = coverage_data.get('files', {})

        for file_path, file_info in files.items():
            if not file_path.startswith('src/'):
                continue

            summary = file_info.get('summary', {})
            total_lines = summary.get('num_statements', 0)
            covered_lines = summary.get('covered_lines', 0)
            uncovered_lines = total_lines - covered_lines

            if uncovered_lines > 50:  # 关注未覆盖超过50行的文件
                gaps.append({
                    "file_path": file_path,
                    "uncovered_lines": uncovered_lines,
                    "total_lines": total_lines,
                    "coverage_percent": round((covered_lines / total_lines * 100), 2) if total_lines > 0 else 0,
                    "missing_lines": file_info.get('missing_lines', [])[:10]  # 只显示前10个缺失行
                })

        # 按未覆盖行数排序
        gaps.sort(key=lambda x: x['uncovered_lines'], reverse=True)
        return gaps

    def generate_test_report(self, test_results: Dict[str, Any],
                           coverage_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成统一测试报告"""
        timestamp = datetime.now().isoformat()

        report = {
            "metadata": {
                "timestamp": timestamp,
                "test_runner_version": "1.0",
                "project_root": str(self.project_root)
            },
            "test_results": test_results,
            "coverage_analysis": {}
        }

        if coverage_data:
            totals = coverage_data.get('totals', {})
            report["coverage_analysis"] = {
                "overall_coverage": round(totals.get('percent_covered', 0), 2),
                "total_statements": totals.get('num_statements', 0),
                "covered_lines": totals.get('covered_lines', 0),
                "missing_lines": totals.get('missing_lines', 0),
                "coverage_gaps": self.analyze_coverage_gaps(coverage_data)[:20]  # Top 20 gaps
            }

        return report

    def save_report(self, report: Dict[str, Any], format_type: str = "json"):
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "json":
            report_file = self.report_dir / f"test_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON report saved to: {report_file}")

        elif format_type == "markdown":
            report_file = self.report_dir / f"test_report_{timestamp}.md"
            self._save_markdown_report(report, report_file)
            logger.info(f"Markdown report saved to: {report_file}")

    def _save_markdown_report(self, report: Dict[str, Any], report_file: Path):
        """保存Markdown格式报告"""
        md_content = self._generate_markdown_content(report)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

    def _generate_markdown_content(self, report: Dict[str, Any]) -> str:
        """生成Markdown内容"""
        test_results = report["test_results"]
        coverage = report.get("coverage_analysis", {})

        content = f"""# 测试执行报告

## 基本信息
- **执行时间**: {report["metadata"]["timestamp"]}
- **测试状态": {"✅ 成功" if test_results["success"] else "❌ 失败"}
- **返回码**: {test_results["returncode"]}

## 覆盖率概览
"""

        if coverage:
            content += f"""
- **整体覆盖率**: {coverage["overall_coverage"]}%
- **总语句数**: {coverage["total_statements"]}
- **覆盖行数**: {coverage["covered_lines"]}
- **未覆盖行数**: {coverage["missing_lines"]}

## 覆盖率缺口 Top 10

| 排名 | 文件 | 未覆盖行数 | 覆盖率 |
|------|------|-----------|--------|
"""

            gaps = coverage.get("coverage_gaps", [])[:10]
            for i, gap in enumerate(gaps, 1):
                content += f"| {i} | `{gap['file_path']}` | {gap['uncovered_lines']} | {gap['coverage_percent']}% |\n"

        content += f"""
## 测试输出

```
{test_results['stdout']}
```

## 错误信息（如有）

```
{test_results['stderr']}
```

---
*报告由 run_tests_with_report.py 自动生成*
"""
        return content

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="统一测试运行和报告生成")
    parser.add_argument("--markers", "-m", help="pytest标记")
    parser.add_argument("--paths", "-p", nargs="*", help="测试路径")
    parser.add_argument("--format", choices=["json", "markdown", "both"],
                       default="both", help="报告格式")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)

    # 运行测试
    test_results = runner.run_tests(args.markers, args.paths)

    # 加载覆盖率数据
    coverage_data = runner.load_coverage_data()

    # 生成报告
    report = runner.generate_test_report(test_results, coverage_data)

    # 保存报告
    if args.format in ["json", "both"]:
        runner.save_report(report, "json")
    if args.format in ["markdown", "both"]:
        runner.save_report(report, "markdown")

    # 设置退出码
    sys.exit(0 if test_results["success"] else 1)

if __name__ == "__main__":
    main()