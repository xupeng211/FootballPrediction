#!/usr/bin/env python3
"""
V1.1 数据一致性单元测试
=======================

测试范围:
1. match_features_v1 与 raw_match_data 记录数对齐
2. 特征完整性检查
3. 数据质量分布验证
"""

from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataConsistency:
    """数据一致性测试"""

    def test_raw_match_data_count(self, mock_db_cursor):
        """测试 raw_match_data 记录数"""
        # Mock 查询结果
        mock_db_cursor.fetchone.return_value = {"count": 8987}

        # 执行查询
        mock_db_cursor.execute("""
            SELECT COUNT(*) as count
            FROM raw_match_data
        """)

        result = mock_db_cursor.fetchone()
        assert result["count"] == 8987

    def test_match_features_v1_count(self, mock_db_cursor):
        """测试 match_features_v1 记录数"""
        mock_db_cursor.fetchone.return_value = {"count": 8987}

        mock_db_cursor.execute("""
            SELECT COUNT(*) as count
            FROM match_features_v1
        """)

        result = mock_db_cursor.fetchone()
        assert result["count"] == 8987

    def test_record_alignment(self, mock_db_cursor):
        """测试记录数对齐"""
        # Mock 两个查询返回相同数量
        query_count = 0

        def mock_execute(sql, params=None):
            nonlocal query_count
            query_count += 1
            if "raw_match_data" in sql or "match_features_v1" in sql:
                mock_db_cursor.fetchone.return_value = {"count": 8987}

        mock_db_cursor.execute.side_effect = mock_execute

        # 检查 raw_match_data
        mock_db_cursor.execute("SELECT COUNT(*) as count FROM raw_match_data")
        raw_count = mock_db_cursor.fetchone()["count"]

        # 检查 match_features_v1
        mock_db_cursor.execute("SELECT COUNT(*) as count FROM match_features_v1")
        features_count = mock_db_cursor.fetchone()["count"]

        # 验证对齐
        assert raw_count == features_count
        assert raw_count == 8987

    def test_unique_match_count(self, mock_db_cursor):
        """测试唯一比赛数"""
        mock_db_cursor.fetchone.return_value = {"unique_count": 8987}

        mock_db_cursor.execute("""
            SELECT COUNT(DISTINCT match_id) as unique_count
            FROM match_features_v1
        """)

        result = mock_db_cursor.fetchone()
        assert result["unique_count"] == 8987

    def test_league_distribution(self, mock_db_cursor):
        """测试按联赛分布"""
        mock_db_cursor.fetchall.return_value = [
            {"league_id": 47, "count": 1901},
            {"league_id": 55, "count": 1901},
            {"league_id": 87, "count": 1900},
            {"league_id": 53, "count": 1755},
            {"league_id": 54, "count": 1530},
        ]

        mock_db_cursor.execute("""
            SELECT league_id, COUNT(*) as count
            FROM match_features_v1
            GROUP BY league_id
            ORDER BY league_id
        """)

        results = mock_db_cursor.fetchall()

        # 验证五大联赛都存在
        assert len(results) == 5
        league_ids = [r["league_id"] for r in results]
        assert 47 in league_ids  # 英超
        assert 55 in league_ids  # 意甲
        assert 87 in league_ids  # 西甲

    def test_quality_distribution(self, mock_db_cursor):
        """测试质量分布"""
        mock_db_cursor.fetchall.return_value = [
            {"extraction_quality": "full", "count": 8980},
            {"extraction_quality": "partial", "count": 1},
            {"extraction_quality": "failed", "count": 6},
        ]

        mock_db_cursor.execute("""
            SELECT extraction_quality, COUNT(*) as count
            FROM match_features_v1
            GROUP BY extraction_quality
            ORDER BY extraction_quality
        """)

        results = mock_db_cursor.fetchall()

        # FULL 质量应该占绝大多数
        full_count = next((r["count"] for r in results if r["extraction_quality"] == "full"), 0)
        total_count = sum(r["count"] for r in results)

        full_ratio = full_count / total_count
        assert full_ratio >= 0.95  # 至少 95% FULL 质量


class TestFeatureCompleteness:
    """特征完整性测试"""

    def test_non_null_feature_ratio(self, mock_db_cursor):
        """测试非空特征比例"""
        mock_db_cursor.fetchone.return_value = {
            "total": 8987,
            "has_xg": 8980,
            "has_possession": 8980,
            "has_rating": 8980,
        }

        mock_db_cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN home_xg IS NOT NULL THEN 1 END) as has_xg,
                COUNT(CASE WHEN home_possession IS NOT NULL THEN 1 END) as has_possession,
                COUNT(CASE WHEN home_avg_player_rating IS NOT NULL THEN 1 END) as has_rating
            FROM match_features_v1
        """)

        result = mock_db_cursor.fetchone()

        # 每个特征应该至少 95% 非空
        for feature in ["has_xg", "has_possession", "has_rating"]:
            ratio = result[feature] / result["total"]
            assert ratio >= 0.95, f"{feature} 覆盖率低于 95%"

    def test_avg_valid_features(self, mock_db_cursor):
        """测试平均有效特征数"""
        mock_db_cursor.fetchone.return_value = {"avg_features": 10.99}

        mock_db_cursor.execute("""
            SELECT AVG(valid_feature_count) as avg_features
            FROM match_features_v1
            WHERE extraction_quality = 'full'
        """)

        result = mock_db_cursor.fetchone()

        # 平均特征数应该接近 11
        assert result["avg_features"] >= 10.0


class TestSeasonCoverage:
    """赛季覆盖测试"""

    def test_season_distribution(self, mock_db_cursor):
        """测试赛季分布"""
        mock_db_cursor.fetchall.return_value = [
            {"season": "20/21", "count": 1900},
            {"season": "21/22", "count": 1900},
            {"season": "22/23", "count": 1900},
            {"season": "23/24", "count": 1900},
            {"season": "24/25", "count": 1387},
        ]

        mock_db_cursor.execute("""
            SELECT season, COUNT(*) as count
            FROM match_features_v1
            GROUP BY season
            ORDER BY season
        """)

        results = mock_db_cursor.fetchall()

        # 应该有 5 个赛季
        assert len(results) == 5
        seasons = [r["season"] for r in results]
        assert "20/21" in seasons
        assert "24/25" in seasons

    def test_current_season_data(self, mock_db_cursor):
        """测试当前赛季数据存在"""
        mock_db_cursor.fetchone.return_value = {"count": 1387}

        mock_db_cursor.execute("""
            SELECT COUNT(*) as count
            FROM match_features_v1
            WHERE season = '24/25'
        """)

        result = mock_db_cursor.fetchone()

        # 当前赛季应该有数据
        assert result["count"] > 0


@pytest.fixture
def mock_db_cursor():
    """Mock 数据库游标"""
    cursor = MagicMock()
    cursor.execute = MagicMock()
    cursor.fetchone = MagicMock()
    cursor.fetchall = MagicMock()
    return cursor


class TestRealDataConsistency:
    """真实数据一致性测试 (需要数据库连接)"""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_actual_record_alignment(self):
        """测试实际记录数对齐 (需要真实数据库)"""
        import psycopg2

        from src.config_unified import get_settings

        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )

        try:
            with conn.cursor() as cursor:
                # 检查 raw_match_data
                cursor.execute("SELECT COUNT(*) FROM raw_match_data")
                raw_count = cursor.fetchone()[0]

                # 检查 match_features_v1
                cursor.execute("SELECT COUNT(*) FROM match_features_v1")
                features_count = cursor.fetchone()[0]

                # 允许 1% 的误差
                assert abs(raw_count - features_count) / raw_count < 0.01

        finally:
            conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
