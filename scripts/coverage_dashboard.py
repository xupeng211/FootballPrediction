import json
import datetime
from pathlib import Path

# 输入输出路径
coverage_file = Path("coverage.json")
dashboard_file = Path("docs/_reports/COVERAGE_DASHBOARD.md")

# 加载覆盖率数据
if not coverage_file.exists():
    print("No coverage.json found, please run pytest --cov first")
    exit(1)

data = json.load(open(coverage_file))
files = data["files"]

# 提取文件覆盖率
stats = []
for path, meta in files.items():
    summary = meta["summary"]
    percent = summary["percent_covered"]
    missing = summary["missing_lines"]
    stats.append((path, percent, missing))

stats.sort(key=lambda x: x[1])  # 按覆盖率升序

# Top/Bottom 5
bottom5 = stats[:5]
top5 = stats[-5:]

# 按目录统计
dir_stats = {}
for path, percent, missing in stats:
    parts = path.split("/")
    if parts:
        d = parts[0]
        if d not in dir_stats:
            dir_stats[d] = {"files": 0, "missing": 0, "covered": 0, "lines": 0}
        dir_stats[d]["files"] += 1
        dir_stats[d]["missing"] += missing
        dir_stats[d]["lines"] += meta["summary"]["num_statements"]
        dir_stats[d]["covered"] += meta["summary"]["covered_lines"]

dir_rows = []
for d, v in dir_stats.items():
    cov = 100 * v["covered"] / v["lines"] if v["lines"] else 0
    dir_rows.append((d, v["files"], v["lines"], cov, v["missing"]))
dir_rows.sort(key=lambda x: x[3], reverse=True)

# 生成报告
lines = []
lines.append("# 📊 Test Coverage Dashboard")
lines.append("")
lines.append(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("")
lines.append("本仪表盘用于追踪项目测试覆盖率趋势和各模块差异。")
lines.append("")

# 总览
overall = data["totals"]["percent_covered"]
lines.append(f"## 1. 总体覆盖率\n\n当前总覆盖率: **{overall:.1f}%**\n")

# Top/Bottom
lines.append("## 2. 模块覆盖率排名")
lines.append("\n### 🏆 Top 5 覆盖率最高模块\n")
lines.append("| 文件 | 覆盖率 | 缺失行数 |")
lines.append("|------|--------|----------|")
for path, percent, missing in reversed(top5):
    lines.append(f"| {path} | {percent:.1f}% | {missing} |")

lines.append("\n### ⚠️ Bottom 5 覆盖率最低模块\n")
lines.append("| 文件 | 覆盖率 | 缺失行数 |")
lines.append("|------|--------|----------|")
for path, percent, missing in bottom5:
    lines.append(f"| {path} | {percent:.1f}% | {missing} |")

# 按目录
lines.append("\n## 3. 按目录覆盖率统计\n")
lines.append("| 目录 | 文件数 | 总行数 | 覆盖率 | 缺失行数 |")
lines.append("|------|--------|--------|--------|----------|")
for d, files, lines_count, cov, missing in dir_rows:
    lines.append(f"| {d} | {files} | {lines_count} | {cov:.1f}% | {missing} |")

# 改进建议
lines.append("\n## 4. 改进建议\n")
lines.append("- 优先修复覆盖率最低的模块 (Bottom 5)")
lines.append("- 持续提升覆盖率，每周 +5% 为目标")
lines.append("- 新增代码必须 ≥80% 覆盖率 (CI 已守护)")

dashboard_file.write_text("\n".join(lines), encoding="utf-8")
print(f"[done] Coverage dashboard updated at {dashboard_file}")
