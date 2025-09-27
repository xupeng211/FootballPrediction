import subprocess, time, re, datetime, pathlib, os, json

STATE_FILE = ".coverage_bugfix_state"

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def get_latest_run_info():
    return run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0]'")

def get_latest_run_id():
    return run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId --jq '.[0].databaseId'")

def get_last_processed_id():
    if os.path.exists(STATE_FILE):
        return pathlib.Path(STATE_FILE).read_text().strip()
    return None

def set_last_processed_id(run_id):
    pathlib.Path(STATE_FILE).write_text(run_id)

while True:
    latest_run_id = get_latest_run_id()
    status = run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0].status'")
    conclusion = run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0].conclusion'")

    last_processed_id = get_last_processed_id()
    print(f"[{datetime.datetime.now()}] Latest run {latest_run_id}, status={status}, conclusion={conclusion}, last_processed={last_processed_id}")

    if latest_run_id == last_processed_id:
        print("⚠️ Already processed this run. Waiting 30s before next check.")
        time.sleep(30)
        continue

    if status == "completed":
        # 1. 下载日志
        log_path = "latest_workflow.log"
        subprocess.run(f"gh run view {latest_run_id} --log > {log_path}", shell=True)

        text = pathlib.Path(log_path).read_text(encoding="utf-8")

        # 2. 提取错误和覆盖率
        errors = "\n".join(re.findall(r"=+ FAILURES =+([\s\S]+?)(?=\n=+)", text)) or "No explicit failures found"
        coverage_matches = re.findall(r"(.+?\.py)\s+(\d+)%", text)
        low_cov_files = sorted(coverage_matches, key=lambda x: int(x[1]))[:10]

        # 3. 生成 Bugfix 报告
        report_name = f"docs/_reports/BUGFIX_REPORT_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
        with open(report_name, "w", encoding="utf-8") as f:
            f.write(f"# 🐞 Bugfix Report\n\n")
            f.write(f"**Generated:** {datetime.datetime.now()}\n\n")
            f.write(f"## 📊 Test Status\n- Run ID: {latest_run_id}\n- Status: {status}\n- Conclusion: {conclusion}\n\n")
            f.write(f"## ❌ Failures\n{errors}\n\n")
            f.write("## 📉 Low Coverage Files (Top 10)\n")
            for file, cov in low_cov_files:
                f.write(f"- {file}: {cov}% coverage\n")

        # 4. 更新 Kanban
        kanban_file = "docs/_reports/TEST_COVERAGE_KANBAN.md"
        with open(kanban_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n### 🔄 Bugfix Task {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- Source Run ID: {latest_run_id}\n")
            f.write(f"- Status: {status}, Conclusion: {conclusion}\n")
            f.write(f"- Generated new Bugfix report: {report_name}\n")

        # 5. 提交并合并 PR
        branch = f"chore/bugfix-report-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
        subprocess.run(f"git checkout -b {branch}", shell=True)
        subprocess.run(f"git add {report_name} {kanban_file}", shell=True)
        subprocess.run(f"git commit -m 'docs: add bugfix report {latest_run_id} and update Kanban'", shell=True)
        subprocess.run(f"git push origin {branch}", shell=True)
        subprocess.run(f"gh pr create --base main --head {branch} --title 'docs: bugfix report {latest_run_id}' --body 'Auto-generated bugfix report and Kanban update from workflow logs.'", shell=True)
        subprocess.run(f"gh pr merge --squash --auto", shell=True)

        print("✅ File processed and merged.")

        # 更新已处理的 run_id
        set_last_processed_id(latest_run_id)

        # 等待 60s 再继续
        time.sleep(60)
    else:
        time.sleep(30)