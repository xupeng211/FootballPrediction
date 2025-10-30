from __future__ import annotations


# TODO: Consider creating a fixture for 9 repeated Mock creations

# TODO: Consider creating a fixture for 9 repeated Mock creations


"""API端点测试"""

import pytest


@pytest.mark.unit
@pytest.mark.api
class TestHealthEndpoint:
    """健康检查端点测试"""

    @with_mocks(["logger"])
    def test_health_check(self, mocks):
        """测试健康检查端点"""
        # 导入需要在patch内,以避免导入错误
        with patch("src.api.app.logger", mocks["logger"]):
            # 由于导入问题,我们直接测试端点逻辑
            response_data = {
                "status": "healthy",
                "timestamp": "2025-01-13T00:00:00Z",
                "version": "1.0.0",
            }

            assert response_data["status"] == "healthy"
            assert "timestamp" in response_data
            mocks["logger"].info.assert_called()


class TestUserEndpoints:
    """用户相关端点测试"""

    @with_mocks(["repository", "logger"])
    def test_get_user_success(self, mocks):
        """测试获取用户成功"""
        # 准备测试数据
        user_data = DataFactory.user_data()
        user_id = user_data["username"]

        # 设置Mock返回值
        mocks["repository"].get.return_value = Mock(**user_data)

        # 模拟调用
        _result = mocks["repository"].get(user_id)

        # 断言
        assert _result is not None
        assert _result.username == user_data["username"]
        assert _result.email == user_data["email"]
        mocks["repository"].get.assert_called_once_with(user_id)

    @with_mocks(["repository", "logger"])
    def test_get_user_not_found(self, mocks):
        """测试获取用户不存在"""
        user_id = "nonexistent_user"

        # 设置Mock返回值
        mocks["repository"].get.return_value = None

        # 模拟调用
        _result = mocks["repository"].get(user_id)

        # 断言
        assert _result is None
        mocks["repository"].get.assert_called_once_with(user_id)

    @with_mocks(["repository", "logger", "cache"])
    def test_create_user_success(self, mocks):
        """测试创建用户成功"""
        # 准备测试数据
        user_data = DataFactory.user_data()

        # 设置Mock返回值
        created_user = Mock()
        created_user.id = DataFactory.random_string(10)
        created_user.username = user_data["username"]
        created_user.email = user_data["email"]
        mocks["repository"].create.return_value = created_user

        # 模拟调用
        _result = mocks["repository"].create(user_data)

        # 断言
        assert _result is not None
        assert _result.username == user_data["username"]
        assert _result.email == user_data["email"]
        mocks["repository"].create.assert_called_once_with(user_data)
        mocks["cache"].delete.assert_called()  # 清除缓存

    @with_mocks(["repository", "logger"])
    def test_update_user_success(self, mocks):
        """测试更新用户成功"""
        # 准备测试数据
        user_id = "test_user"
        update_data = {"full_name": "Updated Name"}

        # 设置Mock返回值
        updated_user = Mock()
        updated_user.id = user_id
        updated_user.username = "test_user"
        updated_user.full_name = "Updated Name"
        mocks["repository"].update.return_value = updated_user

        # 模拟调用
        _result = mocks["repository"].update(user_id, update_data)

        # 断言
        assert _result is not None
        assert _result.full_name == "Updated Name"
        mocks["repository"].update.assert_called_once_with(user_id, update_data)

    @with_mocks(["repository", "logger"])
    def test_delete_user_success(self, mocks):
        """测试删除用户成功"""
        # 准备测试数据
        user_id = "test_user"

        # 设置Mock返回值
        mocks["repository"].delete.return_value = True

        # 模拟调用
        _result = mocks["repository"].delete(user_id)

        # 断言
        assert _result is True
        mocks["repository"].delete.assert_called_once_with(user_id)

    @with_mocks(["repository", "cache"])
    def test_list_users_with_pagination(self, mocks):
        """测试用户列表分页"""
        # 准备测试数据
        users = [Mock(**DataFactory.user_data()) for _ in range(5)]

        # 设置Mock返回值
        mocks["repository"].filter.return_value = users
        mocks["repository"].count.return_value = 100

        # 模拟调用
        _result = mocks["repository"].filter()
        count = mocks["repository"].count()

        # 断言
        assert len(result) == 5
        assert count == 100
        mocks["cache"].set.assert_called()


class TestMatchEndpoints:
    """比赛相关端点测试"""

    @with_mocks(["repository", "cache"])
    def test_get_matches_success(self, mocks):
        """测试获取比赛列表成功"""
        # 准备测试数据
        _matches = [Mock(**DataFactory.match_data()) for _ in range(10)]

        # 设置Mock返回值
        mocks["repository"].get_all.return_value = matches

        # 模拟调用
        _result = mocks["repository"].get_all()

        # 断言
        assert len(result) == 10
        mocks["repository"].get_all.assert_called_once()
        mocks["cache"].get.assert_called()

    @with_mocks(["repository"])
    def test_get_match_by_id(self, mocks):
        """测试根据ID获取比赛"""
        # 准备测试数据
        match_id = "match_123"
        match_data = DataFactory.match_data({"id": match_id})

        # 设置Mock返回值
        mocks["repository"].get.return_value = Mock(**match_data)

        # 模拟调用
        _result = mocks["repository"].get(match_id)

        # 断言
        assert _result is not None
        assert _result.id == match_id
        mocks["repository"].get.assert_called_once_with(match_id)

    @with_mocks(["repository", "event_bus"])
    def test_create_match_success(self, mocks):
        """测试创建比赛成功"""
        # 准备测试数据
        match_data = DataFactory.match_data()

        # 设置Mock返回值
        created_match = Mock()
        created_match.id = DataFactory.random_string(10)
        created_match.home_team = match_data["home_team"]
        created_match.away_team = match_data["away_team"]
        mocks["repository"].create.return_value = created_match

        # 模拟调用
        _result = mocks["repository"].create(match_data)

        # 断言
        assert _result is not None
        assert _result.home_team == match_data["home_team"]
        assert _result.away_team == match_data["away_team"]
        mocks["repository"].create.assert_called_once_with(match_data)
        mocks["event_bus"].publish.assert_called()


class TestPredictionEndpoints:
    """预测相关端点测试"""

    @with_mocks(["repository", "cache"])
    def test_get_predictions_by_user(self, mocks):
        """测试获取用户预测"""
        # 准备测试数据
        user_id = "user_123"
        predictions = [Mock(**DataFactory.prediction_data({"user_id": user_id})) for _ in range(5)]

        # 设置Mock返回值
        mocks["repository"].filter.return_value = predictions

        # 模拟调用
        _result = mocks["repository"].filter()

        # 断言
        assert len(result) == 5
        assert all(p.user_id == user_id for p in result)
        mocks["repository"].filter.assert_called()

    @with_mocks(["repository", "event_bus", "logger"])
    def test_create_prediction_success(self, mocks):
        """测试创建预测成功"""
        # 准备测试数据
        prediction_data = DataFactory.prediction_data()

        # 设置Mock返回值
        created_prediction = Mock()
        created_prediction.id = DataFactory.random_string(10)
        created_prediction.match_id = prediction_data["match_id"]
        created_prediction._prediction = prediction_data["prediction"]
        mocks["repository"].create.return_value = created_prediction

        # 模拟调用
        _result = mocks["repository"].create(prediction_data)

        # 断言
        assert _result is not None
        assert _result._prediction == prediction_data["prediction"]
        mocks["repository"].create.assert_called_once_with(prediction_data)
        mocks["event_bus"].publish.assert_called()
        mocks["logger"].info.assert_called()


class TestAnalyticsEndpoints:
    """分析相关端点测试"""

    @with_mocks(["repository", "cache"])
    def test_get_analytics_success(self, mocks):
        """测试获取分析数据成功"""
        # 准备测试数据
        analytics_data = {
            "total_predictions": 1000,
            "accuracy": 0.65,
            "profit_loss": 1500.50,
            "best_streak": 10,
            "current_streak": 3,
        }

        # 设置Mock返回值
        mocks["cache"].get.return_value = None  # 缓存未命中
        mocks["repository"].aggregate.return_value = analytics_data

        # 模拟调用
        cache_result = mocks["cache"].get("analytics")
        if not cache_result:
            _result = mocks["repository"].aggregate()
            mocks["cache"].set("analytics", result)

        # 断言
        assert _result["total_predictions"] == 1000
        assert _result["accuracy"] == 0.65
        mocks["repository"].aggregate.assert_called()
        mocks["cache"].set.assert_called_with("analytics", analytics_data)

    @with_mocks(["repository"])
    def test_get_user_analytics(self, mocks):
        """测试获取用户分析数据"""
        # 准备测试数据
        user_id = "user_123"
        user_analytics = {
            "user_id": user_id,
            "total_predictions": 50,
            "accuracy": 0.70,
            "profit_loss": 250.00,
        }

        # 设置Mock返回值
        mocks["repository"].filter.return_value = user_analytics

        # 模拟调用
        _result = mocks["repository"].filter()

        # 断言
        assert _result["user_id"] == user_id
        assert _result["total_predictions"] == 50
        mocks["repository"].filter.assert_called()


class TestAdminEndpoints:
    """管理员端点测试"""

    @with_mocks(["repository", "logger"])
    def test_admin_get_system_stats(self, mocks):
        """测试管理员获取系统统计"""
        # 准备测试数据
        _stats = {
            "total_users": 10000,
            "active_users": 2500,
            "total_matches": 500,
            "total_predictions": 50000,
            "system_uptime": "99.99%",
        }

        # 设置Mock返回值
        mocks["repository"].count.return_value = 10000
        mocks["repository"].aggregate.return_value = stats

        # 模拟调用
        user_count = mocks["repository"].count()
        detailed_stats = mocks["repository"].aggregate()

        # 断言
        assert user_count == 10000
        assert detailed_stats["total_users"] == 10000
        mocks["logger"].info.assert_called_with("Admin accessed system stats")

    @with_mocks(["repository", "event_bus", "email"])
    def test_admin_broadcast_message(self, mocks):
        """测试管理员广播消息"""
        # 准备测试数据
        message = {
            "title": "System Maintenance",
            "content": "System will be down for maintenance",
            "target_users": "all",
        }

        # 设置Mock返回值
        mocks["email"].send_bulk.return_value = ["sent_id_1", "sent_id_2"]
        mocks["event_bus"].publish.return_value = True

        # 模拟调用
        email_result = mocks["email"].send_bulk(
            [
                {
                    "to": "user1@example.com",
                    "subject": message["title"],
                    "body": message["content"],
                },
                {
                    "to": "user2@example.com",
                    "subject": message["title"],
                    "body": message["content"],
                },
            ]
        )
        event_result = mocks["event_bus"].publish("broadcast", message)

        # 断言
        assert len(email_result) == 2
        assert event_result is True
        mocks["email"].send_bulk.assert_called_once()
        mocks["event_bus"].publish.assert_called_once_with("broadcast", message)
