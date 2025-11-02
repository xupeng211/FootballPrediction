#!/usr/bin/env python3
"""
质量守护工具单元测试
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.quality_guardian import QualityGuardian


class TestQualityGuardian:
    """质量守护器测试"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.guardian = QualityGuardian(self.temp_dir)

    def test_init_default_project_root(self):
        """测试默认项目根目录初始化"""
        guardian = QualityGuardian()
        assert guardian.project_root.name == "FootballPrediction"
        assert guardian.monitoring_dir == guardian.project_root / "monitoring-data"
        assert guardian.reports_dir == guardian.project_root / "quality-reports"

    def test_init_custom_project_root(self):
        """测试自定义项目根目录初始化"""
        assert self.guardian.project_root == self.temp_dir
        assert self.guardian.monitoring_dir == self.temp_dir / "monitoring-data"
        assert self.guardian.reports_dir == self.temp_dir / "quality-reports"

    def test_quality_status_initialization(self):
        """测试质量状态初始化"""
        status = self.guardian.quality_status
        assert "timestamp" in status
        assert "overall_score" in status
        assert "coverage" in status
        assert "code_quality" in status
        assert "security" in status
        assert "recommendations" in status
        assert "action_items" in status

    def test_smart_quality_fixer_integration(self):
        """测试智能质量修复器集成"""
        # 检查修复器是否正确初始化
        if self.guardian.fixer is not None:
            assert hasattr(self.guardian.fixer, 'project_root')
            assert self.guardian.fixer.project_root == self.temp_dir

    def test_help_functionality(self):
        """测试帮助功能"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/quality_guardian.py", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        assert result.returncode == 0
        assert "质量守护工具" in result.stdout
        assert "--help" in result.stdout

    def test_quality_check_functionality(self):
        """测试质量检查功能"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/quality_guardian.py", "--check-only"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        assert result.returncode == 0
        assert "质量检查完成" in result.stdout
        assert "综合质量分数" in result.stdout

    def test_quality_report_generation(self):
        """测试质量报告生成"""
        # 运行质量检查
        self.guardian.run_full_quality_check()

        # 检查报告是否生成
        assert self.guardian.reports_dir.exists()

        # 查找最新的报告文件
        report_files = list(self.guardian.reports_dir.glob("quality_report_*.json"))
        assert len(report_files) > 0

        # 验证报告内容
        latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
        with open(latest_report, 'r') as f:
            report_data = json.load(f)

        assert "quality_status" in report_data
        assert "timestamp" in report_data["quality_status"]

    def test_quality_metrics_collection(self):
        """测试质量指标收集"""
        metrics = self.guardian._collect_quality_metrics()

        # 验证基本指标
        assert isinstance(metrics, dict)
        assert "ruff_errors" in metrics
        assert "mypy_errors" in metrics
        assert "files_count" in metrics
        assert "coverage" in metrics

    def test_quality_analysis_components(self):
        """测试质量分析组件"""
        # 测试代码质量分析
        code_quality = self.guardian._analyze_code_quality()
        assert isinstance(code_quality, dict)

        # 测试测试健康度检查
        test_health = self.guardian._check_test_health()
        assert isinstance(test_health, dict)

        # 测试安全检查
        security = self.guardian._check_security()
        assert isinstance(security, dict)

    def test_full_quality_check_integration(self):
        """测试完整质量检查集成"""
        result = self.guardian.run_full_quality_check()

        assert isinstance(result, dict)
        # 验证关键字段存在
        assert "coverage" in result
        assert "code_quality" in result
        assert "security" in result
        assert "action_items" in result

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])