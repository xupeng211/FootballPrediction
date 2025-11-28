"""数据管理API安全测试 - Data Security Architecture.

测试 src/api/data_management.py 的所有端点，确保：
1. CRUD操作正常工作
2. 错误处理机制有效
3. 数据安全性和完整性
4. 异常情况下的优雅降级
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.data_management import router


class TestDataManagementAPI:
    """数据管理API安全测试."""

    def setup_method(self):
        """设置测试方法."""
        # 创建测试客户端
        self.client = TestClient(router)

        # 模拟数据
        self.mock_match_data = {
            "id": 1,
            "home_team": {"id": 3, "name": "Manchester United"},
            "away_team": {"id": 4, "name": "Fulham"},
            "league": {"id": 1, "name": "Premier League"},
            "match_date": "2024-08-16T19:00:00Z",
            "home_score": 1,
            "away_score": 0,
            "status": "FINISHED",
        }

        self.mock_team_data = {
            "teams": [
                {"id": 1, "name": "Manchester United", "league_id": 1},
                {"id": 2, "name": "Liverpool", "league_id": 1},
            ],
            "total": 2,
        }

        self.mock_league_data = {
            "leagues": [
                {"id": 1, "name": "Premier League", "country": "England"},
                {"id": 2, "name": "La Liga", "country": "Spain"},
            ],
            "total": 2,
        }

        self.mock_odds_data = {
            "odds": [
                {
                    "id": 1,
                    "match_id": 1,
                    "home_win": 2.5,
                    "draw": 3.2,
                    "away_win": 2.8,
                }
            ],
            "total": 1,
        }

    # ========================================
    # Mock 对象定义
    # ========================================

    def create_mock_match(
        self, match_id=1, home_team_id=3, away_team_id=4, league_id=1
    ):
        """创建模拟比赛对象."""
        mock_match = MagicMock()
        mock_match.id = match_id
        mock_match.home_team_id = home_team_id
        mock_match.away_team_id = away_team_id
        mock_match.league_id = league_id
        mock_match.home_score = 1
        mock_match.away_score = 0
        mock_match.status = "FINISHED"
        mock_match.match_date = datetime(2024, 8, 16, 19, 0, 0)

        # 模拟关联对象
        mock_home_team = MagicMock()
        mock_home_team.id = home_team_id
        mock_home_team.name = "Manchester United"
        mock_match.home_team = mock_home_team

        mock_away_team = MagicMock()
        mock_away_team.id = away_team_id
        mock_away_team.name = "Fulham"
        mock_match.away_team = mock_away_team

        mock_league = MagicMock()
        mock_league.id = league_id
        mock_league.name = "Premier League"
        mock_match.league = mock_league

        return mock_match

    # ========================================
    # GET /matches 端点测试
    # ========================================

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    def test_get_matches_list_success(self, mock_get_session, mock_match_repo):
        """测试成功获取比赛列表."""
        # 设置Mock
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance

        # 模拟比赛数据
        mock_matches = [self.create_mock_match(), self.create_mock_match(match_id=2)]
        mock_repo_instance.get_matches_with_teams.return_value = mock_matches

        # 使用FastAPI TestClient需要完整应用上下文，这里直接测试函数
        from src.api.data_management import get_matches_list

        import asyncio

        result = asyncio.run(get_matches_list(limit=10, offset=0, session=mock_session))

        # 验证结果
        assert "matches" in result
        assert "total" in result
        assert len(result["matches"]) == 2
        assert result["total"] == 2
        assert result["matches"][0]["home_team"]["name"] == "Manchester United"
        assert result["matches"][0]["away_team"]["name"] == "Fulham"

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    def test_get_matches_list_with_pagination(self, mock_get_session, mock_match_repo):
        """测试带分页的比赛列表获取."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance
        mock_repo_instance.get_matches_with_teams.return_value = []

        from src.api.data_management import get_matches_list
        import asyncio

        result = asyncio.run(
            get_matches_list(limit=20, offset=10, session=mock_session)
        )

        # 验证调用参数
        mock_repo_instance.get_matches_with_teams.assert_called_once_with(
            limit=20, offset=10
        )
        assert result["matches"] == []
        assert result["total"] == 0

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    def test_get_matches_list_database_error(self, mock_get_session, mock_match_repo):
        """测试数据库错误时的降级处理."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance
        mock_repo_instance.get_matches_with_teams.side_effect = Exception(
            "Database connection failed"
        )

        from src.api.data_management import get_matches_list
        import asyncio

        result = asyncio.run(get_matches_list(limit=10, offset=0, session=mock_session))

        # 验证降级到模拟数据
        assert "matches" in result
        assert "total" in result
        assert len(result["matches"]) == 2  # 应该返回模拟数据的数量
        assert result["total"] == 2
        # 验证模拟数据内容
        assert result["matches"][0]["home_team"]["name"] == "Manchester United"
        assert result["matches"][1]["home_team"]["name"] == "Liverpool"

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    def test_get_matches_list_empty_result(self, mock_get_session, mock_match_repo):
        """测试空比赛列表."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance
        mock_repo_instance.get_matches_with_teams.return_value = []

        from src.api.data_management import get_matches_list
        import asyncio

        result = asyncio.run(get_matches_list(limit=10, offset=0, session=mock_session))

        assert result["matches"] == []
        assert result["total"] == 0

    # ========================================
    # GET /matches/{match_id} 端点测试
    # ========================================

    @patch("src.services.data.get_data_service")
    def test_get_match_by_id_success(self, mock_get_service):
        """测试成功根据ID获取比赛."""
        mock_service = MagicMock()
        mock_service.get_match_by_id.return_value = self.mock_match_data
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_match_by_id
        import asyncio

        result = asyncio.run(get_match_by_id(1))

        assert result == self.mock_match_data
        mock_service.get_match_by_id.assert_called_once_with(1)

    @patch("src.services.data.get_data_service")
    def test_get_match_by_id_not_found(self, mock_get_service):
        """测试获取不存在的比赛ID."""
        mock_service = MagicMock()
        mock_service.get_match_by_id.return_value = None
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_match_by_id
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_match_by_id(999))

        assert "比赛ID 999 不存在" in str(exc_info.value)

    @patch("src.services.data.get_data_service")
    def test_get_match_by_id_service_error(self, mock_get_service):
        """测试服务层错误处理."""
        mock_service = MagicMock()
        mock_service.get_match_by_id.side_effect = Exception("Service unavailable")
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_match_by_id
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_match_by_id(1))

        assert "获取比赛信息失败" in str(exc_info.value)

    # ========================================
    # GET /teams 端点测试
    # ========================================

    @patch("src.api.data_management.get_real_data_service")
    @patch("src.api.data_management.get_async_session")
    def test_get_teams_list_success(self, mock_get_session, mock_get_service):
        """测试成功获取球队列表."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_service = AsyncMock()
        mock_service.get_teams_list.return_value = self.mock_team_data
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_teams_list
        import asyncio

        result = asyncio.run(get_teams_list(limit=20, offset=0, session=mock_session))

        assert result == self.mock_team_data
        mock_service.get_teams_list.assert_called_once_with(limit=20, offset=0)

    @patch("src.api.data_management.get_real_data_service")
    @patch("src.api.data_management.get_async_session")
    def test_get_teams_list_with_pagination(self, mock_get_session, mock_get_service):
        """测试带分页的球队列表获取."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_service = AsyncMock()
        mock_service.get_teams_list.return_value = {"teams": [], "total": 0}
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_teams_list
        import asyncio

        result = asyncio.run(get_teams_list(limit=5, offset=10, session=mock_session))

        mock_service.get_teams_list.assert_called_once_with(limit=5, offset=10)
        assert result["teams"] == []
        assert result["total"] == 0

    @patch("src.api.data_management.get_real_data_service")
    @patch("src.api.data_management.get_async_session")
    def test_get_teams_list_service_error(self, mock_get_session, mock_get_service):
        """测试服务错误处理."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_service = AsyncMock()
        mock_service.get_teams_list.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_teams_list
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_teams_list(limit=20, offset=0, session=mock_session))

        assert "获取球队列表失败" in str(exc_info.value)

    # ========================================
    # GET /teams/{team_id} 端点测试
    # ========================================

    @patch("src.api.data_management.get_real_data_service")
    @patch("src.api.data_management.get_async_session")
    def test_get_team_by_id_success(self, mock_get_session, mock_get_service):
        """测试成功根据ID获取球队."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_team = {"id": 1, "name": "Manchester United", "league_id": 1}
        mock_service = AsyncMock()
        mock_service.get_team_by_id.return_value = mock_team
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_team_by_id
        import asyncio

        result = asyncio.run(get_team_by_id(1, session=mock_session))

        assert result == mock_team
        mock_service.get_team_by_id.assert_called_once_with(1)

    @patch("src.api.data_management.get_real_data_service")
    @patch("src.api.data_management.get_async_session")
    def test_get_team_by_id_not_found(self, mock_get_session, mock_get_service):
        """测试获取不存在的球队ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_service = AsyncMock()
        mock_service.get_team_by_id.return_value = None
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_team_by_id
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_team_by_id(999, session=mock_session))

        assert "球队ID 999 不存在" in str(exc_info.value)

    @patch("src.api.data_management.get_real_data_service")
    @patch("src.api.data_management.get_async_session")
    def test_get_team_by_id_service_error(self, mock_get_session, mock_get_service):
        """测试服务错误处理."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_service = AsyncMock()
        mock_service.get_team_by_id.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_team_by_id
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_team_by_id(1, session=mock_session))

        assert "获取球队信息失败" in str(exc_info.value)

    # ========================================
    # GET /leagues 端点测试
    # ========================================

    @patch("src.services.data.get_data_service")
    def test_get_leagues_list_success(self, mock_get_service):
        """测试成功获取联赛列表."""
        mock_service = MagicMock()
        mock_service.get_leagues_list.return_value = self.mock_league_data
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_leagues_list
        import asyncio

        result = asyncio.run(get_leagues_list(limit=20, offset=0))

        assert result == self.mock_league_data
        mock_service.get_leagues_list.assert_called_once_with(limit=20, offset=0)

    @patch("src.services.data.get_data_service")
    def test_get_leagues_list_with_pagination(self, mock_get_service):
        """测试带分页的联赛列表获取."""
        mock_service = MagicMock()
        mock_service.get_leagues_list.return_value = {"leagues": [], "total": 0}
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_leagues_list
        import asyncio

        result = asyncio.run(get_leagues_list(limit=5, offset=10))

        mock_service.get_leagues_list.assert_called_once_with(limit=5, offset=10)
        assert result["leagues"] == []
        assert result["total"] == 0

    @patch("src.services.data.get_data_service")
    def test_get_leagues_list_service_error(self, mock_get_service):
        """测试服务错误处理."""
        mock_service = MagicMock()
        mock_service.get_leagues_list.side_effect = Exception("Service unavailable")
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_leagues_list
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_leagues_list(limit=20, offset=0))

        assert "获取联赛列表失败" in str(exc_info.value)

    # ========================================
    # GET /odds 端点测试
    # ========================================

    @patch("src.services.data.get_data_service")
    def test_get_odds_data_success(self, mock_get_service):
        """测试成功获取赔率数据."""
        mock_service = MagicMock()
        mock_service.get_odds_data.return_value = self.mock_odds_data
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_odds_data
        import asyncio

        result = asyncio.run(get_odds_data(match_id=1))

        assert result == self.mock_odds_data
        mock_service.get_odds_data.assert_called_once_with(match_id=1)

    @patch("src.services.data.get_data_service")
    def test_get_odds_data_without_filter(self, mock_get_service):
        """测试不带过滤条件的赔率数据获取."""
        mock_service = MagicMock()
        mock_service.get_odds_data.return_value = {"odds": [], "total": 0}
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_odds_data
        import asyncio

        result = asyncio.run(get_odds_data(match_id=None))

        assert result["odds"] == []
        assert result["total"] == 0
        mock_service.get_odds_data.assert_called_once_with(match_id=None)

    @patch("src.services.data.get_data_service")
    def test_get_odds_data_service_error(self, mock_get_service):
        """测试服务错误处理."""
        mock_service = MagicMock()
        mock_service.get_odds_data.side_effect = Exception("Odds service error")
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_odds_data
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_odds_data(match_id=1))

        assert "获取赔率数据失败" in str(exc_info.value)

    # ========================================
    # 安全性和边界测试
    # ========================================

    @patch("src.services.data.get_data_service")
    def test_get_match_by_id_invalid_id_types(self, mock_get_service):
        """测试无效ID类型的处理."""
        mock_service = MagicMock()
        mock_service.get_match_by_id.return_value = None
        mock_get_service.return_value = mock_service

        from src.api.data_management import get_match_by_id
        import asyncio

        # 测试负数ID
        with pytest.raises(Exception):
            asyncio.run(get_match_by_id(-1))

        # 测试零ID
        with pytest.raises(Exception):
            asyncio.run(get_match_by_id(0))

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    def test_get_matches_list_invalid_pagination(
        self, mock_get_session, mock_match_repo
    ):
        """测试无效分页参数."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance
        mock_repo_instance.get_matches_with_teams.return_value = []

        from src.api.data_management import get_matches_list
        import asyncio

        # 测试负数limit
        result = asyncio.run(get_matches_list(limit=-5, offset=0, session=mock_session))
        assert result["matches"] == []

        # 测试负数offset
        result = asyncio.run(
            get_matches_list(limit=10, offset=-10, session=mock_session)
        )
        assert result["matches"] == []

        # 验证调用参数被传递（即使无效）
        assert mock_repo_instance.get_matches_with_teams.call_count == 2

    def test_data_format_integrity(self):
        """测试返回数据格式的完整性."""
        # 模拟有缺失关联数据的比赛
        incomplete_match = MagicMock()
        incomplete_match.id = 1
        incomplete_match.home_team_id = 999  # 不存在的球队
        incomplete_match.away_team_id = 888  # 不存在的球队
        incomplete_match.league_id = 777  # 不存在的联赛
        incomplete_match.home_score = None
        incomplete_match.away_score = None
        incomplete_match.status = None
        incomplete_match.match_date = None
        incomplete_match.home_team = None
        incomplete_match.away_team = None
        incomplete_match.league = None

        @patch("src.api.data_management.MatchRepository")
        @patch("src.api.data_management.get_async_session")
        def test_incomplete_data(mock_get_session, mock_match_repo):
            mock_session = AsyncMock(spec=AsyncSession)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_repo_instance = AsyncMock()
            mock_match_repo.return_value = mock_repo_instance
            mock_repo_instance.get_matches_with_teams.return_value = [incomplete_match]

            from src.api.data_management import get_matches_list
            import asyncio

            result = asyncio.run(
                get_matches_list(limit=10, offset=0, session=mock_session)
            )

            # 验证默认值处理
            match_data = result["matches"][0]
            assert match_data["home_team"]["name"] == "Unknown Team"
            assert match_data["away_team"]["name"] == "Unknown Team"
            assert match_data["league"]["name"] == "Premier League"  # 默认联赛名
            assert match_data["match_date"] is None
            assert match_data["home_score"] is None
            assert match_data["away_score"] is None
            assert match_data["status"] == "SCHEDULED"  # 默认状态

        test_incomplete_data()

    # ========================================
    # 性能和负载测试边界
    # ========================================

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    def test_get_matches_list_large_dataset(self, mock_get_session, mock_match_repo):
        """测试大数据集处理."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance

        # 模拟大量数据
        large_matches = [self.create_mock_match(match_id=i) for i in range(1000)]
        mock_repo_instance.get_matches_with_teams.return_value = large_matches

        from src.api.data_management import get_matches_list
        import asyncio

        result = asyncio.run(
            get_matches_list(limit=1000, offset=0, session=mock_session)
        )

        assert len(result["matches"]) == 1000
        assert result["total"] == 1000

    # ========================================
    # 集成测试
    # ========================================

    def test_router_initialization(self):
        """测试路由初始化."""
        assert router is not None
        assert router.tags == ["数据管理"]

    @patch("src.api.data_management.MatchRepository")
    @patch("src.api.data_management.get_async_session")
    @patch("logging.getLogger")
    def test_logging_functionality(
        self, mock_logger, mock_get_session, mock_match_repo
    ):
        """测试日志功能."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_match_repo.return_value = mock_repo_instance
        mock_repo_instance.get_matches_with_teams.return_value = [
            self.create_mock_match()
        ]

        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        from src.api.data_management import get_matches_list
        import asyncio

        asyncio.run(get_matches_list(limit=10, offset=0, session=mock_session))

        # 验证日志调用
        mock_log_instance.info.assert_called()
        log_calls = [call.args[0] for call in mock_log_instance.info.call_args_list]
        assert any("成功获取" in msg and "条比赛记录" in msg for msg in log_calls)
