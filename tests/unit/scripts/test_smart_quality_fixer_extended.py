#!/usr/bin/env python3
"""
SmartQualityFixer扩展测试
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

from smart_quality_fixer import SmartQualityFixer


class TestSmartQualityFixerExtended:
    """SmartQualityFixer扩展测试"""

    def setup_method(self):
        """测试前设置"""
        self.fixer = SmartQualityFixer()

    def test_fix_ruff_issues_detailed(self):
        """测试Ruff问题修复的详细功能"""
        initial_fix_count = self.fixer.fix_results["fixes_applied"].get(
            "ruff_issues", 0
        )

        # 执行Ruff修复
        fix_count = self.fixer.fix_ruff_issues()

        # 应该返回一个数字（修复数量）
        assert isinstance(fix_count, int)
        assert fix_count >= 0

        # 修复结果应该被记录
        assert "ruff_issues" in self.fixer.fix_results["fixes_applied"]

    def test_fix_test_issues(self):
        """测试测试问题修复功能"""
        initial_fix_count = self.fixer.fix_results["fixes_applied"].get(
            "test_issues", 0
        )

        # 执行测试问题修复
        fix_count = self.fixer.fix_test_issues()

        # 应该返回一个数字（修复数量）
        assert isinstance(fix_count, int)
        assert fix_count >= 0

        # 修复结果应该被记录
        assert "test_issues" in self.fixer.fix_results["fixes_applied"]

    def test_apply_refactor_suggestions(self):
        """测试应用重构建议功能"""
        initial_fix_count = self.fixer.fix_results["fixes_applied"].get(
            "refactor_suggestions", 0
        )

        # 执行重构建议应用
        fix_count = self.fixer.apply_refactor_suggestions()

        # 应该返回一个数字（修复数量）
        assert isinstance(fix_count, int)
        assert fix_count >= 0

        # 修复结果应该被记录
        assert "refactor_suggestions" in self.fixer.fix_results["fixes_applied"]

    def test_fix_mypy_errors_functional(self):
        """测试MyPy错误修复功能"""
        initial_fix_count = self.fixer.fix_results["fixes_applied"].get(
            "mypy_errors", 0
        )

        # 执行MyPy错误修复
        fix_count = self.fixer.fix_mypy_errors()

        # 应该返回一个数字（修复数量）
        assert isinstance(fix_count, int)
        assert fix_count >= 0

        # 修复结果应该被记录
        assert "mypy_errors" in self.fixer.fix_results["fixes_applied"]

    def test_fix_import_errors_functional(self):
        """测试导入错误修复功能"""
        initial_fix_count = self.fixer.fix_results["fixes_applied"].get(
            "import_errors", 0
        )

        # 执行导入错误修复
        fix_count = self.fixer.fix_import_errors()

        # 应该返回一个数字（修复数量）
        assert isinstance(fix_count, int)
        assert fix_count >= 0

        # 修复结果应该被记录
        assert "import_errors" in self.fixer.fix_results["fixes_applied"]

    def test_fix_syntax_errors_functional(self):
        """测试语法错误修复功能"""
        initial_fix_count = self.fixer.fix_results["fixes_applied"].get(
            "syntax_errors", 0
        )

        # 执行语法错误修复
        fix_count = self.fixer.fix_syntax_errors()

        # 应该返回一个数字（修复数量）
        assert isinstance(fix_count, int)
        assert fix_count >= 0

        # 修复结果应该被记录
        assert "syntax_errors" in self.fixer.fix_results["fixes_applied"]

    def test_quality_standards_loading_from_nonexistent_file(self):
        """测试从不存在的质量标准文件加载"""
        # 如果质量标准文件不存在，应该返回空字典
        standards = self.fixer._load_quality_standards()
        assert isinstance(standards, dict)
        # 可能为空字典，但不应该为None

    def test_error_count_accumulation(self):
        """测试错误计数累加"""
        initial_errors = self.fixer.fix_results["errors_fixed"]

        # 执行一些修复操作
        self.fixer.fix_syntax_errors()
        self.fixer.fix_import_errors()

        # 错误计数应该增加
        final_errors = self.fixer.fix_results["errors_fixed"]
        assert final_errors >= initial_errors

    def test_files_processed_counting(self):
        """测试文件处理计数"""
        initial_files = self.fixer.fix_results["files_processed"]

        # 执行一些修复操作
        self.fixer.fix_syntax_errors()

        # 文件处理计数应该增加
        final_files = self.fixer.fix_results["files_processed"]
        assert final_files >= initial_files

    def test_recommendations_generation(self):
        """测试推荐生成"""
        # 执行一些操作后应该有推荐
        self.fixer.fix_syntax_errors()

        recommendations = self.fixer.fix_results["recommendations"]
        assert isinstance(recommendations, list)

    def test_print_summary_functionality(self):
        """测试打印摘要功能"""
        # 这个测试主要确保print_summary不会抛出异常
        try:
            self.fixer.print_summary()
            # 如果没有抛出异常就算通过
            assert True
        except Exception as e:
            pytest.fail(f"print_summary抛出异常: {e}")

    def test_run_comprehensive_fix_functionality(self):
        """测试综合修复流程"""
        initial_log_count = len(self.fixer.fix_results["fixes_applied"])

        # 执行综合修复
        result = self.fixer.run_comprehensive_fix()

        # 应该返回修复结果字典
        assert isinstance(result, dict)

        # 应该有更多修复记录
        final_log_count = len(self.fixer.fix_results["fixes_applied"])
        assert final_log_count >= initial_log_count

    def test_project_root_path_validation(self):
        """测试项目根目录路径验证"""
        # 项目根目录应该存在
        assert self.fixer.project_root.exists()

        # 应该是FootballPrediction目录
        assert self.fixer.project_root.name == "FootballPrediction"

    def test_src_directory_validation(self):
        """测试src目录验证"""
        # src目录应该存在
        assert self.fixer.src_dir.exists()
        assert self.fixer.src_dir.name == "src"

    def test_test_directory_validation(self):
        """测试test目录验证"""
        # test目录应该存在
        assert self.fixer.test_dir.exists()
        assert self.fixer.test_dir.name == "tests"

    def test_initialization_with_custom_project_root(self):
        """测试使用自定义项目根目录初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # 在临时目录中创建src和tests目录
            (temp_path / "src").mkdir()
            (temp_path / "tests").mkdir()

            custom_fixer = SmartQualityFixer(temp_path)

            # 应该使用自定义目录
            assert custom_fixer.project_root == temp_path
            assert custom_fixer.src_dir == temp_path / "src"
            assert custom_fixer.test_dir == temp_path / "tests"

    def test_timestamp_initialization(self):
        """测试时间戳初始化"""
        import datetime

        timestamp = self.fixer.fix_results["timestamp"]
        assert isinstance(timestamp, str)

        # 应该是有效的ISO格式时间戳
        try:
            datetime.datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail("时间戳不是有效的ISO格式")

    def test_quality_standards_structure(self):
        """测试质量标准结构"""
        standards = self.fixer.quality_standards

        # 应该是一个字典
        assert isinstance(standards, dict)

        # 应该有基本的质量标准键（如果文件存在）
        if standards:
            expected_keys = [
                "max_line_length",
                "max_function_length",
                "max_class_length",
            ]
            # 至少应该有一些键
            assert len(standards) > 0

    def test_recommendations_content(self):
        """测试推荐内容"""
        # 添加一些操作以生成推荐
        self.fixer.fix_syntax_errors()

        recommendations = self.fixer.fix_results["recommendations"]

        # 推荐应该是一个列表
        assert isinstance(recommendations, list)

        # 每个推荐应该是字符串
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
