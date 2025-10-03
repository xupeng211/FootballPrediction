#!/usr/bin/env python3
"""
覆盖率优化工具
自动识别低覆盖率模块并生成优化建议
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re


class CoverageOptimizer:
    """覆盖率优化器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.src_dir = self.project_root / "src"
        self.tests_dir = self.project_root / "tests"

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """运行覆盖率分析"""
        print("🔍 运行覆盖率分析...")

        # 运行pytest coverage
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--quiet"
        ]

        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

        # 读取覆盖率报告
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)
            return self._analyze_coverage_data(coverage_data)

        return {"error": "无法生成覆盖率报告"}

    def _analyze_coverage_data(self, coverage_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析覆盖率数据"""
        analysis = {
            "overall": coverage_data["totals"],
            "files": {},
            "low_coverage_modules": [],
            "uncovered_lines": {},
            "optimization_suggestions": []
        }

        # 分析每个文件
        for file_path, file_data in coverage_data["files"].items():
            if "src/" in file_path:
                module_name = file_path.replace("src/", "").replace(".py", "")
                coverage_pct = file_data["summary"]["percent_covered"]
                missing_lines = file_data["summary"]["missing_lines"]

                analysis["files"][module_name] = {
                    "path": file_path,
                    "coverage": coverage_pct,
                    "missing_lines": missing_lines,
                    "total_lines": file_data["summary"]["num_statements"],
                    "priority": self._calculate_priority(coverage_pct, missing_lines)
                }

                # 识别低覆盖率模块
                if coverage_pct < 25:
                    analysis["low_coverage_modules"].append(module_name)

                # 记录未覆盖的行
                if missing_lines > 0:
                    analysis["uncovered_lines"][module_name] = self._get_missing_lines_details(file_path, file_data["missing_lines"])

        # 生成优化建议
        analysis["optimization_suggestions"] = self._generate_optimization_suggestions(analysis)

        return analysis

    def _calculate_priority(self, coverage: float, missing_lines: int) -> str:
        """计算优化优先级"""
        if coverage < 10:
            return "critical"
        elif coverage < 20:
            return "high"
        elif coverage < 25:
            return "medium"
        else:
            return "low"

    def _get_missing_lines_details(self, file_path: str, missing_lines: List[int]) -> List[Dict[str, Any]]:
        """获取未覆盖行的详细信息"""
        details = []
        full_path = self.project_root / file_path

        if not full_path.exists():
            return details

        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num in missing_lines[:10]:  # 只显示前10行
            if line_num <= len(lines):
                line_content = lines[line_num - 1].strip()
                if line_content and not line_content.startswith('#'):
                    details.append({
                        "line": line_num,
                        "content": line_content[:100],  # 截断长行
                        "type": self._classify_line(line_content)
                    })

        return details

    def _classify_line(self, line: str) -> str:
        """分类代码行类型"""
        line = line.strip()

        if "def " in line or "async def " in line:
            return "function"
        elif "class " in line:
            return "class"
        elif "if " in line or "elif " in line:
            return "condition"
        elif "return " in line:
            return "return"
        elif "raise " in line or "except" in line:
            return "exception"
        elif any(line.startswith(op) for op in ["for ", "while "]):
            return "loop"
        else:
            return "statement"

    def _generate_optimization_suggestions(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []

        # 1. 低覆盖率模块建议
        for module in sorted(analysis["low_coverage_modules"]):
            file_info = analysis["files"][module]
            suggestions.append({
                "type": "low_coverage",
                "module": module,
                "priority": file_info["priority"],
                "message": f"模块 {module} 覆盖率仅 {file_info['coverage']:.1f}%",
                "action": "需要增加单元测试"
            })

        # 2. 未覆盖的函数建议
        for module, missing_lines in analysis["uncovered_lines"].items():
            uncovered_functions = []
            uncovered_conditions = []

            for line_info in missing_lines:
                if line_info["type"] == "function":
                    uncovered_functions.append(line_info["line"])
                elif line_info["type"] == "condition":
                    uncovered_conditions.append(line_info["line"])

            if uncovered_functions:
                suggestions.append({
                    "type": "uncovered_functions",
                    "module": module,
                    "lines": uncovered_functions[:5],
                    "message": f"模块 {module} 有 {len(uncovered_functions)} 个未测试的函数",
                    "action": "为这些函数添加单元测试"
                })

            if uncovered_conditions:
                suggestions.append({
                    "type": "uncovered_conditions",
                    "module": module,
                    "lines": uncovered_conditions[:5],
                    "message": f"模块 {module} 有 {len(uncovered_conditions)} 个未测试的条件分支",
                    "action": "添加测试覆盖这些分支"
                })

        # 3. 通用建议
        suggestions.extend([
            {
                "type": "general",
                "message": "考虑使用测试驱动开发(TDD)来提高覆盖率",
                "action": "先写测试，再实现功能"
            },
            {
                "type": "general",
                "message": "使用参数化测试来覆盖多种输入情况",
                "action": "利用pytest.mark.parametrize"
            },
            {
                "type": "general",
                "message": "定期运行覆盖率检查以监控改进",
                "action": "设置CI自动覆盖率报告"
            }
        ])

        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))

        return suggestions

    def generate_test_templates(self, module: str) -> str:
        """为指定模块生成测试模板"""
        module_path = self.src_dir / f"{module.replace('.', '/')}.py"

        if not module_path.exists():
            return f"模块 {module} 不存在"

        # 读取模块内容
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取函数和类
        functions = re.findall(r'^(def|async def)\s+(\w+)', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)

        # 生成测试模板
        template = f'''"""
自动生成的测试模板 - {module}
请根据实际情况完善测试用例
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# 导入被测试的模块
from {module} import '''

        # 添加导入
        if classes:
            template += ', '.join(classes)
        if functions:
            if classes:
                template += ', '
            template += ', '.join([f[1] for f in functions])

        template += f'''

class Test{module.title().replace('.', '')}:
    """{module} 模块测试"""
'''

        # 为每个类生成测试
        for class_name in classes:
            template += f'''
    @pytest.mark.asyncio
    async def test_{class_name.lower()}_init(self):
        """测试 {class_name} 初始化"""
        # TODO: 实现测试
        pass

    @pytest.mark.asyncio
    async def test_{class_name.lower()}_functionality(self):
        """测试 {class_name} 主要功能"""
        # TODO: 实现测试
        pass
'''

        # 为每个函数生成测试
        for func_type, func_name in functions:
            if func_type == "async def":
                decorator = "@pytest.mark.asyncio\n    "
            else:
                decorator = "    "

            template += f'''
    {decorator}def test_{func_name}(self):
        """测试 {func_name} 函数"""
        # TODO: 实现测试
        pass
'''

        template += '''

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

        return template

    def create_optimization_plan(self) -> Dict[str, Any]:
        """创建优化计划"""
        print("📋 创建覆盖率优化计划...")

        # 运行分析
        analysis = self.run_coverage_analysis()

        if "error" in analysis:
            return analysis

        # 计算目标
        current_coverage = analysis["overall"]["percent_covered"]
        target_coverage = 30.0
        gap = target_coverage - current_coverage

        plan = {
            "current_coverage": current_coverage,
            "target_coverage": target_coverage,
            "gap": gap,
            "phases": []
        }

        # 分阶段计划
        if gap > 0:
            # 阶段1：处理critical和high优先级模块
            critical_modules = [m for m in analysis["low_coverage_modules"]
                              if analysis["files"][m]["priority"] in ["critical", "high"]]

            if critical_modules:
                plan["phases"].append({
                    "name": "阶段1：关键模块覆盖",
                    "modules": critical_modules,
                    "target_increase": min(gap, 5),
                    "estimated_effort": f"{len(critical_modules) * 2}小时",
                    "actions": [
                        "为每个模块创建基础测试",
                        "覆盖主要函数和类",
                        "实现基本的正常流程测试"
                    ]
                })

            # 阶段2：处理medium优先级模块
            medium_modules = [m for m in analysis["low_coverage_modules"]
                            if analysis["files"][m]["priority"] == "medium"]

            if medium_modules and gap > 5:
                plan["phases"].append({
                    "name": "阶段2：中等优先级模块",
                    "modules": medium_modules,
                    "target_increase": min(gap - 5, 5),
                    "estimated_effort": f"{len(medium_modules) * 1.5}小时",
                    "actions": [
                        "添加边界情况测试",
                        "覆盖异常处理路径",
                        "实现参数化测试"
                    ]
                })

            # 阶段3：条件分支和边缘情况
            plan["phases"].append({
                "name": "阶段3：分支和边缘情况",
                "target_increase": max(0, gap - 10),
                "estimated_effort": "4-6小时",
                "actions": [
                    "覆盖所有条件分支",
                    "测试异常情况",
                    "添加性能和压力测试"
                ]
            })

        # 添加具体建议
        plan["recommendations"] = analysis["optimization_suggestions"][:10]

        return plan

    def print_optimization_plan(self, plan: Dict[str, Any]):
        """打印优化计划"""
        print("\n" + "="*60)
        print("📈 覆盖率优化计划")
        print("="*60)

        print(f"\n📊 当前状态:")
        print(f"  当前覆盖率: {plan['current_coverage']:.1f}%")
        print(f"  目标覆盖率: {plan['target_coverage']:.1f}%")
        print(f"  需要提升: {plan['gap']:.1f}%")

        if plan["phases"]:
            print(f"\n📋 执行阶段:")
            for i, phase in enumerate(plan["phases"], 1):
                print(f"\n  {i}. {phase['name']}")
                print(f"     模块数量: {len(phase['modules'])}")
                print(f"     预期提升: +{phase['target_increase']:.1f}%")
                print(f"     预估工时: {phase['estimated_effort']}")
                print(f"     主要任务:")
                for action in phase['actions']:
                    print(f"       - {action}")

        print(f"\n💡 优先建议:")
        for rec in plan["recommendations"][:5]:
            print(f"  • {rec['message']}")

        print("\n" + "="*60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="覆盖率优化工具")
    parser.add_argument("--module", "-m", help="为指定模块生成测试模板")
    parser.add_argument("--plan", "-p", action="store_true", help="生成优化计划")
    parser.add_argument("--template", "-t", help="生成测试模板并保存到文件")

    args = parser.parse_args()

    optimizer = CoverageOptimizer()

    if args.module:
        # 生成单个模块的测试模板
        template = optimizer.generate_test_templates(args.module)
        if args.template:
            with open(args.template, 'w', encoding='utf-8') as f:
                f.write(template)
            print(f"✅ 测试模板已生成: {args.template}")
        else:
            print(template)

    elif args.plan:
        # 生成优化计划
        plan = optimizer.create_optimization_plan()
        optimizer.print_optimization_plan(plan)

        # 保存计划
        plan_file = Path("coverage_optimization_plan.json")
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        print(f"\n📁 详细计划已保存: {plan_file}")

    else:
        # 默认运行分析
        analysis = optimizer.run_coverage_analysis()

        if "error" in analysis:
            print(f"❌ {analysis['error']}")
            return 1

        print("\n📊 覆盖率分析结果:")
        print(f"总体覆盖率: {analysis['overall']['percent_covered']:.1f}%")
        print(f"低覆盖率模块: {len(analysis['low_coverage_modules'])}")

        if analysis["low_coverage_modules"]:
            print("\n需要优化的模块:")
            for module in sorted(analysis["low_coverage_modules"]):
                info = analysis["files"][module]
                print(f"  - {module}: {info['coverage']:.1f}% (优先级: {info['priority']})")


if __name__ == "__main__":
    sys.exit(main())