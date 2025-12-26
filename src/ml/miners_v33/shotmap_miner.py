#!/usr/bin/env python3
"""
V33.0 Shotmap Miner - 射门质量分析器
====================================
从 content.shotmap.shots 中提取高价值射门维度
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ShotmapFeatures:
    """射门特征数据类"""
    # 基础统计
    total_shots_home: int
    total_shots_away: int
    shots_on_target_home: int
    shots_on_target_away: int

    # 射门质量指标
    avg_shot_distance_home: float
    avg_shot_distance_away: float
    big_chances_created_home: int
    big_chances_created_away: int
    big_chances_missed_home: int
    big_chances_missed_away: int

    # 射门类型分布
    header_shot_ratio_home: float
    header_shot_ratio_away: float
    left_foot_shot_ratio_home: float
    left_foot_shot_ratio_away: float
    right_foot_shot_ratio_home: float
    right_foot_shot_ratio_away: float

    # 射门位置热区
    shots_inside_box_home: int
    shots_inside_box_away: int
    shots_outside_box_home: int
    shots_outside_box_away: int

    # xG 相关
    total_xg_home: float
    total_xg_away: float
    xg_per_shot_home: float
    xg_per_shot_away: float
    post_shot_xg_home: float
    post_shot_xg_away: float

    # 特殊情况
    own_goals_home: int
    own_goals_away: int


class ShotmapMiner:
    """
    射门质量分析器

    核心功能:
    1. 射门距离分析 - 平均射门距离反映渗透能力
    2. 大机会创造与错失 - big chances 统计
    3. 射门类型分布 - 头球/左右脚占比
    4. xG 精确分析 - 预期进球与实际对比
    """

    def __init__(self):
        """初始化射门采矿器"""
        self.shot_data = []

    def extract_features(self, json_data: Dict) -> Optional[ShotmapFeatures]:
        """
        从 FotMob JSON 中提取射门特征

        Args:
            json_data: FotMob API 响应数据

        Returns:
            ShotmapFeatures 或 None
        """
        try:
            # 提取 shotmap 数据
            content = json_data.get('content', {})
            shotmap = content.get('shotmap', {})

            # 兼容不同版本的 API 结构
            shots_list = shotmap.get('shots', [])

            if not shots_list:
                logger.debug("没有射门数据")
                return None

            # 分离主客队射门
            home_shots = []
            away_shots = []

            for shot in shots_list:
                # 判断是主队还是客队的射门
                is_home_shot = self._is_home_team_shot(shot)

                shot_data = self._parse_single_shot(shot)
                if shot_data:
                    if is_home_shot:
                        home_shots.append(shot_data)
                    else:
                        away_shots.append(shot_data)

            # 计算特征
            features = self._calculate_shotmap_features(home_shots, away_shots)
            return features

        except Exception as e:
            logger.error(f"射门特征提取失败: {e}")
            return None

    def _is_home_team_shot(self, shot: Dict) -> bool:
        """
        判断射门是否来自主队

        Args:
            shot: 单次射门数据

        Returns:
            bool: True=主队射门, False=客队射门
        """
        try:
            # 根据 team 判断
            team = shot.get('team', {})

            # team 可能是 dict 或 str
            if isinstance(team, dict):
                team_id = team.get('id', 0)
                is_home = team.get('isHome', False)
                # 优先使用 isHome 标志
                if is_home is not None:
                    return is_home
            elif isinstance(team, str):
                # 如果是字符串，判断是否包含 "home"
                return 'home' in team.lower()

            # 根据 shotType 判断 (备用)
            shot_type = shot.get('shotType', {})
            if isinstance(shot_type, dict):
                team_id = shot_type.get('id', 0)
                return team_id < 10000  # 简化判断

            # 默认: 根据其他字段判断
            # 检查是否是主场射门
            return shot.get('isHomeShot', False)

        except Exception:
            # 默认为主队射门
            return True

    def _parse_single_shot(self, shot: Dict) -> Optional[Dict]:
        """
        解析单次射门数据

        Args:
            shot: 射门数据

        Returns:
            解析后的射门信息字典
        """
        try:
            return {
                'distance': shot.get('distanceMeters', 0),
                'is_on_target': shot.get('isOnTarget', False),
                'is_big_chance': shot.get('isBigChance', False),
                'is_goal': shot.get('isGoal', False),
                'shot_type': shot.get('shotType', 'unknown'),
                'body_part': shot.get('bodyPart', 'unknown'),
                'is_inside_box': shot.get('isInsideBox', False),
                'xg': shot.get('expectedGoals', 0.0),
                'post_shot_xg': shot.get('postShotExpectedGoals', 0.0),
                'is_own_goal': shot.get('isOwnGoal', False),
                'minute': shot.get('minute', 0),
            }
        except Exception as e:
            logger.debug(f"解析射门数据失败: {e}")
            return None

    def _calculate_shotmap_features(self, home_shots: List[Dict], away_shots: List[Dict]) -> ShotmapFeatures:
        """
        计算射门特征

        Args:
            home_shots: 主队射门列表
            away_shots: 客队射门列表

        Returns:
            ShotmapFeatures 特征对象
        """
        def calc_metrics(shots: List[Dict]) -> Dict:
            """计算单队射门指标"""
            if not shots:
                return {
                    'total': 0,
                    'on_target': 0,
                    'avg_distance': 0.0,
                    'big_chances': 0,
                    'big_missed': 0,
                    'header_ratio': 0.0,
                    'left_foot_ratio': 0.0,
                    'right_foot_ratio': 0.0,
                    'inside_box': 0,
                    'outside_box': 0,
                    'total_xg': 0.0,
                    'xg_per_shot': 0.0,
                    'post_shot_xg': 0.0,
                    'own_goals': 0,
                }

            total = len(shots)
            on_target = sum(1 for s in shots if s.get('is_on_target'))
            distances = [s.get('distance', 0) for s in shots if s.get('distance', 0) > 0]
            avg_distance = np.mean(distances) if distances else 0.0

            big_chances = sum(1 for s in shots if s.get('is_big_chance'))
            big_missed = sum(1 for s in shots if s.get('is_big_chance') and not s.get('is_goal'))

            headers = sum(1 for s in shots if s.get('body_part') == 'head')
            left_foot = sum(1 for s in shots if s.get('body_part') == 'left')
            right_foot = sum(1 for s in shots if s.get('body_part') == 'right')

            total_shots_with_bodypart = headers + left_foot + right_foot
            header_ratio = headers / total_shots_with_bodypart if total_shots_with_bodypart > 0 else 0.0
            left_foot_ratio = left_foot / total_shots_with_bodypart if total_shots_with_bodypart > 0 else 0.0
            right_foot_ratio = right_foot / total_shots_with_bodypart if total_shots_with_bodypart > 0 else 0.0

            inside_box = sum(1 for s in shots if s.get('is_inside_box'))
            outside_box = total - inside_box

            total_xg = sum(s.get('xg', 0.0) for s in shots)
            xg_per_shot = total_xg / total if total > 0 else 0.0
            post_shot_xg = sum(s.get('post_shot_xg', 0.0) for s in shots)

            own_goals = sum(1 for s in shots if s.get('is_own_goal'))

            return {
                'total': total,
                'on_target': on_target,
                'avg_distance': avg_distance,
                'big_chances': big_chances,
                'big_missed': big_missed,
                'header_ratio': header_ratio,
                'left_foot_ratio': left_foot_ratio,
                'right_foot_ratio': right_foot_ratio,
                'inside_box': inside_box,
                'outside_box': outside_box,
                'total_xg': total_xg,
                'xg_per_shot': xg_per_shot,
                'post_shot_xg': post_shot_xg,
                'own_goals': own_goals,
            }

        home_metrics = calc_metrics(home_shots)
        away_metrics = calc_metrics(away_shots)

        return ShotmapFeatures(
            # 基础统计
            total_shots_home=home_metrics['total'],
            total_shots_away=away_metrics['total'],
            shots_on_target_home=home_metrics['on_target'],
            shots_on_target_away=away_metrics['on_target'],

            # 射门质量
            avg_shot_distance_home=home_metrics['avg_distance'],
            avg_shot_distance_away=away_metrics['avg_distance'],
            big_chances_created_home=home_metrics['big_chances'],
            big_chances_created_away=away_metrics['big_chances'],
            big_chances_missed_home=home_metrics['big_missed'],
            big_chances_missed_away=away_metrics['big_missed'],

            # 射门类型
            header_shot_ratio_home=home_metrics['header_ratio'],
            header_shot_ratio_away=away_metrics['header_ratio'],
            left_foot_shot_ratio_home=home_metrics['left_foot_ratio'],
            left_foot_shot_ratio_away=away_metrics['left_foot_ratio'],
            right_foot_shot_ratio_home=home_metrics['right_foot_ratio'],
            right_foot_shot_ratio_away=away_metrics['right_foot_ratio'],

            # 射门位置
            shots_inside_box_home=home_metrics['inside_box'],
            shots_inside_box_away=away_metrics['inside_box'],
            shots_outside_box_home=home_metrics['outside_box'],
            shots_outside_box_away=away_metrics['outside_box'],

            # xG
            total_xg_home=home_metrics['total_xg'],
            total_xg_away=away_metrics['total_xg'],
            xg_per_shot_home=home_metrics['xg_per_shot'],
            xg_per_shot_away=away_metrics['xg_per_shot'],
            post_shot_xg_home=home_metrics['post_shot_xg'],
            post_shot_xg_away=away_metrics['post_shot_xg'],

            # 乌龙球
            own_goals_home=home_metrics['own_goals'],
            own_goals_away=away_metrics['own_goals'],
        )

    def to_feature_dict(self, features: ShotmapFeatures) -> Dict[str, float]:
        """
        将 ShotmapFeatures 转换为特征字典

        Args:
            features: 射门特征对象

        Returns:
            特征字典
        """
        if not features:
            return {}

        return {
            'shot_total_home': features.total_shots_home,
            'shot_total_away': features.total_shots_away,
            'shot_total_diff': features.total_shots_home - features.total_shots_away,
            'shot_on_target_home': features.shots_on_target_home,
            'shot_on_target_away': features.shots_on_target_away,
            'shot_on_target_diff': features.shots_on_target_home - features.shots_on_target_away,
            'shot_avg_distance_home': features.avg_shot_distance_home,
            'shot_avg_distance_away': features.avg_shot_distance_away,
            'shot_distance_diff': features.avg_shot_distance_home - features.avg_shot_distance_away,
            'shot_big_chances_home': features.big_chances_created_home,
            'shot_big_chances_away': features.big_chances_created_away,
            'shot_big_chances_diff': features.big_chances_created_home - features.big_chances_created_away,
            'shot_big_missed_home': features.big_chances_missed_home,
            'shot_big_missed_away': features.big_chances_missed_away,
            'shot_header_ratio_home': features.header_shot_ratio_home,
            'shot_header_ratio_away': features.header_shot_ratio_away,
            'shot_header_ratio_diff': features.header_shot_ratio_home - features.header_shot_ratio_away,
            'shot_inside_box_home': features.shots_inside_box_home,
            'shot_inside_box_away': features.shots_inside_box_away,
            'shot_inside_box_diff': features.shots_inside_box_home - features.shots_inside_box_away,
            'shot_xg_total_home': features.total_xg_home,
            'shot_xg_total_away': features.total_xg_away,
            'shot_xg_diff': features.total_xg_home - features.total_xg_away,
            'shot_xg_per_shot_home': features.xg_per_shot_home,
            'shot_xg_per_shot_away': features.xg_per_shot_away,
            'shot_xg_efficiency_diff': features.xg_per_shot_home - features.xg_per_shot_away,
        }
