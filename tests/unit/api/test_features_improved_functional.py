"""
features_improved模块功能测试
真实测试API端点的业务逻辑
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.mark.unit
class TestFeaturesImprovedFunctional:
    """features_improved模块功能测试"""

    @pytest.fixture
    def mock_feature_store(self):
        """创建模拟的特征存储"""
        store = MagicMock()
        store.get_match_features_for_prediction = AsyncMock()
        return store

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def sample_match(self):
        """示例比赛数据"""
        match = MagicMock()
        match.id = 1
        match.home_team_id = 100
        match.away_team_id = 200
        match.home_score = 2
        match.away_score = 1
        match.status = "completed"
        match.match_date = "2024-01-01"
        return match

    def test_validate_match_id_valid(self):
        """测试有效的比赛ID验证"""
        from src.api.features_improved import validate_match_id

        # 不应该抛出异常
        validate_match_id(1)
        validate_match_id(100)

    def test_validate_match_id_invalid(self):
        """测试无效的比赛ID验证"""
        from src.api.features_improved import validate_match_id

        # 应该抛出HTTP异常
        with pytest.raises(HTTPException) as exc_info:
            validate_match_id(0)
        assert exc_info.value.status_code == 400
        assert "比赛ID必须大于0" in exc_info.value.detail

        with pytest.raises(HTTPException) as exc_info:
            validate_match_id(-1)
        assert exc_info.value.status_code == 400

    def test_check_feature_store_availability_available(self):
        """测试特征存储可用性检查 - 可用"""
        with patch("src.api.features_improved.feature_store", MagicMock()):
            from src.api.features_improved import check_feature_store_availability

            # 不应该抛出异常
            check_feature_store_availability()

    def test_check_feature_store_unavailable(self):
        """测试特征存储不可用时"""
        with patch("src.api.features_improved.feature_store", None):
            from src.api.features_improved import check_feature_store_availability

            with pytest.raises(HTTPException) as exc_info:
                check_feature_store_availability()
            assert exc_info.value.status_code == 503
            assert "特征存储服务暂时不可用" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_match_info_success(self, mock_db_session, sample_match):
        """测试成功获取比赛信息"""
        from src.api.features_improved import get_match_info

        # 设置mock返回值
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_match
        )

        result = await get_match_info(mock_db_session, 1)
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_match_info_not_found(self, mock_db_session):
        """测试获取不存在的比赛信息"""
        from src.api.features_improved import get_match_info

        # 设置mock返回None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_match_info(mock_db_session, 999)
        assert exc_info.value.status_code == 404
        assert "比赛 999 不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_match_info_db_error(self, mock_db_session):
        """测试数据库查询错误"""
        from src.api.features_improved import get_match_info
        from sqlalchemy.exc import SQLAlchemyError

        # 设置mock抛出数据库异常
        mock_db_session.execute.side_effect = SQLAlchemyError("Connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_match_info(mock_db_session, 1)
        assert exc_info.value.status_code == 500
        assert "数据库查询失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_features_data_success(self, mock_feature_store, sample_match):
        """测试成功获取特征数据"""
        from src.api.features_improved import get_features_data

        # 设置mock返回值
        expected_features = {
            "team_form": {"home": 0.8, "away": 0.6},
            "head_to_head": {"home_wins": 3, "away_wins": 2},
            "recent_performance": {"home_goals": 5, "away_goals": 3},
        }
        mock_feature_store.get_match_features_for_prediction.return_value = (
            expected_features
        )

        with patch("src.api.features_improved.feature_store", mock_feature_store):
            features, error = await get_features_data(1, sample_match)
            assert features == expected_features
            assert error is None

    @pytest.mark.asyncio
    async def test_get_features_data_no_data(self, mock_feature_store, sample_match):
        """测试没有特征数据的情况"""
        from src.api.features_improved import get_features_data

        # 设置mock返回空
        mock_feature_store.get_match_features_for_prediction.return_value = {}

        with patch("src.api.features_improved.feature_store", mock_feature_store):
            features, error = await get_features_data(1, sample_match)
            assert features == {}
            assert error is None

    @pytest.mark.asyncio
    async def test_get_features_data_error(self, mock_feature_store, sample_match):
        """测试获取特征数据出错"""
        from src.api.features_improved import get_features_data

        # 设置mock抛出异常
        mock_feature_store.get_match_features_for_prediction.side_effect = Exception(
            "Feature store error"
        )

        with patch("src.api.features_improved.feature_store", mock_feature_store):
            features, error = await get_features_data(1, sample_match)
            assert features == {}
            assert error == "Feature store error"

    def test_build_response_data_basic(self, sample_match):
        """测试构建响应数据 - 基础版本"""
        from src.api.features_improved import build_response_data

        features = {"team_form": 0.8}
        features_error = None
        include_raw = False

        response = build_response_data(
            sample_match, features, features_error, include_raw
        )

        # 验证响应结构
        assert "match_id" in response
        assert "features" in response
        assert "metadata" in response
        assert response["match_id"] == 1
        assert response["features"] == features

    def test_build_response_data_with_error(self, sample_match):
        """测试构建响应数据 - 包含错误"""
        from src.api.features_improved import build_response_data

        features = {}
        features_error = "Feature store unavailable"
        include_raw = False

        response = build_response_data(
            sample_match, features, features_error, include_raw
        )

        assert response["features"] == {}
        assert "error" in response["metadata"]
        assert response["metadata"]["error"] == features_error

    def test_build_response_data_include_raw(self, sample_match):
        """测试构建响应数据 - 包含原始数据"""
        from src.api.features_improved import build_response_data

        features = {"team_form": 0.8}
        features_error = None
        include_raw = True

        response = build_response_data(
            sample_match, features, features_error, include_raw
        )

        assert "raw_features" in response
        assert response["raw_features"] == features

    @patch("src.api.features_improved.feature_store", None)
    def test_module_initialization_failure(self):
        """测试模块初始化失败的情况"""
        from src.api.features_improved import check_feature_store_availability

        with pytest.raises(HTTPException) as exc_info:
            check_feature_store_availability()
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_full_workflow_success(
        self, mock_db_session, mock_feature_store, sample_match
    ):
        """测试完整的工作流程 - 成功场景"""
        # 设置所有mock
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_match
        )
        mock_feature_store.get_match_features_for_prediction.return_value = {
            "team_form": {"home": 0.8, "away": 0.6}
        }

        with patch("src.api.features_improved.feature_store", mock_feature_store):
            from src.api.features_improved import (
                validate_match_id,
                check_feature_store_availability,
                get_match_info,
                get_features_data,
                build_response_data,
            )

            # 1. 验证参数
            validate_match_id(1)

            # 2. 检查服务可用性
            check_feature_store_availability()

            # 3. 获取比赛信息
            await get_match_info(mock_db_session, 1)

            # 4. 获取特征数据
            features, error = await get_features_data(1, sample_match)

            # 5. 构建响应
            response = build_response_data(
                sample_match, features, error, include_raw=False
            )

            # 验证最终响应
            assert response["match_id"] == 1
            assert "team_form" in response["features"]
            assert response["features"]["team_form"]["home"] == 0.8

    def test_logging_functionality(self, caplog):
        """测试日志功能"""
        from src.api.features_improved import validate_match_id
        import logging

        # 设置日志级别
        caplog.set_level(logging.WARNING)

        # 触发警告日志
        try:
            validate_match_id(-1)
        except HTTPException:
            pass

        # 验证日志记录
        assert "无效的比赛ID" in caplog.text
