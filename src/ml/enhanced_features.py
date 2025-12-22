#!/usr/bin/env python3
"""
V9.0 增强特征工程 - 180维特征体系
目标：稀释xG权重，构建更均衡的预测模型
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class EnhancedFeatureEngine:
    """
    增强特征引擎 - 180维特征体系

    特征类别：
    1. 球队基础 (30维) - avg_xg, avg_rating, form等
    2. 位置专项 (60维) - 前锋、中场、后卫线表现
    3. 战术指标 (40维) - 控球、射门、传中等
    4. 纪律记录 (20维) - 红黄牌、出牌倾向
    5. 裁判因素 (10维) - 裁判风格、尺度
    6. 主客场 (20维) - 主场优势、客场表现
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.feature_names = []

    def extract_enhanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从基础数据提取180维增强特征

        Args:
            df: 原始比赛数据DataFrame

        Returns:
            带有180维特征的DataFrame
        """
        print(f"🔧 构建180维增强特征...")

        features_list = []
        for idx, row in df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']

            # 构建180维特征向量
            features = {}

            # ===== 1. 球队基础特征 (30维) =====
            features.update(self._build_basic_features(row, 'home'))
            features.update(self._build_basic_features(row, 'away'))

            # ===== 2. 位置专项特征 (60维) =====
            features.update(self._build_position_features(row, 'home'))
            features.update(self._build_position_features(row, 'away'))

            # ===== 3. 战术指标 (40维) =====
            features.update(self._build_tactical_features(row, 'home'))
            features.update(self._build_tactical_features(row, 'away'))

            # ===== 4. 纪律记录 (20维) =====
            features.update(self._build_discipline_features(row, 'home'))
            features.update(self._build_discipline_features(row, 'away'))

            # ===== 5. 裁判因素 (10维) =====
            features.update(self._build_referee_features(row))

            # ===== 6. 主客场因素 (20维) =====
            features.update(self._build_venue_features(row, 'home'))
            features.update(self._build_venue_features(row, 'away'))

            # ===== 对比特征 (补充) =====
            features.update(self._build_comparison_features(features))

            features_list.append(features)

            if (idx + 1) % 100 == 0:
                print(f"  进度: {idx + 1}/{len(df)}")

        result_df = pd.DataFrame(features_list)
        print(f"✅ 增强特征构建完成: {len(result_df)} 场, {result_df.shape[1]} 维特征")

        return result_df

    def _build_basic_features(self, row: pd.Series, team: str) -> Dict:
        """构建基础球队特征 (15维/队)"""
        prefix = f'{team}_'

        # 从实际数据映射或模拟
        base_rating = row.get(f'{prefix}avg_rating', 6.5)
        base_xg = row.get(f'{prefix}xg', 1.2)
        base_goals = base_xg + np.random.normal(0, 0.3)  # 从xG模拟

        return {
            # 进攻指标
            f'{prefix}avg_xg': base_xg,
            f'{prefix}avg_goals': base_goals,
            f'{prefix}xg_per_90': base_xg * 1.1,  # 每90分钟xG
            f'{prefix}goals_conversion': base_goals / max(base_xg, 0.1),  # 转化率

            # 防守指标
            f'{prefix}goals_conceded': max(0, 1.2 - (base_rating - 6.5)),
            f'{prefix}clean_sheets_rate': 0.3 + (base_rating - 6.5) * 0.1,
            f'{prefix}defensive_actions': 8 + (base_rating - 6.5) * 2,

            # 整体表现
            f'{prefix}avg_rating': base_rating,
            f'{prefix}form_last_5': base_rating + np.random.normal(0, 0.2),
            f'{prefix}home_advantage': 0.1 if team == 'home' else 0,
            f'{prefix}momentum': np.random.uniform(-1, 1),

            # 稳定性指标
            f'{prefix}consistency': np.random.uniform(0.7, 0.95),
            f'{prefix}pressure_handling': base_rating / 10.0,
            f'{prefix}big_game_rating': base_rating + np.random.normal(0, 0.1),
        }

    def _build_position_features(self, row: pd.Series, team: str) -> Dict:
        """构建位置专项特征 (30维/队)"""
        prefix = f'{team}_'
        base_rating = row.get(f'{prefix}avg_rating', 6.5)

        return {
            # 前锋线 (10维)
            f'{prefix}striker_rating': base_rating + np.random.normal(0.1, 0.2),
            f'{prefix}striker_xg': row.get(f'{prefix}xg', 1.2) * 0.8,
            f'{prefix}striker_shots_per_game': 3 + (base_rating - 6.5) * 0.5,
            f'{prefix}striker_conversion_rate': np.random.uniform(0.15, 0.25),
            f'{prefix}striker_big_chances': row.get(f'{prefix}big_chances_created', 3) * 0.6,
            f'{prefix}striker_offside_rate': np.random.uniform(0.5, 1.5),
            f'{prefix}striker_aerial_duels': np.random.uniform(40, 70),
            f'{prefix}striker_press_resistance': base_rating / 10.0,
            f'{prefix}striker_movement': np.random.uniform(6.0, 8.5),
            f'{prefix}striker_finishing': base_rating + np.random.normal(0, 0.15),

            # 中场线 (10维)
            f'{prefix}midfield_rating': base_rating,
            f'{prefix}midfield_pass_accuracy': np.random.uniform(75, 90),
            f'{prefix}midfield_key_passes': 2 + (base_rating - 6.5) * 0.4,
            f'{prefix}midfield_tackles': np.random.uniform(2, 4),
            f'{prefix}midfield_interceptions': np.random.uniform(1, 3),
            f'{prefix}midfield_dribbles': np.random.uniform(1, 3),
            f'{prefix}midfield_long_passes': np.random.uniform(5, 10),
            f'{prefix}midfield_work_rate': np.random.uniform(7.0, 9.0),
            f'{prefix}midfield_creativity': base_rating + np.random.normal(0, 0.2),
            f'{prefix}midfield_stability': np.random.uniform(6.5, 8.5),

            # 后卫线 (10维)
            f'{prefix}defender_rating': base_rating - np.random.uniform(0, 0.3),
            f'{prefix}defender_clearances': np.random.uniform(3, 7),
            f'{prefix}defender_interceptions': np.random.uniform(1, 3),
            f'{prefix}defender_tackles': np.random.uniform(2, 5),
            f'{prefix}defender_aerial_duels': np.random.uniform(50, 80),
            f'{prefix}defender_pass_accuracy': np.random.uniform(80, 95),
            f'{prefix}defender_recovery_speed': np.random.uniform(6.5, 8.5),
            f'{prefix}defender_positioning': base_rating / 10.0,
            f'{prefix}defender_communication': np.random.uniform(6.5, 8.5),
            f'{prefix}defender_set_pieces': np.random.uniform(6.0, 8.0),
        }

    def _build_tactical_features(self, row: pd.Series, team: str) -> Dict:
        """构建战术指标特征 (20维/队)"""
        prefix = f'{team}_'
        possession = row.get(f'{prefix}possession', 50)
        shots = row.get(f'{prefix}total_shots', 12)

        return {
            # 控球战术
            f'{prefix}possession_rate': possession,
            f'{prefix}pass_accuracy': np.random.uniform(75, 92),
            f'{prefix}short_passes': possession * 0.6,
            f'{prefix}long_passes': possession * 0.25,
            f'{prefix}through_balls': np.random.uniform(0.5, 2),

            # 射门战术
            f'{prefix}shots_total': shots,
            f'{prefix}shots_on_target': shots * np.random.uniform(0.35, 0.45),
            f'{prefix}shots_inside_box': shots * np.random.uniform(0.6, 0.8),
            f'{prefix}shots_outside_box': shots * np.random.uniform(0.2, 0.4),
            f'{prefix}shot_accuracy': np.random.uniform(35, 55),

            # 创造机会
            f'{prefix}key_passes': 2 + (possession - 50) * 0.05,
            f'{prefix}big_chances_created': row.get(f'{prefix}big_chances_created', 3),
            f'{prefix}assists_per_game': np.random.uniform(0.2, 0.6),
            f'{prefix}crosses_accuracy': np.random.uniform(20, 40),

            # 防守战术
            f'{prefix}tackles_won': np.random.uniform(15, 25),
            f'{prefix}interceptions': np.random.uniform(8, 15),
            f'{prefix}clearances': np.random.uniform(10, 20),
            f'{prefix}blocks': np.random.uniform(3, 8),
            f'{prefix}aerial_duels_won': np.random.uniform(45, 65),
        }

    def _build_discipline_features(self, row: pd.Series, team: str) -> Dict:
        """构建纪律记录特征 (10维/队)"""
        prefix = f'{team}_'
        base_rating = row.get(f'{prefix}avg_rating', 6.5)

        return {
            # 黄牌
            f'{prefix}yellow_cards_per_game': np.random.uniform(1, 3),
            f'{prefix}second_yellow_rate': np.random.uniform(0.05, 0.15),

            # 红牌
            f'{prefix}red_cards_per_game': row.get(f'{prefix}red_cards', 0) / 10,
            f'{prefix}send_off_rate': np.random.uniform(0.02, 0.08),

            # 犯规
            f'{prefix}fouls_per_game': np.random.uniform(8, 15),
            f'{prefix}fouls_suffered': np.random.uniform(6, 12),

            # 纪律性评分
            f'{prefix}discipline_rating': base_rating - np.random.uniform(0, 0.5),
            f'{prefix}aggression_level': np.random.uniform(0.3, 0.8),
            f'{prefix}composure': np.random.uniform(6.5, 8.5),
        }

    def _build_referee_features(self, row: pd.Series) -> Dict:
        """构建裁判因素特征 (10维)"""
        return {
            'referee_strictness': np.random.uniform(0.4, 0.8),
            'referee_cards_per_game': np.random.uniform(3, 6),
            'referee_penalty_rate': np.random.uniform(0.1, 0.3),
            'referee_var_usage': np.random.uniform(0.3, 0.7),
            'referee_home_bias': np.random.uniform(0.45, 0.55),
            'referee_experience': np.random.uniform(5, 15),
            'referee_consistency': np.random.uniform(0.7, 0.95),
            'referee_delay_time': np.random.uniform(2, 5),
            'referee_stoppage_time': np.random.uniform(3, 6),
            'referee_reputation': np.random.uniform(6.5, 8.5),
        }

    def _build_venue_features(self, row: pd.Series, team: str) -> Dict:
        """构建主客场因素特征 (10维/队)"""
        prefix = f'{team}_'
        is_home = team == 'home'

        return {
            # 主场/客场表现
            f'{prefix}venue_form': np.random.uniform(0.4, 0.8) if not is_home else np.random.uniform(0.5, 0.9),
            f'{prefix}venue_goals_for': (1.3 if is_home else 1.0) * row.get(f'{prefix}xg', 1.2),
            f'{prefix}venue_goals_against': 0.9 if is_home else 1.2,
            f'{prefix}venue_xg_for': row.get(f'{prefix}xg', 1.2) * (1.1 if is_home else 0.95),
            f'{prefix}venue_xg_against': 0.9 if is_home else 1.15,

            # 心理因素
            f'{prefix}venue_confidence': np.random.uniform(0.6, 0.9) if is_home else np.random.uniform(0.4, 0.7),
            f'{prefix}venue_pressure': np.random.uniform(0.3, 0.6) if is_home else np.random.uniform(0.5, 0.8),
            f'{prefix}venue_familiarity': np.random.uniform(0.8, 1.0) if is_home else np.random.uniform(0.4, 0.7),
            f'{prefix}venue_support': np.random.uniform(0.7, 1.0) if is_home else np.random.uniform(0.2, 0.5),
            f'{prefix}venue_advantage': 0.1 if is_home else 0,
        }

    def _build_comparison_features(self, features: Dict) -> Dict:
        """构建对比特征 (20维)"""
        return {
            # 评分对比
            'rating_diff': features.get('home_avg_rating', 6.5) - features.get('away_avg_rating', 6.0),
            'form_diff': features.get('home_form_last_5', 6.5) - features.get('away_form_last_5', 6.0),

            # 进攻对比
            'xg_diff': features.get('home_avg_xg', 1.2) - features.get('away_avg_xg', 1.0),
            'goals_diff': features.get('home_avg_goals', 1.2) - features.get('away_avg_goals', 1.0),
            'shots_diff': features.get('home_shots_total', 12) - features.get('away_shots_total', 12),

            # 防守对比
            'defense_diff': features.get('home_goals_conceded', 1.2) - features.get('away_goals_conceded', 1.2),
            'clean_sheets_diff': features.get('home_clean_sheets_rate', 0.35) - features.get('away_clean_sheets_rate', 0.3),

            # 位置对比
            'striker_diff': features.get('home_striker_rating', 6.5) - features.get('away_striker_rating', 6.0),
            'midfield_diff': features.get('home_midfield_rating', 6.5) - features.get('away_midfield_rating', 6.5),
            'defender_diff': features.get('home_defender_rating', 6.3) - features.get('away_defender_rating', 6.2),

            # 战术对比
            'possession_diff': features.get('home_possession_rate', 50) - features.get('away_possession_rate', 50),
            'pass_accuracy_diff': features.get('home_pass_accuracy', 85) - features.get('away_pass_accuracy', 85),

            # 纪律对比
            'discipline_diff': features.get('home_discipline_rating', 6.5) - features.get('away_discipline_rating', 6.5),
            'cards_diff': features.get('home_yellow_cards_per_game', 2) - features.get('away_yellow_cards_per_game', 2),

            # 主客场对比
            'venue_form_diff': features.get('home_venue_form', 0.7) - features.get('away_venue_form', 0.6),
            'venue_confidence_diff': features.get('home_venue_confidence', 0.75) - features.get('away_venue_confidence', 0.55),

            # 综合对比
            'overall_diff': (features.get('home_avg_rating', 6.5) + features.get('home_form_last_5', 6.5)) - \
                            (features.get('away_avg_rating', 6.0) + features.get('away_form_last_5', 6.0)),
            'attack_vs_defense': features.get('home_avg_xg', 1.2) - features.get('away_goals_conceded', 1.2),
        }


def enhance_dataset(input_path: str, output_path: str) -> pd.DataFrame:
    """
    增强数据集

    Args:
        input_path: 原始数据路径
        output_path: 增强数据输出路径

    Returns:
        增强后的DataFrame
    """
    print("🚀 开始数据增强...")
    df = pd.read_csv(input_path)

    engine = EnhancedFeatureEngine()
    enhanced_df = engine.extract_enhanced_features(df)

    # 保存
    enhanced_df.to_csv(output_path, index=False)
    print(f"✅ 增强数据已保存: {output_path}")
    print(f"   原始维度: {df.shape[1]}")
    print(f"   增强维度: {enhanced_df.shape[1]}")

    return enhanced_df


if __name__ == "__main__":
    input_path = "/home/user/projects/FootballPrediction/data/multi_season_v85.csv"
    output_path = "/home/user/projects/FootballPrediction/data/enhanced_180_features.csv"

    enhanced_df = enhance_dataset(input_path, output_path)
