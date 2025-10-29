from datetime import datetime
"""
Team领域模型全面边界条件测试
基于成功的边界条件测试模式，对核心业务模型进行深度测试覆盖
目标：将team模块覆盖率提升到90%+
"""

from unittest.mock import patch

import pytest

from src.core.exceptions import DomainError
from src.domain.models.team import Team, TeamForm, TeamStats, TeamType


@pytest.mark.unit
class TestTeamStats:
    """TeamStats值对象边界条件测试"""

    def test_team_stats_initialization_default(self) -> None:
        """✅ 成功用例：默认初始化"""
        stats = TeamStats()

        assert stats.matches_played == 0
        assert stats.wins == 0
        assert stats.draws == 0
        assert stats.losses == 0
        assert stats.goals_for == 0
        assert stats.goals_against == 0

    def test_team_stats_initialization_with_values(self) -> None:
        """✅ 成功用例：带值初始化"""
        stats = TeamStats(
            matches_played=10, wins=6, draws=2, losses=2, goals_for=15, goals_against=8
        )

        assert stats.matches_played == 10
        assert stats.wins == 6
        assert stats.draws == 2
        assert stats.losses == 2
        assert stats.goals_for == 15
        assert stats.goals_against == 8

    def test_team_stats_negative_values_validation(self) -> None:
        """✅ 边界用例：负数值验证"""
        with pytest.raises(DomainError, match="统计数据不能为负数"):
            TeamStats(matches_played=-1)

        with pytest.raises(DomainError, match="统计数据不能为负数"):
            TeamStats(wins=-1)

        with pytest.raises(DomainError, match="统计数据不能为负数"):
            TeamStats(draws=-1)

        with pytest.raises(DomainError, match="统计数据不能为负数"):
            TeamStats(losses=-1)

        with pytest.raises(DomainError, match="统计数据不能为负数"):
            TeamStats(goals_for=-1)

        with pytest.raises(DomainError, match="统计数据不能为负数"):
            TeamStats(goals_against=-1)

    def test_team_stats_matches_validation(self) -> None:
        """✅ 边界用例：比赛场次验证"""
        # 胜负平之和大于总场次
        with pytest.raises(DomainError, match="胜负平场次之和不能大于总比赛场次"):
            TeamStats(matches_played=5, wins=3, draws=3, losses=0)

        with pytest.raises(DomainError, match="胜负平场次之和不能大于总比赛场次"):
            TeamStats(matches_played=0, wins=1, draws=0, losses=0)

    def test_team_stats_valid_scenarios(self) -> None:
        """✅ 成功用例：有效场景"""
        # 完美匹配
        stats = TeamStats(matches_played=10, wins=5, draws=3, losses=2)
        assert stats.matches_played == 10
        assert stats.wins + stats.draws + stats.losses == 10

        # 全胜
        stats = TeamStats(matches_played=5, wins=5, draws=0, losses=0)
        assert stats.wins == 5

        # 全败
        stats = TeamStats(matches_played=5, wins=0, draws=0, losses=5)
        assert stats.losses == 5

        # 全平
        stats = TeamStats(matches_played=5, wins=0, draws=5, losses=0)
        assert stats.draws == 5

    def test_team_stats_points_property(self) -> None:
        """✅ 成功用例：积分计算"""
        # 标准积分规则：胜3平1负0
        stats = TeamStats(matches_played=10, wins=6, draws=2, losses=2)
        assert stats.points == 6 * 3 + 2 * 1  # 20分

        # 全胜
        stats = TeamStats(matches_played=5, wins=5, draws=0, losses=0)
        assert stats.points == 15

        # 全平
        stats = TeamStats(matches_played=5, wins=0, draws=5, losses=0)
        assert stats.points == 5

        # 全败
        stats = TeamStats(matches_played=5, wins=0, draws=0, losses=5)
        assert stats.points == 0

    def test_team_stats_goal_difference_property(self) -> None:
        """✅ 成功用例：净胜球计算"""
        stats = TeamStats(goals_for=15, goals_against=8)
        assert stats.goal_difference == 7

        # 负净胜球
        stats = TeamStats(goals_for=5, goals_against=10)
        assert stats.goal_difference == -5

        # 零净胜球
        stats = TeamStats(goals_for=10, goals_against=10)
        assert stats.goal_difference == 0

    def test_team_stats_win_rate_property(self) -> None:
        """✅ 成功用例：胜率计算"""
        # 无比赛场次
        stats = TeamStats(matches_played=0)
        assert stats.win_rate == 0.0

        # 50%胜率
        stats = TeamStats(matches_played=10, wins=5)
        assert stats.win_rate == 0.5

        # 100%胜率
        stats = TeamStats(matches_played=5, wins=5)
        assert stats.win_rate == 1.0

        # 0%胜率
        stats = TeamStats(matches_played=5, wins=0)
        assert stats.win_rate == 0.0

    def test_team_stats_update_method(self) -> None:
        """✅ 成功用例：更新统计"""
        stats = TeamStats()

        # 胜利
        stats.update("win", 2, 1)
        assert stats.matches_played == 1
        assert stats.wins == 1
        assert stats.goals_for == 2
        assert stats.goals_against == 1

        # 平局
        stats.update("draw", 1, 1)
        assert stats.matches_played == 2
        assert stats.draws == 1
        assert stats.goals_for == 3
        assert stats.goals_against == 2

        # 失利
        stats.update("loss", 0, 2)
        assert stats.matches_played == 3
        assert stats.losses == 1
        assert stats.goals_for == 3
        assert stats.goals_against == 4

    def test_team_stats_str_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        stats = TeamStats(matches_played=10, wins=6, draws=2, losses=2)
        str_repr = str(stats)
        assert "10场" in str_repr
        assert "6胜" in str_repr
        assert "2平" in str_repr
        assert "2负" in str_repr

    def test_team_stats_edge_cases(self) -> None:
        """✅ 边界用例：极端情况"""
        # 大数字
        stats = TeamStats(
            matches_played=1000,
            wins=800,
            draws=100,
            losses=100,
            goals_for=2000,
            goals_against=500,
        )
        assert stats.points == 800 * 3 + 100  # 2500分
        assert stats.goal_difference == 1500
        assert stats.win_rate == 0.8

        # 零进球
        stats = TeamStats(
            matches_played=5, wins=0, draws=0, losses=5, goals_for=0, goals_against=15
        )
        assert stats.goal_difference == -15


@pytest.mark.unit
class TestTeamForm:
    """TeamForm值对象边界条件测试"""

    def test_team_form_initialization_default(self) -> None:
        """✅ 成功用例：默认初始化"""
        form = TeamForm()

        assert form.last_matches == []
        assert form.current_streak == 0
        assert form.streak_type == ""

    def test_team_form_initialization_with_values(self) -> None:
        """✅ 成功用例：带值初始化"""
        form = TeamForm(last_matches=["W", "D", "L", "W"], current_streak=2, streak_type="win")

        assert form.last_matches == ["W", "D", "L", "W"]
        assert form.current_streak == 2
        assert form.streak_type == "win"

    def test_team_form_invalid_result_validation(self) -> None:
        """✅ 边界用例：无效结果验证"""
        with pytest.raises(DomainError, match="比赛结果只能是 W/D/L"):
            TeamForm(last_matches=["X"])

        with pytest.raises(DomainError, match="比赛结果只能是 W/D/L"):
            TeamForm(last_matches=["win"])  # 应该是"W"

        with pytest.raises(DomainError, match="比赛结果只能是 W/D/L"):
            TeamForm(last_matches=["1"])

    def test_team_form_max_matches_validation(self) -> None:
        """✅ 边界用例：最大比赛场次验证"""
        # 正好10场
        form = TeamForm(last_matches=["W"] * 10)
        assert len(form.last_matches) == 10

        # 超过10场
        with pytest.raises(DomainError, match="最近比赛记录最多保留10场"):
            TeamForm(last_matches=["W"] * 11)

    def test_team_form_add_result_method(self) -> None:
        """✅ 成功用例：添加结果"""
        form = TeamForm()

        # 添加胜利
        form.add_result("W")
        assert form.last_matches == ["W"]
        assert form.current_streak == 1
        assert form.streak_type == "win"

        # 添加平局
        form.add_result("D")
        assert form.last_matches == ["D", "W"]
        assert form.current_streak == 0
        assert form.streak_type == "draw"

        # 添加失利
        form.add_result("L")
        assert form.last_matches == ["L", "D", "W"]
        assert form.current_streak == 1
        assert form.streak_type == "loss"

    def test_team_form_add_result_invalid(self) -> None:
        """✅ 边界用例：添加无效结果"""
        form = TeamForm()

        with pytest.raises(DomainError, match="比赛结果只能是 W/D/L"):
            form.add_result("X")

        with pytest.raises(DomainError, match="比赛结果只能是 W/D/L"):
            form.add_result("win")

    def test_team_form_streak_calculation(self) -> None:
        """✅ 成功用例：连续记录计算"""
        form = TeamForm()

        # 连胜
        for _ in range(5):
            form.add_result("W")
        assert form.current_streak == 5
        assert form.streak_type == "win"

        # 平局中断连胜
        form.add_result("D")
        assert form.current_streak == 0
        assert form.streak_type == "draw"

        # 连败
        for _ in range(3):
            form.add_result("L")
        assert form.current_streak == 3
        assert form.streak_type == "loss"

        # 胜利中断连败
        form.add_result("W")
        assert form.current_streak == 1
        assert form.streak_type == "win"

    def test_team_form_recent_form_string(self) -> None:
        """✅ 成功用例：最近状态字符串"""
        form = TeamForm()

        # 添加结果
        for result in ["W", "D", "L", "W", "W"]:
            form.add_result(result)

        # 最近5场应该是 "WWLDW"（倒序）
        assert form.recent_form_string == "WWLDW"

        # 少于5场
        form = TeamForm()
        form.add_result("W")
        form.add_result("D")
        assert form.recent_form_string == "DW"

    def test_team_form_is_in_good_form(self) -> None:
        """✅ 成功用例：状态良好判断"""
        form = TeamForm()

        # 少于5场
        for result in ["W", "W", "W"]:
            form.add_result(result)
        assert not form.is_in_good_form

        # 5场但不够好
        form = TeamForm()
        for result in ["W", "W", "D", "L", "D"]:  # 2胜3平1负
            form.add_result(result)
        assert not form.is_in_good_form

        # 状态良好：5场不败且至少3胜
        form = TeamForm()
        for result in ["W", "W", "W", "D", "D"]:  # 3胜2平
            form.add_result(result)
        assert form.is_in_good_form

        # 全胜
        form = TeamForm()
        for result in ["W", "W", "W", "W", "W"]:
            form.add_result(result)
        assert form.is_in_good_form

    def test_team_form_str_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        form = TeamForm()
        form.add_result("W")
        form.add_result("W")

        str_repr = str(form)
        assert "状态:" in str_repr
        assert "WW" in str_repr
        assert "2W" in str_repr  # 连胜2场

    def test_team_form_edge_cases(self) -> None:
        """✅ 边界用例：极端情况"""
        # 混合连续记录
        form = TeamForm()
        results = ["W", "W", "D", "W", "L", "L", "L", "D", "W", "W"]
        for result in results:
            form.add_result(result)

        # 应该是当前连胜2场
        assert form.current_streak == 2
        assert form.streak_type == "win"

        # 空连续记录
        form = TeamForm()
        form._update_streak()  # 手动调用更新
        assert form.current_streak == 0
        assert form.streak_type == "none"


@pytest.mark.unit
class TestTeam:
    """Team领域模型边界条件测试"""

    def test_team_initialization_minimal(self) -> None:
        """✅ 成功用例：最小初始化"""
        team = Team(name="Test Team")

        assert team.name == "Test Team"
        assert team.id is None
        assert team.short_name is None
        assert team.code is None
        assert team.type == TeamType.CLUB
        assert team.country == ""
        assert team.founded_year is None
        assert team.is_active is True
        assert team.stats is not None
        assert team.form is not None

    def test_team_initialization_full(self) -> None:
        """✅ 成功用例：完整初始化"""
        team = Team(
            id=1,
            name="Test Club",
            short_name="TC",
            code="TST",
            type=TeamType.CLUB,
            country="Testland",
            founded_year=2000,
            stadium="Test Stadium",
            capacity=50000,
            website="http://test.com",
            logo_url="http://test.com/logo.png",
        )

        assert team.id == 1
        assert team.name == "Test Club"
        assert team.short_name == "TC"
        assert team.code == "TST"
        assert team.type == TeamType.CLUB
        assert team.country == "Testland"
        assert team.founded_year == 2000
        assert team.stadium == "Test Stadium"
        assert team.capacity == 50000
        assert team.website == "http://test.com"
        assert team.logo_url == "http://test.com/logo.png"

    def test_team_validation_empty_name(self) -> None:
        """✅ 边界用例：空名称验证"""
        with pytest.raises(DomainError, match="球队名称不能为空"):
            Team(name="")

        with pytest.raises(DomainError, match="球队名称不能为空"):
            Team(name="   ")

        with pytest.raises(DomainError, match="球队名称不能为空"):
            Team(name="\t\n")

    def test_team_validation_short_name(self) -> None:
        """✅ 边界用例：简称验证"""
        # 正常长度
        team = Team(name="Test", short_name="TST")
        assert team.short_name == "TST"

        # 最大长度
        team = Team(name="Test", short_name="A" * 10)
        assert len(team.short_name) == 10

        # 超过最大长度
        with pytest.raises(DomainError, match="简称不能超过10个字符"):
            Team(name="Test", short_name="A" * 11)

    def test_team_validation_code(self) -> None:
        """✅ 边界用例：代码验证"""
        # 正常3字母代码
        team = Team(name="Test", code="TST")
        assert team.code == "TST"

        # 非字母代码
        with pytest.raises(DomainError, match="球队代码必须是3个字母"):
            Team(name="Test", code="123")

        with pytest.raises(DomainError, match="球队代码必须是3个字母"):
            Team(name="Test", code="TS1")

        # 长度不对
        with pytest.raises(DomainError, match="球队代码必须是3个字母"):
            Team(name="Test", code="TS")

        with pytest.raises(DomainError, match="球队代码必须是3个字母"):
            Team(name="Test", code="TEST")

    def test_team_validation_founded_year(self) -> None:
        """✅ 边界用例：成立年份验证"""
        # 正常年份
        current_year = datetime.utcnow().year
        team = Team(name="Test", founded_year=2000)
        assert team.founded_year == 2000

        # 太早
        with pytest.raises(DomainError, match="成立年份无效"):
            Team(name="Test", founded_year=1799)

        # 太晚
        with pytest.raises(DomainError, match="成立年份无效"):
            Team(name="Test", founded_year=current_year + 1)

    def test_team_validation_capacity(self) -> None:
        """✅ 边界用例：容量验证"""
        # 正常容量
        team = Team(name="Test", capacity=50000)
        assert team.capacity == 50000

        # 零容量
        team = Team(name="Test", capacity=0)
        assert team.capacity == 0

        # 负容量
        with pytest.raises(DomainError, match="体育场容量不能为负数"):
            Team(name="Test", capacity=-1)

    def test_team_national_type(self) -> None:
        """✅ 成功用例：国家队类型"""
        team = Team(name="Test National", type=TeamType.NATIONAL, country="Testland")
        assert team.type == TeamType.NATIONAL
        assert team.name == "Test National"

    def test_team_update_info_method(self) -> None:
        """✅ 成功用例：更新信息"""
        team = Team(name="Original")
        original_updated = team.updated_at

        # 等待一小段时间确保时间戳不同
        import time

        time.sleep(0.01)

        team.update_info(
            name="Updated", short_name="UPD", stadium="Updated Stadium", capacity=60000
        )

        assert team.name == "Updated"
        assert team.short_name == "UPD"
        assert team.stadium == "Updated Stadium"
        assert team.capacity == 60000
        assert team.updated_at > original_updated

    def test_team_update_info_negative_capacity(self) -> None:
        """✅ 边界用例：更新信息负容量"""
        team = Team(name="Test")

        with pytest.raises(DomainError, match="体育场容量不能为负数"):
            team.update_info(capacity=-100)

    def test_team_add_match_result_method(self) -> None:
        """✅ 成功用例：添加比赛结果"""
        team = Team(name="Test")

        # 添加胜利
        team.add_match_result("win", 2, 1)
        assert team.stats.matches_played == 1
        assert team.stats.wins == 1
        assert team.stats.goals_for == 2
        assert team.stats.goals_against == 1
        assert team.form.last_matches == ["W"]

        # 添加平局
        team.add_match_result("draw", 1, 1)
        assert team.stats.matches_played == 2
        assert team.stats.draws == 1
        assert team.stats.goals_for == 3
        assert team.stats.goals_against == 2
        assert team.form.last_matches == ["D", "W"]

    def test_team_add_match_result_invalid(self) -> None:
        """✅ 边界用例：无效比赛结果"""
        team = Team(name="Test")

        with pytest.raises(DomainError, match="比赛结果必须是 win/draw/loss"):
            team.add_match_result("victory", 2, 1)

        with pytest.raises(DomainError, match="进球数不能为负数"):
            team.add_match_result("win", -1, 1)

        with pytest.raises(DomainError, match="进球数不能为负数"):
            team.add_match_result("win", 1, -1)

    def test_team_activation_methods(self) -> None:
        """✅ 成功用例：激活/停用方法"""
        team = Team(name="Test")
        original_updated = team.updated_at

        import time

        time.sleep(0.01)

        # 停用
        team.deactivate()
        assert not team.is_active
        assert team.updated_at > original_updated

        time.sleep(0.01)

        # 重新激活
        team.activate()
        assert team.is_active
        assert team.updated_at > original_updated

    def test_team_promotion_relegation(self) -> None:
        """✅ 成功用例：升级/降级"""
        team = Team(name="Test")
        original_updated = team.updated_at

        import time

        time.sleep(0.01)

        # 升级
        team.promote()
        assert team.updated_at > original_updated

        time.sleep(0.01)

        # 降级
        team.relegate()
        assert team.updated_at > original_updated

    def test_team_calculate_strength(self) -> None:
        """✅ 成功用例：计算实力"""
        team = Team(name="Test")

        # 无比赛记录，默认中等实力
        strength = team.calculate_strength()
        assert strength == 50.0

        # 添加一些比赛结果
        team.add_match_result("win", 3, 1)  # 胜
        team.add_match_result("win", 2, 0)  # 胜
        team.add_match_result("draw", 1, 1)  # 平

        strength = team.calculate_strength()
        assert 50.0 < strength < 100.0

        # 实力应该在0-100范围内
        assert 0 <= strength <= 100

    def test_team_display_properties(self) -> None:
        """✅ 成功用例：显示属性"""
        # 有简称
        team = Team(name="Long Name", short_name="LN")
        assert team.full_name == "Long Name"
        assert team.display_name == "LN"

        # 无简称
        team = Team(name="Simple Name")
        assert team.full_name == "Simple Name"
        assert team.display_name == "Simple Name"

    def test_team_age_property(self) -> None:
        """✅ 成功用例：球队年龄"""
        current_year = datetime.utcnow().year

        # 有成立年份
        team = Team(name="Test", founded_year=2000)
        assert team.age == current_year - 2000

        # 无成立年份
        team = Team(name="Test")
        assert team.age is None

    @patch("src.domain.models.team.datetime")
    def test_team_rank_property(self, mock_datetime):
        """✅ 成功用例：排名级别"""
        # 模拟当前时间
        mock_datetime.utcnow.return_value.year = 2023

        team = Team(name="Test")

        # 无比赛记录
        assert team.rank == "N/A"

        # 比赛记录不足
        for _ in range(5):
            team.add_match_result("win", 1, 0)
        assert team.rank == "N/A"

        # 补足比赛记录
        for _ in range(5):
            team.add_match_result("win", 1, 0)

        # 全胜应该顶级
        assert team.rank == "顶级"

        # 50%胜率应该中游
        team = Team(name="Test2")
        for _ in range(10):
            team.add_match_result("win" if _ < 5 else "loss", 1, 0)
        assert team.rank == "中游"

    def test_team_domain_events(self) -> None:
        """✅ 成功用例：领域事件管理"""
        team = Team(name="Test")

        # 初始没有事件
        assert len(team.get_domain_events()) == 0

        # 添加事件（通过私有方法）
        event = {"type": "test", "data": "test"}
        team._add_domain_event(event)

        assert len(team.get_domain_events()) == 1
        assert team.get_domain_events()[0] == event

        # 清除事件
        team.clear_domain_events()
        assert len(team.get_domain_events()) == 0

    def test_team_serialization(self) -> None:
        """✅ 成功用例：序列化"""
        team = Team(
            id=1,
            name="Test Team",
            short_name="TT",
            code="TST",
            type=TeamType.CLUB,
            country="Testland",
        )

        # 添加一些比赛记录
        team.add_match_result("win", 2, 1)
        team.add_match_result("draw", 1, 1)

        data = team.to_dict()

        assert data["id"] == 1
        assert data["name"] == "Test Team"
        assert data["short_name"] == "TT"
        assert data["code"] == "TST"
        assert data["type"] == "club"
        assert data["country"] == "Testland"
        assert data["stats"] is not None
        assert data["form"] is not None
        assert "strength" in data
        assert "rank" in data

    def test_team_deserialization(self) -> None:
        """✅ 成功用例：反序列化"""
        data = {
            "id": 1,
            "name": "Test Team",
            "short_name": "TT",
            "code": "TST",
            "type": "club",
            "country": "Testland",
            "stats": {
                "matches_played": 2,
                "wins": 1,
                "draws": 1,
                "losses": 0,
                "goals_for": 3,
                "goals_against": 2,
            },
            "form": {
                "last_matches": ["W", "D"],
                "current_streak": 0,
                "streak_type": "draw",
            },
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
        }

        team = Team.from_dict(data)

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.short_name == "TT"
        assert team.code == "TST"
        assert team.type == TeamType.CLUB
        assert team.country == "Testland"
        assert team.stats.matches_played == 2
        assert team.stats.wins == 1
        assert team.form.last_matches == ["W", "D"]

    def test_team_str_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        team = Team(name="Test Team", code="TST")
        team.add_match_result("win", 2, 1)
        team.add_match_result("win", 1, 0)

        str_repr = str(team)
        assert "Test Team" in str_repr
        assert "TST" in str_repr

    def test_team_edge_cases(self) -> None:
        """✅ 边界用例：极端情况"""
        # 极端容量
        team = Team(name="Big Stadium", capacity=1000000)
        assert team.capacity == 1000000

        # 极端年份
        team = Team(name="Old Team", founded_year=1800)
        assert team.founded_year == 1800

        # Unicode名称
        team = Team(name="测试球队", short_name="测试", code="TST")
        assert team.name == "测试球队"
        assert team.short_name == "测试"

        # 长名称
        long_name = "A" * 100
        team = Team(name=long_name)
        assert team.name == long_name

    def test_team_comprehensive_workflow(self) -> None:
        """✅ 集成用例：完整工作流"""
        # 创建球队
        team = Team(
            name="Test United",
            short_name="TU",
            code="TUT",
            type=TeamType.CLUB,
            country="Testland",
            founded_year=1990,
            stadium="Test Stadium",
            capacity=45000,
        )

        # 模拟一个赛季
        results = [
            ("win", 2, 1),
            ("draw", 1, 1),
            ("loss", 0, 2),
            ("win", 3, 0),
            ("win", 2, 1),
            ("draw", 1, 1),
            ("win", 1, 0),
            ("loss", 1, 3),
            ("win", 2, 0),
            ("draw", 0, 0),
            ("win", 3, 1),
            ("win", 2, 1),
        ]

        for result, goals_for, goals_against in results:
            team.add_match_result(result, goals_for, goals_against)

        # 验证统计
        stats = team.stats
        assert stats.matches_played == 12
        assert stats.wins == 7
        assert stats.draws == 3
        assert stats.losses == 2
        assert stats.points == 7 * 3 + 3 * 1  # 24分
        assert stats.goal_difference == 18 - 11  # 实际净胜球：7

        # 验证实力计算
        strength = team.calculate_strength()
        assert 50 < strength < 100

        # 验证排名
        assert team.rank in ["顶级", "强队", "中游"]

        # 验证序列化
        data = team.to_dict()
        restored_team = Team.from_dict(data)

        assert restored_team.name == team.name
        assert restored_team.stats.matches_played == team.stats.matches_played
        assert restored_team.form.last_matches == team.form.last_matches
