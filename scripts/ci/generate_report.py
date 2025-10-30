#!/usr/bin/env python3
"""Generate a CI fast/slow test comparison report.

Reads pytest logs (fast.log, slow.log, integration.log) and coverage output
(coverage.txt), then writes docs/CI_REPORT.md with a Markdown summary.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:  # Optional dependency; charting is skipped if unavailable.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
            except Exception:  # pragma: no cover - best effort fallback
    plt = None

ROOT = Path(__file__).resolve().parents[1]
LOG_FAST = ROOT / "fast.log"
LOG_SLOW = ROOT / "slow.log"
LOG_INTEGRATION = ROOT / "integration.log"
COVERAGE_TXT = ROOT / "coverage.txt"
REPORT_PATH = ROOT / "docs" / "CI_REPORT.md"

SUMMARY_RE = re.compile(r"=+\s+(?P<summary>.+?)=+\s*$", re.MULTILINE)
TIME_RE = re.compile(r"in\s+([0-9]+(?:\.[0-9]+)?)s")
COVERAGE_TOTAL_RE = re.compile(r"TOTAL\s+\d+\s+\d+(?:\s+\d+)?\s+([0-9]+)%")
SLOWEST_LINE_RE = re.compile(r"^[0-9.]+s\s+(call|setup|teardown)\s+.+", re.IGNORECASE)


@dataclass
class PytestStats:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    deselected: int = 0
    xfailed: int = 0
    xpassed: int = 0
    duration: float = 0.0
    summary_line: str = ""
    slowest: List[str] | None = None

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.xfailed + self.xpassed


def parse_summary(text: str) -> PytestStats:
    matches = SUMMARY_RE.findall(text)
    if not matches:
        return PytestStats(summary_line="No summary found")
    last = matches[-1]
    stats = PytestStats(summary_line=last)
    for label in ("passed", "failed", "skipped", "deselected", "xfailed", "xpassed"):
        m = re.search(rf"(\d+)\s+{label}", last)
        if m:
            setattr(stats, label, int(m.group(1)))
    time_match = TIME_RE.search(last)
    if time_match:
        stats.duration = float(time_match.group(1))
    stats.slowest = extract_slowest(text)
    return stats


def extract_slowest(text: str, limit: int = 10) -> List[str]:
    anchor = "slowest"
    idx = text.lower().rfind(anchor)
    if idx == -1:
        return []
    lines = text[idx:].splitlines()
    entries: List[str] = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("=") or stripped.startswith("("):
            continue
        if SLOWEST_LINE_RE.match(stripped):
            entries.append(stripped)
        if len(entries) >= limit:
            break
    return entries


def parse_coverage_from_text(text: str) -> float | None:
    matches = COVERAGE_TOTAL_RE.findall(text)
    if not matches:
        return None
    return float(matches[-1])


def format_duration(seconds: float) -> str:
    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    return f"{seconds:.1f}s"


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing expected file: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def main() -> None:
    fast_text = read(LOG_FAST)
    slow_text = read(LOG_SLOW)
    integration_text = read(LOG_INTEGRATION)
    coverage_text = read(COVERAGE_TXT)

    fast_stats = parse_summary(fast_text)
    slow_stats = parse_summary(slow_text)
    integration_stats = parse_summary(integration_text)

    fast_coverage = parse_coverage_from_text(fast_text)
    slow_coverage = parse_coverage_from_text(slow_text)
    integration_coverage = parse_coverage_from_text(integration_text)

    total_matches = re.findall(r"TOTAL\s+\d+\s+\d+(?:\s+\d+)?\s+([0-9]+)%", coverage_text)
    if total_matches:
        overall_coverage = float(total_matches[-1])
    else:
        print("⚠️ Coverage TOTAL not found")
        existing = [
            c for c in (fast_coverage, slow_coverage, integration_coverage) if c is not None
        ]
        overall_coverage = existing[-1] if existing else 0.0

    total_stats = PytestStats(
        passed=fast_stats.passed + slow_stats.passed + integration_stats.passed,
        failed=fast_stats.failed + slow_stats.failed + integration_stats.failed,
        skipped=fast_stats.skipped + slow_stats.skipped + integration_stats.skipped,
        deselected=fast_stats.deselected + slow_stats.deselected + integration_stats.deselected,
        xfailed=fast_stats.xfailed + slow_stats.xfailed + integration_stats.xfailed,
        xpassed=fast_stats.xpassed + slow_stats.xpassed + integration_stats.xpassed,
        duration=fast_stats.duration + slow_stats.duration + integration_stats.duration,
    )

    now = dt.datetime.now(dt.timezone.utc).astimezone()
    date_str = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S %Z")

    table_header = (
        "| 套件 | 用例数 | 通过 | 失败 | 跳过 | 耗时 | 覆盖率 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |"
    )
    display_fast_cov = fast_coverage if fast_coverage is not None else overall_coverage
    display_slow_cov = slow_coverage if slow_coverage is not None else overall_coverage
    display_integration_cov = (
        integration_coverage if integration_coverage is not None else overall_coverage
    )
    base_fast_cov = display_fast_cov if display_fast_cov is not None else overall_coverage

    overall_cov_display = overall_coverage if overall_coverage is not None else 0.0

    table_rows = [
        "| Fast (unit) | {total} | {p} | {f} | {s} | {d} | {c:.2f}% |".format(
            total=fast_stats.total,
            p=fast_stats.passed,
            f=fast_stats.failed,
            s=fast_stats.skipped,
            d=format_duration(fast_stats.duration),
            c=display_fast_cov,
        ),
        "| Slow (slow) | {total} | {p} | {f} | {s} | {d} | {c:.2f}% |".format(
            total=slow_stats.total,
            p=slow_stats.passed,
            f=slow_stats.failed,
            s=slow_stats.skipped,
            d=format_duration(slow_stats.duration),
            c=display_slow_cov,
        ),
        "| Integration | {total} | {p} | {f} | {s} | {d} | {c:.2f}% |".format(
            total=integration_stats.total,
            p=integration_stats.passed,
            f=integration_stats.failed,
            s=integration_stats.skipped,
            d=format_duration(integration_stats.duration),
            c=display_integration_cov,
        ),
        "| **合计** | {total} | {p} | {f} | {s} | {d} | {c:.2f}% |".format(
            total=total_stats.total,
            p=total_stats.passed,
            f=total_stats.failed,
            s=total_stats.skipped,
            d=format_duration(total_stats.duration),
            c=overall_cov_display,
        ),
    ]

    def format_slowest_section(title: str, entries: List[str]) -> List[str]:
        lines = [f"#### {title}"]
        if not entries:
            lines.append("- 无记录")
        else:
            for item in entries[:10]:
                lines.append(f"- {item}")
        lines.append("")
        return lines

    detail_lines = ["### 详细耗时", ""]
    detail_lines.extend(format_slowest_section("Fast 最慢用例 Top 10", fast_stats.slowest or []))
    detail_lines.extend(format_slowest_section("Slow 最慢用例 Top 10", slow_stats.slowest or []))
    detail_lines.extend(
        format_slowest_section("Integration 最慢用例 Top 10", integration_stats.slowest or [])
    )

    coverage_lines = [
        "### 覆盖率详情",
        "",
        "```text",
        coverage_text.strip(),
        "```",
        "",
    ]

    base_fast_cov = display_fast_cov
    coverage_gain = overall_cov_display - base_fast_cov
    duration_diff = (slow_stats.duration + integration_stats.duration) - fast_stats.duration

    fast_ok = fast_stats.duration <= 120
    coverage_ok = overall_cov_display >= 70

    analysis_lines = [
        "### 对比分析",
        "",
        f"- **耗时对比**: 慢测试 + 集成测试比快速套件多 {duration_diff:.1f}s",
        f"- **覆盖率增量**: 快速覆盖 {base_fast_cov:.2f}% → 全局 {overall_cov_display:.2f}% (增量 {coverage_gain:.2f}%)",
        "- **主要耗时模块**:",
    ]

    combined_slowest = (slow_stats.slowest or [])[:5] + (integration_stats.slowest or [])[:5]
    if not combined_slowest:
        combined_slowest = fast_stats.slowest or []
    analysis_lines.extend(f"  - {item}" for item in combined_slowest[:5])
    analysis_lines.append("")

    conclusion_lines = [
        "### 结论",
        "",
        f"- Fast suite 是否满足 <2 分钟目标：{'✅ 是' if fast_ok else '⚠️ 否'}",
        f"- 全局覆盖率是否 ≥70%：{'✅ 是' if coverage_ok else '⚠️ 否'}",
        "- 建议：PR 仅运行快速单测；慢测试与集成测试保留在 nightly / main 推送阶段。",
        "",
    ]

    history_lines, history_rows = build_history_section(
        date_str,
        fast_stats.duration,
        slow_stats.duration,
        integration_stats.duration,
        overall_coverage,
    )

    generate_coverage_chart(history_rows)
    chart_path = REPORT_PATH.parent / "assets" / "coverage_trend.png"
    has_chart = chart_path.exists()

    report_lines = [
        "# CI Fast vs Slow 测试对比报告",
        "",
        f"_Generated at {generated_at}. Do not edit manually._",
        "",
        table_header,
        *table_rows,
        "",
        *detail_lines,
        *coverage_lines,
        *analysis_lines,
        *conclusion_lines,
        *history_lines,
    ]

    if has_chart:
        report_lines.extend(["![Coverage Trend](assets/coverage_trend.png)", ""])

    REPORT_PATH.write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")


def build_history_section(
    date_str: str,
    fast_duration: float,
    slow_duration: float,
    integration_duration: float,
    coverage: float,
) -> tuple[List[str], List[dict]]:
    rows = load_existing_history()
    new_entry = {
        "date": date_str,
        "fast": format_duration_hist(fast_duration),
        "slow": format_duration_hist(slow_duration),
        "integration": format_duration_hist(integration_duration),
        "coverage": f"{coverage:.1f}%",
    }
    # Update existing entry for the same date or append
    found = False
    for row in rows:
        if row["date"] == date_str:
            row.update(new_entry)
            found = True
            break
    if not found:
        rows.append(new_entry)
    rows.sort(key=lambda r: r["date"])

    lines = [
        "## 历史趋势",
        "",
        "| 日期 | Fast 耗时 | Slow 耗时 | 集成耗时 | 总覆盖率 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['date']} | {row['fast']} | {row['slow']} | {row['integration']} | {row['coverage']} |"
        )
    lines.append("")
    return lines, rows


def load_existing_history() -> List[dict]:
    if not REPORT_PATH.exists():
        return []
    content = REPORT_PATH.read_text(encoding="utf-8", errors="ignore")
    if "## 历史趋势" not in content:
        return []
    history_section = content.split("## 历史趋势", 1)[1]
    lines = [line.strip() for line in history_section.splitlines() if line.strip().startswith("|")]
    rows: List[dict] = []
    for line in lines[2:]:  # Skip header
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 5:
            continue
        rows.append(
            {
                "date": parts[0],
                "fast": parts[1],
                "slow": parts[2],
                "integration": parts[3],
                "coverage": parts[4],
            }
        )
    return rows


def format_duration_hist(seconds: float) -> str:
    if seconds >= 60:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    return f"{seconds:.0f}s"


def generate_coverage_chart(rows: List[dict]) -> None:
    if plt is None or not rows:
        return

    try:
        dates = [row["date"] for row in rows]
        coverage_values = [float(row["coverage"].rstrip("%")) for row in rows]
    except (KeyError, ValueError):  # pragma: no cover - defensive
        return

    if not coverage_values:
        return

    # Ensure assets directory exists
    asset_dir = REPORT_PATH.parent / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    output_path = asset_dir / "coverage_trend.png"

    plt.figure(figsize=(8, 4))
    plt.plot(dates, coverage_values, marker="o", linewidth=2, color="#1f77b4")
    plt.title("Coverage Trend")
    plt.xlabel("Date")
    plt.ylabel("Coverage %")
    plt.ylim(0, 100)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    try:
        plt.savefig(output_path)
    finally:  # Ensure resources are released even if savefig fails
        plt.close()


if __name__ == "__main__":
    main()
