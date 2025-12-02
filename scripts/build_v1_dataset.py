#!/usr/bin/env python3
"""
首席AI科学家专用 - V1数据集构建器
基于高质量数据构建ML训练特征集
"""

import subprocess
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class V1DatasetBuilder:
    """V1数据集构建器"""

    def __init__(self):
        self.data = None
        self.features_df = None

    def load_match_data(self):
        """从Silver Layer视图加载比赛数据"""
        try:
            logger.info("📊 从view_match_features加载比赛数据...")

            # 使用docker exec查询数据
            cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-c",
                """
                SELECT
                    match_date,
                    home_team_name,
                    away_team_name,
                    home_score,
                    away_score,
                    home_xg,
                    away_xg,
                    venue,
                    referee
                FROM view_match_features
                WHERE home_score IS NOT NULL
                  AND away_score IS NOT NULL
                ORDER BY match_date, home_team_name, away_team_name;
                """,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"❌ 数据加载失败: {result.stderr}")
                return False

            # 解析CSV输出
            lines = result.stdout.strip().split("\n")
            if len(lines) < 3:
                logger.error("❌ 没有足够的数据行")
                return False

            # 跳过表头和分隔符
            data_lines = [line for line in lines[2:] if line.strip()]

            # 解析数据
            data = []
            for line in data_lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 9:
                    try:
                        data.append(
                            {
                                "match_date": parts[0],
                                "home_team": parts[1],
                                "away_team": parts[2],
                                "home_score": int(parts[3]) if parts[3] else None,
                                "away_score": int(parts[4]) if parts[4] else None,
                                "home_xg": (
                                    float(parts[5])
                                    if parts[5] and parts[5] != ""
                                    else None
                                ),
                                "away_xg": (
                                    float(parts[6])
                                    if parts[6] and parts[6] != ""
                                    else None
                                ),
                                "venue": parts[7],
                                "referee": parts[8],
                            }
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(f"⚠️ 跳过无效行: {line} - {e}")
                        continue

            self.data = pd.DataFrame(data)
            self.data["match_date"] = pd.to_datetime(self.data["match_date"])
            self.data = self.data.sort_values("match_date")

            logger.info(f"✅ 加载了 {len(self.data)} 场比赛")
            logger.info(
                f"📅 时间范围: {self.data['match_date'].min()} 到 {self.data['match_date'].max()}"
            )
            logger.info(f"⚽ xG数据覆盖: {self.data['home_xg'].notna().sum()} 场比赛")

            return True

        except Exception as e:
            logger.error(f"❌ 数据加载异常: {e}")
            return False

    def build_rolling_features(self):
        """构建滚动特征"""
        logger.info("🔧 构建滚动特征...")

        # 为每支球队构建历史数据
        teams = pd.concat([self.data["home_team"], self.data["away_team"]]).unique()

        all_team_stats = {}

        for team in teams:
            # 获取该球队所有比赛（主客队都要考虑）
            home_games = self.data[self.data["home_team"] == team].copy()
            away_games = self.data[self.data["away_team"] == team].copy()

            # 主队数据
            home_games["goals_scored"] = home_games["home_score"]
            home_games["goals_conceded"] = home_games["away_score"]
            home_games["xg_created"] = home_games["home_xg"]
            home_games["xg_conceded"] = home_games["away_xg"]

            # 客队数据
            away_games["goals_scored"] = away_games["away_score"]
            away_games["goals_conceded"] = away_games["home_score"]
            away_games["xg_created"] = away_games["away_xg"]
            away_games["xg_conceded"] = away_games["home_xg"]

            # 统一格式
            team_games = pd.concat([home_games, away_games], ignore_index=True)
            team_games = team_games.sort_values("match_date")

            # 计算滚动统计（过去5场）
            windows = [5]
            for window in windows:
                team_games[f"avg_goals_scored_{window}"] = (
                    team_games["goals_scored"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)  # 防止数据泄露
                )

                team_games[f"avg_goals_conceded_{window}"] = (
                    team_games["goals_conceded"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)
                )

                team_games[f"avg_xg_created_{window}"] = (
                    team_games["xg_created"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)
                )

                team_games[f"avg_xg_conceded_{window}"] = (
                    team_games["xg_conceded"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)
                )

                team_games[f"games_played_{window}"] = (
                    team_games["goals_scored"]
                    .rolling(window, min_periods=1)
                    .count()
                    .shift(1)
                )

            all_team_stats[team] = team_games[
                ["match_date"]
                + [f"avg_goals_scored_{w}" for w in windows]
                + [f"avg_goals_conceded_{w}" for w in windows]
                + [f"avg_xg_created_{w}" for w in windows]
                + [f"avg_xg_conceded_{w}" for w in windows]
                + [f"games_played_{w}" for w in windows]
            ]

        # 将统计信息合并到原始数据
        logger.info("🔄 合并统计信息到原始数据...")

        # 添加主队特征
        home_features = []
        for _, row in self.data.iterrows():
            team_stats = all_team_stats[row["home_team"]]
            team_row = team_stats[team_stats["match_date"] <= row["match_date"]]

            if not team_row.empty:
                latest_stats = team_row.iloc[-1]
                feature_dict = {
                    "home_avg_goals_scored_5": latest_stats.get(
                        "avg_goals_scored_5", 0
                    ),
                    "home_avg_goals_conceded_5": latest_stats.get(
                        "avg_goals_conceded_5", 0
                    ),
                    "home_avg_xg_created_5": latest_stats.get("avg_xg_created_5", 0),
                    "home_avg_xg_conceded_5": latest_stats.get("avg_xg_conceded_5", 0),
                    "home_games_played_5": latest_stats.get("games_played_5", 0),
                }
            else:
                feature_dict = {
                    "home_avg_goals_scored_5": 0,
                    "home_avg_goals_conceded_5": 0,
                    "home_avg_xg_created_5": 0,
                    "home_avg_xg_conceded_5": 0,
                    "home_games_played_5": 0,
                }

            home_features.append(feature_dict)

        # 添加客队特征
        away_features = []
        for _, row in self.data.iterrows():
            team_stats = all_team_stats[row["away_team"]]
            team_row = team_stats[team_stats["match_date"] <= row["match_date"]]

            if not team_row.empty:
                latest_stats = team_row.iloc[-1]
                feature_dict = {
                    "away_avg_goals_scored_5": latest_stats.get(
                        "avg_goals_scored_5", 0
                    ),
                    "away_avg_goals_conceded_5": latest_stats.get(
                        "avg_goals_conceded_5", 0
                    ),
                    "away_avg_xg_created_5": latest_stats.get("avg_xg_created_5", 0),
                    "away_avg_xg_conceded_5": latest_stats.get("avg_xg_conceded_5", 0),
                    "away_games_played_5": latest_stats.get("games_played_5", 0),
                }
            else:
                feature_dict = {
                    "away_avg_goals_scored_5": 0,
                    "away_avg_goals_conceded_5": 0,
                    "away_avg_xg_created_5": 0,
                    "away_avg_xg_conceded_5": 0,
                    "away_games_played_5": 0,
                }

            away_features.append(feature_dict)

        # 合并特征
        self.features_df = self.data.copy()
        home_df = pd.DataFrame(home_features)
        away_df = pd.DataFrame(away_features)

        self.features_df = pd.concat(
            [
                self.features_df.reset_index(drop=True),
                home_df.reset_index(drop=True),
                away_df.reset_index(drop=True),
            ],
            axis=1,
        )

        logger.info(f"✅ 特征构建完成，维度: {self.features_df.shape}")

    def build_target(self):
        """构建目标变量"""
        logger.info("🎯 构建目标变量...")

        def determine_result(row):
            if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
                return None
            elif row["home_score"] > row["away_score"]:
                return 2  # 主胜
            elif row["home_score"] < row["away_score"]:
                return 0  # 客胜
            else:
                return 1  # 平局

        self.features_df["result"] = self.features_df.apply(determine_result, axis=1)

        # 移除没有结果的比赛
        self.features_df = self.features_df.dropna(subset=["result"])
        self.features_df["result"] = self.features_df["result"].astype(int)

        logger.info(f"✅ 目标变量构建完成: {len(self.features_df)} 场有效比赛")

    def save_dataset(self):
        """保存数据集"""
        try:
            # 创建目录
            output_dir = Path("data/training_sets")
            output_dir.mkdir(parents=True, exist_ok=True)

            # 保存完整数据集
            output_file = output_dir / "v1_dataset.csv"
            self.features_df.to_csv(output_file, index=False)

            logger.info(f"💾 数据集已保存到: {output_file}")
            logger.info(f"📊 数据集维度: {self.features_df.shape}")

            # 显示数据集信息
            feature_cols = [
                col
                for col in self.features_df.columns
                if "avg_" in col or "games_" in col
            ]
            logger.info(f"🔧 特征列数: {len(feature_cols)}")
            logger.info(
                f"🎯 目标分布: {self.features_df['result'].value_counts().to_dict()}"
            )

            # 显示样本
            logger.info("📋 数据样本:")
            sample_cols = [
                "match_date",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "result",
            ] + feature_cols[:3]
            logger.info(self.features_df[sample_cols].head().to_string())

            return True

        except Exception as e:
            logger.error(f"❌ 保存数据集失败: {e}")
            return False

    def run(self):
        """执行完整的数据集构建流程"""
        logger.info("🚀 启动首席AI科学家 - V1数据集构建器")
        start_time = datetime.now()

        # 1. 加载数据
        if not self.load_match_data():
            return False

        # 2. 构建特征
        self.build_rolling_features()

        # 3. 构建目标
        self.build_target()

        # 4. 保存数据集
        success = self.save_dataset()

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")

        if success:
            logger.info("🎉 V1数据集构建完成！")
            logger.info("📈 准备进行模型训练...")
            logger.info("⏭️  下一步: python src/models/train_v1_xgboost.py")

        return success


def main():
    """主函数"""
    try:
        builder = V1DatasetBuilder()
        success = builder.run()

        if success:
            logger.info("✅ V1数据集构建成功")
            return 0
        else:
            logger.error("❌ V1数据集构建失败")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
