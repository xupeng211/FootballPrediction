#!/usr/bin/env python3
"""
Services模块smoke测试
测试服务层模块是否可以正常导入和初始化
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestServicesSmoke:
    """Services模块冒烟测试"""

    def test_base_service(self):
        """测试基础服务"""
        from src.services.base_unified import BaseService

        # 创建基础服务实例
        service = BaseService()
        assert service is not None
        assert hasattr(service, "logger")

    def test_services_import(self):
        """测试服务导入"""
        # 测试主要服务可以导入
        from src.services.manager import ServiceManager
        from src.services.audit_service import AuditService
        from src.services.user_profile import UserProfileService

        assert ServiceManager is not None
        assert AuditService is not None
        assert UserProfileService is not None

    def test_prediction_services(self):
        """测试预测服务"""
        from src.services.event_prediction_service import EventPredictionService
        from src.services.strategy_prediction_service import StrategyPredictionService

        # 测试类可以实例化
        event_service = EventPredictionService()
        strategy_service = StrategyPredictionService()

        assert event_service is not None
        assert strategy_service is not None

    def test_data_processing_service(self):
        """测试数据处理服务"""
        from src.services.data_processing import DataProcessingService

        service = DataProcessingService()
        assert service is not None

    def test_content_analysis_service(self):
        """测试内容分析服务"""
        from src.services.content_analysis import ContentAnalysisService

        service = ContentAnalysisService()
        assert service is not None

    def test_service_lifecycle(self):
        """测试服务生命周期管理"""
        from src.core.service_lifecycle import ServiceLifecycle

        lifecycle = ServiceLifecycle()
        assert lifecycle is not None

        # 测试生命周期方法存在
        assert hasattr(lifecycle, "start")
        assert hasattr(lifecycle, "stop")
        assert hasattr(lifecycle, "restart")
