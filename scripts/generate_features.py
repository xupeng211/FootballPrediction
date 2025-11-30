#!/usr/bin/env python3
"""
特征生成脚本 / Feature Generation Script

该脚本从Silver层数据库加载比赛数据，计算机器学习所需的特征，并保存为CSV文件。

This script loads match data from Silver layer database, calculates features for machine learning,
and saves them as a CSV file.

使用方法 / Usage:
    python scripts/generate_features.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

# 尝试加载.env文件
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        break
else:
    pass

# 导入模块
try:
    import pandas as pd
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from src.features.simple_feature_calculator import (
        SimpleFeatureCalculator,
        load_data_from_database,
        save_features_to_csv,
    )
except ImportError:
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FeatureGenerator:
    """特征生成器."""

    def __init__(self):
        """初始化特征生成器."""
        self.matches_df = None
        self.features_df = None
        self.calculator = None

    def load_data(self):
        """从数据库加载比赛数据."""
        logger.info("=" * 60)
        logger.info("🔍 开始加载比赛数据")
        logger.info("=" * 60)

        try:
            # 优先读取环境变量 DATABASE_URL
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                # 回退逻辑：使用单独的环境变量
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "football_prediction_2024")
                db_host = os.getenv("DB_HOST", "db")  # Docker里是 db，不是localhost
                db_port = os.getenv("DB_PORT", "5432")
                db_name = os.getenv("POSTGRES_DB", "football_prediction")
                db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            logger.info(
                f"使用数据库连接: {db_url.split('@')[1] if '@' in db_url else db_url}"
            )

            # Pandas 需要同步驱动，移除 asyncpg
            if "+asyncpg" in db_url:
                db_url = db_url.replace("+asyncpg", "")
                logger.info("已将asyncpg驱动替换为psycopg2以适配Pandas")

            # 连接数据库并查询数据
            conn = psycopg2.connect(db_url)

            query = """
            SELECT
                m.id as match_id,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                m.status,
                m.match_date,
                t1.name as home_team_name,
                t2.name as away_team_name
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE m.status = 'FINISHED'
            ORDER BY m.match_date ASC
            """

            logger.info("执行SQL查询...")
            self.matches_df = pd.read_sql_query(query, conn)
            conn.close()

            logger.info(f"✅ 成功加载 {len(self.matches_df)} 条比赛记录")

            # 显示数据基本信息
            logger.info(
                f"📅 数据时间范围: {self.matches_df['match_date'].min()} 到 {self.matches_df['match_date'].max()}"
            )
            logger.info(
                f"🏆 涉及球队数: {len(set(self.matches_df['home_team_id'].unique()) | set(self.matches_df['away_team_id'].unique()))}"
            )

            # 显示前几行数据
            logger.info("📊 数据预览:")

            return True

        except Exception:
            logger.error(f"❌ 加载数据失败: {e}")
            return False

    def calculate_features(self):
        """计算特征."""
        logger.info("=" * 60)
        logger.info("⚙️  开始计算特征")
        logger.info("=" * 60)

        try:
            # 创建特征计算器
            self.calculator = SimpleFeatureCalculator(self.matches_df)

            # 生成特征数据集
            logger.info("🔄 生成特征数据集...")
            self.features_df = self.calculator.generate_features_dataset()

            logger.info(f"✅ 特征计算完成，生成了 {len(self.features_df)} 条特征记录")

            # 显示特征统计信息
            logger.info("📈 特征统计信息:")

            return True

        except Exception:
            logger.error(f"❌ 特征计算失败: {e}")
            return False

    def validate_features(self):
        """验证特征数据."""
        logger.info("=" * 60)
        logger.info("🔍 开始验证特征数据")
        logger.info("=" * 60)

        try:
            is_valid = self.calculator.validate_features(self.features_df)

            if is_valid:
                logger.info("✅ 特征数据验证通过")

                # 检查第一场比赛的特征（应该没有历史数据）
                first_match = self.features_df.iloc[0]
                logger.info("📊 第一场比赛特征验证:")
                logger.info(f"   主队最近5场积分: {first_match['home_last_5_points']}")
                logger.info(f"   客队最近5场积分: {first_match['away_last_5_points']}")
                logger.info(
                    f"   历史交锋主队获胜次数: {first_match['h2h_last_3_home_wins']}"
                )

                # 检查后续比赛的特征
                if len(self.features_df) >= 10:
                    tenth_match = self.features_df.iloc[9]  # 第10场比赛
                    logger.info("📊 第十场比赛特征验证:")
                    logger.info(
                        f"   主队最近5场积分: {tenth_match['home_last_5_points']}"
                    )
                    logger.info(
                        f"   客队最近5场积分: {tenth_match['away_last_5_points']}"
                    )
                    logger.info(
                        f"   历史交锋主队获胜次数: {tenth_match['h2h_last_3_home_wins']}"
                    )

                return True
            else:
                logger.error("❌ 特征数据验证失败")
                return False

        except Exception:
            logger.error(f"❌ 特征验证失败: {e}")
            return False

    def save_to_database(self):
        """保存特征数据到数据库."""
        logger.info("=" * 60)
        logger.info("💾 开始保存特征到数据库")
        logger.info("=" * 60)

        try:
            import json
            from sqlalchemy import create_engine

            # 获取数据库连接
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                # 回退逻辑：使用单独的环境变量
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "football_prediction_2024")
                db_host = os.getenv("DB_HOST", "db")
                db_port = os.getenv("DB_PORT", "5432")
                db_name = os.getenv("POSTGRES_DB", "football_prediction")
                db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            # Pandas需要同步驱动，移除asyncpg
            if "+asyncpg" in db_url:
                db_url = db_url.replace("+asyncpg", "")

            # 创建SQLAlchemy引擎
            engine = create_engine(db_url)

            # 准备批量插入数据 - 适配实际表结构
            batch_data = []

            logger.info(f"开始准备 {len(self.features_df)} 条特征记录...")

            for index, row in self.features_df.iterrows():
                try:
                    # 准备特征数据 - 只包含实际表结构中的字段
                    feature_record = {
                        "match_id": int(row["match_id"]),
                        "feature_data": json.dumps(
                            {
                                "home_team_id": int(row["home_team_id"]),
                                "away_team_id": int(row["away_team_id"]),
                                "match_date": str(row["match_date"]),
                                "match_result": int(row["match_result"]),
                                "home_last_5_points": float(row["home_last_5_points"]),
                                "away_last_5_points": float(row["away_last_5_points"]),
                                "home_last_5_avg_goals": float(
                                    row["home_last_5_avg_goals"]
                                ),
                                "away_last_5_avg_goals": float(
                                    row["away_last_5_avg_goals"]
                                ),
                                "home_last_5_goal_diff": float(
                                    row["home_last_5_goal_diff"]
                                ),
                                "away_last_5_goal_diff": float(
                                    row["away_last_5_goal_diff"]
                                ),
                                "home_win_streak": int(row["home_win_streak"]),
                                "away_win_streak": int(row["away_win_streak"]),
                                "home_last_5_win_rate": float(
                                    row["home_last_5_win_rate"]
                                ),
                                "away_last_5_win_rate": float(
                                    row["away_last_5_win_rate"]
                                ),
                                "home_rest_days": int(row["home_rest_days"]),
                                "away_rest_days": int(row["away_rest_days"]),
                                "h2h_last_3_home_wins": int(
                                    row["h2h_last_3_home_wins"]
                                ),
                            }
                        ),
                    }
                    batch_data.append(feature_record)

                    # 每50条记录显示一次进度
                    if (index + 1) % 50 == 0:
                        logger.info(
                            f"已准备 {index + 1}/{len(self.features_df)} 条记录..."
                        )

                except Exception:
                    logger.error(f"准备第 {index} 条记录失败: {e}")
                    continue

            logger.info(f"开始批量插入 {len(batch_data)} 条特征记录到数据库...")

            # 批量插入到数据库 - 使用pandas to_sql直接插入
            features_df = pd.DataFrame(batch_data)

            # 添加时间戳和必需字段
            from datetime import datetime

            features_df["created_at"] = datetime.now()
            features_df["updated_at"] = datetime.now()
            features_df["feature_type"] = "match_features"  # 添加必需的feature_type字段
            features_df["team_id"] = None  # 添加可选的team_id字段

            # 只包含表中实际存在的字段
            features_df = features_df[
                [
                    "match_id",
                    "team_id",
                    "feature_type",
                    "feature_data",
                    "created_at",
                    "updated_at",
                ]
            ]

            # 使用pandas的to_sql批量插入
            features_df.to_sql("features", engine, if_exists="append", index=False)

            logger.info(f"✅ 成功保存 {len(batch_data)} 条特征记录到数据库")

            logger.info(f"✅ 成功保存 {len(batch_data)} 条特征记录到数据库")
            return True

        except Exception:
            logger.error(f"❌ 保存到数据库失败: {e}")
            # 打印详细错误信息用于调试
            import traceback

            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def save_dataset(self, filepath: str = "data/dataset_v1.csv"):
        """保存数据集."""
        logger.info("=" * 60)
        logger.info("💾 开始保存数据集")
        logger.info("=" * 60)

        try:
            # 使用特征计算器的保存方法
            save_features_to_csv(self.features_df, filepath)

            # 验证文件是否创建成功
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logger.info(f"✅ 数据集已保存到 {filepath}")
                logger.info(f"📁 文件大小: {file_size:,} 字节")

                # 读取并验证保存的文件
                saved_df = pd.read_csv(filepath)
                logger.info(
                    f"📊 验证保存的文件: {saved_df.shape[0]} 行, {saved_df.shape[1]} 列"
                )

                return True
            else:
                logger.error(f"❌ 文件未创建: {filepath}")
                return False

        except Exception:
            logger.error(f"❌ 保存数据集失败: {e}")
            return False

    def generate_summary_report(self):
        """生成特征摘要报告."""
        logger.info("=" * 60)
        logger.info("📋 特征生成摘要报告")
        logger.info("=" * 60)

        try:
            if self.features_df is None:
                logger.error("❌ 没有特征数据可用于生成报告")
                return

            # 基本统计
            total_matches = len(self.features_df)
            home_wins = len(self.features_df[self.features_df["match_result"] == 1])
            away_wins = len(self.features_df[self.features_df["match_result"] == 2])
            draws = len(self.features_df[self.features_df["match_result"] == 0])

            logger.info("📊 数据集统计:")
            logger.info(f"   总比赛数: {total_matches}")
            logger.info(
                f"   主队获胜: {home_wins} ({home_wins / total_matches * 100:.1f}%)"
            )
            logger.info(
                f"   客队获胜: {away_wins} ({away_wins / total_matches * 100:.1f}%)"
            )
            logger.info(f"   平局: {draws} ({draws / total_matches * 100:.1f}%)")

            # 特征统计
            logger.info("📈 特征统计:")
            logger.info(
                f"   主队近期积分均值: {self.features_df['home_last_5_points'].mean():.2f}"
            )
            logger.info(
                f"   客队近期积分均值: {self.features_df['away_last_5_points'].mean():.2f}"
            )
            logger.info(
                f"   主队近期进球均值: {self.features_df['home_last_5_avg_goals'].mean():.2f}"
            )
            logger.info(
                f"   客队近期进球均值: {self.features_df['away_last_5_avg_goals'].mean():.2f}"
            )

            # 数据质量检查
            zero_history_matches = len(
                self.features_df[
                    (self.features_df["home_last_5_points"] == 0)
                    & (self.features_df["away_last_5_points"] == 0)
                ]
            )
            logger.info("🔍 数据质量:")
            logger.info(
                f"   无历史记录的比赛: {zero_history_matches} ({zero_history_matches / total_matches * 100:.1f}%)"
            )

        except Exception:
            logger.error(f"❌ 生成报告失败: {e}")

    async def run(self, output_path: str = "data/dataset_v1.csv"):
        """运行完整的特征生成流程."""
        logger.info("🚀 开始特征生成流程")
        start_time = datetime.now()

        try:
            # 1. 加载数据
            if not self.load_data():
                return False

            # 2. 计算特征
            if not self.calculate_features():
                return False

            # 3. 验证特征
            if not self.validate_features():
                return False

            # 4. 保存到数据库 (新增)
            if not self.save_to_database():
                logger.warning("⚠️ 保存到数据库失败，但继续保存CSV文件")

            # 5. 保存数据集
            if not self.save_dataset(output_path):
                return False

            # 6. 生成摘要报告
            self.generate_summary_report()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("🎉 特征生成流程完成！")
            logger.info(f"⏱️  总耗时: {duration}")
            logger.info(f"💾 输出文件: {output_path}")
            logger.info("🗄️  数据库: features 表已更新")
            logger.info("=" * 60)

            return True

        except Exception:
            logger.error(f"💥 特征生成流程失败: {e}")
            return False


async def main():
    """主函数."""
    logger.info("🎯 特征生成器启动")

    try:
        generator = FeatureGenerator()
        success = await generator.run()

        if success:
            logger.info("✅ 特征生成成功！数据集已准备好用于模型训练。")
            sys.exit(0)
        else:
            logger.error("❌ 特征生成失败！")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，特征生成停止")
        sys.exit(1)
    except Exception:
        logger.error(f"💥 特征生成异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
