#!/usr/bin/env python3
"""
许可证合规检查脚本
License Compliance Check Script

用于CI/CD集成的许可证合规验证
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ComplianceStatus(Enum):
    """合规状态"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"


@dataclass
class ComplianceIssue:
    """合规问题"""
    package_name: str
    license_name: str
    issue_type: str
    severity: str  # low, medium, high, critical
    description: str
    recommendation: str = ""


@dataclass
class ComplianceReport:
    """合规报告"""
    status: ComplianceStatus
    total_packages: int
    compliant_packages: int
    warning_packages: int
    non_compliant_packages: int
    issues: List[ComplianceIssue]
    summary: str


class LicenseComplianceChecker:
    """许可证合规检查器"""

    def __init__(self):
        """初始化检查器"""
        # 允许的许可证列表
        self.allowed_licenses = {
            "MIT", "BSD", "Apache-2.0", "Apache 2.0", "Apache License 2.0",
            "ISC", "PSF", "Python Software Foundation License",
            "Unlicense", "CC0-1.0", "BSD-3-Clause", "BSD-2-Clause"
        }

        # 警告许可证（需要特别注意）
        self.warning_licenses = {
            "GPL", "LGPL", "AGPL", "EPL", "MPL", "MPL-2.0",
            "GPL-2.0", "GPL-3.0", "LGPL-2.0", "LGPL-2.1", "AGPL-1.0", "AGPL-3.0"
        }

        # 禁止的许可证
        self.forbidden_licenses = {
            "Commercial", "Proprietary", "Shareware", "Freeware"
        }

        # 检查结果
        self.issues: List[ComplianceIssue] = []

    def check_compliance(self, license_file: Optional[Path] = None) -> ComplianceReport:
        """
        执行合规检查

        Args:
            license_file: 许可证报告文件路径

        Returns:
            合规报告
        """
        if license_file and license_file.exists():
            with open(license_file, 'r') as f:
                license_data = json.load(f)
        else:
            # 使用pip-licenses获取数据
            license_data = self._get_license_data()

        if not license_data:
            return ComplianceReport(
                status=ComplianceStatus.NON_COMPLIANT,
                total_packages=0,
                compliant_packages=0,
                warning_packages=0,
                non_compliant_packages=0,
                issues=[],
                summary="无法获取许可证数据"
            )

        # 检查每个包
        total_packages = len(license_data)
        compliant_packages = 0
        warning_packages = 0
        non_compliant_packages = 0

        for pkg in license_data:
            pkg_name = pkg.get('name', '')
            pkg_license = pkg.get('license', '')
            pkg_version = pkg.get('version', '')

            # 检查许可证合规性
            issue = self._check_package_compliance(pkg_name, pkg_license, pkg_version)

            if issue:
                self.issues.append(issue)
                if issue.severity in ['critical', 'high']:
                    non_compliant_packages += 1
                else:
                    warning_packages += 1
            else:
                compliant_packages += 1

        # 确定整体状态
        if non_compliant_packages > 0:
            status = ComplianceStatus.NON_COMPLIANT
            summary = f"发现 {non_compliant_packages} 个不合规的包"
        elif warning_packages > 0:
            status = ComplianceStatus.WARNING
            summary = f"发现 {warning_packages} 个需要警告的包"
        else:
            status = ComplianceStatus.COMPLIANT
            summary = "所有许可证都符合要求"

        return ComplianceReport(
            status=status,
            total_packages=total_packages,
            compliant_packages=compliant_packages,
            warning_packages=warning_packages,
            non_compliant_packages=non_compliant_packages,
            issues=self.issues,
            summary=summary
        )

    def _get_license_data(self) -> List[Dict]:
        """获取许可证数据"""
        try:
            import subprocess
            result = subprocess.run(
                ['pip-licenses', '--from=mixed', '--format=json'],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except:
            return []

    def _check_package_compliance(self, name: str, license_name: str,
                                 version: str) -> Optional[ComplianceIssue]:
        """检查单个包的合规性"""
        # 标准化许可证名称
        license_normalized = license_name.strip().upper()

        # 检查禁止的许可证
        for forbidden in self.forbidden_licenses:
            if forbidden.upper() in license_normalized:
                return ComplianceIssue(
                    package_name=name,
                    license_name=license_name,
                    issue_type="forbidden_license",
                    severity="critical",
                    description=f"包 {name} 使用了禁止的许可证: {license_name}",
                    recommendation="请立即寻找替代包"
                )

        # 检查警告许可证
        for warning in self.warning_licenses:
            if warning.upper() in license_normalized:
                # AGPL是严重问题
                if "AGPL" in license_normalized:
                    return ComplianceIssue(
                        package_name=name,
                        license_name=license_name,
                        issue_type="agpl_license",
                        severity="high",
                        description=f"包 {name} 使用了AGPL许可证",
                        recommendation="AGPL要求网络服务也开源，请评估法律风险"
                    )
                # 其他Copyleft许可证是中等警告
                return ComplianceIssue(
                    package_name=name,
                    license_name=license_name,
                    issue_type="copyleft_license",
                    severity="medium",
                    description=f"包 {name} 使用了Copyleft许可证: {license_name}",
                    recommendation="请确认使用方式符合许可证要求"
                )

        # 检查未知许可证
        if not any(allowed.upper() in license_normalized for allowed in self.allowed_licenses):
            return ComplianceIssue(
                package_name=name,
                license_name=license_name,
                issue_type="unknown_license",
                severity="low",
                description=f"包 {name} 使用了未知许可证: {license_name}",
                recommendation="请手动验证许可证合规性"
            )

        # 检查特定包的额外要求
        return self._check_special_requirements(name, license_name, version)

    def _check_special_requirements(self, name: str, license_name: str,
                                   version: str) -> Optional[ComplianceIssue]:
        """检查特定包的额外要求"""
        # 检查是否需要NOTICE文件署名
        notice_required_licenses = ["MIT", "BSD", "Apache"]
        if any(lic in license_name for lic in notice_required_licenses):
            # 这里可以检查NOTICE文件是否已包含该包
            # 简化实现，返回None
            pass

        # 检查一些已知的需要特别注意的包
        special_packages = {
            'pycrypto': {
                'issue': '已停止维护，存在安全问题',
                'severity': 'high',
                'recommendation': '请使用pycryptodome替代'
            },
            'django': {
                'issue': '需要检查与Python版本的兼容性',
                'severity': 'low',
                'recommendation': '确保版本兼容'
            }
        }

        if name.lower() in special_packages:
            pkg_info = special_packages[name.lower()]
            return ComplianceIssue(
                package_name=name,
                license_name=license_name,
                issue_type="special_requirement",
                severity=pkg_info['severity'],
                description=pkg_info['issue'],
                recommendation=pkg_info['recommendation']
            )

        return None

    def generate_report(self, report: ComplianceReport, output_file: Optional[Path] = None):
        """生成合规报告"""
        lines = []

        # 报告头部
        lines.append("# 许可证合规报告")
        lines.append("")
        lines.append(f"**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**整体状态**: {self._format_status(report.status)}")
        lines.append(f"**总结**: {report.summary}")
        lines.append("")

        # 统计信息
        lines.append("## 📊 统计信息")
        lines.append("")
        lines.append(f"- 总包数: {report.total_packages}")
        lines.append(f"- 合规包数: {report.compliant_packages}")
        lines.append(f"- 警告包数: {report.warning_packages}")
        lines.append(f"- 不合规包数: {report.non_compliant_packages}")
        lines.append(f"- 合规率: {report.compliant_packages / report.total_packages * 100:.1f}%")
        lines.append("")

        # 问题详情
        if report.issues:
            lines.append("## ⚠️ 发现的问题")
            lines.append("")

            # 按严重程度分组
            issues_by_severity = {}
            for issue in report.issues:
                if issue.severity not in issues_by_severity:
                    issues_by_severity[issue.severity] = []
                issues_by_severity[issue.severity].append(issue)

            severity_order = ['critical', 'high', 'medium', 'low']
            for severity in severity_order:
                if severity in issues_by_severity:
                    lines.append(f"### {severity.upper()} 级别问题")
                    lines.append("")

                    for issue in issues_by_severity[severity]:
                        lines.append(f"**{issue.package_name}** ({issue.license_name})")
                        lines.append(f"- 问题: {issue.description}")
                        if issue.recommendation:
                            lines.append(f"- 建议: {issue.recommendation}")
                        lines.append("")
        else:
            lines.append("## ✅ 未发现问题")
            lines.append("")
            lines.append("所有依赖包的许可证都符合要求。")

        # 写入文件
        report_content = "\n".join(lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"报告已保存到: {output_file}")

        return report_content

    def _format_status(self, status: ComplianceStatus) -> str:
        """格式化状态"""
        status_map = {
            ComplianceStatus.COMPLIANT: "✅ 合规",
            ComplianceStatus.WARNING: "⚠️ 警告",
            ComplianceStatus.NON_COMPLIANT: "❌ 不合规"
        }
        return status_map.get(status, "未知")

    def check_ci_compliance(self) -> bool:
        """CI合规检查（用于CI/CD）"""
        report = self.check_compliance()

        # 输出简要信息
        print(f"📄 许可证合规检查结果: {report.summary}")
        print(f"📊 总计 {report.total_packages} 个包，合规率 {report.compliant_packages / report.total_packages * 100:.1f}%")

        # 生成JSON报告
        json_report = {
            'status': report.status.value,
            'summary': report.summary,
            'statistics': {
                'total': report.total_packages,
                'compliant': report.compliant_packages,
                'warning': report.warning_packages,
                'non_compliant': report.non_compliant_packages,
                'compliance_rate': report.compliant_packages / report.total_packages * 100
            },
            'issues': [
                {
                    'package': issue.package_name,
                    'license': issue.license_name,
                    'type': issue.issue_type,
                    'severity': issue.severity,
                    'description': issue.description,
                    'recommendation': issue.recommendation
                }
                for issue in report.issues
            ]
        }

        # 保存报告
        with open('license-compliance-report.json', 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        # 根据结果决定CI是否通过
        if report.status == ComplianceStatus.NON_COMPLIANT:
            print("❌ 许可证合规检查失败，CI未通过")
            for issue in report.issues:
                if issue.severity in ['critical', 'high']:
                    print(f"  - {issue.package_name}: {issue.description}")
            return False
        else:
            print("✅ 许可证合规检查通过")
            return True


def main():
    """主函数"""
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="许可证合规检查")
    parser.add_argument('--input', '-i', type=Path,
                       help="输入的许可证报告文件")
    parser.add_argument('--output', '-o', type=Path,
                       help="输出的合规报告文件")
    parser.add_argument('--format', choices=['text', 'json'],
                       default='text', help="输出格式")
    parser.add_argument('--ci', action='store_true',
                       help="CI模式，返回退出码")

    args = parser.parse_args()

    # 初始化检查器
    checker = LicenseComplianceChecker()

    # 执行检查
    report = checker.check_compliance(args.input)

    if args.ci:
        # CI模式
        success = checker.check_ci_compliance()
        sys.exit(0 if success else 1)
    else:
        # 生成报告
        if args.format == 'json':
            json_data = {
                'status': report.status.value,
                'summary': report.summary,
                'statistics': {
                    'total': report.total_packages,
                    'compliant': report.compliant_packages,
                    'warning': report.warning_packages,
                    'non_compliant': report.non_compliant_packages
                },
                'issues': [
                    {
                        'package': issue.package_name,
                        'license': issue.license_name,
                        'type': issue.issue_type,
                        'severity': issue.severity,
                        'description': issue.description
                    }
                    for issue in report.issues
                ]
            }

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                print(f"JSON报告已保存到: {args.output}")
            else:
                print(json.dumps(json_data, indent=2, ensure_ascii=False))
        else:
            # 文本格式
            report_content = checker.generate_report(report, args.output)
            if not args.output:
                print(report_content)


if __name__ == "__main__":
    main()