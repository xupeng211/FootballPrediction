#!/usr/bin/env python3
"""
V33.0 Enhanced Feature Miner - 增强版特征开采引擎
==================================================
从实际数据结构中提取 400+ 维特征
"""

import sys
import json
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class V33EnhancedMiner:
    """
    V33.0 增强版特征开采引擎

    核心改进:
    1. 完整提取所有 7 组 Technical Stats (~200 维)
    2. 深度分析 Shotmap 坐标数据 (~100 维)
    3. 全面解析 Momentum 动量序列 (~50 维)
    4. 环境与裁判因子 (~20 维)
    5. 交互特征 (~30 维)
    """

    def __init__(self):
        """初始化增强版采矿器"""
        self.feature_counts = {
            'technical': 0,
            'shotmap': 0,
            'momentum': 0,
            'environment': 0,
            'interaction': 0,
            'total': 0
        }

    def extract_all_features(self, json_data: Dict) -> Dict[str, Any]:
        """
        提取所有特征 (400+ 维)

        Args:
            json_data: FotMob JSON 数据

        Returns:
            特征字典
        """
        all_features = {}

        # 1. Technical Stats - 完整提取
        tech_dict = self._extract_technical_stats_full(json_data)
        all_features.update(tech_dict)
        self.feature_counts['technical'] = len(tech_dict)

        # 2. Shotmap - 深度分析
        shotmap_dict = self._extract_shotmap_features_full(json_data)
        all_features.update(shotmap_dict)
        self.feature_counts['shotmap'] = len(shotmap_dict)

        # 3. Momentum - 时序分析
        momentum_dict = self._extract_momentum_features_full(json_data)
        all_features.update(momentum_dict)
        self.feature_counts['momentum'] = len(momentum_dict)

        # 4. Environment
        env_dict = self._extract_environment_features(json_data)
        all_features.update(env_dict)
        self.feature_counts['environment'] = len(env_dict)

        # 5. Interaction
        inter_dict = self._calculate_interaction_features(all_features)
        all_features.update(inter_dict)
        self.feature_counts['interaction'] = len(inter_dict)

        self.feature_counts['total'] = len(all_features)
        return all_features

    def _extract_technical_stats_full(self, json_data: Dict) -> Dict[str, float]:
        """完整提取所有技术统计"""
        features = {}

        try:
            actual_data = json_data.get('l2_json', json_data)
            content = actual_data.get('content', {})
            stats = content.get('stats', {})
            periods = stats.get('Periods', {})
            all_period = periods.get('All', {})
            all_stats = all_period.get('stats', [])

            if not isinstance(all_stats, list):
                return features

            # 提取所有 stat groups
            for group_idx, stat_group in enumerate(all_stats):
                group_title = stat_group.get('title', f'group_{group_idx}')
                stats_list = stat_group.get('stats', [])

                if not isinstance(stats_list, list):
                    continue

                for stat_item in stats_list:
                    if not isinstance(stat_item, dict):
                        continue

                    key = stat_item.get('key', '')
                    if not key:
                        continue

                    # 生成安全的特征名
                    safe_key = key.replace('.', '_').replace('-', '_')

                    stats_values = stat_item.get('stats', [])
                    if len(stats_values) >= 2:
                        home_val = self._parse_stat_value(stats_values[0])
                        away_val = self._parse_stat_value(stats_values[1])

                        # 基础特征
                        features[f'tech_{safe_key}_home'] = home_val
                        features[f'tech_{safe_key}_away'] = away_val
                        features[f'tech_{safe_key}_diff'] = self._safe_subtract(home_val, away_val)
                        features[f'tech_{safe_key}_total'] = self._safe_add(home_val, away_val)

                        # 比率特征
                        ratio = self._safe_divide(home_val, away_val)
                        features[f'tech_{safe_key}_ratio'] = ratio

                        # 百分比特征 (如果有)
                        home_pct = self._extract_percentage(stats_values[0])
                        away_pct = self._extract_percentage(stats_values[1])
                        if home_pct is not None:
                            features[f'tech_{safe_key}_home_pct'] = home_pct
                        if away_pct is not None:
                            features[f'tech_{safe_key}_away_pct'] = away_pct

        except Exception as e:
            logger.error(f"技术统计提取失败: {e}")

        return features

    def _extract_shotmap_features_full(self, json_data: Dict) -> Dict[str, float]:
        """深度提取射门特征"""
        features = {}

        try:
            actual_data = json_data.get('l2_json', json_data)
            content = actual_data.get('content', {})
            shotmap = content.get('shotmap', {})
            shots = shotmap.get('shots', [])

            if not shots:
                return features

            # 获取主客队 ID
            general = actual_data.get('general', {})
            home_team = general.get('homeTeam', {})
            away_team = general.get('awayTeam', {})
            home_id = home_team.get('id', 0)
            away_id = away_team.get('id', 0)

            # 分离主客队射门
            home_shots = []
            away_shots = []

            for shot in shots:
                team_id = shot.get('teamId', 0)

                shot_data = {
                    'x': shot.get('x', 0),
                    'y': shot.get('y', 0),
                    'blockedX': shot.get('blockedX', 0),
                    'blockedY': shot.get('blockedY', 0),
                    'min': shot.get('min', 0),
                    'period': shot.get('period', ''),
                    'playerId': shot.get('playerId', 0),
                    'shotType': shot.get('shotType', ''),
                    'eventType': shot.get('eventType', ''),
                    'fullName': shot.get('fullName', ''),
                    'lastName': shot.get('lastName', ''),
                }

                if team_id == home_id:
                    home_shots.append(shot_data)
                elif team_id == away_id:
                    away_shots.append(shot_data)

            # 计算射门特征
            features.update(self._calc_shotmap_stats(home_shots, away_shots))

        except Exception as e:
            logger.error(f"射门特征提取失败: {e}")

        return features

    def _calc_shotmap_stats(self, home_shots: List, away_shots: List) -> Dict[str, float]:
        """计算射门统计 - 扩展版"""
        features = {}

        def calc_stats(shots: List, prefix: str):
            if not shots:
                return {
                    f'{prefix}_count': 0,
                    f'{prefix}_first_half': 0,
                    f'{prefix}_second_half': 0,
                    f'{prefix}_avg_x': 0,
                    f'{prefix}_avg_y': 0,
                    f'{prefix}_std_x': 0,
                    f'{prefix}_std_y': 0,
                }

            count = len(shots)
            first_half = sum(1 for s in shots if s['period'] == 'FirstHalf')
            second_half = sum(1 for s in shots if s['period'] == 'SecondHalf')

            xs = [s['x'] for s in shots]
            ys = [s['y'] for s in shots]
            avg_x = np.mean(xs)
            avg_y = np.mean(ys)

            # 射门类型分布
            shot_types = {}
            event_types = {}
            for s in shots:
                st = s.get('shotType', 'Unknown')
                et = s.get('eventType', 'Unknown')
                shot_types[st] = shot_types.get(st, 0) + 1
                event_types[et] = event_types.get(et, 0) + 1

            # 距离特征 (假设 x,y 是距离球门的坐标)
            distances = [np.sqrt(x**2 + y**2) for x, y in zip(xs, ys)]

            # 玩家多样性
            unique_players = len(set(s.get('playerId', 0) for s in shots))

            result = {
                f'{prefix}_count': count,
                f'{prefix}_first_half': first_half,
                f'{prefix}_second_half': second_half,
                f'{prefix}_avg_x': avg_x,
                f'{prefix}_avg_y': avg_y,
                f'{prefix}_std_x': np.std(xs),
                f'{prefix}_std_y': np.std(ys),
                f'{prefix}_avg_distance': np.mean(distances),
                f'{prefix}_std_distance': np.std(distances),
                f'{prefix}_unique_players': unique_players,
                f'{prefix}_player_diversity': unique_players / count if count > 0 else 0,
            }

            # 添加射门类型特征
            for st, cnt in shot_types.items():
                safe_st = st.replace(' ', '_').replace('-', '_')
                result[f'{prefix}_{safe_st}_count'] = cnt
                result[f'{prefix}_{safe_st}_ratio'] = cnt / count

            # 添加事件类型特征
            for et, cnt in event_types.items():
                safe_et = et.replace(' ', '_').replace('-', '_')
                result[f'{prefix}_{safe_et}_count'] = cnt
                result[f'{prefix}_{safe_et}_ratio'] = cnt / count

            return result

        # 主队射门
        home_stats = calc_stats(home_shots, 'shot_home')
        features.update(home_stats)

        # 客队射门
        away_stats = calc_stats(away_shots, 'shot_away')
        features.update(away_stats)

        # 差值特征
        features['shot_count_diff'] = home_stats.get('shot_home_count', 0) - away_stats.get('shot_away_count', 0)
        features['shot_avg_x_diff'] = home_stats.get('shot_home_avg_x', 0) - away_stats.get('shot_away_avg_x', 0)
        features['shot_avg_y_diff'] = home_stats.get('shot_home_avg_y', 0) - away_stats.get('shot_away_avg_y', 0)
        features['shot_distance_diff'] = home_stats.get('shot_home_avg_distance', 0) - away_stats.get('shot_away_avg_distance', 0)

        # 比率特征
        total_shots = home_stats.get('shot_home_count', 0) + away_stats.get('shot_away_count', 0)
        if total_shots > 0:
            features['shot_home_ratio'] = home_stats.get('shot_home_count', 0) / total_shots
            features['shot_away_ratio'] = away_stats.get('shot_away_count', 0) / total_shots

        return features

    def _extract_momentum_features_full(self, json_data: Dict) -> Dict[str, float]:
        """完整提取动量特征 - 扩展版"""
        features = {}

        try:
            actual_data = json_data.get('l2_json', json_data)
            content = actual_data.get('content', {})
            momentum = content.get('momentum', {})
            main = momentum.get('main', {})
            data = main.get('data', [])

            if not data:
                return features

            # 解析动量值
            values = [d.get('value', 0) for d in data]
            minutes = [d.get('minute', 0) for d in data]

            if not values:
                return features

            # 基础统计
            features['momentum_mean'] = np.mean(values)
            features['momentum_std'] = np.std(values)
            features['momentum_var'] = np.var(values)
            features['momentum_min'] = np.min(values)
            features['momentum_max'] = np.max(values)
            features['momentum_range'] = np.max(values) - np.min(values)
            features['momentum_median'] = np.median(values)

            # 分段分析 (每15分钟一段)
            segments = [
                (0, 15, 'first_15'),
                (15, 30, 'second_15'),
                (30, 45, 'third_15'),
                (45, 60, 'fourth_15'),
                (60, 75, 'fifth_15'),
                (75, 90, 'sixth_15'),
            ]

            for start, end, seg_name in segments:
                seg_values = [v for i, v in enumerate(values) if minutes[i] >= start and minutes[i] < end]
                if seg_values:
                    features[f'momentum_{seg_name}_mean'] = np.mean(seg_values)
                    features[f'momentum_{seg_name}_std'] = np.std(seg_values)
                    features[f'momentum_{seg_name}_max'] = np.max(seg_values)
                    features[f'momentum_{seg_name}_min'] = np.min(seg_values)

            # 四分位分析
            n = len(values)
            q1 = values[:n//4]
            q2 = values[n//4:n//2]
            q3 = values[n//2:3*n//4]
            q4 = values[3*n//4:]

            features['momentum_q1_mean'] = np.mean(q1) if q1 else 0
            features['momentum_q2_mean'] = np.mean(q2) if q2 else 0
            features['momentum_q3_mean'] = np.mean(q3) if q3 else 0
            features['momentum_q4_mean'] = np.mean(q4) if q4 else 0

            # 动量变化率
            if len(values) > 1:
                changes = [values[i+1] - values[i] for i in range(len(values)-1)]
                features['momentum_change_mean'] = np.mean(changes)
                features['momentum_change_std'] = np.std(changes)
                features['momentum_change_max'] = np.max(changes)
                features['momentum_change_min'] = np.min(changes)

                # 正负动量时间
                positive_time = sum(1 for v in values if v > 0)
                negative_time = sum(1 for v in values if v < 0)
                neutral_time = sum(1 for v in values if v == 0)

                features['momentum_positive_ratio'] = positive_time / len(values)
                features['momentum_negative_ratio'] = negative_time / len(values)
                features['momentum_neutral_ratio'] = neutral_time / len(values)

                # 动量转换次数
                shifts = 0
                prev_sign = 1 if values[0] > 0 else (-1 if values[0] < 0 else 0)
                for v in values[1:]:
                    sign = 1 if v > 0 else (-1 if v < 0 else 0)
                    if sign != 0 and sign != prev_sign:
                        shifts += 1
                        prev_sign = sign
                features['momentum_shifts'] = shifts

        except Exception as e:
            logger.error(f"动量特征提取失败: {e}")

        return features

    def _extract_environment_features(self, json_data: Dict) -> Dict[str, float]:
        """提取环境特征"""
        features = {}

        try:
            actual_data = json_data.get('l2_json', json_data)
            general = actual_data.get('general', {})
            content = actual_data.get('content', {})

            # 比赛信息
            features['env_match_round'] = float(general.get('matchRound', 0))
            features['env_league_id'] = float(general.get('leagueId', 0))

            # 比赛时间特征
            match_time_str = general.get('matchTimeUTCDate', '')
            try:
                from datetime import datetime
                match_time = datetime.fromisoformat(match_time_str.replace('Z', '+00:00'))
                features['env_match_hour'] = float(match_time.hour)
                features['env_day_of_week'] = float(match_time.weekday())
                features['env_is_weekend'] = float(1 if match_time.weekday() >= 5 else 0)
                features['env_is_night_match'] = float(1 if match_time.hour >= 19 or match_time.hour <= 4 else 0)
            except:
                features['env_match_hour'] = 0.0
                features['env_day_of_week'] = 0.0
                features['env_is_weekend'] = 0.0
                features['env_is_night_match'] = 0.0

            # 天气
            weather = content.get('weather', {})
            features['env_weather_temp'] = float(weather.get('temperature', 0))
            features['env_weather_wind'] = float(weather.get('windSpeed', 0))
            features['env_weather_rain'] = float(weather.get('precipitation', 0))
            features['env_weather_humidity'] = float(weather.get('relativeHumidity', 0))
            features['env_cloud_cover'] = float(weather.get('cloudCover', 0))

            # 天气综合指标
            features['env_is_bad_weather'] = float(1 if features['env_weather_rain'] > 5 or features['env_weather_wind'] > 20 else 0)

            # 裁判 (从 matchFacts 获取)
            match_facts = content.get('matchFacts', {})
            referee = match_facts.get('referee', {})
            features['env_referee_name_hash'] = float(hash(str(referee.get('name', ''))) % 1000)

        except Exception as e:
            logger.error(f"环境特征提取失败: {e}")

        return features

    def _calculate_interaction_features(self, all_features: Dict) -> Dict[str, float]:
        """计算交互特征 - 扩展版"""
        features = {}

        try:
            # 射门 x 动量交互
            if 'shot_count_diff' in all_features and 'momentum_mean' in all_features:
                features['inter_shot_momentum'] = (
                    all_features['shot_count_diff'] * all_features['momentum_mean']
                )
            if 'shot_home_count' in all_features and 'momentum_first_15_mean' in all_features:
                features['inter_shot_early_momentum'] = (
                    all_features['shot_home_count'] * all_features['momentum_first_15_mean']
                )
            if 'shot_away_count' in all_features and 'momentum_last_15_mean' in all_features:
                features['inter_away_shot_late_momentum'] = (
                    all_features['shot_away_count'] * all_features['momentum_last_15_mean']
                )

            # 技术 x 环境交互
            if 'tech_expected_goals_home' in all_features and 'env_weather_temp' in all_features:
                features['inter_xg_weather'] = (
                    all_features['tech_expected_goals_home'] * all_features['env_weather_temp'] / 20
                )
            if 'tech_BallPossesion_home' in all_features and 'env_is_night_match' in all_features:
                features['inter_possession_night'] = (
                    all_features['tech_BallPossesion_home'] * all_features['env_is_night_match']
                )

            # 动量 x 环境交互
            if 'momentum_q1_mean' in all_features and 'env_match_round' in all_features:
                features['inter_early_momentum_round'] = (
                    all_features['momentum_q1_mean'] * all_features['env_match_round']
                )
            if 'momentum_positive_ratio' in all_features and 'env_weather_rain' in all_features:
                features['inter_positive_momentum_rain'] = (
                    all_features['momentum_positive_ratio'] * (1 + all_features['env_weather_rain'] / 10)
                )

            # 复合交互特征
            if 'shot_home_count' in all_features and 'tech_expected_goals_home' in all_features:
                features['inter_shot_xg_efficiency'] = (
                    all_features['tech_expected_goals_home'] / max(1, all_features['shot_home_count'])
                )
            if 'shot_away_count' in all_features and 'tech_expected_goals_away' in all_features:
                features['inter_away_shot_xg_efficiency'] = (
                    all_features['tech_expected_goals_away'] / max(1, all_features['shot_away_count'])
                )

            # 动量波动性 x 射门精度
            if 'momentum_std' in all_features and 'tech_ShotsOnTarget_home' in all_features:
                features['inter_momentum_volatility_accuracy'] = (
                    all_features['momentum_std'] * all_features['tech_ShotsOnTarget_home']
                )

            # 比赛时间 x 动量
            if 'momentum_q4_mean' in all_features and 'momentum_q1_mean' in all_features:
                features['inter_momentum_late_vs_early'] = (
                    all_features['momentum_q4_mean'] - all_features['momentum_q1_mean']
                )

            # 技术 x 技术交互 (多项式特征)
            tech_home_keys = [k for k in all_features.keys() if k.startswith('tech_') and k.endswith('_home')]
            for key in tech_home_keys[:30]:  # 扩展到前 30 个
                val = all_features.get(key)
                if isinstance(val, (int, float)) and not np.isnan(val):
                    # 平方特征
                    try:
                        features[f'{key}_squared'] = float(val) ** 2
                        # 平方根特征
                        features[f'{key}_sqrt'] = np.sqrt(abs(float(val))) if float(val) >= 0 else 0
                    except:
                        pass

            # 射门多项式特征
            shot_keys = ['shot_home_count', 'shot_away_count', 'shot_avg_distance_diff',
                        'shot_home_avg_distance', 'shot_away_avg_distance']
            for key in shot_keys:
                if key in all_features:
                    val = all_features.get(key)
                    if isinstance(val, (int, float)) and not np.isnan(val):
                        try:
                            features[f'{key}_squared'] = float(val) ** 2
                            features[f'{key}_log'] = np.log(abs(float(val)) + 1)
                        except:
                            pass

            # 动量多项式特征
            momentum_keys = ['momentum_mean', 'momentum_std', 'momentum_range', 'momentum_var']
            for key in momentum_keys:
                if key in all_features:
                    val = all_features.get(key)
                    if isinstance(val, (int, float)) and not np.isnan(val):
                        try:
                            features[f'{key}_squared'] = float(val) ** 2
                            features[f'{key}_sqrt'] = np.sqrt(abs(float(val))) if float(val) >= 0 else 0
                        except:
                            pass

            # 环境多项式特征
            env_keys = ['env_weather_temp', 'env_weather_wind', 'env_weather_humidity']
            for key in env_keys:
                if key in all_features:
                    val = all_features.get(key)
                    if isinstance(val, (int, float)) and not np.isnan(val):
                        try:
                            features[f'{key}_squared'] = float(val) ** 2
                        except:
                            pass

            # 技术统计派生特征 (xG 相关)
            xg_keys = [k for k in all_features.keys() if 'xg' in k.lower()]
            for key in xg_keys[:10]:
                val = all_features.get(key)
                if isinstance(val, (int, float)) and not np.isnan(val) and val > 0:
                    try:
                        features[f'{key}_log'] = np.log(float(val) + 1)
                    except:
                        pass

        except Exception as e:
            logger.error(f"交互特征计算失败: {e}")

        return features

    # 辅助函数
    def _parse_stat_value(self, value: Any) -> float:
        """解析统计值"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # 移除百分号和非数字字符
            cleaned = ''.join(c for c in value if c.isdigit() or c == '.' or c == '-')
            return float(cleaned) if cleaned else 0.0
        return 0.0

    def _safe_subtract(self, a: float, b: float) -> float:
        return a - b if not np.isnan(a) and not np.isnan(b) else np.nan

    def _safe_add(self, a: float, b: float) -> float:
        return a + b if not np.isnan(a) and not np.isnan(b) else np.nan

    def _safe_divide(self, a: float, b: float) -> float:
        return a / b if not np.isnan(a) and not np.isnan(b) and b != 0 else np.nan

    def _extract_percentage(self, value: Any) -> Optional[float]:
        """从字符串中提取百分比"""
        if isinstance(value, str) and '%' in value:
            try:
                return float(value.replace('%', ''))
            except:
                pass
        return None

    def get_feature_summary(self) -> Dict:
        return self.feature_counts.copy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("V33.0 Enhanced Feature Miner Ready")
