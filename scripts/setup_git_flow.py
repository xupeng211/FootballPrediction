#!/usr/bin/env python3
"""
Git Flow 工作流设置脚本
自动化配置GitHub仓库的Git Flow分支保护规则和工作流
"""

import os
import subprocess
import sys
from pathlib import Path

import requests


class GitFlowSetup:
    """Git Flow工作流配置器"""

    def __init__(self,
    repo_owner: str = "xupeng211",
    repo_name: str = "FootballPrediction"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.api_base = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

        # 验证环境
        self._validate_environment()

    def _validate_environment(self):
        """验证环境配置"""
        if not self.github_token:
            sys.exit(1)

    def _api_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送GitHub API请求"""
        url = f"{self.api_base}/{endpoint}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response.raise_for_status()
            return response.json() if response.content else {}

        except requests.exceptions.RequestException:
            return {}

    def setup_branch_protection(self) -> bool:
        """设置分支保护规则"""

        # main分支保护
        main_protection = {
            "required_status_checks": {
                "strict": True,
                "contexts": [
                    "CI/CD Pipeline",
                    "Code Quality Check",
                    "Test Coverage",
                    "Security Scan"
                ]
            },
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
                "dismissal_restrictions": {
                    "users": [],
                    "teams": []
                }
            },
            "restrictions": {
                "users": [],
                "teams": ["core-developers"]
            }
        }

        # develop分支保护
        develop_protection = {
            "required_status_checks": {
                "strict": False,
                "contexts": [
                    "CI/CD Pipeline",
                    "Code Quality Check"
                ]
            },
            "enforce_admins": False,
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
                "dismissal_restrictions": {
                    "users": [],
                    "teams": []
                }
            },
            "restrictions": {
                "users": [],
                "teams": ["developers"]
            }
        }

        # 应用分支保护
        success = True

        # main分支保护
        if self._update_branch_protection("main", main_protection):
            pass
        else:
            success = False

        # develop分支保护
        if self._update_branch_protection("develop", develop_protection):
            pass
        else:
            success = False

        return success

    def _update_branch_protection(self, branch: str, protection: dict) -> bool:
        """更新单个分支的保护规则"""
        endpoint = f"branches/{branch}/protection"
        result = self._api_request("PUT", endpoint, protection)
        return bool(result)

    def create_initial_branches(self) -> bool:
        """创建初始分支结构"""

        # 检查main分支
        main_exists = self._check_branch_exists("main")
        develop_exists = self._check_branch_exists("develop")

        success = True

        # 如果main分支不存在，尝试从master创建
        if not main_exists:
            if self._check_branch_exists("master"):
                self._create_branch_from("main", "master")
            else:
                success = False

        # 创建develop分支
        if not develop_exists and main_exists:
            self._create_branch_from("develop", "main")
        elif develop_exists:
            pass

        return success

    def _check_branch_exists(self, branch: str) -> bool:
        """检查分支是否存在"""
        endpoint = f"branches/{branch}"
        result = self._api_request("GET", endpoint)
        return bool(result)

    def _create_branch_from(self, new_branch: str, source_branch: str) -> bool:
        """从源分支创建新分支"""
        # 获取源分支的最新提交
        endpoint = f"git/refs/heads/{source_branch}"
        result = self._api_request("GET", endpoint)

        if not result:
            return False

        sha = result.get("object", {}).get("sha")
        if not sha:
            return False

        # 创建新分支
        create_data = {
            "ref": f"refs/heads/{new_branch}",
            "sha": sha
        }

        endpoint = "git/refs"
        result = self._api_request("POST", endpoint, create_data)
        return bool(result)

    def setup_teams(self) -> bool:
        """设置团队权限（如果组织有团队）"""

        # 这里可以设置团队权限
        # 由于需要组织管理权限，这里只提供框架

        return True

    def create_workflow_files(self) -> bool:
        """创建GitHub Actions工作流文件"""

        workflow_dir = Path(".github/workflows")
        workflow_dir.mkdir(parents=True, exist_ok=True)

        # 分支保护工作流
        branch_protection_workflow = """name: Branch Protection

on:
  pull_request:
    branches: [main, develop]

jobs:
  protection-checks:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          make install

      - name: Load project context
        run: make context

      - name: Environment check
        run: make env-check

      - name: Run unit tests
        run: make test.unit

      - name: Run integration tests
        run: make test.int

      - name: Code quality check
        run: make lint

      - name: Security check
        run: make security

      - name: Coverage report
        run: make coverage

      - name: Pre-push validation
        run: make pre-push

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
"""

        # 自动合并工作流
        auto_merge_workflow = """name: Auto Merge

on:
  pull_request:
    types: [ready_for_review, opened, synchronize, reopened]
    branches: [develop]

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.event.pull_request.draft == false

    steps:
      - name: Auto-merge
        uses: ahmadnassri/action-dependabot-auto-merge@v2
        with:
          target: minor
          github-token: "${{ secrets.GITHUB_TOKEN }}"
"""

        # 发布工作流
        release_workflow = """name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: make install

      - name: Run tests
        run: make test

      - name: Build package
        run: python -m build

      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
"""

        # 写入工作流文件
        workflows = {
            "branch-protection.yml": branch_protection_workflow,
            "auto-merge.yml": auto_merge_workflow,
            "release.yml": release_workflow
        }

        success = True
        for filename, content in workflows.items():
            file_path = workflow_dir / filename
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception:
                success = False

        return success

    def create_git_hooks(self) -> bool:
        """创建Git hooks"""

        hooks_dir = Path(".git/hooks")
        if not hooks_dir.exists():
            return False

        # Pre-commit hook
        pre_commit_hook = """#!/bin/bash
# Pre-commit hook for code quality checks

echo "🔍 Running pre-commit checks..."

# Run code formatting
echo "📝 Checking code format..."
make fmt
if [ $? -ne 0 ]; then
    echo "❌ Code formatting failed. Please run 'make fmt' and commit again."
    exit 1
fi

# Run linting
echo "🔍 Running linting..."
make lint
if [ $? -ne 0 ]; then
    echo "❌ Linting failed. Please fix linting issues and commit again."
    exit 1
fi

# Run unit tests
echo "🧪 Running unit tests..."
make test.unit
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed. Please fix failing tests and commit again."
    exit 1
fi

echo "✅ All pre-commit checks passed!"
"""

        # Pre-push hook
        pre_push_hook = """#!/bin/bash
# Pre-push hook for comprehensive checks

echo "🚀 Running pre-push checks..."

# Run full test suite
echo "🧪 Running full test suite..."
make test
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Please fix failing tests and push again."
    exit 1
fi

# Run security checks
echo "🔒 Running security checks..."
make security
if [ $? -ne 0 ]; then
    echo "❌ Security checks failed. Please fix security issues and push again."
    exit 1
fi

# Run coverage check
echo "📊 Running coverage check..."
make coverage
if [ $? -ne 0 ]; then
    echo "⚠️  Coverage check failed. Please consider adding more tests."
fi

echo "✅ All pre-push checks passed!"
"""

        # 写入hooks
        hooks = {
            "pre-commit": pre_commit_hook,
            "pre-push": pre_push_hook
        }

        success = True
        for hook_name, content in hooks.items():
            hook_path = hooks_dir / hook_name
            try:
                with open(hook_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # 设置执行权限
                os.chmod(hook_path, 0o755)
            except Exception:
                success = False

        return success

    def setup_git_config(self) -> bool:
        """设置Git配置"""

        commands = [
            ["git", "config", "pull.rebase", "true"],
            ["git", "config", "push.default", "simple"],
            ["git", "config", "merge.ff", "only"],
            ["git", "config", "rerere.enabled", "true"],
            ["git", "config", "branch.autosetuprebase", "always"]
        ]

        success = True
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                success = False

        return success

    def create_initial_docs(self) -> bool:
        """创建初始文档"""

        # 更新CLAUDE.md中的Git工作流部分
        claude_file = Path("CLAUDE.md")
        if claude_file.exists():
            try:
                with open(claude_file, encoding='utf-8') as f:
                    content = f.read()

                # 添加Git工作流部分
                git_workflow_section = """

## 🔄 Git工作流

项目采用 **Git Flow** 工作流程，详细说明请参考 [Git工作流规范](docs/GIT_WORKFLOW.md)。

### 分支策略
- `main`: 生产环境代码
- `develop`: 开发集成分支
- `feature/*`: 功能开发分支
- `release/*`: 发布准备分支
- `hotfix/*`: 紧急修复分支

### 快速命令
```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 提交代码（遵循提交信息规范）
git commit -m "feat: add your feature description"

# 同步最新代码
git fetch origin
git rebase origin/develop

# 推送到远程
git push origin feature/your-feature-name
```
"""

                content += git_workflow_section

                with open(claude_file, 'w', encoding='utf-8') as f:
                    f.write(content)

            except Exception:
                return False

        return True

    def run_full_setup(self) -> bool:
        """运行完整的Git Flow设置"""

        steps = [
            ("创建初始分支结构", self.create_initial_branches),
            ("设置分支保护规则", self.setup_branch_protection),
            ("创建GitHub Actions工作流", self.create_workflow_files),
            ("创建Git hooks", self.create_git_hooks),
            ("设置Git配置", self.setup_git_config),
            ("创建初始文档", self.create_initial_docs),
            ("设置团队权限", self.setup_teams)
        ]

        success_count = 0
        total_steps = len(steps)

        for _step_name, step_func in steps:
            try:
                if step_func():
                    success_count += 1
                else:
                    pass
            except Exception:
                pass


        if success_count == total_steps:
            self.print_next_steps()
            return True
        else:
            return False

    def print_next_steps(self):
        """打印后续步骤"""



def main():
    """主函数"""

    # 检查是否在正确的目录
    if not Path("pyproject.toml").exists():
        sys.exit(1)

    # 检查是否是Git仓库
    if not Path(".git").exists():
        sys.exit(1)

    # 创建Git Flow设置器
    setup = GitFlowSetup()

    # 询问用户是否要运行完整设置
    try:
        response = input("是否运行完整的Git Flow设置? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            success = setup.run_full_setup()
            sys.exit(0 if success else 1)
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
