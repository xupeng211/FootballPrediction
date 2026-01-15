#!/usr/bin/env python3
"""
V41.77 TDD 测试套件 - SemanticRefiner 单元测试
================================================

本测试套件确保 SemanticRefiner 符合以下要求：
1. 联赛无关（League-Agnostic）URL 解析
2. 各种符号和格式的 Slug 解析
3. 模糊匹配数据库中的比赛
4. 失败自动记录不中断程序

覆盖五大联赛的最难 Slug：
- 英超：Manchester United vs Newcastle United（复杂多词队名）
- 德甲：Borussia Dortmund vs Bayern München（德语特殊字符）
- 意甲：AS Roma vs Inter Milan（意大利缩写）
- 西甲：Rayo Vallecano vs Athletic Club（西班牙复杂队名）
- 法甲：Olympique Marseille vs Olympique Lyon（法语缩写）

Author: 首席系统架构师
Version: V41.77
Date: 2026-01-15
"""

import csv
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.semantic_refiner import (
    SemanticRefiner,
    SlugMatchResult,
    create_semantic_refiner,
)


class TestHashAndSlugExtraction:
    """测试 Hash 和 Slug 提取（联赛无关）"""

    @pytest.fixture
    def refiner(self):
        """创建测试用 Refiner 实例"""
        mock_conn = MagicMock()
        return SemanticRefiner(mock_conn)

    def test_extract_hash_premier_league(self, refiner):
        """测试英超 URL Hash 提取"""
        url = "/football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-AbCd1234/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == "AbCd1234"
        assert slug == "manchester-utd-vs-newcastle"

    def test_extract_hash_bundesliga(self, refiner):
        """测试德甲 URL Hash 提取（德语队名）"""
        url = "/football/germany/bundesliga/Borussia-Dortmund-vs-Bayern-Munchen-XYZ12345/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == "XYZ12345"
        assert slug == "Borussia-Dortmund-vs-Bayern-Munchen"

    def test_extract_hash_serie_a(self, refiner):
        """测试意甲 URL Hash 提取"""
        url = "/football/italy/serie-a-2023-24/Roma-vs-Inter-Milan-QwEr7890/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == "QwEr7890"
        assert slug == "Roma-vs-Inter-Milan"

    def test_extract_hash_la_liga(self, refiner):
        """测试西甲 URL Hash 提取（复杂队名）"""
        url = "/football/spain/la-liga/Rayo-Vallecano-vs-Athletic-Bilbao-Ab12Cd34/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == "Ab12Cd34"
        assert slug == "Rayo-Vallecano-vs-Athletic-Bilbao"

    def test_extract_hash_ligue_1(self, refiner):
        """测试法甲 URL Hash 提取"""
        url = "/football/france/ligue-1/Olympique-Marseille-vs-Olympique-Lyon-1234AbCd/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == "1234AbCd"
        assert slug == "Olympique-Marseille-vs-Olympique-Lyon"

    def test_extract_hash_without_vs(self, refiner):
        """测试没有 vs 分隔符的 URL"""
        url = "/football/england/premier-league/manchester-city-liverpool-ZzYy1234/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == "ZzYy1234"
        # Slug 应该包含所有内容（除了 hash）
        assert "manchester" in slug.lower()
        assert "liverpool" in slug.lower()

    def test_extract_hash_invalid_url(self, refiner):
        """测试无效 URL（没有 Hash）"""
        url = "/football/england/premier-league/manchester-vs-newcastle/"
        hash_value, slug = refiner.extract_hash_and_slug(url)

        assert hash_value == ""
        assert slug == "manchester-vs-newcastle"


class TestSlugParsing:
    """测试 Slug 解析（各种符号和格式）"""

    @pytest.fixture
    def refiner(self):
        """创建测试用 Refiner 实例"""
        mock_conn = MagicMock()
        return SemanticRefiner(mock_conn)

    def test_parse_slug_with_vs_separator(self, refiner):
        """测试带 vs 分隔符的 Slug"""
        slug = "manchester-utd-vs-newcastle-utd"
        home, away = refiner.parse_slug(slug)

        assert "manchester" in home.lower()
        assert "newcastle" in away.lower()

    def test_parse_slug_with_hyphen_separator(self, refiner):
        """测试带连字符分隔符的 Slug（无 vs）"""
        slug = "manchester-city-liverpool"
        home, away = refiner.parse_slug(slug)

        # 应该能够分割
        assert len(home) > 0
        assert len(away) > 0

    def test_parse_slug_german_teams(self, refiner):
        """测试德语队名解析"""
        slug = "Borussia-Dortmund-vs-Bayern-Munchen"
        home, away = refiner.parse_slug(slug)

        assert "Dortmund" in home or "dortmund" in home.lower()
        assert "Bayern" in away or "munich" in away.lower() or "munchen" in away.lower()

    def test_parse_slug_italian_abbreviations(self, refiner):
        """测试意大利缩写解析"""
        slug = "Roma-vs-Inter-Milan"
        home, away = refiner.parse_slug(slug)

        assert "roma" in home.lower()
        assert "inter" in away.lower() or "milan" in away.lower()

    def test_parse_slug_spanish_complex(self, refiner):
        """测试西班牙复杂队名解析"""
        slug = "Rayo-Vallecano-vs-Athletic-Bilbao"
        home, away = refiner.parse_slug(slug)

        assert "vallecano" in home.lower() or "rayo" in home.lower()
        assert "athletic" in away.lower() or "bilbao" in away.lower()

    def test_parse_slug_french_abbreviations(self, refiner):
        """测试法语缩写解析"""
        slug = "Olympique-Marseille-vs-Olympique-Lyon"
        home, away = refiner.parse_slug(slug)

        assert "marseille" in home.lower()
        assert "lyon" in away.lower()

    def test_parse_slug_with_underscore(self, refiner):
        """测试带下划线的 Slug"""
        slug = "manchester_united_vs_chelsea"
        home, away = refiner.parse_slug(slug)

        assert "manchester" in home.lower()
        assert "chelsea" in away.lower()

    def test_parse_slug_empty(self, refiner):
        """测试空 Slug"""
        home, away = refiner.parse_slug("")

        assert home == ""
        assert away == ""


class TestDatabaseMatching:
    """测试数据库匹配"""

    @pytest.fixture
    def mock_connection(self):
        """创建模拟数据库连接"""
        conn = MagicMock()

        # 模拟查询返回
        mock_cursor = MagicMock()
        conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        conn.cursor.return_value.__exit__ = Mock(return_value=None)

        # 模拟查询结果
        mock_cursor.fetchall.return_value = [
            {
                'match_id': '12345',
                'home_team': 'Manchester United',
                'away_team': 'Newcastle United',
                'league_name': 'Premier League',
                'season': '2023/2024',
            },
            {
                'match_id': '12346',
                'home_team': 'Manchester City',
                'away_team': 'Newcastle United',
                'league_name': 'Premier League',
                'season': '2023/2024',
            },
        ]

        return conn

    def test_match_against_database_success(self, mock_connection):
        """测试数据库匹配成功"""
        refiner = SemanticRefiner(mock_connection)

        matches = refiner.match_against_database(
            home_team="Manchester United",
            away_team="Newcastle United",
            league_name="Premier League",
            season="2023/2024",
        )

        assert len(matches) > 0
        assert matches[0]['match_id'] == '12345'
        assert matches[0]['confidence'] >= 85.0

    def test_match_against_database_no_matches(self, mock_connection):
        """测试数据库无匹配"""
        # 修改模拟返回空结果
        mock_connection.cursor.return_value.__enter__.return_value.fetchall.return_value = []

        refiner = SemanticRefiner(mock_connection)

        matches = refiner.match_against_database(
            home_team="Unknown Team",
            away_team="Another Unknown",
            league_name="Premier League",
            season="2023/2024",
        )

        assert len(matches) == 0

    def test_match_against_database_error_handling(self, mock_connection):
        """测试数据库异常处理"""
        # 模拟数据库错误
        mock_connection.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("DB Error")

        refiner = SemanticRefiner(mock_connection)

        matches = refiner.match_against_database(
            home_team="Manchester United",
            away_team="Newcastle United",
            league_name="Premier League",
            season="2023/2024",
        )

        # 应该返回空列表而不是抛出异常
        assert len(matches) == 0


class TestFullRefinement:
    """测试完整的精炼流程"""

    @pytest.fixture
    def refiner_with_mock_db(self, tmp_path):
        """创建带模拟数据库的 Refiner"""
        mock_conn = MagicMock()

        # 模拟成功匹配
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)

        mock_cursor.fetchall.return_value = [
            {
                'match_id': '12345',
                'home_team': 'Manchester United',
                'away_team': 'Newcastle United',
                'league_name': 'Premier League',
                'season': '2023/2024',
            },
        ]

        # 使用临时目录作为日志目录
        refiner = SemanticRefiner(
            db_conn=mock_conn,
            failure_log_dir=str(tmp_path),
            confidence_threshold=85.0,
        )

        return refiner

    def test_refine_url_success(self, refiner_with_mock_db):
        """测试 URL 精炼成功"""
        url = "/football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-AbCd1234/"

        result = refiner_with_mock_db.refine_url(url, "Premier League", "2023/2024")

        assert result.is_match is True
        assert result.hash_value == "AbCd1234"
        assert result.match_id == '12345'
        assert result.confidence >= 85.0
        assert result.failure_reason == ""

    def test_refine_url_no_hash(self, refiner_with_mock_db):
        """测试 URL 没有 Hash"""
        url = "/football/england/premier-league/manchester-vs-newcastle/"

        result = refiner_with_mock_db.refine_url(url, "Premier League", "2023/2024")

        assert result.is_match is False
        assert result.hash_value == ""
        assert "No hash found" in result.failure_reason

    def test_refine_url_parse_failure(self, refiner_with_mock_db):
        """测试 Slug 解析失败"""
        url = "/football/england/premier-league-2023-2024/AbCd1234/"

        result = refiner_with_mock_db.refine_url(url, "Premier League", "2023/2024")

        assert result.is_match is False
        assert "Failed to parse" in result.failure_reason

    def test_refine_url_no_database_match(self, refiner_with_mock_db, tmp_path):
        """测试无数据库匹配"""
        # 修改模拟返回空结果
        refiner_with_mock_db.conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []

        url = "/football/england/premier-league-2023-2024/unknown-team-vs-another-AbCd1234/"

        result = refiner_with_mock_db.refine_url(url, "Premier League", "2023/2024")

        assert result.is_match is False
        assert "No database match" in result.failure_reason

        # 验证失败日志已创建
        log_file = tmp_path / f"alignment_failures_{datetime.now().strftime('%Y%m%d')}.csv"
        assert log_file.exists()

        # 验证日志内容
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['url'] == url
            assert rows[0]['hash_value'] == "AbCd1234"
            assert "No database match" in rows[0]['failure_reason']


class TestLeagueAgnosticCoverage:
    """测试联赛无关覆盖（五大联赛最难的 Slug）"""

    @pytest.fixture
    def mock_db_connection(self):
        """创建模拟数据库连接（返回多联赛数据）"""
        conn = MagicMock()

        mock_cursor = MagicMock()
        conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        conn.cursor.return_value.__exit__ = Mock(return_value=None)

        # 模拟返回不同联赛的比赛
        def mock_execute(query, params):
            league = params[0] if params else "Premier League"
            season = params[1] if len(params) > 1 else "2023/2024"

            # 根据联赛返回不同的比赛
            if "Bundesliga" in league or "bundesliga" in league.lower():
                mock_cursor.fetchall.return_value = [
                    {
                        'match_id': 'de12345',
                        'home_team': 'Borussia Dortmund',
                        'away_team': 'Bayern Munich',
                        'league_name': league,
                        'season': season,
                    },
                ]
            elif "Serie A" in league or "serie" in league.lower():
                mock_cursor.fetchall.return_value = [
                    {
                        'match_id': 'it12345',
                        'home_team': 'Roma',
                        'away_team': 'Inter Milan',
                        'league_name': league,
                        'season': season,
                    },
                ]
            elif "La Liga" in league or "laliga" in league.lower() or "liga" in league.lower():
                mock_cursor.fetchall.return_value = [
                    {
                        'match_id': 'es12345',
                        'home_team': 'Rayo Vallecano',
                        'away_team': 'Athletic Club',
                        'league_name': league,
                        'season': season,
                    },
                ]
            elif "Ligue 1" in league or "ligue" in league.lower():
                mock_cursor.fetchall.return_value = [
                    {
                        'match_id': 'fr12345',
                        'home_team': 'Olympique Marseille',
                        'away_team': 'Olympique Lyon',
                        'league_name': league,
                        'season': season,
                    },
                ]
            else:  # Premier League
                mock_cursor.fetchall.return_value = [
                    {
                        'match_id': 'en12345',
                        'home_team': 'Manchester United',
                        'away_team': 'Newcastle United',
                        'league_name': league,
                        'season': season,
                    },
                ]

        mock_cursor.execute.side_effect = mock_execute

        return conn

    def test_premier_league_complex_slug(self, mock_db_connection):
        """测试英超复杂 Slug：Manchester United vs Newcastle United"""
        refiner = SemanticRefiner(mock_db_connection)

        url = "/football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-united-AbCd1234/"
        result = refiner.refine_url(url, "Premier League", "2023/2024")

        assert result.is_match is True
        assert result.match_id == 'en12345'
        assert result.confidence >= 85.0

    def test_bundesliga_german_characters(self, mock_db_connection):
        """测试德甲德语特殊字符：Borussia Dortmund vs Bayern München"""
        refiner = SemanticRefiner(mock_db_connection)

        url = "/football/germany/bundesliga-2023-24/Borussia-Dortmund-vs-Bayern-Munchen-XYZ12345/"
        result = refiner.refine_url(url, "Bundesliga", "2023/2024")

        assert result.is_match is True
        assert result.match_id == 'de12345'
        # 德语特殊字符应该被正确处理
        assert "Dortmund" in result.home_team or "dortmund" in result.home_team.lower()

    def test_serie_a_italian_abbreviations(self, mock_db_connection):
        """测试意甲意大利缩写：AS Roma vs Inter Milan"""
        refiner = SemanticRefiner(mock_db_connection)

        url = "/football/italy/serie-a-2023-24/Roma-vs-Inter-Milan-QwEr7890/"
        result = refiner.refine_url(url, "Serie A", "2023/2024")

        assert result.is_match is True
        assert result.match_id == 'it12345'
        assert "roma" in result.home_team.lower()

    def test_la_liga_spanish_complex(self, mock_db_connection):
        """测试西甲复杂队名：Rayo Vallecano vs Athletic Club"""
        refiner = SemanticRefiner(mock_db_connection)

        url = "/football/spain/la-liga-2023-24/Rayo-Vallecano-vs-Athletic-Club-Ab12Cd34/"
        result = refiner.refine_url(url, "La Liga", "2023/2024")

        assert result.is_match is True
        assert result.match_id == 'es12345'
        assert "vallecano" in result.home_team.lower() or "rayo" in result.home_team.lower()

    def test_ligue_1_french_abbreviations(self, mock_db_connection):
        """测试法甲法语缩写：Olympique Marseille vs Olympique Lyon"""
        refiner = SemanticRefiner(mock_db_connection)

        url = "/football/france/ligue-1-2023-24/Olympique-Marseille-vs-Olympique-Lyon-1234AbCd/"
        result = refiner.refine_url(url, "Ligue 1", "2023/2024")

        assert result.is_match is True
        assert result.match_id == 'fr12345'
        assert "marseille" in result.home_team.lower()


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_semantic_refiner(self):
        """测试创建 SemanticRefiner 便捷函数"""
        mock_conn = MagicMock()

        refiner = create_semantic_refiner(
            db_conn=mock_conn,
            failure_log_dir="/tmp/test_logs",
            confidence_threshold=90.0,
        )

        assert refiner.conn == mock_conn
        assert refiner.confidence_threshold == 90.0
        assert "test_logs" in str(refiner.failure_log_path)


# ============================================================================
# V41.80: 属性测试（压力演习）
# ============================================================================


class TestPropertyBasedStress:
    """
    V41.80: 使用 Hypothesis 进行属性测试（压力演习）

    模拟海量非标准字符、长 Slug、空字符，确保 SemanticRefiner 永远不抛出未捕获的错误。
    """

    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=0, max_size=200))
    @settings(max_examples=100, deadline=timedelta(milliseconds=5000))
    def test_extract_hash_never_crashes_on_any_text(self, text):
        """
        V41.80: 测试 extract_hash_and_slug 对任何文本都不崩溃

        使用 Hypothesis 生成各种奇怪的文本，确保函数永远不抛出未捕获的异常。
        """
        mock_conn = MagicMock()
        refiner = SemanticRefiner(mock_conn)

        try:
            hash_value, slug = refiner.extract_hash_and_slug(text)
            # 只要函数不崩溃，测试就通过
            # 返回值可以是任何内容
            assert isinstance(hash_value, str)
            assert isinstance(slug, str)
        except Exception as e:
            # 如果有异常，确保是已知的异常类型
            pytest.fail(f"extract_hash_and_slug crashed on: {text[:50]}... Error: {e}")

    @given(st.from_regex(r'[a-zA-Z0-9\-_/vs]+'))
    @settings(max_examples=100, deadline=timedelta(milliseconds=5000))
    def test_parse_slug_never_crashes_on_valid_patterns(self, slug_pattern):
        """
        V41.80: 测试 parse_slug 对有效模式不崩溃

        使用符合 URL 格式的文本进行测试。
        """
        mock_conn = MagicMock()
        refiner = SemanticRefiner(mock_conn)

        try:
            home, away = refiner.parse_slug(slug_pattern)
            # 只要函数不崩溃，测试就通过
            assert isinstance(home, str)
            assert isinstance(away, str)
        except Exception as e:
            pytest.fail(f"parse_slug crashed on: {slug_pattern[:50]}... Error: {e}")

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5))
    @settings(max_examples=50, deadline=timedelta(milliseconds=5000))
    def test_parse_slug_handles_multiple_team_names(self, team_names):
        """
        V41.80: 测试 parse_slug 处理多个队名的情况

        模拟各种奇怪的队名组合。
        """
        # 构造一个 slug
        slug = "-vs-".join(team_names)
        mock_conn = MagicMock()
        refiner = SemanticRefiner(mock_conn)

        try:
            home, away = refiner.parse_slug(slug)
            # 只要函数不崩溃，测试就通过
            assert isinstance(home, str)
            assert isinstance(away, str)
        except Exception as e:
            pytest.fail(f"parse_slug crashed on: {slug[:50]}... Error: {e}")

    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=50, deadline=timedelta(milliseconds=5000))
    def test_refine_url_never_crashes_on_any_url(self, url):
        """
        V41.80: 测试 refine_url 对任何 URL 都不崩溃

        使用 Hypothesis 生成各种奇怪的 URL。
        """
        mock_conn = MagicMock()
        refiner = SemanticRefiner(mock_conn)

        try:
            result = refiner.refine_url(url, "Test League", "2023/2024")
            # 只要函数不崩溃，测试就通过
            assert result is not None
            assert isinstance(result.is_match, bool)
        except Exception as e:
            pytest.fail(f"refine_url crashed on: {url[:50]}... Error: {e}")

    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=100))
    @settings(max_examples=50, deadline=timedelta(milliseconds=5000))
    def test_clean_team_name_never_crashes(self, team_name):
        """
        V41.80: 测试 _clean_team_name 对任何队名都不崩溃

        模拟各种奇怪的队名。
        """
        mock_conn = MagicMock()
        refiner = SemanticRefiner(mock_conn)

        try:
            cleaned = refiner._clean_team_name(team_name)
            # 只要函数不崩溃，测试就通过
            assert isinstance(cleaned, str)
        except Exception as e:
            pytest.fail(f"_clean_team_name crashed on: {team_name[:50]}... Error: {e}")

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=20)
    def test_confidence_threshold_acceptable_range(self, threshold):
        """
        V41.80: 测试各种置信度阈值都能正常工作
        """
        mock_conn = MagicMock()
        try:
            test_refiner = SemanticRefiner(
                db_conn=mock_conn,
                confidence_threshold=float(threshold)
            )
            assert test_refiner.confidence_threshold == float(threshold)
        except Exception as e:
            pytest.fail(f"SemanticRefiner init crashed with threshold={threshold}: {e}")


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
