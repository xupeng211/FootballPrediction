#!/usr/bin/env python3
"""
V19.4 执行阈值过滤器 (Execution Threshold Filter)
=================================================

针对审计中发现的"低价值预测过多"问题，引入执行阈值过滤机制：
- 只有当模型预测概率与市场基准概率的差距超过阈值时才执行下注
- 默认阈值：5% (0.05)

目标：减少低价值预测，提高整体 Yield

作者: V19.4量化策略团队
日期: 2025-12-23
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExecutionThresholdFilter:
    """
    执行阈值过滤器

    核心功能:
    1. 置信度差距计算：模型概率 - 市场基准概率
    2. 执行信号生成：只有当差距超过阈值时才生成执行信号
    3. 性能对比：对比全量执行 vs 阈值过滤执行的绩效
    """

    def __init__(self, threshold: float = 0.05):
        """
        初始化执行阈值过滤器

        Args:
            threshold: 执行阈值（默认 0.05 = 5%）
        """
        self.threshold = threshold
        logger.info(f"执行阈值过滤器初始化完成，阈值: {threshold:.2%}")

    def calculate_confidence_gap(
        self,
        model_prob_h: float,
        model_prob_d: float,
        model_prob_a: float,
        market_prob_h: float,
        market_prob_d: float,
        market_prob_a: float
    ) -> Dict[str, float]:
        """
        计算置信度差距

        Args:
            model_prob_h: 模型预测主胜概率
            model_prob_d: 模型预测平局概率
            model_prob_a: 模型预测客胜概率
            market_prob_h: 市场基准主胜概率
            market_prob_d: 市场基准平局概率
            market_prob_a: 市场基准客胜概率

        Returns:
            Dict: {
                'gap_h': 主胜置信度差距,
                'gap_d': 平局置信度差距,
                'gap_a': 客胜置信度差距,
                'max_gap': 最大置信度差距,
                'prediction_with_gap': 有差距支持的预测结果
            }
        """
        gap_h = model_prob_h - market_prob_h
        gap_d = model_prob_d - market_prob_d
        gap_a = model_prob_a - market_prob_a

        # 确定预测结果
        prediction_probs = {'H': model_prob_h, 'D': model_prob_d, 'A': model_prob_a}
        prediction = max(prediction_probs, key=prediction_probs.get)

        # 检查是否有足够的置信度差距支持
        gap_map = {'H': gap_h, 'D': gap_d, 'A': gap_a}
        has_confidence_gap = gap_map[prediction] >= self.threshold

        return {
            'gap_h': gap_h,
            'gap_d': gap_d,
            'gap_a': gap_a,
            'max_gap': max(gap_h, gap_d, gap_a),
            'prediction': prediction,
            'gap_for_prediction': gap_map[prediction],
            'has_confidence_gap': has_confidence_gap
        }

    def should_execute(
        self,
        model_prob_h: float,
        model_prob_d: float,
        model_prob_a: float,
        market_prob_h: float,
        market_prob_d: float,
        market_prob_a: float
    ) -> Tuple[bool, str, float]:
        """
        判断是否应该执行下注

        Args:
            model_prob_h: 模型预测主胜概率
            model_prob_d: 模型预测平局概率
            model_prob_a: 模型预测客胜概率
            market_prob_h: 市场基准主胜概率
            market_prob_d: 市场基准平局概率
            market_prob_a: 市场基准客胜概率

        Returns:
            Tuple[bool, str, float]: (是否执行, 预测结果, 置信度差距)
        """
        gap_info = self.calculate_confidence_gap(
            model_prob_h, model_prob_d, model_prob_a,
            market_prob_h, market_prob_d, market_prob_a
        )

        should_bet = gap_info['has_confidence_gap']
        prediction = gap_info['prediction']
        gap = gap_info['gap_for_prediction']

        return should_bet, prediction, gap

    def filter_execution_signals(
        self,
        df: pd.DataFrame,
        model_prob_col_prefix: str = 'model_prob_',
        market_prob_col_prefix: str = 'market_prob_'
    ) -> pd.DataFrame:
        """
        对数据框应用执行阈值过滤

        Args:
            df: 包含模型和市场概率的数据框
            model_prob_col_prefix: 模型概率列名前缀
            market_prob_col_prefix: 市场概率列名前缀

        Returns:
            添加了执行信号的新数据框
        """
        logger.info(f"开始应用执行阈值过滤，阈值: {self.threshold:.2%}")

        results = []

        for idx, row in df.iterrows():
            # 获取模型和市场概率
            model_prob_h = row.get(f'{model_prob_col_prefix}h', 0)
            model_prob_d = row.get(f'{model_prob_col_prefix}d', 0)
            model_prob_a = row.get(f'{model_prob_col_prefix}a', 0)

            market_prob_h = row.get(f'{market_prob_col_prefix}h', 0)
            market_prob_d = row.get(f'{market_prob_col_prefix}d', 0)
            market_prob_a = row.get(f'{market_prob_col_prefix}a', 0)

            # 计算置信度差距
            gap_info = self.calculate_confidence_gap(
                model_prob_h, model_prob_d, model_prob_a,
                market_prob_h, market_prob_d, market_prob_a
            )

            # 添加到结果
            result_row = row.copy()
            result_row['gap_h'] = gap_info['gap_h']
            result_row['gap_d'] = gap_info['gap_d']
            result_row['gap_a'] = gap_info['gap_a']
            result_row['max_gap'] = gap_info['max_gap']
            result_row['confidence_gap'] = gap_info['gap_for_prediction']
            result_row['has_confidence_gap'] = gap_info['has_confidence_gap']
            result_row['filtered_prediction'] = gap_info['prediction'] if gap_info['has_confidence_gap'] else None

            results.append(result_row)

        result_df = pd.DataFrame(results)

        # 统计过滤效果
        total_count = len(result_df)
        filtered_count = result_df['has_confidence_gap'].sum()
        filter_rate = (total_count - filtered_count) / total_count * 100 if total_count > 0 else 0

        logger.info(f"执行阈值过滤完成:")
        logger.info(f"  总场次: {total_count}")
        logger.info(f"  通过过滤: {filtered_count} ({filtered_count/total_count*100:.1f}%)")
        logger.info(f"  被过滤: {total_count - filtered_count} ({filter_rate:.1f}%)")

        return result_df

    def calculate_filtered_yield(
        self,
        df: pd.DataFrame,
        result_col: str = 'result_score',
        odds_col_prefix: str = 'b365_'
    ) -> Dict[str, float]:
        """
        计算阈值过滤后的理论执行绩效 (Yield)

        Args:
            df: 包含过滤信号的数据框
            result_col: 实际结果列名
            odds_col_prefix: 市场赔率列名前缀

        Returns:
            Dict: 绩效统计
        """
        # 只选择通过过滤的比赛
        filtered_df = df[df['has_confidence_gap'] == True].copy()

        if len(filtered_df) == 0:
            logger.warning("没有通过过滤的比赛，无法计算 Yield")
            return {
                'total_bets': 0,
                'total_yield': 0.0,
                'yield_percentage': 0.0,
                'avg_return': 0.0
            }

        total_bets = len(filtered_df)
        total_yield = 0.0

        for idx, row in filtered_df.iterrows():
            prediction = row['filtered_prediction']
            actual = row.get(result_col, None)

            if prediction is None or actual is None:
                continue

            # 获取对应结果的市场赔率
            if prediction == 'H':
                odds = row.get(f'{odds_col_prefix}home_odds', 1.0)
            elif prediction == 'D':
                odds = row.get(f'{odds_col_prefix}draw_odds', 1.0)
            else:  # 'A'
                odds = row.get(f'{odds_col_prefix}away_odds', 1.0)

            # 计算收益（下注1单位）
            if prediction == actual:
                total_yield += (odds - 1)  # 净收益
            else:
                total_yield -= 1  # 损失本金

        yield_pct = (total_yield / total_bets * 100) if total_bets > 0 else 0
        avg_return = ((total_yield + total_bets) / total_bets) if total_bets > 0 else 0

        return {
            'total_bets': total_bets,
            'total_yield': total_yield,
            'yield_percentage': yield_pct,
            'avg_return': avg_return
        }

    def compare_execution_modes(
        self,
        df: pd.DataFrame,
        result_col: str = 'result_score',
        odds_col_prefix: str = 'b365_'
    ) -> Dict[str, Dict]:
        """
        对比全量执行 vs 阈值过滤执行的绩效

        Args:
            df: 包含预测和赔率的数据框
            result_col: 实际结果列名
            odds_col_prefix: 市场赔率列名前缀

        Returns:
            Dict: 全量执行和过滤执行的绩效对比
        """
        # 1. 全量执行模式（所有预测都下注）
        full_execution_yield = self._calculate_full_yield(df, result_col, odds_col_prefix)

        # 2. 阈值过滤执行模式（只对有置信度差距的下注）
        filtered_df = self.filter_execution_signals(df)
        filtered_yield = self.calculate_filtered_yield(filtered_df, result_col, odds_col_prefix)

        # 3. 计算改进指标
        improvement = {
            'yield_improvement': filtered_yield['yield_percentage'] - full_execution_yield['yield_percentage'],
            'yield_improvement_pct': (
                (filtered_yield['yield_percentage'] - full_execution_yield['yield_percentage']) /
                abs(full_execution_yield['yield_percentage']) * 100
                if full_execution_yield['yield_percentage'] != 0 else 0
            ),
            'bet_reduction': full_execution_yield['total_bets'] - filtered_yield['total_bets'],
            'bet_reduction_pct': (
                (full_execution_yield['total_bets'] - filtered_yield['total_bets']) /
                full_execution_yield['total_bets'] * 100
                if full_execution_yield['total_bets'] > 0 else 0
            )
        }

        return {
            'full_execution': full_execution_yield,
            'filtered_execution': filtered_yield,
            'improvement': improvement
        }

    def _calculate_full_yield(
        self,
        df: pd.DataFrame,
        result_col: str,
        odds_col_prefix: str
    ) -> Dict[str, float]:
        """计算全量执行的 Yield"""
        total_bets = len(df)
        total_yield = 0.0

        for idx, row in df.iterrows():
            prediction = row.get('predicted_result', None)
            actual = row.get(result_col, None)

            if prediction is None or actual is None:
                continue

            # 获取对应结果的市场赔率
            if prediction == 'H':
                odds = row.get(f'{odds_col_prefix}home_odds', 1.0)
            elif prediction == 'D':
                odds = row.get(f'{odds_col_prefix}draw_odds', 1.0)
            else:  # 'A'
                odds = row.get(f'{odds_col_prefix}away_odds', 1.0)

            # 计算收益
            if prediction == actual:
                total_yield += (odds - 1)
            else:
                total_yield -= 1

        yield_pct = (total_yield / total_bets * 100) if total_bets > 0 else 0
        avg_return = ((total_yield + total_bets) / total_bets) if total_bets > 0 else 0

        return {
            'total_bets': total_bets,
            'total_yield': total_yield,
            'yield_percentage': yield_pct,
            'avg_return': avg_return
        }


def apply_execution_threshold_filter(
    df: pd.DataFrame,
    threshold: float = 0.05,
    model_prob_col_prefix: str = 'model_prob_',
    market_prob_col_prefix: str = 'market_prob_'
) -> pd.DataFrame:
    """
    应用执行阈值过滤的便捷函数

    Args:
        df: 包含模型和市场概率的数据框
        threshold: 执行阈值（默认 0.05 = 5%）
        model_prob_col_prefix: 模型概率列名前缀
        market_prob_col_prefix: 市场概率列名前缀

    Returns:
        添加了执行信号的数据框
    """
    filter_engine = ExecutionThresholdFilter(threshold=threshold)
    return filter_engine.filter_execution_signals(df, model_prob_col_prefix, market_prob_col_prefix)


# ============================================
# 单元测试
# ============================================

if __name__ == "__main__":
    # 测试数据
    test_data = pd.DataFrame({
        'model_prob_h': [0.55, 0.40, 0.30, 0.60],
        'model_prob_d': [0.25, 0.35, 0.40, 0.25],
        'model_prob_a': [0.20, 0.25, 0.30, 0.15],
        'market_prob_h': [0.50, 0.42, 0.28, 0.58],
        'market_prob_d': [0.28, 0.33, 0.38, 0.27],
        'market_prob_a': [0.22, 0.25, 0.34, 0.15],
        'predicted_result': ['H', 'D', 'A', 'H'],
        'result_score': ['H', 'D', 'H', 'A'],
        'b365_home_odds': [2.0, 2.4, 3.2, 1.8],
        'b365_draw_odds': [3.6, 3.0, 2.6, 3.8],
        'b365_away_odds': [4.5, 4.0, 2.9, 5.0]
    })

    # 测试执行阈值过滤
    print("=" * 60)
    print("执行阈值过滤器测试")
    print("=" * 60)

    filter_engine = ExecutionThresholdFilter(threshold=0.05)

    # 应用过滤
    filtered_df = filter_engine.filter_execution_signals(test_data)

    print("\n过滤结果:")
    print(filtered_df[['predicted_result', 'confidence_gap', 'has_confidence_gap', 'filtered_prediction']])

    # 计算绩效对比
    comparison = filter_engine.compare_execution_modes(test_data)

    print("\n全量执行绩效:")
    print(f"  下注场次: {comparison['full_execution']['total_bets']}")
    print(f"  总收益: {comparison['full_execution']['total_yield']:.2f}")
    print(f"  Yield: {comparison['full_execution']['yield_percentage']:.2f}%")

    print("\n过滤执行绩效:")
    print(f"  下注场次: {comparison['filtered_execution']['total_bets']}")
    print(f"  总收益: {comparison['filtered_execution']['total_yield']:.2f}")
    print(f"  Yield: {comparison['filtered_execution']['yield_percentage']:.2f}%")

    print("\n改进指标:")
    print(f"  Yield 提升: {comparison['improvement']['yield_improvement']:.2f}个百分点")
    print(f"  下注减少: {comparison['improvement']['bet_reduction']}场 ({comparison['improvement']['bet_reduction_pct']:.1f}%)")
