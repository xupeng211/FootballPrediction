#!/usr/bin/env python3
"""
AI 代码分析器

集成 Claude Code CLI，实现智能的测试失败分析和修复建议生成。
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .claude_cli_wrapper import ClaudeCodeWrapper, TestFailure, FixSuggestion, TestFailureParser

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果"""
    test_failures: List[TestFailure]
    fix_suggestions: List[FixSuggestion]
    analysis_summary: Dict
    timestamp: datetime
    confidence_score: float


class CodeAnalyzer:
    """AI 代码分析器主类"""

    def __init__(self):
        self.claude_wrapper = ClaudeCodeWrapper()
        self.parser = TestFailureParser()
        logger.info("CodeAnalyzer initialized")

    def analyze_test_results(self, pytest_output: str, coverage_data: Optional[Dict] = None) -> AnalysisResult:
        """
        分析测试结果，生成修复建议

        Args:
            pytest_output: pytest 输出日志
            coverage_data: 覆盖率数据（可选）

        Returns:
            分析结果
        """
        logger.info("Starting test results analysis...")

        # 1. 解析测试失败
        test_failures = self.parser.parse_pytest_output(pytest_output)
        logger.info(f"Found {len(test_failures)} test failures")

        fix_suggestions = []

        # 2. 对每个失败进行分析
        for failure in test_failures:
            try:
                logger.info(f"Analyzing failure: {failure.test_name}")

                # 分析失败原因
                analysis = self.claude_wrapper.analyze_test_failure(failure)

                # 生成修复建议
                fix_suggestion = self.claude_wrapper.generate_fix(failure, analysis)

                # 验证修复建议
                if self.claude_wrapper.validate_fix(fix_suggestion):
                    fix_suggestions.append(fix_suggestion)
                    logger.info(f"Generated valid fix for {failure.test_name}")
                else:
                    logger.warning(f"Invalid fix suggestion for {failure.test_name}")

            except Exception as e:
                logger.error(f"Failed to analyze failure {failure.test_name}: {e}")
                continue

        # 3. 生成分析摘要
        analysis_summary = self._generate_analysis_summary(
            test_failures, fix_suggestions, coverage_data
        )

        # 4. 计算整体置信度
        confidence_score = self._calculate_confidence_score(test_failures, fix_suggestions)

        return AnalysisResult(
            test_failures=test_failures,
            fix_suggestions=fix_suggestions,
            analysis_summary=analysis_summary,
            timestamp=datetime.now(),
            confidence_score=confidence_score
        )

    def prioritize_fixes(self, analysis_result: AnalysisResult) -> List[FixSuggestion]:
        """
        对修复建议进行优先级排序

        Args:
            analysis_result: 分析结果

        Returns:
            排序后的修复建议列表
        """
        suggestions = analysis_result.fix_suggestions

        # 按多个维度排序：
        # 1. 置信度（高到低）
        # 2. 错误类型（语法错误优先）
        # 3. 文件重要性（核心文件优先）

        def get_priority_score(suggestion: FixSuggestion) -> Tuple[float, int, int]:
            # 基础分数：置信度
            base_score = suggestion.confidence

            # 错误类型权重
            error_type_weight = self._get_error_type_weight(suggestion)

            # 文件重要性权重
            file_importance_weight = self._get_file_importance_weight(suggestion.file_path)

            return (base_score, error_type_weight, file_importance_weight)

        return sorted(suggestions, key=get_priority_score, reverse=True)

    def generate_bugfix_todo(self, analysis_result: AnalysisResult, output_path: Path) -> None:
        """
        生成 BUGFIX_TODO.md 文件

        Args:
            analysis_result: 分析结果
            output_path: 输出文件路径
        """
        logger.info(f"Generating BUGFIX_TODO at {output_path}")

        # 获取优先级排序的修复建议
        prioritized_fixes = self.prioritize_fixes(analysis_result)

        # 生成 TODO 内容
        todo_content = self._generate_todo_content(analysis_result, prioritized_fixes)

        # 写入文件
        output_path.write_text(todo_content, encoding='utf-8')
        logger.info("BUGFIX_TODO generated successfully")

    def apply_fix(self, fix_suggestion: FixSuggestion, dry_run: bool = True) -> bool:
        """
        应用修复建议

        Args:
            fix_suggestion: 修复建议
            dry_run: 是否为预览模式

        Returns:
            修复是否成功
        """
        file_path = Path(fix_suggestion.file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        try:
            # 读取原文件
            original_content = file_path.read_text(encoding='utf-8')

            # 如果是预览模式，只显示差异
            if dry_run:
                print(f"📋 Preview fix for {file_path}:")
                print("Original code:")
                print("-" * 40)
                print(original_content)
                print("\nFixed code:")
                print("-" * 40)
                print(fix_suggestion.fixed_code)
                print("\nExplanation:", fix_suggestion.explanation)
                return True

            # 应用修复
            file_path.write_text(fix_suggestion.fixed_code, encoding='utf-8')
            logger.info(f"Applied fix to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply fix to {file_path}: {e}")
            return False

    def _generate_analysis_summary(self, test_failures: List[TestFailure],
                                 fix_suggestions: List[FixSuggestion],
                                 coverage_data: Optional[Dict]) -> Dict:
        """生成分析摘要"""
        summary = {
            "total_failures": len(test_failures),
            "generated_fixes": len(fix_suggestions),
            "success_rate": len(fix_suggestions) / len(test_failures) if test_failures else 0,
            "error_types": {},
            "confidence_distribution": {
                "high": len([f for f in fix_suggestions if f.confidence >= 0.8]),
                "medium": len([f for f in fix_suggestions if 0.5 <= f.confidence < 0.8]),
                "low": len([f for f in fix_suggestions if f.confidence < 0.5])
            }
        }

        # 统计错误类型
        for failure in test_failures:
            error_type = failure.error_type
            summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + 1

        # 添加覆盖率信息
        if coverage_data:
            summary["coverage"] = {
                "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                "low_coverage_files": len([
                    f for f, data in coverage_data.get("files", {}).items()
                    if data.get("summary", {}).get("percent_covered", 100) < 50
                ])
            }

        return summary

    def _calculate_confidence_score(self, test_failures: List[TestFailure],
                                  fix_suggestions: List[FixSuggestion]) -> float:
        """计算整体置信度分数"""
        if not test_failures:
            return 1.0

        if not fix_suggestions:
            return 0.0

        # 基于修复建议的平均置信度
        avg_confidence = sum(f.confidence for f in fix_suggestions) / len(fix_suggestions)

        # 基于修复覆盖率
        coverage_rate = len(fix_suggestions) / len(test_failures)

        # 综合评分
        return (avg_confidence * 0.7) + (coverage_rate * 0.3)

    def _get_error_type_weight(self, suggestion: FixSuggestion) -> int:
        """获取错误类型权重"""
        # 这里可以根据实际错误类型设置权重
        # 语法错误 > 导入错误 > 逻辑错误
        error_priorities = {
            "SyntaxError": 3,
            "ImportError": 2,
            "ModuleNotFoundError": 2,
            "AssertionError": 1,
            "TypeError": 1,
            "ValueError": 1
        }
        return error_priorities.get("UnknownError", 0)

    def _get_file_importance_weight(self, file_path: str) -> int:
        """获取文件重要性权重"""
        path = Path(file_path)

        # 核心文件优先级更高
        if "src/api/" in str(path):
            return 3
        elif "src/core/" in str(path):
            return 2
        elif "src/services/" in str(path):
            return 2
        elif "tests/" in str(path):
            return 1
        else:
            return 0

    def _generate_todo_content(self, analysis_result: AnalysisResult,
                             prioritized_fixes: List[FixSuggestion]) -> str:
        """生成 TODO 内容"""
        lines = []
        lines.append("# 🤖 AI Bugfix TODO Board")
        lines.append("")
        lines.append(f"自动更新于: {analysis_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## 📊 分析摘要")
        lines.append(f"- 总测试失败数: {analysis_result.analysis_summary['total_failures']}")
        lines.append(f"- 生成修复建议: {analysis_result.analysis_summary['generated_fixes']}")
        lines.append(f"- 成功率: {analysis_result.analysis_summary['success_rate']:.1%}")
        lines.append(f"- 整体置信度: {analysis_result.confidence_score:.1%}")
        lines.append("")

        # 错误类型分布
        if analysis_result.analysis_summary["error_types"]:
            lines.append("## 📈 错误类型分布")
            for error_type, count in analysis_result.analysis_summary["error_types"].items():
                lines.append(f"- {error_type}: {count} 次")
            lines.append("")

        # 置信度分布
        lines.append("## 🎯 修复建议置信度分布")
        conf_dist = analysis_result.analysis_summary["confidence_distribution"]
        lines.append(f"- 高置信度 (≥80%): {conf_dist['high']} 个")
        lines.append(f"- 中等置信度 (50-80%): {conf_dist['medium']} 个")
        lines.append(f"- 低置信度 (<50%): {conf_dist['low']} 个")
        lines.append("")

        # 待修复任务
        lines.append("## 🚧 AI 建议的修复任务")
        for i, fix in enumerate(prioritized_fixes, 1):
            lines.append(f"{i}. **{fix.file_path}** (置信度: {fix.confidence:.1%})")
            lines.append(f"   - 问题: {fix.explanation}")
            lines.append(f"   - 修改范围: 第 {fix.line_range[0]}-{fix.line_range[1]} 行")
            lines.append("")

        # 已完成任务
        lines.append("## ✅ 已完成的修复")
        lines.append("（等待修复完成后的更新）")
        lines.append("")

        # 建议行动
        lines.append("## 🔧 AI 建议的行动")
        lines.append("1. 按优先级应用修复建议")
        lines.append("2. 每次修复后运行测试验证")
        lines.append("3. 如果修复效果不佳，请手动调整")
        lines.append("4. 定期运行此分析以保持代码质量")
        lines.append("")

        lines.append("---")
        lines.append("*此报告由 AI 自动生成，请人工审核后执行*")

        return "\n".join(lines)


def main():
    """主函数 - 用于测试"""
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 创建分析器
    analyzer = CodeAnalyzer()

    # 模拟 pytest 输出
    mock_pytest_output = """
    FAIL: tests/test_example.py::test_example_function
        File "/project/tests/test_example.py", line 10
        def test_example_function():
    >       assert False
    E       AssertionError: assert False

    FAIL: tests/test_another.py::test_another_function
        File "/project/tests/test_another.py", line 20
        def test_another_function():
    >       result = undefined_function()
    E       NameError: name 'undefined_function' is not defined
    """

    # 分析测试结果
    print("🔍 Analyzing test results...")
    analysis_result = analyzer.analyze_test_results(mock_pytest_output)

    # 输出分析结果
    print(f"\n📊 Analysis Summary:")
    print(f"Total failures: {analysis_result.analysis_summary['total_failures']}")
    print(f"Generated fixes: {analysis_result.analysis_summary['generated_fixes']}")
    print(f"Confidence score: {analysis_result.confidence_score:.1%}")

    # 生成 BUGFIX_TODO
    todo_path = Path("docs/_reports/BUGFIX_TODO_AI.md")
    analyzer.generate_bugfix_todo(analysis_result, todo_path)
    print(f"\n📝 Generated BUGFIX_TODO at {todo_path}")

    # 显示优先级修复
    prioritized = analyzer.prioritize_fixes(analysis_result)
    print(f"\n🎯 Top priority fix:")
    if prioritized:
        top_fix = prioritized[0]
        print(f"File: {top_fix.file_path}")
        print(f"Confidence: {top_fix.confidence:.1%}")
        print(f"Explanation: {top_fix.explanation}")


if __name__ == "__main__":
    main()