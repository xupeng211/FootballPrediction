#!/usr/bin/env python3
"""P4-3: 敏感信息扫描脚本
扫描代码库中的硬编码敏感信息，并提供修复建议.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from re import Pattern


class SecretScanner:
    """敏感信息扫描器"""

    def __init__(self):
        self.findings = []
        self.scanned_files = 0
        self.skipped_files = 0

        # 敏感信息模式（按严重程度分类）
        self.patterns = {
            "HIGH": [
                # API Keys
                (r'(?i)(?:api[_-]?key|apikey|access[_-]?key)\s*[:=]\s*["\']([a-zA-Z0-9_-]{20,})["\']',
                 "API Key 硬编码"),
                (r'(?i)(?:secret[_-]?key|secretkey|private[_-]?key|privatekey)\s*[:=]\s*["\']([a-zA-Z0-9_-]{20,})["\']',
                 "Secret Key 硬编码"),

                # Passwords
                (r'(?i)(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']',
                 "密码硬编码"),
                (r'(?i)(?:db[_-]?password|database[_-]?password)\s*[:=]\s*["\']([^"\']{8,})["\']',
                 "数据库密码硬编码"),

                # Tokens
                (r'(?i)(?:jwt[_-]?secret|jwtsecret|token[_-]?secret|tokensecret)\s*[:=]\s*["\']([a-zA-Z0-9._-]{20,})["\']',
                 "JWT Secret 硬编码"),
                (r'(?i)(?:auth[_-]?token|authtoken)\s*[:=]\s*["\']([a-zA-Z0-9._-]{20,})["\']',
                 "Auth Token 硬编码"),

                # Credentials
                (r'(?i)(?:user[_-]?name|username)\s*[:=]\s*["\'](?:admin|root|test)[^"\']*["\']\s*[,;]\s*(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{6,})["\']',
                 "默认凭证"),

                # SSH Keys
                (r'(?i)(?:ssh[_-]?key|sshkey|private[_-]?key)\s*[:=]\s*["\']-----BEGIN[^-]*KEY-----[^"\']*-----END[^-]*KEY-----["\']',
                 "SSH 私钥硬编码"),
            ],

            "MEDIUM": [
                # URLs with credentials
                (r'(https?://[^:\s]+:[^@\s]+@[^/\s]+)', "URL 中的凭证"),

                # Connection strings
                (r'(?i)(?:connection[_-]?string|connstr|mongodb[^:]*://)[^:]*://[^:\s]+:[^@;\s]+@', "连接字符串中的凭证"),
                (r'(?i)(?:data[_-]?source|datasource)[^:]*://[^:\s]+:[^@;\s]+@', "数据源连接字符串中的凭证"),

                # Database URLs
                (r'(?i)(?:postgresql|mysql|sqlite)[^:]*://[^:\s]+:[^@;\s]+@', "数据库连接字符串中的凭证"),

                # Environment variables that look like secrets
                (r'(?i)(?:aws[_-]?access[_-]?key|awsaccesskey|aws[_-]?secret[_-]?key|awssecretkey)\s*[:=]\s*["\']([a-zA-Z0-9/+]{20,})["\']',
                 "AWS 访问密钥"),
                (r'(?i)(?:google[_-]?api[_-]?key|googleapikey)\s*[:=]\s*["\']([a-zA-Z0-9_-]{20,})["\']',
                 "Google API Key"),
                (r'(?i)(?:github[_-]?token|githubtoken)\s*[:=]\s*["\'](ghp_[a-zA-Z0-9]{36})["\']',
                 "GitHub Token"),

                # OAuth secrets
                (r'(?i)(?:oauth[_-]?secret|oauthsecret|client[_-]?secret|clientsecret)\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']',
                 "OAuth Secret"),
                (r'(?i)(?:app[_-]?secret|appsecret|consumer[_-]?secret|consumersecret)\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']',
                 "应用 Secret"),
            ],

            "LOW": [
                # Potential sensitive strings
                (r'(?i)(?:admin[_-]?password|adminpassword|test[_-]?password|testpassword)\s*[:=]\s*["\']([^"\']{4,})["\']',
                 "测试密码"),
                (r'(?i)(?:default[_-]?password|defaultpassword)\s*[:=]\s*["\']([^"\']{4,})["\']',
                 "默认密码"),

                # Hardcoded hostnames that might reveal infrastructure
                (r'(?:https?://)(?:admin|api|db|database|staging|dev)[^/\s]*\.(?:local|dev|staging|example\.com)',
                 "开发环境域名暴露"),

                # Common test credentials
                (r'["\'](?:test|demo|sample)[^"\']*(?:password|secret|key)[^"\']*["\']',
                 "测试凭证模式"),
            ],
        }

        # 文件扩展名白名单和黑名单
        self.include_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.json', '.yml', '.yaml', '.xml', '.config', '.conf',
            '.ini', '.env', '.sh', '.bash', '.zsh', '.ps1', '.bat',
            '.sql', '.html', '.css', '.scss', '.less', '.md'
        }

        self.exclude_extensions = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.log', '.tmp', '.cache', '.swp', '.swo'
        }

        # 排除的目录
        self.exclude_dirs = {
            '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules',
            '.git', '.svn', '.hg', 'venv', 'env', '.env',
            'build', 'dist', 'target', 'bin', 'obj', 'out',
            '.idea', '.vscode', '.eclipse',
            'vendor', 'bower_components', '.bundle',
            'logs', 'temp', 'tmp'
        }

    def scan_file(self, file_path: Path) -> list[dict]:
        """扫描单个文件"""
        findings = []

        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                content = f.read()

                # 检查每一行
                for line_num, line in enumerate(content.split('\n'), 1):
                    for severity, patterns in self.patterns.items():
                        for pattern, description in patterns:
                            if hasattr(pattern, 'finditer'):
                                matches = list(pattern.finditer(line))
                            else:
                                # 对于字符串，使用 re.finditer
                                matches = list(re.finditer(pattern, line))

                            for match in matches:
                                findings.append({
                                    'severity': severity,
                                    'file': str(file_path),
                                    'line': line_num,
                                    'column': match.start() + 1,
                                    'pattern': pattern if isinstance(pattern, str) else pattern.pattern,
                                    'match': match.group(0),
                                    'description': description,
                                    'matched_text': match.groups()[0] if match.groups() else match.group(0),
                                    'context': line.strip(),
                                })

        except (OSError, UnicodeDecodeError, PermissionError):
            # 记录但不要中断扫描
            pass

        return findings

    def scan_directory(self, directory: Path, recursive: bool = True) -> None:
        """扫描目录"""
        print(f"🔍 扫描目录: {directory}")

        for item in directory.iterdir():
            if item.is_dir():
                # 检查是否应该排除此目录
                if item.name in self.exclude_dirs:
                    continue

                if recursive:
                    self.scan_directory(item, recursive)

            elif item.is_file():
                # 检查文件扩展名
                if self._should_include_file(item):
                    self.scanned_files += 1
                    findings = self.scan_file(item)
                    self.findings.extend(findings)
                else:
                    self.skipped_files += 1

    def _should_include_file(self, file_path: Path) -> bool:
        """判断是否应该包含此文件"""
        ext = file_path.suffix.lower()

        # 检查排除扩展名
        if ext in self.exclude_extensions:
            return False

        # 检查包含扩展名（如果两者都为空，则包含）
        if self.include_extensions and ext not in self.include_extensions:
            return False

        return True

    def generate_report(self) -> dict:
        """生成扫描报告"""
        high_count = len([f for f in self.findings if f['severity'] == 'HIGH'])
        medium_count = len([f for f in self.findings if f['severity'] == 'MEDIUM'])
        low_count = len([f for f in self.findings if f['severity'] == 'LOW'])

        # 按严重程度分组
        grouped_findings = {}
        for severity in ['HIGH', 'MEDIUM', 'LOW']:
            grouped_findings[severity] = [
                f for f in self.findings if f['severity'] == severity
            ]

        # 按文件分组
        file_findings = {}
        for finding in self.findings:
            file_path = finding['file']
            if file_path not in file_findings:
                file_findings[file_path] = []
            file_findings[file_path].append(finding)

        return {
            'summary': {
                'total_findings': len(self.findings),
                'high_severity': high_count,
                'medium_severity': medium_count,
                'low_severity': low_count,
                'scanned_files': self.scanned_files,
                'skipped_files': self.skipped_files,
            },
            'findings_by_severity': grouped_findings,
            'findings_by_file': file_findings,
            'all_findings': self.findings,
        }

    def print_report(self, report: dict) -> None:
        """打印扫描报告"""
        summary = report['summary']

        print(f"\n{'='*60}")
        print("🔍 敏感信息扫描报告")
        print(f"{'='*60}")

        print("\n📊 扫描统计:")
        print(f"  扫描文件数: {summary['scanned_files']}")
        print(f"  跳过文件数: {summary['skipped_files']}")
        print(f"  发现问题总数: {summary['total_findings']}")

        print("\n🚨 严重程度分布:")
        print(f"  🔴 高危: {summary['high_severity']}")
        print(f"  🟡 中危: {summary['medium_severity']}")
        print(f"  🟢 低危: {summary['low_severity']}")

        # 显示高危和部分中危问题
        if summary['high_severity'] > 0 or summary['medium_severity'] > 0:
            print("\n❌ 发现的敏感信息:")

            for severity in ['HIGH', 'MEDIUM']:
                findings = report['findings_by_severity'].get(severity, [])
                if findings:
                    print(f"\n{severity} 严重程度 ({len(findings)} 项):")

                    # 按文件分组显示
                    file_groups = {}
                    for finding in findings:
                        file_path = finding['file']
                        if file_path not in file_groups:
                            file_groups[file_path] = []
                        file_groups[file_path].append(finding)

                    for file_path, file_findings in file_groups.items():
                        print(f"\n  📁 {file_path}")
                        for finding in file_findings[:3]:  # 每个文件最多显示3个问题
                            severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[severity]
                            print(f"    {severity_emoji} 第{finding['line']}行: {finding['description']}")
                            print(f"       {finding['context']}")
                            print(f"       匹配: {finding['matched_text']}")

                        if len(file_findings) > 3:
                            print(f"    ... 还有 {len(file_findings) - 3} 个问题")

        # 修复建议
        if summary['total_findings'] > 0:
            print("\n💡 修复建议:")
            print("  1. 将敏感信息移动到环境变量或配置文件中")
            print("  2. 使用 os.getenv() 或类似的安全配置管理方式")
            print("  3. 对于 API Keys，考虑使用密钥管理服务")
            print("  4. 对于数据库密码，使用连接池或环境变量")
            print("  5. 确保 .env 文件被添加到 .gitignore")
            print("  6. 考虑使用 git-secrets 预提交钩子防止意外提交")

    def write_report(self, report: dict, output_path: str) -> None:
        """将报告写入文件"""
        import json

        # 准备 JSON 友好的报告
        json_report = {
            'scan_timestamp': str(__import__('datetime').datetime.now()),
            'scanner_version': '1.0.0',
            'report': report
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    print("🚀 P4-3 敏感信息扫描开始\n")

    # 初始化扫描器
    scanner = SecretScanner()

    # 扫描源代码目录
    src_dir = Path("src")
    config_dir = Path("config")

    if src_dir.exists():
        scanner.scan_directory(src_dir, recursive=True)

    if config_dir.exists():
        scanner.scan_directory(config_dir, recursive=True)

    # 生成报告
    report = scanner.generate_report()

    # 打印报告
    scanner.print_report(report)

    # 保存报告到文件
    os.makedirs("reports", exist_ok=True)
    output_path = "reports/secrets_scan.json"
    scanner.write_report(report, output_path)

    print(f"\n📁 详细报告已保存到: {output_path}")

    # 返回适当的退出码
    if report['summary']['high_severity'] > 0:
        print("\n❌ 发现高危敏感信息，请立即修复！")
        return 2
    elif report['summary']['medium_severity'] > 0:
        print("\n⚠️ 发现中危敏感信息，建议修复")
        return 1
    else:
        print("\n✅ 未发现严重敏感信息")
        return 0


if __name__ == "__main__":
    sys.exit(main())
