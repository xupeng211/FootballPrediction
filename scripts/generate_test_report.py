#!/usr/bin/env python3
"""
测试报告生成器 - M2-P1-05
Test Report Generator

功能:
1. 优化测试报告生成和格式化
2. 多格式报告支持 (HTML, JSON, Markdown)
3. 测试执行时间监控
4. 历史数据对比
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import jinja2


@dataclass
class TestSuiteResult:
    """测试套件结果"""
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    time: float
    timestamp: str


@dataclass
class TestCaseResult:
    """测试用例结果"""
    name: str
    classname: str
    time: float
    status: str  # passed, failed, error, skipped
    failure_message: str | None = None
    error_message: str | None = None


@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    execution_time: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    success_rate: float
    test_suites: list[TestSuiteResult]
    test_cases: list[TestCaseResult]
    coverage_data: dict[str, Any] | None = None


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.template_dir = self.project_root / "templates"
        self.output_dir = self.project_root / "test_reports"
        self.junit_file = self.project_root / "test_results.xml"
        self.coverage_file = self.project_root / "coverage.json"

        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)
        self.template_dir.mkdir(exist_ok=True)

    def create_default_templates(self):
        """创建默认的HTML模板"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {{ timestamp }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,
    0,
    0,
    0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit,
    minmax(200px,
    1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: linear-gradient(135deg,
    #667eea 0%,
    #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; font-size: 1.2em; }
        .summary-card .number { font-size: 2.5em; font-weight: bold; }
        .success { background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); }
        .warning { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); }
        .danger { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); }
        .info { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
        .section { margin-bottom: 30px; }
        .section h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .status-passed { color: #28a745; }
        .status-failed { color: #dc3545; }
        .status-error { color: #fd7e14; }
        .status-skipped { color: #6c757d; }
        .progress-bar { width: 100%; height: 20px; background-color: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg,
    #28a745,
    #20c997); transition: width 0.3s ease; }
        .chart-container { margin: 20px 0; text-align: center; }
        .pie-chart { width: 200px; height: 200px; margin: 0 auto; position: relative; }
        .pie-slice { position: absolute; width: 100%; height: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 测试报告</h1>
            <p>生成时间: {{ timestamp }}</p>
        </div>

        <div class="summary">
            <div class="summary-card success">
                <h3>✅ 通过</h3>
                <div class="number">{{ passed_tests }}</div>
            </div>
            <div class="summary-card danger">
                <h3>❌ 失败</h3>
                <div class="number">{{ failed_tests }}</div>
            </div>
            <div class="summary-card warning">
                <h3>⚠️ 错误</h3>
                <div class="number">{{ error_tests }}</div>
            </div>
            <div class="summary-card info">
                <h3>⏭️ 跳过</h3>
                <div class="number">{{ skipped_tests }}</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 测试统计</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ success_rate }}%"></div>
            </div>
    <p><strong>成功率:</strong> {{ success_rate }}% | <strong>总测试数:</strong> {{ total_tests }} | <strong>执行时间:</strong> {{ execution_time }}s</p>;
        </div>

        {% if coverage_data %}
        <div class="section">
            <h2>📈 覆盖率统计</h2>
            <p><strong>总体覆盖率:</strong> {{ coverage_data.total_coverage }}%</p>
            <div class="progress-bar">
    <div class="progress-fill" style="width: {{ coverage_data.total_coverage }}%"></div>;
            </div>
        </div>
        {% endif %}

        <div class="section">
            <h2>📋 测试套件详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>测试套件</th>
                        <th>总数</th>
                        <th>通过</th>
                        <th>失败</th>
                        <th>错误</th>
                        <th>跳过</th>
                        <th>耗时(s)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for suite in test_suites %}
                    <tr>
                        <td>{{ suite.name }}</td>
                        <td>{{ suite.tests }}</td>
                        <td class="status-passed">{{ suite.tests - suite.failures - suite.errors - suite.skipped }}</td>
                        <td class="status-failed">{{ suite.failures }}</td>
                        <td class="status-error">{{ suite.errors }}</td>
                        <td class="status-skipped">{{ suite.skipped }}</td>
                        <td>{{ suite.time | round(2) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        {% if failed_cases %}
        <div class="section">
            <h2>❌ 失败的测试用例</h2>
            <table>
                <thead>
                    <tr>
                        <th>测试用例</th>
                        <th>类名</th>
                        <th>状态</th>
                        <th>错误信息</th>
                    </tr>
                </thead>
                <tbody>
                    {% for case in failed_cases %}
                    <tr>
                        <td>{{ case.name }}</td>
                        <td>{{ case.classname }}</td>
                        <td class="status-{{ case.status }}">{{ case.status }}</td>
                        <td>{{ case.failure_message or case.error_message or 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}
    </div>
</body>
</html>
        """

        # 保存HTML模板
        template_file = self.template_dir / "test_report.html"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(html_template)


    def parse_junit_xml(self) -> dict[str, Any] | None:
        """解析JUnit XML结果"""
        if not self.junit_file.exists():
            return None

        try:
            tree = ET.parse(self.junit_file)
            root = tree.getroot()

            test_suites = []
            test_cases = []
            total_tests = 0
            total_failures = 0
            total_errors = 0
            total_skipped = 0
            total_time = 0.0

            for testsuite in root.findall("testsuite"):
                suite_name = testsuite.get("name", "Unknown")
                tests = int(testsuite.get("tests", 0))
                failures = int(testsuite.get("failures", 0))
                errors = int(testsuite.get("errors", 0))
                skipped = int(testsuite.get("skipped", 0))
                time = float(testsuite.get("time", 0))

                suite_result = TestSuiteResult(
                    name=suite_name,
                    tests=tests,
                    failures=failures,
                    errors=errors,
                    skipped=skipped,
                    time=time,
                    timestamp=datetime.now().isoformat()
                )
                test_suites.append(suite_result)

                total_tests += tests
                total_failures += failures
                total_errors += errors
                total_skipped += skipped
                total_time += time

                # 解析测试用例
                for testcase in testsuite.findall("testcase"):
                    case_name = testcase.get("name", "")
                    classname = testcase.get("classname", "")
                    case_time = float(testcase.get("time", 0))

                    # 确定测试状态
                    failure_elem = testcase.find("failure")
                    error_elem = testcase.find("error")
                    skipped_elem = testcase.find("skipped")

                    if failure_elem is not None:
                        status = "failed"
                        failure_message = failure_elem.get("message", "")
                        error_message = None
                    elif error_elem is not None:
                        status = "error"
                        failure_message = None
                        error_message = error_elem.get("message", "")
                    elif skipped_elem is not None:
                        status = "skipped"
                        failure_message = None
                        error_message = None
                    else:
                        status = "passed"
                        failure_message = None
                        error_message = None

                    case_result = TestCaseResult(
                        name=case_name,
                        classname=classname,
                        time=case_time,
                        status=status,
                        failure_message=failure_message,
                        error_message=error_message
                    )
                    test_cases.append(case_result)

            return {
                "test_suites": test_suites,
                "test_cases": test_cases,
                "total_tests": total_tests,
                "failed_tests": total_failures,
                "error_tests": total_errors,
                "skipped_tests": total_skipped,
                "total_time": total_time
            }

        except Exception:
            return None

    def load_coverage_data(self) -> dict[str, Any] | None:
        """加载覆盖率数据"""
        if not self.coverage_file.exists():
            return None

        try:
            with open(self.coverage_file, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def generate_report(self) -> TestReport:
        """生成测试报告"""

        # 解析JUnit XML
        junit_data = self.parse_junit_xml()
        if not junit_data:
            raise Exception("无法解析测试结果")

        # 加载覆盖率数据
        coverage_data = self.load_coverage_data()

        # 计算统计数据
        total_tests = junit_data["total_tests"]
        failed_tests = junit_data["failed_tests"]
        error_tests = junit_data["error_tests"]
        skipped_tests = junit_data["skipped_tests"]
        passed_tests = total_tests - failed_tests - error_tests - skipped_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # 创建报告
        report = TestReport(
            timestamp=datetime.now().isoformat(),
            execution_time=junit_data["total_time"],
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            success_rate=success_rate,
            test_suites=junit_data["test_suites"],
            test_cases=junit_data["test_cases"],
            coverage_data=coverage_data
        )

        return report

    def save_json_report(self, report: TestReport):
        """保存JSON格式报告"""
        report_data = asdict(report)
        json_file = self.output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return json_file

    def generate_html_report(self, report: TestReport):
        """生成HTML格式报告"""
        # 确保模板存在
        if not (self.template_dir / "test_report.html").exists():
            self.create_default_templates()

        # 准备模板数据
        template_data = {
            "timestamp": report.timestamp[:19],
            "execution_time": round(report.execution_time, 2),
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "error_tests": report.error_tests,
            "skipped_tests": report.skipped_tests,
            "success_rate": round(report.success_rate, 1),
            "test_suites": report.test_suites,
            "test_cases": report.test_cases,
            "failed_cases": [case for case in report.test_cases if case.status in ["failed", "error"]],
            "coverage_data": report.coverage_data
        }

        # 如果有覆盖率数据，添加到模板数据
        if report.coverage_data:
            coverage_data = report.coverage_data.get("totals", {})
            template_data["coverage_data"] = {
                "total_coverage": round(coverage_data.get("percent_covered", 0), 1)
            }

        # 渲染HTML
        try:
            template_loader = jinja2.FileSystemLoader(searchpath=str(self.template_dir))
            template_env = jinja2.Environment(loader=template_loader)
            template = template_env.get_template("test_report.html")

            html_content = template.render(**template_data)

            # 保存HTML报告
            html_file = self.output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            return html_file

        except Exception:
            return None

    def generate_markdown_report(self, report: TestReport):
        """生成Markdown格式报告"""
        markdown_lines = [
            "# 🧪 测试报告",
            "",
            f"**生成时间**: {report.timestamp[:19]}",
            "",
            "## 📊 测试统计",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总测试数 | {report.total_tests} |",
            f"| 通过 | {report.passed_tests} |",
            f"| 失败 | {report.failed_tests} |",
            f"| 错误 | {report.error_tests} |",
            f"| 跳过 | {report.skipped_tests} |",
            f"| 成功率 | {report.success_rate:.1f}% |",
            f"| 执行时间 | {report.execution_time:.2f}s |",
            "",
            "## 📈 进度",
            "",
            f"![Progress](https://progress-bar.dev/{int(report.success_rate)}?scale=100&title=Success%20Rate)",


            ""
        ]

        # 添加覆盖率信息
        if report.coverage_data:
            coverage_totals = report.coverage_data.get("totals", {})
            coverage_percent = coverage_totals.get("percent_covered", 0)
            markdown_lines.extend([
                "## 📊 覆盖率",
                "",
                f"- **总体覆盖率**: {coverage_percent:.1f}%",
                f"- **已覆盖语句**: {coverage_totals.get('covered_lines', 0)}",
                f"- **总语句数**: {coverage_totals.get('num_statements', 0)}",
                ""
            ])

        # 添加测试套件详情
        if report.test_suites:
            markdown_lines.extend([
                "## 📋 测试套件详情",
                "",
                "| 套件名称 | 总数 | 通过 | 失败 | 错误 | 跳过 | 耗时(s) |",
                "|----------|------|------|------|------|------|----------|"
            ])

            for suite in report.test_suites:
                passed = suite.tests - suite.failures - suite.errors - suite.skipped
                markdown_lines.append(
                    f"| {suite.name} | {suite.tests} | {passed} | {suite.failures} | "
                    f"{suite.errors} | {suite.skipped} | {suite.time:.2f} |"
                )
            markdown_lines.append("")

        # 添加失败的测试用例
        failed_cases = [case for case in report.test_cases if case.status in ["failed", "error"]]
        if failed_cases:
            markdown_lines.extend([
                "## ❌ 失败的测试用例",
                "",
                "| 测试用例 | 类名 | 状态 | 错误信息 |",
                "|----------|------|------|----------|"
            ])

            for case in failed_cases[:10]:  # 只显示前10个
                error_msg = case.failure_message or case.error_message or "N/A"
                error_msg = error_msg.replace("\n", " ")[:100]  # 限制长度并换行处理
                markdown_lines.append(
                    f"| `{case.name}` | `{case.classname}` | {case.status} | {error_msg} |"
                )
            markdown_lines.append("")

        # 添加结论
        status = "✅ 通过" if report.failed_tests == 0 and report.error_tests == 0 else "❌ 失败"
        markdown_lines.extend([
            "## 🎯 结论",
            "",
            f"**状态**: {status}",
            f"**成功率**: {report.success_rate:.1f}%",
            ""
        ])

        # 保存Markdown报告
        markdown_content = "\n".join(markdown_lines)
        markdown_file = self.output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return markdown_file

    def generate_report_summary(self, report: TestReport):
        """生成报告摘要"""

        if report.coverage_data:
            coverage_totals = report.coverage_data.get("totals", {})
            coverage_totals.get("percent_covered", 0)

        if report.test_suites:
            for suite in report.test_suites:
                suite.tests - suite.failures - suite.errors - suite.skipped

        failed_count = report.failed_tests + report.error_tests
        if failed_count > 0:
            pass



def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试报告生成器")
    parser.add_argument("--format",
    choices=["all",
    "json",
    "html",
    "markdown"],
    default="all",
    help="报告格式")
    parser.add_argument("--output-dir", help="输出目录 (默认: test_reports)")
    parser.add_argument("--junit-file", help="JUnit XML文件路径 (默认: test_results.xml)")
    parser.add_argument("--coverage-file", help="覆盖率JSON文件路径 (默认: coverage.json)")

    args = parser.parse_args()

    # 创建报告生成器
    generator = TestReportGenerator()

    # 设置自定义路径
    if args.output_dir:
        generator.output_dir = Path(args.output_dir)
        generator.output_dir.mkdir(exist_ok=True)

    if args.junit_file:
        generator.junit_file = Path(args.junit_file)

    if args.coverage_file:
        generator.coverage_file = Path(args.coverage_file)

    try:
        # 生成报告
        report = generator.generate_report()

        # 打印摘要
        generator.generate_report_summary(report)

        # 保存不同格式的报告
        if args.format in ["all", "json"]:
            generator.save_json_report(report)

        if args.format in ["all", "html"]:
            generator.generate_html_report(report)

        if args.format in ["all", "markdown"]:
            generator.generate_markdown_report(report)


        # 返回状态
        return 0 if report.failed_tests == 0 and report.error_tests == 0 else 1

    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
