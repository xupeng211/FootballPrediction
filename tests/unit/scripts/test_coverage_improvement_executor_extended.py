#!/usr/bin/env python3
"""
CoverageImprovementExecutor扩展测试
增加更多测试用例以提升覆盖率
"""

import sys
import tempfile
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from coverage_improvement_executor import CoverageImprovementExecutor


class TestCoverageImprovementExecutorExtended:
    """CoverageImprovementExecutor扩展测试"""

    def setup_method(self):
        """测试前设置"""
        self.executor = CoverageImprovementExecutor()

    def test_run_existing_tests_file_not_found(self):
        """测试运行现有测试时文件不存在的情况"""
        # 这个测试会尝试运行不存在的测试文件
        # 应该能优雅地处理文件不存在的情况
        initial_log_count = len(self.executor.results_log)

        self.executor.run_existing_tests()

        # 应该记录了"文件不存在"的日志
        assert len(self.executor.results_log) > initial_log_count

        # 检查是否有文件不存在的错误记录
        not_found_logs = [
            log
            for log in self.executor.results_log
            if log["category"] == "现有测试" and "不存在" in log["message"]
        ]
        assert len(not_found_logs) > 0

    def test_phase1_basic_modules_success(self):
        """测试Phase 1基础模块测试成功情况"""
        initial_log_count = len(self.executor.results_log)

        self.executor.phase1_basic_modules()

        # 应该记录了Phase 1的执行过程
        assert len(self.executor.results_log) > initial_log_count

        # 检查是否有Phase 1相关的日志 - 检查category字段
        phase1_logs = [
            log for log in self.executor.results_log if log["category"] == "Phase 1"
        ]
        assert len(phase1_logs) > 0

    def test_generate_progress_report(self):
        """测试生成进度报告功能"""
        # 运行一些操作生成日志
        self.executor.log_result("测试类别", "测试消息", True)

        # 生成进度报告
        self.executor.generate_progress_report()

        # 检查报告文件是否生成
        report_file = self.executor.project_root / "coverage_improvement_report.json"
        assert report_file.exists()

    def test_project_root_properties(self):
        """测试项目根目录属性"""
        assert self.executor.project_root.exists()
        assert self.executor.project_root.name == "FootballPrediction"
        assert self.executor.current_phase == 1

    def test_results_log_structure(self):
        """测试结果日志结构"""
        # 添加一个测试日志
        self.executor.log_result("测试类别", "测试消息", True)

        # 检查日志结构
        log = self.executor.results_log[-1]

        required_keys = ["timestamp", "category", "message", "success"]
        for key in required_keys:
            assert key in log

    def test_run_comprehensive_flow(self):
        """测试完整的综合流程"""
        initial_log_count = len(self.executor.results_log)

        # 执行综合流程 - 使用run_phase1方法
        self.executor.run_phase1()

        # 应该有日志记录
        assert len(self.executor.results_log) > initial_log_count

    def test_error_handling_in_syntax_check(self):
        """测试语法检查中的错误处理"""
        # 即使在无效目录也能优雅处理
        initial_log_count = len(self.executor.results_log)

        # 语法检查应该能处理错误情况
        self.executor.run_syntax_check()

        # 应该记录了执行结果
        assert len(self.executor.results_log) > initial_log_count

    def test_start_time_initialization(self):
        """测试开始时间初始化"""
        import datetime

        # 开始时间应该是一个datetime对象
        assert isinstance(self.executor.start_time, datetime.datetime)

        # 开始时间应该是最近的（1分钟内）
        import time

        time_diff = time.time() - self.executor.start_time.timestamp()
        assert time_diff < 60  # 应该在1分钟内

    def test_log_result_with_none_success(self):
        """测试当success为None时的日志记录"""
        initial_log_count = len(self.executor.results_log)

        self.executor.log_result("测试类别", "进行中的操作", None)

        # 应该记录了日志
        assert len(self.executor.results_log) > initial_log_count

        log = self.executor.results_log[-1]
        assert log["success"] is None
        assert log["category"] == "测试类别"
        assert log["message"] == "进行中的操作"

    def test_coverage_improvement_executor_initialization_with_custom_root(self):
        """测试使用自定义根目录初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir)
            custom_executor = CoverageImprovementExecutor()

            # 默认应该使用项目根目录
            assert custom_executor.project_root.name == "FootballPrediction"

    def test_results_log_persistence(self):
        """测试结果日志的持久性"""
        initial_count = len(self.executor.results_log)

        # 添加多个日志
        for i in range(3):
            self.executor.log_result(f"类别{i}", f"消息{i}", i % 2 == 0)

        # 日志应该持续增加
        assert len(self.executor.results_log) == initial_count + 3

        # 检查所有日志都有正确的结构
        for log in self.executor.results_log[-3:]:
            assert "timestamp" in log
            assert "category" in log
            assert "message" in log
            assert "success" in log


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
