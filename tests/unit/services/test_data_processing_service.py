"""
数据处理服务测试
Data Processing Service Tests

测试数据处理服务的功能。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# 添加src到路径
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.services.data_processing import DataProcessingService
from src.core.exceptions import DataProcessingError as ProcessingError, ValidationError


@pytest.mark.unit
@pytest.mark.fast
class TestDataProcessingService:
    """测试数据处理服务"""

    @pytest.fixture
    def service(self):
        """创建数据处理服务实例"""
        return DataProcessingService()

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return [
            {
                "match_id": 1,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "date": "2023-01-01",
                "league": "Premier League",
            },
            {
                "match_id": 2,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
                "date": "2023-01-02",
                "league": "Premier League",
            },
        ]

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.service_name == "data_processing"
        assert hasattr(service, "cache")
        assert hasattr(service, "database")

    @pytest.mark.asyncio
    async def test_process_match_data(self, service, sample_data):
        """测试处理比赛数据"""
        # 模拟数据库操作
        service.database = Mock()
        service.database.insert.return_value = True

        result = await service.process_match_data(sample_data)

        assert result["processed_count"] == 2
        assert result["errors"] == []
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_process_match_data_with_errors(self, service):
        """测试处理无效数据时的错误"""
        invalid_data = [
            {"match_id": None, "home_team": ""},  # 无效数据
            {"invalid": "data"},  # 缺少必需字段
        ]

        result = await service.process_match_data(invalid_data)

        assert result["processed_count"] == 0
        assert len(result["errors"]) == 2
        assert result["status"] == "failed"

    def test_validate_match_data(self, service, sample_data):
        """验证比赛数据"""
        for data in sample_data:
            is_valid = service.validate_match_data(data)
            assert is_valid is True

    def test_validate_invalid_match_data(self, service):
        """验证无效比赛数据"""
        invalid_cases = [
            {},  # 空数据
            {"match_id": None},  # 缺少必需字段
            {"match_id": 1, "home_team": ""},  # 空值
            {"match_id": 1, "home_score": "invalid"},  # 错误类型
        ]

        for case in invalid_cases:
            with pytest.raises(ValidationError):
                service.validate_match_data(case)

    def test_calculate_team_statistics(self, service, sample_data):
        """测试计算球队统计"""
        stats = service.calculate_team_statistics(sample_data)

        # 验证统计数据
        assert "Team A" in stats
        assert "Team B" in stats
        assert "Team C" in stats
        assert "Team D" in stats

        # Team A: 1场比赛，2进球，1失球，3分
        team_a_stats = stats["Team A"]
        assert team_a_stats["matches_played"] == 1
        assert team_a_stats["goals_for"] == 2
        assert team_a_stats["goals_against"] == 1
        assert team_a_stats["points"] == 3

        # Team C: 1场比赛，1进球，1失球，1分
        team_c_stats = stats["Team C"]
        assert team_c_stats["matches_played"] == 1
        assert team_c_stats["goals_for"] == 1
        assert team_c_stats["goals_against"] == 1
        assert team_c_stats["points"] == 1

    def test_calculate_league_standings(self, service, sample_data):
        """测试计算联赛积分榜"""
        standings = service.calculate_league_standings(sample_data)

        # 验证积分榜结构
        assert len(standings) == 4  # 4支球队
        assert all("position" in team for team in standings)
        assert all("points" in team for team in standings)
        assert all("goal_difference" in team for team in standings)

        # Team A应该排在第一（3分）
        assert standings[0]["name"] == "Team A"
        assert standings[0]["points"] == 3

    def test_process_time_series_data(self, service):
        """测试处理时间序列数据"""
        # 创建时间序列数据
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        values = np.random.randn(10).cumsum()

        time_series = pd.DataFrame({"date": dates, "value": values})

        processed = service.process_time_series_data(time_series)

        # 验证处理结果
        assert "moving_average" in processed.columns
        assert "trend" in processed.columns
        assert len(processed) == 10

    def test_filter_data_by_date_range(self, service, sample_data):
        """测试按日期范围过滤数据"""
        # 转换日期格式
        for item in sample_data:
            item["date"] = datetime.strptime(item["date"], "%Y-%m-%d")

        # 设置过滤范围
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 1)

        filtered = service.filter_data_by_date_range(
            sample_data, start_date, end_date, date_field="date"
        )

        # 应该只返回第一场比赛
        assert len(filtered) == 1
        assert filtered[0]["match_id"] == 1

    def test_aggregate_data_by_field(self, service, sample_data):
        """测试按字段聚合数据"""
        aggregated = service.aggregate_data_by_field(
            sample_data,
            group_by="league",
            aggregations={"home_score": "mean", "away_score": "sum"},
        )

        # 验证聚合结果
        assert "Premier League" in aggregated
        assert "home_score_mean" in aggregated["Premier League"]
        assert "away_score_sum" in aggregated["Premier League"]

    @pytest.mark.asyncio
    async def test_batch_process_data(self, service):
        """测试批量处理数据"""
        # 创建大量数据
        large_dataset = [
            {"id": i, "value": i * 2, "category": f"cat_{i % 5}"} for i in range(100)
        ]

        # 设置批处理大小
        batch_size = 20

        processed_count = 0
        async for batch in service.batch_process_data(large_dataset, batch_size):
            assert len(batch) <= batch_size
            processed_count += len(batch)

        assert processed_count == 100

    def test_data_transformation_pipeline(self, service):
        """测试数据转换管道"""
        # 创建原始数据
        raw_data = [
            {"name": "Team A", "score": "10"},
            {"name": "Team B", "score": "15"},
            {"name": "Team C", "score": "invalid"},
        ]

        # 定义转换管道
        transformations = [
            lambda x: {**x, "score": int(x["score"]) if x["score"].isdigit() else 0},
            lambda x: {**x, "score_normalized": x["score"] / 15.0},
            lambda x: {**x, "grade": "A" if x["score_normalized"] > 0.8 else "B"},
        ]

        # 执行转换
        transformed = service.apply_transformations(raw_data, transformations)

        # 验证转换结果
        assert transformed[0]["score"] == 10
        assert transformed[0]["score_normalized"] == 10 / 15
        assert transformed[0]["grade"] == "B"

        assert transformed[1]["score"] == 15
        assert transformed[1]["score_normalized"] == 1.0
        assert transformed[1]["grade"] == "A"

        assert transformed[2]["score"] == 0  # invalid被转换为0

    def test_export_data_to_csv(self, service, sample_data, tmp_path):
        """测试导出数据到CSV"""
        import tempfile

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = f.name

        # 导出数据
        service.export_to_csv(sample_data, temp_path)

        # 验证文件存在
        import os

        assert os.path.exists(temp_path)

        # 验证内容
        df = pd.read_csv(temp_path)
        assert len(df) == 2
        assert "match_id" in df.columns
        assert "home_team" in df.columns

        # 清理
        os.unlink(temp_path)

    def test_import_data_from_json(self, service, tmp_path):
        """测试从JSON导入数据"""
        import tempfile
        import json

        # 创建临时JSON文件
        test_data = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        # 导入数据
        imported_data = service.import_from_json(temp_path)

        # 验证导入结果
        assert len(imported_data) == 2
        assert imported_data[0]["id"] == 1
        assert imported_data[1]["name"] == "test2"

        # 清理
        import os

        os.unlink(temp_path)

    def test_data_cleaning(self, service):
        """测试数据清洗"""
        dirty_data = [
            {"name": "Team A ", "score": 10},  # 多余空格
            {"name": None, "score": None},  # 空值
            {"name": "Team B", "score": 15},  # 正常数据
            {"name": "", "score": ""},  # 空字符串
        ]

        cleaned = service.clean_data(dirty_data)

        # 验证清洗结果
        assert len(cleaned) == 2  # 只保留有效数据
        assert cleaned[0]["name"] == "Team A"  # 空格被去除
        assert cleaned[1]["name"] == "Team B"

    @pytest.mark.asyncio
    async def test_data_enrichment(self, service):
        """测试数据增强"""
        base_data = [{"match_id": 1, "home_team": "Team A", "away_team": "Team B"}]

        # 模拟外部数据源
        async def fetch_team_stats(team_name):
            return {"goals": 10, "wins": 5}

        enriched = await service.enrich_data(
            base_data,
            enrichers={
                "home_stats": lambda x: fetch_team_stats(x["home_team"]),
                "away_stats": lambda x: fetch_team_stats(x["away_team"]),
            },
        )

        # 验证增强结果
        assert "home_stats" in enriched[0]
        assert "away_stats" in enriched[0]
        assert enriched[0]["home_stats"]["goals"] == 10

    def test_data_validation_rules(self, service):
        """测试数据验证规则"""
        # 定义验证规则
        rules = {
            "match_id": lambda x: isinstance(x, int) and x > 0,
            "home_team": lambda x: isinstance(x, str) and len(x) > 0,
            "home_score": lambda x: isinstance(x, int) and x >= 0,
        }

        valid_data = {"match_id": 1, "home_team": "Team A", "home_score": 2}
        invalid_data = {"match_id": -1, "home_team": "", "home_score": -1}

        # 验证有效数据
        assert service.validate_with_rules(valid_data, rules) is True

        # 验证无效数据
        with pytest.raises(ValidationError):
            service.validate_with_rules(invalid_data, rules)

    def test_performance_monitoring(self, service):
        """测试性能监控"""
        # 模拟大量数据处理
        large_data = [{"value": i} for i in range(1000)]

        with service.measure_performance("data_processing"):
            service.process_data(large_data)

        # 验证性能指标被记录
        metrics = service.get_performance_metrics()
        assert "data_processing" in metrics
        assert "duration" in metrics["data_processing"]
        assert "records_processed" in metrics["data_processing"]
