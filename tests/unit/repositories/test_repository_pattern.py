# TODO: Consider creating a fixture for 15 repeated Mock creations

# TODO: Consider creating a fixture for 15 repeated Mock creations


"""""""
仓储模式单元测试
Repository Pattern Unit Tests

测试仓储模式的核心功能。
Tests core functionality of the repository pattern.
"""""""

from datetime import date, datetime, timedelta

import pytest

from src.database.models import Match, Prediction, User
    BaseRepository,
    QuerySpec,
    ReadOnlyRepository,
    Repository,
    WriteOnlyRepository,
)
    get_match_repository,
    get_prediction_repository,
    get_read_only_prediction_repository,
    get_user_repository,
)
    MatchRepository,
    MatchRepositoryInterface,
    MatchStatus,
    ReadOnlyMatchRepository,
)
    PredictionRepository,
    PredictionRepositoryInterface,
    ReadOnlyPredictionRepository,
)
    DefaultRepositoryFactory,
    RepositoryFactory,
    RepositoryProvider,
    get_repository_provider,
    set_repository_provider,
)
    ReadOnlyUserRepository,
    UserRepository,
    UserRepositoryInterface,
)


class MockAsyncSession:
    """模拟异步数据库会话"""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.added_objects = []
        self.deleted_objects = []

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        pass

    def add(self, obj):
        self.added_objects.append(obj)

    async def delete(self, obj):
        self.deleted_objects.append(obj)

    async def execute(self, query):
        _result = AsyncMock()
        # 模拟返回结果
        result.scalars.return_value.first.return_value = None
        result.scalars.return_value.all.return_value = []
        result.scalar.return_value = 0
        result.rowcount = 1
        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.unit
class TestQuerySpec:
    """测试QuerySpec"""

    def test_query_spec_creation(self):
        """测试QuerySpec创建"""
        query_spec = QuerySpec(
            filters={"user_id": 1},
            order_by=["-created_at"],
            limit=10,
            offset=0,
            include=["user"],
        )

        assert query_spec.filters == {"user_id": 1}
        assert query_spec.order_by == ["-created_at"]
        assert query_spec.limit == 10
        assert query_spec.offset == 0
        assert query_spec.include == ["user"]

    def test_query_spec_defaults(self):
        """测试QuerySpec默认值"""
        query_spec = QuerySpec()

        assert query_spec.filters is None
        assert query_spec.order_by is None
        assert query_spec.limit is None
        assert query_spec.offset is None
        assert query_spec.include is None


@pytest.mark.asyncio
class TestReadOnlyPredictionRepository:
    """测试只读预测仓储"""

    async def setup_method(self):
        """设置测试方法"""
        self.session = MockAsyncSession()
        self.repo = ReadOnlyPredictionRepository(self.session, Prediction)

    async def test_find_one(self):
        """测试查询单个预测"""
        query_spec = QuerySpec(filters={"id": 1})
        _prediction = await self.repo.find_one(query_spec)

        # 验证查询被执行
        assert prediction is None  # Mock返回None

    async def test_find_many(self):
        """测试查询多个预测"""
        query_spec = QuerySpec(
            filters={"user_id": 1}, order_by=["-created_at"], limit=10
        )
        predictions = await self.repo.find_many(query_spec)

        assert isinstance(predictions, list)

    async def test_get_by_id(self):
        """测试根据ID获取预测"""
        _prediction = await self.repo.get_by_id(1)

        # Mock返回None
        assert prediction is None

    async def test_get_predictions_by_user(self):
        """测试获取用户预测"""
        predictions = await self.repo.get_predictions_by_user(
            user_id=1, start_date=date.today() - timedelta(days=7), limit=50
        )

        assert isinstance(predictions, list)

    async def test_get_user_statistics(self):
        """测试获取用户统计"""
        with patch("src.repositories.prediction.func") as mock_func:
            # 模拟统计数据
            mock_result = AsyncMock()
            mock_result.total_predictions = 100
            mock_result.total_points = 250
            mock_result.avg_confidence = 0.85
            mock_result.successful_predictions = 60

            mock_func.count.return_value.label.return_value = (
                mock_func.count.return_value
            )
            mock_func.sum.return_value.label.return_value = mock_func.sum.return_value
            mock_func.avg.return_value.label.return_value = mock_func.avg.return_value
            mock_func.case.return_value.label.return_value = mock_func.case.return_value

            self.session.execute.return_value = mock_result

            _stats = await self.repo.get_user_statistics(1)

            assert "total_predictions" in stats
            assert "success_rate" in stats
            assert "total_points" in stats

    async def test_save_not_implemented(self):
        """测试只读仓储不允许保存"""
        _prediction = MagicMock()

        with pytest.raises(NotImplementedError):
            await self.repo.save(prediction)

    async def test_delete_not_implemented(self):
        """测试只读仓储不允许删除"""
        _prediction = MagicMock()

        with pytest.raises(NotImplementedError):
            await self.repo.delete(prediction)


@pytest.mark.asyncio
class TestPredictionRepository:
    """测试预测仓储"""

    async def setup_method(self):
        """设置测试方法"""
        self.session = MockAsyncSession()
        self.repo = PredictionRepository(self.session, Prediction)

    async def test_create_prediction(self):
        """测试创建预测"""
        _data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "strategy_used": "test_strategy",
            "notes": "测试预测",
        }

        with patch("src.repositories.prediction.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

            await self.repo.create(data)

            # 验证对象被添加到会话
            assert len(self.session.added_objects) == 1
            assert self.session.committed

    async def test_update_by_id(self):
        """测试更新预测"""
        update_data = {"confidence": 0.90, "notes": "更新后的预测"}

        with patch("src.repositories.prediction.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = (
                mock_update.return_value
            )

            # 模拟找到并更新成功
            with patch.object(self.repo, "get_by_id") as mock_get:
                mock_prediction = MagicMock()
                mock_prediction.id = 1
                mock_get.return_value = mock_prediction

                _result = await self.repo.update_by_id(1, update_data)

                assert _result == mock_prediction
                assert self.session.committed

    async def test_bulk_create(self):
        """测试批量创建预测"""
        entities_data = [
            {
                "match_id": 1,
                "user_id": 1,
                "predicted_home": 2,
                "predicted_away": 1,
                "confidence": 0.85,
            },
            {
                "match_id": 2,
                "user_id": 1,
                "predicted_home": 1,
                "predicted_away": 1,
                "confidence": 0.75,
            },
        ]

        await self.repo.bulk_create(entities_data)

        # 验证所有对象都被添加
        assert len(self.session.added_objects) == 2
        assert self.session.committed

    async def test_delete_by_id(self):
        """测试删除预测"""
        with patch("src.repositories.prediction.delete") as mock_delete:
            mock_delete.return_value.where.return_value = mock_delete.return_value
            self.session.execute.return_value.rowcount = 1

            _result = await self.repo.delete_by_id(1)

            assert _result is True
            assert self.session.committed


@pytest.mark.asyncio
class TestUserRepository:
    """测试用户仓储"""

    async def setup_method(self):
        """设置测试方法"""
        self.session = MockAsyncSession()
        self.repo = UserRepository(self.session, User)

    async def test_create_user(self):
        """测试创建用户"""
        _data = {
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "display_name": "测试用户",
            "role": "user",
        }

        with patch("src.repositories.user.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

            await self.repo.create(data)

            assert len(self.session.added_objects) == 1
            assert self.session.committed

    async def test_get_user_statistics(self):
        """测试获取用户统计"""
        mock_result = AsyncMock()
        mock_result.total_predictions = 50
        mock_result.total_points = 120
        mock_result.avg_confidence = 0.82
        mock_result.last_prediction_at = datetime.utcnow()

        self.session.execute.return_value = mock_result

        # 模拟用户存在
        with patch.object(self.repo, "get_by_id") as mock_get:
            mock_user = MagicMock()
            mock_user.created_at = datetime.utcnow() - timedelta(days=30)
            mock_get.return_value = mock_user

            _stats = await self.repo.get_user_statistics(1)

        assert "total_predictions" in stats
        assert "predictions_per_day" in stats

    async def test_update_last_login(self):
        """测试更新最后登录时间"""
        with patch("src.repositories.user.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = (
                mock_update.return_value
            )
            self.session.execute.return_value.rowcount = 1

            with patch("src.repositories.user.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

                _result = await self.repo.update_last_login(1)

                assert _result is True
                assert self.session.committed

    async def test_deactivate_user(self):
        """测试停用用户"""
        with patch("src.repositories.user.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = (
                mock_update.return_value
            )
            self.session.execute.return_value.rowcount = 1

            _result = await self.repo.deactivate_user(1)

            assert _result is True
            assert self.session.committed


@pytest.mark.asyncio
class TestMatchRepository:
    """测试比赛仓储"""

    async def setup_method(self):
        """设置测试方法"""
        self.session = MockAsyncSession()
        self.repo = MatchRepository(self.session, Match)

    async def test_get_upcoming_matches(self):
        """测试获取即将到来的比赛"""
        _matches = await self.repo.get_upcoming_matches(days=7, limit=10)

        assert isinstance(matches, list)

    async def test_get_live_matches(self):
        """测试获取正在进行的比赛"""
        _matches = await self.repo.get_live_matches()

        assert isinstance(matches, list)

    async def test_get_matches_by_team(self):
        """测试获取指定队伍的比赛"""
        _matches = await self.repo.get_matches_by_team(team_id=1, limit=20)

        assert isinstance(matches, list)

    async def test_start_match(self):
        """测试开始比赛"""
        with patch("src.repositories.match.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = (
                mock_update.return_value
            )

            with patch.object(self.repo, "get_by_id") as mock_get:
                mock_match = MagicMock()
                mock_match.id = 1
                mock_get.return_value = mock_match

                with patch("src.repositories.match.datetime") as mock_datetime:
                    mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

                    _result = await self.repo.start_match(1)

                    assert _result == mock_match
                    assert self.session.committed

    async def test_finish_match(self):
        """测试结束比赛"""
        with patch("src.repositories.match.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = (
                mock_update.return_value
            )

            with patch.object(self.repo, "get_by_id") as mock_get:
                mock_match = MagicMock()
                mock_match.id = 1
                mock_get.return_value = mock_match

                with patch("src.repositories.match.datetime") as mock_datetime:
                    mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

                    _result = await self.repo.finish_match(1, 2, 1)

                    assert _result == mock_match
                    assert self.session.committed

    async def test_get_match_statistics(self):
        """测试获取比赛统计"""
        with patch.object(self.repo, "get_by_id") as mock_get:
            mock_match = MagicMock()
            mock_match.id = 1
            mock_match.home_team_name = "Team A"
            mock_match.away_team_name = "Team B"
            mock_match.competition_name = "Premier League"
            mock_match.status = MatchStatus.FINISHED.value
            mock_match.home_score = 2
            mock_match.away_score = 1
            mock_get.return_value = mock_match

            mock_result = AsyncMock()
        mock_result.total_predictions = 100
        mock_result.avg_confidence = 0.85
        mock_result.home_win_predictions = 60
        mock_result.away_win_predictions = 20
        mock_result.draw_predictions = 20

        self.session.execute.return_value = mock_result

        _stats = await self.repo.get_match_statistics(1)

        assert "match_info" in stats
        assert "predictions" in stats
        assert "actual_result" in stats
        assert stats["actual_result"] == "home_win"


class TestRepositoryFactory:
    """测试仓储工厂"""

    def test_default_factory_creates_prediction_repository(self):
        """测试默认工厂创建预测仓储"""
        session = MockAsyncSession()
        factory = DefaultRepositoryFactory()

        # 创建读写仓储
        repo = factory.create_prediction_repository(session, read_only=False)
        assert isinstance(repo, PredictionRepository)

        # 创建只读仓储
        read_only_repo = factory.create_prediction_repository(session, read_only=True)
        assert isinstance(read_only_repo, ReadOnlyPredictionRepository)

    def test_default_factory_creates_user_repository(self):
        """测试默认工厂创建用户仓储"""
        session = MockAsyncSession()
        factory = DefaultRepositoryFactory()

        repo = factory.create_user_repository(session, read_only=False)
        assert isinstance(repo, UserRepository)

        read_only_repo = factory.create_user_repository(session, read_only=True)
        assert isinstance(read_only_repo, ReadOnlyUserRepository)

    def test_default_factory_creates_match_repository(self):
        """测试默认工厂创建比赛仓储"""
        session = MockAsyncSession()
        factory = DefaultRepositoryFactory()

        repo = factory.create_match_repository(session, read_only=False)
        assert isinstance(repo, MatchRepository)

        read_only_repo = factory.create_match_repository(session, read_only=True)
        assert isinstance(read_only_repo, ReadOnlyMatchRepository)


class TestRepositoryProvider:
    """测试仓储提供者"""

    def setup_method(self):
        """设置测试方法"""
        self.provider = RepositoryProvider()

    def test_get_prediction_repository_caching(self):
        """测试预测仓储缓存"""
        session = MockAsyncSession()

        # 第一次获取
        repo1 = self.provider.get_prediction_repository(session)

        # 第二次获取相同会话应该返回缓存
        repo2 = self.provider.get_prediction_repository(session)

        assert repo1 is repo2

    def test_get_read_only_repository_different_instance(self):
        """测试只读仓储是不同实例"""
        session = MockAsyncSession()

        # 获取读写仓储
        read_write_repo = self.provider.get_prediction_repository(
            session, read_only=False
        )

        # 获取只读仓储
        read_only_repo = self.provider.get_prediction_repository(
            session, read_only=True
        )

        # 应该是不同的实例
        assert read_write_repo is not read_only_repo
        assert isinstance(read_only_repo, ReadOnlyPredictionRepository)

    def test_clear_cache(self):
        """测试清除缓存"""
        session = MockAsyncSession()

        # 获取仓储
        repo1 = self.provider.get_prediction_repository(session)

        # 清除缓存
        self.provider.clear_cache()

        # 再次获取应该是新实例
        repo2 = self.provider.get_prediction_repository(session)

        assert repo1 is not repo2

    def test_set_factory(self):
        """测试设置工厂"""
        custom_factory = MagicMock()
        self.provider.set_factory(custom_factory)

        session = MockAsyncSession()

        # 获取仓储应该使用新工厂
        self.provider.get_prediction_repository(session)

        # 验证工厂方法被调用
        custom_factory.create_prediction_repository.assert_called_once_with(
            session, False
        )


class TestGlobalRepositoryProvider:
    """测试全局仓储提供者"""

    def test_get_and_set_global_provider(self):
        """测试获取和设置全局提供者"""
        custom_provider = RepositoryProvider()

        # 设置全局提供者
        set_repository_provider(custom_provider)

        # 获取全局提供者应该是相同的
        retrieved = get_repository_provider()
        assert retrieved is custom_provider


@pytest.mark.asyncio
class TestRepositoryDependencyInjection:
    """测试仓储依赖注入"""

    async def test_get_prediction_repository_dep(self):
        """测试获取预测仓储依赖"""
        with patch("src.repositories.di.get_async_session") as mock_get_session:
            session = MockAsyncSession()
            mock_get_session.return_value = session

            repo = await get_prediction_repository()

            assert isinstance(repo, PredictionRepository)

    async def test_get_read_only_repository_dep(self):
        """测试获取只读预测仓储依赖"""
        with patch("src.repositories.di.get_async_session") as mock_get_session:
            session = MockAsyncSession()
            mock_get_session.return_value = session

            repo = await get_read_only_prediction_repository()

            assert isinstance(repo, ReadOnlyPredictionRepository)


@pytest.mark.asyncio
class TestRepositoryIntegration:
    """仓储集成测试"""

    async def test_full_prediction_workflow(self):
        """测试完整的预测工作流"""
        session = MockAsyncSession()
        repo = PredictionRepository(session, Prediction)

        # 1. 创建预测
        _data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        with patch("src.repositories.prediction.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

            await repo.create(data)
        assert len(session.added_objects) == 1

        # 2. 查询预测
        with patch.object(repo, "get_by_id") as mock_get:
            mock_prediction = MagicMock()
            mock_prediction.id = 1
            mock_get.return_value = mock_prediction

            found = await repo.get_by_id(1)
            assert found == mock_prediction

        # 3. 更新预测
        update_data = {"confidence": 0.90}
        with patch("src.repositories.prediction.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = (
                mock_update.return_value
            )

            with patch.object(repo, "get_by_id") as mock_get:
                mock_prediction.updated_at = datetime.utcnow()
                mock_get.return_value = mock_prediction

                updated = await repo.update_by_id(1, update_data)
                assert updated.updated_at is not None

    async def test_read_only_repository_restriction(self):
        """测试只读仓储限制"""
        session = MockAsyncSession()
        repo = ReadOnlyPredictionRepository(session, Prediction)

        # 尝试写入操作应该抛出异常
        with pytest.raises(NotImplementedError):
            await repo.save(MagicMock())

        with pytest.raises(NotImplementedError):
            await repo.delete(MagicMock())

        # 读取操作应该正常
        _prediction = await repo.get_by_id(1)
        assert prediction is None  # Mock返回None
