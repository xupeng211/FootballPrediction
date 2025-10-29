# TODO: Consider creating a fixture for 23 repeated Mock creations

# TODO: Consider creating a fixture for 23 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, patch

"""
仓储模式单元测试
"""


import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.match import Match
from src.database.repositories.base import BaseRepository
from src.database.repositories.match import MatchRepository
from src.database.repositories.prediction import PredictionRepository
from src.database.repositories.user import UserRepository


@pytest.mark.unit
class TestBaseRepository:
    """基础仓储测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def base_repo(self, mock_db):
        """创建基础仓储实例"""
        return BaseRepository(Match, mock_db)

    def test_base_repository_init(self, base_repo, mock_db):
        """测试基础仓储初始化"""
        assert base_repo.model == Match
        assert base_repo.db_manager == mock_db

    @pytest.mark.asyncio
    async def test_create(self, base_repo):
        """测试创建记录"""
        mock_obj = MagicMock()
        mock_obj.id = 1

        with patch.object(base_repo.db_manager, "add", return_value=None):
            with patch.object(base_repo.db_manager, "commit", return_value=None):
                with patch.object(base_repo.db_manager, "refresh", return_value=None):
                    _result = await base_repo.create(mock_obj)
                    assert _result == mock_obj

    @pytest.mark.asyncio
    async def test_get_by_id(self, base_repo):
        """测试根据ID获取记录"""
        mock_obj = MagicMock()
        mock_obj.id = 1

        with patch.object(base_repo, "find_one", return_value=mock_obj):
            _result = await base_repo.get_by_id(1)
            assert _result == mock_obj

    @pytest.mark.asyncio
    async def test_update(self, base_repo):
        """测试更新记录"""
        mock_obj = MagicMock()
        mock_obj.id = 1

        with patch.object(base_repo.db_manager, "merge", return_value=mock_obj):
            with patch.object(base_repo.db_manager, "commit", return_value=None):
                _result = await base_repo.update(mock_obj)
                assert _result == mock_obj

    @pytest.mark.asyncio
    async def test_delete(self, base_repo):
        """测试删除记录"""
        mock_obj = MagicMock()

        with patch.object(base_repo.db_manager, "delete", return_value=None):
            with patch.object(base_repo.db_manager, "commit", return_value=None):
                await base_repo.delete(mock_obj)
                base_repo.db_manager.delete.assert_called_once_with(mock_obj)


class TestMatchRepository:
    """比赛仓储测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def match_repo(self, mock_db):
        """创建比赛仓储实例"""
        return MatchRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_upcoming_matches(self, match_repo):
        """测试获取即将到来的比赛"""
        mock_matches = [MagicMock(), MagicMock()]
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = mock_matches

        with patch("sqlalchemy.select"):
            with patch.object(match_repo.db_manager, "execute", return_value=mock_execute):
                _result = await match_repo.get_upcoming_matches(days=7)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_matches_by_team(self, match_repo):
        """测试根据球队获取比赛"""
        mock_matches = [MagicMock()]
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = mock_matches

        with patch("sqlalchemy.select"):
            with patch.object(match_repo.db_manager, "execute", return_value=mock_execute):
                _result = await match_repo.get_matches_by_team(team_id=1, limit=10)
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_live_matches(self, match_repo):
        """测试获取正在进行的比赛"""
        mock_matches = [MagicMock(), MagicMock(), MagicMock()]
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = mock_matches

        with patch("sqlalchemy.select"):
            with patch.object(match_repo.db_manager, "execute", return_value=mock_execute):
                _result = await match_repo.get_live_matches()
                assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_match_statistics(self, match_repo):
        """测试获取比赛统计"""
        mock_execute = MagicMock()
        mock_execute.return_value.first.return_value = (100, 50, 20)

        with patch("sqlalchemy.select"):
            with patch.object(match_repo.db_manager, "execute", return_value=mock_execute):
                _result = await match_repo.get_match_statistics()
                assert _result["total_matches"] == 100
                assert _result["completed_matches"] == 50
                assert _result["upcoming_matches"] == 20


class TestUserRepository:
    """用户仓储测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def user_repo(self, mock_db):
        """创建用户仓储实例"""
        return UserRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_repo):
        """测试根据用户名获取用户"""
        mock_user = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.first.return_value = mock_user

        with patch("sqlalchemy.select"):
            with patch.object(user_repo.db_manager, "execute", return_value=mock_execute):
                _result = await user_repo.get_user_by_username("testuser")
                assert _result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_repo):
        """测试根据邮箱获取用户"""
        mock_user = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.first.return_value = mock_user

        with patch("sqlalchemy.select"):
            with patch.object(user_repo.db_manager, "execute", return_value=mock_execute):
                _result = await user_repo.get_user_by_email("test@example.com")
                assert _result == mock_user


class TestPredictionRepository:
    """预测仓储测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def prediction_repo(self, mock_db):
        """创建预测仓储实例"""
        return PredictionRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_user_predictions(self, prediction_repo):
        """测试获取用户预测"""
        mock_predictions = [MagicMock(), MagicMock()]

        with patch.object(prediction_repo, "find", return_value=mock_predictions):
            _result = await prediction_repo.get_user_predictions(user_id=1, limit=10)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_match_predictions(self, prediction_repo):
        """测试获取比赛预测"""
        mock_predictions = [MagicMock()]

        with patch.object(prediction_repo, "find", return_value=mock_predictions):
            _result = await prediction_repo.get_match_predictions(match_id=123)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_prediction_accuracy(self, prediction_repo):
        """测试获取预测准确率"""
        with patch.object(prediction_repo, "count", side_effect=[100, 65]):
            _result = await prediction_repo.get_prediction_accuracy(user_id=1, days=30)
            assert _result == 65.0

    @pytest.mark.asyncio
    async def test_get_pending_predictions(self, prediction_repo):
        """测试获取待结算预测"""
        mock_predictions = [MagicMock(), MagicMock(), MagicMock()]

        with patch.object(prediction_repo, "find", return_value=mock_predictions):
            _result = await prediction_repo.get_pending_predictions(user_id=1)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_batch_update_predictions(self, prediction_repo):
        """测试批量更新预测"""
        mock_predictions = [MagicMock(id=1), MagicMock(id=2)]

        with patch.object(prediction_repo.db_manager, "commit", return_value=None):
            _result = await prediction_repo.batch_update_predictions(mock_predictions)
            assert _result == 2
