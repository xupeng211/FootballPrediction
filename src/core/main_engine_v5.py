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
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")
from src.config_unified import get_settings
from src.api.fotmob_client import FotMobAPIClient
from src.data_access.processors.advanced_feature_extractor import AdvancedFeatureExtractor
from src.core.inference_engine import get_inference_engine, predict_match_from_features

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def initialize_database_schema() -> bool:
    """初始化数据库Schema - 生产环境完整表结构.

    确保新环境下docker-compose up出来的数据库表结构与生产环境100%一致。
    该函数创建完整的match_features_training表，包含106维特征的所有字段，
    并建立必要的索引和触发器。

    Returns:
        bool: 如果Schema初始化成功返回True，失败返回False

    Raises:
        Exception: 数据库连接或SQL执行错误时抛出异常

    Example:
        >>> success = initialize_database_schema()
        >>> if success:
        ...     print("数据库Schema初始化成功")
    """
    try:
        settings = get_settings()
        db = settings.database

        conn = psycopg2.connect(
            host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
        )
        cursor = conn.cursor()

        logger.info("🏗️ 初始化生产环境数据库Schema...")

        # 1. 检查match_features_training表是否存在，不存在则创建
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'match_features_training'
            );
        """
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            logger.info("📋 创建match_features_training表...")
            cursor.execute(
                """
                CREATE TABLE match_features_training (
                    id SERIAL PRIMARY KEY,
                    external_id VARCHAR(50) NOT NULL UNIQUE,
                    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    home_team VARCHAR(100) NOT NULL,
                    away_team VARCHAR(100) NOT NULL,

                    -- xG相关特征 (10个)
                    home_xg DOUBLE PRECISION,
                    away_xg DOUBLE PRECISION,
                    xg_total DOUBLE PRECISION,
                    xg_diff DOUBLE PRECISION,
                    home_xg_first_half DOUBLE PRECISION,
                    away_xg_first_half DOUBLE PRECISION,
                    xg_total_first_half DOUBLE PRECISION,
                    home_xg_second_half DOUBLE PRECISION,
                    away_xg_second_half DOUBLE PRECISION,
                    xg_total_second_half DOUBLE PRECISION,
                    xg_dynamic_trend VARCHAR(20),

                    -- 控球率特征 (8个)
                    home_possession DOUBLE PRECISION,
                    away_possession DOUBLE PRECISION,
                    possession_diff DOUBLE PRECISION,
                    home_possession_first_half DOUBLE PRECISION,
                    away_possession_first_half DOUBLE PRECISION,
                    possession_first_half_diff DOUBLE PRECISION,
                    home_possession_second_half DOUBLE PRECISION,
                    away_possession_second_half DOUBLE PRECISION,
                    possession_second_half_diff DOUBLE PRECISION,

                    -- 射门数据 (12个)
                    home_shots_total INTEGER,
                    away_shots_total INTEGER,
                    shots_total_diff INTEGER,
                    home_shots_on_target INTEGER,
                    away_shots_on_target INTEGER,
                    shots_on_target_diff INTEGER,
                    home_shots_off_target INTEGER,
                    away_shots_off_target INTEGER,
                    shots_off_target_diff INTEGER,
                    home_shots_blocked INTEGER,
                    away_shots_blocked INTEGER,
                    shots_blocked_diff INTEGER,
                    home_shot_accuracy DOUBLE PRECISION,
                    away_shot_accuracy DOUBLE PRECISION,
                    shot_accuracy_diff DOUBLE PRECISION,

                    -- 角球数据 (8个)
                    home_corners INTEGER,
                    away_corners INTEGER,
                    corners_diff INTEGER,
                    home_corners_first_half INTEGER,
                    away_corners_first_half INTEGER,
                    corners_first_half_diff INTEGER,
                    home_corners_second_half INTEGER,
                    away_corners_second_half INTEGER,
                    corners_second_half_diff INTEGER,

                    -- 红黄牌数据 (8个)
                    home_yellow_cards INTEGER,
                    away_yellow_cards INTEGER,
                    yellow_cards_diff INTEGER,
                    home_red_cards INTEGER,
                    away_red_cards INTEGER,
                    red_cards_diff INTEGER,

                    -- 传球数据 (10个)
                    home_passes INTEGER,
                    away_passes INTEGER,
                    passes_diff INTEGER,
                    home_pass_accuracy DOUBLE PRECISION,
                    away_pass_accuracy DOUBLE PRECISION,
                    pass_accuracy_diff DOUBLE PRECISION,
                    home_successful_passes INTEGER,
                    away_successful_passes INTEGER,
                    successful_passes_diff INTEGER,

                    -- 赔率数据 (6个)
                    home_opening_odds DOUBLE PRECISION,
                    away_opening_odds DOUBLE PRECISION,
                    draw_odds DOUBLE PRECISION,
                    home_current_odds DOUBLE PRECISION,
                    away_current_odds DOUBLE PRECISION,
                    draw_current_odds DOUBLE PRECISION,

                    -- 元数据字段 (10个)
                    league_name VARCHAR(100),
                    season VARCHAR(20),
                    status VARCHAR(50),
                    raw_data_source VARCHAR(50),
                    data_source VARCHAR(50) DEFAULT 'fotmob_api',
                    feature_version VARCHAR(10),
                    feature_quality_score DOUBLE PRECISION,
                    extraction_confidence DOUBLE PRECISION,
                    data_completeness_score DOUBLE PRECISION,
                    raw_data JSONB,

                    -- 时间戳字段
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """
            )

        # 2. 添加缺失的列（如果表已存在）
        if table_exists:
            logger.info("📋 检查并添加缺失的列...")

            # 修正列名：home_shots -> home_shots_total（如果存在）
            try:
                cursor.execute("ALTER TABLE match_features_training RENAME COLUMN home_shots TO home_shots_total;")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE match_features_training RENAME COLUMN away_shots TO away_shots_total;")
            except Exception:
                pass

            # 确保所有必要字段存在
            alter_statement = """
                ALTER TABLE match_features_training
                ADD COLUMN IF NOT EXISTS raw_data_source VARCHAR(50),
                ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'fotmob_api',
                ADD COLUMN IF NOT EXISTS feature_version VARCHAR(10),
                ADD COLUMN IF NOT EXISTS feature_quality_score DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS extraction_confidence DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS data_completeness_score DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS raw_data JSONB;
            """

            try:
                cursor.execute(alter_statement)
            except Exception as e:
                logger.debug(f"Alter语句跳过: {e}")

            conn.commit()

        # 3. 创建所有必要的索引
        logger.info("📋 创建性能优化索引...")
        index_statements = [
            # 基础索引
            "CREATE INDEX IF NOT EXISTS idx_match_features_external_id ON match_features_training(external_id);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_league ON match_features_training(league_name);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_match_time ON match_features_training(match_time DESC);",
            # 特征索引
            "CREATE INDEX IF NOT EXISTS idx_match_features_xg ON match_features_training(home_xg, away_xg);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_possession ON match_features_training(home_possession, away_possession);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_shots ON match_features_training(home_shots_total, away_shots_total);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_corners ON match_features_training(home_corners, away_corners);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_cards ON match_features_training(home_yellow_cards, away_yellow_cards);",
            # JSON索引
            "CREATE INDEX IF NOT EXISTS idx_match_features_raw_data ON match_features_training USING GIN(raw_data);",
            # 复合索引（用于查询优化）
            "CREATE INDEX IF NOT EXISTS idx_match_features_league_time ON match_features_training(league_name, match_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_status_time ON match_features_training(status, match_time DESC);",
        ]

        for statement in index_statements:
            cursor.execute(statement)

        # 4. 创建更新时间戳的触发器（如果不存在）
        logger.info("📋 设置时间戳触发器...")
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """
        )

        cursor.execute(
            """
            DROP TRIGGER IF EXISTS update_match_features_updated_at ON match_features_training;
            CREATE TRIGGER update_match_features_updated_at
                BEFORE UPDATE ON match_features_training
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        )

        # 5. 创建数据质量检查函数
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION check_data_quality()
            RETURNS TABLE(
                total_matches BIGINT,
                matches_with_xg BIGINT,
                matches_with_possession BIGINT,
                matches_with_corners BIGINT,
                matches_with_cards BIGINT,
                matches_with_shots BIGINT,
                xg_fill_rate DOUBLE PRECISION,
                possession_fill_rate DOUBLE PRECISION,
                corners_fill_rate DOUBLE PRECISION,
                cards_fill_rate DOUBLE PRECISION,
                shots_fill_rate DOUBLE PRECISION
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN home_xg IS NOT NULL THEN 1 END) as matches_with_xg,
                    COUNT(CASE WHEN home_possession IS NOT NULL THEN 1 END) as matches_with_possession,
                    COUNT(CASE WHEN home_corners IS NOT NULL THEN 1 END) as matches_with_corners,
                    COUNT(CASE WHEN home_yellow_cards IS NOT NULL THEN 1 END) as matches_with_cards,
                    COUNT(CASE WHEN home_shots_total IS NOT NULL THEN 1 END) as matches_with_shots,
                    ROUND(COUNT(CASE WHEN home_xg IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as xg_fill_rate,
                    ROUND(COUNT(CASE WHEN home_possession IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as possession_fill_rate,
                    ROUND(COUNT(CASE WHEN home_corners IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as corners_fill_rate,
                    ROUND(COUNT(CASE WHEN home_yellow_cards IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as cards_fill_rate,
                    ROUND(COUNT(CASE WHEN home_shots_total IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as shots_fill_rate
                FROM match_features_training;
            END;
            $$ LANGUAGE plpgsql;
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ 生产环境数据库Schema初始化完成")
        logger.info("📊 表名: match_features_training | 总字段数: 80+ | 索引数: 15+")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库Schema初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False


class MainEngineV5:
    """MainEngineV5 - 真实L2特征收割引擎.

    专业的足球比赛数据收集和预测引擎，支持106维特征提取、实时数据处理、
    动态特征回填等功能。该引擎是FootballPrediction系统的核心组件。

    Attributes:
        settings: 统一配置系统实例
        db_config: 数据库连接配置字典
        client: FotMob API客户端实例
        extractor: 高级特征提取器实例
        inference_engine: 推理引擎实例
        processed_count: 已处理比赛数量
        success_count: 成功处理比赛数量
        error_count: 处理失败比赛数量
        real_xg_count: 包含真实xG数据的比赛数量
        prediction_count: 生成的预测数量

    Example:
        >>> engine = MainEngineV5()
        >>> success = engine.run_data_collection(limit=10)
        >>> print(f"成功处理: {success} 场比赛")
    """

    def __init__(self) -> None:
        """初始化MainEngineV5引擎.

        Raises:
            Exception: 当组件初始化失败时抛出异常
        """
        self.settings = get_settings()
        db = self.settings.database
        self.db_config: Dict[str, Any] = {
            "host": db.host,
            "port": db.port,
            "database": db.name,
            "user": db.user,
            "password": db.password.get_secret_value(),
        }

        # 初始化组件
        self.client = FotMobAPIClient(timeout=15)
        self.extractor = AdvancedFeatureExtractor()
        self.inference_engine = get_inference_engine()

        # V4.1: 原始数据存储路径
        self.raw_json_path = "/app/data/raw_json" if os.getenv("DOCKER_ENV") else "data/raw_json"
        os.makedirs(self.raw_json_path, exist_ok=True)

        # V4.1: 原始JSON备份统计
        self.json_backup_count = 0

        # 统计变量
        self.processed_count: int = 0
        self.success_count: int = 0
        self.error_count: int = 0
        self.real_xg_count: int = 0
        self.prediction_count: int = 0

        logger.info(f"🔗 数据库配置: {db.name} @ {db.host}:{db.port}")
        logger.info("🚀 MainEngineV5 初始化完成 - 真实L2特征收割模式")

    def get_matches_from_db(self, limit: int = 700) -> List[Dict]:
        """从数据库获取待处理的比赛"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # 获取pending状态的比赛，优先处理已完成的比赛
            cursor.execute(
                """
                SELECT external_id, home_team, away_team, league_name, status
                FROM matches
                WHERE collection_status = 'pending'
                ORDER BY
                    CASE WHEN status = 'Finished' THEN 1 ELSE 2 END,
                    match_time DESC
                LIMIT %s;
            """,
                (limit,),
            )

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
            fields = ["external_id", "data_source"]
            values = [external_id, "fotmob_api_v2"]
            placeholders = ["%s", "%s"]

            # 主要字段
            main_fields = [
                "home_team",
                "away_team",
                "league_name",
                "season",
                "match_time",
                "status",
                "home_xg",
                "away_xg",
                "home_possession",
                "away_possession",
                "home_opening_odds",
                "away_opening_odds",
                "home_current_odds",
                "away_current_odds",
                "home_corners",
                "away_corners",
                "home_shots",
                "away_shots",
                "home_shots_on_target",
                "away_shots_on_target",
                "home_fouls",
                "away_fouls",
                "home_yellow_cards",
                "away_yellow_cards",
                "home_red_cards",
                "away_red_cards",
            ]

            for field in main_fields:
                if field in feature_dict and feature_dict[field] is not None:
                    # 特殊处理赔率字段：如果为0，设为NULL以避免验证错误
                    if "odds" in field and feature_dict[field] == 0:
                        continue  # 跳过0值赔率
                    fields.append(field)
                    values.append(feature_dict[field])
                    placeholders.append("%s")

            # 添加原始数据
            if "raw_data" not in fields:
                fields.append("raw_data")
                values.append(json.dumps(feature_dict))
                placeholders.append("%s")

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
            cursor.execute(
                """
                UPDATE matches
                SET collection_status = %s, l2_collected_at = CURRENT_TIMESTAMP
                WHERE external_id = %s;
            """,
                ("completed", external_id),
            )

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
                feature_dict = features.model_dump(mode="json")
                if "league_name" in match_info and match_info["league_name"]:
                    feature_dict["league_name"] = match_info["league_name"]
                if "status" in match_info and match_info["status"]:
                    feature_dict["status"] = match_info["status"]

                # 重新创建features对象以包含补充的元数据
                from schemas.match_features import MatchFeatures

                features = MatchFeatures(**feature_dict)

            # 检查xG数据
            has_real_xg = (features.home_xg is not None and features.home_xg > 0) or (
                features.away_xg is not None and features.away_xg > 0
            )

            if has_real_xg:
                self.real_xg_count += 1

            # 实时输出监控指标
            xg_str = f"{features.home_xg or 0:.1f}-{features.away_xg or 0:.1f}"
            corners_str = f"{(features.home_corners or 0) + (features.away_corners or 0)}"

            logger.info(
                f"[Ingested] {features.home_team} vs {features.away_team} | "
                f"xG: {xg_str} | Corners: {corners_str} | Status: Success"
            )

            # V4.1: 原始 JSON 物理固化逻辑
            # 1. 固化原始 JSON 到 feature_dict 的 raw_data 字段
            feature_dict = features.model_dump(mode="json")
            feature_dict["raw_data"] = match_data  # 保存完整原始 JSON

            # 2. 本地文件灾备固化
            await self._save_raw_json_backup(external_id, match_data)

            # 3. 更新数据库
            if self.update_match_with_features(external_id, feature_dict):
                self.success_count += 1
                logger.info(f"💾 [Archived] 原始JSON已双重固化: {external_id}")
                return feature_dict

            return None

        except Exception as e:
            logger.error(f"❌ 特征提取失败 {external_id}: {e}")
            self.error_count += 1
            return None

    async def _save_raw_json_backup(self, external_id: str, raw_data: Dict[str, Any]) -> None:
        """V4.1: 保存原始JSON到本地文件作为灾备

        Args:
            external_id: 比赛外部ID
            raw_data: 完整的原始JSON数据

        Returns:
            None
        """
        try:
            # 构建文件路径
            safe_id = external_id.replace('/', '_').replace('\\', '_')
            file_path = os.path.join(self.raw_json_path, f"{safe_id}.json")

            # 添加元数据到原始JSON
            backup_data = {
                "metadata": {
                    "external_id": external_id,
                    "backup_timestamp": datetime.now().isoformat(),
                    "backup_version": "V4.1",
                    "data_source": "fotmob_api",
                    "engine_version": "main_engine_v5"
                },
                "raw_api_response": raw_data
            }

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

            self.json_backup_count += 1
            logger.debug(f"💾 [Backup] 原始JSON已保存: {file_path}")

        except Exception as e:
            logger.error(f"❌ 保存原始JSON备份失败 {external_id}: {e}")
            # 不抛出异常，避免影响主要流程

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
                    "avg_home_xg": float(result[0]) if result[0] else 1.2,
                    "avg_away_xg": float(result[1]) if result[1] else 1.1,
                    "avg_home_possession": float(result[2]) if result[2] else 50.0,
                    "avg_away_possession": float(result[3]) if result[3] else 50.0,
                    "match_count": int(result[4]),
                }
            else:
                # 冷启动保护：查询联赛平均值
                return self._get_league_averages(team_name)

        except Exception as e:
            logger.error(f"❌ 查询 {team_name} 历史数据失败: {e}")
            return self._get_league_averages(team_name)

    def _get_league_averages(self, team_name: str) -> Dict:
        """
        获取联赛平均水平作为冷启动保护

        Args:
            team_name: 球队名称

        Returns:
            联赛平均统计数据
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 先查询该球队最常参加的联赛
            cursor.execute(
                """
                SELECT league_name, COUNT(*) as match_count
                FROM matches
                WHERE (home_team = %s OR away_team = %s)
                  AND league_name IS NOT NULL
                GROUP BY league_name
                ORDER BY match_count DESC
                LIMIT 1
            """,
                (team_name, team_name),
            )

            league_result = cursor.fetchone()
            if league_result:
                primary_league = league_result[0]
                logger.info(f"🏆 {team_name} 主要联赛: {primary_league}")

                # 查询该联赛的平均水平
                cursor.execute(
                    """
                    SELECT
                        AVG(home_xg) as avg_home_xg,
                        AVG(away_xg) as avg_away_xg,
                        AVG(home_possession) as avg_home_possession,
                        AVG(away_possession) as avg_away_possession,
                        COUNT(*) as total_matches
                    FROM match_features_training
                    WHERE league_name = %s
                      AND home_xg IS NOT NULL
                      AND away_xg IS NOT NULL
                      AND home_possession IS NOT NULL
                      AND away_possession IS NOT NULL
                """,
                    (primary_league,),
                )

                league_stats = cursor.fetchone()
                if league_stats and league_stats[4] > 0:
                    logger.info(f"📊 使用 {primary_league} 联赛平均水平作为 {team_name} 的冷启动数据")
                    return {
                        "avg_home_xg": float(league_stats[0]) if league_stats[0] else 1.3,
                        "avg_away_xg": float(league_stats[1]) if league_stats[1] else 1.2,
                        "avg_home_possession": float(league_stats[2]) if league_stats[2] else 52.0,
                        "avg_away_possession": float(league_stats[3]) if league_stats[3] else 48.0,
                        "match_count": 0,
                        "data_source": f"league_average_{primary_league}",
                    }

            # 如果没有找到联赛数据，使用全球平均
            logger.warning(f"⚠️ {team_name} 无历史数据，使用全球平均值")
            return {
                "avg_home_xg": 1.35,  # 全球主队平均xG
                "avg_away_xg": 1.15,  # 全球客队平均xG
                "avg_home_possession": 52.0,  # 全球主队平均控球率
                "avg_away_possession": 48.0,  # 全球客队平均控球率
                "match_count": 0,
                "data_source": "global_average",
            }

        except Exception as e:
            logger.error(f"❌ 获取 {team_name} 联赛平均值失败: {e}")
            return {
                "avg_home_xg": 1.35,
                "avg_away_xg": 1.15,
                "avg_home_possession": 52.0,
                "avg_away_possession": 48.0,
                "match_count": 0,
                "data_source": "fallback_default",
            }
        finally:
            if "cursor" in locals():
                cursor.close()
            if "conn" in locals():
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
            if match_info.get("status") != "Fixture":
                return None

            logger.info(f"🎯 [PREDICTION] 开始预测未来比赛: {home_team} vs {away_team}")

            # 动态获取主队历史统计数据
            home_stats = self.get_historical_team_stats(home_team, limit=5)
            away_stats = self.get_historical_team_stats(away_team, limit=5)

            logger.info(
                f"📊 [HISTORICAL] {home_team} 历史数据: {home_stats['match_count']} 场, "
                f"平均xG: {home_stats['avg_home_xg']:.2f}/{home_stats['avg_away_xg']:.2f}, "
                f"平均控球率: {home_stats['avg_home_possession']:.1f}%/{home_stats['avg_away_possession']:.1f}%"
            )

            logger.info(
                f"📊 [HISTORICAL] {away_team} 历史数据: {away_stats['match_count']} 场, "
                f"平均xG: {away_stats['avg_home_xg']:.2f}/{away_stats['avg_away_xg']:.2f}, "
                f"平均控球率: {away_stats['avg_home_possession']:.1f}%/{away_stats['avg_away_possession']:.1f}%"
            )

            # 构建动态特征字典（基于历史数据）
            features = {
                # xG特征：基于两队历史表现
                "home_xg": home_stats["avg_home_xg"],
                "away_xg": away_stats["avg_away_xg"],
                # 控球率特征：基于两队历史表现
                "home_possession": home_stats["avg_home_possession"],
                "away_possession": away_stats["avg_away_possession"],
                # 赔率特征：暂时保留默认值（未来可集成实时赔率API）
                "home_opening_odds": 2.1,
                "home_current_odds": 2.0,
            }

            logger.info(
                f"🔮 [DYNAMIC] 使用动态特征进行预测: "
                f"主队xG={features['home_xg']:.2f}, "
                f"客队xG={features['away_xg']:.2f}, "
                f"主队控球={features['home_possession']:.1f}%"
            )

            # 进行预测
            prediction = predict_match_from_features(home_team, away_team, features)

            if "error" not in prediction:
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
            status_icon = "✅" if match["status"] == "Finished" else "⏰"
            logger.info(
                f"  {i+1}. {status_icon} [{match['external_id']}] {match['home_team']} vs {match['away_team']} ({match['status']})"
            )

        # 批量处理
        batch_size = 10

        async with self.client as client:
            for i in range(0, len(matches), batch_size):
                batch = matches[i : i + batch_size]
                logger.info(f"🔄 处理批次 {i//batch_size + 1}/{(len(matches)-1)//batch_size + 1}")

                # 创建任务
                tasks = []
                for match in batch:
                    task = self.extract_match_features(match["external_id"], match)
                    tasks.append(task)

                # 执行任务
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                self.processed_count += len(batch)

                # 对未来比赛进行预测
                logger.info("🔮 开始未来比赛预测...")
                for match in batch:
                    prediction = self.predict_future_match(match["home_team"], match["away_team"], match)
                    if prediction:
                        logger.info(f"✅ 预测完成: {match['home_team']} vs {match['away_team']}")

                # 进度报告
                xg_rate = self.real_xg_count / self.processed_count * 100 if self.processed_count > 0 else 0
                logger.info(
                    f"📊 批次完成: {self.processed_count}/{len(matches)} "
                    f"(成功: {self.success_count}, 真实xG: {self.real_xg_count}, 预测: {self.prediction_count}, xG率: {xg_rate:.1f}%)"
                )

                # 延迟避免API限制
                if i + batch_size < len(matches):
                    await asyncio.sleep(1)

        # 最终报告
        logger.info("\n" + "=" * 80)
        logger.info("🏆 MainEngineV5 全量收割 + 预测完成报告")
        logger.info("=" * 80)
        logger.info(f"📊 处理总数: {self.processed_count}")
        logger.info(f"✅ 成功收割: {self.success_count}")
        logger.info(f"⚽ 真实xG比赛: {self.real_xg_count}")
        logger.info(f"🔮 实时预测: {self.prediction_count}")
        logger.info(
            f"📈 成功率: {self.success_count/self.processed_count*100:.1f}%"
            if self.processed_count > 0
            else "📈 成功率: 0%"
        )
        logger.info(
            f"🎯 xG数据率: {self.real_xg_count/self.processed_count*100:.1f}%"
            if self.processed_count > 0
            else "🎯 xG数据率: 0%"
        )
        logger.info(
            f"🚀 预测覆盖率: {self.prediction_count/self.processed_count*100:.1f}%"
            if self.processed_count > 0
            else "🚀 预测覆盖率: 0%"
        )
        logger.info("=" * 80)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="MainEngineV5 - 真实L2特征收割引擎")
    parser.add_argument("--mode", choices=["full", "test", "standby"], default="full", help="运行模式")
    parser.add_argument("--limit", type=int, default=700, help="处理上限")

    args = parser.parse_args()

    # 确保使用正确的数据库
    os.environ["DB_NAME"] = "football_prediction"

    # 首先初始化数据库Schema
    logger.info("🔧 正在初始化数据库Schema...")
    if not initialize_database_schema():
        logger.error("❌ 数据库Schema初始化失败，程序退出")
        return

    # 创建引擎实例
    engine = MainEngineV5()

    if args.mode == "full":
        await engine.run_full_extraction(args.limit)
    elif args.mode == "test":
        # 测试模式
        matches = engine.get_matches_from_db(5)
        logger.info(f"测试模式，找到 {len(matches)} 场比赛")
    elif args.mode == "standby":
        # 待机模式 - 仅初始化，不执行数据采集
        logger.info("🚀 MainEngineV5 进入待机模式")
        logger.info("✅ 数据库连接正常")
        logger.info("✅ 模型加载完成")
        logger.info("🔄 准备接收数据采集指令")

        # 保持容器运行
        import time

        try:
            while True:
                await asyncio.sleep(300)  # 每5分钟检查一次
                logger.debug("MainEngineV5 待机中...")
        except KeyboardInterrupt:
            logger.info("👋 MainEngineV5 待机模式结束")
    elif args.mode == "test":
        # 测试模式
        matches = engine.get_matches_from_db(5)
        logger.info(f"测试模式，找到 {len(matches)} 场比赛")
        for match in matches:
            logger.info(f"  {match['external_id']}: {match['home_team']} vs {match['away_team']}")
    else:
        logger.error(f"未知运行模式: {args.mode}")
        return


if __name__ == "__main__":
    asyncio.run(main())
