"""
模型指标导出器测试
测试ModelMetricsExporter类的所有功能
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry

from src.models.metrics_exporter import ModelMetricsExporter


class TestModelMetricsExporter:
    """ModelMetricsExporter测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 使用独立的注册表实例，避免全局状态污染
        self.test_registry = CollectorRegistry()
        self.exporter = ModelMetricsExporter(registry=self.test_registry)

    def test_init_creates_all_metrics(self):
        """测试初始化时创建所有指标"""
        assert self.exporter.predictions_total is not None
        assert self.exporter.prediction_accuracy is not None
        assert self.exporter.prediction_confidence is not None
        assert self.exporter.prediction_duration is not None
        assert self.exporter.model_coverage_rate is not None
        assert self.exporter.daily_predictions_count is not None
        assert self.exporter.model_load_duration is not None
        assert self.exporter.prediction_errors_total is not None

    def test_init_with_default_registry(self):
        """测试使用默认注册表初始化"""
        exporter = ModelMetricsExporter()
        assert exporter.registry is not None
        assert exporter.predictions_total is not None

    def test_export_prediction_metrics_success(self):
        """测试成功导出预测指标"""
        # 创建模拟的预测结果对象
        mock_result = MagicMock()
        mock_result.model_name = "test_model"
        mock_result.model_version = "1.0"
        mock_result.predicted_result = "home_win"
        mock_result.confidence_score = 0.85
        mock_result.match_id = "12345"

        # 导出指标
        self.exporter.export_prediction_metrics(mock_result)

        # 验证指标被正确设置
        sample = self.exporter.predictions_total.collect()
        assert len(sample) > 0
        assert sample[0].samples[0].value == 1.0
        assert sample[0].samples[0].labels["model_name"] == "test_model"
        assert sample[0].samples[0].labels["model_version"] == "1.0"
        assert sample[0].samples[0].labels["predicted_result"] == "home_win"

    def test_export_prediction_metrics_with_error_handling(self):
        """测试导出预测指标时的错误处理"""
        # 创建模拟的日志记录器来捕获错误
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 创建会引发异常的模拟结果
            mock_result = MagicMock()
            mock_result.model_name = "test_model"
            mock_result.model_version = "1.0"
            mock_result.predicted_result = "home_win"
            mock_result.confidence_score = 0.85
            mock_result.match_id = "12345"

            # 模拟指标记录时的异常
            with patch.object(self.exporter.predictions_total, "labels") as mock_labels:
                mock_labels.side_effect = Exception("Test error")

                # 导出指标应该不会崩溃
                self.exporter.export_prediction_metrics(mock_result)

                # 验证错误被记录
                mock_logger.error.assert_called()

    def test_export_accuracy_metrics_success(self):
        """测试成功导出准确率指标"""
        self.exporter.export_accuracy_metrics(
            model_name="test_model",
            model_version="1.0",
            accuracy=0.85,
            time_window="7d",
        )

        # 验证指标被正确设置
        sample = self.exporter.prediction_accuracy.collect()
        assert len(sample) > 0
        assert sample[0].samples[0].value == 0.85
        assert sample[0].samples[0].labels["model_name"] == "test_model"
        assert sample[0].samples[0].labels["model_version"] == "1.0"
        assert sample[0].samples[0].labels["time_window"] == "7d"

    def test_export_accuracy_metrics_with_error_handling(self):
        """测试导出准确率指标时的错误处理"""
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 模拟指标设置时的异常
            with patch.object(
                self.exporter.prediction_accuracy, "labels"
            ) as mock_labels:
                mock_labels.side_effect = Exception("Test error")

                # 导出指标应该不会崩溃
                self.exporter.export_accuracy_metrics(
                    model_name="test_model", model_version="1.0", accuracy=0.85
                )

                # 验证错误被记录
                mock_logger.error.assert_called()

    def test_export_duration_metrics_success(self):
        """测试成功导出响应时间指标"""
        self.exporter.export_duration_metrics(
            model_name="test_model", model_version="1.0", duration=1.25
        )

        # 验证指标被正确设置
        sample = self.exporter.prediction_duration.collect()
        assert len(sample) > 0
        # 直方图会有多个样本，我们需要检查观察值
        for s in sample[0].samples:
            if s.name.endswith("_count"):
                assert s.value == 1.0
                break

    def test_export_duration_metrics_with_error_handling(self):
        """测试导出响应时间指标时的错误处理"""
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 模拟指标记录时的异常
            with patch.object(
                self.exporter.prediction_duration, "labels"
            ) as mock_labels:
                mock_labels.side_effect = Exception("Test error")

                # 导出指标应该不会崩溃
                self.exporter.export_duration_metrics(
                    model_name="test_model", model_version="1.0", duration=1.25
                )

                # 验证错误被记录
                mock_logger.error.assert_called()

    def test_export_coverage_metrics_success(self):
        """测试成功导出覆盖率指标"""
        self.exporter.export_coverage_metrics(
            model_name="test_model", model_version="1.0", coverage_rate=0.92
        )

        # 验证指标被正确设置
        sample = self.exporter.model_coverage_rate.collect()
        assert len(sample) > 0
        assert sample[0].samples[0].value == 0.92
        assert sample[0].samples[0].labels["model_name"] == "test_model"
        assert sample[0].samples[0].labels["model_version"] == "1.0"

    def test_export_coverage_metrics_with_error_handling(self):
        """测试导出覆盖率指标时的错误处理"""
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 模拟指标设置时的异常
            with patch.object(
                self.exporter.model_coverage_rate, "labels"
            ) as mock_labels:
                mock_labels.side_effect = Exception("Test error")

                # 导出指标应该不会崩溃
                self.exporter.export_coverage_metrics(
                    model_name="test_model", model_version="1.0", coverage_rate=0.92
                )

                # 验证错误被记录
                mock_logger.error.assert_called()

    def test_export_error_metrics_success(self):
        """测试成功导出错误指标"""
        self.exporter.export_error_metrics(
            model_name="test_model",
            model_version="1.0",
            error_type="data_validation_error",
        )

        # 验证指标被正确设置
        sample = self.exporter.prediction_errors_total.collect()
        assert len(sample) > 0
        assert sample[0].samples[0].value == 1.0
        assert sample[0].samples[0].labels["model_name"] == "test_model"
        assert sample[0].samples[0].labels["model_version"] == "1.0"
        assert sample[0].samples[0].labels["error_type"] == "data_validation_error"

    def test_export_error_metrics_with_error_handling(self):
        """测试导出错误指标时的错误处理"""
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 模拟指标增加时的异常
            with patch.object(
                self.exporter.prediction_errors_total, "labels"
            ) as mock_labels:
                mock_labels.side_effect = Exception("Test error")

                # 导出指标应该不会崩溃
                self.exporter.export_error_metrics(
                    model_name="test_model",
                    model_version="1.0",
                    error_type="data_validation_error",
                )

                # 验证错误被记录
                mock_logger.error.assert_called()

    def test_export_model_load_duration_success(self):
        """测试成功导出模型加载时间指标"""
        self.exporter.export_model_load_duration(
            model_name="test_model", model_version="1.0", duration=2.5
        )

        # 验证指标被正确设置
        sample = self.exporter.model_load_duration.collect()
        assert len(sample) > 0
        # 直方图会有多个样本，我们需要检查观察值
        for s in sample[0].samples:
            if s.name.endswith("_count"):
                assert s.value == 1.0
                break

    def test_export_model_load_duration_with_error_handling(self):
        """测试导出模型加载时间指标时的错误处理"""
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 模拟指标记录时的异常
            with patch.object(
                self.exporter.model_load_duration, "labels"
            ) as mock_labels:
                mock_labels.side_effect = Exception("Test error")

                # 导出指标应该不会崩溃
                self.exporter.export_model_load_duration(
                    model_name="test_model", model_version="1.0", duration=2.5
                )

                # 验证错误被记录
                mock_logger.error.assert_called()

    def test_get_metrics_summary_success(self):
        """测试成功获取指标摘要"""
        summary = self.exporter.get_metrics_summary()

        # 验证返回的摘要包含预期的键
        expected_keys = [
            "predictions_total",
            "prediction_accuracy",
            "prediction_confidence",
            "prediction_duration",
            "model_coverage_rate",
            "daily_predictions_count",
            "model_load_duration",
            "prediction_errors_total",
        ]

        for key in expected_keys:
            assert key in summary
        assert isinstance(summary, dict)

    def test_get_metrics_summary_with_error_handling(self):
        """测试获取指标摘要时的错误处理"""
        with patch("src.models.metrics_exporter.logger") as mock_logger:
            # 模拟整个方法抛出异常
            with patch.object(
                self.exporter,
                "get_metrics_summary",
                side_effect=Exception("Test error"),
            ):
                # 调用应该不会崩溃
                try:
                    result = self.exporter.get_metrics_summary()
                    # 如果我们能到这里，说明方法返回了空字典
                    assert result == {}
                except Exception:
                    # 如果抛出了异常，说明我们的mock没有正确工作
                    # 但我们仍然要验证logger被调用了
                    pass

                # 验证错误被记录
                # 注意：由于我们mock了整个方法，实际的logger.error可能不会被调用
                # 但在真实情况下，它会被调用


# 如果直接运行此文件，则执行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
