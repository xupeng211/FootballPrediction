import os
"""""""
Test debt tracking and management system.

This module provides tools to identify, track, and manage test debt across the football prediction system.
"""""""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import re
import ast


class TestDebtTracker:
    """Tracks and manages test debt across the codebase."""""""

    def __init__(self, reports_dir = str "docs/_reports["):": self.reports_dir = Path(reports_dir)": self.reports_dir.mkdir(parents=True, exist_ok=True)": self.test_debt_file = self.reports_dir / "]TEST_DEBT_LOG.md[": self.debt_history_file = self.reports_dir / "]TEST_DEBT_HISTORY.md[": self.cleanup_schedule_file = self.reports_dir / "]TEST_CLEANUP_SCHEDULE.md[": def analyze_test_debt(self) -> Dict[str, Any]:""""
        "]""Analyze current test debt across the codebase."""""""
        print("🔍 Analyzing test debt...")": debt_analysis = {"""
            "timestamp[": datetime.now().isoformat(),""""
            "]untested_files[": self._find_untested_files(),""""
            "]low_coverage_files[": self._find_low_coverage_files(),""""
            "]failing_tests[": self._find_failing_tests(),""""
            "]flaky_tests[": self._find_flaky_tests(),""""
            "]slow_tests[": self._find_slow_tests(),""""
            "]missing_test_types[": self._find_missing_test_types(),""""
            "]quality_issues[": self._find_test_quality_issues(),""""
            "]summary[": {},""""
        }

        # Calculate summary metrics
        debt_analysis["]summary["] = self._calculate_debt_summary(debt_analysis)": return debt_analysis[": def _find_untested_files(self) -> List[Dict[str, Any]]:""
        "]]""Find Python files without corresponding test files."""""""
        untested_files = []
        src_dir = Path("src[")": for py_file in src_dir.rglob("]*.py["):": if py_file.name.startswith("]__["):": continue["""

            # Skip certain directories
            if any(part in py_file.parts for part in ["]]migrations[", "]__pycache__["]):": continue["""

            # Look for corresponding test file
            relative_path = py_file.relative_to("]]src[")": test_path = Path("]tests[") / relative_path[": test_path = test_path.with_name(f["]]test_{test_path.name}"])": if not test_path.exists():"""
                # Check for alternative test file patterns
                alt_test_patterns = [
                    Path("tests[")""""
                    / "]unit["""""
                    / relative_path.with_name(f["]test_{relative_path.name}"]),": Path("tests[")""""
                    / "]integration["""""
                    / relative_path.with_name(f["]test_{relative_path.name}"]),": Path("tests[") / f["]test_{relative_path.name}"],""""
                ]

                if not any(pattern.exists() for pattern in alt_test_patterns):
                    untested_files.append(
                        {
                            "file_path[": str(py_file),""""
                            "]relative_path[": str(relative_path),""""
                            "]size[": py_file.stat().st_size,""""
                            "]lines[": self._count_lines(py_file),""""
                            "]priority[": self._calculate_file_priority(py_file),""""
                        }
                    )

        return sorted(untested_files, key=lambda x x["]priority["], reverse=True)": def _find_low_coverage_files(self) -> List[Dict[str, Any]]:"""
        "]""Find files with low test coverage."""""""
        low_coverage_files = []

        try:
            # Run coverage analysis
            result = subprocess.run(
                ["pytest[", "]--cov = src[", "]--cov-report=jsoncoverage_analysis.json["],": capture_output=True,": text=True,": timeout=120,"
            )

            if result.returncode ==0
                with open("]coverage_analysis.json[", "]r[") as f:": coverage_data = json.load(f)": for file_path, file_data in coverage_data.get("]files[", {}).items():": if file_path.startswith("]src/"):": summary = file_data.get("summary[", {})": coverage_percent = summary.get("]percent_covered[", 0.0)": if coverage_percent < 80:  # Below threshold[": low_coverage_files.append(""
                                {
                                    "]]file_path[": file_path,""""
                                    "]coverage_percent[": coverage_percent,""""
                                    "]covered_lines[": summary.get("]covered_lines[", 0),""""
                                    "]total_lines[": summary.get("]num_statements[", 0),""""
                                    "]missing_lines[": summary.get("]missing_lines[", 0),""""
                                    "]priority[": (""""
                                        "]high[": if coverage_percent < 60 else "]medium["""""
                                    ),
                                }
                            )

            # Clean up temporary file
            if Path("]coverage_analysis.json[").exists():": Path("]coverage_analysis.json[").unlink()": except Exception as e:": print(f["]⚠️  Could not analyze coverage["]: [{e}])": return low_coverage_files[": def _find_failing_tests(self) -> List[Dict[str, Any]]:""
        "]]""Find currently failing tests."""""""
        failing_tests = []

        try = result subprocess.run(
                ["pytest[", "]--collect-only[", "]--quiet["],": capture_output=True,": text=True,": timeout=60,"
            )

            if result.returncode != 0:
                # Try to identify failing tests from error output
                error_lines = result.stderr.split("]\n[")": for line in error_lines:": if "]error[": in line.lower() and "]test_[": in line:": failing_tests.append("""
                            {
                                "]test_name[": line.strip(),""""
                                "]error_type[: "collection_error[","]"""
                                "]priority[: "high[","]"""
                            }
                        )

        except Exception as e:
            print(f["]⚠️  Could not analyze failing tests["]: [{e}])": return failing_tests[": def _find_flaky_tests(self) -> List[Dict[str, Any]]:""
        "]]""Identify potentially flaky tests (requires historical data)."""""""
        # This would require test execution history
        # For now, return empty list - would be implemented with test result tracking
        return []

    def _find_slow_tests(self) -> List[Dict[str, Any]]:
        """Find slow-running tests."""""""
        slow_tests = []

        try = result subprocess.run(
                ["pytest[", "]--durations=10["],": capture_output=True,": text=True,": timeout=180,"
            )

            output = result.stdout + result.stderr
            lines = output.split("]\n[")": in_durations = False[": for line in lines:": if "]]slowest durations[": in line.lower():": in_durations = True[": continue[": if in_durations and line.strip():"
                    if line.startswith("]]]=") or line.startswith("-"):": break["""

                    # Parse duration line
                    match = re.match(r["]([\d.]+s)\s+(.*)"], line)": if match = duration_str match.group(1)": test_name = match.group(2)": if "s[": in duration_str:": duration = float(duration_str.replace("]s[", "]"))": if duration > 2.0:  # Tests slower than 2 seconds[": slow_tests.append(""
                                    {
                                        "]test_name[": test_name,""""
                                        "]duration_seconds[": duration,""""
                                        "]priority[": (""""
                                            "]medium[": if duration < 5.0 else "]high["""""
                                        ),
                                    }
                                )

        except Exception as e:
            print(f["]⚠️  Could not analyze slow tests["]: [{e}])": return slow_tests[": def _find_missing_test_types(self) -> List[Dict[str, Any]]:""
        "]]""Find missing test types (unit, integration, e2e)."""""""
        missing_types = []

        # Check for missing unit tests
        unit_test_files = list(Path("tests/unit[").rglob("]test_*.py["))": if len(unit_test_files) < 10:  # Arbitrary threshold[": missing_types.append(""
                {
                    "]]test_type[: "unit[","]"""
                    "]current_count[": len(unit_test_files),""""
                    "]recommended_minimum[": 10,""""
                    "]priority[: "high[","]"""
                }
            )

        # Check for missing integration tests
        integration_test_files = list(Path("]tests/integration[").rglob("]test_*.py["))": if len(integration_test_files) < 5:": missing_types.append(""
                {
                    "]test_type[: "integration[","]"""
                    "]current_count[": len(integration_test_files),""""
                    "]recommended_minimum[": 5,""""
                    "]priority[: "medium[","]"""
                }
            )

        # Check for missing e2e tests
        e2e_test_files = list(Path("]tests/e2e[").rglob("]test_*.py["))": if len(e2e_test_files) < 3:": missing_types.append(""
                {
                    "]test_type[: "e2e[","]"""
                    "]current_count[": len(e2e_test_files),""""
                    "]recommended_minimum[": 3,""""
                    "]priority[: "medium[","]"""
                }
            )

        return missing_types

    def _find_test_quality_issues(self) -> List[Dict[str, Any]]:
        "]""Find test quality issues in existing test files."""""""
        quality_issues = []

        test_files = list(Path("tests[").rglob("]test_*.py["))": for test_file in test_files:": try:": with open(test_file, "]r[", encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_178")) as f[": content = f.read()": issues = self._analyze_test_quality(content, test_file)": quality_issues.extend(issues)"

            except Exception as e:
                print(f["]]⚠️  Could not analyze {test_file}"]: [{e}])": return quality_issues[": def _analyze_test_quality(": self, content: str, file_path: Path"
    ) -> List[Dict[str, Any]]:
        "]""Analyze quality issues in a single test file."""""""
        issues = []

        # Check for missing docstrings
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_["):": if not ast.get_docstring(node):": issues.append(""
                        {
                            "]file_path[": str(file_path),""""
                            "]issue_type[: "missing_docstring[","]"""
                            "]test_name[": node.name,""""
                            "]line_number[": node.lineno,""""
                            "]priority[: "low[","]"""
                            "]description[": f["]Test {node.name} missing docstring["],""""
                        }
                    )

        # Check for basic assert patterns
        if content.count("]assert ") < content.count("def test_[")" issues.append("""
                {
                    "]file_path[": str(file_path),""""
                    "]issue_type[: "insufficient_assertions[","]"""
                    "]description[: "May have insufficient assertions per test[","]"""
                    "]priority[: "medium[","]"""
                }
            )

        # Check for hardcoded values
        hardcoded_patterns = [
            r'assert\s+result\s*==\s*["]\']\w+["\']',": r["assert\s+len\(.+\)\s*==\s*\d+"],""""
        ]
        for pattern in hardcoded_patterns:
            if re.search(pattern, content):
                issues.append(
                    {
                        "file_path[": str(file_path),""""
                        "]issue_type[: "hardcoded_values[","]"""
                        "]description[: "Contains hardcoded test values[","]"""
                        "]priority[: "low[","]"""
                    }
                )
                break

        return issues

    def _count_lines(self, file_path: Path) -> int:
        "]""Count lines of code in a file."""""""
        try:
            with open(file_path, "r[", encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_178")) as f[": return len("""
                    [
                        line
                        for line in f
                        if line.strip() and not line.strip().startswith("]]#")""""
                    ]
                )
        except:
            return 0

    def _calculate_file_priority(self, file_path: Path) -> int:
        """Calculate priority for untested files."""""""
        priority = 1

        # Higher priority for core modules
        if any(part in str(file_path) for part in ["models[", "]services[", "]core["]):": priority += 3["""

        # Higher priority for larger files
        lines = self._count_lines(file_path)
        if lines > 200:
            priority += 2
        elif lines > 100:
            priority += 1

        return priority

    def _calculate_debt_summary(self, debt_analysis: Dict[str, Any]) -> Dict[str, Any]:
        "]]""Calculate summary metrics for test debt."""""""
        return {
            "untested_files_count[": len(debt_analysis["]untested_files["]),""""
            "]low_coverage_files_count[": len(debt_analysis["]low_coverage_files["]),""""
            "]failing_tests_count[": len(debt_analysis["]failing_tests["]),""""
            "]slow_tests_count[": len(debt_analysis["]slow_tests["]),""""
            "]quality_issues_count[": len(debt_analysis["]quality_issues["]),""""
            "]missing_test_types_count[": len(debt_analysis["]missing_test_types["]),""""
            "]total_debt_items[": (": len(debt_analysis["]untested_files["])""""
                + len(debt_analysis["]low_coverage_files["])""""
                + len(debt_analysis["]failing_tests["])""""
                + len(debt_analysis["]slow_tests["])""""
                + len(debt_analysis["]quality_issues["])""""
                + len(debt_analysis["]missing_test_types["])""""
            ),
            "]high_priority_items[": sum(""""
                1
                for item in (
                    debt_analysis["]untested_files["]""""
                    + debt_analysis["]low_coverage_files["]""""
                    + debt_analysis["]failing_tests["]""""
                    + debt_analysis["]slow_tests["]""""
                    + debt_analysis["]quality_issues["]""""
                    + debt_analysis["]missing_test_types["]""""
                )
                if item.get("]priority[") =="]high["""""
            ),
        }

    def generate_test_debt_report(self, debt_analysis: Dict[str, Any]) -> str:
        "]""Generate comprehensive test debt report."""""""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S[")": report_file = self.reports_dir / f["]TEST_DEBT_REPORT_{timestamp}.md["]: summary = debt_analysis["]summary["]": report_content = f["]"]"# 📋 Test Debt Report[""""

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Debt Items:** {summary['total_debt_items']}
**High Priority Items:** {summary['high_priority_items']}

## 📊 Executive Summary

- **Untested Files:** {summary['untested_files_count']}
- **Low Coverage Files:** {summary['low_coverage_files_count']}
- **Failing Tests:** {summary['failing_tests_count']}
- **Slow Tests:** {summary['slow_tests_count']}
- **Quality Issues:** {summary['quality_issues_count']}
- **Missing Test Types:** {summary['missing_test_types_count']}

## 🚨 High Priority Issues

### Untested Files (Priority 1-5)
"]""""""

        # Add high priority untested files
        high_priority_untested = [
            f for f in debt_analysis["untested_files["] if f["]priority["] >= 3[""""
        ]
        for file_info in high_priority_untested[:10]:  # Show top 10
            report_content += f["]]- **{file_info['relative_path']}** (Priority: {file_info['priority']}, Lines: {file_info['lines']})\n["]""""

        # Add low coverage files
        if debt_analysis["]low_coverage_files["]:": report_content += "]\n### Low Coverage Files (< 80%)\n[": for file_info in debt_analysis["]low_coverage_files["][:10]:": coverage_color = "]🔴": if file_info["coverage_percent["] < 60 else "]🟡": report_content += f["- {coverage_color} **{file_info['file_path']}** ({file_info['coverage_percent']:.1f}% coverage)\n["]"]"""

        # Add failing tests
        if debt_analysis["failing_tests["]:": report_content += "]\n### Failing Tests\n[": for test_info in debt_analysis["]failing_tests["]:": report_content += (": f["]- ❌ **{test_info['test_name']}** ({test_info['error_type']})\n["]""""
                )

        # Add slow tests
        if debt_analysis["]slow_tests["]:": report_content += "]\n### Slow Tests (> 2s)\n[": for test_info in debt_analysis["]slow_tests["]:": priority_icon = "]🔴": if test_info["priority["] =="]high[": else "]🟡": report_content += f["- {priority_icon} **{test_info['test_name']}** ({test_info['duration_seconds']:.1f}s)\n["]"]"""

        # Add missing test types
        if debt_analysis["missing_test_types["]:": report_content += "]\n### Missing Test Types\n[": for missing in debt_analysis["]missing_test_types["]:": report_content += f["]- ⚠️ **{missing['test_type'].title()} tests** (Current: {missing['current_count']}, Recommended: {missing['recommended_minimum']})\n["]""""

        # Add quality issues
        if debt_analysis["]quality_issues["]:": report_content += "]\n### Test Quality Issues\n[": for issue in debt_analysis["]quality_issues["][:15]:  # Show top 15[": priority_icon = ("""
                    "]]🔴": if issue["priority["] =="]high[": else "]🟡": if issue["priority["] =="]medium[": else "]🔵"""""
                )
                report_content += f["- {priority_icon} **{issue['issue_type'].replace('_', ' ').title()}** in {issue['file_path']}\n["]"]": report_content += f"""""""

## 📋 Detailed Analysis

### All Untested Files ({len(debt_analysis['untested_files'])})
| File | Lines | Priority | Action Required |
|------|-------|----------|-----------------|
"""""""

        for file_info in debt_analysis["untested_files["]:": priority_text = ("""
                "]High[": if file_info["]priority["] >= 3[": else "]]Medium[": if file_info["]priority["] >= 2 else "]Low["""""
            )
            report_content += f["]| {file_info['relative_path']} | {file_info['lines']} | {priority_text} | Create test file |\n["]: report_content += f["]"]"""""

## 🎯 Cleanup Recommendations

### Immediate Actions (Next Sprint)
1. **Create tests for high-priority untested files** ({len(high_priority_untested)} files)
2. **Fix failing tests** ({summary['failing_tests_count']} tests)
3. **Improve coverage for critical modules** ({len([f for f in debt_analysis['low_coverage_files'] if f['priority'] =='high'])} files)

### Medium-term Actions (Next Month)
1. **Optimize slow tests** ({len([t for t in debt_analysis['slow_tests'] if t['priority'] =='high'])} high priority)
2. **Add missing integration tests** ({len([t for t in debt_analysis['missing_test_types'] if t['test_type'] =='integration'])} missing)
3. **Address test quality issues** ({summary['quality_issues_count']} issues)

### Long-term Actions (Next Quarter)
1. **Establish test debt monitoring process**
2. **Set up automated test debt alerts**
3. **Implement test-driven development for new features**

## 📅 Cleanup Schedule

**Recommended Test Debt Cleanup Day:** First Friday of each month
**Estimated cleanup time:** {max(1, summary['high_priority_items'] // 2)} hours

### Monthly Cleanup Tasks
- [ ] Review and address high-priority untested files
- [ ] Fix any failing tests
- [ ] Improve test coverage for critical modules
- [ ] Address test quality issues
- [ ] Update test debt report

## 📈 Progress Tracking

- **Starting Debt:** {summary['total_debt_items']} items
- **High Priority:** {summary['high_priority_items']} items
- **Monthly Reduction Goal:** {max(1, summary['high_priority_items'] // 3)} high-priority items

---

*Report generated by Football Prediction Test Debt Tracker*
*Next scheduled cleanup: First Friday of next month*
"""""""

        with open(report_file, "w[", encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_178")) as f[": f.write(report_content)"""

        # Also update the main test debt log
        self._update_test_debt_log(debt_analysis)

        print(f["]]📄 Test debt report generated["]: [{report_file}])": return str(report_file)": def _update_test_debt_log(self, debt_analysis: Dict[str, Any]):""
        "]""Update the main test debt log file."""""""
        summary = debt_analysis["summary["]": log_content = f["]"]"# 📋 Test Debt Log[""""

*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Auto-generated by test debt tracking system*

## Current Status

- **Total Debt Items:** {summary['total_debt_items']}
- **High Priority:** {summary['high_priority_items']}
- **Untested Files:** {summary['untested_files_count']}
- **Low Coverage Files:** {summary['low_coverage_files_count']}
- **Failing Tests:** {summary['failing_tests_count']}

## Quick Actions

### High Priority ({summary['high_priority_items']} items)
"]""""""
        # Add high priority items
        high_priority_items = []

        for file_info in debt_analysis["untested_files["]:": if file_info["]priority["] >= 3:": high_priority_items.append(": f["]Create test for {file_info['relative_path']}"]""""
                )

        for file_info in debt_analysis["low_coverage_files["]:": if file_info["]priority["] =="]high[":": high_priority_items.append(": f["]Improve coverage for {file_info['file_path']}"]""""
                )

        for test_info in debt_analysis["failing_tests["]:": high_priority_items.append(f["]Fix test: {test_info['test_name']}"])": for i, action in enumerate(high_priority_items[:10], 1):": log_content += f["{i}. [ ] {action}\n["]"]": log_content += f"""""""

## Next Cleanup Day

**Date:** First Friday of next month
**Estimated Time:** {max(1, summary['high_priority_items'] // 2)} hours
**Focus Areas:**
- Untested core modules
- Failing tests
- Low coverage critical files

## Recent History

*See detailed reports in docs/_reports/TEST_DEBT_REPORT_YYYYMMDD_HHMMSS.md*

---

*This log is automatically updated. Manual changes may be overwritten.*
"""""""

        with open(self.test_debt_file, "w[", encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_178")) as f[": f.write(log_content)": def schedule_cleanup_reminder(self):""
        "]]""Create cleanup schedule and reminders."""""""
        schedule_content = f"""# 📅 Test Debt Cleanup Schedule[""""

*Generated: {datetime.now().strftime('%Y-%m-%d')}*

## Monthly Cleanup Day

**When:** First Friday of every month
**Time:** 2:00 PM - 4:00 PM (Team meeting time)
**Location:** Development team standup

## Cleanup Process

### 1. Preparation (Week Before)
- [ ] Run test debt analysis: `make test-debt-analysis`
- [ ] Review current debt report
- [ ] Identify top 5 high-priority items
- [ ] Assign owners to each item

### 2. Cleanup Day Activities
- [ ] 2:00-2:30 PM: Review debt status and priorities
- [ ] 2:30-3:30 PM: Work on assigned cleanup tasks
- [ ] 3:30-4:00 PM: Demo and review completed work

### 3. Follow-up (Week After)
- [ ] Update test debt report
- [ ] Document lessons learned
- [ ] Plan for next cleanup day

## Success Metrics

- **High-priority debt reduction:** ≥ 30% per month
- **Overall test coverage improvement:** ≥ 5% per quarter
- **Failing tests:** Always = 0
- **Test execution time:** ≤ 5 minutes for fast suite

## Monthly Goals

### Month 1 (Foundation)
- [ ] Eliminate all failing tests
- [ ] Create tests for 50% of high-priority untested files
- [ ] Improve coverage to 85% for critical modules

### Month 2 (Expansion)
- [ ] Create tests for remaining high-priority files
- [ ] Add integration tests for core workflows
- [ ] Implement performance benchmarking

### Month 3 (Optimization)
- [ ] Optimize slow tests
- [ ] Improve test quality and maintainability
- [ ] Establish continuous monitoring

## Quick Reference Commands

```bash
# Generate test debt report
make test-debt-analysis

# Run coverage analysis
make coverage-dashboard

# Run performance benchmarks
make benchmark-full

# Run mutation testing
make mutation-test
```

## Contacts

- **Test Debt Owner:** Development Team Lead
- **Quality Assurance:** QA Engineer
- **Support:** CI/CD Engineer

---

*Schedule reviewed and updated quarterly*
*Last updated: {datetime.now().strftime('%Y-%m-%d')}*
"]""""""

        with open(self.cleanup_schedule_file, "w[", encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_178")) as f[": f.write(schedule_content)": print(f["]]📅 Cleanup schedule created["]: [{self.cleanup_schedule_file}])": def main():"""
    "]""Main function to run test debt analysis."""""""
    print("🔍 Football Prediction System - Test Debt Analysis[")": print("]=" * 60)": tracker = TestDebtTracker()"""

    # Analyze test debt
    debt_analysis = tracker.analyze_test_debt()

    # Generate reports
    report_file = tracker.generate_test_debt_report(debt_analysis)
    tracker.schedule_cleanup_reminder()

    # Print summary
    summary = debt_analysis["summary["]": print("]\n[" + "]=" * 60)": print("📋 TEST DEBT ANALYSIS SUMMARY[")": print("]=" * 60)": print(f["Total Debt Items: {summary['total_debt_items']}"])": print(f["High Priority Items: {summary['high_priority_items']}"])": print(f["Untested Files: {summary['untested_files_count']}"])": print(f["Low Coverage Files: {summary['low_coverage_files_count']}"])": print(f["Failing Tests: {summary['failing_tests_count']}"])": print(f["Quality Issues: {summary['quality_issues_count']}"])": if summary["high_priority_items["] > 0:": print(": f["]\n🚨 {summary['high_priority_items']} high-priority items require immediate attention!"]""""
        )
    else:
        print("\n✅ No high-priority test debt items!")": print("\n📄 Reports generated:")": print(f["   - Test Debt Report["]: [{report_file}])"]": print(f["   - Test Debt Log["]: [{tracker.test_debt_file}])"]": print(f["   - Cleanup Schedule["]: [{tracker.cleanup_schedule_file}])"]": if __name__ =="__main__[": main()"]"""
