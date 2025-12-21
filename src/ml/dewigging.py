"""
V8.1 De-wigging (去水) 算法模块
专业级市场真实概率计算，支持多种去水算法
"""

import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DewiggingEngine:
    """
    专业去水算法引擎

    支持四种去水算法：
    1. 比例去水法 - 最稳定，适用性广
    2. 功率去水法 - 保护高概率事件
    3. 加法去水法 - 平均调整策略
    4. 赔率比例法 - 智能赔率调整
    """

    def __init__(self, default_method: str = 'proportional'):
        self.default_method = default_method
        self.supported_methods = ['proportional', 'power', 'additive', 'odds_ratio']

    def calculate_market_probabilities(self, odds: Dict[str, float],
                                       method: Optional[str] = None) -> Dict[str, float]:
        """
        计算去水后的市场真实概率

        Args:
            odds: 市场赔率 {'home_win': 2.10, 'draw': 3.40, 'away_win': 3.60}
            method: 去水方法，默认使用比例法

        Returns:
            Dict[str, float]: 去水后的真实概率
        """
        method = method or self.default_method

        if method not in self.supported_methods:
            logger.warning(f"不支持的去水方法: {method}，使用默认方法")
            method = self.default_method

        # 计算基础隐含概率
        raw_home_prob = 1 / odds['home_win']
        raw_draw_prob = 1 / odds['draw']
        raw_away_prob = 1 / odds['away_win']
        total_implied_prob = raw_home_prob + raw_draw_prob + raw_away_prob

        # 选择去水算法
        if method == 'proportional':
            fair_probs = self._dewig_proportional(raw_home_prob, raw_draw_prob, raw_away_prob, total_implied_prob)
        elif method == 'power':
            fair_probs = self._dewig_power(raw_home_prob, raw_draw_prob, raw_away_prob, total_implied_prob)
        elif method == 'additive':
            fair_probs = self._dewig_additive(raw_home_prob, raw_draw_prob, raw_away_prob, total_implied_prob)
        elif method == 'odds_ratio':
            fair_probs = self._dewig_odds_ratio(raw_home_prob, raw_draw_prob, raw_away_prob, total_implied_prob)
        else:
            fair_probs = self._dewig_proportional(raw_home_prob, raw_draw_prob, raw_away_prob, total_implied_prob)

        # 计算庄家margin
        bookmaker_margin = total_implied_prob - 1.0

        logger.debug(f"去水算法: {method}, 总隐含概率={total_implied_prob:.4f}, "
                    f"庄家margin={bookmaker_margin:.1%}")

        return fair_probs

    def compare_all_methods(self, odds: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        比较所有去水算法的结果

        Args:
            odds: 市场赔率

        Returns:
            Dict[str, Dict[str, float]]: 各算法的去水结果
        """
        raw_home_prob = 1 / odds['home_win']
        raw_draw_prob = 1 / odds['draw']
        raw_away_prob = 1 / odds['away_win']
        total_p = raw_home_prob + raw_draw_prob + raw_away_prob

        methods = {
            'raw': {'home_win': raw_home_prob, 'draw': raw_draw_prob, 'away_win': raw_away_prob},
            'proportional': self._dewig_proportional(raw_home_prob, raw_draw_prob, raw_away_prob, total_p),
            'power': self._dewig_power(raw_home_prob, raw_draw_prob, raw_away_prob, total_p),
            'additive': self._dewig_additive(raw_home_prob, raw_draw_prob, raw_away_prob, total_p),
            'odds_ratio': self._dewig_odds_ratio(raw_home_prob, raw_draw_prob, raw_away_prob, total_p)
        }

        return methods

    def _dewig_proportional(self, home_p: float, draw_p: float, away_p: float, total_p: float) -> Dict[str, float]:
        """比例去水法 (Proportional De-wigging)"""
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        normalization_factor = 1.0 / total_p

        return {
            'home_win': round(home_p * normalization_factor, 4),
            'draw': round(draw_p * normalization_factor, 4),
            'away_win': round(away_p * normalization_factor, 4)
        }

    def _dewig_power(self, home_p: float, draw_p: float, away_p: float, total_p: float) -> Dict[str, float]:
        """功率去水法 (Power De-wigging)"""
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        # 使用对数-幂转换
        log_home = np.log(home_p)
        log_draw = np.log(draw_p)
        log_away = np.log(away_p)

        log_sum = log_home + log_draw + log_away
        adjustment = -log_sum / 3.0

        adj_log_home = log_home + adjustment
        adj_log_draw = log_draw + adjustment
        adj_log_away = log_away + adjustment

        dewigged_total = np.exp(adj_log_home) + np.exp(adj_log_draw) + np.exp(adj_log_away)

        return {
            'home_win': round(np.exp(adj_log_home) / dewigged_total, 4),
            'draw': round(np.exp(adj_log_draw) / dewigged_total, 4),
            'away_win': round(np.exp(adj_log_away) / dewigged_total, 4)
        }

    def _dewig_additive(self, home_p: float, draw_p: float, away_p: float, total_p: float) -> Dict[str, float]:
        """加法去水法 (Additive De-wigging)"""
        if total_p <= 1.0:
            return {'home_win': home_p, 'draw': draw_p, 'away_win': away_p}

        margin_to_remove = (total_p - 1.0) / 3.0

        dewigged_home = max(home_p - margin_to_remove, 0.001)
        dewigged_draw = max(draw_p - margin_to_remove, 0.001)
        dewigged_away = max(away_p - margin_to_remove, 0.001)

        total_dewigged = dewigged_home + dewigged_draw + dewigged_away

        return {
            'home_win': round(dewigged_home / total_dewigged, 4),
            'draw': round(dewigged_draw / total_dewigged, 4),
            'away_win': round(dewigged_away / total_dewigged, 4)
        }

    def _dewig_odds_ratio(self, home_p: float, draw_p: float, away_p: float, total_p: float) -> Dict[str, float]:
        """赔率比例去水法 (Odds Ratio De-wigging)"""
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

    def calculate_edge(self, model_probs: Dict[str, float], market_probs: Dict[str, float]) -> Dict[str, float]:
        """
        计算边际优势 Edge = P_model - P_market

        Args:
            model_probs: 模型预测概率
            market_probs: 市场真实概率（去水后）

        Returns:
            Dict[str, float]: 各结果的边际优势
        """
        edges = {}
        for outcome in ['home_win', 'draw', 'away_win']:
            model_p = model_probs.get(outcome, 0)
            market_p = market_probs.get(outcome, 0)
            edges[outcome] = round(model_p - market_p, 4)

        return edges

    def get_performance_stats(self, test_cases: int = 1000) -> Dict[str, float]:
        """
        获取算法性能统计

        Args:
            test_cases: 测试用例数量

        Returns:
            Dict[str, float]: 各算法的稳定性评分
        """
        np.random.seed(42)
        performance_stats = {}

        for method in self.supported_methods:
            stability_scores = []

            for _ in range(test_cases):
                # 生成随机赔率
                home_odds = np.random.uniform(1.2, 5.0)
                draw_odds = np.random.uniform(2.8, 4.5)
                away_odds = np.random.uniform(2.5, 8.0)

                odds = {'home_win': home_odds, 'draw': draw_odds, 'away_win': away_odds}
                probs = self.calculate_market_probabilities(odds, method)

                # 计算概率范围（稳定性指标）
                prob_range = max(probs.values()) - min(probs.values())
                stability_scores.append(prob_range)

            # 稳定性评分（范围越小越稳定）
            avg_range = np.mean(stability_scores)
            stability_score = 1.0 / (1.0 + np.std(stability_scores))
            performance_stats[method] = stability_score

        return performance_stats


# 全局实例
dewigging_engine = DewiggingEngine()


def calculate_market_probabilities(odds: Dict[str, float], method: str = 'proportional') -> Dict[str, float]:
    """
    便利函数：计算去水后的市场概率

    Args:
        odds: 市场赔率
        method: 去水方法

    Returns:
        Dict[str, float]: 去水后的真实概率
    """
    return dewigging_engine.calculate_market_probabilities(odds, method)


def get_dewigging_performance_report() -> Dict[str, Any]:
    """
    获取去水算法性能报告

    Returns:
        Dict[str, Any]: 详细的性能报告
    """
    try:
        performance_stats = dewigging_engine.get_performance_stats(1000)

        # 找出最佳算法
        best_method = max(performance_stats, key=performance_stats.get)
        best_score = performance_stats[best_method]

        return {
            'best_method': best_method,
            'best_score': round(best_score, 3),
            'performance_stats': performance_stats,
            'supported_methods': dewigging_engine.supported_methods,
            'default_method': dewigging_engine.default_method,
            'recommendation': f"推荐使用{best_method}算法，稳定性评分: {best_score:.3f}",
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }