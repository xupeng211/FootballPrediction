"""
投注策略管理器 - Betting Strategy Manager
实现基于边际优势的智能投注决策和风险管理
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from src.ml.value_finder import BetRecommendation

logger = logging.getLogger(__name__)


class RecommendationLevel(Enum):
    """推荐等级枚举"""
    NO_VALUE = 0
    GOLD = 1
    SILVER = 2
    WARNING = 3


@dataclass
class BettingStrategy:
    """投注策略配置"""
    name: str
    min_edge_threshold: float
    max_edge_threshold: float
    kelly_multiplier: float
    max_daily_bets: int
    max_exposure_per_match: float
    min_confidence: float
    description: str


@dataclass
class PortfolioPosition:
    """投资组合头寸"""
    match_id: str
    outcome: str  # home_win, draw, away_win
    stake: float
    odds: float
    edge: float
    confidence: float
    placed_at: datetime
    status: str = "pending"  # pending, won, lost, void
    result: Optional[float] = None  # 盈亏结果


@dataclass
class DailyBettingReport:
    """每日投注报告"""
    date: datetime
    total_bets: int
    total_stake: float
    total_returns: float
    net_profit: float
    roi: float
    winning_rate: float
    bets: List[PortfolioPosition] = field(default_factory=list)


class BettingStrategyManager:
    """
    投注策略管理器

    职责：
    1. 管理投注等级制度
    2. 风险控制和头寸管理
    3. 投注组合优化
    4. 业绩跟踪和报告
    """

    def __init__(self):
        # 定义标准投注策略
        self.strategies = {
            'conservative': BettingStrategy(
                name="保守策略",
                min_edge_threshold=0.08,
                max_edge_threshold=0.25,
                kelly_multiplier=0.25,
                max_daily_bets=3,
                max_exposure_per_match=0.02,
                min_confidence=0.7,
                description="低风险，稳定收益，适合长期投资"
            ),
            'moderate': BettingStrategy(
                name="适中策略",
                min_edge_threshold=0.05,
                max_edge_threshold=0.30,
                kelly_multiplier=0.5,
                max_daily_bets=5,
                max_exposure_per_match=0.03,
                min_confidence=0.6,
                description="平衡风险收益，中等投注频率"
            ),
            'aggressive': BettingStrategy(
                name="激进策略",
                min_edge_threshold=0.03,
                max_edge_threshold=0.40,
                kelly_multiplier=0.75,
                max_daily_bets=8,
                max_exposure_per_match=0.05,
                min_confidence=0.5,
                description="高风险高收益，频繁投注"
            )
        }

        # 当前活跃策略
        self.current_strategy = self.strategies['moderate']

        # 投资组合管理
        self.portfolio: List[PortfolioPosition] = []
        self.daily_reports: List[DailyBettingReport] = []

        # 风险管理参数
        self.max_total_exposure = 0.20  # 总风险敞口不超过20%
        self.max_consecutive_losses = 5  # 最大连续亏损次数
        self.stop_loss_threshold = -0.10  # 止损阈值-10%

        # 投注限制
        self.active_matches: Set[str] = set()
        self.daily_bets_count = 0
        self.last_reset_date = datetime.now().date()

        # 性能统计
        self.total_bets = 0
        self.total_profit = 0.0
        self.current_streak = 0  # 连续盈亏次数

    def set_strategy(self, strategy_name: str) -> bool:
        """
        设置投注策略

        Args:
            strategy_name: 策略名称

        Returns:
            bool: 是否设置成功
        """
        if strategy_name in self.strategies:
            self.current_strategy = self.strategies[strategy_name]
            logger.info(f"投注策略已切换到: {strategy_name}")
            return True
        else:
            logger.warning(f"未找到策略: {strategy_name}")
            return False

    def evaluate_recommendation(self, recommendation: BetRecommendation) -> Dict:
        """
        评估投注推荐

        Args:
            recommendation: 投注推荐

        Returns:
            Dict: 评估结果
        """
        strategy = self.current_strategy

        # 1. 基本门槛检查
        if recommendation.edge_value < strategy.min_edge_threshold:
            return {
                'action': 'reject',
                'reason': f'边际优势不足: {recommendation.edge_value:.3f} < {strategy.min_edge_threshold}',
                'score': 0.0
            }

        if recommendation.confidence < strategy.min_confidence:
            return {
                'action': 'reject',
                'reason': f'置信度不足: {recommendation.confidence:.3f} < {strategy.min_confidence}',
                'score': 0.0
            }

        # 2. 计算综合评分
        edge_score = min(recommendation.edge_value / strategy.max_edge_threshold, 1.0)
        confidence_score = recommendation.confidence
        ev_score = max(0, recommendation.expected_value or 0) if recommendation.expected_value else 0

        # 权重分配
        total_score = (edge_score * 0.5 + confidence_score * 0.3 + ev_score * 0.2)

        # 3. 风险检查
        risk_checks = self._perform_risk_checks(recommendation)
        if not risk_checks['passed']:
            return {
                'action': 'reject',
                'reason': risk_checks['reason'],
                'score': 0.0,
                'risk_factors': risk_checks['factors']
            }

        # 4. 确定行动
        if total_score >= 0.7:
            action = 'bet'
        elif total_score >= 0.5:
            action = 'consider'
        else:
            action = 'reject'

        # 5. 计算建议投注金额
        stake = 0.0
        if action == 'bet':
            stake = self._calculate_optimal_stake(recommendation, strategy)

        return {
            'action': action,
            'reason': self._get_action_reason(action, total_score),
            'score': round(total_score, 3),
            'stake': round(stake, 2),
            'edge_score': round(edge_score, 3),
            'confidence_score': round(confidence_score, 3),
            'ev_score': round(ev_score, 3),
            'risk_checks': risk_checks
        }

    def _perform_risk_checks(self, recommendation: BetRecommendation) -> Dict:
        """
        执行风险检查

        Args:
            recommendation: 投注推荐

        Returns:
            Dict: 风险检查结果
        """
        risk_factors = []

        # 检查1: 总风险敞口
        current_exposure = self._calculate_total_exposure()
        if current_exposure >= self.max_total_exposure:
            risk_factors.append(f'总风险敞口过高: {current_exposure:.1%}')

        # 检查2: 连续亏损
        if self.current_streak <= -self.max_consecutive_losses:
            risk_factors.append(f'连续亏损过多: {abs(self.current_streak)}次')

        # 检查3: 每日投注限制
        self._reset_daily_counter_if_needed()
        if self.daily_bets_count >= self.current_strategy.max_daily_bets:
            risk_factors.append(f'每日投注次数已达上限: {self.daily_bets_count}')

        # 检查4: 单场比赛重复投注
        if recommendation.match_id in self.active_matches:
            risk_factors.append('该比赛已有活跃投注')

        # 检查5: 预警等级处理
        if recommendation.recommendation_level == 3:  # 避坑预警
            # 预警等级可以考虑反向投注，但这里暂时拒绝
            risk_factors.append('市场高估，不建议投注')

        return {
            'passed': len(risk_factors) == 0,
            'reason': '; '.join(risk_factors) if risk_factors else '风险检查通过',
            'factors': risk_factors
        }

    def _calculate_optimal_stake(self, recommendation: BetRecommendation, strategy: BettingStrategy) -> float:
        """
        计算最优投注金额

        Args:
            recommendation: 投注推荐
            strategy: 投注策略

        Returns:
            float: 投注金额
        """
        # 基于Kelly分数
        base_stake = recommendation.kelly_fraction or 0.0

        # 应用策略调整
        adjusted_stake = base_stake * strategy.kelly_multiplier

        # 应用置信度调整
        adjusted_stake *= recommendation.confidence

        # 限制单场比赛投注
        max_stake = strategy.max_exposure_per_match
        adjusted_stake = min(adjusted_stake, max_stake)

        # 设置最小投注金额
        min_stake = 0.01  # 1%
        adjusted_stake = max(adjusted_stake, min_stake)

        return round(adjusted_stake, 4)

    def _calculate_total_exposure(self) -> float:
        """计算总风险敞口"""
        total = 0.0
        for position in self.portfolio:
            if position.status == 'pending':
                total += position.stake
        return total

    def _reset_daily_counter_if_needed(self):
        """如果需要，重置每日计数器"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_bets_count = 0
            self.active_matches.clear()
            self.last_reset_date = today
            logger.info("每日投注计数器已重置")

    def _get_action_reason(self, action: str, score: float) -> str:
        """获取行动原因"""
        if action == 'bet':
            return f'强烈推荐 (评分: {score:.3f})'
        elif action == 'consider':
            return f'适度考虑 (评分: {score:.3f})'
        else:
            return f'拒绝投注 (评分: {score:.3f})'

    def place_bet(self, recommendation: BetRecommendation, stake: float) -> bool:
        """
        执行投注

        Args:
            recommendation: 投注推荐
            stake: 投注金额

        Returns:
            bool: 是否成功
        """
        try:
            # 创建投注头寸
            position = PortfolioPosition(
                match_id=recommendation.match_id,
                outcome=recommendation.best_bet,
                stake=stake,
                odds=recommendation.market_odds[recommendation.best_bet],
                edge=recommendation.edge_value,
                confidence=recommendation.confidence,
                placed_at=datetime.now()
            )

            # 添加到投资组合
            self.portfolio.append(position)
            self.active_matches.add(recommendation.match_id)
            self.daily_bets_count += 1
            self.total_bets += 1

            logger.info(f"投注成功: {recommendation.match_id} - {recommendation.best_bet} "
                       f"金额: {stake:.2f} 赔率: {position.odds:.2f} 边际: {recommendation.edge_value:.3f}")

            return True

        except Exception as e:
            logger.error(f"投注失败: {e}")
            return False

    def settle_bet(self, match_id: str, outcome: str, final_odds: Optional[float] = None) -> Optional[float]:
        """
        结算投注

        Args:
            match_id: 比赛ID
            outcome: 比赛结果 (home_win, draw, away_win)
            final_odds: 最终赔率（可选）

        Returns:
            Optional[float]: 盈亏金额
        """
        try:
            settled_positions = []
            total_pnl = 0.0

            for position in self.portfolio:
                if (position.match_id == match_id and
                    position.status == 'pending' and
                    position.outcome == outcome):

                    # 计算盈亏
                    if final_odds:
                        position.odds = final_odds

                    pnl = position.stake * (position.odds - 1) if outcome == position.outcome else -position.stake
                    position.result = pnl
                    position.status = 'won' if pnl > 0 else 'lost'

                    total_pnl += pnl
                    settled_positions.append(position)

            # 更新统计
            if total_pnl != 0:
                self.total_profit += total_pnl
                # 更新连续盈亏
                if total_pnl > 0:
                    self.current_streak = max(1, self.current_streak + 1)
                else:
                    self.current_streak = min(-1, self.current_streak - 1)

                # 更新活跃比赛列表
                self.active_matches.discard(match_id)

            logger.info(f"投注结算完成: {match_id} 结果: {outcome} 盈亏: {total_pnl:.2f}")
            return total_pnl

        except Exception as e:
            logger.error(f"投注结算失败: {e}")
            return None

    def generate_daily_report(self, date: datetime = None) -> DailyBettingReport:
        """
        生成每日投注报告

        Args:
            date: 报告日期（可选）

        Returns:
            DailyBettingReport: 每日报告
        """
        if date is None:
            date = datetime.now().date()

        # 筛选当日投注
        day_bets = [
            pos for pos in self.portfolio
            if pos.placed_at.date() == date and pos.status != 'pending'
        ]

        if not day_bets:
            return DailyBettingReport(
                date=datetime.combine(date, datetime.min.time()),
                total_bets=0,
                total_stake=0.0,
                total_returns=0.0,
                net_profit=0.0,
                roi=0.0,
                winning_rate=0.0,
                bets=[]
            )

        total_stake = sum(pos.stake for pos in day_bets)
        total_returns = sum(pos.stake + pos.result for pos in day_bets if pos.result > 0)
        net_profit = sum(pos.result for pos in day_bets)
        winning_bets = len([pos for pos in day_bets if pos.result > 0])

        report = DailyBettingReport(
            date=datetime.combine(date, datetime.min.time()),
            total_bets=len(day_bets),
            total_stake=total_stake,
            total_returns=total_returns,
            net_profit=net_profit,
            roi=(net_profit / total_stake) if total_stake > 0 else 0,
            winning_rate=(winning_bets / len(day_bets)) if day_bets else 0,
            bets=day_bets
        )

        # 保存报告
        self.daily_reports.append(report)

        return report

    def get_strategy_summary(self) -> Dict:
        """获取策略执行摘要"""
        return {
            'current_strategy': self.current_strategy.name,
            'current_strategy_params': {
                'min_edge_threshold': self.current_strategy.min_edge_threshold,
                'max_daily_bets': self.current_strategy.max_daily_bets,
                'kelly_multiplier': self.current_strategy.kelly_multiplier
            },
            'portfolio_stats': {
                'total_bets': self.total_bets,
                'total_profit': round(self.total_profit, 2),
                'current_exposure': round(self._calculate_total_exposure(), 4),
                'active_positions': len([p for p in self.portfolio if p.status == 'pending']),
                'current_streak': self.current_streak
            },
            'risk_metrics': {
                'max_total_exposure': self.max_total_exposure,
                'max_consecutive_losses': self.max_consecutive_losses,
                'stop_loss_threshold': self.stop_loss_threshold
            },
            'performance': {
                'winning_rate': self._calculate_winning_rate(),
                'average_roi': self._calculate_average_roi(),
                'sharpe_ratio': self._calculate_sharpe_ratio()
            }
        }

    def _calculate_winning_rate(self) -> float:
        """计算胜率"""
        settled_bets = [p for p in self.portfolio if p.status in ['won', 'lost']]
        if not settled_bets:
            return 0.0
        winning_bets = len([p for p in settled_bets if p.status == 'won'])
        return winning_bets / len(settled_bets)

    def _calculate_average_roi(self) -> float:
        """计算平均ROI"""
        settled_bets = [p for p in self.portfolio if p.status in ['won', 'lost']]
        if not settled_bets:
            return 0.0
        total_stake = sum(p.stake for p in settled_bets)
        total_return = sum(p.result for p in settled_bets)
        return (total_return / total_stake) if total_stake > 0 else 0.0

    def _calculate_sharpe_ratio(self, periods: int = 252) -> float:
        """计算夏普比率"""
        if len(self.daily_reports) < 2:
            return 0.0

        # 计算日收益率
        daily_returns = [report.roi for report in self.daily_reports]

        if not daily_returns:
            return 0.0

        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        std_dev = variance ** 0.5

        # 年化夏普比率
        return (mean_return * periods) / (std_dev * (periods ** 0.5)) if std_dev > 0 else 0.0

    def save_strategy_state(self, filename: str = None) -> str:
        """保存策略状态"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"betting_strategy_state_{timestamp}.json"

        output_path = Path("reports") / filename
        output_path.parent.mkdir(exist_ok=True)

        state_data = {
            'strategy_summary': self.get_strategy_summary(),
            'portfolio': [
                {
                    'match_id': pos.match_id,
                    'outcome': pos.outcome,
                    'stake': pos.stake,
                    'odds': pos.odds,
                    'edge': pos.edge,
                    'confidence': pos.confidence,
                    'placed_at': pos.placed_at.isoformat(),
                    'status': pos.status,
                    'result': pos.result
                }
                for pos in self.portfolio
            ],
            'daily_reports': [
                {
                    'date': report.date.isoformat(),
                    'total_bets': report.total_bets,
                    'net_profit': report.net_profit,
                    'roi': report.roi,
                    'winning_rate': report.winning_rate
                }
                for report in self.daily_reports
            ],
            'saved_at': datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

        logger.info(f"策略状态已保存到: {output_path}")
        return str(output_path)