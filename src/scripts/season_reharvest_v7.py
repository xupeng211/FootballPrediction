#!/usr/bin/env python3
"""
FootballPrediction V7.0 赛季全量收割脚本 - 重构版
使用新的模块化架构，彻底解决硬编码和逻辑重复问题
"""

import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入新模块化组件
from src.core.config import get_config
from src.data_access.api_client import get_api_client
from src.data_access.processors.bulletproof_feature_extractor import BulletproofFeatureExtractor
from src.utils import setup_logger, get_db_manager
from src.utils.database import DatabaseManager


class SeasonReharvesterV7:
    """V7.0 赛季收割器 - 模块化架构"""

    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger('season_reharvest')
        self.api_client = get_api_client()
        self.feature_extractor = BulletproofFeatureExtractor()
        self.db_manager = get_db_manager()

        # 收割数据存储
        self.harvested_data = []
        self.failed_matches = []

        self.logger.info("🚀 V7.0 赛季收割器初始化完成")

    def setup_database(self) -> bool:
        """设置数据库表结构"""
        if not self.db_manager.is_available():
            self.logger.warning("⚠️ 数据库不可用，跳过数据库设置")
            return False

        try:
            # 创建表结构
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS match_features_training (
                    id SERIAL PRIMARY KEY,
                    external_id VARCHAR(50) NOT NULL UNIQUE,
                    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    home_team VARCHAR(100) NOT NULL,
                    away_team VARCHAR(100) NOT NULL,

                    -- 基础特征
                    home_possession REAL,
                    away_possession REAL,
                    home_total_shots INTEGER,
                    away_total_shots INTEGER,
                    home_xg REAL,
                    away_xg REAL,
                    home_corners INTEGER,
                    away_corners INTEGER,
                    home_shots_on_target INTEGER,
                    away_shots_on_target INTEGER,
                    home_avg_rating REAL,
                    away_avg_rating REAL,

                    -- 事件特征
                    home_red_cards INTEGER DEFAULT 0,
                    away_red_cards INTEGER DEFAULT 0,
                    home_substitutions INTEGER DEFAULT 0,
                    away_substitutions INTEGER DEFAULT 0,
                    home_early_goal INTEGER DEFAULT 0,
                    away_early_goal INTEGER DEFAULT 0,
                    home_penalties INTEGER DEFAULT 0,
                    away_penalties INTEGER DEFAULT 0,

                    -- 衍生特征
                    home_xg_per_shot REAL,
                    away_xg_per_shot REAL,
                    rating_diff REAL,

                    -- 元数据
                    league_id VARCHAR(50) DEFAULT '47',
                    league_name VARCHAR(100) DEFAULT 'Premier League',
                    is_real_data BOOLEAN DEFAULT TRUE,
                    feature_version VARCHAR(20) DEFAULT 'v7.0',
                    data_source VARCHAR(50) DEFAULT 'harvested',
                    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """

            success = self.db_manager.create_table_if_not_exists(
                'match_features_training',
                create_table_sql
            )

            if success:
                self.logger.info("✅ 数据库表结构设置成功")
                # 清空表数据
                self.db_manager.execute_query("TRUNCATE TABLE match_features_training RESTART IDENTITY CASCADE;")
                self.logger.info("✅ 表数据已清空")
            else:
                self.logger.error("❌ 数据库表设置失败")

            return success

        except Exception as e:
            self.logger.error(f"❌ 数据库设置异常: {e}")
            return False

    def get_season_matches(self) -> list:
        """获取赛季所有已完成比赛"""
        self.logger.info(f"🔍 获取英超 {self.config.harvest.season} 赛季比赛列表...")

        try:
            matches = self.api_client.get_season_matches(
                league_id=self.config.harvest.league_id,
                season=self.config.harvest.season
            )

            if not matches:
                self.logger.warning("⚠️ 未获取到比赛数据")
                return []

            self.logger.info(f"✅ 获取到 {len(matches)} 场已完成的比赛")
            return matches

        except Exception as e:
            self.logger.error(f"❌ 获取比赛列表失败: {e}")
            return []

    def harvest_match(self, match_id: str) -> dict:
        """收割单场比赛数据"""
        try:
            # 获取比赛详情
            match_data = self.api_client.get_match_details(match_id)
            if not match_data:
                raise ValueError("比赛数据为空")

            # 提取特征
            features = self.feature_extractor.extract(match_data)
            if not features:
                raise ValueError("特征提取失败")

            # 添加元数据
            features.update({
                'external_id': match_id,
                'league_id': self.config.harvest.league_id,
                'league_name': 'Premier League',
                'is_real_data': True,
                'feature_version': self.config.model.feature_version,
                'data_source': 'fotmob_api',
                'match_time': datetime.now()  # 临时时间戳
            })

            # 存储到内存
            self.harvested_data.append(features)
            return features

        except Exception as e:
            error_info = {
                'match_id': match_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.failed_matches.append(error_info)
            self.logger.error(f"❌ 收割比赛 {match_id} 失败: {e}")
            raise

    def save_harvested_data(self) -> bool:
        """保存收割的数据"""
        if not self.harvested_data:
            self.logger.warning("⚠️ 没有收割数据可保存")
            return False

        try:
            # 创建DataFrame
            df = pd.DataFrame(self.harvested_data)

            # 保存到CSV文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config.paths.data_dir / f"harvested_matches_v7_{timestamp}.csv"
            df.to_csv(filename, index=False)

            self.logger.info(f"✅ 收割数据已保存到: {filename}")
            self.logger.info(f"  总计: {len(df)} 场比赛")
            self.logger.info(f"  特征数量: {df.shape[1]}")

            # 更新标准文件
            df.to_csv(self.config.paths.final_features_path, index=False)
            self.logger.info(f"✅ 已更新 {self.config.paths.final_features_path.name}: {len(df)} 场比赛")

            # 保存失败列表
            if self.failed_matches:
                failed_filename = self.config.paths.data_dir / f"failed_matches_{timestamp}.json"
                with open(failed_filename, 'w', encoding='utf-8') as f:
                    json.dump(self.failed_matches, f, indent=2, ensure_ascii=False)
                self.logger.info(f"⚠️ 失败列表已保存到: {failed_filename} ({len(self.failed_matches)} 场)")

            # 保存到数据库（如果可用）
            if self.db_manager.is_available():
                self.save_to_database(df)

            return True

        except Exception as e:
            self.logger.error(f"❌ 保存数据失败: {e}")
            return False

    def save_to_database(self, df: pd.DataFrame) -> bool:
        """保存数据到数据库"""
        try:
            # 转换为数据库格式
            records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    if col in row:
                        record[col] = row[col]
                records.append(record)

            # 批量插入
            if records:
                columns = list(records[0].keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                insert_sql = f"""
                    INSERT INTO match_features_training ({columns_str})
                    VALUES ({placeholders})
                    ON CONFLICT (external_id) DO UPDATE SET
                        {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'external_id'])},
                        updated_at = NOW()
                """

                success = self.db_manager.execute_many(
                    insert_sql,
                    [tuple(record.values()) for record in records]
                )

                if success:
                    self.logger.info(f"✅ 已保存 {len(records)} 条记录到数据库")

            return True

        except Exception as e:
            self.logger.error(f"❌ 数据库保存失败: {e}")
            return False

    def run(self):
        """运行完整收割流程"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🚀 开始英超赛季全量收割 - V7.0")
            self.logger.info("=" * 60)

            # 设置数据库
            self.setup_database()

            # 获取比赛列表
            matches = self.get_season_matches()
            if not matches:
                self.logger.error("❌ 没有找到比赛数据")
                return

            # 收割数据
            total_matches = len(matches)
            success_count = 0
            failure_count = 0

            self.logger.info(f"📊 开始收割 {total_matches} 场比赛...")
            self.logger.info(f"🔇 静默模式: 随机延迟 {self.config.api.rate_limit_delay[0]}-{self.config.api.rate_limit_delay[1]} 秒")
            self.logger.info("-" * 60)

            for i, match in enumerate(matches, 1):
                match_id = match['match_id']
                home_team = match['home_team']
                away_team = match['away_team']

                self.logger.info(f"[{i}/{total_matches}] 收割中: {home_team} vs {away_team}")

                try:
                    features = self.harvest_match(match_id)
                    success_count += 1
                    self.logger.info(f"  ✅ 成功 (累计: {success_count})")

                except Exception as e:
                    failure_count += 1
                    self.logger.warning(f"  ❌ 收割失败 (累计失败: {failure_count})")

                # 进度报告
                if i % self.config.harvest.save_interval == 0:
                    self.logger.info("=" * 60)
                    self.logger.info(f"📊 进度报告: {i}/{total_matches} ({i/total_matches*100:.1f}%)")
                    self.logger.info(f"  成功: {success_count}, 失败: {failure_count}")
                    self.logger.info(f"  成功率: {success_count/i*100:.1f}%")
                    self.logger.info("=" * 60)

            # 保存数据
            self.save_harvested_data()

            # 最终报告
            self.logger.info("=" * 60)
            self.logger.info("🎉 全量收割完成!")
            self.logger.info(f"  总计: {total_matches} 场")
            self.logger.info(f"  成功: {success_count} 场 ({success_count/total_matches*100:.1f}%)")
            self.logger.info(f"  失败: {failure_count} 场 ({failure_count/total_matches*100:.1f}%)")
            self.logger.info(f"  收割数据: {len(self.harvested_data)} 场比赛")
            self.logger.info("=" * 60)

        except KeyboardInterrupt:
            self.logger.info("\n⚠️ 用户中断操作")
        except Exception as e:
            self.logger.error(f"❌ 收割过程出错: {e}", exc_info=True)
        finally:
            # 清理资源
            self.api_client.close()
            self.db_manager.close()


def main():
    """主函数"""
    reharvester = SeasonReharvesterV7()
    reharvester.run()


if __name__ == "__main__":
    main()