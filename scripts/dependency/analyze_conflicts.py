#!/usr/bin/env python3
"""
依赖冲突深度分析工具
找出冲突的根本原因并提供解决方案
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import networkx as nx


@dataclass
class Package:
    """包信息"""

    name: str
    version: str
    requirements: Dict[str, str]
    required_by: List[str]
    conflicts: List[str]


class DependencyAnalyzer:
    """依赖分析器"""

    def __init__(self):
        self.packages = {}
        self.conflicts = []
        self.dependency_graph = nx.DiGraph()

    def analyze_dependencies(self) -> Dict:
        """深度分析依赖关系"""
        print("🔍 深度分析依赖关系...")

        # 1. 获取所有已安装的包
        self._get_installed_packages()

        # 2. 分析冲突
        self._analyze_conflicts()

        # 3. 构建依赖图
        self._build_dependency_graph()

        # 4. 识别问题包
        problematic = self._identify_problematic_packages()

        # 5. 生成解决方案
        solutions = self._generate_solutions(problematic)

        return {
            "total_packages": len(self.packages),
            "conflicts": self.conflicts,
            "problematic_packages": problematic,
            "solutions": solutions,
            "dependency_graph": self._export_graph(),
        }

    def _get_installed_packages(self):
        """获取已安装的包"""
        print("  - 获取已安装包...")

        # 获取包列表
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            packages = json.loads(result.stdout)
            for pkg in packages:
                self.packages[pkg["name"].lower()] = {
                    "name": pkg["name"],
                    "version": pkg["version"],
                    "requirements": {},
                    "required_by": [],
                    "conflicts": [],
                }

    def _analyze_conflicts(self):
        """分析冲突"""
        print("  - 分析依赖冲突...")

        # 运行pip check
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"], capture_output=True, text=True
        )

        if result.returncode != 0:
            # 解析冲突
            lines = result.stderr.split("\n")
            for line in lines:
                if "has requirement" in line and "but you have" in line:
                    conflict = self._parse_conflict_line(line)
                    if conflict:
                        self.conflicts.append(conflict)

    def _parse_conflict_line(self, line: str) -> Optional[Dict]:
        """解析冲突行"""
        # 示例: "rich-toolkit 0.15.0 has requirement rich>=13.7.1, but you have rich 13.5.2"
        try:
            parts = line.split(" has requirement ")
            if len(parts) != 2:
                return None

            pkg_part = parts[0].split(" ")
            pkg_name = pkg_part[0]
            pkg_version = pkg_part[1]

            req_part = parts[1].split(", but you have ")
            if len(req_part) != 2:
                return None

            requirement = req_part[0]
            have_part = req_part[1].split(" ")
            conflict_pkg = have_part[0]
            conflict_version = have_part[1]

            return {
                "package": pkg_name,
                "version": pkg_version,
                "requires": requirement,
                "conflicts_with": conflict_pkg,
                "current_version": conflict_version,
                "severity": self._calculate_severity(pkg_name, conflict_pkg),
            }
        except Exception:
            return None

    def _calculate_severity(self, pkg1: str, pkg2: str) -> str:
        """计算冲突严重程度"""
        # 核心依赖
        core_packages = {
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "alembic",
            "pydantic",
            "pandas",
            "numpy",
            "redis",
        }

        # 开发工具
        dev_tools = {
            "semgrep",
            "rich-toolkit",
            "pipdeptree",
            "pyproject-api",
            "checkov",
            "fastmcp",
            "mypy",
            "black",
            "flake8",
        }

        pkg1_lower = pkg1.lower()
        pkg2_lower = pkg2.lower()

        if pkg1_lower in core_packages or pkg2_lower in core_packages:
            return "critical"
        elif pkg1_lower in dev_tools or pkg2_lower in dev_tools:
            return "low"
        else:
            return "medium"

    def _build_dependency_graph(self):
        """构建依赖图"""
        print("  - 构建依赖图...")

        for pkg_name, pkg_info in self.packages.items():
            # 添加节点
            self.dependency_graph.add_node(pkg_name, **pkg_info)

            # 添加依赖边
            for req_name, req_version in pkg_info.get("requirements", {}).items():
                self.dependency_graph.add_edge(pkg_name, req_name, requirement=req_version)

    def _identify_problematic_packages(self) -> List[Dict]:
        """识别问题包"""
        print("  - 识别问题包...")

        problematic = []

        for conflict in self.conflicts:
            pkg_name = conflict["conflicts_with"]

            # 检查是否在问题包列表中
            if not any(p["name"] == pkg_name for p in problematic):
                pkg_info = {
                    "name": pkg_name,
                    "current_version": conflict["current_version"],
                    "conflicts": [],
                    "required_by": [],
                    "category": self._categorize_package(pkg_name),
                    "removable": self._is_removable(pkg_name),
                }
                problematic.append(pkg_info)

            # 添加冲突信息
            for p in problematic:
                if p["name"] == pkg_name:
                    p["conflicts"].append(
                        {
                            "from": conflict["package"],
                            "requires": conflict["requires"],
                            "severity": conflict["severity"],
                        }
                    )
                    break

        return problematic

    def _categorize_package(self, pkg_name: str) -> str:
        """分类包"""
        pkg_name = pkg_name.lower()

        if pkg_name in {
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "alembic",
            "pydantic",
            "asyncpg",
            "psycopg2",
        }:
            return "core"
        elif pkg_name in {"pytest", "black", "flake8", "mypy", "semgrep", "pipdeptree"}:
            return "dev_tool"
        elif pkg_name in {"rich", "click", "typer", "colorama"}:
            return "cli_utility"
        elif pkg_name in {"numpy", "pandas", "scikit-learn", "mlflow"}:
            return "ml"
        else:
            return "other"

    def _is_removable(self, pkg_name: str) -> bool:
        """判断是否可以移除"""
        category = self._categorize_package(pkg_name)
        return category in {"dev_tool", "cli_utility"}

    def _generate_solutions(self, problematic: List[Dict]) -> List[Dict]:
        """生成解决方案"""
        print("  - 生成解决方案...")

        solutions = []

        # 方案1: 移除冲突的开发工具
        dev_tools = [p for p in problematic if p["category"] == "dev_tool" and p["removable"]]
        if dev_tools:
            solutions.append(
                {
                    "name": "remove_dev_tools",
                    "description": "移除冲突的开发工具（生产环境不需要）",
                    "packages": [p["name"] for p in dev_tools],
                    "impact": "low",
                    "commands": [f"pip uninstall {' '.join([p['name'] for p in dev_tools])} -y"],
                }
            )

        # 方案2: 版本锁定
        core_conflicts = [p for p in problematic if p["category"] in {"core", "ml"}]
        if core_conflicts:
            solutions.append(
                {
                    "name": "version_lock",
                    "description": "锁定核心包版本",
                    "packages": [p["name"] for p in core_conflicts],
                    "impact": "medium",
                    "commands": self._generate_version_commands(core_conflicts),
                }
            )

        # 方案3: 创建独立的开发环境
        solutions.append(
            {
                "name": "separate_envs",
                "description": "创建独立的开发和生产环境",
                "packages": [],
                "impact": "high",
                "commands": [
                    "python -m venv venv-dev",
                    "python -m venv venv-prod",
                    "# 分别激活并安装不同依赖",
                ],
            }
        )

        return solutions

    def _generate_version_commands(self, packages: List[Dict]) -> List[str]:
        """生成版本命令"""
        commands = []

        # 基于冲突生成兼容版本
        for pkg in packages:
            if pkg["name"] == "numpy":
                # numpy是最大冲突源
                commands.append("pip install 'numpy>=1.26.4,<2.0.0'  # 兼容pandas")
            elif pkg["name"] == "pydantic":
                commands.append("pip install 'pydantic>=2.10.0,<2.12.0'")
            elif pkg["name"] == "rich":
                commands.append("pip install 'rich>=13.5.0,<14.0.0'")
            elif pkg["name"] == "urllib3":
                commands.append("pip install 'urllib3>=1.26.0,<2.1.0'")

        return commands

    def _export_graph(self) -> Dict:
        """导出依赖图"""
        return {
            "nodes": len(self.dependency_graph.nodes()),
            "edges": len(self.dependency_graph.edges()),
            "cycles": list(nx.simple_cycles(self.dependency_graph))[:5],  # 前5个循环
        }


def main():
    """主函数"""
    analyzer = DependencyAnalyzer()
    analysis = analyzer.analyze_dependencies()

    print("\n" + "=" * 60)
    print("📊 依赖分析结果")
    print(f"总包数: {analysis['total_packages']}")
    print(f"冲突数: {len(analysis['conflicts'])}")
    print(f"问题包: {len(analysis['problematic_packages'])}")

    print("\n🔥 严重冲突:")
    critical_conflicts = [c for c in analysis["conflicts"] if c["severity"] == "critical"]
    for conflict in critical_conflicts:
        print(
            f"  - {conflict['package']} 需要 {conflict['requires']} 但 {conflict['conflicts_with']} 是 {conflict['current_version']}"
        )

    print("\n💡 解决方案:")
    for i, sol in enumerate(analysis["solutions"], 1):
        print(f"\n方案{i}: {sol['name']}")
        print(f"  描述: {sol['description']}")
        print(f"  影响: {sol['impact']}")
        if sol["commands"]:
            print("  命令:")
            for cmd in sol["commands"]:
                print(f"    {cmd}")

    # 保存分析结果
    output_file = Path("docs/_reports/DEPENDENCY_ANALYSIS.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 分析结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
