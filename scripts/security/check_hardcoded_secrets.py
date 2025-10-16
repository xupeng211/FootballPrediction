#!/usr/bin/env python3
"""
检查硬编码敏感信息的脚本

扫描代码库中的硬编码密码、API密钥、token等敏感信息
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Pattern

# 需要检查的模式
SECRET_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    # API Keys / Tokens
    ("API Key", re.compile(r'["\']([A-Za-z0-9]{20,})["\'].*api[_-]?key', re.IGNORECASE)),
    ("API Token", re.compile(r'["\']([A-Za-z0-9]{20,})["\'].*token', re.IGNORECASE)),
    ("Authorization Bearer", re.compile(r'authorization:\s*Bearer\s+([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE)),

    # Passwords
    ("Password", re.compile(r'password\s*=\s*["\']([^"\']{8,})["\']', re.IGNORECASE)),
    ("DB Password", re.compile(r'db_password\s*=\s*["\']([^"\']{8,})["\']', re.IGNORECASE)),
    ("Database URL", re.compile(r'(?:mysql|postgresql)://(?!{.*})([^:@\s]+):([^@]+)@', re.IGNORECASE)),

    # Secrets
    ("Secret Key", re.compile(r'[_-]?secret[_-]?\s*=\s*["\']([^"\']{16,})["\']', re.IGNORECASE)),
    ("JWT Secret", re.compile(r'jwt[_-]?secret\s*=\s*["\']([^"\']{16,})["\']', re.IGNORECASE)),

    # AWS Keys
    ("AWS Access Key", re.compile(r'AKIA[0-9A-Z]{16}')),
    ("AWS Secret Key", re.compile(r'["\']([A-Za-z0-9/+=]{40})["\'].*aws.*secret', re.IGNORECASE)),

    # SSH Keys
    ("SSH Private Key", re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----')),

    # Generic patterns
    ("Base64 Secret", re.compile(r'["\']([A-Za-z0-9+/]{40,}={0,2})["\'].*secret', re.IGNORECASE)),

    # Hardcoded URLs with credentials
    ("URL with credentials", re.compile(r'https?://[^:]+:([^@]+)@[^/]+', re.IGNORECASE)),
]

# 忽略的文件和目录
IGNORE_PATTERNS = [
    r'\.git/',
    r'__pycache__/',
    r'\.venv/',
    r'\.env$',
    r'\.env\.example$',
    r'\.log$',
    r'/tests/',
    r'/test_',
    r'/stubs/',
    r'/migrations/',
    r'\.pyc$',
    r'\.pyo$',
    r'\.pyd$',
    r'\.DS_Store$',
    r'\.mypy_cache/',
    r'\.pytest_cache/',
    r'htmlcov/',
    r'\.coverage',
    r'\.tox/',
    r'\.cleanup_backup/',
    r'\.cleanup_archive/',
    r'/archive/',
    r'/node_modules/',
    r'\.cache/',
]

# 白名单 - 这些是示例值，不是真实的密钥
FALSE_POSITIVES = [
    "your-",
    "your_",
    "example",
    "test",
    "mock",
    "fake",
    "dummy",
    "placeholder",
    "xxx",
    "yyy",
    "zzz",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "change-this",
    "please-change",
    "secret-key-here",
    "password-here",
    "token-here",
]

def should_ignore_file(file_path: Path) -> bool:
    """检查文件是否应该被忽略"""
    path_str = str(file_path)
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, path_str):
            return True
    return False

def is_false_positive(secret: str) -> bool:
    """检查是否是误报"""
    secret_lower = secret.lower()
    for fp in FALSE_POSITIVES:
        if fp in secret_lower:
            return True
    return False

def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    扫描单个文件

    Returns:
        List of (line_number, secret_type, matched_text)
    """
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️  无法读取文件 {file_path}: {e}")
        return findings

    for line_num, line in enumerate(lines, 1):
        for secret_type, pattern in SECRET_PATTERNS:
            matches = pattern.finditer(line)
            for match in matches:
                secret_value = match.group(1) if match.groups() else match.group(0)

                # 跳过误报
                if is_false_positive(secret_value):
                    continue

                # 跳过注释
                if line.strip().startswith('#'):
                    continue

                findings.append((line_num, secret_type, secret_value))

    return findings

def main():
    """主函数"""
    if len(sys.argv) > 1:
        scan_dir = Path(sys.argv[1])
    else:
        scan_dir = Path('.')

    print("🔍 扫描硬编码敏感信息...")
    print(f"📁 扫描目录: {scan_dir.absolute()}")
    print("-" * 50)

    total_findings = 0
    files_with_issues = 0

    # 获取所有需要扫描的文件
    scan_extensions = {'.py', '.yml', '.yaml', '.json', '.js', '.ts', '.jsx', '.tsx', '.env', '.conf', '.cfg'}

    for file_path in scan_dir.rglob('*'):
        if not file_path.is_file():
            continue

        if file_path.suffix not in scan_extensions:
            continue

        if should_ignore_file(file_path):
            continue

        findings = scan_file(file_path)
        if findings:
            files_with_issues += 1
            print(f"\n🚨 {file_path.relative_to(scan_dir)}:")
            for line_num, secret_type, secret in findings:
                # 隐藏部分敏感信息
                if len(secret) > 8:
                    masked = secret[:4] + "*" * (len(secret) - 8) + secret[-4:]
                else:
                    masked = "*" * len(secret)
                print(f"  Line {line_num}: {secret_type} -> {masked}")
            total_findings += len(findings)

    print("\n" + "=" * 50)
    print("📊 扫描结果:")
    print(f"  📁 扫描文件数: {len([f for f in scan_dir.rglob('*') if f.is_file() and f.suffix in scan_extensions and not should_ignore_file(f)])}")
    print(f"  🚨 发现问题文件: {files_with_issues}")
    print(f"  ⚠️  发现敏感信息: {total_findings}")

    if total_findings > 0:
        print("\n💡 建议:")
        print("  1. 将硬编码的敏感信息移到环境变量")
        print("  2. 使用 .env.example 作为模板")
        print("  3. 确保 .env 在 .gitignore 中")
        print("  4. 使用密钥管理服务（如 AWS Secrets Manager）")
        print("  5. 在 CI/CD 中添加安全扫描")
        sys.exit(1)
    else:
        print("\n✅ 未发现硬编码的敏感信息！")
        sys.exit(0)

if __name__ == "__main__":
    main()
