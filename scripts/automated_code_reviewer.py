#!/usr/bin/env python3
"""
AI驱动的自动化代码审查系统
Automated Code Review System

基于Issue #98方法论，提供智能代码审查和改进建议
"""

import os
import sys
import json
import subprocess
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
import logging
from src.core.config import 
from src.core.config import 

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class CodeIssue:
    """代码问题数据类"""

    file_path: str
    line_number: int
    issue_type: str
    severity: str  # critical, high, medium, low
    message: str
    suggestion: str
    rule_id: str


@dataclass
class CodeMetrics:
    """代码指标数据类"""

    file_path: str
    lines_of_code: int
    cyclomatic_complexity: int
    maintainability_index: float
    duplicate_lines: int
    test_coverage: float


class AutomatedCodeReviewer:
    """自动化代码审查系统 - 基于Issue #98方法论"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"

        # 审查结果
        self.review_results = {
            "timestamp": datetime.now().isoformat(),
            "issues_found": [],
            "metrics": {},
            "summary": {},
            "recommendations": [],
            "quality_score": 0.0,
            "issue_98_methodology_applied": True,
        }

        # 审查规则配置
        self.review_rules = self._load_review_rules()

    def _load_review_rules(self) -> Dict[str, Any]:
        """加载审查规则"""
        return {
            "complexity_threshold": 10,
            "function_length_limit": 50,
            "class_length_limit": 200,
            "max_parameters": 7,
            "max_nesting_depth": 4,
            "min_test_coverage": 15.0,
            "duplicate_line_threshold": 5,
            "magic_number_threshold": 10,
        }

    def run_comprehensive_review(self) -> Dict[str, Any]:
        """运行全面代码审查"""
        logger.info("🔍 开始自动化代码审查...")

        print("🔍 AI驱动自动化代码审查系统")
        print("基于Issue #98方法论")
        print("=" * 60)

        # 1. 扫描代码问题
        print("\n1️⃣ 扫描代码质量问题...")
        issues = self.scan_code_issues()

        # 2. 计算代码指标
        print("\n2️⃣ 计算代码质量指标...")
        metrics = self.calculate_code_metrics()

        # 3. 分析测试覆盖率
        print("\n3️⃣ 分析测试覆盖率...")
        coverage_analysis = self.analyze_test_coverage()

        # 4. 检测代码重复
        print("\n4️⃣ 检测代码重复...")
        duplication_analysis = self.detect_code_duplication()

        # 5. 安全性检查
        print("\n5️⃣ 执行安全性检查...")
        security_issues = self.perform_security_analysis()

        # 6. 性能分析
        print("\n6️⃣ 执行性能分析...")
        performance_issues = self.perform_performance_analysis()

        # 7. 生成综合报告
        print("\n7️⃣ 生成综合审查报告...")
        self.generate_comprehensive_report(
            issues,
            metrics,
            coverage_analysis,
            duplication_analysis,
            security_issues,
            performance_issues,
        )

        print("\n✅ 代码审查完成！")
        print(f"📊 发现问题: {len(self.review_results['issues_found'])} 个")
        print(f"📈 质量评分: {self.review_results['quality_score']:.1f}/10")

        return self.review_results

    def scan_code_issues(self) -> List[CodeIssue]:
        """扫描代码质量问题"""
        issues = []

        # 扫描所有Python文件
        python_files = list(self.src_dir.rglob("*.py"))

        for py_file in python_files:
            try:
                file_issues = self._analyze_file_issues(py_file)
                issues.extend(file_issues)
            except Exception as e:
                logger.error(f"分析文件失败 {py_file}: {e}")

        # 按严重程度排序
        issues.sort(key=lambda x: self._severity_priority(x.severity), reverse=True)

        self.review_results["issues_found"] = [
            {
                "file_path": issue.file_path,
                "line_number": issue.line_number,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "rule_id": issue.rule_id,
            }
            for issue in issues
        ]

        print(f"  ✅ 发现质量问题: {len(issues)} 个")
        return issues

    def _analyze_file_issues(self, file_path: Path) -> List[CodeIssue]:
        """分析单个文件的问题"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # 解析AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return [
                    CodeIssue(
                        file_path=str(file_path),
                        line_number=1,
                        issue_type="syntax_error",
                        severity="critical",
                        message="文件存在语法错误",
                        suggestion="修复语法错误后重新审查",
                        rule_id="SYNTAX001",
                    )
                ]

            # 分析AST节点
            for node in ast.walk(tree):
                node_issues = self._analyze_ast_node(node, file_path, lines)
                issues.extend(node_issues)

            # 逐行分析
            for i, line in enumerate(lines, 1):
                line_issues = self._analyze_line(line, i, file_path)
                issues.extend(line_issues)

        except Exception as e:
            logger.error(f"文件分析失败 {file_path}: {e}")

        return issues

    def _analyze_ast_node(
        self, node: ast.AST, file_path: Path, lines: List[str]
    ) -> List[CodeIssue]:
        """分析AST节点问题"""
        issues = []

        # 函数复杂度检查
        if isinstance(node, ast.FunctionDef):
            complexity = self._calculate_cyclomatic_complexity(node)
            if complexity > self.review_rules["complexity_threshold"]:
                issues.append(
                    CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        issue_type="high_complexity",
                        severity="high",
                        message=f"函数 '{node.name}' 的圈复杂度过高: {complexity}",
                        suggestion=f"建议将函数拆分为更小的函数，目标复杂度 < {self.review_rules['complexity_threshold']}",
                        rule_id="COMPLEX001",
                    )
                )

            # 函数长度检查
            if hasattr(node, "end_lineno") and node.end_lineno:
                function_length = node.end_lineno - node.lineno + 1
                if function_length > self.review_rules["function_length_limit"]:
                    issues.append(
                        CodeIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            issue_type="long_function",
                            severity="medium",
                            message=f"函数 '{node.name}' 过长: {function_length} 行",
                            suggestion=f"建议将函数拆分，目标长度 < {self.review_rules['function_length_limit']} 行",
                            rule_id="LENGTH001",
                        )
                    )

            # 参数数量检查
            if len(node.args.args) > self.review_rules["max_parameters"]:
                issues.append(
                    CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        issue_type="too_many_parameters",
                        severity="medium",
                        message=f"函数 '{node.name}' 参数过多: {len(node.args.args)} 个",
                        suggestion="考虑使用参数对象或配置字典来减少参数数量",
                        rule_id="PARAM001",
                    )
                )

        # 类长度检查
        elif isinstance(node, ast.ClassDef):
            if hasattr(node, "end_lineno") and node.end_lineno:
                class_length = node.end_lineno - node.lineno + 1
                if class_length > self.review_rules["class_length_limit"]:
                    issues.append(
                        CodeIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            issue_type="large_class",
                            severity="medium",
                            message=f"类 '{node.name}' 过大: {class_length} 行",
                            suggestion="建议将类拆分为多个职责单一的类",
                            rule_id="CLASS001",
                        )
                    )

        return issues

    def _analyze_line(self, line: str, line_num: int, file_path: Path) -> List[CodeIssue]:
        """分析单行代码问题"""
        issues = []

        # 魔法数字检查
        magic_numbers = re.findall(r"\b\d{2,}\b", line)
        for num in magic_numbers:
            if int(num) > self.review_rules["magic_number_threshold"] and "TODO" not in line:
                issues.append(
                    CodeIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type="magic_number",
                        severity="low",
                        message=f"发现魔法数字: {num}",
                        suggestion="建议将魔法数字提取为命名常量",
                        rule_id="MAGIC001",
                    )
                )

        # 长行检查
        if len(line) > 120:
            issues.append(
                CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="long_line",
                    severity="low",
                    message=f"代码行过长: {len(line)} 字符",
                    suggestion="建议将长行拆分为多行，提高可读性",
                    rule_id="FORMAT001",
                )
            )

        # TODO/FIXME检查
        if "TODO" in line or "FIXME" in line:
            issues.append(
                CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="todo_comment",
                    severity="low",
                    message="存在待办事项注释",
                    suggestion="及时处理TODO/FIXME项目",
                    rule_id="TODO001",
                )
            )

        return issues

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def calculate_code_metrics(self) -> Dict[str, Any]:
        """计算代码质量指标"""
        metrics = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "average_complexity": 0.0,
            "max_complexity": 0,
            "average_function_length": 0.0,
            "test_coverage": 0.0,
        }

        python_files = list(self.src_dir.rglob("*.py"))
        metrics["total_files"] = len(python_files)

        total_complexity = 0
        total_function_length = 0
        function_count = 0

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                metrics["total_lines"] += len(lines)

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        metrics["total_functions"] += 1
                        function_count += 1

                        complexity = self._calculate_cyclomatic_complexity(node)
                        total_complexity += complexity
                        metrics["max_complexity"] = max(metrics["max_complexity"], complexity)

                        if hasattr(node, "end_lineno") and node.end_lineno:
                            function_length = node.end_lineno - node.lineno + 1
                            total_function_length += function_length

                    elif isinstance(node, ast.ClassDef):
                        metrics["total_classes"] += 1

            except Exception as e:
                logger.error(f"计算指标失败 {py_file}: {e}")

        # 计算平均值
        if function_count > 0:
            metrics["average_complexity"] = total_complexity / function_count
            metrics["average_function_length"] = total_function_length / function_count

        self.review_results["metrics"] = metrics

        print(f"  ✅ 处理文件: {metrics['total_files']} 个")
        print(f"  ✅ 总代码行数: {metrics['total_lines']} 行")
        print(f"  ✅ 平均复杂度: {metrics['average_complexity']:.1f}")

        return metrics

    def analyze_test_coverage(self) -> Dict[str, Any]:
        """分析测试覆盖率"""
        coverage_info = {
            "overall_coverage": 0.0,
            "covered_files": 0,
            "uncovered_files": 0,
            "recommendations": [],
        }

        try:
            # 尝试读取覆盖率报告
            coverage_file = self.project_root / "htmlcov" / "index.html"
            if coverage_file.exists():
                with open(coverage_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 解析覆盖率百分比
                match = re.search(r"([0-9]*\.[0-9]%)", content)
                if match:
                    coverage_info["overall_coverage"] = float(match.group(1).rstrip("%"))

            # 分析测试文件与源文件的比例
            test_files = list(self.test_dir.rglob("test_*.py"))
            src_files = list(self.src_dir.rglob("*.py"))

            coverage_info["test_files_count"] = len(test_files)
            coverage_info["source_files_count"] = len(src_files)
            coverage_info["test_to_source_ratio"] = len(test_files) / max(len(src_files), 1)

            # 生成覆盖率建议
            if coverage_info["overall_coverage"] < self.review_rules["min_test_coverage"]:
                coverage_info["recommendations"].append(
                    f"测试覆盖率({coverage_info['overall_coverage']:.1f}%)低于目标({self.review_rules['min_test_coverage']}%)"
                )

            if coverage_info["test_to_source_ratio"] < 0.8:
                coverage_info["recommendations"].append("建议为每个主要源文件编写对应的测试文件")

        except Exception as e:
            logger.error(f"覆盖率分析失败: {e}")

        print(f"  ✅ 测试覆盖率: {coverage_info['overall_coverage']:.1f}%")
        return coverage_info

    def detect_code_duplication(self) -> Dict[str, Any]:
        """检测代码重复"""
        duplication_info = {
            "duplicated_blocks": 0,
            "duplicated_lines": 0,
            "duplication_percentage": 0.0,
            "similar_functions": [],
        }

        # 简化的重复检测：检查相似的函数结构
        function_signatures = defaultdict(list)

        python_files = list(self.src_dir.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 生成函数签名（简化版）
                        signature = self._generate_function_signature(node)
                        function_signatures[signature].append(
                            {"file": str(py_file), "line": node.lineno, "name": node.name}
                        )

            except Exception as e:
                logger.error(f"重复检测失败 {py_file}: {e}")

        # 找出重复的函数
        for signature, functions in function_signatures.items():
            if len(functions) > 1:
                duplication_info["duplicated_blocks"] += len(functions) - 1
                duplication_info["similar_functions"].append(
                    {"signature": signature, "occurrences": functions}
                )

        print(f"  ✅ 发现重复块: {duplication_info['duplicated_blocks']} 个")
        return duplication_info

    def _generate_function_signature(self, node: ast.FunctionDef) -> str:
        """生成函数签名"""
        args = [arg.arg for arg in node.args.args]
        return f"{node.name}({', '.join(args)})"

    def perform_security_analysis(self) -> List[Dict[str, Any]]:
        """执行安全性分析"""
        security_issues = []

        python_files = list(self.src_dir.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # 检查安全问题
                    if "eval(" in line or "exec(" in line:
                        security_issues.append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "severity": "high",
                                "issue": "使用危险的eval/exec函数",
                                "recommendation": "避免使用eval/exec，考虑更安全的替代方案",
                            }
                        )

                    if "password" in line.lower() and "=" in line and '"' in line:
                        security_issues.append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "severity": "critical",
                                "issue": "可能硬编码密码",
                                "recommendation": "使用环境变量或配置文件存储敏感信息",
                            }
                        )

                    if "sql" in line.lower() and "%" in line and "format" in line:
                        security_issues.append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "severity": "high",
                                "issue": "可能的SQL注入风险",
                                "recommendation": "使用参数化查询替代字符串格式化",
                            }
                        )

            except Exception as e:
                logger.error(f"安全分析失败 {py_file}: {e}")

        print(f"  ✅ 发现安全问题: {len(security_issues)} 个")
        return security_issues

    def perform_performance_analysis(self) -> List[Dict[str, Any]]:
        """执行性能分析"""
        performance_issues = []

        python_files = list(self.src_dir.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # 检查性能问题
                    if "while True:" in line and "sleep" not in line:
                        performance_issues.append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "severity": "medium",
                                "issue": "可能的无限循环",
                                "recommendation": "确保循环有明确的退出条件",
                            }
                        )

                    if line.count("[") > 3 and "for" in line:
                        performance_issues.append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "severity": "low",
                                "issue": "嵌套循环可能影响性能",
                                "recommendation": "考虑优化算法或使用更高效的数据结构",
                            }
                        )

                    if "+=" in line and "str" in line:
                        performance_issues.append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "severity": "low",
                                "issue": "字符串拼接可能影响性能",
                                "recommendation": "考虑使用join()或f-string替代字符串拼接",
                            }
                        )

            except Exception as e:
                logger.error(f"性能分析失败 {py_file}: {e}")

        print(f"  ✅ 发现性能问题: {len(performance_issues)} 个")
        return performance_issues

    def generate_comprehensive_report(
        self, issues, metrics, coverage, duplication, security, performance
    ):
        """生成综合审查报告"""
        # 计算质量评分
        quality_score = self._calculate_overall_quality_score(issues, metrics, coverage, security)
        self.review_results["quality_score"] = quality_score

        # 生成问题摘要
        issue_summary = self._generate_issue_summary(issues, security, performance)
        self.review_results["summary"] = issue_summary

        # 生成改进建议
        recommendations = self._generate_comprehensive_recommendations(
            issues, metrics, coverage, security, performance
        )
        self.review_results["recommendations"] = recommendations

        # 保存报告
        self._save_review_report()

    def _calculate_overall_quality_score(self, issues, metrics, coverage, security_issues):
        """计算总体质量评分"""
        base_score = 10.0

        # 根据问题数量扣分
        critical_issues = len([i for i in issues if i.severity == "critical"])
        high_issues = len([i for i in issues if i.severity == "high"])
        medium_issues = len([i for i in issues if i.severity == "medium"])

        base_score -= critical_issues * 2.0
        base_score -= high_issues * 1.0
        base_score -= medium_issues * 0.5

        # 根据安全性问题扣分
        critical_security = len([s for s in security_issues if s["severity"] == "critical"])
        high_security = len([s for s in security_issues if s["severity"] == "high"])

        base_score -= critical_security * 3.0
        base_score -= high_security * 1.5

        # 根据覆盖率调整
        if coverage["overall_coverage"] < self.review_rules["min_test_coverage"]:
            base_score -= 1.0

        # 根据复杂度调整
        if metrics["average_complexity"] > self.review_rules["complexity_threshold"]:
            base_score -= 1.0

        return max(0.0, min(10.0, base_score))

    def _generate_issue_summary(self, issues, security_issues, performance_issues):
        """生成问题摘要"""
        return {
            "total_issues": len(issues) + len(security_issues) + len(performance_issues),
            "by_severity": {
                "critical": len([i for i in issues if i.severity == "critical"])
                + len([s for s in security_issues if s["severity"] == "critical"]),
                "high": len([i for i in issues if i.severity == "high"])
                + len([s for s in security_issues if s["severity"] == "high"])
                + len([p for p in performance_issues if p["severity"] == "high"]),
                "medium": len([i for i in issues if i.severity == "medium"])
                + len([p for p in performance_issues if p["severity"] == "medium"]),
                "low": len([i for i in issues if i.severity == "low"])
                + len([p for p in performance_issues if p["severity"] == "low"]),
            },
            "by_type": {
                "complexity": len([i for i in issues if i.issue_type == "high_complexity"]),
                "security": len(security_issues),
                "performance": len(performance_issues),
                "style": len([i for i in issues if i.issue_type in ["long_line", "magic_number"]]),
            },
        }

    def _generate_comprehensive_recommendations(
        self, issues, metrics, coverage, duplication, security, performance
    ):
        """生成综合改进建议"""
        recommendations = [
            "🤖 基于Issue #98方法论：建议定期运行代码审查保持代码质量",
            "📊 质量门禁：将代码审查集成到CI/CD流水线中",
            "🔧 工具集成：与pre-commit钩子结合实现自动化检查",
        ]

        # 基于具体问题生成建议
        if coverage["overall_coverage"] < 15:
            recommendations.append("🧪 测试优先：优先提升测试覆盖率到15%以上")

        if metrics["average_complexity"] > 8:
            recommendations.append("🔄 重构建议：重点关注高复杂度函数的重构")

        if security_issues:
            recommendations.append("🔒 安全优先：立即修复所有关键和高优先级安全问题")

        if performance_issues:
            recommendations.append("⚡ 性能优化：优化识别出的性能瓶颈点")

        return recommendations

    def _save_review_report(self):
        """保存审查报告"""
        report_file = self.project_root / "automated_code_review_report.json"

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(self.review_results, f, indent=2, ensure_ascii=False)

            logger.info(f"代码审查报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"保存审查报告失败: {e}")

    def _severity_priority(self, severity: str) -> int:
        """获取严重程度优先级"""
        priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return priority_map.get(severity, 0)

    def print_review_summary(self):
        """打印审查摘要"""
        print("\n" + "=" * 60)
        print("📊 自动化代码审查摘要")
        print("=" * 60)

        # 质量评分
        score = self.review_results["quality_score"]
        score_emoji = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
        print(f"质量评分: {score_emoji} {score:.1f}/10")

        # 问题统计
        summary = self.review_results["summary"]
        print("\n📋 问题统计:")
        print(f"  总问题数: {summary['total_issues']}")
        for severity, count in summary["by_severity"].items():
            if count > 0:
                emoji = {"critical": "🚨", "high": "⚠️", "medium": "⭐", "low": "💡"}[severity]
                print(f"  {severity.upper()}: {emoji} {count}")

        # 指标信息
        metrics = self.review_results["metrics"]
        print("\n📈 代码指标:")
        print(f"  文件总数: {metrics['total_files']}")
        print(f"  代码行数: {metrics['total_lines']}")
        print(f"  函数数量: {metrics['total_functions']}")
        print(f"  平均复杂度: {metrics['average_complexity']:.1f}")

        # 关键建议
        if self.review_results["recommendations"]:
            print("\n💡 关键建议:")
            for rec in self.review_results["recommendations"][:5]:
                print(f"  {rec}")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AI驱动自动化代码审查系统")
    parser.add_argument("--project-root", type=Path, help="项目根目录")
    parser.add_argument(
        "--output-format", choices=["text", "json"], default="text", help="输出格式"
    )
    parser.add_argument("--severity-filter", help="过滤问题严重程度 (critical,high,medium,low)")

    args = parser.parse_args()

    reviewer = AutomatedCodeReviewer(args.project_root)

    # 运行审查
    results = reviewer.run_comprehensive_review()

    # 输出结果
    if args.output_format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        reviewer.print_review_summary()

    # 设置退出码
    if results["quality_score"] < 6.0:
        sys.exit(1)
    elif results["summary"]["by_severity"]["critical"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
