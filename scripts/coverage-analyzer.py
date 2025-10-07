#!/usr/bin/env python3
"""
测试覆盖率分析器
分析覆盖率报告并生成改进建议
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple
import json


class CoverageAnalyzer:
    def __init__(self, coverage_file: str = "coverage.xml"):
        self.coverage_file = coverage_file
        self.data = None
        self.load_coverage()

    def load_coverage(self):
        """加载覆盖率数据"""
        try:
            if os.path.exists(self.coverage_file):
                tree = ET.parse(self.coverage_file)
                self.data = tree.getroot()
            else:
                print(f"❌ 覆盖率文件不存在: {self.coverage_file}")
                return False
        except Exception as e:
            print(f"❌ 解析覆盖率文件失败: {e}")
            return False

        return True

    def get_total_coverage(self) -> float:
        """获取总覆盖率百分比"""
        if not self.data:
            return 0.0

        # 查找line-rate属性
        for elem in self.data.iter():
            if 'line-rate' in elem.attrib:
                return float(elem.attrib['line-rate']) * 100

        return 0.0

    def get_module_coverage(self) -> Dict[str, float]:
        """获取各模块的覆盖率"""
        modules = {}

        if not self.data:
            return modules

        for package in self.data.findall('.//package'):
            package_name = package.get('name', '')
            for class_elem in package.findall('.//class'):
                class_name = class_elem.get('name', '')
                full_name = f"{package_name}.{class_name}".replace('.', '/')
                line_rate = float(class_elem.get('line-rate', 0)) * 100
                modules[full_name] = line_rate

        return modules

    def get_uncovered_files(self, threshold: float = 50.0) -> List[str]:
        """获取覆盖率低于阈值的文件"""
        uncovered = []

        for module, coverage in self.get_module_coverage().items():
            if coverage < threshold:
                uncovered.append((module, coverage))

        # 按覆盖率排序
        uncovered.sort(key=lambda x: x[1])

        return [f"{mod} ({cov:.1f}%)" for mod, cov in uncovered]

    def get_improvement_suggestions(self) -> List[str]:
        """生成改进建议"""
        suggestions = []
        total = self.get_total_coverage()

        if total < 20:
            suggestions.append("🎯 第一阶段目标：达到20%覆盖率")
            suggestions.append("   - 优先为核心模块添加单元测试")
            suggestions.append("   - 关注utils/、database/等基础模块")
        elif total < 35:
            suggestions.append("🎯 第二阶段目标：达到35%覆盖率")
            suggestions.append("   - 添加服务层测试")
            suggestions.append("   - 测试API端点")
        elif total < 55:
            suggestions.append("🎯 第三阶段目标：达到55%覆盖率")
            suggestions.append("   - 添加集成测试")
            suggestions.append("   - 测试业务流程")
        elif total < 80:
            suggestions.append("🎯 第四阶段目标：达到80%覆盖率")
            suggestions.append("   - 添加端到端测试")
            suggestions.append("   - 提高边界情况覆盖")
        else:
            suggestions.append("🎉 已达到目标覆盖率！")
            suggestions.append("   - 保持测试质量")
            suggestions.append("   - 持续优化测试结构")

        # 分析具体模块
        uncovered = self.get_uncovered_files(30.0)
        if uncovered:
            suggestions.append("\n📌 需要重点关注的模块:")
            for item in uncovered[:5]:  # 显示前5个
                suggestions.append(f"   - {item}")

        return suggestions

    def generate_report(self) -> str:
        """生成详细的覆盖率报告"""
        total = self.get_total_coverage()
        modules = self.get_module_coverage()

        report = f"""
# 📊 测试覆盖率分析报告

## 总体覆盖率
**当前覆盖率**: {total:.2f}%

## 覆盖率分布
- 测试过的模块: {len([m for m in modules.values() if m > 0])}
- 总模块数: {len(modules)}
- 平均模块覆盖率: {sum(modules.values())/len(modules):.2f}% if modules else 0

## 改进建议
{chr(10).join(self.get_improvement_suggestions())}

## 模块覆盖率详情
"""

        # 按覆盖率排序显示模块
        sorted_modules = sorted(modules.items(), key=lambda x: x[1], reverse=True)
        for module, coverage in sorted_modules[:10]:  # 显示前10个
            status = "✅" if coverage > 70 else "⚠️" if coverage > 30 else "❌"
            report += f"- {status} {module}: {coverage:.1f}%\n"

        if len(sorted_modules) > 10:
            report += f"... 还有 {len(sorted_modules) - 10} 个模块\n"

        return report

    def save_report(self, output_file: str = "coverage-analysis.md"):
        """保存报告到文件"""
        report = self.generate_report()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ 报告已保存到: {output_file}")
        return report

    def update_todo_board(self):
        """更新任务看板"""
        total = self.get_total_coverage()

        # 读取任务看板
        todo_file = Path("TEST_COVERAGE_TASK_BOARD.md")
        if not todo_file.exists():
            print("❌ 任务看板文件不存在")
            return

        with open(todo_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 更新进度
        if total < 20:
            content = content.replace(
                "**当前进度**: 16% → 20% (第一阶段)",
                f"**当前进度**: {total:.1f}% → 20% (第一阶段)"
            )

        with open(todo_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 任务看板已更新")


def main():
    """主函数"""
    analyzer = CoverageAnalyzer()

    if not analyzer.data:
        sys.exit(1)

    # 打印简要信息
    total = analyzer.get_total_coverage()
    print(f"\n📊 当前测试覆盖率: {total:.2f}%")

    # 生成并保存报告
    analyzer.save_report()

    # 更新任务看板
    analyzer.update_todo_board()

    # 输出改进建议
    print("\n💡 改进建议:")
    for suggestion in analyzer.get_improvement_suggestions()[:5]:
        print(f"  {suggestion}")

    # 返回退出码
    if total >= 20:
        print("\n✅ 已达到第一阶段目标！")
        sys.exit(0)
    else:
        print(f"\n⚠️  还需增加 {20 - total:.1f}% 以达到第一阶段目标")
        sys.exit(1)


if __name__ == "__main__":
    main()