import subprocess, time, re, datetime, pathlib, os

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def get_latest_run_id():
    out = run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0]'")
    return out

while True:
    latest = run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0].databaseId'")
    status = run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0].status'")
    conclusion = run("gh run list --workflow=coverage-auto-phase1.yml --limit 1 --json databaseId,status,conclusion --jq '.[0].conclusion'")

    print(f"[{datetime.datetime.now()}] Latest run {latest}, status={status}, conclusion={conclusion}")

    if status == "completed":
        # 2. 下载日志
        log_path = "latest_workflow.log"
        subprocess.run(f"gh run view {latest} --log > {log_path}", shell=True)

        text = pathlib.Path(log_path).read_text(encoding="utf-8")

        # 3. 提取错误和覆盖率
        errors = "\n".join(re.findall(r"=+ FAILURES =+([\s\S]+?)(?=\n=+)", text)) or "No explicit failures found"
        coverage_matches = re.findall(r"(.+?\.py)\s+(\d+)%", text)
        low_cov_files = sorted(coverage_matches, key=lambda x: int(x[1]))[:10]

        # 4. 生成 Bugfix 报告
        report_name = f"docs/_reports/BUGFIX_REPORT_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
        with open(report_name, "w", encoding="utf-8") as f:
            f.write(f"# 🐞 Bugfix Report\n\n")
            f.write(f"**Generated:** {datetime.datetime.now()}\n\n")
            f.write(f"## 📊 Test Status\n- Run ID: {latest}\n- Status: {status}\n- Conclusion: {conclusion}\n\n")
            f.write(f"## ❌ Failures\n{errors}\n\n")
            f.write("## 📉 Low Coverage Files (Top 10)\n")
            for file, cov in low_cov_files:
                f.write(f"- {file}: {cov}% coverage\n")

        # 5. 更新 Kanban
        kanban_file = "docs/_reports/TEST_COVERAGE_KANBAN.md"
        with open(kanban_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n### 🔄 Bugfix Task {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- Source Run ID: {latest}\n")
            f.write(f"- Status: {status}, Conclusion: {conclusion}\n")
            f.write(f"- Generated new Bugfix report: {report_name}\n")

        # 6. 提交并合并 PR
        branch = f"chore/bugfix-report-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
        subprocess.run(f"git checkout -b {branch}", shell=True)
        subprocess.run(f"git add {report_name} {kanban_file}", shell=True)
        subprocess.run(f"git commit -m 'docs: add bugfix report {latest} and update Kanban'", shell=True)
        subprocess.run(f"git push origin {branch}", shell=True)
        subprocess.run(f"gh pr create --base main --head {branch} --title 'docs: bugfix report {latest}' --body 'Auto-generated bugfix report and Kanban update from workflow logs.'", shell=True)
        subprocess.run(f"gh pr merge --squash --auto", shell=True)

        print("✅ Bugfix report + Kanban update completed and merged.")

        # 避免重复处理同一次 run，等待60秒再检查
        time.sleep(60)

    else:
        # 如果还没完成，就隔30秒再检查
        time.sleep(30)