#!/usr/bin/env python3
"""
开发环境安全设置脚本
配置开发环境的安全防护措施
"""

import os
import sys
import subprocess
from pathlib import Path

class DevSecuritySetup:
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

    def install_security_tools(self):
        """安装安全工具"""
        self.log("\n🔧 安装安全工具...", "HIGHLIGHT")

        tools = [
            "pip-audit",      # 依赖漏洞扫描
            "bandit",         # 代码安全扫描
            "safety",         # 安全检查
            "semgrep",        # 静态分析
            "checkov",        # 基础设施安全扫描
        ]

        for tool in tools:
            try:
                self.log(f"  安装 {tool}...", "INFO")
                subprocess.run([sys.executable, "-m", "pip", "install", tool],
                             check=True, capture_output=True)
                self.log(f"  ✅ {tool} 安装成功", "SUCCESS")
            except subprocess.CalledProcessError:
                self.log(f"  ❌ {tool} 安装失败", "ERROR")

    def setup_pre_commit_hooks(self):
        """设置pre-commit hooks"""
        self.log("\n🪝 设置Pre-commit Hooks...", "HIGHLIGHT")

        # 安装pre-commit
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pre-commit"],
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.log("  pre-commit 安装失败", "ERROR")
            return

        # 创建.pre-commit-config.yaml
        config = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-yaml
      - id: debug-statements
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-toml
      - id: check-json
      - id: check-xml
      - id: detect-aws-credentials
      - id: detect-private-key

  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.6
    hooks:
      - id: bandit
        args: ['-c', '.bandit']
        additional_dependencies: ['bandit[toml]']

  - repo: https://github.com/pycqa/isort
    rev: 6.0.1
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/psf/black
    rev: 25.1.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 7.1.1
    hooks:
      - id: flake8
        additional_dependencies:
          - flake8-docstrings
          - flake8-bugbear
          - flake8-comprehensions
          - flake8-simplify

  - repo: https://github.com/PyCQA/pydocstyle
    rev: 6.3.0
    hooks:
      - id: pydocstyle
        args: ['--convention=google']

  - repo: local
    hooks:
      - id: pip-audit
        name: pip-audit
        entry: pip-audit
        language: system
        args: ['-r', 'requirements.txt', '--format', 'table']
        pass_filenames: false
        always_run: true
"""

        config_path = self.project_root / ".pre-commit-config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config)

        self.log(f"  ✅ Pre-commit配置已创建: {config_path.name}", "SUCCESS")

        # 安装hooks
        try:
            subprocess.run(["pre-commit", "install"], cwd=self.project_root, check=True)
            self.log("  ✅ Pre-commit hooks已安装", "SUCCESS")
        except subprocess.CalledProcessError:
            self.log("  ❌ Pre-commit hooks安装失败", "ERROR")

    def create_dev_env_file(self):
        """创建开发环境配置"""
        self.log("\n📝 创建开发环境配置...", "INFO")

        dev_env = """# 开发环境配置
# 这是一个示例配置文件，复制为 .env.local 并修改值

# 基础配置
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# 数据库（开发使用SQLite）
DB_URL=sqlite:///./football_dev.db
# 或者使用PostgreSQL（需要先启动）
# DB_URL=postgresql://postgres:password@localhost:5432/football_prediction_dev

# Redis（开发可选）
REDIS_URL=redis://localhost:6379/0

# API密钥（开发可以使用测试值）
FOOTBALL_API_KEY=test_api_key_development
ODDS_API_KEY=test_odds_key_development

# JWT配置（开发使用弱密钥）
JWT_SECRET_KEY=development-secret-key-not-for-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# CORS（开发允许所有源）
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000

# 安全配置（开发环境关闭）
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_CONTENT_TYPE_NOSNIFF=False
SECURE_BROWSER_XSS_FILTER=False

# 测试配置
TESTING=False
TEST_DB_URL=sqlite:///./football_test.db
"""

        dev_env_path = self.project_root / ".env.development"
        with open(dev_env_path, 'w', encoding='utf-8') as f:
            f.write(dev_env)

        self.log(f"  ✅ 开发环境配置已创建: {dev_env_path.name}", "SUCCESS")

    def setup_git_secrets(self):
        """设置git-secrets防止提交敏感信息"""
        self.log("\n🔐 设置Git Secrets...", "HIGHLIGHT")

        # 检查是否已安装git-secrets
        try:
            subprocess.run(["git-secrets", "--help"], capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("  git-secrets未安装，跳过", "WARN")
            return

        # 初始化git-secrets
        try:
            subprocess.run(["git-secrets", "--register-aws"], cwd=self.project_root)
            subprocess.run(["git-secrets", "--install"], cwd=self.project_root)

            # 添加自定义模式
            patterns = [
                "password\\s*=\\s*['\\\"][^'\\\"]+['\\\"]",
                "secret\\s*=\\s*['\\\"][^'\\\"]+['\\\"]",
                "api_key\\s*=\\s*['\\\"][^'\\\"]+['\\\"]",
                "token\\s*=\\s*['\\\"][^'\\\"]+['\\\"][^'\\\"]+['\\\"]",
                "AKIA[0-9A-Z]{16}",
                "[0-9a-f]{32,}",
            ]

            for pattern in patterns:
                subprocess.run(["git-secrets", "--add", pattern], cwd=self.project_root)

            self.log("  ✅ Git Secrets配置完成", "SUCCESS")
        except subprocess.CalledProcessError as e:
            self.log(f"  ❌ Git Secrets配置失败: {e}", "ERROR")

    def create_security_scripts(self):
        """创建安全检查脚本"""
        self.log("\n📜 创建安全检查脚本...", "INFO")

        # 创建安全检查脚本
        security_check = """#!/bin/bash
# 安全检查脚本

echo "🔍 执行安全检查..."

echo "1. 扫描依赖漏洞..."
pip-audit -r requirements.txt --severity="high,critical"

echo -e "\n2. 扫描代码安全问题..."
bandit -r src/ -f text

echo -e "\n3. 检查敏感文件..."
find . -type f -name "*.env*" -not -path "./.git/*" | head -10

echo -e "\n4. 检查权限问题..."
find . -type f -name "*.key" -o -name "*.pem" | head -10

echo -e "\n✅ 安全检查完成"
"""

        script_path = self.project_root / "scripts" / "security-check.sh"
        with open(script_path, 'w') as f:
            f.write(security_check)
        os.chmod(script_path, 0o755)

        self.log(f"  ✅ 安全检查脚本已创建: security-check.sh", "SUCCESS")

    def run(self):
        """运行所有设置"""
        self.log("=" * 70)
        self.log("开始设置开发环境安全防护...", "SUCCESS")
        self.log("=" * 70)

        self.install_security_tools()
        self.setup_pre_commit_hooks()
        self.create_dev_env_file()
        self.setup_git_secrets()
        self.create_security_scripts()

        self.log("\n" + "=" * 70)
        self.log("开发环境安全设置完成！", "SUCCESS")
        self.log("\n下一步操作:", "HIGHLIGHT")
        self.log("1. 复制 .env.development 为 .env.local", "INFO")
        self.log("2. 运行 ./scripts/security-check.sh 测试安全检查", "INFO")
        self.log("3. 提交代码会自动运行安全检查", "INFO")
        self.log("=" * 70)


if __name__ == "__main__":
    setup = DevSecuritySetup()
    setup.run()