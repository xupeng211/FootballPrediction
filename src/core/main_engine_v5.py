#!/usr/bin/env python3
"""
MainEngineV5 - 真实L2特征收割引擎
Clean Version - 专注于真实数据提取
"""

import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import sys

# 添加项目路径
# 添加项目路径
sys.path.append('/app' if os.getenv('DOCKER_ENV') else '.')
sys.path.append('src')
from config_unified import get_settings
from api.fotmob_client import FotMobAPIClient
from data_access.processors.advanced_feature_extractor import AdvancedFeatureExtractor
from core.inference_engine import get_inference_engine, predict_match_from_features

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def initialize_database_schema():
    """初始化数据库Schema"""
    try:
        settings = get_settings()
        db = settings.database

        conn = psycopg2.connect(
            host=db.host,
            port=db.port,
            database=db.name,
            user=db.user,
            password=db.password.get_secret_value()
        )
        cursor = conn.cursor()

        logger.info("🏗️ 初始化数据库Schema...")

        # 检查并更新match_features_training表结构
        try:
            cursor.execute("""
                ALTER TABLE match_features_training
                ADD COLUMN IF NOT EXISTS league_name VARCHAR(100),
                ADD COLUMN IF NOT EXISTS season VARCHAR(20),
                ADD COLUMN IF NOT EXISTS status VARCHAR(50),
                ADD COLUMN IF NOT EXISTS away_opening_odds FLOAT,
                ADD COLUMN IF NOT EXISTS home_current_odds FLOAT,
                ADD COLUMN IF NOT EXISTS away_current_odds FLOAT,
                ADD COLUMN IF NOT EXISTS home_corners INTEGER,
                ADD COLUMN IF NOT EXISTS away_corners INTEGER,
                ADD COLUMN IF NOT EXISTS home_shots INTEGER,
                ADD COLUMN IF NOT EXISTS away_shots INTEGER,
                ADD COLUMN IF NOT EXISTS home_shots_on_target INTEGER,
                ADD COLUMN IF NOT EXISTS away_shots_on_target INTEGER,
                ADD COLUMN IF NOT EXISTS home_fouls INTEGER,
                ADD COLUMN IF NOT EXISTS away_fouls INTEGER,
                ADD COLUMN IF NOT EXISTS home_yellow_cards INTEGER,
                ADD COLUMN IF NOT EXISTS away_yellow_cards INTEGER,
                ADD COLUMN IF NOT EXISTS home_red_cards INTEGER,
                ADD COLUMN IF NOT EXISTS away_red_cards INTEGER,
                ADD COLUMN IF NOT EXISTS raw_data JSONB;
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_features_league ON match_features_training(league_name);
                CREATE INDEX IF NOT EXISTS idx_match_features_xg ON match_features_training(home_xg, away_xg);
            """)

        except Exception as e:
            logger.warning(f"表结构更新跳过: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ 数据库Schema初始化完成")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库Schema初始化失败: {e}")
        return False


class MainEngineV5:
    """MainEngineV5 - 真实L2特征收割引擎"""

    def __init__(self):
        self.settings = get_settings()
        db = self.settings.database
        self.db_config = {
            'host': db.host,
            'port': db.port,
            'database': db.name,
            'user': db.user,
            'password': db.password.get_secret_value()
        }

        # 初始化组件
        self.client = FotMobAPIClient(timeout=15)
        self.extractor = AdvancedFeatureExtractor()
        self.inference_engine = get_inference_engine()

        # 统计变量
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.real_xg_count = 0
        self.prediction_count = 0

        logger.info(f"🔗 数据库配置: {db.name} @ {db.host}:{db.port}")
        logger.info(f"🚀 MainEngineV5 初始化完成 - 真实L2特征收割模式")

    def get_matches_from_db(self, limit: int = 700) -> List[Dict]:
        """从数据库获取待处理的比赛"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # 获取pending状态的比赛，优先处理已完成的比赛
            cursor.execute("""
                SELECT external_id, home_team, away_team, league_name, status
                FROM matches
                WHERE collection_status = 'pending'
                ORDER BY
                    CASE WHEN status = 'Finished' THEN 1 ELSE 2 END,
                    match_time DESC
                LIMIT %s;
            """, (limit,))

            matches = []
            for row in cursor.fetchall():
                matches.append(dict(row))

            logger.info(f"📋 从数据库获取到 {len(matches)} 场待处理比赛")
            return matches

        finally:
            conn.close()

    def update_match_with_features(self, external_id: str, features_data: Dict[str, Any]):
        """更新比赛特征数据到数据库"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()

        try:
            # 插入特征数据到match_features_training表
            feature_dict = features_data

            # 构建插入语句 - 动态字段处理
            fields = ['external_id', 'data_source']
            values = [external_id, 'fotmob_api_v2']
            placeholders = ['%s', '%s']

            # 主要字段
            main_fields = [
                'home_team', 'away_team', 'league_name', 'season', 'match_time', 'status',
                'home_xg', 'away_xg', 'home_possession', 'away_possession',
                'home_opening_odds', 'away_opening_odds', 'home_current_odds', 'away_current_odds',
                'home_corners', 'away_corners', 'home_shots', 'away_shots',
                'home_shots_on_target', 'away_shots_on_target', 'home_fouls', 'away_fouls',
                'home_yellow_cards', 'away_yellow_cards', 'home_red_cards', 'away_red_cards'
            ]

            for field in main_fields:
                if field in feature_dict and feature_dict[field] is not None:
                    # 特殊处理赔率字段：如果为0，设为NULL以避免验证错误
                    if 'odds' in field and feature_dict[field] == 0:
                        continue  # 跳过0值赔率
                    fields.append(field)
                    values.append(feature_dict[field])
                    placeholders.append('%s')

            # 添加原始数据
            if 'raw_data' not in fields:
                fields.append('raw_data')
                values.append(json.dumps(feature_dict))
                placeholders.append('%s')

            # 创建插入语句
            insert_sql = f"""
                INSERT INTO match_features_training ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT (external_id) DO UPDATE SET
                    {', '.join([f"{field} = EXCLUDED.{field}" for field in fields[1:]])},
                    updated_at = CURRENT_TIMESTAMP;
            """

            cursor.execute(insert_sql, values)

            # 更新matches表的收割状态
            cursor.execute("""
                UPDATE matches
                SET collection_status = %s, l2_collected_at = CURRENT_TIMESTAMP
                WHERE external_id = %s;
            """, ('completed', external_id))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"❌ 更新特征数据失败 {external_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    async def extract_match_features(self, external_id: str, match_info: Dict[str, Any] = None):
        """提取单场比赛的特征"""
        try:
            logger.info(f"🔄 [Ingested] 开始提取: {external_id}")

            async with self.client as client:
                match_data = await client.get_match_details(external_id)

                if not match_data:
                    logger.warning(f"⚠️ 无法获取比赛数据: {external_id}")
                    return None

            # 使用AdvancedFeatureExtractor提取特征
            features = self.extractor.extract_complete_features(match_data, external_id)

            # 如果提供了match_info，补充league_name等元数据
            if match_info:
                feature_dict = features.model_dump(mode='json')
                if 'league_name' in match_info and match_info['league_name']:
                    feature_dict['league_name'] = match_info['league_name']
                if 'status' in match_info and match_info['status']:
                    feature_dict['status'] = match_info['status']

                # 重新创建features对象以包含补充的元数据
                from schemas.match_features import MatchFeatures
                features = MatchFeatures(**feature_dict)

            # 检查xG数据
            has_real_xg = (features.home_xg is not None and features.home_xg > 0) or \
                         (features.away_xg is not None and features.away_xg > 0)

            if has_real_xg:
                self.real_xg_count += 1

            # 实时输出监控指标
            xg_str = f"{features.home_xg or 0:.1f}-{features.away_xg or 0:.1f}"
            corners_str = f"{(features.home_corners or 0) + (features.away_corners or 0)}"

            logger.info(f"[Ingested] {features.home_team} vs {features.away_team} | "
                       f"xG: {xg_str} | Corners: {corners_str} | Status: Success")

            # 更新数据库 - 使用Pydantic V2官方推荐的JSON序列化模式
            feature_dict = features.model_dump(mode='json')
            if self.update_match_with_features(external_id, feature_dict):
                self.success_count += 1
                return feature_dict

            return None

        except Exception as e:
            logger.error(f"❌ 特征提取失败 {external_id}: {e}")
            self.error_count += 1
            return None

    def get_historical_team_stats(self, team_name: str, limit: int = 5) -> Dict:
        """
        从数据库获取球队过去5场比赛的平均统计数据

        Args:
            team_name: 球队名称
            limit: 查询的比赛数量（默认5场）

        Returns:
            包含平均统计数据的字典
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()

        try:
            # SQL查询：获取该队过去5场比赛的平均xG和控球率
            query = """
                SELECT
                    AVG(home_xg) as avg_home_xg,
                    AVG(away_xg) as avg_away_xg,
                    AVG(home_possession) as avg_home_possession,
                    AVG(away_possession) as avg_away_possession,
                    COUNT(*) as match_count
                FROM match_features_training
                WHERE (home_team = %s OR away_team = %s)
                  AND home_xg IS NOT NULL
                  AND away_xg IS NOT NULL
                  AND home_possession IS NOT NULL
                  AND away_possession IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT %s
            """

            cursor.execute(query, (team_name, team_name, limit))
            result = cursor.fetchone()

            if result and result[4] > 0:  # match_count > 0
                return {
                    'avg_home_xg': float(result[0]) if result[0] else 1.2,
                    'avg_away_xg': float(result[1]) if result[1] else 1.1,
                    'avg_home_possession': float(result[2]) if result[2] else 50.0,
                    'avg_away_possession': float(result[3]) if result[3] else 50.0,
                    'match_count': int(result[4])
                }
            else:
                logger.warning(f"⚠️ 未找到 {team_name} 的历史数据，使用默认值")
                return {
                    'avg_home_xg': 1.2,
                    'avg_away_xg': 1.1,
                    'avg_home_possession': 50.0,
                    'avg_away_possession': 50.0,
                    'match_count': 0
                }

        except Exception as e:
            logger.error(f"❌ 查询 {team_name} 历史数据失败: {e}")
            return {
                'avg_home_xg': 1.2,
                'avg_away_xg': 1.1,
                'avg_home_possession': 50.0,
                'avg_away_possession': 50.0,
                'match_count': 0
            }
        finally:
            cursor.close()
            conn.close()

    def predict_future_match(self, home_team: str, away_team: str, match_info: Dict) -> Optional[Dict]:
        """
        对未来比赛进行实时预测（V2.0 动态特征回填版本）

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_info: 比赛信息包含状态

        Returns:
            预测结果或None
        """
        try:
            # 只对未来比赛（Fixture）进行预测
            if match_info.get('status') != 'Fixture':
                return None

            logger.info(f"🎯 [PREDICTION] 开始预测未来比赛: {home_team} vs {away_team}")

            # 动态获取主队历史统计数据
            home_stats = self.get_historical_team_stats(home_team, limit=5)
            away_stats = self.get_historical_team_stats(away_team, limit=5)

            logger.info(f"📊 [HISTORICAL] {home_team} 历史数据: {home_stats['match_count']} 场, "
                       f"平均xG: {home_stats['avg_home_xg']:.2f}/{home_stats['avg_away_xg']:.2f}, "
                       f"平均控球率: {home_stats['avg_home_possession']:.1f}%/{home_stats['avg_away_possession']:.1f}%")

            logger.info(f"📊 [HISTORICAL] {away_team} 历史数据: {away_stats['match_count']} 场, "
                       f"平均xG: {away_stats['avg_home_xg']:.2f}/{away_stats['avg_away_xg']:.2f}, "
                       f"平均控球率: {away_stats['avg_home_possession']:.1f}%/{away_stats['avg_away_possession']:.1f}%")

            # 构建动态特征字典（基于历史数据）
            features = {
                # xG特征：基于两队历史表现
                'home_xg': home_stats['avg_home_xg'],
                'away_xg': away_stats['avg_away_xg'],

                # 控球率特征：基于两队历史表现
                'home_possession': home_stats['avg_home_possession'],
                'away_possession': away_stats['avg_away_possession'],

                # 赔率特征：暂时保留默认值（未来可集成实时赔率API）
                'home_opening_odds': 2.1,
                'home_current_odds': 2.0
            }

            logger.info(f"🔮 [DYNAMIC] 使用动态特征进行预测: "
                       f"主队xG={features['home_xg']:.2f}, "
                       f"客队xG={features['away_xg']:.2f}, "
                       f"主队控球={features['home_possession']:.1f}%")

            # 进行预测
            prediction = predict_match_from_features(home_team, away_team, features)

            if 'error' not in prediction:
                # 格式化并输出预测日志
                prediction_log = self.inference_engine.format_prediction_log(prediction)
                logger.info(prediction_log)

                self.prediction_count += 1
                return prediction
            else:
                logger.error(f"❌ 预测失败: {prediction['error']}")
                return None

        except Exception as e:
            logger.error(f"❌ 预测异常 {home_team} vs {away_team}: {e}")
            return None

    async def run_full_extraction(self, limit: int = 700):
        """运行全量特征提取"""
        logger.info("🚀 MainEngineV5 启动 - 真实L2特征收割大决战")
        logger.info(f"📊 处理上限: {limit} 场比赛")

        # 获取待处理的比赛
        matches = self.get_matches_from_db(limit)
        logger.info(f"📋 找到 {len(matches)} 场待处理比赛")

        if not matches:
            logger.warning("⚠️ 没有待处理的比赛")
            return

        # 显示前几场比赛确认真实性
        logger.info("🎯 即将处理的真实比赛样本:")
        for i, match in enumerate(matches[:5]):
            status_icon = "✅" if match['status'] == 'Finished' else "⏰"
            logger.info(f"  {i+1}. {status_icon} [{match['external_id']}] {match['home_team']} vs {match['away_team']} ({match['status']})")

        # 批量处理
        batch_size = 10

        async with self.client as client:
            for i in range(0, len(matches), batch_size):
                batch = matches[i:i+batch_size]
                logger.info(f"🔄 处理批次 {i//batch_size + 1}/{(len(matches)-1)//batch_size + 1}")

                # 创建任务
                tasks = []
                for match in batch:
                    task = self.extract_match_features(match['external_id'], match)
                    tasks.append(task)

                # 执行任务
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                self.processed_count += len(batch)

                # 对未来比赛进行预测
                logger.info("🔮 开始未来比赛预测...")
                for match in batch:
                    prediction = self.predict_future_match(match['home_team'], match['away_team'], match)
                    if prediction:
                        logger.info(f"✅ 预测完成: {match['home_team']} vs {match['away_team']}")

                # 进度报告
                xg_rate = self.real_xg_count / self.processed_count * 100 if self.processed_count > 0 else 0
                logger.info(f"📊 批次完成: {self.processed_count}/{len(matches)} "
                           f"(成功: {self.success_count}, 真实xG: {self.real_xg_count}, 预测: {self.prediction_count}, xG率: {xg_rate:.1f}%)")

                # 延迟避免API限制
                if i + batch_size < len(matches):
                    await asyncio.sleep(1)

        # 最终报告
        logger.info("\n" + "="*80)
        logger.info("🏆 MainEngineV5 全量收割 + 预测完成报告")
        logger.info("="*80)
        logger.info(f"📊 处理总数: {self.processed_count}")
        logger.info(f"✅ 成功收割: {self.success_count}")
        logger.info(f"⚽ 真实xG比赛: {self.real_xg_count}")
        logger.info(f"🔮 实时预测: {self.prediction_count}")
        logger.info(f"📈 成功率: {self.success_count/self.processed_count*100:.1f}%" if self.processed_count > 0 else "📈 成功率: 0%")
        logger.info(f"🎯 xG数据率: {self.real_xg_count/self.processed_count*100:.1f}%" if self.processed_count > 0 else "🎯 xG数据率: 0%")
        logger.info(f"🚀 预测覆盖率: {self.prediction_count/self.processed_count*100:.1f}%" if self.processed_count > 0 else "🚀 预测覆盖率: 0%")
        logger.info("="*80)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='MainEngineV5 - 真实L2特征收割引擎')
    parser.add_argument('--mode', choices=['full', 'test'], default='full', help='运行模式')
    parser.add_argument('--limit', type=int, default=700, help='处理上限')

    args = parser.parse_args()

    # 确保使用正确的数据库
    os.environ['DB_NAME'] = 'football_prediction'

    # 首先初始化数据库Schema
    logger.info("🔧 正在初始化数据库Schema...")
    if not initialize_database_schema():
        logger.error("❌ 数据库Schema初始化失败，程序退出")
        return

    # 创建引擎实例
    engine = MainEngineV5()

    if args.mode == 'full':
        await engine.run_full_extraction(args.limit)
    else:
        # 测试模式
        matches = engine.get_matches_from_db(5)
        logger.info(f"测试模式，找到 {len(matches)} 场比赛")
        for match in matches:
            logger.info(f"  {match['external_id']}: {match['home_team']} vs {match['away_team']}")


if __name__ == "__main__":
    asyncio.run(main())