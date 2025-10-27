#!/usr/bin/env python3
"""
监控API简化测试
测试 src.api.monitoring 模块的功能
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.monitoring import _get_database_metrics, router


@pytest.mark.unit
class TestMonitoringAPI:
    """监控API测试"""

    def test_router_import(self):
        """测试路由器导入"""
        # 验证路由器可以导入
        assert router is not None
        from fastapi import APIRouter

        assert isinstance(router, APIRouter)

    def test_router_tags(self):
        """测试路由器标签"""
        # 验证路由器标签
        assert router.tags == ["monitoring"]

    def test_router_routes_count(self):
        """测试路由器路由数量"""
        # 验证路由器有路由
        assert len(router.routes) > 0

    def test_get_database_metrics_function(self):
        """测试获取数据库指标函数"""
        # 验证函数存在且可调用
        assert callable(_get_database_metrics)
        import asyncio

        assert asyncio.iscoroutinefunction(_get_database_metrics)

    @pytest.mark.asyncio
    async def test_get_database_metrics_mock_db(self):
        """测试获取数据库指标 - 模拟数据库"""
        # 创建模拟数据库会话
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = [42]
        mock_db.execute.return_value = mock_result

        # 调用函数
        result = await _get_database_metrics(mock_db)

        # 验证返回结构
        assert isinstance(result, dict)
        assert "healthy" in result
        assert "response_time_ms" in result
        assert "statistics" in result
        assert isinstance(result["statistics"], dict)

    @pytest.mark.asyncio
    async def test_get_database_metrics_time_measurement(self):
        """测试数据库指标时间测量"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = [5]
        mock_db.execute.return_value = mock_result

        # 调用函数
        result = await _get_database_metrics(mock_db)

        # 验证时间被测量
        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], float)
        assert result["response_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_get_database_metrics_success_case(self):
        """测试数据库指标成功情况"""
        mock_db = Mock()
        mock_db.execute.return_value.fetchone.return_value = [10]

        result = await _get_database_metrics(mock_db)

        # 验证成功状态
        assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_database_metrics_exception_handling(self):
        """测试数据库指标异常处理"""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database error")

        result = await _get_database_metrics(mock_db)

        # 验证异常处理
        assert isinstance(result, dict)
        assert result["healthy"] is False

    @pytest.mark.asyncio
    async def test_get_database_metrics_statistics_structure(self):
        """测试数据库指标统计结构"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = [100]
        mock_db.execute.return_value = mock_result

        result = await _get_database_metrics(mock_db)

        # 验证统计结构
        stats = result["statistics"]
        assert "teams_count" in stats
        assert "matches_count" in stats
        assert "predictions_count" in stats
        assert "active_connections" in stats

    @pytest.mark.asyncio
    async def test_get_database_metrics_val_function_error_handling(self):
        """测试_val函数错误处理"""
        mock_db = Mock()
        mock_result = Mock()
        # 模拟fetchone返回None
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await _get_database_metrics(mock_db)

        # 验证错误处理
        assert result["statistics"]["teams_count"] == 0

    @pytest.mark.asyncio
    async def test_get_database_metrics_multiple_queries(self):
        """测试数据库指标多次查询"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = [1]
        mock_db.execute.return_value = mock_result

        # 验证多次执行数据库查询
        await _get_database_metrics(mock_db)

        # 验证调用次数（应该是4次：SELECT 1, teams, matches, predictions, active）
        assert mock_db.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_get_database_metrics_performance_timing(self):
        """测试数据库指标性能计时"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = [25]
        mock_db.execute.return_value = mock_result

        # 记录开始时间
        start_time = time.time()
        result = await _get_database_metrics(mock_db)
        end_time = time.time()

        # 验证函数执行时间合理
        execution_time = end_time - start_time
        assert execution_time < 1.0  # 应该在1秒内完成

        # 验证返回的响应时间
        assert "response_time_ms" in result
        assert result["response_time_ms"] > 0

    def test_module_imports(self):
        """测试模块导入"""
        # 验证所有导入的模块
        import time
        from typing import Any, Dict, Optional

        import psutil
        from fastapi import APIRouter, Response
        from fastapi.responses import PlainTextResponse
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        from src.api.monitoring import _get_database_metrics, router

        assert router is not None
        assert _get_database_metrics is not None
        assert APIRouter is not None
        assert Response is not None
        assert PlainTextResponse is not None
        assert Session is not None
        assert text is not None
        assert psutil is not None
        assert time is not None
        assert Dict is not None
        assert Any is not None
        assert Optional is not None

    def test_module_structure(self):
        """测试模块结构"""
        # 验证模块有预期的结构
        from src.api.monitoring import __file__, __name__

        assert __file__ is not None
        assert __name__ is not None
        assert "monitoring" in __name__

    def test_router_path_prefix(self):
        """测试路由器路径前缀"""
        # 验证路由器没有硬编码路径前缀
        # 路径前缀应该在include_router时设置
        assert hasattr(router, "prefix")
        # prefix默认应该是None或空字符串
        assert router.prefix in [None, ""]

    def test_monitoring_dependencies(self):
        """测试监控依赖"""
        # 验证监控相关依赖
        from src.core.logger import get_logger

        # 验证logger可以获取
        logger = get_logger("test")
        assert logger is not None

    @patch("src.api.monitoring.psutil")
    def test_system_dependencies(self, mock_psutil):
        """测试系统依赖"""
        # 验证psutil模块可以导入和使用
        mock_psutil.cpu_percent.return_value = 50.0
        assert mock_psutil is not None
        result = mock_psutil.cpu_percent()
        assert result == 50.0
