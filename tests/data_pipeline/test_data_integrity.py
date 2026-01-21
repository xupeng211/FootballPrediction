#!/usr/bin/env python3
"""
数据完整性测试 - TDD驱动验证物理数据质量
确保数据库关联率=100%，核心特征NULL密度<5%
"""

import logging
from typing import Any, Dict, List, Tuple

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.database.schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


class TestDataIntegrity:
    """数据完整性测试类 - TDD核心验证"""

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """数据库连接前置条件"""
        self.settings = get_settings()
        self.db = self.settings.database
        self.schema_manager = get_schema_manager()

        # 建立数据库连接
        self.conn = psycopg2.connect(
            host=self.db.host,
            port=self.db.port,
            database=self.db.name,
            user=self.db.user,
            password=self.db.password.get_secret_value()
        )

        yield

        # 清理资源
        if self.conn and not self.conn.closed:
            self.conn.close()

    def test_database_connection_success(self):
        """测试: 数据库连接必须成功"""
        assert self.conn is not None
        assert not self.conn.closed

        with self.conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_external_id_alignment_100_percent(self):
        """测试: external_id关联率必须=100%"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_features,
                    COUNT(m.external_id) as linked_matches,
                    COUNT(m.external_id) * 100.0 / COUNT(*) as link_rate
                FROM match_features_training ft
                LEFT JOIN matches m ON ft.external_id = m.external_id
            """)

            result = cursor.fetchone()

            # 验证数据量
            assert result['total_features'] > 0, "必须有特征数据"

            # 核心要求：关联率必须=100%
            assert result['link_rate'] == 100.0, f"ID关联率必须100%，当前: {result['link_rate']:.2f}%"

            logger.info(f"✅ ID关联率验证: {result['link_rate']}% ({result['linked_matches']}/{result['total_features']})")

    def test_core_features_null_density_under_5_percent(self):
        """测试: 核心特征(xG, 控球率, 结果)NULL密度必须<5%"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(home_xg) as home_xg_count,
                    COUNT(away_xg) as away_xg_count,
                    COUNT(home_possession) as home_possession_count,
                    COUNT(away_possession) as away_possession_count,
                    COUNT(home_score) as home_score_count,
                    COUNT(away_score) as away_score_count
                FROM match_features_training
            """)

            result = cursor.fetchone()
            total = result['total_records']

            # 计算每个核心特征的NULL密度
            core_features = {
                'home_xg': result['home_xg_count'],
                'away_xg': result['away_xg_count'],
                'home_possession': result['home_possession_count'],
                'away_possession': result['away_possession_count'],
                'home_score': result['home_score_count'],
                'away_score': result['away_score_count']
            }

            for feature_name, non_null_count in core_features.items():
                fill_rate = (non_null_count / total) * 100
                null_density = 100 - fill_rate

                # 核心要求：NULL密度必须<5%
                assert null_density < 5.0, f"{feature_name} NULL密度过高: {null_density:.2f}% (要求<5%)"

                logger.info(f"✅ {feature_name}: 填充率{fill_rate:.1f}%, NULL密度{null_density:.1f}%")

    def test_data_quality_score_acceptable(self):
        """测试: 数据质量分数必须可接受"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    AVG(feature_quality_score) as avg_quality,
                    MIN(feature_quality_score) as min_quality,
                    MAX(feature_quality_score) as max_quality,
                    COUNT(*) FILTER (WHERE feature_quality_score >= 0.8) as high_quality_count,
                    COUNT(*) as total_count
                FROM match_features_training
                WHERE feature_quality_score IS NOT NULL
            """)

            result = cursor.fetchone()

            # 验证平均质量分数
            assert result['avg_quality'] is not None, "必须有质量分数"
            assert result['avg_quality'] >= 0.7, f"平均质量分数过低: {result['avg_quality']:.3f} (要求>=0.7)"

            # 验证高质量数据占比
            high_quality_rate = result['high_quality_count'] / result['total_count'] * 100
            assert high_quality_rate >= 60.0, f"高质量数据占比过低: {high_quality_rate:.1f}% (要求>=60%)"

            logger.info(f"✅ 数据质量: 平均{result['avg_quality']:.3f}, 高质量占比{high_quality_rate:.1f}%")

    def test_feature_schema_completeness(self):
        """测试: 特征Schema完整性"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 检查核心表是否存在
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('match_features_training', 'matches', 'raw_match_data')
            """)

            tables = {row['table_name'] for row in cursor.fetchall()}
            required_tables = {'match_features_training', 'matches', 'raw_match_data'}

            assert required_tables.issubset(tables), f"缺少必要表: {required_tables - tables}"

            # 检查关键字段是否存在
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'match_features_training'
                AND table_schema = 'public'
            """)

            columns = {row['column_name'] for row in cursor.fetchall()}
            required_columns = {
                'external_id', 'home_team', 'away_team', 'match_time',
                'home_xg', 'away_xg', 'home_possession', 'away_possession',
                'home_score', 'away_score', 'data_source', 'feature_quality_score'
            }

            assert required_columns.issubset(columns), f"缺少必要字段: {required_columns - columns}"

            logger.info(f"✅ Schema验证通过: {len(tables)}个表, {len(columns)}个字段")

    def test_data_consistency_validation(self):
        """测试: 数据一致性验证"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 检查比分一致性
            cursor.execute("""
                SELECT COUNT(*) as inconsistent_scores
                FROM match_features_training
                WHERE (home_score IS NOT NULL AND away_score IS NULL)
                   OR (home_score IS NULL AND away_score IS NOT NULL)
                   OR (home_score < 0 OR away_score < 0)
            """)

            inconsistent_count = cursor.fetchone()['inconsistent_scores']
            assert inconsistent_count == 0, f"存在{inconsistent_count}条不一致的比分记录"

            # 检查xG合理性
            cursor.execute("""
                SELECT COUNT(*) as unreasonable_xg
                FROM match_features_training
                WHERE (home_xg IS NOT NULL AND (home_xg < 0 OR home_xg > 10))
                   OR (away_xg IS NOT NULL AND (away_xg < 0 OR away_xg > 10))
            """)

            unreasonable_xg = cursor.fetchone()['unreasonable_xg']
            assert unreasonable_xg == 0, f"存在{unreasonable_xg}条不合理的xG记录"

            # 检查控球率合理性
            cursor.execute("""
                SELECT COUNT(*) as unreasonable_possession
                FROM match_features_training
                WHERE (home_possession IS NOT NULL AND (home_possession < 0 OR home_possession > 100))
                   OR (away_possession IS NOT NULL AND (away_possession < 0 OR away_possession > 100))
            """)

            unreasonable_possession = cursor.fetchone()['unreasonable_possession']
            assert unreasonable_possession == 0, f"存在{unreasonable_possession}条不合理的控球率记录"

            logger.info("✅ 数据一致性验证通过")

    def test_physical_feature_dimensions(self):
        """测试: 物理特征维度验证 - 确保没有大量NULL字段"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 获取所有数值字段
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'match_features_training'
                AND table_schema = 'public'
                AND data_type IN ('integer', 'double precision', 'numeric', 'real')
                AND column_name NOT IN ('id', 'external_id')
            """)

            numeric_columns = [row['column_name'] for row in cursor.fetchall()]

            # 检查每个字段的非空率
            low_completeness_fields = []
            for column in numeric_columns:
                cursor.execute(f"""
                    SELECT COUNT(*) as total, COUNT({column}) as non_null_count
                    FROM match_features_training
                """)

                result = cursor.fetchone()
                fill_rate = (result['non_null_count'] / result['total']) * 100

                if fill_rate < 50:  # 填充率低于50%认为是低质量字段
                    low_completeness_fields.append((column, fill_rate))

            # 确保低质量字段数量可控
            assert len(low_completeness_fields) <= 20, f"低质量字段过多: {len(low_completeness_fields)}个 (要求<=20个)"

            for field_name, fill_rate in low_completeness_fields:
                logger.warning(f"⚠️ 低质量字段: {field_name} - 填充率{fill_rate:.1f}%")

            # 计算整体特征维度（物理非空特征）
            cursor.execute("""
                SELECT COUNT(*) as total_records
                FROM match_features_training
                LIMIT 1
            """)

            total_records = cursor.fetchone()['total_records']
            logger.info(f"✅ 物理特征维度验证: {len(numeric_columns)}个数值字段, {len(low_completeness_fields)}个低质量字段")

    def test_pipeline_performance_benchmarks(self):
        """测试: 数据管线性能基准"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 测试查询性能
            import time

            start_time = time.time()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM match_features_training
                WHERE feature_quality_score > 0.8
            """)

            result = cursor.fetchone()
            query_time = time.time() - start_time

            # 查询时间应该 < 1秒
            assert query_time < 1.0, f"查询性能过慢: {query_time:.3f}秒 (要求<1秒)"

            logger.info(f"✅ 性能基准测试: {query_time:.3f}秒, 返回{result['count']}条高质量记录")


if __name__ == "__main__":
    # 单独运行测试
    pytest.main([__file__, "-v", "--tb=short"])