#!/usr/bin/env python3
"""
增强版特征提取器 - Enhanced Feature Extractor
将原始比赛数据转换为ML特征矩阵
Phase 2: 数据预处理和特征工程

主要功能:
- 元数据特征提取 (match_id, date, league)
- 目标变量提取 (score, result)
- 基础统计数据提取 (possession, shots)
- 高级统计数据提取 (xG, advanced stats)
- 上下文特征提取 (referee, stadium, odds)
- 衍生特征工程 (ratios, differences)

作者: Chief Data Scientist
创建时间: 2025-12-10
版本: 2.0.0 - Phase 2 Kick-off
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """特征配置"""
    # 基础特征
    include_metadata: bool = True
    include_basic_stats: bool = True
    include_advanced_stats: bool = True
    include_context: bool = True
    include_derived_features: bool = True


class EnhancedFeatureExtractor:
    """
    增强版特征提取器

    将数据库中的原始比赛数据转换为扁平化的特征字典
    为机器学习模型准备输入数据
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.feature_stats = {
            'total_matches': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'missing_fields': {}
        }

    def extract_features(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单场比赛数据中提取特征

        Args:
            match_data: 数据库中的比赛数据字典

        Returns:
            扁平化的特征字典
        """
        try:
            self.feature_stats['total_matches'] += 1

            # 初始化特征字典
            features = {}

            # 1. 元数据特征
            if self.config.include_metadata:
                features.update(self._extract_metadata(match_data))

            # 2. 目标变量（标签）
            features.update(self._extract_target_variables(match_data))

            # 3. 基础统计数据
            if self.config.include_basic_stats:
                features.update(self._extract_basic_stats(match_data))

            # 4. 高级统计数据
            if self.config.include_advanced_stats:
                features.update(self._extract_advanced_stats(match_data))

            # 5. 上下文特征
            if self.config.include_context:
                features.update(self._extract_context_features(match_data))

            # 6. 衍生特征
            if self.config.include_derived_features:
                features.update(self._extract_derived_features(features))

            self.feature_stats['successful_extractions'] += 1
            return features

        except Exception as e:
            self.feature_stats['failed_extractions'] += 1
            logger.error(f"特征提取失败: {e}, match_id: {match_data.get('id', 'unknown')}")
            return {}

    def _extract_metadata(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取元数据特征"""
        features = {}

        # 比赛ID
        features['match_id'] = match_data.get('id')

        # 日期特征
        match_date = match_data.get('match_date')
        if match_date:
            # 转换为datetime对象
            if isinstance(match_date, str):
                try:
                    dt = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                except:
                    dt = None
            else:
                dt = match_date

            if dt:
                features['year'] = dt.year
                features['month'] = dt.month
                features['day_of_week'] = dt.weekday()  # 0=Monday, 6=Sunday
                features['day_of_year'] = dt.timetuple().tm_yday
                features['is_weekend'] = 1 if dt.weekday() >= 5 else 0
            else:
                features['year'] = None
                features['month'] = None
                features['day_of_week'] = None
                features['day_of_year'] = None
                features['is_weekend'] = None
        else:
            features['year'] = None
            features['month'] = None
            features['day_of_week'] = None
            features['day_of_year'] = None
            features['is_weekend'] = None

        # 联赛信息
        features['league_id'] = match_data.get('league_id')
        features['league_name'] = match_data.get('league_name')

        return features

    def _extract_target_variables(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取目标变量（标签）"""
        features = {}

        # 原始得分
        home_score = match_data.get('home_score')
        away_score = match_data.get('away_score')

        features['home_score'] = home_score
        features['away_score'] = away_score

        # 比赛结果
        if home_score is not None and away_score is not None:
            if home_score > away_score:
                result = 'H'  # Home Win
            elif home_score < away_score:
                result = 'A'  # Away Win
            else:
                result = 'D'  # Draw

            # 数值编码
            result_numeric = {'H': 1, 'D': 0, 'A': -1}[result]

            features['result'] = result
            features['result_numeric'] = result_numeric

            # 是否分胜负
            features['has_winner'] = 1 if result in ['H', 'A'] else 0

            # 净胜球
            features['goal_difference'] = home_score - away_score

            # 总进球数
            features['total_goals'] = home_score + away_score

            # 大小球基准
            features['over_2_5_goals'] = 1 if (home_score + away_score) > 2.5 else 0
        else:
            features['result'] = None
            features['result_numeric'] = None
            features['has_winner'] = None
            features['goal_difference'] = None
            features['total_goals'] = None
            features['over_2_5_goals'] = None

        return features

    def _extract_basic_stats(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取基础统计数据"""
        features = {}

        stats_json = match_data.get('stats_json')
        if not stats_json:
            stats_json = match_data.get('match_stats_json')

        if stats_json:
            try:
                # 解析JSON
                if isinstance(stats_json, str):
                    stats = json.loads(stats_json)
                else:
                    stats = stats_json

                # 正确的基础统计指标映射 - 基于实际调试结果
                basic_stats_map = {
                    # 射门数据
                    ('shots', 'total_shots'): 'total_shots',
                    ('shots', 'ShotsOnTarget'): 'shots_on_target',
                    ('shots', 'ShotsOffTarget'): 'shots_off_target',
                    ('shots', 'blocked_shots'): 'blocked_shots',

                    # 角球数据 (可能在corners字段中，如果为空则查找其他字段)
                    ('corners', 'corners'): 'corners',

                    # 越位数据 (在passes字段中)
                    ('passes', 'Offsides'): 'offsides',

                    # 传球数据
                    ('passes', 'passes'): 'total_passes',
                    ('passes', 'accurate_passes'): 'pass_accuracy',
                }

                # 提取统计数据 - 正确处理 [home, away] 格式
                for (section, stat_key), feature_name in basic_stats_map.items():
                    home_key = f'home_{feature_name}'
                    away_key = f'away_{feature_name}'

                    # 获取统计数据
                    section_data = stats.get(section, {})
                    stat_value = section_data.get(stat_key)

                    if stat_value is not None and isinstance(stat_value, list) and len(stat_value) >= 2:
                        home_value = stat_value[0]
                        away_value = stat_value[1]

                        # 特殊处理：pass_accuracy 需要解析百分比字符串
                        if feature_name == 'pass_accuracy':
                            home_value = self._parse_percentage(home_value)
                            away_value = self._parse_percentage(away_value)

                        features[home_key] = home_value
                        features[away_key] = away_value

                        # 差值特征
                        if home_value is not None and away_value is not None:
                            diff_key = f'{feature_name}_difference'
                            features[diff_key] = home_value - away_value

                            # 比率特征（仅当分母不为0时）
                            if away_value != 0 and isinstance(away_value, (int, float)):
                                ratio_key = f'{feature_name}_ratio'
                                features[ratio_key] = home_value / away_value
                    else:
                        # 记录缺失的数据
                        self._track_missing_field(f'{section}.{stat_key}')

                # 尝试从数据库直连字段获取基础统计（备用方案）
                direct_stats_map = {
                    'home_possession': match_data.get('home_possession'),
                    'away_possession': match_data.get('away_possession'),
                    'home_shots': match_data.get('home_shots'),
                    'away_shots': match_data.get('away_shots'),
                    'home_shots_on_target': match_data.get('home_shots_on_target'),
                    'away_shots_on_target': match_data.get('away_shots_on_target'),
                    'home_corners': match_data.get('home_corners'),
                    'away_corners': match_data.get('away_corners'),
                    'home_fouls': match_data.get('home_fouls'),
                    'away_fouls': match_data.get('away_fouls'),
                    'home_yellow_cards': match_data.get('home_yellow_cards'),
                    'away_yellow_cards': match_data.get('away_yellow_cards'),
                    'home_red_cards': match_data.get('home_red_cards'),
                    'away_red_cards': match_data.get('away_red_cards'),
                    'home_passes': match_data.get('home_passes'),
                    'away_passes': match_data.get('away_passes'),
                    'home_pass_accuracy': match_data.get('home_pass_accuracy'),
                    'away_pass_accuracy': match_data.get('away_pass_accuracy'),
                }

                # 合并直连字段数据（如果stats_json中没有找到）
                for field, value in direct_stats_map.items():
                    if value is not None and field not in features:
                        features[field] = value

            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"统计数据解析失败: {e}")
                self._track_missing_field('stats_json_parsing_error')
        else:
            # 如果没有统计数据，记录缺失
            self._track_missing_field('stats_json')

        return features

    def _parse_percentage(self, percentage_str):
        """解析百分比字符串，如 '604 (89%)' -> 89.0"""
        if percentage_str is None:
            return None

        if isinstance(percentage_str, (int, float)):
            return float(percentage_str)

        if isinstance(percentage_str, str):
            # 提取百分比数字
            import re
            match = re.search(r'(\d+)%', percentage_str)
            if match:
                return float(match.group(1))

        return None

    def _extract_advanced_stats(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取高级统计数据"""
        features = {}

        # xG期望进球数据
        home_xg = match_data.get('home_xg')
        away_xg = match_data.get('away_xg')

        features['home_xg'] = home_xg
        features['away_xg'] = away_xg

        if home_xg is not None and away_xg is not None:
            features['xg_difference'] = home_xg - away_xg
            features['total_xg'] = home_xg + away_xg

            # xG vs 实际进球对比
            home_score = match_data.get('home_score')
            away_score = match_data.get('away_score')

            if home_score is not None and away_score is not None:
                features['home_xg_vs_actual'] = home_xg - home_score
                features['away_xg_vs_actual'] = away_xg - away_score
                features['total_xg_vs_actual'] = (home_xg + away_xg) - (home_score + away_score)
        else:
            self._track_missing_field('xg_data')

        return features

    def _extract_context_features(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取上下文特征"""
        features = {}

        # 从environment_json中提取上下文信息
        environment_json = match_data.get('environment_json')
        if environment_json:
            try:
                if isinstance(environment_json, str):
                    env_data = json.loads(environment_json)
                else:
                    env_data = environment_json

                # 裁判信息
                referee_name = env_data.get('referee')
                features['referee_name'] = referee_name

                # 比赛场地
                venue_name = env_data.get('venue')
                features['stadium_name'] = venue_name

                # 天气信息（虽然为空，但仍记录结构）
                weather_data = env_data.get('weather', {})
                if weather_data:
                    features['weather_condition'] = weather_data.get('condition')
                    features['weather_temperature'] = weather_data.get('temperature')
                    features['weather_humidity'] = weather_data.get('humidity')
                    features['weather_wind_speed'] = weather_data.get('wind_speed')
                    features['pitch_condition'] = weather_data.get('pitch_condition')

                # 赔率信息
                odds_data = env_data.get('odds', {})
                if odds_data:
                    # 主胜赔率
                    features['home_win_odds'] = odds_data.get('home_win')
                    # 平局赔率
                    features['draw_odds'] = odds_data.get('draw')
                    # 客胜赔率
                    features['away_win_odds'] = odds_data.get('away_win')

                    # 计算隐含概率
                    if (odds_data.get('home_win') and odds_data.get('draw') and odds_data.get('away_win')):
                        home_imp_prob = 1 / odds_data['home_win'] if odds_data['home_win'] > 0 else 0
                        draw_imp_prob = 1 / odds_data['draw'] if odds_data['draw'] > 0 else 0
                        away_imp_prob = 1 / odds_data['away_win'] if odds_data['away_win'] > 0 else 0

                        total_imp_prob = home_imp_prob + draw_imp_prob + away_imp_prob
                        if total_imp_prob > 0:
                            features['home_win_implied_prob'] = home_imp_prob / total_imp_prob
                            features['draw_implied_prob'] = draw_imp_prob / total_imp_prob
                            features['away_win_implied_prob'] = away_imp_prob / total_imp_prob
                        else:
                            features['home_win_implied_prob'] = None
                            features['draw_implied_prob'] = None
                            features['away_win_implied_prob'] = None

            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"环境数据解析失败: {e}")
        else:
            self._track_missing_field('environment_json')

        return features

    def _extract_derived_features(self, base_features: Dict[str, Any]) -> Dict[str, Any]:
        """提取衍生特征"""
        derived = {}

        try:
            # 射门转化率
            home_shots = base_features.get('home_total_shots')
            home_shots_on_target = base_features.get('home_shots_on_target')
            away_shots = base_features.get('away_total_shots')
            away_shots_on_target = base_features.get('away_shots_on_target')

            if home_shots and home_shots > 0 and home_shots_on_target:
                derived['home_shot_accuracy'] = home_shots_on_target / home_shots

            if away_shots and away_shots > 0 and away_shots_on_target:
                derived['away_shot_accuracy'] = away_shots_on_target / away_shots

            # 期望进球vs实际进球
            home_xg = base_features.get('home_xg')
            away_xg = base_features.get('away_xg')
            home_score = base_features.get('home_score')
            away_score = base_features.get('away_score')

            if home_xg and home_score is not None:
                derived['home_xg_overperformance'] = home_score - home_xg

            if away_xg and away_score is not None:
                derived['away_xg_overperformance'] = away_score - away_xg

            # 控球率优势
            home_possession = base_features.get('home_possession_percentage')
            away_possession = base_features.get('away_possession_percentage')

            if home_possession is not None and away_possession is not None:
                derived['possession_advantage'] = home_possession - away_possession

        except Exception as e:
            logger.warning(f"衍生特征计算失败: {e}")

        return derived

    def _get_nested_value(self, data: Dict[str, Any], keys: List[str]) -> Any:
        """从嵌套字典中获取值"""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _track_missing_field(self, field_name: str):
        """记录缺失字段"""
        if field_name not in self.feature_stats['missing_fields']:
            self.feature_stats['missing_fields'][field_name] = 0
        self.feature_stats['missing_fields'][field_name] += 1

    def get_feature_stats(self) -> Dict[str, Any]:
        """获取特征提取统计信息"""
        return {
            'total_matches': self.feature_stats['total_matches'],
            'successful_extractions': self.feature_stats['successful_extractions'],
            'failed_extractions': self.feature_stats['failed_extractions'],
            'success_rate': (
                self.feature_stats['successful_extractions'] /
                max(self.feature_stats['total_matches'], 1) * 100
            ),
            'missing_fields': self.feature_stats['missing_fields']
        }

    def extract_feature_names(self) -> List[str]:
        """提取所有特征名称（用于构建DataFrame列）"""
        # 基于配置返回特征名称列表
        feature_names = []

        if self.config.include_metadata:
            feature_names.extend([
                'match_id', 'year', 'month', 'day_of_week', 'day_of_year', 'is_weekend',
                'league_id', 'league_name'
            ])

        # 目标变量
        feature_names.extend([
            'home_score', 'away_score', 'result', 'result_numeric', 'has_winner',
            'goal_difference', 'total_goals', 'over_2_5_goals'
        ])

        if self.config.include_basic_stats:
            feature_names.extend([
                'home_possession_percentage', 'away_possession_percentage',
                'home_total_shots', 'away_total_shots',
                'home_shots_on_target', 'away_shots_on_target',
                'home_corners', 'away_corners',
                'home_fouls', 'away_fouls',
                'home_yellow_cards', 'away_yellow_cards',
                'home_red_cards', 'away_red_cards',
                'home_offsides', 'away_offsides',
                'home_total_passes', 'away_total_passes',
                'home_pass_accuracy', 'away_pass_accuracy',
                'home_tackles', 'away_tackles',
                'home_interceptions', 'away_interceptions'
            ])

        if self.config.include_advanced_stats:
            feature_names.extend([
                'home_xg', 'away_xg', 'xg_difference', 'total_xg',
                'home_xg_vs_actual', 'away_xg_vs_actual', 'total_xg_vs_actual'
            ])

        if self.config.include_context:
            feature_names.extend([
                'referee_name', 'stadium_name',
                'weather_condition', 'weather_temperature', 'weather_humidity',
                'weather_wind_speed', 'pitch_condition',
                'home_win_odds', 'draw_odds', 'away_win_odds',
                'home_win_implied_prob', 'draw_implied_prob', 'away_win_implied_prob'
            ])

        if self.config.include_derived_features:
            feature_names.extend([
                'home_shot_accuracy', 'away_shot_accuracy',
                'home_xg_overperformance', 'away_xg_overperformance',
                'possession_advantage'
            ])

        return feature_names