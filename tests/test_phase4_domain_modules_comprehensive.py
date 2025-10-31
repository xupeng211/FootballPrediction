"""
Phase 4: Domain模块综合测试
覆盖所有领域层的实体、值对象、领域服务、事件系统等核心组件
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class TestDomainEntities:
    """测试领域实体"""

    def test_match_entity(self):
        """测试比赛实体"""

        class MatchStatus(Enum):
            SCHEDULED = "scheduled"
            IN_PROGRESS = "in_progress"
            COMPLETED = "completed"
            CANCELLED = "cancelled"

        class Match:
            def __init__(self, id: str, home_team_id: str, away_team_id: str,
                        scheduled_start: datetime, venue_id: str = None):
                self.id = id
                self.home_team_id = home_team_id
                self.away_team_id = away_team_id
                self.scheduled_start = scheduled_start
                self.venue_id = venue_id
                self.status = MatchStatus.SCHEDULED
                self.home_score = 0
                self.away_score = 0
                self.actual_start = None
                self.actual_end = None
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

            def start_match(self):
                if self.status != MatchStatus.SCHEDULED:
                    raise ValueError("Match can only be started from SCHEDULED status")
                self.status = MatchStatus.IN_PROGRESS
                self.actual_start = datetime.now()
                self.updated_at = datetime.now()

            def finish_match(self, home_score: int, away_score: int):
                if self.status != MatchStatus.IN_PROGRESS:
                    raise ValueError("Match can only be finished from IN_PROGRESS status")
                self.home_score = home_score
                self.away_score = away_score
                self.status = MatchStatus.COMPLETED
                self.actual_end = datetime.now()
                self.updated_at = datetime.now()

            def cancel_match(self, reason: str = None):
                if self.status == MatchStatus.COMPLETED:
                    raise ValueError("Cannot cancel completed match")
                self.status = MatchStatus.CANCELLED
                self.updated_at = datetime.now()

            def update_score(self, home_score: int, away_score: int):
                if self.status != MatchStatus.IN_PROGRESS:
                    raise ValueError("Score can only be updated during IN_PROGRESS status")
                self.home_score = home_score
                self.away_score = away_score
                self.updated_at = datetime.now()

            def get_duration(self) -> Optional[timedelta]:
                if self.actual_start and self.actual_end:
                    return self.actual_end - self.actual_start
                return None

            def __str__(self):
                return f"Match({self.id}): {self.home_team_id} vs {self.away_team_id}"

            def __repr__(self):
                return f"Match(id={self.id}, status={self.status.value}, " \
                       f"score={self.home_score}-{self.away_score})"

        # 测试比赛实体创建
        match_id = str(uuid.uuid4())
        scheduled_time = datetime.now() + timedelta(hours=2)
        match = Match(
            id=match_id,
            home_team_id="team_1",
            away_team_id="team_2",
            scheduled_start=scheduled_time,
            venue_id="venue_1"
        )

        assert match.id == match_id
        assert match.home_team_id == "team_1"
        assert match.away_team_id == "team_2"
        assert match.status == MatchStatus.SCHEDULED
        assert match.home_score == 0
        assert match.away_score    == 0

        # 测试开始比赛
        match.start_match()
        assert match.status    == MatchStatus.IN_PROGRESS
        assert match.actual_start is not None

        # 测试更新比分
        match.update_score(2, 1)
        assert match.home_score == 2
        assert match.away_score    == 1

        # 测试结束比赛
        match.finish_match(3, 1)
        assert match.status == MatchStatus.COMPLETED
        assert match.home_score == 3
        assert match.away_score    == 1
        assert match.actual_end is not None

        # 测试比赛持续时间
        duration = match.get_duration()
        assert duration is not None
        assert isinstance(duration, timedelta)

        # 测试异常情况
        with pytest.raises(ValueError):
            # 试图取消已完成的比赛
            match.cancel_match()

        # 测试比赛取消
        match2 = Match("match_2", "team_1", "team_2", scheduled_time)
        match2.cancel_match("Weather conditions")
        assert match2.status    == MatchStatus.CANCELLED

    def test_team_entity(self):
        """测试球队实体"""

        class Team:
            def __init__(self, id: str, name: str, abbreviation: str,
                        founded_year: int, league_id: str):
                self.id = id
                self.name = name
                self.abbreviation = abbreviation
                self.founded_year = founded_year
                self.league_id = league_id
                self.home_venue_id = None
                self.is_active = True
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

            def set_home_venue(self, venue_id: str):
                self.home_venue_id = venue_id
                self.updated_at = datetime.now()

            def activate(self):
                if self.is_active:
                    return
                self.is_active = True
                self.updated_at = datetime.now()

            def deactivate(self):
                if not self.is_active:
                    return
                self.is_active = False
                self.updated_at = datetime.now()

            def update_name(self, new_name: str):
                if not new_name or not new_name.strip():
                    raise ValueError("Team name cannot be empty")
                self.name = new_name.strip()
                self.updated_at = datetime.now()

            def get_age(self) -> int:
                return datetime.now().year - self.founded_year

            def __str__(self):
                return f"{self.name} ({self.abbreviation})"

            def __repr__(self):
                return f"Team(id={self.id}, name={self.name}, active={self.is_active})"

        # 测试球队实体创建
        team = Team(
            id="team_1",
            name="Real Madrid",
            abbreviation="RMA",
            founded_year=1902,
            league_id="la_liga"
        )

        assert team.id == "team_1"
        assert team.name == "Real Madrid"
        assert team.abbreviation == "RMA"
        assert team.founded_year    == 1902
        assert team.is_active is True

        # 测试设置主场
        team.set_home_venue("santiago_bernabeu")
        assert team.home_venue_id    == "santiago_bernabeu"

        # 测试球队年龄计算
        age = team.get_age()
        current_year = datetime.now().year
        assert age    == current_year - 1902

        # 测试更新名称
        team.update_name("Real Madrid CF")
        assert team.name    == "Real Madrid CF"

        # 测试无效名称
        with pytest.raises(ValueError):
            team.update_name("")

        # 测试激活/停用
        team.deactivate()
        assert team.is_active is False

        team.activate()
        assert team.is_active is True

    def test_prediction_entity(self):
        """测试预测实体"""

        class PredictionStatus(Enum):
            PENDING = "pending"
            PROCESSING = "processing"
            COMPLETED = "completed"
            FAILED = "failed"

        class Prediction:
            def __init__(self, id: str, match_id: str, user_id: str,
                        predicted_home_score: int, predicted_away_score: int,
                        confidence: float = None):
                if not 0 <= confidence <= 1 if confidence else True:
                    raise ValueError("Confidence must be between 0 and 1")

                self.id = id
                self.match_id = match_id
                self.user_id = user_id
                self.predicted_home_score = predicted_home_score
                self.predicted_away_score = predicted_away_score
                self.confidence = confidence
                self.status = PredictionStatus.PENDING
                self.algorithm_used = None
                self.processing_time_ms = None
                self.actual_home_score = None
                self.actual_away_score = None
                self.is_correct = None
                self.accuracy_score = None
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

            def start_processing(self, algorithm: str):
                if self.status != PredictionStatus.PENDING:
                    raise ValueError("Prediction can only be processed from PENDING status")
                self.status = PredictionStatus.PROCESSING
                self.algorithm_used = algorithm
                self.updated_at = datetime.now()

            def complete_processing(self, processing_time_ms: int):
                if self.status != PredictionStatus.PROCESSING:
                    raise ValueError("Prediction can only be completed from PROCESSING status")
                self.status = PredictionStatus.COMPLETED
                self.processing_time_ms = processing_time_ms
                self.updated_at = datetime.now()

            def fail_processing(self, error_message: str):
                if self.status == PredictionStatus.COMPLETED:
                    raise ValueError("Cannot fail completed prediction")
                self.status = PredictionStatus.FAILED
                self.error_message = error_message
                self.updated_at = datetime.now()

            def set_actual_result(self, actual_home_score: int, actual_away_score: int):
                self.actual_home_score = actual_home_score
                self.actual_away_score = actual_away_score
                self._calculate_accuracy()
                self.updated_at = datetime.now()

            def _calculate_accuracy(self):
                if self.actual_home_score is None or self.actual_away_score is None:
                    return

                # 准确预测比分
                if (self.predicted_home_score == self.actual_home_score and
                    self.predicted_away_score == self.actual_away_score):
                    self.is_correct = True
                    self.accuracy_score = 1.0
                    return

                # 预测正确胜负关系
                predicted_outcome = self._get_outcome(self.predicted_home_score, self.predicted_away_score)
                actual_outcome = self._get_outcome(self.actual_home_score, self.actual_away_score)

                if predicted_outcome == actual_outcome:
                    self.is_correct = True
                    self.accuracy_score = 0.5
                else:
                    self.is_correct = False
                    self.accuracy_score = 0.0

            def _get_outcome(self, home_score: int, away_score: int) -> str:
                if home_score > away_score:
                    return "home_win"
                elif home_score < away_score:
                    return "away_win"
                else:
                    return "draw"

            def get_predicted_score(self) -> str:
                return f"{self.predicted_home_score}-{self.predicted_away_score}"

            def get_actual_score(self) -> Optional[str]:
                if (self.actual_home_score is not None and
                    self.actual_away_score is not None):
                    return f"{self.actual_home_score}-{self.actual_away_score}"
                return None

        # 测试预测实体创建
        prediction = Prediction(
            id="pred_1",
            match_id="match_1",
            user_id="user_1",
            predicted_home_score=2,
            predicted_away_score=1,
            confidence=0.85
        )

        assert prediction.id == "pred_1"
        assert prediction.predicted_home_score == 2
        assert prediction.predicted_away_score == 1
        assert prediction.confidence == 0.85
        assert prediction.status    == PredictionStatus.PENDING

        # 测试开始处理
        prediction.start_processing("neural_network_v2")
        assert prediction.status == PredictionStatus.PROCESSING
        assert prediction.algorithm_used    == "neural_network_v2"

        # 测试完成处理
        prediction.complete_processing(1500)
        assert prediction.status == PredictionStatus.COMPLETED
        assert prediction.processing_time_ms    == 1500

        # 测试设置实际结果 - 完全准确
        prediction.set_actual_result(2, 1)
        assert prediction.actual_home_score == 2
        assert prediction.actual_away_score == 1
        assert prediction.is_correct is True
        assert prediction.accuracy_score    == 1.0

        # 测试部分准确预测
        prediction2 = Prediction("pred_2", "match_2", "user_2", 1, 1)
        prediction2.set_actual_result(2, 2)  # 预测平局，实际平局
        assert prediction2.is_correct is True
        assert prediction2.accuracy_score    == 0.5

        # 测试错误预测
        prediction3 = Prediction("pred_3", "match_3", "user_3", 1, 0)
        prediction3.set_actual_result(0, 2)  # 预测主胜，实际客胜
        assert prediction3.is_correct is False
        assert prediction3.accuracy_score    == 0.0


class TestValueObjects:
    """测试值对象"""

    def test_score_value_object(self):
        """测试比分值对象"""

        class Score:
            def __init__(self, home_score: int, away_score: int):
                if home_score < 0 or away_score < 0:
                    raise ValueError("Scores cannot be negative")
                self.home_score = home_score
                self.away_score = away_score

            def __eq__(self, other):
                if not isinstance(other, Score):
                    return False
                return (self.home_score == other.home_score and
                       self.away_score == other.away_score)

            def __hash__(self):
                return hash((self.home_score, self.away_score))

            def __str__(self):
                return f"{self.home_score}-{self.away_score}"

            def __repr__(self):
                return f"Score({self.home_score}, {self.away_score})"

            def get_total_goals(self) -> int:
                return self.home_score + self.away_score

            def get_goal_difference(self) -> int:
                return self.home_score - self.away_score

            def is_draw(self) -> bool:
                return self.home_score == self.away_score

            def get_winner(self) -> Optional[str]:
                if self.home_score > self.away_score:
                    return "home"
                elif self.away_score > self.home_score:
                    return "away"
                return None

            def add_goals(self, home_goals: int = 0, away_goals: int = 0):
                return Score(
                    self.home_score + home_goals,
                    self.away_score + away_goals
                )

        # 测试比分值对象创建
        score = Score(2, 1)
        assert score.home_score == 2
        assert score.away_score    == 1
        assert str(score) == "2-1"

        # 测试相等性
        score2 = Score(2, 1)
        score3 = Score(1, 2)
        assert score    == score2
        assert score    != score3

        # 测试哈希（可用于集合）
        score_set = {score, score2, score3}
        assert len(score_set) == 2  # score和score2相同

        # 测试计算方法
        assert score.get_total_goals() == 3
        assert score.get_goal_difference() == 1
        assert score.is_draw() is False
        assert score.get_winner() == "home"

        # 测试平局
        draw_score = Score(1, 1)
        assert draw_score.is_draw() is True
        assert draw_score.get_winner() is None

        # 测试添加进球
        new_score = score.add_goals(1, 0)
        assert new_score.home_score == 3
        assert new_score.away_score == 1
        assert score.home_score    == 2  # 原对象不变

        # 测试异常情况
        with pytest.raises(ValueError):
            Score(-1, 1)

    def test_odds_value_object(self):
        """测试赔率值对象"""

        class Odds:
            def __init__(self, home_win: Decimal, draw: Decimal, away_win: Decimal):
                if any(o <= 0 for o in [home_win, draw, away_win]):
                    raise ValueError("Odds must be positive")
                self.home_win = Decimal(str(home_win))
                self.draw = Decimal(str(draw))
                self.away_win = Decimal(str(away_win))

            def __eq__(self, other):
                if not isinstance(other, Odds):
                    return False
                return (self.home_win == other.home_win and
                       self.draw == other.draw and
                       self.away_win == other.away_win)

            def __str__(self):
                return f"{self.home_win}/{self.draw}/{self.away_win}"

            def get_implied_probabilities(self) -> Dict[str, Decimal]:
                total = (Decimal('1') / self.home_win +
                        Decimal('1') / self.draw +
                        Decimal('1') / self.away_win)

                return {
                    "home_win": (Decimal('1') / self.home_win) / total,
                    "draw": (Decimal('1') / self.draw) / total,
                    "away_win": (Decimal('1') / self.away_win) / total
                }

            def get_vig(self) -> Decimal:
                probabilities = self.get_implied_probabilities()
                total_probability = sum(probabilities.values())
                return total_probability - Decimal('1')

            def get_fair_odds(self) -> 'Odds':
                probabilities = self.get_implied_probabilities()
                return Odds(
                    home_win=Decimal('1') / probabilities['home_win'],
                    draw=Decimal('1') / probabilities['draw'],
                    away_win=Decimal('1') / probabilities['away_win']
                )

        # 测试赔率值对象创建
        odds = Odds(Decimal('2.5'), Decimal('3.2'), Decimal('2.8'))
        assert odds.home_win    == Decimal('2.5')
        assert odds.draw    == Decimal('3.2')
        assert odds.away_win    == Decimal('2.8')

        # 测试隐含概率计算
        probabilities = odds.get_implied_probabilities()
        assert all(0 < p < 1 for p in probabilities.values())
        total_prob = sum(probabilities.values())
        assert total_prob > Decimal('1')  # 包含抽水

        # 测试抽水计算
        vig = odds.get_vig()
        assert vig > 0

        # 测试公平赔率
        fair_odds = odds.get_fair_odds()
        assert fair_odds.home_win < odds.home_win  # 公平赔率更高（概率更大）
        fair_probabilities = fair_odds.get_implied_probabilities()
        fair_total = sum(fair_probabilities.values())
        assert abs(fair_total - Decimal('1')) < Decimal('0.001')  # 总概率接近1

    def test_money_value_object(self):
        """测试金额值对象"""

        class Money:
            def __init__(self, amount: Union[int, float, str, Decimal], currency: str = "USD"):
                self.amount = Decimal(str(amount))
                if self.amount < 0:
                    raise ValueError("Amount cannot be negative")
                self.currency = currency.upper()

            def __eq__(self, other):
                if not isinstance(other, Money):
                    return False
                return (self.amount == other.amount and
                       self.currency == other.currency)

            def __add__(self, other):
                if not isinstance(other, Money):
                    raise TypeError("Can only add Money to Money")
                if self.currency != other.currency:
                    raise ValueError("Cannot add different currencies")
                return Money(self.amount + other.amount, self.currency)

            def __sub__(self, other):
                if not isinstance(other, Money):
                    raise TypeError("Can only subtract Money from Money")
                if self.currency != other.currency:
                    raise ValueError("Cannot subtract different currencies")
                result = self.amount - other.amount
                if result < 0:
                    raise ValueError("Result cannot be negative")
                return Money(result, self.currency)

            def __mul__(self, multiplier: Union[int, float, Decimal]):
                result = self.amount * Decimal(str(multiplier))
                if result < 0:
                    raise ValueError("Result cannot be negative")
                return Money(result, self.currency)

            def __str__(self):
                return f"{self.currency} {self.amount:.2f}"

            def __repr__(self):
                return f"Money({self.amount}, {self.currency})"

        # 测试金额值对象创建
        money1 = Money(100.50, "USD")
        money2 = Money("50.25", "USD")

        assert money1.currency == "USD"
        assert money1.amount    == Decimal('100.50')

        # 测试货币运算
        total = money1 + money2
        assert total.amount    == Decimal('150.75')

        difference = money1 - Money("25.00", "USD")
        assert difference.amount    == Decimal('75.50')

        doubled = money1 * 2
        assert doubled.amount    == Decimal('201.00')

        # 测试不同货币错误
        money_eur = Money(100, "EUR")
        with pytest.raises(ValueError):
            money1 + money_eur

        # 测试负金额错误
        with pytest.raises(ValueError):
            Money(-10)


class TestDomainServices:
    """测试领域服务"""

    def test_prediction_calculation_service(self):
        """测试预测计算服务"""

        class PredictionCalculationService:
            def __init__(self):
                self.algorithms = {
                    "simple_average": self._simple_average,
                    "weighted_recent": self._weighted_recent,
                    "head_to_head": self._head_to_head
                }

            def calculate_prediction(self, algorithm: str, match_history: List[Dict],
                                   team_stats: Dict) -> Dict[str, Any]:
                if algorithm not in self.algorithms:
                    raise ValueError(f"Unknown algorithm: {algorithm}")

                return self.algorithms[algorithm](match_history, team_stats)

            def _simple_average(self, match_history: List[Dict], team_stats: Dict) -> Dict:
                """简单平均算法"""
                if not match_history:
                    return {"home_score": 1, "away_score": 1, "confidence": 0.3}

                total_goals = 0
                home_wins = 0
                away_wins = 0
                draws = 0

                for match in match_history:
                    goals = match.get("home_score", 0) + match.get("away_score", 0)
                    total_goals += goals

                    if match.get("home_score", 0) > match.get("away_score", 0):
                        home_wins += 1
                    elif match.get("away_score", 0) > match.get("home_score", 0):
                        away_wins += 1
                    else:
                        draws += 1

                avg_goals = total_goals / len(match_history)
                total_matches = len(match_history)

                # 基于历史结果预测
                if home_wins / total_matches > 0.4:
                    home_score = min(int(avg_goals * 0.6), 5)
                    away_score = max(int(avg_goals * 0.4) - 1, 0)
                elif away_wins / total_matches > 0.4:
                    home_score = max(int(avg_goals * 0.4) - 1, 0)
                    away_score = min(int(avg_goals * 0.6), 5)
                else:
                    home_score = away_score = int(avg_goals / 2)

                confidence = min(0.3 + (total_matches / 50), 0.8)

                return {
                    "home_score": home_score,
                    "away_score": away_score,
                    "confidence": confidence,
                    "algorithm": "simple_average",
                    "data_points": total_matches
                }

            def _weighted_recent(self, match_history: List[Dict], team_stats: Dict) -> Dict:
                """加权最近表现算法"""
                if not match_history:
                    return {"home_score": 1, "away_score": 1, "confidence": 0.3}

                # 最近比赛权重更高
                weighted_goals = 0
                total_weight = 0

                for i, match in enumerate(reversed(match_history[:10])):  # 只取最近10场
                    weight = (i + 1) / 10  # 最近的权重更高
                    goals = match.get("home_score", 0) + match.get("away_score", 0)
                    weighted_goals += goals * weight
                    total_weight += weight

                avg_weighted_goals = weighted_goals / total_weight if total_weight > 0 else 2

                # 基于球队统计调整
                home_attack = team_stats.get("home_attack_strength", 1.0)
                away_defense = team_stats.get("away_defense_strength", 1.0)

                expected_home_goals = avg_weighted_goals * home_attack * away_defense
                expected_away_goals = avg_weighted_goals * (2 - home_attack) * (2 - away_defense)

                home_score = max(0, min(int(expected_home_goals), 6))
                away_score = max(0, min(int(expected_away_goals), 6))

                confidence = min(0.4 + (len(match_history) / 40), 0.85)

                return {
                    "home_score": home_score,
                    "away_score": away_score,
                    "confidence": confidence,
                    "algorithm": "weighted_recent",
                    "data_points": min(len(match_history), 10)
                }

            def _head_to_head(self, match_history: List[Dict], team_stats: Dict) -> Dict:
                """历史对战算法"""
                if not match_history:
                    return {"home_score": 1, "away_score": 1, "confidence": 0.2}

                # 分析历史对战数据
                home_wins = sum(1 for m in match_history
                              if m.get("home_score", 0) > m.get("away_score", 0))
                away_wins = sum(1 for m in match_history
                              if m.get("away_score", 0) > m.get("home_score", 0))
                draws = len(match_history) - home_wins - away_wins

                # 计算平均进球
                avg_home_goals = sum(m.get("home_score", 0) for m in match_history) / len(match_history)
                avg_away_goals = sum(m.get("away_score", 0) for m in match_history) / len(match_history)

                # 基于历史倾向调整
                if home_wins > away_wins and home_wins > draws:
                    # 主队优势明显
                    home_score = int(avg_home_goals * 1.2)
                    away_score = int(avg_away_goals * 0.8)
                elif away_wins > home_wins and away_wins > draws:
                    # 客队优势明显
                    home_score = int(avg_home_goals * 0.8)
                    away_score = int(avg_away_goals * 1.2)
                else:
                    # 势均力敌
                    home_score = int(avg_home_goals)
                    away_score = int(avg_away_goals)

                confidence = min(0.5 + (len(match_history) / 20), 0.9)

                return {
                    "home_score": max(0, home_score),
                    "away_score": max(0, away_score),
                    "confidence": confidence,
                    "algorithm": "head_to_head",
                    "data_points": len(match_history),
                    "head_to_head_stats": {
                        "home_wins": home_wins,
                        "away_wins": away_wins,
                        "draws": draws
                    }
                }

        # 测试预测计算服务
        service = PredictionCalculationService()

        # 准备测试数据
        match_history = [
            {"home_score": 2, "away_score": 1, "date": "2024-01-01"},
            {"home_score": 1, "away_score": 1, "date": "2024-01-15"},
            {"home_score": 3, "away_score": 0, "date": "2024-02-01"},
            {"home_score": 1, "away_score": 2, "date": "2024-02-15"}
        ]

        team_stats = {
            "home_attack_strength": 1.2,
            "away_defense_strength": 0.9
        }

        # 测试简单平均算法
        result1 = service.calculate_prediction("simple_average", match_history, team_stats)
        assert "home_score" in result1
        assert "away_score" in result1
        assert "confidence" in result1
        assert result1["algorithm"]    == "simple_average"
        assert 0 <= result1["confidence"] <= 1

        # 测试加权最近算法
        result2 = service.calculate_prediction("weighted_recent", match_history, team_stats)
        assert result2["algorithm"]    == "weighted_recent"
        assert result2["data_points"] <= 10

        # 测试历史对战算法
        result3 = service.calculate_prediction("head_to_head", match_history, team_stats)
        assert result3["algorithm"]    == "head_to_head"
        assert "head_to_head_stats" in result3

        # 测试无效算法
        with pytest.raises(ValueError):
            service.calculate_prediction("invalid_algorithm", match_history, team_stats)

    def test_match_analytics_service(self):
        """测试比赛分析服务"""

        class MatchAnalyticsService:
            def analyze_team_form(self, team_matches: List[Dict], team_side: str = "home") -> Dict[str, Any]:
                """分析球队状态"""
                if not team_matches:
                    return {"form_score": 0, "trend": "unknown", "recommendation": "insufficient_data"}

                # 计算最近状态
                recent_matches = team_matches[:5]  # 最近5场比赛
                points = 0

                for match in recent_matches:
                    if team_side == "home":
                        team_score = match.get("home_score", 0)
                        opponent_score = match.get("away_score", 0)
                    else:
                        team_score = match.get("away_score", 0)
                        opponent_score = match.get("home_score", 0)

                    if team_score > opponent_score:
                        points += 3
                    elif team_score == opponent_score:
                        points += 1

                max_points = len(recent_matches) * 3
                form_score = points / max_points

                # 分析趋势
                if form_score >= 0.8:
                    trend = "excellent"
                    recommendation = "strong_favorite"
                elif form_score >= 0.6:
                    trend = "good"
                    recommendation = "favorite"
                elif form_score >= 0.4:
                    trend = "average"
                    recommendation = "neutral"
                else:
                    trend = "poor"
                    recommendation = "underdog"

                return {
                    "form_score": round(form_score, 3),
                    "trend": trend,
                    "recommendation": recommendation,
                    "recent_points": points,
                    "matches_analyzed": len(recent_matches)
                }

            def analyze_head_to_head(self, h2h_matches: List[Dict]) -> Dict[str, Any]:
                """分析历史对战"""
                if not h2h_matches:
                    return {"dominance": "balanced", "win_rate_diff": 0, "insufficient_data": True}

                home_wins = sum(1 for m in h2h_matches
                              if m.get("home_score", 0) > m.get("away_score", 0))
                away_wins = sum(1 for m in h2h_matches
                              if m.get("away_score", 0) > m.get("home_score", 0))
                draws = len(h2h_matches) - home_wins - away_wins

                home_win_rate = home_wins / len(h2h_matches)
                away_win_rate = away_wins / len(h2h_matches)
                win_rate_diff = abs(home_win_rate - away_win_rate)

                if win_rate_diff >= 0.3:
                    dominance = "home_dominant" if home_win_rate > away_win_rate else "away_dominant"
                elif win_rate_diff >= 0.15:
                    dominance = "slight_advantage"
                else:
                    dominance = "balanced"

                # 计算平均进球
                avg_home_goals = sum(m.get("home_score", 0) for m in h2h_matches) / len(h2h_matches)
                avg_away_goals = sum(m.get("away_score", 0) for m in h2h_matches) / len(h2h_matches)

                return {
                    "dominance": dominance,
                    "home_win_rate": round(home_win_rate, 3),
                    "away_win_rate": round(away_win_rate, 3),
                    "win_rate_diff": round(win_rate_diff, 3),
                    "total_matches": len(h2h_matches),
                    "home_wins": home_wins,
                    "away_wins": away_wins,
                    "draws": draws,
                    "avg_home_goals": round(avg_home_goals, 2),
                    "avg_away_goals": round(avg_away_goals, 2),
                    "avg_total_goals": round(avg_home_goals + avg_away_goals, 2)
                }

            def calculate_prediction_confidence(self, team_form: Dict, h2h_analysis: Dict,
                                              recent_performance: Dict) -> float:
                """计算预测置信度"""
                confidence_factors = []

                # 球队状态权重
                if not team_form.get("insufficient_data"):
                    form_score = team_form["form_score"]
                    confidence_factors.append(min(form_score * 1.5, 1.0))

                # 历史对战权重
                if not h2h_analysis.get("insufficient_data"):
                    win_rate_diff = h2h_analysis["win_rate_diff"]
                    # 历史对战越一边倒，置信度越高
                    confidence_factors.append(min(win_rate_diff * 2, 1.0))

                # 最近表现权重
                if "consistency_score" in recent_performance:
                    consistency = recent_performance["consistency_score"]
                    confidence_factors.append(consistency)

                # 数据充分性权重
                total_matches = (team_form.get("matches_analyzed", 0) +
                               h2h_analysis.get("total_matches", 0))
                data_sufficiency = min(total_matches / 20, 1.0)
                confidence_factors.append(data_sufficiency)

                if not confidence_factors:
                    return 0.3  # 默认低置信度

                # 加权平均
                return round(sum(confidence_factors) / len(confidence_factors), 3)

        # 测试比赛分析服务
        service = MatchAnalyticsService()

        # 准备测试数据
        team_matches = [
            {"home_score": 2, "away_score": 1},
            {"home_score": 1, "away_score": 1},
            {"home_score": 3, "away_score": 0},
            {"home_score": 0, "away_score": 1},
            {"home_score": 2, "away_score": 0}
        ]

        h2h_matches = [
            {"home_score": 2, "away_score": 1},
            {"home_score": 1, "away_score": 2},
            {"home_score": 3, "away_score": 1},
            {"home_score": 1, "away_score": 1}
        ]

        # 测试球队状态分析
        form_analysis = service.analyze_team_form(team_matches, "home")
        assert "form_score" in form_analysis
        assert "trend" in form_analysis
        assert "recommendation" in form_analysis
        assert 0 <= form_analysis["form_score"] <= 1

        # 测试历史对战分析
        h2h_analysis = service.analyze_head_to_head(h2h_matches)
        assert "dominance" in h2h_analysis
        assert "home_win_rate" in h2h_analysis
        assert "total_matches" in h2h_analysis
        assert not h2h_analysis.get("insufficient_data")

        # 测试置信度计算
        recent_performance = {"consistency_score": 0.8}
        confidence = service.calculate_prediction_confidence(
            form_analysis, h2h_analysis, recent_performance
        )
        assert 0 <= confidence <= 1

        # 测试数据不足情况
        empty_form = service.analyze_team_form([], "home")
        assert empty_form["insufficient_data"]

        empty_h2h = service.analyze_head_to_head([])
        assert empty_h2h["insufficient_data"]


class TestDomainEvents:
    """测试领域事件"""

    def test_domain_event_base(self):
        """测试领域事件基类"""

        class DomainEvent:
            def __init__(self):
                self.event_id = str(uuid.uuid4())
                self.occurred_at = datetime.now()
                self.version = 1

            def __eq__(self, other):
                if not isinstance(other, DomainEvent):
                    return False
                return self.event_id == other.event_id

            def __hash__(self):
                return hash(self.event_id)

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "event_id": self.event_id,
                    "event_type": self.__class__.__name__,
                    "occurred_at": self.occurred_at.isoformat(),
                    "version": self.version
                }

        # 测试事件创建
        event = DomainEvent()
        assert event.event_id is not None
        assert event.occurred_at is not None
        assert event.version    == 1

        # 测试序列化
        event_dict = event.to_dict()
        assert "event_id" in event_dict
        assert "event_type" in event_dict
        assert "occurred_at" in event_dict

    def test_match_events(self):
        """测试比赛相关事件"""

        class MatchScheduledEvent:
            def __init__(self, match_id: str, home_team_id: str, away_team_id: str,
                        scheduled_start: datetime, venue_id: str = None):
                self.match_id = match_id
                self.home_team_id = home_team_id
                self.away_team_id = away_team_id
                self.scheduled_start = scheduled_start
                self.venue_id = venue_id
                self.occurred_at = datetime.now()

        class MatchStartedEvent:
            def __init__(self, match_id: str, actual_start: datetime):
                self.match_id = match_id
                self.actual_start = actual_start
                self.occurred_at = datetime.now()

        class MatchFinishedEvent:
            def __init__(self, match_id: str, final_score: str, actual_end: datetime):
                self.match_id = match_id
                self.final_score = final_score
                self.actual_end = actual_end
                self.occurred_at = datetime.now()

        class ScoreUpdatedEvent:
            def __init__(self, match_id: str, home_score: int, away_score: int,
                        scorer: str = None, minute: int = None):
                self.match_id = match_id
                self.home_score = home_score
                self.away_score = away_score
                self.scorer = scorer
                self.minute = minute
                self.occurred_at = datetime.now()

        # 测试比赛事件
        scheduled_event = MatchScheduledEvent(
            match_id="match_1",
            home_team_id="team_1",
            away_team_id="team_2",
            scheduled_start=datetime.now() + timedelta(hours=2),
            venue_id="venue_1"
        )

        started_event = MatchStartedEvent(
            match_id="match_1",
            actual_start=datetime.now()
        )

        finished_event = MatchFinishedEvent(
            match_id="match_1",
            final_score="2-1",
            actual_end=datetime.now()
        )

        score_event = ScoreUpdatedEvent(
            match_id="match_1",
            home_score=1,
            away_score=0,
            scorer="Player1",
            minute=25
        )

        assert scheduled_event.match_id == "match_1"
        assert scheduled_event.home_team_id == "team_1"
        assert started_event.actual_start is not None
        assert finished_event.final_score == "2-1"
        assert score_event.scorer == "Player1"
        assert score_event.minute    == 25

    def test_prediction_events(self):
        """测试预测相关事件"""

        class PredictionCreatedEvent:
            def __init__(self, prediction_id: str, match_id: str, user_id: str,
                        predicted_score: str, confidence: float):
                self.prediction_id = prediction_id
                self.match_id = match_id
                self.user_id = user_id
                self.predicted_score = predicted_score
                self.confidence = confidence
                self.occurred_at = datetime.now()

        class PredictionCompletedEvent:
            def __init__(self, prediction_id: str, processing_time_ms: int,
                        algorithm_used: str):
                self.prediction_id = prediction_id
                self.processing_time_ms = processing_time_ms
                self.algorithm_used = algorithm_used
                self.occurred_at = datetime.now()

        class PredictionEvaluatedEvent:
            def __init__(self, prediction_id: str, actual_score: str,
                        is_correct: bool, accuracy_score: float):
                self.prediction_id = prediction_id
                self.actual_score = actual_score
                self.is_correct = is_correct
                self.accuracy_score = accuracy_score
                self.occurred_at = datetime.now()

        # 测试预测事件
        created_event = PredictionCreatedEvent(
            prediction_id="pred_1",
            match_id="match_1",
            user_id="user_1",
            predicted_score="2-1",
            confidence=0.85
        )

        completed_event = PredictionCompletedEvent(
            prediction_id="pred_1",
            processing_time_ms=1500,
            algorithm_used="neural_network_v2"
        )

        evaluated_event = PredictionEvaluatedEvent(
            prediction_id="pred_1",
            actual_score="2-1",
            is_correct=True,
            accuracy_score=1.0
        )

        assert created_event.confidence == 0.85
        assert completed_event.algorithm_used == "neural_network_v2"
        assert evaluated_event.is_correct is True
        assert evaluated_event.accuracy_score    == 1.0

    def test_event_aggregate(self):
        """测试事件聚合"""

        class EventAggregate:
            def __init__(self):
                self.events = []

            def add_event(self, event):
                self.events.append(event)

            def get_events_by_type(self, event_type: type) -> List:
                return [event for event in self.events if isinstance(event, event_type)]

            def get_events_since(self, since: datetime) -> List:
                return [event for event in self.events
                       if event.occurred_at >= since]

            def clear_events(self):
                self.events.clear()

            def get_event_count(self) -> int:
                return len(self.events)

        # 测试事件聚合
        aggregate = EventAggregate()

        # 添加事件
        aggregate.add_event(MatchScheduledEvent(
            "match_1", "team_1", "team_2", datetime.now()
        ))
        aggregate.add_event(PredictionCreatedEvent(
            "pred_1", "match_1", "user_1", "2-1", 0.85
        ))
        aggregate.add_event(MatchStartedEvent("match_1", datetime.now()))

        # 测试事件计数
        assert aggregate.get_event_count() == 3

        # 测试按类型获取事件
        match_events = aggregate.get_events_by_type(MatchScheduledEvent)
        prediction_events = aggregate.get_events_by_type(PredictionCreatedEvent)

        assert len(match_events) == 1
        assert len(prediction_events) == 1

        # 测试时间过滤
        yesterday = datetime.now() - timedelta(days=1)
        recent_events = aggregate.get_events_since(yesterday)
        assert len(recent_events) == 3

        future = datetime.now() + timedelta(days=1)
        future_events = aggregate.get_events_since(future)
        assert len(future_events) == 0

        # 测试清除事件
        aggregate.clear_events()
        assert aggregate.get_event_count() == 0


class TestAggregateRoots:
    """测试聚合根"""

    def test_match_aggregate_root(self):
        """测试比赛聚合根"""

        class MatchAggregateRoot:
            def __init__(self, match_id: str, home_team_id: str, away_team_id: str,
                        scheduled_start: datetime):
                self.match_id = match_id
                self.home_team_id = home_team_id
                self.away_team_id = away_team_id
                self.scheduled_start = scheduled_start
                self.status = "scheduled"
                self.home_score = 0
                self.away_score = 0
                self.predictions = []  # 预测集合
                self.events = []  # 领域事件
                self.version = 1

            def add_prediction(self, prediction_id: str, user_id: str,
                             predicted_home_score: int, predicted_away_score: int,
                             confidence: float):
                # 业务规则：比赛开始后不能添加预测
                if self.status != "scheduled":
                    raise ValueError("Cannot add prediction after match started")

                # 业务规则：不能重复预测
                if any(p["user_id"] == user_id for p in self.predictions):
                    raise ValueError("User has already predicted this match")

                prediction = {
                    "prediction_id": prediction_id,
                    "user_id": user_id,
                    "predicted_home_score": predicted_home_score,
                    "predicted_away_score": predicted_away_score,
                    "confidence": confidence,
                    "created_at": datetime.now()
                }
                self.predictions.append(prediction)

                # 发布领域事件
                self.events.append({
                    "type": "PredictionAdded",
                    "prediction_id": prediction_id,
                    "match_id": self.match_id,
                    "user_id": user_id
                })

            def start_match(self):
                if self.status != "scheduled":
                    raise ValueError("Match can only be started from scheduled status")

                self.status = "in_progress"
                self.version += 1

                # 发布领域事件
                self.events.append({
                    "type": "MatchStarted",
                    "match_id": self.match_id,
                    "started_at": datetime.now()
                })

            def update_score(self, home_score: int, away_score: int):
                if self.status != "in_progress":
                    raise ValueError("Score can only be updated during match")

                old_home_score = self.home_score
                old_away_score = self.away_score

                self.home_score = home_score
                self.away_score = away_score
                self.version += 1

                # 发布领域事件
                self.events.append({
                    "type": "ScoreUpdated",
                    "match_id": self.match_id,
                    "old_score": f"{old_home_score}-{old_away_score}",
                    "new_score": f"{home_score}-{away_score}",
                    "updated_at": datetime.now()
                })

            def finish_match(self):
                if self.status != "in_progress":
                    raise ValueError("Match can only be finished from in_progress status")

                self.status = "completed"
                self.version += 1

                # 自动评估所有预测
                evaluated_predictions = []
                for prediction in self.predictions:
                    predicted_home = prediction["predicted_home_score"]
                    predicted_away = prediction["predicted_away_score"]

                    if (predicted_home == self.home_score and
                        predicted_away == self.away_score):
                        is_correct = True
                        accuracy = 1.0
                    elif ((predicted_home > predicted_away and self.home_score > self.away_score) or
                          (predicted_home < predicted_away and self.home_score < self.away_score) or
                          (predicted_home == predicted_away and self.home_score == self.away_score)):
                        is_correct = True
                        accuracy = 0.5
                    else:
                        is_correct = False
                        accuracy = 0.0

                    evaluated_predictions.append({
                        **prediction,
                        "is_correct": is_correct,
                        "accuracy_score": accuracy
                    })

                self.predictions = evaluated_predictions

                # 发布领域事件
                self.events.append({
                    "type": "MatchFinished",
                    "match_id": self.match_id,
                    "final_score": f"{self.home_score}-{self.away_score}",
                    "total_predictions": len(self.predictions),
                    "correct_predictions": sum(1 for p in self.predictions if p["is_correct"]),
                    "finished_at": datetime.now()
                })

            def get_uncommitted_events(self):
                return self.events.copy()

            def mark_events_as_committed(self):
                self.events.clear()

        # 测试比赛聚合根
        match = MatchAggregateRoot(
            match_id="match_1",
            home_team_id="team_1",
            away_team_id="team_2",
            scheduled_start=datetime.now() + timedelta(hours=2)
        )

        # 测试添加预测
        match.add_prediction("pred_1", "user_1", 2, 1, 0.85)
        match.add_prediction("pred_2", "user_2", 1, 1, 0.70)

        assert len(match.predictions) == 2
        assert len(match.get_uncommitted_events()) == 2

        # 测试开始比赛
        match.start_match()
        assert match.status    == "in_progress"
        assert len(match.get_uncommitted_events()) == 3

        # 测试更新比分
        match.update_score(1, 0)
        match.update_score(2, 1)
        assert match.home_score == 2
        assert match.away_score    == 1
        assert len(match.get_uncommitted_events()) == 5

        # 测试结束比赛
        match.finish_match()
        assert match.status    == "completed"
        assert len(match.get_uncommitted_events()) == 6

        # 验证预测评估
        correct_predictions = [p for p in match.predictions if p["is_correct"]]
        assert len(correct_predictions) >= 1  # 至少有一个预测正确

        # 测试业务规则验证
        with pytest.raises(ValueError):
            match.add_prediction("pred_3", "user_1", 3, 0, 0.9)  # 重复预测

        with pytest.raises(ValueError):
            match.start_match()  # 比赛已结束

        # 测试事件提交
        uncommitted = match.get_uncommitted_events()
        match.mark_events_as_committed()
        assert len(match.get_uncommitted_events()) == 0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])