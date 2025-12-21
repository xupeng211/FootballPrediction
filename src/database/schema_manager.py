#!/usr/bin/env python3
"""
Database Schema Manager - 生产级数据库架构管理
统一管理所有数据库操作、ID对齐和Schema维护
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


class SchemaManager:
    """数据库Schema管理器 - 生产级架构管理"""

    def __init__(self):
        """初始化Schema管理器"""
        self.settings = get_settings()
        self.conn = None

    def get_connection(self):
        """获取数据库连接"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value()
            )
        return self.conn

    def initialize_production_schema(self) -> bool:
        """
        初始化生产环境完整Schema

        Returns:
            bool: 初始化是否成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            logger.info("🏗️ 初始化生产环境数据库Schema...")

            # 创建match_features_training表
            self._create_match_features_table(cursor)

            # 创建matches表
            self._create_matches_table(cursor)

            # 创建raw_match_data表
            self._create_raw_match_data_table(cursor)

            # 创建所有索引
            self._create_indexes(cursor)

            # 创建触发器
            self._create_triggers(cursor)

            conn.commit()
            logger.info("✅ 生产环境Schema初始化完成")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Schema初始化失败: {e}")
            return False

    def _create_match_features_table(self, cursor):
        """创建match_features_training表"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_features_training (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR(50) NOT NULL UNIQUE,
                match_time TIMESTAMP WITH TIME ZONE NOT NULL,
                home_team VARCHAR(100) NOT NULL,
                away_team VARCHAR(100) NOT NULL,
                home_score INTEGER,
                away_score INTEGER,

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
                home_possession_second_half DOUBLE PRECISION,
                away_possession_second_half DOUBLE PRECISION,
                possession_control_periods VARCHAR(50),

                -- 角球特征 (6个)
                home_corners INTEGER,
                away_corners INTEGER,
                corners_total INTEGER,
                corners_diff INTEGER,
                home_corners_first_half INTEGER,
                away_corners_first_half INTEGER,

                -- 射门特征 (6个)
                home_shots_total INTEGER,
                away_shots_total INTEGER,
                home_shots_on_target INTEGER,
                away_shots_on_target INTEGER,
                home_shots_off_target INTEGER,
                away_shots_off_target INTEGER,

                -- 红黄牌特征 (6个)
                home_yellow_cards INTEGER,
                away_yellow_cards INTEGER,
                home_red_cards INTEGER,
                away_red_cards INTEGER,
                total_cards_home INTEGER,
                total_cards_away INTEGER,

                -- 传球特征 (6个)
                home_passes INTEGER,
                away_passes INTEGER,
                home_pass_accuracy DOUBLE PRECISION,
                away_pass_accuracy DOUBLE PRECISION,
                home_successful_passes INTEGER,
                away_successful_passes INTEGER,

                -- 犯规特征 (4个)
                home_fouls INTEGER,
                away_fouls INTEGER,
                home_fouls_first_half INTEGER,
                away_fouls_first_half INTEGER,

                -- 越位特征 (4个)
                home_offsides INTEGER,
                away_offsides INTEGER,
                home_offside_traps INTEGER,
                away_offside_traps INTEGER,

                -- 扑救特征 (4个)
                home_saves INTEGER,
                away_saves INTEGER,
                home_goalkeeper_saves INTEGER,
                away_goalkeeper_saves INTEGER,

                -- 控球深度特征 (6个)
                home_possession_third_final DOUBLE PRECISION,
                away_possession_third_final DOUBLE PRECISION,
                home_possession_third_middle DOUBLE PRECISION,
                away_possession_third_middle DOUBLE PRECISION,
                home_possession_third_own DOUBLE PRECISION,
                away_possession_third_own DOUBLE PRECISION,

                -- 球员评分特征 (20个)
                home_avg_rating DOUBLE PRECISION,
                away_avg_rating DOUBLE PRECISION,
                home_best_player_rating DOUBLE PRECISION,
                away_best_player_rating DOUBLE PRECISION,
                home_players_with_rating_7 INTEGER,
                away_players_with_rating_7 INTEGER,
                home_players_with_rating_8 INTEGER,
                away_players_with_rating_8 INTEGER,
                home_top_scorer_rating DOUBLE PRECISION,
                away_top_scorer_rating DOUBLE PRECISION,
                home_top_midfielder_rating DOUBLE PRECISION,
                away_top_midfielder_rating DOUBLE PRECISION,
                home_top_defender_rating DOUBLE PRECISION,
                away_top_defender_rating DOUBLE PRECISION,
                home_top_goalkeeper_rating DOUBLE PRECISION,
                away_top_goalkeeper_rating DOUBLE PRECISION,
                home_rating_variance DOUBLE PRECISION,
                away_rating_variance DOUBLE PRECISION,
                home_rating_consistency DOUBLE PRECISION,
                away_rating_consistency DOUBLE PRECISION,

                -- 战术风格特征 (30个)
                home_high_press_success_rate DOUBLE PRECISION,
                away_high_press_success_rate DOUBLE PRECISION,
                home_counter_attack_goals INTEGER,
                away_counter_attack_goals INTEGER,
                home_set_piece_goals INTEGER,
                away_set_piece_goals INTEGER,
                home_long_ball_success_rate DOUBLE PRECISION,
                away_long_ball_success_rate DOUBLE PRECISION,
                home_short_pass_success_rate DOUBLE PRECISION,
                away_short_pass_success_rate DOUBLE PRECISION,
                home_cross_success_rate DOUBLE PRECISION,
                away_cross_success_rate DOUBLE PRECISION,
                home_dribble_success_rate DOUBLE PRECISION,
                away_dribble_success_rate DOUBLE PRECISION,
                home_aerial_duel_win_rate DOUBLE PRECISION,
                away_aerial_duel_win_rate DOUBLE PRECISION,
                home_tackles_success_rate DOUBLE PRECISION,
                away_tackles_success_rate DOUBLE PRECISION,
                home_interceptions INTEGER,
                away_interceptions INTEGER,
                home_clearances INTEGER,
                away_clearances INTEGER,
                home_blocked_shots INTEGER,
                away_blocked_shots INTEGER,
                home_big_chances_created INTEGER,
                away_big_chances_created INTEGER,
                home_big_chances_missed INTEGER,
                away_big_chances_missed INTEGER,
                home_penalties_won INTEGER,
                away_penalties_won INTEGER,
                home_penalties_conceded INTEGER,
                away_penalties_conceded INTEGER,

                -- 进阶射门特征 (20个)
                home_xg_from_open_play DOUBLE PRECISION,
                away_xg_from_open_play DOUBLE PRECISION,
                home_xg_from_set_pieces DOUBLE PRECISION,
                away_xg_from_set_pieces DOUBLE PRECISION,
                home_xg_from_penalties DOUBLE PRECISION,
                away_xg_from_penalties DOUBLE PRECISION,
                home_shots_inside_box INTEGER,
                away_shots_inside_box INTEGER,
                home_shots_outside_box INTEGER,
                away_shots_outside_box INTEGER,
                home_shot_accuracy DOUBLE PRECISION,
                away_shot_accuracy DOUBLE PRECISION,
                home_shot_conversion_rate DOUBLE PRECISION,
                away_shot_conversion_rate DOUBLE PRECISION,
                home_expected_assists DOUBLE PRECISION,
                away_expected_assists DOUBLE PRECISION,
                home_key_passes INTEGER,
                away_key_passes INTEGER,
                home_chances_created INTEGER,
                away_chances_created INTEGER,

                -- 赔率特征 (6个)
                home_current_odds DOUBLE PRECISION,
                away_current_odds DOUBLE PRECISION,
                home_opening_odds DOUBLE PRECISION,
                away_opening_odds DOUBLE PRECISION,
                odds_movement_home DOUBLE PRECISION,
                odds_movement_away DOUBLE PRECISION,

                -- 元数据特征
                data_source VARCHAR(50) DEFAULT 'fotmob_api_v2',
                feature_version VARCHAR(20) DEFAULT 'V4.3',
                extraction_confidence DOUBLE PRECISION,
                feature_quality_score DOUBLE PRECISION,
                data_completeness_score DOUBLE PRECISION,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                processing_status VARCHAR(20) DEFAULT 'completed',
                validation_errors TEXT
            );
        """)

        logger.info("✅ 创建match_features_training表")

    def _create_matches_table(self, cursor):
        """创建matches表"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR(50) NOT NULL UNIQUE,
                league_name VARCHAR(100) NOT NULL,
                season VARCHAR(20) NOT NULL,
                match_time TIMESTAMP WITH TIME ZONE NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Fixture',
                home_team VARCHAR(100) NOT NULL,
                away_team VARCHAR(100) NOT NULL,
                result_score VARCHAR(20),
                collection_status VARCHAR(20) DEFAULT 'pending',
                league_id INTEGER,
                home_team_id INTEGER,
                away_team_id INTEGER,
                venue_name VARCHAR(200),
                round_info JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                l1_collected_at TIMESTAMP WITH TIME ZONE,
                l2_collected_at TIMESTAMP WITH TIME ZONE
            );
        """)

        logger.info("✅ 创建matches表")

    def _create_raw_match_data_table(self, cursor):
        """创建raw_match_data表"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_match_data (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR(50) NOT NULL,
                raw_data JSONB NOT NULL,
                data_version VARCHAR(20) DEFAULT 'v1.0',
                api_source VARCHAR(50) DEFAULT 'fotmob',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (external_id) REFERENCES matches(external_id) ON UPDATE CASCADE ON DELETE CASCADE
            );
        """)

        logger.info("✅ 创建raw_match_data表")

    def _create_indexes(self, cursor):
        """创建性能优化索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_match_features_external_id ON match_features_training(external_id);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_match_time ON match_features_training(match_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_data_source ON match_features_training(data_source);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_processing_status ON match_features_training(processing_status);",
            "CREATE INDEX IF NOT EXISTS idx_match_features_created_at ON match_features_training(created_at DESC);",

            "CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);",
            "CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league_name, season);",
            "CREATE INDEX IF NOT EXISTS idx_matches_match_time ON matches(match_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);",
            "CREATE INDEX IF NOT EXISTS idx_matches_collection_status ON matches(collection_status);",

            "CREATE INDEX IF NOT EXISTS idx_raw_match_external_id ON raw_match_data(external_id);",
            "CREATE INDEX IF NOT EXISTS idx_raw_match_created_at ON raw_match_data(created_at DESC);"
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        logger.info("✅ 创建所有性能索引")

    def _create_triggers(self, cursor):
        """创建时间戳触发器"""
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        cursor.execute("""
            DROP TRIGGER IF EXISTS update_match_features_updated_at ON match_features_training;
            CREATE TRIGGER update_match_features_updated_at
                BEFORE UPDATE ON match_features_training
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

        cursor.execute("""
            DROP TRIGGER IF EXISTS update_matches_updated_at ON matches;
            CREATE TRIGGER update_matches_updated_at
                BEFORE UPDATE ON matches
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

        logger.info("✅ 创建时间戳触发器")

    def align_external_ids(self) -> Dict[str, Any]:
        """
        强制对齐所有external_id为FotMob数字格式

        Returns:
            Dict: 对齐结果统计
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            logger.info("🔄 开始强制ID对齐...")

            # 执行批量ID更新
            cursor.execute("""
                UPDATE match_features_training
                SET external_id =
                    CASE
                        WHEN external_id ~ '^extra_bundesliga_%' THEN '10' || LPAD(SUBSTRING(external_id FROM LENGTH('extra_bundesliga_') + 1), 4, '0')
                        WHEN external_id ~ '^extra_la_liga_%' THEN '20' || LPAD(SUBSTRING(external_id FROM LENGTH('extra_la_liga_') + 1), 4, '0')
                        WHEN external_id ~ '^extra_seriea_%' THEN '30' || LPAD(SUBSTRING(external_id FROM LENGTH('extra_seriea_') + 1), 4, '0')
                        WHEN external_id ~ '^feature_bundesliga_%' THEN '11' || LPAD(SUBSTRING(external_id FROM LENGTH('feature_bundesliga_') + 1), 4, '0')
                        WHEN external_id ~ '^feature_la_liga_%' THEN '21' || LPAD(SUBSTRING(external_id FROM LENGTH('feature_la_liga_') + 1), 4, '0')
                        WHEN external_id ~ '^feature_seriea_%' THEN '31' || LPAD(SUBSTRING(external_id FROM LENGTH('feature_seriea_') + 1), 4, '0')
                        WHEN external_id ~ '^match_%' THEN '70' || LPAD(SUBSTRING(external_id FROM LENGTH('match_') + 1), 5, '0')
                        WHEN external_id ~ '^final_batch_%' THEN '80' || LPAD(SUBSTRING(external_id FROM LENGTH('final_batch_') + 1), 5, '0')
                        ELSE external_id
                    END
                WHERE external_id ~ '^(extra_|feature_|match_|final_batch_)';
            """)

            updated_count = cursor.rowcount
            logger.info(f"✅ 更新 {updated_count} 条external_id记录")

            # 为新ID创建对应的matches记录
            cursor.execute("""
                INSERT INTO matches (external_id, home_team, away_team, league_name, season, status, collection_status, match_time, created_at, updated_at)
                SELECT
                    ft.external_id,
                    COALESCE(ft.home_team, 'Unknown Home'),
                    COALESCE(ft.away_team, 'Unknown Away'),
                    CASE
                        WHEN ft.external_id LIKE '10%' OR ft.external_id LIKE '11%' THEN 'Bundesliga'
                        WHEN ft.external_id LIKE '20%' OR ft.external_id LIKE '21%' THEN 'La Liga'
                        WHEN ft.external_id LIKE '30%' OR ft.external_id LIKE '31%' THEN 'Serie A'
                        ELSE 'Unknown League'
                    END,
                    '2024',
                    'Finished',
                    'completed',
                    COALESCE(ft.match_time, CURRENT_TIMESTAMP),
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                FROM match_features_training ft
                LEFT JOIN matches m ON ft.external_id = m.external_id
                WHERE m.external_id IS NULL
                  AND ft.external_id ~ '^[0-9]+$';
            """)

            created_count = cursor.rowcount
            logger.info(f"✅ 创建 {created_count} 条matches记录")

            conn.commit()

            # 验证对齐结果
            result = self._verify_alignment(cursor)

            return {
                'updated_records': updated_count,
                'created_matches': created_count,
                'verification': result,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ ID对齐失败: {e}")
            raise

    def _verify_alignment(self, cursor) -> Dict[str, Any]:
        """验证ID对齐结果"""
        cursor.execute("""
            SELECT
                COUNT(*) as total_features,
                COUNT(m.external_id) as linked_matches,
                COUNT(m.external_id) * 100.0 / COUNT(*) as link_rate,
                COUNT(*) FILTER (WHERE ft.external_id ~ '^[0-9]+$') as numeric_ids
            FROM match_features_training ft
            LEFT JOIN matches m ON ft.external_id = m.external_id
        """)

        result = cursor.fetchone()
        return {
            'total_features': result[0],
            'linked_matches': result[1],
            'link_rate': result[2],
            'numeric_ids': result[3],
            'fully_aligned': result[2] >= 99.0
        }

    def bulk_insert_features(self, features_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量插入特征数据 - 原子性操作

        Args:
            features_list: 特征数据列表

        Returns:
            Dict: 插入结果统计
        """
        if not features_list:
            return {'success': True, 'inserted_count': 0, 'errors': []}

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 获取字段名
            field_names = list(features_list[0].keys())
            table_name = "match_features_training"

            # 准备数据
            values_list = []
            for features in features_list:
                values = [features.get(field) for field in field_names]
                values_list.append(values)

            # 使用execute_values进行高性能批量插入
            insert_query = f"""
                INSERT INTO {table_name} ({', '.join(field_names)})
                VALUES %s
                ON CONFLICT (external_id) DO UPDATE SET
                    {', '.join([f"{field} = EXCLUDED.{field}" for field in field_names if field != 'external_id'])},
                    updated_at = CURRENT_TIMESTAMP
            """

            execute_values(cursor, insert_query, values_list, template=None, page_size=100)

            inserted_count = len(features_list)
            conn.commit()

            logger.info(f"✅ 批量插入完成: {inserted_count} 条记录")

            return {
                'success': True,
                'inserted_count': inserted_count,
                'field_count': len(field_names),
                'table_name': table_name
            }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 批量插入失败: {e}")
            return {
                'success': False,
                'inserted_count': 0,
                'error': str(e)
            }

    def validate_features_data(self, features: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证特征数据的完整性

        Args:
            features: 特征数据字典

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 必需字段检查
        required_fields = ['external_id', 'home_team', 'away_team', 'match_time']
        for field in required_fields:
            if not features.get(field):
                errors.append(f"Missing required field: {field}")

        # 数据类型检查
        if features.get('home_xg') is not None:
            try:
                float(features['home_xg'])
            except (ValueError, TypeError):
                errors.append("Invalid home_xg value")

        if features.get('away_xg') is not None:
            try:
                float(features['away_xg'])
            except (ValueError, TypeError):
                errors.append("Invalid away_xg value")

        # 逻辑一致性检查
        if features.get('home_score') is not None and features.get('away_score') is not None:
            try:
                home_score = int(features['home_score'])
                away_score = int(features['away_score'])
                if home_score < 0 or away_score < 0:
                    errors.append("Negative score values not allowed")
            except (ValueError, TypeError):
                errors.append("Invalid score values")

        return len(errors) == 0, errors

    def get_schema_statistics(self) -> Dict[str, Any]:
        """获取Schema统计信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            stats = {}

            # match_features_training统计
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(home_xg) as home_xg_count,
                    COUNT(away_xg) as away_xg_count,
                    COUNT(home_possession) as home_possession_count,
                    COUNT(away_possession) as away_possession_count,
                    AVG(feature_quality_score) as avg_quality_score,
                    MAX(created_at) as latest_record
                FROM match_features_training
            """)

            result = cursor.fetchone()
            stats['match_features'] = {
                'total_records': result[0],
                'home_xg_count': result[1],
                'away_xg_count': result[2],
                'home_possession_count': result[3],
                'away_possession_count': result[4],
                'avg_quality_score': float(result[5]) if result[5] else 0.0,
                'latest_record': str(result[6]) if result[6] else None
            }

            # matches统计
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(result_score) as with_scores,
                    COUNT(DISTINCT league_name) as unique_leagues,
                    COUNT(DISTINCT season) as unique_seasons
                FROM matches
            """)

            result = cursor.fetchone()
            stats['matches'] = {
                'total_records': result[0],
                'with_scores': result[1],
                'unique_leagues': result[2],
                'unique_seasons': result[3]
            }

            return stats

        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}


# 全局Schema管理器实例
_schema_manager = None

def get_schema_manager() -> SchemaManager:
    """获取全局Schema管理器实例"""
    global _schema_manager
    if _schema_manager is None:
        _schema_manager = SchemaManager()
    return _schema_manager