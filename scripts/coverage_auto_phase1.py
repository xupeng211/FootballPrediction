#!/usr/bin/env python3
import json, subprocess, datetime, time
from pathlib import Path

def get_coverage():
    coverage_json = Path("coverage.json")
    if not coverage_json.exists():
        return 0.0
    data = json.load(open(coverage_json))
    return data.get("totals", {}).get("percent_covered", 0.0)

rounds = 0
while True:
    current_cov = get_coverage()
    print(f"📊 Current coverage: {current_cov}%")

    if current_cov >= 40.0:
        print("✅ Target 40% reached! Stopping loop.")
        break

    rounds += 1
    print(f"🚀 Starting iteration {rounds}...")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"chore/coverage-phase1-{ts}"

    # Step 1: Create new branch
    subprocess.run(["git", "checkout", "-b", branch])

    # Step 2: Generate new tests (Claude Code can auto-fill here)
    print("⚡ Generating new tests for low coverage files...")

    # Step 3: Run tests & generate reports
    subprocess.run(["python", "scripts/run_tests_with_report.py"], check=False)

    # Step 4: Update fix plan, dashboard, and kanban
    subprocess.run(["python", "scripts/generate_fix_plan.py"])
    subprocess.run(["python", "scripts/coverage_dashboard.py"])
    subprocess.run(["python", "scripts/kanban_next.py"])

    # Step 5: Commit and push
    subprocess.run(["git", "add", "tests/unit/", "docs/_reports/*"])
    subprocess.run(["git", "commit", "-m", f"test(phase1): auto coverage improvement {ts}"])
    subprocess.run(["git", "push", "origin", branch])

    # Step 6: Create and merge PR
    subprocess.run([
        "gh","pr","create",
        "--base","main",
        "--head",branch,
        "--title",f"test(phase1): auto coverage improvement {ts}",
        "--body","Automated Phase 1 coverage improvement loop iteration"
    ])
    subprocess.run(["gh","pr","merge","--squash","--delete-branch","--auto"])

    # Step 7: Wait before next iteration
    print("⏳ Waiting for changes to propagate...")
    time.sleep(60)