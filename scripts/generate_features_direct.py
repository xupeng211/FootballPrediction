#!/usr/bin/env python3
"""
直接从 raw_match_data 生成特征的脚本
为 2942 条原始数据计算机器学习特征
"""

import sys
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入数据库连接
import sqlalchemy
from sqlalchemy import create_engine, text
from sklearn.preprocessing import LabelEncoder
import joblib
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DirectFeatureGenerator:
    """直接从原始数据生成特征的类"""

    def __init__(self):
        self.engine = create_engine(
            "postgresql://postgres:postgres-dev-password@db:5432/football_prediction"
        )
        self.team_stats = defaultdict(
            lambda: {
                "matches_played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
                "recent_form": [],
                "last_5": [],
            }
        )
        self.matches = []
        self.features = []

    def load_raw_data(self):
        """加载原始比赛数据"""
        try:
            logger.info("🔍 加载原始比赛数据...")

            query = """
            SELECT match_data, collected_at
            FROM raw_match_data
            WHERE match_data::jsonb->'status'->>'finished' = 'true'
            AND match_data::jsonb->'status'->>'scoreStr' IS NOT NULL
            ORDER BY collected_at ASC
            """

            df = pd.read_sql_query(query, self.engine)
            logger.info(f"✅ 成功加载 {len(df)} 条已完成比赛记录")

            # 处理数据（已经是字典格式，不需要JSON解析）
            for _, row in df.iterrows():
                try:
                    match_data = row["match_data"]
                    # 如果是字符串，尝试解析为JSON
                    if isinstance(match_data, str):
                        match_data = json.loads(match_data)

                    if self._is_valid_match(match_data):
                        self.matches.append(
                            {
                                "raw_data": match_data,
                                "collected_at": row["collected_at"],
                            }
                        )
                except Exception as e:
                    logger.warning(f"处理比赛数据时出错: {str(e)}")
                    continue

            logger.info(f"✅ 成功解析 {len(self.matches)} 条有效比赛")
            return self.matches

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {str(e)}")
            return []

    def _is_valid_match(self, match_data):
        """检查比赛数据是否有效"""
        try:
            status = match_data.get("status", {})

            # 检查是否已完成
            if not status.get("finished", False):
                return False

            # 检查比分字符串
            score_str = status.get("scoreStr", "")
            if not score_str or "-" not in score_str:
                return False

            # 检查队伍名称 - 优先使用新字段
            home_team_name = match_data.get("home_team_name") or match_data.get(
                "raw_data", {}
            ).get("home", {}).get("name")
            away_team_name = match_data.get("away_team_name") or match_data.get(
                "raw_data", {}
            ).get("away", {}).get("name")

            if not all([home_team_name, away_team_name]):
                return False

            return True
        except Exception as e:
            logger.warning(f"验证比赛数据时出错: {str(e)}")
            return False

    def extract_result(self, match_data):
        """提取比赛结果"""
        try:
            status = match_data.get("status", {})
            score_str = status.get("scoreStr", "")

            if not score_str:
                return None

            # 解析比分
            parts = score_str.split(" - ")
            if len(parts) != 2:
                return None

            home_score, away_score = map(int, parts)

            # 返回结果：1=主队胜，0=平局，-1=客队胜
            if home_score > away_score:
                return 1
            elif home_score < away_score:
                return -1
            else:
                return 0

        except:
            return None

    def extract_team_names(self, match_data):
        """提取队伍名称"""
        home_team = match_data.get("home_team", {})
        away_team = match_data.get("away_team", {})
        return home_team.get("name", "Unknown"), away_team.get("name", "Unknown")

    def calculate_team_statistics(self):
        """计算所有球队的统计数据"""
        logger.info("📊 计算球队统计数据...")

        # 按时间顺序处理比赛
        for match in self.matches:
            match_data = match["raw_data"]

            # 提取队伍名称
            home_team, away_team = self.extract_team_names(match_data)
            result = self.extract_result(match_data)

            if result is None:
                continue

            # 更新主队统计
            self._update_team_stats(home_team, result, True)
            # 更新客队统计
            self._update_team_stats(away_team, result, False)

        logger.info(f"✅ 完成统计计算，涉及 {len(self.team_stats)} 支球队")

    def _update_team_stats(self, team_name, result, is_home):
        """更新单支球队统计"""
        stats = self.team_stats[team_name]
        stats["matches_played"] += 1

        # 记录结果
        stats["recent_form"].append(result)
        stats["last_5"].append(result)

        # 更新胜负平统计
        if result == 1:  # 胜
            stats["wins"] += 1
            stats["points"] += 3
        elif result == 0:  # 平
            stats["draws"] += 1
            stats["points"] += 1
        else:  # 负
            stats["losses"] += 1

        # 只保留最近5场记录
        if len(stats["last_5"]) > 5:
            stats["last_5"].pop(0)
        if len(stats["recent_form"]) > 10:  # 保留最近10场
            stats["recent_form"].pop(0)

    def extract_goals_stats(self, match_data):
        """提取进球统计"""
        try:
            status = match_data.get("status", {})
            score_str = status.get("scoreStr", "")

            if not score_str:
                return 0, 0

            parts = score_str.split(" - ")
            if len(parts) != 2:
                return 0, 0

            home_goals, away_goals = map(int, parts)
            return home_goals, away_goals

        except:
            return 0, 0

    def generate_features_for_match(
        self, match_data, home_team, away_team, collected_at
    ):
        """为单场比赛生成特征"""
        try:
            # 获取球队统计
            home_stats = self.team_stats[home_team]
            away_stats = self.team_stats[away_team]

            # 提取进球数据
            home_goals, away_goals = self.extract_goals_stats(match_data)

            # 基础特征
            features = {
                "home_team_name": home_team,
                "away_team_name": away_team,
                "league_name": match_data.get("league_name", ""),
                "match_time": match_data.get("match_time", ""),
                "collection_date": collected_at,
                # 主队特征
                "home_matches_played": home_stats["matches_played"],
                "home_wins": home_stats["wins"],
                "home_draws": home_stats["draws"],
                "home_losses": home_stats["losses"],
                "home_points": home_stats["points"],
                "home_win_rate": home_stats["wins"]
                / max(1, home_stats["matches_played"]),
                "home_recent_form_points": sum(max(0, r) for r in home_stats["last_5"]),
                "home_last_5_avg_goals": self._calc_avg_goals(
                    home_stats["last_5"], match_data, True
                ),
                "home_goal_diff": self._calc_goal_diff(home_stats["last_5"]),
                # 客队特征
                "away_matches_played": away_stats["matches_played"],
                "away_wins": away_stats["wins"],
                "away_draws": away_stats["draws"],
                "away_losses": away_stats["losses"],
                "away_points": away_stats["points"],
                "away_win_rate": away_stats["wins"]
                / max(1, away_stats["matches_played"]),
                "away_recent_form_points": sum(max(0, r) for r in away_stats["last_5"]),
                "away_last_5_avg_goals": self._calc_avg_goals(
                    away_stats["last_5"], match_data, False
                ),
                "away_goal_diff": self._calc_goal_diff(away_stats["last_5"]),
                # 比赛特征
                "match_result": self.extract_result(match_data),
                "home_score": home_goals,
                "away_score": away_goals,
                "total_goals": home_goals + away_goals,
                "goal_difference": home_goals - away_goals,
            }

            return features

        except Exception as e:
            logger.warning(f"生成特征时出错: {str(e)}")
            return None

    def _calc_avg_goals(self, recent_5, match_data, is_home):
        """计算最近5场平均进球"""
        if len(recent_5) == 0:
            return 0.0

        # 对于最近比赛，从历史数据中提取进球，或使用当前比赛数据
        total_goals = 0
        valid_matches = 0

        # 如果队伍有足够历史，从历史数据计算
        if is_home and "home_score" in str(match_data):
            total_goals += match_data.get("status", {}).get("homeScore", 0)
            valid_matches = max(1, len(recent_5))
        elif not is_home and "away_score" in str(match_data):
            total_goals += match_data.get("status", {}).get("awayScore", 0)
            valid_matches = max(1, len(recent_5))

        return total_goals / valid_matches if valid_matches > 0 else 0.0

    def _calc_goal_diff(self, recent_5):
        """计算最近5场净胜球"""
        return sum(recent_5) / max(1, len(recent_5)) if recent_5 else 0.0

    def generate_all_features(self):
        """为所有比赛生成特征"""
        logger.info("🔄 开始生成特征数据...")

        # 首先计算统计
        self.calculate_team_statistics()

        # 为每场比赛生成特征
        for match in self.matches:
            match_data = match["raw_data"]
            home_team, away_team = self.extract_team_names(match_data)
            collected_at = match["collected_at"]

            features = self.generate_features_for_match(
                match_data, home_team, away_team, collected_at
            )
            if features:
                self.features.append(features)

        logger.info(f"✅ 特征生成完成，共生成 {len(self.features)} 条特征记录")
        return self.features

    def save_features(self):
        """保存特征数据"""
        if not self.features:
            logger.warning("⚠️ 没有特征数据可保存")
            return

        df = pd.DataFrame(self.features)

        # 删除无效记录
        df = df.dropna()
        logger.info(f"✅ 清理后保留 {len(df)} 条有效特征记录")

        # 保存到文件
        features_file = "/app/data/features_direct.csv"
        df.to_csv(features_file, index=False)
        logger.info(f"💾 特征数据已保存到: {features_file}")

        # 显示特征统计
        logger.info("📊 特征数据统计:")
        logger.info(f"  - 总记录数: {len(df)}")
        logger.info(f"  - 特征维度: {df.shape[1]}")
        logger.info(f"  - 主队胜率: {df['home_win_rate'].mean():.3f}")
        logger.info(f"  - 平均进球数: {df['total_goals'].mean():.2f}")

        return df


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🎯 直接特征生成器启动")
    logger.info("📊 目标：为 2942 条原始数据生成 ML 特征")
    logger.info("=" * 60)

    # 创建特征生成器
    generator = DirectFeatureGenerator()

    # 1. 加载数据
    raw_data = generator.load_raw_data()
    if not raw_data:
        logger.error("❌ 数据加载失败，终止")
        return

    # 2. 生成特征
    features_data = generator.generate_all_features()

    # 3. 保存特征
    if features_data and len(features_data) > 0:
        generator.save_features()
        logger.info("🎉 特征生成任务完成！")
        logger.info(f"📈 生成了 {len(features_data)} 条特征记录，可用于模型训练")
    else:
        logger.error("❌ 特征生成失败")


if __name__ == "__main__":
    main()
