#!/usr/bin/env python3
"""
V30.0 高阶赔率特征提取器 (Advanced Odds Features Extractor)
============================================================

核心功能：
1. 赔率离散度 (Odds Variance) - 衡量博彩公司之间的分歧程度
2. 资金流向模拟 (Market Bias) - 通过赔率变动推导市场热度
3. 冷门预测因子 (Upset Prediction Factor) - 结合历史统计的冷门指标

设计原则：
- 与 V25.1 提取器兼容，可作为后处理步骤
- 使用 match_odds 表的时序数据
- 计算标准化特征，确保跨比赛可比性

Author: Senior Football Betting Analyst & Feature Engineering Expert
Version: V30.0
Date: 2025-12-30
"""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

import numpy as np
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# 特征定义与数学公式
# ============================================================================

"""
1. 赔率离散度 (Odds Variance)
------------------------------
定义: 衡量不同博彩公司对同一场比赛赔率的分歧程度

数学公式:
    OddsVariance = CV(1/Odds_home, 1/Odds_draw, 1/Odds_away)

其中:
    CV = Coefficient of Variation = StdDev / Mean
    1/Odds 将赔率转换为隐含概率

解释:
- 高离散度 → 博彩公司意见分歧大 → 可能存在价值投注机会
- 低离散度 → 博彩公司意见一致 → 市场共识明确


2. 资金流向模拟 (Market Bias)
-------------------------------
定义: 通过初盘到终盘的赔率变动趋势推导市场热度

数学公式:
    MarketBias_home = (ImpliedProb_opening_home - ImpliedProb_closing_home) / ImpliedProb_opening_home
    MarketBias_away = (ImpliedProb_opening_away - ImpliedProb_closing_away) / ImpliedProb_opening_away

其中:
    ImpliedProb = 1 / DecimalOdds

解释:
- MarketBias_home < 0 → 主队赔率下降 (隐含概率上升) → 市场看好主队
- MarketBias_home > 0 → 主队赔率上升 (隐含概率下降) → 市场看衰主队


3. 冷门预测因子 (Upset Prediction Factor)
-----------------------------------------
定义: 结合历史数据预测强队爆冷的可能性

数学公式:
    UpsetFactor = w1 * AwayFatigue + w2 * HomeMomentum + w3 * OddsMovement + w4 * H2HUpsetRate

其中:
    AwayFatigue: 客队疲劳指数 (连续客场作战)
    HomeMomentum: 主队近期状态 (近5场得分)
    OddsMovement: 赔率对客队不利变动幅度
    H2HUpsetRate: 历史交手中低排名球队胜率

解释:
- UpsetFactor > 0.6 → 高冷门概率
- 0.4 < UpsetFactor < 0.6 → 中等冷门概率
- UpsetFactor < 0.4 → 低冷门概率
"""


# ============================================================================
# 数据类定义
# ============================================================================


@dataclass
class OddsFeatures:
    """赔率特征集合"""

    # 基础信息
    match_id: str
    feature_timestamp: datetime

    # 1. 赔率离散度特征 (3维)
    odds_variance_home: float | None = None
    odds_variance_draw: float | None = None
    odds_variance_away: float | None = None
    overall_odds_variance: float | None = None

    # 2. 资金流向特征 (6维)
    market_bias_home: float | None = None
    market_bias_draw: float | None = None
    market_bias_away: float | None = None
    market_bias_asymmetry: float | None = None
    odds_volatility_home: float | None = None
    odds_volatility_away: float | None = None

    # 3. 冷门预测因子特征 (4维)
    upset_prediction_factor: float | None = None
    away_fatigue_index: float | None = None
    home_momentum_score: float | None = None
    historical_upset_rate: float | None = None

    # 4. 市场共识强度 (2维)
    market_consensus_strength: float | None = None
    bookmaker_disagreement_index: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于特征合并）"""
        return {
            "odds_variance_home": self.odds_variance_home,
            "odds_variance_draw": self.odds_variance_draw,
            "odds_variance_away": self.odds_variance_away,
            "overall_odds_variance": self.overall_odds_variance,
            "market_bias_home": self.market_bias_home,
            "market_bias_draw": self.market_bias_draw,
            "market_bias_away": self.market_bias_away,
            "market_bias_asymmetry": self.market_bias_asymmetry,
            "odds_volatility_home": self.odds_volatility_home,
            "odds_volatility_away": self.odds_volatility_away,
            "upset_prediction_factor": self.upset_prediction_factor,
            "away_fatigue_index": self.away_fatigue_index,
            "home_momentum_score": self.home_momentum_score,
            "historical_upset_rate": self.historical_upset_rate,
            "market_consensus_strength": self.market_consensus_strength,
            "bookmaker_disagreement_index": self.bookmaker_disagreement_index,
        }


# ============================================================================
# 核心特征提取器
# ============================================================================


class AdvancedOddsFeaturesExtractor:
    """
    高阶赔率特征提取器

    职责:
    - 从 match_odds 表计算赔率离散度
    - 分析初盘到终盘的资金流向
    - 综合历史数据计算冷门预测因子
    """

    def __init__(self):
        """初始化提取器"""
        self.settings = get_settings()
        self._conn = None

    def get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            import psycopg2

            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    # ========================================================================
    # 1. 赔率离散度计算
    # ========================================================================

    def _calculate_odds_variance(self, match_id: str) -> dict[str, float]:
        """
        计算赔率离散度

        算法:
        1. 获取所有博彩公司的最新赔率
        2. 将赔率转换为隐含概率 (1/odds)
        3. 计算变异系数 (CV = StdDev / Mean)
        """
        conn = self.get_connection()

        with conn.cursor() as cursor:
            # 获取该比赛所有供应商的最新 1X2 赔率
            cursor.execute("""
                WITH latest_odds AS (
                    SELECT DISTINCT ON (provider)
                        provider,
                        home_win_odds,
                        draw_odds,
                        away_win_odds
                    FROM match_odds
                    WHERE match_id = %s
                      AND market_type = '1X2'
                      AND home_win_odds IS NOT NULL
                      AND draw_odds IS NOT NULL
                      AND away_win_odds IS NOT NULL
                    ORDER BY provider, timestamp DESC
                )
                SELECT
                    provider,
                    home_win_odds,
                    draw_odds,
                    away_win_odds
                FROM latest_odds
            """, (match_id,))

            odds_data = cursor.fetchall()

            if len(odds_data) < 3:
                # 需要至少 3 个博彩公司才能计算离散度
                logger.debug(f"Match {match_id}: 供应商不足 ({len(odds_data)}), 跳过离散度计算")
                return {
                    "odds_variance_home": None,
                    "odds_variance_draw": None,
                    "odds_variance_away": None,
                    "overall_odds_variance": None,
                }

            # 转换为隐含概率并计算离散度
            home_probs = [1.0 / row["home_win_odds"] for row in odds_data]
            draw_probs = [1.0 / row["draw_odds"] for row in odds_data]
            away_probs = [1.0 / row["away_win_odds"] for row in odds_data]

            def cv(values: list[float]) -> float:
                """计算变异系数"""
                if not values or len(values) < 2:
                    return 0.0
                mean_val = np.mean(values)
                if mean_val == 0:
                    return 0.0
                return np.std(values) / mean_val

            return {
                "odds_variance_home": cv(home_probs),
                "odds_variance_draw": cv(draw_probs),
                "odds_variance_away": cv(away_probs),
                "overall_odds_variance": np.mean([cv(home_probs), cv(draw_probs), cv(away_probs)]),
            }

    # ========================================================================
    # 2. 资金流向计算
    # ========================================================================

    def _calculate_market_bias(self, match_id: str) -> dict[str, float]:
        """
        计算资金流向

        算法:
        1. 获取初盘 (opening) 和终盘 (closing) 赔率
        2. 计算隐含概率变化
        3. 标准化为相对变化率
        """
        conn = self.get_connection()

        with conn.cursor() as cursor:
            # 获取初盘和终盘赔率（使用平均赔率）
            cursor.execute("""
                WITH opening_odds AS (
                    SELECT
                        AVG(home_win_odds) as avg_home,
                        AVG(draw_odds) as avg_draw,
                        AVG(away_win_odds) as avg_away
                    FROM match_odds
                    WHERE match_id = %s
                      AND is_opening = TRUE
                      AND home_win_odds IS NOT NULL
                ),
                closing_odds AS (
                    SELECT
                        AVG(home_win_odds) as avg_home,
                        AVG(draw_odds) as avg_draw,
                        AVG(away_win_odds) as avg_away
                    FROM match_odds
                    WHERE match_id = %s
                      AND is_closing = TRUE
                      AND home_win_odds IS NOT NULL
                )
                SELECT
                    o.avg_home as opening_home,
                    o.avg_draw as opening_draw,
                    o.avg_away as opening_away,
                    c.avg_home as closing_home,
                    c.avg_draw as closing_draw,
                    c.avg_away as closing_away
                FROM opening_odds o, closing_odds c
            """, (match_id, match_id))

            result = cursor.fetchone()

            if not result or result["opening_home"] is None:
                logger.debug(f"Match {match_id}: 缺少初盘/终盘赔率")
                return {
                    "market_bias_home": None,
                    "market_bias_draw": None,
                    "market_bias_away": None,
                    "market_bias_asymmetry": None,
                    "odds_volatility_home": None,
                    "odds_volatility_away": None,
                }

            # 计算隐含概率
            open_home_prob = 1.0 / result["opening_home"]
            open_draw_prob = 1.0 / result["opening_draw"]
            open_away_prob = 1.0 / result["opening_away"]

            close_home_prob = 1.0 / result["closing_home"]
            close_draw_prob = 1.0 / result["closing_draw"]
            close_away_prob = 1.0 / result["closing_away"]

            # 计算市场流向 (负值表示市场看好该结果)
            market_bias_home = (open_home_prob - close_home_prob) / open_home_prob
            market_bias_draw = (open_draw_prob - close_draw_prob) / open_draw_prob
            market_bias_away = (open_away_prob - close_away_prob) / open_away_prob

            # 市场偏向不对称性 (主队 vs 客队资金流向差异)
            market_bias_asymmetry = market_bias_home - market_bias_away

            # 计算赔率波动率 (使用中间时序数据)
            cursor.execute("""
                SELECT
                    STDDEV(home_win_odds) / AVG(home_win_odds) as home_volatility,
                    STDDEV(away_win_odds) / AVG(away_win_odds) as away_volatility
                FROM match_odds
                WHERE match_id = %s
                  AND home_win_odds IS NOT NULL
                  AND away_win_odds IS NOT NULL
                  AND is_opening = FALSE
                  AND is_closing = FALSE
            """, (match_id,))

            volatility = cursor.fetchone()

            return {
                "market_bias_home": market_bias_home,
                "market_bias_draw": market_bias_draw,
                "market_bias_away": market_bias_away,
                "market_bias_asymmetry": market_bias_asymmetry,
                "odds_volatility_home": volatility["home_volatility"] if volatility else None,
                "odds_volatility_away": volatility["away_volatility"] if volatility else None,
            }

    # ========================================================================
    # 3. 冷门预测因子计算
    # ========================================================================

    def _calculate_upset_factor(self, match_id: str) -> dict[str, float]:
        """
        计算冷门预测因子

        综合指标:
        1. 客队疲劳指数 (连续客场作战)
        2. 主队近期状态 (近5场积分)
        3. 赔率对客队不利变动
        4. 历史交手冷门率
        """
        conn = self.get_connection()

        # 首先获取比赛基本信息
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.league_id
                FROM matches m
                WHERE m.match_id = %s
            """, (match_id,))

            match_info = cursor.fetchone()

            if not match_info:
                return {
                    "upset_prediction_factor": None,
                    "away_fatigue_index": None,
                    "home_momentum_score": None,
                    "historical_upset_rate": None,
                }

        # 1. 计算客队疲劳指数 (最近30天客场作战次数)
        with conn.cursor() as cursor:
            cursor.execute("""
                WITH away_matches AS (
                    SELECT
                        m.match_date,
                        CASE WHEN m.away_team = %s THEN 1 ELSE 0 END as is_away
                    FROM matches m
                    WHERE m.away_team = %s
                      AND m.match_date < %s
                      AND m.match_date >= %s - INTERVAL '30 days'
                      AND m.status = 'finished'
                )
                SELECT
                    SUM(is_away)::float / COUNT(*) as away_fatigue_index
                FROM away_matches
            """, (match_info["away_team"], match_info["away_team"],
                  match_info["match_date"], match_info["match_date"]))

            fatigue_result = cursor.fetchone()
            away_fatigue = fatigue_result["away_fatigue_index"] if fatigue_result else 0.5

        # 2. 计算主队近期状态 (近5场场均积分)
        with conn.cursor() as cursor:
            cursor.execute("""
                WITH recent_matches AS (
                    SELECT
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score,
                        CASE
                            WHEN m.home_team = %s THEN
                                CASE WHEN m.home_score > m.away_score THEN 3
                                     WHEN m.home_score = m.away_score THEN 1
                                     ELSE 0 END
                            ELSE
                                CASE WHEN m.away_score > m.home_score THEN 3
                                     WHEN m.away_score = m.home_score THEN 1
                                     ELSE 0 END
                        END as points
                    FROM matches m
                    WHERE (m.home_team = %s OR m.away_team = %s)
                      AND m.match_date < %s
                      AND m.status = 'finished'
                    ORDER BY m.match_date DESC
                    LIMIT 5
                )
                SELECT
                    AVG(points)::float / 3.0 as home_momentum_score  -- 标准化到 [0,1]
                FROM recent_matches
            """, (match_info["home_team"], match_info["home_team"], match_info["home_team"],
                  match_info["match_date"]))

            momentum_result = cursor.fetchone()
            home_momentum = momentum_result["home_momentum_score"] if momentum_result else 0.5

        # 3. 赔率变动对客队不利性
        with conn.cursor() as cursor:
            cursor.execute("""
                WITH odds_change AS (
                    SELECT
                        AVG(home_win_odds) FILTER (WHERE is_opening = TRUE) as open_home,
                        AVG(away_win_odds) FILTER (WHERE is_opening = TRUE) as open_away,
                        AVG(home_win_odds) FILTER (WHERE is_closing = TRUE) as close_home,
                        AVG(away_win_odds) FILTER (WHERE is_closing = TRUE) as close_away
                    FROM match_odds
                    WHERE match_id = %s
                )
                SELECT
                    -- 客队赔率上升 (不利变动) 会增加此值
                    ((close_away - open_away) / open_away) -
                    ((close_home - open_home) / open_home) as away_unfavorable_movement
                FROM odds_change
            """, (match_id,))

            movement_result = cursor.fetchone()
            away_unfavorable = movement_result["away_unfavorable_movement"] if movement_result else 0.0

        # 4. 历史交手冷门率
        with conn.cursor() as cursor:
            cursor.execute("""
                WITH h2h_matches AS (
                    SELECT
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score,
                        -- 获取当时排名差
                        (SELECT COUNT(*) + 1
                         FROM team_standings_snapshot
                         WHERE team_name = m.away_team
                           AND snapshot_date < m.match_date
                         ORDER BY snapshot_date DESC LIMIT 1) as away_rank,
                        (SELECT COUNT(*) + 1
                         FROM team_standings_snapshot
                         WHERE team_name = m.home_team
                           AND snapshot_date < m.match_date
                         ORDER BY snapshot_date DESC LIMIT 1) as home_rank
                    FROM matches m
                    WHERE (m.home_team = %s AND m.away_team = %s)
                       OR (m.home_team = %s AND m.away_team = %s)
                      AND m.match_date < %s
                      AND m.status = 'finished'
                    ORDER BY m.match_date DESC
                    LIMIT 10
                ),
                upsets AS (
                    SELECT *,
                        -- 定义冷门: 排名低的球队获胜或战平
                        CASE
                            WHEN away_rank IS NULL OR home_rank IS NULL THEN 0
                            WHEN away_rank > home_rank + 5 AND away_score > home_score THEN 1
                            WHEN home_rank > away_rank + 5 AND home_score > away_score THEN 1
                            WHEN away_rank > home_rank + 5 AND away_score = home_score THEN 0.5
                            WHEN home_rank > away_rank + 5 AND home_score = away_score THEN 0.5
                            ELSE 0
                        END as is_upset
                    FROM h2h_matches
                )
                SELECT
                    COALESCE(AVG(is_upset), 0.0) as historical_upset_rate
                FROM upsets
            """, (match_info["home_team"], match_info["away_team"],
                  match_info["away_team"], match_info["home_team"],
                  match_info["match_date"]))

            upset_rate_result = cursor.fetchone()
            historical_upset = upset_rate_result["historical_upset_rate"] if upset_rate_result else 0.0

        # 综合冷门因子 (加权组合)
        # 权重设计:
        # - 疲劳度: 30%
        # - 主队状态: 25%
        # - 赔率变动: 25%
        # - 历史冷门: 20%

        upset_factor = (
            away_fatigue * 0.30 +
            (1.0 - home_momentum) * 0.25 +  # 主队状态差 → 冷门概率高
            max(away_unfavorable, 0.0) * 0.25 +  # 客队赔率不利 → 主队优势大 → 冷门概率低
            historical_upset * 0.20
        )

        return {
            "upset_prediction_factor": upset_factor,
            "away_fatigue_index": away_fatigue,
            "home_momentum_score": home_momentum,
            "historical_upset_rate": historical_upset,
        }

    # ========================================================================
    # 4. 市场共识强度
    # ========================================================================

    def _calculate_market_consensus(self, match_id: str) -> dict[str, float]:
        """
        计算市场共识强度

        指标:
        1. 市场共识强度: 供应商数量与离散度的综合指标
        2. 博彩公司分歧指数: 加权分歧程度
        """
        conn = self.get_connection()

        with conn.cursor() as cursor:
            # 获取供应商数量和赔率范围
            cursor.execute("""
                WITH latest_odds AS (
                    SELECT DISTINCT ON (provider)
                        provider,
                        home_win_odds,
                        draw_odds,
                        away_win_odds
                    FROM match_odds
                    WHERE match_id = %s
                      AND market_type = '1X2'
                      AND home_win_odds IS NOT NULL
                    ORDER BY provider, timestamp DESC
                ),
                odds_stats AS (
                    SELECT
                        COUNT(*) as provider_count,
                        MIN(home_win_odds) as min_home,
                        MAX(home_win_odds) as max_home,
                        STDDEV(home_win_odds) as std_home
                    FROM latest_odds
                )
                SELECT
                    provider_count,
                    min_home,
                    max_home,
                    std_home,
                    CASE
                        WHEN max_home > 0 THEN (max_home - min_home) / max_home
                        ELSE 0
                    END as odds_range_ratio
                FROM odds_stats
            """, (match_id,))

            result = cursor.fetchone()

            if not result or result["provider_count"] < 2:
                return {
                    "market_consensus_strength": None,
                    "bookmaker_disagreement_index": None,
                }

            # 市场共识强度: 供应商数量越多且离散度越小，共识越强
            provider_count = result["provider_count"]
            odds_range_ratio = result["odds_range_ratio"]
            std_home = result["std_home"] or 0.0

            # 共识强度 = 标准化供应商数量 / (1 + 离散度)
            consensus_strength = (min(provider_count / 10.0, 1.0)) / (1.0 + odds_range_ratio)

            # 分歧指数: 综合标准差和范围
            disagreement_index = std_home * odds_range_ratio

            return {
                "market_consensus_strength": consensus_strength,
                "bookmaker_disagreement_index": disagreement_index,
            }

    # ========================================================================
    # 主提取方法
    # ========================================================================

    def extract_features(self, match_id: str) -> OddsFeatures:
        """
        提取单场比赛的所有赔率特征

        Args:
            match_id: 比赛 ID

        Returns:
            OddsFeatures: 赔率特征对象
        """
        logger.debug(f"提取赔率特征: {match_id}")

        # 并行计算各类特征
        variance = self._calculate_odds_variance(match_id)
        bias = self._calculate_market_bias(match_id)
        upset = self._calculate_upset_factor(match_id)
        consensus = self._calculate_market_consensus(match_id)

        features = OddsFeatures(
            match_id=match_id,
            feature_timestamp=datetime.now(),
            # 赔率离散度
            odds_variance_home=variance.get("odds_variance_home"),
            odds_variance_draw=variance.get("odds_variance_draw"),
            odds_variance_away=variance.get("odds_variance_away"),
            overall_odds_variance=variance.get("overall_odds_variance"),
            # 资金流向
            market_bias_home=bias.get("market_bias_home"),
            market_bias_draw=bias.get("market_bias_draw"),
            market_bias_away=bias.get("market_bias_away"),
            market_bias_asymmetry=bias.get("market_bias_asymmetry"),
            odds_volatility_home=bias.get("odds_volatility_home"),
            odds_volatility_away=bias.get("odds_volatility_away"),
            # 冷门预测
            upset_prediction_factor=upset.get("upset_prediction_factor"),
            away_fatigue_index=upset.get("away_fatigue_index"),
            home_momentum_score=upset.get("home_momentum_score"),
            historical_upset_rate=upset.get("historical_upset_rate"),
            # 市场共识
            market_consensus_strength=consensus.get("market_consensus_strength"),
            bookmaker_disagreement_index=consensus.get("bookmaker_disagreement_index"),
        )

        logger.debug(f"提取完成: {match_id}, 共 {len(features.to_dict())} 个特征")
        return features

    def extract_batch(self, match_ids: list[str]) -> dict[str, OddsFeatures]:
        """
        批量提取赔率特征

        Args:
            match_ids: 比赛 ID 列表

        Returns:
            dict: {match_id: OddsFeatures}
        """
        logger.info(f"批量提取赔率特征: {len(match_ids)} 场比赛")

        results = {}
        for i, match_id in enumerate(match_ids):
            try:
                features = self.extract_features(match_id)
                results[match_id] = features

                if (i + 1) % 50 == 0:
                    logger.info(f"  进度: {i + 1}/{len(match_ids)}")

            except Exception as e:
                logger.error(f"提取失败 {match_id}: {e}")
                continue

        logger.info(f"批量提取完成: {len(results)}/{len(match_ids)} 成功")
        return results


# ============================================================================
# 便捷函数
# ============================================================================


def extract_odds_features_for_match(match_id: str) -> dict[str, Any]:
    """
    提取单场比赛赔率特征的便捷函数

    Args:
        match_id: 比赛 ID

    Returns:
        特征字典
    """
    extractor = AdvancedOddsFeaturesExtractor()
    features = extractor.extract_features(match_id)
    return features.to_dict()


def merge_odds_features_to_raw_data(raw_data: dict, odds_features: dict[str, Any]) -> dict:
    """
    将赔率特征合并到原始数据字典中

    Args:
        raw_data: V25 提取的原始数据
        odds_features: 赔率特征字典

    Returns:
        合并后的数据字典
    """
    # 在原始数据中添加高级赔率特征
    merged = {**raw_data, **odds_features}
    return merged
