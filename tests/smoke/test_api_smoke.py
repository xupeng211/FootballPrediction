#!/usr/bin/env python3
"""
API模块smoke测试
测试API模块是否可以正常导入和初始化
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestAPISmoke:
    """API模块冒烟测试"""

    def test_fastapi_app(self):
        """测试FastAPI应用"""
        from src.api.app import create_app

        app = create_app()
        assert app is not None
        assert hasattr(app, "router")

    def test_api_dependencies(self):
        """测试API依赖注入"""
        from src.api.dependencies import get_db_session, get_current_user

        # 测试函数存在
        assert get_db_session is not None
        assert get_current_user is not None

    def test_api_schemas(self):
        """测试API模式"""
        from src.api.schemas import PredictionRequest, PredictionResponse, ErrorResponse

        assert PredictionRequest is not None
        assert PredictionResponse is not None
        assert ErrorResponse is not None

    def test_cqrs_module(self):
        """测试CQRS模块"""
        from src.api.cqrs import CommandBus, QueryBus

        # 测试类存在
        assert CommandBus is not None
        assert QueryBus is not None

    def test_events_system(self):
        """测试事件系统"""
        from src.api.events import EventBus, Event

        assert EventBus is not None
        assert Event is not None

    def test_observers(self):
        """测试观察者模式"""
        from src.api.observers import Observer, Subject

        assert Observer is not None
        assert Subject is not None

    def test_health_check(self):
        """测试健康检查"""
        from src.api.health import HealthChecker

        checker = HealthChecker()
        assert checker is not None
        assert hasattr(checker, "check_health")

    def test_api_router(self):
        """测试API路由"""
        from src.api.data_router import router

        assert router is not None
        assert hasattr(router, "routes")
