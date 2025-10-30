"""
联赛积分榜业务逻辑测试
"""

from enum import Enum
from typing import Any, Dict, List, Optional

import pytest


class MatchResult(Enum):
    """比赛结果"""

    WIN = "win"
    DRAW = "draw"
    LOSS = "loss"


class Team:
    """球队"""

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.goals_for = 0
        self.goals_against = 0
        self.goal_difference = 0
        self.points = 0

    def update_match(self, goals_for: int, goals_against: int):
        """更新比赛数据"""
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        self.goal_difference = self.goals_for - self.goals_against

        if goals_for > goals_against:
            self.wins += 1
            self.points += 3
        elif goals_for == goals_against:
            self.draws += 1
            self.points += 1
        else:
            self.losses += 1

    def get_form(self) -> str:
        """获取状态字符串"""
        return f"{self.wins}{self.draws}{self.losses}"


class League:
    """联赛"""

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.teams: Dict[int, Team] = {}


class LeagueStandings:
    """联赛积分榜"""

    def __init__(self, league: League):
        self.league = league
        self.standings: List[Team] = []

    def add_team(self, team: Team):
        """添加球队"""
        self.league.teams[team.id] = team
        self.update_standings()

    def update_standings(self):
        """更新积分榜"""
        self.standings = sorted(
            self.league.teams.values(),
            key=lambda t: (-t.points, -t.goal_difference, -t.goals_for),
        )

    def get_position(self, team_id: int) -> Optional[int]:
        """获取球队排名"""
        for i, team in enumerate(self.standings):
            if team.id == team_id:
                return i + 1
        return None

    def get_team(self, position: int) -> Optional[Team]:
        """根据排名获取球队"""
        if 1 <= position <= len(self.standings):
            return self.standings[position - 1]
        return None

    def get_top_teams(self, n: int) -> List[Team]:
        """获取前n名球队"""
        return self.standings[:n]

    def get_bottom_teams(self, n: int) -> List[Team]:
        """获取后n名球队"""
        return self.standings[-n:]

    def get_point_difference(self, pos1: int, pos2: int) -> int:
        """获取两名球队积分差"""
        team1 = self.get_team(pos1)
        team2 = self.get_team(pos2)
        if team1 and team2:
            return team1.points - team2.points
        return 0

    def is_championship_decided(self) -> bool:
        """判断冠军是否已决出"""
        if len(self.standings) < 2:
            return True

        top = self.standings[0]
        second = self.standings[1]
        remaining_matches = 38 - top.played  # 假设38轮联赛

        # 第二名最多能获得的积分
        max_second_points = second.points + remaining_matches * 3

        return top.points > max_second_points

    def get_relegation_zone(self, positions: int = 3) -> List[Team]:
        """获取降级区球队"""
        return self.standings[-positions:]

    def get_promotion_zone(self, positions: int = 2) -> List[Team]:
        """获取升级区球队"""
        return self.standings[:positions]

    def calculate_h2h_advantage(
        self, team1_id: int, team2_id: int, h2h_results: List[Dict]
    ) -> Dict[str, Any]:
        """计算两队交锋优势"""
        team1_wins = sum(1 for r in h2h_results if r["winner"] == team1_id)
        team2_wins = sum(1 for r in h2h_results if r["winner"] == team2_id)
        draws = len(h2h_results) - team1_wins - team2_wins

        return {
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "team1_advantage": team1_wins > team2_wins,
            "total_matches": len(h2h_results),
        }

    def predict_final_position(self, team_id: int) -> Dict[str, Any]:
        """预测最终排名"""
        team = self.league.teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        current_pos = self.get_position(team_id)
        remaining_matches = 38 - team.played
        max_possible_points = team.points + remaining_matches * 3

        # 简单预测:假设所有球队都赢下剩余比赛
        predicted_teams = []
        for t in self.standings:
            if t.id == team_id:
                predicted_points = max_possible_points
            else:
                t_remaining = 38 - t.played
                predicted_points = t.points + t_remaining * 3
            predicted_teams.append((t, predicted_points))

        predicted_teams.sort(key=lambda x: x[1], reverse=True)

        for i, (t, _) in enumerate(predicted_teams):
            if t.id == team_id:
                return {
                    "current_position": current_pos,
                    "best_possible": i + 1,
                    "max_points": max_possible_points,
                    "remaining_matches": remaining_matches,
                }

        return {"error": "Prediction failed"}

    def get_tight_positions(self) -> List[Dict[str, Any]]:
        """获取排名接近的位置"""
        tight_groups = []

        for i in range(len(self.standings) - 1):
            current = self.standings[i]
            next_team = self.standings[i + 1]
            point_diff = current.points - next_team.points

            if point_diff <= 3:  # 3分以内算接近
                tight_groups.append(
                    {
                        "positions": [i + 1, i + 2],
                        "teams": [current.name, next_team.name],
                        "point_difference": point_diff,
                    }
                )

        return tight_groups

    def get_statistics(self) -> Dict[str, Any]:
        """获取积分榜统计信息"""
        if not self.standings:
            return {}

        total_goals = sum(t.goals_for for t in self.standings)
        total_matches = sum(t.played for t in self.standings) // 2

        return {
            "total_teams": len(self.standings),
            "total_goals": total_goals,
            "total_matches": total_matches,
            "avg_goals_per_match": (total_goals / total_matches if total_matches > 0 else 0),
            "highest_points": self.standings[0].points if self.standings else 0,
            "lowest_points": self.standings[-1].points if self.standings else 0,
            "biggest_gap": (
                self.standings[0].points - self.standings[-1].points
                if len(self.standings) > 1
                else 0
            ),
        }


@pytest.mark.unit
class TestLeagueStandings:
    """测试联赛积分榜"""

    def test_team_creation(self):
        """测试创建球队"""
        team = Team(1, "Test Team")
        assert team.id == 1
        assert team.name == "Test Team"
        assert team.played == 0
        assert team.points == 0

    def test_team_update_match_win(self):
        """测试更新比赛-胜利"""
        team = Team(1, "Test Team")
        team.update_match(3, 1)

        assert team.played == 1
        assert team.wins == 1
        assert team.draws == 0
        assert team.losses == 0
        assert team.goals_for == 3
        assert team.goals_against == 1
        assert team.goal_difference == 2
        assert team.points == 3

    def test_team_update_match_draw(self):
        """测试更新比赛-平局"""
        team = Team(1, "Test Team")
        team.update_match(2, 2)

        assert team.played == 1
        assert team.wins == 0
        assert team.draws == 1
        assert team.losses == 0
        assert team.goals_for == 2
        assert team.goals_against == 2
        assert team.goal_difference == 0
        assert team.points == 1

    def test_team_update_match_loss(self):
        """测试更新比赛-失败"""
        team = Team(1, "Test Team")
        team.update_match(1, 2)

        assert team.played == 1
        assert team.wins == 0
        assert team.draws == 0
        assert team.losses == 1
        assert team.goals_for == 1
        assert team.goals_against == 2
        assert team.goal_difference == -1
        assert team.points == 0

    def test_league_standings_creation(self):
        """测试创建积分榜"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        assert standings.league == league
        assert standings.standings == []

    def test_add_team(self):
        """测试添加球队"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)
        team = Team(1, "Team A")

        standings.add_team(team)

        assert len(standings.standings) == 1
        assert standings.standings[0] == team

    def test_standings_sorting(self):
        """测试积分榜排序"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        # 创建不同积分的球队
        teams_data = [
            (1, "Team D", 10, 5, 15),  # 15分
            (2, "Team A", 20, 5, 40),  # 40分
            (3, "Team C", 15, 10, 35),  # 35分
            (4, "Team B", 18, 8, 40),  # 40分, 净胜球少
        ]

        for team_id, name, gf, ga, points in teams_data:
            team = Team(team_id, name)
            team.points = points
            team.goals_for = gf
            team.goals_against = ga
            team.goal_difference = gf - ga
            league.teams[team_id] = team

        standings.update_standings()

        # 验证排序:积分 > 净胜球 > 进球数
        assert standings.standings[0].name == "Team A"  # 40分, +15
        assert standings.standings[1].name == "Team B"  # 40分, +10
        assert standings.standings[2].name == "Team C"  # 35分, +5
        assert standings.standings[3].name == "Team D"  # 15分, +5

    def test_get_position(self):
        """测试获取排名"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        for i in range(5):
            team = Team(i + 1, f"Team {i + 1}")
            team.points = 20 - i
            standings.add_team(team)

        assert standings.get_position(1) == 1
        assert standings.get_position(3) == 3
        assert standings.get_position(6) is None

    def test_get_team(self):
        """测试根据排名获取球队"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        for i in range(5):
            team = Team(i + 1, f"Team {i + 1}")
            standings.add_team(team)

        first_team = standings.get_team(1)
        assert first_team is not None
        assert first_team.name == "Team 1"

        assert standings.get_team(10) is None

    def test_get_top_teams(self):
        """测试获取前n名"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        for i in range(5):
            team = Team(i + 1, f"Team {i + 1}")
            team.points = 20 - i
            standings.add_team(team)

        top_3 = standings.get_top_teams(3)
        assert len(top_3) == 3
        assert top_3[0].points >= top_3[1].points >= top_3[2].points

    def test_get_bottom_teams(self):
        """测试获取后n名"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        for i in range(5):
            team = Team(i + 1, f"Team {i + 1}")
            team.points = 20 - i
            standings.add_team(team)

        bottom_2 = standings.get_bottom_teams(2)
        assert len(bottom_2) == 2
        assert bottom_2[0].points <= bottom_2[1].points

    def test_point_difference(self):
        """测试积分差"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        # 创建两支不同积分的球队
        team1 = Team(1, "Team 1")
        team1.points = 30
        team2 = Team(2, "Team 2")
        team2.points = 25

        standings.add_team(team1)
        standings.add_team(team2)

        diff = standings.get_point_difference(1, 2)
        assert diff == 5

        # 反向
        diff_reverse = standings.get_point_difference(2, 1)
        assert diff_reverse == -5

    def test_championship_decided(self):
        """测试冠军是否决出"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        # 创建领先优势巨大的情况
        leader = Team(1, "Leader")
        leader.points = 90
        leader.played = 36

        second = Team(2, "Second")
        second.points = 70
        second.played = 36

        standings.add_team(leader)
        standings.add_team(second)

        assert standings.is_championship_decided() is True

        # 激烈的竞争
        leader.points = 70
        second.points = 68
        standings.update_standings()
        assert standings.is_championship_decided() is False

    def test_relegation_zone(self):
        """测试降级区"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        for i in range(20):
            team = Team(i + 1, f"Team {i + 1}")
            team.points = 40 - i * 2
            standings.add_team(team)

        relegation = standings.get_relegation_zone(3)
        assert len(relegation) == 3
        assert relegation[0].name == "Team 18"
        assert relegation[2].name == "Team 20"

    def test_promotion_zone(self):
        """测试升级区"""
        league = League(1, "Championship")
        standings = LeagueStandings(league)

        for i in range(24):
            team = Team(i + 1, f"Team {i + 1}")
            team.points = 60 - i * 2
            standings.add_team(team)

        promotion = standings.get_promotion_zone(2)
        assert len(promotion) == 2
        assert promotion[0].name == "Team 1"
        assert promotion[1].name == "Team 2"

    def test_h2h_advantage(self):
        """测试交锋优势"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        h2h_results = [
            {"winner": 1, "loser": 2},
            {"winner": 2, "loser": 1},
            {"winner": 1, "loser": 2},
            {"draw": True, "teams": [1, 2]},
        ]

        advantage = standings.calculate_h2h_advantage(1, 2, h2h_results)
        assert advantage["team1_wins"] == 2
        assert advantage["team2_wins"] == 1
        assert advantage["draws"] == 1
        assert advantage["team1_advantage"] is True
        assert advantage["total_matches"] == 4

    def test_predict_final_position(self):
        """测试预测最终排名"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        team = Team(1, "Test Team")
        team.points = 60
        team.played = 30
        standings.add_team(team)

        _prediction = standings.predict_final_position(1)
        assert "current_position" in prediction
        assert "best_possible" in prediction
        assert "max_points" in prediction
        assert "remaining_matches" in prediction
        assert prediction["remaining_matches"] == 8
        assert prediction["max_points"] == 84  # 60 + 8 * 3

    def test_get_tight_positions(self):
        """测试排名接近的位置"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        # 创建积分接近的球队
        points = [50, 48, 47, 45, 40, 40, 38]
        for i, p in enumerate(points):
            team = Team(i + 1, f"Team {i + 1}")
            team.points = p
            standings.add_team(team)

        tight = standings.get_tight_positions()
        assert len(tight) >= 2

        # 验证3分以内的差距都被识别
        for group in tight:
            assert group["point_difference"] <= 3
            assert len(group["positions"]) == 2
            assert len(group["teams"]) == 2

    def test_get_statistics(self):
        """测试获取统计信息"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        # 创建20支球队,每队38场比赛
        for i in range(20):
            team = Team(i + 1, f"Team {i + 1}")
            team.played = 38
            team.points = 50 - i * 2
            team.goals_for = 50
            team.goals_against = 40
            standings.add_team(team)

        _stats = standings.get_statistics()
        assert stats["total_teams"] == 20
        assert stats["total_goals"] == 1000  # 20 * 50
        assert stats["total_matches"] == 380  # 20 * 38 / 2
        assert stats["avg_goals_per_match"] == 2.63  # 1000 / 380
        assert stats["highest_points"] == 50
        assert stats["lowest_points"] == 12
        assert stats["biggest_gap"] == 38

    def test_empty_standings(self):
        """测试空积分榜"""
        league = League(1, "Premier League")
        standings = LeagueStandings(league)

        assert standings.get_position(1) is None
        assert standings.get_team(1) is None
        assert standings.get_top_teams(5) == []
        assert standings.get_bottom_teams(5) == []
        assert standings.get_point_difference(1, 2) == 0
        assert standings.is_championship_decided() is True
        assert standings.get_relegation_zone() == []
        assert standings.get_promotion_zone() == []
        assert standings.get_tight_positions() == []
        assert standings.get_statistics() == {}
