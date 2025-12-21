"""
模拟回测系统 - Historical Backtesting Engine
基于168场历史数据验证Value Betting策略的盈利能力
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from pathlib import Path
import json
import matplotlib.pyplot as plt
import seaborn as sns

from .value_finder import ValueFinder, BetRecommendation
from .betting_strategy import BettingStrategyManager, PortfolioPosition

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """回测结果"""
    total_bets: int
    winning_bets: int
    losing_bets: int
    winning_rate: float
    total_stake: float
    total_returns: float
    net_profit: float
    roi: float
    max_drawdown: float
    max_drawdown_duration: int  # 最大回撤持续时间（天）
    sharpe_ratio: float
    profit_factor: float  # 盈利因子：总盈利/总亏损
    average_edge: float
    kelly_performance: Dict
    monthly_performance: Dict
    recommendations: List[Dict] = None


@dataclass
class PerformanceMetrics:
    """性能指标"""
    daily_pnl: List[float]
    cumulative_pnl: List[float]
    running_max: List[float]
    drawdowns: List[float]
    monthly_returns: Dict[str, float]


class HistoricalDataLoader:
    """历史数据加载器"""

    def __init__(self):
        self.data_path = Path("data/final_v7_solid_features.csv")

    def load_historical_data(self) -> pd.DataFrame:
        """
        加载历史比赛数据

        Returns:
            pd.DataFrame: 历史数据
        """
        try:
            logger.info(f"加载历史数据: {self.data_path}")

            if not self.data_path.exists():
                # 如果文件不存在，创建模拟数据
                logger.warning("历史数据文件不存在，创建模拟数据...")
                return self._create_mock_historical_data()

            df = pd.read_csv(self.data_path)
            logger.info(f"成功加载{len(df)}场比赛数据")

            # 数据清洗和预处理
            df = self._preprocess_data(df)
            return df

        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")
            return self._create_mock_historical_data()

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """预处理历史数据"""
        # 检查必要列
        required_columns = ['result', 'home_team', 'away_team']
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"缺少必要列: {col}")
                # 添加默认值
                if col == 'result':
                    df[col] = np.random.choice([0, 1, 2], size=len(df))
                else:
                    df[col] = f"Team_{np.random.randint(1000, 9999)}"

        # 添加模拟赔率列（如果没有）
        if 'odds_home_win' not in df.columns:
            df['odds_home_win'] = np.random.uniform(1.8, 3.5, size=len(df))
        if 'odds_draw' not in df.columns:
            df['odds_draw'] = np.random.uniform(3.0, 4.5, size=len(df))
        if 'odds_away_win' not in df.columns:
            df['odds_away_win'] = np.random.uniform(2.0, 4.0, size=len(df))

        # 添加日期列（如果没有）
        if 'match_date' not in df.columns:
            start_date = datetime.now() - timedelta(days=365)
            df['match_date'] = [start_date + timedelta(days=i) for i in range(len(df))]

        return df

    def _create_mock_historical_data(self) -> pd.DataFrame:
        """创建模拟历史数据"""
        logger.info("创建168场模拟历史数据...")

        # 生成日期序列
        start_date = datetime.now() - timedelta(days=168)
        dates = [start_date + timedelta(days=i) for i in range(168)]

        # 生成比赛数据
        teams = ['Man City', 'Liverpool', 'Chelsea', 'Arsenal', 'Man United',
                'Tottenham', 'Leicester', 'West Ham', 'Everton', 'Wolves']

        data = []
        for i in range(168):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 模拟真实比分分布
            result = np.random.choice([0, 1, 2], p=[0.25, 0.45, 0.30])

            # 生成特征数据
            home_xg = np.random.normal(1.5, 0.8)
            away_xg = np.random.normal(1.2, 0.6)
            home_possession = np.random.normal(55, 15)
            home_shots = np.random.poisson(15)

            # 生成赔率（基于隐含概率）
            implied_prob_home = 1 / np.random.uniform(1.8, 3.5)
            implied_prob_draw = 1 / np.random.uniform(3.0, 4.5)
            implied_prob_away = 1 - implied_prob_home - implied_prob_draw

            # 添加一些随机噪声使赔率更真实
            odds_home = 1 / implied_prob_home * np.random.uniform(0.95, 1.05)
            odds_draw = 1 / implied_prob_draw * np.random.uniform(0.95, 1.05)
            odds_away = 1 / implied_prob_away * np.random.uniform(0.95, 1.05)

            data.append({
                'match_date': dates[i],
                'home_team': home_team,
                'away_team': away_team,
                'result': result,
                'home_xg': max(0, home_xg),
                'away_xg': max(0, away_xg),
                'home_possession': max(0, min(100, home_possession)),
                'away_possession': max(0, min(100, 100 - home_possession)),
                'home_shots': max(0, home_shots),
                'away_shots': max(0, np.random.poisson(12)),
                'home_corners': np.random.poisson(6),
                'away_corners': np.random.poisson(5),
                'home_yellow_cards': np.random.poisson(2),
                'away_yellow_cards': np.random.poisson(2),
                'home_red_cards': np.random.binomial(1, 0.05),
                'away_red_cards': np.random.binomial(1, 0.05),
                'odds_home_win': round(odds_home, 2),
                'odds_draw': round(odds_draw, 2),
                'odds_away_win': round(odds_away, 2)
            })

        return pd.DataFrame(data)


class Backtester:
    """
    回测引擎

    核心功能：
    1. 历史数据回测
    2. 性能指标计算
    3. 风险分析
    4. 可视化报告
    """

    def __init__(self):
        self.value_finder = ValueFinder()
        self.strategy_manager = BettingStrategyManager()
        self.data_loader = HistoricalDataLoader()

        # 回测参数
        self.initial_capital = 1000.0  # 初始资金
        self.fixed_stake = 10.0  # 固定投注金额
        self.kelly_stake = True  # 是否使用Kelly投注
        self.commission_rate = 0.02  # 手续费率

    def run_backtest(self, strategy_name: str = 'moderate') -> BacktestResult:
        """
        运行完整回测

        Args:
            strategy_name: 投注策略名称

        Returns:
            BacktestResult: 回测结果
        """
        logger.info(f"开始回测，策略: {strategy_name}")

        # 1. 加载历史数据
        historical_data = self.data_loader.load_historical_data()
        logger.info(f"加载{len(historical_data)}场历史比赛")

        # 2. 设置投注策略
        self.strategy_manager.set_strategy(strategy_name)

        # 3. 生成投注推荐
        recommendations = self._generate_historical_recommendations(historical_data)

        # 4. 执行模拟投注
        results = self._execute_simulated_betting(recommendations, historical_data)

        # 5. 计算性能指标
        backtest_result = self._calculate_performance_metrics(results)

        # 6. 生成报告
        self._generate_backtest_report(backtest_result, strategy_name)

        logger.info(f"回测完成: 总投注{backtest_result.total_bets}次, "
                   f"ROI: {backtest_result.roi:.2%}, 胜率: {backtest_result.winning_rate:.2%}")

        return backtest_result

    def _generate_historical_recommendations(self, historical_data: pd.DataFrame) -> List[BetRecommendation]:
        """生成历史投注推荐"""
        recommendations = []

        for idx, row in historical_data.iterrows():
            try:
                # 模拟比赛数据
                match_data = {
                    'id': f"historical_{idx}",
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'match_time': pd.to_datetime(row['match_date']),
                    'league': 'Premier League'
                }

                # 获取特征数据
                features = {
                    'home_xg': row['home_xg'],
                    'away_xg': row['away_xg'],
                    'home_possession': row['home_possession'],
                    'away_possession': row['away_possession'],
                    'home_shots': row['home_shots'],
                    'away_shots': row['away_shots'],
                    'home_corners': row['home_corners'],
                    'away_corners': row['away_corners'],
                    'home_yellow_cards': row['home_yellow_cards'],
                    'away_yellow_cards': row['away_yellow_cards'],
                    'home_red_cards': row['home_red_cards'],
                    'away_red_cards': row['away_red_cards']
                }

                # 模拟市场赔率
                market_odds = [
                    type('MarketOdds', (), {
                        'bookmaker': 'Historical',
                        'odds_home_win': row['odds_home_win'],
                        'odds_draw': row['odds_draw'],
                        'odds_away_win': row['odds_away_win'],
                        'timestamp': pd.to_datetime(row['match_date']),
                        'liquidity_score': 1.0
                    })()
                ]

                # 模拟模型预测（基于特征和实际结果）
                model_probs = self._simulate_model_prediction(features, row['result'])

                # 创建推荐
                recommendation = BetRecommendation(
                    match_id=match_data['id'],
                    home_team=match_data['home_team'],
                    away_team=match_data['away_team'],
                    match_time=match_data['match_time'],
                    market_odds={
                        'home_win': row['odds_home_win'],
                        'draw': row['odds_draw'],
                        'away_win': row['odds_away_win']
                    },
                    model_probabilities=model_probs,
                    market_probabilities=self.value_finder.calculate_market_probabilities(market_odds[0]),
                    edges=self.value_finder.calculate_edges(
                        model_probs,
                        self.value_finder.calculate_market_probabilities(market_odds[0])
                    ),
                    best_bet='home_win',  # 将在实际计算中确定
                    edge_value=0.0,  # 将在实际计算中确定
                    confidence=0.7,
                    recommendation_level=1,  # 将在实际计算中确定
                    kelly_fraction=0.05
                )

                # 计算实际的最佳投注和边际优势
                edges = recommendation.edges
                best_outcome = max(edges.items(), key=lambda x: x[1])
                recommendation.best_bet = best_outcome[0]
                recommendation.edge_value = best_outcome[1]

                # 计算Kelly分数和期望值
                best_odds = recommendation.market_odds[recommendation.best_bet]
                recommendation.kelly_fraction = self.value_finder.calculate_kelly_fraction(
                    recommendation.edge_value, best_odds, recommendation.confidence
                )
                recommendation.expected_value = self.value_finder.calculate_expected_value(
                    recommendation.edge_value, best_odds
                )

                # 确定推荐等级
                level, _ = self.strategy_manager.determine_recommendation_level(edges)
                recommendation.recommendation_level = level

                recommendations.append(recommendation)

            except Exception as e:
                logger.error(f"生成第{idx}场比赛推荐失败: {e}")
                continue

        logger.info(f"生成{len(recommendations)}个历史投注推荐")
        return recommendations

    def _simulate_model_prediction(self, features: Dict, actual_result: int) -> Dict[str, float]:
        """
        模拟模型预测

        Args:
            features: 特征数据
            actual_result: 实际结果

        Returns:
            Dict[str, float]: 预测概率
        """
        # 基于特征和实际结果生成合理的预测概率
        # 这里使用简化的逻辑，实际应用中应该使用训练好的模型

        # xG差异影响
        xg_diff = features.get('home_xg', 1.5) - features.get('away_xg', 1.2)

        # 控球率影响
        possession_diff = features.get('home_possession', 50) - 50

        # 射门差异影响
        shots_diff = features.get('home_shots', 15) - features.get('away_shots', 12)

        # 计算基础概率
        home_advantage = 0.1  # 主场优势

        # 线性组合特征
        feature_score = (xg_diff * 0.3 + possession_diff * 0.01 + shots_diff * 0.02 + home_advantage)

        # 转换为概率（使用softmax）
        import math
        scores = {
            'home_win': feature_score,
            'draw': 0.0,
            'away_win': -feature_score * 0.8
        }

        # Softmax转换
        exp_scores = {k: math.exp(v) for k, v in scores.items()}
        total_exp = sum(exp_scores.values())
        probabilities = {k: v / total_exp for k, v in exp_scores.items()}

        # 添加一些随机噪声，使预测更真实
        noise_factor = 0.1
        for outcome in probabilities:
            probabilities[outcome] += np.random.normal(0, noise_factor)

        # 重新归一化
        total = sum(probabilities.values())
        probabilities = {k: v / total for k, v in probabilities.items()}

        # 确保概率在合理范围内
        for outcome in probabilities:
            probabilities[outcome] = max(0.05, min(0.95, probabilities[outcome]))

        return {k: round(v, 3) for k, v in probabilities.items()}

    def _execute_simulated_betting(self, recommendations: List[BetRecommendation],
                                  historical_data: pd.DataFrame) -> List[Dict]:
        """
        执行模拟投注

        Args:
            recommendations: 投注推荐列表
            historical_data: 历史数据

        Returns:
            List[Dict]: 投注结果列表
        """
        results = []
        current_capital = self.initial_capital

        for i, rec in enumerate(recommendations):
            try:
                # 评估推荐
                evaluation = self.strategy_manager.evaluate_recommendation(rec)

                # 只执行推荐的投注
                if evaluation['action'] != 'bet':
                    continue

                # 确定投注金额
                if self.kelly_stake and rec.kelly_fraction:
                    stake = rec.kelly_fraction * current_capital
                else:
                    stake = self.fixed_stake

                # 限制投注金额（不超过当前资金的5%）
                max_stake = current_capital * 0.05
                stake = min(stake, max_stake)

                if stake <= 0:
                    continue

                # 获取实际结果
                actual_result = historical_data.iloc[i]['result']
                result_map = {0: 'draw', 1: 'home_win', 2: 'away_win'}
                actual_outcome = result_map.get(actual_result, 'draw')

                # 计算投注结果
                bet_outcome = rec.best_bet
                bet_odds = rec.market_odds[bet_outcome]

                if actual_outcome == bet_outcome:
                    # 投注获胜
                    returns = stake * bet_odds
                    profit = returns - stake - (returns * self.commission_rate)  # 扣除手续费
                    won = True
                else:
                    # 投注失败
                    profit = -stake
                    returns = 0
                    won = False

                # 更新资金
                current_capital += profit

                # 记录结果
                result = {
                    'match_id': rec.match_id,
                    'match_date': historical_data.iloc[i]['match_date'],
                    'home_team': rec.home_team,
                    'away_team': rec.away_team,
                    'bet_outcome': bet_outcome,
                    'actual_outcome': actual_outcome,
                    'odds': bet_odds,
                    'stake': stake,
                    'returns': returns,
                    'profit': profit,
                    'won': won,
                    'capital_before': current_capital - profit,
                    'capital_after': current_capital,
                    'edge': rec.edge_value,
                    'confidence': rec.confidence,
                    'recommendation_level': rec.recommendation_level,
                    'kelly_fraction': rec.kelly_fraction,
                    'expected_value': rec.expected_value
                }

                results.append(result)

            except Exception as e:
                logger.error(f"执行第{i}场模拟投注失败: {e}")
                continue

        logger.info(f"模拟投注完成，共{len(results)}次投注")
        return results

    def _calculate_performance_metrics(self, results: List[Dict]) -> BacktestResult:
        """
        计算性能指标

        Args:
            results: 投注结果列表

        Returns:
            BacktestResult: 回测结果
        """
        if not results:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, {}, {})

        # 基本统计
        total_bets = len(results)
        winning_bets = len([r for r in results if r['won']])
        losing_bets = total_bets - winning_bets
        winning_rate = winning_bets / total_bets if total_bets > 0 else 0

        # 资金统计
        total_stake = sum(r['stake'] for r in results)
        total_returns = sum(r['returns'] for r in results if r['won'])
        net_profit = sum(r['profit'] for r in results)
        roi = (net_profit / total_stake) if total_stake > 0 else 0

        # 最大回撤计算
        capital_series = [r['capital_after'] for r in results]
        running_max = np.maximum.accumulate(capital_series)
        drawdown_series = running_max - capital_series
        max_drawdown = max(drawdown_series) if len(drawdown_series) > 0 else 0

        # 最大回撤持续时间
        max_drawdown_duration = self._calculate_max_drawdown_duration(drawdown_series)

        # 夏普比率
        daily_returns = [r['profit'] / r['capital_before'] for r in results if r['capital_before'] > 0]
        if len(daily_returns) > 1:
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        else:
            sharpe_ratio = 0

        # 盈利因子
        total_wins = sum(r['profit'] for r in results if r['profit'] > 0)
        total_losses = abs(sum(r['profit'] for r in results if r['profit'] < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # 平均边际优势
        avg_edge = np.mean([r['edge'] for r in results if r['edge'] > 0])

        # Kelly表现分析
        kelly_performance = self._analyze_kelly_performance(results)

        # 月度表现分析
        monthly_performance = self._analyze_monthly_performance(results)

        return BacktestResult(
            total_bets=total_bets,
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            winning_rate=winning_rate,
            total_stake=total_stake,
            total_returns=total_returns,
            net_profit=net_profit,
            roi=roi,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            average_edge=avg_edge,
            kelly_performance=kelly_performance,
            monthly_performance=monthly_performance
        )

    def _calculate_max_drawdown_duration(self, drawdown_series: np.ndarray) -> int:
        """计算最大回撤持续时间"""
        if len(drawdown_series) == 0:
            return 0

        max_duration = 0
        current_duration = 0

        for dd in drawdown_series:
            if dd > 0:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        return max_duration

    def _analyze_kelly_performance(self, results: List[Dict]) -> Dict:
        """分析Kelly投注表现"""
        kelly_results = [r for r in results if r.get('kelly_fraction', 0) > 0]
        non_kelly_results = [r for r in results if r.get('kelly_fraction', 0) == 0]

        kelly_roi = (sum(r['profit'] for r in kelly_results) /
                    sum(r['stake'] for r in kelly_results)) if kelly_results else 0
        non_kelly_roi = (sum(r['profit'] for r in non_kelly_results) /
                       sum(r['stake'] for r in non_kelly_results)) if non_kelly_results else 0

        return {
            'kelly_bets': len(kelly_results),
            'non_kelly_bets': len(non_kelly_results),
            'kelly_roi': kelly_roi,
            'non_kelly_roi': non_kelly_roi,
            'kelly_outperformance': kelly_roi - non_kelly_roi
        }

    def _analyze_monthly_performance(self, results: List[Dict]) -> Dict:
        """分析月度表现"""
        if not results:
            return {}

        monthly_data = {}
        for result in results:
            month_key = result['match_date'][:7]  # YYYY-MM
            if month_key not in monthly_data:
                monthly_data[month_key] = {'profit': 0, 'stake': 0, 'bets': 0}
            monthly_data[month_key]['profit'] += result['profit']
            monthly_data[month_key]['stake'] += result['stake']
            monthly_data[month_key]['bets'] += 1

        monthly_performance = {}
        for month, data in monthly_data.items():
            roi = (data['profit'] / data['stake']) if data['stake'] > 0 else 0
            monthly_performance[month] = {
                'profit': data['profit'],
                'stake': data['stake'],
                'bets': data['bets'],
                'roi': roi
            }

        return monthly_performance

    def _generate_backtest_report(self, result: BacktestResult, strategy_name: str):
        """生成回测报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path("reports") / f"backtest_report_{strategy_name}_{timestamp}.json"
        report_path.parent.mkdir(exist_ok=True)

        report_data = {
            'strategy': strategy_name,
            'backtest_period': f"168 historical matches",
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital + result.net_profit,
            'performance': {
                'total_bets': result.total_bets,
                'winning_bets': result.winning_bets,
                'winning_rate': result.winning_rate,
                'roi': result.roi,
                'net_profit': result.net_profit,
                'max_drawdown': result.max_drawdown,
                'max_drawdown_duration': result.max_drawdown_duration,
                'sharpe_ratio': result.sharpe_ratio,
                'profit_factor': result.profit_factor,
                'average_edge': result.average_edge
            },
            'kelly_analysis': result.kelly_performance,
            'monthly_performance': result.monthly_performance,
            'recommendations_summary': {
                'gold_level': sum(1 for r in result.recommendations if r.get('recommendation_level') == 1),
                'silver_level': sum(1 for r in result.recommendations if r.get('recommendation_level') == 2),
                'warning_level': sum(1 for r in result.recommendations if r.get('recommendation_level') == 3)
            },
            'generated_at': datetime.now().isoformat()
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"回测报告已保存到: {report_path}")

        # 生成可视化报告
        self._generate_visualization_report(result, strategy_name, timestamp)

    def _generate_visualization_report(self, result: BacktestResult, strategy_name: str, timestamp: str):
        """生成可视化报告"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            # 设置图表样式
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(f'Value Betting Backtest Report - {strategy_name}', fontsize=16, fontweight='bold')

            # 1. 资金曲线
            if result.recommendations:
                capital_data = [r['capital_after'] for r in result.recommendations]
                axes[0, 0].plot(capital_data, linewidth=2, color='blue')
                axes[0, 0].set_title('Capital Curve')
                axes[0, 0].set_xlabel('Bet Number')
                axes[0, 0].set_ylabel('Capital ($)')
                axes[0, 0].grid(True, alpha=0.3)

            # 2. 月度收益
            if result.monthly_performance:
                months = list(result.monthly_performance.keys())
                monthly_profits = [result.monthly_performance[m]['profit'] for m in months]
                monthly_rois = [result.monthly_performance[m]['roi'] for m in months]

                color = 'green' if monthly_profits[-1] > 0 else 'red'
                axes[0, 1].bar(months, monthly_profits, color=color, alpha=0.7)
                axes[0, 1].set_title('Monthly Profit')
                axes[0, 1].set_xlabel('Month')
                axes[0, 1].set_ylabel('Profit ($)')
                axes[0, 1].tick_params(axis='x', rotation=45)

            # 3. 胜率统计
            win_labels = ['Win', 'Loss']
            win_counts = [result.winning_bets, result.losing_bets]
            colors = ['green', 'red']

            axes[1, 0].pie(win_counts, labels=win_labels, colors=colors, autopct='%1.1f%%')
            axes[1, 0].set_title(f'Win Rate: {result.winning_rate:.1%}')

            # 4. 边际优势分布
            if result.recommendations:
                edges = [r['edge'] for r in result.recommendations if r['edge'] > 0]
                axes[1, 1].hist(edges, bins=20, alpha=0.7, color='orange', edgecolor='black')
                axes[1, 1].set_title('Edge Distribution')
                axes[1, 1].set_xlabel('Edge Value')
                axes[1, 1].set_ylabel('Frequency')
                axes[1, 1].axvline(result.average_edge, color='red', linestyle='--', label=f'Avg: {result.average_edge:.3f}')
                axes[1, 1].legend()

            plt.tight_layout()

            # 保存图表
            chart_path = Path("reports") / f"backtest_charts_{strategy_name}_{timestamp}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"可视化报告已保存到: {chart_path}")

        except Exception as e:
            logger.error(f"生成可视化报告失败: {e}")

    def compare_strategies(self, strategies: List[str]) -> Dict:
        """
        比较不同策略的表现

        Args:
            strategies: 策略名称列表

        Returns:
            Dict: 策略比较结果
        """
        comparison_results = {}

        for strategy in strategies:
            try:
                logger.info(f"回测策略: {strategy}")
                result = self.run_backtest(strategy)
                comparison_results[strategy] = {
                    'roi': result.roi,
                    'winning_rate': result.winning_rate,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'total_bets': result.total_bets,
                    'net_profit': result.net_profit
                }
            except Exception as e:
                logger.error(f"策略{strategy}回测失败: {e}")
                comparison_results[strategy] = {'error': str(e)}

        # 生成比较报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_path = Path("reports") / f"strategy_comparison_{timestamp}.json"
        comparison_path.parent.mkdir(exist_ok=True)

        with open(comparison_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, indent=2, ensure_ascii=False)

        logger.info(f"策略比较报告已保存到: {comparison_path}")

        return comparison_results