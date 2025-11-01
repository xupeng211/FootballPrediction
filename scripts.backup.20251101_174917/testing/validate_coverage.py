#!/usr/bin/env python3
"""Validate coverage consistency across pytest.ini, COVERAGE_PROGRESS, and CI_REPORT."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
PYTEST_INI = ROOT / "pytest.ini"
COVERAGE_PROGRESS = ROOT / "docs" / "COVERAGE_PROGRESS.md"
CI_REPORT = ROOT / "docs" / "CI_REPORT.md"


def parse_pytest_threshold() -> Optional[float]:
    text = PYTEST_INI.read_text(encoding="utf-8")
    match = re.search(r"--cov-fail-under=(\d+)", text)
    return float(match.group(1)) if match else None


def parse_progress_latest() -> Optional[float]:
    text = COVERAGE_PROGRESS.read_text(encoding="utf-8")
    entries = re.findall(r"\| (\d{4}-\d{2}-\d{2}) \| `[^`]+` \| ([0-9.]+)% \|", text)
    if not entries:
        return None
    _, value = entries[-1]
    return float(value)


def parse_ci_report() -> tuple[Optional[float], Optional[float]]:
    text = CI_REPORT.read_text(encoding="utf-8")
    total_match = re.search(r"^\|\s*\*\*合计\*\*\s*\|.*\|\s*([0-9.]+)%\s*\|$", text, re.MULTILINE)
    total = float(total_match.group(1)) if total_match else None
    trend_entries = re.findall(
        r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\| [^|]+ \| [^|]+ \| [^|]+ \|\s*([0-9.]+)%\s*\|$",
        text,
        re.MULTILINE,
    )
    trend = float(trend_entries[-1][1]) if trend_entries else None
    return total, trend


def append_result(
    pytest_thr: Optional[float],
    progress: Optional[float],
    ci_total: Optional[float],
    ci_trend: Optional[float],
) -> None:
    today = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y-%m-%d")
    lines = [f"## 覆盖率一致性验证结果 ({today})", ""]

    def fmt(value: Optional[float]) -> str:
        return f"{value:.2f}%" if value is not None else "N/A"

    lines.append(
        f"- pytest.ini 阈值：{int(pytest_thr)}%"
        if pytest_thr is not None
        else "- pytest.ini 阈值：未设置"
    )
    lines.append(f"- COVERAGE_PROGRESS.md 最新记录：{fmt(progress)}")
    lines.append(f"- CI_REPORT.md 最新覆盖率：{fmt(ci_total)}")
    lines.append(f"- CI_REPORT.md 历史趋势覆盖率：{fmt(ci_trend)}")

    compare_values = [value for value in (ci_total, ci_trend) if value is not None]
    consistent = (
        progress is not None
        and compare_values
        and all(abs(progress - value) <= 0.1 for value in compare_values)
    )

    threshold_values = [value for value in (progress, ci_total, ci_trend) if value is not None]
    threshold_ok = (
        pytest_thr is not None
        and threshold_values
        and all(value >= pytest_thr for value in threshold_values)
    )

    lines.append("")
    lines.append("**结论**：")
    if consistent and threshold_ok:
        lines.append("- ✅ 三者一致（满足阈值要求）")
    else:
        issues = []
        if not consistent:
            issues.append("覆盖率数值不一致")
        if not threshold_ok:
            issues.append("pytest.ini 阈值未达到最新覆盖率")
        lines.append("- ❌ 不一致（" + "；".join(issues) + "）")

    lines.append("")

    report_text = CI_REPORT.read_text(encoding="utf-8")
    CI_REPORT.write_text(report_text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    pytest_thr = parse_pytest_threshold()
    progress = parse_progress_latest()
    ci_total, ci_trend = parse_ci_report()
    append_result(pytest_thr, progress, ci_total, ci_trend)


if __name__ == "__main__":
    main()
