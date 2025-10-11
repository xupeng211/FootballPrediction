"""
历史数据策略
Historical Strategy

基于历史比赛数据和相似场景进行预测的策略。
Strategy based on historical match data and similar scenarios.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass

from .base import (
    PredictionStrategy,
    PredictionInput,
    PredictionOutput,
    StrategyType,
    StrategyMetrics,
)
from ..models.prediction import Prediction


@dataclass
class HistoricalMatch:
    """历史比赛数据结构"""

    match_id: int
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    match_date: datetime
    league_id: int
    season: str
    importance: float = 1.0  # 比赛重要性权重


@dataclass
class SimilarScenario:
    """相似场景数据"""

    matches: List[HistoricalMatch]
    similarity_score: float
    common_patterns: Dict[str, Any]


class HistoricalStrategy(PredictionStrategy):
    """历史数据预测策略

    基于以下历史数据进行预测：
    - 相同对战的历史记录
    - 相似比分场景的历史记录
    - 同赛季类似情况
    - 相似时间段的表现
    """

    def __init__(self, name: str = "historical_analyzer"):
        super().__init__(name, StrategyType.HISTORICAL)
        self._historical_matches: Dict[int, List[HistoricalMatch]] = {}
        self._team_vs_team: Dict[Tuple[int, int], List[HistoricalMatch]] = {}
        self._score_patterns: Dict[Tuple[int, int], List[HistoricalMatch]] = {}
        self._season_patterns: Dict[str, List[HistoricalMatch]] = {}
        self._min_historical_matches = 3
        self._similarity_threshold = 0.7

    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化历史策略

        Args:
            config: 配置参数，包含：
                - min_historical_matches: 最少历史比赛数
                - similarity_threshold: 相似度阈值
                - max_historical_years: 考虑的历史年数
                - weight_factors: 各种历史因素的权重
        """
        self._config = config
        self._min_historical_matches = config.get("min_historical_matches", 3)
        self._similarity_threshold = config.get("similarity_threshold", 0.7)
        self._max_historical_years = config.get("max_historical_years", 5)
        self._weight_factors = config.get(
            "weight_factors",
            {
                "direct_h2h": 0.4,  # 直接对战历史
                "similar_score_patterns": 0.25,  # 相似比分模式
                "season_performance": 0.2,  # 赛季表现
                "time_based_patterns": 0.15,  # 时间模式
            },
        )

        # 加载历史数据（实际应从数据库加载）
        await self._load_historical_data()

        self._is_initialized = True
        print(f"历史策略 '{self.name}' 初始化成功")

    async def _load_historical_data(self) -> None:
        """加载历史数据（模拟）"""
        # 实际实现中，这里应该从数据库查询历史比赛数据
        # 这里使用模拟数据
        current_year = datetime.now().year

        for year in range(current_year - self._max_historical_years, current_year + 1):
            season = f"{year-1}/{year}"
            self._season_patterns[season] = []

            # 模拟生成历史比赛数据
            for team_id in range(1, 21):  # 20支球队
                team_matches = []
                for match_id in range(1, 39):  # 每队38场比赛
                    # 随机生成对手和比分
                    opponent_id = (team_id + match_id) % 20 + 1
                    if opponent_id == team_id:
                        opponent_id = 20 if team_id < 20 else 1

                    home_score = np.random.poisson(1.4)
                    away_score = np.random.poisson(1.1)
                    if match_id % 2 == 0:  # 主客场交换
                        home_score, away_score = away_score, home_score

                    match = HistoricalMatch(
                        match_id=match_id + team_id * 1000,
                        home_team_id=team_id if match_id % 2 == 0 else opponent_id,
                        away_team_id=opponent_id if match_id % 2 == 0 else team_id,
                        home_score=home_score,
                        away_score=away_score,
                        match_date=datetime(
                            year, (match_id % 12) + 1, (match_id % 28) + 1
                        ),
                        league_id=1,
                        season=season,
                        importance=1.0,
                    )

                    team_matches.append(match)
                    self._season_patterns[season].append(match)

                    # 更新对战记录
                    key = tuple(sorted([team_id, opponent_id]))
                    if key not in self._team_vs_team:
                        self._team_vs_team[key] = []  # type: ignore
                    self._team_vs_team[key].append(match)  # type: ignore

                    # 更新比分模式
                    score_key = (home_score, away_score)
                    if score_key not in self._score_patterns:
                        self._score_patterns[score_key] = []
                    self._score_patterns[score_key].append(match)

                self._historical_matches[team_id] = team_matches

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行单次预测"""
        if not self._is_initialized:
            raise RuntimeError("策略未初始化")

        start_time = time.time()

        # 验证输入
        if not await self.validate_input(input_data):
            raise ValueError("输入数据无效")

        # 预处理
        processed_input = await self.pre_process(input_data)

        # 查找相关历史数据
        h2h_prediction = await self._predict_from_head_to_head(processed_input)
        similar_score_prediction = await self._predict_from_similar_scores(
            processed_input
        )
        season_prediction = await self._predict_from_season_patterns(processed_input)
        time_pattern_prediction = await self._predict_from_time_patterns(
            processed_input
        )

        # 集成预测结果
        final_prediction = await self._combine_predictions(
            {
                "h2h": h2h_prediction,
                "similar_scores": similar_score_prediction,
                "season": season_prediction,
                "time_patterns": time_pattern_prediction,
            }
        )

        # 计算置信度
        confidence = await self._calculate_confidence(processed_input, final_prediction)

        # 创建概率分布
        probability_distribution = await self._estimate_probabilities(processed_input)

        # 分析特征重要性
        feature_importance = {
            "head_to_head_history": self._weight_factors["direct_h2h"],
            "similar_score_patterns": self._weight_factors["similar_score_patterns"],
            "season_performance": self._weight_factors["season_performance"],
            "time_based_patterns": self._weight_factors["time_based_patterns"],
        }

        # 创建输出
        output = PredictionOutput(
            predicted_home_score=final_prediction[0],
            predicted_away_score=final_prediction[1],
            confidence=confidence,
            probability_distribution=probability_distribution,
            feature_importance=feature_importance,
            metadata={
                "method": "historical_analysis",
                "h2h_matches": len(
                    await self._get_head_to_head_matches(
                        input_data.home_team.id,
                        input_data.away_team.id,  # type: ignore
                    )
                ),
                "similar_scenarios": await self._count_similar_scenarios(
                    processed_input
                ),
                "historical_coverage": await self._calculate_historical_coverage(
                    processed_input
                ),
            },
        )

        output.execution_time_ms = (time.time() - start_time) * 1000
        output.strategy_used = self.name

        # 后处理
        output = await self.post_process(output)

        return output

    async def batch_predict(
        self, inputs: List[PredictionInput]
    ) -> List[PredictionOutput]:
        """批量预测"""
        outputs = []
        for input_data in inputs:
            output = await self.predict(input_data)
            outputs.append(output)
        return outputs

    async def _predict_from_head_to_head(
        self, input_data: PredictionInput
    ) -> Optional[Tuple[int, int]]:
        """基于直接对战历史预测"""
        h2h_matches = await self._get_head_to_head_matches(
            input_data.home_team.id,
            input_data.away_team.id,  # type: ignore
        )

        if len(h2h_matches) < self._min_historical_matches:
            return None

        # 计算平均比分
        home_goals = []
        away_goals = []

        for match in h2h_matches:
            if match.home_team_id == input_data.home_team.id:
                home_goals.append(match.home_score)
                away_goals.append(match.away_score)
            else:
                home_goals.append(match.away_score)
                away_goals.append(match.home_score)

        # 考虑时间衰减（最近比赛权重更高）
        weights = []
        now = datetime.now()
        for match in h2h_matches:
            days_ago = (now - match.match_date).days
            weight = np.exp(-days_ago / 365)  # 一年衰减到e^-1
            weights.append(weight)

        # 计算加权平均
        if weights:
            avg_home = np.average(home_goals, weights=weights)
            avg_away = np.average(away_goals, weights=weights)
        else:
            avg_home = np.mean(home_goals)
            avg_away = np.mean(away_goals)

        return (int(round(avg_home)), int(round(avg_away)))

    async def _predict_from_similar_scores(
        self, input_data: PredictionInput
    ) -> Optional[Tuple[int, int]]:
        """基于相似比分模式预测"""
        # 获取主队最近的主场比分
        home_recent_home = await self._get_recent_home_games(
            input_data.home_team.id,
            10,
        )
        # 获取客队最近的客场比分
        away_recent_away = await self._get_recent_away_games(
            input_data.away_team.id,
            10,
        )

        if not home_recent_home or not away_recent_away:
            return None

        # 计算平均模式
        home_avg_score = np.mean([m.home_score for m in home_recent_home])
        away_avg_score = np.mean([m.away_score for m in away_recent_away])

        # 查找历史上具有相似得分模式的情况
        similar_scenarios = []
        for score, matches in self._score_patterns.items():
            if (
                abs(score[0] - home_avg_score) <= 1
                and abs(score[1] - away_avg_score) <= 1
            ):
                similar_scenarios.extend(matches)

        if len(similar_scenarios) < self._min_historical_matches:
            return None

        # 分析相似场景的结果
        results = []
        for scenario in similar_scenarios:
            # 找到对应的下一场比赛结果
            next_match = await self._find_next_match(scenario)
            if next_match:
                results.append((next_match.home_score, next_match.away_score))

        if results:
            avg_home = np.mean([r[0] for r in results])
            avg_away = np.mean([r[1] for r in results])
            return (int(round(avg_home)), int(round(avg_away)))

        return None

    async def _predict_from_season_patterns(
        self, input_data: PredictionInput
    ) -> Optional[Tuple[int, int]]:
        """基于赛季表现模式预测"""
        current_month = input_data.match.match_time.month  # type: ignore

        # 获取相同球队在历史上同期的表现
        seasonal_matches = []
        for season, matches in self._season_patterns.items():
            for match in matches:
                if (
                    match.home_team_id == input_data.home_team.id
                    or match.away_team_id == input_data.home_team.id
                ):
                    if abs(match.match_date.month - current_month) <= 1:
                        seasonal_matches.append(match)

        if len(seasonal_matches) < self._min_historical_matches:
            return None

        # 分析主场表现
        home_performances = []
        for match in seasonal_matches:
            if match.home_team_id == input_data.home_team.id:
                home_performances.append((match.home_score, match.away_score))
            elif match.away_team_id == input_data.home_team.id:
                home_performances.append((match.away_score, match.home_score))

        if home_performances:
            avg_home = np.mean([p[0] for p in home_performances])
            avg_away = np.mean([p[1] for p in home_performances])
            return (int(round(avg_home)), int(round(avg_away)))

        return None

    async def _predict_from_time_patterns(
        self, input_data: PredictionInput
    ) -> Optional[Tuple[int, int]]:
        """基于时间模式预测"""
        # 分析特定时间段的比赛模式
        match_day = input_data.match.match_time.weekday()  # type: ignore
        match_hour = input_data.match.match_time.hour  # type: ignore

        # 查找相似时间的历史比赛
        time_similar_matches = []
        for matches in self._historical_matches.values():
            for match in matches:
                if (
                    match.home_team_id == input_data.home_team.id
                    or match.away_team_id == input_data.home_team.id
                ):
                    if (
                        match.match_date.weekday() == match_day
                        and abs(match.match_date.hour - match_hour) <= 2
                    ):
                        time_similar_matches.append(match)

        if len(time_similar_matches) < self._min_historical_matches:
            return None

        # 计算平均表现
        home_scores = []
        away_scores = []

        for match in time_similar_matches:
            if match.home_team_id == input_data.home_team.id:
                home_scores.append(match.home_score)
                away_scores.append(match.away_score)
            else:
                home_scores.append(match.away_score)
                away_scores.append(match.home_score)

        if home_scores:
            avg_home = np.mean(home_scores)
            avg_away = np.mean(away_scores)
            return (int(round(avg_home)), int(round(avg_away)))

        return None

    async def _combine_predictions(
        self, predictions: Dict[str, Optional[Tuple[int, int]]]
    ) -> Tuple[int, int]:
        """组合多个预测结果"""
        valid_predictions = {k: v for k, v in predictions.items() if v is not None}

        if not valid_predictions:
            return (1, 1)  # 默认预测

        total_home = 0
        total_away = 0
        total_weight = 0

        for method, pred in valid_predictions.items():
            weight_key = {
                "h2h": "direct_h2h",
                "similar_scores": "similar_score_patterns",
                "season": "season_performance",
                "time_patterns": "time_based_patterns",
            }.get(method, 0.1)

            weight = self._weight_factors.get(weight_key, 0.1)
            total_home += pred[0] * weight
            total_away += pred[1] * weight
            total_weight += weight

        if total_weight > 0:
            avg_home = total_home / total_weight
            avg_away = total_away / total_weight
        else:
            avg_home, avg_away = 1, 1

        return (int(round(avg_home)), int(round(avg_away)))

    async def _calculate_confidence(
        self, input_data: PredictionInput, prediction: Tuple[int, int]
    ) -> float:
        """计算预测置信度"""
        confidence_factors = []

        # 检查历史数据充足性
        h2h_count = len(
            await self._get_head_to_head_matches(
                input_data.home_team.id,
                input_data.away_team.id,  # type: ignore
            )
        )
        if h2h_count >= 10:
            confidence_factors.append(0.9)
        elif h2h_count >= 5:
            confidence_factors.append(0.7)
        elif h2h_count >= 3:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.2)

        # 检查相似场景数量
        similar_count = await self._count_similar_scenarios(input_data)
        if similar_count >= 20:
            confidence_factors.append(0.8)
        elif similar_count >= 10:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)

        # 检查预测一致性
        # 简化处理，假设有一定一致性
        confidence_factors.append(0.7)

        return np.mean(confidence_factors)  # type: ignore

    async def _estimate_probabilities(
        self, input_data: PredictionInput
    ) -> Dict[str, float]:
        """估计结果概率"""
        h2h_matches = await self._get_head_to_head_matches(
            input_data.home_team.id,
            input_data.away_team.id,  # type: ignore
        )

        if not h2h_matches:
            return {"home_win": 0.4, "draw": 0.3, "away_win": 0.3}

        home_wins = 0
        draws = 0
        away_wins = 0

        for match in h2h_matches:
            if match.home_team_id == input_data.home_team.id:
                if match.home_score > match.away_score:
                    home_wins += 1
                elif match.home_score == match.away_score:
                    draws += 1
                else:
                    away_wins += 1
            else:
                if match.away_score > match.home_score:
                    home_wins += 1
                elif match.away_score == match.home_score:
                    draws += 1
                else:
                    away_wins += 1

        total = home_wins + draws + away_wins
        if total > 0:
            return {
                "home_win": home_wins / total,
                "draw": draws / total,
                "away_win": away_wins / total,
            }

        return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33}

    # 辅助方法
    async def _get_head_to_head_matches(
        self, team1_id: int, team2_id: int
    ) -> List[HistoricalMatch]:
        """获取对战历史"""
        key = tuple(sorted([team1_id, team2_id]))
        return self._team_vs_team.get(key, [])  # type: ignore

    async def _get_recent_home_games(
        self, team_id: int, limit: int
    ) -> List[HistoricalMatch]:
        """获取最近的主场比赛"""
        matches = self._historical_matches.get(team_id, [])
        home_matches = [m for m in matches if m.home_team_id == team_id]
        home_matches.sort(key=lambda x: x.match_date, reverse=True)
        return home_matches[:limit]

    async def _get_recent_away_games(
        self, team_id: int, limit: int
    ) -> List[HistoricalMatch]:
        """获取最近的客场比赛"""
        matches = self._historical_matches.get(team_id, [])
        away_matches = [m for m in matches if m.away_team_id == team_id]
        away_matches.sort(key=lambda x: x.match_date, reverse=True)
        return away_matches[:limit]

    async def _find_next_match(
        self, match: HistoricalMatch
    ) -> Optional[HistoricalMatch]:
        """找到指定比赛后的下一场比赛"""
        team_matches = self._historical_matches.get(match.home_team_id, [])
        future_matches = [m for m in team_matches if m.match_date > match.match_date]
        if future_matches:
            future_matches.sort(key=lambda x: x.match_date)
            return future_matches[0]
        return None

    async def _count_similar_scenarios(self, input_data: PredictionInput) -> int:
        """计算相似场景数量"""
        count = 0
        # 简化计算
        count += len(
            await self._get_head_to_head_matches(
                input_data.home_team.id,
                input_data.away_team.id,  # type: ignore
            )
        )
        count += len(await self._get_recent_home_games(input_data.home_team.id, 10))  # type: ignore
        count += len(await self._get_recent_away_games(input_data.away_team.id, 10))  # type: ignore
        return count

    async def _calculate_historical_coverage(
        self, input_data: PredictionInput
    ) -> float:
        """计算历史数据覆盖率"""
        total_matches = len(self._historical_matches.get(input_data.home_team.id, []))  # type: ignore
        if total_matches == 0:
            return 0.0
        return min(1.0, total_matches / 100)  # 假设100场为完整覆盖

    async def update_metrics(
        self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]
    ) -> None:
        """更新策略性能指标"""
        if not actual_results:
            return

        total_predictions = len(actual_results)
        correct_predictions = 0
        score_errors = []

        for pred, actual in actual_results:
            actual_home = actual.get("actual_home_score", 0)
            actual_away = actual.get("actual_away_score", 0)

            # 精确匹配
            if (
                pred.predicted_home == actual_home  # type: ignore
                and pred.predicted_away == actual_away  # type: ignore
            ):
                correct_predictions += 1

            # 计算得分误差
            error = abs(pred.predicted_home - actual_home) + abs(  # type: ignore
                pred.predicted_away - actual_away  # type: ignore
            )
            score_errors.append(error)

        # 计算指标
        accuracy = (
            correct_predictions / total_predictions if total_predictions > 0 else 0
        )
        mean_error = np.mean(score_errors) if score_errors else 0
        precision = max(0, 1 - mean_error / 5)
        recall = accuracy
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        self._metrics = StrategyMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            total_predictions=total_predictions,
            last_updated=datetime.utcnow(),
        )
