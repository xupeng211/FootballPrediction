#!/usr/bin/env python3
"""
覆盖率缺口分析工具
识别未覆盖的代码并提供改进建议
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
import subprocess
import sys


class CoverageGapAnalyzer:
    """覆盖率缺口分析器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.uncovered_lines = {}  # 文件 -> 未覆盖行号集合
        self.test_coverage = {}  # 测试文件 -> 覆盖的源文件

    def parse_coverage_xml(self, xml_file: str = "coverage.xml"):
        """解析coverage.xml文件"""
        if not os.path.exists(xml_file):
            print(f"❌ 找不到覆盖率文件: {xml_file}")
            return False

        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(xml_file)
            root = tree.getroot()

            # 提取未覆盖的行
            for class_elem in root.findall(".//class"):
                filename = class_elem.attrib.get("filename", "")
                if not filename.startswith("src/"):
                    continue

                # 获取未覆盖的行
                lines_elem = class_elem.find("lines")
                if lines_elem is not None:
                    uncovered = set()
                    for line in lines_elem.findall("line"):
                        if line.attrib.get("hits") == "0":
                            uncovered.add(int(line.attrib.get("number", 0)))

                    if uncovered:
                        self.uncovered_lines[filename] = uncovered

            print(f"✅ 成功解析覆盖率文件: {xml_file}")
            return True

        except Exception as e:
            print(f"❌ 解析覆盖率文件失败: {e}")
            return False

    def find_functions_in_file(self, file_path: Path) -> List[Dict]:
        """找到文件中的所有函数"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(
                        {
                            "name": node.name,
                            "line_start": node.lineno,
                            "line_end": node.end_lineno or node.lineno,
                            "type": "function",
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            functions.append(
                                {
                                    "name": f"{node.name}.{child.name}",
                                    "line_start": child.lineno,
                                    "line_end": child.end_lineno or child.lineno,
                                    "type": "method",
                                }
                            )

            return functions

        except Exception as e:
            print(f"⚠️ 无法解析文件 {file_path}: {e}")
            return []

    def identify_test_gaps(self) -> Dict[str, List[Dict]]:
        """识别测试缺口"""
        gaps = {}

        for file_path, uncovered_lines in self.uncovered_lines.items():
            path = Path(file_path)
            if not path.exists():
                continue

            functions = self.find_functions_in_file(path)
            uncovered_funcs = []

            for func in functions:
                # 检查函数是否完全没有被覆盖
                func_lines = set(range(func["line_start"], func["line_end"] + 1))
                if func_lines & uncovered_lines:
                    # 计算覆盖率百分比
                    uncovered_func_lines = len(func_lines & uncovered_lines)
                    coverage = (len(func_lines) - uncovered_func_lines) / len(
                        func_lines
                    )

                    uncovered_funcs.append(
                        {
                            "name": func["name"],
                            "type": func["type"],
                            "line_start": func["line_start"],
                            "line_end": func["line_end"],
                            "total_lines": len(func_lines),
                            "uncovered_lines": uncovered_func_lines,
                            "coverage": coverage,
                            "priority": self._calculate_priority(func, coverage),
                        }
                    )

            if uncovered_funcs:
                gaps[file_path] = sorted(
                    uncovered_funcs, key=lambda x: x["priority"], reverse=True
                )

        return gaps

    def _calculate_priority(self, func: Dict, coverage: float) -> float:
        """计算函数的测试优先级"""
        # 优先级 = (1 - 覆盖率) * 重要系数
        # 重要系数根据函数类型调整
        importance_factor = 1.0

        # 公共方法优先级更高
        if func["name"].startswith("_"):
            importance_factor *= 0.5
        elif func["name"].startswith("__"):
            importance_factor *= 0.3

        # 测试方法优先级更高
        if "test" in func["name"].lower():
            importance_factor *= 1.5

        # 长函数需要更多关注
        if func["total_lines"] > 20:
            importance_factor *= 1.2

        return (1 - coverage) * importance_factor

    def generate_test_suggestions(self, gaps: Dict[str, List[Dict]]) -> List[Dict]:
        """生成测试建议"""
        suggestions = []

        for file_path, functions in gaps.items():
            # 按优先级排序
            functions.sort(key=lambda x: x["priority"], reverse=True)

            # 取前5个最高优先级的函数
            for func in functions[:5]:
                module_name = self._get_module_name(file_path)

                # 根据函数类型生成测试建议
                if func["type"] == "function":
                    test_name = f"test_{func['name']}"
                    test_type = "function"
                else:  # method
                    class_name = func["name"].split(".")[0]
                    method_name = func["name"].split(".")[1]
                    test_name = f"test_{class_name}_{method_name}"
                    test_type = "method"

                suggestions.append(
                    {
                        "file_path": file_path,
                        "module": module_name,
                        "function": func["name"],
                        "test_name": test_name,
                        "test_type": test_type,
                        "line_start": func["line_start"],
                        "line_end": func["line_end"],
                        "priority": func["priority"],
                        "coverage": func["coverage"],
                        "estimated_effort": self._estimate_effort(func),
                    }
                )

        # 按优先级排序所有建议
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        return suggestions[:20]  # 返回前20个最重要的建议

    def _get_module_name(self, file_path: str) -> str:
        """获取模块名"""
        # 移除src/前缀和.py后缀
        module = file_path.replace("src/", "").replace(".py", "")
        # 将路径转换为模块点分格式
        return module.replace("/", ".")

    def _estimate_effort(self, func: Dict) -> str:
        """估算测试工作量"""
        lines = func["total_lines"]

        if lines < 5:
            return "简单 (5-10分钟)"
        elif lines < 10:
            return "中等 (10-20分钟)"
        elif lines < 20:
            return "复杂 (20-30分钟)"
        else:
            return "困难 (30-60分钟)"

    def generate_test_template(self, suggestion: Dict) -> str:
        """生成测试模板"""
        if suggestion["test_type"] == "function":
            return f"""
def {suggestion['test_name']}(self):
    \"\"\"测试 {suggestion['function']}\"\"\"
    # TODO: 实现测试逻辑
    # 函数位置: {suggestion['file_path']}:{suggestion['line_start']}-{suggestion['line_end']}

    # 准备测试数据
    test_data = {{
        # 添加测试数据
    }}

    # 执行测试
    result = {suggestion['module']}.{suggestion['function']}(test_data)

    # 断言结果
    assert result is not None
"""
        else:  # method
            class_name = suggestion["function"].split(".")[0]
            return f"""
def {suggestion['test_name']}(self):
    \"\"\"测试 {class_name}.{suggestion['function'].split('.')[1]}\"\"\"
    # TODO: 实现测试逻辑
    # 方法位置: {suggestion['file_path']}:{suggestion['line_start']}-{suggestion['line_end']}

    # 创建类实例
    instance = {suggestion['module']}.{class_name}()

    # 准备测试数据
    test_data = {{
        # 添加测试数据
    }}

    # 执行测试
    result = instance.{suggestion['function'].split('.')[1]}(test_data)

    # 断言结果
    assert result is not None
"""

    def create_test_generation_script(self, suggestions: List[Dict]) -> str:
        """创建测试生成脚本"""
        script = """#!/usr/bin/env python3
\"\"\"
自动生成测试脚本
基于覆盖率分析结果生成缺失的测试
\"\"\"

import os
from pathlib import Path

# 测试模板
TEST_FILE_TEMPLATE = '''
import pytest
from unittest.mock import Mock

# TODO: 添加必要的导入

'''

def generate_test_files():
    \"\"\"生成测试文件\"\"\"
    # 这里应该包含生成测试的逻辑
    pass

if __name__ == "__main__":
    generate_test_files()
    print("✅ 测试文件生成完成")
"""
        return script

    def print_summary(self, gaps: Dict, suggestions: List[Dict]):
        """打印分析总结"""
        print("\n" + "=" * 60)
        print("📊 覆盖率缺口分析总结")
        print("=" * 60)

        print("\n📈 统计信息:")
        print(f"  - 需要测试的文件数: {len(gaps)}")
        print(f"  - 未覆盖的函数数: {sum(len(funcs) for funcs in gaps.values())}")
        print(f"  - 生成测试建议数: {len(suggestions)}")

        print("\n🎯 前10个最高优先级测试:")
        print("-" * 60)
        for i, sugg in enumerate(suggestions[:10], 1):
            print(f"{i:2d}. {sugg['test_name']}")
            print(f"    文件: {sugg['file_path']}")
            print(
                f"    优先级: {sugg['priority']:.2f} | 当前覆盖率: {sugg['coverage']*100:.1f}%"
            )
            print(f"    预估工作量: {sugg['estimated_effort']}")
            print()

        print("\n💡 改进建议:")
        print("-" * 60)
        print("1. 优先实现标记为'简单'的测试（5-10分钟）")
        print("2. 每天至少完成2-3个测试，持续改进")
        print("3. 使用Mock避免复杂的依赖")
        print("4. 专注于业务逻辑测试而非基础设施")
        print("5. 设置自动化的覆盖率检查（建议30%门槛）")

        # 估算总工作量
        effort_mapping = {"简单": 1, "中等": 2, "复杂": 3, "困难": 4}
        total_effort = sum(
            effort_mapping.get(s["estimated_effort"].split()[0], 1)
            for s in suggestions[:20]
        )
        print(f"\n⏱️ 预估总工作量: {total_effort * 10}-{total_effort * 20} 分钟")
        print(f"   按每天30分钟计算，需要 {total_effort/2:.1f} 个工作日")

    def save_report(
        self,
        gaps: Dict,
        suggestions: List[Dict],
        output_file: str = "coverage_gap_report.md",
    ):
        """保存报告到文件"""
        report_content = f"""# 覆盖率缺口分析报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 概述

本报告基于当前的测试覆盖率分析，识别了需要测试的关键函数和方法。

## 统计信息

- 需要测试的文件数: {len(gaps)}
- 未覆盖的函数/方法数: {sum(len(funcs) for funcs in gaps.values())}
- 生成测试建议数: {len(suggestions)}

## 测试优先级列表

### 高优先级 (建议优先实现)

"""

        for i, sugg in enumerate(suggestions[:10], 1):
            report_content += f"""
{i}. **{sugg['test_name']}**
   - 文件: `{sugg['file_path']}`
   - 位置: 第 {sugg['line_start']}-{sugg['line_end']} 行
   - 当前覆盖率: {sugg['coverage']*100:.1f}%
   - 预估工作量: {sugg['estimated_effort']}
   - 优先级分数: {sugg['priority']:.2f}

"""

        report_content += """
## 实施计划

### 第一阶段（1周）：简单测试
- 实现优先级前5的简单测试
- 预期覆盖率提升: 3-5%

### 第二阶段（2周）：中等难度测试
- 实现中等复杂度的测试
- 预期覆盖率提升: 5-8%

### 第三阶段（3周）：复杂测试
- 实现复杂的业务逻辑测试
- 预期覆盖率提升: 8-12%

## 工具和资源

- 使用 `pytest` 运行测试
- 使用 `unittest.mock` 处理依赖
- 参考 `test_coverage_summary.py` 查看覆盖率

---
*报告由 coverage_gap_analyzer.py 生成*
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"\n📄 报告已保存到: {output_file}")


def main():
    """主函数"""
    print("🔍 开始覆盖率缺口分析...")

    analyzer = CoverageGapAnalyzer()

    # 解析覆盖率文件
    if not analyzer.parse_coverage_xml():
        sys.exit(1)

    # 识别测试缺口
    print("\n📋 识别测试缺口...")
    gaps = analyzer.identify_test_gaps()

    if not gaps:
        print("✅ 所有代码都已覆盖！")
        return

    # 生成测试建议
    print("\n💡 生成测试建议...")
    suggestions = analyzer.generate_test_suggestions(gaps)

    # 打印总结
    analyzer.print_summary(gaps, suggestions)

    # 保存报告
    analyzer.save_report(gaps, suggestions)

    # 生成测试生成脚本
    print("\n📝 生成测试生成脚本...")
    script = analyzer.create_test_generation_script(suggestions)
    with open("generate_missing_tests.py", "w", encoding="utf-8") as f:
        f.write(script)

    print("\n✅ 分析完成！")
    print("\n下一步:")
    print("1. 查看 coverage_gap_report.md 获取详细建议")
    print("2. 从最高优先级的测试开始实现")
    print("3. 运行 'python generate_missing_tests.py' 自动生成测试模板")


if __name__ == "__main__":
    from datetime import datetime

    main()
