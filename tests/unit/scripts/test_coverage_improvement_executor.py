#!/usr/bin/env python3
"""
CoverageImprovementExecutor单元测试
验证覆盖率改进执行器的核心功能
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from coverage_improvement_executor import CoverageImprovementExecutor


class TestCoverageImprovementExecutor:
    """覆盖率改进执行器测试"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.executor = CoverageImprovementExecutor()

    def test_initialization(self):
        """测试初始化"""
        assert self.executor.project_root.name == "FootballPrediction"
        assert self.executor.current_phase == 1
        assert isinstance(self.executor.results_log, list)
        assert len(self.executor.results_log) == 0

    def test_log_result(self):
        """测试结果记录功能"""
        self.executor.log_result("测试类别", "测试消息", True)

        assert len(self.executor.results_log) == 1
        result = self.executor.results_log[0]
        assert result["category"] == "测试类别"
        assert result["message"] == "测试消息"
        assert result["success"] is True
        assert "timestamp" in result

    def test_syntax_check(self):
        """测试语法检查功能"""
        # 测试语法检查方法可以执行
        self.executor.run_syntax_check()

        # 检查是否记录了结果
        syntax_results = [
            r for r in self.executor.results_log if r["category"] == "语法检查"
        ]
        assert len(syntax_results) > 0

    def test_help_functionality(self):
        """测试帮助功能"""
        import subprocess

        result = subprocess.run(
            [sys.executable, "scripts/coverage_improvement_executor.py", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "测试覆盖率改进执行器" in result.stdout
        assert "--help" in result.stdout

    def test_diagnosis_mode(self):
        """测试诊断模式"""
        import subprocess

        result = subprocess.run(
            [sys.executable, "scripts/coverage_improvement_executor.py", "--diagnosis"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "快速诊断" in result.stdout

    def teardown_method(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
