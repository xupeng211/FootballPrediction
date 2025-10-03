#!/usr/bin/env python3
"""
密码安全修复工具
自动扫描并修复所有硬编码密码
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

class PasswordFixer:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.fixed_files: List[Dict] = []
        self.errors: List[str] = []
        self.env_vars: Dict[str, str] = {}

        # 密码匹配模式
        self.password_patterns = [
            (r'(\w+)\s*=\s*["\']([^"\']{6,})["\']', 'assignment'),  # 变量 = "密码"
            (r'password\s*=\s*["\']([^"\']+)["\']', 'password'),     # password = "xxx"
            (r'api_key\s*=\s*["\']([^"\']+)["\']', 'api_key'),       # api_key = "xxx"
            (r'secret\s*=\s*["\']([^"\']+)["\']', 'secret'),         # secret = "xxx"
            (r'token\s*=\s*["\']([^"\']+)["\']', 'token'),           # token = "xxx"
            (r'aws_secret_access_key\s*=\s*["\']([^"\']+)["\']', 'aws'),
            (r'auth\s*=\s*\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)', 'auth_tuple'),
        ]

        # 测试密码（这些是测试用的，但仍需要修复）
        self.test_passwords = [
            'test_password', 'test_password_123', 'my_password', 'password123',
            'correct_password', 'wrong_password', 'my_secure_password',
            'test_key', 'test_api_key', 'test_token', 'fake_password'
        ]

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

    def scan_and_fix(self, dry_run: bool = False):
        """扫描并修复所有硬编码密码"""
        self.log(f"🔍 开始扫描项目: {self.project_root}", "HIGHLIGHT")

        if dry_run:
            self.log("⚠️ 试运行模式 - 不会修改文件", "WARN")

        fixed_count = 0
        scanned_count = 0

        for py_file in self.project_root.rglob("*.py"):
            # 跳过某些目录
            if any(skip in str(py_file) for skip in ['.git', 'venv', '__pycache__', '.pytest_cache']):
                continue

            scanned_count += 1
            if self.fix_file(py_file, dry_run):
                fixed_count += 1

        self.log(f"\n📊 扫描完成:", "HIGHLIGHT")
        self.log(f"  扫描文件数: {scanned_count}")
        self.log(f"  修复文件数: {fixed_count}")
        self.log(f"  发现密码数: {len(self.fixed_files)}")
        self.log(f"  错误数: {len(self.errors)}")

        return fixed_count > 0

    def fix_file(self, file_path: Path, dry_run: bool = False) -> bool:
        """修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content

            modified = False
            changes = []

            # 处理密码模式
            for pattern, pattern_type in self.password_patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))

                for match in matches:
                    # 获取匹配的信息
                    groups = match.groups()

                    if pattern_type == 'assignment':
                        var_name = groups[0]
                        password = groups[1]
                    elif pattern_type == 'auth_tuple':
                        # 处理 auth = (os.getenv("PASSWORD_FIXER_AUTH_101_USER"), os.getenv("PASSWORD_FIXER_AUTH_101_PASS")) 格式
                        username = groups[0]
                        password = groups[1]
                        var_name = 'auth'
                    else:
                        password = groups[0] if groups else ''
                        var_name = pattern_type

                    # 跳过明显的非密码（如路径、URL等）
                    if self.is_not_password(password):
                        continue

                    # 记录需要修复的内容
                    old_line = match.group()
                    line_num = content[:match.start()].count('\n') + 1

                    # 生成环境变量名
                    env_var_name = self.generate_env_var_name(var_name, file_path, line_num)

                    # 生成新代码
                    if pattern_type == 'auth_tuple':
                        new_line = f'auth = (os.getenv("{env_var_name}_USER"), os.getenv("{env_var_name}_PASS"))'
                    else:
                        new_line = f'{var_name} = os.getenv("{env_var_name}")'

                    changes.append({
                        'line': line_num,
                        'old': old_line.strip(),
                        'new': new_line,
                        'env_var': env_var_name,
                        'password': password
                    })

                    # 应用修改
                    if not dry_run:
                        content = content.replace(old_line, new_line)
                        modified = True

            # 添加os导入（如果需要且不存在）
            if modified and changes and 'import os' not in content and 'from os import' not in content:
                # 找到合适的位置插入import
                lines = content.split('\n')
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_pos = i + 1
                    elif line.startswith('#') and i == 0:
                        continue
                    elif line.strip() == '':
                        continue
                    else:
                        break

                lines.insert(insert_pos, 'import os')
                content = '\n'.join(lines)

            # 保存修改
            if modified and not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # 记录修复信息
            if changes:
                self.fixed_files.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'changes': changes
                })

                # 生成环境变量映射
                for change in changes:
                    if 'env_var' in change:
                        self.env_vars[change['env_var']] = change['password']

                if not dry_run:
                    self.log(f"  ✅ 修复: {file_path.relative_to(self.project_root)} ({len(changes)}处)", "SUCCESS")
                else:
                    self.log(f"  🔍 发现: {file_path.relative_to(self.project_root)} ({len(changes)}处)", "INFO")

                return True

        except Exception as e:
            self.errors.append(f"处理文件失败 {file_path}: {e}")

        return False

    def is_not_password(self, password: str) -> bool:
        """判断是否不是密码"""
        # 跳过明显的非密码
        not_password_patterns = [
            r'https?://',  # URL
            r'/[\w/]+',    # 文件路径
            r'\w+\.\w+',  # 域名
            r'^\d+$',      # 纯数字
            r'^[a-zA-Z]$', # 单字符
            r'^\w{1,3}$',  # 太短的
            r'^\d{4}-\d{2}-\d{2}',  # 日期
            r'^localhost$',
            r'^\d+\.\d+\.\d+\.\d+$',  # IP地址
        ]

        for pattern in not_password_patterns:
            if re.match(pattern, password):
                return True

        return False

    def generate_env_var_name(self, var_name: str, file_path: Path, line_num: int) -> str:
        """生成环境变量名"""
        # 使用文件名和变量名生成唯一的环境变量名
        file_stem = file_path.stem.upper().replace('.', '_').replace('-', '_')

        # 清理变量名
        var_clean = re.sub(r'[^A-Z0-9_]', '', var_name.upper())

        # 组合
        env_var = f"{file_stem}_{var_clean}_{line_num}"

        # 限制长度
        if len(env_var) > 50:
            env_var = env_var[:50]

        return env_var

    def generate_env_template(self) -> str:
        """生成环境变量模板文件"""
        template = """# 安全配置模板
# ⚠️ 警告：包含敏感信息，请勿提交到版本控制系统！
# 1. 复制此文件为 .env.local
# 2. 填写实际的配置值
# 3. 确保 .env.local 已在 .gitignore 中

"""

        # 按文件分组
        by_file = {}
        for file_info in self.fixed_files:
            file_name = file_info['file']
            if file_name not in by_file:
                by_file[file_name] = []
            by_file[file_name].extend(file_info['changes'])

        # 生成模板内容
        for file_name, changes in by_file.items():
            template += f"\n# {file_name}\n"
            for change in changes:
                if 'env_var' in change:
                    # 生成注释说明
                    password = change.get('password', '')
                    if password and not any(test in password for test in self.test_passwords):
                        template += f"# 原值: {password[:10]}... (需要填写实际值)\n"
                    else:
                        template += f"# 请填写实际值\n"
                    template += f"{change['env_var']}=\n\n"

        # 添加一些额外的配置项
        template += """
# 其他常用配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres

REDIS_HOST=localhost
REDIS_PORT=6379

# 应用配置
SECRET_KEY=your-secret-key-here
DEBUG=False
ENVIRONMENT=development
"""

        return template

    def save_env_template(self):
        """保存环境变量模板"""
        template_content = self.generate_env_template()

        # 保存主模板
        template_path = self.project_root / ".env.template"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

        self.log(f"✅ 环境变量模板已生成: {template_path}", "SUCCESS")

        # 创建 .env.example（可以提交的示例）
        example_content = """# 环境变量示例（不含敏感信息）
# 复制为 .env.local 并填写实际值

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres
DB_PASSWORD=your-database-password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# API配置
FOOTBALL_API_KEY=your-football-api-key
ODDS_API_KEY=your-odds-api-key

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret
"""

        example_path = self.project_root / ".env.example"
        with open(example_path, 'w', encoding='utf-8') as f:
            f.write(example_content)

        self.log(f"✅ 环境变量示例已生成: {example_path}", "SUCCESS")

    def save_fix_report(self):
        """保存修复报告"""
        report_path = self.project_root / "docs" / "_reports"
        report_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"password_fix_report_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 密码安全修复报告\n\n")
            f.write(f"**修复时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**修复工具**: scripts/security/password_fixer.py\n\n")

            f.write("## 修复统计\n\n")
            f.write(f"- 修复文件数: {len(self.fixed_files)}\n")
            f.write(f"- 修复密码数: {sum(len(f['changes']) for f in self.fixed_files)}\n")
            f.write(f"- 生成环境变量: {len(self.env_vars)}\n\n")

            if self.fixed_files:
                f.write("## 修复详情\n\n")
                for file_info in self.fixed_files:
                    f.write(f"### {file_info['file']}\n\n")
                    for change in file_info['changes']:
                        f.write(f"- 行 {change['line']}: `{change['old']}`\n")
                        f.write(f"  → `{change['new']}`\n")
                        f.write(f"  → 环境变量: `{change['env_var']}`\n\n")

            if self.errors:
                f.write("## 错误列表\n\n")
                for error in self.errors:
                    f.write(f"- {error}\n")
                f.write("\n")

            f.write("## 后续步骤\n\n")
            f.write("1. 复制 `.env.template` 为 `.env.local`\n")
            f.write("2. 填写实际的配置值\n")
            f.write("3. 确保 `.env.local` 在 `.gitignore` 中\n")
            f.write("4. 运行测试验证修复效果\n")

        self.log(f"📄 修复报告已保存: {report_file.relative_to(self.project_root)}")

    def run(self, dry_run: bool = False, generate_template: bool = True):
        """运行修复流程"""
        self.log("🔧 开始密码安全修复...", "HIGHLIGHT")

        # 扫描和修复
        has_fixes = self.scan_and_fix(dry_run)

        if has_fixes and not dry_run:
            # 生成环境变量模板
            if generate_template:
                self.save_env_template()

            # 保存报告
            self.save_fix_report()

            self.log("\n✅ 密码修复完成！", "SUCCESS")
            self.log(f"共修复 {len(self.fixed_files)} 个文件", "INFO")
            self.log("\n下一步:", "HIGHLIGHT")
            self.log("1. cp .env.template .env.local", "INFO")
            self.log("2. 编辑 .env.local 填写实际值", "INFO")
            self.log("3. 确保 .env.local 在 .gitignore 中", "INFO")
        elif dry_run:
            self.log("\n🔍 试运行完成，请运行不带 --dry-run 的参数进行实际修复", "INFO")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("PASSWORD_FIXER_DESCRIPTION_385"))
    parser.add_argument("--project-root", help="项目根目录", default=None)
    parser.add_argument("--dry-run", action = os.getenv("PASSWORD_FIXER_ACTION_387"), help = os.getenv("PASSWORD_FIXER_HELP_387"))
    parser.add_argument("--no-template", action = os.getenv("PASSWORD_FIXER_ACTION_387"), help = os.getenv("PASSWORD_FIXER_HELP_387"))

    args = parser.parse_args()

    fixer = PasswordFixer(args.project_root)
    fixer.run(dry_run=args.dry_run, generate_template=not args.no_template)