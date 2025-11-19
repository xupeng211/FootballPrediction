from typing import Optional

#!/usr/bin/env python3
"""
Phase 5.0 - 最后冲刺15%企业级覆盖率
League领域模型comprehensive测试，业务逻辑全覆盖
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.domain.models.league import (
    DomainError,
    League,
    LeagueSeason,
    LeagueSettings,
    LeagueStatus,
    LeagueType,
)


class TestLeagueSettingsComprehensive:
    """LeagueSettings值对象全面测试"""

    def test_league_settings_default(self):
        """测试默认设置创建"""
        settings = LeagueSettings()
        assert settings.points_for_win == 3
        assert settings.points_for_draw == 1
        assert settings.points_for_loss == 0
        assert settings.promotion_places == 3
        assert settings.relegation_places == 3
        assert settings.max_foreign_players == 5
        assert settings.match_duration == 90
        assert settings.halftime_duration == 15
        assert not settings.extra_time
        assert not settings.penalty_shootout

    def test_league_settings_valid_creation(self):
        """测试有效设置创建"""
        settings = LeagueSettings(
            points_for_win=3,
            points_for_draw=1,
            points_for_loss=0,
            promotion_places=2,
            relegation_places=2,
            max_foreign_players=7,
            match_duration=90,
            halftime_duration=15,
        )

        assert settings.points_for_win == 3
        assert settings.points_for_draw == 1
        assert settings.points_for_loss == 0
        assert settings.promotion_places == 2
        assert settings.relegation_places == 2
        assert settings.max_foreign_players == 7

    def test_league_settings_negative_points_validation(self):
        """测试负积分验证"""
        with pytest.raises(DomainError, match="积分不能为负数"):
            LeagueSettings(points_for_win=-1)

        with pytest.raises(DomainError, match="积分不能为负数"):
            LeagueSettings(points_for_draw=-1)

        with pytest.raises(DomainError, match="积分不能为负数"):
            LeagueSettings(points_for_loss=-1)

    def test_league_settings_points_hierarchy_validation(self):
        """测试积分层次验证"""
        # 胜场积分少于平场
        with pytest.raises(DomainError, match="胜场积分不能少于平场积分"):
            LeagueSettings(points_for_win=2, points_for_draw=3)

        # 平场积分少于负场
        with pytest.raises(DomainError, match="平场积分不能少于负场积分"):
            LeagueSettings(points_for_draw=0, points_for_loss=1)

        # 正确层次：胜>平>负
        settings = LeagueSettings(
            points_for_win=3, points_for_draw=1, points_for_loss=0
        )
        assert (
            settings.points_for_win
            > settings.points_for_draw
            >= settings.points_for_loss
        )

    def test_league_settings_places_validation(self):
        """测试升降级名额验证"""
        with pytest.raises(DomainError, match="升级降级名额不能为负数"):
            LeagueSettings(promotion_places=-1)

        with pytest.raises(DomainError, match="升级降级名额不能为负数"):
            LeagueSettings(relegation_places=-3)

    def test_league_settings_foreign_players_validation(self):
        """测试外援名额验证"""
        with pytest.raises(DomainError, match="外援名额不能为负数"):
            LeagueSettings(max_foreign_players=-1)

    def test_league_settings_match_duration_validation(self):
        """测试比赛时长验证"""
        with pytest.raises(DomainError, match="比赛时长必须大于0"):
            LeagueSettings(match_duration=0)

        with pytest.raises(DomainError, match="比赛时长必须大于0"):
            LeagueSettings(match_duration=-90)

    def test_league_settings_halftime_duration_validation(self):
        """测试中场休息时长验证"""
        with pytest.raises(DomainError, match="中场休息时长不能为负数"):
            LeagueSettings(halftime_duration=-5)

    def test_league_settings_calculate_points(self):
        """测试积分计算"""
        settings = LeagueSettings()

        # 标准情况
        points = settings.calculate_points(wins=10, draws=5, losses=3)
        assert points == 35  # 10*3 + 5*1 + 3*0

        # 全胜
        points = settings.calculate_points(wins=5, draws=0, losses=0)
        assert points == 15

        # 全平
        points = settings.calculate_points(wins=0, draws=5, losses=0)
        assert points == 5

        # 全负
        points = settings.calculate_points(wins=0, draws=0, losses=5)
        assert points == 0

        # 自定义积分规则
        custom_settings = LeagueSettings(
            points_for_win=2, points_for_draw=1, points_for_loss=0
        )
        points = custom_settings.calculate_points(wins=5, draws=3, losses=2)
        assert points == 13  # 5*2 + 3*1 + 2*0

    def test_league_settings_string_representation(self):
        """测试字符串表示"""
        settings = LeagueSettings()
        assert "胜3 平1 负0" in str(settings)

        custom_settings = LeagueSettings(
            points_for_win=2, points_for_draw=0, points_for_loss=0
        )
        assert "胜2 平0 负0" in str(custom_settings)


class TestLeagueSeasonComprehensive:
    """LeagueSeason值对象全面测试"""

    def test_league_season_default_creation(self):
        """测试默认赛季创建"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=365)

        season = LeagueSeason(
            season="2023-2024", start_date=start_date, end_date=end_date
        )

        assert season.season == "2023-2024"
        assert season.start_date == start_date
        assert season.end_date == end_date
        assert season.status == LeagueStatus.UPCOMING
        assert season.total_rounds == 38
        assert season.current_round == 0
        assert season.progress == 0.0
        assert not season.is_active

    def test_league_season_custom_creation(self):
        """测试自定义赛季创建"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=200)

        season = LeagueSeason(
            season="2023",
            start_date=start_date,
            end_date=end_date,
            status=LeagueStatus.ACTIVE,
            total_rounds=30,
            current_round=15,
        )

        assert season.season == "2023"
        assert season.total_rounds == 30
        assert season.current_round == 15
        assert season.status == LeagueStatus.ACTIVE
        assert season.is_active
        assert season.progress == 0.5

    def test_league_season_empty_season_validation(self):
        """测试空赛季名称验证"""
        with pytest.raises(DomainError, match="赛季名称不能为空"):
            LeagueSeason(
                season="",
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=1),
            )

    def test_league_season_date_validation(self):
        """测试日期验证"""
        start_date = datetime.utcnow()
        end_date = start_date - timedelta(days=1)  # 结束日期早于开始日期

        with pytest.raises(DomainError, match="开始日期必须早于结束日期"):
            LeagueSeason(season="2023-2024", start_date=start_date, end_date=end_date)

        # 相同日期也不允许
        with pytest.raises(DomainError, match="开始日期必须早于结束日期"):
            LeagueSeason(season="2023-2024", start_date=start_date, end_date=start_date)

    def test_league_season_total_rounds_validation(self):
        """测试总轮次验证"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        with pytest.raises(DomainError, match="总轮次必须大于0"):
            LeagueSeason(
                season="2023-2024",
                start_date=start_date,
                end_date=end_date,
                total_rounds=0,
            )

        with pytest.raises(DomainError, match="总轮次必须大于0"):
            LeagueSeason(
                season="2023-2024",
                start_date=start_date,
                end_date=end_date,
                total_rounds=-10,
            )

    def test_league_season_current_round_validation(self):
        """测试当前轮次验证"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        # 负数轮次
        with pytest.raises(DomainError, match="当前轮次无效"):
            LeagueSeason(
                season="2023-2024",
                start_date=start_date,
                end_date=end_date,
                total_rounds=38,
                current_round=-1,
            )

        # 超过总轮次
        with pytest.raises(DomainError, match="当前轮次无效"):
            LeagueSeason(
                season="2023-2024",
                start_date=start_date,
                end_date=end_date,
                total_rounds=38,
                current_round=39,
            )

        # 正好等于总轮次（允许）
        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            total_rounds=38,
            current_round=38,
        )
        assert season.current_round == 38

    def test_league_season_progress_calculation(self):
        """测试进度计算"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        # 最小轮次（不能为0）
        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            total_rounds=1,
            current_round=0,
        )
        assert season.progress == 0.0

        # 进行一半
        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            total_rounds=38,
            current_round=19,
        )
        assert season.progress == 0.5

        # 全部完成
        season.current_round = 38
        assert season.progress == 1.0

        # 超过100%（应该限制为1.0）
        season.current_round = 40  # 不应该出现，但测试限制
        assert season.progress == 1.0

    def test_league_season_start_season(self):
        """测试开始赛季"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            status=LeagueStatus.UPCOMING,
        )

        season.start_season()
        assert season.status == LeagueStatus.ACTIVE
        assert season.current_round == 1

    def test_league_season_start_season_invalid_status(self):
        """测试无效状态开始赛季"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        # 已经进行中
        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            status=LeagueStatus.ACTIVE,
        )

        with pytest.raises(DomainError, match="赛季状态为 active，无法开始"):
            season.start_season()

        # 已完成
        season.status = LeagueStatus.COMPLETED
        with pytest.raises(DomainError, match="赛季状态为 completed，无法开始"):
            season.start_season()

    def test_league_season_advance_round(self):
        """测试推进轮次"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            status=LeagueStatus.ACTIVE,
            total_rounds=38,
            current_round=1,
        )

        # 正常推进
        season.advance_round()
        assert season.current_round == 2
        assert season.status == LeagueStatus.ACTIVE

        # 推进到最后一轮
        season.current_round = 37
        season.advance_round()
        assert season.current_round == 38
        assert season.status == LeagueStatus.ACTIVE

        # 推进到结束
        season.advance_round()
        assert season.current_round == 38  # 不应超过总轮次
        assert season.status == LeagueStatus.COMPLETED

    def test_league_season_advance_round_invalid_status(self):
        """测试无效状态推进轮次"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            status=LeagueStatus.UPCOMING,
        )

        with pytest.raises(DomainError, match="只有进行中的赛季才能推进轮次"):
            season.advance_round()

    def test_league_season_complete_season(self):
        """测试结束赛季"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=100)

        season = LeagueSeason(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            status=LeagueStatus.ACTIVE,
            total_rounds=38,
            current_round=35,  # 还没打完
        )

        season.complete_season()
        assert season.status == LeagueStatus.COMPLETED
        assert season.current_round == 38  # 应该设置为总轮次

    def test_league_season_string_representation(self):
        """测试字符串表示"""
        season = LeagueSeason(
            season="2023-2024",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=100),
            total_rounds=38,
            current_round=15,
        )

        result_str = str(season)
        assert "2023-2024" in result_str
        assert "15/38" in result_str
        assert "轮" in result_str


class TestLeagueDomainComprehensive:
    """League领域模型全面测试"""

    def test_league_creation_valid(self):
        """测试有效联赛创建"""
        league = League(
            name="英超联赛",
            short_name="英超",
            code="EPL",
            type=LeagueType.DOMESTIC_LEAGUE,
            country="英格兰",
            level=1,
            founded_year=1888,
            website="https://www.premierleague.com",
        )

        assert league.name == "英超联赛"
        assert league.short_name == "英超"
        assert league.code == "EPL"
        assert league.type == LeagueType.DOMESTIC_LEAGUE
        assert league.country == "英格兰"
        assert league.level == 1
        assert league.founded_year == 1888
        assert league.is_active
        assert league.settings is not None

    def test_league_creation_invalid_name(self):
        """测试无效联赛名称"""
        with pytest.raises(DomainError, match="联赛名称不能为空"):
            League(name="")

        with pytest.raises(DomainError, match="联赛名称不能为空"):
            League(name="   ")

    def test_league_creation_invalid_short_name(self):
        """测试无效简称"""
        with pytest.raises(DomainError, match="简称不能超过20个字符"):
            League(
                name="测试联赛",
                short_name="这是一个非常非常长的联赛简称超过了20个字符的限制",
            )

    def test_league_creation_invalid_code(self):
        """测试无效代码"""
        with pytest.raises(DomainError, match="联赛代码长度必须在2-5个字符之间"):
            League(name="测试联赛", code="E")  # 太短

        with pytest.raises(DomainError, match="联赛代码长度必须在2-5个字符之间"):
            League(name="测试联赛", code="PREMIER")  # 太长

    def test_league_creation_invalid_level(self):
        """测试无效级别"""
        with pytest.raises(DomainError, match="联赛级别必须大于0"):
            League(name="测试联赛", level=0)

        with pytest.raises(DomainError, match="联赛级别必须大于0"):
            League(name="测试联赛", level=-1)

    def test_league_creation_invalid_founded_year(self):
        """测试无效成立年份"""
        with pytest.raises(DomainError, match="成立年份无效"):
            League(name="测试联赛", founded_year=1799)

        current_year = datetime.utcnow().year + 1
        with pytest.raises(DomainError, match="成立年份无效"):
            League(name="测试联赛", founded_year=current_year)

    def test_league_different_types(self):
        """测试不同联赛类型"""
        # 国内联赛
        league1 = League(name="中超", type=LeagueType.DOMESTIC_LEAGUE)
        assert league1.type == LeagueType.DOMESTIC_LEAGUE

        # 杯赛
        league2 = League(name="足总杯", type=LeagueType.CUP)
        assert league2.type == LeagueType.CUP

        # 国际赛事
        league3 = League(name="世界杯", type=LeagueType.INTERNATIONAL)
        assert league3.type == LeagueType.INTERNATIONAL

        # 友谊赛
        league4 = League(name="国际友谊赛", type=LeagueType.FRIENDLY)
        assert league4.type == LeagueType.FRIENDLY

    def test_league_start_new_season(self):
        """测试开始新赛季"""
        league = League(name="测试联赛")
        original_updated = league.updated_at

        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=300)

        season = league.start_new_season(
            season="2023-2024",
            start_date=start_date,
            end_date=end_date,
            total_rounds=38,
        )

        assert season.season == "2023-2024"
        assert season.start_date == start_date
        assert season.end_date == end_date
        assert season.total_rounds == 38
        assert season.status == LeagueStatus.UPCOMING
        assert league.current_season == season
        assert league.updated_at > original_updated

    def test_league_start_new_season_with_active_season(self):
        """测试有活跃赛季时开始新赛季"""
        league = League(name="测试联赛")

        # 先开始一个赛季
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=300)
        league.start_new_season("2023-2024", start_date, end_date)

        # 将赛季设为进行中
        league.current_season.start_season()

        # 尝试开始新赛季应该失败
        with pytest.raises(DomainError, match="当前赛季仍在进行中"):
            league.start_new_season("2024-2025", start_date, end_date)

    def test_league_update_info(self):
        """测试更新联赛信息"""
        league = League(name="测试联赛")
        original_updated = league.updated_at

        league.update_info(
            name="新名称",
            short_name="新简称",
            website="https://new-website.com",
            logo_url="https://new-logo.png",
        )

        assert league.name == "新名称"
        assert league.short_name == "新简称"
        assert league.website == "https://new-website.com"
        assert league.logo_url == "https://new-logo.png"
        assert league.updated_at > original_updated

    def test_league_update_settings(self):
        """测试更新联赛设置"""
        league = League(name="测试联赛")
        original_updated = league.updated_at

        league.update_settings(
            points_for_win=2,
            points_for_draw=1,
            points_for_loss=0,
            max_foreign_players=6,
        )

        assert league.settings.points_for_win == 2
        assert league.settings.points_for_draw == 1
        assert league.settings.points_for_loss == 0
        assert league.settings.max_foreign_players == 6
        assert league.updated_at > original_updated

    def test_league_activate_deactivate(self):
        """测试激活停用"""
        league = League(name="测试联赛")
        original_updated = league.updated_at

        assert league.is_active

        league.deactivate()
        assert not league.is_active
        assert league.updated_at > original_updated

        league.activate()
        assert league.is_active
        assert league.updated_at > original_updated

    def test_league_promote_relegate_level(self):
        """测试升级降级"""
        league = League(name="测试联赛", level=3)
        original_updated = league.updated_at

        # 升级
        league.promote_to_next_level()
        assert league.level == 2
        assert league.updated_at > original_updated

        # 再次升级
        original_updated = league.updated_at
        league.promote_to_next_level()
        assert league.level == 1
        assert league.updated_at > original_updated

        # 尝试从顶级升级应该失败
        with pytest.raises(DomainError, match="已经是最高级别联赛"):
            league.promote_to_next_level()

        # 降级
        original_updated = league.updated_at
        league.relegate_to_lower_level()
        assert league.level == 2
        assert league.updated_at > original_updated

    def test_league_calculate_revenue_sharing(self):
        """测试收入分成计算"""
        league = League(name="测试联赛")

        # 冠军
        revenue = league.calculate_revenue_sharing(1, 20)
        assert revenue > Decimal("1000000")  # 基础分成

        # 中游
        revenue = league.calculate_revenue_sharing(10, 20)
        assert revenue > Decimal("1000000")

        # 倒数第一
        revenue = league.calculate_revenue_sharing(20, 20)
        assert revenue == Decimal("1000000")  # 只有基础分成

    def test_league_calculate_revenue_sharing_invalid_position(self):
        """测试无效排名的分成计算"""
        league = League(name="测试联赛")

        with pytest.raises(DomainError, match="排名无效"):
            league.calculate_revenue_sharing(0, 20)

        with pytest.raises(DomainError, match="排名无效"):
            league.calculate_revenue_sharing(21, 20)

        with pytest.raises(DomainError, match="排名无效"):
            league.calculate_revenue_sharing(-5, 20)

    def test_league_display_name(self):
        """测试显示名称"""
        league = League(name="英格兰足球超级联赛", short_name="英超")
        assert league.display_name == "英超"

        league = League(name="只有名称的联赛")
        assert league.display_name == "只有名称的联赛"

    def test_league_age(self):
        """测试联赛年龄"""
        current_year = datetime.utcnow().year

        league = League(name="测试联赛")
        assert league.age is None

        league = League(name="测试联赛", founded_year=1992)
        assert league.age == current_year - 1992

        league = League(name="测试联赛", founded_year=1888)
        assert league.age == current_year - 1888

    def test_league_prestige(self):
        """测试声望等级"""
        # 顶级联赛
        league = League(name="顶级联赛", level=1)
        assert league.prestige == "顶级联赛"

        # 高级联赛
        league = League(name="高级联赛", level=2)
        assert league.prestige == "高级联赛"

        league = League(name="高级联赛", level=3)
        assert league.prestige == "高级联赛"

        # 中级联赛
        league = League(name="中级联赛", level=4)
        assert league.prestige == "中级联赛"

        league = League(name="中级联赛", level=5)
        assert league.prestige == "中级联赛"

        # 低级联赛
        league = League(name="低级联赛", level=6)
        assert league.prestige == "低级联赛"

        league = League(name="低级联赛", level=10)
        assert league.prestige == "低级联赛"

    def test_league_current_progress(self):
        """测试当前赛季进度"""
        league = League(name="测试联赛")

        # 无赛季
        assert league.current_progress == 0.0

        # 添加赛季
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=300)
        league.start_new_season("2023-2024", start_date, end_date)

        # 默认进度0
        assert league.current_progress == 0.0

        # 设置进行中的赛季
        league.current_season.start_season()
        league.current_season.current_round = 19
        assert league.current_progress == 19 / 90  # 19轮/90轮 ≈ 0.211

    def test_league_type_properties(self):
        """测试类型属性"""
        # 杯赛
        cup = League(name="足总杯", type=LeagueType.CUP)
        assert cup.is_cup_competition
        assert not cup.is_international

        # 国际赛事
        international = League(name="世界杯", type=LeagueType.INTERNATIONAL)
        assert not international.is_cup_competition
        assert international.is_international

        # 国内联赛
        domestic = League(name="英超", type=LeagueType.DOMESTIC_LEAGUE)
        assert not domestic.is_cup_competition
        assert not domestic.is_international

        # 友谊赛
        friendly = League(name="友谊赛", type=LeagueType.FRIENDLY)
        assert not friendly.is_cup_competition
        assert not friendly.is_international

    def test_league_get_seasons_count(self):
        """测试获取赛季数量"""
        current_year = datetime.utcnow().year

        league = League(name="测试联赛")
        assert league.get_seasons_count() == 0

        league = League(name="测试联赛", founded_year=2000)
        expected_count = current_year - 2000 + 1
        assert league.get_seasons_count() == expected_count

        league = League(name="测试联赛", founded_year=1888)
        expected_count = current_year - 1888 + 1
        assert league.get_seasons_count() == expected_count

    def test_league_can_team_register(self):
        """测试球队注册条件"""
        league = League(name="测试联赛", level=2)

        # 同级别球队可以注册
        assert league.can_team_register(2)

        # 相差1级可以注册
        assert league.can_team_register(1)
        assert league.can_team_register(3)

        # 相差2级可以注册
        assert league.can_team_register(4)

        # 相差超过2级不能注册
        assert not league.can_team_register(5)
        # 0级球队可以注册到2级联赛 (abs(0-2)=2 <= 2)
        assert league.can_team_register(0)

    def test_league_domain_event_management(self):
        """测试领域事件管理"""
        league = League(name="测试联赛")

        # 初始无事件
        events = league.get_domain_events()
        assert len(events) == 0

        # 添加事件（通过私有方法模拟）
        league._add_domain_event({"type": "test_event", "data": "test"})
        events = league.get_domain_events()
        assert len(events) == 1

        # 清除事件
        league.clear_domain_events()
        events = league.get_domain_events()
        assert len(events) == 0

    def test_league_to_dict_serialization(self):
        """测试字典序列化"""
        league = League(
            id=1,
            name="英超联赛",
            short_name="英超",
            code="EPL",
            type=LeagueType.DOMESTIC_LEAGUE,
            country="英格兰",
            level=1,
            founded_year=1888,
            website="https://www.premierleague.com",
        )

        # 添加赛季
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=300)
        season = league.start_new_season("2023-2024", start_date, end_date, 38)
        season.start_season()
        season.current_round = 19

        data = league.to_dict()

        assert data["id"] == 1
        assert data["name"] == "英超联赛"
        assert data["type"] == "domestic_league"
        assert data["country"] == "英格兰"
        assert data["level"] == 1
        assert data["prestige"] == "顶级联赛"
        assert data["current_season"]["season"] == "2023-2024"
        assert data["current_season"]["status"] == "active"
        assert data["current_season"]["current_round"] == 19
        assert data["current_season"]["progress"] == 0.5
        assert data["settings"]["points_for_win"] == 3
        assert "created_at" in data
        assert "updated_at" in data

    def test_league_from_dict_deserialization(self):
        """测试字典反序列化"""
        data = {
            "id": 1,
            "name": "西甲联赛",
            "short_name": "西甲",
            "code": "LAL",
            "type": "domestic_league",
            "country": "西班牙",
            "level": 1,
            "is_active": True,
            "founded_year": 1929,
            "current_season": {
                "season": "2023-2024",
                "start_date": "2023-08-01T00:00:00",
                "end_date": "2024-05-31T00:00:00",
                "status": "active",
                "total_rounds": 38,
                "current_round": 25,
            },
            "settings": {
                "points_for_win": 3,
                "points_for_draw": 1,
                "points_for_loss": 0,
                "promotion_places": 4,
                "relegation_places": 3,
                "max_foreign_players": 5,
            },
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T15:00:00",
        }

        league = League.from_dict(data)

        assert league.id == 1
        assert league.name == "西甲联赛"
        assert league.code == "LAL"
        assert league.type == LeagueType.DOMESTIC_LEAGUE
        assert league.level == 1
        assert league.founded_year == 1929
        assert league.current_season.season == "2023-2024"
        assert league.current_season.status == LeagueStatus.ACTIVE
        assert league.current_season.current_round == 25
        assert league.settings.points_for_win == 3
        assert league.settings.promotion_places == 4

    def test_league_string_representation(self):
        """测试字符串表示"""
        league = League(name="英超联赛", country="英格兰", level=1)

        result_str = str(league)
        assert "英超联赛" in result_str
        assert "顶级联赛" in result_str
        assert "英格兰" in result_str

        # 低级别联赛
        league = League(name="英乙联赛", country="英格兰", level=4)
        result_str = str(league)
        assert "英乙联赛" in result_str
        assert "中级联赛" in result_str

    def test_league_complete_lifecycle(self):
        """测试完整的联赛生命周期"""
        # 创建联赛
        league = League(
            name="新兴联赛",
            short_name="新联",
            code="NWL",
            type=LeagueType.DOMESTIC_LEAGUE,
            country="中国",
            level=3,
            founded_year=2020,
            website="https://new-league.com",
        )

        # 初始状态
        assert league.is_active
        assert league.level == 3
        assert league.prestige == "高级联赛"  # 3级联赛是高级联赛
        assert league.current_progress == 0.0

        # 开始新赛季
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=200)
        season = league.start_new_season("2023-2024", start_date, end_date, 30)

        # 赛季进行
        season.start_season()
        for _round_num in range(1, 16):  # 进行一半
            season.advance_round()

        # 验证中期状态
        assert league.current_progress == 16 / 30  # 16轮/30轮 ≈ 0.533
        assert season.status == LeagueStatus.ACTIVE

        # 升级
        league.promote_to_next_level()
        assert league.level == 2
        assert league.prestige == "高级联赛"

        # 更新设置
        league.update_settings(max_foreign_players=7)
        assert league.settings.max_foreign_players == 7

        # 计算收入分成（假设获得第5名）
        revenue = league.calculate_revenue_sharing(5, 18)
        assert revenue > Decimal("1000000")

        # 赛季结束
        season.complete_season()
        assert season.status == LeagueStatus.COMPLETED
        assert league.current_progress == 1.0

        # 验证最终状态
        assert league.level == 2
        assert league.is_active
        assert league.current_season.status == LeagueStatus.COMPLETED
        assert league.prestige == "高级联赛"


def test_league_domain_comprehensive_suite():
    """联赛领域模型综合测试套件"""
    # 快速验证核心功能
    league = League(name="测试联赛", code="TEST")
    assert league.name == "测试联赛"
    assert league.code == "TEST"
    assert league.settings is not None
    assert league.level == 1
    assert league.prestige == "顶级联赛"

    # 测试赛季管理
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=100)
    season = league.start_new_season("2023-2024", start_date, end_date)
    assert season.season == "2023-2024"

    # 测试收入分成
    revenue = league.calculate_revenue_sharing(1, 10)
    assert revenue > Decimal("1000000")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
