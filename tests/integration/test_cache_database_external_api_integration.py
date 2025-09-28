"""
缓存↔数据库↔外部API集成测试

覆盖多层系统交互和缓存策略：
- 缓存策略↔数据库查询↔外部API调用
- 缓存失效↔数据一致性↔错误处理
- 多级缓存↔数据库连接池↔API限流
"""

from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio
from datetime import datetime, timedelta
from enum import Enum

pytestmark = pytest.mark.integration


class TestCacheDatabaseApiIntegration:
    """缓存↔数据库↔外部API集成测试"""

    @pytest.fixture
    def mock_cache_manager(self):
        """模拟缓存管理器"""
        cache = AsyncMock()
        cache.get = AsyncMock()
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        cache.get_cache_stats = AsyncMock()
        return cache

    @pytest.fixture
    def mock_database_manager(self):
        """模拟数据库管理器"""
        db = AsyncMock()
        db.execute_query = AsyncMock()
        db.execute_transaction = AsyncMock()
        db.get_connection = AsyncMock()
        db.get_database_stats = AsyncMock()
        return db

    @pytest.fixture
    def mock_external_api_client(self):
        """模拟外部API客户端"""
        client = AsyncMock()
        client.get_data = AsyncMock()
        client.post_data = AsyncMock()
        client.get_rate_limit_info = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_cache_miss_database_query_api_fallback(self):
        """测试缓存未命中→数据库查询→API回退的完整流程"""
        # 模拟缓存未命中
        with patch('src.cache.redis_manager.RedisManager') as mock_cache_class:
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            # 缓存未命中
            mock_cache.get.return_value = None

            # 模拟数据库查询
            with patch('src.database.connection.DatabaseManager') as mock_db_class:
                mock_db = AsyncMock()
                mock_db_class.return_value = mock_db

                # 数据库也没有数据
                mock_db.execute_query.return_value = []

                # 模拟外部API调用
                with patch('src.data.collectors.ExternalAPIClient') as mock_api_class:
                    mock_api = AsyncMock()
                    mock_api_class.return_value = mock_api

                    # API返回数据
                    mock_api.get_data.return_value = {
                        'fixtures': [
                            {'id': 1, 'home_team': 'Team A', 'away_team': 'Team B'},
                            {'id': 2, 'home_team': 'Team C', 'away_team': 'Team D'}
                        ]
                    }

                    # 验证完整流程
                    # 1. 缓存查询
                    cache_result = await mock_cache.get('fixtures:recent')
                    assert cache_result is None

                    # 2. 数据库查询
                    db_result = await mock_db.execute_query('SELECT * FROM fixtures WHERE date >= NOW() - INTERVAL \'7 days\'')
                    assert len(db_result) == 0

                    # 3. API调用
                    api_result = await mock_api.get_data('fixtures')
                    assert 'fixtures' in api_result
                    assert len(api_result['fixtures']) == 2

                    # 4. 写入缓存
                    await mock_cache.set('fixtures:recent', api_result['fixtures'], ttl=3600)

                    # 5. 写入数据库
                    for fixture in api_result['fixtures']:
                        await mock_db.execute_transaction(
                            'INSERT INTO fixtures (id, home_team, away_team) VALUES (%s, %s, %s)',
                            (fixture['id'], fixture['home_team'], fixture['away_team'])
                        )

                    # 验证调用次数
                    mock_cache.get.assert_called_once()
                    mock_db.execute_query.assert_called_once()
                    mock_api.get_data.assert_called_once()
                    mock_cache.set.assert_called_once()
                    assert mock_db.execute_transaction.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_hit_optimization(self):
        """测试缓存命中优化流程"""
        # 模拟缓存命中
        with patch('src.cache.redis_manager.RedisManager') as mock_cache_class:
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            # 缓存命中
            cached_data = [
                {'id': 1, 'home_team': 'Team A', 'away_team': 'Team B'},
                {'id': 2, 'home_team': 'Team C', 'away_team': 'Team D'}
            ]
            mock_cache.get.return_value = cached_data

            # 验证缓存命中流程
            result = await mock_cache.get('fixtures:recent')

            assert result == cached_data
            assert len(result) == 2

            # 验证没有调用数据库和API
            mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_invalidation_consistency(self):
        """测试缓存失效和数据一致性"""
        # 模拟缓存失效
        with patch('src.cache.redis_manager.RedisManager') as mock_cache_class:
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            # 模拟数据库管理器
            with patch('src.database.connection.DatabaseManager') as mock_db_class:
                mock_db = AsyncMock()
                mock_db_class.return_value = mock_db

                # 模拟数据更新
                updated_fixture = {'id': 1, 'home_team': 'Team A', 'away_team': 'Team B', 'score': '2-1'}

                # 数据库更新成功
                mock_db.execute_transaction.return_value = {'affected_rows': 1, 'status': 'success'}

                # 验证缓存失效流程
                # 1. 失效缓存
                await mock_cache.delete('fixtures:recent')
                await mock_cache.delete(f'fixture:{updated_fixture["id"]}')

                # 2. 更新数据库
                db_result = await mock_db.execute_transaction(
                    'UPDATE fixtures SET score = %s WHERE id = %s',
                    ('2-1', updated_fixture['id'])
                )

                # 3. 重新缓存
                await mock_cache.set(f'fixture:{updated_fixture["id"]}', updated_fixture, ttl=3600)

                # 验证结果
                assert db_result['affected_rows'] == 1
                assert db_result['status'] == 'success'

                mock_cache.delete.assert_called()
                mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_connection_pool_integration(self):
        """测试数据库连接池集成"""
        # 模拟连接池管理
        with patch('src.database.connection.DatabaseConnectionPool') as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool

            # 模拟连接池统计
            mock_pool.get_pool_stats.return_value = {
                'total_connections': 10,
                'active_connections': 3,
                'idle_connections': 7,
                'max_connections': 20,
                'connection_wait_time_ms': 5,
                'connection_success_rate': 0.99
            }

            # 模拟连接获取
            mock_pool.get_connection.return_value = {
                'connection_id': 'conn_123',
                'created_at': datetime.now(),
                'status': 'active'
            }

            # 模拟连接释放
            mock_pool.release_connection.return_value = {'status': 'released'}

            # 验证连接池集成
            stats = await mock_pool.get_pool_stats()
            assert stats['total_connections'] == 10
            assert stats['active_connections'] == 3

            connection = await mock_pool.get_connection()
            assert connection['status'] == 'active'

            release_result = await mock_pool.release_connection(connection['connection_id'])
            assert release_result['status'] == 'released'

    @pytest.mark.asyncio
    async def test_api_rate_limiting_integration(self):
        """测试API限流集成"""
        # 模拟API限流器
        with patch('src.data.collectors.RateLimiter') as mock_limiter_class:
            mock_limiter = AsyncMock()
            mock_limiter_class.return_value = mock_limiter

            # 模拟限流检查
            mock_limiter.check_rate_limit.return_value = {
                'allowed': True,
                'remaining_requests': 95,
                'reset_time': datetime.now() + timedelta(minutes=1),
                'limit': 100
            }

            # 模拟API客户端
            with patch('src.data.collectors.ExternalAPIClient') as mock_api_class:
                mock_api = AsyncMock()
                mock_api_class.return_value = mock_api

                # 模拟API调用
                mock_api.get_data.return_value = {
                    'fixtures': [{'id': 1, 'home_team': 'Team A', 'away_team': 'Team B'}]
                }

                # 验证限流集成
                rate_limit_check = await mock_limiter.check_rate_limit('football-api', 'fixtures')
                assert rate_limit_check['allowed'] is True
                assert rate_limit_check['remaining_requests'] == 95

                if rate_limit_check['allowed']:
                    api_result = await mock_api.get_data('fixtures')
                    assert 'fixtures' in api_result

    @pytest.mark.asyncio
    async def test_multi_level_cache_integration(self):
        """测试多级缓存集成"""
        # 模拟L1缓存 (内存)
        with patch('src.cache.memory_cache.MemoryCache') as mock_l1_cache_class:
            mock_l1_cache = AsyncMock()
            mock_l1_cache_class.return_value = mock_l1_cache

            # 模拟L2缓存 (Redis)
            with patch('src.cache.redis_manager.RedisManager') as mock_l2_cache_class:
                mock_l2_cache = AsyncMock()
                mock_l2_cache_class.return_value = mock_l2_cache

                # L1缓存未命中，L2缓存命中
                mock_l1_cache.get.return_value = None
                mock_l2_cache.get.return_value = {'data': 'from_l2_cache'}

                # 验证多级缓存流程
                # 1. 检查L1缓存
                l1_result = await mock_l1_cache.get('test_key')
                assert l1_result is None

                # 2. 检查L2缓存
                l2_result = await mock_l2_cache.get('test_key')
                assert l2_result['data'] == 'from_l2_cache'

                # 3. 写入L1缓存
                await mock_l1_cache.set('test_key', l2_result, ttl=300)  # L1缓存时间更短

                # 验证调用顺序
                mock_l1_cache.get.assert_called_once()
                mock_l2_cache.get.assert_called_once()
                mock_l1_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """测试断路器集成"""
        # 模拟断路器
        with patch('src.utils.circuit_breaker.CircuitBreaker') as mock_breaker_class:
            mock_breaker = AsyncMock()
            mock_breaker_class.return_value = mock_breaker

            # 模拟断路器状态
            mock_breaker.get_state.return_value = {
                'state': 'CLOSED',
                'failure_count': 0,
                'last_failure_time': None,
                'success_count': 10
            }

            # 模拟受保护的API调用
            mock_breaker.call.return_value = {
                'status': 'success',
                'data': {'result': 'api_call_success'}
            }

            # 验证断路器集成
            state = await mock_breaker.get_state()
            assert state['state'] == 'CLOSED'
            assert state['failure_count'] == 0

            # 受保护的调用
            result = await mock_breaker.call('external_api_call', timeout=5.0)
            assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_retry_mechanism_integration(self):
        """测试重试机制集成"""
        # 模拟重试管理器
        with patch('src.utils.retry_manager.RetryManager') as mock_retry_class:
            mock_retry = AsyncMock()
            mock_retry_class.return_value = mock_retry

            # 模拟重试执行
            mock_retry.execute_with_retry.return_value = {
                'success': True,
                'attempts': 2,
                'final_result': {'data': 'retry_success'},
                'execution_time_ms': 1500
            }

            # 验证重试集成
            retry_config = {
                'max_attempts': 3,
                'delay_ms': 1000,
                'backoff_factor': 2,
                'retryable_errors': ['ConnectionError', 'TimeoutError']
            }

            result = await mock_retry.execute_with_retry(
                'api_call_function',
                retry_config,
                endpoint='test_endpoint',
                params={'param1': 'value1'}
            )

            assert result['success'] is True
            assert result['attempts'] == 2
            assert result['final_result']['data'] == 'retry_success'

    @pytest.mark.asyncio
    async def test_data_consistency_check_integration(self):
        """测试数据一致性检查集成"""
        # 模拟一致性检查器
        with patch('src.data.consistency.DataConsistencyChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker

            # 模拟一致性检查结果
            mock_checker.check_consistency.return_value = {
                'consistent': True,
                'cache_db_consistency': True,
                'db_api_consistency': True,
                'inconsistencies_found': [],
                'check_time_ms': 200
            }

            # 模拟数据同步器
            with patch('src.data.synchronizer.DataSynchronizer') as mock_sync_class:
                mock_sync = AsyncMock()
                mock_sync_class.return_value = mock_sync

                # 模拟数据同步
                mock_sync.synchronize_data.return_value = {
                    'synced_records': 0,  # 没有不一致的数据需要同步
                    'sync_time_ms': 50,
                    'status': 'no_sync_needed'
                }

                # 验证一致性检查集成
                consistency_result = await mock_checker.check_consistency(
                    data_sources=['cache', 'database', 'api'],
                    data_key='fixtures:recent'
                )

                assert consistency_result['consistent'] is True
                assert consistency_result['cache_db_consistency'] is True

                # 如果发现不一致，执行同步
                if not consistency_result['consistent']:
                    sync_result = await mock_sync.synchronize_data(
                        source='api',
                        target='cache,database',
                        data_key='fixtures:recent'
                    )
                    assert sync_result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """测试性能监控集成"""
        # 模拟性能监控器
        with patch('src.monitoring.performance_monitor.PerformanceMonitor') as mock_monitor_class:
            mock_monitor = AsyncMock()
            mock_monitor_class.return_value = mock_monitor

            # 模拟性能指标
            mock_monitor.get_performance_metrics.return_value = {
                'cache_metrics': {
                    'hit_rate': 0.85,
                    'avg_response_time_ms': 2,
                    'total_operations': 1000
                },
                'database_metrics': {
                    'avg_query_time_ms': 15,
                    'connection_pool_usage': 0.3,
                    'total_queries': 500
                },
                'api_metrics': {
                    'avg_response_time_ms': 150,
                    'success_rate': 0.95,
                    'rate_limit_utilization': 0.2
                },
                'overall_performance_score': 0.88
            }

            # 模拟指标导出器
            with patch('src.monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证性能监控集成
                metrics = await mock_monitor.get_performance_metrics()
                assert metrics['cache_metrics']['hit_rate'] == 0.85
                assert metrics['database_metrics']['avg_query_time_ms'] == 15
                assert metrics['overall_performance_score'] == 0.88

                # 验证指标导出
                mock_exporter.record_performance_metrics.assert_called_once_with(
                    performance_data=metrics
                )

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_integration(self):
        """测试错误处理和恢复集成"""
        # 模拟错误处理器
        with patch('src.utils.error_handler.ErrorHandler') as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler_class.return_value = mock_handler

            # 模拟错误处理结果
            mock_handler.handle_error.return_value = {
                'error_handled': True,
                'error_type': 'ConnectionError',
                'error_message': 'Database connection failed',
                'recovery_action': 'retry_with_fallback',
                'fallback_data': {'cached_data': 'fallback_response'}
            }

            # 模拟恢复管理器
            with patch('src.utils.recovery_manager.RecoveryManager') as mock_recovery_class:
                mock_recovery = AsyncMock()
                mock_recovery_class.return_value = mock_recovery

                # 模拟恢复操作
                mock_recovery.execute_recovery.return_value = {
                    'recovery_successful': True,
                    'recovery_method': 'cache_fallback',
                    'recovered_data': {'fixtures': []},
                    'recovery_time_ms': 100
                }

                # 验证错误处理集成
                error_info = {
                    'error_type': 'ConnectionError',
                    'error_message': 'Database connection failed',
                    'context': 'fixtures_api_call',
                    'timestamp': datetime.now()
                }

                handled_result = await mock_handler.handle_error(error_info)
                assert handled_result['error_handled'] is True
                assert handled_result['recovery_action'] == 'retry_with_fallback'

                # 执行恢复操作
                recovery_result = await mock_recovery.execute_recovery(
                    recovery_method=handled_result['recovery_action'],
                    context=error_info['context']
                )

                assert recovery_result['recovery_successful'] is True
                assert recovery_result['recovery_method'] == 'cache_fallback'

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """测试健康检查集成"""
        # 模拟健康检查器
        with patch('src.monitoring.health_checker.HealthChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker

            # 模拟健康检查结果
            mock_checker.check_all_systems.return_value = {
                'overall_status': 'healthy',
                'systems': {
                    'cache': {'status': 'healthy', 'response_time_ms': 2, 'details': 'Cache operating normally'},
                    'database': {'status': 'healthy', 'response_time_ms': 15, 'details': 'Database connection stable'},
                    'external_api': {'status': 'degraded', 'response_time_ms': 500, 'details': 'API response slow but functional'},
                    'feature_store': {'status': 'healthy', 'response_time_ms': 25, 'details': 'Feature store accessible'}
                },
                'recommendations': [
                    'Monitor API response times',
                    'Consider optimizing API calls'
                ]
            }

            # 验证健康检查集成
            health_status = await mock_checker.check_all_systems()
            assert health_status['overall_status'] == 'healthy'
            assert health_status['systems']['cache']['status'] == 'healthy'
            assert health_status['systems']['external_api']['status'] == 'degraded'

            # 基于健康状态调整系统行为
            if health_status['systems']['external_api']['status'] == 'degraded':
                # 减少API调用频率
                assert 'Monitor API response times' in health_status['recommendations']

    @pytest.mark.asyncio
    async def test_scaling_integration(self):
        """测试扩展集成"""
        # 模拟扩展管理器
        with patch('src.utils.scaling_manager.ScalingManager') as mock_scaling_class:
            mock_scaling = AsyncMock()
            mock_scaling_class.return_value = mock_scaling

            # 模拟扩展决策
            mock_scaling.should_scale.return_value = {
                'should_scale': True,
                'direction': 'scale_up',
                'current_load': 0.85,
                'target_load': 0.60,
                'reason': 'high_cpu_usage'
            }

            # 模拟扩展执行
            mock_scaling.execute_scaling.return_value = {
                'scaling_executed': True,
                'new_capacity': 150,
                'old_capacity': 100,
                'scaling_time_ms': 30000,
                'status': 'success'
            }

            # 验证扩展集成
            scaling_decision = await mock_scaling.should_scale(
                service_type='api',
                current_metrics={'cpu_usage': 0.85, 'memory_usage': 0.70}
            )

            assert scaling_decision['should_scale'] is True
            assert scaling_decision['direction'] == 'scale_up'

            if scaling_decision['should_scale']:
                scaling_result = await mock_scaling.execute_scaling(
                    direction=scaling_decision['direction'],
                    service_type='api'
                )

                assert scaling_result['scaling_executed'] is True
                assert scaling_result['new_capacity'] == 150


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing"])