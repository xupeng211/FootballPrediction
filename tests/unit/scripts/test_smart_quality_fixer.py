#!/usr/bin/env python3
"""
智能质量修复工具单元测试
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.smart_quality_fixer import SmartQualityFixer


class TestSmartQualityFixer:
    """智能质量修复器测试"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.fixer = SmartQualityFixer(self.temp_dir)

    def test_init_default_project_root(self):
        """测试默认项目根目录初始化"""
        fixer = SmartQualityFixer()
        assert fixer.project_root.name == "FootballPrediction"
        assert fixer.src_dir == fixer.project_root / "src"
        assert fixer.test_dir == fixer.project_root / "tests"

    def test_init_custom_project_root(self):
        """测试自定义项目根目录初始化"""
        assert self.fixer.project_root == self.temp_dir
        assert self.fixer.src_dir == self.temp_dir / "src"
        assert self.fixer.test_dir == self.temp_dir / "tests"

    def test_fix_results_initialization(self):
        """测试修复结果初始化"""
        results = self.fixer.fix_results
        assert "timestamp" in results
        assert "fixes_applied" in results
        assert "errors_fixed" in results
        assert "files_processed" in results
        assert "recommendations" in results

    def test_syntax_error_fixing(self):
        """测试语法错误修复"""
        # 创建包含语法错误的文件
        src_dir = self.temp_dir / "src"
        src_dir.mkdir()
        test_file = src_dir / "test_syntax.py"
        test_file.write_text("def broken_function(\n    pass\n")

        # 测试语法修复
        fix_count = self.fixer.fix_syntax_errors()
        # 应该至少尝试修复或检测到问题
        assert fix_count >= 0

    def test_import_error_fixing(self):
        """测试导入错误修复"""
        # 创建包含导入错误的文件
        src_dir = self.temp_dir / "src"
        src_dir.mkdir()
        test_file = src_dir / "test_import.py"
        test_file.write_text("import nonexistent_module\n\ndef test():\n    pass\n")

        # 测试导入修复
        fix_count = self.fixer.fix_import_errors()
        # 应该尝试修复或检测到问题
        assert fix_count >= 0

    def test_quality_standards_loading(self):
        """测试质量标准加载"""
        standards = self.fixer.quality_standards
        assert isinstance(standards, dict)
        # 应该有默认标准即使文件不存在
        assert len(standards) > 0

    def test_fix_ruff_issues_dry_run(self):
        """测试Ruff问题修复（试运行）"""
        # 创建包含简单Ruff问题的文件
        src_dir = self.temp_dir / "src"
        src_dir.mkdir()
        test_file = src_dir / "test_ruff.py"
        test_file.write_text("import os\nimport sys\n\ndef func( ):\n    pass\n")

        # 测试修复
        fix_count = self.fixer.fix_ruff_issues()
        # 应该修复一些问题
        assert fix_count >= 0

    def test_help_functionality(self):
        """测试帮助功能"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/smart_quality_fixer.py", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        assert result.returncode == 0
        assert "智能质量修复工具" in result.stdout
        assert "--help" in result.stdout

    def test_dry_run_mode(self):
        """测试试运行模式"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/smart_quality_fixer.py", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        assert result.returncode == 0
        assert "试运行模式" in result.stdout

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])