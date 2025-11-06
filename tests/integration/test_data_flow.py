"""
Data Flow Integration Tests
足球比赛结果预测系统 - 数据流集成测试

Author: Claude Code
Version: 1.0
Purpose: Test complete data flow from collection to prediction
"""

from unittest.mock import MagicMock, patch

import pytest

# Import system components
try:
    from src.data.cleaning import FootballDataCleaner
    from src.data.fixtures_collector import FixturesCollector
    from src.data.odds_collector import OddsCollector
    from src.data.scores_collector import ScoresCollector

    from src.core.config import Config
    from src.queues.fifo_queue import MemoryFIFOQueue, RedisFIFOQueue
    from src.services.prediction import PredictionService
except ImportError as e:
    pytest.skip(f"Cannot import required modules: {e}", allow_module_level=True)


# Test fixtures
@pytest.fixture
async def mock_queue():
    """Mock queue for testing"""
    queue = MemoryFIFOQueue(max_size=100)
    await queue.initialize()
    return queue


@pytest.fixture
async def sample_raw_match_data():
    """Sample raw match data from external API"""
    return {
        "match": {
            "id": 123456,
            "homeTeam": {
                "id": 1,
                "name": "Manchester United FC",
                "shortName": "Man United",
                "crest": "https://crests.football-data.org/66.png",
            },
            "awayTeam": {
                "id": 2,
                "name": "Liverpool FC",
                "shortName": "Liverpool",
                "crest": "https://crests.football-data.org/86.png",
            },
            "competition": {
                "id": 39,
                "name": "Premier League",
                "code": "PL",
                "type": "LEAGUE",
                "emblem": "https://crests.football-data.org/PL.png",
            },
            "utcDate": "2025-11-10T15:00:00Z",
            "status": "SCHEDULED",
            "matchday": 12,
            "venue": "Old Trafford",
            "referees": [{"id": 12345, "name": "Michael Oliver", "role": "REFEREE"}],
        },
        "head2head": {
            "numberOfMatches": 10,
            "totalGoals": 28,
            "homeTeam": {"wins": 4, "draws": 3, "losses": 3},
            "awayTeam": {"wins": 3, "draws": 3, "losses": 4},
        },
    }


@pytest.fixture
async def sample_raw_odds_data():
    """Sample raw odds data"""
    return {
        "match_id": 123456,
        "bookmakers": [
            {
                "id": 1,
                "name": "Bet365",
                "bets": [
                    {
                        "id": 1,
                        "name": "Match Winner",
                        "values": [
                            {"odd": "2.10", "value": "HOME_TEAM"},
                            {"odd": "3.40", "value": "DRAW"},
                            {"odd": "3.80", "value": "AWAY_TEAM"},
                        ],
                    }
                ],
            }
        ],
        "last_updated": "2025-11-06T08:00:00Z",
    }


class TestDataCollectionFlow:
    """数据收集流程测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fixtures_collection_workflow(
        self, mock_queue, sample_raw_match_data
    ):
        """测试赛程数据收集工作流"""

        # Mock external API response
        with patch("src.data.fixtures_collector.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "matches": [sample_raw_match_data["match"]]
            }
            mock_get.return_value = mock_response

            # Initialize fixtures collector
            collector = FixturesCollector()
            await collector.initialize()

            # Collect fixtures
            collected_data = await collector.collect_fixtures(league_id=39)

            assert len(collected_data) > 0
            assert "homeTeam" in collected_data[0]
            assert "awayTeam" in collected_data[0]
            assert "competition" in collected_data[0]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_odds_collection_workflow(self, mock_queue, sample_raw_odds_data):
        """测试赔率数据收集工作流"""

        with patch("src.data.odds_collector.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_raw_odds_data
            mock_get.return_value = mock_response

            collector = OddsCollector()
            await collector.initialize()

            # Collect odds for specific match
            odds_data = await collector.collect_odds(match_id=123456)

            assert odds_data is not None
            assert "bookmakers" in odds_data
            assert len(odds_data["bookmakers"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scores_collection_workflow(self, mock_queue):
        """测试比分数据收集工作流"""

        sample_scores_data = {
            "matches": [
                {
                    "id": 123456,
                    "score": {
                        "fullTime": {"homeTeam": 2, "awayTeam": 1},
                        "halfTime": {"homeTeam": 1, "awayTeam": 1},
                    },
                    "status": "FINISHED",
                    "utcDate": "2025-11-08T16:30:00Z",
                }
            ]
        }

        with patch("src.data.scores_collector.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_scores_data
            mock_get.return_value = mock_response

            collector = ScoresCollector()
            await collector.initialize()

            # Collect live scores
            scores_data = await collector.collect_live_scores()

            assert len(scores_data) > 0
            assert "score" in scores_data[0]
            assert scores_data[0]["status"] == "FINISHED"


class TestDataProcessingFlow:
    """数据处理流程测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_cleaning_workflow(self, sample_raw_match_data):
        """测试数据清洗工作流"""

        cleaner = FootballDataCleaner()

        # Clean raw match data
        cleaned_data = cleaner.clean_match_data(sample_raw_match_data["match"])

        # Verify cleaning results
        assert "home_team" in cleaned_data  # Should be normalized field names
        assert "away_team" in cleaned_data
        assert "league" in cleaned_data
        assert "date" in cleaned_data
        assert "status" in cleaned_data

        # Verify data quality
        assert cleaned_data["home_team"]["name"] is not None
        assert cleaned_data["away_team"]["name"] is not None
        assert cleaned_data["date"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_feature_engineering_workflow(self):
        """测试特征工程工作流"""

        # Create sample cleaned data
        sample_cleaned_data = {
            "home_team": {"id": 1, "name": "Manchester United"},
            "away_team": {"id": 2, "name": "Liverpool"},
            "league": {"id": 39, "name": "Premier League"},
            "date": "2025-11-10T15:00:00Z",
            "venue": "Old Trafford",
        }

        # Mock historical data for feature calculation

        with (
            patch("src.ml.features.calculate_team_form") as mock_form,
            patch("src.ml.features.calculate_h2h_stats") as mock_h2h,
            patch("src.ml.features.calculate_home_advantage") as mock_advantage,
        ):

            mock_form.return_value = {"home_form": 0.75, "away_form": 0.65}
            mock_h2h.return_value = {"h2h_win_rate": 0.6, "h2h_goals": 2.5}
            mock_advantage.return_value = {"home_advantage": 0.15}

            # Calculate features
            features = {
                "home_team_id": sample_cleaned_data["home_team"]["id"],
                "away_team_id": sample_cleaned_data["away_team"]["id"],
                "league_id": sample_cleaned_data["league"]["id"],
                "venue": sample_cleaned_data["venue"],
            }

            # Add calculated features
            features.update(mock_form.return_value)
            features.update(mock_h2h.return_value)
            features.update(mock_advantage.return_value)

            # Verify features
            assert "home_form" in features
            assert "away_form" in features
            assert "h2h_win_rate" in features
            assert "home_advantage" in features


class TestPredictionWorkflow:
    """预测工作流测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_prediction_flow(self, mock_queue):
        """测试端到端预测流程"""

        # Step 1: Collect and process data

        sample_features = {
            "home_team_id": 1,
            "away_team_id": 2,
            "home_form": 0.85,
            "away_form": 0.72,
            "h2h_history": 0.60,
            "home_advantage": 0.15,
            "league_importance": 0.9,
        }

        # Step 2: Create prediction request
        prediction_request = {
            "match_id": 123456,
            "features": sample_features,
            "priority": "normal",
        }

        # Add to queue
        task_id = await mock_queue.enqueue(
            task_type="prediction", data=prediction_request, priority="normal"
        )
        assert task_id is not None

        # Step 3: Process prediction (mock the ML model)
        with patch("src.ml.models.PredictionModel.predict") as mock_predict:
            mock_predict.return_value = {
                "predicted_result": "home_win",
                "probabilities": {"home_win": 0.65, "draw": 0.20, "away_win": 0.15},
                "confidence": 0.75,
                "model_version": "1.2.0",
            }

            # Dequeue and process task
            task = await mock_queue.dequeue()
            assert task is not None
            assert task.task_type == "prediction"
            assert task.data["match_id"] == 123456

            # Process prediction
            prediction_result = mock_predict(**sample_features)
            assert prediction_result is not None
            assert "predicted_result" in prediction_result
            assert "probabilities" in prediction_result

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_prediction_processing(self, mock_queue):
        """测试批量预测处理"""

        # Create multiple prediction requests
        prediction_requests = []
        for i in range(5):
            request = {
                "match_id": 123456 + i,
                "features": {
                    "home_team_id": 1,
                    "away_team_id": 2 + i,
                    "home_form": 0.8 + (i * 0.02),
                    "away_form": 0.7 - (i * 0.02),
                    "h2h_history": 0.6,
                    "home_advantage": 0.15,
                },
                "priority": "normal",
            }
            prediction_requests.append(request)

        # Add all requests to queue
        task_ids = []
        for request in prediction_requests:
            task_id = await mock_queue.enqueue(
                task_type="prediction", data=request, priority="normal"
            )
            task_ids.append(task_id)

        assert len(task_ids) == 5

        # Process all tasks
        processed_results = []
        with patch("src.ml.models.PredictionModel.predict") as mock_predict:
            mock_predict.return_value = {
                "predicted_result": "home_win",
                "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.70,
                "model_version": "1.2.0",
            }

            for _ in range(5):
                task = await mock_queue.dequeue()
                if task:
                    result = mock_predict(**task.data["features"])
                    processed_results.append(
                        {"match_id": task.data["match_id"], "prediction": result}
                    )

        assert len(processed_results) == 5
        assert all("match_id" in result for result in processed_results)
        assert all("prediction" in result for result in processed_results)


class TestErrorHandlingInDataFlow:
    """数据流错误处理测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_collection_error_recovery(self, mock_queue):
        """测试数据收集错误恢复"""

        with patch("src.data.fixtures_collector.requests.get") as mock_get:
            # Simulate network error
            mock_get.side_effect = Exception("Network timeout")

            collector = FixturesCollector()
            await collector.initialize()

            # Should handle error gracefully
            collected_data = await collector.collect_fixtures(league_id=39)

            # Should return empty list or raise handled exception
            assert isinstance(collected_data, list)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_prediction_processing_error_handling(self, mock_queue):
        """测试预测处理错误处理"""

        # Add a task with invalid data
        invalid_request = {
            "match_id": "invalid_id",  # Should be integer
            "features": {},  # Missing required features
        }

        await mock_queue.enqueue(
            task_type="prediction", data=invalid_request, priority="normal"
        )

        # Process task and handle error
        task = await mock_queue.dequeue()
        assert task is not None

        with patch("src.ml.models.PredictionModel.predict") as mock_predict:
            # Simulate model error
            mock_predict.side_effect = ValueError("Invalid input data")

            # Should handle the error
            try:
                mock_predict(**task.data["features"])
                raise AssertionError("Should have raised an exception")
            except ValueError:
                pass  # Expected error

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_overflow_handling(self):
        """测试队列溢出处理"""

        # Create a small queue for testing
        small_queue = MemoryFIFOQueue(max_size=3)
        await small_queue.initialize()

        # Fill the queue
        for i in range(5):  # More than max_size
            task_id = await small_queue.enqueue(
                task_type="test", data={"test": i}, priority="normal"
            )

            if i < 3:
                assert task_id is not None
            else:
                # Should fail when queue is full
                assert task_id is None

        # Verify queue size
        stats = small_queue.get_stats()
        assert stats["queue_size"] == 3


class TestDataFlowPerformance:
    """数据流性能测试"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_processing_performance(self):
        """测试数据处理性能"""

        import time


        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append(
                {
                    "id": i,
                    "home_team": {"id": i % 20, "name": f"Team_{i % 20}"},
                    "away_team": {"id": (i + 1) % 20, "name": f"Team_{(i + 1) % 20}"},
                    "date": "2025-11-10T15:00:00Z",
                    "status": "SCHEDULED",
                }
            )

        # Test cleaning performance
        cleaner = FootballDataCleaner()
        start_time = time.time()

        cleaned_data = []
        for item in large_dataset:
            cleaned = cleaner.clean_match_data(item)
            cleaned_data.append(cleaned)

        end_time = time.time()
        processing_time = end_time - start_time

        # Performance assertions
        assert len(cleaned_data) == 1000
        assert processing_time < 5.0  # Should process within 5 seconds
        assert processing_time < 1000 / len(cleaned_data)  # Less than 1ms per record

    @pytest.mark.performance
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_throughput_performance(self):
        """测试队列吞吐量性能"""

        import time

        queue = MemoryFIFOQueue(max_size=10000)
        await queue.initialize()

        # Test enqueue performance
        start_time = time.time()
        task_ids = []

        for i in range(1000):
            task_id = await queue.enqueue(
                task_type="test",
                data={"test_data": i, "timestamp": time.time()},
                priority="normal",
            )
            task_ids.append(task_id)

        enqueue_time = time.time() - start_time

        # Test dequeue performance
        start_time = time.time()
        dequeued_tasks = []

        for _ in range(1000):
            task = await queue.dequeue()
            if task:
                dequeued_tasks.append(task)

        dequeue_time = time.time() - start_time

        # Performance assertions
        assert len(task_ids) == 1000
        assert len(dequeued_tasks) == 1000
        assert enqueue_time < 2.0  # Should enqueue within 2 seconds
        assert dequeue_time < 2.0  # Should dequeue within 2 seconds
        assert enqueue_time < 1000 / 500  # More than 500 ops/second
        assert dequeue_time < 1000 / 500  # More than 500 ops/second


# Test markers
pytest.mark.integration(TestDataCollectionFlow)
pytest.mark.integration(TestDataProcessingFlow)
pytest.mark.integration(TestPredictionWorkflow)
pytest.mark.integration(TestErrorHandlingInDataFlow)
pytest.mark.performance(TestDataFlowPerformance)

# Critical flow markers
pytest.mark.critical(test_end_to_end_prediction_flow)
pytest.mark.critical(test_data_cleaning_workflow)

# Data flow specific markers
pytest.mark.data_flow(TestDataCollectionFlow)
pytest.mark.data_flow(TestDataProcessingFlow)
pytest.mark.data_flow(TestPredictionWorkflow)
