#!/usr/bin/env python3
"""
设置每周安全检查脚本
"""

import os
import subprocess
from pathlib import Path

class WeeklySecurityCheckSetup:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def log(self, message: str, level: str = "INFO"):
        colors = {
            "INFO": "\033[0m",
            "WARN": "\033[0;33m",
            "ERROR": "\033[0;31m",
            "SUCCESS": "\033[0;32m",
            "HIGHLIGHT": "\033[1;34m"
        }
        color = colors.get(level, "\033[0m")
        print(f"{color}{message}\033[0m")

    def create_cron_job(self):
        """创建cron任务"""
        self.log("\n⏰ 设置每周安全检查任务...", "HIGHLIGHT")

        # 获取当前目录
        current_dir = os.getcwd()

        # 创建cron任务内容
        cron_content = f"""# 每周一早上8点运行安全检查
0 8 * * 1 cd {current_dir} && ./scripts/security-check.sh >> logs/security-check.log 2>&1

# 每月1号凌晨2点更新依赖
0 2 1 * * cd {current_dir} && pip-audit -r requirements.txt >> logs/dependency-update.log 2>&1
"""

        # 创建临时的cron文件
        cron_file = self.project_root / "security-cron.txt"
        with open(cron_file, 'w') as f:
            f.write(cron_content)

        self.log(f"  Cron任务已创建: {cron_file}", "INFO")
        self.log("  请手动执行以下命令安装cron任务:", "WARN")
        self.log(f"    crontab {cron_file}", "HIGHLIGHT")

    def create_systemd_service(self):
        """创建systemd服务（可选）"""
        self.log("\n🔧 创建Systemd服务...", "INFO")

        service_content = f"""[Unit]
Description=Football Prediction Security Check
After=network.target

[Service]
Type=oneshot
User={os.getenv('USER')}
WorkingDirectory={self.project_root}
ExecStart={self.project_root}/scripts/security-check.sh
StandardOutput=file:{self.project_root}/logs/security-check.log
StandardError=file:{self.project_root}/logs/security-check.log

[Install]
WantedBy=multi-user.target
"""

        timer_content = """[Unit]
Description=Weekly security check
Requires=football-security.service

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
"""

        # 创建服务文件
        service_dir = Path("/etc/systemd/system")
        if os.access(service_dir, os.W_OK):
            service_path = service_dir / "football-security.service"
            timer_path = service_dir / "football-security.timer"

            try:
                with open(service_path, 'w') as f:
                    f.write(service_content)
                with open(timer_path, 'w') as f:
                    f.write(timer_content)

                self.log("  Systemd服务已创建", "SUCCESS")
                self.log("  启用服务:", "INFO")
                self.log("    sudo systemctl enable football-security.timer", "HIGHLIGHT")
                self.log("    sudo systemctl start football-security.timer", "HIGHLIGHT")
            except PermissionError:
                self.log("  需要sudo权限创建系统服务", "WARN")
        else:
            self.log("  没有写入/etc/systemd/system的权限", "WARN")

    def create_github_action(self):
        """创建GitHub Action定期安全检查"""
        self.log("\n🤖 创建GitHub Action定期安全检查...", "INFO")

        workflow_dir = self.project_root / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = """name: Security Scan

on:
  schedule:
    - cron: '0 8 * * 1'  # 每周一早上8点
  workflow_dispatch:

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pip-audit bandit safety

    - name: Run dependency audit
      run: pip-audit -r requirements.txt

    - name: Run security scan
      run: bandit -r src/ -f json -o security-report.json

    - name: Upload security report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-report
        path: security-report.json

    - name: Create issue if vulnerabilities found
      if: failure()
      uses: actions/github-script@v6
      with:
        script: |
          const issueTitle = 'Security Vulnerabilities Detected';
          const issueBody = 'Security scan found vulnerabilities. Please check the logs.';

          // Check if issue already exists
          const { data: issues } = await github.rest.issues.listForRepo({
            owner: context.repo.owner,
            repo: context.repo.repo,
            state: 'open',
            labels: 'security'
          });

          const existingIssue = issues.find(issue => issue.title === issueTitle);

          if (!existingIssue) {
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: issueTitle,
              body: issueBody,
              labels: ['security', 'automation']
            });
          }
"""

        workflow_file = workflow_dir / "security-scan.yml"
        with open(workflow_file, 'w') as f:
            f.write(workflow_content)

        self.log(f"  GitHub Action已创建: {workflow_file.relative_to(self.project_root)}", "SUCCESS")

    def create_monitoring_dashboard(self):
        """创建安全监控面板"""
        self.log("\n📊 创建安全监控面板...", "INFO")

        dashboard_content = """# 安全监控面板

## 每周检查清单

- [ ] 运行 `./scripts/security-check.sh`
- [ ] 检查依赖漏洞
- [ ] 检查代码安全问题
- [ ] 验证敏感文件保护
- [ ] 检查日志文件大小

## 安全指标

### 依赖漏洞数
- 严重: 0
- 高危: 0
- 中危: 0
- 低危: 0

### 代码安全问题
- 严重: 0
- 高危: 1 (MD5哈希 - 已标记为非安全用途)
- 中危: 5 (SQL注入 - 已部分修复)
- 低危: 31 (主要是try-except-pass模式)

### 文件权限
- .env.production: 600 ✓
- 其他配置文件: 644 ✓

## 快速命令

```bash
# 运行完整安全检查
./scripts/security-check.sh

# 只检查依赖漏洞
pip-audit -r requirements.txt

# 只检查代码安全
bandit -r src/ -f txt

# 检查敏感文件
find . -name "*.env*" -not -path "./.git/*"

# 检查大文件
find . -type f -size +10M
```

## 最近的安全活动

{{ 在这里记录安全检查结果 }}

---

最后更新: 2025-10-04
"""

        dashboard_file = self.project_root / "docs" / "security" / "dashboard.md"
        dashboard_file.parent.mkdir(parents=True, exist_ok=True)
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(dashboard_content)

        self.log(f"  安全面板已创建: {dashboard_file.relative_to(self.project_root)}", "SUCCESS")

    def setup_log_rotation(self):
        """设置日志轮转"""
        self.log("\n📝 设置日志轮转...", "INFO")

        logrotate_content = f"""# 安全检查日志轮转配置
{self.project_root}/logs/security-check.log {{
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 644 {os.getenv('USER')} {os.getenv('USER')}
}}

{self.project_root}/logs/dependency-update.log {{
    monthly
    rotate 6
    compress
    delaycompress
    missingok
    notifempty
    create 644 {os.getenv('USER')} {os.getenv('USER')}
}}
"""

        logrotate_file = self.project_root / "security-logrotate"
        with open(logrotate_file, 'w') as f:
            f.write(logrotate_content)

        self.log(f"  日志轮转配置已创建: {logrotate_file.name}", "INFO")
        self.log("  安装到系统:", "WARN")
        self.log(f"    sudo cp {logrotate_file} /etc/logrotate.d/football-security", "HIGHLIGHT")

    def run(self):
        """运行所有设置"""
        self.log("=" * 70)
        self.log("设置定期安全检查...", "SUCCESS")
        self.log("=" * 70)

        # 创建logs目录
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)

        self.create_cron_job()
        self.create_systemd_service()
        self.create_github_action()
        self.create_monitoring_dashboard()
        self.setup_log_rotation()

        self.log("\n" + "=" * 70)
        self.log("定期安全检查设置完成！", "SUCCESS")
        self.log("\n配置选项:", "HIGHLIGHT")
        self.log("1. Cron任务 (推荐用于简单场景)", "INFO")
        self.log("2. Systemd服务 (推荐用于服务器)", "INFO")
        self.log("3. GitHub Action (推荐用于CI/CD)", "INFO")
        self.log("=" * 70)


if __name__ == "__main__":
    setup = WeeklySecurityCheckSetup()
    setup.run()