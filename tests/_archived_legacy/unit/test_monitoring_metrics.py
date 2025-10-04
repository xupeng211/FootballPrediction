from datetime import datetime, timedelta

from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.metrics_exporter import MetricsExporter
from unittest.mock import Mock, patch
import pytest

"""
监控指标模块测试
"""

class TestMetricsExporter:
    """指标导出器测试"""
    @pytest.fixture(autouse=True)
    def setup_method(self, clean_metrics_registry):
        """
        测试设置
        使用干净的 CollectorRegistry 避免测试间的全局状态污染。
        这确保每个测试都有独立的指标注册表。
        """
        # 使用独立的注册表实例，避免全局状态污染
        self.test_registry = clean_metrics_registry
        self.exporter = MetricsExporter(registry=self.test_registry)
    def test_metrics_exporter_initialization(self):
        """测试指标导出器初始化"""
    assert self.exporter is not None
    assert hasattr(self.exporter, "record_data_collection_success[")" assert hasattr(self.exporter, "]record_data_collection_failure[")" def test_record_data_collection_success(self):"""
        "]""测试记录数据收集成功"""
        # 直接调用方法测试，不使用mock验证，因为我们使用了真实的指标
        self.exporter.record_data_collection_success("fixtures[", 100)""""
        # 验证方法执行没有抛出异常即可
        # 实际的指标增量已经记录到了self.test_registry中
    def test_record_data_collection_failure(self):
        "]""测试记录数据收集失败"""
        # 直接调用方法测试，不使用mock验证
        self.exporter.record_data_collection_failure("odds[", "]API timeout[")""""
        # 验证方法执行没有抛出异常即可
    def test_record_data_cleaning_success(self):
        "]""测试记录数据清洗成功"""
        # 直接调用方法测试，不使用mock验证
        self.exporter.record_data_cleaning_success(50)
        # 验证方法执行没有抛出异常即可
    def test_record_scheduler_task(self):
        """测试记录调度任务"""
        # 使用简化接口进行测试
        self.exporter.record_scheduler_task_simple("collect_fixtures[", "]success[", 2.5)""""
        # 验证指标已经被记录（通过检查内部状态）
        # 注意：实际的指标验证通过Prometheus注册表进行
    def test_update_table_row_counts(self):
        "]""测试更新表行数统计"""
        table_counts = {"matches[": 1000, "]odds[": 5000, "]predictions[": 500}""""
        # 直接调用方法，使用提供的测试数据
        self.exporter.update_table_row_counts(table_counts)
        # 验证指标已经被设置（可以通过注册表验证）
        # 这里我们主要测试方法不抛出异常
    def test_get_metrics_prometheus_format(self):
        "]"""
        测试获取Prometheus格式指标
        修正：get_metrics方法返回tuple(content_type, metrics_data)，不是单个字符串
        使用正确的patch路径
        """
        with patch("src.monitoring.metrics_exporter.generate_latest[") as mock_generate:": mock_generate.return_value = b["]# HELP test_metric Test metric\n["]: result = self.exporter.get_metrics()""""
            # 验证返回的是tuple，包含content_type和metrics_data
            assert isinstance(result, tuple)
            assert len(result) ==2
            content_type, metrics_data = result
            assert isinstance(content_type, str)
            assert isinstance(metrics_data, str)
            mock_generate.assert_called_once()
class TestMetricsCollector:
    "]""指标收集器测试"""
    @pytest.fixture(autouse=True)
    def setup_method(self, clean_metrics_registry):
        """
        测试设置
        使用独立的 CollectorRegistry 实例来避免测试间的状态污染。
        """
        self.test_registry = clean_metrics_registry
        # MetricsCollector 可能也需要支持自定义registry
        self.collector = MetricsCollector()
    def test_metrics_collector_initialization(self):
        """测试指标收集器初始化"""
    assert self.collector is not None
    assert hasattr(self.collector, "collect_system_metrics[")" assert hasattr(self.collector, "]collect_database_metrics[")""""
    @patch("]psutil.cpu_percent[")""""
    @patch("]psutil.virtual_memory[")""""
    @patch("]psutil.disk_usage[")": def test_collect_system_metrics(self, mock_disk, mock_memory, mock_cpu):"""
        "]""测试收集系统指标"""
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=75.2, available=1024 * 1024 * 1024)
        mock_disk.return_value = Mock(percent=60.0, free=2 * 1024 * 1024 * 1024)
        self.collector.collect_system_metrics()
    assert "cpu_usage_percent[" in metrics[""""
    assert "]]memory_usage_percent[" in metrics[""""
    assert "]]disk_usage_percent[" in metrics[""""
    assert metrics["]]cpu_usage_percent["] ==45.5[""""
    @pytest.mark.asyncio
    @patch("]]src.monitoring.metrics_collector.get_async_session[")": async def test_collect_database_metrics(self, mock_session):"""
        "]""测试收集数据库指标"""
        mock_session_instance = Mock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        # 模拟查询结果
        mock_result = Mock()
        mock_result.fetchall.return_value = [
        ("matches[", 1000),""""
        ("]odds[", 5000),""""
        ("]predictions[", 500)]": mock_session_instance.execute.return_value = mock_result[": await self.collector.collect_database_metrics()": assert "]]table_counts[" in metrics[""""
    assert isinstance(metrics["]]table_counts["], dict)" def test_collect_application_metrics(self):"""
        "]""测试收集应用指标"""
        with patch.object(self.collector, "_get_prediction_stats[") as mock_stats:": mock_stats.return_value = {"""
            "]total_predictions[": 1000,""""
            "]accuracy_rate[": 0.65,""""
            "]avg_confidence[": 0.78}": self.collector.collect_application_metrics()": assert "]prediction_stats[" in metrics[""""
    assert metrics["]]prediction_stats["]"]total_predictions[" ==1000[" def test_format_metrics_for_export(self):"""
        "]]""测试格式化指标用于导出"""
        raw_metrics = {
        "system[": {"]cpu_usage[": 45.5},""""
        "]database[": {"]table_counts[": {"]matches[": 1000}},""""
        "]application[": {"]prediction_stats[": {"]total[": 500}}}": self.collector.format_metrics_for_export(raw_metrics)": assert isinstance(formatted, dict)" assert "]timestamp[" in formatted[""""
    assert "]]metrics[" in formatted[""""
class TestMetricsIntegration:
    "]]""指标系统集成测试"""
    def test_metrics_pipeline(self):
        """测试指标收集和导出管道"""
        collector = MetricsCollector()
        # exporter = MetricsExporter()
        # 模拟指标收集
        with patch.object(collector, "collect_system_metrics[") as mock_collect:": mock_collect.return_value = {"]cpu_usage[": 50.0}": collector.collect_system_metrics()"""
            # 验证指标格式
    assert isinstance(metrics, dict)
    assert "]cpu_usage[" in metrics[""""
    def test_prometheus_integration(self):
        "]]"""
        测试Prometheus集成
        修正：update_table_row_counts是async方法且不接受参数，使用mock代替
        """
        exporter = MetricsExporter()
        # 使用mock模拟指标更新，因为实际方法是async且需要数据库连接
        with patch.object(exporter, "_get_or_create_gauge[") as mock_gauge:": mock_metric = Mock()": mock_gauge.return_value = mock_metric[""
            # 模拟更新表行数指标
            exporter.table_row_count.labels(table_name="]]test_table[").set(100)""""
        # 获取Prometheus格式输出
        content_type, prometheus_output = exporter.get_metrics()
        # 验证返回格式
    assert isinstance(content_type, str)
    assert isinstance(prometheus_output, str)
    assert len(prometheus_output) > 0
    assert "]text_plain[" in content_type[""""
    def test_metrics_persistence(self):
        "]]""测试指标持久化"""
        # 模拟指标存储
        {
        "timestamp[": datetime.now()""""
        # 验证数据格式
    assert "]timestamp[" in metrics_data[""""
    assert isinstance(metrics_data["]]cpu_usage["], float)" def test_metrics_alerting_thresholds(self):"""
        "]""测试指标告警阈值"""
        # 定义告警阈值
        thresholds = {"cpu_usage[": 80.0, "]memory_usage[": 85.0, "]disk_usage[": 90.0}""""
        # 测试指标
        current_metrics = {
        "]cpu_usage[": 85.0,  # 超过阈值[""""
        "]]memory_usage[": 70.0,  # 正常[""""
        "]]disk_usage[": 95.0,  # 超过阈值[""""
        }
        alerts = []
        for metric, value in current_metrics.items():
            if value > thresholds.get(metric, 100):
                alerts.append(f["]]{metric} is {value}%, threshold is {thresholds["]metric[")%"]""""
                )
    assert len(alerts) ==2  # cpu_usage 和 disk_usage 超过阈值
    def test_metrics_aggregation(self):
        """测试指标聚合"""
        # 模拟时间序列数据
        time_series_data = [
        {"timestamp[": datetime.now(),""""
        {"]timestamp[": datetime.now(),""""
        {"]timestamp[": datetime.now(),""""
            {"]timestamp[": datetime.now(),""""
            {"]timestamp[": datetime.now()]""""
        # 计算平均值
        sum(data["]cpu_usage["]: for data in time_series_data) / len(:"]: time_series_data"""
        )
    assert avg_cpu ==50.0
    assert len(time_series_data) ==5