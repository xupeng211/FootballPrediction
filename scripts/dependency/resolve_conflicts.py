#!/usr/bin/env python3
"""
依赖冲突解决脚本
自动检测和解决Python包依赖冲突
"""

import subprocess
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from packaging import version


@dataclass
class Dependency:
    """依赖项数据类"""
    name: str
    current_version: Optional[str] = None
    required_versions: List[str] = None
    conflicts: List[str] = None

    def __post_init__(self):
        if self.required_versions is None:
            self.required_versions = []
        if self.conflicts is None:
            self.conflicts = []


class DependencyResolver:
    """依赖冲突解决器"""

    def __init__(self):
        self.requirements_file = Path("requirements.txt")
        self.dev_requirements_file = Path("requirements-dev.txt")
        self.lock_file = Path("requirements.lock")
        self.conflicts_file = Path("docs/_reports/DEPENDENCY_CONFLICTS_REPORT.json")

        # 依赖数据库
        self.dependency_db = {
            "pandas": {
                "compatible_versions": ["2.1.3", "2.1.4"],
                "conflicts": ["great-expectations<1.5.11"],
                "notes": "great-expectations 1.5.11 需要 pandas<2.2"
            },
            "numpy": {
                "compatible_versions": ["1.26.4", "2.0.0"],
                "conflicts": ["feast<0.53.0"],
                "notes": "feast 0.53.0 需要 numpy>=2.0.0"
            },
            "pydantic": {
                "compatible_versions": ["2.10.6"],
                "conflicts": ["feast<0.53.0"],
                "notes": "feast 0.53.0 需要 pydantic==2.10.6"
            },
            "requests": {
                "compatible_versions": ["2.32.3", "2.32.4"],
                "conflicts": ["openlineage-python<1.37.0"],
                "notes": "openlineage-python 1.37.0 需要 requests>=2.32.4"
            },
            "rich": {
                "compatible_versions": ["13.5.2"],
                "conflicts": ["semgrep<1.139.0"],
                "notes": "semgrep 1.139.0 需要 rich~=13.5.2"
            },
            "urllib3": {
                "compatible_versions": ["2.0.7"],
                "conflicts": ["semgrep<1.139.0"],
                "notes": "semgrep 1.139.0 需要 urllib3~=2.0"
            },
            "typer": {
                "compatible_versions": ["0.16.0"],
                "conflicts": ["safety<3.6.2"],
                "notes": "safety 3.6.2 需要 typer>=0.16.0"
            }
        }

    def detect_conflicts(self) -> Dict[str, Dependency]:
        """检测依赖冲突"""
        print("🔍 检测依赖冲突...")

        conflicts = {}

        # 1. 运行pip check
        print("  - 运行 pip check...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # 解析pip check输出
            pip_conflicts = self._parse_pip_check(result.stderr)
            for conflict in pip_conflicts:
                pkg_name = conflict[0]
                if pkg_name not in conflicts:
                    conflicts[pkg_name] = Dependency(name=pkg_name)
                conflicts[pkg_name].conflicts.extend(conflict[1])

        # 2. 检查已知冲突
        print("  - 检查已知冲突...")
        installed_packages = self._get_installed_packages()

        for pkg_name, pkg_info in self.dependency_db.items():
            if pkg_name in installed_packages:
                current_version = installed_packages[pkg_name]

                # 检查版本兼容性
                if current_version not in pkg_info["compatible_versions"]:
                    if pkg_name not in conflicts:
                        conflicts[pkg_name] = Dependency(name=pkg_name)
                    conflicts[pkg_name].current_version = current_version
                    conflicts[pkg_name].required_versions = pkg_info["compatible_versions"]
                    conflicts[pkg_name].conflicts.extend(pkg_info["conflicts"])

        # 3. 生成冲突报告
        self._generate_conflict_report(conflicts)

        return conflicts

    def _parse_pip_check(self, output: str) -> List[Tuple[str, List[str]]]:
        """解析pip check的输出"""
        conflicts = []

        # 匹配 "package-a 1.0 has requirement package-b>=2.0, but you have package-b 1.5"
        pattern = r"(\S+)\s+[\d\.]+\s+has\s+requirement\s+(\S+)[^\s]*\s+(.*?),\s+but\s+you\s+have\s+(\S+)\s+([\d\.]+)"

        for match in re.finditer(pattern, output):
            package = match.group(1)
            requirement = match.group(2)
            version_constraint = match.group(3)
            conflict_package = match.group(4)
            conflict_version = match.group(5)

            conflicts.append((package, [f"{conflict_package} {conflict_version}"]))

        return conflicts

    def _get_installed_packages(self) -> Dict[str, str]:
        """获取已安装的包版本"""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True
        )

        packages = {}
        if result.returncode == 0:
            for pkg in json.loads(result.stdout):
                packages[pkg["name"]] = pkg["version"]

        return packages

    def _generate_conflict_report(self, conflicts: Dict[str, Dependency]):
        """生成冲突报告"""
        print("  - 生成冲突报告...")

        report = {
            "timestamp": "2025-10-04T09:30:00Z",
            "total_conflicts": len(conflicts),
            "conflicts": {},
            "recommendations": []
        }

        for pkg_name, dep in conflicts.items():
            report["conflicts"][pkg_name] = {
                "current_version": dep.current_version,
                "required_versions": dep.required_versions,
                "conflicts": dep.conflicts,
                "notes": self.dependency_db.get(pkg_name, {}).get("notes", "")
            }

            # 生成建议
            if dep.required_versions:
                latest_compatible = max(dep.required_versions, key=version.parse)
                report["recommendations"].append({
                    "package": pkg_name,
                    "action": "upgrade",
                    "target_version": latest_compatible,
                    "command": f"pip install {pkg_name}=={latest_compatible}"
                })

        # 保存报告
        self.conflicts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.conflicts_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"  ✅ 冲突报告已生成: {self.conflicts_file}")

    def resolve_conflicts(self, conflicts: Dict[str, Dependency]) -> bool:
        """解决依赖冲突"""
        print("\n🔧 解决依赖冲突...")

        success = True

        # 创建解决方案计划
        resolution_plan = self._create_resolution_plan(conflicts)

        # 执行解决方案
        for step in resolution_plan:
            print(f"\n  - {step['description']}")

            if step["type"] == "install":
                result = subprocess.run(
                    step["command"],
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    print(f"    ❌ 失败: {result.stderr}")
                    success = False
                else:
                    print("    ✅ 成功")

            elif step["type"] == "uninstall":
                # 先卸载冲突包
                result = subprocess.run(
                    step["command"],
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    print(f"    ❌ 失败: {result.stderr}")
                    success = False
                else:
                    print("    ✅ 成功")

        return success

    def _create_resolution_plan(self, conflicts: Dict[str, Dependency]) -> List[Dict]:
        """创建解决方案计划"""
        plan = []

        # 按优先级排序
        priority_order = ["pydantic", "numpy", "pandas", "requests", "rich", "urllib3", "typer"]

        for pkg_name in priority_order:
            if pkg_name in conflicts:
                dep = conflicts[pkg_name]

                if dep.required_versions:
                    # 升级到兼容版本
                    target_version = max(dep.required_versions, key=version.parse)
                    plan.append({
                        "type": "install",
                        "description": f"升级 {pkg_name} 到 {target_version}",
                        "command": f"pip install {pkg_name}=={target_version}"
                    })

                # 处理冲突包
                for conflict in dep.conflicts:
                    if "great-expectations" in conflict:
                        plan.append({
                            "type": "install",
                            "description": "安装兼容版本的 great-expectations",
                            "command": "pip install 'great-expectations>=1.5.11,<2.0.0'"
                        })
                    elif "feast" in conflict:
                        plan.append({
                            "type": "install",
                            "description": "升级 feast 到兼容版本",
                            "command": "pip install 'feast>=0.53.0,<1.0.0'"
                        })

        # 最后验证
        plan.append({
            "type": "verify",
            "description": "验证依赖冲突是否解决",
            "command": "pip check"
        })

        return plan

    def generate_lock_file(self) -> bool:
        """生成锁定文件"""
        print("\n🔒 生成依赖锁定文件...")

        # 使用pip-tools生成锁定文件
        try:
            # 检查pip-tools是否安装
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pip-tools"],
                check=True,
                capture_output=True
            )

            # 生成锁定文件
            result = subprocess.run(
                [sys.executable, "-m", "pip", "compile", str(self.requirements_file)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                with open(self.lock_file, "w") as f:
                    f.write(result.stdout)
                print(f"✅ 锁定文件已生成: {self.lock_file}")
                return True
            else:
                print(f"❌ 生成锁定文件失败: {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ 安装pip-tools失败: {e}")
            return False

    def create_requirements_matrix(self):
        """创建依赖矩阵表"""
        print("\n📊 创建依赖矩阵表...")

        matrix = {
            "package": [],
            "current_version": [],
            "target_version": [],
            "conflicts_with": [],
            "resolution": [],
            "priority": []
        }

        for pkg_name, pkg_info in self.dependency_db.items():
            matrix["package"].append(pkg_name)
            matrix["target_version"].append(pkg_info["compatible_versions"][0])
            matrix["conflicts_with"].append(", ".join(pkg_info["conflicts"]))

            # 添加默认值以保持列数一致
            matrix["current_version"].append("待检查")
            matrix["resolution"].append("升级")

            # 设置优先级
            if pkg_name in ["pydantic", "numpy", "pandas"]:
                matrix["priority"].append("高")
            elif pkg_name in ["requests", "rich"]:
                matrix["priority"].append("中")
            else:
                matrix["priority"].append("低")

        # 保存为CSV
        import csv
        matrix_file = Path("docs/_reports/DEPENDENCY_MATRIX.csv")
        matrix_file.parent.mkdir(parents=True, exist_ok=True)

        with open(matrix_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=matrix.keys())
            writer.writeheader()
            for i in range(len(matrix["package"])):
                row = {k: v[i] for k, v in matrix.items()}
                writer.writerow(row)

        print(f"✅ 依赖矩阵表已生成: {matrix_file}")

    def run_full_resolution(self) -> bool:
        """运行完整的冲突解决流程"""
        print("🚀 开始依赖冲突解决流程...")
        print("=" * 60)

        # 1. 检测冲突
        conflicts = self.detect_conflicts()

        if not conflicts:
            print("\n✅ 未发现依赖冲突!")
            return True

        print(f"\n⚠️  发现 {len(conflicts)} 个依赖冲突:")
        for pkg_name, dep in conflicts.items():
            print(f"  - {pkg_name}: {dep.current_version}")

        # 2. 解决冲突
        if self.resolve_conflicts(conflicts):
            print("\n✅ 依赖冲突解决成功!")
        else:
            print("\n❌ 依赖冲突解决失败!")
            return False

        # 3. 生成锁定文件
        if self.generate_lock_file():
            print("\n✅ 依赖锁定文件生成成功!")

        # 4. 创建依赖矩阵
        self.create_requirements_matrix()

        # 5. 验证
        print("\n🔍 最终验证...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ 验证通过!")
            print("\n" + "=" * 60)
            print("🎉 依赖冲突已全部解决!")
            return True
        else:
            print(f"❌ 验证失败: {result.stderr}")
            return False

    def create_test_requirements(self):
        """创建测试专用requirements"""
        print("\n🧪 创建测试专用requirements...")

        test_requirements = """# 测试依赖 - 精确版本控制
# 生产在 requirements.txt 中定义

# 测试框架
pytest==8.3.4
pytest-asyncio==0.25.0
pytest-cov==6.0.0
pytest-mock==3.14.0
pytest-xdist==3.6.1  # 并行测试

# 测试工具
factory-boy==3.3.1
faker==30.8.1
freezegun==1.5.1
responses==0.25.3
httpx==0.28.1

# 性能测试
locust==2.29.0
pytest-benchmark==5.1.0

# 测试数据生成
mimesis==13.1.0
 hypothesis==6.114.1
"""

        test_file = Path("requirements-test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_requirements)

        print(f"✅ 测试requirements已生成: {test_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="依赖冲突解决工具")
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="仅检测冲突，不解决"
    )
    parser.add_argument(
        "--create-test-reqs",
        action="store_true",
        help="创建测试requirements"
    )

    args = parser.parse_args()

    resolver = DependencyResolver()

    if args.create_test_reqs:
        resolver.create_test_requirements()
    elif args.detect_only:
        conflicts = resolver.detect_conflicts()
        print(f"\n发现 {len(conflicts)} 个冲突")
    else:
        success = resolver.run_full_resolution()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()