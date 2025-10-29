from typing import List
from typing import Tuple
from typing import Dict
from typing import Any
"""
锦标赛业务逻辑测试
"""

import random
from datetime import datetime, timedelta
from enum import Enum

import pytest


class TournamentType(Enum):
    """锦标赛类型"""

    KNOCKOUT = "knockout"
    GROUP_STAGE = "group_stage"
    LEAGUE = "league"
    MIXED = "mixed"


class MatchStatus(Enum):
    """比赛状态"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Team:
    """球队"""

    def __init__(self, id: int, name: str, ranking: int = 0):
        self.id = id
        self.name = name
        self.ranking = ranking
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.goals_for = 0
        self.goals_against = 0
        self.points = 0
        self.eliminated = False


class Match:
    """比赛"""

    def __init__(
        self,
        id: int,
        home_team: Team,
        away_team: Team,
        match_date: datetime,
        round_name: str = "",
    ):
        self.id = id
        self.home_team = home_team
        self.away_team = away_team
        self.match_date = match_date
        self.round_name = round_name
        self.status = MatchStatus.SCHEDULED
        self.home_score = 0
        self.away_score = 0
        self.winner = None

    def finish_match(self, home_score: int, away_score: int):
        """结束比赛"""
        self.home_score = home_score
        self.away_score = away_score
        self.status = MatchStatus.FINISHED

        # 更新球队统计
        self.home_team.goals_for += home_score
        self.home_team.goals_against += away_score
        self.away_team.goals_for += away_score
        self.away_team.goals_against += home_score

        # 确定胜者
        if home_score > away_score:
            self.winner = self.home_team
            self.home_team.wins += 1
            self.home_team.points += 3
            self.away_team.losses += 1
        elif away_score > home_score:
            self.winner = self.away_team
            self.away_team.wins += 1
            self.away_team.points += 3
            self.home_team.losses += 1
        else:
            self.winner = None  # 平局
            self.home_team.draws += 1
            self.away_team.draws += 1
            self.home_team.points += 1
            self.away_team.points += 1


class Group:
    """小组"""

    def __init__(self, name: str, teams: List[Team]):
        self.name = name
        self._teams = teams
        self.matches: List[Match] = []
        self.standings: List[Team] = []

    def generate_fixtures(self):
        """生成小组赛程"""
        # 循环赛，每队打其他队一次
        for i in range(len(self.teams)):
            for j in range(i + 1, len(self.teams)):
                match = Match(
                    len(self.matches) + 1,
                    self.teams[i],
                    self.teams[j],
                    datetime.now() + timedelta(days=len(self.matches) * 3),
                    f"Group {self.name}",
                )
                self.matches.append(match)

    def update_standings(self):
        """更新小组排名"""
        # 按积分排序，然后按净胜球，然后按进球数
        self.standings = sorted(
            self.teams,
            key=lambda t: (t.points, t.goals_for - t.goals_against, t.goals_for),
            reverse=True,
        )

    def get_qualified_teams(self, positions: int = 2) -> List[Team]:
        """获取出线球队"""
        self.update_standings()
        return self.standings[:positions]


class Tournament:
    """锦标赛"""

    def __init__(self, id: int, name: str, tournament_type: TournamentType):
        self.id = id
        self.name = name
        self.type = tournament_type
        self.teams: List[Team] = []
        self.groups: Dict[str, Group] = {}
        self.knockout_matches: List[Match] = []
        self.champion = None
        self.start_date = None
        self.end_date = None

    def add_team(self, team: Team):
        """添加球队"""
        self.teams.append(team)

    def create_groups(self, num_groups: int, teams_per_group: int):
        """创建小组"""
        if len(self.teams) < num_groups * teams_per_group:
            raise ValueError("Not enough teams for specified groups")

        # 随机分组（简化版）
        shuffled_teams = self.teams.copy()
        random.shuffle(shuffled_teams)

        for i in range(num_groups):
            group_letter = chr(65 + i)  # A, B, C, ...
            group_teams = shuffled_teams[i * teams_per_group : (i + 1) * teams_per_group]
            group = Group(f"{group_letter}", group_teams)
            group.generate_fixtures()
            self.groups[group.name] = group

    def simulate_group_stage(self):
        """模拟小组赛"""
        for group in self.groups.values():
            for match in group.matches:
                # 简单的模拟逻辑
                home_advantage = 0.3
                ranking_diff = (match.away_team.ranking - match.home_team.ranking) * 0.1
                home_expected = 1.5 + home_advantage - ranking_diff
                away_expected = 1.0 - home_advantage + ranking_diff

                # 生成随机比分
                home_score = max(0, int(random.gauss(home_expected, 1)))
                away_score = max(0, int(random.gauss(away_expected, 1)))
                match.finish_match(home_score, away_score)

            group.update_standings()

    def get_knockout_teams(self, qualified_per_group: int = 2) -> List[Team]:
        """获取淘汰赛球队"""
        qualified = []
        for group in self.groups.values():
            qualified.extend(group.get_qualified_teams(qualified_per_group))
        return qualified

    def create_knockout_bracket(self, teams: List[Team]):
        """创建淘汰赛对阵"""
        # 按小组排名排序
        teams.sort(key=lambda t: t.points, reverse=True)

        # 创建对阵（第一对第八，第二对第七，等）
        round_matches = []
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                match = Match(
                    len(self.knockout_matches) + 1,
                    teams[i],
                    teams[i + 1],
                    datetime.now() + timedelta(days=len(self.knockout_matches) * 7),
                    "Round of 16",
                )
                round_matches.append(match)
                self.knockout_matches.append(match)
        return round_matches

    def simulate_knockout_match(self, match: Match):
        """模拟淘汰赛"""
        # 如果比分相同，进行点球大战
        if match.home_score == match.away_score:
            # 点球大战（简化）
            home_penalty = random.choice([0, 1, 2, 3, 4, 5])
            away_penalty = random.choice([0, 1, 2, 3, 4, 5])

            while home_penalty == away_penalty:
                home_penalty = random.choice([0, 1, 2, 3, 4, 5])
                away_penalty = random.choice([0, 1, 2, 3, 4, 5])

            if home_penalty > away_penalty:
                match.winner = match.home_team
            else:
                match.winner = match.away_team

    def simulate_knockout_round(self, round_name: str, matches: List[Match]) -> List[Match]:
        """模拟淘汰赛轮次"""
        next_round_teams = []

        for match in matches:
            # 简单模拟
            home_advantage = 0.2
            ranking_diff = (match.away_team.ranking - match.home_team.ranking) * 0.1
            home_expected = 1.2 + home_advantage - ranking_diff
            away_expected = 1.0 - home_advantage + ranking_diff

            home_score = max(0, int(random.gauss(home_expected, 0.8)))
            away_score = max(0, int(random.gauss(away_expected, 0.8)))
            match.finish_match(home_score, away_score)

            # 处理平局
            self.simulate_knockout_match(match)

            # 晋级球队
            if match.winner:
                next_round_teams.append(match.winner)

        # 创建下一轮比赛
        next_matches = []
        if len(next_round_teams) > 1:
            for i in range(0, len(next_round_teams), 2):
                if i + 1 < len(next_round_teams):
                    next_match = Match(
                        len(self.knockout_matches) + 1,
                        next_round_teams[i],
                        next_round_teams[i + 1],
                        datetime.now() + timedelta(days=len(self.knockout_matches) * 7),
                        round_name,
                    )
                    next_matches.append(next_match)
                    self.knockout_matches.append(next_match)

        return next_matches

    def run_tournament(self):
        """运行整个锦标赛"""
        if self.type == TournamentType.GROUP_STAGE or self.type == TournamentType.MIXED:
            # 小组赛阶段
            self.simulate_group_stage()
            knockout_teams = self.get_knockout_teams()

            if self.type == TournamentType.MIXED and knockout_teams:
                # 淘汰赛阶段
                round16 = self.create_knockout_bracket(knockout_teams[:16])
                quarter_finals = self.simulate_knockout_round("Quarter-finals", round16)
                semi_finals = self.simulate_knockout_round("Semi-finals", quarter_finals)
                final = self.simulate_knockout_round("Final", semi_finals)

                if final and final[0].winner:
                    self.champion = final[0].winner

        elif self.type == TournamentType.KNOCKOUT:
            # 纯淘汰赛
            round1 = self.create_knockout_bracket(self.teams)
            quarter_finals = self.simulate_knockout_round("Quarter-finals", round1)
            semi_finals = self.simulate_knockout_round("Semi-finals", quarter_finals)
            final = self.simulate_knockout_round("Final", semi_finals)

            if final and final[0].winner:
                self.champion = final[0].winner

    def get_top_scorers(self, limit: int = 10) -> List[Tuple[Team, int]]:
        """获取射手榜（以球队为单位）"""
        return sorted(
            [(team, team.goals_for) for team in self.teams],
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def get_final_standings(self) -> List[Team]:
        """获取最终排名"""
        if self.champion:
            # 冠军放在第一位
            others = [t for t in self.teams if t != self.champion]
            others.sort(
                key=lambda t: (t.points, t.goals_for - t.goals_against, t.goals_for),
                reverse=True,
            )
            return [self.champion] + others
        else:
            return sorted(
                self.teams,
                key=lambda t: (t.points, t.goals_for - t.goals_against, t.goals_for),
                reverse=True,
            )

    def get_tournament_statistics(self) -> Dict[str, Any]:
        """获取锦标赛统计"""
        total_matches = sum(len(g.matches) for g in self.groups.values()) + len(
            self.knockout_matches
        )
        total_goals = sum(t.goals_for for t in self.teams)
        total_teams = len(self.teams)

        return {
            "name": self.name,
            "type": self.type.value,
            "total_teams": total_teams,
            "total_matches": total_matches,
            "total_goals": total_goals,
            "avg_goals_per_match": (total_goals / total_matches if total_matches > 0 else 0),
            "champion": self.champion.name if self.champion else None,
            "total_groups": len(self.groups),
            "group_stage_teams": sum(len(g.teams) for g in self.groups.values()),
            "knockout_teams": (len(self.get_knockout_teams()) if self.groups else total_teams),
        }


@pytest.mark.unit
class TestTournament:
    """测试锦标赛业务逻辑"""

    def test_team_creation(self):
        """测试创建球队"""
        team = Team(1, "Test Team", 10)
        assert team.id == 1
        assert team.name == "Test Team"
        assert team.ranking == 10
        assert team.wins == 0
        assert team.points == 0

    def test_match_creation(self):
        """测试创建比赛"""
        home = Team(1, "Home", 10)
        away = Team(2, "Away", 20)
        match_date = datetime.now() + timedelta(days=1)
        match = Match(1, home, away, match_date, "Final")

        assert match.id == 1
        assert match.home_team == home
        assert match.away_team == away
        assert match.round_name == "Final"
        assert match.status == MatchStatus.SCHEDULED

    def test_match_finish_win(self):
        """测试比赛结束-胜利"""
        home = Team(1, "Home", 10)
        away = Team(2, "Away", 20)
        match = Match(1, home, away, datetime.now())
        match.finish_match(2, 1)

        assert match.status == MatchStatus.FINISHED
        assert match.home_score == 2
        assert match.away_score == 1
        assert match.winner == home
        assert home.wins == 1
        assert home.points == 3
        assert away.losses == 1
        assert away.points == 0

    def test_match_finish_draw(self):
        """测试比赛结束-平局"""
        home = Team(1, "Home", 10)
        away = Team(2, "Away", 20)
        match = Match(1, home, away, datetime.now())
        match.finish_match(1, 1)

        assert match.winner is None
        assert home.draws == 1
        assert away.draws == 1
        assert home.points == 1
        assert away.points == 1

    def test_group_creation(self):
        """测试创建小组"""
        _teams = [Team(i, f"Team {i}", i) for i in range(1, 5)]
        group = Group("A", teams)

        assert group.name == "A"
        assert len(group.teams) == 4
        assert group._teams == teams

    def test_group_generate_fixtures(self):
        """测试生成小组赛程"""
        _teams = [Team(i, f"Team {i}", i) for i in range(1, 5)]
        group = Group("A", teams)
        group.generate_fixtures()

        # 4队循环赛应该有6场比赛
        assert len(group.matches) == 6
        # 每队应该打3场比赛
        for team in teams:
            team_matches = [m for m in group.matches if m.home_team == team or m.away_team == team]
            assert len(team_matches) == 3

    def test_group_update_standings(self):
        """测试更新小组排名"""
        _teams = [Team(i, f"Team {i}", i) for i in range(1, 5)]
        group = Group("A", teams)

        # 设置不同的积分
        teams[0].points = 9
        teams[1].points = 6
        teams[2].points = 3
        teams[3].points = 0

        group.update_standings()
        assert group.standings[0].points == 9
        assert group.standings[1].points == 6
        assert group.standings[2].points == 3
        assert group.standings[3].points == 0

    def test_group_get_qualified_teams(self):
        """测试获取出线球队"""
        _teams = [Team(i, f"Team {i}", i) for i in range(1, 5)]
        teams[0].points = 9
        teams[1].points = 6
        teams[2].points = 3
        teams[3].points = 0

        group = Group("A", teams)
        qualified = group.get_qualified_teams(2)

        assert len(qualified) == 2
        assert qualified[0].points == 9
        assert qualified[1].points == 6

    def test_tournament_creation(self):
        """测试创建锦标赛"""
        tournament = Tournament(1, "World Cup", TournamentType.MIXED)
        assert tournament.id == 1
        assert tournament.name == "World Cup"
        assert tournament.type == TournamentType.MIXED
        assert tournament._teams == []

    def test_tournament_add_team(self):
        """测试添加球队到锦标赛"""
        tournament = Tournament(1, "World Cup", TournamentType.MIXED)
        team = Team(1, "Brazil", 1)
        tournament.add_team(team)

        assert len(tournament.teams) == 1
        assert tournament.teams[0] == team

    def test_tournament_create_groups(self):
        """测试创建小组"""
        tournament = Tournament(1, "World Cup", TournamentType.MIXED)

        # 添加8支球队
        for i in range(8):
            tournament.add_team(Team(i + 1, f"Team {i + 1}", i + 1))

        tournament.create_groups(2, 4)
        assert len(tournament.groups) == 2
        assert "A" in tournament.groups
        assert "B" in tournament.groups
        assert len(tournament.groups["A"].teams) == 4
        assert len(tournament.groups["B"].teams) == 4

    def test_tournament_simulate_group_stage(self):
        """测试模拟小组赛"""
        tournament = Tournament(1, "Test Cup", TournamentType.GROUP_STAGE)

        # 添加8支球队
        for i in range(8):
            tournament.add_team(Team(i + 1, f"Team {i + 1}", i + 1))

        tournament.create_groups(2, 4)
        tournament.simulate_group_stage()

        # 检查所有比赛都已完成
        for group in tournament.groups.values():
            assert all(m.status == MatchStatus.FINISHED for m in group.matches)
            # 检查排名已更新
            assert len(group.standings) == 4

    def test_get_knockout_teams(self):
        """测试获取淘汰赛球队"""
        tournament = Tournament(1, "Test Cup", TournamentType.MIXED)

        # 添加8支球队
        for i in range(8):
            tournament.add_team(Team(i + 1, f"Team {i + 1}", i + 1))

        tournament.create_groups(2, 4)
        tournament.simulate_group_stage()

        knockout_teams = tournament.get_knockout_teams(2)
        assert len(knockout_teams) == 4  # 每组2支球队出线

    def test_create_knockout_bracket(self):
        """测试创建淘汰赛对阵"""
        tournament = Tournament(1, "Test Cup", TournamentType.KNOCKOUT)

        # 添加8支球队
        _teams = [Team(i + 1, f"Team {i + 1}", i + 1) for i in range(8)]
        for team in teams:
            tournament.add_team(team)

        _matches = tournament.create_knockout_bracket(teams)
        assert len(matches) == 4  # 8队淘汰赛第一轮有4场比赛

        # 检查对阵安排
        assert matches[0].home_team in teams
        assert matches[0].away_team in teams
        assert matches[0].home_team != matches[0].away_team

    def test_simulate_knockout_match(self):
        """测试模拟淘汰赛"""
        home = Team(1, "Home", 10)
        away = Team(2, "Away", 20)
        match = Match(1, home, away, datetime.now(), "Test")

        # 设置平局比分
        match.home_score = 1
        match.away_score = 1
        match.status = MatchStatus.FINISHED

        tournament = Tournament(1, "Test", TournamentType.KNOCKOUT)
        tournament.simulate_knockout_match(match)

        # 平局后应该有胜者
        assert match.winner is not None
        assert match.winner in [home, away]

    def test_run_tournament_mixed(self):
        """测试运行混合赛制锦标赛"""
        random.seed(42)  # 固定随机种子
        tournament = Tournament(1, "Test Cup", TournamentType.MIXED)

        # 添加8支球队
        for i in range(8):
            tournament.add_team(Team(i + 1, f"Team {i + 1}", i + 1))

        tournament.create_groups(2, 4)
        tournament.run_tournament()

        # 检查有冠军
        assert tournament.champion is not None
        assert tournament.champion in tournament.teams

    def test_get_top_scorers(self):
        """测试获取射手榜"""
        tournament = Tournament(1, "Test Cup", TournamentType.MIXED)

        # 添加球队并设置进球数
        for i in range(4):
            team = Team(i + 1, f"Team {i + 1}", i + 1)
            team.goals_for = 10 - i * 2
            tournament.add_team(team)

        top_scorers = tournament.get_top_scorers(2)
        assert len(top_scorers) == 2
        assert top_scorers[0][1] == 10  # 第一名10球
        assert top_scorers[1][1] == 8  # 第二名8球

    def test_get_final_standings(self):
        """测试获取最终排名"""
        tournament = Tournament(1, "Test Cup", TournamentType.LEAGUE)

        # 添加球队并设置积分
        _teams = []
        for i in range(4):
            team = Team(i + 1, f"Team {i + 1}", i + 1)
            team.points = 9 - i * 3
            teams.append(team)
            tournament.add_team(team)

        tournament.champion = teams[0]  # 设置冠军
        standings = tournament.get_final_standings()

        assert standings[0] == teams[0]  # 冠军第一
        assert standings[1].points == 6
        assert standings[2].points == 3
        assert standings[3].points == 0

    def test_get_tournament_statistics(self):
        """测试获取锦标赛统计"""
        tournament = Tournament(1, "Test Cup", TournamentType.MIXED)

        # 添加球队
        for i in range(8):
            team = Team(i + 1, f"Team {i + 1}", i + 1)
            team.goals_for = 10
            tournament.add_team(team)

        tournament.create_groups(2, 4)
        tournament.champion = tournament.teams[0]

        _stats = tournament.get_tournament_statistics()
        assert stats["name"] == "Test Cup"
        assert stats["type"] == "mixed"
        assert stats["total_teams"] == 8
        assert stats["total_groups"] == 2
        assert stats["group_stage_teams"] == 8
        assert stats["champion"] is not None

    def test_tournament_knockout_only(self):
        """测试纯淘汰赛锦标赛"""
        random.seed(42)
        tournament = Tournament(1, "Knockout Cup", TournamentType.KNOCKOUT)

        # 添加8支球队
        for i in range(8):
            tournament.add_team(Team(i + 1, f"Team {i + 1}", i + 1))

        tournament.run_tournament()

        # 检查有冠军
        assert tournament.champion is not None
        # 检查有淘汰赛比赛
        assert len(tournament.knockout_matches) >= 7  # 8队淘汰赛共7场

    def test_empty_tournament(self):
        """测试空锦标赛"""
        tournament = Tournament(1, "Empty Cup", TournamentType.MIXED)

        # 运行空锦标赛
        tournament.run_tournament()
        assert tournament.champion is None

        _stats = tournament.get_tournament_statistics()
        assert stats["total_teams"] == 0
        assert stats["total_matches"] == 0
        assert stats["total_goals"] == 0
        assert stats["champion"] is None
