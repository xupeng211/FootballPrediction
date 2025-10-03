#!/usr/bin/env python3
"""
依赖诊断工具
全面检测项目中的依赖冲突问题
"""

import os
import sys
import json
import subprocess
import importlib
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import warnings

@dataclass
class DependencyIssue:
    """依赖问题"""
    type: str  # conflict, missing, outdated, circular
    package: str
    description: str
    severity: str  # critical, high, medium, low
    solution: str
    affected_modules: List[str]

@dataclass
class PackageInfo:
    """包信息"""
    name: str
    version: str
    location: str
    dependencies: List[str]
    dependents: List[str]
    size: int = 0
    install_time: str = ""

class DependencyDiagnostic:
    def __init__(self):
        self.issues: List[DependencyIssue] = []
        self.packages: Dict[str, PackageInfo] = {}
        self.project_root = Path(__file__).parent.parent.parent

    def run_full_diagnosis(self) -> Dict[str, Any]:
        """运行完整诊断"""
        print("🔍 开始依赖诊断...")
        print("="*60)

        results = {
            "timestamp": "",
            "environment": {},
            "packages": {},
            "issues": [],
            "recommendations": []
        }

        # 1. 环境信息
        print("\n📍 1. 收集环境信息...")
        results["environment"] = self._collect_environment_info()

        # 2. 检测已安装包
        print("\n📦 2. 扫描已安装包...")
        self._scan_installed_packages()
        results["packages"] = {k: v.__dict__ for k, v in self.packages.items()}

        # 3. 检测已知冲突
        print("\n⚠️ 3. 检测已知冲突...")
        self._detect_known_conflicts()

        # 4. 检测版本冲突
        print("\n💥 4. 检测版本冲突...")
        self._detect_version_conflicts()

        # 5. 检测循环依赖
        print("\n🔄 5. 检测循环依赖...")
        self._detect_circular_dependencies()

        # 6. 检测项目导入问题
        print("\n📥 6. 测试项目导入...")
        self._test_project_imports()

        # 7. 检测过时包
        print("\n📅 7. 检测过时包...")
        self._detect_outdated_packages()

        # 8. 生成建议
        print("\n💡 8. 生成建议...")
        results["recommendations"] = self._generate_recommendations()

        results["issues"] = [issue.__dict__ for issue in self.issues]
        results["timestamp"] = self._get_timestamp()

        # 保存结果
        self._save_results(results)

        # 打印摘要
        self._print_summary(results)

        return results

    def _collect_environment_info(self) -> Dict[str, str]:
        """收集环境信息"""
        info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "executable": sys.executable,
            "pip_version": self._get_pip_version(),
            "virtual_env": os.environ.get("VIRTUAL_ENV", "None"),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "None")
        }

        # 检查是否有Docker
        if os.path.exists("/.dockerenv"):
            info["environment"] = "Docker"

        return info

    def _get_pip_version(self) -> str:
        """获取pip版本"""
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "Unknown"

    def _scan_installed_packages(self):
        """扫描已安装包"""
        try:
            import pkg_resources
            for dist in pkg_resources.working_set:
                package_info = PackageInfo(
                    name=dist.project_name,
                    version=dist.version,
                    location=dist.location,
                    dependencies=[str(req) for req in dist.requires()],
                    dependents=[]
                )
                self.packages[dist.project_name] = package_info
        except Exception as e:
            print(f"扫描包失败: {e}")
            # 尝试替代方法
            self._scan_packages_alternative()

    def _scan_packages_alternative(self):
        """替代的包扫描方法"""
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"],
                                  capture_output=True, text=True)
            packages = json.loads(result.stdout)
            for pkg in packages:
                package_info = PackageInfo(
                    name=pkg["name"],
                    version=pkg["version"],
                    location="",
                    dependencies=[],
                    dependents=[]
                )
                self.packages[pkg["name"]] = package_info
        except:
            print("无法获取包列表")

    def _detect_known_conflicts(self):
        """检测已知冲突"""
        known_conflicts = [
            {
                "packages": ["scipy", "highspy"],
                "issue": "类型注册冲突",
                "symptom": "ImportError: generic_type: type \"ObjSense\" is already registered!",
                "solution": "使用兼容版本或降级highspy"
            },
            {
                "packages": ["sklearn", "scipy"],
                "issue": "版本不兼容",
                "symptom": "导入sklearn时触发scipy错误",
                "solution": "确保scipy >= 1.9.0且与sklearn兼容"
            },
            {
                "packages": ["tensorflow", "numpy"],
                "issue": "版本限制",
                "symptom": "numpy版本过高或过低",
                "solution": "使用tensorflow指定的numpy版本范围"
            },
            {
                "packages": ["pydantic", "fastapi"],
                "issue": "版本差异",
                "symptom": "DeprecationWarning或API不兼容",
                "solution": "确保pydantic >= 2.0且与fastapi兼容"
            }
        ]

        for conflict in known_conflicts:
            installed_packages = [p for p in conflict["packages"] if p in self.packages]
            if len(installed_packages) > 1:
                issue = DependencyIssue(
                    type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_196"),
                    package=", ".join(installed_packages),
                    description=f"{conflict['issue']}: {conflict['symptom']}",
                    severity = os.getenv("DIAGNOSE_DEPENDENCIES_SEVERITY_198"),
                    solution=conflict["solution"],
                    affected_modules=[]
                )
                self.issues.append(issue)
                print(f"  ⚠️ 发现冲突: {conflict['packages']}")

    def _detect_version_conflicts(self):
        """检测版本冲突"""
        # 检查重复包的不同版本
        version_map = {}
        for name, info in self.packages.items():
            base_name = name.lower()
            if base_name not in version_map:
                version_map[base_name] = {}
            version_map[base_name][info.version] = info.location

        for base_name, versions in version_map.items():
            if len(versions) > 1:
                issue = DependencyIssue(
                    type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_217"),
                    package=base_name,
                    description=f"发现多个版本: {list(versions.keys())}",
                    severity="high",
                    solution = os.getenv("DIAGNOSE_DEPENDENCIES_SOLUTION_221"),
                    affected_modules=[]
                )
                self.issues.append(issue)
                print(f"  💥 版本冲突: {base_name} 有 {len(versions)} 个版本")

    def _detect_circular_dependencies(self):
        """检测循环依赖"""
        # 构建依赖图
        graph = {}
        for name, info in self.packages.items():
            graph[name] = []
            for dep in info.dependencies:
                dep_name = dep.split(">=")[0].split("==")[0].split("<=")[0].strip()
                graph[name].append(dep_name)

        # 简单的循环检测
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    issue = DependencyIssue(
                        type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_259"),
                        package=node,
                        description=f"检测到循环依赖，涉及: {node}",
                        severity="high",
                        solution = os.getenv("DIAGNOSE_DEPENDENCIES_SOLUTION_262"),
                        affected_modules=[]
                    )
                    self.issues.append(issue)
                    print(f"  🔄 循环依赖: {node}")

    def _test_project_imports(self):
        """测试项目导入"""
        test_modules = [
            "src.api.schemas",
            "src.api.data",
            "src.api.health",
            "src.api.models",
            "src.api.monitoring",
            "src.api.cache",
            "src.api.features",
            "src.api.predictions"
        ]

        for module in test_modules:
            try:
                # 抑制警告
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    importlib.import_module(module)
                print(f"  ✅ {module} - 导入成功")
            except ImportError as e:
                if "generic_type" in str(e):
                    severity = os.getenv("DIAGNOSE_DEPENDENCIES_SEVERITY_289")
                else:
                    severity = "high"

                issue = DependencyIssue(
                    type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_293"),
                    package=module,
                    description=f"导入失败: {str(e)}",
                    severity=severity,
                    solution = os.getenv("DIAGNOSE_DEPENDENCIES_SOLUTION_296"),
                    affected_modules=[module]
                )
                self.issues.append(issue)
                print(f"  ❌ {module} - 导入失败: {str(e)[:100]}")

    def _detect_outdated_packages(self):
        """检测过时包"""
        # 这里简化处理，实际可以调用pip list --outdated
        outdated_checks = {
            "scipy": "1.9.0",
            "numpy": "1.20.0",
            "pandas": "1.3.0",
            "matplotlib": "3.5.0",
            "sklearn": "1.0.0"
        }

        for package, min_version in outdated_checks.items():
            if package in self.packages:
                current_version = self.packages[package].version
                # 简单版本比较（实际应该使用packaging.version）
                try:
                    current_parts = [int(x) for x in current_version.split('.')]
                    min_parts = [int(x) for x in min_version.split('.')]

                    if current_parts < min_parts:
                        issue = DependencyIssue(
                            type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_323"),
                            package=package,
                            description=f"版本过时: {current_version} < {min_version}",
                            severity = os.getenv("DIAGNOSE_DEPENDENCIES_SEVERITY_326"),
                            solution=f"升级到 {min_version} 或更高版本",
                            affected_modules=[]
                        )
                        self.issues.append(issue)
                        print(f"  📅 {package} - 版本过时: {current_version}")
                except:
                    pass

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """生成建议"""
        recommendations = []

        # 统计问题
        critical_issues = [i for i in self.issues if i.severity == "critical"]
        high_issues = [i for i in self.issues if i.severity == "high"]

        if critical_issues:
            recommendations.append({
                "priority": "urgent",
                "action": "立即解决关键冲突",
                "description": f"发现 {len(critical_issues)} 个关键问题，需要立即处理"
            })

        if "scipy" in self.packages and "highspy" in self.packages:
            recommendations.append({
                "priority": "high",
                "action": "解决scipy/highspy冲突",
                "description": "尝试: pip uninstall highspy && pip install scipy==1.11.4"
            })

        recommendations.append({
            "priority": "medium",
            "action": "创建requirements.lock",
            "description": "锁定所有依赖版本，确保环境一致性"
        })

        recommendations.append({
            "priority": "medium",
            "action": "设置虚拟环境",
            "description": "使用独立的Python虚拟环境，避免全局污染"
        })

        return recommendations

    def _save_results(self, results: Dict[str, Any]):
        """保存诊断结果"""
        output_dir = Path("docs/_reports/dependency_health")
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON格式
        json_file = output_dir / f"dependency_diagnosis_{self._get_timestamp().replace(':', '-')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Markdown报告
        md_file = output_dir / "dependency_diagnosis_report.md"
        self._generate_markdown_report(results, md_file)

        print(f"\n📄 诊断结果已保存到: {output_dir}")

    def _generate_markdown_report(self, results: Dict[str, Any], filename: Path):
        """生成Markdown报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 依赖诊断报告\n\n")
            f.write(f"生成时间: {results['timestamp']}\n\n")

            f.write("## 环境信息\n\n")
            f.write(f"- Python版本: {results['environment']['python_version']}\n")
            f.write(f"- 平台: {results['environment']['platform']}\n")
            f.write(f"- 虚拟环境: {results['environment']['virtual_env']}\n\n")

            f.write("## 发现的问题\n\n")
            for issue in results['issues']:
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(issue['severity'], "⚪")

                f.write(f"### {severity_icon} {issue['package']} - {issue['type']}\n")
                f.write(f"**描述**: {issue['description']}\n\n")
                f.write(f"**解决方案**: {issue['solution']}\n\n")

            f.write("## 建议\n\n")
            for rec in results['recommendations']:
                priority_icon = {
                    "urgent": "🔥",
                    "high": "⬆️",
                    "medium": "➡️",
                    "low": "⬇️"
                }.get(rec['priority'], "📌")

                f.write(f"### {priority_icon} {rec['action']}\n")
                f.write(f"{rec['description']}\n\n")

    def _print_summary(self, results: Dict[str, Any]):
        """打印摘要"""
        print("\n" + "="*60)
        print("📊 诊断摘要")
        print("="*60)

        total_issues = len(results['issues'])
        critical = len([i for i in results['issues'] if i['severity'] == 'critical'])
        high = len([i for i in results['issues'] if i['severity'] == 'high'])
        medium = len([i for i in results['issues'] if i['severity'] == 'medium'])
        low = len([i for i in results['issues'] if i['severity'] == 'low'])

        print(f"\n📈 问题统计:")
        print(f"  总计: {total_issues}")
        print(f"  🔴 关键: {critical}")
        print(f"  🟠 高: {high}")
        print(f"  🟡 中: {medium}")
        print(f"  🟢 低: {low}")

        if total_issues > 0:
            print(f"\n🔝 最严重的问题:")
            sorted_issues = sorted(results['issues'],
                                 key=lambda x: ['critical', 'high', 'medium', 'low'].index(x['severity']))
            for issue in sorted_issues[:3]:
                print(f"  • {issue['package']}: {issue['description'][:80]}...")

        print(f"\n💡 建议 ({len(results['recommendations'])}条):")
        for rec in results['recommendations'][:3]:
            print(f"  • {rec['action']}")

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    diagnostic = DependencyDiagnostic()
    results = diagnostic.run_full_diagnosis()

    # 如果有关键问题，返回非零退出码
    critical_issues = [i for i in results['issues'] if i['severity'] == 'critical']
    if critical_issues:
        sys.exit(1)