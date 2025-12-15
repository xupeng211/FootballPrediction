"""
测试：FotMob 与 Titan007 比赛 ID 对齐服务

使用 pytest + rapidfuzz 实现模糊匹配逻辑测试。
"""

import pytest
from datetime import datetime
from typing import List

from src.schemas.titan import (
    FotMobMatchInfo,
    TitanMatchInfo,
    TitanTeamInfo,
)
from src.services.match_alignment_service import MatchAlignmentService


@pytest.fixture
def sample_fotmob_matches() -> List[FotMobMatchInfo]:
    """模拟 FotMob 比赛数据"""
    return [
        FotMobMatchInfo(
            fotmob_id="4193497",
            home_team="Man City",
            away_team="Liverpool",
            match_date=datetime(2024, 1, 1),
            competition_name="Premier League"
        ),
        FotMobMatchInfo(
            fotmob_id="4193498",
            home_team="Chelsea",
            away_team="Arsenal",
            match_date=datetime(2024, 1, 1),
            competition_name="Premier League"
        ),
        FotMobMatchInfo(
            fotmob_id="4193499",
            home_team="Man United",
            away_team="Tottenham",
            match_date=datetime(2024, 1, 2),
            competition_name="Premier League"
        ),
        FotMobMatchInfo(
            fotmob_id="4193500",
            home_team="PSG",
            away_team="Monaco",
            match_date=datetime(2024, 1, 1),
            competition_name="Ligue 1"
        ),
    ]


@pytest.fixture
def sample_titan_matches() -> List[TitanMatchInfo]:
    """模拟 Titan007 比赛数据（含轻微队名差异）"""
    return [
        TitanMatchInfo(
            match_id="2971465",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Manchester City", tid=1001),
            away_team=TitanTeamInfo(name="Liverpool", tid=1002),
            match_date="2024-01-01",
            match_time="16:00"
        ),
        TitanMatchInfo(
            match_id="2971466",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Chelsea", tid=1003),
            away_team=TitanTeamInfo(name="Arsenal", tid=1004),
            match_date="2024-01-01",
            match_time="18:30"
        ),
        TitanMatchInfo(
            match_id="2971467",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Manchester United", tid=1005),
            away_team=TitanTeamInfo(name="Tottenham Hotspur", tid=1006),
            match_date="2024-01-02",
            match_time="20:00"
        ),
        TitanMatchInfo(
            match_id="2971468",
            league_id="45",
            league_name="French Ligue 1",
            home_team=TitanTeamInfo(name="Paris Saint-Germain", tid=2001),
            away_team=TitanTeamInfo(name="AS Monaco", tid=2002),
            match_date="2024-01-01",
            match_time="21:00"
        ),
    ]


class TestMatchAlignmentService:
    """测试 ID 对齐服务"""

    @pytest.fixture
    def alignment_service(self):
        """创建对齐服务实例"""
        return MatchAlignmentService(min_confidence_score=80.0)

    def test_perfect_match_simple_names(self, alignment_service, sample_fotmob_matches, sample_titan_matches):
        """测试完全匹配（简单队名相同）"""
        # 测试 Liverpool 精准匹配
        result = alignment_service.align_match(
            sample_fotmob_matches[0],
            sample_titan_matches[0]
        )

        assert result is not None
        assert result.fotmob_id == "4193497"
        assert result.titan_id == "2971465"
        assert result.confidence_score == 100.0
        assert result.is_aligned is True

    def test_fuzzy_match_abbreviated_names(self, alignment_service):
        """测试模糊匹配（缩写 vs 全称）"""
        fotmob_match = FotMobMatchInfo(
            fotmob_id="4193497",
            home_team="Man City",
            away_team="Liverpool",
            match_date=datetime(2024, 1, 1)
        )

        titan_match = TitanMatchInfo(
            match_id="2971465",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Manchester City", tid=1001),
            away_team=TitanTeamInfo(name="Liverpool", tid=1002),
            match_date="2024-01-01",
            match_time="16:00"
        )

        result = alignment_service.align_match(fotmob_match, titan_match)

        assert result is not None
        assert result.home_team_fotmob == "Man City"
        assert result.home_team_titan == "Manchester City"
        assert result.confidence_score >= 80.0  # "Man City" vs "Manchester City" 分数应该很高
        assert result.is_aligned is True

    def test_fuzzy_match_full_names(self, alignment_service):
        """测试模糊匹配（全称 vs 全称）"""
        fotmob_match = FotMobMatchInfo(
            fotmob_id="4193499",
            home_team="Man United",
            away_team="Tottenham",
            match_date=datetime(2024, 1, 2)
        )

        titan_match = TitanMatchInfo(
            match_id="2971467",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Manchester United", tid=1005),
            away_team=TitanTeamInfo(name="Tottenham Hotspur", tid=1006),
            match_date="2024-01-02",
            match_time="20:00"
        )

        result = alignment_service.align_match(fotmob_match, titan_match)

        assert result is not None
        # "Man United" vs "Manchester United" 应该有较高匹配度
        assert result.confidence_score >= 80.0
        assert result.is_aligned is True

    def test_no_match_different_dates(self, alignment_service):
        """测试日期不匹配（应该无法匹配）"""
        fotmob_match = FotMobMatchInfo(
            fotmob_id="4193497",
            home_team="Man City",
            away_team="Liverpool",
            match_date=datetime(2024, 1, 1)
        )

        titan_match = TitanMatchInfo(
            match_id="2971465",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Manchester City", tid=1001),
            away_team=TitanTeamInfo(name="Liverpool", tid=1002),
            match_date="2024-01-05",  # 不同日期
            match_time="16:00"
        )

        result = alignment_service.align_match(fotmob_match, titan_match)

        assert result is None  # 日期不匹配，返回None

    def test_fuzzy_match_french_teams(self, alignment_service):
        """测试法甲比赛匹配（验证不同联赛匹配）"""
        fotmob_match = FotMobMatchInfo(
            fotmob_id="4193500",
            home_team="PSG",
            away_team="Monaco",
            match_date=datetime(2024, 1, 1),
        )

        titan_match = TitanMatchInfo(
            match_id="2971468",
            league_id="45",
            league_name="French Ligue 1",
            home_team=TitanTeamInfo(name="Paris Saint-Germain", tid=2001),
            away_team=TitanTeamInfo(name="AS Monaco", tid=2002),
            match_date="2024-01-01",
            match_time="21:00"
        )

        result = alignment_service.align_match(fotmob_match, titan_match)

        assert result is not None
        assert result.fotmob_id == "4193500"
        assert result.titan_id == "2971468"
        assert result.confidence_score >= 80.0
        assert "PSG" in result.home_team_fotmob or "Paris" in result.home_team_titan

    def test_confidence_score_calculation(self, alignment_service):
        """测试置信度分数计算"""
        fotmob_match = FotMobMatchInfo(
            fotmob_id="test123",
            home_team="Chelsea",
            away_team="Arsenal",
            match_date=datetime(2024, 1, 1)
        )

        titan_match = TitanMatchInfo(
            match_id="test456",
            league_id="34",
            league_name="English Premier League",
            home_team=TitanTeamInfo(name="Chelsea", tid=1),
            away_team=TitanTeamInfo(name="Arsenal", tid=2),
            match_date="2024-01-01",
            match_time="18:30"
        )

        result = alignment_service.align_match(fotmob_match, titan_match)

        assert result is not None
        # 完全相同的队名应该是100分
        assert result.confidence_score == 100.0
        assert result.is_aligned is True

    def test_batch_align_multiple_matches(self, alignment_service, sample_fotmob_matches, sample_titan_matches):
        """测试批量对齐多场比赛"""
        results = alignment_service.batch_align(
            fotmob_matches=sample_fotmob_matches,
            titan_matches=sample_titan_matches
        )

        assert len(results) >= 3  # 至少匹配3场

        # 验证所有结果置信度都大于等于阈值
        for result in results:
            assert result.confidence_score >= 80.0
            assert result.is_aligned is True
            assert len(result.fotmob_id) > 0
            assert len(result.titan_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
