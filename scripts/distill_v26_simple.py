#!/usr/bin/env python3
"""
V26.1 智能降维导出脚本 - 简化版
使用 CSV 导入方式，避免数据库连接问题
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import numpy as np
from tqdm import tqdm


def run_sql_query(query: str) -> pd.DataFrame:
    """通过 Docker 执行 SQL 查询"""
    cmd = f'''docker exec football_prediction_db psql -U football_user -d football_prediction_dev -t -c "{query}"'''

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"SQL 查询失败: {result.stderr}")

    # 解析输出
    lines = result.stdout.strip().split('\n')

    if not lines or lines[0].strip() == '':
        return pd.DataFrame()

    # 使用 CSV 格式更可靠
    return pd.read_csv(result.stdout.strip(), sep='|')


def export_data_via_csv() -> pd.DataFrame:
    """通过 CSV 导出数据"""
    print("📦 导出 match_features_training 数据...")

    # 先导出到 CSV（在容器内）
    cmd = '''docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "\\copy (SELECT match_id, season, match_date, home_team, away_team, actual_result, rolling_xg_home, rolling_xg_away, rolling_shots_on_target_home, rolling_shots_on_target_away, rolling_possession_home, rolling_possession_away, rolling_team_rating_home, rolling_team_rating_away, home_table_position, away_table_position, table_position_diff, home_points, away_points, points_diff, home_recent_form_points, away_recent_form_points, raw_elo_gap, adjusted_elo_gap, fatigue_impact, schedule_impact, home_fatigue_index, away_fatigue_index, fatigue_diff, home_rest_days, away_rest_days, home_relegation_incentive, away_relegation_incentive, incentive_diff, home_desperation, table_proximity, low_scoring_tendency, elo_diff_cluster, adaptive_features::text FROM match_features_training ORDER BY match_date) TO STDOUT WITH CSV HEADER" > /tmp/v26_raw_data.csv'''

    subprocess.run(cmd, shell=True, check=True)

    # 读取 CSV
    df = pd.read_csv('/tmp/v26_raw_data.csv')
    print(f"   加载 {len(df)} 行数据")

    return df


def build_feature_matrix(
    max_features: int = 3000,
    min_fill_rate: float = 0.8
) -> Tuple[pd.DataFrame, List[str]]:
    """
    构建特征矩阵并降维
    """
    print(f"\n🔨 构建特征矩阵（目标：{max_features} 维，填充率 > {min_fill_rate*100}%）...")

    # 1. 导出数据
    df = export_data_via_csv()

    # 2. 解析 adaptive_features
    print("   解析 adaptive_features...")

    adaptive_features_list = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="解析 JSON"):
        af_str = row.get('adaptive_features', '{}')

        try:
            if pd.isna(af_str) or af_str == '':
                adaptive_features_list.append({})
            else:
                adaptive = json.loads(af_str)
                adaptive_features_list.append(adaptive)
        except:
            adaptive_features_list.append({})

    # 3. 扁平化 adaptive_features
    print("   扁平化 adaptive_features...")

    flattened_data = []

    for adaptive in tqdm(adaptive_features_list, desc="扁平化"):
        flat = flatten_jsonb(adaptive)
        flattened_data.append(flat)

    df_adaptive = pd.DataFrame(flattened_data)

    # 4. 合并基础特征和自适应特征
    print("   合并特征...")

    # 移除 adaptive_features 原始列
    df = df.drop(columns=['adaptive_features'])

    # 合并
    df_full = pd.concat([df, df_adaptive], axis=1)

    print(f"   合并后维度: {df_full.shape[1]}")

    # 5. 创建标签
    df_full['target_win'] = (df_full['actual_result'] == 'home').astype(int)

    # 6. 选择数值型特征
    numeric_cols = df_full.select_dtypes(include=[np.number]).columns.tolist()

    # 移除非特征列
    exclude_cols = ['match_id']
    feature_cols = [c for c in numeric_cols if c not in exclude_cols]

    print(f"   数值型特征数量: {len(feature_cols)}")

    # 7. 填充率过滤
    print("   执行填充率过滤...")
    fill_rates = df_full[feature_cols].notna().mean()

    valid_features = fill_rates[fill_rates >= min_fill_rate].index.tolist()

    print(f"   填充率过滤后: {len(valid_features)} 维")

    # 8. 方差过滤
    print("   执行方差过滤...")
    df_valid = df_full[valid_features].fillna(0)
    variances = df_valid.var()

    high_variance_features = variances[variances > 1e-6].index.tolist()

    print(f"   方差过滤后: {len(high_variance_features)} 维")

    # 9. 硬限制降维
    if len(high_variance_features) > max_features:
        variance_series = variances[high_variance_features].sort_values(ascending=False)
        selected_features = variance_series.head(max_features).index.tolist()
        print(f"   硬限制降维: {len(selected_features)} 维（按方差排序）")
    else:
        selected_features = high_variance_features

    # 10. 构建最终特征矩阵
    final_cols = ['match_id', 'match_date', 'home_team', 'away_team', 'actual_result', 'target_win']
    final_cols.extend(selected_features)

    df_final = df_full[final_cols].copy()

    # 填充缺失值
    for col in selected_features:
        df_final[col] = df_final[col].fillna(0)

    print(f"\n✅ 最终特征矩阵: {df_final.shape}")
    print(f"   - 行数: {df_final.shape[0]}")
    print(f"   - 列数: {df_final.shape[1]}")
    print(f"   - 特征维度: {len(selected_features)}")

    return df_final, selected_features


def flatten_jsonb(data, prefix: str = "", sep: str = ".") -> dict:
    """
    扁平化嵌套 JSON/字典
    """
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
    print("V26.1 智能降维导出 (Feature Distillation)")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "V26_Distilled_3000.parquet"

    # 构建特征矩阵
    df, selected_features = build_feature_matrix(
        max_features=3000,
        min_fill_rate=0.8
    )

    # 保存数据
    print(f"\n💾 保存数据到: {output_path}")
    df.to_parquet(output_path, index=False)

    # 保存特征列表
    feature_list_path = output_dir / "V26_Distilled_3000_features.txt"
    with open(feature_list_path, 'w') as f:
        f.write(f"# V26.1 蒸馏特征列表 ({len(selected_features)} 维)\n\n")
        for i, feat in enumerate(selected_features, 1):
            f.write(f"{i}. {feat}\n")

    print(f"✅ 特征列表保存到: {feature_list_path}")

    # 统计信息
    print(f"\n📊 数据集统计:")
    print(f"   - 总行数: {len(df)}")
    print(f"   - 特征维度: {len(selected_features)}")
    print(f"   - 目标分布:")
    print(f"     * 主队胜: {df['target_win'].sum()} ({df['target_win'].mean()*100:.1f}%)")
    print(f"     * 非主队胜: {(df['target_win'] == 0).sum()} ({(1-df['target_win']).mean()*100:.1f}%)")
    print(f"   - 时间范围: {df['match_date'].min()} ~ {df['match_date'].max()}")

    print("\n✅ V26.1 特征蒸馏完成！")


if __name__ == "__main__":
    main()
