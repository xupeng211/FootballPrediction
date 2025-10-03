#!/usr/bin/env python3
import subprocess
import json
import datetime
import re
from pathlib import Path

KANBAN = Path("docs/_reports/TEST_COVERAGE_KANBAN.md")
REPORT_DIR = Path("docs/_reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def run(cmd):
    print(f"$ {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
    return res

# 1. 找到进行中任务
kanban_text = KANBAN.read_text(encoding="utf-8")
m = re.search(r"- \[ \] \*\*.*?覆盖率提升阶段 (\d+)\*\*: .*", kanban_text)
if not m:
    print("❌ No '进行中' coverage task found in Kanban.")
    exit(1)
phase = int(m.group(1))
target_map = {1:40, 2:50, 3:60, 4:70, 5:80}
target = target_map.get(phase, None)
if not target:
    print(f"❌ Phase {phase} not mapped to target coverage")
    exit(1)

print(f"🚧 当前进行中任务: Phase {phase}, 目标覆盖率 {target}%")

# 2. 跑 pytest 覆盖率
run(["pytest", "--cov=.", "--cov-report=term-missing", "--cov-report=json:coverage.json"])
cov = json.load(open("coverage.json"))
overall = cov["totals"]["percent_covered"]
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 3. 基线 & 改进计划
base_name = f"COVERAGE_BASELINE_P{phase}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
baseline = REPORT_DIR / base_name
bl = [f"# 📊 Coverage Baseline (Phase {phase}, {ts})", ""]
bl.append(f"- 当前总覆盖率：**{overall:.1f}%**")
bl.append(f"- 阶段目标：**{target}%**")
baseline.write_text("\n".join(bl), encoding="utf-8")

plan = REPORT_DIR / f"COVERAGE_{target}_PLAN.md"
pl = [f"# 🚀 Coverage Improvement Plan → {target}%", ""]
pl.append(f"- 基线时间：{ts}")
pl.append(f"- 当前覆盖率：**{overall:.1f}%**")
pl.append(f"- 阶段目标：**提升至 ≥ {target}%**")
plan.write_text("\n".join(pl), encoding="utf-8")

# 4. 回写 Kanban
def update_kanban(text:str)->str:
    block = f"Coverage提升阶段 {phase}:"
    if overall >= target:
        # 本阶段完成 → 打钩
        text = re.sub(
            fr"- \[ \] {block}.*",
            f"- [x] {block} 从当前覆盖率提升至 {target}% ✅ (当前 {overall:.1f}%)",
            text
        )
        # 推进下一阶段
        if phase+1 in target_map:
            nxt = f"Coverage提升阶段 {phase+1}: {target_map[phase]}% → {target_map[phase+1]}%"
            if nxt in text:
                text = text.replace(f"- [ ] {nxt}", f"- [ ] {nxt}\n  ⏳ 状态: 待执行\n  任务: 运行 make coverage 并更新 {target_map[phase+1]}% 计划")
    else:
        # 附加当前基线链接
        text = text.replace(block, block + f"\n  📌 当前基线：**{overall:.1f}%**（{ts}）\n  📄 基线报告：docs/_reports/{base_name}\n  🛠️ 行动方案：docs/_reports/{plan.name}")
    return text

KANBAN.write_text(update_kanban(kanban_text), encoding="utf-8")

# 5. 提交并推送 PR
branch = f"chore/kanban-phase{phase}-update"
run(["git", "checkout", "-b", branch])
run(["git", "add", "coverage.json", str(KANBAN), str(baseline), str(plan)])
run(["git", "commit", "-m", f"docs(test): Kanban Phase {phase} update, coverage {overall:.1f}%"])
run(["git", "push", "origin", branch])

title = f"docs(test): Kanban Phase {phase} update (coverage {overall:.1f}%)"
body = f"Update Kanban Phase {phase} with current coverage baseline and plan to reach {target}%."
run(["gh", "pr", "create", "--base", "main", "--head", branch, "--title", title, "--body", body])
run(["gh", "pr", "merge", "--squash", "--delete-branch", "--auto"])

print("✅ Kanban update complete.")