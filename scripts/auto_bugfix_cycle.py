import subprocess, pathlib, datetime, re, time

def run(cmd, check=True):
    print(f"⚙️ Running: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)

def run_tests():
    print("🚀 Running full test suite...")
    run("python scripts/run_tests_with_report.py", check=False)
    reports = sorted(pathlib.Path("docs/_reports").glob("BUGFIX_REPORT_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None

def update_kanban():
    print("📋 Updating Kanban...")
    run("python scripts/kanban_next.py", check=False)

def analyze_failures(report_path):
    print(f"🔍 Analyzing failures from {report_path}...")
    text = pathlib.Path(report_path).read_text(encoding="utf-8")
    failures = re.findall(r"## ❌ Failures\n([\s\S]+?)(?=\n##|$)", text)
    return failures[0].strip() if failures else "No explicit failures found"

def auto_fix(report_path):
    print("🛠️ Running AI auto-fix (Claude Code should handle this)...")
    # 占位：实际由 Claude Code 根据报告修复源码/测试
    # 这里生成一个分支并提交
    branch = f"fix/bug-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
    run(f"git checkout -b {branch}", check=False)
    run("git add src/ tests/ || true", check=False)
    run(f"git commit -m 'fix: auto bugfix based on {report_path.name}' || true", check=False)
    run(f"git push origin {branch}", check=False)
    run(f"gh pr create --base main --head {branch} --title 'fix: auto bugfix from {report_path.name}' --body 'Automated bugfix from {report_path.name}' || true", check=False)
    run("gh pr merge --squash --auto || true", check=False)

def main():
    while True:
        # Step 1: Run tests
        report = run_tests()
        if not report:
            print("❌ No bugfix report generated, exiting.")
            break

        # Step 2: Update Kanban
        update_kanban()

        # Step 3: Analyze report
        failures = analyze_failures(report)
        if "No explicit failures found" in failures:
            print("✅ No failures detected. Bugfix cycle complete.")
            break

        print(f"❌ Failures detected:\n{failures}")

        # Step 4: Auto-fix
        auto_fix(report)

        # Step 5: Wait a bit for CI to validate
        print("⏳ Waiting 60s before next cycle...")
        time.sleep(60)

if __name__ == "__main__":
    main()