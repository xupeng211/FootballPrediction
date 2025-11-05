#!/usr/bin/env python3
"""
工具集成优化器
优化各个脚本工具之间的依赖关系和集成
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
import ast


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    path: Path
    dependencies: List[str]
    dependents: List[str]
    functionality: str
    status: str  # working, broken, needs_improvement


class ToolIntegrationOptimizer:
    """工具集成优化器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.src_dir = self.project_root / "src"
        self.tools: Dict[str, ToolInfo] = {}

    def discover_tools(self) -> Dict[str, ToolInfo]:
        """发现所有工具脚本"""
        print("🔍 发现工具脚本...")

        for script_file in self.scripts_dir.glob("*.py"):
            if script_file.name.startswith("__"):
                continue

            tool_info = self._analyze_tool(script_file)
            if tool_info:
                self.tools[tool_info.name] = tool_info
                print(f"   ✅ 发现工具: {tool_info.name}")

        return self.tools

    def _analyze_tool(self, script_path: Path) -> ToolInfo:
        """分析工具脚本"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content)

            # 提取导入和依赖
            imports = self._extract_imports(tree)
            dependencies = self._identify_dependencies(imports)

            # 提取功能描述
            functionality = self._extract_functionality(content)

            # 检查工具状态
            status = self._check_tool_status(script_path)

            return ToolInfo(
                name=script_path.stem,
                path=script_path,
                dependencies=dependencies,
                dependents=[],  # 稍后计算
                functionality=functionality,
                status=status
            )

        except Exception as e:
            print(f"❌ 分析工具失败 {script_path}: {e}")
            return None

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入语句"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def _identify_dependencies(self, imports: List[str]) -> List[str]:
        """识别工具依赖"""
        dependencies = []

        # 项目内部模块
        for imp in imports:
            if imp.startswith('src.'):
                dependencies.append(imp)
            elif imp in ['requests', 'pandas', 'numpy', 'aiohttp', 'psutil']:
                dependencies.append(imp)

        # 工具脚本依赖
        script_dependencies = ['coverage_improvement_executor', 'phase35_ai_coverage_master',
                             'integrated_coverage_improver', 'smart_quality_fixer',
                             'quality_guardian', 'create_api_tests', 'create_service_tests']

        for dep in script_dependencies:
            if dep in imports:
                dependencies.append(dep)

        return list(set(dependencies))

    def _extract_functionality(self, content: str) -> str:
        """提取功能描述"""
        lines = content.split('\n')

        # 查找文档字符串
        for line in lines:
            if line.strip().startswith('"""'):
                # 提取文档字符串的第一行
                doc_start = line.find('"""') + 3
                doc_line = line[doc_start:].strip()
                if doc_line:
                    return doc_line
                break

        # 查找注释
        for line in lines[:10]:  # 只检查前10行
            if line.strip().startswith('#') and '工具' in line:
                return line.strip().lstrip('#').strip()

        return "未知功能"

    def _check_tool_status(self, script_path: Path) -> str:
        """检查工具状态"""
        try:
            # 尝试运行工具 --help 或 --version
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root
            )

            if result.returncode == 0:
                return "working"
            else:
                return "needs_improvement"

        except subprocess.TimeoutExpired:
            return "needs_improvement"
        except Exception:
            return "broken"

    def calculate_dependents(self):
        """计算工具的依赖关系"""
        print("🔗 计算依赖关系...")

        for tool_name, tool_info in self.tools.items():
            tool_info.dependents = []

        for tool_name, tool_info in self.tools.items():
            for dep in tool_info.dependencies:
                # 检查是否有其他工具依赖此工具
                for other_name, other_info in self.tools.items():
                    if other_name != tool_name and tool_name in other_info.dependencies:
                        tool_info.dependents.append(other_name)

    def analyze_integration(self) -> Dict[str, Any]:
        """分析工具集成情况"""
        print("📊 分析工具集成...")

        # 统计工具状态
        status_counts = {}
        for tool in self.tools.values():
            status_counts[tool.status] = status_counts.get(tool.status, 0) + 1

        # 找出关键工具（被其他工具依赖）
        critical_tools = [
            name for name, tool in self.tools.items()
            if len(tool.dependents) > 0
        ]

        # 找出孤立工具（无依赖且不被依赖）
        isolated_tools = [
            name for name, tool in self.tools.items()
            if len(tool.dependencies) == 0 and len(tool.dependents) == 0
        ]

        # 分析依赖链
        dependency_chains = self._find_dependency_chains()

        return {
            'total_tools': len(self.tools),
            'status_distribution': status_counts,
            'critical_tools': critical_tools,
            'isolated_tools': isolated_tools,
            'dependency_chains': dependency_chains,
            'tools': {name: {
                'path': str(tool.path),
                'dependencies': tool.dependencies,
                'dependents': tool.dependents,
                'functionality': tool.functionality,
                'status': tool.status
            } for name, tool in self.tools.items()}
        }

    def _find_dependency_chains(self) -> List[List[str]]:
        """找出依赖链"""
        chains = []

        for tool_name in self.tools:
            visited = set()
            path = []

            def dfs(current: str):
                if current in visited:
                    return

                visited.add(current)
                path.append(current)

                tool = self.tools.get(current)
                if tool:
                    for dep in tool.dependencies:
                        if dep in self.tools:
                            dfs(dep)

                if len(path) > 1:
                    chains.append(path.copy())

                path.pop()

            dfs(tool_name)

        # 去重并过滤长链
        unique_chains = []
        for chain in chains:
            if len(chain) > 1 and chain not in unique_chains:
                unique_chains.append(chain)

        return unique_chains[:10]  # 返回前10条链

    def generate_optimization_suggestions(self,
    analysis: Dict[str,
    Any]) -> List[Dict[str,
    Any]]:
        """生成优化建议"""
        suggestions = []

        # 状态优化建议
        broken_tools = [
            name for name, tool in self.tools.items()
            if tool.status == "broken"
        ]

        if broken_tools:
            suggestions.append({
                'priority': 'high',
                'category': '修复损坏工具',
                'description': f'发现{len(broken_tools)}个损坏的工具需要修复',
                'items': broken_tools[:5]
            })

        # 依赖优化建议
        complex_tools = [
            name for name, tool in self.tools.items()
            if len(tool.dependencies) > 5
        ]

        if complex_tools:
            suggestions.append({
                'priority': 'medium',
                'category': '简化复杂依赖',
                'description': f'发现{len(complex_tools)}个工具依赖过多模块',
                'items': complex_tools[:3]
            })

        # 集成优化建议
        if analysis['isolated_tools']:
            suggestions.append({
                'priority': 'low',
                'category': '集成孤立工具',
                'description': f'发现{len(analysis["isolated_tools"])}个孤立工具可以考虑集成',
                'items': analysis['isolated_tools'][:5]
            })

        # 工作流建议
        critical_tools = analysis['critical_tools']
        if critical_tools:
            suggestions.append({
                'priority': 'medium',
                'category': '优化关键工具',
                'description': f'发现{len(critical_tools)}个关键工具，建议优先优化',
                'items': critical_tools[:5]
            })

        return suggestions

    def create_integration_workflow(self) -> Dict[str, List[str]]:
        """创建集成工作流"""
        workflow = {
            'quality_improvement': [
                'smart_quality_fixer.py',  # 质量修复
                'quality_guardian.py',      # 质量守护
                'precise_error_fixer.py'    # 精确修复
            ],
            'coverage_improvement': [
                'coverage_improvement_executor.py',  # 覆盖率执行
                'phase35_ai_coverage_master.py',     # AI覆盖率
                'integrated_coverage_improver.py',   # 集成改进
                'simple_coverage_analyzer.py',       # 覆盖率分析
                'coverage_dashboard.py'              # 覆盖率仪表板
            ],
            'test_generation': [
                'create_api_tests.py',     # API测试生成
                'create_service_tests.py'  # 服务测试生成
            ],
            'monitoring': [
                'tool_integration_optimizer.py',  # 工具集成优化
                'continuous_improvement_engine.py' # 持续改进
            ]
        }

        return workflow

    def generate_report(self) -> str:
        """生成集成分析报告"""
        self.discover_tools()
        self.calculate_dependents()
        analysis = self.analyze_integration()
        suggestions = self.generate_optimization_suggestions(analysis)
        workflow = self.create_integration_workflow()

        report_lines = [
            "# 工具集成优化报告",
            "",
            "## 概览",
            f"- 总工具数: {analysis['total_tools']}",
            f"- 工作状态: {analysis['status_distribution']}",
            "",
            "## 工具状态分布"
        ]

        for status, count in analysis['status_distribution'].items():
            emoji = {"working": "✅", "broken": "❌", "needs_improvement": "⚠️"}
            report_lines.append(f"- {emoji.get(status, '•')} {status}: {count}")

        report_lines.extend([
            "",
            "## 关键工具",
            ""
        ])

        for tool_name in analysis['critical_tools']:
            tool = self.tools[tool_name]
            report_lines.append(f"- **{tool_name}** ({tool.functionality})")
            report_lines.append(f"  - 被依赖: {', '.join(tool.dependents)}")

        report_lines.extend([
            "",
            "## 优化建议",
            ""
        ])

        for i, suggestion in enumerate(suggestions, 1):
            emoji = {"high": "🔥", "medium": "⚡", "low": "💡"}
            report_lines.append(f"{i}. {emoji.get(suggestion['priority'],
    '•')} **{suggestion['category']}** ({suggestion['priority']})")
            report_lines.append(f"   - {suggestion['description']}")
            if suggestion['items']:
                report_lines.append(f"   - 涉及工具: {', '.join(suggestion['items'])}")

        report_lines.extend([
            "",
            "## 推荐工作流",
            ""
        ])

        for workflow_name, tools in workflow.items():
            report_lines.append(f"### {workflow_name.replace('_', ' ').title()}")
            for tool in tools:
                if tool in self.tools:
                    status_emoji = {"working": "✅", "broken": "❌", "needs_improvement": "⚠️"}
                    status = self.tools[tool].status
                    report_lines.append(f"- {status_emoji.get(status, '•')} {tool}")

        return "\n".join(report_lines)


def main():
    """主函数"""
    print("🔧 工具集成优化器")
    print("=" * 40)

    optimizer = ToolIntegrationOptimizer()
    report = optimizer.generate_report()

    # 输出报告
    print(report)

    # 保存报告
    report_file = optimizer.project_root / "tool_integration_report.md"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_file}")
    except Exception as e:
        print(f"❌ 保存报告失败: {e}")


if __name__ == "__main__":
    main()