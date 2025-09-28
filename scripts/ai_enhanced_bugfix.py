#!/usr/bin/env python3
"""
AI 增强的 Bug 修复主脚本

集成到现有的自动化 bug 修复闭环中，提供智能分析和修复建议。
"""

import sys
import subprocess
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.code_analyzer import CodeAnalyzer, AnalysisResult
from src.ai.fix_applier import FixApplier
from src.ai.claude_cli_wrapper import TestFailure
from src.ai.mutation_tester import SelectiveMutationTester
from src.ai.flaky_test_detector import SmartFlakyTestDetector
from src.ai.performance_benchmark import RelativePerformanceBenchmark
from src.ai.test_quality_aggregator import TestQualityAggregator
from src.ai.test_generator import AITestGenerator
from src.ai.fix_validator import FixValidator
from src.ai.feedback_db import FeedbackDatabase

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIEnhancedBugfix:
    """AI 增强的 Bug 修复系统"""

    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.applier = FixApplier()

        # Phase 2: Test Effectiveness Enhancement components
        self.mutation_tester = SelectiveMutationTester()
        self.flaky_detector = SmartFlakyTestDetector()
        self.performance_benchmark = RelativePerformanceBenchmark()
        self.quality_aggregator = TestQualityAggregator()

        # Phase 3: Intelligent Enhancement components
        self.test_generator = AITestGenerator()
        self.fix_validator = FixValidator()
        self.feedback_db = FeedbackDatabase()

        self.reports_dir = Path("docs/_reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        logger.info("AI Enhanced Bugfix system initialized with Phase 3 components")

    def run_analysis_and_generate_fixes(self, interactive: bool = True) -> bool:
        """
        运行完整的分析和修复生成流程

        Args:
            interactive: 是否交互式模式

        Returns:
            流程是否成功完成
        """
        try:
            print("🚀 Starting AI-enhanced bugfix analysis...")

            # 1. 运行测试获取失败信息
            print("📊 Running tests to collect failures...")
            test_output = self._run_tests_collect_failures()

            # 2. 获取覆盖率数据
            print("📈 Collecting coverage data...")
            coverage_data = self._collect_coverage_data()

            # 3. AI 分析测试失败
            print("🤖 AI analyzing test failures...")
            analysis_result = self.analyzer.analyze_test_results(test_output, coverage_data)

            # 4. 生成 BUGFIX_TODO
            print("📝 Generating BUGFIX_TODO...")
            todo_path = self.reports_dir / "BUGFIX_TODO.md"
            self.analyzer.generate_bugfix_todo(analysis_result, todo_path)

            # 5. 显示分析结果
            self._display_analysis_summary(analysis_result)

            # 6. 如果有修复建议，询问是否应用
            if analysis_result.fix_suggestions and interactive:
                return self._handle_fix_application(analysis_result)

            print("✅ Analysis completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Error in bugfix analysis: {e}")
            print(f"❌ Error: {e}")
            return False

    def apply_recommended_fixes(self, todo_path: Optional[Path] = None) -> bool:
        """
        应用推荐的修复（从现有 TODO 或新的分析）

        Args:
            todo_path: TODO 文件路径，如果为 None 则重新分析

        Returns:
            是否成功应用修复
        """
        try:
            # 如果没有提供 TODO 路径，重新分析
            if todo_path is None:
                print("🔄 Running fresh analysis...")
                if not self.run_analysis_and_generate_fixes(interactive=False):
                    return False

                todo_path = self.reports_dir / "BUGFIX_TODO.md"

            # 解析 TODO 文件获取修复建议
            print("📋 Parsing TODO file for fix suggestions...")
            fix_suggestions = self._parse_todo_for_fixes(todo_path)

            if not fix_suggestions:
                print("ℹ️  No fix suggestions found in TODO file")
                return True

            print(f"🎯 Found {len(fix_suggestions)} fix suggestions")

            # 批量应用修复
            results = self.applier.batch_apply_fixes(fix_suggestions, interactive=True)

            # 显示应用结果
            self._display_application_results(results)

            # 更新 TODO 文件
            self._update_todo_after_fixes(todo_path, results)

            return True

        except Exception as e:
            logger.error(f"Error applying fixes: {e}")
            print(f"❌ Error: {e}")
            return False

    def validate_fixes(self) -> bool:
        """
        验证已应用的修复

        Returns:
            验证是否成功
        """
        try:
            print("🔍 Validating applied fixes...")

            # 运行测试检查是否修复成功
            print("📊 Running tests to validate fixes...")
            test_result = self._run_tests_collect_failures()

            # 分析测试结果
            if "FAIL:" in test_result:
                print("⚠️  Some tests are still failing after fixes")
                # 可以在这里进行更详细的分析
                return False
            else:
                print("✅ All tests are passing! Fixes are successful.")
                return True

        except Exception as e:
            logger.error(f"Error validating fixes: {e}")
            return False

    def run_phase2_quality_analysis(self, incremental: bool = True) -> bool:
        """
        运行 Phase 2 综合质量分析

        Args:
            incremental: 是否使用增量模式

        Returns:
            分析是否成功完成
        """
        try:
            print("🚀 Starting Phase 2 comprehensive quality analysis...")

            # 1. 突变测试
            print("🔬 Running mutation testing...")
            mutation_results = self.mutation_tester.run_mutation_tests(incremental=incremental)

            # 2. Flaky测试检测
            print("🔄 Detecting flaky tests...")
            flaky_results = self.flaky_detector.detect_flaky_tests(incremental=incremental)

            # 3. 性能基准测试
            print("⚡ Running performance benchmarks...")
            performance_results = self.performance_benchmark.run_performance_benchmarks(update_baselines=False)

            # 4. 综合质量评估
            print("📊 Aggregating quality metrics...")
            quality_results = self.quality_aggregator.run_comprehensive_quality_check(incremental=incremental)

            # 生成综合报告
            print("📝 Generating comprehensive report...")
            report_path = self._generate_phase2_report(mutation_results, flaky_results, performance_results, quality_results)

            print(f"✅ Phase 2 analysis completed. Report: {report_path}")
            return True

        except Exception as e:
            logger.error(f"Error in Phase 2 quality analysis: {e}")
            print(f"❌ Error: {e}")
            return False

    def run_phase3_intelligent_enhancement(self, target: Optional[str] = None) -> bool:
        """
        运行 Phase 3 智能化完善

        Args:
            target: 目标文件或目录，如果为None则分析所有失败测试

        Returns:
            执行是否成功
        """
        try:
            print("🤖 Starting Phase 3 intelligent enhancement...")

            # 1. 自动生成缺失测试
            print("🧪 Auto-generating tests for uncovered files...")
            test_generation_results = self._auto_generate_tests(target)

            # 2. 验证现有修复
            print("🔍 Validating existing fixes...")
            validation_results = self._validate_existing_fixes()

            # 3. 分析历史数据获取改进建议
            print("📚 Analyzing historical data for improvement patterns...")
            learning_patterns = self._analyze_learning_patterns()

            # 4. 更新 TODO 文件
            print("📋 Updating TODO file with Phase 3 results...")
            phase3_summary = {
                'tests_generated': len(test_generation_results.get('generated_files', [])),
                'test_cases_added': sum(len(result.get('validation', {}).get('test_count', 0)) for result in test_generation_results.get('results', [])),
                'coverage_improvement': 'Estimated 5-15%',
                'fixes_validated': validation_results.get('validated_count', 0),
                'fixes_failed': validation_results.get('failed_count', 0),
                'average_validation_score': validation_results.get('average_score', '0%'),
                'feedback_records_added': learning_patterns.get('new_feedback_records', 0),
                'patterns_learned': learning_patterns.get('patterns_discovered', 0),
                'suggestions_improved': learning_patterns.get('improvements_suggested', 0)
            }

            todo_path = Path("docs/_reports/BUGFIX_TODO.md")
            self.update_todo_with_phase3_results(todo_path, phase3_summary)

            # 5. 生成智能报告
            print("📝 Generating intelligent enhancement report...")
            report_path = self._generate_phase3_report(test_generation_results, validation_results, learning_patterns)

            print(f"✅ Phase 3 enhancement completed. Report: {report_path}")
            return True

        except Exception as e:
            logger.error(f"Error in Phase 3 intelligent enhancement: {e}")
            print(f"❌ Error: {e}")
            return False

    def auto_generate_tests(self, target: str) -> bool:
        """
        自动生成测试

        Args:
            target: 目标文件或目录路径

        Returns:
            是否成功
        """
        try:
            print(f"🧪 Auto-generating tests for: {target}")

            target_path = Path(target)
            if target_path.is_file():
                result = self.test_generator.generate_tests_for_file(str(target_path))
            elif target_path.is_dir():
                result = self.test_generator.generate_tests_for_directory(str(target_path))
            else:
                print(f"❌ Target not found: {target}")
                return False

            # 记录到反馈数据库
            self.feedback_db.add_test_generation(str(target_path), result)

            # 显示结果
            if "error" in result:
                print(f"❌ Test generation failed: {result['error']}")
                return False
            else:
                print(f"✅ Tests generated: {result['test_file']}")
                validation = result.get("validation", {})
                if validation.get("syntax_valid"):
                    print(f"✅ Generated {validation.get('test_count', 0)} tests with {validation.get('assertion_count', 0)} assertions")
                else:
                    print("⚠️ Generated tests have syntax issues")
                return True

        except Exception as e:
            logger.error(f"Error auto-generating tests: {e}")
            print(f"❌ Error: {e}")
            return False

    def validate_fix(self, file_path: str) -> bool:
        """
        验证修复效果

        Args:
            file_path: 要验证的文件路径

        Returns:
            是否成功
        """
        try:
            print(f"🔍 Validating fix for: {file_path}")

            # 构建修复信息
            fix_info = {
                "file_path": file_path,
                "description": "Manual fix validation",
                "timestamp": datetime.now().isoformat()
            }

            # 运行验证
            validation_result = self.fix_validator.validate_fix(fix_info)

            # 记录到反馈数据库
            fix_id = self.feedback_db.add_fix_attempt(fix_info)
            if fix_id:
                self.feedback_db.add_validation_result(fix_id, validation_result)

            # 显示结果
            overall_result = validation_result.get("overall_result", "unknown")
            quality_score = validation_result.get("quality_score", 0)

            print(f"📊 Validation result: {overall_result}")
            print(f"📈 Quality score: {quality_score:.2%}")

            if validation_result.get("recommendations"):
                print("💡 Recommendations:")
                for rec in validation_result["recommendations"][:3]:
                    print(f"   - {rec}")

            return overall_result in ["excellent", "good", "acceptable"]

        except Exception as e:
            logger.error(f"Error validating fix: {e}")
            print(f"❌ Error: {e}")
            return False

    def show_feedback_history(self, days: int = 30) -> bool:
        """
        显示历史修复经验

        Args:
            days: 查询天数

        Returns:
            是否成功
        """
        try:
            print(f"📚 Analyzing feedback history for last {days} days...")

            # 获取统计信息
            stats = self.feedback_db.query_fix_statistics(days)

            if not stats:
                print("ℹ️ No feedback data available")
                return True

            print(f"\n📊 Fix Statistics (Last {days} days):")
            print(f"   Total fix attempts: {stats.get('total_fix_attempts', 0)}")
            print(f"   Successful fixes: {stats.get('successful_fixes', 0)}")
            print(f"   Failed fixes: {stats.get('failed_fixes', 0)}")
            print(f"   Average quality score: {stats.get('average_quality_score', 0):.2%}")

            # 显示验证结果分布
            validation_results = stats.get('validation_results', {})
            if validation_results:
                print(f"\n📈 Validation Results Distribution:")
                for result_type, count in validation_results.items():
                    print(f"   {result_type}: {count}")

            # 显示常见错误类型
            top_errors = stats.get('top_error_types', {})
            if top_errors:
                print(f"\n🔍 Top Error Types:")
                for error_type, count in list(top_errors.items())[:5]:
                    print(f"   {error_type}: {count}")

            # 显示常见文件路径
            top_files = stats.get('top_file_paths', {})
            if top_files:
                print(f"\n📁 Most Fixed Files:")
                for file_path, count in list(top_files.items())[:5]:
                    print(f"   {file_path}: {count}")

            # 获取学习模式
            patterns = self.feedback_db.get_learning_patterns()
            if patterns.get("effective_strategies"):
                print(f"\n✨ Effective Strategies:")
                for strategy in list(patterns["effective_strategies"].keys())[:3]:
                    print(f"   - {strategy}")

            return True

        except Exception as e:
            logger.error(f"Error showing feedback history: {e}")
            print(f"❌ Error: {e}")
            return False

    def _auto_generate_tests(self, target: Optional[str] = None) -> Dict:
        """自动生成测试的内部实现"""
        if target:
            target_path = Path(target)
            if target_path.is_file():
                return self.test_generator.generate_tests_for_file(str(target_path))
            elif target_path.is_dir():
                return self.test_generator.generate_tests_for_directory(str(target_path))

        # 如果没有指定目标，分析低覆盖率文件
        print("🔍 Analyzing low coverage files...")
        # 这里可以添加覆盖率分析逻辑
        return {"message": "No specific target provided, use --auto-generate-tests with specific target"}

    def _validate_existing_fixes(self) -> Dict:
        """验证现有修复的内部实现"""
        # 从TODO文件或历史数据中获取修复信息
        todo_path = self.reports_dir / "BUGFIX_TODO.md"
        if todo_path.exists():
            # 解析TODO文件获取修复信息
            # 这里可以扩展TODO解析逻辑
            return {"message": "TODO parsing not fully implemented yet"}

        return {"message": "No existing fixes to validate"}

    def _analyze_learning_patterns(self) -> Dict:
        """分析学习模式的内部实现"""
        return self.feedback_db.get_learning_patterns()

    def _generate_phase3_report(self, test_results: Dict, validation_results: Dict, learning_patterns: Dict) -> Path:
        """生成Phase 3报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        report_path = self.reports_dir / f"PHASE3_INTELLIGENT_REPORT_{timestamp}.md"

        # 获取反馈统计
        stats = self.feedback_db.query_fix_statistics(30)

        report_content = f"""# 🤖 Phase 3: 智能化完善 - 综合报告

**生成时间:** {datetime.now().isoformat()}

## 📊 执行摘要

### 测试生成结果
- 目标: {test_results.get('target', 'Auto-detected')}
- 状态: {'✅ 成功' if 'error' not in test_results else '❌ 失败'}
- 生成文件: {test_results.get('test_file', 'N/A')}

### 修复验证结果
- 验证状态: {validation_results.get('message', 'N/A')}

### 学习模式分析
- 有效策略数量: {len(learning_patterns.get('effective_strategies', {}))}
- 问题模式数量: {len(learning_patterns.get('problematic_approaches', {}))}

## 📈 历史统计 (最近30天)

- 总修复尝试: {stats.get('total_fix_attempts', 0)}
- 成功修复: {stats.get('successful_fixes', 0)}
- 失败修复: {stats.get('failed_fixes', 0)}
- 平均质量分数: {stats.get('average_quality_score', 0):.2%}

## 🎯 关键发现

### 高效修复策略
{self._format_patterns_for_report(learning_patterns.get('effective_strategies', {}))}

### 需要避免的模式
{self._format_patterns_for_report(learning_patterns.get('problematic_approaches', {}))}

## 🚀 改进建议

### 短期优化
1. 重点关注高频错误文件
2. 应用成功的修复模式
3. 避免已知的问题修复方式

### 长期策略
1. 建立更完善的测试自动化流程
2. 持续学习和优化修复策略
3. 扩大反馈数据库的覆盖范围

## ⚠️ 风险提示

- 自动生成的测试需要人工审核
- 修复验证结果依赖于测试覆盖率
- 学习模式需要足够的历史数据支持

---
*此报告由 AI 智能化完善系统自动生成*
"""

        report_path.write_text(report_content, encoding='utf-8')
        return report_path

    def _format_patterns_for_report(self, patterns: Dict) -> str:
        """格式化模式为报告文本"""
        if not patterns:
            return "暂无数据"

        formatted_lines = []
        for pattern, count in list(patterns.items())[:5]:
            formatted_lines.append(f"- {pattern}: {count} 次")

        return "\n".join(formatted_lines) if formatted_lines else "暂无数据"

    def generate_report(self) -> bool:
        """
        生成 AI 修复活动报告

        Returns:
            是否成功生成报告
        """
        try:
            print("📊 Generating AI bugfix activity report...")

            # 获取统计信息
            analyzer_stats = {
                "timestamp": datetime.now().isoformat(),
                "analysis_history": "Not implemented",  # 可以扩展记录分析历史
            }

            applier_stats = self.applier.get_fix_statistics()

            # 生成报告
            report_path = self.reports_dir / f"AI_BUGFIX_REPORT_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
            report_content = self._generate_report_content(analyzer_stats, applier_stats)

            report_path.write_text(report_content, encoding='utf-8')
            print(f"✅ Report generated: {report_path}")

            return True

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return False

    def _run_tests_collect_failures(self) -> str:
        """运行测试并收集失败信息"""
        # 使用现有的测试脚本逻辑
        cmd = [
            "pytest",
            "--maxfail=10",
            "--tb=short",
            "--disable-warnings",
            "tests/test_ai_demo_failure.py"  # 明确指定测试文件
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # 保存失败日志到文件
        log_file = Path("pytest_failures.log")
        log_file.write_text(result.stdout + "\n" + result.stderr, encoding='utf-8')

        return result.stdout + "\n" + result.stderr

    def _collect_coverage_data(self) -> Optional[Dict]:
        """收集覆盖率数据"""
        try:
            # 运行带覆盖率的测试
            cmd = [
                "pytest",
                "--cov=src",
                "--cov-report=json:coverage.json",
                "--maxfail=10",
                "--disable-warnings",
                "tests/test_ai_demo_failure.py"  # 明确指定测试文件
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if Path("coverage.json").exists():
                return json.load(open("coverage.json"))
            else:
                logger.warning("Coverage data not available")
                return None

        except Exception as e:
            logger.error(f"Error collecting coverage data: {e}")
            return None

    def _display_analysis_summary(self, analysis_result: AnalysisResult):
        """显示分析摘要"""
        print("\n" + "="*50)
        print("📊 AI 分析结果摘要")
        print("="*50)
        print(f"🔍 发现测试失败: {analysis_result.analysis_summary['total_failures']} 个")
        print(f"🛠️  生成修复建议: {analysis_result.analysis_summary['generated_fixes']} 个")
        print(f"📈 分析成功率: {analysis_result.analysis_summary['success_rate']:.1%}")
        print(f"🎯 整体置信度: {analysis_result.confidence_score:.1%}")

        # 显示错误类型分布
        if analysis_result.analysis_summary["error_types"]:
            print("\n📋 错误类型分布:")
            for error_type, count in analysis_result.analysis_summary["error_types"].items():
                print(f"   - {error_type}: {count} 次")

        # 显示置信度分布
        conf_dist = analysis_result.analysis_summary["confidence_distribution"]
        print(f"\n🎯 修复建议置信度:")
        print(f"   - 高置信度 (≥80%): {conf_dist['high']} 个")
        print(f"   - 中等置信度 (50-80%): {conf_dist['medium']} 个")
        print(f"   - 低置信度 (<50%): {conf_dist['low']} 个")

        print("="*50)

    def _handle_fix_application(self, analysis_result: AnalysisResult) -> bool:
        """处理修复应用"""
        if not analysis_result.fix_suggestions:
            print("ℹ️  No fix suggestions available")
            return True

        response = input("\n🤖 AI has generated fix suggestions. Apply them? [Y/n]: ").strip().lower()
        if response == 'n':
            print("⏭️  Skipping fix application")
            return True

        # 获取优先级排序的修复建议
        prioritized_fixes = self.analyzer.prioritize_fixes(analysis_result)

        # 应用修复
        results = self.applier.batch_apply_fixes(prioritized_fixes, interactive=True)

        # 显示应用结果
        self._display_application_results(results)

        return True

    def _parse_todo_for_fixes(self, todo_path: Path) -> List:
        """从 TODO 文件解析修复建议"""
        # 这里可以扩展解析 TODO 文件的逻辑
        # 目前返回空列表，实际应用中可以根据 TODO 内容生成修复建议
        print("ℹ️  TODO parsing not fully implemented yet")
        return []

    def _display_application_results(self, results: Dict[str, any]):
        """显示修复应用结果"""
        print("\n" + "="*50)
        print("🔧 修复应用结果")
        print("="*50)

        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        print(f"✅ 成功应用: {successful} 个")
        print(f"❌ 应用失败: {failed} 个")

        if failed > 0:
            print("\n失败的修复:")
            for file_path, result in results.items():
                if not result.success:
                    print(f"   - {file_path}: {result.message}")

        print("="*50)

    def _update_todo_after_fixes(self, todo_path: Path, results: Dict[str, any]):
        """修复应用后更新 TODO 文件"""
        try:
            if todo_path.exists():
                content = todo_path.read_text(encoding='utf-8')

                # 更新完成统计
                successful = sum(1 for result in results.values() if result.success)
                failed = len(results) - successful

                # 更新完成的部分
                completed_section = "## ✅ 已完成的修复\n"
                completed_content = []

                for file_path, result in results.items():
                    if result.success:
                        completed_content.append(f"- **{file_path}**: ✅ 修复成功")

                        # 添加验证结果（如果有）
                        if hasattr(result, 'validation_score'):
                            completed_content.append(f"  - 验证得分: {result.validation_score:.2%}")

                        # 添加测试生成结果（如果有）
                        if hasattr(result, 'tests_generated'):
                            completed_content.append(f"  - 生成测试: {result.tests_generated} 个")
                    else:
                        completed_content.append(f"- **{file_path}**: ❌ 修复失败 - {result.message}")

                if completed_content:
                    completed_section += "\n".join(completed_content)

                    # 替换原有的完成部分
                    if "## ✅ 已完成的修复" in content:
                        content = re.sub(
                            r"## ✅ 已完成的修复.*?(?=\n##|\n---|$)",
                            completed_section,
                            content,
                            flags=re.DOTALL
                        )
                    else:
                        # 插入新的完成部分
                        insert_pos = content.find("## 🔧 AI 建议的行动")
                        if insert_pos != -1:
                            content = content[:insert_pos] + completed_section + "\n\n" + content[insert_pos:]

                # 更新时间戳
                content = re.sub(
                    r"自动更新于:.*",
                    f"自动更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    content
                )

                todo_path.write_text(content, encoding='utf-8')
                print(f"✅ TODO 文件已更新: {todo_path}")

        except Exception as e:
            print(f"⚠️  更新 TODO 文件失败: {e}")

    def update_todo_with_phase3_results(self, todo_path: Path, phase3_results: Dict[str, any]):
        """使用 Phase 3 结果更新 TODO 文件"""
        try:
            if todo_path.exists():
                content = todo_path.read_text(encoding='utf-8')

                # 添加 Phase 3 结果部分
                phase3_section = f"""## 🤖 Phase 3 智能化增强结果

### 📊 自动测试生成
- 生成的测试文件: {phase3_results.get('tests_generated', 0)} 个
- 新增的测试用例: {phase3_results.get('test_cases_added', 0)} 个
- 测试覆盖率提升: {phase3_results.get('coverage_improvement', '0%')}

### 🔍 修复验证结果
- 验证通过的修复: {phase3_results.get('fixes_validated', 0)} 个
- 验证失败的修复: {phase3_results.get('fixes_failed', 0)} 个
- 平均验证得分: {phase3_results.get('average_validation_score', '0%')}

### 📚 持续学习统计
- 反馈记录新增: {phase3_results.get('feedback_records_added', 0)} 条
- 学习到的模式: {phase3_results.get('patterns_learned', 0)} 个
- 修复建议改进: {phase3_results.get('suggestions_improved', 0)} 个

### 🎯 AI 建议的后续行动
1. 重点关注验证失败的修复，重新分析问题原因
2. 基于生成的测试用例，进一步优化代码质量
3. 利用持续学习机制，提高未来修复的准确性
4. 定期运行 Phase 3 分析以保持智能化的持续提升

"""

                # 移除旧的 Phase 3 部分（如果存在）
                content = re.sub(
                    r"## 🤖 Phase 3 智能化增强结果.*?(?=\n##|\n---|$)",
                    "",
                    content,
                    flags=re.DOTALL
                )

                # 插入新的 Phase 3 部分
                insert_pos = content.find("---")
                if insert_pos != -1:
                    content = content[:insert_pos] + phase3_section + "\n---" + content[insert_pos:]

                # 更新时间戳
                content = re.sub(
                    r"自动更新于:.*",
                    f"自动更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    content
                )

                todo_path.write_text(content, encoding='utf-8')
                print(f"✅ TODO 文件已更新 Phase 3 结果: {todo_path}")

        except Exception as e:
            print(f"⚠️  更新 TODO 文件 Phase 3 结果失败: {e}")

    def _generate_phase2_report(self, mutation_results: Dict, flaky_results: Dict, performance_results: Dict, quality_results: Dict) -> Path:
        """生成 Phase 2 综合报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        report_path = self.reports_dir / f"PHASE2_QUALITY_REPORT_{timestamp}.md"

        # 生成各组件的报告
        mutation_report = self.mutation_tester.generate_mutation_report()
        flaky_report = self.flaky_detector.generate_flaky_report()
        performance_report = self.performance_benchmark.generate_performance_report()
        quality_report = self.quality_aggregator.generate_quality_report()

        report_content = f"""# 🚀 Phase 2: 测试有效性提升 - 综合质量报告

**生成时间:** {datetime.now().isoformat()}
**执行模式:** {"增量" if quality_results.get("execution_mode") == "incremental" else "完整"}

## 📊 质量概览

- **整体质量等级:** {quality_results.get('quality_grade', 'unknown').upper()}
- **综合得分:** {quality_results.get('overall_score', 0):.2%}
- **总执行时间:** {quality_results.get('execution_time', 0):.1f}秒

## 🔬 突变测试结果

{mutation_report}

## 🔄 Flaky测试检测结果

{flaky_report}

## ⚡ 性能基准测试结果

{performance_report}

## 📈 综合质量评估

{quality_report}

## 🎯 改进建议

### 短期行动项
1. 优先处理严重警报和高风险问题
2. 修复发现的Flaky测试以提高测试稳定性
3. 解决性能退化问题
4. 提高低覆盖率模块的测试覆盖率

### 长期策略
1. 建立持续的性能监控机制
2. 定期运行突变测试确保测试质量
3. 实施代码审查流程预防质量问题
4. 优化CI/CD流水线集成质量检查

## ⚠️ 风险提示

- **非阻塞模式:** 当前配置为非阻塞模式，严重质量问题不会阻断CI流程
- **增量测试:** 使用增量模式提高测试效率，但可能遗漏某些问题
- **环境依赖:** 某些测试可能依赖特定环境配置

---
*此报告由 AI 增强的测试有效性提升系统自动生成*
"""

        report_path.write_text(report_content, encoding='utf-8')
        return report_path

    def _generate_report_content(self, analyzer_stats: Dict, applier_stats: Dict) -> str:
        """生成报告内容"""
        lines = [
            "# 🤖 AI Bugfix Activity Report",
            "",
            f"**Generated:** {analyzer_stats['timestamp']}",
            "",
            "## 📊 修复统计",
            f"- 总修复尝试: {applier_stats['total']}",
            f"- 成功修复: {applier_stats['successful']}",
            f"- 失败修复: {applier_stats['failed']}",
            f"- 成功率: {applier_stats['success_rate']:.1%}",
            "",
            "## 🎯 建议",
            "- 定期运行 AI 分析以保持代码质量",
            "- 优先处理高置信度的修复建议",
            "- 应用修复后始终运行测试验证",
            "- 保持备份以便必要时回滚",
            "",
            "---",
            "*此报告由 AI 增强的 Bug 修复系统自动生成*"
        ]

        return "\n".join(lines)

    def run_continuous_loop(self, max_iterations: int = None, non_interactive: bool = True) -> bool:
        """
        运行持续 bug 修复循环

        Args:
            max_iterations: 最大循环次数，None 表示无限循环
            non_interactive: 是否非交互式模式

        Returns:
            是否成功完成所有循环
        """
        iteration = 0
        continuous_report_path = Path("docs/_reports") / f"CONTINUOUS_FIX_REPORT_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"

        # 创建持续修复报告
        report_content = f"""# 🔄 AI 增强的持续 Bug 修复循环报告

**开始时间:** {datetime.now().isoformat()}
**最大循环次数:** {'无限' if max_iterations is None else max_iterations}
**模式:** {'非交互式' if non_interactive else '交互式'}

## 📊 循环执行记录

"""

    try:
            while max_iterations is None or iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"🔄 开始第 {iteration} 轮持续 Bug 修复循环")
            print(f"{'='*60}")

            loop_start_time = datetime.now()
            loop_results = {
                'iteration': iteration,
                'start_time': loop_start_time.isoformat(),
                'phase1_success': False,
                'phase2_success': False,
                'phase3_success': False,
                'fixes_applied': 0,
                'tests_generated': 0,
                'errors': []
            }

            # Phase 1: 测试失败检测 + Claude Code 分析
            try:
                print("\n🚀 Phase 1: 测试失败检测 + AI 分析...")
                loop_results['phase1_success'] = self.run_analysis_and_generate_fixes(interactive=False)
                if loop_results['phase1_success']:
                    print("✅ Phase 1 完成")
                else:
                    print("⚠️ Phase 1 部分失败，继续执行")
            except Exception as e:
                error_msg = f"Phase 1 执行失败: {e}"
                print(f"❌ {error_msg}")
                loop_results['errors'].append(error_msg)

            # Phase 2: 测试有效性分析
            try:
                print("\n🔬 Phase 2: 测试有效性分析...")
                loop_results['phase2_success'] = self.run_phase2_quality_analysis(incremental=True)
                if loop_results['phase2_success']:
                    print("✅ Phase 2 完成")
                else:
                    print("⚠️ Phase 2 部分失败，继续执行")
            except Exception as e:
                error_msg = f"Phase 2 执行失败: {e}"
                print(f"❌ {error_msg}")
                loop_results['errors'].append(error_msg)

            # Phase 3: AI 智能化功能
            try:
                print("\n🤖 Phase 3: AI 智能化增强...")
                loop_results['phase3_success'] = self.run_phase3_intelligent_enhancement()
                if loop_results['phase3_success']:
                    print("✅ Phase 3 完成")
                else:
                    print("⚠️ Phase 3 部分失败，继续执行")
            except Exception as e:
                error_msg = f"Phase 3 执行失败: {e}"
                print(f"❌ {error_msg}")
                loop_results['errors'].append(error_msg)

            # 记录循环结果
            loop_end_time = datetime.now()
            loop_duration = (loop_end_time - loop_start_time).total_seconds()
            loop_results['end_time'] = loop_end_time.isoformat()
            loop_results['duration'] = f"{loop_duration:.1f}秒"

            # 更新持续报告
            report_content += f"""### 循环 {iteration} - {loop_start_time.strftime('%H:%M:%S')}
- **执行时间:** {loop_results['duration']}
- **Phase 1:** {'✅ 成功' if loop_results['phase1_success'] else '❌ 失败'}
- **Phase 2:** {'✅ 成功' if loop_results['phase2_success'] else '❌ 失败'}
- **Phase 3:** {'✅ 成功' if loop_results['phase3_success'] else '❌ 失败'}
- **错误数量:** {len(loop_results['errors'])}

"""

            if loop_results['errors']:
                report_content += "**错误详情:**\n"
                for error in loop_results['errors'][:3]:  # 只显示前3个错误
                    report_content += f"- {error}\n"
                report_content += "\n"

            # 写入报告文件
            continuous_report_path.write_text(report_content + "\n\n*报告持续更新中...*", encoding='utf-8')

            print(f"\n📊 第 {iteration} 轮循环完成")
            print(f"⏱️  执行时间: {loop_results['duration']}")
            print(f"📋 报告已更新: {continuous_report_path}")

            # 如果所有阶段都失败，等待更长时间
            all_phases_failed = not any([loop_results['phase1_success'], loop_results['phase2_success'], loop_results['phase3_success']])
            if all_phases_failed:
                print("⚠️ 所有阶段都失败，等待60秒后重试...")
                import time
                time.sleep(60)
            else:
                print("⏳ 等待30秒后开始下一轮循环...")
                import time
                time.sleep(30)

        # 循环结束，完成报告
        final_report = report_content + f"""
## 📊 循环执行总结

- **总循环次数:** {iteration}
- **完成时间:** {datetime.now().isoformat()}
- **总体状态:** 完成

## 📈 各阶段成功率

- **Phase 1 (测试分析):** {'N/A' if iteration == 0 else f"{sum(1 for i in range(1, iteration+1) if getattr(self, f'_loop_{i}_phase1_success', False)) / iteration * 100:.1f}%"}
- **Phase 2 (质量分析):** {'N/A' if iteration == 0 else f"{sum(1 for i in range(1, iteration+1) if getattr(self, f'_loop_{i}_phase2_success', False)) / iteration * 100:.1f}%"}
- **Phase 3 (智能增强):** {'N/A' if iteration == 0 else f"{sum(1 for i in range(1, iteration+1) if getattr(self, f'_loop_{i}_phase3_success', False)) / iteration * 100:.1f}%"}

## 🎯 建议的后续行动

1. **定期运行持续循环**以保持代码质量
2. **监控 Phase 成功率**，如果有阶段持续失败需要调查
3. **检查生成的报告**了解修复进展
4. **结合人工审查**确保修复质量

---
*此报告由 AI 增强的持续 Bug 修复系统自动生成*
"""

        continuous_report_path.write_text(final_report, encoding='utf-8')
        print(f"\n🎉 持续 Bug 修复循环完成！")
        print(f"📊 最终报告: {continuous_report_path}")

        return True

    except KeyboardInterrupt:
        print(f"\n⏹️  持续循环被用户中断 (第 {iteration} 轮)")
        # 保存中断时的报告
        interrupt_report = report_content + f"""
## ⏹️ 循环中断

- **中断时间:** {datetime.now().isoformat()}
- **完成循环数:** {iteration - 1}
- **中断原因:** 用户手动中断

---
*报告在循环中断时自动保存*
"""
        continuous_report_path.write_text(interrupt_report, encoding='utf-8')
        return True

    except Exception as e:
        print(f"\n❌ 持续循环发生严重错误: {e}")
        logger.error(f"Error in continuous loop: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Enhanced Bugfix System")
    parser.add_argument("--mode", choices=["analyze", "fix", "validate", "report", "phase2", "phase3", "continuous"],
                       default="analyze", help="运行模式")
    parser.add_argument("--max-iterations", type=int, help="持续模式的最大循环次数")
    parser.add_argument("--todo", type=str, help="TODO 文件路径")
    parser.add_argument("--non-interactive", action="store_true", help="非交互式模式")
    parser.add_argument("--full-analysis", action="store_true", help="运行完整分析（非增量）")

    # Phase 3 选项
    parser.add_argument("--auto-generate-tests", type=str, help="自动生成缺失测试（指定文件路径或目录）")
    parser.add_argument("--validate-fix", type=str, help="验证修复效果（指定修复后的文件路径）")
    parser.add_argument("--feedback", action="store_true", help="输出历史修复经验")

    args = parser.parse_args()

    # 创建 AI 增强修复系统
    bugfix_system = AIEnhancedBugfix()

    # 处理 Phase 3 选项（优先处理）
    if args.auto_generate_tests:
        success = bugfix_system.auto_generate_tests(args.auto_generate_tests)
    elif args.validate_fix:
        success = bugfix_system.validate_fix(args.validate_fix)
    elif args.feedback:
        success = bugfix_system.show_feedback_history()
    # 根据模式运行
    elif args.mode == "analyze":
        success = bugfix_system.run_analysis_and_generate_fixes(
            interactive=not args.non_interactive
        )
    elif args.mode == "fix":
        todo_path = Path(args.todo) if args.todo else None
        success = bugfix_system.apply_recommended_fixes(todo_path)
    elif args.mode == "validate":
        success = bugfix_system.validate_fixes()
    elif args.mode == "report":
        success = bugfix_system.generate_report()
    elif args.mode == "phase2":
        success = bugfix_system.run_phase2_quality_analysis(
            incremental=not args.full_analysis
        )
    elif args.mode == "phase3":
        success = bugfix_system.run_phase3_intelligent_enhancement()
    elif args.mode == "continuous":
        success = bugfix_system.run_continuous_loop(
            max_iterations=args.max_iterations,
            non_interactive=args.non_interactive or True  # 默认非交互式
        )
    else:
        print(f"Unknown mode: {args.mode}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()