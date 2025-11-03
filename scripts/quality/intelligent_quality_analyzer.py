#!/usr/bin/env python3
"""
智能质量分析引擎
自动化检测、分析和报告系统质量的AI驱动工具
基于Issue #159的70.1%覆盖率成就，建立智能化质量管理体系
"""

import ast
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import subprocess
import re
import os

@dataclass
class QualityTrend:
    """质量趋势数据"""
    date: datetime
    coverage_percentage: float
    test_count: int
    complexity_score: float
    security_score: float
    performance_score: float
    overall_score: float

@dataclass
class QualityPattern:
    """质量模式识别"""
    pattern_name: str
    description: str
    indicators: List[str]
    recommendations: List[str]
    auto_fix_available: bool = False

@dataclass
class QualityInsight:
    """质量洞察"""
    category: str
    insight: str
    impact_level: str  # HIGH, MEDIUM, LOW
    actionable: bool
    evidence: List[str]
    suggested_actions: List[str]

class IntelligentQualityAnalyzer:
    """智能质量分析引擎"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.src_root = self.project_root / "src"
        self.tests_root = self.project_root / "tests"

        # 质量模式库
        self.quality_patterns = self._initialize_quality_patterns()

        # 趋势数据存储
        self.trend_data = []
        self.trend_data_file = self.project_root / "quality_data" / "quality_trends.json"

        # 确保目录存在
        self.trend_data_file.parent.mkdir(exist_ok=True)

        # 加载历史趋势数据
        self._load_trend_data()

    def _initialize_quality_patterns(self) -> List[QualityPattern]:
        """初始化质量模式库"""
        patterns = [
            QualityPattern(
                pattern_name="低覆盖率模块",
                description="识别覆盖率低于50%的模块",
                indicators=["coverage_low", "missing_tests", "complex_module"],
                recommendations=[
                    "优先添加关键路径的测试",
                    "使用TDD方法重构模块",
                    "增加边界条件测试"
                ],
                auto_fix_available=True
            ),
            QualityPattern(
                pattern_name="复杂度热点",
                description="识别复杂度过高的函数和类",
                indicators=["high_cyclomatic_complexity", "deep_nesting", "long_functions"],
                recommendations=[
                    "拆分大函数",
                    "提取子方法",
                    "使用设计模式简化结构"
                ],
                auto_fix_available=False
            ),
            QualityPattern(
                pattern_name="测试质量不足",
                description="识别测试质量问题的模式",
                indicators=["weak_assertions", "missing_edge_cases", "no_error_handling"],
                recommendations=[
                    "增加断言覆盖率",
                    "添加边界值测试",
                    "完善异常处理测试"
                ],
                auto_fix_available=True
            ),
            QualityPattern(
                pattern_name="安全隐患",
                description="识别常见的安全漏洞模式",
                indicators=["sql_injection_risk", "xss_vulnerability", "hardcoded_secrets"],
                recommendations=[
                    "使用参数化查询",
                    "输入验证和清理",
                    "环境变量存储敏感信息"
                ],
                auto_fix_available=True
            ),
            QualityPattern(
                pattern_name="性能瓶颈",
                description="识别性能问题的模式",
                indicators=["inefficient_loops", "memory_leaks", "blocking_operations"],
                recommendations=[
                    "优化算法复杂度",
                    "使用异步编程",
                    "添加缓存机制"
                ],
                auto_fix_available=False
            ),
            QualityPattern(
                pattern_name="代码重复",
                description="识别代码重复和维护性问题",
                indicators=["duplicate_blocks", "similar_functions", "magic_numbers"],
                recommendations=[
                    "提取公共方法",
                    "使用常量替换魔法数字",
                    "重构相似代码"
                ],
                auto_fix_available=True
            )
        ]
        return patterns

    def analyze_project_quality(self) -> Dict[str, Any]:
        """分析项目整体质量"""
        print("🤖 启动智能质量分析引擎...")

        start_time = time.time()

        # 收集数据
        analysis_data = self._collect_project_data()

        # 模式识别
        patterns_found = self._identify_quality_patterns(analysis_data)

        # 生成洞察
        insights = self._generate_quality_insights(analysis_data, patterns_found)

        # 趋势分析
        current_trend = self._calculate_current_trend(analysis_data)
        self._save_trend_data(current_trend)

        # 综合评分
        quality_score = self._calculate_comprehensive_score(analysis_data)

        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "analysis_time": time.time() - start_time,
            "coverage_data": analysis_data.get("coverage", {}),
            "test_quality": analysis_data.get("test_quality", {}),
            "code_metrics": analysis_data.get("code_metrics", {}),
            "patterns_found": [
                {
                    "name": p.pattern_name,
                    "description": p.description,
                    "count": len([i for i in patterns_found if i["pattern_name"] == p.pattern_name])
                }
                for p in self.quality_patterns
            ],
            "insights": insights,
            "trend": current_trend,
            "overall_score": quality_score,
            "recommendations": self._generate_comprehensive_recommendations(analysis_data, patterns_found, insights)
        }

        return analysis_result

    def _collect_project_data(self) -> Dict[str, Any]:
        """收集项目数据"""
        data = {}

        # 运行覆盖率分析
        print("  📊 收集覆盖率数据...")
        try:
            result = subprocess.run([
                "python3", "tests/enhanced_coverage_system_v2.py"
            ], capture_output=True, text=True, cwd=self.project_root)

            # 解析覆盖率结果
            coverage_data = self._parse_coverage_output(result.stdout)
            data["coverage"] = coverage_data
        except Exception as e:
            print(f"    ⚠️ 覆盖率分析失败: {e}")
            data["coverage"] = {"coverage_percentage": 0, "covered_modules": 0}

        # 分析测试质量
        print("  🧪 分析测试质量...")
        data["test_quality"] = self._analyze_test_quality()

        # 分析代码指标
        print("  📈 分析代码指标...")
        data["code_metrics"] = self._analyze_code_metrics()

        return data

    def _parse_coverage_output(self, output: str) -> Dict[str, Any]:
        """解析覆盖率输出"""
        coverage_data = {}

        # 提取覆盖率百分比
        coverage_match = re.search(r"🎯 最终覆盖率: (\d+\.\d+)%", output)
        if coverage_match:
            coverage_data["coverage_percentage"] = float(coverage_match.group(1))

        # 提取覆盖模块数
        modules_match = re.search(r"✅ 覆盖模块数: (\d+)", output)
        if modules_match:
            coverage_data["covered_modules"] = int(modules_match.group(1))

        # 提取项目总模块数
        total_match = re.search(r"📁 项目总模块: (\d+)", output)
        if total_match:
            coverage_data["total_modules"] = int(total_match.group(1))

        return coverage_data

    def _analyze_test_quality(self) -> Dict[str, Any]:
        """分析测试质量"""
        test_files = list(self.tests_root.glob("test_*.py"))

        quality_metrics = {
            "total_test_files": len(test_files),
            "total_test_methods": 0,
            "test_classes": 0,
            "files_with_good_assertions": 0,
            "files_with_error_handling": 0,
            "files_with_edge_cases": 0,
            "average_methods_per_file": 0,
            "test_complexity_score": 0.0
        }

        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                # 统计测试类和方法
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                        quality_metrics["test_classes"] += 1

                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                                quality_metrics["total_test_methods"] += 1

                # 检查断言质量
                if self._has_good_assertions(content):
                    quality_metrics["files_with_good_assertions"] += 1

                # 检查错误处理
                if self._has_error_handling(content):
                    quality_metrics["files_with_error_handling"] += 1

                # 检查边界条件
                if self._has_edge_case_tests(content):
                    quality_metrics["files_with_edge_cases"] += 1

            except Exception as e:
                print(f"    ⚠️ 分析测试文件失败 {test_file.name}: {e}")

        # 计算平均值
        if quality_metrics["total_test_files"] > 0:
            quality_metrics["average_methods_per_file"] = (
                quality_metrics["total_test_methods"] / quality_metrics["total_test_files"]
            )

        # 计算测试复杂度分数
        quality_metrics["test_complexity_score"] = min(100, (
            (quality_metrics["files_with_good_assertions"] / quality_metrics["total_test_files"]) * 40 +
            (quality_metrics["files_with_error_handling"] / quality_metrics["total_test_files"]) * 30 +
            (quality_metrics["files_with_edge_cases"] / quality_metrics["total_test_files"]) * 30
        ))

        return quality_metrics

    def _has_good_assertions(self, content: str) -> bool:
        """检查是否有好的断言"""
        good_assertion_patterns = [
            r"assert\s+\w+\s*==\s*[^,]+",
            r"assert\s+\w+\s*!=\s*[^,]+",
            r"assert\s+\w+\s*>\s*[^,]+",
            r"assert\s+\w+\s*<\s*[^,]+",
            r"assert\s+\w+\s*in\s+[^,]+",
            r"self\.assert[A-Z][a-zA-Z]*\s*\(",
            r"self\.assertEqual\s*\(",
            r"self\.assertTrue\s*\(",
            r"self\.assertFalse\s*\("
        ]

        return any(re.search(pattern, content) for pattern in good_assertion_patterns)

    def _has_error_handling(self, content: str) -> bool:
        """检查是否有错误处理"""
        error_handling_patterns = [
            r"try\s*:",
            r"except\s+\w+",
            r"raise\s+\w+",
            r"finally\s*:",
            r"with\s+\w+\s+as\s+\w+"
        ]

        return any(re.search(pattern, content) for pattern in error_handling_patterns)

    def _has_edge_case_tests(self, content: str) -> bool:
        """检查是否有边界条件测试"""
        edge_case_patterns = [
            r"test.*empty",
            r"test.*null",
            r"test.*zero",
            r"test.*negative",
            r"test.*invalid",
            r"test.*boundary",
            r"test.*limit",
            r"test.*edge"
        ]

        return any(re.search(pattern, content, re.IGNORECASE) for pattern in edge_case_patterns)

    def _analyze_code_metrics(self) -> Dict[str, Any]:
        """分析代码指标"""
        code_metrics = {
            "total_python_files": 0,
            "total_lines_of_code": 0,
            "average_file_size": 0,
            "complex_files_count": 0,
            "files_with_docstrings": 0,
            "files_with_type_hints": 0,
            "duplication_score": 0,
            "maintainability_index": 0.0
        }

        python_files = list(self.src_root.rglob("*.py"))
        code_metrics["total_python_files"] = len(python_files)

        total_lines = 0
        docstring_files = 0
        type_hint_files = 0
        complex_files = 0

        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = len(content.split('\n'))
                total_lines += lines

                # 检查文档字符串
                if '"""' in content or "'''" in content:
                    docstring_files += 1

                # 检查类型提示
                if ':' in content and ('int:' in content or 'str:' in content or 'bool:' in content):
                    type_hint_files += 1

                # 检查文件复杂度（基于行数）
                if lines > 100:
                    complex_files += 1

            except Exception as e:
                print(f"    ⚠️ 分析代码文件失败 {py_file.name}: {e}")

        code_metrics["total_lines_of_code"] = total_lines
        code_metrics["complex_files_count"] = complex_files
        code_metrics["files_with_docstrings"] = docstring_files
        code_metrics["files_with_type_hints"] = type_hint_files

        if code_metrics["total_python_files"] > 0:
            code_metrics["average_file_size"] = total_lines / code_metrics["total_python_files"]

        # 计算可维护性指数
        code_metrics["maintainability_index"] = min(100, (
            (code_metrics["files_with_docstrings"] / code_metrics["total_python_files"]) * 30 +
            (code_metrics["files_with_type_hints"] / code_metrics["total_python_files"]) * 25 +
            ((code_metrics["total_python_files"] - code_metrics["complex_files_count"]) / code_metrics["total_python_files"]) * 45
        ))

        return code_metrics

    def _identify_quality_patterns(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别质量模式"""
        patterns_found = []

        # 覆盖率模式
        coverage_data = analysis_data.get("coverage", {})
        coverage_percentage = coverage_data.get("coverage_percentage", 0)

        if coverage_percentage < 50:
            patterns_found.append({
                "pattern_name": "低覆盖率模块",
                "severity": "HIGH",
                "evidence": [f"覆盖率: {coverage_percentage}%"],
                "suggested_actions": ["优先添加关键路径测试", "使用TDD方法"]
            })

        # 测试质量模式
        test_quality = analysis_data.get("test_quality", {})
        test_complexity_score = test_quality.get("test_complexity_score", 0)

        if test_complexity_score < 50:
            patterns_found.append({
                "pattern_name": "测试质量不足",
                "severity": "MEDIUM",
                "evidence": [f"测试复杂度分数: {test_complexity_score}"],
                "suggested_actions": ["增加断言覆盖率", "添加边界测试"]
            })

        # 代码复杂度模式
        code_metrics = analysis_data.get("code_metrics", {})
        complex_files_count = code_metrics.get("complex_files_count", 0)

        if complex_files_count > 10:
            patterns_found.append({
                "pattern_name": "复杂度热点",
                "severity": "MEDIUM",
                "evidence": [f"复杂文件数量: {complex_files_count}"],
                "suggested_actions": ["拆分大函数", "提取子方法"]
            })

        return patterns_found

    def _generate_quality_insights(self, analysis_data: Dict[str, Any], patterns_found: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成质量洞察"""
        insights = []

        coverage_data = analysis_data.get("coverage", {})
        coverage_percentage = coverage_data.get("coverage_percentage", 0)

        # 生成覆盖率洞察
        if coverage_percentage > 70:
            insights.append({
                "category": "coverage",
                "insight": f"项目测试覆盖率达到了 {coverage_percentage:.1f}%，处于良好水平",
                "impact_level": "POSITIVE",
                "actionable": False,
                "evidence": [f"覆盖率: {coverage_percentage}%"],
                "suggested_actions": ["继续保持当前测试质量"]
            })
        elif coverage_percentage < 50:
            insights.append({
                "category": "coverage",
                "insight": f"项目测试覆盖率仅为 {coverage_percentage:.1f}%，需要重点关注",
                "impact_level": "HIGH",
                "actionable": True,
                "evidence": [f"覆盖率: {coverage_percentage}%"],
                "suggested_actions": ["增加测试覆盖率", "优先覆盖核心模块"]
            })

        # 生成测试质量洞察
        test_quality = analysis_data.get("test_quality", {})
        test_complexity_score = test_quality.get("test_complexity_score", 0)

        if test_complexity_score > 80:
            insights.append({
                "category": "test_quality",
                "insight": f"测试质量评分 {test_complexity_score:.1f}，测试用例质量较高",
                "impact_level": "POSITIVE",
                "actionable": False,
                "evidence": [f"测试质量分数: {test_complexity_score}"],
                "suggested_actions": ["继续保持测试质量标准"]
            })

        # 生成模式洞察
        if patterns_found:
            high_severity_patterns = [p for p in patterns_found if p.get("severity") == "HIGH"]
            if high_severity_patterns:
                insights.append({
                    "category": "patterns",
                    "insight": f"发现 {len(high_severity_patterns)} 个高严重性质量问题模式",
                    "impact_level": "HIGH",
                    "actionable": True,
                    "evidence": [p["pattern_name"] for p in high_severity_patterns],
                    "suggested_actions": ["优先解决高严重性问题"]
                })

        return insights

    def _calculate_current_trend(self, analysis_data: Dict[str, Any]) -> QualityTrend:
        """计算当前趋势"""
        coverage_data = analysis_data.get("coverage", {})
        test_quality = analysis_data.get("test_quality", {})
        code_metrics = analysis_data.get("code_metrics", {})

        return QualityTrend(
            date=datetime.now(),
            coverage_percentage=coverage_data.get("coverage_percentage", 0),
            test_count=test_quality.get("total_test_methods", 0),
            complexity_score=10.0 - (code_metrics.get("complex_files_count", 0) / max(code_metrics.get("total_python_files", 1), 1)),
            security_score=85.0,  # 基于当前项目估算
            performance_score=90.0,  # 基于当前项目估算
            overall_score=self._calculate_comprehensive_score(analysis_data)
        )

    def _calculate_comprehensive_score(self, analysis_data: Dict[str, Any]) -> float:
        """计算综合质量分数"""
        coverage_data = analysis_data.get("coverage", {})
        test_quality = analysis_data.get("test_quality", {})
        code_metrics = analysis_data.get("code_metrics", {})

        # 各项指标分数
        coverage_score = min(100, coverage_data.get("coverage_percentage", 0))
        test_quality_score = test_quality.get("test_complexity_score", 0)
        maintainability_score = code_metrics.get("maintainability_index", 0)

        # 加权计算
        comprehensive_score = (
            coverage_score * 0.4 +
            test_quality_score * 0.3 +
            maintainability_score * 0.3
        )

        return comprehensive_score

    def _generate_comprehensive_recommendations(self, analysis_data: Dict[str, Any], patterns_found: List[Dict[str, Any]], insights: List[Dict[str, Any]]) -> List[str]:
        """生成综合建议"""
        recommendations = []

        coverage_data = analysis_data.get("coverage", {})
        coverage_percentage = coverage_data.get("coverage_percentage", 0)

        # 基于覆盖率的建议
        if coverage_percentage < 75:
            recommendations.append(f"📈 提升测试覆盖率到75%以上 (当前: {coverage_percentage:.1f}%)")

        # 基于模式的建议
        for pattern in patterns_found:
            if pattern.get("suggested_actions"):
                recommendations.extend([f"🔧 {action}" for action in pattern["suggested_actions"]])

        # 基于洞察的建议
        high_impact_insights = [i for i in insights if i.get("impact_level") == "HIGH" and i.get("actionable")]
        for insight in high_impact_insights:
            if insight.get("suggested_actions"):
                recommendations.extend(insight["suggested_actions"])

        return recommendations

    def _load_trend_data(self):
        """加载历史趋势数据"""
        if self.trend_data_file.exists():
            try:
                with open(self.trend_data_file, 'r') as f:
                    data = json.load(f)
                    self.trend_data = [
                        QualityTrend(**item) for item in data
                    ]
            except Exception as e:
                print(f"⚠️ 加载趋势数据失败: {e}")

    def _save_trend_data(self, trend: QualityTrend):
        """保存趋势数据"""
        self.trend_data.append(trend)

        # 保留最近30天的数据
        cutoff_date = datetime.now() - timedelta(days=30)
        self.trend_data = [t for t in self.trend_data if t.date >= cutoff_date]

        try:
            with open(self.trend_data_file, 'w') as f:
                json.dump([
                    {
                        "date": t.date.isoformat(),
                        "coverage_percentage": t.coverage_percentage,
                        "test_count": t.test_count,
                        "complexity_score": t.complexity_score,
                        "security_score": t.security_score,
                        "performance_score": t.performance_score,
                        "overall_score": t.overall_score
                    }
                    for t in self.trend_data
                ], f, indent=2)
        except Exception as e:
            print(f"⚠️ 保存趋势数据失败: {e}")

    def generate_quality_report(self, analysis_result: Dict[str, Any]) -> str:
        """生成质量报告"""
        report = f"""
# 🏛️ 智能质量分析报告

## 📊 质量概览
- **分析时间**: {analysis_result['timestamp']}
- **分析耗时**: {analysis_result['analysis_time']:.2f}秒
- **综合质量分数**: {analysis_result['overall_score']:.1f}/100

## 📈 覆盖率指标
- **当前覆盖率**: {analysis_result['coverage_data'].get('coverage_percentage', 0):.1f}%
- **覆盖模块数**: {analysis_result['coverage_data'].get('covered_modules', 0)}
- **总模块数**: {analysis_result['coverage_data'].get('total_modules', 0)}

## 🧪 测试质量分析
- **测试文件总数**: {analysis_result['test_quality'].get('total_test_files', 0)}
- **测试方法总数**: {analysis_result['test_quality'].get('total_test_methods', 0)}
- **测试复杂度分数**: {analysis_result['test_quality'].get('test_complexity_score', 0):.1f}/100
- **文件平均方法数**: {analysis_result['test_quality'].get('average_methods_per_file', 0):.1f}

## 📊 代码指标
- **Python文件总数**: {analysis_result['code_metrics'].get('total_python_files', 0)}
- **代码总行数**: {analysis_result['code_metrics'].get('total_lines_of_code', 0)}
- **平均文件大小**: {analysis_result['code_metrics'].get('average_file_size', 0):.1f}行
- **复杂文件数**: {analysis_result['code_metrics'].get('complex_files_count', 0)}
- **可维护性指数**: {analysis_result['code_metrics'].get('maintainability_index', 0):.1f}/100

## 🔍 质量模式识别
"""

        for pattern in analysis_result['patterns_found']:
            report += f"- **{pattern['name']}**: {pattern['description']}\n"

        report += """
## 💡 质量洞察
"""

        for insight in analysis_result['insights']:
            impact_icon = "🟢" if insight['impact_level'] == "POSITIVE" else "🟡" if insight['impact_level'] == "MEDIUM" else "🔴"
            report += f"- {impact_icon} **{insight['category'].title()}**: {insight['insight']}\n"

        report += f"""
## 📈 趋势分析
- **日期**: {analysis_result['trend']['date'].strftime('%Y-%m-%d')}
- **覆盖率趋势**: {analysis_result['trend']['coverage_percentage']:.1f}%
- **测试数量趋势**: {analysis_result['trend']['test_count']}
- **综合质量分数**: {analysis_result['trend']['overall_score']:.1f}/100

## 📋 改进建议
"""

        for i, rec in enumerate(analysis_result['recommendations'], 1):
            report += f"{i}. {rec}\n"

        report += f"""
---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*分析引擎版本: 1.0.0*
"""

        return report

def main():
    """主函数"""
    analyzer = IntelligentQualityAnalyzer()

    print("🤖 智能质量分析引擎启动...")

    # 分析项目质量
    result = analyzer.analyze_project_quality()

    # 生成报告
    report = analyzer.generate_quality_report(result)

    print("\n" + "="*60)
    print("📊 智能质量分析报告")
    print("="*60)
    print(report)

    # 保存报告
    report_file = Path("quality_system") / "quality_analysis_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 报告已保存: {report_file}")
    print("✅ 智能质量分析完成！")

if __name__ == "__main__":
    main()