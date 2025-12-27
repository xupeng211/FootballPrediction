#!/usr/bin/env python3
"""
V26.1 智能降维导出脚本 - 优化版
分块处理 + 特征采样
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Tuple, Dict, Set

import pandas as pd
import numpy as np
from collections import Counter


def export_sample_data(sample_size: int = 2000) -> pd.DataFrame:
    """
    先导出样本数据，用于特征发现
    """
    print(f"📦 导出样本数据（{sample_size} 行）用于特征发现...")

    cmd = f'''docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "\\copy (SELECT match_id, season, match_date, home_team, away_team, actual_result, rolling_xg_home, rolling_xg_away, rolling_shots_on_target_home, rolling_shots_on_target_away, rolling_possession_home, rolling_possession_away, rolling_team_rating_home, rolling_team_rating_away, home_table_position, away_table_position, table_position_diff, home_points, away_points, points_diff, home_recent_form_points, away_recent_form_points, raw_elo_gap, adjusted_elo_gap, fatigue_impact, schedule_impact, home_fatigue_index, away_fatigue_index, fatigue_diff, home_rest_days, away_rest_days, home_relegation_incentive, away_relegation_incentive, incentive_diff, home_desperation, table_proximity, low_scoring_tendency, elo_diff_cluster, adaptive_features::text FROM match_features_training ORDER BY RANDOM() LIMIT {sample_size}) TO STDOUT WITH CSV HEADER" > /tmp/v26_sample.csv'''

    subprocess.run(cmd, shell=True, check=True)

    df = pd.read_csv('/tmp/v26_sample.csv')
    print(f"   加载 {len(df)} 行样本")

    return df


def discover_high_quality_features(
    df_sample: pd.DataFrame,
    min_fill_rate: float = 0.5,
    max_features: int = 3000
) -> List[str]:
    """
    从样本中发现高质量特征
    """
    print(f"\n🔍 特征发现（目标：{max_features} 维，填充率 > {min_fill_rate*100}%）...")

    # 解析 adaptive_features
    print("   解析样本 adaptive_features...")
    adaptive_features_list = []

    for _, row in df_sample.iterrows():
        af_str = row.get('adaptive_features', '{}')

        try:
            if pd.notna(af_str) and af_str != '':
                adaptive = json.loads(af_str)
                adaptive_features_list.append(adaptive)
            else:
                adaptive_features_list.append({})
        except:
            adaptive_features_list.append({})

    # 扁平化
    print("   扁平化特征...")
    flattened_data = []

    for adaptive in adaptive_features_list:
        flat = flatten_jsonb(adaptive)
        flattened_data.append(flat)

    df_adaptive = pd.DataFrame(flattened_data)

    # 合并基础特征
    df_sample_af = df_sample.drop(columns=['adaptive_features'])
    df_full = pd.concat([df_sample_af, df_adaptive], axis=1)

    # 选择数值型特征
    numeric_cols = df_full.select_dtypes(include=[np.number]).columns.tolist()
    exclude_cols = ['match_id']
    feature_cols = [c for c in numeric_cols if c not in exclude_cols]

    print(f"   样本数值特征数量: {len(feature_cols)}")

    # 填充率过滤
    fill_rates = df_full[feature_cols].notna().mean()
    valid_features = fill_rates[fill_rates >= min_fill_rate].index.tolist()

    print(f"   填充率过滤后: {len(valid_features)} 维")

    # 方差过滤
    df_valid = df_full[valid_features].fillna(0)
    variances = df_valid.var()
    high_variance_features = variances[variances > 1e-6].index.tolist()

    print(f"   方差过滤后: {len(high_variance_features)} 维")

    # 按方差排序取 Top
    if len(high_variance_features) > max_features:
        variance_series = variances[high_variance_features].sort_values(ascending=False)
        selected = variance_series.head(max_features).index.tolist()
        print(f"   硬限制降维: {len(selected)} 维")
    else:
        selected = high_variance_features

    return selected


def export_full_data(selected_features: List[str]) -> pd.DataFrame:
    """
    导出完整数据，只提取选定的特征
    """
    print(f"\n📦 导出完整数据（{len(selected_features)} 个特征）...")

    # 基础列
    base_cols = [
        'match_id', 'match_date', 'home_team', 'away_team', 'actual_result',
        'rolling_xg_home', 'rolling_xg_away',
        'rolling_shots_on_target_home', 'rolling_shots_on_target_away',
        'rolling_possession_home', 'rolling_possession_away',
        'rolling_team_rating_home', 'rolling_team_rating_away',
        'home_table_position', 'away_table_position', 'table_position_diff',
        'home_points', 'away_points', 'points_diff',
        'home_recent_form_points', 'away_recent_form_points',
        'raw_elo_gap', 'adjusted_elo_gap',
        'fatigue_impact', 'schedule_impact',
        'home_fatigue_index', 'away_fatigue_index', 'fatigue_diff',
        'home_rest_days', 'away_rest_days',
        'home_relegation_incentive', 'away_relegation_incentive',
        'incentive_diff', 'home_desperation',
        'table_proximity', 'low_scoring_tendency', 'elo_diff_cluster',
        'adaptive_features::text'
    ]

    cmd = '''docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "\\COPY (SELECT ''' + ', '.join(base_cols) + ''' FROM match_features_training ORDER BY match_date) TO STDOUT WITH CSV HEADER" > /tmp/v26_full.csv'''

    subprocess.run(cmd, shell=True, check=True)

    df = pd.read_csv('/tmp/v26_full.csv')
    print(f"   加载 {len(df)} 行完整数据")

    return df


def build_final_dataset(
    df_full: pd.DataFrame,
    selected_features: List[str],
    max_features: int = 3000
) -> Tuple[pd.DataFrame, List[str]]:
    """
    构建最终数据集
    """
    print(f"\n🔨 构建最终特征矩阵...")

    # 解析 adaptive_features（分块处理避免内存溢出）
    print("   解析 adaptive_features（分块处理）...")

    chunk_size = 1000
    adaptive_dfs = []

    for i in range(0, len(df_full), chunk_size):
        chunk = df_full.iloc[i:i+chunk_size].copy()

        flattened_list = []
        for _, row in chunk.iterrows():
            af_str = row.get('adaptive_features', '{}')
            try:
                if pd.notna(af_str) and af_str != '':
                    adaptive = json.loads(af_str)
                else:
                    adaptive = {}
            except:
                adaptive = {}

            flat = flatten_jsonb(adaptive)
            flattened_list.append(flat)

        df_adaptive_chunk = pd.DataFrame(flattened_list)
        adaptive_dfs.append(df_adaptive_chunk)

    df_adaptive = pd.concat(adaptive_dfs, ignore_index=True)

    # 合并
    df_base = df_full.drop(columns=['adaptive_features'])
    df_merged = pd.concat([df_base.reset_index(drop=True), df_adaptive], axis=1)

    # 创建标签
    df_merged['target_win'] = (df_merged['actual_result'] == 'home').astype(int)

    # 选择已识别的特征
    available_features = [f for f in selected_features if f in df_merged.columns]

    print(f"   可用特征: {len(available_features)}/{len(selected_features)}")

    # 构建最终数据集
    final_cols = ['match_id', 'match_date', 'home_team', 'away_team', 'actual_result', 'target_win']
    final_cols.extend(available_features)

    df_final = df_merged[final_cols].copy()

    # 填充缺失值
    for col in available_features:
        df_final[col] = df_final[col].fillna(0)

    print(f"\n✅ 最终特征矩阵: {df_final.shape}")
    print(f"   - 行数: {df_final.shape[0]}")
    print(f"   - 特征维度: {len(available_features)}")

    return df_final, available_features


def flatten_jsonb(data, prefix: str = "", sep: str = ".") -> dict:
    """扁平化嵌套 JSON"""
    items = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}{sep}{key}" if prefix else key

            if isinstance(value, dict):
                items.update(flatten_jsonb(value, new_key, sep=sep))
            elif isinstance(value, list):
                if len(value) > 0 and isinstance(value[0], (int, float)):
                    items[new_key] = np.mean(value) if value else 0
                else:
                    items[new_key] = 0
            else:
                items[new_key] = value if (value is not None and not isinstance(value, dict)) else 0

    return items


def main():
    """主函数"""
    print("=" * 60)
    print("V26.1 智能降维导出 (Feature Distillation - Optimized)")
    print("=" * 60)

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: 样本特征发现
    df_sample = export_sample_data(sample_size=2000)
    selected_features = discover_high_quality_features(df_sample, max_features=3000)

    # Step 2: 导出完整数据
    df_full = export_full_data(selected_features)

    # Step 3: 构建最终数据集
    df_final, final_features = build_final_dataset(df_full, selected_features)

    # 保存
    output_path = output_dir / "V26_Distilled_3000.parquet"
    print(f"\n💾 保存数据到: {output_path}")
    df_final.to_parquet(output_path, index=False)

    # 保存特征列表
    feature_list_path = output_dir / "V26_Distilled_3000_features.txt"
    with open(feature_list_path, 'w') as f:
        f.write(f"# V26.1 蒸馏特征列表 ({len(final_features)} 维)\n\n")
        for i, feat in enumerate(final_features, 1):
            f.write(f"{i}. {feat}\n")

    print(f"✅ 特征列表保存到: {feature_list_path}")

    # 统计
    print(f"\n📊 数据集统计:")
    print(f"   - 总行数: {len(df_final)}")
    print(f"   - 特征维度: {len(final_features)}")
    print(f"   - 主队胜: {df_final['target_win'].sum()} ({df_final['target_win'].mean()*100:.1f}%)")
    print(f"   - 时间范围: {df_final['match_date'].min()} ~ {df_final['match_date'].max()}")

    print("\n✅ V26.1 特征蒸馏完成！")


if __name__ == "__main__":
    main()
