#!/usr/bin/env python3
"""
AI 增强的持续 Bug 修复循环脚本

简化版本，专注于运行完整的持续修复循环。
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


class ContinuousBugFixSystem:
    """持续 Bug 修复系统"""

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
        logger.info("Continuous Bugfix system initialized")

    def run_phase1_analysis(self) -> bool:
        """运行 Phase 1: 测试失败检测 + AI 分析"""
        try:
            print("🚀 Phase 1: 测试失败检测 + AI 分析...")

            # 运行测试获取失败信息
            test_output = self._run_tests_collect_failures()

            # 获取覆盖率数据
            coverage_data = self._collect_coverage_data()

            # AI 分析测试失败
            analysis_result = self.analyzer.analyze_test_results(test_output, coverage_data)

            # 生成 BUGFIX_TODO
            todo_path = self.reports_dir / "BUGFIX_TODO.md"
            self.analyzer.generate_bugfix_todo(analysis_result, todo_path)

            print("✅ Phase 1 完成")
            return True

        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            return False

    def run_phase2_analysis(self) -> bool:
        """运行 Phase 2: 测试有效性分析"""
        try:
            print("🔬 Phase 2: 测试有效性分析...")

            # 突变测试
            mutation_results = self.mutation_tester.run_mutation_tests(incremental=True)

            # Flaky测试检测
            flaky_results = self.flaky_detector.detect_flaky_tests(incremental=True)

            # 性能基准测试
            performance_results = self.performance_benchmark.run_performance_benchmarks(update_baselines=False)

            # 综合质量评估
            quality_results = self.quality_aggregator.run_comprehensive_quality_check(incremental=True)

            print("✅ Phase 2 完成")
            return True

        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            return False

    def run_phase3_enhancement(self) -> bool:
        """运行 Phase 3: AI 智能化增强"""
        try:
            print("🤖 Phase 3: AI 智能化增强...")

            # 自动生成测试（示例）
            # 这里可以添加自动生成测试的逻辑

            # 验证修复
            # 这里可以添加修复验证的逻辑

            # 分析历史数据
            learning_patterns = self.feedback_db.get_learning_patterns()

            print("✅ Phase 3 完成")
            return True

        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            return False

    def run_continuous_loop(self, max_iterations: int = None) -> bool:
        """
        运行持续 bug 修复循环

        Args:
            max_iterations: 最大循环次数，None 表示无限循环

        Returns:
            是否成功完成所有循环
        """
        iteration = 0
        continuous_report_path = self.reports_dir / f"CONTINUOUS_FIX_REPORT_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"

        # 创建持续修复报告
        report_content = f"""# 🔄 AI 增强的持续 Bug 修复循环报告

**开始时间:** {datetime.now().isoformat()}
**最大循环次数:** {'无限' if max_iterations is None else max_iterations}

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
                    'errors': []
                }

                # Phase 1: 测试失败检测 + Claude Code 分析
                try:
                    print("\n🚀 Phase 1: 测试失败检测 + AI 分析...")
                    loop_results['phase1_success'] = self.run_phase1_analysis()
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
                    loop_results['phase2_success'] = self.run_phase2_analysis()
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
                    loop_results['phase3_success'] = self.run_phase3_enhancement()
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

    def _run_tests_collect_failures(self) -> str:
        """运行测试并收集失败信息"""
        cmd = [
            "pytest",
            "--maxfail=10",
            "--tb=short",
            "--disable-warnings",
            "tests/test_ai_demo_failure.py"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.stdout + "\n" + result.stderr

    def _collect_coverage_data(self) -> Optional[Dict]:
        """收集覆盖率数据"""
        try:
            cmd = [
                "pytest",
                "--cov=src",
                "--cov-report=json:coverage.json",
                "--maxfail=10",
                "--disable-warnings",
                "tests/test_ai_demo_failure.py"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if Path("coverage.json").exists():
                return json.load(open("coverage.json"))
            else:
                return None

        except Exception as e:
            logger.error(f"Error collecting coverage data: {e}")
            return None


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Enhanced Continuous Bugfix System")
    parser.add_argument("--max-iterations", type=int, help="持续模式的最大循环次数")

    args = parser.parse_args()

    # 创建持续修复系统
    bugfix_system = ContinuousBugFixSystem()

    # 运行持续循环
    success = bugfix_system.run_continuous_loop(max_iterations=args.max_iterations)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()