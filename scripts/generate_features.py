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
        print(f"✅ 已加载环境文件: {env_file}")
        break
else:
    print("⚠️  未找到.env文件，将使用系统环境变量")

# 导入模块
try:
    import pandas as pd
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from src.features.simple_feature_calculator import (
        SimpleFeatureCalculator,
        load_data_from_database,
        save_features_to_csv
    )
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("💡 提示: 请确保已安装所有依赖: pip install pandas psycopg2-binary")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            # 数据库连接配置
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME', 'football_prediction'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres-dev-password')
            }

            logger.info(f"连接数据库: {db_config['host']}:{db_config['port']}/{db_config['database']}")

            # 连接数据库并查询数据
            conn = psycopg2.connect(**db_config)

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
            logger.info(f"📅 数据时间范围: {self.matches_df['match_date'].min()} 到 {self.matches_df['match_date'].max()}")
            logger.info(f"🏆 涉及球队数: {len(set(self.matches_df['home_team_id'].unique()) | set(self.matches_df['away_team_id'].unique()))}")

            # 显示前几行数据
            logger.info("📊 数据预览:")
            print(self.matches_df.head(3))

            return True

        except Exception as e:
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
            print(self.features_df.describe())

            return True

        except Exception as e:
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
                logger.info(f"📊 第一场比赛特征验证:")
                logger.info(f"   主队最近5场积分: {first_match['home_last_5_points']}")
                logger.info(f"   客队最近5场积分: {first_match['away_last_5_points']}")
                logger.info(f"   历史交锋主队获胜次数: {first_match['h2h_last_3_home_wins']}")

                # 检查后续比赛的特征
                if len(self.features_df) >= 10:
                    tenth_match = self.features_df.iloc[9]  # 第10场比赛
                    logger.info(f"📊 第十场比赛特征验证:")
                    logger.info(f"   主队最近5场积分: {tenth_match['home_last_5_points']}")
                    logger.info(f"   客队最近5场积分: {tenth_match['away_last_5_points']}")
                    logger.info(f"   历史交锋主队获胜次数: {tenth_match['h2h_last_3_home_wins']}")

                return True
            else:
                logger.error("❌ 特征数据验证失败")
                return False

        except Exception as e:
            logger.error(f"❌ 特征验证失败: {e}")
            return False

    def save_dataset(self, filepath: str = 'data/dataset_v1.csv'):
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
                logger.info(f"📊 验证保存的文件: {saved_df.shape[0]} 行, {saved_df.shape[1]} 列")

                return True
            else:
                logger.error(f"❌ 文件未创建: {filepath}")
                return False

        except Exception as e:
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
            home_wins = len(self.features_df[self.features_df['match_result'] == 1])
            away_wins = len(self.features_df[self.features_df['match_result'] == 2])
            draws = len(self.features_df[self.features_df['match_result'] == 0])

            logger.info(f"📊 数据集统计:")
            logger.info(f"   总比赛数: {total_matches}")
            logger.info(f"   主队获胜: {home_wins} ({home_wins/total_matches*100:.1f}%)")
            logger.info(f"   客队获胜: {away_wins} ({away_wins/total_matches*100:.1f}%)")
            logger.info(f"   平局: {draws} ({draws/total_matches*100:.1f}%)")

            # 特征统计
            logger.info(f"📈 特征统计:")
            logger.info(f"   主队近期积分均值: {self.features_df['home_last_5_points'].mean():.2f}")
            logger.info(f"   客队近期积分均值: {self.features_df['away_last_5_points'].mean():.2f}")
            logger.info(f"   主队近期进球均值: {self.features_df['home_last_5_avg_goals'].mean():.2f}")
            logger.info(f"   客队近期进球均值: {self.features_df['away_last_5_avg_goals'].mean():.2f}")

            # 数据质量检查
            zero_history_matches = len(self.features_df[
                (self.features_df['home_last_5_points'] == 0) &
                (self.features_df['away_last_5_points'] == 0)
            ])
            logger.info(f"🔍 数据质量:")
            logger.info(f"   无历史记录的比赛: {zero_history_matches} ({zero_history_matches/total_matches*100:.1f}%)")

        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")

    async def run(self, output_path: str = 'data/dataset_v1.csv'):
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

            # 4. 保存数据集
            if not self.save_dataset(output_path):
                return False

            # 5. 生成摘要报告
            self.generate_summary_report()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("🎉 特征生成流程完成！")
            logger.info(f"⏱️  总耗时: {duration}")
            logger.info(f"💾 输出文件: {output_path}")
            logger.info("=" * 60)

            return True

        except Exception as e:
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
    except Exception as e:
        logger.error(f"💥 特征生成异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())