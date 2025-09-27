import subprocess, time, datetime, argparse

def run(cmd, check=True):
    print(f"⚙️ Running: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)

def get_coverage():
    try:
        out = run("coverage report -m", check=False).stdout
        for line in out.splitlines():
            if "TOTAL" in line:
                return float(line.split()[-1].replace("%", ""))
    except Exception:
        return 0.0
    return 0.0

def execute_once():
    now = datetime.datetime.now().strftime("%Y%m%d%H%M")
    branch = f"chore/coverage-phase1-{now}"

    # 1. 创建分支
    run(f"git checkout -b {branch}", check=False)

    # 2. 运行测试并生成报告
    run("pytest --maxfail=5 --disable-warnings -q --cov=. --cov-report=json:coverage.json || true", check=False)

    # 3. 生成 Bugfix 报告
    run("python scripts/generate_fix_plan.py", check=False)

    # 4. 更新 Kanban + Dashboard
    run("python scripts/kanban_next.py", check=False)
    run("python scripts/coverage_dashboard.py", check=False)

    # 5. 提交并推送
    run("git add docs/_reports/* coverage.json || true", check=False)
    run(f"git commit -m 'chore: auto coverage improvement round {now}' || true", check=False)
    run(f"git push origin {branch}", check=False)

    # 6. 创建并合并 PR
    run(f"gh pr create --base main --head {branch} --title 'ci: auto coverage improvement {now}' --body 'Automated coverage improvement iteration.' || true", check=False)
    run("gh pr merge --squash --auto || true", check=False)

def loop_until_target(target=40.0):
    round_num = 1
    while True:
        print(f"🚀 Iteration {round_num} started...")
        cov = get_coverage()
        if cov >= target:
            print(f"✅ Target reached: {cov}% >= {target}%")
            break
        execute_once()
        print(f"⏳ Waiting before next iteration...")
        time.sleep(60)
        round_num += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run only one iteration and exit")
    args = parser.parse_args()

    if args.once:
        execute_once()
    else:
        loop_until_target()