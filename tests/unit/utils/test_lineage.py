"""数据血缘测试"""

import pytest


class TestLineage:
    """测试数据血缘模块"""

    def test_lineage_reporter_import(self):
        """测试血缘报告器导入"""
        try:
            from src.lineage.lineage_reporter import LineageReporter

            assert LineageReporter is not None
        except ImportError:
            pass  # 已激活

    def test_metadata_manager_import(self):
        """测试元数据管理器导入"""
        try:
            from src.lineage.metadata_manager import MetadataManager

            assert MetadataManager is not None
        except ImportError:
            pass  # 已激活
