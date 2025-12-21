"""
价值发现引擎 - Value Betting Strategy Engine
基于边际优势(Edge)的智能投注决策系统

核心理念：P_model - P_market = Edge (边际优势)
当模型预测概率 > 市场隐含概率时，存在价值投注机会
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd
import numpy as np

from src.api.fotmob_client import get_api_client
from src.models.model_handler import get_model_handler
from src.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class BetRecommendation:
    """投注推荐结果"""
    match_id: str
    home_team: str
    away_team: str
    match_time: datetime
    market_odds: Dict[str, float]  # {'home_win': 2.10, 'draw': 3.40, 'away_win': 3.60}
    model_probabilities: Dict[str, float]  # {'home_win': 0.48, 'draw': 0.29, 'away_win': 0.23}
    market_probabilities: Dict[str, float]  # {'home_win': 0.476, 'draw': 0.294, 'away_win': 0.278}
    edges: Dict[str, float]  # {'home_win': 0.004, 'draw': -0.004, 'away_win': -0.048}
    best_bet: str  # 'home_win', 'draw', 'away_win', or 'no_value'
    edge_value: float  # 最佳边际优势
    confidence: float  # 推荐置信度 0-1
    recommendation_level: int  # 1=黄金, 2=白银, 3=预警, 0=无推荐
    kelly_fraction: Optional[float] = None  # Kelly准则建议投注比例
    expected_value: Optional[float] = None  # 期望收益率


@dataclass
class MarketData:
    """市场数据"""
    bookmaker: str
    odds_home_win: float
    odds_draw: float
    odds_away_win: float
    timestamp: datetime
    liquidity_score: float = 1.0  # 流动性评分


@dataclass
class ModelPrediction:
    """模型预测结果"""
    match_id: str
    probabilities: Dict[str, float]
    confidence: float
    feature_importance: Optional[Dict[str, float]] = None


class ValueFinder:
    """
    价值发现引擎

    战略逻辑：
    1. 获取实时市场赔率 (P_market = 1/odds)
    2. 计算模型预测概率 (P_model)
    3. 计算边际优势 Edge = P_model - P_market
    4. 基于Edge制定投注策略
    """

    def __init__(self):
        self.config = get_config()
        self.api_client = get_api_client()
        self.model_handler = get_model_handler()

        # 投注策略参数
        self.edge_thresholds = {
            'gold': 0.15,      # 黄金推荐: Edge > 15%
            'silver': 0.08,    # 白银观察: Edge > 8%
            'warning': -0.10   # 避坑预警: Edge < -10%
        }

        # Kelly准则参数
        self.kelly_fraction = 0.25  # 保守Kelly分数
        self.min_kelly_fraction = 0.01  # 最小投注比例
        self.max_kelly_fraction = 0.10  # 最大投注比例

        # 风险管理参数
        self.max_daily_bets = 5  # 每日最大投注数量
        self.max_exposure_per_match = 0.05  # 单场比赛最大风险敞口5%

        # 缓存机制
        self._market_cache = {}
        self._prediction_cache = {}

    async def get_upcoming_matches(self, days_ahead: int = 1, league: str = "Premier League") -> List[Dict]:
        """
        获取未来比赛列表

        Args:
            days_ahead: 向前获取天数
            league: 联赛名称

        Returns:
            List[Dict]: 比赛列表
        """
        try:
            logger.info(f"获取未来{days_ahead}天的{league}比赛...")

            # 这里需要实现获取比赛列表的逻辑
            # 暂时返回模拟数据
            upcoming_matches = [
                {
                    "id": "match_001",
                    "home_team": "Manchester City",
                    "away_team": "Arsenal",
                    "match_time": datetime.now() + timedelta(hours=24),
                    "league": league
                },
                {
                    "id": "match_002",
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_time": datetime.now() + timedelta(hours=26),
                    "league": league
                },
                {
                    "id": "match_003",
                    "home_team": "Tottenham",
                    "away_team": "Manchester United",
                    "match_time": datetime.now() + timedelta(hours=28),
                    "league": league
                }
            ]

            logger.info(f"成功获取{len(upcoming_matches)}场比赛")
            return upcoming_matches

        except Exception as e:
            logger.error(f"获取比赛列表失败: {e}")
            return []

    async def get_market_odds(self, match_id: str) -> List[MarketData]:
        """
        获取市场赔率数据

        Args:
            match_id: 比赛ID

        Returns:
            List[MarketData]: 市场赔率列表
        """
        try:
            # 检查缓存
            if match_id in self._market_cache:
                cache_data = self._market_cache[match_id]
                if (datetime.now() - cache_data['timestamp']).seconds < 300:  # 5分钟缓存
                    return cache_data['data']

            logger.info(f"获取比赛{match_id}的市场赔率...")

            # 这里需要实现获取实际赔率的逻辑
            # 暂时返回模拟数据，模拟不同博彩公司的赔率
            mock_odds = [
                MarketData(
                    bookmaker="Bet365",
                    odds_home_win=2.10,
                    odds_draw=3.40,
                    odds_away_win=3.60,
                    timestamp=datetime.now(),
                    liquidity_score=0.95
                ),
                MarketData(
                    bookmaker="William Hill",
                    odds_home_win=2.15,
                    odds_draw=3.30,
                    odds_away_win=3.50,
                    timestamp=datetime.now(),
                    liquidity_score=0.88
                ),
                MarketData(
                    bookmaker="Paddy Power",
                    odds_home_win=2.05,
                    odds_draw=3.50,
                    odds_away_win=3.70,
                    timestamp=datetime.now(),
                    liquidity_score=0.82
                )
            ]

            # 缓存结果
            self._market_cache[match_id] = {
                'data': mock_odds,
                'timestamp': datetime.now()
            }

            logger.info(f"成功获取{len(mock_odds)}个市场赔率")
            return mock_odds

        except Exception as e:
            logger.error(f"获取市场赔率失败: {e}")
            return []

    def get_model_prediction(self, match_data: Dict) -> ModelPrediction:
        """
        获取模型预测

        Args:
            match_data: 比赛数据

        Returns:
            ModelPrediction: 模型预测结果
        """
        try:
            match_id = match_data.get('id')

            # 检查缓存
            if match_id in self._prediction_cache:
                cache_data = self._prediction_cache[match_id]
                if (datetime.now() - cache_data['timestamp']).seconds < 1800:  # 30分钟缓存
                    return cache_data['data']

            logger.info(f"计算比赛{match_id}的模型预测...")

            # 这里需要调用实际的模型预测逻辑
            # 暂时返回模拟预测结果
            home_win_prob = np.random.uniform(0.35, 0.65)
            draw_prob = np.random.uniform(0.20, 0.35)
            away_win_prob = 1.0 - home_win_prob - draw_prob

            # 确保概率和为1
            total = home_win_prob + draw_prob + away_win_prob
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total

            prediction = ModelPrediction(
                match_id=match_id,
                probabilities={
                    'home_win': round(home_win_prob, 3),
                    'draw': round(draw_prob, 3),
                    'away_win': round(away_win_prob, 3)
                },
                confidence=np.random.uniform(0.6, 0.9)
            )

            # 缓存结果
            self._prediction_cache[match_id] = {
                'data': prediction,
                'timestamp': datetime.now()
            }

            logger.info(f"模型预测: 主胜{prediction.probabilities['home_win']:.1%} "
                       f"平局{prediction.probabilities['draw']:.1%} "
                       f"客胜{prediction.probabilities['away_win']:.1%}")

            return prediction

        except Exception as e:
            logger.error(f"模型预测失败: {e}")
            # 返回默认预测
            return ModelPrediction(
                match_id=match_data.get('id', 'unknown'),
                probabilities={'home_win': 0.33, 'draw': 0.34, 'away_win': 0.33},
                confidence=0.5
            )

    def calculate_market_probabilities(self, odds: MarketData) -> Dict[str, float]:
        """
        计算市场隐含概率（V8.0升级版 - De-wigging算法）

        Args:
            odds: 市场赔率数据

        Returns:
            Dict[str, float]: 去水后的真实公平概率
        """
        # 计算基础隐含概率（未去水）
        raw_home_prob = 1 / odds.odds_home_win
        raw_draw_prob = 1 / odds.odds_draw
        raw_away_prob = 1 / odds.odds_away_win

        # 总隐含概率（>1.0的部分就是庄家优势）
        total_implied_prob = raw_home_prob + raw_draw_prob + raw_away_prob

        # 使用多种去水算法计算真实公平概率
        dewigging_methods = {
            'proportional': self._dewig_proportional,
            'power': self._dewig_power,
            'additive': self._dewig_additive,
            'odds_ratio': self._dewig_odds_ratio
        }

        # 默认使用比例法（最常用且稳定）
        fair_probs = dewigging_methods['proportional'](
            raw_home_prob, raw_draw_prob, raw_away_prob, total_implied_prob
        )

        # 计算庄家margin（用于风险控制参考）
        bookmaker_margin = total_implied_prob - 1.0

        logger.info(f"去水算法: 总隐含概率={total_implied_prob:.4f}, "
                   f"庄家margin={bookmaker_margin:.1%}, "
                   f"去水方法=proportional")

        return fair_probs

    def _dewig_proportional(self, home_p: float, draw_p: float, away_p: float,
                          total_p: float) -> Dict[str, float]:
        """
        比例去水法 (Proportional De-wigging)
        最常用方法，按比例缩减各结果的概率
        """
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        # 归一化因子
        normalization_factor = 1.0 / total_p

        return {
            'home_win': round(home_p * normalization_factor, 4),
            'draw': round(draw_p * normalization_factor, 4),
            'away_win': round(away_p * normalization_factor, 4)
        }

    def _dewig_power(self, home_p: float, draw_p: float, away_p: float,
                    total_p: float) -> Dict[str, float]:
        """
        功率去水法 (Power De-wigging)
        使用对数变换，对高概率事件调整较少，低概率事件调整较多
        """
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        # 使用对数-幂转换
        log_home = np.log(home_p)
        log_draw = np.log(draw_p)
        log_away = np.log(away_p)

        # 调整对数概率使其和为0（对应概率和为1）
        log_sum = log_home + log_draw + log_away
        adjustment = -log_sum / 3.0

        adj_log_home = log_home + adjustment
        adj_log_draw = log_draw + adjustment
        adj_log_away = log_away + adjustment

        # 转换回概率空间
        dewigged_total = np.exp(adj_log_home) + np.exp(adj_log_draw) + np.exp(adj_log_away)

        return {
            'home_win': round(np.exp(adj_log_home) / dewigged_total, 4),
            'draw': round(np.exp(adj_log_draw) / dewigged_total, 4),
            'away_win': round(np.exp(adj_log_away) / dewigged_total, 4)
        }

    def _dewig_additive(self, home_p: float, draw_p: float, away_p: float,
                       total_p: float) -> Dict[str, float]:
        """
        加法去水法 (Additive De-wigging)
        从每个概率中减去相等的数值
        """
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        # 计算需要减去的数值
        margin_to_remove = (total_p - 1.0) / 3.0

        dewigged_home = max(home_p - margin_to_remove, 0.001)
        dewigged_draw = max(draw_p - margin_to_remove, 0.001)
        dewigged_away = max(away_p - margin_to_remove, 0.001)

        # 重新归一化确保和为1
        total_dewigged = dewigged_home + dewigged_draw + dewigged_away

        return {
            'home_win': round(dewigged_home / total_dewigged, 4),
            'draw': round(dewigged_draw / total_dewigged, 4),
            'away_win': round(dewigged_away / total_dewigged, 4)
        }

    def _dewig_odds_ratio(self, home_p: float, draw_p: float, away_p: float,
                         total_p: float) -> Dict[str, float]:
        """
        赔率比例去水法 (Odds Ratio De-wigging)
        基于赔率比例的智能去水
        """
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        # 转换为赔率
        home_odds = 1 / home_p
        draw_odds = 1 / draw_p
        away_odds = 1 / away_p

        # 调整赔率（移除margin）
        margin_factor = total_p
        fair_home_odds = home_odds * margin_factor
        fair_draw_odds = draw_odds * margin_factor
        fair_away_odds = away_odds * margin_factor

        # 转换回概率
        total_fair_odds = fair_home_odds + fair_draw_odds + fair_away_odds

        return {
            'home_win': round(fair_home_odds / total_fair_odds, 4),
            'draw': round(fair_draw_odds / total_fair_odds, 4),
            'away_win': round(fair_away_odds / total_fair_odds, 4)
        }

    def calculate_market_probabilities_comparison(self, odds: MarketData) -> Dict[str, Dict[str, float]]:
        """
        比较不同去水算法的结果（用于分析）

        Args:
            odds: 市场赔率数据

        Returns:
            Dict[str, Dict[str, float]]: 各算法的去水结果
        """
        # 计算基础隐含概率
        raw_home_prob = 1 / odds.odds_home_win
        raw_draw_prob = 1 / odds.odds_draw
        raw_away_prob = 1 / odds.odds_away_win
        total_p = raw_home_prob + raw_draw_prob + raw_away_prob

        # 所有去水方法
        methods = {
            'raw': {'home_win': raw_home_prob, 'draw': raw_draw_prob, 'away_win': raw_away_prob},
            'proportional': self._dewig_proportional(raw_home_prob, raw_draw_prob, raw_away_prob, total_p),
            'power': self._dewig_power(raw_home_prob, raw_draw_prob, raw_away_prob, total_p),
            'additive': self._dewig_additive(raw_home_prob, raw_draw_prob, raw_away_prob, total_p),
            'odds_ratio': self._dewig_odds_ratio(raw_home_prob, raw_draw_prob, raw_away_prob, total_p)
        }

        return methods

    def calculate_edges(self, model_probs: Dict[str, float], market_probs: Dict[str, float]) -> Dict[str, float]:
        """
        计算边际优势

        Args:
            model_probs: 模型预测概率
            market_probs: 市场隐含概率

        Returns:
            Dict[str, float]: 各结果的边际优势
        """
        edges = {}
        for outcome in ['home_win', 'draw', 'away_win']:
            model_p = model_probs.get(outcome, 0)
            market_p = market_probs.get(outcome, 0)
            edges[outcome] = round(model_p - market_p, 4)

        return edges

    def determine_recommendation_level(self, edges: Dict[str, float]) -> Tuple[int, str]:
        """
        确定推荐等级

        Args:
            edges: 边际优势字典

        Returns:
            Tuple[int, str]: (等级, 描述)
        """
        max_edge = max(edges.values())

        if max_edge > self.edge_thresholds['gold']:
            return 1, "黄金推荐 - 强烈价值"
        elif max_edge > self.edge_thresholds['silver']:
            return 2, "白银观察 - 适度价值"
        elif max_edge < self.edge_thresholds['warning']:
            return 3, "避坑预警 - 市场高估"
        else:
            return 0, "无推荐 - 边际优势不足"

    def calculate_kelly_fraction(self, edge: float, odds: float, confidence: float) -> float:
        """
        计算Kelly准则投注比例

        Args:
            edge: 边际优势
            odds: 赔率
            confidence: 预测置信度

        Returns:
            float: Kelly投注比例
        """
        if edge <= 0:
            return 0.0

        # Kelly公式: f* = (bp - q) / b
        # 其中: b = 赔率 - 1, p = 胜率, q = 败率
        b = odds - 1
        p = edge + (1 / odds)  # 近似胜率
        q = 1 - p

        if b <= 0 or p <= 0:
            return 0.0

        kelly_fraction = (b * p - q) / b

        # 考虑置信度调整
        kelly_fraction *= confidence

        # 保守调整
        kelly_fraction *= self.kelly_fraction

        # 限制范围
        kelly_fraction = max(self.min_kelly_fraction,
                            min(kelly_fraction, self.max_kelly_fraction))

        return round(kelly_fraction, 4)

    def calculate_expected_value(self, edge: float, odds: float) -> float:
        """
        计算期望收益率

        Args:
            edge: 边际优势
            odds: 赔率

        Returns:
            float: 期望收益率
        """
        if edge <= 0:
            return -1.0  # 负期望，不应投注

        # EV = (模型概率 * 赔率) - 1
        model_prob = edge + (1 / odds)
        ev = (model_prob * odds) - 1

        return round(ev, 4)

    async def analyze_match(self, match_data: Dict) -> Optional[BetRecommendation]:
        """
        分析单场比赛的价值投注机会

        Args:
            match_data: 比赛数据

        Returns:
            Optional[BetRecommendation]: 投注推荐
        """
        try:
            match_id = match_data.get('id')
            logger.info(f"开始分析比赛: {match_id}")

            # 1. 获取市场赔率
            market_odds_list = await self.get_market_odds(match_id)
            if not market_odds_list:
                logger.warning(f"比赛{match_id}无市场赔率数据")
                return None

            # 使用流动性最高的赔率（通常是最准确的）
            best_market = max(market_odds_list, key=lambda x: x.liquidity_score)

            # 2. 获取模型预测
            model_prediction = self.get_model_prediction(match_data)

            # 3. 计算市场隐含概率
            market_probs = self.calculate_market_probabilities(best_market)

            # 4. 计算边际优势
            edges = self.calculate_edges(
                model_prediction.probabilities,
                market_probs
            )

            # 5. 确定最佳投注选项
            best_outcome = max(edges.items(), key=lambda x: x[1])
            best_bet_type, best_edge_value = best_outcome

            # 6. 确定推荐等级
            level, level_desc = self.determine_recommendation_level(edges)

            # 7. 计算Kelly投注比例和期望收益率
            best_odds = getattr(best_market, f'odds_{best_bet_type}')
            kelly_frac = self.calculate_kelly_fraction(
                best_edge_value, best_odds, model_prediction.confidence
            )
            expected_value = self.calculate_expected_value(best_edge_value, best_odds)

            # 8. 构建推荐结果
            recommendation = BetRecommendation(
                match_id=match_id,
                home_team=match_data.get('home_team', 'Unknown'),
                away_team=match_data.get('away_team', 'Unknown'),
                match_time=match_data.get('match_time', datetime.now()),
                market_odds={
                    'home_win': best_market.odds_home_win,
                    'draw': best_market.odds_draw,
                    'away_win': best_market.odds_away_win
                },
                model_probabilities=model_prediction.probabilities,
                market_probabilities=market_probs,
                edges=edges,
                best_bet=best_bet_type if best_edge_value > 0 else 'no_value',
                edge_value=best_edge_value,
                confidence=model_prediction.confidence,
                recommendation_level=level,
                kelly_fraction=kelly_frac if kelly_frac > 0 else None,
                expected_value=expected_value if best_edge_value > 0 else None
            )

            logger.info(f"比赛{match_id}分析完成: {level_desc}")
            return recommendation

        except Exception as e:
            logger.error(f"分析比赛{match_data.get('id', 'unknown')}失败: {e}")
            return None

    async def analyze_upcoming_matches(self, days_ahead: int = 1) -> List[BetRecommendation]:
        """
        分析未来所有比赛

        Args:
            days_ahead: 向前分析天数

        Returns:
            List[BetRecommendation]: 投注推荐列表
        """
        logger.info(f"开始分析未来{days_ahead}天的比赛...")

        # 1. 获取比赛列表
        upcoming_matches = await self.get_upcoming_matches(days_ahead)

        # 2. 并发分析所有比赛
        tasks = [self.analyze_match(match) for match in upcoming_matches]
        recommendations = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 过滤有效推荐
        valid_recommendations = []
        for result in recommendations:
            if isinstance(result, BetRecommendation):
                valid_recommendations.append(result)
            elif isinstance(result, Exception):
                logger.error(f"比赛分析异常: {result}")

        logger.info(f"分析完成，发现{len(valid_recommendations)}个推荐")
        return valid_recommendations

    def get_summary_statistics(self, recommendations: List[BetRecommendation]) -> Dict:
        """
        获取推荐统计摘要

        Args:
            recommendations: 投注推荐列表

        Returns:
            Dict: 统计摘要
        """
        if not recommendations:
            return {}

        # 统计各等级推荐数量
        level_counts = {}
        for rec in recommendations:
            level = rec.recommendation_level
            level_counts[level] = level_counts.get(level, 0) + 1

        # 统计边际优势分布
        edges = [rec.edge_value for rec in recommendations if rec.edge_value > 0]
        avg_edge = np.mean(edges) if edges else 0

        # 统计期望收益率
        evs = [rec.expected_value for rec in recommendations if rec.expected_value is not None]
        avg_ev = np.mean(evs) if evs else 0

        return {
            'total_recommendations': len(recommendations),
            'gold_recommendations': level_counts.get(1, 0),
            'silver_recommendations': level_counts.get(2, 0),
            'warning_recommendations': level_counts.get(3, 0),
            'avg_edge': round(avg_edge, 4),
            'avg_expected_value': round(avg_ev, 4),
            'high_confidence_count': sum(1 for r in recommendations if r.confidence > 0.8),
            'analysis_time': datetime.now().isoformat()
        }

    async def save_recommendations(self, recommendations: List[BetRecommendation],
                                 filename: Optional[str] = None) -> str:
        """
        保存推荐结果

        Args:
            recommendations: 投注推荐列表
            filename: 文件名（可选）

        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"value_betting_recommendations_{timestamp}.json"

        output_path = Path("reports") / filename
        output_path.parent.mkdir(exist_ok=True)

        # 转换为可序列化格式
        serializable_recs = []
        for rec in recommendations:
            rec_dict = {
                'match_id': rec.match_id,
                'home_team': rec.home_team,
                'away_team': rec.away_team,
                'match_time': rec.match_time.isoformat(),
                'market_odds': rec.market_odds,
                'model_probabilities': rec.model_probabilities,
                'market_probabilities': rec.market_probabilities,
                'edges': rec.edges,
                'best_bet': rec.best_bet,
                'edge_value': rec.edge_value,
                'confidence': rec.confidence,
                'recommendation_level': rec.recommendation_level,
                'kelly_fraction': rec.kelly_fraction,
                'expected_value': rec.expected_value
            }
            serializable_recs.append(rec_dict)

        # 添加统计摘要
        summary = self.get_summary_statistics(recommendations)

        output_data = {
            'summary': summary,
            'recommendations': serializable_recs,
            'parameters': {
                'edge_thresholds': self.edge_thresholds,
                'kelly_fraction': self.kelly_fraction,
                'max_daily_bets': self.max_daily_bets
            },
            'generated_at': datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"推荐结果已保存到: {output_path}")
        return str(output_path)