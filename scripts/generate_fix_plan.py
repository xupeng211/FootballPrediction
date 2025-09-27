#!/usr/bin/env python3
import re, glob, datetime
from pathlib import Path

REPORT_DIR = Path("docs/_reports")
fix_plan = REPORT_DIR / "COVERAGE_FIX_PLAN.md"

# 找到最新的 Bugfix 报告
reports = sorted(glob.glob(str(REPORT_DIR / "BUGFIX_REPORT_*.md")))
latest = reports[-1] if reports else None

tasks = []
if latest:
    text = Path(latest).read_text(encoding="utf-8")

    # 提取退出码
    m_exit = re.search(r"退出码: (\d+)", text)
    exit_code = m_exit.group(1) if m_exit else "unknown"

    # 提取覆盖率
    m_cov = re.search(r"总覆盖率: \*\*([\d\.]+)%\*\*", text)
    coverage = m_cov.group(1) if m_cov else "0.0"

    # 提取低覆盖率文件列表
    low_cov_files = re.findall(r"- ([\w\./-]+): ([\d\.]+)% 覆盖率", text)

    tasks.append(f"### 测试状态\n- 退出码: {exit_code}\n- 总覆盖率: {coverage}%\n")

    if low_cov_files:
        tasks.append("### 优先处理文件 (覆盖率最低 Top 10)\n")
        for f, pc in low_cov_files:
            tasks.append(f"- [ ] {f} — {pc}% 覆盖率")

# 写出计划文件
fix_plan.write_text(
    "# 🔧 Coverage Fix Plan\n\n"
    f"生成时间: {datetime.datetime.now()}\n\n"
    "以下任务由最新 Bugfix 报告自动生成：\n\n"
    + "\n".join(tasks) + "\n\n"
    "### 后续行动建议\n"
    "- 修复失败用例（见 pytest_failures.log）\n"
    "- 补充低覆盖率文件的测试\n"
    "- 每次完成后运行 `python scripts/run_tests_with_report.py` 更新报告\n"
    "- 提交改进结果并更新 Kanban\n",
    encoding="utf-8"
)

print(f"✅ Coverage Fix Plan generated: {fix_plan}")