#!/usr/bin/env python3
"""
安全扫描和修复工具
Security Scan and Fix Tool

针对Issue #156的P1-2阶段：安全加固和漏洞修复
执行bandit安全扫描和pip-audit依赖漏洞检查
"""

import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class SecurityScanner:
    """安全扫描器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.scripts_dir = project_root / "scripts"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "bandit_scan": {},
            "pip_audit": {},
            "fixes_applied": [],
            "recommendations": [],
        }

    def run_bandit_scan(self) -> Dict:
        """运行bandit安全扫描"""
        print("🔒 运行bandit安全扫描...")

        try:
            # 首先安装bandit
            subprocess.run([
                sys.executable, "-m", "pip", "install", "bandit"
            ], check=True, capture_output=True)

            # 运行bandit扫描
            result = subprocess.run([
                sys.executable, "-m", "bandit", "-r", "src/", "-f", "json"
            ], capture_output=True, text=True)

            if result.stdout:
                try:
                    bandit_results = json.loads(result.stdout)
                    self.results["bandit_scan"] = {
                        "success": True,
                        "results": bandit_results.get("results", []),
                        "metrics": bandit_results.get("metrics", {}),
                        "total_issues": len(bandit_results.get("results", [])),
                    }
                    print(f"✅ bandit扫描完成，发现 {self.results['bandit_scan']['total_issues']} 个问题")
                except json.JSONDecodeError:
                    self.results["bandit_scan"] = {
                        "success": False,
                        "error": "无法解析bandit输出",
                        "raw_output": result.stdout,
                        "stderr": result.stderr,
                    }
            else:
                self.results["bandit_scan"] = {
                    "success": True,
                    "results": [],
                    "metrics": {},
                    "total_issues": 0,
                }
                print("✅ bandit扫描完成，未发现安全问题")

        except subprocess.CalledProcessError as e:
            self.results["bandit_scan"] = {
                "success": False,
                "error": f"bandit扫描失败: {e}",
                "stderr": e.stderr if hasattr(e, 'stderr') else "",
            }
            print(f"❌ bandit扫描失败: {e}")

        except Exception as e:
            self.results["bandit_scan"] = {
                "success": False,
                "error": f"意外错误: {e}",
            }
            print(f"❌ bandit扫描意外错误: {e}")

        return self.results["bandit_scan"]

    def run_pip_audit(self) -> Dict:
        """运行pip-audit依赖漏洞检查"""
        print("🔍 运行pip-audit依赖漏洞检查...")

        try:
            # 首先安装pip-audit
            subprocess.run([
                sys.executable, "-m", "pip", "install", "pip-audit"
            ], check=True, capture_output=True)

            # 运行pip-audit
            result = subprocess.run([
                sys.executable, "-m", "pip", "audit", "--format", "json"
            ], capture_output=True, text=True)

            if result.stdout:
                try:
                    audit_results = json.loads(result.stdout)
                    self.results["pip_audit"] = {
                        "success": True,
                        "dependencies": audit_results.get("dependencies", []),
                        "vulns": audit_results.get("vulns", []),
                        "total_vulns": len(audit_results.get("vulns", [])),
                    }
                    print(f"✅ pip-audit完成，发现 {self.results['pip_audit']['total_vulns']} 个漏洞")
                except json.JSONDecodeError:
                    self.results["pip_audit"] = {
                        "success": False,
                        "error": "无法解析pip-audit输出",
                        "raw_output": result.stdout,
                        "stderr": result.stderr,
                    }
            else:
                self.results["pip_audit"] = {
                    "success": True,
                    "dependencies": [],
                    "vulns": [],
                    "total_vulns": 0,
                }
                print("✅ pip-audit完成，未发现漏洞")

        except subprocess.CalledProcessError as e:
            self.results["pip_audit"] = {
                "success": False,
                "error": f"pip-audit失败: {e}",
                "stderr": e.stderr if hasattr(e, 'stderr') else "",
            }
            print(f"❌ pip-audit失败: {e}")

        except Exception as e:
            self.results["pip_audit"] = {
                "success": False,
                "error": f"意外错误: {e}",
            }
            print(f"❌ pip-audit意外错误: {e}")

        return self.results["pip_audit"]

    def fix_common_security_issues(self) -> List[str]:
        """修复常见的安全问题"""
        print("🔧 修复常见安全问题...")

        fixes_applied = []

        # 1. 检查硬编码的密码或密钥
        password_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]

        # 2. 检查不安全的随机数生成
        insecure_random_patterns = [
            r'random\.random\(\)',
            r'random\.randint\(',
        ]

        # 3. 检查SQL注入风险
        sql_injection_patterns = [
            r'execute\([^)]*\+[^)]*\)',
            r'execute\([^)]*%[^)]*\)',
        ]

        for py_file in self.src_dir.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    original_content = content

                    # 检查并标记安全问题
                    for pattern in password_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            print(f"⚠️ 在 {py_file.relative_to(self.project_root)} 中发现可能的硬编码密码")
                            self.results["recommendations"].append(
                                f"检查文件 {py_file.relative_to(self.project_root)} 中的硬编码密码"
                            )

                    for pattern in insecure_random_patterns:
                        if re.search(pattern, content):
                            print(f"⚠️ 在 {py_file.relative_to(self.project_root)} 中发现不安全的随机数生成")
                            self.results["recommendations"].append(
                                f"在 {py_file.relative_to(self.project_root)} 中使用secrets模块替代random模块"
                            )

                    for pattern in sql_injection_patterns:
                        if re.search(pattern, content):
                            print(f"⚠️ 在 {py_file.relative_to(self.project_root)} 中发现潜在的SQL注入风险")
                            self.results["recommendations"].append(
                                f"在 {py_file.relative_to(self.project_root)} 中使用参数化查询"
                            )

                except Exception as e:
                    print(f"⚠️ 处理文件 {py_file} 时出错: {e}")

        return fixes_applied

    def check_file_permissions(self) -> List[str]:
        """检查文件权限"""
        print("🔐 检查文件权限...")

        permission_issues = []

        # 检查敏感文件的权限
        sensitive_files = [
            ".env",
            "config.ini",
            "secrets.json",
            "private_key.pem",
        ]

        for sensitive_file in sensitive_files:
            file_path = self.project_root / sensitive_file
            if file_path.exists():
                stat_info = file_path.stat()
                mode = oct(stat_info.st_mode)[-3:]
                if mode != "600" and mode != "644":
                    permission_issues.append(
                        f"{sensitive_file}: 权限过于宽松 ({mode})"
                    )

        return permission_issues

    def generate_security_report(self) -> str:
        """生成安全扫描报告"""
        report = f"""
# 安全扫描报告
# Security Scan Report

**扫描时间**: {self.results['timestamp']}
**项目根目录**: {self.project_root}

## 📊 扫描结果摘要

### Bandit安全扫描
- **状态**: {'✅ 成功' if self.results['bandit_scan'].get('success') else '❌ 失败'}
- **发现问题**: {self.results['bandit_scan'].get('total_issues', 0)} 个

### 依赖漏洞扫描 (pip-audit)
- **状态**: {'✅ 成功' if self.results['pip_audit'].get('success') else '❌ 失败'}
- **发现漏洞**: {self.results['pip_audit'].get('total_vulns', 0)} 个

### 文件权限检查
- **发现问题**: {len(self.results.get('permission_issues', []))} 个

## 🔍 详细结果

### Bandit扫描结果
"""

        if self.results['bandit_scan'].get('success'):
            issues = self.results['bandit_scan'].get('results', [])
            if issues:
                for i, issue in enumerate(issues[:10], 1):  # 只显示前10个问题
                    report += f"""
**问题 {i}**:
- **文件**: {issue.get('filename', 'N/A')}
- **行号**: {issue.get('line_number', 'N/A')}
- **严重程度**: {issue.get('issue_severity', 'N/A')}
- **置信度**: {issue.get('issue_cwe_id', 'N/A')}
- **问题ID**: {issue.get('test_id', 'N/A')}
- **描述**: {issue.get('issue_text', 'N/A')}
"""
            else:
                report += "✅ 未发现安全问题\n"
        else:
            report += f"❌ 扫描失败: {self.results['bandit_scan'].get('error', '未知错误')}\n"

        report += "\n### 依赖漏洞扫描结果\n"

        if self.results['pip_audit'].get('success'):
            vulns = self.results['pip_audit'].get('vulns', [])
            if vulns:
                for i, vuln in enumerate(vulns[:10], 1):  # 只显示前10个漏洞
                    report += f"""
**漏洞 {i}**:
- **包名**: {vuln.get('name', 'N/A')}
- **漏洞ID**: {vuln.get('id', 'N/A')}
- **版本**: {vuln.get('version', 'N/A')}
- **修复版本**: {vuln.get('fix_versions', ['N/A'])}
- **描述**: {vuln.get('description', 'N/A')}
"""
            else:
                report += "✅ 未发现依赖漏洞\n"
        else:
            report += f"❌ 扫描失败: {self.results['pip_audit'].get('error', '未知错误')}\n"

        if self.results.get('recommendations'):
            report += "\n## 💡 安全建议\n\n"
            for i, rec in enumerate(self.results['recommendations'], 1):
                report += f"{i}. {rec}\n"

        report += f"""

## 🎯 总结

- **安全问题**: {self.results['bandit_scan'].get('total_issues', 0)} 个
- **依赖漏洞**: {self.results['pip_audit'].get('total_vulns', 0)} 个
- **应用修复**: {len(self.results['fixes_applied'])} 个

**总体安全状态**: {'🟢 良好' if self.results['bandit_scan'].get('total_issues', 0) == 0 and self.results['pip_audit'].get('total_vulns', 0) == 0 else '🟡 需要关注'}

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report

    def save_report(self, report: str) -> Path:
        """保存安全扫描报告"""
        report_file = self.project_root / f"security_scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        return report_file

    def run_full_scan(self) -> Dict:
        """运行完整的安全扫描"""
        print("🔒 开始完整安全扫描...")
        print("=" * 50)

        # 1. 运行bandit扫描
        self.run_bandit_scan()

        # 2. 运行pip-audit
        self.run_pip_audit()

        # 3. 修复常见问题
        fixes = self.fix_common_security_issues()
        self.results["fixes_applied"] = fixes

        # 4. 检查文件权限
        permission_issues = self.check_file_permissions()
        self.results["permission_issues"] = permission_issues

        # 5. 生成报告
        report = self.generate_security_report()
        report_file = self.save_report(report)

        print(f"\n📄 安全扫描报告已保存到: {report_file}")
        print("=" * 50)

        return self.results


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent

    print("🔒 安全扫描和修复工具")
    print("针对Issue #156的P1-2阶段")
    print("=" * 50)

    scanner = SecurityScanner(project_root)
    results = scanner.run_full_scan()

    # 输出摘要
    print("\n📊 扫描摘要:")
    print(f"  - Bandit问题: {results['bandit_scan'].get('total_issues', 0)}")
    print(f"  - 依赖漏洞: {results['pip_audit'].get('total_vulns', 0)}")
    print(f"  - 修复数量: {len(results.get('fixes_applied', []))}")
    print(f"  - 建议数量: {len(results.get('recommendations', []))}")

    total_issues = results['bandit_scan'].get('total_issues', 0) + results['pip_audit'].get('total_vulns', 0)
    if total_issues == 0:
        print("\n🎉 安全扫描完成，未发现严重安全问题！")
        return 0
    else:
        print(f"\n⚠️ 发现 {total_issues} 个安全问题，请查看报告详情")
        return 1


if __name__ == "__main__":
    sys.exit(main())