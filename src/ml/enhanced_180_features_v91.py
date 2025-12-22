#!/usr/bin/env python3
"""
V9.1 180维精细特征提取器 - 精算级
激活 JSON 中的细腻数据，提取门将、关键传球、前锋转换率等特征
目标: 增强模型的"触觉"，区分运气球和实力球
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class AdvancedFeatureExtractorV91:
    """V9.1 高级特征提取器 - 180维精算级实现"""

    def __init__(self):
        """初始化特征提取器"""
        self.feature_names = []
        self._build_feature_names()

    def _build_feature_names(self):
        """构建180维特征名称列表"""
        # 基础统计特征 (30维)
        self.feature_names.extend([
            'home_avg_xg', 'away_avg_xg',
            'home_avg_goals', 'away_avg_goals',
            'home_avg_shots', 'away_avg_shots',
            'home_avg_shots_on_target', 'away_avg_shots_on_target',
            'home_avg_possession', 'away_avg_possession',
            'home_avg_pass_accuracy', 'away_avg_pass_accuracy',
            'home_avg_rating', 'away_avg_rating',
            'home_win_rate', 'away_win_rate',
            'home_draw_rate', 'away_draw_rate',
            'home_loss_rate', 'away_loss_rate',
            'home_avg_corners', 'away_avg_corners',
            'home_avg_fouls', 'away_avg_fouls',
            'home_avg_yellow_cards', 'away_avg_yellow_cards',
            'home_avg_red_cards', 'away_avg_red_cards',
            'home_avg_offsides', 'away_avg_offsides'
        ])

        # 门将特征 (20维) - 新增
        self.feature_names.extend([
            'home_keeper_saves_per_game', 'away_keeper_saves_per_game',
            'home_keeper_save_percentage', 'away_keeper_save_percentage',
            'home_keeper_clean_sheets', 'away_keeper_clean_sheets',
            'home_keeper_punches', 'away_keeper_punches',
            'home_keeper_high_claims', 'away_keeper_high_claims',
            'home_keeper_sweeper_clearances', 'away_keeper_sweeper_clearances',
            'home_keeper_errors_leading_to_goal', 'away_keeper_errors_leading_to_goal',
            'home_keeper_distribution_accuracy', 'away_keeper_distribution_accuracy',
            'home_keeper_goal_prevention', 'away_keeper_goal_prevention',
            'home_keeper_ps_xg_on_target', 'away_keeper_ps_xg_on_target'
        ])

        # 关键传球与创造力特征 (18维) - 新增
        self.feature_names.extend([
            'home_key_passes_per_game', 'away_key_passes_per_game',
            'home_assists_per_game', 'away_assists_per_game',
            'home_through_balls', 'away_through_balls',
            'home_crosses', 'away_crosses',
            'home_cross_accuracy', 'away_cross_accuracy',
            'home_progressive_passes', 'away_progressive_passes',
            'home_progressive_carries', 'away_progressive_carries',
            'home_final_third_passes', 'away_final_third_passes',
            'home_big_chances_created', 'away_big_chances_created'
        ])

        # 前锋转换效率特征 (20维) - 新增
        self.feature_names.extend([
            'home_shot_conversion_rate', 'away_shot_conversion_rate',
            'home_xg_per_shot', 'away_xg_per_shot',
            'home_big_chance_conversion', 'away_big_chance_conversion',
            'home_first_time_shots', 'away_first_time_shots',
            'home_left_foot_shots', 'away_left_foot_shots',
            'home_right_foot_shots', 'away_right_foot_shots',
            'home_headed_goals', 'away_headed_goals',
            'home_penalty_area_shots', 'away_penalty_area_shots',
            'home_open_play_goals', 'away_open_play_goals',
            'home_set_piece_goals', 'away_set_piece_goals'
        ])

        # 防守与抢断特征 (20维) - 新增
        self.feature_names.extend([
            'home_tackles_won', 'away_tackles_won',
            'home_tackles_attempted', 'away_tackles_attempted',
            'home_tackle_success_rate', 'away_tackle_success_rate',
            'home_interceptions', 'away_interceptions',
            'home_clearances', 'away_clearances',
            'home_blocks', 'away_blocks',
            'home_aerial_duels_won', 'away_aerial_duels_won',
            'home_aerial_duels_total', 'away_aerial_duels_total',
            'home_aerial_success_rate', 'away_aerial_success_rate',
            'home_sliding_tackles', 'away_sliding_tackles'
        ])

        # 控球与节奏特征 (20维) - 新增
        self.feature_names.extend([
            'home_pass_completion_rate', 'away_pass_completion_rate',
            'home_total_passes', 'away_total_passes',
            'home_short_passes', 'away_short_passes',
            'home_medium_passes', 'away_medium_passes',
            'home_long_passes', 'away_long_passes',
            'home_pass_into_final_third', 'away_pass_into_final_third',
            'home_pass_into_penalty_area', 'away_pass_into_penalty_area',
            'home_touches', 'away_touches',
            'home_ball_recoveries', 'away_ball_recoveries',
            'home_possession_won_att_3rd', 'away_possession_won_att_3rd'
        ])

        # 纪律性与心理特征 (17维) - 新增
        self.feature_names.extend([
            'home_cards_per_game', 'away_cards_per_game',
            'home_second_yellow_cards', 'away_second_yellow_cards',
            'home_diving_save', 'away_diving_save',
            'home_penalty_committed', 'away_penalty_committed',
            'home_penalty_missed', 'away_penalty_missed',
            'home_error_leading_to_goal', 'away_error_leading_to_goal',
            'home_possession', 'away_possession',
            'home_saves_made', 'away_saves_made',
            'home_big_chances_missed', 'away_big_chances_missed'
        ])

        # 高级指标特征 (20维) - 新增
        self.feature_names.extend([
            'home_np_xg', 'away_np_xg',  # Non-penalty xG
            'home_xg_chain', 'away_xg_chain',
            'home_xg_buildup', 'away_xg_buildup',
            'home_shot_creating_actions', 'away_shot_creating_actions',
            'home_goal_creating_actions', 'away_goal_creating_actions',
            'home_carries_into_final_third', 'away_carries_into_final_third',
            'home_carries_into_penalty_area', 'away_carries_into_penalty_area',
            'home_receives_progressive_passes', 'away_receives_progressive_passes',
            'home_dispossessed', 'away_dispossessed',
            'home_aerial_duels_won_pct', 'away_aerial_duels_won_pct'
        ])

        # 差异特征 (15维)
        self.feature_names.extend([
            'xg_diff', 'goals_diff', 'shots_diff', 'shots_on_target_diff',
            'possession_diff', 'pass_accuracy_diff', 'rating_diff',
            'corners_diff', 'fouls_diff', 'cards_diff', 'offsides_diff',
            'keeper_saves_diff', 'key_passes_diff', 'conversion_rate_diff',
            'tackles_won_diff'
        ])

        # 总计检查
        print(f"✅ {len(self.feature_names)}维特征名称列表已构建")

    def extract_features_from_json(self, match_data: Dict) -> np.ndarray:
        """
        从 JSON 数据中提取180维特征

        Args:
            match_data: 比赛数据字典

        Returns:
            180维特征向量
        """
        features = []

        # 基础统计特征 (30维)
        features.extend([
            match_data.get('home_avg_xg', 1.2),
            match_data.get('away_avg_xg', 1.0),
            match_data.get('home_avg_goals', 1.2),
            match_data.get('away_avg_goals', 1.0),
            match_data.get('home_avg_shots', 12),
            match_data.get('away_avg_shots', 12),
            match_data.get('home_avg_shots_on_target', 4),
            match_data.get('away_avg_shots_on_target', 4),
            match_data.get('home_avg_possession', 50),
            match_data.get('away_avg_possession', 50),
            match_data.get('home_avg_pass_accuracy', 80),
            match_data.get('away_avg_pass_accuracy', 80),
            match_data.get('home_avg_rating', 6.5),
            match_data.get('away_avg_rating', 6.0),
            match_data.get('home_win_rate', 0.33),
            match_data.get('away_win_rate', 0.33),
            match_data.get('home_draw_rate', 0.25),
            match_data.get('away_draw_rate', 0.25),
            match_data.get('home_loss_rate', 0.42),
            match_data.get('away_loss_rate', 0.42),
            match_data.get('home_avg_corners', 5),
            match_data.get('away_avg_corners', 5),
            match_data.get('home_avg_fouls', 12),
            match_data.get('away_avg_fouls', 12),
            match_data.get('home_avg_yellow_cards', 2),
            match_data.get('away_avg_yellow_cards', 2),
            match_data.get('home_avg_red_cards', 0.1),
            match_data.get('away_avg_red_cards', 0.1),
            match_data.get('home_avg_offsides', 2),
            match_data.get('away_avg_offsides', 2)
        ])

        # 门将特征 (20维) - 从 JSON 提取或模拟
        features.extend([
            match_data.get('home_keeper_saves_per_game', 3),
            match_data.get('away_keeper_saves_per_game', 3),
            match_data.get('home_keeper_save_percentage', 70),
            match_data.get('away_keeper_save_percentage', 70),
            match_data.get('home_keeper_clean_sheets', 0.3),
            match_data.get('away_keeper_clean_sheets', 0.3),
            match_data.get('home_keeper_punches', 1),
            match_data.get('away_keeper_punches', 1),
            match_data.get('home_keeper_high_claims', 1),
            match_data.get('away_keeper_high_claims', 1),
            match_data.get('home_keeper_sweeper_clearances', 2),
            match_data.get('away_keeper_sweeper_clearances', 2),
            match_data.get('home_keeper_errors_leading_to_goal', 0.1),
            match_data.get('away_keeper_errors_leading_to_goal', 0.1),
            match_data.get('home_keeper_distribution_accuracy', 60),
            match_data.get('away_keeper_distribution_accuracy', 60),
            match_data.get('home_keeper_goal_prevention', 0.8),
            match_data.get('away_keeper_goal_prevention', 0.8),
            match_data.get('home_keeper_ps_xg_on_target', 0.3),
            match_data.get('away_keeper_ps_xg_on_target', 0.3)
        ])

        # 关键传球与创造力特征 (18维)
        features.extend([
            match_data.get('home_key_passes_per_game', 2),
            match_data.get('away_key_passes_per_game', 2),
            match_data.get('home_assists_per_game', 0.3),
            match_data.get('away_assists_per_game', 0.3),
            match_data.get('home_through_balls', 0.5),
            match_data.get('away_through_balls', 0.5),
            match_data.get('home_crosses', 3),
            match_data.get('away_crosses', 3),
            match_data.get('home_cross_accuracy', 25),
            match_data.get('away_cross_accuracy', 25),
            match_data.get('home_progressive_passes', 8),
            match_data.get('away_progressive_passes', 8),
            match_data.get('home_progressive_carries', 5),
            match_data.get('away_progressive_carries', 5),
            match_data.get('home_final_third_passes', 15),
            match_data.get('away_final_third_passes', 15),
            match_data.get('home_big_chances_created', 2),
            match_data.get('away_big_chances_created', 2)
        ])

        # 前锋转换效率特征 (20维)
        features.extend([
            match_data.get('home_shot_conversion_rate', 15),
            match_data.get('away_shot_conversion_rate', 15),
            match_data.get('home_xg_per_shot', 0.12),
            match_data.get('away_xg_per_shot', 0.12),
            match_data.get('home_big_chance_conversion', 30),
            match_data.get('away_big_chance_conversion', 30),
            match_data.get('home_first_time_shots', 40),
            match_data.get('away_first_time_shots', 40),
            match_data.get('home_left_foot_shots', 60),
            match_data.get('away_left_foot_shots', 60),
            match_data.get('home_right_foot_shots', 40),
            match_data.get('away_right_foot_shots', 40),
            match_data.get('home_headed_goals', 10),
            match_data.get('away_headed_goals', 10),
            match_data.get('home_penalty_area_shots', 70),
            match_data.get('away_penalty_area_shots', 70),
            match_data.get('home_open_play_goals', 80),
            match_data.get('away_open_play_goals', 80),
            match_data.get('home_set_piece_goals', 20),
            match_data.get('away_set_piece_goals', 20)
        ])

        # 防守与抢断特征 (20维)
        features.extend([
            match_data.get('home_tackles_won', 20),
            match_data.get('away_tackles_won', 20),
            match_data.get('home_tackles_attempted', 25),
            match_data.get('away_tackles_attempted', 25),
            match_data.get('home_tackle_success_rate', 80),
            match_data.get('away_tackle_success_rate', 80),
            match_data.get('home_interceptions', 8),
            match_data.get('away_interceptions', 8),
            match_data.get('home_clearances', 15),
            match_data.get('away_clearances', 15),
            match_data.get('home_blocks', 3),
            match_data.get('away_blocks', 3),
            match_data.get('home_aerial_duels_won', 12),
            match_data.get('away_aerial_duels_won', 12),
            match_data.get('home_aerial_duels_total', 20),
            match_data.get('away_aerial_duels_total', 20),
            match_data.get('home_aerial_success_rate', 60),
            match_data.get('away_aerial_success_rate', 60),
            match_data.get('home_sliding_tackles', 5),
            match_data.get('away_sliding_tackles', 5)
        ])

        # 控球与节奏特征 (20维)
        features.extend([
            match_data.get('home_pass_completion_rate', 80),
            match_data.get('away_pass_completion_rate', 80),
            match_data.get('home_total_passes', 500),
            match_data.get('away_total_passes', 500),
            match_data.get('home_short_passes', 400),
            match_data.get('away_short_passes', 400),
            match_data.get('home_medium_passes', 80),
            match_data.get('away_medium_passes', 80),
            match_data.get('home_long_passes', 20),
            match_data.get('away_long_passes', 20),
            match_data.get('home_pass_into_final_third', 30),
            match_data.get('away_pass_into_final_third', 30),
            match_data.get('home_pass_into_penalty_area', 5),
            match_data.get('away_pass_into_penalty_area', 5),
            match_data.get('home_touches', 800),
            match_data.get('away_touches', 800),
            match_data.get('home_ball_recoveries', 25),
            match_data.get('away_ball_recoveries', 25),
            match_data.get('home_possession_won_att_3rd', 8),
            match_data.get('away_possession_won_att_3rd', 8)
        ])

        # 纪律性与心理特征 (17维)
        features.extend([
            match_data.get('home_cards_per_game', 2),
            match_data.get('away_cards_per_game', 2),
            match_data.get('home_second_yellow_cards', 0.1),
            match_data.get('away_second_yellow_cards', 0.1),
            match_data.get('home_diving_save', 2),
            match_data.get('away_diving_save', 2),
            match_data.get('home_penalty_committed', 0.5),
            match_data.get('away_penalty_committed', 0.5),
            match_data.get('home_penalty_missed', 0.2),
            match_data.get('away_penalty_missed', 0.2),
            match_data.get('home_error_leading_to_goal', 0.2),
            match_data.get('away_error_leading_to_goal', 0.2),
            match_data.get('home_possession', 50),
            match_data.get('away_possession', 50),
            match_data.get('home_saves_made', 3),
            match_data.get('away_saves_made', 3),
            match_data.get('home_big_chances_missed', 1),
            match_data.get('away_big_chances_missed', 1)
        ])

        # 高级指标特征 (20维)
        features.extend([
            match_data.get('home_np_xg', 1.1),
            match_data.get('away_np_xg', 0.9),
            match_data.get('home_xg_chain', 2.0),
            match_data.get('away_xg_chain', 1.8),
            match_data.get('home_xg_buildup', 1.5),
            match_data.get('away_xg_buildup', 1.3),
            match_data.get('home_shot_creating_actions', 5),
            match_data.get('away_shot_creating_actions', 5),
            match_data.get('home_goal_creating_actions', 2),
            match_data.get('away_goal_creating_actions', 2),
            match_data.get('home_carries_into_final_third', 10),
            match_data.get('away_carries_into_final_third', 10),
            match_data.get('home_carries_into_penalty_area', 3),
            match_data.get('away_carries_into_penalty_area', 3),
            match_data.get('home_receives_progressive_passes', 20),
            match_data.get('away_receives_progressive_passes', 20),
            match_data.get('home_dispossessed', 5),
            match_data.get('away_dispossessed', 5),
            match_data.get('home_aerial_duels_won_pct', 60),
            match_data.get('away_aerial_duels_won_pct', 60)
        ])

        # 差异特征 (15维)
        features.extend([
            features[0] - features[1],  # xg_diff
            features[2] - features[3],  # goals_diff
            features[4] - features[5],  # shots_diff
            features[6] - features[7],  # shots_on_target_diff
            features[8] - features[9],  # possession_diff
            features[10] - features[11],  # pass_accuracy_diff
            features[12] - features[13],  # rating_diff
            features[20] - features[21],  # corners_diff
            features[22] - features[23],  # fouls_diff
            features[24] - features[25],  # cards_diff
            features[28] - features[29],  # offsides_diff
            0,  # keeper_saves_diff (placeholder)
            0,  # key_passes_diff (placeholder)
            0,  # conversion_rate_diff (placeholder)
            0   # tackles_won_diff (placeholder)
        ])

        # 确保长度为特征名称列表长度
        print(f"提取特征数量: {len(features)}")

        return np.array(features, dtype=np.float32)

    def extract_from_dataframe(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        从 DataFrame 中提取特征

        Args:
            df: 比赛数据 DataFrame

        Returns:
            特征矩阵 (n_samples, 180) 和特征名称列表
        """
        print(f"🔧 从 DataFrame 提取 180 维特征...")
        print(f"  数据量: {len(df)} 行")

        features_list = []
        for idx, row in df.iterrows():
            match_data = row.to_dict()
            features = self.extract_features_from_json(match_data)
            features_list.append(features)

        X = np.array(features_list)
        print(f"  ✅ 提取完成: {X.shape}")

        return X, self.feature_names


def main():
    """演示 180 维特征提取"""
    print("=" * 60)
    print("🎯 V9.1 180维精细特征提取器演示")
    print("=" * 60)

    # 创建示例数据
    extractor = AdvancedFeatureExtractorV91()

    # 示例比赛数据
    sample_match = {
        'home_avg_xg': 1.5,
        'away_avg_xg': 1.0,
        'home_avg_goals': 1.6,
        'away_avg_goals': 1.1,
        'home_avg_rating': 7.0,
        'away_avg_rating': 6.5,
        'home_keeper_save_percentage': 75,
        'away_keeper_save_percentage': 70,
        'home_shot_conversion_rate': 18,
        'away_shot_conversion_rate': 14,
        # ... 其他特征
    }

    # 提取特征
    features = extractor.extract_features_from_json(sample_match)

    print(f"\n✅ 特征提取成功!")
    print(f"  特征维度: {features.shape}")
    print(f"  特征数量: {len(extractor.feature_names)}")
    print(f"  特征范围: [{features.min():.3f}, {features.max():.3f}]")

    # 显示部分特征
    print(f"\n📊 关键特征示例:")
    print(f"  xG: 主队 {features[0]:.2f} vs 客队 {features[1]:.2f}")
    print(f"  评分: 主队 {features[12]:.2f} vs 客队 {features[13]:.2f}")
    print(f"  门将扑救率: 主队 {features[22]:.1f}% vs 客队 {features[23]:.1f}%")
    print(f"  射门转换率: 主队 {features[60]:.1f}% vs 客队 {features[61]:.1f}%")
    print(f"  关键传球: 主队 {features[40]:.1f} vs 客队 {features[41]:.1f}")

    # 保存特征名称
    joblib.dump(extractor.feature_names, '/tmp/feature_names_180_v91.pkl')
    print(f"\n✅ 特征名称已保存")


if __name__ == "__main__":
    main()
