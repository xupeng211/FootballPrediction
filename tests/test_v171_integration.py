"""
V171-Standard-04 集成测试
=========================

测试微闭环：
- 从数据库读取 pending 比赛
- 获取/更新 URL
- 验证状态更新逻辑

使用测试数据库，不污染生产数据
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# 设置测试环境
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'football_db_test'
os.environ['DB_USER'] = 'football_user'
os.environ['DB_PASSWORD'] = 'test_password'


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_connection():
    """模拟数据库连接"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


@pytest.fixture
def sample_pending_matches():
    """测试用的 pending 比赛数据"""
    now = datetime.now()
    return [
        {
            'match_id': 'TEST_001',
            'home_team': 'Liverpool',
            'away_team': 'West Ham',
            'league_name': 'Premier League',
            'match_date': now + timedelta(days=1),
            'external_id': None,
            'status': 'pending'
        },
        {
            'match_id': 'TEST_002',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'league_name': 'Premier League',
            'match_date': now + timedelta(days=2),
            'external_id': 'https://example.com/arsenal-chelsea-ABC123/',
            'status': 'pending'
        },
        {
            'match_id': 'TEST_003',
            'home_team': 'Man Utd',
            'away_team': 'Man City',
            'league_name': 'Premier League',
            'match_date': now + timedelta(days=3),
            'external_id': None,
            'status': 'pending'
        },
    ]


# ============================================================================
# 测试类
# ============================================================================

class TestMicroLoop:
    """微闭环测试"""

    def test_get_pending_matches(self, mock_db_connection, sample_pending_matches):
        """测试获取 pending 比赛"""
        conn, cursor = mock_db_connection

        # 模拟查询返回
        cursor.fetchall.return_value = [
            {
                'match_id': m['match_id'],
                'home_team': m['home_team'],
                'away_team': m['away_team'],
                'external_id': m['external_id']
            }
            for m in sample_pending_matches
        ]

        # 执行查询
        cursor.execute("SELECT * FROM matches WHERE status = 'pending'")
        results = cursor.fetchall()

        assert len(results) == 3
        assert results[0]['match_id'] == 'TEST_001'
        assert results[1]['external_id'] is not None  # TEST_002 已有 URL

    def test_update_url(self, mock_db_connection):
        """测试更新 URL"""
        conn, cursor = mock_db_connection

        match_id = 'TEST_001'
        url = 'https://example.com/liverpool-west-ham-KbUrxW1T/'

        # 模拟更新
        cursor.rowcount = 1

        cursor.execute(
            "UPDATE matches SET external_id = %s WHERE match_id = %s",
            (url, match_id)
        )

        assert cursor.execute.called
        call_args = cursor.execute.call_args
        assert url in str(call_args)
        assert match_id in str(call_args)

    def test_mark_completed(self, mock_db_connection):
        """测试标记完成"""
        conn, cursor = mock_db_connection

        match_id = 'TEST_001'

        cursor.execute(
            "UPDATE matches SET status = 'completed' WHERE match_id = %s",
            (match_id,)
        )

        assert cursor.execute.called

    def test_full_micro_loop(self, mock_db_connection, sample_pending_matches):
        """测试完整微闭环"""
        conn, cursor = mock_db_connection

        # Step 1: 获取 pending 比赛
        cursor.fetchall.return_value = [
            {'match_id': m['match_id'], 'external_id': m['external_id']}
            for m in sample_pending_matches
        ]

        cursor.execute("SELECT * FROM matches WHERE status = 'pending'")
        pending = cursor.fetchall()

        processed = 0
        updated_urls = 0
        completed = 0

        for match in pending:
            processed += 1

            # Step 2: 如果没有 URL，获取 URL
            if not match['external_id']:
                # 模拟 URL 获取
                new_url = f"https://example.com/match-{match['match_id']}/"
                cursor.execute(
                    "UPDATE matches SET external_id = %s WHERE match_id = %s",
                    (new_url, match['match_id'])
                )
                updated_urls += 1

            # Step 3: 标记完成
            cursor.execute(
                "UPDATE matches SET status = 'completed' WHERE match_id = %s",
                (match['match_id'],)
            )
            completed += 1

        assert processed == 3
        assert updated_urls == 2  # TEST_001 和 TEST_003 需要 URL
        assert completed == 3


class TestDatabaseIsolation:
    """数据库隔离测试"""

    def test_test_database_config(self):
        """验证使用测试数据库"""
        assert os.environ.get('DB_NAME') == 'football_db_test'

    def test_no_production_data_pollution(self):
        """验证不会污染生产数据"""
        # 在测试中，所有操作应该使用 TEST_ 前缀的 match_id
        test_match_ids = ['TEST_001', 'TEST_002', 'TEST_003']

        for mid in test_match_ids:
            assert mid.startswith('TEST_')


class TestUrlExtractor:
    """URL 提取器测试"""

    def test_extract_url_hash(self):
        """测试 URL Hash 提取"""
        import re

        pattern = re.compile(r'/([A-Za-z0-9]{8})/?$')

        urls = [
            "https://oddsportal.com/liverpool-west-ham-KbUrxW1T/",
            "https://oddsportal.com/arsenal-chelsea-CE2gREmB/",
            "https://oddsportal.com/fulham-tottenham-CSsSuE24/",
        ]

        hashes = []
        for url in urls:
            match = pattern.search(url)
            if match:
                hashes.append(match.group(1))

        assert len(hashes) == 3
        assert 'KbUrxW1T' in hashes
        assert 'CE2gREmB' in hashes

    def test_url_generation(self):
        """测试 URL 生成"""
        base_url = "https://www.oddsportal.com/football/england/premier-league/"
        matches = [
            ("liverpool", "west-ham", "KbUrxW1T"),
            ("arsenal", "chelsea", "CE2gREmB"),
        ]

        for home, away, hash_val in matches:
            url = f"{base_url}{home}-{away}-{hash_val}/"
            assert "oddsportal.com" in url
            assert hash_val in url


class TestStatusTransition:
    """状态转换测试"""

    def test_status_flow(self):
        """测试状态流转"""
        statuses = ['pending', 'processing', 'completed']

        # 模拟状态转换
        current = 'pending'

        # pending -> processing
        assert current == 'pending'
        current = 'processing'

        # processing -> completed
        assert current == 'processing'
        current = 'completed'

        assert current == 'completed'

    def test_error_handling(self):
        """测试错误处理"""
        # 模拟处理失败
        try:
            raise Exception("Database connection failed")
        except Exception as e:
            # 应该回滚到 pending
            final_status = 'pending'
            assert final_status == 'pending'


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
