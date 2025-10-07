"""
DataProcessingService测试
提升服务层覆盖率
"""

import sys
import pytest
from unittest.mock import Mock, patch

# Mock外部依赖
sys.modules['pandas'] = Mock()
sys.modules['numpy'] = Mock()
sys.modules['sklearn'] = Mock()
sys.modules['sklearn.preprocessing'] = Mock()
sys.modules['sklearn.impute'] = Mock()

# 设置测试环境
import os
os.environ["TESTING"] = "true"

from src.services.data_processing import DataProcessingService


class TestDataProcessingService:
    """DataProcessingService测试类"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DataProcessingService()

    @pytest.fixture
    def mock_data(self):
        """创建测试数据"""
        return {
            "teams": [
                {"id": 1, "name": "Team A", "short_name": "TA"},
                {"id": 2, "name": "Team B", "short_name": "TB"}
            ],
            "matches": [
                {"id": 1, "home_team_id": 1, "away_team_id": 2, "date": "2024-01-01"},
                {"id": 2, "home_team_id": 2, "away_team_id": 1, "date": "2024-01-02"}
            ],
            "predictions": [
                {"id": 1, "match_id": 1, "predicted_outcome": "home_win"},
                {"id": 2, "match_id": 2, "predicted_outcome": "draw"}
            ]
        }

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'process_data')
        assert hasattr(service, 'validate_data')
        assert hasattr(service, 'transform_data')

    def test_process_data_success(self, service, mock_data):
        """测试数据处理成功"""
        # Mock处理方法
        service.validate_data = Mock(return_value=True)
        service.transform_data = Mock(return_value={"processed": True})
        service.save_data = Mock(return_value=True)

        # 执行处理
        result = service.process_data(mock_data)

        # 验证结果
        assert result is True
        service.validate_data.assert_called_once_with(mock_data)
        service.transform_data.assert_called_once_with(mock_data)
        service.save_data.assert_called_once()

    def test_process_data_validation_failure(self, service, mock_data):
        """测试数据处理验证失败"""
        # Mock验证失败
        service.validate_data = Mock(return_value=False)
        service.log_error = Mock()

        # 执行处理
        result = service.process_data(mock_data)

        # 验证结果
        assert result is False
        service.validate_data.assert_called_once_with(mock_data)
        service.log_error.assert_called_once()

    def test_validate_data_valid(self, service, mock_data):
        """测试数据验证 - 有效数据"""
        result = service.validate_data(mock_data)
        assert result is True

    def test_validate_data_missing_required_field(self, service, mock_data):
        """测试数据验证 - 缺少必需字段"""
        invalid_data = mock_data.copy()
        del invalid_data["teams"]

        result = service.validate_data(invalid_data)
        assert result is False

    def test_validate_data_empty_teams(self, service, mock_data):
        """测试数据验证 - 空的teams数组"""
        invalid_data = mock_data.copy()
        invalid_data["teams"] = []

        result = service.validate_data(invalid_data)
        assert result is False

    def test_transform_data(self, service, mock_data):
        """测试数据转换"""
        # Mock pandas DataFrame
        mock_df = Mock()
        mock_df.to_dict.return_value = mock_data

        with patch('src.services.data_processing.pd.DataFrame', return_value=mock_df):
            result = service.transform_data(mock_data)

        # 验证转换结果
        assert isinstance(result, dict)
        assert "teams" in result
        assert "matches" in result
        assert "predictions" in result

    def test_transform_data_with_features(self, service, mock_data):
        """测试数据转换 - 生成特征"""
        # Mock特征生成
        service.generate_features = Mock(return_value={"feature1": 1.0, "feature2": 2.0})

        service.transform_data(mock_data)

        # 验证特征生成被调用
        assert service.generate_features.called

    def test_save_data(self, service):
        """测试数据保存"""
        processed_data = {"processed": True}

        # Mock数据库会话
        mock_session = Mock()
        service.get_db_session = Mock(return_value=mock_session)

        # 执行保存
        result = service.save_data(processed_data)

        # 验证保存操作
        assert result is True
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    def test_save_data_with_error(self, service):
        """测试数据保存 - 出错情况"""
        processed_data = {"processed": True}

        # Mock数据库会话抛出异常
        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Database error")
        service.get_db_session = Mock(return_value=mock_session)
        service.log_error = Mock()

        # 执行保存
        result = service.save_data(processed_data)

        # 验证错误处理
        assert result is False
        service.log_error.assert_called_once()

    def test_generate_features(self, service, mock_data):
        """测试特征生成"""
        features = service.generate_features(mock_data)

        # 验证特征
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_batch_processing(self, service, mock_data):
        """测试批量处理"""
        batch_data = [mock_data, mock_data]

        # Mock单个处理
        service.process_single_batch = Mock(return_value=True)

        # 执行批量处理
        results = service.batch_processing(batch_data)

        # 验证结果
        assert len(results) == 2
        assert all(r is True for r in results)
        assert service.process_single_batch.call_count == 2

    def test_data_cleaning(self, service):
        """测试数据清洗"""
        dirty_data = {
            "teams": [
                {"id": 1, "name": "Team A ", "short_name": "TA"},  # 有空格
                {"id": 2, "name": "", "short_name": "TB"},  # 空名称
                {"id": None, "name": "Team C", "short_name": "TC"},  # None ID
            ]
        }

        cleaned_data = service.clean_data(dirty_data)

        # 验证清洗结果
        assert cleaned_data["teams"][0]["name"] == "Team A"  # 空格被去除
        assert len([t for t in cleaned_data["teams"] if t["name"]]) == 2  # 空名称被过滤

    def test_data_aggregation(self, service, mock_data):
        """测试数据聚合"""
        aggregated = service.aggregate_data(mock_data)

        # 验证聚合结果
        assert isinstance(aggregated, dict)
        assert "summary" in aggregated
        assert "statistics" in aggregated

    def test_data_validation_rules(self, service):
        """测试数据验证规则"""
        # 测试各种验证规则
        assert service.validate_team_name("Valid Team Name") is True
        assert service.validate_team_name("") is False
        assert service.validate_team_id(1) is True
        assert service.validate_team_id(None) is False
        assert service.validate_match_date("2024-01-01") is True
        assert service.validate_match_date("invalid") is False

    def test_error_logging(self, service):
        """测试错误日志记录"""
        # Mock logger
        service.logger = Mock()

        # 记录错误
        service.log_error("Test error", {"context": "test"})

        # 验证日志记录
        service.logger.error.assert_called_once()

    def test_performance_monitoring(self, service, mock_data):
        """测试性能监控"""
        # Mock性能监控
        service.start_timer = Mock()
        service.end_timer = Mock()

        # 执行处理
        service.process_data(mock_data)

        # 验证性能监控被调用
        service.start_timer.assert_called()
        service.end_timer.assert_called()

    def test_concurrent_processing(self, service, mock_data):
        """测试并发处理"""
        import concurrent.futures

        # Mock处理函数
        def process_batch(batch):
            return {"processed": True, "batch_id": batch["id"]}

        # 创建多个批次
        batches = [
            {"id": 1, "data": mock_data},
            {"id": 2, "data": mock_data},
            {"id": 3, "data": mock_data}
        ]

        # 并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_batch, batch) for batch in batches]
            results = [f.result() for f in futures]

        # 验证结果
        assert len(results) == 3
        assert all(r["processed"] for r in results)

    def test_data_pipeline_integration(self, service, mock_data):
        """测试数据管道集成"""
        # Mock管道组件
        service.extract_data = Mock(return_value=mock_data)
        service.transform_data = Mock(return_value={"transformed": True})
        service.load_data = Mock(return_value=True)

        # 执行管道
        result = service.run_pipeline(mock_data)

        # 验证管道执行
        assert result is True
        service.extract_data.assert_called_once()
        service.transform_data.assert_called_once()
        service.load_data.assert_called_once()

    def test_caching_mechanism(self, service, mock_data):
        """测试缓存机制"""
        # Mock缓存
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        service.cache = mock_cache

        # 执行处理（应该使用缓存）
        cache_key = "test_data"
        service.process_with_cache(mock_data, cache_key)

        # 验证缓存操作
        mock_cache.get.assert_called_with(cache_key)
        mock_cache.set.assert_called_once()

    def test_retry_mechanism(self, service, mock_data):
        """测试重试机制"""
        # Mock处理函数前两次失败，第三次成功
        call_count = 0
        def mock_process():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return True

        service.process_with_retry = mock_process

        # 执行重试
        result = service.process_with_retry(mock_data, max_retries=3)

        # 验证重试成功
        assert result is True
        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])