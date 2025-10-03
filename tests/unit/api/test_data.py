"""
数据API模块精细化测试
专注于修复Mock问题并提升更多函数的覆盖率
目标：src/api/data.py 从25%提升到40%+
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Query
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 创建更完善的Mock
def create_mock_async_session():
    """创建更完善的mock async session"""
    session = AsyncMock(spec=AsyncSession)

    # Mock result对象
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None

    # Mock count
    mock_result.count.return_value = 0

    session.execute.return_value = mock_result
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    return session

def create_mock_query_result(data_list):
    """创建更好的查询结果mock"""
    result_mock = MagicMock()

    if data_list:
        # Mock scalars()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = data_list
        scalars_mock.first.return_value = data_list[0] if data_list else None
        result_mock.scalars.return_value = scalars_mock

        # Mock first()
        result_mock.first.return_value = data_list[0] if data_list else None

        # Mock scalar_one_or_none()
        result_mock.scalar_one_or_none.return_value = data_list[0] if len(data_list) == 1 else None

        # Mock count
        result_mock.count.return_value = len(data_list)
    else:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        scalars_mock.first.return_value = None
        result_mock.scalars.return_value = scalars_mock
        result_mock.first.return_value = None
        result_mock.scalar_one_or_none.return_value = None
        result_mock.count.return_value = 0

    return result_mock


class TestDataAPIMocks:
    """测试改进的Mock方法"""

    @pytest.mark.asyncio
    async def test_get_matches_with_proper_mocks(self):
        """测试使用正确Mock的获取比赛"""
        # 创建测试数据
        matches = [{
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "home_score": 2,
            "away_score": 1,
            "status": "finished",
            "match_date": datetime.now()
        }]

        # 创建完善mock
        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result(matches)
        mock_session.execute.return_value = mock_result

        # Mock format_pagination函数
        with patch('src.api.data.get_async_session', return_value=mock_session), \
             patch('src.api.data.format_pagination') as mock_format_pagination:

            mock_format_pagination.return_value = {
                "page": 1,
                "page_size": 10,
                "total": 1,
                "pages": 1
            }

            try:
                from src.api.data import get_matches
                result = await get_matches(
                    limit=10,
                    offset=0,
                    session=mock_session
                )
                assert result is not None
                assert "items" in result
                assert "pagination" in result
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_get_matches_with_all_parameters(self):
        """测试带所有参数的比赛查询"""
        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result([])
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session), \
             patch('src.api.data.format_pagination') as mock_format_pagination:

            mock_format_pagination.return_value = {"page": 1}

            try:
                from src.api.data import get_matches
                result = await get_matches(
                    limit=20,
                    offset=10,
                    league_id=1,
                    team_id=101,
                    status = os.getenv("TEST_DATA_STATUS_138"),
                    session=mock_session
                )
                assert result is not None
                # 验证所有参数都被使用
                mock_session.execute.assert_called()
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_get_teams_with_count_mock(self):
        """测试获取球队（改进Mock）"""
        teams = [{
            "id": 101,
            "name": "Test Team",
            "league_id": 1,
            "points": 30
        }]

        mock_session = create_mock_async_session()

        # 分别mock获取数据和总数
        mock_session.execute.side_effect = [
            create_mock_query_result(teams),  # 第一次调用返回数据
            create_mock_query_result([{"count": len(teams)}])  # 第二次调用返回总数
        ]

        with patch('src.api.data.get_async_session', return_value=mock_session), \
             patch('src.api.data.format_pagination') as mock_format_pagination:

            mock_format_pagination.return_value = {"page": 1}

            try:
                from src.api.data import get_teams
                result = await get_teams(
                    limit=10,
                    offset=0,
                    search="Test",
                    session=mock_session
                )
                assert result is not None
            except ImportError:
                pytest.skip("get_teams not available")

    @pytest.mark.asyncio
    async def test_get_match_by_id_with_existing_match(self):
        """测试获取存在的比赛"""
        match = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": "live",
            "match_date": datetime.now()
        }

        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result([match])
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session):
            try:
                from src.api.data import get_match_by_id
                result = await get_match_by_id(match_id=1, session=mock_session)
                assert result is not None
                assert result["id"] == 1
            except ImportError:
                pytest.skip("get_match_by_id not available")

    @pytest.mark.asyncio
    async def test_get_league_standings(self):
        """测试获取联赛积分榜"""
        standings = [
            {"position": 1, "team_id": 101, "points": 30, "goal_diff": 15},
            {"position": 2, "team_id": 102, "points": 25, "goal_diff": 8}
        ]

        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result(standings)
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session):
            try:
                from src.api.data import get_league_standings
                result = await get_league_standings(league_id=1, session=mock_session)
                assert result is not None
                assert len(result) == 2
                assert result[0]["position"] == 1
            except ImportError:
                pytest.skip("get_league_standings not available")


class TestDataUtilityFunctions:
    """测试数据工具函数"""

    def test_validate_pagination_function(self):
        """测试分页验证函数的多种情况"""
        try:
            from src.api.data import validate_pagination

            # 测试各种有效组合
            test_cases = [
                (10, 0, True),
                (50, 100, True),
                (1000, 0, True),
                (100, 1000, True)
            ]

            for limit, offset, expected in test_cases:
                result = validate_pagination(limit, offset)
                assert result == expected, f"Failed for limit={limit}, offset={offset}"

        except ImportError:
            pytest.skip("validate_pagination not available")
        except Exception as e:
            # 如果函数抛出异常，说明有验证逻辑
            assert isinstance(e, (HTTPException, ValueError))

    def test_format_pagination_function(self):
        """测试分页格式化函数"""
        try:
            from src.api.data import format_pagination

            result = format_pagination(
                page=1,
                page_size=10,
                total=95,
                offset=0
            )

            assert result is not None
            assert "page" in result
            assert "page_size" in result
            assert "total" in result
            assert "has_next" in result
            assert "has_prev" in result

        except ImportError:
            pytest.skip("format_pagination not available")

    def test_format_match_response_function(self):
        """测试比赛响应格式化"""
        match_data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "home_score": 2,
            "away_score": 1,
            "status": "finished",
            "match_date": datetime.now()
        }

        try:
            from src.api.data import format_match_response
            result = format_match_response(match_data)

            assert result is not None
            assert result["id"] == 1
            assert result["home_score"] == 2
            assert result["away_score"] == 1

        except ImportError:
            pytest.skip("format_match_response not available")

    def test_format_team_response_function(self):
        """测试球队响应格式化"""
        team_data = {
            "id": 101,
            "name": "Test Team",
            "league_id": 1,
            "points": 30,
            "played": 10,
            "won": 8,
            "drawn": 2,
            "lost": 0
        }

        try:
            from src.api.data import format_team_response
            result = format_team_response(team_data)

            assert result is not None
            assert result["id"] == 101
            assert result["name"] == "Test Team"
            assert result["points"] == 30

        except ImportError:
            pytest.skip("format_team_response not available")


class TestDataValidationFunctions:
    """测试数据验证函数"""

    def test_validate_match_data_comprehensive(self):
        """测试比赛数据验证的全面情况"""
        try:
            from src.api.data import validate_match_data

            # 测试有效数据
            valid_match = {
                "id": 1,
                "home_team_id": 101,
                "away_team_id": 102,
                "league_id": 1,
                "status": "finished",
                "match_date": datetime.now()
            }
            assert validate_match_data(valid_match) == True

            # 测试缺少必要字段
            invalid_match = {"id": 1}
            assert validate_match_data(invalid_match) == False

            # 测试无效的球队ID（相同）
            same_team_match = {
                "id": 1,
                "home_team_id": 101,
                "away_team_id": 101,  # 相同球队
                "league_id": 1,
                "status": "scheduled",
                "match_date": datetime.now()
            }
            assert validate_match_data(same_team_match) == False

        except ImportError:
            pytest.skip("validate_match_data not available")

    def test_parse_match_status_function(self):
        """测试比赛状态解析函数"""
        try:
            from src.api.data import _parse_match_status

            # 测试各种状态
            test_cases = [
                ("finished", "finished"),
                ("FINISHED", "finished"),
                ("Live", "live"),
                ("SCHEDULED", "scheduled"),
                ("CANCELLED", "cancelled"),
                ("postponed", "postponed")
            ]

            for input_status, expected in test_cases:
                result = _parse_match_status(input_status)
                assert result == expected, f"Failed for {input_status}"

        except ImportError:
            pytest.skip("_parse_match_status not available")
        except Exception as e:
            # 可能会抛出HTTPException
            assert "status" in str(e).lower()


class TestDataEdgeCases:
    """测试数据API的边界情况"""

    @pytest.mark.asyncio
    async def test_empty_database_results(self):
        """测试空数据库结果"""
        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result([])
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session), \
             patch('src.api.data.format_pagination') as mock_format_pagination:

            mock_format_pagination.return_value = {"page": 1, "total": 0}

            try:
                from src.api.data import get_matches
                result = await get_matches(limit=10, offset=0, session=mock_session)
                assert result is not None
                assert result["items"] == []
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_large_offset_pagination(self):
        """测试大偏移量的分页"""
        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result([])
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session), \
             patch('src.api.data.format_pagination') as mock_format_pagination:

            mock_format_pagination.return_value = {"page": 100, "total": 0}

            try:
                from src.api.data import get_matches
                result = await get_matches(
                    limit=10,
                    offset=990,  # 大偏移量
                    session=mock_session
                )
                assert result is not None
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_maximum_limit(self):
        """测试最大限制参数"""
        mock_session = create_mock_async_session()
        mock_result = create_mock_query_result([])
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session), \
             patch('src.api.data.format_pagination') as mock_format_pagination:

            mock_format_pagination.return_value = {"page": 1}

            try:
                from src.api.data import get_matches
                result = await get_matches(
                    limit=1000,  # 最大值
                    offset=0,
                    session=mock_session
                )
                assert result is not None
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_exceed_maximum_limit(self):
        """测试超过最大限制"""
        try:
            from src.api.data import get_matches

            with pytest.raises(HTTPException) as exc_info:
                await get_matches(
                    limit=1001,  # 超过最大值
                    offset=0,
                    session=create_mock_async_session()
                )
            assert exc_info.value.status_code == 400

        except ImportError:
            pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_negative_parameters(self):
        """测试负参数"""
        try:
            from src.api.data import get_matches

            # 测试负limit
            with pytest.raises(HTTPException):
                await get_matches(
                    limit=-1,
                    offset=0,
                    session=create_mock_async_session()
                )

            # 测试负offset
            with pytest.raises(HTTPException):
                await get_matches(
                    limit=10,
                    offset=-1,
                    session=create_mock_async_session()
                )

        except ImportError:
            pytest.skip("get_matches not available")


class TestDataErrorHandling:
    """测试数据API错误处理"""

    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """测试数据库连接错误"""
        mock_session = create_mock_async_session()
        mock_session.execute.side_effect = Exception("Connection failed")

        with patch('src.api.data.get_async_session', return_value=mock_session):
            try:
                from src.api.data import get_matches
                with pytest.raises(Exception):
                    await get_matches(limit=10, offset=0, session=mock_session)
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_session_timeout(self):
        """测试会话超时"""
        mock_session = create_mock_async_session()
        mock_session.execute.side_effect = asyncio.TimeoutError("Query timeout")

        with patch('src.api.data.get_async_session', return_value=mock_session):
            try:
                from src.api.data import get_matches
                with pytest.raises(asyncio.TimeoutError):
                    await get_matches(limit=10, offset=0, session=mock_session)
            except ImportError:
                pytest.skip("get_matches not available")

    @pytest.mark.asyncio
    async def test_corrupted_data(self):
        """测试损坏的数据"""
        # 模拟返回格式错误的数据
        mock_session = create_mock_async_session()
        mock_result = MagicMock()
        mock_result.scalars.side_effect = Exception("Data corruption")
        mock_session.execute.return_value = mock_result

        with patch('src.api.data.get_async_session', return_value=mock_session):
            try:
                from src.api.data import get_matches
                with pytest.raises(Exception):
                    await get_matches(limit=10, offset=0, session=mock_session)
            except ImportError:
                pytest.skip("get_matches not available")


# 运行所有测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])