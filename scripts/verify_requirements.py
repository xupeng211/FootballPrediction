import os
#!/usr/bin/env python3
"""
Requirements验证脚本
Requirements Verification Script

验证requirements.txt的完整性和安全性
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from packaging import version
import requests

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class RequirementsVerifier:
    """Requirements验证器"""

    def __init__(self, requirements_file: Optional[Path] = None):
        """
        初始化验证器

        Args:
            requirements_file: requirements.txt文件路径
        """
        self.requirements_file = requirements_file or project_root / "requirements.txt"
        self.vulnerability_db_url = "https://pypi.org/pypi"
        self.issues = []

    def parse_requirements(self) -> List[Tuple[str, str]]:
        """
        解析requirements.txt

        Returns:
            包名和版本号的列表
        """
        requirements = []

        if not self.requirements_file.exists():
            self.issues.append(f"❌ requirements.txt文件不存在: {self.requirements_file}")
            return requirements

        try:
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue

                    # 解析包名和版本
                    if '==' in line:
                        package, version_spec = line.split('==', 1)
                        # 处理额外的说明符（如[extra]）
                        package = package.split('[')[0]
                        requirements.append((package.strip(), version_spec.strip()))
                    elif '>=' in line or '<=' in line or '>' in line or '<' in line:
                        # 处理版本范围
                        parts = line.split('>=' if '>=' in line else
                                        '<=' if '<=' in line else
                                        '>' if '>' in line else '<')
                        package = parts[0].split('[')[0]
                        version_spec = line[len(package):].strip()
                        requirements.append((package.strip(), version_spec))
                    else:
                        # 无版本限制的包
                        package = line.split('[')[0]
                        requirements.append((package.strip(), "any"))

            return requirements

        except Exception as e:
            self.issues.append(f"❌ 解析requirements.txt失败: {e}")
            return []

    def check_duplicates(self, requirements: List[Tuple[str, str]]):
        """检查重复的包"""
        packages = [req[0].lower() for req in requirements]
        seen = set()
        duplicates = set()

        for pkg in packages:
            if pkg in seen:
                duplicates.add(pkg)
            seen.add(pkg)

        if duplicates:
            self.issues.append(f"❌ 发现重复的包: {', '.join(duplicates)}")
        else:
            print("✅ 没有发现重复的包")

    def check_security_vulnerabilities(self, requirements: List[Tuple[str, str]]):
        """检查安全漏洞"""
        print("🔍 检查安全漏洞...")

        # 使用pip-audit检查
        try:
            result = subprocess.run(
                ['pip-audit', '--requirement', str(self.requirements_file),
                 '--format', 'json'],
                capture_output=True,
                text=True,
                check=False  # 不因为漏洞而退出
            )

            if result.returncode == 0:
                print("✅ 没有发现安全漏洞")
            else:
                try:
                    audit_data = json.loads(result.stdout)
                    vulnerabilities = audit_data.get('vulnerabilities', [])

                    if vulnerabilities:
                        print(f"⚠️ 发现 {len(vulnerabilities)} 个安全漏洞:")
                        for vuln in vulnerabilities[:5]:  # 只显示前5个
                            pkg = vuln.get('name', 'Unknown')
                            version = vuln.get('installed_version', 'Unknown')
                            advisory = vuln.get('advisory', {})
                            severity = advisory.get('severity', 'Unknown')
                            desc = advisory.get('description', 'No description')

                            print(f"  - {pkg}=={version} ({severity}): {desc[:100]}...")

                        if len(vulnerabilities) > 5:
                            print(f"  ... 还有 {len(vulnerabilities) - 5} 个漏洞")

                        self.issues.append(f"⚠️ 发现 {len(vulnerabilities)} 个安全漏洞")
                except json.JSONDecodeError:
                    print("⚠️ 无法解析pip-audit输出")
                    print(result.stdout)

        except FileNotFoundError:
            print("⚠️ pip-audit未安装，跳过安全检查")
            print("   安装命令: pip install pip-audit")

    def check_version_conflicts(self, requirements: List[Tuple[str, str]]):
        """检查版本冲突"""
        print("🔍 检查版本冲突...")

        # 已知的一些冲突组合
        known_conflicts = {
            # Django版本冲突
            ('django', 'djangorestframework'): [
                ('4.2', '3.14+'),  # DRF 3.14+ 需要Django 4.2+
            ],
            # SQLAlchemy版本冲突
            ('sqlalchemy', 'alembic'): [
                ('2.0+', '1.12+'),  # Alembic 1.12+ 推荐SQLAlchemy 2.0+
            ],
        }

        # 构建包版本字典
        package_versions = {pkg: ver for pkg, ver in requirements}
        conflicts_found = False

        for (pkg1, pkg2), version_matrix in known_conflicts.items():
            if pkg1 in package_versions and pkg2 in package_versions:
                ver1 = package_versions[pkg1]
                ver2 = package_versions[pkg2]

                # 简单的版本检查（实际应该更复杂）
                for v1_range, v2_range in version_matrix:
                    if (v1_range in ver1 or 'any' in ver1) and \
                       (v2_range in ver2 or 'any' in ver2):
                        print(f"⚠️ 可能的版本冲突: {pkg1} ({ver1}) 和 {pkg2} ({ver2})")
                        self.issues.append(f"⚠️ 版本冲突: {pkg1} 和 {pkg2}")
                        conflicts_found = True
                        break

        if not conflicts_found:
            print("✅ 没有发现明显的版本冲突")

    def check_outdated_packages(self, requirements: List[Tuple[str, str]]):
        """检查过时的包"""
        print("🔍 检查过时的包...")

        try:
            # 使用pip list --outdated
            result = subprocess.run(
                ['pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                outdated_packages = json.loads(result.stdout)

                # 筛出requirements中的包
                outdated_in_requirements = []
                for pkg in requirements:
                    pkg_name = pkg[0].lower().replace('_', '-')
                    for outdated in outdated_packages:
                        if outdated['name'].lower().replace('_', '-') == pkg_name:
                            outdated_in_requirements.append({
                                'name': pkg[0],
                                'current': pkg[1],
                                'latest': outdated['latest_version'],
                                'type': outdated['latest_filetype']
                            })

                if outdated_in_requirements:
                    print(f"⚠️ 发现 {len(outdated_in_requirements)} 个过时的包:")
                    for pkg in outdated_in_requirements[:5]:  # 只显示前5个
                        print(f"  - {pkg['name']}: {pkg['current']} → {pkg['latest']}")

                    if len(outdated_in_requirements) > 5:
                        print(f"  ... 还有 {len(outdated_in_requirements) - 5} 个过时的包")
                else:
                    print("✅ 所有包都是最新版本")

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            print("⚠️ 无法检查过时的包")

    def check_essential_packages(self, requirements: List[Tuple[str, str]]):
        """检查必需的包是否存在"""
        print("🔍 检查必需的包...")

        essential_packages = {
            'fastapi': 'Web框架',
            'uvicorn': 'ASGI服务器',
            'sqlalchemy': 'ORM框架',
            'pydantic': '数据验证',
            'cryptography': '加密库',
            'python-jose': 'JWT处理',
        }

        missing_packages = []
        package_names = {pkg[0].lower() for pkg in requirements}

        for pkg, desc in essential_packages.items():
            if pkg not in package_names:
                missing_packages.append(f"{pkg} ({desc})")

        if missing_packages:
            self.issues.append(f"❌ 缺少必需的包: {', '.join(missing_packages)}")
        else:
            print("✅ 所有必需的包都存在")

    def check_package_sizes(self, requirements: List[Tuple[str, str]]):
        """检查包大小（可选）"""
        print("🔍 检查包大小...")

        total_size = 0
        large_packages = []

        # 获取已安装包的大小
        try:
            result = subprocess.run(
                ['pip', 'show', '-f'],
                capture_output=True,
                text=True,
                check=False
            )

            # 这里简化处理，实际应该解析pip show的输出
            print("ℹ️ 包大小检查需要完整的pip环境")

        except Exception as e:
            print(f"⚠️ 无法检查包大小: {e}")

    def generate_report(self, requirements: List[Tuple[str, str]]) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 60)
        report.append("Requirements验证报告")
        report.append("=" * 60)
        report.append(f"文件: {self.requirements_file}")
        report.append(f"包数量: {len(requirements)}")
        report.append("")

        # 包列表
        report.append("📦 包列表:")
        for pkg, ver in sorted(requirements):
            report.append(f"  - {pkg}=={ver}")
        report.append("")

        # 检查结果
        if self.issues:
            report.append("❌ 发现的问题:")
            for issue in self.issues:
                report.append(f"  {issue}")
        else:
            report.append("✅ 所有检查通过！")

        report.append("")
        report.append("📝 建议:")
        report.append("  1. 定期运行 'pip-audit' 检查安全漏洞")
        report.append("  2. 使用 'pip-tools' 锁定依赖版本")
        report.append("  3. 考虑使用 'safety' 进行额外的安全检查")
        report.append("  4. 定期更新包到最新稳定版本")

        return "\n".join(report)

    def verify_all(self) -> bool:
        """执行所有验证"""
        print("🚀 开始验证requirements.txt...")
        print()

        # 解析requirements
        requirements = self.parse_requirements()
        if not requirements:
            return False

        print(f"📦 找到 {len(requirements)} 个包")
        print()

        # 执行各项检查
        self.check_duplicates(requirements)
        self.check_essential_packages(requirements)
        self.check_version_conflicts(requirements)
        self.check_security_vulnerabilities(requirements)
        self.check_outdated_packages(requirements)
        self.check_package_sizes(requirements)

        # 生成报告
        report = self.generate_report(requirements)
        print()
        print(report)

        # 返回是否成功
        return len(self.issues) == 0


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="验证requirements.txt")
    parser.add_argument('--file', '-f', type=Path,
                       help="requirements.txt文件路径")
    parser.add_argument('--output', '-o', type=Path,
                       help = os.getenv("VERIFY_REQUIREMENTS_HELP_340"))
    parser.add_argument('--fix', action = os.getenv("VERIFY_REQUIREMENTS_ACTION_340"),
                       help = os.getenv("VERIFY_REQUIREMENTS_HELP_341"))

    args = parser.parse_args()

    # 初始化验证器
    verifier = RequirementsVerifier(args.file)

    # 执行验证
    success = verifier.verify_all()

    # 保存报告
    if args.output:
        report = verifier.generate_report(verifier.parse_requirements())
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存到: {args.output}")

    # 设置退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()