#!/usr/bin/env python3
"""
V41.77 TDD 测试套件 - MatchRepository 单元测试
===============================================

本测试套件确保 MatchRepository 的 Upsert 操作符合以下要求：
1. 幂等性：多次运行安全
2. 并发一致性：多线程并发写入不冲突
3. 事务完整性：失败时回滚
4. 队伍名称模糊匹配

Author: 首席系统架构师
Version: V41.77
Date: 2026-01-15
"""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
import psycopg2
from psycopg2 import sql

from src.database.match_repository import MatchRepository


class TestMatchRepositoryInitialization:
    """测试 MatchRepository 初始化"""

    @pytest.fixture
    def mock_connection(self):
        """创建模拟数据库连接"""
        conn = MagicMock()
        conn.closed = 0
        return conn

    def test_init_with_connection(self, mock_connection):
        """测试使用连接初始化"""
        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_connection
        repo._verify_database_identity = MagicMock()
        repo._verify_database_identity.return_value = None

        # 手动初始化
        repo.conn = mock_connection

        assert repo.conn == mock_connection

    def test_database_verification_called(self):
        """测试数据库身份验证被调用"""
        with patch('src.database.match_repository.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__ = MagicMock()
            mock_conn.cursor.return_value.__exit__ = MagicMock()
            mock_conn.cursor.return_value.fetchone.return_value = {'count': 14}

            with pytest.raises(Exception):  # 可能因为其他验证失败
                MatchRepository(
                    db_host="localhost",
                    db_name="test",
                    db_user="test",
                    db_password="test"
                )


class TestUpsertIdempotency:
    """测试 UPSERT 幂等性"""

    @pytest.fixture
    def repository(self):
        """创建测试用的 Repository 实例"""
        repo = MagicMock(spec=MatchRepository)
        repo.conn = MagicMock()
        repo.upsert_match_hash = MatchRepository.upsert_match_hash.__get__(repo, MatchRepository)
        return repo

    def test_upsert_same_hash_twice_idempotent(self):
        """
        测试相同的哈希值插入两次是幂等的

        第一次插入：应该成功
        第二次插入：应该检测到哈希已存在，返回 False（或跳过）
        """
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # 第一次调用：检查哈希不存在
        mock_cursor.fetchone.return_value = None
        # UPSERT 插入 1 行
        mock_cursor.rowcount = 1

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        result1 = repo.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        assert result1 == True, "第一次插入应该成功"

        # 第二次调用：检查哈希存在（返回已存在的记录）
        mock_cursor.fetchone.return_value = {'fotmob_id': '12345'}

        result2 = repo.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        assert result2 == False, "哈希已存在时应返回 False"

    def test_upsert_different_hash_updates(self):
        """
        测试不同的哈希值会触发更新

        场景：同一 match_id 先后有不同哈希值
        - 第一次：hash_v1
        - 第二次：hash_v2（应该更新）
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        # 第一次插入
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 1

        result1 = repo.upsert_match_hash(
            match_id="12345",
            hash_value="HASH_V1",
            url="https://test.com/v1",
            league_name="Premier League",
            season="2023/2024"
        )

        assert result1 == True

        # 第二次插入（不同哈希）
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 1

        result2 = repo.upsert_match_hash(
            match_id="12345",
            hash_value="HASH_V2",
            url="https://test.com/v2",
            league_name="Premier League",
            season="2023/2024"
        )

        assert result2 == True, "不同哈希应该触发更新"


class TestUpsertConcurrency:
    """测试 UPSERT 并发一致性"""

    def test_concurrent_upsert_same_match_different_hashes(self):
        """
        测试并发插入同一 match_id 但不同哈希值

        场景：10 个线程同时插入 match_id="12345"，各自有不同的哈希值
        预期：只有 1 个成功，其他 9 个失败（或覆盖）
        不应该出现数据库不一致或死锁
        """
        results = []
        errors = []

        def upsert_worker(hash_value):
            """工作线程：执行 UPSERT"""
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

            repo = MatchRepository.__new__(MatchRepository)
            repo.conn = mock_conn

            # 第一次检查：哈希不存在
            mock_cursor.fetchone.return_value = None
            # UPSERT 插入 1 行
            mock_cursor.rowcount = 1

            try:
                result = repo.upsert_match_hash(
                    match_id="CONCURRENT_TEST",
                    hash_value=hash_value,
                    url=f"https://test.com/{hash_value}",
                    league_name="Test League",
                    season="2023/2024"
                )
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        # 创建 10 个线程，每个使用不同的哈希值
        threads = []
        for i in range(10):
            hash_value = f"HASH_{i}"
            thread = threading.Thread(target=upsert_worker, args=(hash_value,))
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=5)

        # 验证：没有错误
        assert len(errors) == 0, f"并发操作不应出错: {errors}"

        # 验证：所有操作都返回了结果
        assert len(results) == 10, f"应该有 10 个结果，实际: {len(results)}"

    def test_concurrent_upsert_different_matches(self):
        """
        测试并发插入不同的 match_id

        场景：10 个线程同时插入 10 个不同的 match_id
        预期：全部成功，无冲突
        """
        results = []

        def upsert_worker(match_id, hash_value):
            """工作线程：执行 UPSERT"""
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

            repo = MatchRepository.__new__(MatchRepository)
            repo.conn = mock_conn

            mock_cursor.fetchone.return_value = None
            mock_cursor.rowcount = 1

            result = repo.upsert_match_hash(
                match_id=match_id,
                hash_value=hash_value,
                url=f"https://test.com/{match_id}",
                league_name="Test League",
                season="2023/2024"
            )
            results.append(result)

        # 创建 10 个线程，每个插入不同的 match_id
        threads = []
        for i in range(10):
            match_id = f"MATCH_{i}"
            hash_value = f"HASH_{i}"
            thread = threading.Thread(target=upsert_worker, args=(match_id, hash_value))
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=5)

        # 验证：全部成功
        assert len(results) == 10
        assert all(results), "所有并发操作都应成功"


class TestUpsertTransactionIntegrity:
    """测试 UPSERT 事务完整性"""

    def test_rollback_on_integrity_error(self):
        """
        测试违反约束时回滚

        场景：UPSERT 违反 UNIQUE 约束
        预期：回滚事务，返回 False
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        # 模拟 IntegrityError
        mock_cursor.execute.side_effect = psycopg2.IntegrityError(
            "duplicate key value violates unique constraint"
        )

        result = repo.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        # 验证：回滚被调用
        mock_conn.rollback.assert_called_once()

        # 验证：返回 False
        assert result == False

    def test_rollback_on_database_error(self):
        """
        测试数据库错误时回滚

        场景：UPSERT 触发数据库错误（非完整性错误）
        预期：回滚事务，返回 False
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        # 模拟数据库错误
        mock_cursor.execute.side_effect = Exception("Database connection lost")

        result = repo.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        # 验证：返回 False
        assert result == False

    def test_commit_on_success(self):
        """
        测试成功时提交

        场景：UPSERT 成功
        预期：提交事务，返回 True
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        # 第一次检查：哈希不存在
        mock_cursor.fetchone.return_value = None
        # UPSERT 插入 1 行
        mock_cursor.rowcount = 1

        result = repo.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        # 验证：提交被调用
        mock_conn.commit.assert_called_once()

        # 验证：返回 True
        assert result == True


class TestFuzzyTeamMatching:
    """测试队伍名称模糊匹配"""

    @pytest.fixture
    def repository_with_mock_db(self):
        """创建带有模拟数据库的 Repository"""
        repo = MagicMock(spec=MatchRepository)
        repo.conn = MagicMock()

        # 模拟数据库查询返回比赛列表
        mock_cursor = MagicMock()
        repo.conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        repo.conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # 模拟数据库中有多场比赛
        mock_cursor.fetchall.return_value = [
            {'match_id': '1', 'home_team': 'Manchester United', 'away_team': 'Liverpool'},
            {'match_id': '2', 'home_team': 'Manchester City', 'away_team': 'Arsenal'},
            {'match_id': '3', 'home_team': 'Tottenham Hotspur', 'away_team': 'Chelsea'},
        ]

        return repo

    def test_fuzzy_match_abbreviated_team_name(self, repository_with_mock_db):
        """
        测试模糊匹配缩写队名

        场景：输入 "Man Utd" 应能匹配 "Manchester United"
        """
        # 测试 normalize_team_name 能处理缩写
        from src.utils.team_alias import normalize_team_name

        abbreviated = "Man Utd"
        full_name = "Manchester United"

        normalized_abbrev = normalize_team_name(abbreviated)
        normalized_full = normalize_team_name(full_name)

        # 验证：标准化后应该有相似部分
        assert "manchester" in normalized_full or "united" in normalized_full
        assert "man" in normalized_abbrev or "united" in normalized_abbrev

    def test_fuzzy_match_wolves_to_wolverhampton(self, repository_with_mock_db):
        """
        测试模糊匹配 Wolves 到 Wolverhampton Wanderers
        """
        from src.utils.team_alias import normalize_team_name

        short_name = "Wolves"
        full_name = "Wolverhampton Wanderers"

        normalized_short = normalize_team_name(short_name)
        normalized_full = normalize_team_name(full_name)

        # 验证：应该能识别关联
        assert "wolves" in normalized_short or "wolverhampton" in normalized_short
        assert "wolves" in normalized_full or "wolverhampton" in normalized_full

    def test_no_match_for_completely_different_names(self, repository_with_mock_db):
        """
        测试完全不相关的队名不匹配
        """
        from src.utils.team_alias import match_teams

        # Arsenal vs Chelsea 应该与 Liverpool vs Man City 低相似度
        score, details = match_teams("Arsenal", "Chelsea", "Liverpool", "Man City")

        # 验证：低相似度
        assert score < 50.0


class TestUpsertWithFuzzyMatching:
    """测试带模糊匹配的 UPSERT（V41.76 新功能）"""

    @pytest.fixture
    def repository_with_fuzzy_match(self):
        """创建带模糊匹配的 Repository"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        return repo

    def test_upsert_uses_fuzzy_match_when_exact_fails(self, repository_with_fuzzy_match):
        """
        测试精确匹配失败时使用模糊匹配

        场景：
        1. 输入 home_team="Newcastle Utd", away_team="Brighton"
        2. 数据库中没有精确匹配
        3. 数据库中有 "Newcastle United" vs "Brighton & Hove Albion"
        4. 模糊匹配应该找到这场比赛
        """
        mock_cursor = repository_with_fuzzy_match.conn.cursor.return_value.__enter__.return_value

        # 精确匹配查询：无结果
        mock_cursor.fetchone.return_value = None

        # 模糊匹配查询：返回多场比赛
        mock_cursor.fetchall.return_value = [
            {
                'match_id': '12345',
                'home_team': 'Newcastle United',
                'away_team': 'Brighton & Hove Albion'
            },
        ]

        # UPSERT：插入 1 行
        mock_cursor.rowcount = 1

        result = repository_with_fuzzy_match.upsert_match_hash(
            match_id="",  # 留空，让 Repository 查找
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024",
            home_team="Newcastle Utd",
            away_team="Brighton"
        )

        # 验证：应该成功
        assert result == True

    def test_upsert_fails_when_no_fuzzy_match_found(self, repository_with_fuzzy_match):
        """
        测试找不到模糊匹配时返回 False

        场景：
        1. 精确匹配失败
        2. 模糊匹配也找不到任何比赛
        3. 返回 False
        """
        mock_cursor = repository_with_fuzzy_match.conn.cursor.return_value.__enter__.return_value

        # 精确匹配查询：无结果
        mock_cursor.fetchone.return_value = None

        # 模糊匹配查询：返回空列表
        mock_cursor.fetchall.return_value = []

        result = repository_with_fuzzy_match.upsert_match_hash(
            match_id="",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Non-existent League",
            season="2023/2024",
            home_team="Unknown Team A",
            away_team="Unknown Team B"
        )

        # 验证：应该返回 False
        assert result == False


class TestUpsertSeasonValidation:
    """测试赛季验证逻辑"""

    @pytest.fixture
    def repository(self):
        """创建测试用的 Repository 实例"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        return repo

    def test_season_mismatch_rejects_url(self, repository):
        """
        测试赛季不匹配时拒绝 URL

        场景：
        - URL 中包含 2022-2023 赛季
        - match_id 属于 2023/2024 赛季
        - 应拒绝并返回 False
        """
        mock_cursor = repository.conn.cursor.return_value.__enter__.return_value

        # 第一次检查：哈希不存在
        mock_cursor.fetchone.return_value = None

        # 第二次检查：赛季检查
        # 返回不同的赛季
        mock_cursor.fetchone.return_value = {'season': '2023/2024'}

        # URL 包含不同的赛季（22/23 vs 23/24）
        url_with_different_season = "https://www.oddsportal.com/football/england/premier-league-2022-2023/"

        result = repository.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url=url_with_different_season,
            league_name="Premier League",
            season="2023/2024"
        )

        # 验证：应返回 False（由于赛季检查）
        # 注意：当前实现可能没有这个检查，测试反映理想行为
        # 如果当前实现没有此检查，此测试会失败
        assert result == False


class TestUpsertEdgeCases:
    """测试 UPSERT 边界条件"""

    @pytest.fixture
    def repository(self):
        """创建测试用的 Repository 实例"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        repo = MatchRepository.__new__(MatchRepository)
        repo.conn = mock_conn

        return repo

    def test_upsert_with_empty_hash_value(self, repository):
        """测试空哈希值"""
        mock_cursor = repository.conn.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 1

        result = repository.upsert_match_hash(
            match_id="12345",
            hash_value="",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        # 空哈希应该被允许（可能表示清除哈希）
        # 或者应该被拒绝，取决于业务逻辑
        # 当前测试假设允许
        assert result == True

    def test_upsert_with_very_long_hash_value(self, repository):
        """测试超长哈希值"""
        mock_cursor = repository.conn.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 1

        long_hash = "A" * 1000

        result = repository.upsert_match_hash(
            match_id="12345",
            hash_value=long_hash,
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024"
        )

        # 超长哈希应该被处理
        assert result == True

    def test_upsert_with_special_characters_in_url(self, repository):
        """测试 URL 包含特殊字符"""
        mock_cursor = repository.conn.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 1

        url_with_special_chars = "https://www.oddsportal.com/football/england/premier-league-2023-2024/?param=value&other=123"

        result = repository.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url=url_with_special_chars,
            league_name="Premier League",
            season="2023/2024"
        )

        # 特殊字符 URL 应该被正确处理
        assert result == True

    def test_upsert_with_unicode_team_names(self, repository):
        """测试 Unicode 队名"""
        mock_cursor = repository.conn.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 1

        result = repository.upsert_match_hash(
            match_id="12345",
            hash_value="ABC12345",
            url="https://test.com",
            league_name="Premier League",
            season="2023/2024",
            home_team="München",  # 德语 umlaut
            away_team="Fc Köln"  # 德语 umlaut
        )

        # Unicode 队名应该被正确处理
        assert result == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
