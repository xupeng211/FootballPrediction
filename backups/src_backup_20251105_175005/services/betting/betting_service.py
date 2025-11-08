"""
投注服务 - 重写版本

提供EV计算和投注策略集成功能
Betting Service - Rewritten Version
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class BettingOdds:
    """投注赔率数据"""

    home_win: float
    draw: float
    away_win: float
    over_under_2_5: tuple[float, float] | None = None  # (over, under)
    both_teams_score: tuple[float, float] | None = None  # (yes, no)


@dataclass
class PredictionProbabilities:
    """预测概率数据"""

    home_win: float
    draw: float
    away_win: float
    over_under_2_5: tuple[float, float] | None = None
    both_teams_score: tuple[float, float] | None = None


@dataclass
class EVCalculation:
    """期望值计算结果"""

    ev_home_win: float
    ev_draw: float
    ev_away_win: float
    recommendation: str
    confidence: float
    ev_over_2_5: float | None = None
    ev_under_2_5: float | None = None
    ev_bts_yes: float | None = None
    ev_bts_no: float | None = None


@dataclass
class BettingRecommendation:
    """投注建议"""

    match_id: str
    bet_type: str
    odds: float
    probability: float
    ev: float
    kelly_fraction: float | None
    confidence: float
    reasoning: str
    created_at: datetime


class EVCalculator:
    """期望值计算器"""

    def __init__(self,
    margin: float = 0.05):
        """
        初始化EV计算器

        Args:
            margin: 计算中使用的安全边际
        """
        self.margin = margin

    def calculate_ev(self,
    odds: float,
    probability: float) -> float:
        """计算单个投注的期望值"""
        if odds <= 1.0 or probability <= 0.0 or probability >= 1.0:
            return 0.0

        1.0 / odds
        actual_prob = probability * (1 - self.margin)

        return (actual_prob * odds - 1.0) * 100  # 返回百分比

    def calculate_kelly_fraction(self,
    ev: float,
    odds: float) -> float | None:
        """计算凯利投注比例"""
        if ev <= 0:
            return 0.0

        # 简化的凯利公式
        edge = ev / 100.0
        kelly = (odds * edge - 1) / (odds - 1)

        # 限制最大投注比例
        return max(0.0,
    min(kelly,
    0.25))  # 最大25%

    def calculate_match_ev(
        self,
    odds: BettingOdds,
    probabilities: PredictionProbabilities
    ) -> EVCalculation:
        """计算整场比赛的期望值"""

        # 计算1X2投注的EV
        ev_home = self.calculate_ev(odds.home_win,
    probabilities.home_win)
        ev_draw = self.calculate_ev(odds.draw,
    probabilities.draw)
        ev_away = self.calculate_ev(odds.away_win,
    probabilities.away_win)

        # 计算大小球EV
        ev_over_2_5 = None
        ev_under_2_5 = None
        if odds.over_under_2_5 and probabilities.over_under_2_5:
            ev_over_2_5 = self.calculate_ev(
                odds.over_under_2_5[0],
    probabilities.over_under_2_5[0]
            )
            ev_under_2_5 = self.calculate_ev(
                odds.over_under_2_5[1],
    probabilities.over_under_2_5[1]
            )

        # 计算双方进球EV
        ev_bts_yes = None
        ev_bts_no = None
        if odds.both_teams_score and probabilities.both_teams_score:
            ev_bts_yes = self.calculate_ev(
                odds.both_teams_score[0],
    probabilities.both_teams_score[0]
            )
            ev_bts_no = self.calculate_ev(
                odds.both_teams_score[1],
    probabilities.both_teams_score[1]
            )

        # 确定最佳推荐
        ev_values = [
            ev
            for ev in [
                ev_home,

                ev_draw,
                ev_away,
                ev_over_2_5,
                ev_under_2_5,
                ev_bts_yes,
                ev_bts_no,
            ]
            if ev is not None
        ]

        if not ev_values:
            recommendation = "no_bet"
            confidence = 0.0
        else:
            max_ev = max(ev_values)
            if max_ev > 2.0:  # EV阈值
                recommendation = "strong_bet"
                confidence = min(max_ev / 10.0,
    1.0)
            elif max_ev > 1.0:
                recommendation = "moderate_bet"
                confidence = min(max_ev / 5.0,
    0.8)
            else:
                recommendation = "no_bet"
                confidence = 0.0

        return EVCalculation(
            ev_home_win=ev_home,
    ev_draw=ev_draw,

            ev_away_win=ev_away,
            ev_over_2_5=ev_over_2_5,
            ev_under_2_5=ev_under_2_5,
            ev_bts_yes=ev_bts_yes,
            ev_bts_no=ev_bts_no,
            recommendation=recommendation,
            confidence=confidence,
        )


class BettingRecommendationEngine:
    """投注建议引擎"""

    def __init__(self, ev_calculator: EVCalculator):
        self.ev_calculator = ev_calculator
        self.logger = logging.getLogger(f"{__name__}.BettingRecommendationEngine")

    def generate_recommendations(
        self,
    match_id: str,
    odds: BettingOdds,
    probabilities: PredictionProbabilities
    ) -> list[BettingRecommendation]:
        """生成投注建议"""
        ev_calc = self.ev_calculator.calculate_match_ev(odds,
    probabilities)
        recommendations = []

        # 主胜推荐
        if ev_calc.ev_home_win > 1.0:
            recommendations.append(
                BettingRecommendation(
                    match_id=match_id,
    bet_type="home_win",
    odds=odds.home_win,
    probability=probabilities.home_win,

                    ev=ev_calc.ev_home_win,
                    kelly_fraction=self.ev_calculator.calculate_kelly_fraction(
                        ev_calc.ev_home_win, odds.home_win
                    ),
                    confidence=ev_calc.confidence,
                    reasoning=f"EV: {ev_calc.ev_home_win:.2f}%, 概率: {probabilities.home_win:.2f}",
                    created_at=datetime.utcnow(),
    )
            )

        # 平局推荐
        if ev_calc.ev_draw > 1.0:
            recommendations.append(
                BettingRecommendation(
                    match_id=match_id,
    bet_type="draw",
    odds=odds.draw,

                    probability=probabilities.draw,
                    ev=ev_calc.ev_draw,
                    kelly_fraction=self.ev_calculator.calculate_kelly_fraction(
                        ev_calc.ev_draw, odds.draw
                    ),
                    confidence=ev_calc.confidence,
                    reasoning=f"EV: {ev_calc.ev_draw:.2f}%, 概率: {probabilities.draw:.2f}",
                    created_at=datetime.utcnow(),
    )
            )

        # 客胜推荐
        if ev_calc.ev_away_win > 1.0:
            recommendations.append(
                BettingRecommendation(
                    match_id=match_id,
    bet_type="away_win",
    odds=odds.away_win,

                    probability=probabilities.away_win,
                    ev=ev_calc.ev_away_win,
                    kelly_fraction=self.ev_calculator.calculate_kelly_fraction(
                        ev_calc.ev_away_win, odds.away_win
                    ),
                    confidence=ev_calc.confidence,
                    reasoning=f"EV: {ev_calc.ev_away_win:.2f}%, 概率: {probabilities.away_win:.2f}",
                    created_at=datetime.utcnow(),
    )
            )

        # 大小球推荐
        if ev_calc.ev_over_2_5 and ev_calc.ev_over_2_5 > 1.0:
            recommendations.append(
                BettingRecommendation(
                    match_id=match_id,
    bet_type="over_2_5",
    odds=odds.over_under_2_5[0] if odds.over_under_2_5 else 0.0,

                    probability=(
                        probabilities.over_under_2_5[0]
                        if probabilities.over_under_2_5
                        else 0.0
                    ),
                    ev=ev_calc.ev_over_2_5,
                    kelly_fraction=(
                        self.ev_calculator.calculate_kelly_fraction(
                            ev_calc.ev_over_2_5, odds.over_under_2_5[0]
                        )
                        if odds.over_under_2_5
                        else None
                    ),
                    confidence=ev_calc.confidence,
                    reasoning=f"EV: {ev_calc.ev_over_2_5:.2f}%, 大小球推荐",
                    created_at=datetime.utcnow(),
                )
            )

        return recommendations


class BettingService:
    """投注服务主类 - 简化版本"""

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化投注服务"""
        self.logger = logging.getLogger(f"{__name__}.BettingService")

        # 配置参数
        self.config = config or {
            "ev_margin": 0.05,
            "min_ev_threshold": 1.0,
            "max_kelly_fraction": 0.25,
            "confidence_threshold": 0.1,
        }

        # 初始化组件
        self.ev_calculator = EVCalculator(margin=self.config["ev_margin"])
        self.recommendation_engine = BettingRecommendationEngine(self.ev_calculator)

        # 历史记录
        self.recommendation_history: list[BettingRecommendation] = []

    async def analyze_match(
        self,
    match_id: str,
    odds_data: dict[str,
    Any],
    prediction_data: dict[str,
    Any]
    ) -> dict[str, Any]:
        """分析单场比赛"""
        try:
            # 转换数据格式
            odds = self._parse_odds_data(odds_data)
            probabilities = self._parse_prediction_data(prediction_data)

            if not odds or not probabilities:
                return {"error": "无效的赔率或预测数据"}

            # 计算EV
            ev_calculation = self.ev_calculator.calculate_match_ev(odds, probabilities)

            # 生成推荐
            recommendations = self.recommendation_engine.generate_recommendations(
                match_id, odds, probabilities
            )

            # 保存推荐历史
            self.recommendation_history.extend(recommendations)

            return {
                "match_id": match_id,
                "ev_calculation": ev_calculation,
                "recommendations": recommendations,
                "analysis_summary": self._generate_analysis_summary(
                    ev_calculation, recommendations
                ),
                "analyzed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"分析比赛 {match_id} 失败: {e}")
            return {"error": str(e)}

    def _parse_odds_data(self,
    odds_data: dict[str,
    Any]) -> BettingOdds | None:
        """解析赔率数据"""
        try:
            return BettingOdds(
                home_win=float(odds_data.get("home_win",
    0)),

                draw=float(odds_data.get("draw",
    0)),
    away_win=float(odds_data.get("away_win",
    0)),

                over_under_2_5=(
                    (
                        float(odds_data.get("over_2_5",
    0)),
    float(odds_data.get("under_2_5",
    0)),

                    )
                    if odds_data.get("over_2_5") and odds_data.get("under_2_5")
                    else None
                ),
    both_teams_score=(
                    (
                        float(odds_data.get("bts_yes",
    0)),
    float(odds_data.get("bts_no",
    0)),

                    )
                    if odds_data.get("bts_yes") and odds_data.get("bts_no")
                    else None
                ),
            )
        except (ValueError, TypeError) as e:
            self.logger.warning(f"赔率数据解析失败: {e}")
            return None

    def _parse_prediction_data(
        self,
    prediction_data: dict[str,
    Any]
    ) -> PredictionProbabilities | None:
        """解析预测数据"""
        try:
            return PredictionProbabilities(
                home_win=float(prediction_data.get("home_win_prob",
    0)),

                draw=float(prediction_data.get("draw_prob",
    0)),
    away_win=float(prediction_data.get("away_win_prob",
    0)),

                over_under_2_5=(
                    (
                        float(prediction_data.get("over_2_5_prob",
    0)),
    float(prediction_data.get("under_2_5_prob",
    0)),

                    )
                    if prediction_data.get("over_2_5_prob")
                    and prediction_data.get("under_2_5_prob")
                    else None
                ),
    both_teams_score=(
                    (
                        float(prediction_data.get("bts_yes_prob",
    0)),
    float(prediction_data.get("bts_no_prob",
    0)),

                    )
                    if prediction_data.get("bts_yes_prob")
                    and prediction_data.get("bts_no_prob")
                    else None
                ),
            )
        except (ValueError, TypeError) as e:
            self.logger.warning(f"预测数据解析失败: {e}")
            return None

    def _generate_analysis_summary(
        self, ev_calc: EVCalculation, recommendations: list[BettingRecommendation]
    ) -> dict[str, Any]:
        """生成分析摘要"""
        return {
            "overall_recommendation": ev_calc.recommendation,
            "confidence_score": ev_calc.confidence,
            "best_bet": {
                "type": recommendations[0].bet_type if recommendations else None,
                "ev": recommendations[0].ev if recommendations else 0.0,
                "kelly_fraction": (
                    recommendations[0].kelly_fraction if recommendations else None
                ),
            },
            "recommendation_count": len(recommendations),
    "max_ev": max([r.ev for r in recommendations]) if recommendations else 0.0,
    }

    async def get_recommendations_by_confidence(
        self,
    min_confidence: float = 0.1,
    limit: int = 10
    ) -> list[BettingRecommendation]:
        """根据置信度获取推荐"""
        filtered = [
            r for r in self.recommendation_history if r.confidence >= min_confidence
        ]

        # 按EV排序
        filtered.sort(key=lambda x: x.ev,
    reverse=True)

        return filtered[:limit]

    async def calculate_portfolio_performance(
        self,
    start_date: datetime | None = None,
    end_date: datetime | None = None
    ) -> dict[str,
    Any]:
        """计算投资组合表现"""
        if not self.recommendation_history:
            return {"error": "没有推荐历史"}

        # 过滤时间范围
        if start_date:
            history = [
                r for r in self.recommendation_history if r.created_at >= start_date
            ]
        else:
            history = self.recommendation_history

        if end_date:
            history = [r for r in history if r.created_at <= end_date]

        if not history:
            return {"error": "指定时间范围内没有推荐"}

        # 计算统计数据
        total_recommendations = len(history)
        total_ev = sum(r.ev for r in history)
        avg_ev = total_ev / total_recommendations if total_recommendations > 0 else 0

        high_confidence = [r for r in history if r.confidence >= 0.5]
        high_confidence_count = len(high_confidence)
        high_confidence_ev = sum(r.ev for r in high_confidence)

        return {
            "total_recommendations": total_recommendations,
            "average_ev": round(avg_ev, 2),
            "total_ev": round(total_ev, 2),
            "high_confidence_count": high_confidence_count,
            "high_confidence_ev": round(high_confidence_ev,
    2),
    "high_confidence_ratio": (
                round(high_confidence_count / total_recommendations,
    3)
                if total_recommendations > 0
                else 0
            ),

            "period": {
                "start": start_date.isoformat() if start_date else None,
    "end": end_date.isoformat() if end_date else None,
    },
    }

    def get_service_stats(self) -> dict[str,
    Any]:
        """获取服务统计信息"""
        return {
            "total_recommendations": len(self.recommendation_history),
            "config": self.config,
            "components": {
                "ev_calculator": "initialized",
                "recommendation_engine": "initialized",
            },
            "created_at": datetime.utcnow().isoformat(),
        }
