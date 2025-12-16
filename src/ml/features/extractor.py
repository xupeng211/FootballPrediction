"""
比赛特征提取器 - Match Feature Extractor

为足球比赛数据提取机器学习特征，整合多种高级特征计算器。
支持历史交锋、场馆分析、球队形态等多种特征工程。

主要功能:
1. 整合H2H和场馆分析器
2. 计算滚动统计特征
3. 提取球队当前形态
4. 生成标准化特征向量
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .h2h_calculator import H2HCalculator
from .venue_analyzer import VenueAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class MatchFeatureSet:
    """比赛特征集合"""
    match_id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime

    # 基础特征
    home_team_name: str
    away_team_name: str
    league_id: str
    season: str

    # 特征向量
    features: Dict[str, float]
    feature_names: List[str]
    feature_vector: np.ndarray

    # 元数据
    feature_completeness: float
    extraction_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'match_id': self.match_id,
            'home_team_id': self.home_team_id,
            'away_team_id': self.away_team_id,
            'match_date': self.match_date.isoformat(),
            'home_team_name': self.home_team_name,
            'away_team_name': self.away_team_name,
            'league_id': self.league_id,
            'season': self.season,
            'features': self.features,
            'feature_names': self.feature_names,
            'feature_vector': self.feature_vector.tolist(),
            'feature_completeness': self.feature_completeness,
            'extraction_time': self.extraction_time.isoformat()
        }


class MatchFeatureExtractor:
    """
    比赛特征提取器

    整合多种特征计算方法，为足球比赛生成全面的特征表示。
    支持历史交锋、主客场分析、球队形态等特征提取。

    主要特征类别:
    1. H2H历史交锋特征
    2. 场馆分离滚动统计
    3. 球队近期形态
    4. 联赛排名和积分
    """

    def __init__(
        self,
        h2h_calculator: Optional[H2HCalculator] = None,
        venue_analyzer: Optional[VenueAnalyzer] = None,
        min_history_days: int = 30,
        max_history_days: int = 365,
        feature_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化特征提取器

        Args:
            h2h_calculator: H2H计算器，如果为None则创建默认实例
            venue_analyzer: 场馆分析器，如果为None则创建默认实例
            min_history_days: 最小历史数据天数
            max_history_days: 最大历史数据天数
            feature_weights: 特征权重配置
        """
        self.h2h_calculator = h2h_calculator or H2HCalculator()
        self.venue_analyzer = venue_analyzer or VenueAnalyzer()

        self.min_history_days = min_history_days
        self.max_history_days = max_history_days
        self.feature_weights = feature_weights or {}

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 特征名称缓存
        self._feature_names_cache: Optional[List[str]] = None

        self.logger.info("MatchFeatureExtractor 初始化完成")

    async def extract_features(
        self,
        match_data: Dict[str, Any],
        historical_matches: pd.DataFrame,
        team_stats: Optional[pd.DataFrame] = None
    ) -> MatchFeatureSet:
        """
        为单场比赛提取特征

        Args:
            match_data: 比赛数据字典
            historical_matches: 历史比赛数据DataFrame
            team_stats: 球队统计数据DataFrame（可选）

        Returns:
            MatchFeatureSet: 比赛特征集合
        """
        try:
            start_time = datetime.now()

            # 解析比赛数据
            match_id = match_data.get('id')
            home_team_id = match_data.get('home_team_id')
            away_team_id = match_data.get('away_team_id')
            match_date = self._parse_match_date(match_data.get('match_date'))

            if not all([match_id, home_team_id, away_team_id, match_date]):
                raise ValueError(f"比赛数据不完整: {match_data}")

            self.logger.info(f"开始提取比赛 {match_id} 的特征")

            # 1. 提取H2H特征
            h2h_features = await self._extract_h2h_features(
                home_team_id, away_team_id, historical_matches, match_date
            )

            # 2. 提取场馆特征
            venue_features = await self._extract_venue_features(
                home_team_id, away_team_id, historical_matches, match_date
            )

            # 3. 提取球队形态特征
            form_features = await self._extract_form_features(
                home_team_id, away_team_id, historical_matches, match_date
            )

            # 4. 提取联赛排名特征（如果提供了球队统计数据）
            ranking_features = {}
            if team_stats is not None:
                ranking_features = await self._extract_ranking_features(
                    home_team_id, away_team_id, team_stats, match_date
                )

            # 合并所有特征
            all_features = {**h2h_features, **venue_features, **form_features, **ranking_features}

            # 应用特征权重
            weighted_features = self._apply_feature_weights(all_features)

            # 生成特征向量
            feature_names = self._get_feature_names()
            feature_vector = self._create_feature_vector(weighted_features, feature_names)

            # 计算特征完整性
            feature_completeness = self._calculate_feature_completeness(weighted_features)

            # 创建特征集合
            feature_set = MatchFeatureSet(
                match_id=match_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                match_date=match_date,
                home_team_name=match_data.get('home_team_name', ''),
                away_team_name=match_data.get('away_team_name', ''),
                league_id=match_data.get('league_id', ''),
                season=match_data.get('season', ''),
                features=weighted_features,
                feature_names=feature_names,
                feature_vector=feature_vector,
                feature_completeness=feature_completeness,
                extraction_time=datetime.now()
            )

            extraction_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"特征提取完成，耗时 {extraction_time:.2f}秒，特征数: {len(weighted_features)}")

            return feature_set

        except Exception as e:
            self.logger.error(f"特征提取失败: {str(e)}")
            raise

    async def _extract_h2h_features(
        self,
        home_team_id: int,
        away_team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime
    ) -> Dict[str, float]:
        """
        提取H2H历史交锋特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_matches: 历史比赛数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: H2H特征字典
        """
        try:
            # 使用正确的方法名计算H2H统计
            h2h_stats = self.h2h_calculator.calculate_h2h_for_match(
                historical_matches, home_team_id, away_team_id, match_date
            )

            if h2h_stats.matches_count == 0:
                return self._get_default_h2h_features()

            # 转换为特征向量
            features = {
                'h2h_matches_played': float(h2h_stats.matches_count),
                'h2h_home_win_rate': float(h2h_stats.home_win_rate),
                'h2h_avg_goal_diff': float(h2h_stats.avg_goal_diff),
                'h2h_avg_total_goals': float(h2h_stats.avg_total_goals)
            }

            return features

        except Exception as e:
            self.logger.warning(f"H2H特征提取失败: {str(e)}")
            return self._get_default_h2h_features()

    async def _extract_venue_features(
        self,
        home_team_id: int,
        away_team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime
    ) -> Dict[str, float]:
        """
        提取场馆相关特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_matches: 历史比赛数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 场馆特征字典
        """
        try:
            # 获取主队在主场的表现
            home_venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
                historical_matches, home_team_id, away_team_id, match_date
            )

            # 注意：VenueAnalyzer的calculate_venue_features_for_match已包含两队的统计
            # 我们直接从返回的VenueStats中提取数据
            venue_stats = home_venue_stats

            # 合并场馆特征
            features = {}

            # 从VenueStats提取特征
            features.update({
                'home_venue_goals_rolling_3': float(venue_stats.home_goals_rolling_3),
                'home_venue_goals_rolling_5': float(venue_stats.home_goals_rolling_5),
                'away_venue_goals_rolling_3': float(venue_stats.away_goals_rolling_3),
                'away_venue_goals_rolling_5': float(venue_stats.away_goals_rolling_5),
                'home_venue_advantage_3': float(venue_stats.home_advantage_3),
                'home_venue_advantage_5': float(venue_stats.home_advantage_5),
                'venue_home_vs_away_diff_3': float(venue_stats.home_away_goal_diff_3),
                'venue_home_vs_away_diff_5': float(venue_stats.home_away_goal_diff_5)
            })

            return features

        except Exception as e:
            self.logger.warning(f"场馆特征提取失败: {str(e)}")
            return self._get_default_venue_features()

    async def _extract_form_features(
        self,
        home_team_id: int,
        away_team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime
    ) -> Dict[str, float]:
        """
        提取球队近期形态特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            historical_matches: 历史比赛数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 形态特征字典
        """
        try:
            features = {}

            # 计算最近5场比赛的形态
            for team_id, prefix in [(home_team_id, 'home'), (away_team_id, 'away')]:
                team_matches = self._get_recent_matches(
                    team_id, historical_matches, match_date, 5
                )

                if not team_matches.empty:
                    # 计算形态指标
                    recent_form = self._calculate_recent_form(team_matches, team_id)

                    features.update({
                        f'{prefix}_recent_matches': float(len(team_matches)),
                        f'{prefix}_recent_win_rate': float(recent_form.get('win_rate', 0.0)),
                        f'{prefix}_recent_draw_rate': float(recent_form.get('draw_rate', 0.0)),
                        f'{prefix}_recent_loss_rate': float(recent_form.get('loss_rate', 0.0)),
                        f'{prefix}_recent_avg_goals_scored': float(recent_form.get('avg_goals_scored', 0.0)),
                        f'{prefix}_recent_avg_goals_conceded': float(recent_form.get('avg_goals_conceded', 0.0)),
                        f'{prefix}_recent_points_per_game': float(recent_form.get('points_per_game', 0.0)),
                        f'{prefix}_recent_momentum': float(recent_form.get('momentum', 0.0))  # 近期趋势
                    })
                else:
                    # 没有近期比赛数据时的默认值
                    for suffix in ['matches', 'win_rate', 'draw_rate', 'loss_rate',
                                 'avg_goals_scored', 'avg_goals_conceded', 'points_per_game', 'momentum']:
                        features[f'{prefix}_recent_{suffix}'] = 0.0

            return features

        except Exception as e:
            self.logger.warning(f"形态特征提取失败: {str(e)}")
            return self._get_default_form_features()

    async def _extract_ranking_features(
        self,
        home_team_id: int,
        away_team_id: int,
        team_stats: pd.DataFrame,
        match_date: datetime
    ) -> Dict[str, float]:
        """
        提取联赛排名特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            team_stats: 球队统计数据
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 排名特征字典
        """
        try:
            features = {}

            # 获取两队排名信息
            home_stats = team_stats[team_stats['team_id'] == home_team_id]
            away_stats = team_stats[team_stats['team_id'] == away_team_id]

            if not home_stats.empty:
                home_rank = home_stats.iloc[0]
                features.update({
                    'home_league_position': float(home_rank.get('position', 20)),
                    'home_league_points': float(home_rank.get('points', 0)),
                    'home_league_goals_for': float(home_rank.get('goals_for', 0)),
                    'home_league_goals_against': float(home_rank.get('goals_against', 0)),
                    'home_league_goal_difference': float(home_rank.get('goal_difference', 0)),
                    'home_league_matches_played': float(home_rank.get('matches_played', 0))
                })

            if not away_stats.empty:
                away_rank = away_stats.iloc[0]
                features.update({
                    'away_league_position': float(away_rank.get('position', 20)),
                    'away_league_points': float(away_rank.get('points', 0)),
                    'away_league_goals_for': float(away_rank.get('goals_for', 0)),
                    'away_league_goals_against': float(away_rank.get('goals_against', 0)),
                    'away_league_goal_difference': float(away_rank.get('goal_difference', 0)),
                    'away_league_matches_played': float(away_rank.get('matches_played', 0))
                })

            # 计算相对特征
            if not home_stats.empty and not away_stats.empty:
                features.update({
                    'position_difference': float(home_rank.get('position', 20) - away_rank.get('position', 20)),
                    'points_difference': float(home_rank.get('points', 0) - away_rank.get('points', 0)),
                    'goal_difference_difference': float(home_rank.get('goal_difference', 0) - away_rank.get('goal_difference', 0))
                })

            return features

        except Exception as e:
            self.logger.warning(f"排名特征提取失败: {str(e)}")
            return self._get_default_ranking_features()

    def _parse_match_date(self, date_value: Any) -> datetime:
        """解析比赛日期"""
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        else:
            raise ValueError(f"无法解析日期: {date_value}")

    def _get_recent_matches(
        self,
        team_id: int,
        historical_matches: pd.DataFrame,
        match_date: datetime,
        limit: int = 5
    ) -> pd.DataFrame:
        """获取球队最近的比赛"""
        team_matches = historical_matches[
            ((historical_matches['home_team_id'] == team_id) |
             (historical_matches['away_team_id'] == team_id)) &
            (historical_matches['match_date'] < match_date)
        ].sort_values('match_date', ascending=False).head(limit)

        return team_matches

    def _calculate_recent_form(self, team_matches: pd.DataFrame, team_id: int) -> Dict[str, float]:
        """计算球队近期形态"""
        if team_matches.empty:
            return {}

        total_matches = len(team_matches)
        wins, draws, losses = 0, 0, 0
        goals_scored, goals_conceded = 0, 0
        total_points = 0

        # 计算动量（最近比赛的权重）
        momentum = 0
        weights = [5, 4, 3, 2, 1]  # 最近比赛权重更高

        for i, (_, match) in enumerate(team_matches.iterrows()):
            weight = weights[i] if i < len(weights) else 1

            if match['home_team_id'] == match['away_team_id']:
                continue  # 跳过异常数据

            is_home = match['home_team_id'] == team_id
            team_score = match['home_score'] if is_home else match['away_score']
            opponent_score = match['away_score'] if is_home else match['home_score']

            goals_scored += team_score
            goals_conceded += opponent_score

            if team_score > opponent_score:
                wins += 1
                total_points += 3
                momentum += weight * 3
            elif team_score == opponent_score:
                draws += 1
                total_points += 1
                momentum += weight * 1
            else:
                losses += 1
                momentum += weight * 0

        return {
            'win_rate': wins / total_matches if total_matches > 0 else 0.0,
            'draw_rate': draws / total_matches if total_matches > 0 else 0.0,
            'loss_rate': losses / total_matches if total_matches > 0 else 0.0,
            'avg_goals_scored': goals_scored / total_matches if total_matches > 0 else 0.0,
            'avg_goals_conceded': goals_conceded / total_matches if total_matches > 0 else 0.0,
            'points_per_game': total_points / total_matches if total_matches > 0 else 0.0,
            'momentum': momentum / total_matches if total_matches > 0 else 0.0
        }

    def _apply_feature_weights(self, features: Dict[str, float]) -> Dict[str, float]:
        """应用特征权重"""
        if not self.feature_weights:
            return features

        weighted_features = {}
        for name, value in features.items():
            weight = self.feature_weights.get(name, 1.0)
            weighted_features[name] = value * weight

        return weighted_features

    def _get_feature_names(self) -> List[str]:
        """获取特征名称列表（缓存）"""
        if self._feature_names_cache is None:
            # 合并所有可能的特征名称
            feature_names = []

            # H2H特征
            feature_names.extend([
                'h2h_matches_played', 'h2h_home_wins', 'h2h_away_wins', 'h2h_draws',
                'h2h_home_win_rate', 'h2h_away_win_rate', 'h2h_draw_rate',
                'h2h_avg_home_goals', 'h2h_avg_away_goals', 'h2h_avg_total_goals',
                'h2h_both_teams_score_rate', 'h2h_clean_sheets_home_rate', 'h2h_clean_sheets_away_rate'
            ])

            # 场馆特征
            for prefix in ['home_venue', 'away_venue']:
                feature_names.extend([
                    f'{prefix}_matches', f'{prefix}_win_rate', f'{prefix}_draw_rate', f'{prefix}_loss_rate',
                    f'{prefix}_avg_goals_scored', f'{prefix}_avg_goals_conceded', f'{prefix}_clean_sheets_rate', f'{prefix}_cs_score'
                ])

            # 形态特征
            for prefix in ['home_recent', 'away_recent']:
                feature_names.extend([
                    f'{prefix}_matches', f'{prefix}_win_rate', f'{prefix}_draw_rate', f'{prefix}_loss_rate',
                    f'{prefix}_avg_goals_scored', f'{prefix}_avg_goals_conceded', f'{prefix}_points_per_game', f'{prefix}_momentum'
                ])

            # 排名特征
            for prefix in ['home_league', 'away_league']:
                feature_names.extend([
                    f'{prefix}_position', f'{prefix}_points', f'{prefix}_goals_for',
                    f'{prefix}_goals_against', f'{prefix}_goal_difference', f'{prefix}_matches_played'
                ])

            # 相对特征
            feature_names.extend(['position_difference', 'points_difference', 'goal_difference_difference'])

            self._feature_names_cache = feature_names

        return self._feature_names_cache

    def _create_feature_vector(self, features: Dict[str, float], feature_names: List[str]) -> np.ndarray:
        """创建特征向量"""
        vector = []
        for name in feature_names:
            value = features.get(name, 0.0)
            vector.append(value)

        return np.array(vector, dtype=np.float32)

    def _calculate_feature_completeness(self, features: Dict[str, float]) -> float:
        """计算特征完整性"""
        if not features:
            return 0.0

        non_zero_features = sum(1 for v in features.values() if v != 0.0)
        return non_zero_features / len(features)

    # 默认特征方法
    def _get_default_h2h_features(self) -> Dict[str, float]:
        """获取默认H2H特征"""
        return {name: 0.0 for name in self._get_feature_names() if name.startswith('h2h_')}

    def _get_default_venue_features(self) -> Dict[str, float]:
        """获取默认场馆特征"""
        return {name: 0.0 for name in self._get_feature_names() if 'venue' in name}

    def _get_default_form_features(self) -> Dict[str, float]:
        """获取默认形态特征"""
        return {name: 0.0 for name in self._get_feature_names() if 'recent' in name}

    def _get_default_ranking_features(self) -> Dict[str, float]:
        """获取默认排名特征"""
        return {name: 0.0 for name in self._get_feature_names() if any(x in name for x in ['league', 'position_difference', 'points_difference'])}

    async def extract_batch_features(
        self,
        matches_data: List[Dict[str, Any]],
        historical_matches: pd.DataFrame,
        team_stats: Optional[pd.DataFrame] = None
    ) -> List[MatchFeatureSet]:
        """
        批量提取特征

        Args:
            matches_data: 比赛数据列表
            historical_matches: 历史比赛数据
            team_stats: 球队统计数据

        Returns:
            List[MatchFeatureSet]: 比赛特征集合列表
        """
        feature_sets = []

        for match_data in matches_data:
            try:
                feature_set = await self.extract_features(
                    match_data, historical_matches, team_stats
                )
                feature_sets.append(feature_set)
            except Exception as e:
                self.logger.error(f"比赛 {match_data.get('id')} 特征提取失败: {str(e)}")
                continue

        self.logger.info(f"批量特征提取完成: {len(feature_sets)}/{len(matches_data)}")
        return feature_sets

    def get_feature_importance_info(self) -> Dict[str, Any]:
        """获取特征重要性信息"""
        feature_names = self._get_feature_names()

        return {
            'total_features': len(feature_names),
            'feature_categories': {
                'h2h': len([n for n in feature_names if n.startswith('h2h_')]),
                'venue': len([n for n in feature_names if 'venue' in n]),
                'form': len([n for n in feature_names if 'recent' in n]),
                'ranking': len([n for n in feature_names if 'league' in n or 'difference' in n])
            },
            'feature_weights': self.feature_weights,
            'feature_names': feature_names
        }