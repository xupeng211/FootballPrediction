"""
数据处理服务单元测试

测试数据清洗器、缺失值处理器和Bronze到Silver层数据处理功能。
验证清洗逻辑的正确性和异常数据的处理。

基于 DATA_DESIGN.md 第4节设计的测试。
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.data.processing.missing_data_handler import MissingDataHandler
from src.services.data_processing import DataProcessingService


class TestDataProcessingService(unittest.TestCase):
    """数据处理服务测试类"""

    def setUp(self):
        """设置测试环境"""
        self.service = DataProcessingService()
        self.sample_match_data = {
            "id": "123456",
            "homeTeam": {"id": "1", "name": "Team A"},
            "awayTeam": {"id": "2", "name": "Team B"},
            "utcDate": "2024-01-15T15:00:00Z",
            "score": {
                "fullTime": {"home": 2, "away": 1},
                "halfTime": {"home": 1, "away": 0},
            },
            "status": "FINISHED",
            "competition": {"id": "PL", "name": "Premier League"},
        }

        self.sample_odds_data = [
            {
                "match_id": "123456",
                "bookmaker": "Bet365",
                "market_type": "h2h",
                "outcomes": [
                    {"name": "1", "price": 2.50},
                    {"name": "X", "price": 3.20},
                    {"name": "2", "price": 2.80},
                ],
                "last_update": "2024-01-15T14:00:00Z",
            }
        ]

    @patch("src.services.data_processing.DatabaseManager")
    @patch("src.services.data_processing.DataLakeStorage")
    @patch("src.services.data_processing.MissingDataHandler")
    @patch("src.services.data_processing.FootballDataCleaner")
    async def test_initialize_service(
        self, mock_cleaner, mock_handler, mock_lake, mock_db
    ):
        """测试服务初始化"""
        mock_cleaner.return_value = MagicMock()
        mock_handler.return_value = MagicMock()
        mock_lake.return_value = MagicMock()
        mock_db.return_value = MagicMock()

        result = await self.service.initialize()

        self.assertTrue(result)
        self.assertIsNotNone(self.service.data_cleaner)
        self.assertIsNotNone(self.service.missing_handler)
        self.assertIsNotNone(self.service.data_lake)
        self.assertIsNotNone(self.service.db_manager)

    async def test_process_raw_match_data_success(self):
        """测试成功处理原始比赛数据"""
        # 模拟初始化的服务
        self.service.data_cleaner = AsyncMock()
        self.service.missing_handler = AsyncMock()

        cleaned_data = {
            "external_match_id": "123456",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00+00:00",
            "home_score": 2,
            "away_score": 1,
        }

        processed_data = cleaned_data.copy()
        processed_data["venue"] = "Stadium A"

        self.service.data_cleaner.clean_match_data.return_value = cleaned_data
        self.service.missing_handler.handle_missing_match_data.return_value = (
            processed_data
        )

        result = await self.service.process_raw_match_data(self.sample_match_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["external_match_id"], "123456")
        self.assertEqual(result["venue"], "Stadium A")
        self.service.data_cleaner.clean_match_data.assert_called_once_with(
            self.sample_match_data
        )
        self.service.missing_handler.handle_missing_match_data.assert_called_once_with(
            cleaned_data
        )

    async def test_process_raw_match_data_cleaning_failed(self):
        """测试清洗失败的情况"""
        self.service.data_cleaner = AsyncMock()
        self.service.data_cleaner.clean_match_data.return_value = None

        result = await self.service.process_raw_match_data(self.sample_match_data)

        self.assertIsNone(result)

    async def test_process_raw_odds_data_success(self):
        """测试成功处理赔率数据"""
        self.service.data_cleaner = AsyncMock()

        cleaned_odds = [
            {
                "external_match_id": "123456",
                "bookmaker": "bet365",
                "market_type": "1x2",
                "outcomes": [
                    {"name": "home", "price": 2.500},
                    {"name": "draw", "price": 3.200},
                    {"name": "away", "price": 2.800},
                ],
                "implied_probabilities": {"home": 0.33, "draw": 0.26, "away": 0.30},
            }
        ]

        self.service.data_cleaner.clean_odds_data.return_value = cleaned_odds

        result = await self.service.process_raw_odds_data(self.sample_odds_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bookmaker"], "bet365")
        self.assertEqual(result[0]["market_type"], "1x2")
        self.service.data_cleaner.clean_odds_data.assert_called_once_with(
            self.sample_odds_data
        )

    async def test_validate_data_quality_match_success(self):
        """测试比赛数据质量验证成功"""
        valid_match_data = {
            "external_match_id": "123456",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00Z",
            "home_score": 2,
            "away_score": 1,
        }

        result = await self.service.validate_data_quality(valid_match_data, "match")

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["data_type"], "match")
        self.assertEqual(len(result["issues"]), 0)

    async def test_validate_data_quality_match_missing_fields(self):
        """测试比赛数据缺少必需字段"""
        invalid_match_data = {
            "home_team_id": 1,
            "away_team_id": 2,
            # 缺少 external_match_id 和 match_time
        }

        result = await self.service.validate_data_quality(invalid_match_data, "match")

        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["issues"]), 0)
        self.assertTrue(any("external_match_id" in issue for issue in result["issues"]))
        self.assertTrue(any("match_time" in issue for issue in result["issues"]))

    async def test_validate_data_quality_negative_scores(self):
        """测试负比分数据验证"""
        invalid_match_data = {
            "external_match_id": "123456",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00Z",
            "home_score": -1,  # 负分数
            "away_score": 2,
        }

        result = await self.service.validate_data_quality(invalid_match_data, "match")

        self.assertFalse(result["is_valid"])
        self.assertTrue(
            any("Negative scores detected" in issue for issue in result["issues"])
        )

    async def test_validate_data_quality_odds_success(self):
        """测试赔率数据质量验证成功"""
        valid_odds_data = {
            "outcomes": [{"price": 2.50}, {"price": 3.20}, {"price": 2.80}]
        }

        result = await self.service.validate_data_quality(valid_odds_data, "odds")

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["data_type"], "odds")

    async def test_validate_data_quality_invalid_odds_price(self):
        """测试无效赔率价格"""
        invalid_odds_data = {"outcomes": [{"price": 0.50}, {"price": 3.20}]}  # 赔率过低

        result = await self.service.validate_data_quality(invalid_odds_data, "odds")

        self.assertFalse(result["is_valid"])
        self.assertTrue(
            any("Invalid odds price" in issue for issue in result["issues"])
        )


class TestFootballDataCleaner(unittest.TestCase):
    """足球数据清洗器测试类"""

    def setUp(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()
        self.sample_match_data = {
            "id": "123456",
            "homeTeam": {"id": "1", "name": "Team A"},
            "awayTeam": {"id": "2", "name": "Team B"},
            "utcDate": "2024-01-15T15:00:00Z",
            "score": {
                "fullTime": {"home": 2, "away": 1},
                "halfTime": {"home": 1, "away": 0},
            },
            "status": "FINISHED",
            "competition": {"id": "PL", "name": "Premier League"},
            "season": {"id": "2023", "startDate": "2023-08-01T00:00:00Z"},
            "venue": "Old Trafford",
            "referees": [{"role": "REFEREE", "name": "John Smith"}],
        }

    async def test_clean_match_data_success(self):
        """测试成功清洗比赛数据"""
        with patch.object(
            self.cleaner, "_map_team_id", side_effect=[1, 2]
        ), patch.object(self.cleaner, "_map_league_id", return_value=10):
            result = await self.cleaner.clean_match_data(self.sample_match_data)

            self.assertIsNotNone(result)
            self.assertEqual(result["external_match_id"], "123456")
            self.assertEqual(result["home_team_id"], 1)
            self.assertEqual(result["away_team_id"], 2)
            self.assertEqual(result["league_id"], 10)
            self.assertEqual(result["home_score"], 2)
            self.assertEqual(result["away_score"], 1)
            self.assertEqual(result["match_status"], "finished")
            self.assertIsNotNone(result["match_time"])

    async def test_clean_match_data_invalid_input(self):
        """测试无效输入数据"""
        invalid_data = {"invalid": "data"}  # 缺少必需字段

        result = await self.cleaner.clean_match_data(invalid_data)

        self.assertIsNone(result)

    def test_validate_score_valid(self):
        """测试有效比分验证"""
        self.assertEqual(self.cleaner._validate_score(0), 0)
        self.assertEqual(self.cleaner._validate_score(5), 5)
        self.assertEqual(self.cleaner._validate_score(99), 99)

    def test_validate_score_invalid(self):
        """测试无效比分验证"""
        self.assertIsNone(self.cleaner._validate_score(-1))  # 负数
        self.assertIsNone(self.cleaner._validate_score(100))  # 超出范围
        self.assertIsNone(self.cleaner._validate_score("invalid"))  # 非数字
        self.assertIsNone(self.cleaner._validate_score(None))  # 空值

    def test_to_utc_time_valid_formats(self):
        """测试UTC时间转换的各种格式"""
        # ISO格式，带Z
        result1 = self.cleaner._to_utc_time("2024-01-15T15:00:00Z")
        self.assertIsNotNone(result1)
        self.assertIn("2024-01-15", result1)

        # ISO格式，带时区
        result2 = self.cleaner._to_utc_time("2024-01-15T15:00:00+01:00")
        self.assertIsNotNone(result2)

        # 无效格式
        result3 = self.cleaner._to_utc_time("invalid-date")
        self.assertIsNone(result3)

        # 空值
        result4 = self.cleaner._to_utc_time(None)
        self.assertIsNone(result4)

    def test_standardize_match_status(self):
        """测试比赛状态标准化"""
        self.assertEqual(self.cleaner._standardize_match_status("FINISHED"), "finished")
        self.assertEqual(self.cleaner._standardize_match_status("IN_PLAY"), "live")
        self.assertEqual(
            self.cleaner._standardize_match_status("SCHEDULED"), "scheduled"
        )
        self.assertEqual(
            self.cleaner._standardize_match_status("CANCELLED"), "cancelled"
        )
        self.assertEqual(
            self.cleaner._standardize_match_status("UNKNOWN_STATUS"), "unknown"
        )
        self.assertEqual(self.cleaner._standardize_match_status(None), "unknown")

    async def test_clean_odds_data_success(self):
        """测试成功清洗赔率数据"""
        odds_data = [
            {
                "match_id": "123456",
                "bookmaker": "Bet 365",
                "market_type": "h2h",
                "outcomes": [
                    {"name": "1", "price": 2.50},
                    {"name": "X", "price": 3.20},
                    {"name": "2", "price": 2.80},
                ],
                "last_update": "2024-01-15T14:00:00Z",
            }
        ]

        result = await self.cleaner.clean_odds_data(odds_data)

        self.assertEqual(len(result), 1)
        cleaned_odds = result[0]
        self.assertEqual(cleaned_odds["external_match_id"], "123456")
        self.assertEqual(cleaned_odds["bookmaker"], "bet_365")
        self.assertEqual(cleaned_odds["market_type"], "1x2")
        self.assertEqual(len(cleaned_odds["outcomes"]), 3)
        self.assertIn("implied_probabilities", cleaned_odds)

    async def test_clean_odds_data_invalid_price(self):
        """测试无效赔率价格"""
        odds_data = [
            {
                "match_id": "123456",
                "bookmaker": "Bookmaker",
                "market_type": "h2h",
                "outcomes": [
                    {"name": "1", "price": 0.50},  # 无效价格
                    {"name": "X", "price": 3.20},
                ],
            }
        ]

        result = await self.cleaner.clean_odds_data(odds_data)

        # 应该跳过包含无效赔率的数据
        self.assertEqual(len(result), 0)

    def test_validate_odds_consistency_valid(self):
        """测试有效赔率一致性"""
        outcomes = [{"price": 2.50}, {"price": 3.20}, {"price": 2.80}]

        result = self.cleaner._validate_odds_consistency(outcomes)
        self.assertTrue(result)

    def test_validate_odds_consistency_invalid(self):
        """测试无效赔率一致性"""
        outcomes = [{"price": 1.01}, {"price": 1.01}]  # 总概率过高

        result = self.cleaner._validate_odds_consistency(outcomes)
        self.assertFalse(result)

    def test_calculate_implied_probabilities(self):
        """测试隐含概率计算"""
        outcomes = [
            {"name": "home", "price": 2.0},
            {"name": "draw", "price": 4.0},
            {"name": "away", "price": 2.0},
        ]

        probabilities = self.cleaner._calculate_implied_probabilities(outcomes)

        self.assertIn("home", probabilities)
        self.assertIn("draw", probabilities)
        self.assertIn("away", probabilities)

        # 概率之和应该约等于1（标准化后）
        total_prob = sum(probabilities.values())
        self.assertAlmostEqual(total_prob, 1.0, places=2)


class TestMissingDataHandler(unittest.TestCase):
    """缺失数据处理器测试类"""

    def setUp(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    async def test_handle_missing_match_data_with_missing_scores(self):
        """测试处理缺失比分数据"""
        match_data = {
            "id": "123456",
            "home_score": None,  # 缺失
            "away_score": None,  # 缺失
            "venue": None,  # 缺失
            "referee": None,  # 缺失
        }

        result = await self.handler.handle_missing_match_data(match_data)

        self.assertEqual(result["home_score"], 0)  # 填充为0
        self.assertEqual(result["away_score"], 0)  # 填充为0
        self.assertEqual(result["venue"], "Unknown")  # 填充为Unknown
        self.assertEqual(result["referee"], "Unknown")  # 填充为Unknown

    async def test_handle_missing_match_data_no_missing_values(self):
        """测试处理无缺失值的数据"""
        match_data = {
            "id": "123456",
            "home_score": 2,
            "away_score": 1,
            "venue": "Stadium A",
            "referee": "John Doe",
        }

        result = await self.handler.handle_missing_match_data(match_data)

        # 数据应该保持不变
        self.assertEqual(result["home_score"], 2)
        self.assertEqual(result["away_score"], 1)
        self.assertEqual(result["venue"], "Stadium A")
        self.assertEqual(result["referee"], "John Doe")

    async def test_handle_missing_features_with_historical_average(self):
        """测试使用历史平均值填充缺失特征"""
        # 创建包含缺失值的DataFrame
        features_df = pd.DataFrame(
            {
                "avg_possession": [50.0, None, 60.0],
                "avg_shots_per_game": [12.0, 15.0, None],
                "avg_goals_per_game": [1.5, None, 2.0],
            }
        )

        with patch.object(
            self.handler, "_get_historical_average", side_effect=[50.0, 12.5, 1.5]
        ):
            result = await self.handler.handle_missing_features(123, features_df)

        # 检查缺失值是否被填充
        self.assertFalse(result.isnull().any().any())
        self.assertEqual(result.iloc[1]["avg_possession"], 50.0)
        self.assertEqual(result.iloc[2]["avg_shots_per_game"], 12.5)
        self.assertEqual(result.iloc[1]["avg_goals_per_game"], 1.5)

    async def test_get_historical_average_known_features(self):
        """测试获取已知特征的历史平均值"""
        avg_possession = await self.handler._get_historical_average("avg_possession")
        self.assertEqual(avg_possession, 50.0)

        avg_shots = await self.handler._get_historical_average("avg_shots_per_game")
        self.assertEqual(avg_shots, 12.5)

        unknown_feature = await self.handler._get_historical_average("unknown_feature")
        self.assertEqual(unknown_feature, 0.0)

    def test_interpolate_time_series_data(self):
        """测试时间序列数据插值"""
        # 创建包含缺失值的时间序列
        data = pd.Series([1.0, None, 3.0, None, 5.0])

        result = self.handler.interpolate_time_series_data(data)

        # 检查插值结果
        self.assertEqual(result.iloc[1], 2.0)  # 1和3的中间值
        self.assertEqual(result.iloc[3], 4.0)  # 3和5的中间值

    def test_remove_rows_with_missing_critical_data(self):
        """测试删除包含关键缺失数据的行"""
        df = pd.DataFrame(
            {
                "critical_col1": [1, None, 3, 4],
                "critical_col2": [1, 2, None, 4],
                "other_col": [1, 2, 3, None],
            }
        )

        critical_columns = ["critical_col1", "critical_col2"]
        result = self.handler.remove_rows_with_missing_critical_data(
            df, critical_columns
        )

        # 应该保留第1行（索引0）和第4行（索引3），因为它们在关键列中没有缺失值
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["critical_col1"], 1)
        self.assertEqual(result.iloc[0]["critical_col2"], 1)
        self.assertEqual(result.iloc[1]["critical_col1"], 4)
        self.assertEqual(result.iloc[1]["critical_col2"], 4)


if __name__ == "__main__":
    unittest.main()
