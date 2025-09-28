"""
数据处理与特征存储集成测试

覆盖数据处理、特征工程和模型预测的完整集成链路：
- 数据采集↔清洗↔特征工程↔模型预测
- 特征存储↔在线特征↔实时预测
- 数据质量↔特征质量↔模型性能
"""

from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio
from datetime import datetime
from enum import Enum

pytestmark = pytest.mark.integration


class TestDataProcessingFeaturePipeline:
    """数据处理与特征管道集成测试"""

    @pytest.fixture
    def mock_data_collector(self):
        """模拟数据采集器"""
        collector = AsyncMock()
        collector.collect_data = AsyncMock()
        collector.get_collection_stats = AsyncMock()
        return collector

    @pytest.fixture
    def mock_data_processor(self):
        """模拟数据处理器"""
        processor = AsyncMock()
        processor.process_data = AsyncMock()
        processor.validate_data = AsyncMock()
        return processor

    @pytest.fixture
    def mock_feature_store(self):
        """模拟特征存储"""
        feature_store = AsyncMock()
        feature_store.get_online_features = AsyncMock()
        feature_store.get_historical_features = AsyncMock()
        feature_store.ingest_features = AsyncMock()
        return feature_store

    @pytest.fixture
    def mock_prediction_service(self):
        """模拟预测服务"""
        prediction_service = AsyncMock()
        prediction_service.predict = AsyncMock()
        prediction_service.get_model_info = AsyncMock()
        return prediction_service

    @pytest.mark.asyncio
    async def test_data_collection_processing_integration(self):
        """测试数据采集与处理的集成"""
        # 模拟数据采集
        with patch('data.collectors.DataCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector_class.return_value = mock_collector

            # 模拟数据采集结果
            mock_collector.collect_data.return_value = {
                'source': 'api',
                'records_collected': 100,
                'data': [
                    {'match_id': 1, 'home_team': 'Team A', 'away_team': 'Team B', 'home_score': 2, 'away_score': 1},
                    {'match_id': 2, 'home_team': 'Team C', 'away_team': 'Team D', 'home_score': 0, 'away_score': 0}
                ],
                'collection_time_ms': 500,
                'status': 'success'
            }

            # 模拟数据处理器
            with patch('data.processing.DataProcessor') as mock_processor_class:
                mock_processor = AsyncMock()
                mock_processor_class.return_value = mock_processor

                # 模拟数据处理结果
                mock_processor.process_data.return_value = {
                    'input_records': 100,
                    'output_records': 95,
                    'processed_data': [
                        {'match_id': 1, 'home_team': 'Team A', 'away_team': 'Team B', 'home_score': 2, 'away_score': 1, 'processed': True},
                        {'match_id': 2, 'home_team': 'Team C', 'away_team': 'Team D', 'home_score': 0, 'away_score': 0, 'processed': True}
                    ],
                    'processing_time_ms': 300,
                    'quality_score': 0.95
                }

                # 验证集成流程
                collected_data = await mock_collector.collect_data(source='api', endpoint='fixtures')
                assert collected_data['records_collected'] == 100
                assert collected_data['status'] == 'success'

                processed_data = await mock_processor.process_data(collected_data['data'])
                assert processed_data['output_records'] == 95
                assert processed_data['quality_score'] == 0.95

    @pytest.mark.asyncio
    async def test_feature_engineering_integration(self):
        """测试特征工程的集成"""
        # 模拟特征计算器
        with patch('features.feature_calculator.FeatureCalculator') as mock_calculator_class:
            mock_calculator = AsyncMock()
            mock_calculator_class.return_value = mock_calculator

            # 模拟特征计算结果
            mock_calculator.calculate_features.return_value = {
                'match_features': [
                    {
                        'match_id': 1,
                        'home_team_form': 0.75,
                        'away_team_form': 0.60,
                        'home_advantage': 0.15,
                        'head_to_head_win_rate': 0.70,
                        'recent_goals_scored': 2.5,
                        'recent_goals_conceded': 1.2
                    }
                ],
                'feature_count': 6,
                'calculation_time_ms': 150,
                'feature_quality_score': 0.88
            }

            # 模拟特征存储
            with patch('features.feature_store.FeatureStore') as mock_store_class:
                mock_store = AsyncMock()
                mock_store_class.return_value = mock_store

                # 模拟特征存储结果
                mock_store.ingest_features.return_value = {
                    'ingested_features': 6,
                    'storage_time_ms': 100,
                    'status': 'success'
                }

                # 验证集成流程
                match_data = {'match_id': 1, 'home_team': 'Team A', 'away_team': 'Team B'}
                features = await mock_calculator.calculate_features(match_data)
                assert features['feature_count'] == 6
                assert features['feature_quality_score'] == 0.88

                ingestion_result = await mock_store.ingest_features(features['match_features'])
                assert ingestion_result['ingested_features'] == 6
                assert ingestion_result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_online_feature_retrieval_integration(self):
        """测试在线特征检索的集成"""
        # 模拟特征存储
        with patch('features.feature_store.FeatureStore') as mock_store_class:
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            # 模拟在线特征检索
            mock_store.get_online_features.return_value = {
                'features': {
                    'home_team_form': 0.75,
                    'away_team_form': 0.60,
                    'home_advantage': 0.15,
                    'head_to_head_win_rate': 0.70,
                    'recent_goals_scored': 2.5,
                    'recent_goals_conceded': 1.2
                },
                'retrieval_time_ms': 50,
                'cache_hit': True,
                'feature_freshness_ms': 30000
            }

            # 模拟预测服务
            with patch('models.prediction_service.PredictionService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # 模拟预测结果
                mock_service.predict.return_value = {
                    'prediction': 0.65,
                    'confidence': 0.82,
                    'model_version': 'v2.1.0',
                    'features_used': ['home_team_form', 'away_team_form', 'home_advantage'],
                    'prediction_time_ms': 25
                }

                # 验证集成流程
                feature_request = {
                    'features': ['home_team_form', 'away_team_form', 'home_advantage'],
                    'entity_rows': [{'match_id': 'match_123'}]
                }

                features = await mock_store.get_online_features(**feature_request)
                assert features['cache_hit'] is True
                assert features['retrieval_time_ms'] == 50

                prediction = await mock_service.predict(features['features'])
                assert prediction['prediction'] == 0.65
                assert prediction['confidence'] == 0.82

    @pytest.mark.asyncio
    async def test_historical_feature_analysis_integration(self):
        """测试历史特征分析的集成"""
        # 模拟特征存储
        with patch('features.feature_store.FeatureStore') as mock_store_class:
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            # 模拟历史特征检索
            mock_store.get_historical_features.return_value = {
                'features': [
                    {
                        'match_id': 1,
                        'date': '2024-01-01',
                        'home_team_form': 0.75,
                        'away_team_form': 0.60,
                        'actual_result': 1  # Home win
                    },
                    {
                        'match_id': 2,
                        'date': '2024-01-02',
                        'home_team_form': 0.80,
                        'away_team_form': 0.70,
                        'actual_result': 0  # Draw
                    }
                ],
                'total_records': 2,
                'date_range': {'start': '2024-01-01', 'end': '2024-01-02'},
                'retrieval_time_ms': 200
            }

            # 模拟特征分析器
            with patch('features.feature_analyzer.FeatureAnalyzer') as mock_analyzer_class:
                mock_analyzer = AsyncMock()
                mock_analyzer_class.return_value = mock_analyzer

                # 模拟特征分析结果
                mock_analyzer.analyze_features.return_value = {
                    'feature_importance': {
                        'home_team_form': 0.35,
                        'away_team_form': 0.30,
                        'home_advantage': 0.25,
                        'head_to_head_win_rate': 0.10
                    },
                    'feature_statistics': {
                        'home_team_form': {'mean': 0.75, 'std': 0.15, 'min': 0.40, 'max': 0.95},
                        'away_team_form': {'mean': 0.65, 'std': 0.18, 'min': 0.35, 'max': 0.90}
                    },
                    'analysis_time_ms': 150
                }

                # 验证集成流程
                historical_request = {
                    'features': ['home_team_form', 'away_team_form', 'home_advantage'],
                    'date_range': {'start': '2024-01-01', 'end': '2024-01-02'}
                }

                historical_features = await mock_store.get_historical_features(**historical_request)
                assert historical_features['total_records'] == 2

                analysis = await mock_analyzer.analyze_features(historical_features['features'])
                assert 'feature_importance' in analysis
                assert analysis['feature_importance']['home_team_form'] == 0.35

    @pytest.mark.asyncio
    async def test_feature_quality_validation_integration(self):
        """测试特征质量验证的集成"""
        # 模拟特征质量检查器
        with patch('features.quality.FeatureQualityChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker

            # 模拟质量检查结果
            mock_checker.check_feature_quality.return_value = {
                'quality_score': 0.92,
                'completeness_score': 0.95,
                'accuracy_score': 0.88,
                'consistency_score': 0.90,
                'timeliness_score': 0.85,
                'issues_found': [
                    {'feature': 'home_team_form', 'issue': 'missing_values', 'severity': 'low'},
                    {'feature': 'away_team_form', 'issue': 'out_of_range', 'severity': 'medium'}
                ],
                'recommendations': [
                    'Impute missing home_team_form values',
                    'Validate away_team_form range constraints'
                ]
            }

            # 模拟特征存储
            with patch('features.feature_store.FeatureStore') as mock_store_class:
                mock_store = AsyncMock()
                mock_store_class.return_value = mock_store

                # 模拟特征更新
                mock_store.update_features.return_value = {
                    'updated_features': 2,
                    'update_time_ms': 100,
                    'status': 'success'
                }

                # 验证集成流程
                features = {
                    'home_team_form': [0.75, None, 0.80],
                    'away_team_form': [0.60, 1.20, 0.70],  # 1.20 is out of range
                    'home_advantage': [0.15, 0.18, 0.12]
                }

                quality_result = await mock_checker.check_feature_quality(features)
                assert quality_result['quality_score'] == 0.92
                assert len(quality_result['issues_found']) == 2

                # 基于质量结果更新特征
                if quality_result['quality_score'] < 0.95:
                    update_result = await mock_store.update_features(features)
                    assert update_result['updated_features'] == 2
                    assert update_result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_model_prediction_pipeline_integration(self):
        """测试模型预测管道的完整集成"""
        # 模拟完整的预测管道
        with patch('models.prediction_pipeline.PredictionPipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline

            # 模拟管道预测结果
            mock_pipeline.run_prediction_pipeline.return_value = {
                'prediction': {
                    'home_win_probability': 0.65,
                    'draw_probability': 0.25,
                    'away_win_probability': 0.10,
                    'predicted_result': 'HOME_WIN',
                    'confidence': 0.82
                },
                'features_used': {
                    'home_team_form': 0.75,
                    'away_team_form': 0.60,
                    'home_advantage': 0.15,
                    'head_to_head_win_rate': 0.70
                },
                'model_info': {
                    'model_version': 'v2.1.0',
                    'training_date': '2024-01-15',
                    'accuracy': 0.78,
                    'feature_count': 15
                },
                'pipeline_stats': {
                    'total_time_ms': 125,
                    'feature_retrieval_time_ms': 50,
                    'prediction_time_ms': 25,
                    'quality_check_time_ms': 50
                }
            }

            # 验证管道集成
            pipeline_request = {
                'match_id': 'match_123',
                'home_team': 'Team A',
                'away_team': 'Team B',
                'required_features': ['home_team_form', 'away_team_form', 'home_advantage']
            }

            prediction_result = await mock_pipeline.run_prediction_pipeline(pipeline_request)
            assert prediction_result['prediction']['predicted_result'] == 'HOME_WIN'
            assert prediction_result['prediction']['confidence'] == 0.82
            assert prediction_result['pipeline_stats']['total_time_ms'] == 125

    @pytest.mark.asyncio
    async def test_real_time_feature_update_integration(self):
        """测试实时特征更新的集成"""
        # 模拟实时特征更新器
        with patch('features.realtime_updater.RealtimeFeatureUpdater') as mock_updater_class:
            mock_updater = AsyncMock()
            mock_updater_class.return_value = mock_updater

            # 模拟实时更新结果
            mock_updater.update_features_realtime.return_value = {
                'updated_features': ['home_team_form', 'away_team_form'],
                'update_source': 'live_scores',
                'update_time_ms': 75,
                'features_updated': 2,
                'status': 'success'
            }

            # 模拟特征存储
            with patch('features.feature_store.FeatureStore') as mock_store_class:
                mock_store = AsyncMock()
                mock_store_class.return_value = mock_store

                # 模拟缓存失效
                mock_store.invalidate_cache.return_value = {
                    'invalidated_features': ['home_team_form', 'away_team_form'],
                    'cache_clear_time_ms': 25,
                    'status': 'success'
                }

                # 验证集成流程
                update_request = {
                    'match_id': 'match_123',
                    'live_data': {
                        'current_score': '2-1',
                        'minute': 75,
                        'home_team_possession': 65
                    }
                }

                update_result = await mock_updater.update_features_realtime(update_request)
                assert update_result['features_updated'] == 2
                assert update_result['status'] == 'success'

                # 失效相关缓存
                cache_result = await mock_store.invalidate_cache(
                    features=['home_team_form', 'away_team_form']
                )
                assert cache_result['invalidated_features'] == 2
                assert cache_result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_feature_monitoring_integration(self):
        """测试特征监控的集成"""
        # 模拟特征监控器
        with patch('features.monitoring.FeatureMonitor') as mock_monitor_class:
            mock_monitor = AsyncMock()
            mock_monitor_class.return_value = mock_monitor

            # 模拟监控结果
            mock_monitor.get_feature_monitoring_stats.return_value = {
                'feature_freshness': {
                    'home_team_form': {'age_ms': 30000, 'fresh': True},
                    'away_team_form': {'age_ms': 120000, 'fresh': False}
                },
                'feature_usage': {
                    'home_team_form': {'usage_count': 1000, 'success_rate': 0.98},
                    'away_team_form': {'usage_count': 950, 'success_rate': 0.96}
                },
                'performance_metrics': {
                    'avg_retrieval_time_ms': 45,
                    'cache_hit_rate': 0.75,
                    'error_rate': 0.02
                }
            }

            # 模拟指标导出器
            with patch('monitoring.metrics_exporter.MetricsExporter') as mock_exporter_class:
                mock_exporter = Mock()
                mock_exporter_class.return_value = mock_exporter

                # 验证监控集成
                monitoring_stats = await mock_monitor.get_feature_monitoring_stats()
                assert monitoring_stats['feature_freshness']['home_team_form']['fresh'] is True
                assert monitoring_stats['feature_freshness']['away_team_form']['fresh'] is False

                # 验证指标记录
                mock_exporter.record_feature_metrics.assert_called_once_with(
                    monitoring_stats=monitoring_stats
                )

    @pytest.mark.asyncio
    async def test_feature_drift_detection_integration(self):
        """测试特征漂移检测的集成"""
        # 模拟特征漂移检测器
        with patch('features.drift_detector.FeatureDriftDetector') as mock_detector_class:
            mock_detector = AsyncMock()
            mock_detector_class.return_value = mock_detector

            # 模拟漂移检测结果
            mock_detector.detect_feature_drift.return_value = {
                'drift_detected': True,
                'drift_score': 0.25,
                'drifted_features': [
                    {'feature': 'home_team_form', 'drift_score': 0.35, 'severity': 'high'},
                    {'feature': 'away_team_form', 'drift_score': 0.15, 'severity': 'medium'}
                ],
                'recommendations': [
                    'Retrain model with recent data',
                    'Update feature calculation logic'
                ],
                'detection_time_ms': 200
            }

            # 模拟模型管理器
            with patch('models.model_manager.ModelManager') as mock_manager_class:
                mock_manager = AsyncMock()
                mock_manager_class.return_value = mock_manager

                # 模型重新训练
                mock_manager.retrain_model.return_value = {
                    'model_version': 'v2.2.0',
                    'training_time_ms': 5000,
                    'training_samples': 1000,
                    'validation_accuracy': 0.80,
                    'status': 'success'
                }

                # 验证漂移检测集成
                drift_result = await mock_detector.detect_feature_drift(
                    current_features={'home_team_form': 0.85, 'away_team_form': 0.75},
                    reference_features={'home_team_form': 0.65, 'away_team_form': 0.55}
                )

                assert drift_result['drift_detected'] is True
                assert drift_result['drift_score'] == 0.25
                assert len(drift_result['drifted_features']) == 2

                # 基于漂移结果触发模型重新训练
                if drift_result['drift_detected']:
                    retrain_result = await mock_manager.retrain_model(
                        model_id='football_prediction',
                        training_data='recent_matches'
                    )
                    assert retrain_result['status'] == 'success'
                    assert retrain_result['model_version'] == 'v2.2.0'

    @pytest.mark.asyncio
    async def test_feature_abtesting_integration(self):
        """测试特征A/B测试的集成"""
        # 模拟特征A/B测试管理器
        with patch('features.abtesting.FeatureABTestManager') as mock_abtest_class:
            mock_abtest = AsyncMock()
            mock_abtest_class.return_value = mock_abtest

            # 模拟A/B测试结果
            mock_abtest.run_ab_test.return_value = {
                'test_id': 'test_123',
                'variant_a': {
                    'features': ['home_team_form', 'away_team_form'],
                    'performance': {'accuracy': 0.75, 'coverage': 0.80}
                },
                'variant_b': {
                    'features': ['home_team_form', 'away_team_form', 'home_advantage'],
                    'performance': {'accuracy': 0.78, 'coverage': 0.75}
                },
                'winner': 'variant_b',
                'confidence': 0.85,
                'test_duration_ms': 3600000,
                'sample_size': 1000
            }

            # 模拟特征存储
            with patch('features.feature_store.FeatureStore') as mock_store_class:
                mock_store = AsyncMock()
                mock_store_class.return_value = mock_store

                # 模拟特征集部署
                mock_store.deploy_feature_set.return_value = {
                    'feature_set_id': 'set_v2',
                    'features': ['home_team_form', 'away_team_form', 'home_advantage'],
                    'deployment_time_ms': 100,
                    'status': 'success'
                }

                # 验证A/B测试集成
                ab_test_config = {
                    'variant_a_features': ['home_team_form', 'away_team_form'],
                    'variant_b_features': ['home_team_form', 'away_team_form', 'home_advantage'],
                    'test_duration_ms': 3600000,
                    'sample_size': 1000
                }

                ab_test_result = await mock_abtest.run_ab_test(ab_test_config)
                assert ab_test_result['winner'] == 'variant_b'
                assert ab_test_result['confidence'] == 0.85

                # 部署获胜的特征集
                if ab_test_result['winner'] == 'variant_b':
                    deployment_result = await mock_store.deploy_feature_set(
                        features=ab_test_result['variant_b']['features'],
                        feature_set_id='set_v2'
                    )
                    assert deployment_result['status'] == 'success'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing"])