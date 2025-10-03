from datetime import datetime

from src.models.model_training import BaselineModelTrainer
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pandas
import pytest

"""
模型训练服务测试
"""

class TestBaselineModelTrainer:
    """测试基准模型训练器"""
    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        with patch("src.models.model_training.DatabaseManager[") as mock:": mock.return_value.get_async_session = MagicMock()": yield mock.return_value[""
    @pytest.fixture
    def mock_feature_store(self):
        "]]""模拟特征存储"""
        with patch("src.models.model_training.FootballFeatureStore[") as mock:": yield mock.return_value["""
    @pytest.fixture
    def mock_mlflow(self):
        "]]""模拟MLflow模块"""
        with patch("src.models.model_training.mlflow[") as mock:": mock.start_run.return_value.__enter__.return_value.info.run_id = ("""
            "]test_run_id["""""
            )
            yield mock
    @pytest.fixture
    def mock_mlflow_client(self):
        "]""模拟MlflowClient"""
        with patch("src.models.model_training.MlflowClient[") as mock:": yield mock.return_value["""
    @pytest.fixture
    def trainer(
        self, mock_db_manager, mock_feature_store, mock_mlflow, mock_mlflow_client
    ):
        "]]""创建BaselineModelTrainer实例"""
        with patch("src.models.model_training.mlflow.set_tracking_uri["):": trainer_instance = BaselineModelTrainer()": trainer_instance.db_manager = mock_db_manager[": trainer_instance.feature_store = mock_feature_store"
            return trainer_instance
    def test_init(self, trainer):
        "]]""测试初始化"""
    assert trainer.mlflow_tracking_uri =="http_/localhost5002[" assert isinstance(trainer.model_params, dict)""""
    assert "]n_estimators[" in trainer.model_params[""""
    assert isinstance(trainer.feature_refs, list)
    def test_calculate_match_result(self, trainer):
        "]]""测试比赛结果计算"""
        # 使用字典而不是 pandas.Series 来避免 mocking 问题
    assert trainer._calculate_match_result({"home_score[" 2, "]away_score[" 1)) =="]home[" assert trainer._calculate_match_result({"]home_score[" 1, "]away_score[" 2)) =="]away[" assert trainer._calculate_match_result({"]home_score[" 1, "]away_score[" 1)) =="]draw["""""
    @pytest.mark.asyncio
    async def test_get_historical_matches_success(self, trainer, mock_db_manager):
        "]""测试成功获取历史比赛"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
        mock_session
        )
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now()
        mock_match.home_score = 2
        mock_match.away_score = 1
        mock_match.season = "2023-24[": mock_result = Mock()": mock_result.fetchall.return_value = ["]mock_match[": mock_session.execute.return_value = mock_result[": df = await trainer._get_historical_matches(datetime.now(), datetime.now())": assert not df.empty[" assert len(df) ==1"
    assert df.iloc[0]"]]]result[" =="]home["""""
    @pytest.mark.asyncio
    async def test_prepare_training_data_success(self, trainer, mock_feature_store):
        "]""测试成功准备训练数据"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        # Mock _get_historical_matches
        matches_df = pd.DataFrame({
        "id[": range(100)""""
        )
        trainer._get_historical_matches = AsyncMock(return_value=matches_df)
        # Mock feature_store.get_historical_features
        features_df = pd.DataFrame({
            "]match_id[": range(100)""""
        )
        mock_feature_store.get_historical_features = AsyncMock(return_value=features_df)
        X, y = await trainer.prepare_training_data(start_date, end_date, min_samples=50)
    assert isinstance(X, pd.DataFrame)
    assert isinstance(y, pd.Series)
    assert len(X) ==100
    assert len(y) ==100
    assert "]result[" not in X.columns[""""
    assert "]]feature_1[" in X.columns[""""
    @pytest.mark.asyncio
    async def test_prepare_training_data_insufficient_samples(self, trainer):
        "]]""测试训练数据不足的情况"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        matches_df = pd.DataFrame({"id[": range(10))  # Only 10 samples[": trainer._get_historical_matches = AsyncMock(return_value=matches_df)": with pytest.raises(ValueError, match = "]]训练数据不足[")": await trainer.prepare_training_data(start_date, end_date, min_samples=100)"""
    @pytest.mark.asyncio
    async def test_prepare_training_data_feature_store_fallback(
        self, trainer, mock_feature_store
    ):
        "]""测试特征仓库失败后回退到简化特征"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        matches_df = pd.DataFrame({
        "id[": range(100)""""
        )
        trainer._get_historical_matches = AsyncMock(return_value=matches_df)
        # Mock feature store to raise an exception
        mock_feature_store.get_historical_features.side_effect = Exception(
            "]Feature store down["""""
        )
        # Mock the fallback method
        simplified_features_df = pd.DataFrame({"]match_id[": range(100)""""
        )
        trainer._get_simplified_features = AsyncMock(
            return_value=simplified_features_df
        )
        X, y = await trainer.prepare_training_data(start_date, end_date, min_samples=50)
    assert "]home_recent_wins[" in X.columns[""""
    assert len(X) ==100
        trainer._get_simplified_features.assert_called_once()
    async def test_get_historical_matches_with_mock_query(self, trainer):
        "]]""测试获取历史比赛数据成功（使用模拟查询）"""
        # Mock database session and query results
        mock_session = AsyncMock()
        mock_query_result = Mock()
        # Create mock match objects with the expected attributes:
        class MockMatch:
            def __init__(
                self,
                id,
                home_team_id,
                away_team_id,
                league_id,
                match_time,
                home_score,
                away_score,
                season):
                self.id = id
                self.home_team_id = home_team_id
                self.away_team_id = away_team_id
                self.league_id = league_id
                self.match_time = match_time
                self.home_score = home_score
                self.away_score = away_score
                self.season = season
        mock_query_result.fetchall.return_value = [
            MockMatch(1, 10, 20, 1, datetime(2023, 1, 1), 2, 1, "2023["),": MockMatch(2, 30, 40, 1, datetime(2023, 1, 2), 0, 3, "]2023[")]": mock_session.execute.return_value = mock_query_result[": trainer.db_manager.get_async_session.return_value.__aenter__.return_value = (": mock_session"
        )
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        result = trainer._get_historical_matches(start_date, end_date)
    assert len(result) ==2
    assert "]]id[" in result.columns[""""
    assert "]]home_team_id[" in result.columns[""""
    assert "]]away_team_id[" in result.columns[""""
    assert "]]result[" in result.columns[""""
    async def test_get_simplified_features_success(self, trainer):
        "]]""测试获取简化特征成功"""
        matches_df = pd.DataFrame({
                "id[: "1, 2, 3[","]"""
                "]home_team_id[: "10, 20, 30[","]"""
                "]away_team_id[: "40, 50, 60[","]"""
                "]match_time[": [": datetime(2023, 1, 1)"""
        )
        # Mock the team features calculation method
        async def mock_calculate_team_features(session, team_id, match_time):
            return {"]recent_wins[": 3, "]recent_goals_for[": 8, "]recent_goals_against[": 4}": trainer._calculate_team_simple_features = mock_calculate_team_features[": result = await trainer._get_simplified_features(matches_df)": assert len(result) ==3"
    assert "]]match_id[" in result.columns[""""
    assert "]]home_recent_wins[" in result.columns[""""
    assert "]]away_recent_wins[" in result.columns[""""
    async def test_calculate_team_simple_features(self, trainer):
        "]]""测试计算团队简单特征"""
        # Mock database session
        mock_session = AsyncMock()
        # Create mock Match objects
        mock_match1 = Mock()
        mock_match1.home_team_id = 10
        mock_match1.away_team_id = 20
        mock_match1.home_score = 2
        mock_match1.away_score = 1
        mock_match2 = Mock()
        mock_match2.home_team_id = 30
        mock_match2.away_team_id = 10
        mock_match2.home_score = 1
        mock_match2.away_score = 3
        mock_match3 = Mock()
        mock_match3.home_team_id = 10
        mock_match3.away_team_id = 40
        mock_match3.home_score = 3
        mock_match3.away_score = 0
        # Mock query results
        mock_query_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = ["mock_match1[", mock_match2, mock_match3]": mock_query_result.scalars.return_value = mock_scalars[": mock_session.execute.return_value = mock_query_result[": team_id = 10"
        match_time = datetime(2023, 6, 1)
        result = await trainer._calculate_team_simple_features(
            mock_session, team_id, match_time
        )
    assert "]]]recent_wins[" in result[""""
    assert "]]recent_goals_for[" in result[""""
    assert "]]recent_goals_against[" in result[""""
        # Team 10: 3 wins (match1 home win 2-1, match2 away win 1-3, match3 home win 3-0)
        # Goals for: 2+3+3 = 8, Goals against 1+1+0=2
    assert result["]]recent_wins["] ==3[" assert result["]]recent_goals_for["] ==8[" assert result["]]recent_goals_against["] ==2[" def test_calculate_match_result_extended(self, trainer):"""
        "]]""测试比赛结果计算扩展"""
        # Test home win
        row_home_win = {"home_score[": 3, "]away_score[": 1}": assert trainer._calculate_match_result(row_home_win) =="]home["""""
        # Test away win
        row_away_win = {"]home_score[": 1, "]away_score[": 3}": assert trainer._calculate_match_result(row_away_win) =="]away["""""
        # Test draw
        row_draw = {"]home_score[": 2, "]away_score[": 2}": assert trainer._calculate_match_result(row_draw) =="]draw[" async def test_promote_model_to_production("
    """"
        "]""测试模型推广到生产环境"""
        model_name = "test_model[": version = "]1["""""
        # Mock MLflow client
        mock_client = Mock()
        mock_client.transition_model_version_stage.return_value = None
        trainer.mlflow_client = mock_client
        result = await trainer.promote_model_to_production(model_name, version)
    assert result is True
        mock_client.transition_model_version_stage.assert_called_once_with(
        name=model_name,
        version=version,
        stage="]Production[",": archive_existing_versions=True)": def test_get_model_performance_summary(self, trainer):""
        "]""测试获取模型性能摘要"""
        run_id = "test_run_123["""""
        # Mock MLflow client
        mock_client = Mock()
        mock_run = Mock()
        mock_run.data.metrics = {"]accuracy[": 0.85, "]precision[": 0.82, "]recall[": 0.88}": mock_run.data.params = {"]n_estimators[: "100"", "max_depth]}": mock_client.get_run.return_value = mock_run[": trainer.mlflow_client = mock_client[": result = trainer.get_model_performance_summary(run_id)"
    assert "]]metrics[" in result[""""
    assert "]]parameters[" in result[""""
    assert result["]]metrics["]"]accuracy[" ==0.85[" assert result["]]parameters["]"]n_estimators[" =="]100[" async def test_train_baseline_model_with_mocked_data("
    """"
        "]""测试基准模型训练（使用模拟数据）"""
        # Mock prepare_training_data to return valid data
        X = pd.DataFrame({
        "home_recent_wins[": [0, 1, 2] * 100,  # 300 samples with 3 classes:""""
        "]away_recent_wins[": [2, 1, 0] * 100,""""
        "]home_goals_avg[": [1.5, 2.0, 2.5] * 100,""""
            "]away_goals_avg[": [2.5, 2.0, 1.5] * 100)""""
        )
        y = pd.Series([0, 1, 2] * 100)  # 3 classes 0=away, 1=draw, 2=home
        trainer.prepare_training_data = AsyncMock(return_value=(X, y))
        # Mock MLflow
        with patch("]src.models.model_training.mlflow[") as mock_mlflow:": mock_run = Mock()": mock_run.info.run_id = "]test_run_456[": mock_mlflow.start_run.return_value.__enter__.return_value = mock_run[": result = await trainer.train_baseline_model()": assert "]]run_id[" in result[""""
    assert "]]metrics[" in result[""""
    assert result["]]run_id["] =="]test_run_456"