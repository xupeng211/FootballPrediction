#!/usr/bin/env python3
"""
一键修复所有严重问题
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

class CriticalIssuesFixer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.fixes_applied = []
        self.errors = []

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

    def run_command(self, cmd: str, description: str) -> bool:
        """运行命令并记录结果"""
        self.log(f"执行: {description}", "INFO")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                self.log(f"✅ {description} - 成功", "SUCCESS")
                self.fixes_applied.append(description)
                return True
            else:
                self.log(f"❌ {description} - 失败: {result.stderr}", "ERROR")
                self.errors.append(f"{description}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.log(f"❌ {description} - 超时", "ERROR")
            self.errors.append(f"{description}: 超时")
            return False
        except Exception as e:
            self.log(f"❌ {description} - 异常: {e}", "ERROR")
            self.errors.append(f"{description}: {e}")
            return False

    def fix_security_issues(self):
        """修复安全问题"""
        self.log("\n🔒 修复安全问题...", "HIGHLIGHT")

        # 1. 修复硬编码密码
        self.log("\n1. 修复硬编码密码", "INFO")
        if self.run_command(
            "python scripts/security/password_fixer.py",
            "扫描并修复硬编码密码"
        ):
            self.log("   生成了 .env.template 和 .env.example", "INFO")

        # 2. 保护敏感文件
        self.log("\n2. 保护敏感文件", "INFO")
        if self.run_command(
            "python scripts/security/protect_sensitive_files.py",
            "更新 .gitignore 保护敏感文件"
        ):
            self.log("   敏感文件已加入 .gitignore", "INFO")

        # 3. 更新依赖
        self.log("\n3. 更新依赖包", "INFO")
        deps_to_update = ["requests", "urllib3", "pyyaml", "jinja2"]
        for dep in deps_to_update:
            self.run_command(
                f"pip install --upgrade {dep}",
                f"更新 {dep}"
            )

        # 4. 重新生成 requirements
        self.run_command(
            "pip freeze > requirements.txt",
            "更新 requirements.txt"
        )

        # 5. 安装安全扫描工具
        self.run_command(
            "pip install pip-audit bandit safety",
            "安装安全扫描工具"
        )

        # 6. 运行安全扫描
        self.log("\n6. 运行安全扫描", "INFO")
        self.run_command(
            "pip-audit --requirements=requirements.txt",
            "扫描依赖漏洞"
        )

    def fix_code_quality(self):
        """修复代码质量问题"""
        self.log("\n📊 修复代码质量问题...", "HIGHLIGHT")

        # 1. 清理大文件（报告但不自动拆分，需要手动处理）
        self.log("\n1. 检查大文件", "INFO")
        self.run_command(
            "python scripts/quality/check_file_sizes.py --list-only",
            "列出需要拆分的大文件"
        )

        # 2. 清理重复文件
        self.log("\n2. 清理重复文件", "INFO")
        if self.run_command(
            "python scripts/refactoring/clean_duplicates.py",
            "删除重复文件"
        ):
            self.log("   重复文件已清理", "INFO")

        # 3. 清理 legacy 测试
        self.log("\n3. 清理 legacy 代码", "INFO")
        if Path("tests/legacy").exists():
            self.run_command(
                "mv tests/legacy tests/legacy_backup",
                "备份 legacy 测试"
            )

        # 4. 修复导入
        self.run_command(
            "python scripts/refactoring/fix_imports.py",
            "修复导入问题"
        )

    def run_tests(self):
        """运行测试验证修复"""
        self.log("\n🧪 运行测试验证...", "HIGHLIGHT")

        # 1. 快速测试
        self.run_command(
            "pytest tests/unit/ -v --tb=short -x",
            "运行单元测试"
        )

        # 2. 代码检查
        self.run_command(
            "ruff check src/ --fix",
            "运行 ruff 检查并自动修复"
        )

        # 3. 格式化
        self.run_command(
            "ruff format src/",
            "格式化代码"
        )

    def generate_report(self):
        """生成修复报告"""
        report_path = self.project_root / "docs" / "_reports"
        report_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"critical_fixes_execution_report_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 严重问题修复执行报告\n\n")
            f.write(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**分支**: {subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()}\n\n")

            f.write("## 修复项目\n\n")
            for fix in self.fixes_applied:
                f.write(f"✅ {fix}\n")

            if self.errors:
                f.write("\n## 错误列表\n\n")
                for error in self.errors:
                    f.write(f"❌ {error}\n")

            f.write("\n## 后续步骤\n\n")
            f.write("1. 检查 .env.template 并创建 .env.local\n")
            f.write("2. 填写实际的环境变量值\n")
            f.write("3. 手动处理大文件拆分（如需要）\n")
            f.write("4. 运行完整测试套件\n")
            f.write("5. 提交修复到版本控制\n")

        self.log(f"\n📄 执行报告已保存: {report_file.relative_to(self.project_root)}")

    def run_all_fixes(self):
        """运行所有修复"""
        self.log("🚀 开始修复所有严重问题...", "HIGHLIGHT")
        self.log(f"项目路径: {self.project_root}")

        # 创建分支（如果不在新分支）
        current_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            text=True
        ).strip()

        if not current_branch.startswith('security/'):
            new_branch = f"security/fixes-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            if self.run_command(
                f"git checkout -b {new_branch}",
                f"创建新分支 {new_branch}"
            ):
                self.log(f"已在分支: {new_branch}", "INFO")

        # 保存当前状态
        self.run_command(
            "git add .",
            "添加所有文件"
        )
        self.run_command(
            "git commit -m 'fix: 保存修复前状态'",
            "提交修复前状态"
        )

        # 执行修复
        self.fix_security_issues()
        self.fix_code_quality()
        self.run_tests()

        # 生成报告
        self.generate_report()

        # 总结
        self.log("\n" + "=" * 80)
        self.log("修复执行完成！", "SUCCESS")
        self.log(f"成功修复: {len(self.fixes_applied)} 项")
        self.log(f"失败: {len(self.errors)} 项")

        if self.errors:
            self.log("\n以下修复失败，需要手动处理:", "WARN")
            for error in self.errors[:5]:
                self.log(f"  - {error}", "ERROR")

        self.log("\n下一步操作:", "HIGHLIGHT")
        self.log("1. cp .env.template .env.local", "INFO")
        self.log("2. 编辑 .env.local 填写实际配置", "INFO")
        self.log("3. git add . && git commit -m 'fix: 修复所有严重安全问题'", "INFO")
        self.log("4. git push origin security/fixes-xxx", "INFO")
        self.log("5. 创建 Pull Request", "INFO")

        self.log("=" * 80)


if __name__ == "__main__":
    # 确保在项目根目录
    if not Path("scripts").exists():
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)

    fixer = CriticalIssuesFixer()
    fixer.run_all_fixes()