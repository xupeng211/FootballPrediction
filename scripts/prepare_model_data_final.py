#!/usr/bin/env python3
"""
最终训练数据准备脚本
首席AI科学家: Gold Standard数据准备

Purpose: 为V1.1实战级预测模型准备高质量训练数据
"""

import asyncio
import logging
import sys
import json
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class ModelDataPreparer:
    """最终训练数据准备器"""

    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres-dev-password',
            database='football_prediction'
        )

    def get_team_mapping(self) -> Dict[int, str]:
        """获取团队ID到名称的映射"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT id, name FROM teams ORDER BY id")
                return {row[0]: row[1] for row in cur.fetchall()}
        except Exception as e:
            logger.error(f"获取团队映射失败: {e}")
            return {}

    def calculate_team_form_features(self, team_id: int, match_date: datetime,
                                   matches_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算球队状态特征 - 过去5场比赛的平均表现

        Args:
            team_id: 球队ID
            match_date: 当前比赛日期
            matches_df: 所有比赛数据DataFrame

        Returns:
            特征字典
        """
        try:
            # 获取该球队过去5场比赛（主客场都算）
            past_matches = matches_df[
                ((matches_df['home_team_id'] == team_id) |
                 (matches_df['away_team_id'] == team_id)) &
                (matches_df['match_date'] < match_date)
            ].sort_values('match_date', ascending=False).head(5)

            if past_matches.empty:
                return {
                    'avg_xg_created': 0.0,
                    'avg_xg_conceded': 0.0,
                    'win_rate': 0.0,
                    'recent_form': 0.0
                }

            # 计算xG平均值
            xg_created = []
            xg_conceded = []
            wins = 0
            total_matches = len(past_matches)

            for _, match in past_matches.iterrows():
                is_home = match['home_team_id'] == team_id

                if is_home:
                    xg_created.append(match.get('xg_home', 0))
                    xg_conceded.append(match.get('xg_away', 0))

                    # 判断胜负
                    if match['home_score'] > match['away_score']:
                        wins += 1
                else:
                    xg_created.append(match.get('xg_away', 0))
                    xg_conceded.append(match.get('xg_home', 0))

                    # 判断胜负
                    if match['away_score'] > match['home_score']:
                        wins += 1

            # 计算最近表现（更近的比赛权重更高）
            recent_scores = []
            for i, (_, match) in enumerate(past_matches.iterrows()):
                is_home = match['home_team_id'] == team_id

                if is_home:
                    goal_diff = match['home_score'] - match['away_score']
                    xg_diff = match.get('xg_home', 0) - match.get('xg_away', 0)
                else:
                    goal_diff = match['away_score'] - match['home_score']
                    xg_diff = match.get('xg_away', 0) - match.get('xg_home', 0)

                # 综合评分（进球差 + xG差）
                score = goal_diff + xg_diff
                # 越近的比赛权重越高
                weighted_score = score * (5 - i) / 5
                recent_scores.append(weighted_score)

            return {
                'avg_xg_created': np.mean(xg_created) if xg_created else 0.0,
                'avg_xg_conceded': np.mean(xg_conceded) if xg_conceded else 0.0,
                'win_rate': wins / total_matches if total_matches > 0 else 0.0,
                'recent_form': np.mean(recent_scores) if recent_scores else 0.0
            }

        except Exception as e:
            logger.error(f"计算球队状态特征失败: {e}")
            return {
                'avg_xg_created': 0.0,
                'avg_xg_conceded': 0.0,
                'win_rate': 0.0,
                'recent_form': 0.0
            }

    def determine_match_result(self, home_score: int, away_score: int) -> str:
        """确定比赛结果（3分类）"""
        if home_score > away_score:
            return 'Home Win'
        elif home_score < away_score:
            return 'Away Win'
        else:
            return 'Draw'

    def extract_training_data(self) -> pd.DataFrame:
        """
        提取训练数据

        Returns:
            包含特征和目标的DataFrame
        """
        logger.info("🚀 开始提取最终训练数据...")

        try:
            # 从数据库获取所有FBref数据
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        id, home_team_id, away_team_id, home_score, away_score,
                        match_date, stats, data_completeness, season
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    ORDER BY match_date ASC
                """)

                matches = cur.fetchall()
                logger.info(f"📊 获取到 {len(matches)} 场比赛数据")

            # 转换为DataFrame
            matches_data = []
            for match in matches:
                stats_json = match[6]
                xg_home = 0.0
                xg_away = 0.0

                try:
                    if isinstance(stats_json, str):
                        stats = json.loads(stats_json)
                    else:
                        stats = stats_json

                    xg_home = float(stats.get('xg_home', 0.0))
                    xg_away = float(stats.get('xg_away', 0.0))

                except Exception as e:
                    logger.warning(f"解析xG数据失败 (比赛ID {match[0]}): {e}")
                    continue

                # 只保留有xG数据的比赛
                if xg_home > 0 or xg_away > 0:
                    matches_data.append({
                        'match_id': match[0],
                        'home_team_id': match[1],
                        'away_team_id': match[2],
                        'home_score': match[3],
                        'away_score': match[4],
                        'match_date': match[5],
                        'xg_home': xg_home,
                        'xg_away': xg_away,
                        'season': match[8] or 'unknown'
                    })

            matches_df = pd.DataFrame(matches_data)
            logger.info(f"✅ 筛选后保留 {len(matches_df)} 场有xG数据的比赛")

            if matches_df.empty:
                logger.error("❌ 没有找到有效训练数据")
                return pd.DataFrame()

            # 计算特征
            logger.info("🔧 开始计算球队状态特征...")
            training_data = []

            team_mapping = self.get_team_mapping()

            for idx, match in matches_df.iterrows():
                try:
                    # 计算主队特征
                    home_features = self.calculate_team_form_features(
                        match['home_team_id'],
                        match['match_date'],
                        matches_df
                    )

                    # 计算客队特征
                    away_features = self.calculate_team_form_features(
                        match['away_team_id'],
                        match['match_date'],
                        matches_df
                    )

                    # 确定比赛结果
                    result = self.determine_match_result(
                        match['home_score'],
                        match['away_score']
                    )

                    # 构建训练样本
                    sample = {
                        'match_id': match['match_id'],
                        'home_team_id': match['home_team_id'],
                        'away_team_id': match['away_team_id'],
                        'match_date': match['match_date'],

                        # 核心特征 - 当前比赛的xG
                        'home_xg': match['xg_home'],
                        'away_xg': match['xg_away'],
                        'xg_diff': match['xg_home'] - match['xg_away'],

                        # 历史状态特征 - 过去5场比赛
                        'home_avg_xg_created': home_features['avg_xg_created'],
                        'home_avg_xg_conceded': home_features['avg_xg_conceded'],
                        'home_win_rate': home_features['win_rate'],
                        'home_recent_form': home_features['recent_form'],

                        'away_avg_xg_created': away_features['avg_xg_created'],
                        'away_avg_xg_conceded': away_features['avg_xg_conceded'],
                        'away_win_rate': away_features['win_rate'],
                        'away_recent_form': away_features['recent_form'],

                        # 对比特征
                        'xg_created_diff': home_features['avg_xg_created'] - away_features['avg_xg_created'],
                        'xg_conceded_diff': home_features['avg_xg_conceded'] - away_features['avg_xg_conceded'],
                        'win_rate_diff': home_features['win_rate'] - away_features['win_rate'],
                        'form_diff': home_features['recent_form'] - away_features['recent_form'],

                        # 目标变量
                        'result': result,
                        'home_score': match['home_score'],
                        'away_score': match['away_score'],
                        'goal_difference': match['home_score'] - match['away_score'],
                        'season': match['season']
                    }

                    training_data.append(sample)

                    if (idx + 1) % 100 == 0:
                        logger.info(f"📊 已处理 {idx + 1}/{len(matches_df)} 场比赛")

                except Exception as e:
                    logger.error(f"处理比赛 {match['match_id']} 失败: {e}")
                    continue

            training_df = pd.DataFrame(training_data)
            logger.info(f"✅ 训练数据准备完成: {len(training_df)} 个样本, {len(training_df.columns)} 个特征")

            # 显示数据质量报告
            logger.info("📈 数据质量报告:")
            logger.info(f"   - 样本数量: {len(training_df)}")
            logger.info(f"   - 特征数量: {len(training_df.columns) - 3}")  # 减去目标变量
            logger.info(f"   - 比赛结果分布:")
            for result_type, count in training_df['result'].value_counts().items():
                percentage = count / len(training_df) * 100
                logger.info(f"     {result_type}: {count} ({percentage:.1f}%)")

            return training_df

        except Exception as e:
            logger.error(f"❌ 提取训练数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def save_training_data(self, training_df: pd.DataFrame, filename: str = None) -> str:
        """
        保存训练数据到文件

        Args:
            training_df: 训练数据DataFrame
            filename: 文件名（可选）

        Returns:
            保存的文件路径
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"training_data_v1_final_{timestamp}.csv"

            data_dir = Path(__file__).parent.parent / "data" / "training"
            data_dir.mkdir(parents=True, exist_ok=True)

            file_path = data_dir / filename
            training_df.to_csv(file_path, index=False, encoding='utf-8')

            logger.info(f"✅ 训练数据已保存: {file_path}")
            logger.info(f"📊 文件大小: {file_path.stat().st_size:,} 字节")

            return str(file_path)

        except Exception as e:
            logger.error(f"❌ 保存训练数据失败: {e}")
            return None

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


def main():
    """主函数"""
    logger.info("🚀 首席AI科学家 - 开始准备最终训练数据")
    logger.info("=" * 70)

    try:
        preparer = ModelDataPreparer()

        # 提取训练数据
        training_df = preparer.extract_training_data()

        if training_df.empty:
            logger.error("❌ 训练数据准备失败：没有有效数据")
            return False

        # 保存训练数据
        file_path = preparer.save_training_data(training_df)

        if file_path:
            logger.info("🎉 最终训练数据准备完成!")
            logger.info(f"📄 文件路径: {file_path}")
            logger.info(f"🎯 下一步: 运行模型训练脚本")
            return True
        else:
            logger.error("❌ 训练数据保存失败")
            return False

    except Exception as e:
        logger.error(f"💥 数据准备过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)