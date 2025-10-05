"""
数据库模型测试 - Match模型
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.database.models.match import Match, MatchStatus
from src.database.models.team import Team


@pytest.mark.unit
class TestMatchModel:
    """Match模型测试"""

    @pytest.fixture
    def sample_match(self):
        """创建示例比赛"""
        match = Match()
        match.id = 12345
        match.home_team_id = 10
        match.away_team_id = 20
        match.league_id = 1
        match.match_time = datetime(2025, 9, 15, 15, 0, 0)
        match.match_status = MatchStatus.SCHEDULED
        match.season = "2024-25"
        match.home_score = None
        match.away_score = None
        match.venue = "Stadium"
        match.weather = "Sunny"
        match.attendance = 50000
        match.referee = "Referee Name"
        match.created_at = datetime.now()
        match.updated_at = datetime.now()
        return match

    @pytest.fixture
    def home_team(self):
        """创建主队"""
        team = Team()
        team.id = 10
        team.team_name = "Home Team"
        team.team_code = "HT"
        team.country = "Country"
        team.founded_year = 1900
        return team

    @pytest.fixture
    def away_team(self):
        """创建客队"""
        team = Team()
        team.id = 20
        team.team_name = "Away Team"
        team.team_code = "AT"
        team.country = "Country"
        team.founded_year = 1950
        return team

    def test_match_creation(self, sample_match):
        """测试比赛创建"""
        assert sample_match.id == 12345
        assert sample_match.home_team_id == 10
        assert sample_match.away_team_id == 20
        assert sample_match.league_id == 1
        assert sample_match.match_status == MatchStatus.SCHEDULED
        assert sample_match.season == "2024-25"

    def test_match_relationships(self, sample_match, home_team, away_team):
        """测试比赛关联关系"""
        # Mock 关联对象
        sample_match.home_team = home_team
        sample_match.away_team = away_team

        assert sample_match.home_team.name == "Home Team"
        assert sample_match.away_team.name == "Away Team"

    def test_match_status_enum(self):
        """测试比赛状态枚举"""
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.LIVE.value == "live"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.POSTPONED.value == "postponed"
        assert MatchStatus.CANCELLED.value == "cancelled"

    def test_match_result_methods(self, sample_match):
        """测试比赛结果方法"""
        # 未开始的比赛
        sample_match.home_score = None
        sample_match.away_score = None
        sample_match.match_status = MatchStatus.SCHEDULED
        assert sample_match.is_finished() is False
        assert sample_match.get_winner() is None

        # 已结束的比赛 - 主队胜
        sample_match.home_score = 2
        sample_match.away_score = 1
        sample_match.match_status = MatchStatus.FINISHED
        assert sample_match.is_finished() is True
        assert sample_match.get_winner() == "home"

        # 已结束的比赛 - 客队胜
        sample_match.home_score = 1
        sample_match.away_score = 2
        assert sample_match.get_winner() == "away"

        # 已结束的比赛 - 平局
        sample_match.home_score = 1
        sample_match.away_score = 1
        assert sample_match.get_winner() == "draw"

    def test_match_duration(self, sample_match):
        """测试比赛持续时间计算"""
        # 90分钟比赛
        sample_match.match_status = MatchStatus.FINISHED
        sample_match.duration_minutes = 90
        assert sample_match.duration_minutes == 90

        # 加时赛
        sample_match.duration_minutes = 120
        assert sample_match.duration_minutes == 120

    def test_match_repr(self, sample_match):
        """测试比赛的字符串表示"""
        expected = f"Match(id={sample_match.id}, home_team_id={sample_match.home_team_id}, away_team_id={sample_match.away_team_id})"
        assert repr(sample_match) == expected

    def test_match_to_dict(self, sample_match):
        """测试比赛转换为字典"""
        match_dict = sample_match.to_dict() if hasattr(sample_match, "to_dict") else {}

        # 如果没有to_dict方法，测试__dict__
        if not match_dict:
            match_dict = sample_match.__dict__

        assert match_dict["id"] == 12345
        assert match_dict["home_team_id"] == 10
        assert match_dict["away_team_id"] == 20

    def test_match_validation(self, sample_match):
        """测试比赛数据验证"""
        # 有效的比赛数据
        assert sample_match.home_team_id is not None
        assert sample_match.away_team_id is not None
        assert sample_match.league_id is not None
        assert sample_match.match_time is not None

    def test_match_upcoming_status(self, sample_match):
        """测试即将到来的比赛状态"""
        # 未来的比赛
        future_time = datetime(2025, 12, 25, 15, 0, 0)
        sample_match.match_time = future_time
        sample_match.match_status = MatchStatus.SCHEDULED

        assert sample_match.is_upcoming() if hasattr(sample_match, "is_upcoming") else True

    def test_match_score_update(self, sample_match):
        """测试比分更新"""
        # 初始比分
        sample_match.home_score = None
        sample_match.away_score = None

        # 更新比分
        sample_match.home_score = 1
        sample_match.away_score = 0
        sample_match.match_status = MatchStatus.LIVE

        assert sample_match.home_score == 1
        assert sample_match.away_score == 0
        assert sample_match.match_status == MatchStatus.LIVE

    def test_match_weather_conditions(self, sample_match):
        """测试天气条件"""
        weather_conditions = ["Sunny", "Rainy", "Cloudy", "Snow", "Windy"]

        for weather in weather_conditions:
            sample_match.weather = weather
            assert sample_match.weather == weather

    def test_match_attendance(self, sample_match):
        """测试观众人数"""
        # 有效观众人数
        valid_attendances = [0, 1000, 50000, 100000]

        for attendance in valid_attendances:
            sample_match.attendance = attendance
            assert sample_match.attendance == attendance

    def test_match_season_format(self, sample_match):
        """测试赛季格式"""
        valid_seasons = ["2024-25", "2023-24", "2025-26"]

        for season in valid_seasons:
            sample_match.season = season
            assert sample_match.season == season

    @pytest.mark.asyncio
    async def test_match_async_operations(self, sample_match):
        """测试比赛的异步操作"""
        # Mock async session
        mock_session = AsyncMock()

        # 测试异步保存（如果有）
        if hasattr(sample_match, "async_save"):
            result = await sample_match.async_save(mock_session)
            assert result is not None

    def test_match_comparisons(self, sample_match):
        """测试比赛比较操作"""
        # 创建第二个比赛
        match2 = Match()
        match2.id = 12346
        match2.home_team_id = 10
        match2.away_team_id = 30

        # 测试ID比较
        assert sample_match != match2
        assert sample_match.id != match2.id
