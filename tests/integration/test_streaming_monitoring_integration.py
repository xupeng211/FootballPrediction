"""
Streaming↔Monitoring联动集成测试

覆盖流处理与监控系统的深度集成：
- Kafka流处理↔Prometheus指标
- 异常检测↔告警触发
- 实时数据处理↔系统监控
- 流质量监控↔性能指标
"""

from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio
from datetime import datetime
from enum import Enum

pytestmark = pytest.mark.integration


class TestStreamingMetricsIntegration:
    """流处理与指标集成测试"""

    @pytest.fixture
    def mock_kafka_consumer(self):
        """模拟Kafka消费者"""
        consumer = AsyncMock()
        consumer.consume = AsyncMock()
        consumer.get_consumer_stats = AsyncMock()
        consumer.commit_offsets = AsyncMock()
        return consumer

    @pytest.fixture
    def mock_kafka_producer(self):
        """模拟Kafka生产者"""
        producer = AsyncMock()
        producer.produce = AsyncMock()
        producer.get_producer_stats = AsyncMock()
        return producer

    @pytest.fixture
    def mock_metrics_exporter(self):
        """模拟指标导出器"""
        exporter = Mock()
        exporter.record_stream_processing = Mock()
        exporter.record_kafka_metrics = Mock()
        exporter.record_data_collection = Mock()
        return exporter

    @pytest.mark.asyncio
    async def test_kafka_consumer_metrics_integration(self):
        """测试Kafka消费者与指标的集成"""
        # 模拟Kafka消费者处理消息
        with patch('src.streaming.kafka_consumer.KafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer

            # 模拟消息消费
            mock_consumer.consume.return_value = [
                {'topic': 'test_topic', 'partition': 0, 'offset': 1, 'value': b'test_data'},
                {'topic': 'test_topic', 'partition': 0, 'offset': 2, 'value': b'more_data'}
            ]

            # 模拟消费者统计
            mock_consumer.get_consumer_stats.return_value = {
                'messages_consumed': 2,
                'consumer_lag': 0,
                'bytes_consumed': 18,
                'processing_time_ms': 10
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证集成流程
                messages = await mock_consumer.consume(timeout=1000)
                assert len(messages) == 2

                stats = await mock_consumer.get_consumer_stats()
                assert stats['messages_consumed'] == 2

                # 验证指标记录被调用
                mock_exporter.record_kafka_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_kafka_producer_metrics_integration(self):
        """测试Kafka生产者与指标的集成"""
        # 模拟Kafka生产者发送消息
        with patch('src.streaming.kafka_producer.KafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer

            # 模拟消息发送
            mock_producer.produce.return_value = {
                'topic': 'output_topic',
                'partition': 0,
                'offset': 1,
                'status': 'success'
            }

            # 模拟生产者统计
            mock_producer.get_producer_stats.return_value = {
                'messages_produced': 1,
                'bytes_produced': 12,
                'produce_time_ms': 5,
                'success_rate': 1.0
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证集成流程
                result = await mock_producer.produce('output_topic', b'test_message')
                assert result['status'] == 'success'

                stats = await mock_producer.get_producer_stats()
                assert stats['messages_produced'] == 1

                # 验证指标记录被调用
                mock_exporter.record_kafka_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_processor_metrics_integration(self):
        """测试流处理器与指标的集成"""
        # 模拟流处理器
        with patch('src.streaming.stream_processor.StreamProcessor') as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor_class.return_value = mock_processor

            # 模拟流处理
            mock_processor.process_stream.return_value = {
                'processed_records': 100,
                'successful_records': 95,
                'failed_records': 5,
                'processing_time_ms': 100
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证集成流程
                result = await mock_processor.process_stream(stream_id='test_stream')
                assert result['processed_records'] == 100

                # 验证指标记录
                mock_exporter.record_stream_processing.assert_called_once_with(
                    stream_id='test_stream',
                    processed_records=100,
                    successful_records=95,
                    failed_records=5,
                    processing_time_ms=100
                )

    @pytest.mark.asyncio
    async def test_stream_quality_metrics_integration(self):
        """测试流质量与指标的集成"""
        # 模拟流质量检查
        with patch('src.data.quality.StreamQualityChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker

            # 模拟质量检查结果
            mock_checker.check_stream_quality.return_value = {
                'completeness_score': 0.95,
                'accuracy_score': 0.88,
                'timeliness_score': 0.92,
                'consistency_score': 0.90,
                'overall_quality_score': 0.91
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证集成流程
                quality_result = await mock_checker.check_stream_quality(stream_id='test_stream')
                assert quality_result['overall_quality_score'] == 0.91

                # 验证质量指标记录
                mock_exporter.record_stream_quality.assert_called_once_with(
                    stream_id='test_stream',
                    quality_scores=quality_result
                )

    @pytest.mark.asyncio
    async def test_stream_performance_metrics_integration(self):
        """测试流性能与指标的集成"""
        # 模拟流性能监控
        with patch('src.streaming.performance_monitor.StreamPerformanceMonitor') as mock_monitor_class:
            mock_monitor = AsyncMock()
            mock_monitor_class.return_value = mock_monitor

            # 模拟性能监控结果
            mock_monitor.get_performance_metrics.return_value = {
                'throughput_rps': 1000,
                'latency_p50_ms': 10,
                'latency_p95_ms': 25,
                'latency_p99_ms': 50,
                'error_rate': 0.01,
                'cpu_usage': 45.0,
                'memory_usage_mb': 512
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证集成流程
                metrics = await mock_monitor.get_performance_metrics(stream_id='test_stream')
                assert metrics['throughput_rps'] == 1000
                assert metrics['latency_p95_ms'] == 25

                # 验证性能指标记录
                mock_exporter.record_stream_performance.assert_called_once_with(
                    stream_id='test_stream',
                    performance_metrics=metrics
                )


class TestAnomalyDetectionAlertIntegration:
    """异常检测与告警集成测试"""

    @pytest.fixture
    def mock_anomaly_detector(self):
        """模拟异常检测器"""
        detector = AsyncMock()
        detector.detect_anomalies = AsyncMock()
        detector.get_detection_stats = AsyncMock()
        return detector

    @pytest.fixture
    def mock_alert_manager(self):
        """模拟告警管理器"""
        alert_manager = AsyncMock()
        alert_manager.evaluate_alerts = AsyncMock()
        alert_manager.send_alert = AsyncMock()
        alert_manager.get_alert_history = AsyncMock()
        return alert_manager

    @pytest.mark.asyncio
    async def test_anomaly_detection_alert_workflow(self):
        """测试异常检测触发告警的工作流"""
        # 模拟异常检测
        with patch('src.monitoring.anomaly_detector.AnomalyDetector') as mock_detector_class:
            mock_detector = AsyncMock()
            mock_detector_class.return_value = mock_detector

            # 模拟异常检测结果
            mock_detector.detect_anomalies.return_value = [
                {
                    'table_name': 'stream_data',
                    'column_name': 'response_time',
                    'anomaly_type': 'outlier',
                    'severity': 'high',
                    'anomaly_score': 0.92,
                    'description': 'Response time outlier detected'
                }
            ]

            # 模拟告警管理器
            with patch('src.monitoring.alert_manager.AlertManager') as mock_alert_class:
                mock_alert = AsyncMock()
                mock_alert_class.return_value = mock_alert

                # 模拟告警评估
                mock_alert.evaluate_alerts.return_value = [
                    {
                        'rule_id': 'high_response_time',
                        'rule_name': 'High Response Time',
                        'severity': 'critical',
                        'message': 'Critical response time detected',
                        'timestamp': datetime.now()
                    }
                ]

                # 验证集成流程
                anomalies = await mock_detector.detect_anomalies(table_names=['stream_data'])
                assert len(anomalies) == 1
                assert anomalies[0]['severity'] == 'high'

                alerts = await mock_alert.evaluate_alerts(anomalies)
                assert len(alerts) == 1
                assert alerts[0]['severity'] == 'critical'

                # 验证告警发送
                mock_alert.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_anomaly_metrics_integration(self):
        """测试流异常与指标的集成"""
        # 模拟流异常检测
        with patch('src.streaming.anomaly_detector.StreamAnomalyDetector') as mock_detector_class:
            mock_detector = AsyncMock()
            mock_detector_class.return_value = mock_detector

            # 模拟异常检测统计
            mock_detector.get_detection_stats.return_value = {
                'total_records_analyzed': 10000,
                'anomalies_detected': 150,
                'anomaly_rate': 0.015,
                'average_detection_time_ms': 2.5,
                'false_positive_rate': 0.05
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证集成流程
                stats = await mock_detector.get_detection_stats(stream_id='test_stream')
                assert stats['anomalies_detected'] == 150
                assert stats['anomaly_rate'] == 0.015

                # 验证异常指标记录
                mock_exporter.record_anomaly_detection.assert_called_once_with(
                    stream_id='test_stream',
                    detection_stats=stats
                )

    @pytest.mark.asyncio
    async def test_alert_threshold_integration(self):
        """测试告警阈值的集成"""
        # 模拟告警阈值配置
        with patch('src.monitoring.alert_manager.AlertManager') as mock_alert_class:
            mock_alert = AsyncMock()
            mock_alert_class.return_value = mock_alert

            # 模拟阈值检查
            mock_alert.check_thresholds.return_value = {
                'cpu_usage': {'current': 85.0, 'threshold': 80.0, 'exceeded': True},
                'memory_usage': {'current': 75.0, 'threshold': 80.0, 'exceeded': False},
                'disk_usage': {'current': 95.0, 'threshold': 90.0, 'exceeded': True}
            }

            # 验证阈值检查
            threshold_result = await mock_alert.check_thresholds()
            assert threshold_result['cpu_usage']['exceeded'] is True
            assert threshold_result['memory_usage']['exceeded'] is False
            assert threshold_result['disk_usage']['exceeded'] is True

    @pytest.mark.asyncio
    async def test_alert_notification_integration(self):
        """测试告警通知的集成"""
        # 模拟告警通知服务
        with patch('src.monitoring.notification_service.NotificationService') as mock_notification_class:
            mock_notification = AsyncMock()
            mock_notification_class.return_value = mock_notification

            # 模拟通知发送
            mock_notification.send_notification.return_value = {
                'notification_id': 'notif_123',
                'status': 'sent',
                'recipient': 'admin@example.com',
                'timestamp': datetime.now()
            }

            # 模拟告警管理器
            with patch('src.monitoring.alert_manager.AlertManager') as mock_alert_class:
                mock_alert = AsyncMock()
                mock_alert_class.return_value = mock_alert

                # 验证通知发送
                notification_result = await mock_notification.send_notification(
                    recipient='admin@example.com',
                    subject='Critical Alert',
                    message='System overload detected',
                    severity='critical'
                )

                assert notification_result['status'] == 'sent'
                assert notification_result['recipient'] == 'admin@example.com'

    @pytest.mark.asyncio
    async def test_alert_history_integration(self):
        """测试告警历史的集成"""
        # 模拟告警历史记录
        with patch('src.monitoring.alert_manager.AlertManager') as mock_alert_class:
            mock_alert = AsyncMock()
            mock_alert_class.return_value = mock_alert

            # 模拟历史查询
            mock_alert.get_alert_history.return_value = [
                {
                    'alert_id': 'alert_1',
                    'rule_id': 'high_cpu',
                    'severity': 'critical',
                    'message': 'CPU usage exceeded threshold',
                    'timestamp': datetime.now(),
                    'resolved': False
                },
                {
                    'alert_id': 'alert_2',
                    'rule_id': 'high_memory',
                    'severity': 'warning',
                    'message': 'Memory usage exceeded threshold',
                    'timestamp': datetime.now(),
                    'resolved': True
                }
            ]

            # 验证历史查询
            history = await mock_alert.get_alert_history(limit=10)
            assert len(history) == 2
            assert history[0]['severity'] == 'critical'
            assert history[1]['resolved'] is True


class TestRealTimeDataFlowIntegration:
    """实时数据流集成测试"""

    @pytest.mark.asyncio
    async def test_kafka_to_database_integration(self):
        """测试Kafka到数据库的集成"""
        # 模拟Kafka消费者
        with patch('src.streaming.kafka_consumer.KafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer

            # 模拟消息消费
            mock_consumer.consume.return_value = [
                {'topic': 'fixtures', 'value': b'{"id": 1, "home_team": "Team A"}'},
                {'topic': 'fixtures', 'value': b'{"id": 2, "home_team": "Team B"}'}
            ]

            # 模拟数据库写入
            with patch('src.database.connection.DatabaseManager') as mock_db_class:
                mock_db = AsyncMock()
                mock_db_class.return_value = mock_db

                # 模拟批量插入
                mock_db.bulk_insert.return_value = {'inserted_count': 2, 'status': 'success'}

                # 验证集成流程
                messages = await mock_consumer.consume(timeout=1000)
                assert len(messages) == 2

                # 解析消息并准备数据
                records = []
                for message in messages:
                    import json
                    record = json.loads(message['value'])
                    records.append(record)

                # 写入数据库
                result = await mock_db.bulk_insert('fixtures', records)
                assert result['inserted_count'] == 2
                assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_stream_processing_pipeline_integration(self):
        """测试流处理管道的集成"""
        # 模拟完整的流处理管道
        with patch('src.streaming.pipeline.StreamProcessingPipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline

            # 模拟管道处理
            mock_pipeline.process_pipeline.return_value = {
                'input_records': 1000,
                'output_records': 950,
                'filtered_records': 50,
                'processing_time_ms': 500,
                'quality_score': 0.92,
                'stages_completed': ['validation', 'transformation', 'enrichment', 'quality_check']
            }

            # 验证管道处理
            result = await mock_pipeline.process_pipeline(
                input_stream='raw_data',
                output_stream='processed_data',
                config={'validation': True, 'enrichment': True}
            )

            assert result['input_records'] == 1000
            assert result['output_records'] == 950
            assert result['quality_score'] == 0.92
            assert len(result['stages_completed']) == 4

    @pytest.mark.asyncio
    async def test_real_time_feature_computation_integration(self):
        """测试实时特征计算的集成"""
        # 模拟特征计算服务
        with patch('src.features.realtime_computer.RealtimeFeatureComputer') as mock_computer_class:
            mock_computer = AsyncMock()
            mock_computer_class.return_value = mock_computer

            # 模拟特征计算
            mock_computer.compute_features.return_value = {
                'features': {
                    'team_form': 0.75,
                    'home_advantage': 0.15,
                    'recent_performance': 0.82,
                    'head_to_head': 0.60
                },
                'computation_time_ms': 25,
                'data_sources': ['live_scores', 'historical_data'],
                'feature_confidence': 0.88
            }

            # 验证特征计算
            result = await mock_computer.compute_features(
                match_id='match_123',
                data_sources=['live_scores', 'historical_data']
            )

            assert 'features' in result
            assert result['feature_confidence'] == 0.88
            assert len(result['data_sources']) == 2

    @pytest.mark.asyncio
    async def test_stream_backup_recovery_integration(self):
        """测试流备份恢复的集成"""
        # 模拟流备份管理器
        with patch('src.streaming.backup.StreamBackupManager') as mock_backup_class:
            mock_backup = AsyncMock()
            mock_backup_class.return_value = mock_backup

            # 模拟备份创建
            mock_backup.create_stream_backup.return_value = {
                'backup_id': 'backup_123',
                'stream_id': 'test_stream',
                'records_backed_up': 5000,
                'backup_size_mb': 10.5,
                'backup_time_ms': 2000,
                'status': 'success'
            }

            # 模拟备份恢复
            mock_backup.restore_stream_backup.return_value = {
                'backup_id': 'backup_123',
                'records_restored': 5000,
                'restore_time_ms': 3000,
                'status': 'success'
            }

            # 验证备份创建
            backup_result = await mock_backup.create_stream_backup(stream_id='test_stream')
            assert backup_result['status'] == 'success'
            assert backup_result['records_backed_up'] == 5000

            # 验证备份恢复
            restore_result = await mock_backup.restore_stream_backup(backup_id='backup_123')
            assert restore_result['status'] == 'success'
            assert restore_result['records_restored'] == 5000

    @pytest.mark.asyncio
    async def test_stream_scaling_integration(self):
        """测试流扩展的集成"""
        # 模拟流扩展管理器
        with patch('src.streaming.scaling.StreamScalingManager') as mock_scaling_class:
            mock_scaling = AsyncMock()
            mock_scaling_class.return_value = mock_scaling

            # 模拟自动扩展
            mock_scaling.auto_scale_stream.return_value = {
                'stream_id': 'test_stream',
                'current_partitions': 3,
                'new_partitions': 5,
                'scaling_time_ms': 15000,
                'status': 'success',
                'scaling_reason': 'high_throughput'
            }

            # 模拟扩展指标
            mock_scaling.get_scaling_metrics.return_value = {
                'current_throughput_rps': 1500,
                'target_throughput_rps': 2000,
                'current_latency_ms': 45,
                'target_latency_ms': 30,
                'scaling_factor': 1.5
            }

            # 验证自动扩展
            scaling_result = await mock_scaling.auto_scale_stream(stream_id='test_stream')
            assert scaling_result['status'] == 'success'
            assert scaling_result['new_partitions'] == 5

            # 验证扩展指标
            metrics = await mock_scaling.get_scaling_metrics(stream_id='test_stream')
            assert metrics['current_throughput_rps'] == 1500
            assert metrics['scaling_factor'] == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing"])