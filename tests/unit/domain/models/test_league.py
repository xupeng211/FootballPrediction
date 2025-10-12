from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.core.exceptions import DomainError
from src.domain.models.league import (
    League,
    LeagueSeason,
    LeagueSettings,
    LeagueStatus,
    LeagueType,
)


@pytest.fixture
def league() -> League:
    return League(name="Premier League", country="England", level=1)


class TestLeagueSeason:
    def test_should_validate_basic_constraints(self):
        start = datetime(2024, 8, 1)
        end = datetime(2025, 5, 31)
        season = LeagueSeason(
            season="2024-2025",
            start_date=start,
            end_date=end,
            total_rounds=38,
            current_round=10,
        )

        assert season.progress == pytest.approx(10 / 38)
        assert season.is_active is False

    def test_should_raise_when_dates_invalid(self):
        with pytest.raises(DomainError):
            LeagueSeason(
                season="2024",
                start_date=datetime(2024, 8, 1),
                end_date=datetime(2024, 7, 31),
            )

    def test_should_transition_status_through_lifecycle(self):
        season = LeagueSeason(
            season="2024",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            total_rounds=3,
        )

        season.start_season()
        assert season.is_active is True
        assert season.current_round == 1

        season.advance_round()
        assert season.current_round == 2
        assert season.status == LeagueStatus.ACTIVE

        season.advance_round()
        assert season.current_round == 3
        assert season.status == LeagueStatus.ACTIVE

        season.advance_round()
        assert season.status == LeagueStatus.COMPLETED
        assert season.current_round == 3

    def test_should_complete_season_early(self):
        """测试：提前结束赛季应该设置为已完成状态"""
        # Given - 进行中的赛季，还有很多轮次未完成
        season = LeagueSeason(
            season="2024",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            total_rounds=38,
            current_round=20,
            status=LeagueStatus.ACTIVE
        )
        
        # When - 提前结束赛季
        season.complete_season()
        
        # Then - 状态变为已完成，当前轮次设为总轮次
        assert season.status == LeagueStatus.COMPLETED
        assert season.current_round == 38

    def test_should_not_start_season_if_not_upcoming(self):
        """测试：只有未开始的赛季才能启动（业务规则）"""
        # Given - 已经进行中的赛季
        season = LeagueSeason(
            season="2024",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            status=LeagueStatus.ACTIVE
        )
        
        # When/Then - 尝试启动应该失败
        with pytest.raises(DomainError, match="无法开始"):
            season.start_season()

    def test_should_not_advance_round_if_not_active(self):
        """测试：只有进行中的赛季才能推进轮次（业务规则）"""
        # Given - 未开始的赛季
        season = LeagueSeason(
            season="2024",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )
        
        # When/Then - 尝试推进应该失败
        with pytest.raises(DomainError, match="只有进行中的赛季才能推进轮次"):
            season.advance_round()

    def test_should_validate_season_name_not_empty(self):
        """测试：赛季名称不能为空（业务约束）"""
        # When/Then
        with pytest.raises(DomainError, match="赛季名称不能为空"):
            LeagueSeason(
                season="",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31)
            )

    def test_should_validate_total_rounds_positive(self):
        """测试：总轮次必须大于0（业务约束）"""
        # When/Then
        with pytest.raises(DomainError, match="总轮次必须大于0"):
            LeagueSeason(
                season="2024",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                total_rounds=0
            )

    def test_should_validate_current_round_range(self):
        """测试：当前轮次必须在有效范围内（业务约束）"""
        # When/Then - 负数轮次
        with pytest.raises(DomainError, match="当前轮次无效"):
            LeagueSeason(
                season="2024",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                total_rounds=38,
                current_round=-1
            )
        
        # When/Then - 超过总轮次
        with pytest.raises(DomainError, match="当前轮次无效"):
            LeagueSeason(
                season="2024",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                total_rounds=38,
                current_round=39
            )


class TestLeagueSettings:
    def test_should_calculate_points(self):
        settings = LeagueSettings(points_for_win=3, points_for_draw=1, points_for_loss=0)
        assert settings.calculate_points(10, 5, 3) == 10 * 3 + 5 * 1

    def test_should_reject_invalid_configuration(self):
        with pytest.raises(DomainError):
            LeagueSettings(points_for_win=-1)

    def test_should_validate_points_hierarchy(self):
        """测试：积分规则必须符合层级关系（业务规则）"""
        # When/Then - 胜场积分少于平场积分
        with pytest.raises(DomainError, match="胜场积分不能少于平场积分"):
            LeagueSettings(points_for_win=1, points_for_draw=2, points_for_loss=0)
        
        # When/Then - 平场积分少于负场积分
        with pytest.raises(DomainError, match="平场积分不能少于负场积分"):
            LeagueSettings(points_for_win=3, points_for_draw=0, points_for_loss=1)

    def test_should_validate_promotion_relegation_places(self):
        """测试：升降级名额不能为负数（业务约束）"""
        # When/Then - 升级名额为负
        with pytest.raises(DomainError, match="升级降级名额不能为负数"):
            LeagueSettings(promotion_places=-1)
        
        # When/Then - 降级名额为负
        with pytest.raises(DomainError, match="升级降级名额不能为负数"):
            LeagueSettings(relegation_places=-1)

    def test_should_validate_match_settings(self):
        """测试：比赛相关设置验证"""
        # When/Then - 比赛时长必须大于0
        with pytest.raises(DomainError, match="比赛时长必须大于0"):
            LeagueSettings(match_duration=0)
        
        # When/Then - 中场休息时长不能为负
        with pytest.raises(DomainError, match="中场休息时长不能为负数"):
            LeagueSettings(halftime_duration=-5)

    def test_should_validate_max_foreign_players(self):
        """测试：外援名额不能为负数（业务约束）"""
        # When/Then
        with pytest.raises(DomainError, match="外援名额不能为负数"):
            LeagueSettings(max_foreign_players=-1)

    def test_should_create_settings_with_custom_values(self):
        """测试：可以创建自定义规则的联赛设置"""
        # Given/When - 创建杯赛规则（需要加时和点球）
        settings = LeagueSettings(
            points_for_win=3,
            points_for_draw=1,
            points_for_loss=0,
            extra_time=True,
            penalty_shootout=True,
            match_duration=120  # 含加时
        )
        
        # Then - 验证所有设置
        assert settings.extra_time is True
        assert settings.penalty_shootout is True
        assert settings.match_duration == 120


class TestLeague:
    def test_should_initialize_with_defaults(self, league):
        assert league.settings is not None
        assert league.is_active is True
        assert league.prestige == "顶级联赛"

    def test_should_require_name(self):
        with pytest.raises(DomainError):
            League(name="")

    def test_should_start_new_season(self, league):
        start = datetime.utcnow()
        end = start + timedelta(days=100)

        season = league.start_new_season("2024-2025", start, end)

        assert league.current_season is season
        assert season.total_rounds == league.settings.match_duration  # 默认沿用设置
        assert league.current_progress == 0.0

    def test_should_not_start_new_season_when_active(self, league):
        start = datetime.utcnow()
        end = start + timedelta(days=100)

        season = league.start_new_season("2024", start, end)
        season.start_season()

        with pytest.raises(DomainError):
            league.start_new_season("2025", start + timedelta(days=365), end + timedelta(days=365))

    def test_should_update_settings_and_calculate_revenue(self, league):
        league.update_settings(points_for_win=4, max_foreign_players=7)
        assert league.settings.points_for_win == 4
        assert league.settings.max_foreign_players == 7

        revenue = league.calculate_revenue_sharing(position=1, total_teams=20)
        assert revenue == Decimal("1000000") + Decimal("1900000")

    def test_should_raise_for_invalid_revenue_position(self, league):
        with pytest.raises(DomainError):
            league.calculate_revenue_sharing(position=0, total_teams=20)

    def test_should_serialize_and_deserialize(self, league):
        start = datetime(2024, 8, 1)
        end = datetime(2025, 5, 31)
        league.start_new_season("2024-2025", start, end)

        payload = league.to_dict()
        restored = League.from_dict(payload)

        assert restored.name == league.name
        assert restored.current_season is not None
        assert restored.settings is not None
        assert restored.current_season.season == "2024-2025"

    def test_should_validate_team_registration(self, league):
        assert league.can_team_register(team_level=2) is True
        assert league.can_team_register(team_level=6) is False

    def test_should_update_league_info(self, league):
        """测试：更新联赛信息应该正确修改字段并更新时间戳"""
        # Given - 记录原始更新时间
        original_updated_at = league.updated_at
        
        # When - 更新联赛信息
        league.update_info(
            name="English Premier League",
            short_name="EPL",
            website="https://www.premierleague.com",
            logo_url="https://example.com/logo.png"
        )
        
        # Then - 验证所有字段已更新
        assert league.name == "English Premier League"
        assert league.short_name == "EPL"
        assert league.website == "https://www.premierleague.com"
        assert league.logo_url == "https://example.com/logo.png"
        assert league.updated_at > original_updated_at

    def test_should_activate_and_deactivate_league(self, league):
        """测试：联赛激活/停用功能应该正确切换状态"""
        # Given - 联赛初始是激活的
        assert league.is_active is True
        
        # When - 停用联赛
        league.deactivate()
        
        # Then - 验证状态已改变
        assert league.is_active is False
        
        # When - 重新激活联赛
        league.activate()
        
        # Then - 验证状态恢复
        assert league.is_active is True

    def test_should_promote_league_to_higher_level(self):
        """测试：联赛升级应该降低级别数字（数字越小级别越高）"""
        # Given - 二级联赛
        league = League(name="Championship", country="England", level=2)
        
        # When - 升级到下一级别
        league.promote_to_next_level()
        
        # Then - 级别数字减1
        assert league.level == 1

    def test_should_not_promote_top_level_league(self):
        """测试：顶级联赛不能再升级（业务规则）"""
        # Given - 顶级联赛
        league = League(name="Premier League", country="England", level=1)
        
        # When/Then - 尝试升级应该抛出业务异常
        with pytest.raises(DomainError, match="已经是最高级别联赛"):
            league.promote_to_next_level()

    def test_should_relegate_league_to_lower_level(self, league):
        """测试：联赛降级应该增加级别数字"""
        # Given - 顶级联赛
        assert league.level == 1
        
        # When - 降级
        league.relegate_to_lower_level()
        
        # Then - 级别数字加1
        assert league.level == 2

    def test_should_validate_league_code_length(self):
        """测试：联赛代码必须在2-5个字符之间（业务约束）"""
        # When/Then - 代码太短应该失败
        with pytest.raises(DomainError, match="联赛代码长度"):
            League(name="Test League", code="X")
        
        # When/Then - 代码太长应该失败
        with pytest.raises(DomainError, match="联赛代码长度"):
            League(name="Test League", code="TOOLONG")
        
        # When/Then - 合法代码应该成功
        league = League(name="Test League", code="EPL")
        assert league.code == "EPL"

    def test_should_validate_short_name_length(self):
        """测试：简称不能超过20个字符（业务约束）"""
        # When/Then - 简称太长应该失败
        with pytest.raises(DomainError, match="简称不能超过20个字符"):
            League(name="Test", short_name="A" * 21)

    def test_should_validate_founded_year(self):
        """测试：成立年份必须在合理范围内（1800-今年）"""
        current_year = datetime.utcnow().year
        
        # When/Then - 年份太早应该失败
        with pytest.raises(DomainError, match="成立年份无效"):
            League(name="Test", founded_year=1799)
        
        # When/Then - 未来年份应该失败
        with pytest.raises(DomainError, match="成立年份无效"):
            League(name="Test", founded_year=current_year + 1)
        
        # When/Then - 合法年份应该成功
        league = League(name="Test", founded_year=1992)
        assert league.founded_year == 1992

    def test_should_calculate_league_age(self):
        """测试：联赛年龄计算（基于成立年份）"""
        # Given - 1992年成立的联赛
        league = League(name="Premier League", founded_year=1992)
        
        # When - 计算年龄
        age = league.age
        
        # Then - 年龄 = 当前年份 - 成立年份
        expected_age = datetime.utcnow().year - 1992
        assert age == expected_age

    def test_should_return_none_age_when_no_founded_year(self, league):
        """测试：没有成立年份时年龄返回None"""
        # Given - 联赛没有成立年份
        league.founded_year = None
        
        # When/Then
        assert league.age is None

    def test_should_return_display_name(self):
        """测试：显示名称优先使用简称，否则使用全称"""
        # Given - 有简称的联赛
        league = League(name="Premier League", short_name="EPL")
        assert league.display_name == "EPL"
        
        # Given - 没有简称的联赛
        league2 = League(name="Championship")
        assert league2.display_name == "Championship"

    def test_should_classify_prestige_by_level(self):
        """测试：根据联赛级别分类声望等级（业务规则）"""
        # 顶级联赛
        league1 = League(name="Test", level=1)
        assert league1.prestige == "顶级联赛"
        
        # 高级联赛
        league2 = League(name="Test", level=3)
        assert league2.prestige == "高级联赛"
        
        # 中级联赛
        league3 = League(name="Test", level=5)
        assert league3.prestige == "中级联赛"
        
        # 低级联赛
        league4 = League(name="Test", level=8)
        assert league4.prestige == "低级联赛"

    def test_should_identify_cup_and_international_competitions(self):
        """测试：识别杯赛和国际赛事类型"""
        # 杯赛
        cup = League(name="FA Cup", type=LeagueType.CUP)
        assert cup.is_cup_competition is True
        assert cup.is_international is False
        
        # 国际赛事
        intl = League(name="Champions League", type=LeagueType.INTERNATIONAL)
        assert intl.is_international is True
        assert intl.is_cup_competition is False

    def test_should_calculate_seasons_count(self):
        """测试：计算总赛季数量"""
        # Given - 1992年成立的联赛
        current_year = datetime.utcnow().year
        league = League(name="Test", founded_year=1992)
        
        # When
        count = league.get_seasons_count()
        
        # Then - 赛季数 = 当前年 - 成立年 + 1
        assert count == current_year - 1992 + 1

    def test_should_manage_domain_events(self, league):
        """测试：领域事件管理功能"""
        # Given - 创建模拟事件
        event1 = {"type": "league_created"}
        event2 = {"type": "season_started"}
        
        # When - 添加事件
        league._add_domain_event(event1)
        league._add_domain_event(event2)
        
        # Then - 可以获取事件
        events = league.get_domain_events()
        assert len(events) == 2
        assert events[0] == event1
        assert events[1] == event2
        
        # When - 清除事件
        league.clear_domain_events()
        
        # Then - 事件列表为空
        assert len(league.get_domain_events()) == 0
