"""
比赛数据处理器测试
Match Processor Tests

测试Phase 5+重写的MatchProcessor功能
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from src.services.processing.processors.match_processor import MatchProcessor


class TestMatchProcessor:
    """MatchProcessor测试类"""

    @pytest.fixture
    def processor(self):
        """测试用处理器实例"""
        return MatchProcessor()

    @pytest.fixture
    def sample_raw_data(self):
        """示例原始数据"""
        return [
            {
                "match_id": 1,
                "home_team": "MANCHESTER UNITED",
                "away_team": "LIVERPOOL",
                "match_date": "2023-12-25",
                "home_score": "2",
                "away_score": "1",
                "venue": "OLD TRAFFORD",
                "competition": "PREMIER LEAGUE",
                "season": "2023-24"
            },
            {
                "match_id": 2,
                "home_team": "ARSENAL",
                "away_team": "CHELSEA",
                "match_date": "2023-12-26",
                "home_score": "3",
                "away_score": "1",
                "venue": "EMIRATES STADIUM",
                "competition": "PREMIER LEAGUE",
                "season": "2023-24"
            },
            {
                "match_id": 3,
                "home_team": "BARCELONA",
                "away_team": "REAL MADRID",
                "match_date": "2023-12-27",
                "home_score": "invalid",
                "away_score": "2",
                "venue": "CAMP NOU",
                "competition": "LA LIGA",
                "season": "2023-24"
            }
        ]

    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """测试处理器初始化"""
        assert processor.required_fields == {
            "match_id",
            "home_team",
            "away_team",
            "match_date",
            "home_score",
            "away_score"
        }
        assert processor.optional_fields == {
            "venue",
            "competition",
            "season",
            "match_status"
        }

    @pytest.mark.asyncio
    async def test_process_raw_match_data_valid(self, processor, sample_raw_data):
        """测试处理原始比赛数据 - 有效数据"""
        result = await processor.process_raw_match_data(sample_raw_data)

        assert len(result) == 2  # 第三条数据无效，应该被过滤
        assert result[0]["match_id"] == 1
        assert result[0]["home_team"] == "Manchester United"
        assert result[0]["away_team"] == "Liverpool"
        assert result[0]["home_score"] == 2
        assert result[0]["away_score"] == 1
        assert result[0]["venue"] == "Old Trafford"
        assert result[0]["competition"] == "Premier League"
        assert "total_goals" in result[0]
        assert "goal_difference" in result[0]
        assert "winner" in result[0]

    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty(self, processor):
        """测试处理原始比赛数据 - 空数据"""
        result = await processor.process_raw_match_data([])

        assert result == []

    @pytest.mark.asyncio
    async def test_process_raw_match_data_exception(self, processor, sample_raw_data):
        """测试处理原始比赛数据 - 异常处理"""
        # 模拟处理过程中出现异常
        with patch.object(processor, '_process_single_match', side_effect=Exception("Test error")):
            result = await processor.process_raw_match_data(sample_raw_data)

            assert result == []  # 异常时应该返回空列表

    @pytest.mark.asyncio
    async def test_process_single_match_valid(self, processor):
        """测试处理单个比赛 - 有效数据"""
        match_data = {
            "match_id": 1,
            "home_team": "MANCHESTER UNITED",
            "away_team": "LIVERPOOL",
            "match_date": "2023-12-25",
            "home_score": "2",
            "away_score": "1"
        }

        result = await processor._process_single_match(match_data)

        assert result is not None
        assert result["match_id"] == "1"
        assert result["home_team"] == "Manchester United"
        assert result["away_team"] == "Liverpool"
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["total_goals"] == 3
        assert result["goal_difference"] == 1
        assert result["winner"] == "home"

    @pytest.mark.asyncio
    async def test_process_single_match_missing_required_fields(self, processor):
        """测试处理单个比赛 - 缺少必需字段"""
        match_data = {
            "home_team": "MANCHESTER UNITED",
            "away_team": "LIVERPOOL"
            # 缺少match_id, match_date, home_score, away_score
        }

        result = await processor._process_single_match(match_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_required_fields_valid(self, processor):
        """测试验证必需字段 - 有效"""
        match_data = {
            "match_id": 1,
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2023-12-25",
            "home_score": 2,
            "away_score": 1
        }

        result = await processor._validate_required_fields(match_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_required_fields_missing(self, processor):
        """测试验证必需字段 - 缺少字段"""
        match_data = {
            "home_team": "Team A",
            "away_team": "Team B"
        }

        result = await processor._validate_required_fields(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_clean_match_data(self, processor):
        """测试清洗比赛数据"""
        match_data = {
            "match_id": 1,
            "home_team": "  MANCHESTER UNITED  ",
            "away_team": "LIVERPOOL",
            "home_score": "2",
            "away_score": "1",
            "venue": "  Old Trafford  ",
            "competition": None,
            "match_date": "2023-12-25"
        }

        result = await processor._clean_match_data(match_data)

        assert result["home_team"] == "Manchester United"
        assert result["away_team"] == "Liverpool"
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["venue"] == "Old Trafford"
        assert result["competition"] == ""
        assert isinstance(result["match_date"], datetime)

    @pytest.mark.asyncio
    async def test_parse_date_standard_format(self, processor):
        """测试解析日期 - 标准格式"""
        result = await processor._parse_date("2023-12-25")

        assert result == datetime(2023, 12, 25)

    @pytest.mark.asyncio
    async def test_parse_date_datetime_object(self, processor):
        """测试解析日期 - datetime对象"""
        dt = datetime(2023, 12, 25, 15, 30, 45)
        result = await processor._parse_date(dt)

        assert result == dt

    @pytest.mark.asyncio
    async def test_parse_date_various_formats(self, processor):
        """测试解析日期 - 各种格式"""
        test_cases = [
            ("2023-12-25", datetime(2023, 12, 25)),
            ("2023-12-25 15:30:45", datetime(2023, 12, 25, 15, 30, 45)),
            ("25/12/2023", datetime(2023, 12, 25)),
            ("20231225", datetime(2023, 12, 25))
        ]

        for date_str, expected in test_cases:
            result = await processor._parse_date(date_str)
            assert result == expected

    @pytest.mark.asyncio
    async def test_parse_date_invalid(self, processor):
        """测试解析日期 - 无效格式"""
        result = await processor._parse_date("invalid_date")

        assert result is None

    @pytest.mark.asyncio
    async def test_standardize_match_data(self, processor):
        """测试标准化比赛数据"""
        cleaned_data = {
            "match_id": 1,
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "home_score": 2,
            "away_score": 1,
            "venue": "Old Trafford",
            "competition": "Premier League",
            "match_date": datetime(2023, 12, 25)
        }

        result = await processor._standardize_match_data(cleaned_data)

        assert result["match_id"] == "1"
        assert result["home_team"] == "Manchester United"
        assert result["away_team"] == "Liverpool"
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["total_goals"] == 3
        assert result["goal_difference"] == 1
        assert result["winner"] == "home"
        assert result["venue"] == "Old Trafford"
        assert result["competition"] == "Premier League"
        assert result["match_status"] == "finished"  # 默认值
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_determine_winner_home_win(self, processor):
        """测试确定获胜者 - 主队获胜"""
        result = await processor._determine_winner(3, 1)

        assert result == "home"

    @pytest.mark.asyncio
    async def test_determine_winner_away_win(self, processor):
        """测试确定获胜者 - 客队获胜"""
        result = await processor._determine_winner(1, 3)

        assert result == "away"

    @pytest.mark.asyncio
    async def test_determine_winner_draw(self, processor):
        """测试确定获胜者 - 平局"""
        result = await processor._determine_winner(2, 2)

        assert result == "draw"

    @pytest.mark.asyncio
    async def test_process_dataframe_valid(self, processor, sample_raw_data):
        """测试处理DataFrame - 有效数据"""
        df = pd.DataFrame(sample_raw_data)
        result = await processor.process_dataframe(df)

        assert isinstance(result, pd.DataFrame)
        # 第三条数据无效，应该被过滤
        assert len(result) == 2
        assert "match_id" in result.columns
        assert "home_team" in result.columns
        assert "total_goals" in result.columns

    @pytest.mark.asyncio
    async def test_process_dataframe_empty(self, processor):
        """测试处理DataFrame - 空数据"""
        df = pd.DataFrame()
        result = await processor.process_dataframe(df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_validate_match_integrity_valid(self, processor):
        """测试验证比赛完整性 - 有效数据"""
        match_data = {
            "home_score": 2,
            "away_score": 1,
            "match_date": datetime.utcnow()
        }

        result = await processor.validate_match_integrity(match_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_match_integrity_negative_scores(self, processor):
        """测试验证比赛完整性 - 负分"""
        match_data = {
            "home_score": -1,
            "away_score": 1,
            "match_date": datetime.utcnow()
        }

        result = await processor.validate_match_integrity(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_match_integrity_future_date(self, processor):
        """测试验证比赛完整性 - 未来日期"""
        future_date = datetime.utcnow() + timedelta(days=60)  # 超过30天的未来日期
        match_data = {
            "home_score": 2,
            "away_score": 1,
            "match_date": future_date
        }

        result = await processor.validate_match_integrity(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_match_integrity_exception(self, processor):
        """测试验证比赛完整性 - 异常处理"""
        match_data = {
            "home_score": "invalid",
            "away_score": 1
        }

        result = await processor.validate_match_integrity(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_processing_stats(self, processor):
        """测试获取处理统计"""
        stats = await processor.get_processing_stats(10, 8)

        assert stats["original_count"] == 10
        assert stats["processed_count"] == 8
        assert stats["failed_count"] == 2
        assert stats["success_rate"] == 80.0
        assert "processed_at" in stats

    @pytest.mark.asyncio
    async def test_batch_process(self, processor, sample_raw_data):
        """测试批量处理"""
        # 将数据分成两批
        batch1 = sample_raw_data[:2]
        batch2 = sample_raw_data[2:]

        data_batches = [batch1, batch2]

        with patch.object(processor, 'process_raw_match_data') as mock_process:
            # 模拟第一批处理2个，第二批处理1个（第三条无效）
            mock_process.side_effect = [
                [{"id": 1}, {"id": 2}],  # 第一批结果
                [{"id": 3}]               # 第二批结果
            ]

            result = await processor.batch_process(data_batches)

            assert len(result) == 3
            assert mock_process.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_process_empty_batches(self, processor):
        """测试批量处理 - 空批次"""
        data_batches = [[], [], []]

        result = await processor.batch_process(data_batches)

        assert result == []

    @pytest.mark.asyncio
    async def test_batch_process_with_logging(self, processor, sample_raw_data):
        """测试批量处理 - 日志记录"""
        data_batches = [sample_raw_data]

        with patch.object(processor, 'process_raw_match_data') as mock_process:
            with patch.object(processor.logger, 'info') as mock_logger:
                mock_process.return_value = [{"id": 1}]

                result = await processor.batch_process(data_batches)

                assert len(result) == 1
                mock_logger.assert_called()


class TestMatchProcessorIntegration:
    """MatchProcessor集成测试类"""

    @pytest.mark.asyncio
    async def test_complete_processing_pipeline(self):
        """测试完整处理流水线"""
        processor = MatchProcessor()

        raw_data = [
            {
                "match_id": 1,
                "home_team": "MANCHESTER UNITED",
                "away_team": "LIVERPOOL",
                "match_date": "2023-12-25",
                "home_score": "2",
                "away_score": "1",
                "venue": "OLD TRAFFORD"
            }
        ]

        # 处理数据
        processed_data = await processor.process_raw_match_data(raw_data)

        # 验证结果
        assert len(processed_data) == 1
        match = processed_data[0]

        # 验证数据清洗
        assert match["home_team"] == "Manchester United"
        assert match["away_team"] == "Liverpool"
        assert match["venue"] == "Old Trafford"

        # 验证数据标准化
        assert match["match_id"] == "1"
        assert match["total_goals"] == 3
        assert match["goal_difference"] == 1
        assert match["winner"] == "home"

        # 验证完整性
        assert "processed_at" in match

    @pytest.mark.asyncio
    async def test_error_handling_robustness(self):
        """测试错误处理健壮性"""
        processor = MatchProcessor()

        # 测试各种异常情况
        test_cases = [
            [],  # 空数据
            [{}],  # 空字典
            [{"invalid": "data"}],  # 缺少必需字段
            [{"home_score": "invalid", "away_score": "1"}],  # 无效数据类型
        ]

        for test_data in test_cases:
            try:
                result = await processor.process_raw_match_data(test_data)
                # 应该不抛出异常，返回空列表或过滤后的结果
                assert isinstance(result, list)
            except Exception as e:
                pytest.fail(f"处理数据时不应抛出异常: {e}")

    @pytest.mark.asyncio
    async def test_dataframe_integration(self):
        """测试DataFrame集成"""
        processor = MatchProcessor()

        # 创建测试DataFrame
        data = {
            "match_id": [1, 2],
            "home_team": ["TEAM A", "TEAM B"],
            "away_team": ["TEAM C", "TEAM D"],
            "match_date": ["2023-12-25", "2023-12-26"],
            "home_score": [2, 1],
            "away_score": [1, 1]
        }

        df = pd.DataFrame(data)
        result = await processor.process_dataframe(df)

        # 验证结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "total_goals" in result.columns
        assert "winner" in result.columns