#!/usr/bin/env python3
"""
敏感信息扫描脚本
扫描代码库中的硬编码密码、API密钥和令牌等敏感信息。
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

class SecretScanner:
    """敏感信息扫描器"""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.secrets_found = []

        # 敏感信息模式
        self.patterns = {
            "password": [
                r'password\s*=\s*["\'][^"\']{4,}["\']',
                r'pwd\s*=\s*["\'][^"\']{4,}["\']',
                r'passwd\s*=\s*["\'][^"\']{4,}["\']',
                r'pass\s*=\s*["\'][^"\']{4,}["\']',
            ],
            "api_key": [
                r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']',
                r'apikey\s*=\s*["\'][^"\']{10,}["\']',
                r'API[_-]?KEY\s*=\s*["\'][^"\']{10,}["\']',
            ],
            "token": [
                r'token\s*=\s*["\'][^"\']{10,}["\']',
                r'auth[_-]?token\s*=\s*["\'][^"\']{10,}["\']',
                r'TOKEN\s*=\s*["\'][^"\']{10,}["\']',
            ],
            "secret": [
                r'secret\s*=\s*["\'][^"\']{8,}["\']',
                r'client[_-]?secret\s*=\s*["\'][^"\']{8,}["\']',
                r'SECRET[_-]?KEY\s*=\s*["\'][^"\']{8,}["\']',
            ],
            "database_url": [
                r'database[_-]?url\s*=\s*["\'][^"\']*password[^"\']*["\']',
                r'DATABASE[_-]?URL\s*=\s*["\'][^"\']*password[^"\']*["\']',
            ],
            "connection_string": [
                r'connection[_-]?string\s*=\s*["\'][^"\']*password[^"\']*["\']',
                r'CONNECTION[_-]?STRING\s*=\s*["\'][^"\']*password[^"\']*["\']',
            ],
            "hardcoded_credentials": [
                r'postgres[^a-zA-Z]*:([^@\s]){4,}[^@\s]*@',
                r'mysql[^a-zA-Z]*:([^@\s]){4,}[^@\s]*@',
                r'root:[^@\s]{4,}@',
                r'admin:[^@\s]{4,}@',
            ],
            "private_key": [
                r'-----BEGIN (RSA |OPENSSH |DSA |EC |PGP )?PRIVATE KEY-----',
                r'-----BEGIN ENCRYPTED PRIVATE KEY-----',
            ],
            "aws_credentials": [
                r'AKIA[0-9A-Z]{16}',  # AWS Access Key ID
                r'[0-9a-zA-Z/+=]{40}',  # AWS Secret Access Key pattern
            ],
        }

        # 排除的目录
        self.exclude_dirs = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules',
            'venv', 'env', '.venv', '.env', 'htmlcov', '.mypy_cache',
            '.coverage', 'dist', 'build', '.tox'
        }

        # 排除的文件模式
        self.exclude_files = {
            '*.pyc', '*.pyo', '*.pyd', '*.log', '*.tmp', '*.swp',
            '*.swo', '*~', '.DS_Store', 'Thumbs.db'
        }

    def should_exclude_file(self, file_path: Path) -> bool:
        """检查文件是否应该被排除"""
        # 检查目录
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return True

        # 检查文件模式
        for pattern in self.exclude_files:
            if file_path.match(pattern):
                return True

        # 只扫描Python文件
        if not file_path.suffix == '.py':
            return True

        return False

    def scan_file(self, file_path: Path) -> list[tuple[str, int, str, str]]:
        """扫描单个文件"""
        secrets = []

        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line_content = line.strip()

                # 跳过注释行
                if line_content.startswith('#') or line_content.startswith('"""') or line_content.startswith("'''"):
                    continue

                # 跳过明显的示例代码
                if 'example' in line_content.lower() or 'dummy' in line_content.lower():
                    continue

                for secret_type, patterns in self.patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, line_content, re.IGNORECASE)
                        for match in matches:
                            secrets.append((
                                secret_type,
                                line_num,
                                line_content,
                                match.group()
                            ))

        except Exception as e:
            print(f"警告：无法读取文件 {file_path}: {e}")

        return secrets

    def scan_directory(self) -> None:
        """扫描整个目录"""
        print("🔍 开始敏感信息扫描...")
        print(f"📁 扫描目录: {self.root_path.absolute()}")
        print("=" * 60)

        scanned_files = 0

        for py_file in self.root_path.rglob("*.py"):
            if not self.should_exclude_file(py_file):
                scanned_files += 1
                file_secrets = self.scan_file(py_file)

                if file_secrets:
                    self.secrets_found.extend([(str(py_file), *secret) for secret in file_secrets])

        print(f"📊 扫描完成！共检查 {scanned_files} 个 Python 文件")
        print("=" * 60)

    def report_results(self) -> bool:
        """报告扫描结果"""
        if not self.secrets_found:
            print("✅ 未发现敏感信息泄露")
            print("🛡️ 代码库安全性检查通过")
            return True

        print(f"🚨 发现 {len(self.secrets_found)} 处潜在敏感信息：")
        print("=" * 80)

        # 按文件分组显示结果
        file_secrets = {}
        for file_path, secret_type, line_num, line_content, match in self.secrets_found:
            if file_path not in file_secrets:
                file_secrets[file_path] = []
            file_secrets[file_path].append((secret_type, line_num, line_content, match))

        for file_path, secrets in file_secrets.items():
            print(f"\n📄 文件: {file_path}")
            print("-" * 60)

            for secret_type, line_num, line_content, match in secrets:
                print(f"  🔴 类型: {secret_type}")
                print(f"  📍 行号: {line_num}")
                print(f"  📝 内容: {line_content[:80]}...")
                print(f"  🎯 匹配: {match[:60]}...")
                print()

        print("=" * 80)
        print("⚠️  请立即处理以上敏感信息！")
        print("💡 建议：")
        print("   1. 使用环境变量存储敏感信息")
        print("   2. 使用 .env 文件并确保 .env 在 .gitignore 中")
        print("   3. 使用密钥管理服务（如 AWS Secrets Manager）")

        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."

    scanner = SecretScanner(root_path)

    try:
        scanner.scan_directory()
        is_safe = scanner.report_results()

        if not is_safe:
            print("\n❌ 安全检查失败！")
            sys.exit(1)
        else:
            print("\n✅ 安全检查通过！")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n⏹️  扫描被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 扫描过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
