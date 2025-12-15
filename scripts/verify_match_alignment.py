"""
手动验证 MatchAlignmentService 功能

绕过复杂的 pytest 环境，直接运行核心逻辑验证。
"""

import sys

sys.path.insert(0, "/home/user/projects/FootballPrediction")

from datetime import datetime
from src.schemas.titan import FotMobMatchInfo, TitanMatchInfo
from src.services.match_alignment_service import MatchAlignmentService


def test_perfect_match():
    """测试完全匹配"""
    print("\n" + "=" * 60)
    print("测试 1: 完全匹配 (Liverpool vs Liverpool)")
    print("=" * 60)

    fotmob_match = FotMobMatchInfo(
        fotmob_id="4193497",
        home_team="Liverpool",
        away_team="Chelsea",
        match_date=datetime(2024, 1, 1),
    )

    titan_match = TitanMatchInfo.model_validate(
        {
            "matchid": "2971465",
            "leagueid": "34",
            "leaguename": "English Premier League",
            "hometeam": {"name": "Liverpool", "tid": 1001},
            "awayteam": {"name": "Chelsea", "tid": 1002},
            "matchdate": "2024-01-01",
            "matchtime": "16:00",
        }
    )

    service = MatchAlignmentService(min_confidence_score=80.0)
    result = service.align_match(fotmob_match, titan_match)

    assert result is not None, "应该匹配成功"
    assert result.confidence_score == 100.0, "置信度应该是100%"
    print(f"✅ 匹配成功！置信度: {result.confidence_score}%")
    print(f"   FotMob ID: {result.fotmob_id}")
    print(f"   Titan ID: {result.titan_id}")
    print(f"   主队: {result.home_team_fotmob} ↔ {result.home_team_titan}")
    print(f"   客队: {result.away_team_fotmob} ↔ {result.away_team_titan}")


def test_fuzzy_match_abbreviation():
    """测试模糊匹配（缩写 vs 全称）"""
    print("\n" + "=" * 60)
    print("测试 2: 模糊匹配 (Man City vs Manchester City)")
    print("=" * 60)

    fotmob_match = FotMobMatchInfo(
        fotmob_id="4193497",
        home_team="Man City",
        away_team="Liverpool",
        match_date=datetime(2024, 1, 1),
    )

    titan_match = TitanMatchInfo.model_validate(
        {
            "matchid": "2971465",
            "leagueid": "34",
            "leaguename": "English Premier League",
            "hometeam": {"name": "Manchester City", "tid": 1001},
            "awayteam": {"name": "Liverpool", "tid": 1002},
            "matchdate": "2024-01-01",
            "matchtime": "16:00",
        }
    )

    service = MatchAlignmentService(min_confidence_score=80.0)
    result = service.align_match(fotmob_match, titan_match)

    assert result is not None, "应该匹配成功"
    assert result.confidence_score >= 80.0, "置信度应该大于等于80%"
    print(f"✅ 模糊匹配成功！置信度: {result.confidence_score}%")
    print(f"   FotMob: '{result.home_team_fotmob}'")
    print(f"   Titan:  '{result.home_team_titan}'")
    print("   相似度足够高，判定为同一球队")


def test_date_mismatch():
    """测试日期不匹配"""
    print("\n" + "=" * 60)
    print("测试 3: 日期不匹配 (应该返回 None)")
    print("=" * 60)

    fotmob_match = FotMobMatchInfo(
        fotmob_id="4193497",
        home_team="Man City",
        away_team="Liverpool",
        match_date=datetime(2024, 1, 1),
    )

    titan_match = TitanMatchInfo.model_validate(
        {
            "matchid": "2971465",
            "leagueid": "34",
            "leaguename": "English Premier League",
            "hometeam": {"name": "Manchester City", "tid": 1001},
            "awayteam": {"name": "Liverpool", "tid": 1002},
            "matchdate": "2024-01-05",  # 不同日期
            "matchtime": "16:00",
        }
    )

    service = MatchAlignmentService(min_confidence_score=80.0)
    result = service.align_match(fotmob_match, titan_match)

    assert result is None, "日期不匹配，应该返回 None"
    print("✅ 正确拒绝：日期不匹配 (2024-01-01 vs 2024-01-05)")


def test_batch_alignment():
    """测试批量对齐"""
    print("\n" + "=" * 60)
    print("测试 4: 批量对齐多场比赛")
    print("=" * 60)

    fotmob_matches = [
        FotMobMatchInfo(
            fotmob_id="4193497",
            home_team="Man City",
            away_team="Liverpool",
            match_date=datetime(2024, 1, 1),
        ),
        FotMobMatchInfo(
            fotmob_id="4193498",
            home_team="Chelsea",
            away_team="Arsenal",
            match_date=datetime(2024, 1, 1),
        ),
        FotMobMatchInfo(
            fotmob_id="4193499",
            home_team="Man United",
            away_team="Tottenham",
            match_date=datetime(2024, 1, 2),
        ),
    ]

    titan_matches = [
        TitanMatchInfo.model_validate(
            {
                "matchid": "2971465",
                "leagueid": "34",
                "leaguename": "English Premier League",
                "hometeam": {"name": "Manchester City", "tid": 1001},
                "awayteam": {"name": "Liverpool", "tid": 1002},
                "matchdate": "2024-01-01",
                "matchtime": "16:00",
            }
        ),
        TitanMatchInfo.model_validate(
            {
                "matchid": "2971466",
                "leagueid": "34",
                "leaguename": "English Premier League",
                "hometeam": {"name": "Chelsea", "tid": 1003},
                "awayteam": {"name": "Arsenal", "tid": 1004},
                "matchdate": "2024-01-01",
                "matchtime": "18:30",
            }
        ),
        TitanMatchInfo.model_validate(
            {
                "matchid": "2971467",
                "leagueid": "34",
                "leaguename": "English Premier League",
                "hometeam": {"name": "Manchester United", "tid": 1005},
                "awayteam": {"name": "Tottenham Hotspur", "tid": 1006},
                "matchdate": "2024-01-02",
                "matchtime": "20:00",
            }
        ),
    ]

    service = MatchAlignmentService(min_confidence_score=80.0)
    results = service.batch_align(fotmob_matches, titan_matches)

    print(f"✅ 批量匹配成功：{len(results)} 场比赛对齐")

    for result in results:
        print(f"\n   📊 FotMob({result.fotmob_id}) ↔ Titan({result.titan_id})")
        print(f"      置信度: {result.confidence_score}%")
        print(f"      主队: {result.home_team_fotmob} ↔ {result.home_team_titan}")
        print(f"      客队: {result.away_team_fotmob} ↔ {result.away_team_titan}")

    # 验证统计信息
    stats = service.get_alignment_stats(results)
    print("\n   📈 统计信息:")
    print(f"      总匹配数: {stats['total_aligned']}")
    print(f"      平均置信度: {stats['average_confidence']}%")
    print(f"      高置信度(>90): {stats['high_confidence_count']}")
    print(f"      中置信度(80-90): {stats['medium_confidence_count']}")


def test_low_confidence_rejection():
    """测试低置信度拒绝"""
    print("\n" + "=" * 60)
    print("测试 5: 低置信度拒绝 (低于阈值)")
    print("=" * 60)

    fotmob_match = FotMobMatchInfo(
        fotmob_id="12345",
        home_team="Totally Different Team",
        away_team="Another Team",
        match_date=datetime(2024, 1, 1),
    )

    titan_match = TitanMatchInfo.model_validate(
        {
            "matchid": "67890",
            "leagueid": "34",
            "leaguename": "English Premier League",
            "hometeam": {"name": "Manchester City", "tid": 1001},
            "awayteam": {"name": "Liverpool", "tid": 1002},
            "matchdate": "2024-01-01",
            "matchtime": "16:00",
        }
    )

    service = MatchAlignmentService(min_confidence_score=80.0)
    result = service.align_match(fotmob_match, titan_match)

    assert result is None, "队名差异太大，置信度应该低于阈值"
    print("✅ 正确拒绝：队名差异太大，置信度低于 80%")


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("Titan007 比赛 ID 对齐服务 - 手动验证")
    print("🚀" * 30)

    try:
        test_perfect_match()
        test_fuzzy_match_abbreviation()
        test_date_mismatch()
        test_batch_alignment()
        test_low_confidence_rejection()

        print("\n" + "🎉" * 30)
        print("✅ 所有测试通过！")
        print("🎉" * 30 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 异常错误: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
