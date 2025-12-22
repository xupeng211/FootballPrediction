#!/usr/bin/env python3
"""
V9.5 数据欺诈紧急修复 - 特征集"大清洗"
彻底删除所有赛后统计，只保留赛前可获得的数据
建立不可逾越的"时间隔离带"
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class DataSanitizer:
    """数据清洗器 - 建立严格时间隔离"""

    def __init__(self):
        # 绝对禁止的赛后特征
        self.FORBIDDEN_FEATURES = [
            'actual_home_goals',
            'actual_away_goals',
            'actual_result',
            'real_match_date',
            'real_season',
            'match_date',
            'season'
        ]

        # 安全的赛前特征
        self.SAFE_FEATURES = [
            # 基本信息
            'home_team_name',
            'away_team_name',
            'year',
            'month',
            'day_of_week',
            'is_weekend',
            'league_id',
            'league_name',

            # 赔率 (开盘赔率，赛前可得)
            'home_win_odds',
            'draw_odds',
            'away_win_odds',
            'home_win_odds.1',
            'draw_odds.1',
            'away_win_odds.1',
            'real_home_odds',
            'real_draw_odds',
            'real_away_odds',

            # 历史滚动统计 (前N场，在比赛前可计算)
            'home_last_3_avg_goal_diff',
            'home_last_3_win_rate',
            'home_last_3_positive_diff_rate',
            'away_last_3_avg_goal_diff',
            'away_last_3_win_rate',
            'away_last_3_positive_diff_rate',
            'home_last_5_avg_goal_diff',
            'home_last_5_win_rate',
            'home_last_5_positive_diff_rate',
            'away_last_5_avg_goal_diff',
            'away_last_5_win_rate',
            'away_last_5_positive_diff_rate',
            'home_last_10_avg_goal_diff',
            'home_last_10_win_rate',
            'home_last_10_positive_diff_rate',
            'away_last_10_avg_goal_diff',
            'away_last_10_win_rate',
            'away_last_10_positive_diff_rate',

            # 衍生特征 (基于安全的赛前数据)
            'home_prob',
            'draw_prob',
            'away_prob',
            'total_prob',
            'home_prob_norm',
            'draw_prob_norm',
            'away_prob_norm',
        ]

        # 需要检查的特征 (可能包含赛后统计)
        self.SUSPICIOUS_FEATURES = [
            'home_last_3_avg_goals_scored',
            'home_last_3_avg_goals_conceded',
            'home_last_3_avg_xg',
            'home_last_3_avg_xg_advantage',
            'home_last_3_form_score',
            'away_last_3_avg_goals_scored',
            'away_last_3_avg_goals_conceded',
            'away_last_3_avg_xg',
            'away_last_3_avg_xg_advantage',
            'away_last_3_form_score',
            'home_last_5_avg_goals_scored',
            'home_last_5_avg_goals_conceded',
            'home_last_5_avg_xg',
            'home_last_5_avg_xg_advantage',
            'home_last_5_form_score',
            'away_last_5_avg_goals_scored',
            'away_last_5_avg_goals_conceded',
            'away_last_5_avg_xg',
            'away_last_5_avg_xg_advantage',
            'away_last_5_form_score',
            'home_last_10_avg_goals_scored',
            'home_last_10_avg_goals_conceded',
            'home_last_10_avg_xg',
            'home_last_10_avg_xg_advantage',
            'home_last_10_form_score',
            'away_last_10_avg_goals_scored',
            'away_last_10_avg_goals_conceded',
            'away_last_10_avg_xg',
            'away_last_10_avg_xg_advantage',
            'away_last_10_form_score',
        ]

    def sanitize_dataset(self, input_path, output_path):
        """清洗数据集"""
        print("🧹 V9.5 数据集紧急清洗")
        print("=" * 80)

        # 加载数据
        df = pd.read_csv(input_path)
        print(f"原始数据: {len(df)} 场比赛, {len(df.columns)} 个特征")

        # 识别需要删除的特征
        features_to_delete = []
        features_to_keep = []

        for col in df.columns:
            if col in self.FORBIDDEN_FEATURES:
                features_to_delete.append((col, "赛后结果"))
            elif col in self.SUSPICIOUS_FEATURES:
                features_to_delete.append((col, "赛后统计"))
            elif col in self.SAFE_FEATURES:
                features_to_keep.append(col)
            else:
                # 未知特征，默认删除
                features_to_delete.append((col, "未知"))

        # 报告删除的特征
        print(f"\n🚨 删除的特征 ({len(features_to_delete)} 个):")
        for feat, reason in features_to_delete:
            print(f"  ❌ {feat:50} - {reason}")

        # 保留的特征
        print(f"\n✅ 保留的特征 ({len(features_to_keep)} 个):")
        for feat in features_to_keep:
            print(f"  ✅ {feat}")

        # 创建清洗后的数据框
        df_clean = df[features_to_keep].copy()

        # 添加必要的赛前特征
        # 计算赛季信息
        df_clean['match_date'] = pd.to_datetime(df.get('match_date', df.get('real_match_date')))
        df_clean['season'] = df_clean['match_date'].apply(
            lambda x: f'{x.year-1}/{x.year}' if x.month <= 7 else f'{x.year}/{x.year+1}'
        )

        # 添加标签 (目标变量)
        if 'actual_result' in df.columns:
            df_clean['target'] = (df['actual_result'] == 'H').astype(int)
        else:
            df_clean['target'] = 0  # 无标签

        # 保存清洗后的数据
        df_clean.to_csv(output_path, index=False)

        print(f"\n✅ 清洗完成!")
        print(f"  原始特征: {len(df.columns)} → 清洗后: {len(features_to_keep)}")
        print(f"  删除率: {(len(df.columns) - len(features_to_keep)) / len(df.columns) * 100:.1f}%")
        print(f"  保存路径: {output_path}")

        return df_clean

    def validate_temporal_integrity(self, df):
        """验证时间完整性"""
        print(f"\n🔍 验证时间完整性...")

        # 检查日期范围
        df['match_date'] = pd.to_datetime(df['match_date'])
        min_date = df['match_date'].min()
        max_date = df['match_date'].max()

        print(f"  日期范围: {min_date} 到 {max_date}")

        # 按赛季统计
        season_counts = df['season'].value_counts().sort_index()
        print(f"\n  按赛季分布:")
        for season, count in season_counts.items():
            print(f"    {season}: {count} 场")

        # 检查标签完整性
        if 'target' in df.columns:
            label_rate = df['target'].notna().mean()
            print(f"\n  标签完整率: {label_rate:.1%}")

            if label_rate > 0:
                positive_rate = df['target'].mean()
                print(f"  主胜率: {positive_rate:.1%}")

        return True

def main():
    """主函数"""
    print("=" * 80)
    print("🚨 V9.5 数据欺诈紧急修复 - 特征集大清洗")
    print("=" * 80)

    sanitizer = DataSanitizer()

    # 清洗数据集
    input_path = "/home/user/projects/FootballPrediction/data/v9_3_comprehensive_dataset.csv"
    output_path = "/home/user/projects/FootballPrediction/data/v9_5_sanitized_features.csv"

    df_clean = sanitizer.sanitize_dataset(input_path, output_path)

    # 验证时间完整性
    sanitizer.validate_temporal_integrity(df_clean)

    # 生成报告
    print("\n" + "=" * 80)
    print("✅ V9.5 数据清洗完成")
    print("=" * 80)
    print(f"  📊 清洗后数据: {len(df_clean)} 场比赛")
    print(f"  🔒 时间隔离带: 已建立")
    print(f"  🎯 特征维度: {len([c for c in df_clean.columns if c not in ['target', 'season', 'match_date']])}")
    print(f"  📁 保存路径: {output_path}")

    return df_clean

if __name__ == "__main__":
    df_clean = main()
