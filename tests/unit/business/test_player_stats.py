"""
球员统计业务逻辑测试
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class Position(Enum):
    """球场位置"""

    GOALKEEPER = "GK"
    DEFENDER = "DEF"
    MIDFIELDER = "MID"
    FORWARD = "FWD"


class CardType(Enum):
    """牌的类型"""

    YELLOW = "yellow"
    RED = "red"


class Player:
    """球员类"""

    def __init__(self, id: int, name: str, position: Position, team_id: int):
        self.id = id
        self.name = name
        self.position = position
        self.team_id = team_id
        self.age = 25
        self.height = 180  # cm
        self.weight = 75  # kg
        self._stats = PlayerStats()

    def update_match_stats(
        self,
        goals: int = 0,
        assists: int = 0,
        minutes_played: int = 0,
        yellow_cards: int = 0,
        red_cards: int = 0,
    ):
        """更新比赛统计"""
        self.stats.matches_played += 1
        self.stats.goals += goals
        self.stats.assists += assists
        self.stats.minutes_played += minutes_played
        self.stats.yellow_cards += yellow_cards
        self.stats.red_cards += red_cards

        if yellow_cards > 0:
            for _ in range(yellow_cards):
                self.stats.cards.append(CardType.YELLOW)
        if red_cards > 0:
            for _ in range(red_cards):
                self.stats.cards.append(CardType.RED)

        # 更新评分（模拟）
        base_rating = 6.0
        rating = (
            base_rating
            + (goals * 0.5)
            + (assists * 0.3)
            - (yellow_cards * 0.2)
            - (red_cards * 0.5)
        )
        self.stats.ratings.append(min(10, max(0, rating)))

    def get_average_rating(self) -> float:
        """获取平均评分"""
        if not self.stats.ratings:
            return 0.0
        return sum(self.stats.ratings) / len(self.stats.ratings)

    def get_goals_per_game(self) -> float:
        """场均进球"""
        if self.stats.matches_played == 0:
            return 0.0
        return self.stats.goals / self.stats.matches_played

    def get_assists_per_game(self) -> float:
        """场均助攻"""
        if self.stats.matches_played == 0:
            return 0.0
        return self.stats.assists / self.stats.matches_played

    def get_minutes_per_goal(self) -> float:
        """每球所需分钟"""
        if self.stats.goals == 0:
            return float("inf")
        return self.stats.minutes_played / self.stats.goals


class PlayerStats:
    """球员统计类"""

    def __init__(self):
        self.matches_played = 0
        self.goals = 0
        self.assists = 0
        self.minutes_played = 0
        self.yellow_cards = 0
        self.red_cards = 0
        self.cards: List[CardType] = []
        self.ratings: List[float] = []
        self.injuries: List[Dict[str, Any]] = []


class PlayerAnalyzer:
    """球员分析器"""

    def __init__(self):
        self.players: Dict[int, Player] = {}

    def add_player(self, player: Player):
        """添加球员"""
        self.players[player.id] = player

    def get_top_scorers(self, limit: int = 10) -> List[Player]:
        """获取射手榜"""
        return sorted(self.players.values(), key=lambda p: p.stats.goals, reverse=True)[
            :limit
        ]

    def get_top_assisters(self, limit: int = 10) -> List[Player]:
        """获取助攻榜"""
        return sorted(
            self.players.values(), key=lambda p: p.stats.assists, reverse=True
        )[:limit]

    def get_players_by_position(self, position: Position) -> List[Player]:
        """根据位置获取球员"""
        return [p for p in self.players.values() if p.position == position]

    def get_best_rated_players(
        self, min_matches: int = 5, limit: int = 10
    ) -> List[Player]:
        """获取最高评分球员"""
        qualified = [
            p for p in self.players.values() if p.stats.matches_played >= min_matches
        ]
        return sorted(qualified, key=lambda p: p.get_average_rating(), reverse=True)[
            :limit
        ]

    def find_most_consistent_player(self, min_matches: int = 10) -> Optional[Player]:
        """找到最稳定的球员（评分方差最小）"""
        import math

        candidates = [
            p for p in self.players.values() if len(p.stats.ratings) >= min_matches
        ]

        if not candidates:
            return None

        def variance(ratings: List[float]) -> float:
            if not ratings:
                return float("inf")
            mean = sum(ratings) / len(ratings)
            return sum((x - mean) ** 2 for x in ratings) / len(ratings)

        best_player = min(candidates, key=lambda p: variance(p.stats.ratings))
        return best_player

    def analyze_player_performance(self, player_id: int) -> Dict[str, Any]:
        """分析球员表现"""
        player = self.players.get(player_id)
        if not player:
            return {"error": "Player not found"}

        _stats = player.stats
        if stats.matches_played == 0:
            return {"error": "No matches played"}

        return {
            "player_name": player.name,
            "position": player.position.value,
            "matches_played": stats.matches_played,
            "goals": stats.goals,
            "assists": stats.assists,
            "goals_per_game": player.get_goals_per_game(),
            "assists_per_game": player.get_assists_per_game(),
            "minutes_played": stats.minutes_played,
            "minutes_per_match": stats.minutes_played / stats.matches_played,
            "minutes_per_goal": player.get_minutes_per_goal(),
            "average_rating": player.get_average_rating(),
            "yellow_cards": stats.yellow_cards,
            "red_cards": stats.red_cards,
            "goal_involvement": stats.goals + stats.assists,
            "goal_involvement_per_game": (stats.goals + stats.assists)
            / stats.matches_played,
        }

    def compare_players(self, player1_id: int, player2_id: int) -> Dict[str, Any]:
        """比较两名球员"""
        p1 = self.players.get(player1_id)
        p2 = self.players.get(player2_id)

        if not p1 or not p2:
            return {"error": "One or both players not found"}

        return {
            "player1": {
                "name": p1.name,
                "goals": p1.stats.goals,
                "assists": p1.stats.assists,
                "avg_rating": p1.get_average_rating(),
                "goals_per_game": p1.get_goals_per_game(),
            },
            "player2": {
                "name": p2.name,
                "goals": p2.stats.goals,
                "assists": p2.stats.assists,
                "avg_rating": p2.get_average_rating(),
                "goals_per_game": p2.get_goals_per_game(),
            },
            "comparison": {
                "better_goals": p1.name if p1.stats.goals > p2.stats.goals else p2.name,
                "better_assists": p1.name
                if p1.stats.assists > p2.stats.assists
                else p2.name,
                "better_rating": p1.name
                if p1.get_average_rating() > p2.get_average_rating()
                else p2.name,
            },
        }

    def find_potential_star(self, min_age: int = 18, max_age: int = 23) -> List[Player]:
        """找到潜在新星（年轻且表现好）"""
        candidates = [
            p
            for p in self.players.values()
            if min_age <= p.age <= max_age and p.stats.matches_played >= 5
        ]

        # 根据进球/助攻/评分综合评分
        def potential_score(p: Player) -> float:
            goal_score = p.get_goals_per_game() * 10
            assist_score = p.get_assists_per_game() * 8
            rating_score = p.get_average_rating() * 5
            return goal_score + assist_score + rating_score

        return sorted(candidates, key=potential_score, reverse=True)[:5]

    def get_discipline_records(self) -> Dict[str, List[Player]]:
        """获取纪律记录"""
        most_yellow = sorted(
            self.players.values(), key=lambda p: p.stats.yellow_cards, reverse=True
        )[:5]

        most_red = sorted(
            self.players.values(), key=lambda p: p.stats.red_cards, reverse=True
        )[:5]

        cleanest = [
            p
            for p in self.players.values()
            if p.stats.matches_played >= 10
            and p.stats.yellow_cards == 0
            and p.stats.red_cards == 0
        ][:5]

        return {
            "most_yellow_cards": most_yellow,
            "most_red_cards": most_red,
            "cleanest_players": cleanest,
        }

    def calculate_player_value(self, player_id: int) -> Dict[str, Any]:
        """计算球员价值（简化版）"""
        player = self.players.get(player_id)
        if not player:
            return {"error": "Player not found"}

        # 基础价值因子
        age_factor = max(0.5, 1 - (player.age - 25) * 0.02) if player.age > 25 else 1.0
        performance_factor = player.get_average_rating() / 10
        goal_factor = player.get_goals_per_game() * 2
        assist_factor = player.get_assists_per_game() * 1.5

        # 位置权重
        position_weights = {
            Position.FORWARD: 1.2,
            Position.MIDFIELDER: 1.0,
            Position.DEFENDER: 0.8,
            Position.GOALKEEPER: 0.6,
        }
        position_factor = position_weights.get(player.position, 1.0)

        # 计算综合分数
        total_score = (
            age_factor * 30
            + performance_factor * 30
            + goal_factor * 20
            + assist_factor * 15
        ) * position_factor

        return {
            "player_name": player.name,
            "age": player.age,
            "position": player.position.value,
            "total_score": round(total_score, 2),
            "age_factor": round(age_factor, 2),
            "performance_factor": round(performance_factor, 2),
            "goal_factor": round(goal_factor, 2),
            "assist_factor": round(assist_factor, 2),
            "position_factor": position_factor,
        }

    def get_iron_man(self) -> Optional[Player]:
        """获得铁人（出场时间最多的球员）"""
        if not self.players:
            return None

        return max(self.players.values(), key=lambda p: p.stats.minutes_played)


class TestPlayerStats:
    """测试球员统计业务逻辑"""

    def test_player_creation(self):
        """测试创建球员"""
        player = Player(1, "John Doe", Position.FORWARD, 100)
        assert player.id == 1
        assert player.name == "John Doe"
        assert player.position == Position.FORWARD
        assert player.team_id == 100
        assert player.age == 25
        assert player.stats.matches_played == 0

    def test_update_match_stats_basic(self):
        """测试更新比赛统计-基础"""
        player = Player(1, "Test Player", Position.MIDFIELDER, 100)
        player.update_match_stats(goals=1, assists=2, minutes_played=90)

        assert player.stats.matches_played == 1
        assert player.stats.goals == 1
        assert player.stats.assists == 2
        assert player.stats.minutes_played == 90
        assert len(player.stats.ratings) == 1

    def test_update_match_stats_with_cards(self):
        """测试更新比赛统计-包含牌"""
        player = Player(1, "Test Player", Position.DEFENDER, 100)
        player.update_match_stats(
            goals=0, assists=0, minutes_played=90, yellow_cards=1, red_cards=0
        )

        assert player.stats.yellow_cards == 1
        assert player.stats.red_cards == 0
        assert len(player.stats.cards) == 1
        assert player.stats.cards[0] == CardType.YELLOW

    def test_update_match_stats_red_card(self):
        """测试红牌统计"""
        player = Player(1, "Test Player", Position.DEFENDER, 100)
        player.update_match_stats(
            goals=0, assists=0, minutes_played=45, yellow_cards=0, red_cards=1
        )

        assert player.stats.red_cards == 1
        assert len(player.stats.cards) == 1
        assert player.stats.cards[0] == CardType.RED

    def test_get_average_rating(self):
        """测试获取平均评分"""
        player = Player(1, "Test Player", Position.FORWARD, 100)

        # 无比赛
        assert player.get_average_rating() == 0.0

        # 有比赛
        player.stats.ratings = [7.0, 8.0, 9.0]
        avg = player.get_average_rating()
        assert avg == 8.0

    def test_get_goals_per_game(self):
        """测试场均进球"""
        player = Player(1, "Test Player", Position.FORWARD, 100)

        # 无比赛
        assert player.get_goals_per_game() == 0.0

        # 有比赛
        player.stats.matches_played = 10
        player.stats.goals = 5
        assert player.get_goals_per_game() == 0.5

    def test_get_assists_per_game(self):
        """测试场均助攻"""
        player = Player(1, "Test Player", Position.MIDFIELDER, 100)

        player.stats.matches_played = 10
        player.stats.assists = 7
        assert player.get_assists_per_game() == 0.7

    def test_get_minutes_per_goal(self):
        """测试每球所需分钟"""
        player = Player(1, "Test Player", Position.FORWARD, 100)

        # 无进球
        assert player.get_minutes_per_goal() == float("inf")

        # 有进球
        player.stats.goals = 10
        player.stats.minutes_played = 900
        assert player.get_minutes_per_goal() == 90

    def test_player_analyzer_add_player(self):
        """测试添加球员到分析器"""
        analyzer = PlayerAnalyzer()
        player = Player(1, "Test Player", Position.FORWARD, 100)

        analyzer.add_player(player)
        assert len(analyzer.players) == 1
        assert analyzer.players[1] == player

    def test_get_top_scorers(self):
        """测试获取射手榜"""
        analyzer = PlayerAnalyzer()

        # 添加球员
        for i in range(5):
            player = Player(i + 1, f"Player {i + 1}", Position.FORWARD, 100)
            player.stats.goals = 20 - i * 3
            analyzer.add_player(player)

        top_scorers = analyzer.get_top_scorers(3)
        assert len(top_scorers) == 3
        assert top_scorers[0].stats.goals == 20
        assert top_scorers[1].stats.goals == 17
        assert top_scorers[2].stats.goals == 14

    def test_get_top_assisters(self):
        """测试获取助攻榜"""
        analyzer = PlayerAnalyzer()

        players_data = [(1, "A", 10), (2, "B", 15), (3, "C", 8)]
        for pid, name, assists in players_data:
            player = Player(pid, name, Position.MIDFIELDER, 100)
            player.stats.assists = assists
            analyzer.add_player(player)

        top_assisters = analyzer.get_top_assisters(2)
        assert len(top_assisters) == 2
        assert top_assisters[0].name == "B"
        assert top_assisters[1].name == "A"

    def test_get_players_by_position(self):
        """测试根据位置获取球员"""
        analyzer = PlayerAnalyzer()

        # 添加不同位置的球员
        positions = [
            Position.FORWARD,
            Position.MIDFIELDER,
            Position.DEFENDER,
            Position.FORWARD,
            Position.GOALKEEPER,
        ]
        for i, pos in enumerate(positions):
            player = Player(i + 1, f"Player {i + 1}", pos, 100)
            analyzer.add_player(player)

        forwards = analyzer.get_players_by_position(Position.FORWARD)
        assert len(forwards) == 2
        assert all(p.position == Position.FORWARD for p in forwards)

        goalkeepers = analyzer.get_players_by_position(Position.GOALKEEPER)
        assert len(goalkeepers) == 1

    def test_get_best_rated_players(self):
        """测试获取最高评分球员"""
        analyzer = PlayerAnalyzer()

        # 添加球员
        for i in range(5):
            player = Player(i + 1, f"Player {i + 1}", Position.FORWARD, 100)
            player.stats.matches_played = 10
            player.stats.ratings = [7.0 + i * 0.5] * 5
            analyzer.add_player(player)

        best = analyzer.get_best_rated_players(min_matches=5, limit=3)
        assert len(best) == 3
        # 按评分降序排列
        assert best[0].get_average_rating() > best[1].get_average_rating()
        assert best[1].get_average_rating() > best[2].get_average_rating()

    def test_find_most_consistent_player(self):
        """测试找到最稳定的球员"""
        analyzer = PlayerAnalyzer()

        # 稳定的球员
        consistent = Player(1, "Consistent", Position.MIDFIELDER, 100)
        consistent.stats.matches_played = 10
        consistent.stats.ratings = [7.0] * 10
        analyzer.add_player(consistent)

        # 不稳定的球员
        inconsistent = Player(2, "Inconsistent", Position.FORWARD, 100)
        inconsistent.stats.matches_played = 10
        inconsistent.stats.ratings = [5.0, 9.0, 6.0, 8.0, 4.0, 10.0, 5.5, 8.5, 6.5, 7.5]
        analyzer.add_player(inconsistent)

        most_consistent = analyzer.find_most_consistent_player(min_matches=5)
        assert most_consistent.name == "Consistent"

    def test_analyze_player_performance(self):
        """测试分析球员表现"""
        analyzer = PlayerAnalyzer()
        player = Player(1, "Test Player", Position.FORWARD, 100)

        # 设置一些数据
        player.stats.matches_played = 20
        player.stats.goals = 10
        player.stats.assists = 5
        player.stats.minutes_played = 1800
        player.stats.ratings = [7.0] * 20
        analyzer.add_player(player)

        analysis = analyzer.analyze_player_performance(1)
        assert analysis["player_name"] == "Test Player"
        assert analysis["matches_played"] == 20
        assert analysis["goals"] == 10
        assert analysis["assists"] == 5
        assert analysis["goals_per_game"] == 0.5
        assert analysis["assists_per_game"] == 0.25
        assert analysis["minutes_per_match"] == 90
        assert analysis["minutes_per_goal"] == 180
        assert analysis["average_rating"] == 7.0
        assert analysis["goal_involvement"] == 15
        assert analysis["goal_involvement_per_game"] == 0.75

    def test_compare_players(self):
        """测试比较球员"""
        analyzer = PlayerAnalyzer()

        # 球员1 - 更好的射手
        p1 = Player(1, "Striker", Position.FORWARD, 100)
        p1.stats.matches_played = 10
        p1.stats.goals = 10
        p1.stats.assists = 2
        p1.stats.ratings = [8.0] * 10

        # 球员2 - 更好的组织者
        p2 = Player(2, "Playmaker", Position.MIDFIELDER, 100)
        p2.stats.matches_played = 10
        p2.stats.goals = 3
        p2.stats.assists = 8
        p2.stats.ratings = [7.5] * 10

        analyzer.add_player(p1)
        analyzer.add_player(p2)

        comparison = analyzer.compare_players(1, 2)
        assert comparison["player1"]["name"] == "Striker"
        assert comparison["player2"]["name"] == "Playmaker"
        assert comparison["comparison"]["better_goals"] == "Striker"
        assert comparison["comparison"]["better_assists"] == "Playmaker"
        assert comparison["comparison"]["better_rating"] == "Striker"

    def test_find_potential_star(self):
        """测试找到潜在新星"""
        analyzer = PlayerAnalyzer()

        # 年轻球员
        young_star = Player(1, "Young Star", Position.FORWARD, 100)
        young_star.age = 20
        young_star.stats.matches_played = 10
        young_star.stats.goals = 5
        young_star.stats.assists = 3
        young_star.stats.ratings = [7.5] * 10

        # 普通年轻球员
        normal_young = Player(2, "Normal Young", Position.MIDFIELDER, 100)
        normal_young.age = 21
        normal_young.stats.matches_played = 10
        normal_young.stats.goals = 1
        normal_young.stats.assists = 2
        normal_young.stats.ratings = [6.5] * 10

        # 老球员（不符合条件）
        veteran = Player(3, "Veteran", Position.FORWARD, 100)
        veteran.age = 30
        veteran.stats.matches_played = 10
        veteran.stats.goals = 10
        veteran.stats.ratings = [8.0] * 10

        analyzer.add_player(young_star)
        analyzer.add_player(normal_young)
        analyzer.add_player(veteran)

        stars = analyzer.find_potential_star(min_age=18, max_age=23)
        assert len(stars) == 2
        assert stars[0].name == "Young Star"
        assert stars[1].name == "Normal Young"

    def test_get_discipline_records(self):
        """测试纪律记录"""
        analyzer = PlayerAnalyzer()

        # 添加不同纪律记录的球员
        dirty_player = Player(1, "Dirty", Position.DEFENDER, 100)
        dirty_player.stats.matches_played = 10
        dirty_player.stats.yellow_cards = 8
        dirty_player.stats.red_cards = 2

        clean_player = Player(2, "Clean", Position.MIDFIELDER, 100)
        clean_player.stats.matches_played = 15
        clean_player.stats.yellow_cards = 0
        clean_player.stats.red_cards = 0

        analyzer.add_player(dirty_player)
        analyzer.add_player(clean_player)

        records = analyzer.get_discipline_records()
        assert len(records["most_yellow_cards"]) == 1
        assert records["most_yellow_cards"][0].name == "Dirty"
        assert len(records["most_red_cards"]) == 1
        assert records["most_red_cards"][0].name == "Dirty"
        assert len(records["cleanest_players"]) == 1
        assert records["cleanest_players"][0].name == "Clean"

    def test_calculate_player_value(self):
        """测试计算球员价值"""
        analyzer = PlayerAnalyzer()

        # 年轻前锋
        young_forward = Player(1, "Young Forward", Position.FORWARD, 100)
        young_forward.age = 22
        young_forward.stats.matches_played = 20
        young_forward.stats.goals = 10
        young_forward.stats.assists = 5
        young_forward.stats.ratings = [7.5] * 20

        # 年老后卫
        old_defender = Player(2, "Old Defender", Position.DEFENDER, 100)
        old_defender.age = 32
        old_defender.stats.matches_played = 20
        old_defender.stats.goals = 0
        old_defender.stats.assists = 2
        old_defender.stats.ratings = [6.5] * 20

        analyzer.add_player(young_forward)
        analyzer.add_player(old_defender)

        value1 = analyzer.calculate_player_value(1)
        value2 = analyzer.calculate_player_value(2)

        # 年轻前锋应该有更高价值
        assert value1["total_score"] > value2["total_score"]
        assert value1["age_factor"] > value2["age_factor"]
        assert value1["position_factor"] > value2["position_factor"]

    def test_get_iron_man(self):
        """测试铁人"""
        analyzer = PlayerAnalyzer()

        players_data = [
            (1, "Iron", 2700),  # 30场
            (2, "Regular", 1800),  # 20场
            (3, "Part-time", 900),  # 10场
        ]

        for pid, name, minutes in players_data:
            player = Player(pid, name, Position.MIDFIELDER, 100)
            player.stats.minutes_played = minutes
            analyzer.add_player(player)

        iron_man = analyzer.get_iron_man()
        assert iron_man.name == "Iron"
        assert iron_man.stats.minutes_played == 2700

    def test_empty_analyzer(self):
        """测试空分析器"""
        analyzer = PlayerAnalyzer()

        assert analyzer.get_top_scorers() == []
        assert analyzer.get_top_assisters() == []
        assert analyzer.get_players_by_position(Position.FORWARD) == []
        assert analyzer.get_best_rated_players() == []
        assert analyzer.find_most_consistent_player() is None
        assert analyzer.find_potential_star() == []
        assert analyzer.get_iron_man() is None

        analysis = analyzer.analyze_player_performance(1)
        assert "error" in analysis

        comparison = analyzer.compare_players(1, 2)
        assert "error" in comparison

        value = analyzer.calculate_player_value(1)
        assert "error" in value
