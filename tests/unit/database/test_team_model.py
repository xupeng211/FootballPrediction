"""球队模型测试"""
import pytest
from src.database.models.team import Team, TeamForm

class TestTeamModel:
    """球队模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(
            id=1,
            name="Team A",
            code="TA",
            league="Premier League",
            country="England",
            founded=1886
        )

        assert team.id == 1
        assert team.name == "Team A"
        assert team.code == "TA"
        assert team.league == "Premier League"
        assert team.founded == 1886

    def test_team_properties(self):
        """测试球队属性"""
        team = Team(
            id=1,
            name="Manchester United",
            code="MUN",
            league="Premier League"
        )

        assert team.short_name == "MUN"
        assert team.display_name == "Manchester United"

    def test_team_form_calculation(self):
        """测试球队状态计算"""
        team = Team(id=1, name="Team A")

        # 添加比赛记录
        team.recent_matches = [
            {"result": "W", "score": "2-1"},
            {"result": "D", "score": "0-0"},
            {"result": "W", "score": "3-0"},
            {"result": "L", "score": "1-2"},
            {"result": "W", "score": "2-0"}
        ]

        form = team.calculate_form()
        assert form["played"] == 5
        assert form["won"] == 3
        assert form["drawn"] == 1
        assert form["lost"] == 1
        assert form["points"] == 10

    def test_team_statistics(self):
        """测试球队统计"""
        team = Team(
            id=1,
            name="Team A",
            goals_scored=45,
            goals_conceded=20,
            matches_played=25
        )

        stats = team.get_statistics()
        assert stats["goals_scored"] == 45
        assert stats["goals_conceded"] == 20
        assert stats["goal_difference"] == 25
        assert stats["goals_per_match"] == 1.8

    def test_team_validation(self):
        """测试球队验证"""
        # 测试无效的代码
        with pytest.raises(ValueError):
            Team(
                id=1,
                name="Team A",
                code="",  # 空代码
                league="Premier League"
            )

        # 测试过长的代码
        with pytest.raises(ValueError):
            Team(
                id=1,
                name="Team A",
                code="TOOLONGCODE",  # 超过3个字符
                league="Premier League"
            )

    def test_team_form_string(self):
        """测试球队状态字符串"""
        team = Team(id=1, name="Team A")
        team.recent_form = TeamForm.WDLWD

        assert str(team.recent_form) == "WDLWD"
        assert len(team.recent_form) == 5

    def test_team_home_advantage(self):
        """测试主场优势"""
        team = Team(
            id=1,
            name="Team A",
            home_matches_played=15,
            home_matches_won=10,
            away_matches_played=15,
            away_matches_won=5
        )

        home_advantage = team.calculate_home_advantage()
        assert home_advantage > 0  # 主场胜率应该更高

    def test_team_head_to_head(self):
        """测试交锋记录"""
        team_a = Team(id=1, name="Team A")
        team_b = Team(id=2, name="Team B")

        # 设置交锋记录
        team_a.head_to_head = {
            team_b.id: {
                "played": 10,
                "won": 6,
                "drawn": 2,
                "lost": 2,
                "goals_for": 20,
                "goals_against": 10
            }
        }

        h2h = team_a.get_head_to_head(team_b.id)
        assert h2h["played"] == 10
        assert h2h["win_rate"] == 0.6
        assert h2h["goal_difference"] == 10
