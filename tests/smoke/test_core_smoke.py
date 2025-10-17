#!/usr/bin/env python3
"""
Core模块smoke测试
测试核心功能是否可以正常导入和初始化
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestCoreSmoke:
    """Core模块冒烟测试"""

    def test_core_imports(self):
        """测试核心模块导入"""
        # 测试异常模块
        from src.core.exceptions import (
            ValidationError,
            NotFoundError,
            ConfigurationError,
            BasePredictionError,
        )

        assert ValidationError is not None
        assert NotFoundError is not None
        assert ConfigurationError is not None
        assert BasePredictionError is not None

    def test_core_logger(self):
        """测试日志模块"""
        from src.core.logger import get_logger

        logger = get_logger("test")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def test_di_container(self):
        """测试依赖注入容器"""
        from src.core.di import DIContainer

        container = DIContainer()
        assert container is not None

        # 测试基本功能
        container.register("test_service", lambda: "test_value")
        service = container.get("test_service")
        assert service == "test_value"

    def test_config_module(self):
        """测试配置模块"""
        from src.core.config import Config

        # 测试配置加载
        config = Config()
        assert config is not None
        assert hasattr(config, "get")

    def test_event_application(self):
        """测试事件应用"""
        from src.core.event_application import EventApplication

        app = EventApplication()
        assert app is not None

    def test_service_lifecycle(self):
        """测试服务生命周期"""
        from src.core.service_lifecycle import ServiceLifecycle

        lifecycle = ServiceLifecycle()
        assert lifecycle is not None
        assert hasattr(lifecycle, "start")
        assert hasattr(lifecycle, "stop")

    def test_prediction_engine(self):
        """测试预测引擎"""
        from src.core.prediction_engine import PredictionEngine

        engine = PredictionEngine()
        assert engine is not None
        assert hasattr(engine, "predict")
