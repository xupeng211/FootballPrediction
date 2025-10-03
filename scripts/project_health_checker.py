#!/usr/bin/env python3
"""
项目健康检查器
深度检查项目中的各种严重问题
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

class ProjectHealthChecker:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.issues = {
            'critical': [],    # 严重问题
            'warning': [],     # 警告
            'info': [],        # 信息
            'suggestion': []   # 建议
        }
        self.stats = {
            'files_checked': 0,
            'lines_analyzed': 0,
            'dependencies': 0,
            'security_issues': 0
        }

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "CRITICAL": "\033[1;31m",
            "ERROR": "\033[0;31m",
            "WARN": "\033[0;33m",
            "INFO": "\033[0m",
            "SUCCESS": "\033[0;32m",
            "HIGHLIGHT": "\033[1;34m"
        }
        color = colors.get(level, "\033[0m")
        print(f"{color}[{timestamp}] {level}: {message}\033[0m")

    def add_issue(self, category: str, severity: str, description: str, file_path: str = None, line: int = None):
        """添加问题到列表"""
        issue = {
            'category': category,
            'description': description,
            'file': str(file_path) if file_path else None,
            'line': line
        }
        self.issues[severity].append(issue)

        # 显示问题
        if severity == 'critical':
            self.log(f"❌ {description} ({file_path}:{line if line else '?'})", "CRITICAL")
        elif severity == 'warning':
            self.log(f"⚠️ {description} ({file_path}:{line if line else '?'})", "WARN")
        elif severity == 'info':
            self.log(f"ℹ️ {description}", "INFO")
        else:
            self.log(f"💡 {description}", "INFO")

    def check_dependencies(self):
        """检查依赖问题"""
        self.log("\n🔍 检查项目依赖...", "HIGHLIGHT")

        # 检查requirements文件
        req_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "requirements.lock"
        ]

        for req_file in req_files:
            file_path = self.project_root / req_file
            if file_path.exists():
                self.log(f"  检查 {req_file}...", "INFO")

                with open(file_path, 'r') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # 检查版本固定问题
                    if '==' not in line and not line.startswith('-e'):
                        self.add_issue(
                            '依赖管理',
                            'warning',
                            f"依赖未固定版本: {line}",
                            req_file,
                            i
                        )

                    # 检查已知的安全问题包
                    if any(pkg in line.lower() for pkg in ['urllib3==1.', 'requests==2.', 'jinja2==2.', 'pyyaml==5.']):
                        self.add_issue(
                            '安全',
                            'critical',
                            f"可能存在安全漏洞的旧版本: {line}",
                            req_file,
                            i
                        )

                    self.stats['dependencies'] += 1

        # 检查poetry/pipenv/pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            self.log("  检查 pyproject.toml...", "INFO")
            # 检查依赖版本冲突
            try:
                result = subprocess.run(
                    ['pip', 'check'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    self.add_issue(
                        '依赖管理',
                        'critical',
                        f"依赖冲突: {result.stderr.strip()}",
                        "pip-check"
                    )
            except subprocess.TimeoutExpired:
                self.add_issue(
                    '依赖管理',
                    'warning',
                    "pip check 超时",
                    "pip-check"
                )

    def check_security_issues(self):
        """检查安全问题"""
        self.log("\n🔒 检查安全问题...", "HIGHLIGHT")

        # 检查敏感文件
        sensitive_patterns = [
            ('**/.env', '环境变量文件可能包含敏感信息'),
            ('**/config/secrets.yaml', '配置文件可能包含密钥'),
            ('**/id_rsa', 'SSH私钥'),
            ('**/*.pem', '证书文件'),
            ('**/*.key', '私钥文件'),
            ('**/passwords.txt', '密码文件'),
            ('**/api_keys.txt', 'API密钥文件'),
        ]

        for pattern, description in sensitive_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and '.git' not in str(file_path):
                    self.add_issue(
                        '安全',
                        'critical',
                        description,
                        file_path
                    )
                    self.stats['security_issues'] += 1

        # 检查代码中的硬编码密钥
        key_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', '硬编码密码'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', '硬编码API密钥'),
            (r'secret\s*=\s*["\'][^"\']+["\']', '硬编码密钥'),
            (r'token\s*=\s*["\'][^"\']+["\']', '硬编码Token'),
            (r'aws_secret_access_key\s*=\s*["\'][^"\']+["\']', 'AWS密钥'),
        ]

        for py_file in self.project_root.glob('**/*.py'):
            if '.git' in str(py_file) or 'venv' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    for pattern, description in key_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.add_issue(
                                '安全',
                                'critical',
                                f"{description}: {line.strip()[:50]}...",
                                py_file,
                                i
                            )
                            self.stats['security_issues'] += 1

                self.stats['files_checked'] += 1
                self.stats['lines_analyzed'] += len(lines)
            except UnicodeDecodeError:
                continue

    def check_code_quality(self):
        """检查代码质量问题"""
        self.log("\n📊 检查代码质量...", "HIGHLIGHT")

        # 检查大文件
        for py_file in self.project_root.glob('**/*.py'):
            if '.git' in str(py_file) or 'venv' in str(py_file):
                continue

            if py_file.is_file():
                try:
                    lines = sum(1 for _ in open(py_file, 'r', encoding='utf-8'))
                    if lines > 500:
                        self.add_issue(
                            '代码质量',
                            'warning',
                            f"文件过大({lines}行): 建议拆分",
                            py_file
                        )
                except:
                    pass

        # 检查重复文件
        file_hashes = {}
        for py_file in self.project_root.glob('**/*.py'):
            if '.git' in str(py_file) or 'venv' in str(py_file):
                continue

            if py_file.is_file() and py_file.stat().st_size < 100000:  # 小于100KB
                try:
                    with open(py_file, 'rb') as f:
                        content = f.read()
                        file_hash = hash(content)

                    if file_hash in file_hashes:
                        self.add_issue(
                            '代码质量',
                            'warning',
                            f"重复文件: 与 {file_hashes[file_hash]} 相同",
                            py_file
                        )
                    else:
                        file_hashes[file_hash] = py_file
                except:
                    pass

        # 检查TODO/FIXME
        todo_patterns = [
            (r'#\s*TODO[:\s]', '待办事项'),
            (r'#\s*FIXME[:\s]', '需要修复'),
            (r'#\s*HACK[:\s]', '临时解决方案'),
            (r'#\s*XXX[:\s]', '问题代码'),
        ]

        for py_file in self.project_root.glob('**/*.py'):
            if '.git' in str(py_file) or 'venv' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    for pattern, description in todo_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.add_issue(
                                '代码质量',
                                'info',
                                f"{description}: {line.strip()}",
                                py_file,
                                i
                            )
            except:
                pass

    def check_database_issues(self):
        """检查数据库相关问题"""
        self.log("\n🗄️ 检查数据库配置...", "HIGHLIGHT")

        # 检查数据库配置
        config_patterns = [
            ('**/*.env', 'DATABASE_URL'),
            ('**/config/*.py', 'database'),
            ('**/config/*.yaml', 'database'),
            ('**/config/*.yml', 'database'),
        ]

        for pattern, search in config_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            if 'password' in content.lower() and search in content.lower():
                                self.add_issue(
                                    '安全',
                                    'warning',
                                    f"数据库配置可能包含明文密码",
                                    file_path
                                )
                    except:
                        pass

        # 检查迁移文件
        migrations_dir = self.project_root / "src/database/migrations"
        if migrations_dir.exists():
            migration_files = list(migrations_dir.glob('**/*.py'))
            if len(migration_files) > 50:
                self.add_issue(
                    '数据库',
                    'warning',
                    f"迁移文件过多({len(migration_files)}): 考虑合并或清理"
                )

    def check_ci_cd_issues(self):
        """检查CI/CD配置问题"""
        self.log("\n🔄 检查CI/CD配置...", "HIGHLIGHT")

        # 检查GitHub Actions
        workflows_dir = self.project_root / ".github/workflows"
        if workflows_dir.exists():
            for workflow_file in workflows_dir.glob("*.yml"):
                with open(workflow_file, 'r') as f:
                    content = f.read()

                # 检查安全问题
                if '${{ secrets.' in content and 'GITHUB_TOKEN' in content:
                    self.add_issue(
                        'CI/CD',
                        'warning',
                        "工作流可能泄露敏感信息",
                        workflow_file
                    )

                # 检查权限问题
                if 'permissions: write-all' in content:
                    self.add_issue(
                        'CI/CD',
                        'warning',
                        "工作流权限过高",
                        workflow_file
                    )

    def check_performance_issues(self):
        """检查性能问题"""
        self.log("\n⚡ 检查性能问题...", "HIGHLIGHT")

        # 检查可能的性能问题
        performance_patterns = [
            (r'time\.sleep\(', '使用time.sleep可能阻塞'),
            (r'subprocess\.call\(', '使用subprocess.call可能阻塞'),
            (r'os\.system\(', '使用os.system不安全'),
            (r'eval\(', '使用eval不安全'),
            (r'exec\(', '使用exec不安全'),
        ]

        for py_file in self.project_root.glob('**/*.py'):
            if '.git' in str(py_file) or 'venv' in str(py_file) or 'tests' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    for pattern, description in performance_patterns:
                        if re.search(pattern, line):
                            self.add_issue(
                                '性能',
                                'warning',
                                f"{description}: {line.strip()[:50]}...",
                                py_file,
                                i
                            )
            except:
                pass

    def check_docker_issues(self):
        """检查Docker相关问题"""
        self.log("\n🐳 检查Docker配置...", "HIGHLIGHT")

        # 检查Dockerfile
        dockerfile = self.project_root / "Dockerfile"
        if dockerfile.exists():
            with open(dockerfile, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                line = line.strip()

                # 检安全问题
                if 'ADD http' in line:
                    self.add_issue(
                        'Docker',
                        'warning',
                        "使用ADD下载远程文件不安全",
                        "Dockerfile",
                        i
                    )

                # 检查最佳实践
                if 'FROM latest' in line:
                    self.add_issue(
                        'Docker',
                        'warning',
                        "不建议使用latest标签",
                        "Dockerfile",
                        i
                    )

                if 'USER root' in line or line == 'USER root':
                    self.add_issue(
                        'Docker',
                        'warning',
                        "不建议使用root用户运行",
                        "Dockerfile",
                        i
                    )

    def check_project_structure(self):
        """检查项目结构问题"""
        self.log("\n📁 检查项目结构...", "HIGHLIGHT")

        # 检查必要的文件
        required_files = [
            ('README.md', '项目说明文件'),
            ('requirements.txt', '依赖文件'),
            ('.gitignore', 'Git忽略文件'),
            ('pyproject.toml', '项目配置文件'),
        ]

        for file, description in required_files:
            if not (self.project_root / file).exists():
                self.add_issue(
                    '项目结构',
                    'warning',
                    f"缺少{description}: {file}"
                )

        # 检查空目录
        for root, dirs, files in os.walk(self.project_root):
            if '.git' in root or 'venv' in root or '__pycache__' in root:
                continue

            if not files and not dirs:
                self.add_issue(
                    '项目结构',
                    'info',
                    f"空目录: {root}"
                )

    def generate_report(self):
        """生成健康检查报告"""
        self.log("\n" + "=" * 80)
        self.log("项目健康检查完成!", "SUCCESS")

        # 统计信息
        total_issues = sum(len(issues) for issues in self.issues.values())
        self.log(f"\n📊 检查统计:", "HIGHLIGHT")
        self.log(f"  文件数: {self.stats['files_checked']}")
        self.log(f"  代码行数: {self.stats['lines_analyzed']}")
        self.log(f"  依赖数: {self.stats['dependencies']}")
        self.log(f"  安全问题: {self.stats['security_issues']}")
        self.log(f"  总问题数: {total_issues}")

        # 问题分类统计
        self.log(f"\n🔍 问题分布:", "HIGHLIGHT")
        for severity, issues in self.issues.items():
            if issues:
                color = {
                    'critical': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️',
                    'suggestion': '💡'
                }[severity]
                self.log(f"  {color} {severity.capitalize()}: {len(issues)}")

        # 严重问题详情
        if self.issues['critical']:
            self.log(f"\n🚨 严重问题详情:", "CRITICAL")
            for issue in self.issues['critical'][:10]:  # 只显示前10个
                location = f" ({issue['file']}:{issue['line']})" if issue['file'] else ""
                self.log(f"  • {issue['description']}{location}")
            if len(self.issues['critical']) > 10:
                self.log(f"  ... 还有 {len(self.issues['critical']) - 10} 个严重问题")

        # 保存详细报告
        self.save_health_report()

        self.log("\n" + "=" * 80)

    def save_health_report(self):
        """保存健康检查报告"""
        report_path = self.project_root / "docs" / "_reports"
        report_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"health_check_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 项目健康检查报告\n\n")
            f.write(f"**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**检查工具**: scripts/project_health_checker.py\n\n")

            f.write("## 检查统计\n\n")
            f.write("| 项目 | 数量 |\n")
            f.write("|------|------|\n")
            f.write(f"| 检查的文件 | {self.stats['files_checked']} |\n")
            f.write(f"| 代码行数 | {self.stats['lines_analyzed']} |\n")
            f.write(f"| 依赖数量 | {self.stats['dependencies']} |\n")
            f.write(f"| 安全问题 | {self.stats['security_issues']} |\n\n")

            # 问题详情
            for severity in ['critical', 'warning', 'info', 'suggestion']:
                issues = self.issues[severity]
                if issues:
                    f.write(f"## {severity.capitalize()} 级问题 ({len(issues)}个)\n\n")
                    for issue in issues:
                        location = ""
                        if issue['file']:
                            location = f" ({issue['file']}"
                            if issue['line']:
                                location += f":{issue['line']}"
                            location += ")"
                        f.write(f"- **{issue['category']}**: {issue['description']}{location}\n")
                    f.write("\n")

            # 建议
            f.write("## 改进建议\n\n")
            f.write("1. 立即修复所有critical级别问题\n")
            f.write("2. 尽快处理warning级别问题\n")
            f.write("3. 定期运行健康检查\n")
            f.write("4. 建立代码审查流程\n")
            f.write("5. 使用安全扫描工具\n")

        self.log(f"\n📄 详细报告已保存: {report_file.relative_to(self.project_root)}")

    def run_checks(self):
        """运行所有检查"""
        self.log("🔍 开始项目健康检查...", "HIGHLIGHT")
        self.log(f"项目路径: {self.project_root}")

        # 执行各项检查
        self.check_dependencies()
        self.check_security_issues()
        self.check_code_quality()
        self.check_database_issues()
        self.check_ci_cd_issues()
        self.check_performance_issues()
        self.check_docker_issues()
        self.check_project_structure()

        # 生成报告
        self.generate_report()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="项目健康检查工具")
    parser.add_argument("--project-root", help="项目根目录路径", default=None)

    args = parser.parse_args()

    checker = ProjectHealthChecker(args.project_root)
    checker.run_checks()