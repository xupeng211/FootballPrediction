# TODO: Consider creating a fixture for 23 repeated Mock creations

# TODO: Consider creating a fixture for 23 repeated Mock creations

from unittest.mock import Mock, patch, AsyncMock
"""
性能监控集成模块测试
Performance Integration Module Tests
"""

import pytest
from typing import Dict, Any

from fastapi import FastAPI

from src.performance.integration import (
    PerformanceMonitoringIntegration,
    get_performance_integration,
    setup_performance_monitoring,
    integrate_performance_monitoring,
    start_performance_profiling,
    stop_performance_profiling,
    generate_performance_report,
)


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.critical

class TestPerformanceMonitoringIntegration:
    """性能监控集成器测试类"""

    @patch("src.performance.integration.get_settings")
    def test_init_default_settings(self, mock_get_settings):
        """测试使用默认设置初始化"""
        # 模拟配置
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "PERFORMANCE_MONITORING_ENABLED": True,
            "PERFORMANCE_MONITORING_SAMPLE_RATE": 1.0,
            "PERFORMANCE_PROFILING_ENABLED": False,
            "SLOW_REQUEST_THRESHOLD": 1.0,
            "CRITICAL_REQUEST_THRESHOLD": 5.0,
            "SLOW_QUERY_THRESHOLD": 0.1,
            "DB_POOL_MIN": 1,
            "DB_POOL_MAX": 20,
            "CACHE_TTL": 3600,
            "CACHE_MAX_SIZE": 1000,
        }.get(key, default)
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()

        assert integration.enabled is True
        assert integration.sample_rate == 1.0
        assert integration.profiling_enabled is False

    @patch("src.performance.integration.get_settings")
    def test_init_disabled(self, mock_get_settings):
        """测试禁用性能监控"""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()

        assert integration.enabled is False
        assert integration.sample_rate == 0.0

    @patch("src.performance.integration.PerformanceMonitoringMiddleware")
    @patch("src.performance.integration.performance_router")
    def test_integrate_with_fastapi(self, mock_router, mock_middleware):
        """测试集成到FastAPI应用"""
        # 设置模拟
        mock_app = Mock(spec=FastAPI)
        mock_middleware_instance = Mock()
        mock_middleware.return_value = mock_middleware_instance

        with patch("src.performance.integration.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.get.side_effect = lambda key, default=None: {
                "PERFORMANCE_MONITORING_ENABLED": True,
                "PERFORMANCE_MONITORING_SAMPLE_RATE": 0.5,
                "PERFORMANCE_PROFILING_ENABLED": False,
            }.get(key, default)
            mock_get_settings.return_value = mock_settings

            integration = PerformanceMonitoringIntegration()
            integration.integrate_with_fastapi(mock_app)

            # 验证中间件被添加
            mock_app.add_middleware.assert_called_once_with(
                mock_middleware,
                track_memory=True,
                track_concurrency=True,
                sample_rate=0.5,
            )

            # 验证路由被包含
            mock_app.include_router.assert_called_once_with(
                mock_router, tags=["performance"]
            )

    @patch("src.performance.integration.get_settings")
    def test_integrate_with_fastapi_disabled(self, mock_get_settings):
        """测试禁用时集成到FastAPI"""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()
        mock_app = Mock(spec=FastAPI)

        # 应该不添加任何中间件或路由
        integration.integrate_with_fastapi(mock_app)

        mock_app.add_middleware.assert_not_called()
        mock_app.include_router.assert_not_called()

    @patch("src.performance.integration.DatabaseQueryProfiler")
    @patch("src.performance.integration.get_profiler")
    def test_initialize_database_monitoring(self, mock_get_profiler, mock_db_profiler):
        """测试初始化数据库监控"""
        mock_get_settings.return_value = Mock()
        mock_get_settings.return_value.get.return_value = True

        integration = PerformanceMonitoringIntegration()
        integration.initialize_database_monitoring()

        # 验证数据库查询分析器被创建
        mock_db_profiler.assert_called_once()

    @patch("src.performance.integration.get_settings")
    def test_initialize_database_monitoring_disabled(self, mock_get_settings):
        """测试禁用时初始化数据库监控"""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()

        with patch(
            "src.performance.integration.DatabaseQueryProfiler"
        ) as mock_db_profiler:
            integration.initialize_database_monitoring()

            # 应该不创建任何东西
            mock_db_profiler.assert_not_called()

    @patch("src.performance.integration.start_profiling")
    @patch("src.performance.integration.get_settings")
    def test_start_profiling(self, mock_get_settings, mock_start_profiling):
        """测试启动性能分析"""
        mock_settings = Mock()
        mock_settings.get.return_value = True
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()
        integration.start_profiling()

        mock_start_profiling.assert_called_once()

    @patch("src.performance.integration.get_settings")
    def test_start_profiling_disabled(self, mock_get_settings):
        """测试禁用时启动性能分析"""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()

        with patch(
            "src.performance.integration.start_profiling"
        ) as mock_start_profiling:
            integration.start_profiling()

            mock_start_profiling.assert_not_called()

    @patch("src.performance.integration.stop_profiling")
    def test_stop_profiling(self, mock_stop_profiling):
        """测试停止性能分析"""
        mock_stop_profiling.return_value = {"function_count": 10}

        integration = PerformanceMonitoringIntegration()
        integration.stop_profiling()

        mock_stop_profiling.assert_called_once()

    def test_get_performance_config(self):
        """测试获取性能配置"""
        with patch("src.performance.integration.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.get.side_effect = lambda key, default=None: {
                "PERFORMANCE_MONITORING_SAMPLE_RATE": 0.8,
                "PERFORMANCE_PROFILING_ENABLED": True,
                "SLOW_REQUEST_THRESHOLD": 2.0,
                "CRITICAL_REQUEST_THRESHOLD": 10.0,
                "SLOW_QUERY_THRESHOLD": 0.2,
                "DB_POOL_MIN": 5,
                "DB_POOL_MAX": 50,
                "CACHE_TTL": 7200,
                "CACHE_MAX_SIZE": 2000,
            }.get(key, default)
            mock_get_settings.return_value = mock_settings

            integration = PerformanceMonitoringIntegration()
            _config = integration.get_performance_config()

            assert _config["enabled"] is True
            assert _config["sample_rate"] == 0.8
            assert _config["profiling_enabled"] is True
            assert "thresholds" in config
            assert _config["thresholds"]["response_time"]["slow"] == 2.0
            assert _config["thresholds"]["database"]["slow_query"] == 0.2

    def test_update_config(self):
        """测试更新配置"""
        integration = PerformanceMonitoringIntegration()

        # 创建一个模拟的中间件
        integration._monitoring_middleware = Mock()

        # 更新配置
        new_config = {
            "sample_rate": 0.5,
            "profiling_enabled": True,
            "thresholds": {"response_time": {"slow": 2.0}},
        }

        integration.update_config(new_config)

        # 验证配置被更新
        assert integration.sample_rate == 0.5
        assert integration.profiling_enabled is True

        # 验证中间件配置被更新
        integration._monitoring_middleware.sample_rate = 0.5

    @patch("src.performance.integration.PerformanceAnalyzer")
    @patch("src.performance.integration.get_profiler")
    def test_create_performance_report(self, mock_get_profiler, mock_analyzer_class):
        """测试创建性能报告"""
        # 设置模拟
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.generate_performance_report.return_value = {"test": "report"}
        mock_analyzer.export_report.return_value = '{"test": "report"}'

        mock_profiler = Mock()
        mock_get_profiler.return_value = mock_profiler

        integration = PerformanceMonitoringIntegration()
        integration.enabled = True

        report = integration.create_performance_report()

        # 验证报告生成和导出
        mock_analyzer.generate_performance_report.assert_called_once()
        mock_analyzer.export_report.assert_called_once()
        assert report == '{"test": "report"}'

    @patch("src.performance.integration.get_settings")
    def test_create_performance_report_disabled(self, mock_get_settings):
        """测试禁用时创建性能报告"""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_get_settings.return_value = mock_settings

        integration = PerformanceMonitoringIntegration()

        # 应该返回None
        report = integration.create_performance_report()
        assert report is None

    def test_setup_alerting(self):
        """测试设置告警"""
        integration = PerformanceMonitoringIntegration()
        integration.enabled = True

        # 目前是TODO，但应该不抛出错误
        integration.setup_alerting()

    def test_cleanup(self):
        """测试清理资源"""
        integration = PerformanceMonitoringIntegration()
        integration.profiling_enabled = True

        with patch("src.performance.integration.stop_profiling") as mock_stop:
            integration.cleanup()

            mock_stop.assert_called_once()

            # 验证资源被清理
            assert integration._monitoring_middleware is None
            assert integration._db_monitor is None
            assert integration._cache_monitor is None
            assert integration._task_monitor is None


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_performance_integration_singleton(self):
        """测试获取全局集成实例（单例）"""
        # 重置全局变量
        import src.performance.integration

        src.performance.integration._integration = None

        integration1 = get_performance_integration()
        integration2 = get_performance_integration()

        # 应该返回同一个实例
        assert integration1 is integration2
        assert isinstance(integration1, PerformanceMonitoringIntegration)

    @patch("src.performance.integration.get_performance_integration")
    def test_setup_performance_monitoring(self, mock_get_integration):
        """测试设置性能监控"""
        mock_integration = Mock()
        mock_get_integration.return_value = mock_integration

        mock_app = Mock(spec=FastAPI)

        # 测试带应用参数
        _result = setup_performance_monitoring(mock_app)

        # 验证调用
        mock_integration.integrate_with_fastapi.assert_called_once_with(mock_app)
        mock_integration.initialize_database_monitoring.assert_called_once()
        mock_integration.initialize_cache_monitoring.assert_called_once()
        mock_integration.initialize_task_monitoring.assert_called_once()
        mock_integration.setup_alerting.assert_called_once()

        # 返回值应该是集成实例
        assert _result == mock_integration

        # 测试不带应用参数
        mock_integration.reset_mock()
        setup_performance_monitoring()

        mock_integration.integrate_with_fastapi.assert_not_called()
        mock_integration.initialize_database_monitoring.assert_called_once()

    @patch("src.performance.integration.setup_performance_monitoring")
    def test_integrate_performance_monitoring(self, mock_setup):
        """测试集成性能监控（便捷函数）"""
        mock_app = Mock(spec=FastAPI)

        integrate_performance_monitoring(mock_app)

        mock_setup.assert_called_once_with(mock_app)

    @patch("src.performance.integration.get_performance_integration")
    def test_start_performance_profiling(self, mock_get_integration):
        """测试启动性能分析（便捷函数）"""
        mock_integration = Mock()
        mock_get_integration.return_value = mock_integration

        start_performance_profiling()

        mock_integration.start_profiling.assert_called_once()

    @patch("src.performance.integration.get_performance_integration")
    def test_stop_performance_profiling(self, mock_get_integration):
        """测试停止性能分析（便捷函数）"""
        mock_integration = Mock()
        mock_get_integration.return_value = mock_integration

        stop_performance_profiling()

        mock_integration.stop_profiling.assert_called_once()

    @patch("src.performance.integration.get_performance_integration")
    def test_generate_performance_report(self, mock_get_integration):
        """测试生成性能报告（便捷函数）"""
        mock_integration = Mock()
        mock_integration.create_performance_report.return_value = '{"test": "report"}'
        mock_get_integration.return_value = mock_integration

        report = generate_performance_report()

        assert report == '{"test": "report"}'
        mock_integration.create_performance_report.assert_called_once()


class TestErrorHandling:
    """错误处理测试"""

    def test_integrate_with_fastapi_error(self):
        """测试集成时的错误处理"""
        integration = PerformanceMonitoringIntegration()
        integration.enabled = True

        mock_app = Mock(spec=FastAPI)
        mock_app.add_middleware.side_effect = Exception("Middleware error")

        with patch("src.performance.integration.logger") as mock_logger:
            # 应该不抛出错误，只记录日志
            integration.integrate_with_fastapi(mock_app)

            mock_logger.error.assert_called_once()
            assert "Failed to integrate performance monitoring" in str(
                mock_logger.error.call_args
            )

    def test_start_profiling_error(self):
        """测试启动分析时的错误处理"""
        integration = PerformanceMonitoringIntegration()
        integration.profiling_enabled = True

        with patch("src.performance.integration.start_profiling") as mock_start:
            mock_start.side_effect = Exception("Profiling error")

            with patch("src.performance.integration.logger") as mock_logger:
                integration.start_profiling()

                mock_logger.error.assert_called_once()
                assert "Failed to start profiling" in str(mock_logger.error.call_args)

    def test_create_performance_report_error(self):
        """测试创建报告时的错误处理"""
        integration = PerformanceMonitoringIntegration()
        integration.enabled = True

        with patch("src.performance.integration.PerformanceAnalyzer") as mock_analyzer:
            mock_analyzer.side_effect = Exception("Analyzer error")

            with patch("src.performance.integration.logger") as mock_logger:
                report = integration.create_performance_report()

                # 应该返回None
                assert report is None
                mock_logger.error.assert_called_once()
                assert "Failed to create performance report" in str(
                    mock_logger.error.call_args
                )
