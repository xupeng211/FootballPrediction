#!/usr/bin/env python3
"""
修复计划生成器
Fix Plan Generator

基于覆盖率数据自动生成测试修复计划
根据测试覆盖率基线分析报告，优先处理高业务价值模块

功能：
- 读取 coverage.json 和 uncovered_files.json
- 按未覆盖行数排序生成修复计划
- 优先处理 Service 和 API 层的关键文件
- 输出 Markdown 格式的待办清单

创建时间: 2025-11-22
基于: 测试覆盖率基线分析报告
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import argparse
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FixPlanGenerator:
    """修复计划生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_file = project_root / "coverage.json"
        self.uncovered_file = project_root / "uncovered_files.json"
        self.modules_file = project_root / "modules_without_tests.json"

    def load_coverage_data(self) -> dict[str, Any] | None:
        """加载覆盖率数据"""
        if not self.coverage_file.exists():
            logger.error(f"Coverage file not found: {self.coverage_file}")
            return None

        try:
            with open(self.coverage_file) as f:
                return json.load(f)
        except Exception:
            logger.error(f"Failed to load coverage data: {e}")
            return None

    def load_uncovered_files(self) -> list[dict[str, Any]] | None:
        """加载未覆盖文件数据"""
        if not self.uncovered_file.exists():
            logger.error(f"Uncovered files data not found: {self.uncovered_file}")
            return None

        try:
            with open(self.uncovered_file) as f:
                data = json.load(f)
                return data.get("uncovered_files", [])
        except Exception:
            logger.error(f"Failed to load uncovered files data: {e}")
            return None

    def load_modules_without_tests(self) -> dict[str, Any] | None:
        """加载无测试模块数据"""
        if not self.modules_file.exists():
            logger.warning(f"Modules without tests file not found: {self.modules_file}")
            return None

        try:
            with open(self.modules_file) as f:
                return json.load(f)
        except Exception:
            logger.error(f"Failed to load modules without tests data: {e}")
            return None

    def categorize_by_priority(
        self, files: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """按优先级分类文件"""
        categories = {
            "P0_Critical": [],  # 核心业务模块，高未覆盖
            "P1_High": [],  # 重要模块，中等未覆盖
            "P2_Medium": [],  # 一般模块，需要关注
            "P3_Low": [],  # 低优先级
        }

        for file_info in files:
            file_info["file_path"]
            uncovered_lines = file_info["uncovered_lines"]
            business_criticality = file_info.get("business_criticality", "medium")

            # P0: 核心业务模块 + 高未覆盖行数
            if (
                (business_criticality == "critical" and uncovered_lines > 100)
                or (business_criticality == "high" and uncovered_lines > 200)
                or uncovered_lines > 250
            ):
                categories["P0_Critical"].append(file_info)

            # P1: 重要模块
            elif (
                business_criticality in ["critical", "high"] and uncovered_lines > 50
            ) or uncovered_lines > 150:
                categories["P1_High"].append(file_info)

            # P2: 一般模块
            elif uncovered_lines > 50:
                categories["P2_Medium"].append(file_info)

            # P3: 低优先级
            else:
                categories["P3_Low"].append(file_info)

        return categories

    def generate_test_suggestions(self, file_info: dict[str, Any]) -> list[str]:
        """为文件生成测试建议"""
        suggestions = []
        file_path = file_info["file_path"]
        uncovered_lines = file_info["uncovered_lines"]

        if "api/" in file_path:
            suggestions.extend(
                [
                    f"创建 `tests/unit/api/{file_path.split('/')[-1].replace('.py', '_test.py')}`",
                    "测试HTTP端点的请求/响应",
                    "验证参数验证和错误处理",
                    "测试API返回状态码和响应格式",
                ]
            )
        elif "services/" in file_path:
            suggestions.extend(
                [
                    f"创建 `tests/unit/services/{file_path.split('/')[-1].replace('.py', '_test.py')}`",
                    "使用unittest.mock模拟外部依赖",
                    "测试核心业务逻辑",
                    "验证边界条件和异常处理",
                    "添加性能基准测试",
                ]
            )
        elif "database/" in file_path:
            suggestions.extend(
                [
                    f"创建 `tests/unit/database/{file_path.split('/')[-1].replace('.py', '_test.py')}`",
                    "使用内存数据库进行测试",
                    "测试数据库连接和事务",
                    "验证SQL查询逻辑",
                ]
            )
        elif "cache/" in file_path:
            suggestions.extend(
                [
                    f"创建 `tests/unit/cache/{file_path.split('/')[-1].replace('.py', '_test.py')}`",
                    "模拟Redis连接进行测试",
                    "测试缓存策略和失效逻辑",
                    "验证性能和并发访问",
                ]
            )
        else:
            suggestions.extend(
                [
                    f"创建 `tests/unit/{file_path.replace('src/', '').replace('.py', '_test.py')}`",
                    "添加基础单元测试",
                    "覆盖主要函数和方法",
                ]
            )

        # 根据未覆盖行数添加建议
        if uncovered_lines > 200:
            suggestions.append("考虑拆分大文件以提高可测试性")
        elif uncovered_lines > 100:
            suggestions.append("重点关注核心函数和类的测试覆盖")

        return suggestions

    def generate_markdown_report(
        self,
        categories: dict[str, list[dict[str, Any]]],
        modules_data: dict[str, Any] | None = None,
    ) -> str:
        """生成Markdown格式的修复计划"""

        report = f"""# 测试覆盖率修复计划

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**基于数据**: coverage.json + uncovered_files.json

## 📊 修复计划概览

| 优先级 | 文件数量 | 总未覆盖行数 | 平均覆盖率 |
|--------|----------|------------|------------|
"""

        # 添加概览统计
        for priority, files in categories.items():
            if files:
                total_uncovered = sum(f["uncovered_lines"] for f in files)
                avg_coverage = sum(f["coverage_percent"] for f in files) / len(files)
                report += f"| {priority} | {len(files)} | {total_uncovered} | {avg_coverage:.1f}% |\n"

        # P0 优先级详细计划
        if categories["P0_Critical"]:
            report += """

## 🔴 P0 优先级 - 关键业务模块 (立即处理)

**说明**: 这些文件包含核心业务逻辑，未覆盖代码超过250行或属于高业务价值模块
**目标**: 本周内完成基础测试覆盖

"""
            for i, file_info in enumerate(categories["P0_Critical"], 1):
                report += f"""
### {i}. {file_info["file_path"]}

- **未覆盖行数**: {file_info["uncovered_lines"]}
- **总行数**: {file_info["total_lines"]}
- **当前覆盖率**: {file_info["coverage_percent"]}%
- **业务关键性**: {file_info.get("business_criticality", "unknown")}

**测试建议**:
"""
                suggestions = self.generate_test_suggestions(file_info)
                for suggestion in suggestions:
                    report += f"- {suggestion}\n"

                report += f"""
**推荐测试文件名**: `tests/unit/{file_info["file_path"].replace("src/", "").replace(".py", "_test.py")}`

**预期覆盖率提升**: {min(file_info["uncovered_lines"] / 2, file_info["total_lines"] * 0.7):.0f} 行

---

"""

        # P1 优先级
        if categories["P1_High"]:
            report += """

## 🟡 P1 优先级 - 重要模块 (本周目标)

**说明**: 重要功能模块，需要完善测试覆盖

"""
            for i, file_info in enumerate(categories["P1_High"], 1):
                report += f"""
### {i}. {file_info["file_path"]}

- **未覆盖行数**: {file_info["uncovered_lines"]}
- **当前覆盖率**: {file_info["coverage_percent"]}%

"""

        # P2 优先级
        if categories["P2_Medium"]:
            report += """

## 🟢 P2 优先级 - 一般模块 (计划处理)

"""
            for _, file_info in enumerate(
                categories["P2_Medium"][:10], 1
            ):  # 只显示前10个
                report += f"- {file_info['file_path']} ({file_info['uncovered_lines']}行未覆盖)\n"

        # 模块级分析
        if modules_data:
            report += """

## 📁 模块级测试覆盖分析

"""
            modules = modules_data.get("modules_without_tests", [])
            for module in modules:
                report += f"""
### {module["module_path"]} (无测试覆盖)

- **文件数量**: {module["file_count"]}
- **总代码行数**: {module["total_lines"]}
- **风险等级**: {module["risk_level"]}
- **推荐测试文件**:
"""
                for test_file in module.get("recommended_test_files", []):
                    report += f"  - `{test_file}`\n"

        # 执行计划
        report += f"""

## 🚀 执行计划

### 第一周 (P0 优先级)
- [ ] 完成 {len(categories.get("P0_Critical", []))} 个关键文件的单元测试
- [ ] 预期覆盖率提升: {sum(f["uncovered_lines"] for f in categories.get("P0_Critical", []))} 行
- [ ] 重点关注: EV计算器、缓存性能API等核心业务

### 第二周 (P1 优先级)
- [ ] 完成 {len(categories.get("P1_High", []))} 个重要文件的测试
- [ ] 开始集成测试覆盖
- [ ] 建立持续监控机制

### 第三周 (P2 优先级 + 完善)
- [ ] 完成 {len(categories.get("P2_Medium", []))} 个一般文件测试
- [ ] 完善测试文档和覆盖率报告
- [ ] 建立自动化质量门禁

## 📈 预期效果

执行完此计划后预期达成：
- **整体覆盖率**: 从 35.12% 提升至 45%+
- **核心模块覆盖**: 关键业务文件测试覆盖率 >80%
- **测试质量**: 减少空测试和无断言测试

## 🔧 推荐工具和脚本

1. **快速创建测试**:
   ```bash
   python scripts/create_test_template.py --file src/services/betting/enhanced_ev_calculator.py
   ```

2. **覆盖率监控**:
   ```bash
   python scripts/run_tests_with_report.py --format both
   ```

3. **自动化修复**:
   ```bash
   python scripts/continuous_bugfix.py --priority P0
   ```

---

*报告由 generate_fix_plan.py 自动生成*
*下次更新: 根据修复进度调整计划*
"""

        return report

    def save_report(self, report: str, filename: str | None = None):
        """保存修复计划报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_coverage_fix_plan_{timestamp}.md"

        report_file = self.project_root / "docs" / filename
        report_file.parent.mkdir(exist_ok=True)

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"Fix plan report saved to: {report_file}")
            return report_file
        except Exception:
            logger.error(f"Failed to save report: {e}")
            return None

    def generate_plan(self, output_format: str = "markdown") -> str:
        """生成完整的修复计划"""
        logger.info("Generating test coverage fix plan...")

        # 加载数据
        uncovered_files = self.load_uncovered_files()
        if not uncovered_files:
            return "Error: Could not load uncovered files data"

        modules_data = self.load_modules_without_tests()

        # 分类文件
        categories = self.categorize_by_priority(uncovered_files)

        # 生成报告
        if output_format == "markdown":
            report = self.generate_markdown_report(categories, modules_data)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        # 保存报告
        self.save_report(report)

        # 输出到控制台

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成测试覆盖率修复计划")
    parser.add_argument(
        "--format", choices=["markdown"], default="markdown", help="输出格式"
    )
    parser.add_argument("--output", help="输出文件名")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    generator = FixPlanGenerator(project_root)

    try:
        report = generator.generate_plan(args.format)

        # 如果指定了输出文件名，也保存一份
        if args.output:
            generator.save_report(report, args.output)

    except Exception:
        logger.error(f"Failed to generate fix plan: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
