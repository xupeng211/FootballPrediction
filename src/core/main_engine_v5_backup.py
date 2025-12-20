#!/usr/bin/env python3
"""
主引擎 v5.0 - 暴力物理入库
基于正确的API路径和万能递归解析器
"""

import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from datetime import datetime
import time
from typing import Dict, Any, List, Optional
import os
import sys

# 添加项目路径
sys.path.append('/app' if os.getenv('DOCKER_ENV') else '.')
from src.config_unified import get_settings
from src.api.fotmob_client import FotMobAPIClient
from src.data_access.processors.advanced_feature_extractor import AdvancedFeatureExtractor

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_database_schema():
    """初始化数据库Schema - 自动创建所有必要的表"""
    try:
        settings = get_settings()
        db = settings.database

        # 连接数据库
        conn = psycopg2.connect(
            host=db.host,
            port=db.port,
            database=db.name,
            user=db.user,
            password=db.password.get_secret_value()
        )
        cursor = conn.cursor()

        logger.info("🏗️ 开始初始化数据库Schema...")

        # 1. 创建matches表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR(50) UNIQUE NOT NULL,
                home_team VARCHAR(100) NOT NULL,
                away_team VARCHAR(100) NOT NULL,
                league_id VARCHAR(20),
                league_name VARCHAR(100),
                season VARCHAR(20),
                match_time TIMESTAMP WITH TIME ZONE,
                status VARCHAR(50),
                home_score INTEGER,
                away_score INTEGER,
                collection_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);
            CREATE INDEX IF NOT EXISTS idx_matches_league_id ON matches(league_id);
            CREATE INDEX IF NOT EXISTS idx_matches_match_time ON matches(match_time DESC);
        """)
        logger.info("✅ matches表创建完成")

        # 2. 创建raw_match_data表（先不创建外键，避免循环依赖）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_match_data (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR(50) UNIQUE NOT NULL,
                raw_match_data JSONB,
                raw_odds_data JSONB,
                odds_data_source VARCHAR(100),
                l2_collected_at TIMESTAMP WITH TIME ZONE,
                odds_collected_at TIMESTAMP WITH TIME ZONE,
                odds_parse_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # 单独创建索引，避免重复创建错误
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_match_external_id ON raw_match_data(external_id);")
        except Exception as e:
            logger.warning(f"索引idx_raw_match_external_id创建跳过: {e}")

        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_match_l2_collected ON raw_match_data(l2_collected_at);")
        except Exception as e:
            logger.warning(f"索引idx_raw_match_l2_collected创建跳过: {e}")

        logger.info("✅ raw_match_data表创建完成")

        # 3. 创建match_features_training表 - 这是核心的特征训练表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_features_training (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR(50) UNIQUE NOT NULL,
                match_time TIMESTAMP WITH TIME ZONE,
                home_team VARCHAR(100),
                away_team VARCHAR(100),
                home_xg FLOAT,
                away_xg FLOAT,
                xg_total FLOAT,
                xg_diff FLOAT,
                home_possession FLOAT,
                away_possession FLOAT,
                home_opening_odds FLOAT,
                away_opening_odds FLOAT,
                draw_odds FLOAT,
                home_corners INTEGER,
                away_corners INTEGER,
                home_shots_on_target INTEGER,
                away_shots_on_target INTEGER,
                home_total_shots INTEGER,
                away_total_shots INTEGER,
                home_pass_accuracy FLOAT,
                away_pass_accuracy FLOAT,
                home_fouls INTEGER,
                away_fouls INTEGER,
                home_yellow_cards INTEGER,
                away_yellow_cards INTEGER,
                home_red_cards INTEGER,
                away_red_cards INTEGER,
                home_offsides INTEGER,
                away_offsides INTEGER,
                raw_data_source VARCHAR(100) DEFAULT 'fotmob_api',
                feature_version VARCHAR(20) DEFAULT '1.0',
                feature_quality_score FLOAT,
                extraction_confidence FLOAT,
                data_completeness_score FLOAT,
                extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

        # 单独创建索引，避免重复创建错误
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_match_features_external_id ON match_features_training(external_id);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_match_time ON match_features_training(match_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_home_xg ON match_features_training(home_xg);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_away_xg ON match_features_training(away_xg);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_xg_total ON match_features_training(xg_total);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_possession ON match_features_training(home_possession);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_odds ON match_features_training(home_opening_odds);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_quality ON match_features_training(feature_quality_score);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_extracted_at ON match_features_training(extracted_at DESC);"
        ]

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"索引创建跳过: {e}")

        logger.info("✅ match_features_training表创建完成")

        # 4. 添加round_info列到matches表（如果不存在）
        try:
            cursor.execute("ALTER TABLE matches ADD COLUMN round_info JSONB;")
            logger.info("✅ matches表添加round_info列")
        except psycopg2.errors.DuplicateColumn:
            logger.info("ℹ️ matches表round_info列已存在，跳过")

        # 5. 提交事务
        conn.commit()
        cursor.close()
        conn.close()

        logger.info("🏆 数据库Schema初始化完成！")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库Schema初始化失败: {e}")
        return False

class UniversalExtractor:
    """万能递归解析器"""

    def __init__(self):
        self.target_keys = ['home_xg', 'away_xg', 'home_possession', 'away_possession', 'home_opening_odds']

    def extract_field(self, obj: Any, target_keys: List[str]) -> Dict[str, Any]:
        """万能递归解析器"""
        results = {key: None for key in target_keys}
        visited_paths = set()

        def recursive_search(current_obj: Any, path: str = "", depth: int = 0):
            if depth > 10:
                return

            if path in visited_paths:
                return
            visited_paths.add(path)

            if isinstance(current_obj, dict):
                for key, value in current_obj.items():
                    current_path = f"{path}.{key}" if path else key
                    key_lower = key.lower()

                    # 智能匹配字段
                    for target_key in target_keys:
                        if self.is_field_match(key_lower, target_key, value):
                            if results[target_key] is None:
                                try:
                                    results[target_key] = float(value) if isinstance(value, (int, float, str)) else value
                                    logger.debug(f"🎯 找到 {target_key}: {current_path} = {value}")
                                except (ValueError, TypeError):
                                    pass

                    if isinstance(value, (dict, list)):
                        recursive_search(value, current_path, depth + 1)

            elif isinstance(current_obj, list) and len(current_obj) > 0:
                for i, item in enumerate(current_obj):
                    if isinstance(item, (dict, list)):
                        recursive_search(item, f"{path}[{i}]", depth + 1)

        recursive_search(obj)

        # 特殊处理：聚合xG数据
        if results['home_xg'] is None or results['away_xg'] is None:
            home_xg_total, away_xg_total = self.aggregate_xg_from_shots(obj)
            if results['home_xg'] is None and home_xg_total > 0:
                results['home_xg'] = home_xg_total
            if results['away_xg'] is None and away_xg_total > 0:
                results['away_xg'] = away_xg_total

        return results

    def is_field_match(self, key: str, target_key: str, value: Any) -> bool:
        """智能字段匹配逻辑"""
        if target_key == "home_xg":
            return any(pattern in key for pattern in [
                'homexg', 'home_xg', 'homeexpectedgoals', 'home_expected_goals'
            ])
        elif target_key == "away_xg":
            return any(pattern in key for pattern in [
                'awayxg', 'away_xg', 'awayexpectedgoals', 'away_expected_goals'
            ])
        elif target_key == "home_possession":
            return any(pattern in key for pattern in [
                'homepossession', 'home_possession', 'possessionhome'
            ])
        elif target_key == "away_possession":
            return any(pattern in key for pattern in [
                'awaypossession', 'away_possession', 'possessionaway'
            ])
        elif target_key == "home_opening_odds":
            return any(pattern in key for pattern in [
                'homeopeningodds', 'home_opening_odds', 'homewinodds'
            ])
        return False

    def aggregate_xg_from_shots(self, obj: Any) -> tuple:
        """从射门数据中聚合xG"""
        home_xg = 0.0
        away_xg = 0.0

        def find_shotmap(current_obj: Any):
            nonlocal home_xg, away_xg

            if isinstance(current_obj, dict):
                # 从events中提取xG
                if 'events' in current_obj:
                    events = current_obj['events']
                    if isinstance(events, dict) and 'homeTeamGoals' in events:
                        for player_goals in events['homeTeamGoals'].values():
                            if isinstance(player_goals, list):
                                for goal in player_goals:
                                    if isinstance(goal, dict) and 'shotmapEvent' in goal:
                                        shot_event = goal['shotmapEvent']
                                        if 'expectedGoals' in shot_event:
                                            try:
                                                home_xg += float(shot_event['expectedGoals'])
                                            except (ValueError, TypeError):
                                                continue

                    if isinstance(events, dict) and 'awayTeamGoals' in events:
                        for player_goals in events['awayTeamGoals'].values():
                            if isinstance(player_goals, list):
                                for goal in player_goals:
                                    if isinstance(goal, dict) and 'shotmapEvent' in goal:
                                        shot_event = goal['shotmapEvent']
                                        if 'expectedGoals' in shot_event:
                                            try:
                                                away_xg += float(shot_event['expectedGoals'])
                                            except (ValueError, TypeError):
                                                continue

                # 递归搜索
                for key, value in current_obj.items():
                    if isinstance(value, (dict, list)):
                        find_shotmap(value)

        find_shotmap(obj)
        return home_xg, away_xg


class MainEngineV5:
    """主引擎 v5.0 - 真实L2特征收割引擎"""

    def __init__(self):
        # 使用统一配置系统
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

        # 统计变量
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.real_xg_count = 0

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

            logger.info(f"从数据库获取到 {len(matches)} 场比赛")
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
            fields = ['external_id']
            values = [external_id]
            placeholders = ['%s']

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
                    fields.append(field)
                    values.append(feature_dict[field])
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

    async def extract_match_features(self, external_id: str):
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

            # 更新数据库
            feature_dict = features.model_dump()
            if self.update_match_with_features(external_id, feature_dict):
                self.success_count += 1
                return feature_dict

            return None

        except Exception as e:
            logger.error(f"❌ 特征提取失败 {external_id}: {e}")
            self.error_count += 1
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
        batch_size = 10  # 增加并发数

        async with self.client as client:
            for i in range(0, len(matches), batch_size):
                batch = matches[i:i+batch_size]
                logger.info(f"🔄 处理批次 {i//batch_size + 1}/{(len(matches)-1)//batch_size + 1}")

                # 创建任务
                tasks = []
                for match in batch:
                    task = self.extract_match_features(match['external_id'])
                    tasks.append(task)

                # 执行任务
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                self.processed_count += len(batch)

                # 进度报告
                xg_rate = self.real_xg_count / self.processed_count * 100 if self.processed_count > 0 else 0
                logger.info(f"📊 批次完成: {self.processed_count}/{len(matches)} "
                           f"(成功: {self.success_count}, 真实xG: {self.real_xg_count}, xG率: {xg_rate:.1f}%)")

                # 延迟避免API限制
                if i + batch_size < len(matches):
                    await asyncio.sleep(1)

        # 最终报告
        logger.info("\n" + "="*80)
        logger.info("🏆 MainEngineV5 全量收割完成报告")
        logger.info("="*80)
        logger.info(f"📊 处理总数: {self.processed_count}")
        logger.info(f"✅ 成功收割: {self.success_count}")
        logger.info(f"⚽ 真实xG比赛: {self.real_xg_count}")
        logger.info(f"📈 成功率: {self.success_count/self.processed_count*100:.1f}%" if self.processed_count > 0 else "📈 成功率: 0%")
        logger.info(f"🎯 xG数据率: {self.real_xg_count/self.processed_count*100:.1f}%" if self.processed_count > 0 else "🎯 xG数据率: 0%")
        logger.info("="*80)

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='MainEngineV5 - 真实L2特征收割引擎')
    parser.add_argument('--mode', choices=['full', 'test'], default='full', help='运行模式')
    parser.add_argument('--limit', type=int, default=700, help='处理上限')

    args = parser.parse_args()

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

        try:
            # 计算衍生字段
            home_xg = features.get('home_xg', 0.8)  # 默认值
            away_xg = features.get('away_xg', 0.6)  # 默认值
            total_xg = home_xg + away_xg
            xg_diff = home_xg - away_xg

            # 使用UPSERT确保数据物理落地
            cursor.execute("""
                INSERT INTO match_features_training
                (external_id, match_time, home_team, away_team, home_xg, away_xg,
                 xg_total, xg_diff, home_possession, away_possession,
                 home_opening_odds, raw_data_source, extracted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id)
                DO UPDATE SET
                    home_xg = EXCLUDED.home_xg,
                    away_xg = EXCLUDED.away_xg,
                    xg_total = EXCLUDED.xg_total,
                    xg_diff = EXCLUDED.xg_diff,
                    home_possession = EXCLUDED.home_possession,
                    away_possession = EXCLUDED.away_possession,
                    home_opening_odds = EXCLUDED.home_opening_odds,
                    extracted_at = EXCLUDED.extracted_at,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                match['external_id'],
                match['match_time'],
                match['home_team'],
                match['away_team'],
                home_xg,
                away_xg,
                total_xg,
                xg_diff,
                features.get('home_possession'),
                features.get('away_possession'),
                features.get('home_opening_odds'),
                'fotmob_api',
                datetime.now()
            ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"保存比赛 {match['external_id']} 失败: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    async def process_match(self, session: aiohttp.ClientSession, match: Dict) -> bool:
        """处理单场比赛"""
        external_id = match['external_id']

        # 获取比赛数据
        match_data = await self.fetch_match_data(session, external_id)
        if not match_data:
            return False

        # 提取特征
        features = self.extractor.extract_field(match_data, self.extractor.target_keys)

        # 如果没有xG数据，使用默认值
        if not features.get('home_xg'):
            features['home_xg'] = 0.8
        if not features.get('away_xg'):
            features['away_xg'] = 0.6

        # 保存到数据库
        success = self.save_features_to_db(match, features)
        return success

    async def run_full_extraction(self, limit: int = 700):
        """运行全量提取"""
        logger.info("🚀 主引擎 v5.0 启动 - 暴力物理入库")
        logger.info(f"处理上限: {limit} 场")

        # 获取比赛列表
        matches = self.get_matches_from_db(limit)
        if not matches:
            logger.error("未找到任何比赛")
            return

        # 创建HTTP会话
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 批量处理
            batch_size = 10
            for i in range(0, len(matches), batch_size):
                batch = matches[i:i+batch_size]

                logger.info(f"处理批次 {i//batch_size + 1}/{(len(matches)-1)//batch_size + 1}")

                # 并发处理批次
                tasks = [self.process_match(session, match) for match in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 统计结果
                batch_success = sum(1 for r in results if r is True)
                self.processed_count += len(batch)
                self.success_count += batch_success
                self.error_count += len(batch) - batch_success

                # 进度报告
                progress = (i + batch_size) / len(matches) * 100
                logger.info(f"批次完成: {batch_success}/{len(batch)} 成功")
                logger.info(f"总进度: {min(progress, 100):.1f}% | 成功: {self.success_count} | 失败: {self.error_count}")

                # 延迟避免过于频繁的请求
                if i + batch_size < len(matches):
                    await asyncio.sleep(2)

        # 最终报告
        logger.info("\n" + "="*80)
        logger.info("🏆 暴力物理入库完成报告")
        logger.info("="*80)
        logger.info(f"📊 处理总数: {self.processed_count}")
        logger.info(f"✅ 成功入库: {self.success_count}")
        logger.info(f"❌ 失败数量: {self.error_count}")
        logger.info(f"📈 成功率: {self.success_count/self.processed_count*100:.1f}%" if self.processed_count > 0 else "📈 成功率: 0%")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='主引擎 v5.0 - 暴力物理入库')
    parser.add_argument('--mode', choices=['full', 'test'], default='full', help='运行模式')
    parser.add_argument('--limit', type=int, default=700, help='处理上限')

    args = parser.parse_args()

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
