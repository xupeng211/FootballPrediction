#!/usr/bin/env python3
"""
时序特征工程脚本 - Rolling Features Engineering
Phase 2.2: 解决数据泄露问题，构建赛前预测特征

核心功能:
1. 从后比赛统计推导历史表现指标
2. 计算球队滚动平均特征 (Last 3, 5, 10 games)
3. 构建主客场表现差异指标
4. 生成安全的前比赛数据集 (无泄露风险)

作者: Advanced ML Engineer
创建时间: 2025-12-10
版本: 2.0.0 - Rolling Features Dataset
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollingFeatureEngineer:
    """时序特征工程器"""

    def __init__(self):
        self.rolling_windows = [3, 5, 10]  # 滚动窗口大小
        self.team_stats_cache = {}  # 缓存球队统计数据

    def load_data(self, file_path: str) -> pd.DataFrame:
        """加载基础数据集"""
        logger.info(f"📊 加载数据集: {file_path}")
        df = pd.read_csv(file_path)

        # 确保match_date字段格式正确
        if "match_date" not in df.columns:
            # 使用year, month创建模拟日期（简单估算）
            df["match_date"] = pd.to_datetime(
                df["year"].astype(str)
                + "-"
                + df["month"].astype(str).str.zfill(2)
                + "-"
                + "01"  # 使用每月1号作为估算日期
            )
        else:
            df["match_date"] = pd.to_datetime(df["match_date"])

        logger.info(f"   数据形状: {df.shape}")
        logger.info(
            f"   日期范围: {df['match_date'].min()} 到 {df['match_date'].max()}"
        )

        return df

    def extract_team_identifiers(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取球队标识符"""
        logger.info("🏷️ 提取球队标识符")

        # 从已有数据中提取主客队信息
        # 由于原始数据中没有team_id，我们需要创建标识符
        if "home_team_name" not in df.columns and "away_team_name" not in df.columns:
            # 如果没有team_name列，我们可以使用match_id作为唯一标识
            # 在实际应用中，这里应该从其他数据源获取team信息
            logger.warning("⚠️ 未找到球队名称字段，使用模拟数据")
            df["home_team_name"] = df.apply(
                lambda x: f"Team_Home_{x['match_id'] % 100}", axis=1
            )
            df["away_team_name"] = df.apply(
                lambda x: f"Team_Away_{x['match_id'] % 100}", axis=1
            )

        return df

    def calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """从基础数据推导衍生指标（赛前可获得）"""
        logger.info("📈 计算衍生指标")

        # 从进球数据推导的表现指标
        df["home_goals_scored"] = df["home_score"]
        df["away_goals_scored"] = df["away_score"]
        df["home_goals_conceded"] = df["away_score"]
        df["away_goals_conceded"] = df["home_score"]

        # 目标差异指标
        df["home_goal_diff"] = df["home_score"] - df["away_score"]
        df["away_goal_diff"] = df["away_score"] - df["home_score"]

        # xG表现指标（赛前可获得的期望数据）
        df["home_xg_advantage"] = df["home_xg"] - df["away_xg"]
        df["away_xg_disadvantage"] = df["away_xg"] - df["home_xg"]

        # 场地类型编码（主场=1, 客场=0）
        df["home_venue"] = 1
        df["away_venue"] = 0

        logger.info("   ✅ 衍生指标计算完成")
        return df

    def build_team_history(self, df: pd.DataFrame) -> dict:
        """构建球队历史数据字典"""
        logger.info("🏗️ 构建球队历史数据字典")

        team_history = {}

        # 获取所有唯一球队
        all_teams = set(df["home_team_name"].unique()) | set(
            df["away_team_name"].unique()
        )

        for team in all_teams:
            team_history[team] = []

        # 为每场比赛记录球队表现
        for _, row in df.iterrows():
            # 主队记录
            home_record = {
                "match_date": row["match_date"],
                "venue": "home",
                "goals_scored": row["home_goals_scored"],
                "goals_conceded": row["home_goals_conceded"],
                "goal_diff": row["home_goal_diff"],
                "xg": row["home_xg"],
                "xg_advantage": row["home_xg_advantage"],
                "opponent": row["away_team_name"],
                "result": row["result"],
            }
            team_history[row["home_team_name"]].append(home_record)

            # 客队记录
            away_record = {
                "match_date": row["match_date"],
                "venue": "away",
                "goals_scored": row["away_goals_scored"],
                "goals_conceded": row["away_goals_conceded"],
                "goal_diff": row["away_goal_diff"],
                "xg": row["away_xg"],
                "xg_advantage": row["away_xg_disadvantage"],
                "opponent": row["home_team_name"],
                "result": row["result"],
            }
            team_history[row["away_team_name"]].append(away_record)

        # 对每个球队的历史记录按日期排序
        for team in team_history:
            team_history[team] = sorted(
                team_history[team], key=lambda x: x["match_date"]
            )

        logger.info(f"   ✅ 构建 {len(team_history)} 支球队的历史数据")
        return team_history

    def apply_rolling_features(
        self, df: pd.DataFrame, team_history: dict
    ) -> pd.DataFrame:
        """应用滚动特征到数据集 - 确保时序安全"""
        logger.info("⚡ 应用滚动特征到数据集（时序安全）")

        # 为每个窗口大小计算滚动特征
        for window_size in self.rolling_windows:
            logger.info(f"   计算 {window_size} 场比赛滚动特征...")

            # 逐行处理以确保时序安全
            for i, row in df.iterrows():
                home_team = row["home_team_name"]
                away_team = row["away_team_name"]
                current_date = row["match_date"]

                # 获取每支球队的历史记录（排除当前及之后比赛）
                home_history = [
                    m
                    for m in team_history.get(home_team, [])
                    if m["match_date"] < current_date
                ]
                away_history = [
                    m
                    for m in team_history.get(away_team, [])
                    if m["match_date"] < current_date
                ]

                # 计算主队滚动特征
                home_rolling = self._calculate_team_rolling_features(
                    home_history, window_size
                )
                for feature_name, feature_value in home_rolling.items():
                    df.loc[i, f"home_{feature_name}"] = feature_value

                # 计算客队滚动特征
                away_rolling = self._calculate_team_rolling_features(
                    away_history, window_size
                )
                for feature_name, feature_value in away_rolling.items():
                    df.loc[i, f"away_{feature_name}"] = feature_value

                if (i + 1) % 100 == 0:
                    logger.info(f"   已处理 {i + 1}/{len(df)} 场比赛")

        logger.info("   ✅ 滚动特征应用完成（时序安全）")
        return df

    def _calculate_team_rolling_features(self, matches: list, window_size: int) -> dict:
        """计算单支球队的滚动特征"""
        if not matches:
            # 没有历史数据时使用默认值
            return {
                f"last_{window_size}_avg_goals_scored": 1.0,
                f"last_{window_size}_avg_goals_conceded": 1.0,
                f"last_{window_size}_avg_goal_diff": 0.0,
                f"last_{window_size}_avg_xg": 1.3,
                f"last_{window_size}_avg_xg_advantage": 0.0,
                f"last_{window_size}_win_rate": 0.33,
                f"last_{window_size}_positive_diff_rate": 0.33,
                f"last_{window_size}_form_score": 1.0,
            }

        # 取最近的window_size场比赛
        window_matches = (
            matches[-window_size:] if len(matches) >= window_size else matches
        )

        # 计算各项指标的滚动平均
        goals_scored_avg = np.mean([m["goals_scored"] for m in window_matches])
        goals_conceded_avg = np.mean([m["goals_conceded"] for m in window_matches])
        goal_diff_avg = np.mean([m["goal_diff"] for m in window_matches])
        xg_avg = np.mean([m["xg"] for m in window_matches])
        xg_advantage_avg = np.mean([m["xg_advantage"] for m in window_matches])

        # 计算胜率
        wins = sum(
            1
            for m in window_matches
            if (m["result"] == "H" and m["venue"] == "home")
            or (m["result"] == "A" and m["venue"] == "away")
        )
        win_rate = wins / len(window_matches)

        # 计算净胜球率
        positive_goal_diff = sum(1 for m in window_matches if m["goal_diff"] > 0)
        positive_diff_rate = positive_goal_diff / len(window_matches)

        return {
            f"last_{window_size}_avg_goals_scored": goals_scored_avg,
            f"last_{window_size}_avg_goals_conceded": goals_conceded_avg,
            f"last_{window_size}_avg_goal_diff": goal_diff_avg,
            f"last_{window_size}_avg_xg": xg_avg,
            f"last_{window_size}_avg_xg_advantage": xg_advantage_avg,
            f"last_{window_size}_win_rate": win_rate,
            f"last_{window_size}_positive_diff_rate": positive_diff_rate,
            f"last_{window_size}_form_score": (wins * 3 + positive_goal_diff)
            / len(window_matches),
        }

    def create_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建对战历史特征"""
        logger.info("🆚 创建对战历史特征")

        # 简化的对战历史特征：计算主队vs客队的历史平均表现
        # 在实际应用中，这里需要更复杂的逻辑来追踪具体的对战记录

        df["h2h_home_advantage"] = 0.1  # 默认主场优势
        df["h2v_home_xg_boost"] = 0.05  # 主场xG加成

        logger.info("   ✅ 对战历史特征创建完成")
        return df

    def build_safe_feature_dataset(
        self, input_path: str, output_path: str
    ) -> pd.DataFrame:
        """构建安全的无泄露特征数据集"""
        logger.info("🚀 开始构建安全的时序特征数据集")

        # 1. 加载基础数据
        df = self.load_data(input_path)

        # 2. 验证球队标识符
        if "home_team_name" not in df.columns or "away_team_name" not in df.columns:
            raise ValueError("❌ 缺少team_name列，无法进行滚动特征计算")
        logger.info("🏷️ 球队标识符验证通过")

        # 3. 按日期排序（重要：确保时序正确）
        df = df.sort_values("match_date").reset_index(drop=True)

        # 4. 使用现有数据直接计算必要的衍生指标
        df["home_goals_scored"] = df["home_score"]
        df["away_goals_scored"] = df["away_score"]
        df["home_goals_conceded"] = df["away_score"]
        df["away_goals_conceded"] = df["home_score"]
        df["home_goal_diff"] = df["home_score"] - df["away_score"]
        df["away_goal_diff"] = df["away_score"] - df["home_score"]
        df["home_xg_advantage"] = df["home_xg"] - df["away_xg"]
        df["away_xg_disadvantage"] = df["away_xg"] - df["home_xg"]

        # 5. 构建球队历史数据
        team_history = self.build_team_history(df)

        # 6. 应用滚动特征
        df = self.apply_rolling_features(df, team_history)

        # 7. 创建对战历史特征
        df = self.create_h2h_features(df)

        # 8. 选择安全的预测特征（无数据泄露）
        # 先获取所有现有特征
        all_features = list(df.columns)

        # 定义安全的前赛特征（无数据泄露）
        base_safe_features = [
            "match_id",
            "match_date",
            "year",
            "month",
            "day_of_week",
            "is_weekend",
            "league_id",
            "league_name",
            "home_team_name",
            "away_team_name",
            "result",
            "result_numeric",  # 仅用于验证，不在训练中使用
            # 赔率特征（如果存在）- 明确保留
            "home_win_odds",
            "draw_odds",
            "away_win_odds",
        ]

        # 确保所有基础列都被保留（即使数据为空）
        additional_features = []
        for col in ["home_win_odds", "draw_odds", "away_win_odds"]:
            if col in df.columns:
                additional_features.append(col)

        # 合并基础特征和额外特征
        base_safe_features.extend(additional_features)

        # 添加所有滚动特征（这些是安全的，因为是基于历史数据计算）
        rolling_features = [col for col in all_features if "last_" in col]

        # 合并特征列表
        safe_features = base_safe_features + rolling_features

        logger.info(f"   📊 基础特征: {len(base_safe_features)}")
        logger.info(f"   ⚡ 滚动特征: {len(rolling_features)}")
        logger.info(f"   🎯 总特征数: {len(safe_features)}")

        # 确保所有安全特征都存在
        existing_features = [f for f in safe_features if f in df.columns]

        # 创建最终数据集
        final_df = df[existing_features].copy()

        logger.info("✅ 安全特征数据集构建完成")
        logger.info(f"   输出特征数量: {len(final_df.columns)}")
        logger.info(f"   数据形状: {final_df.shape}")

        # 保存数据集
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        final_df.to_csv(output_path, index=False)

        file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
        logger.info(f"   保存文件: {output_path}")
        logger.info(f"   文件大小: {file_size:.2f} MB")

        return final_df

    def print_dataset_summary(self, df: pd.DataFrame):
        """打印数据集摘要"""
        print("\n" + "=" * 80)
        print("🏆 FOOTBALL PREDICTION ROLLING FEATURES DATASET v2")
        print("=" * 80)

        print("\n📊 数据集概况:")
        print(f"   数据形状: {df.shape}")
        print(f"   特征数量: {len(df.columns)}")
        print(f"   内存占用: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

        # 统计滚动特征
        rolling_feature_count = sum(1 for col in df.columns if "last_" in col)
        print(f"   滚动特征: {rolling_feature_count}")

        print("\n🔍 滚动特征分布:")
        window_sizes = [3, 5, 10]
        for window in window_sizes:
            count = sum(1 for col in df.columns if f"last_{window}_" in col)
            print(f"   Last {window} games: {count} 个特征")

        print("\n📋 数据样本 (前3场):")
        rolling_cols = [col for col in df.columns if "last_" in col][
            :8
        ]  # 显示前8个滚动特征

        sample_cols = [
            "match_id",
            "home_team_name",
            "away_team_name",
            "home_score",
            "away_score",
        ] + rolling_cols
        existing_cols = [col for col in sample_cols if col in df.columns]

        print(df[existing_cols].head(3).to_string(index=False))

        print("\n🎯 数据集用途:")
        print("   • 赛前预测模型训练")
        print("   • 时序特征工程分析")
        print("   • 球队表现趋势分析")
        print("   • 避免数据泄露的安全建模")

        print("=" * 80)


def main():
    """主函数"""
    # 初始化时序特征工程器
    engineer = RollingFeatureEngineer()

    try:
        # 构建安全的滚动特征数据集
        df = engineer.build_safe_feature_dataset(
            input_path="data/processed/features_with_teams.csv",
            output_path="data/processed/features_v2_rolling.csv",
        )

        # 打印数据集摘要
        engineer.print_dataset_summary(df)

        logger.info("🎉 Rolling Features Dataset v2 构建成功!")

    except Exception as e:
        logger.error(f"❌ 构建失败: {e}")
        raise


if __name__ == "__main__":
    main()
