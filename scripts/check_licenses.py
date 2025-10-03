#!/usr/bin/env python3
"""
依赖许可证检查脚本
Dependency License Check Script

检查所有依赖包的许可证合规性
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class LicenseType(Enum):
    """许可证类型"""
    PERMISSIVE = os.getenv("CHECK_LICENSES_PERMISSIVE_25")
    COPYLEFT = os.getenv("CHECK_LICENSES_COPYLEFT_25")
    COMMERCIAL = os.getenv("CHECK_LICENSES_COMMERCIAL_26")
    PROPRIETARY = os.getenv("CHECK_LICENSES_PROPRIETARY_26")
    UNKNOWN = os.getenv("CHECK_LICENSES_UNKNOWN_27")


@dataclass
class LicenseInfo:
    """许可证信息"""
    name: str
    type: LicenseType
    allowed: bool = True
    description: str = ""
    requires_attribution: bool = False
    requires_source: bool = False
    requires_same_license: bool = False


@dataclass
class PackageLicense:
    """包许可证信息"""
    name: str
    version: str
    license_name: str
    license_type: LicenseType
    license_info: LicenseInfo
    author: str = ""
    author_email: str = ""
    description: str = ""
    homepage: str = ""
    issues: List[str] = None


class LicenseChecker:
    """许可证检查器"""

    def __init__(self):
        """初始化检查器"""
        # 许可证定义
        self.licenses: Dict[str, LicenseInfo] = self._init_licenses()

        # 允许的许可证
        self.allowed_licenses = {
            "MIT", "BSD", "Apache-2.0", "PSF", "ISC", "MPL-2.0",
            "Unlicense", "CC0-1.0", "Apache 2.0"
        }

        # 需要注意的许可证
        self.warning_licenses = {
            "GPL": LicenseType.COPYLEFT,
            "LGPL": LicenseType.COPYLEFT,
            "AGPL": LicenseType.COPYLEFT,
            "EPL": LicenseType.COPYLEFT,
            "MPL": LicenseType.COPYLEFT
        }

        # 禁止的许可证
        self.blocked_licenses = {
            "Commercial": LicenseType.COMMERCIAL,
            "Proprietary": LicenseType.PROPRIETARY,
            "Shareware": LicenseType.COMMERCIAL
        }

        # 检查结果
        self.packages: List[PackageLicense] = []
        self.issues: List[str] = []

    def _init_licenses(self) -> Dict[str, LicenseInfo]:
        """初始化许可证信息"""
        return {
            # 宽松许可证
            "MIT": LicenseInfo(
                name="MIT",
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_97"),
                requires_attribution=True
            ),
            "BSD": LicenseInfo(
                name="BSD",
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_102"),
                requires_attribution=True
            ),
            "Apache-2.0": LicenseInfo(
                name = os.getenv("CHECK_LICENSES_NAME_107"),
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description="Apache许可证2.0，专利保护",
                requires_attribution=True
            ),
            "ISC": LicenseInfo(
                name="ISC",
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_115"),
                requires_attribution=True
            ),
            "PSF": LicenseInfo(
                name="PSF",
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_122")
            ),
            "Unlicense": LicenseInfo(
                name = os.getenv("CHECK_LICENSES_NAME_125"),
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_128")
            ),
            "CC0-1.0": LicenseInfo(
                name = os.getenv("CHECK_LICENSES_NAME_129"),
                type=LicenseType.PERMISSIVE,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_132")
            ),

            # Copyleft许可证
            "GPL": LicenseInfo(
                name="GPL",
                type=LicenseType.COPYLEFT,
                allowed=False,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_138"),
                requires_same_license=True,
                requires_source=True,
                issues=["GPL许可证可能要求开源您的代码"]
            ),
            "LGPL": LicenseInfo(
                name="LGPL",
                type=LicenseType.COPYLEFT,
                allowed=False,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_147"),
                requires_source=True,
                issues=["LGPL许可证要求提供源代码"]
            ),
            "AGPL": LicenseInfo(
                name="AGPL",
                type=LicenseType.COPYLEFT,
                allowed=False,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_154"),
                requires_same_license=True,
                requires_source=True,
                issues=["AGPL要求网络服务也开源"]
            ),
            "EPL": LicenseInfo(
                name="EPL",
                type=LicenseType.COPYLEFT,
                allowed=False,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_163"),
                requires_same_license=True,
                issues=["EPL许可证的兼容性需要检查"]
            ),
            "MPL": LicenseInfo(
                name="MPL",
                type=LicenseType.COPYLEFT,
                allowed=True,
                description = os.getenv("CHECK_LICENSES_DESCRIPTION_169"),
                requires_source=True,
                issues=["MPL允许部分开源"]
            ),

            # 其他许可证
            "Apache 2.0": LicenseInfo(
                name = os.getenv("CHECK_LICENSES_NAME_175"),
                type=LicenseType.PERMISSIVE,
                allowed=True
            ),
            "UNKNOWN": LicenseInfo(
                name = os.getenv("CHECK_LICENSES_NAME_179"),
                type=LicenseType.UNKNOWN,
                allowed=False,
                description="未知许可证",
                issues=["需要手动验证许可证"]
            )
        }

    def check_all_packages(self) -> List[PackageLicense]:
        """检查所有包的许可证"""
        print("🔍 检查依赖包许可证...")

        try:
            # 使用pip-licenses
            result = subprocess.run(
                ['pip-licenses', '--from=mixed', '--format=json'],
                capture_output=True,
                text=True,
                check=True
            )

            packages_data = json.loads(result.stdout)

            for pkg_data in packages_data:
                package_license = self._process_package_license(pkg_data)
                self.packages.append(package_license)

        except FileNotFoundError:
            print("❌ pip-licenses未安装")
            print("   安装命令: pip install pip-licenses")
        except subprocess.CalledProcessError as e:
            print(f"❌ 执行pip-licenses失败: {e}")
        except json.JSONDecodeError as e:
            print(f"❌ 解析pip-licenses输出失败: {e}")

        return self.packages

    def _process_package_license(self, pkg_data: Dict) -> PackageLicense:
        """处理单个包的许可证信息"""
        name = pkg_data.get('name', '')
        version = pkg_data.get('version', '')
        license_name = pkg_data.get('license', 'UNKNOWN')
        author = pkg_data.get('author', '')
        author_email = pkg_data.get('author_email', '')
        description = pkg_data.get('description', '')
        homepage = pkg_data.get('homepage', '')

        # 确定许可证类型
        license_info = self.licenses.get(license_name)
        if not license_info:
            license_info = self._match_license(license_name)

        package_license = PackageLicense(
            name=name,
            version=version,
            license_name=license_name,
            license_type=license_info.type,
            license_info=license_info,
            author=author,
            author_email=author_email,
            description=description,
            homepage=homepage,
            issues=[]
        )

        # 检查许可证问题
        self._check_license_issues(package_license)

        return package_license

    def _match_license(self, license_name: str) -> LicenseInfo:
        """匹配许可证"""
        name_lower = license_name.lower()

        # 检查是否是允许的许可证
        for allowed in self.allowed_licenses:
            if allowed.lower() in name_lower:
                return self.licenses.get(allowed, self.licenses["UNKNOWN"])

        # 检查是否是警告许可证
        for warning, license_type in self.warning_licenses.items():
            if warning.lower() in name_lower:
                return LicenseInfo(
                    name=license_name,
                    type=license_type,
                    allowed=False,
                    issues=["该许可证类型需要特别注意"]
                )

        # 检查是否是禁止的许可证
        for blocked, license_type in self.blocked_licenses.items():
            if blocked.lower() in name_lower:
                return LicenseInfo(
                    name=license_name,
                    type=license_type,
                    allowed=False,
                    issues=["该许可证类型禁止使用"]
                )

        # 未知许可证
        return self.licenses["UNKNOWN"]

    def _check_license_issues(self, pkg_license: PackageLicense):
        """检查许可证问题"""
        license_info = pkg_license.license_info

        if not license_info.allowed:
            pkg_license.issues.append("许可证不被允许")

        if license_info.issues:
            pkg_license.issues.extend(license_info.issues)

        # 特定包的额外检查
        self._check_specific_packages(pkg_license)

    def _check_specific_packages(self, pkg_license: PackageLicense):
        """检查特定包的许可证问题"""
        name = pkg_license.name.lower()

        # 一些需要注意的包
        problematic_packages = {
            'pycrypto': ["已停止维护，存在安全问题"],
            'pycrypto2': ["已停止维护，存在安全问题"],
            'django': ["检查与Python版本的兼容性"],
            'tensorflow': ["可能有额外的专利限制"],
            'opencv-python': ["可能有额外的许可证要求"]
        }

        if name in problematic_packages:
            pkg_license.issues.extend(problematic_packages[name])

    def generate_report(self) -> str:
        """生成许可证报告"""
        report = []
        report.append("=" * 60)
        report.append("依赖许可证检查报告")
        report.append("=" * 60)
        report.append(f"检查时间: {self._get_current_time()}")
        report.append(f"总包数: {len(self.packages)}")
        report.append("")

        # 统计信息
        stats = self._get_statistics()
        report.append("📊 许可证统计:")
        for license_type, count in stats['by_type'].items():
            report.append(f"  {license_type.value}: {count}")
        report.append("")

        # 问题统计
        issue_stats = self._get_issue_statistics()
        if issue_stats['total'] > 0:
            report.append("⚠️ 问题统计:")
            report.append(f"  有问题的包: {issue_stats['total']}")
            report.append(f"  禁止的许可证: {issue_stats['blocked']}")
            report.append(f"  需要注意的许可证: {issue_stats['warning']}")
            report.append(f"  未知许可证: {issue_stats['unknown']}")
            report.append("")

        # 详细的包信息
        report.append("📦 包许可证详情:")
        for pkg in sorted(self.packages, key=lambda x: x.name):
            status_icon = "✅" if pkg.license_info.allowed else "❌"
            report.append(f"  {status_icon} {pkg.name}=={pkg.version}")
            report.append(f"    许可证: {pkg.license_name}")
            report.append(f"    类型: {pkg.license_type.value}")

            if pkg.license_info.requires_attribution:
                report.append(f"    要求: 需要署名")
            if pkg.license_info.requires_source:
                report.append(f"    要求: 需要提供源代码")
            if pkg.license_info.requires_same_license:
                report.append(f"    要求: 相同许可证")

            if pkg.issues:
                report.append(f"    问题: {', '.join(pkg.issues)}")

            report.append("")

        # 总结和建议
        report.append("💡 总结和建议:")

        if issue_stats['total'] == 0:
            report.append("✅ 所有依赖包的许可证都符合要求")
        else:
            report.append(f"⚠️ 发现 {issue_stats['total']} 个许可证问题")

            if issue_stats['blocked'] > 0:
                report.append(f"  - 有 {issue_stats['blocked']} 个包使用禁止的许可证")
                report.append("    建议寻找替代包")

            if issue_stats['warning'] > 0:
                report.append(f"  - 有 {issue_stats['warning']} 个包使用Copyleft许可证")
                report.append("    请确认是否影响项目许可证")

            if issue_stats['unknown'] > 0:
                report.append(f"  - 有 {issue_stats['unknown']} 个包使用未知许可证")
                report.append("    建议手动验证这些包的许可证")

        # 生成NOTICE文件建议
        report.append("\n📄 NOTICE文件建议:")
        notice_packages = [
            pkg for pkg in self.packages
            if pkg.license_info.requires_attribution or pkg.license_info.license_name in ["MIT", "BSD", "Apache-2.0"]
        ]

        if notice_packages:
            report.append("以下包要求在NOTICE文件中署名:")
            for pkg in notice_packages[:10]:  # 只显示前10个
                report.append(f"  - {pkg.name}: {pkg.license_name}")
            if len(notice_packages) > 10:
                report.append(f"  ... 还有 {len(notice_packages) - 10} 个包")
        else:
            report.append("  没有需要特别署名的包")

        return "\n".join(report)

    def _get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            'by_type': {},
            'by_license': {}
        }

        for pkg in self.packages:
            license_type = pkg.license_type
            license_name = pkg.license_name

            stats['by_type'][license_type] = stats['by_type'].get(license_type, 0) + 1
            stats['by_license'][license_name] = stats['by_license'].get(license_name, 0) + 1

        return stats

    def _get_issue_statistics(self) -> Dict:
        """获取问题统计"""
        stats = {
            'total': 0,
            'blocked': 0,
            'warning': 0,
            'unknown': 0
        }

        for pkg in self.packages:
            if pkg.issues:
                stats['total'] += 1

                if not pkg.license_info.allowed:
                    stats['blocked'] += 1
                elif pkg.license_type == LicenseType.COPYLEFT:
                    stats['warning'] += 1
                elif pkg.license_type == LicenseType.UNKNOWN:
                    stats['unknown'] += 1

        return stats

    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_notice_file(self, output_path: Path = None):
        """生成NOTICE文件"""
        if not output_path:
            output_path = project_root / "NOTICE"

        notice_packages = [
            pkg for pkg in self.packages
            if pkg.license_info.requires_attribution
        ]

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("NOTICE\n")
            f.write("=" * 60 + "\n\n")
            f.write("本项目使用了以下开源软件包:\n\n")

            for pkg in sorted(notice_packages, key=lambda x: x.name):
                f.write(f"{pkg.name}=={pkg.version}\n")
                f.write(f"  许可证: {pkg.license_name}\n")
                f.write(f"  作者: {pkg.author or '未知'}\n")
                f.write(f"  项目主页: {pkg.homeback or '未知'}\n\n")

            f.write("完整许可证信息请查看各个包的源代码。\n")

        print(f"✅ NOTICE文件已生成: {output_path}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("CHECK_LICENSES_DESCRIPTION_465"))
    parser.add_argument('--output', '-o', type=Path,
                       help = os.getenv("CHECK_LICENSES_HELP_469"))
    parser.add_argument('--notice', '-n', action = os.getenv("CHECK_LICENSES_ACTION_469"),
                       help = os.getenv("CHECK_LICENSES_HELP_470"))
    parser.add_argument('--format', choices=['text', 'json'],
                       default='text', help="输出格式")

    args = parser.parse_args()

    # 初始化检查器
    checker = LicenseChecker()

    # 检查所有包
    packages = checker.check_all_packages()

    if not packages:
        print("❌ 未能获取包许可证信息")
        sys.exit(1)

    # 生成报告
    if args.format == 'json':
        # JSON格式
        report = {
            'packages': [],
            'statistics': checker._get_statistics(),
            'issues': checker._get_issue_statistics()
        }

        for pkg in packages:
            report['packages'].append({
                'name': pkg.name,
                'version': pkg.version,
                'license': pkg.license_name,
                'type': pkg.license_type.value,
                'allowed': pkg.license_info.allowed,
                'issues': pkg.issues
            })

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"JSON报告已保存到: {args.output}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # 文本格式
        report = checker.generate_report()

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"报告已保存到: {args.output}")
        else:
            print(report)

    # 生成NOTICE文件
    if args.notice:
        checker.generate_notice_file()

    # 检查是否有严重问题
    issue_stats = checker._get_issue_statistics()
    if issue_stats['blocked'] > 0:
        print(f"\n❌ 发现 {issue_stats['blocked']} 个禁止的许可证")
        sys.exit(1)
    elif issue_stats['total'] > 0:
        print(f"\n⚠️ 发现 {issue_stats['total']} 个许可证问题需要注意")
        sys.exit(0)


if __name__ == "__main__":
    main()