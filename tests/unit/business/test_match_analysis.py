"""
比赛分析业务逻辑测试
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import pytest


class MatchResult(Enum):
    """比赛结果枚举"""

    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"


class MatchStatus(Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class Team:
    """球队类"""

    def __init__(self, id: int, name: str, league: str, rating: float = 1000.0):
        self.id = id
        self.name = name
        self.league = league
        self.rating = rating
        self.form = []  # 最近5场比赛结果
        self.goals_scored = 0
        self.goals_conceded = 0

    def update_form(self, result: MatchResult):
        """更新球队状态"""
        self.form.append(result)
        if len(self.form) > 5:
            self.form.pop(0)

    def get_form_points(self) -> int:
        """获取近期积分"""
        total = 0
        for result in self.form:
            if _result == MatchResult.HOME_WIN or _result == MatchResult.AWAY_WIN:
                total += 3  # Win
            elif _result == MatchResult.DRAW:
                total += 1  # Draw
        return total


class Match:
    """比赛类"""

    def __init__(
        self,
        id: int,
        home_team: Team,
        away_team: Team,
        match_date: datetime,
        league: str,
    ):
        self.id = id
        self.home_team = home_team
        self.away_team = away_team
        self.match_date = match_date
        self.league = league
        self.status = MatchStatus.SCHEDULED
        self.home_score = 0
        self.away_score = 0
        self.home_goals = []
        self.away_goals = []
        self.events = []

    def finish_match(self, home_score: int, away_score: int):
        """结束比赛"""
        self.home_score = home_score
        self.away_score = away_score
        self.status = MatchStatus.FINISHED

        # 更新球队数据
        self.home_team.goals_scored += home_score
        self.home_team.goals_conceded += away_score
        self.away_team.goals_scored += away_score
        self.away_team.goals_conceded += home_score

        # 更新球队状态
        if home_score > away_score:
            result_home = MatchResult.HOME_WIN
            result_away = MatchResult.AWAY_WIN
        elif away_score > home_score:
            result_home = MatchResult.AWAY_WIN
            result_away = MatchResult.HOME_WIN
        else:
            result_home = result_away = MatchResult.DRAW

        self.home_team.update_form(result_home)
        self.away_team.update_form(result_away)

    def get_result(self) -> Optional[MatchResult]:
        """获取比赛结果"""
        if self.status != MatchStatus.FINISHED:
            return None
        if self.home_score > self.away_score:
            return MatchResult.HOME_WIN
        elif self.away_score > self.home_score:
            return MatchResult.AWAY_WIN
        return MatchResult.DRAW

    def get_goal_difference(self) -> int:
        """获取净胜球"""
        return self.home_score - self.away_score

    def add_goal(self, team: str, minute: int, scorer: str):
        """添加进球"""
        goal_event = {"minute": minute, "scorer": scorer, "team": team}
        self.events.append(goal_event)

        if team == "home":
            self.home_goals.append(goal_event)
            self.home_score += 1
        else:
            self.away_goals.append(goal_event)
            self.away_score += 1


class MatchAnalyzer:
    """比赛分析器"""

    def __init__(self):
        self.matches: List[Match] = []

    def add_match(self, match: Match):
        """添加比赛"""
        self.matches.append(match)

    def get_team_form(self, team: Team, last_n: int = 5) -> List[MatchResult]:
        """获取球队近期状态"""
        team_matches = [
            m
            for m in self.matches
            if (m.home_team == team or m.away_team == team) and m.status == MatchStatus.FINISHED
        ]
        team_matches.sort(key=lambda x: x.match_date, reverse=True)

        results = []
        for match in team_matches[:last_n]:
            if match.home_team == team:
                if match.home_score > match.away_score:
                    results.append(MatchResult.HOME_WIN)
                elif match.home_score < match.away_score:
                    results.append(MatchResult.AWAY_WIN)
                else:
                    results.append(MatchResult.DRAW)
            else:
                if match.away_score > match.home_score:
                    results.append(MatchResult.AWAY_WIN)
                elif match.away_score < match.home_score:
                    results.append(MatchResult.HOME_WIN)
                else:
                    results.append(MatchResult.DRAW)

        return results

    def get_head_to_head(self, team1: Team, team2: Team) -> Dict[str, Any]:
        """获取两队历史交锋记录"""
        h2h_matches = [
            m
            for m in self.matches
            if (m.home_team == team1 and m.away_team == team2)
            or (m.home_team == team2 and m.away_team == team1)
            and m.status == MatchStatus.FINISHED
        ]

        team1_wins = 0
        team2_wins = 0
        draws = 0
        team1_goals = 0
        team2_goals = 0

        for match in h2h_matches:
            if match.home_team == team1:
                team1_goals += match.home_score
                team2_goals += match.away_score
                if match.home_score > match.away_score:
                    team1_wins += 1
                elif match.away_score > match.home_score:
                    team2_wins += 1
                else:
                    draws += 1
            else:
                team1_goals += match.away_score
                team2_goals += match.home_score
                if match.away_score > match.home_score:
                    team1_wins += 1
                elif match.home_score > match.away_score:
                    team2_wins += 1
                else:
                    draws += 1

        return {
            "matches": len(h2h_matches),
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "team1_goals": team1_goals,
            "team2_goals": team2_goals,
            "win_rate": team1_wins / len(h2h_matches) if h2h_matches else 0,
        }

    def predict_score(self, home_team: Team, away_team: Team) -> Dict[str, float]:
        """简单预测比分"""
        # 基于球队评分的简单预测
        rating_diff = home_team.rating - away_team.rating
        home_advantage = 50  # 主场优势

        # 基础期望进球
        home_base = 1.2 + (rating_diff + home_advantage) / 500
        away_base = 1.0 - (rating_diff - home_advantage) / 500

        # 确保非负
        home_expected = max(0.1, home_base)
        away_expected = max(0.1, away_base)

        return {
            "home_expected": round(home_expected, 2),
            "away_expected": round(away_expected, 2),
            "total_expected": round(home_expected + away_expected, 2),
        }

    def analyze_team_performance(self, team: Team, matches: int = 10) -> Dict[str, Any]:
        """分析球队表现"""
        team_matches = [
            m
            for m in self.matches
            if (m.home_team == team or m.away_team == team) and m.status == MatchStatus.FINISHED
        ]
        team_matches.sort(key=lambda x: x.match_date, reverse=True)
        recent_matches = team_matches[:matches]

        if not recent_matches:
            return {"error": "No matches found"}

        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        clean_sheets = 0

        for match in recent_matches:
            is_home = match.home_team == team
            team_score = match.home_score if is_home else match.away_score
            opponent_score = match.away_score if is_home else match.home_score

            goals_for += team_score
            goals_against += opponent_score

            if opponent_score == 0:
                clean_sheets += 1

            if team_score > opponent_score:
                wins += 1
            elif team_score == opponent_score:
                draws += 1
            else:
                losses += 1

        return {
            "matches": len(recent_matches),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": wins / len(recent_matches),
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "goals_per_game": goals_for / len(recent_matches),
            "clean_sheets": clean_sheets,
            "clean_sheet_rate": clean_sheets / len(recent_matches),
        }

    def find_high_scoring_matches(self, min_total_goals: int = 5) -> List[Match]:
        """查找高比分比赛"""
        return [
            m
            for m in self.matches
            if m.status == MatchStatus.FINISHED and (m.home_score + m.away_score) >= min_total_goals
        ]

    def find_clean_sheets(self, team: Team) -> List[Match]:
        """查找球队零封比赛"""
        clean_sheet_matches = []
        for match in self.matches:
            if match.status == MatchStatus.FINISHED:
                if match.home_team == team and match.away_score == 0:
                    clean_sheet_matches.append(match)
                elif match.away_team == team and match.home_score == 0:
                    clean_sheet_matches.append(match)
        return clean_sheet_matches


@pytest.mark.unit
class TestMatchAnalysis:
    """测试比赛分析业务逻辑"""

    def test_team_creation(self):
        """测试创建球队"""
        team = Team(1, "Test Team", "Premier League", 1200.0)
        assert team.id == 1
        assert team.name == "Test Team"
        assert team.league == "Premier League"
        assert team.rating == 1200.0
        assert team.form == []

    def test_team_form_update(self):
        """测试更新球队状态"""
        team = Team(1, "Test Team", "Premier League")
        team.update_form(MatchResult.HOME_WIN)
        team.update_form(MatchResult.DRAW)
        team.update_form(MatchResult.AWAY_WIN)

        assert len(team.form) == 3
        assert team.form[-1] == MatchResult.AWAY_WIN

        # 测试超过5场比赛
        team.update_form(MatchResult.DRAW)
        team.update_form(MatchResult.HOME_WIN)
        team.update_form(MatchResult.DRAW)  # 第6场
        assert len(team.form) == 5
        assert team.form[0] == MatchResult.DRAW  # 第一场被移除

    def test_match_creation(self):
        """测试创建比赛"""
        home = Team(1, "Home Team", "Premier League")
        away = Team(2, "Away Team", "Premier League")
        match_date = datetime.now() + timedelta(days=1)
        match = Match(1, home, away, match_date, "Premier League")

        assert match.id == 1
        assert match.home_team == home
        assert match.away_team == away
        assert match.status == MatchStatus.SCHEDULED
        assert match.home_score == 0
        assert match.away_score == 0

    def test_match_finish(self):
        """测试结束比赛"""
        home = Team(1, "Home Team", "Premier League")
        away = Team(2, "Away Team", "Premier League")
        match_date = datetime.now()
        match = Match(1, home, away, match_date, "Premier League")

        match.finish_match(2, 1)
        assert match.status == MatchStatus.FINISHED
        assert match.home_score == 2
        assert match.away_score == 1
        assert match.get_result() == MatchResult.HOME_WIN
        assert match.get_goal_difference() == 1

        # 验证球队数据更新
        assert home.goals_scored == 2
        assert home.goals_conceded == 1
        assert away.goals_scored == 1
        assert away.goals_conceded == 2

    def test_match_draw(self):
        """测试平局"""
        home = Team(1, "Home Team", "Premier League")
        away = Team(2, "Away Team", "Premier League")
        match = Match(1, home, away, datetime.now(), "Premier League")

        match.finish_match(1, 1)
        assert match.get_result() == MatchResult.DRAW
        assert match.get_goal_difference() == 0

    def test_add_goal(self):
        """测试添加进球"""
        home = Team(1, "Home Team", "Premier League")
        away = Team(2, "Away Team", "Premier League")
        match = Match(1, home, away, datetime.now(), "Premier League")

        match.add_goal("home", 25, "John Doe")
        match.add_goal("away", 67, "Jane Smith")

        assert match.home_score == 1
        assert match.away_score == 1
        assert len(match.home_goals) == 1
        assert len(match.away_goals) == 1
        assert match.home_goals[0]["scorer"] == "John Doe"
        assert match.away_goals[0]["minute"] == 67

    def test_match_analyzer_add_match(self):
        """测试添加比赛到分析器"""
        analyzer = MatchAnalyzer()
        home = Team(1, "Home Team", "Premier League")
        away = Team(2, "Away Team", "Premier League")
        match = Match(1, home, away, datetime.now(), "Premier League")

        analyzer.add_match(match)
        assert len(analyzer.matches) == 1
        assert analyzer.matches[0] == match

    def test_get_team_form(self):
        """测试获取球队状态"""
        analyzer = MatchAnalyzer()
        team = Team(1, "Test Team", "Premier League")
        opponent = Team(2, "Opponent", "Premier League")

        # 创建并完成几场比赛
        for i in range(3):
            match = Match(
                i,
                team,
                opponent,
                datetime.now() - timedelta(days=i + 1),
                "Premier League",
            )
            match.finish_match(2 - i, i)  # 2-0, 1-1, 0-2
            analyzer.add_match(match)

        form = analyzer.get_team_form(team)
        assert len(form) == 3
        # 注意：最新的比赛在前面
        # 0-2 (负), 1-1 (平), 2-0 (胜)

    def test_head_to_head(self):
        """测试历史交锋"""
        analyzer = MatchAnalyzer()
        team1 = Team(1, "Team 1", "Premier League")
        team2 = Team(2, "Team 2", "Premier League")

        # 创建几场交锋
        matches_data = [
            (2, 1),  # Team1胜
            (1, 1),  # 平局
            (0, 2),  # Team2胜
            (3, 1),  # Team1胜
        ]

        for i, (home_score, away_score) in enumerate(matches_data):
            match = Match(
                i,
                team1,
                team2,
                datetime.now() - timedelta(days=i + 1),
                "Premier League",
            )
            match.finish_match(home_score, away_score)
            analyzer.add_match(match)

        h2h = analyzer.get_head_to_head(team1, team2)
        assert h2h["matches"] == 4
        assert h2h["team1_wins"] == 2
        assert h2h["team2_wins"] == 1
        assert h2h["draws"] == 1
        assert h2h["team1_goals"] == 6
        assert h2h["team2_goals"] == 5
        assert h2h["win_rate"] == 0.5

    def test_predict_score(self):
        """测试预测比分"""
        analyzer = MatchAnalyzer()
        home = Team(1, "Home Team", "Premier League", 1200.0)
        away = Team(2, "Away Team", "Premier League", 1000.0)

        _prediction = analyzer.predict_score(home, away)
        assert "home_expected" in prediction
        assert "away_expected" in prediction
        assert "total_expected" in prediction
        assert prediction["home_expected"] > prediction["away_expected"]  # 主队评分更高
        assert prediction["total_expected"] > 0

    def test_analyze_team_performance(self):
        """测试分析球队表现"""
        analyzer = MatchAnalyzer()
        team = Team(1, "Test Team", "Premier League")
        opponent = Team(2, "Opponent", "Premier League")

        # 创建5场比赛
        results = [(2, 0), (1, 1), (3, 1), (0, 2), (2, 2)]
        for i, (home_score, away_score) in enumerate(results):
            match = Match(
                i,
                team,
                opponent,
                datetime.now() - timedelta(days=i + 1),
                "Premier League",
            )
            match.finish_match(home_score, away_score)
            analyzer.add_match(match)

        performance = analyzer.analyze_team_performance(team)
        assert performance["matches"] == 5
        assert performance["wins"] == 2
        assert performance["draws"] == 2
        assert performance["losses"] == 1
        assert performance["win_rate"] == 0.4
        assert performance["goals_for"] == 8
        assert performance["goals_against"] == 6
        assert performance["goal_difference"] == 2
        assert performance["goals_per_game"] == 1.6
        assert performance["clean_sheets"] == 1
        assert performance["clean_sheet_rate"] == 0.2

    def test_find_high_scoring_matches(self):
        """测试查找高比分比赛"""
        analyzer = MatchAnalyzer()
        team1 = Team(1, "Team 1", "Premier League")
        team2 = Team(2, "Team 2", "Premier League")

        # 创建不同比分的比赛
        matches_scores = [(1, 0), (3, 2), (4, 2), (0, 0), (2, 3)]
        for i, (home_score, away_score) in enumerate(matches_scores):
            match = Match(
                i,
                team1,
                team2,
                datetime.now() - timedelta(days=i + 1),
                "Premier League",
            )
            match.finish_match(home_score, away_score)
            analyzer.add_match(match)

        high_scoring = analyzer.find_high_scoring_matches(5)
        assert len(high_scoring) == 3  # 3-2, 4-2, 2-3
        total_goals = [m.home_score + m.away_score for m in high_scoring]
        assert all(goals >= 5 for goals in total_goals)

    def test_find_clean_sheets(self):
        """测试查找零封比赛"""
        analyzer = MatchAnalyzer()
        team = Team(1, "Test Team", "Premier League")
        opponent = Team(2, "Opponent", "Premier League")

        # 创建比赛
        matches_scores = [(2, 0), (1, 1), (0, 0), (3, 0), (1, 2)]
        for i, (home_score, away_score) in enumerate(matches_scores):
            match = Match(
                i,
                team,
                opponent,
                datetime.now() - timedelta(days=i + 1),
                "Premier League",
            )
            match.finish_match(home_score, away_score)
            analyzer.add_match(match)

        clean_sheets = analyzer.find_clean_sheets(team)
        assert len(clean_sheets) == 3  # 2-0, 0-0, 3-0
        for match in clean_sheets:
            assert match.away_score == 0

    def test_empty_analyzer(self):
        """测试空分析器"""
        analyzer = MatchAnalyzer()
        team = Team(1, "Test Team", "Premier League")

        assert analyzer.get_team_form(team) == []
        assert analyzer.find_high_scoring_matches() == []
        assert analyzer.find_clean_sheets(team) == []

        performance = analyzer.analyze_team_performance(team)
        assert "error" in performance
