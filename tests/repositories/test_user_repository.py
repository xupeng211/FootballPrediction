"""
用户仓储测试
User Repository Tests

测试Phase 5+重写的UserRepository功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.repositories.user import UserRepository
from src.services.processing.validators.data_validator import DataValidator


class MockUser:
    """模拟用户模型"""
    def __init__(self, id, username, email="", role="user", is_active=True, **kwargs):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = is_active
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())


class TestUserRepository:
    """UserRepository测试类"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """测试用户仓储实例"""
        with pytest.MonkeyPatch().context() as m:
            # 模拟User模型导入
            m.setattr('src.repositories.user.User', MockUser)
            repo = UserRepository(mock_session)
            return repo

    @pytest.mark.asyncio
    async def test_repository_initialization(self, repository, mock_session):
        """测试仓储初始化"""
        assert repository.session == mock_session
        assert repository.model_class == MockUser

    @pytest.mark.asyncio
    async def test_get_by_id_existing(self, repository, mock_session):
        """测试根据ID获取用户 - 存在"""
        user = MockUser(1, "testuser", "test@example.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result == user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_existing(self, repository, mock_session):
        """测试根据ID获取用户 - 不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_no_filters(self, repository, mock_session):
        """测试获取所有用户 - 无过滤条件"""
        users = [MockUser(1, "user1"), MockUser(2, "user2")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = users
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].username == "user1"
        assert result[1].username == "user2"

    @pytest.mark.asyncio
    async def test_create_user(self, repository, mock_session):
        """测试创建用户"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "role": "user"
        }

        # 模拟数据库操作
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.create(user_data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_defaults(self, repository, mock_session):
        """测试创建用户 - 使用默认值"""
        user_data = {
            "username": "newuser"
        }

        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.create(user_data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user(self, repository, mock_session):
        """测试更新用户"""
        update_data = {
            "email": "updated@example.com",
            "role": "admin"
        }

        # 模拟get_by_id和数据库操作
        existing_user = MockUser(1, "testuser", "old@example.com")

        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'get_by_id', AsyncMock(return_value=existing_user))
            m.setattr(mock_session, 'execute', AsyncMock())
            m.setattr(mock_session, 'commit', AsyncMock())

            result = await repository.update(1, update_data)

            # 验证更新数据包含时间戳
            assert "updated_at" in update_data

    @pytest.mark.asyncio
    async def test_update_user_not_existing(self, repository, mock_session):
        """测试更新用户 - 用户不存在"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'get_by_id', AsyncMock(return_value=None))

            result = await repository.update(999, {"email": "test"})

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_existing(self, repository, mock_session):
        """测试删除用户 - 用户存在"""
        user = MockUser(1, "testuser")

        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'get_by_id', AsyncMock(return_value=user))
            m.setattr(mock_session, 'delete', AsyncMock())
            m.setattr(mock_session, 'commit', AsyncMock())

            result = await repository.delete(1)

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_not_existing(self, repository, mock_session):
        """测试删除用户 - 用户不存在"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'get_by_id', AsyncMock(return_value=None))

            result = await repository.delete(999)

            assert result is False

    @pytest.mark.asyncio
    async def test_find_by_username_existing(self, repository, mock_session):
        """测试根据用户名查找用户 - 存在"""
        user = MockUser(1, "testuser", "test@example.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_username("testuser")

        assert result == user

    @pytest.mark.asyncio
    async def test_find_by_username_not_existing(self, repository, mock_session):
        """测试根据用户名查找用户 - 不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_username("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_email_existing(self, repository, mock_session):
        """测试根据邮箱查找用户 - 存在"""
        user = MockUser(1, "testuser", "test@example.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_email("test@example.com")

        assert result == user

    @pytest.mark.asyncio
    async def test_find_by_email_not_existing(self, repository, mock_session):
        """测试根据邮箱查找用户 - 不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_email("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_active_users(self, repository, mock_session):
        """测试查找活跃用户"""
        active_users = [
            MockUser(1, "user1", is_active=True),
            MockUser(2, "user2", is_active=True)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = active_users
        mock_session.execute.return_value = mock_result

        result = await repository.find_active_users()

        assert len(result) == 2
        assert all(user.is_active for user in result)

    @pytest.mark.asyncio
    async def test_find_active_users_with_limit(self, repository, mock_session):
        """测试查找活跃用户 - 带限制"""
        active_users = [MockUser(1, "user1", is_active=True)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = active_users
        mock_session.execute.return_value = mock_result

        result = await repository.find_active_users(limit=1)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_active_users(self, repository, mock_session):
        """测试统计活跃用户数量"""
        active_users = [MockUser(1, "user1"), MockUser(2, "user2")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = active_users
        mock_session.execute.return_value = mock_result

        result = await repository.count_active_users()

        assert result == 2

    @pytest.mark.asyncio
    async def test_bulk_create_users(self, repository, mock_session):
        """测试批量创建用户"""
        users_data = [
            {"username": "user1", "email": "user1@example.com"},
            {"username": "user2", "email": "user2@example.com"}
        ]

        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.bulk_create(users_data)

        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_change_password(self, repository, mock_session):
        """测试修改密码"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'update', AsyncMock(return_value=True))

            result = await repository.change_password(1, "newpassword123")

            repository.update.assert_called_once()
            assert "password_hash" in repository.update.call_args[0][1]

    @pytest.mark.asyncio
    async def test_change_password_user_not_existing(self, repository, mock_session):
        """测试修改密码 - 用户不存在"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'update', AsyncMock(return_value=None))

            result = await repository.change_password(999, "newpassword123")

            assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_user(self, repository, mock_session):
        """测试停用用户"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'update', AsyncMock(return_value=True))

            result = await repository.deactivate_user(1)

            repository.update.assert_called_once()
            assert repository.update.call_args[0][1]["is_active"] is False

    @pytest.mark.asyncio
    async def test_activate_user(self, repository, mock_session):
        """测试激活用户"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'update', AsyncMock(return_value=True))

            result = await repository.activate_user(1)

            repository.update.assert_called_once()
            assert repository.update.call_args[0][1]["is_active"] is True

    @pytest.mark.asyncio
    async def test_update_last_login(self, repository, mock_session):
        """测试更新最后登录时间"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repository, 'update', AsyncMock(return_value=True))

            result = await repository.update_last_login(1)

            repository.update.assert_called_once()
            assert "last_login_at" in repository.update.call_args[0][1]

    @pytest.mark.asyncio
    async def test_search_users(self, repository, mock_session):
        """测试搜索用户"""
        search_results = [
            MockUser(1, "testuser", "test@example.com"),
            MockUser(2, "usertest", "user@example.com")
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = search_results
        mock_session.execute.return_value = mock_result

        result = await repository.search_users("test", limit=50)

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_users_with_limit(self, repository, mock_session):
        """测试搜索用户 - 带限制"""
        search_results = [MockUser(1, "testuser", "test@example.com")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = search_results
        mock_session.execute.return_value = mock_result

        result = await repository.search_users("test", limit=10)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_users_by_role(self, repository, mock_session):
        """测试根据角色获取用户"""
        admin_users = [MockUser(1, "admin", role="admin"), MockUser(2, "admin2", role="admin")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = admin_users
        mock_session.execute.return_value = mock_result

        result = await repository.get_users_by_role("admin")

        assert len(result) == 2
        assert all(user.role == "admin" for user in result)

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        """测试检查用户是否存在 - 存在"""
        user = MockUser(1, "testuser")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        result = await repository.exists(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """测试检查用户是否存在 - 不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.exists(999)

        assert result is False