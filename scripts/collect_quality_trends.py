#!/usr/bin/env python3
"""
Quality Trends Collector for Football Prediction Project
Phase 6: Long-term Optimization - Quality Monitoring

This script automatically collects quality metrics and generates trend reports.
Usage: python scripts/collect_quality_trends.py
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import re

class QualityTrendsCollector:
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.reports_dir = self.project_root / "docs" / "_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def run_command(self, cmd: list, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout
            )
            return result
        except subprocess.TimeoutExpired:
            print(f"Command timed out: {' '.join(cmd)}")
            return None
        except Exception as e:
            print(f"Error running command {' '.join(cmd)}: {e}")
            return None

    def collect_ruff_stats(self) -> dict:
        """Collect Ruff statistics."""
        print("📋 Collecting Ruff statistics...")

        # Run ruff check with statistics
        result = self.run_command(["ruff", "check", ".", "--statistics"])
        if not result or result.returncode != 0:
            return {"error": "Failed to run ruff check", "output": result.stderr if result else "No output"}

        # Parse ruff output
        stats = {"total_errors": 0, "error_types": {}, "files": []}

        # Extract total error count
        total_match = re.search(r'(\d+)\s+error', result.stdout, re.IGNORECASE)
        if total_match:
            stats["total_errors"] = int(total_match.group(1))

        # Extract error breakdown by type
        lines = result.stdout.split('\n')
        for line in lines:
            if 'Found' in line and 'error' in line.lower():
                # Extract error codes like E999, F841, etc.
                error_codes = re.findall(r'\b[A-Z]\d{3}\b', line)
                for code in error_codes:
                    stats["error_types"][code] = stats["error_types"].get(code, 0) + 1

        # Get per-module statistics
        modules = ["src/services", "src/api", "src/monitoring", "tests/unit", "tests/integration", "tests/e2e"]
        for module in modules:
            if (self.project_root / module).exists():
                module_result = self.run_command(["ruff", "check", module, "--output-format=json"])
                if module_result and module_result.returncode == 0:
                    try:
                        module_errors = json.loads(module_result.stdout)
                        stats["files"].append({
                            "module": module,
                            "error_count": len(module_errors)
                        })
                    except json.JSONDecodeError:
                        stats["files"].append({
                            "module": module,
                            "error_count": 0,
                            "error": "Failed to parse JSON"
                        })
                else:
                    stats["files"].append({
                        "module": module,
                        "error_count": 0,
                        "error": "Command failed"
                    })

        return stats

    def collect_mypy_stats(self) -> dict:
        """Collect MyPy statistics."""
        print("🔍 Collecting MyPy statistics...")

        result = self.run_command(["mypy", "src", "tests", "--ignore-missing-imports", "--no-error-summary"])
        if result is None:
            return {"error": "MyPy command failed to run"}

        stats = {
            "total_errors": 0,
            "error_types": {},
            "status": "passed" if result.returncode == 0 else "failed"
        }

        if result.returncode != 0:
            # Parse MyPy errors
            lines = result.stderr.split('\n') + result.stdout.split('\n')
            for line in lines:
                if ':' in line and ('error:' in line or 'warning:' in line):
                    stats["total_errors"] += 1

                    # Extract error type
                    if 'error:' in line:
                        error_type = "type_error"
                    elif 'warning:' in line:
                        error_type = "warning"
                    else:
                        error_type = "other"

                    stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1

        return stats

    def collect_pytest_stats(self) -> dict:
        """Collect Pytest statistics."""
        print("🧪 Collecting Pytest statistics...")

        # Run pytest with quiet output and JSON reporting
        result = self.run_command([
            "pytest", "tests/unit", "-q", "--tb=no",
            "--json-report", "--json-report-file=/tmp/pytest_report.json"
        ])

        stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "pass_rate": 0.0,
            "status": "passed" if result.returncode == 0 else "failed"
        }

        # Parse pytest output if JSON report is available
        try:
            with open("/tmp/pytest_report.json", "r") as f:
                pytest_data = json.load(f)

            summary = pytest_data.get("summary", {})
            stats["total_tests"] = summary.get("total", 0)
            stats["passed"] = summary.get("passed", 0)
            stats["failed"] = summary.get("failed", 0)
            stats["skipped"] = summary.get("skipped", 0)
            stats["errors"] = summary.get("error", 0)

            if stats["total_tests"] > 0:
                stats["pass_rate"] = (stats["passed"] / stats["total_tests"]) * 100

        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            # Fallback to parsing text output
            if result:
                lines = result.stdout.split('\n') + result.stderr.split('\n')
                for line in lines:
                    if ' passed' in line and ' failed' in line:
                        # Parse output like "100 passed, 2 failed"
                        passed_match = re.search(r'(\d+)\s+passed', line)
                        failed_match = re.search(r'(\d+)\s+failed', line)

                        if passed_match:
                            stats["passed"] = int(passed_match.group(1))
                        if failed_match:
                            stats["failed"] = int(failed_match.group(1))

                        stats["total_tests"] = stats["passed"] + stats["failed"]
                        if stats["total_tests"] > 0:
                            stats["pass_rate"] = (stats["passed"] / stats["total_tests"]) * 100
                        break

        return stats

    def generate_trend_report(self, ruff_stats: dict, mypy_stats: dict, pytest_stats: dict) -> str:
        """Generate a comprehensive trend report."""
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename_date = datetime.now().strftime("%Y%m%d")

        report = f"""# Quality Trends Report - {date_str}

## 📊 Executive Summary

**Generated**: {date_str}
**Report Type**: Daily Quality Trends
**Phase**: 6 - Long-term Optimization

### 🎯 Key Metrics

| Metric | Current | Status | Trend |
|--------|---------|--------|-------|
| Ruff Errors | {ruff_stats.get('total_errors', 'N/A')} | {'🟢 Good' if ruff_stats.get('total_errors', 999) < 1000 else '🟡 Warning' if ruff_stats.get('total_errors', 999) < 5000 else '🔴 Critical'} | {'📈 Improving' if ruff_stats.get('total_errors', 999) < 1000 else '📉 Needs attention'} |
| MyPy Errors | {mypy_stats.get('total_errors', 'N/A')} | {'🟢 Passed' if mypy_stats.get('status') == 'passed' else '🔴 Failed'} | {'📈 Improving' if mypy_stats.get('status') == 'passed' else '📉 Needs attention'} |
| Test Pass Rate | {pytest_stats.get('pass_rate', 0):.1f}% | {'🟢 Good' if pytest_stats.get('pass_rate', 0) >= 95 else '🟡 Warning' if pytest_stats.get('pass_rate', 0) >= 80 else '🔴 Critical'} | {'📈 Improving' if pytest_stats.get('pass_rate', 0) >= 95 else '📉 Needs attention'} |

## 🔍 Detailed Analysis

### Ruff Static Analysis

**Total Errors**: {ruff_stats.get('total_errors', 'N/A')}

#### Error Breakdown by Type
"""

        if ruff_stats.get('error_types'):
            for error_code, count in sorted(ruff_stats['error_types'].items(), key=lambda x: x[1], reverse=True):
                report += f"- **{error_code}**: {count} errors\n"
        else:
            report += "No error types parsed or Ruff failed to run.\n"

        report += "\n#### Module-wise Error Distribution\n"

        if ruff_stats.get('files'):
            for file_info in ruff_stats['files']:
                module = file_info['module']
                errors = file_info['error_count']
                status = '🟢' if errors == 0 else '🟡' if errors < 100 else '🔴'
                report += f"- {status} **{module}**: {errors} errors\n"
        else:
            report += "Module statistics unavailable.\n"

        report += f"""
### MyPy Type Checking

**Status**: {mypy_stats.get('status', 'Unknown').title()}
**Total Errors**: {mypy_stats.get('total_errors', 'N/A')}

#### Error Types
"""

        if mypy_stats.get('error_types'):
            for error_type, count in mypy_stats['error_types'].items():
                report += f"- **{error_type}**: {count}\n"
        else:
            report += "No type errors detected or MyPy failed to run.\n"

        report += f"""
### Pytest Test Suite

**Status**: {pytest_stats.get('status', 'Unknown').title()}
**Total Tests**: {pytest_stats.get('total_tests', 'N/A')}
**Pass Rate**: {pytest_stats.get('pass_rate', 0):.1f}%

#### Test Results
- ✅ **Passed**: {pytest_stats.get('passed', 0)}
- ❌ **Failed**: {pytest_stats.get('failed', 0)}
- ⏭️ **Skipped**: {pytest_stats.get('skipped', 0)}
- 💥 **Errors**: {pytest_stats.get('errors', 0)}

## 📈 Trend Analysis

### Quality Gate Status
"""

        # Evaluate quality gates
        ruff_status = "PASS" if ruff_stats.get('total_errors', 999999) < 1000 else "FAIL"
        mypy_status = "PASS" if mypy_stats.get('status') == 'passed' else "FAIL"
        pytest_status = "PASS" if pytest_stats.get('pass_rate', 0) >= 95 else "FAIL"

        report += f"""
- **Ruff Quality Gate**: {ruff_status} (Target: < 1000 errors, Current: {ruff_stats.get('total_errors', 'N/A')})
- **MyPy Quality Gate**: {mypy_status} (Target: 0 errors, Current: {mypy_stats.get('total_errors', 'N/A')})
- **Pytest Quality Gate**: {pytest_status} (Target: ≥95% pass rate, Current: {pytest_stats.get('pass_rate', 0):.1f}%)

### Recommendations
"""

        recommendations = []

        if ruff_stats.get('total_errors', 0) > 1000:
            recommendations.append("🔴 **High Priority**: Ruff errors exceed 1000. Consider a focused cleanup sprint.")
        elif ruff_stats.get('total_errors', 0) > 500:
            recommendations.append("🟡 **Medium Priority**: Ruff errors trending high. Monitor and plan cleanup.")

        if mypy_stats.get('status') != 'passed':
            recommendations.append("🔴 **High Priority**: MyPy type checking failed. Fix type errors immediately.")

        if pytest_stats.get('pass_rate', 100) < 95:
            recommendations.append("🔴 **High Priority**: Test pass rate below 95%. Fix failing tests.")
        elif pytest_stats.get('pass_rate', 100) < 80:
            recommendations.append("🟡 **Medium Priority**: Test coverage could be improved.")

        if not recommendations:
            recommendations.append("🟢 **Good**: All quality gates passing. Maintain current standards.")

        for rec in recommendations:
            report += f"- {rec}\n"

        report += f"""
## 📋 Historical Context

This report is part of the Phase 6 Long-term Optimization initiative.
- **Collection Frequency**: Daily (via GitHub Actions nightly job)
- **Storage Location**: docs/_reports/RUFF_TREND_{filename_date}.md
- **Integration**: Automatically updates TASK_KANBAN.md with trends

## 🔗 Related Reports

- [QUALITY_IMPROVEMENT_PLAN.md](QUALITY_IMPROVEMENT_PLAN.md) - Quality targets and improvement roadmap
- [TASK_KANBAN.md](../TASK_KANBAN.md) - Project status and progress tracking
- [RUFF_FINAL_REPORT.md](RUFF_FINAL_REPORT.md) - Phase 4 global cleanup results

---

**Report generated by**: scripts/collect_quality_trends.py
**Generation time**: {date_str}
**Next scheduled run**: {datetime.now().strftime('%Y-%m-%d')} 02:00 UTC (Nightly GitHub Actions)
"""

        return report

    def save_report(self, report_content: str) -> str:
        """Save the trend report to file."""
        filename_date = datetime.now().strftime("%Y%m%d")
        report_path = self.reports_dir / f"RUFF_TREND_{filename_date}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"📄 Trend report saved to: {report_path}")
        return str(report_path)

    def update_kanban_status(self, report_path: str) -> None:
        """Update TASK_KANBAN.md with the latest trend information."""
        kanban_path = self.project_root / "docs" / "_reports" / "TASK_KANBAN.md"

        if not kanban_path.exists():
            print("⚠️ TASK_KANBAN.md not found, skipping update")
            return

        # Read current kanban content
        with open(kanban_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add trend update to Phase 6 section
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        trend_entry = f"""
**{date_str}** - 📊 **Daily Quality Trends Generated**
- **报告路径**: {os.path.relpath(report_path, self.project_root)}
- **状态**: 自动质量趋势监控已启用
- **下一步**: 持续监控质量指标，准备季度冲刺
"""

        # Find Phase 6 section and add entry
        phase6_pattern = r'(### Phase 6: 长期优化.*?)(\n---|\n##|$)'
        match = re.search(phase6_pattern, content, re.DOTALL)

        if match:
            # Add trend entry before the section end
            updated_content = content[:match.end(1)] + trend_entry + content[match.end(1):]

            with open(kanban_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            print("📋 TASK_KANBAN.md updated with trend information")
        else:
            print("⚠️ Phase 6 section not found in TASK_KANBAN.md")

def main():
    """Main execution function."""
    print("🚀 Starting Quality Trends Collection...")

    try:
        # Initialize collector
        collector = QualityTrendsCollector()

        # Collect statistics
        ruff_stats = collector.collect_ruff_stats()
        mypy_stats = collector.collect_mypy_stats()
        pytest_stats = collector.collect_pytest_stats()

        # Generate report
        report = collector.generate_trend_report(ruff_stats, mypy_stats, pytest_stats)

        # Save report
        report_path = collector.save_report(report)

        # Update kanban
        collector.update_kanban_status(report_path)

        print("✅ Quality trends collection completed successfully!")

    except Exception as e:
        print(f"❌ Error during quality trends collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()