#!/usr/bin/env python3
"""
依赖更新策略脚本
Dependency Update Strategy Script

自动管理依赖包的更新
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import re

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class PackageInfo:
    """包信息"""
    name: str
    current_version: str
    latest_version: str
    update_available: bool
    release_date: Optional[str] = None
    dependencies: List[str] = None
    vulnerabilities: List[Dict] = None
    deprecated: bool = False


@dataclass
class UpdatePolicy:
    """更新策略"""
    package: str
    strategy: str  # auto, manual, security, patch, minor, major
    reason: str
    last_updated: datetime


class DependencyManager:
    """依赖管理器"""

    def __init__(self, requirements_file: Path = None):
        """
        初始化依赖管理器

        Args:
            requirements_file: requirements.txt文件路径
        """
        self.requirements_file = requirements_file or project_root / "requirements.txt"
        self.dev_requirements_file = project_root / "requirements-dev.txt"
        self.lock_file = project_root / "requirements.lock"
        self.update_log_file = project_root / "dependency_updates.json"

        # PyPI API
        self.pypi_url = "https://pypi.org/pypi"

        # 更新策略
        self.update_policies: Dict[str, UpdatePolicy] = {}
        self._load_update_policies()

        # 已知的不兼容包
        self.incompatible_packages: Set[Tuple[str, str, str]] = set()
        self._load_incompatible_packages()

    def _load_update_policies(self):
        """加载更新策略"""
        policy_file = project_root / "scripts" / "update_policies.json"

        # 默认策略
        default_policies = {
            # 自动更新（安全补丁）
            "cryptography": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_81"),
                strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_81"),
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_82")
            ),
            "pydantic": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_83"),
                strategy="patch",
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_85")
            ),
            "fastapi": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_87"),
                strategy="minor",
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_88")
            ),
            "uvicorn": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_91"),
                strategy="auto",
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_92")
            ),

            # 手动更新（需要测试）
            "sqlalchemy": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_95"),
                strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_96"),
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_96")
            ),
            "psycopg2-binary": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_98"),
                strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_96"),
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_102")
            ),

            # 仅安全更新
            "requests": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_104"),
                strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_81"),
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_105")
            ),
            "python-jose": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_107"),
                strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_81"),
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_108")
            ),

            # 开发工具（自动更新）
            "black": UpdatePolicy(
                package="black",
                strategy="auto",
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_112")
            ),
            "ruff": UpdatePolicy(
                package="ruff",
                strategy="auto",
                reason = os.getenv("UPDATE_DEPENDENCIES_REASON_116")
            ),
            "pytest": UpdatePolicy(
                package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_117"),
                strategy="minor",
                reason="测试框架"
            ),
        }

        if policy_file.exists():
            try:
                with open(policy_file, 'r') as f:
                    custom_policies = json.load(f)
                    for pkg, policy_data in custom_policies.items():
                        policy = UpdatePolicy(**policy_data)
                        if isinstance(policy.last_updated, str):
                            policy.last_updated = datetime.fromisoformat(policy.last_updated)
                        default_policies[pkg] = policy
            except Exception as e:
                print(f"⚠️ 加载自定义策略失败: {e}")

        self.update_policies = default_policies

    def _load_incompatible_packages(self):
        """加载不兼容包列表"""
        # 已知的不兼容组合 (package, version1, version2)
        self.incompatible_packages = {
            # Django 4.0+ 不支持 Python 3.7
            ("django", "4.0.0", "python", "3.7"),
            # SQLAlchemy 2.0+ 有重大变更
            ("sqlalchemy", "2.0.0", "alembic", "1.7.0"),
        }

    def get_package_info(self, package_name: str) -> Optional[PackageInfo]:
        """获取包信息"""
        try:
            # 获取当前版本
            current_version = self._get_current_version(package_name)
            if not current_version:
                return None

            # 获取最新版本信息
            response = requests.get(f"{self.pypi_url}/{package_name}/json", timeout=10)
            response.raise_for_status()
            data = response.json()

            releases = data.get('releases', {})
            if not releases:
                return None

            # 获取最新版本
            latest_version = self._get_latest_version(releases)
            if not latest_version:
                return None

            # 检查是否废弃
            deprecated = self._is_deprecated(data)

            # 获取依赖信息
            dependencies = self._get_dependencies(data, latest_version)

            # 获取发布日期
            release_date = self._get_release_date(releases, latest_version)

            return PackageInfo(
                name=package_name,
                current_version=current_version,
                latest_version=latest_version,
                update_available=self._version_compare(current_version, latest_version) < 0,
                release_date=release_date,
                dependencies=dependencies,
                deprecated=deprecated
            )

        except Exception as e:
            print(f"⚠️ 获取包信息失败 {package_name}: {e}")
            return None

    def _get_current_version(self, package_name: str) -> Optional[str]:
        """获取当前安装的版本"""
        try:
            result = subprocess.run(
                ['pip', 'show', package_name],
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':')[1].strip()

        except subprocess.CalledProcessError:
            return None

    def _get_latest_version(self, releases: Dict) -> Optional[str]:
        """获取最新版本"""
        versions = []
        for version_str in releases.keys():
            # 过滤预发布版本
            if not any(pre in version_str for pre in ['a', 'b', 'rc', 'alpha', 'beta']):
                try:
                    # 解析版本号
                    version_parts = re.findall(r'\d+', version_str)
                    if version_parts:
                        versions.append((version_parts, version_str))
                except:
                    pass

        if versions:
            # 返回最新版本
            versions.sort(key=lambda x: [int(i) for i in x[0]], reverse=True)
            return versions[0][1]

        return None

    def _is_deprecated(self, package_data: Dict) -> bool:
        """检查包是否废弃"""
        info = package_data.get('info', {})
        return any(keyword in info.get('summary', '').lower()
                  for keyword in ['deprecated', 'unmaintained', 'abandoned'])

    def _get_dependencies(self, package_data: Dict, version: str) -> List[str]:
        """获取依赖列表"""
        releases = package_data.get('releases', {})
        if version not in releases:
            return []

        for file_info in releases[version]:
            if file_info.get('packagetype') == 'bdist_wheel':
                requires_dist = file_info.get('requires_dist', [])
                if requires_dist:
                    # 提取包名
                    deps = []
                    for req in requires_dist:
                        dep = req.split('[')[0].split('<')[0].split('>')[0].split('==')[0].split('!=')[0]
                        deps.append(dep.strip())
                    return deps

        return []

    def _get_release_date(self, releases: Dict, version: str) -> Optional[str]:
        """获取发布日期"""
        if version in releases:
            for file_info in releases[version]:
                upload_time = file_info.get('upload_time')
                if upload_time:
                    return upload_time.split('T')[0]
        return None

    def _version_compare(self, v1: str, v2: str) -> int:
        """比较版本号 (v1 < v2: -1, v1 == v2: 0, v1 > v2: 1)"""
        def normalize(v):
            return [int(x) for x in re.findall(r'\d+', v)]

        v1_parts = normalize(v1)
        v2_parts = normalize(v2)

        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))

        for a, b in zip(v1_parts, v2_parts):
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0

    def check_updates(self) -> List[PackageInfo]:
        """检查所有包的更新"""
        packages = self._parse_requirements()
        updates = []

        print("🔍 检查包更新...")
        for package in packages:
            info = self.get_package_info(package)
            if info and info.update_available:
                updates.append(info)
                print(f"  {package}: {info.current_version} → {info.latest_version}")

        return updates

    def _parse_requirements(self) -> List[str]:
        """解析requirements文件"""
        packages = []

        if self.requirements_file.exists():
            with open(self.requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 提取包名
                        package = line.split('[')[0].split('>')[0].split('<')[0].split('==')[0].split('!=')[0]
                        packages.append(package.strip())

        return packages

    def check_vulnerabilities(self) -> Dict[str, List[Dict]]:
        """检查安全漏洞"""
        print("🔒 检查安全漏洞...")

        vulnerabilities = {}

        try:
            # 使用pip-audit
            result = subprocess.run(
                ['pip-audit', '--requirement', str(self.requirements_file), '--format', 'json'],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                print("✅ 未发现安全漏洞")
            else:
                try:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get('vulnerabilities', []):
                        pkg = vuln.get('name')
                        if pkg:
                            if pkg not in vulnerabilities:
                                vulnerabilities[pkg] = []
                            vulnerabilities[pkg].append({
                                'id': vuln.get('id'),
                                'version': vuln.get('version'),
                                'advisory': vuln.get('advisory', {})
                            })
                except json.JSONDecodeError:
                    print("⚠️ 无法解析pip-audit输出")

        except FileNotFoundError:
            print("⚠️ pip-audit未安装，跳过安全检查")
            print("   安装命令: pip install pip-audit")

        return vulnerabilities

    def update_package(self, package: str, version: str = None,
                      strategy: str = None) -> bool:
        """更新包"""
        current_version = self._get_current_version(package)
        if not current_version:
            print(f"❌ 包未安装: {package}")
            return False

        # 获取更新策略
        if not strategy:
            policy = self.update_policies.get(package)
            if policy:
                strategy = policy.strategy
            else:
                strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_360")

        # 获取目标版本
        if not version:
            info = self.get_package_info(package)
            if info:
                version = info.latest_version
            else:
                print(f"❌ 无法获取包信息: {package}")
                return False

        print(f"\n🔄 更新包: {package}")
        print(f"  当前版本: {current_version}")
        print(f"  目标版本: {version}")
        print(f"  更新策略: {strategy}")

        # 根据策略决定是否更新
        should_update = self._should_update(package, current_version, version, strategy)

        if not should_update:
            print(f"⏭️ 跳过更新（策略限制）")
            return False

        # 执行更新
        try:
            if version:
                cmd = ['pip', 'install', f'{package}=={version}']
            else:
                cmd = ['pip', 'install', '--upgrade', package]

            print(f"  执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True)

            # 更新requirements文件
            self._update_requirements_file(package, version or "latest")

            # 记录更新
            self._record_update(package, current_version, version or "latest", strategy)

            print(f"✅ 更新成功: {package}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ 更新失败: {e}")
            return False

    def _should_update(self, package: str, current: str, latest: str,
                       strategy: str) -> bool:
        """判断是否应该更新"""
        cmp = self._version_compare(current, latest)

        if cmp >= 0:
            return False  # 已经是最新版本

        current_parts = [int(x) for x in re.findall(r'\d+', current)]
        latest_parts = [int(x) for x in re.findall(r'\d+', latest)]

        # 确定更新类型
        if len(current_parts) >= 2 and len(latest_parts) >= 2:
            if current_parts[0] < latest_parts[0]:
                update_type = "major"
            elif current_parts[1] < latest_parts[1]:
                update_type = "minor"
            else:
                update_type = "patch"
        else:
            update_type = "minor"

        # 根据策略决定
        if strategy == "auto":
            return True
        elif strategy == "security":
            # 需要检查是否有安全漏洞
            vulns = self.check_vulnerabilities()
            return package in vulns
        elif strategy == "patch":
            return update_type == "patch"
        elif strategy == "minor":
            return update_type in ["patch", "minor"]
        elif strategy == "major":
            return update_type in ["patch", "minor", "major"]
        else:  # manual
            return False

    def _update_requirements_file(self, package: str, version: str):
        """更新requirements文件"""
        if not self.requirements_file.exists():
            return

        lines = []
        updated = False

        with open(self.requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 检查是否是目标包
                    pkg_pattern = re.escape(package).replace('\\*', '.*?')
                    if re.match(f'^{pkg_pattern}[\\[=<>!]', line):
                        if version == "latest":
                            # 移除版本限制
                            line = package
                        else:
                            # 更新版本
                            line = f"{package}=={version}"
                        updated = True
                lines.append(line)

        if updated:
            with open(self.requirements_file, 'w') as f:
                f.write('\n'.join(lines))

    def _record_update(self, package: str, old_version: str,
                      new_version: str, strategy: str):
        """记录更新"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'package': package,
            'old_version': old_version,
            'new_version': new_version,
            'strategy': strategy
        }

        # 加载现有日志
        update_log = []
        if self.update_log_file.exists():
            try:
                with open(self.update_log_file, 'r') as f:
                    update_log = json.load(f)
            except:
                pass

        # 添加新日志
        update_log.append(log_entry)

        # 保留最近100条记录
        if len(update_log) > 100:
            update_log = update_log[-100:]

        # 保存日志
        with open(self.update_log_file, 'w') as f:
            json.dump(update_log, f, indent=2)

    def generate_update_report(self) -> str:
        """生成更新报告"""
        updates = self.check_updates()
        vulnerabilities = self.check_vulnerabilities()

        report = []
        report.append("=" * 60)
        report.append("依赖更新报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 更新摘要
        report.append("📊 更新摘要:")
        report.append(f"  可更新包: {len(updates)}")
        report.append(f"  安全漏洞: {sum(len(v) for v in vulnerabilities.values())}")
        report.append("")

        # 待更新包
        if updates:
            report.append("🔄 待更新包:")
            for pkg in sorted(updates, key=lambda x: x.name):
                policy = self.update_policies.get(pkg.name)
                strategy = policy.strategy if policy else "manual"
                report.append(f"  - {pkg.name}: {pkg.current_version} → {pkg.latest_version} ({strategy})")
                if pkg.deprecated:
                    report.append(f"    ⚠️ 该包已废弃！")
            report.append("")

        # 安全漏洞
        if vulnerabilities:
            report.append("🔒 安全漏洞:")
            for pkg, vulns in vulnerabilities.items():
                report.append(f"  - {pkg}: {len(vulns)} 个漏洞")
                for vuln in vulns[:2]:  # 只显示前2个
                    advisory = vuln.get('advisory', {})
                    severity = advisory.get('severity', 'Unknown')
                    desc = advisory.get('description', 'No description')
                    report.append(f"    • {severity}: {desc[:80]}...")
            report.append("")

        # 更新建议
        report.append("💡 更新建议:")
        auto_updates = [pkg for pkg in updates
                      if self.update_policies.get(pkg.name, UpdatePolicy("", "", "", datetime.now())).strategy == "auto"]
        if auto_updates:
            report.append(f"  可自动更新 ({len(auto_updates)} 个):")
            for pkg in auto_updates[:5]:
                report.append(f"    - {pkg.name}")

        security_updates = []
        for pkg in updates:
            if pkg.name in vulnerabilities:
                security_updates.append(pkg)

        if security_updates:
            report.append(f"\n  安全更新优先 ({len(security_updates)} 个):")
            for pkg in security_updates:
                report.append(f"    - {pkg.name}")

        report.append("")
        report.append("📝 执行更新:")
        report.append("  自动更新所有: python scripts/update_dependencies.py --auto")
        report.append("  更新单个包: python scripts/update_dependencies.py --package <package>")
        report.append("  安全更新: python scripts/update_dependencies.py --security")

        return "\n".join(report)

    def auto_update(self, strategy_filter: str = None) -> bool:
        """自动更新包"""
        updates = self.check_updates()
        success_count = 0
        total_count = len(updates)

        print(f"\n🚀 开始自动更新 ({total_count} 个包)")

        for pkg in updates:
            policy = self.update_policies.get(pkg.name)
            if not policy:
                print(f"\n⚠️ {pkg.name}: 无更新策略，跳过")
                continue

            if strategy_filter and policy.strategy != strategy_filter:
                continue

            if self.update_package(pkg.name, pkg.latest_version, policy.strategy):
                success_count += 1

        print(f"\n✅ 更新完成: {success_count}/{total_count}")
        return success_count == total_count


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("UPDATE_DEPENDENCIES_DESCRIPTION_594"))
    parser.add_argument('--check', '-c', action = os.getenv("UPDATE_DEPENDENCIES_ACTION_596"), help="检查更新")
    parser.add_argument('--package', '-p', help="更新指定包")
    parser.add_argument('--version', '-v', help="指定版本")
    parser.add_argument('--auto', '-a', action = os.getenv("UPDATE_DEPENDENCIES_ACTION_596"), help="自动更新")
    parser.add_argument('--security', '-s', action = os.getenv("UPDATE_DEPENDENCIES_ACTION_596"), help="仅安全更新")
    parser.add_argument('--report', '-r', action = os.getenv("UPDATE_DEPENDENCIES_ACTION_596"), help="生成报告")
    parser.add_argument('--output', '-o', help = os.getenv("UPDATE_DEPENDENCIES_HELP_610"))

    args = parser.parse_args()

    # 初始化依赖管理器
    manager = DependencyManager()

    # 执行命令
    if args.check:
        updates = manager.check_updates()
        if updates:
            print(f"\n发现 {len(updates)} 个更新")
        else:
            print("\n所有包都是最新版本")

    elif args.package:
        manager.update_package(args.package, args.version)

    elif args.auto:
        if args.security:
            manager.auto_update("security")
        else:
            manager.auto_update()

    elif args.report:
        report = manager.generate_update_report()
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"报告已保存到: {args.output}")
        else:
            print(report)

    else:
        # 默认检查更新
        manager.check_updates()


if __name__ == "__main__":
    main()