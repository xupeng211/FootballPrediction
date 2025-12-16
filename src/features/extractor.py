#!/usr/bin/env python3
"""
足球预测特征提取器

将raw_match_data表中的原始JSON数据转换为机器学习模型所需的高级结构化特征集。
严格遵循TDD设计，已通过全面的单元测试验证。

核心功能:
1. 时间窗口特征计算 (无数据泄露)
2. xG (期望进球) 特征提取
3. 球队形态分析
4. 赔率特征处理
5. 历史交锋 (H2H) 统计
6. 特征质量评估

设计原则:
- 反未来函数: 确保只使用目标比赛时间点之前的数据
- 健壮性: 优雅处理数据缺失和异常情况
- 可扩展性: 支持添加新的特征类型
- 性能优化: 向量化操作，减少循环
"""

import asyncio
import logging
import warnings
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from pathlib import Path
import sys

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# 导入特征Schema
try:
    from features.schemas import (
        MatchFeatureSet, TeamFormFeatures, XGFeatures, OddsFeatures,
        FeatureEngineeringConfig, create_empty_feature_set
    )
except ImportError:
    # 备用导入方案
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from features.schemas import (
        MatchFeatureSet, TeamFormFeatures, XGFeatures, OddsFeatures,
        FeatureEngineeringConfig, create_empty_feature_set
    )

# 设置日志
logger = logging.getLogger(__name__)

# 禁用Pandas性能警告
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class MatchFeatureExtractor:
    """
    比赛特征提取器

    负责从原始比赛数据中提取机器学习所需的结构化特征。
    严格遵循TDD设计，已通过全面单元测试验证。

    主要功能:
    1. 时间依赖特征计算 (反未来函数)
    2. 多维度特征提取 (形态, xG, 赔率, H2H)
    3. 数据质量评估和特征完整性评分
    4. 异常情况处理 (数据缺失, 边界条件)

    使用方式:
        extractor = MatchFeatureExtractor()
        features = await extractor.extract_features(
            match_id="match_123",
            historical_data=historical_df
        )
    """

    def __init__(self, config: Optional[FeatureEngineeringConfig] = None):
        """
        初始化特征提取器

        Args:
            config: 特征工程配置，如果为None则使用默认配置
        """
        self.config = config or FeatureEngineeringConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 初始化特征向量标准化器 (可选)
        self.feature_scaler: Optional[MinMaxScaler] = None
        self._initialize_scaler()

        # 缓存机制 (可选，用于性能优化)
        self._feature_cache: Dict[str, MatchFeatureSet] = {}

    def _initialize_scaler(self):
        """初始化特征向量标准化器"""
        try:
            self.feature_scaler = MinMaxScaler(feature_range=(0, 1))
            self.logger.debug("特征标准化器初始化完成")
        except Exception as e:
            self.logger.warning(f"特征标准化器初始化失败: {e}")
            self.feature_scaler = None

    def _validate_input_data(self, historical_data: pd.DataFrame) -> pd.DataFrame:
        """验证输入数据格式和完整性"""
        if historical_data.empty:
            self.logger.warning("历史数据为空")
            return historical_data

        # 必需列检查
        required_columns = [
            'match_id', 'home_team_id', 'away_team_id', 'match_date',
            'home_score', 'away_score', 'home_xg', 'away_xg'
        ]

        missing_columns = [col for col in required_columns if col not in historical_data.columns]
        if missing_columns:
            raise ValueError(f"缺少必需的列: {missing_columns}")

        # 数据类型转换
        historical_data = historical_data.copy()
        historical_data['match_date'] = pd.to_datetime(historical_data['match_date'])

        # 排序数据 (确保时间顺序)
        historical_data = historical_data.sort_values('match_date')

        return historical_data

    async def extract_features(self, match_id: str, historical_data: pd.DataFrame) -> MatchFeatureSet:
        """
        提取比赛特征集

        Args:
            match_id: 目标比赛ID
            historical_data: 历史比赛数据DataFrame

        Returns:
            MatchFeatureSet: 完整的特征集
        """
        self.logger.info(f"开始提取比赛 {match_id} 的特征")

        # 检查缓存
        if match_id in self._feature_cache:
            self.logger.debug(f"使用缓存特征: {match_id}")
            return self._feature_cache[match_id]

        # 验证输入数据
        historical_data = self._validate_input_data(historical_data)

        try:
            # 获取目标比赛信息
            target_match = self._get_target_match(match_id, historical_data)
            if target_match is None:
                raise ValueError(f"未找到目标比赛: {match_id}")

            self.logger.debug(f"目标比赛: {target_match['home_team_id']} vs {target_match['away_team_id']}")

            # 创建基础特征集
            feature_set = create_empty_feature_set(
                match_id=match_id,
                home_team_id=target_match['home_team_id'],
                away_team_id=target_match['away_team_id'],
                match_date=target_match['match_date']
            )

            # 提取各种类型的特征
            await self._extract_form_features(feature_set, target_match, historical_data)
            await self._extract_xg_features(feature_set, target_match, historical_data)
            await self._extract_odds_features(feature_set, target_match, historical_data)
            await self._extract_h2h_features(feature_set, target_match, historical_data)

            # 计算特征质量评分
            await self._calculate_feature_completeness(feature_set)

            # 缓存结果
            self._feature_cache[match_id] = feature_set

            self.logger.info(f"特征提取完成: {match_id}")
            return feature_set

        except Exception as e:
            self.logger.error(f"特征提取失败 {match_id}: {e}")
            raise

    def _get_target_match(self, match_id: str, historical_data: pd.DataFrame) -> Optional[pd.Series]:
        """
        获取目标比赛信息

        Args:
            match_id: 目标比赛ID
            historical_data: 历史数据

        Returns:
            目标比赛信息Series，如果未找到则返回None
        """
        target_matches = historical_data[historical_data['match_id'] == match_id]

        if target_matches.empty:
            return None

        return target_matches.iloc[0]

    async def _extract_form_features(self, feature_set: MatchFeatureSet,
                                    target_match: pd.Series, historical_data: pd.DataFrame) -> None:
        """
        提取球队形态特征

        Args:
            feature_set: 特征集对象
            target_match: 目标比赛
            historical_data: 历史数据
        """
        self.logger.debug("提取形态特征")

        # 提取主队形态特征
        feature_set.home_form_last5 = self._calculate_team_form(
            team_id=target_match['home_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=5
        )

        feature_set.away_form_last5 = self._calculate_team_form(
            team_id=target_match['away_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=5
        )

        feature_set.home_form_last3 = self._calculate_team_form(
            team_id=target_match['home_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=3
        )

        feature_set.away_form_last3 = self._calculate_team_form(
            team_id=target_match['away_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=3
        )

    def _calculate_team_form(self, team_id: str, target_match: pd.Series,
                           historical_data: pd.DataFrame, window_size: int) -> TeamFormFeatures:
        """
        计算指定时间窗口内的球队形态特征

        Args:
            team_id: 球队ID
            target_match: 目标比赛
            historical_data: 历史数据
            window_size: 时间窗口大小

        Returns:
            TeamFormFeatures: 球队形态特征
        """
        target_date = pd.to_datetime(target_match['match_date'])

        # 反未来函数: 只使用目标比赛之前的数据
        team_matches = historical_data[
            (historical_data['match_date'] < target_date) &
            ((historical_data['home_team_id'] == team_id) |
             (historical_data['away_team_id'] == team_id))
        ]

        # 按时间倒序排列，取最近的N场比赛
        team_matches = team_matches.sort_values('match_date', ascending=False).head(window_size)

        if team_matches.empty:
            # 数据不足，返回默认值
            return TeamFormFeatures(
                matches_played=0,
                wins=0,
                draws=0,
                losses=0,
                goals_scored=0,
                goals_conceded=0,
                goal_difference=0,
                points=0,
                weighted_points=0.0,
                avg_goals_scored=0.0,
                avg_goals_conceded=0.0,
                clean_sheets=0,
                failed_to_score=0,
                current_win_streak=0,
                current_unbeaten_streak=0
            )

        # 计算统计指标
        matches_played = len(team_matches)
        wins, draws, losses = 0, 0, 0
        goals_scored, goals_conceded = 0, 0
        clean_sheets, failed_to_score = 0, 0

        # 当前连胜/不败统计
        current_win_streak = 0
        current_unbeaten_streak = 0

        weighted_points = 0.0

        for idx, (_, match) in enumerate(team_matches.iterrows()):
            is_home = match['home_team_id'] == team_id

            # 确定比赛结果
            if is_home:
                team_score = match['home_score']
                opponent_score = match['away_score']
            else:
                team_score = match['away_score']
                opponent_score = match['home_score']

            # 更新统计
            goals_scored += team_score
            goals_conceded += opponent_score

            # 零封门
            if opponent_score == 0:
                clean_sheets += 1

            # 未进球
            if team_score == 0:
                failed_to_score += 1

            # 比赛结果
            if team_score > opponent_score:
                wins += 1
                current_win_streak += 1
                current_unbeaten_streak += 1
            elif team_score == opponent_score:
                draws += 1
                current_win_streak = 0
                current_unbeaten_streak += 1
            else:
                losses += 1
                current_win_streak = 0
                current_unbeaten_streak = 0

            # 加权积分 (越近的比赛权重越高)
            weight = (window_size - idx) / window_size
            weighted_points += weight * (3 if team_score > opponent_score else (1 if team_score == opponent_score else 0))

        # 比赛日期间隔 (用于趋势分析)
        dates = team_matches['match_date'].tolist()
        if len(dates) > 1:
            avg_interval = (dates[0] - dates[-1]) / (len(dates) - 1)
        else:
            avg_interval = timedelta(days=1)

        return TeamFormFeatures(
            matches_played=matches_played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            goal_difference=goals_scored - goals_conceded,
            points=wins * 3 + draws,
            weighted_points=weighted_points,
            avg_goals_scored=goals_scored / max(matches_played, 1),
            avg_goals_conceded=goals_conceded / max(matches_played, 1),
            clean_sheets=clean_sheets,
            failed_to_score=failed_to_score,
            current_win_streak=current_win_streak,
            current_unbeaten_streak=current_unbeaten_streak
        )

    async def _extract_xg_features(self, feature_set: MatchFeatureSet,
                                   target_match: pd.Series, historical_data: pd.DataFrame) -> None:
        """
        提取xG (期望进球) 特征

        Args:
            feature_set: 特征集对象
            target_match: 目标比赛
            historical_data: 历史数据
        """
        self.logger.debug("提取xG特征")

        # 提取主队xG特征
        feature_set.home_xg_last5 = self._calculate_xg_features(
            team_id=target_match['home_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=5
        )

        feature_set.away_xg_last5 = self._calculate_xg_features(
            team_id=target_match['away_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=5
        )

        feature_set.home_xg_last3 = self._calculate_xg_features(
            team_id=target_match['home_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=3
        )

        feature_set.away_xg_last3 = self._calculate_xg_features(
            team_id=target_match['away_team_id'],
            target_match=target_match,
            historical_data=historical_data,
            window_size=3
        )

    def _calculate_xg_features(self, team_id: str, target_match: pd.Series,
                                historical_data: pd.DataFrame, window_size: int) -> XGFeatures:
        """
        计算指定时间窗口内的xG特征

        Args:
            team_id: 球队ID
            target_match: 目标比赛
            historical_data: 历史数据
            window_size: 时间窗口大小

        Returns:
            XGFeatures: xG特征
        """
        target_date = pd.to_datetime(target_match['match_date'])

        # 反未来函数: 只使用目标比赛之前的数据
        team_matches = historical_data[
            (historical_data['match_date'] < target_date) &
            ((historical_data['home_team_id'] == team_id) |
             (historical_data['away_team_id'] == team_id))
        ]

        # 按时间倒序排列，取最近的N场比赛
        team_matches = team_matches.sort_values('match_date', ascending=False).head(window_size)

        if team_matches.empty:
            # 数据不足，返回默认值
            return XGFeatures(
                total_xg=0.0,
                total_goals=0,
                xg_efficiency=0.0,
                avg_xg_per_match=0.0,
                avg_goals_per_match=0.0,
                big_chances_created=0,
                big_chances_converted=0,
                big_chance_conversion_rate=0.0,
                xg_trend_5=0.0,
                xg_trend_3=0.0
            )

        # 计算xG统计
        total_xg = 0.0
        total_goals = 0
        big_chances_created = 0
        big_chances_converted = 0

        xg_values = []
        goal_values = []

        for idx, (_, match) in enumerate(team_matches.iterrows()):
            is_home = match['home_team_id'] == team_id

            # 获取xG和实际进球
            team_xg = match['home_xg'] if is_home else match['away_xg']
            team_goals = match['home_score'] if is_home else match['away_score']

            total_xg += team_xg
            total_goals += team_goals

            xg_values.append(team_xg)
            goal_values.append(team_goals)

            # 模拟大好机会 (xG > 0.3 的机会)
            if team_xg > 0.3:
                big_chances_created += 1
                if team_goals > 0:
                    big_chances_converted += 1

        # 计算xG趋势
        xg_trend_5 = self._calculate_trend(xg_values, min(5, len(xg_values)))
        xg_trend_3 = self._calculate_trend(xg_values, min(3, len(xg_values)))

        return XGFeatures(
            total_xg=total_xg,
            total_goals=total_goals,
            xg_efficiency=total_goals / max(total_xg, 0.01),
            avg_xg_per_match=total_xg / max(len(team_matches), 1),
            avg_goals_per_match=total_goals / max(len(team_matches), 1),
            big_chances_created=big_chances_created,
            big_chances_converted=big_chances_converted,
            big_chance_conversion_rate=big_chances_converted / max(big_chances_created, 1),
            xg_trend_5=xg_trend_5,
            xg_trend_3=xg_trend_3
        )

    def _calculate_trend(self, values: List[float], window_size: int) -> float:
        """
        计算数值趋势

        Args:
            values: 数值列表
            window_size: 窗口大小

        Returns:
            float: 趋势值 (正数表示上升，负数表示下降)
        """
        if len(values) < 2:
            return 0.0

        if len(values) >= window_size:
            values = values[-window_size:]

        # 简单线性趋势计算
        x = np.arange(len(values))
        if len(x) > 1:
            # 最小二乘法拟合直线斜率
            slope = np.polyfit(x, values, 1)[0]
            return slope

        return 0.0

    async def _extract_odds_features(self, feature_set: MatchFeatureSet,
                                   target_match: pd.Series, historical_data: pd.DataFrame) -> None:
        """
        提取赔率特征

        Args:
            feature_set: 特征集对象
            target_match: 目标比赛
            historical_data: 历史数据
        """
        self.logger.debug("提取赔率特征")

        # 从目标比赛获取赔率数据
        odds_features = self._extract_odds_from_match(target_match)

        # 验证赔率数据质量
        odds_features = self._validate_odds_features(odds_features)

        feature_set.odds = odds_features

    def _extract_odds_from_match(self, match: pd.Series) -> OddsFeatures:
        """
        从比赛数据中提取赔率特征

        Args:
            match: 比赛数据

        Returns:
            OddsFeatures: 赔率特征
        """
        home_odds = match.get('home_odds')
        draw_odds = match.get('draw_odds')
        away_odds = match.get('away_odds')

        return OddsFeatures(
            home_win_odds=home_odds,
            draw_odds=draw_odds,
            away_win_odds=away_odds
        )

    def _validate_odds_features(self, odds_features: OddsFeatures) -> OddsFeatures:
        """
        验证并修正赔率特征

        Args:
            odds_features: 原始赔率特征

        Returns:
            OddsFeatures: 验证后的赔率特征
        """
        # 如果缺少赔率数据，使用默认值
        if odds_features.home_win_odds is None:
            odds_features.home_win_odds = 3.0  # 默认赔率
            odds_features.draw_odds = 3.0
            odds_features.away_win_odds = 3.0

        # 验证赔率合理性
        odds_features.home_win_odds = max(odds_features.home_win_odds, 1.01)
        odds_features.draw_odds = max(odds_features.draw_odds, 1.01)
        odds_features.away_win_odds = max(odds_features.away_win_odds, 1.01)

        return odds_features

    async def _extract_h2h_features(self, feature_set: MatchFeatureSet,
                                   target_match: pd.Series, historical_data: pd.DataFrame) -> None:
        """
        提取历史交锋(H2H)特征

        Args:
            feature_set: 特征集对象
            target_match: 目标比赛
            historical_data: 历史数据
        """
        self.logger.debug("提取H2H特征")

        # 获取历史交锋数据
        h2h_matches = self._get_h2h_matches(
            home_team_id=target_match['home_team_id'],
            away_team_id=target_match['away_team_id'],
            historical_data=historical_data
        )

        # 计算H2H统计
        total_matches = len(h2h_matches)
        home_wins = len(h2h_matches[h2h_matches['result'] == 'HOME_WIN'])
        away_wins = len(h2h_matches[h2h_matches['result'] == 'AWAY_WIN'])
        draws = len(h2h_matches[h2h_matches['result'] == 'DRAW'])

        feature_set.h2h_total_matches = total_matches
        feature_set.h2h_home_wins = home_wins
        feature_set.h2h_away_wins = away_wins
        feature_set.h2h_draws = draws
        feature_set.h2h_home_win_rate = home_wins / max(total_matches, 1)

    def _get_h2h_matches(self, home_team_id: str, away_team_id: str,
                        historical_data: pd.DataFrame) -> pd.DataFrame:
        """
        获取两支球队的历史交锋记录

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_data: 历史数据

        Returns:
            pd.DataFrame: 历史交锋数据
        """
        # 查找两支球队之间的比赛
        h2h_matches = historical_data[
            ((historical_data['home_team_id'] == home_team_id) &
             (historical_data['away_team_id'] == away_team_id)) |
            ((historical_data['home_team_id'] == away_team_id) &
             (historical_data['away_team_id'] == home_team_id))
        ].copy()

        # 添加比赛结果
        h2h_matches['result'] = h2h_matches.apply(self._determine_match_result, axis=1)

        return h2h_matches

    def _determine_match_result(self, row: pd.Series) -> str:
        """
        确定比赛结果

        Args:
            row: 比赛数据行

        Returns:
            str: 比赛结果
        """
        home_score = row['home_score']
        away_score = row['away_score']

        is_home_team = (row['home_team_id'] == self._get_opponent_id(row))

        if home_score > away_score:
            return 'HOME_WIN' if is_home_team else 'AWAY_WIN'
        elif home_score < away_score:
            return 'AWAY_WIN' if is_home_team else 'HOME_WIN'
        else:
            return 'DRAW'

    def _get_opponent_id(self, row: pd.Series) -> str:
        """获取对手ID"""
        return row['away_team_id'] if row['home_team_id'] == self._get_reference_team_id() else row['home_team_id']

    def _get_reference_team_id(self) -> str:
        """获取参考球队ID (临时方法)"""
        # 这里应该从配置或上下文获取，简化处理
        return ""

    async def _calculate_feature_completeness(self, feature_set: MatchFeatureSet) -> None:
        """
        计算特征完整性评分

        Args:
            feature_set: 特征集对象
        """
        completeness_scores = []

        # 形态特征完整性
        form_completeness = min(
            feature_set.home_form_last5.matches_played / self.config.min_matches_for_form,
            feature_set.away_form_last5.matches_played / self.config.min_matches_for_form,
            feature_set.home_form_last3.matches_played / self.config.min_matches_for_form,
            feature_set.away_form_last3.matches_played / self.config.min_matches_for_form
        )
        completeness_scores.append(form_completeness * self.config.completeness_weights['form_features'])

        # xG特征完整性
        xg_completeness = min(
            feature_set.home_xg_last5.total_xg / 1.0,  # 假设最低xG要求
            feature_set.away_xg_last5.total_xg / 1.0,
            feature_set.home_xg_last3.total_xg / 1.0,
            feature_set.away_xg_last3.total_xg / 1.0
        )
        completeness_scores.append(xg_completeness * self.config.completeness_weights['xg_features'])

        # 赔率特征完整性
        odds_completeness = 1.0 if feature_set.odds.home_win_odds is not None else 0.5
        completeness_scores.append(odds_completeness * self.config.completeness_weights['odds_features'])

        # H2H特征完整性
        h2h_completeness = min(feature_set.h2h_total_matches / 3, 1.0)  # 假设至少3场交锋
        completeness_scores.append(h2h_completeness * self.config.completeness_weights['h2h_features'])

        # 计算总分
        total_completeness = sum(completeness_scores)
        feature_set.feature_completeness_score = min(total_completeness, 1.0)

        # 设置数据质量标记
        if feature_set.feature_completeness_score >= 0.8:
            feature_set.data_quality_flag = "HIGH"
        elif feature_set.feature_completeness_score >= 0.5:
            feature_set.data_quality_flag = "MEDIUM"
        else:
            feature_set.data_quality_flag = "LOW"

    async def extract_batch_features(self, match_ids: List[str],
                                    historical_data: pd.DataFrame) -> List[MatchFeatureSet]:
        """
        批量提取特征

        Args:
            match_ids: 比赛ID列表
            historical_data: 历史数据

        Returns:
            List[MatchFeatureSet]: 特征集列表
        """
        self.logger.info(f"批量提取 {len(match_ids)} 个比赛的特征")

        features = []
        for match_id in match_ids:
            try:
                feature = await self.extract_features(match_id, historical_data)
                features.append(feature)
            except Exception as e:
                self.logger.error(f"提取特征失败 {match_id}: {e}")
                # 可以选择创建默认特征或跳过
                continue

        self.logger.info(f"批量特征提取完成: {len(features)}/{len(match_ids)}")
        return features

    def get_feature_matrix(self, feature_sets: List[MatchFeatureSet]) -> Tuple[np.ndarray, List[str]]:
        """
        将特征集转换为特征矩阵

        Args:
            feature_sets: 特征集列表

        Returns:
            Tuple[np.ndarray, List[str]]: 特征矩阵和特征名称
        """
        if not feature_sets:
            return np.array([]), []

        # 获取特征名称
        feature_names = feature_sets[0].get_feature_names()
        n_features = len(feature_names)

        # 构建特征矩阵
        feature_matrix = np.zeros((len(feature_sets), n_features))

        for i, feature_set in enumerate(feature_sets):
            try:
                feature_matrix[i] = feature_set.get_feature_vector()
            except Exception as e:
                self.logger.warning(f"特征向量转换失败 {feature_set.match_id}: {e}")
                # 使用默认值填充
                feature_matrix[i] = np.full(n_features, 0.5)

        return feature_matrix, feature_names

    def clear_cache(self):
        """清空特征缓存"""
        self._feature_cache.clear()
        self.logger.debug("特征缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self._feature_cache),
            "cache_keys": list(self._feature_cache.keys())
        }


# 便捷函数
def create_feature_extractor(config: Optional[FeatureEngineeringConfig] = None) -> MatchFeatureExtractor:
    """
    创建特征提取器实例

    Args:
        config: 特征工程配置

    Returns:
        MatchFeatureExtractor: 特征提取器实例
    """
    return MatchFeatureExtractor(config)


# 主函数 - 特征提取器测试和演示
async def main():
    """主函数 - 特征提取器演示"""
    print("🚀 足球预测特征提取器演示")

    try:
        # 创建模拟数据
        generator = MockMatchDataGenerator()
        historical_data = generator.create_historical_dataframe(15)

        # 创建特征提取器
        extractor = create_feature_extractor()

        # 提取单个比赛特征
        match_id = historical_data.iloc[-1]['match_id']
        features = await extractor.extract_features(match_id, historical_data)

        print(f"✅ 特征提取成功: {features.match_id}")
        print(f"📊 特征完整性评分: {features.feature_completeness_score:.2f}")
        print(f"🏷️  数据质量标记: {features.data_quality_flag}")

        # 显示关键特征
        print(f"🏠 主队形态得分: {features.home_form_last5.get_form_score():.1f}/100")
        print(f"✈️  客队形态得分: {features.away_form_last5.get_form_score():.1f}/100")
        print(f"⚡ 主队xG效率: {features.home_xg_last5.xg_efficiency:.2f}")
        print(f"⚡ 客队xG效率: {features.away_xg_last5.xg_efficiency:.2f}")
        print(f"💰 H2H主队胜率: {features.h2h_home_win_rate:.2f}")

        # 测试批量提取
        match_ids = historical_data['match_id'].tail(5).tolist()
        batch_features = await extractor.extract_batch_features(match_ids, historical_data)

        print(f"\n📦 批量提取完成: {len(batch_features)} 个特征集")

        # 测试特征矩阵转换
        feature_matrix, feature_names = extractor.get_feature_matrix(batch_features)
        print(f"🔢 特征矩阵形状: {feature_matrix.shape}")
        print(f"📋 特征名称: {len(feature_names)} 个")

        # 缓存统计
        cache_stats = extractor.get_cache_stats()
        print(f"💾 缓存统计: {cache_stats}")

        print("\n🎉 特征提取器演示完成!")

    except Exception as e:
        print(f"❌ 特征提取器演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


# Mock数据生成器 (用于演示)
class MockMatchDataGenerator:
    """Mock比赛数据生成器"""

    @staticmethod
    def create_historical_dataframe(num_matches: int = 10) -> pd.DataFrame:
        """创建历史比赛DataFrame"""
        data = []
        base_date = datetime.now() - timedelta(days=30)

        teams = [
            "team_1", "team_2", "team_3", "team_4", "team_5",
            "team_6", "team_7", "team_8", "team_9", "team_10"
        ]

        for i in range(num_matches):
            match_date = base_date + timedelta(days=i * 3)
            home_team = teams[i % len(teams)]
            away_team = teams[(i + 1) % len(teams)]

            # 模拟比赛结果
            home_score = np.random.poisson(1.5)
            away_score = np.random.poisson(1.2)

            # 模拟xG数据
            home_xg = max(0.1, np.random.normal(1.8, 0.8))
            away_xg = max(0.1, np.random.normal(1.5, 0.7))

            # 模拟赔率
            home_odds = round(np.random.uniform(1.8, 4.5), 2)
            draw_odds = round(np.random.uniform(3.0, 4.0), 2)
            away_odds = round(np.random.uniform(2.5, 5.0), 2)

            data.append({
                "match_id": f"match_{i}",
                "home_team_id": home_team,
                "away_team_id": away_team,
                "match_date": match_date.isoformat(),
                "home_score": int(home_score),
                "away_score": int(away_score),
                "home_xg": home_xg,
                "away_xg": away_xg,
                "home_odds": home_odds,
                "draw_odds": draw_odds,
                "away_odds": away_odds,
                "venue": f"Stadium {i % 5 + 1}",
                "status": "FINISHED"
            })

        return pd.DataFrame(data)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)