"""
金融级风控策略引擎 V7.1
金融级风险控制，防止本金归零
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class StrategyMode(Enum):
    """策略模式枚举"""
    SANDBOX = "SANDBOX"  # 沙盒模式：仅建议，不执行
    LIVE = "LIVE"        # 实战模式：执行下注


class RiskLevel(Enum):
    """风险等级枚举"""
    CRITICAL = "CRITICAL"    # 立即停止
    HIGH = "HIGH"            # 高风险，限制下注
    MEDIUM = "MEDIUM"        # 中等风险，正常下注
    LOW = "LOW"              # 低风险，积极下注


@dataclass
class BettingParameters:
    """下注参数配置"""
    # 基础风控参数
    max_single_bet_pct: float = 0.02      # 单场最大下注比例（2%）
    max_daily_bets: int = 5                # 每日最大下注次数
    max_consecutive_losses: int = 5      # 最大连续亏损次数
    max_total_exposure: float = 0.20     # 最大总风险敞口（20%）

    # Kelly公式参数
    kelly_fraction: float = 0.25         # Kelly公式保守系数
    max_kelly_pct: float = 0.05           # 最大Kelly投注比例
    min_kelly_pct: float = 0.01           # 最小Kelly投注比例

    # 期望收益阈值
    min_edge_threshold: float = 0.05     # 最小边际优势阈值（5%）
    min_expected_value: float = 0.0     # 最小期望收益率
    confidence_threshold: float = 0.6     # 最小置信度阈值

    # 市场参数保护
    min_odds: float = 1.01               # 最小赔率
    max_odds: float = 100.0              # 最大赔率
    odds_range_factor: float = 10.0      # 赔率范围保护因子


@dataclass
class PortfolioState:
    """投资组合状态"""
    initial_capital: float = 1000.0
    current_capital: float = 1000.0
    total_profit: float = 0.0
    total_stake: float = 0.0
    winning_bets: int = 0
    losing_bets: int = 0
    consecutive_losses: int = 0
    daily_bets: int = 0
    last_reset_date: datetime = field(default_factory=datetime.now)
    active_positions: List[Dict] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class BettingRecommendation:
    """下注建议"""
    match_id: str
    home_team: str
    away_team: str
    outcome: str  # home_win, draw, away_win
    odds: float
    model_probability: float
    edge: float
    expected_value: float
    confidence: float
    kelly_fraction: Optional[float] = None
    recommended_stake_pct: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    recommendation_type: str = "NO_BET"
    warnings: List[str] = field(default_factory=list)


class StrategyEngine:
    """
    金融级策略引擎

    核心功能：
    1. 金融级风险控制
    2. Kelly公式计算
    3. 多级风险监控
    4. 投资组合管理
    5. 完全解耦设计
    """

    def __init__(self, params: Optional[BettingParameters] = None,
                 mode: StrategyMode = StrategyMode.SANDBOX):
        self.params = params or BettingParameters()
        self.mode = mode
        self.portfolio = PortfolioState()
        self.betting_history: List[Dict] = []

        # 风控统计
        self.risk_metrics = {
            'total_recommendations': 0,
            'high_risk_warnings': 0,
            'circular_warnings': 0,
            'odds_warnings': 0,
            'portfolio_warnings': 0,
            'safety_activations': 0
        }

        logger.info(f"策略引擎初始化 - 模式: {mode.value}, 初始资金: {self.portfolio.initial_capital}")

    def evaluate_betting_opportunity(self, model_probabilities: Dict[str, float],
                                    market_odds: Dict[str, float],
                                    match_id: str, home_team: str, away_team: str) -> BettingRecommendation:
        """
        评估下注机会（金融级分析）

        Args:
            model_probabilities: 模型预测概率 {'home_win': 0.52, 'draw': 0.25, 'away_win': 0.23}
            market_odds: 市场赔率 {'home_win': 2.10, 'draw': 3.40, 'away_win': 3.60}
            match_id: 比赛ID
            home_team: 主队
            away_team: 客队

        Returns:
            BettingRecommendation: 下注建议
        """
        try:
            # 1. 基础参数验证
            odds_validation = self._validate_odds(market_odds)
            if not odds_validation['valid']:
                return self._create_rejection(match_id, home_team, away_team, odds_validation['warnings'])

            # 1.5. 极端概率检测
            probability_validation = self._validate_probabilities(model_probabilities)
            if not probability_validation['valid']:
                return self._create_rejection(match_id, home_team, away_team, probability_validation['warnings'])

            # 2. 计算边际优势和期望值
            edge_analysis = self._calculate_edge_analysis(model_probabilities, market_odds)

            # 3. 风险评估
            risk_assessment = self._assess_risk(edge_analysis)

            # 4. Kelly公式计算
            kelly_analysis = self._calculate_kelly_fraction(edge_analysis, risk_assessment)

            # 5. 投资组合检查
            portfolio_check = self._check_portfolio_constraints()

            # 6. 综合建议
            recommendation = self._generate_comprehensive_recommendation(
                match_id, home_team, away_team, market_odds, model_probabilities,
                edge_analysis, kelly_analysis, risk_assessment, portfolio_check
            )

            # 7. 模式特定处理
            recommendation = self._apply_mode_specific_logic(recommendation)

            # 8. 风险统计更新
            self._update_risk_metrics(recommendation)

            return recommendation

        except Exception as e:
            logger.error(f"策略引擎异常 {match_id}: {e}")
            return self._create_error_recommendation(match_id, home_team, away_team, str(e))

    def _validate_odds(self, odds: Dict[str, float]) -> Dict[str, Any]:
        """验证赔率参数"""
        warnings = []

        for outcome, odds_value in odds.items():
            if odds_value < self.params.min_odds:
                warnings.append(f"赔率过低 ({outcome}: {odds_value} < {self.params.min_odds})")
            elif odds_value > self.params.max_odds:
                warnings.append(f"赔率过高 ({outcome}: {odds_value} > {self.params.max_odds})")

        # 检查赔率范围合理性
        if odds:
            max_odds_value = max(odds.values())
            min_odds_value = min(odds.values())
            if max_odds_value / min_odds_value > self.params.odds_range_factor:
                warnings.append(f"赔率范围异常 ({min_odds_value:.2f} - {max_odds_value:.2f})")

        return {
            'valid': len(warnings) == 0,
            'warnings': warnings
        }

    def _validate_probabilities(self, probs: Dict[str, float]) -> Dict[str, Any]:
        """验证极端概率"""
        warnings = []

        # 检查100%概率（极端自信）
        for outcome, prob in probs.items():
            if prob >= 0.99:  # 99%以上视为极端
                warnings.append(f"极端模型概率 ({outcome}: {prob:.0%})")
            elif prob <= 0.01:  # 1%以下视为极端
                warnings.append(f"极端模型概率 ({outcome}: {prob:.0%})")

        # 检查概率总和
        total_prob = sum(probs.values())
        if abs(total_prob - 1.0) > 0.01:
            warnings.append(f"概率总和不等于1 ({total_prob:.3f})")

        return {
            'valid': len(warnings) == 0,
            'warnings': warnings
        }

    def _calculate_edge_analysis(self, model_probs: Dict[str, float],
                               odds: Dict[str, float]) -> Dict[str, Any]:
        """计算边际优势分析"""
        edges = {}
        expected_values = {}

        for outcome in model_probs.keys():
            if outcome not in odds:
                continue

            model_p = model_probs[outcome]
            market_p = 1.0 / odds[outcome]

            # 边际优势
            edge = model_p - market_p
            edges[outcome] = round(edge, 4)

            # 期望收益率 EV = (P_model * odds) - 1
            ev = (model_p * odds[outcome]) - 1.0
            expected_values[outcome] = round(ev, 4)

        # 找出最佳机会
        best_outcome = max(edges.items(), key=lambda x: x[1])
        best_edge = best_outcome[1]
        best_odds = odds[best_outcome[0]]
        best_expected_value = expected_values.get(best_outcome[0], 0)

        return {
            'edges': edges,
            'expected_values': expected_values,
            'best_outcome': best_outcome[0],
            'best_edge': best_edge,
            'best_odds': best_odds,
            'best_expected_value': best_expected_value
        }

    def _assess_risk(self, edge_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """风险评估"""
        best_edge = edge_analysis['best_edge']

        # 基础风险等级
        if best_edge < -self.params.min_edge_threshold:
            risk_level = RiskLevel.HIGH
            risk_reason = f"负边际优势 ({best_edge:+.3f})"
        elif best_edge > self.params.min_edge_threshold * 2:
            risk_level = RiskLevel.HIGH
            risk_reason = f"过高边际优势 ({best_edge:+.3f})"
        elif best_edge < self.params.min_edge_threshold / 2:
            risk_level = RiskLevel.HIGH
            risk_reason = f"边际优势不足 ({best_edge:+.3f})"
        else:
            risk_level = RiskLevel.MEDIUM
            risk_reason = "边际优势合理"

        # 紧急停止状态检查
        if self.portfolio.risk_level == RiskLevel.CRITICAL:
            risk_level = RiskLevel.CRITICAL
            risk_reason = "系统处于紧急停止状态"

        # 连续亏损检查
        if self.portfolio.consecutive_losses >= self.params.max_consecutive_losses:
            risk_level = RiskLevel.CRITICAL
            risk_reason = f"连续亏损过多 ({self.portfolio.consecutive_losses}次)"

        # 资金枯竭检查
        capital_ratio = self.portfolio.current_capital / self.portfolio.initial_capital
        if capital_ratio < 0.1:  # 剩余资金少于10%
            risk_level = RiskLevel.CRITICAL
            risk_reason = f"资金严重不足 ({capital_ratio:.1%})"
        elif capital_ratio < 0.5:
            risk_level = RiskLevel.HIGH
            risk_reason = f"资金不足 ({capital_ratio:.1%})"

        return {
            'level': risk_level,
            'reason': risk_reason,
            'capital_ratio': capital_ratio,
            'consecutive_losses': self.portfolio.consecutive_losses
        }

    def _calculate_kelly_fraction(self, edge_analysis: Dict[str, Any],
                                  risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """计算Kelly分数（金融级保守处理）"""
        best_edge = edge_analysis['best_edge']
        best_odds = edge_analysis['best_odds']

        if best_edge <= 0:
            return {
                'kelly_fraction': 0.0,
                'recommended': False,
                'reason': '负边际优势，不应下注'
            }

        # 风险调整
        risk_multiplier = {
            RiskLevel.CRITICAL: 0.0,
            RiskLevel.HIGH: 0.5,
            RiskLevel.MEDIUM: 0.75,
            RiskLevel.LOW: 1.0
        }.get(risk_assessment['level'], 0.5)

        # 资金调整
        capital_multiplier = min(1.0, self.portfolio.current_capital / self.portfolio.initial_capital)

        # Kelly公式计算: f* = (bp - q) / b
        # 其中: b = odds - 1, p = 胜率, q = 败率
        b = best_odds - 1.0
        p = best_edge + (1.0 / best_odds)  # 近似胜率
        q = 1.0 - p

        if b <= 0 or p <= 0 or q <= 0:
            return {
                'kelly_fraction': 0.0,
                'recommended': False,
                'reason': 'Kelly公式参数异常'
            }

        raw_kelly = (b * p - q) / b

        # 应用保守系数和调整因子
        conservative_kelly = (raw_kelly *
                           self.params.kelly_fraction *
                           risk_multiplier *
                           capital_multiplier)

        # 限制范围 - 只有当推荐下注时才应用最小值
        if conservative_kelly > 0:
            limited_kelly = max(self.params.min_kelly_pct,
                              min(conservative_kelly, self.params.max_kelly_pct))
        else:
            limited_kelly = 0.0

        return {
            'kelly_fraction': round(limited_kelly, 4),
            'raw_kelly': round(raw_kelly, 4),
            'recommended': limited_kelly > self.params.min_kelly_pct,
            'risk_multiplier': risk_multiplier,
            'capital_multiplier': capital_multiplier
        }

    def _check_portfolio_constraints(self) -> Dict[str, Any]:
        """检查投资组合约束"""
        constraints = {
            'single_bet_check': True,
            'daily_bet_check': True,
            'total_exposure_check': True,
            'consecutive_loss_check': True,
            'warnings': []
        }

        # 单场下注限制
        current_exposure = sum(pos['stake_pct'] for pos in self.portfolio.active_positions)
        if current_exposure > self.params.max_single_bet_pct:
            constraints['single_bet_check'] = False
            constraints['warnings'].append(f"单场下注超限 ({current_exposure:.2%} > {self.params.max_single_bet_pct:.1%})")

        # 每日下注限制
        if self.portfolio.daily_bets >= self.params.max_daily_bets:
            constraints['daily_bet_check'] = False
            constraints['warnings'].append(f"每日下注次数超限 ({self.portfolio.daily_bets} >= {self.params.max_daily_bets})")

        # 总风险敞口限制
        if current_exposure > self.params.max_total_exposure:
            constraints['total_exposure_check'] = False
            constraints['warnings'].append(f"总风险敞口超限 ({current_exposure:.2%} > {self.params.max_total_exposure:.1%})")

        # 连续亏损检查
        if self.portfolio.consecutive_losses >= self.params.max_consecutive_losses:
            constraints['consecutive_loss_check'] = False
            constraints['warnings'].append(f"连续亏损次数超限 ({self.portfolio.consecutive_losses} >= {self.params.max_consecutive_losses})")

        constraints['all_passed'] = all([
            constraints['single_bet_check'],
            constraints['daily_bet_check'],
            constraints['total_exposure_check'],
            constraints['consecutive_loss_check']
        ])

        return constraints

    def _generate_comprehensive_recommendation(self, match_id: str, home_team: str, away_team: str,
                                            odds: Dict[str, float], model_probs: Dict[str, float],
                                            edge_analysis: Dict[str, Any], kelly_analysis: Dict[str, Any],
                                            risk_assessment: Dict[str, Any], portfolio_check: Dict[str, Any]) -> BettingRecommendation:
        """生成综合下注建议"""
        best_outcome = edge_analysis['best_outcome']
        best_edge = edge_analysis['best_edge']
        best_odds = odds[best_outcome]
        best_model_prob = model_probs[best_outcome]
        best_expected_value = edge_analysis['best_expected_value']

        # 判断是否下注
        should_bet = (
            best_edge >= self.params.min_edge_threshold and
            best_expected_value >= self.params.min_expected_value and
            portfolio_check['all_passed'] and
            kelly_analysis['recommended']
        )

        # 确定下注类型
        if not should_bet:
            recommendation_type = "NO_BET"
            stake_pct = 0.0
        elif best_edge > self.params.min_edge_threshold * 2:
            recommendation_type = "STRONG_BET"
            stake_pct = kelly_analysis['kelly_fraction']
        elif best_edge > self.params.min_edge_threshold:
            recommendation_type = "STANDARD_BET"
            stake_pct = kelly_analysis['kelly_fraction']
        else:
            recommendation_type = "NO_BET"
            stake_pct = 0.0

        # 组装所有警告
        all_warnings = []
        if edge_analysis['best_edge'] < 0:
            all_warnings.append("负边际优势")
        if not portfolio_check['all_passed']:
            all_warnings.extend(portfolio_check['warnings'])
        if risk_assessment['level'] == RiskLevel.HIGH:
            all_warnings.append(f"高风险: {risk_assessment['reason']}")
        if risk_assessment['level'] == RiskLevel.CRITICAL:
            all_warnings.append(f"紧急风险: {risk_assessment['reason']}")

        return BettingRecommendation(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            outcome=best_outcome,
            odds=best_odds,
            model_probability=best_model_prob,
            edge=best_edge,
            expected_value=best_expected_value,
            confidence=self.params.confidence_threshold,
            kelly_fraction=kelly_analysis['kelly_fraction'],
            recommended_stake_pct=stake_pct if should_bet else None,
            risk_level=risk_assessment['level'],
            recommendation_type=recommendation_type,
            warnings=all_warnings
        )

    def _apply_mode_specific_logic(self, recommendation: BettingRecommendation) -> BettingRecommendation:
        """应用模式特定逻辑"""
        if self.mode == StrategyMode.SANDBOX:
            # 沙盒模式：将下注转为建议
            if recommendation.recommendation_type != "NO_BET":
                recommendation.warnings.insert(0, "沙盒模式：仅展示建议，不执行下注")

        return recommendation

    def _update_risk_metrics(self, recommendation: BettingRecommendation):
        """更新风险统计"""
        self.risk_metrics['total_recommendations'] += 1

        for warning in recommendation.warnings:
            if '紧急风险' in warning or 'critical' in warning.lower():
                self.risk_metrics['circular_warnings'] += 1
            elif '高风险' in warning:
                self.risk_metrics['high_risk_warnings'] += 1
            elif '赔率' in warning:
                self.risk_metrics['odds_warnings'] += 1
            elif '投资组合' in warning:
                self.risk_metrics['portfolio_warnings'] += 1

        if recommendation.risk_level == RiskLevel.CRITICAL:
            self.risk_metrics['safety_activations'] += 1

    def _create_rejection(self, match_id: str, home_team: str, away_team: str,
                         warnings: List[str]) -> BettingRecommendation:
        """创建拒绝建议"""
        return BettingRecommendation(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            outcome="no_value",
            odds=1.0,
            model_probability=0.0,
            edge=0.0,
            expected_value=0.0,
            confidence=0.0,
            recommendation_type="NO_BET",
            risk_level=RiskLevel.HIGH,
            warnings=warnings
        )

    def _create_error_recommendation(self, match_id: str, home_team: str, away_team: str,
                                  error_message: str) -> BettingRecommendation:
        """创建错误建议"""
        return BettingRecommendation(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            outcome="error",
            odds=1.0,
            model_probability=0.0,
            edge=0.0,
            expected_value=0.0,
            confidence=0.0,
            recommendation_type="ERROR",
            risk_level=RiskLevel.CRITICAL,
            warnings=[f"策略引擎错误: {error_message}"]
        )

    def get_risk_report(self) -> Dict[str, Any]:
        """获取风险报告"""
        return {
            'strategy_mode': self.mode.value,
            'risk_metrics': self.risk_metrics,
            'portfolio_state': {
                'initial_capital': self.portfolio.initial_capital,
                'current_capital': self.portfolio.current_capital,
                'total_profit': self.portfolio.total_profit,
                'roi': (self.portfolio.total_profit / self.portfolio.initial_capital * 100) if self.portfolio.initial_capital > 0 else 0,
                'winning_rate': (self.portfolio.winning_bets / (self.portfolio.winning_bets + self.portfolio.losing_bets)) if (self.portfolio.winning_bets + self.portfolio.losing_bets) > 0 else 0,
                'consecutive_losses': self.portfolio.consecutive_losses,
                'daily_bets': self.portfolio.daily_bets
            },
            'risk_level_distribution': {
                'critical': self.risk_metrics.get('circular_warnings', 0),
                'high': self.risk_metrics.get('high_risk_warnings', 0),
                'medium': self.risk_metrics.get('total_recommendations', 0) - self.risk_metrics.get('high_risk_warnings', 0) - self.risk_metrics.get('circular_warnings', 0),
                'low': 0
            },
            'safety_activations': self.risk_metrics.get('safety_activations', 0),
            'timestamp': datetime.now().isoformat(),
            'version': 'V7.1-FINANCIAL-GRADE'
        }

    def reset_daily_limits(self):
        """重置每日限制"""
        self.portfolio.daily_bets = 0
        self.portfolio.active_positions.clear()
        logger.info("每日限制已重置")

    def emergency_stop(self, reason: str) -> bool:
        """紧急停止"""
        logger.error(f"🚨 紧急停止: {reason}")

        # 清除所有活跃仓位
        self.portfolio.active_positions.clear()

        # 更新风险等级
        self.portfolio.risk_level = RiskLevel.CRITICAL

        # 记录紧急停止
        self.risk_metrics['safety_activations'] += 1

        return True


# 金融级策略引擎实例
strategy_engine = StrategyEngine(mode=StrategyMode.SANDBOX)