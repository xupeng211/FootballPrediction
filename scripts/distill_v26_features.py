#!/usr/bin/env python3
"""
V26.1 智能降维导出脚本 (Feature Distillation)
- 从 match_features_training 表中提取特征
- 方差过滤：仅保留填充率 > 80% 的特征
- 硬限制：3,000 维以内
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    db = settings.database

    return psycopg2.connect(
        host=db.host,
        port=db.port,
        database=db.name,
        user=db.user,
        password=db.password.get_secret_value()
    )


def extract_all_feature_keys(conn, sample_size: int = 1000) -> set:
    """
    从 adaptive_features (JSONB) 中提取所有唯一的特征键
    """
    print(f"🔍 扫描 adaptive_features 中的所有特征键（采样 {sample_size} 行）...")

    query = f"""
    SELECT adaptive_features
    FROM match_features_training
    WHERE adaptive_features IS NOT NULL
    ORDER BY RANDOM()
    LIMIT %s;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (sample_size,))
        rows = cur.fetchall()

    all_keys = set()

    for row in tqdm(rows, desc="提取特征键"):
        if row['adaptive_features']:
            # 递归提取所有键（包括嵌套结构）
            keys = extract_keys_from_jsonb(row['adaptive_features'])
            all_keys.update(keys)

    print(f"   发现 {len(all_keys)} 个唯一特征键")
    return all_keys


def extract_keys_from_jsonb(data, prefix: str = "") -> set:
    """
    递归提取 JSONB 中的所有键
    """
    keys = set()

    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            # 只收集叶子节点（数值型）
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                keys.add(full_key)
            elif isinstance(value, dict):
                keys.update(extract_keys_from_jsonb(value, full_key))
            elif isinstance(value, list) and len(value) > 0:
                # 处理数组
                if isinstance(value[0], (int, float)) and not isinstance(value[0], bool):
                    keys.add(full_key)

    return keys


def build_feature_matrix(
    conn,
    max_features: int = 3000,
    min_fill_rate: float = 0.8
) -> Tuple[pd.DataFrame, List[str]]:
    """
    构建特征矩阵并降维

    Returns:
        (DataFrame, list_of_selected_features)
    """
    print(f"\n🔨 构建特征矩阵（目标：{max_features} 维，填充率 > {min_fill_rate*100}%）...")

    # 1. 加载基础数据
    query = """
    SELECT
        match_id,
        season,
        match_date,
        home_team,
        away_team,
        actual_result,
        -- 基础特征（约 40 维）
        rolling_xg_home, rolling_xg_away,
        rolling_shots_on_target_home, rolling_shots_on_target_away,
        rolling_possession_home, rolling_possession_away,
        rolling_team_rating_home, rolling_team_rating_away,
        home_table_position, away_table_position, table_position_diff,
        home_points, away_points, points_diff,
        home_recent_form_points, away_recent_form_points,
        raw_elo_gap, adjusted_elo_gap,
        fatigue_impact, schedule_impact,
        home_fatigue_index, away_fatigue_index, fatigue_diff,
        home_rest_days, away_rest_days,
        home_relegation_incentive, away_relegation_incentive,
        incentive_diff, home_desperation,
        table_proximity, low_scoring_tendency, elo_diff_cluster,
        adaptive_features,
        feature_count
    FROM match_features_training
    ORDER BY match_date;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    print(f"   加载 {len(rows)} 行数据")

    # 2. 构建 DataFrame
    data = []

    for row in tqdm(rows, desc="解析数据"):
        row_dict = dict(row)

        # 处理 adaptive_features
        adaptive = row_dict.pop('adaptive_features', None)
        row_dict.pop('feature_count', None)  # 移除元数据

        if adaptive:
            # 扁平化 adaptive_features
            flat_features = flatten_jsonb(adaptive)
            row_dict.update(flat_features)

        data.append(row_dict)

    df = pd.DataFrame(data)

    # 3. 创建标签
    df['target_win'] = (df['actual_result'] == 'home').astype(int)

    print(f"   原始特征维度: {df.shape[1]}")

    # 4. 选择数值型特征
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # 移除非特征列
    exclude_cols = ['match_id']
    feature_cols = [c for c in numeric_cols if c not in exclude_cols]

    print(f"   数值型特征数量: {len(feature_cols)}")

    # 5. 填充率过滤
    fill_rates = df[feature_cols].notna().mean()

    # 过滤掉填充率 < 80% 的特征
    valid_features = fill_rates[fill_rates >= min_fill_rate].index.tolist()

    print(f"   填充率过滤后: {len(valid_features)} 维")

    # 6. 方差过滤（移除常数特征）
    df_valid = df[valid_features].fillna(0)
    variances = df_valid.var()

    # 移除方差接近 0 的特征
    high_variance_features = variances[variances > 1e-6].index.tolist()

    print(f"   方差过滤后: {len(high_variance_features)} 维")

    # 7. 如果仍然超过 3000 维，按方差排序取 Top 3000
    if len(high_variance_features) > max_features:
        variance_series = variances[high_variance_features].sort_values(ascending=False)
        selected_features = variance_series.head(max_features).index.tolist()
        print(f"   硬限制降维: {len(selected_features)} 维（按方差排序）")
    else:
        selected_features = high_variance_features

    # 8. 构建最终特征矩阵
    final_cols = ['match_id', 'match_date', 'home_team', 'away_team', 'actual_result', 'target_win']
    final_cols.extend(selected_features)

    df_final = df[final_cols].copy()

    # 填充缺失值
    for col in selected_features:
        df_final[col] = df_final[col].fillna(0)

    print(f"\n✅ 最终特征矩阵: {df_final.shape}")
    print(f"   - 行数: {df_final.shape[0]}")
    print(f"   - 列数: {df_final.shape[1]}")
    print(f"   - 特征维度: {len(selected_features)}")

    return df_final, selected_features


def flatten_jsonb(data, prefix: str = "", sep: str = ".") -> Dict:
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
                # 数组转换为均值或保持原样
                if len(value) > 0 and isinstance(value[0], (int, float)):
                    items[new_key] = np.mean(value) if value else 0
                else:
                    items[new_key] = 0
            else:
                items[new_key] = value if value is not None else 0

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

    # 连接数据库
    conn = get_db_connection()

    try:
        # 构建特征矩阵
        df, selected_features = build_feature_matrix(
            conn,
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

    finally:
        conn.close()

    print("\n✅ V26.1 特征蒸馏完成！")


if __name__ == "__main__":
    main()
