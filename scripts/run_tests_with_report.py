#!/usr/bin/env python3
import subprocess
import datetime
import json
from pathlib import Path

REPORT_DIR = Path("docs/_reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# 1. 运行测试（使用 pytest.ini 配置）
cmd = [
    "pytest",
    "-vv", "-ra", "--maxfail=5",       # 保持与pytest.ini一致
    "--cov=src", "--cov-report=json:coverage.json",
    "--cov-report=term-missing", "-p", "no:xdist"  # 保持与pytest.ini一致
]

print("🚀 Running tests...")
result = subprocess.run(cmd, text=True)

# 2. 解析覆盖率
coverage_data = {}
if Path("coverage.json").exists():
    coverage_data = json.load(open("coverage.json"))

overall = coverage_data.get("totals", {}).get("percent_covered", 0.0)

# 3. 生成 BUGFIX_REPORT.md
bugfix_report = REPORT_DIR / f"BUGFIX_REPORT_{ts}.md"
lines = []
lines.append(f"# 🐞 Bugfix Report ({ts})\n")
lines.append("## ✅ 测试执行结果")
lines.append(f"- 测试退出码: {result.returncode}")
lines.append(f"- 总覆盖率: **{overall:.1f}%**\n")

# 如果有失败，收集日志
log_file = Path("pytest_failures.log")
if result.returncode != 0:
    lines.append("## ❌ 失败用例日志\n")
    with open(log_file, "w", encoding="utf-8") as f:
        proc = subprocess.run(["pytest", "--maxfail=10", "--tb=short"],
                              text=True, stdout=f, stderr=f)
    lines.append("以下是失败用例的详细输出，请对照修复：\n")
    lines.append(f"日志文件: `{log_file}`\n")

# 覆盖率分析
lines.append("## 📊 覆盖率缺口分析\n")
files = coverage_data.get("files", {})
low_cov = sorted(
    [(p, f["summary"]["percent_covered"]) for p, f in files.items()],
    key=lambda x: x[1]
)[:10]
for path, pc in low_cov:
    lines.append(f"- {path}: {pc:.1f}% 覆盖率")

bugfix_report.write_text("\n".join(lines), encoding="utf-8")
print(f"✅ Bugfix report generated: {bugfix_report}")