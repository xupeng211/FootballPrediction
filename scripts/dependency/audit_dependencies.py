#!/usr/bin/env python3
"""
依赖审计脚本
分析项目中所有的依赖定义文件，检测冲突和差异
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import json

class DependencyAuditor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.dependencies = defaultdict(dict)
        self.conflicts = []
        self.issues = []

    def parse_requirement_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        """解析requirements文件中的一行，返回(包名, 版本, 来源)"""
        line = line.strip()

        # 跳过注释和空行
        if not line or line.startswith('#') or line.startswith('-'):
            return None

        # 处理 -r 引用
        if line.startswith('-r '):
            return None

        # 提取包名和版本
        # 支持 package==1.0.0, package>=1.0.0, package~=1.0.0等格式
        match = re.match(r'^([a-zA-Z0-9][a-zA-Z0-9\-_\.]*)\s*([><=!~]+.*)?$', line)
        if match:
            package = match.group(1).lower()
            version = match.group(2) if match.group(2) else "any"
            return (package, version, line)

        return None

    def read_requirements_file(self, file_path: Path, context: str) -> Dict[str, Dict]:
        """读取requirements文件"""
        deps = {}

        if not file_path.exists():
            return deps

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            result = self.parse_requirement_line(line)
            if result:
                package, version, raw_line = result
                deps[package] = {
                    'version': version,
                    'context': context,
                    'file': str(file_path),
                    'line': line_num,
                    'raw': raw_line
                }

        return deps

    def scan_all_files(self):
        """扫描所有依赖定义文件"""
        # 1. requirements文件
        req_files = [
            ('requirements.txt', 'production'),
            ('requirements-dev.txt', 'development'),
            ('requirements-test.txt', 'test'),
            ('requirements.lock.txt', 'locked'),
            ('requirements_full.txt', 'full'),
            ('tests/requirements.txt', 'test-legacy'),
        ]

        for file_name, context in req_files:
            file_path = self.project_root / file_name
            deps = self.read_requirements_file(file_path, context)
            for pkg, info in deps.items():
                self.dependencies[pkg][context] = info

        # 2. setup.py中的依赖
        setup_py = self.project_root / 'setup.py'
        if setup_py.exists():
            with open(setup_py, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析extras_require
            extras_match = re.search(r'"dev":\s*\[(.*?)\]', content, re.DOTALL)
            if extras_match:
                dev_deps = extras_match.group(1)
                for line in dev_deps.split(','):
                    line = line.strip().strip('"\'')
                    result = self.parse_requirement_line(line)
                    if result:
                        package, version, _ = result
                        self.dependencies[package]['setup.py-dev'] = {
                            'version': version,
                            'context': 'setup.py-dev',
                            'file': 'setup.py',
                            'line': 0,
                            'raw': line
                        }

        # 3. 读取环境快照
        env_freeze = self.project_root / 'docs/_reports/ENVIRONMENT_FREEZE.txt'
        if env_freeze.exists():
            with open(env_freeze, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                result = self.parse_requirement_line(line)
                if result:
                    package, version, _ = result
                    self.dependencies[package]['environment'] = {
                        'version': version,
                        'context': 'environment',
                        'file': 'ENVIRONMENT_FREEZE.txt',
                        'line': line_num,
                        'raw': line
                    }

    def detect_conflicts(self):
        """检测版本冲突"""
        for package, contexts in self.dependencies.items():
            versions = {}
            for context, info in contexts.items():
                version = info['version']
                if version != 'any':
                    if version not in versions:
                        versions[version] = []
                    versions[version].append(context)

            # 如果同一个包有多个不同版本
            if len(versions) > 1:
                conflict = {
                    'package': package,
                    'type': 'version_conflict',
                    'versions': versions,
                    'message': f"Package {package} has conflicting versions"
                }
                self.conflicts.append(conflict)

    def detect_issues(self):
        """检测各种问题"""
        # 1. 检查在环境中但未声明的包
        env_packages = set()
        declared_packages = set()

        for package, contexts in self.dependencies.items():
            if 'environment' in contexts:
                env_packages.add(package)
            if any(ctx not in ['environment'] for ctx in contexts):
                declared_packages.add(package)

        undeclared = env_packages - declared_packages
        if undeclared:
            self.issues.append({
                'type': 'undeclared_dependencies',
                'count': len(undeclared),
                'packages': sorted(list(undeclared)[:20]),  # 只显示前20个
                'message': f"Found {len(undeclared)} packages in environment but not declared"
            })

        # 2. 检查声明但未安装的包
        not_installed = declared_packages - env_packages
        if not_installed:
            self.issues.append({
                'type': 'not_installed',
                'count': len(not_installed),
                'packages': sorted(list(not_installed)),
                'message': f"Found {len(not_installed)} declared packages but not installed"
            })

        # 3. 检查重复定义
        duplicates = defaultdict(list)
        for package, contexts in self.dependencies.items():
            for context, info in contexts.items():
                if context not in ['environment'] and info['version'] != 'any':
                    duplicates[package].append(context)

        duplicate_defs = {pkg: ctxs for pkg, ctxs in duplicates.items() if len(ctxs) > 1}
        if duplicate_defs:
            self.issues.append({
                'type': 'duplicate_definitions',
                'count': len(duplicate_defs),
                'packages': duplicate_defs,
                'message': f"Found {len(duplicate_defs)} packages defined in multiple files"
            })

    def generate_report(self) -> str:
        """生成Markdown报告"""
        report = []
        report.append("# 足球预测系统依赖审计报告\n")
        report.append(f"**生成时间**: {os.popen('date').read().strip()}\n")

        # 1. 依赖总览
        report.append("## 🔍 依赖总览\n")

        # 按上下文统计
        context_stats = defaultdict(int)
        for package, contexts in self.dependencies.items():
            for context in contexts:
                context_stats[context] += 1

        report.append("| 上下文 | 包数量 | 说明 |")
        report.append("|--------|--------|------|")
        context_order = ['production', 'development', 'test', 'locked', 'environment']
        for ctx in context_order:
            if ctx in context_stats:
                desc = {
                    'production': '生产依赖',
                    'development': '开发依赖',
                    'test': '测试依赖',
                    'locked': '锁定版本',
                    'environment': '当前环境'
                }.get(ctx, ctx)
                report.append(f"| {desc} | {context_stats[ctx]} | |")

        # 核心依赖列表
        report.append("\n### 核心生产依赖\n")
        report.append("| 包名 | 版本 | 文件 |")
        report.append("|------|------|------|")

        core_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 'pandas', 'numpy']
        for pkg in sorted(core_packages):
            if pkg in self.dependencies and 'production' in self.dependencies[pkg]:
                info = self.dependencies[pkg]['production']
                report.append(f"| {pkg} | {info['version']} | {info['file']} |")

        # 2. 冲突分析
        report.append("\n## ⚠️ 冲突与风险分析\n")

        if self.conflicts:
            report.append("### 版本冲突\n")
            report.append("| 包名 | 冲突版本 | 上下文 |")
            report.append("|------|----------|--------|")

            for conflict in self.conflicts:
                for version, contexts in conflict['versions'].items():
                    report.append(f"| {conflict['package']} | {version} | {', '.join(contexts)} |")
        else:
            report.append("✅ **未发现版本冲突**\n")

        # 3. 问题分析
        if self.issues:
            report.append("\n### 发现的问题\n")
            for issue in self.issues:
                report.append(f"\n#### {issue['type']}")
                report.append(f"{issue['message']}")

                if issue['type'] == 'undeclared_dependencies':
                    report.append("```")
                    report.append("\n".join(issue['packages'][:10]))
                    if len(issue['packages']) > 10:
                        report.append(f"... and {len(issue['packages']) - 10} more")
                    report.append("```")

                elif issue['type'] == 'not_installed':
                    report.append("```")
                    report.append(", ".join(issue['packages']))
                    report.append("```")

        # 4. 环境差异说明
        report.append("\n## 🧩 环境差异说明\n")

        env_total = sum(1 for p in self.dependencies.values() if 'environment' in p)
        declared_total = sum(1 for p in self.dependencies.values()
                           if any(ctx not in ['environment'] for ctx in p))

        report.append(f"- **当前环境已安装**: {env_total} 个包")
        report.append(f"- **已声明依赖**: {declared_total} 个包")

        if self.issues:
            for issue in self.issues:
                if issue['type'] == 'undeclared_dependencies':
                    report.append(f"- **未声明但已安装**: {issue['count']} 个包")
                elif issue['type'] == 'not_installed':
                    report.append(f"- **已声明但未安装**: {issue['count']} 个包")

        # 5. 优化建议
        report.append("\n## 💡 优化建议\n")

        report.append("### 立即行动项")
        report.append("1. **使用 pip-tools**")
        report.append("   - 创建 `requirements.in` 文件定义直接依赖")
        report.append("   - 使用 `pip-compile` 生成锁定文件")
        report.append("   - 确保版本一致性\n")

        report.append("2. **清理依赖定义**")
        report.append("   - 统一使用 requirements.txt 系列文件")
        report.append("   - 移除 setup.py 中的重复定义")
        report.append("   - 使用 `-r` 引用避免重复\n")

        report.append("3. **版本管理改进**")
        report.append("   - 为所有包指定精确版本")
        report.append("   - 使用 `>=` 替代 `==` 以允许补丁更新")
        report.append("   - 定期更新依赖版本\n")

        # 6. 下一步行动
        report.append("\n## 📌 下一步行动建议\n")
        report.append("1. **短期** (1-2天)")
        report.append("   - [ ] 运行 `pip install pip-tools`")
        report.append("   - [ ] 创建 `requirements.in` 和 `requirements-dev.in`")
        report.append("   - [ ] 生成锁定文件 `pip-compile requirements.in`")
        report.append("   - [ ] 更新 CI/CD 使用锁定文件\n")

        report.append("2. **中期** (1周)")
        report.append("   - [ ] 实施依赖扫描自动化")
        report.append("   - [ ] 集成 Dependabot 或 Renovate")
        report.append("   - [ ] 建立依赖更新流程\n")

        report.append("3. **长期** (持续)")
        report.append("   - [ ] 定期审计依赖安全性")
        report.append("   - [ ] 监控依赖许可证变更")
        report.append("   - [ ] 评估并移除未使用的依赖\n")

        # 总结
        report.append("\n---\n")
        report.append("### 总结\n")

        if self.conflicts:
            report.append(f"⚠️ 发现 **{len(self.conflicts)}** 个版本冲突需要解决")
        else:
            report.append("✅ 未发现严重的版本冲突")

        total_issues = sum(issue.get('count', 0) for issue in self.issues)
        if total_issues > 0:
            report.append(f"⚠️ 发现 **{total_issues}** 个依赖问题需要关注")
        else:
            report.append("✅ 依赖管理状况良好")

        report.append("\n建议立即实施 pip-tools 方案，实现更可靠的依赖管理。")

        return "\n".join(report)

    def save_analysis_json(self):
        """保存分析结果为JSON格式"""
        analysis = {
            'summary': {
                'total_packages': len(self.dependencies),
                'conflicts': len(self.conflicts),
                'issues': len(self.issues)
            },
            'dependencies': dict(self.dependencies),
            'conflicts': self.conflicts,
            'issues': self.issues
        }

        output_file = self.project_root / 'docs/_reports' / 'DEPENDENCY_ANALYSIS.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

def main():
    project_root = Path(__file__).parent.parent.parent
    auditor = DependencyAuditor(str(project_root))

    print("🔍 扫描依赖文件...")
    auditor.scan_all_files()

    print("⚠️ 检测冲突...")
    auditor.detect_conflicts()

    print("🔎 分析问题...")
    auditor.detect_issues()

    print("📝 生成报告...")
    report = auditor.generate_report()

    # 保存报告
    report_file = project_root / 'docs' / '_reports' / 'DEPENDENCY_AUDIT_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    # 保存JSON分析
    auditor.save_analysis_json()

    print(f"✅ 报告已生成: {report_file}")
    print(f"✅ 分析数据已保存: docs/_reports/DEPENDENCY_ANALYSIS.json")

    # 打印摘要
    print("\n📊 审计摘要:")
    print(f"- 总包数: {len(auditor.dependencies)}")
    print(f"- 版本冲突: {len(auditor.conflicts)}")
    print(f"- 发现问题: {len(auditor.issues)}")

if __name__ == "__main__":
    main()