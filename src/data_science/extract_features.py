#!/usr/bin/env python3
"""
足球数据特征提取脚本
Football Data Feature Extraction Script

从PostgreSQL数据库中提取FotMob采集的足球数据，并进行初步的特征工程和EDA分析。
"""

import sys
import os
from pathlib import Path
import logging
import json
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# 设置项目根路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 数据库配置
DATABASE_URL = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FootballDataExtractor:
    """足球数据提取器"""

    def __init__(self):
        self.conn = None
        self.data = None

    def connect_database(self):
        """连接数据库"""
        try:
            self.conn = psycopg2.connect(DATABASE_URL)
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def extract_match_data(self) -> pd.DataFrame:
        """提取比赛数据"""
        try:
            query = """
                SELECT
                    id
                    fotmob_id
                    home_team_id
                    away_team_id
                    home_score
                    away_score
                    status
                    match_date
                    data_completeness
                    stats
                    lineups
                    odds
                    match_metadata
                    created_at
                    updated_at
                    (SELECT name FROM teams WHERE id = home_team_id) as home_team_name
                    (SELECT name FROM teams WHERE id = away_team_id) as away_team_name
                FROM matches
                WHERE data_completeness = 'complete'
                AND home_score IS NOT NULL
                AND away_score IS NOT NULL
                ORDER BY match_date DESC
            """

            self.data = pd.read_sql_query(query, self.conn)
            logger.info(f"✅ 成功提取 {len(self.data)} 场比赛数据")

            return self.data

        except Exception as e:
            logger.error(f"❌ 数据提取失败: {e}")
            raise

    def parse_json_fields(self) -> pd.DataFrame:
        """解析JSONB字段并拉平特征"""
        try:
            # 解析stats字段
            stats_features = []
            lineups_features = []
            odds_features = []

            for _idx, row in self.data.iterrows():
                # 解析stats
                stats_data = {}
                if row["stats"]:
                    try:
                        stats_json = (
                            json.loads(row["stats"])
                            if isinstance(row["stats"], str)
                            else row["stats"]
                        )
                    except:
                        stats_json = {}

                    # 提取xG数据（从stats顶层获取）
                    home_xg = stats_json.get("home_xg")
                    away_xg = stats_json.get("away_xg")

                    stats_data["home_xg"] = (
                        float(home_xg) if home_xg is not None else 0.0
                    )
                    stats_data["away_xg"] = (
                        float(away_xg) if away_xg is not None else 0.0
                    )
                    stats_data["xg_difference"] = (
                        stats_data["home_xg"] - stats_data["away_xg"]
                    )
                    stats_data["xg_ratio"] = (
                        stats_data["away_xg"] / stats_data["home_xg"]
                        if stats_data["home_xg"] > 0
                        else 0
                    )

                    # 标记xG数据质量
                    stats_data["has_xg_data"] = (
                        home_xg is not None and away_xg is not None
                    )

                    # 提取其他统计数据
                    stats_data["stats_field_count"] = len(stats_json.keys())

                    # 检查是否有shotmap数据
                    has_shotmap = (
                        "shotmap" in stats_json and stats_json["shotmap"] is not None
                    )
                    stats_data["has_shotmap"] = has_shotmap

                    # 提取球员统计
                    player_stats = stats_json.get("playerStats", {})
                    if player_stats:
                        stats_data["has_player_stats"] = True
                        # 简单的球员数量统计
                        stats_data["player_count"] = (
                            len(player_stats.keys())
                            if isinstance(player_stats, dict)
                            else 0
                        )

                # 解析lineups
                lineup_data = {}
                if row["lineups"]:
                    try:
                        lineup_json = (
                            json.loads(row["lineups"])
                            if isinstance(row["lineups"], str)
                            else row["lineups"]
                        )
                    except:
                        lineup_json = {}

                    lineup_data["has_lineups"] = bool(lineup_json)
                    lineup_data["lineup_field_count"] = len(lineup_json.keys())

                    # 提取首发球员数量（从实际数据结构中获取）
                    home_team = lineup_json.get("homeTeam", {})
                    away_team = lineup_json.get("awayTeam", {})

                    home_lineup = home_team.get("lineUp", [])
                    away_lineup = away_team.get("lineUp", [])

                    lineup_data["home_lineup_count"] = (
                        len(home_lineup) if isinstance(home_lineup, list) else 0
                    )
                    lineup_data["away_lineup_count"] = (
                        len(away_lineup) if isinstance(away_lineup, list) else 0
                    )
                    lineup_data["total_lineup_players"] = (
                        lineup_data["home_lineup_count"]
                        + lineup_data["away_lineup_count"]
                    )

                # 解析odds
                odds_data = {}
                if row["odds"]:
                    try:
                        odds_json = (
                            json.loads(row["odds"])
                            if isinstance(row["odds"], str)
                            else row["odds"]
                        )
                    except:
                        odds_json = {}

                    odds_data["has_odds"] = bool(odds_json)
                    odds_data["odds_field_count"] = len(odds_json.keys())

                    # 提取赔率信息
                    if "bet365" in odds_json:
                        bet365_odds = odds_json["bet365"]
                        if isinstance(bet365_odds, dict) and "homeWin" in bet365_odds:
                            odds_data["home_odds"] = bet365_odds.get("homeWin", 0)
                            odds_data["draw_odds"] = bet365_odds.get("draw", 0)
                            odds_data["away_odds"] = bet365_odds.get("awayWin", 0)

                stats_features.append(stats_data)
                lineups_features.append(lineup_data)
                odds_features.append(odds_data)

            # 将解析的特征添加到DataFrame
            stats_df = pd.DataFrame(stats_features)
            lineups_df = pd.DataFrame(lineups_features)
            odds_df = pd.DataFrame(odds_features)

            # 合并数据
            result_df = self.data.reset_index(drop=True)
            result_df = pd.concat([result_df, stats_df, lineups_df, odds_df], axis=1)

            logger.info(f"✅ 特征解析完成，共 {len(result_df.columns)} 列特征")
            return result_df

        except Exception as e:
            logger.error(f"❌ 特征解析失败: {e}")
            raise

    def create_target_variable(self) -> pd.DataFrame:
        """创建目标变量"""
        try:
            df = self.data.copy()

            # 基于比分创建结果标签
            def determine_result(row):
                if row["home_score"] > row["away_score"]:
                    return "Home Win"
                elif row["home_score"] < row["away_score"]:
                    return "Away Win"
                else:
                    return "Draw"

            df["match_result"] = df.apply(determine_result, axis=1)

            logger.info("✅ 目标变量创建完成")
            return df

        except Exception as e:
            logger.error(f"❌ 目标变量创建失败: {e}")
            raise

    def generate_eda_report(self, df: pd.DataFrame) -> dict:
        """生成探索性数据分析报告"""
        try:
            report = {}

            # 基本数据统计
            report["basic_stats"] = {
                "total_matches": len(df)
                "date_range": {
                    "earliest": df["match_date"].min()
                    "latest": df["match_date"].max()
                }
            }

            # 数据质量分析
            report["data_quality"] = {
                "total_matches": len(df)
                "xg_data_available": df["has_xg_data"].sum()
                "xg_data_rate": df["has_xg_data"].sum() / len(df) * 100
                "lineups_available": df["has_lineups"].sum()
                "lineups_rate": df["has_lineups"].sum() / len(df) * 100
                "odds_available": df["has_odds"].sum()
                "odds_rate": df["has_odds"].sum() / len(df) * 100
                "home_xg_mean": df["home_xg"].mean()
                "away_xg_mean": df["away_xg"].mean()
            }

            # 目标变量分布
            result_distribution = df["match_result"].value_counts()
            report["target_distribution"] = {
                "home_win": result_distribution.get("Home Win", 0)
                "draw": result_distribution.get("Draw", 0)
                "away_win": result_distribution.get("Away Win", 0)
                "percentages": {
                    "home_win_pct": result_distribution.get("Home Win", 0)
                    / len(df)
                    * 100
                    "draw_pct": result_distribution.get("Draw", 0) / len(df) * 100
                    "away_win_pct": result_distribution.get("Away Win", 0)
                    / len(df)
                    * 100
                }
            }

            # xG数据统计
            report["xg_stats"] = {
                "home_xg_mean": df["home_xg"].mean()
                "home_xg_std": df["home_xg"].std()
                "away_xg_mean": df["away_xg"].mean()
                "away_xg_std": df["away_xg"].std()
                "xg_difference_mean": df["xg_difference"].mean()
                "total_xg_per_match": (df["home_xg"] + df["away_xg"]).mean()
            }

            logger.info("✅ EDA报告生成完成")
            return report

        except Exception as e:
            logger.error(f"❌ EDA报告生成失败: {e}")
            raise

    def close_connection(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("✅ 数据库连接已关闭")

    def run_extraction(self):
        """执行完整的数据提取流程"""
        try:
            logger.info("🚀 开始足球数据特征提取流程")

            # 1. 连接数据库
            self.connect_database()

            # 2. 提取原始数据
            logger.info("📊 步骤 1: 提取比赛数据...")
            self.extract_match_data()

            # 3. 解析JSON字段
            logger.info("🔧 步骤 2: 解析JSONB字段并拉平特征...")
            self.parse_json_fields()

            # 4. 创建目标变量
            logger.info("🎯 步骤 3: 创建目标变量...")
            final_data = self.create_target_variable()

            # 5. 生成EDA报告
            logger.info("📈 步骤 4: 生成探索性数据分析报告...")
            eda_report = self.generate_eda_report(final_data)

            # 6. 关闭连接
            self.close_connection()

            # 7. 保存处理后的数据
            output_path = project_root / "data" / "processed_features.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            final_data.to_csv(output_path, index=False)
            logger.info(f"💾 处理后的数据已保存到: {output_path}")

            return final_data, eda_report

        except Exception as e:
            logger.error(f"❌ 数据提取流程失败: {e}")
            raise


def main():
    """主函数"""
    extractor = FootballDataExtractor()

    try:
        # 运行数据提取
        processed_data, eda_report = extractor.run_extraction()

        # 打印报告
        print("\n" + "=" * 60)
        print("🎯 足球数据提取与探索性分析报告")
        print("=" * 60)

        print("\n📊 数据概览:")
        print(f"   总比赛数: {eda_report['basic_stats']['total_matches']}")
        print(
            f"   日期范围: {eda_report['basic_stats']['date_range']['earliest']} 到 {eda_report['basic_stats']['date_range']['latest']}"
        )

        print("\n🔍 数据质量:")
        print(f"   总比赛数: {eda_report['data_quality']['total_matches']}")
        print(
            f"   xG数据可用性: {eda_report['data_quality']['xg_data_available']} 场比赛 ({eda_report['data_quality']['xg_data_rate']:.1f}%)"
        )
        print(
            f"   完整阵容数据: {eda_report['data_quality']['lineups_available']} 场比赛 ({eda_report['data_quality']['lineups_rate']:.1f}%)"
        )
        print(
            f"   完整赔率数据: {eda_report['data_quality']['odds_available']} 场比赛 ({eda_report['data_quality']['odds_rate']:.1f}%)"
        )

        print("\n🎯 目标变量分布:")
        print(
            f"   主队获胜: {eda_report['target_distribution']['home_win']} ({eda_report['target_distribution']['percentages']['home_win_pct']:.1f}%)"
        )
        print(
            f"   平局: {eda_report['target_distribution']['draw']} ({eda_report['target_distribution']['percentages']['draw_pct']:.1f}%)"
        )
        print(
            f"   客队获胜: {eda_report['target_distribution']['away_win']} ({eda_report['target_distribution']['percentages']['away_win_pct']:.1f}%)"
        )

        print("\n⚽ xG数据统计:")
        print(f"   主队xG均值: {eda_report['xg_stats']['home_xg_mean']:.2f}")
        print(f"   客队xG均值: {eda_report['xg_stats']['away_xg_mean']:.2f}")
        print(f"   xG差异均值: {eda_report['xg_stats']['xg_difference_mean']:.2f}")
        print(f"   每场总xG: {eda_report['xg_stats']['total_xg_per_match']:.2f}")

        print("\n📋 DataFrame头部预览:")
        print(
            processed_data[
                [
                    "fotmob_id"
                    "home_team_name"
                    "away_team_name"
                    "home_score"
                    "away_score"
                    "match_result"
                    "home_xg"
                    "away_xg"
                    "xg_difference"
                    "has_xg_data"
                    "has_lineups"
                ]
            ].head()
        )

        print("\n" + "=" * 60)
        print("✅ 数据提取和EDA分析完成！")
        print("📁 处理后的数据已保存到 data/processed_features.csv")
        print("🚀 准备进行特征工程...")
        print("=" * 60)

        return processed_data

    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
