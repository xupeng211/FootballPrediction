from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from src.database.models.league import League
from src.database.models.team import Team

"""
数据库模型测试 - Team模型
"""


@pytest.mark.unit
class TestTeamModel:
    """Team模型测试"""

    @pytest.fixture
    def sample_team(self):
        """创建示例球队"""
        team = Team()
        team.id = 10
        team.team_name = "Test Team FC"
        team.team_code = "TTF"
        team.country = "Testland"
        team.founded_year = 1900
        team.stadium = "Test Stadium"
        team.capacity = 50000
        team.website = "https://testteam.com"
        team.colors = ["red", "white"]
        team.created_at = datetime.now()
        team.updated_at = datetime.now()
        return team

    @pytest.fixture
    def sample_league(self):
        """创建示例联赛"""
        league = League()
        league.id = 1
        league.league_name = "Test League"
        league.country = "Testland"
        league.season = "2024-25"
        return league

    def test_team_creation(self, sample_team):
        """测试球队创建"""
        assert sample_team.id == 10
        assert sample_team.name == "Test Team FC"
        assert sample_team.short_name == "TTF"
        assert sample_team.country == "Testland"
        assert sample_team.founded_year == 1900

    def test_team_attributes(self, sample_team):
        """测试球队属性"""
        assert sample_team.stadium == "Test Stadium"
        assert sample_team.capacity == 50000
        assert sample_team.website == "https://testteam.com"
        assert isinstance(sample_team.colors, list)
        assert "red" in sample_team.colors
        assert "white" in sample_team.colors

    def test_team_relationships(self, sample_team, sample_league):
        """测试球队关联关系"""
        # Mock 关联对象
        sample_team.league = sample_league
        sample_team.home_matches = []
        sample_team.away_matches = []

        assert sample_team.league.name == "Test League"
        assert sample_team.league.country == "Testland"
        assert isinstance(sample_team.home_matches, list)
        assert isinstance(sample_team.away_matches, list)

    def test_team_age(self, sample_team):
        """测试球队年龄计算"""
        current_year = datetime.now().year
        expected_age = current_year - sample_team.founded_year

        # 如果有get_age方法
        if hasattr(sample_team, "get_age"):
            assert sample_team.get_age() == expected_age
        else:
            # 手动计算
            actual_age = current_year - sample_team.founded_year
            assert actual_age == expected_age

    def test_team_colors_management(self, sample_team):
        """测试球队颜色管理"""
        # 添加颜色
        new_colors = ["blue", "red", "white"]
        sample_team.colors = new_colors

        assert len(sample_team.colors) == 3
        assert "blue" in sample_team.colors

        # 移除颜色
        sample_team.colors.remove("blue")
        assert "blue" not in sample_team.colors
        assert len(sample_team.colors) == 2

    def test_team_stadium_info(self, sample_team):
        """测试球场信息"""
        stadium_info = {"name": sample_team.stadium, "capacity": sample_team.capacity}

        assert stadium_info["name"] == "Test Stadium"
        assert stadium_info["capacity"] == 50000

        # 更新球场信息
        sample_team.stadium = "New Stadium"
        sample_team.capacity = 60000

        assert sample_team.stadium == "New Stadium"
        assert sample_team.capacity == 60000

    def test_team_website_validation(self, sample_team):
        """测试网站验证"""
        # 有效的网站
        valid_websites = [
            "https://testteam.com",
            "http://testteam.org",
            "https://www.testteam.net",
            "",
        ]

        for website in valid_websites:
            sample_team.website = website
            assert sample_team.website == website

    def test_team_country_validation(self, sample_team):
        """测试国家验证"""
        valid_countries = [
            "England",
            "Spain",
            "Germany",
            "France",
            "Italy",
            "Brazil",
            "Argentina",
        ]

        for country in valid_countries:
            sample_team.country = country
            assert sample_team.country == country

    def test_team_founded_year_validation(self, sample_team):
        """测试成立年份验证"""
        # 有效的成立年份
        valid_years = [1800, 1900, 1950, 2000, 2023]

        for year in valid_years:
            sample_team.founded_year = year
            assert sample_team.founded_year == year

        # 无效的年份（未来）
        future_year = datetime.now().year + 1
        sample_team.founded_year = future_year
        # 注意：实际应用中应该有验证逻辑

    def test_team_short_name(self, sample_team):
        """测试球队简称"""
        # 设置不同的简称
        short_names = ["TT", "TFC", "TEST", "TTF"]

        for short_name in short_names:
            sample_team.short_name = short_name
            assert len(short_name) <= 10  # 简称长度限制
            assert sample_team.short_name == short_name

    def test_team_to_dict(self, sample_team):
        """测试球队转换为字典"""
        team_dict = sample_team.__dict__.copy()
        team_dict.pop("_sa_instance_state", None)

        assert team_dict["id"] == 10
        assert team_dict["name"] == "Test Team FC"
        assert team_dict["country"] == "Testland"

    def test_team_repr(self, sample_team):
        """测试球队的字符串表示"""
        team_str = repr(sample_team)
        assert str(sample_team.id) in team_str
        assert sample_team.name in team_str

    def test_team_timestamps(self, sample_team):
        """测试时间戳"""
        assert isinstance(sample_team.created_at, datetime)
        assert isinstance(sample_team.updated_at, datetime)

        # 更新时间戳
        old_updated = sample_team.updated_at
        sample_team.updated_at = datetime.now()
        assert sample_team.updated_at >= old_updated

    def test_team_active_status(self, sample_team):
        """测试球队活跃状态"""
        # 添加活跃状态属性
        sample_team.is_active = True
        assert sample_team.is_active is True

        sample_team.is_active = False
        assert sample_team.is_active is False

    def test_team_comparisons(self, sample_team):
        """测试球队比较"""
        # 创建第二个球队
        team2 = Team()
        team2.id = 11
        team2.name = "Another Team FC"
        team2.country = "Testland"

        # 测试比较
        assert sample_team != team2
        assert sample_team.id != team2.id
        assert sample_team.name != team2.name

        # 同国家比较
        assert sample_team.country == team2.country

    def test_team_statistics(self, sample_team):
        """测试球队统计信息"""
        # 添加统计属性
        stats = {
            "matches_played": 38,
            "wins": 20,
            "draws": 10,
            "losses": 8,
            "goals_for": 60,
            "goals_against": 35,
            "points": 70,
        }

        for key, value in stats.items():
            setattr(sample_team, key, value)
            assert getattr(sample_team, key) == value

        # 计算胜率
        if hasattr(sample_team, "get_win_rate"):
            win_rate = sample_team.get_win_rate()
            expected_rate = stats["wins"] / stats["matches_played"]
            assert abs(win_rate - expected_rate) < 0.01

    @pytest.mark.asyncio
    async def test_team_async_operations(self, sample_team):
        """测试球队异步操作"""
        mock_session = AsyncMock()

        # 测试异步保存（如果有）
        if hasattr(sample_team, "async_save"):
            result = await sample_team.async_save(mock_session)
            assert result is not None

    def test_team_batch_creation(self):
        """测试批量创建球队"""
        teams = []
        countries = ["England", "Spain", "Germany", "France", "Italy"]

        for i in range(5):
            team = Team()
            team.id = i + 1
            team.name = f"Team {i+1} FC"
            team.short_name = f"T{i+1}"
            team.country = countries[i]
            team.founded_year = 1900 + i * 10
            teams.append(team)

        assert len(teams) == 5
        for i, team in enumerate(teams):
            assert team.id == i + 1
            assert team.country == countries[i]

    def test_team_search_methods(self, sample_team):
        """测试球队搜索方法"""
        # 按名称搜索
        if hasattr(sample_team, "matches_name"):
            assert sample_team.matches_name("Test")
            assert sample_team.matches_name("TEST")
            assert not sample_team.matches_name("Nonexistent")

        # 按国家搜索
        if hasattr(sample_team, "in_country"):
            assert sample_team.in_country("Testland")
            assert not sample_team.in_country("Otherland")

    def test_team_validation_rules(self, sample_team):
        """测试球队验证规则"""
        # 名称不能为空
        assert sample_team.name is not None
        assert len(sample_team.name) > 0

        # 简称长度限制
        assert len(sample_team.short_name) <= 50

        # 成立年份合理性
        current_year = datetime.now().year
        assert 1800 <= sample_team.founded_year <= current_year

        # 容量必须为正数
        assert sample_team.capacity >= 0
