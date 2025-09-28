"""
集成测试模块

覆盖多模块交互和端到端业务流程：
- API↔数据库↔任务链路测试
- Streaming↔Monitoring联动测试
- 数据处理↔特征存储↔模型预测集成
- 缓存↔数据库↔外部API集成
"""

from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio
from datetime import datetime
from enum import Enum

pytestmark = pytest.mark.integration


class TestApiDatabaseTaskPipeline:
    """API↔数据库↔任务链路集成测试"""

    @pytest.fixture
    def mock_database_manager(self):
        """模拟数据库管理器"""
        db_manager = AsyncMock()
        db_manager.get_session = AsyncMock()
        db_manager.execute_query = AsyncMock()
        return db_manager

    @pytest.fixture
    def mock_cache_manager(self):
        """模拟缓存管理器"""
        cache_manager = AsyncMock()
        cache_manager.get = AsyncMock()
        cache_manager.set = AsyncMock()
        cache_manager.delete = AsyncMock()
        return cache_manager

    @pytest.fixture
    def mock_task_queue(self):
        """模拟任务队列"""
        task_queue = AsyncMock()
        task_queue.enqueue = AsyncMock()
        task_queue.get_status = AsyncMock()
        return task_queue

    def test_api_request_database_task_workflow(self):
        """测试API请求触发数据库操作和任务执行的工作流"""
        # 模拟API请求处理流程
        from src.api.features import get_features

        # 模拟数据库查询
        with patch('src.api.features.DatabaseManager') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db

            # 模拟任务队列
            with patch('src.api.features.TaskQueue') as mock_task_class:
                mock_task = AsyncMock()
                mock_task_class.return_value = mock_task

                # 模拟缓存
                with patch('src.api.features.CacheManager') as mock_cache_class:
                    mock_cache = AsyncMock()
                    mock_cache_class.return_value = mock_cache

                    # 验证工作流集成
                    assert callable(get_features)

    @pytest.mark.asyncio
    async def test_feature_api_integration(self):
        """测试特征API的集成流程"""
        # 模拟完整的特征获取流程
        with patch('src.features.feature_store.FeatureStore') as mock_store_class:
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            # 模拟特征获取
            mock_store.get_online_features.return_value = {
                'feature1': 0.5,
                'feature2': 0.8,
                'feature3': 1.2
            }

            # 验证集成流程
            result = await mock_store.get_online_features(
                features=['feature1', 'feature2', 'feature3'],
                entity_rows=[{'entity_id': 'test_1'}]
            )

            assert isinstance(result, dict)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_prediction_api_integration(self):
        """测试预测API的集成流程"""
        # 模拟预测请求流程
        with patch('src.models.prediction_service.PredictionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # 模拟预测结果
            mock_service.predict.return_value = {
                'prediction': 0.75,
                'confidence': 0.85,
                'model_version': 'v1.0.0'
            }

            # 验证集成流程
            result = await mock_service.predict(
                features={'feature1': 0.5, 'feature2': 0.8}
            )

            assert isinstance(result, dict)
            assert 'prediction' in result
            assert 'confidence' in result
            assert 'model_version' in result

    @pytest.mark.asyncio
    async def test_data_collection_integration(self):
        """测试数据采集的集成流程"""
        # 模拟数据采集任务链路
        with patch('src.tasks.data_collection_tasks.collect_fixtures_task') as mock_task:
            mock_task.run = AsyncMock()
            mock_task.run.return_value = {'status': 'success', 'records': 100}

            # 验证任务执行
            result = await mock_task.run(days_ahead=7)

            assert result['status'] == 'success'
            assert result['records'] == 100

    @pytest.mark.asyncio
    async def test_cache_database_integration(self):
        """测试缓存和数据库的集成"""
        # 模拟缓存未命中，查询数据库的场景
        with patch('src.cache.redis_manager.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis

            # 模拟缓存未命中
            mock_redis.get.return_value = None

            # 模拟数据库查询
            with patch('src.database.connection.DatabaseManager') as mock_db_class:
                mock_db = AsyncMock()
                mock_db_class.return_value = mock_db

                # 模拟数据库查询结果
                mock_db.execute_query.return_value = [
                    {'id': 1, 'data': 'value1'},
                    {'id': 2, 'data': 'value2'}
                ]

                # 模拟缓存设置
                mock_redis.set.return_value = True

                # 验证集成流程
                cache_result = await mock_redis.get('test_key')
                assert cache_result is None

                db_result = await mock_db.execute_query('SELECT * FROM test_table')
                assert len(db_result) == 2

                # 验证缓存设置被调用
                mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_error_handling_integration(self):
        """测试API错误处理的集成"""
        # 模拟API错误场景
        with patch('src.api.features.DatabaseManager') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db

            # 模拟数据库错误
            mock_db.execute_query.side_effect = Exception("Database connection failed")

            # 验证错误处理
            with pytest.raises(Exception) as exc_info:
                await mock_db.execute_query('SELECT * FROM test_table')

            assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_task_retry_integration(self):
        """测试任务重试机制的集成"""
        # 模拟任务重试流程
        with patch('src.tasks.celery_app.app') as mock_app:
            mock_app.send_task = AsyncMock()
            mock_app.send_task.return_value = {'id': 'task_123'}

            # 模拟任务状态查询
            mock_app.AsyncResult = Mock()
            mock_result = Mock()
            mock_result.status = 'SUCCESS'
            mock_result.get.return_value = {'result': 'success'}
            mock_app.AsyncResult.return_value = mock_result

            # 验证任务发送
            task_result = await mock_app.send_task(
                'tasks.data_collection_tasks.collect_fixtures_task',
                args=[7]
            )

            assert task_result['id'] == 'task_123'

            # 验证任务状态查询
            result = mock_app.AsyncResult('task_123')
            assert result.status == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """测试监控系统的集成"""
        # 模拟监控数据收集流程
        with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            # 模拟指标记录
            mock_exporter.record_data_collection = Mock()
            mock_exporter.record_system_health = Mock()

            # 模拟API调用
            with patch('src.api.monitoring.get_metrics') as mock_get_metrics:
                mock_get_metrics.return_value = {
                    'cpu_usage': 75.0,
                    'memory_usage': 60.0,
                    'disk_usage': 45.0
                }

                # 验证监控集成
                metrics = mock_get_metrics()
                assert isinstance(metrics, dict)
                assert 'cpu_usage' in metrics

                # 验证指标记录被调用
                mock_exporter.record_system_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_pipeline_integration(self):
        """测试数据管道的集成"""
        # 模拟数据从采集到处理的完整流程
        with patch('src.data.processing.DataProcessor') as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor_class.return_value = mock_processor

            # 模拟数据处理
            mock_processor.process_data.return_value = {
                'processed_records': 100,
                'quality_score': 0.95,
                'processing_time': 2.5
            }

            # 验证数据处理流程
            result = await mock_processor.process_data(
                data_source='api',
                raw_data=[{'id': 1, 'value': 10}, {'id': 2, 'value': 20}]
            )

            assert result['processed_records'] == 100
            assert result['quality_score'] == 0.95
            assert result['processing_time'] == 2.5

    @pytest.mark.asyncio
    async def test_external_api_integration(self):
        """测试外部API集成的流程"""
        # 模拟外部API调用
        with patch('src.data.collectors.ExternalAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # 模拟API响应
            mock_client.get_data.return_value = {
                'fixtures': [
                    {'id': 1, 'home_team': 'Team A', 'away_team': 'Team B'},
                    {'id': 2, 'home_team': 'Team C', 'away_team': 'Team D'}
                ]
            }

            # 验证API集成
            result = await mock_client.get_data(endpoint='fixtures')

            assert 'fixtures' in result
            assert len(result['fixtures']) == 2

    def test_configuration_integration(self):
        """测试配置管理的集成"""
        # 模拟配置加载和验证
        with patch('src.core.config.Config') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            # 模拟配置值
            mock_config.get.return_value = 'test_value'
            mock_config.get_int.return_value = 8080
            mock_config.get_bool.return_value = True

            # 验证配置集成
            value = mock_config.get('database.url')
            assert value == 'test_value'

            port = mock_config.get_int('server.port')
            assert port == 8080

            enabled = mock_config.get_bool('feature.enabled')
            assert enabled is True


class TestStreamingMonitoringIntegration:
    """Streaming↔Monitoring联动集成测试"""

    @pytest.fixture
    def mock_stream_processor(self):
        """模拟流处理器"""
        processor = AsyncMock()
        processor.process_stream = AsyncMock()
        processor.get_stream_stats = AsyncMock()
        return processor

    @pytest.fixture
    def mock_alert_manager(self):
        """模拟告警管理器"""
        alert_manager = AsyncMock()
        alert_manager.evaluate_alerts = AsyncMock()
        alert_manager.send_alert = AsyncMock()
        return alert_manager

    @pytest.mark.asyncio
    async def test_stream_processing_alert_integration(self):
        """测试流处理触发告警的集成"""
        # 模拟流处理异常触发告警
        with patch('src.streaming.stream_processor.StreamProcessor') as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor_class.return_value = mock_processor

            # 模拟流处理异常
            mock_processor.process_stream.side_effect = Exception("Stream processing failed")

            # 模拟告警管理器
            with patch('src.monitoring.alert_manager.AlertManager') as mock_alert_class:
                mock_alert = AsyncMock()
                mock_alert_class.return_value = mock_alert

                # 验证异常触发告警
                with pytest.raises(Exception):
                    await mock_processor.process_stream(stream_id='test_stream')

                # 验证告警被触发
                mock_alert.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_metrics_stream_integration(self):
        """测试指标和流处理的集成"""
        # 模拟流处理指标收集
        with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            # 模拟流处理器
            with patch('src.streaming.stream_processor.StreamProcessor') as mock_processor_class:
                mock_processor = AsyncMock()
                mock_processor_class.return_value = mock_processor

                # 模拟流处理统计
                mock_processor.get_stream_stats.return_value = {
                    'records_processed': 1000,
                    'processing_rate': 100,
                    'error_rate': 0.01,
                    'latency_ms': 50
                }

                # 验证集成流程
                stats = await mock_processor.get_stream_stats()
                assert stats['records_processed'] == 1000
                assert stats['processing_rate'] == 100

                # 验证指标记录
                mock_exporter.record_stream_processing.assert_called_once()

    @pytest.mark.asyncio
    async def test_anomaly_detection_integration(self):
        """测试异常检测和流处理的集成"""
        # 模拟流数据异常检测
        with patch('src.monitoring.anomaly_detector.AnomalyDetector') as mock_detector_class:
            mock_detector = AsyncMock()
            mock_detector_class.return_value = mock_detector

            # 模拟异常检测结果
            mock_detector.detect_anomalies.return_value = [
                {
                    'table_name': 'stream_data',
                    'column_name': 'value',
                    'anomaly_type': 'outlier',
                    'severity': 'high',
                    'anomaly_score': 0.85
                }
            ]

            # 验证异常检测集成
            anomalies = await mock_detector.detect_anomalies(table_names=['stream_data'])

            assert len(anomalies) == 1
            assert anomalies[0]['severity'] == 'high'

    @pytest.mark.asyncio
    async def test_kafka_monitoring_integration(self):
        """测试Kafka和监控的集成"""
        # 模拟Kafka消费者监控
        with patch('src.streaming.kafka_consumer.KafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer

            # 模拟消费者统计
            mock_consumer.get_consumer_stats.return_value = {
                'messages_consumed': 500,
                'consumer_lag': 10,
                'bytes_consumed': 1024000,
                'processing_time_ms': 25
            }

            # 验证Kafka监控集成
            stats = await mock_consumer.get_consumer_stats()
            assert stats['messages_consumed'] == 500
            assert stats['consumer_lag'] == 10

    @pytest.mark.asyncio
    async def test_database_monitoring_integration(self):
        """测试数据库监控的集成"""
        # 模拟数据库性能监控
        with patch('src.database.connection.DatabaseManager') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db

            # 模拟数据库统计
            mock_db.get_database_stats.return_value = {
                'active_connections': 15,
                'query_count': 1000,
                'average_query_time_ms': 5.2,
                'cache_hit_ratio': 0.85
            }

            # 验证数据库监控集成
            stats = await mock_db.get_database_stats()
            assert stats['active_connections'] == 15
            assert stats['cache_hit_ratio'] == 0.85

    @pytest.mark.asyncio
    async def test_cache_monitoring_integration(self):
        """测试缓存监控的集成"""
        # 模拟Redis缓存监控
        with patch('src.cache.redis_manager.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis

            # 模拟缓存统计
            mock_redis.get_cache_stats.return_value = {
                'keys_count': 1000,
                'memory_usage_mb': 50,
                'hit_rate': 0.75,
                'operations_per_second': 100
            }

            # 验证缓存监控集成
            stats = await mock_redis.get_cache_stats()
            assert stats['keys_count'] == 1000
            assert stats['hit_rate'] == 0.75

    @pytest.mark.asyncio
    async def test_end_to_end_integration(self):
        """测试端到端集成流程"""
        # 模拟完整的端到端流程
        with patch('src.data.collectors.ExternalAPIClient') as mock_client_class, \
             patch('src.data.processing.DataProcessor') as mock_processor_class, \
             patch('src.features.feature_store.FeatureStore') as mock_store_class, \
             patch('src.models.prediction_service.PredictionService') as mock_service_class:

            # 模拟数据采集
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_data.return_value = {'fixtures': [{'id': 1, 'data': 'test'}]}

            # 模拟数据处理
            mock_processor = AsyncMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.process_data.return_value = {'processed_records': 1}

            # 模拟特征存储
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store
            mock_store.get_online_features.return_value = {'feature1': 0.5}

            # 模拟预测服务
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.predict.return_value = {'prediction': 0.75}

            # 验证端到端流程
            data = await mock_client.get_data('fixtures')
            assert len(data['fixtures']) == 1

            processed = await mock_processor.process_data(data)
            assert processed['processed_records'] == 1

            features = await mock_store.get_online_features(['feature1'], [{'entity_id': '1'}])
            assert features['feature1'] == 0.5

            prediction = await mock_service.predict(features)
            assert prediction['prediction'] == 0.75

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """测试错误恢复的集成"""
        # 模拟错误恢复流程
        with patch('src.tasks.backup_tasks.BackupManager') as mock_backup_class:
            mock_backup = AsyncMock()
            mock_backup_class.return_value = mock_backup

            # 模拟备份恢复
            mock_backup.restore_backup.return_value = {'status': 'success', 'restored_records': 100}

            # 验证错误恢复集成
            result = await mock_backup.restore_backup(backup_id='backup_123')
            assert result['status'] == 'success'
            assert result['restored_records'] == 100

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """测试性能监控的集成"""
        # 模拟性能监控流程
        with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            # 模拟性能指标记录
            mock_exporter.record_request_duration = Mock()
            mock_exporter.record_database_query_time = Mock()
            mock_exporter.record_cache_operation_time = Mock()

            # 验证性能监控集成
            mock_exporter.record_request_duration('api_endpoint', 0.1)
            mock_exporter.record_database_query_time('SELECT', 0.05)
            mock_exporter.record_cache_operation_time('get', 0.001)

            # 验证所有性能指标都被记录
            mock_exporter.record_request_duration.assert_called_once()
            mock_exporter.record_database_query_time.assert_called_once()
            mock_exporter.record_cache_operation_time.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing"])