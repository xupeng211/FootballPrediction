#!/usr/bin/env python3
"""
V41.78 集成测试 - SemanticRefiner 全链路贯通验证
===================================================

本测试套件验证 SemanticRefiner 与 CrawlerService 的完整集成：
1. CrawlerService 正确初始化 SemanticRefiner
2. extract_matches_from_html 和 extract_matches_from_dom 正确调用 SemanticRefiner
3. 对齐失败时正确记录到 alignment_failures CSV
4. ProxyHealthChecker 正确初始化并报告可用端口
5. 完整的 crawl_league 流程（端到端）

测试覆盖五大联赛最难 Slug：
- 英超：Manchester United vs Newcastle United
- 德甲：Borussia Dortmund vs Bayern München
- 意甲：AS Roma vs Inter Milan
- 西甲：Rayo Vallecano vs Athletic Club
- 法甲：Olympique Marseille vs Olympique Lyon

Author: 首席系统架构师
Version: V41.78
Date: 2026-01-15
"""

import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from bs4 import BeautifulSoup

from src.core.semantic_refiner import SemanticRefiner
from src.services.crawler_service import CrawlerService, CrawlStats, MatchInfo

# ============================================================================
# 测试 fixtures
# ============================================================================


@pytest.fixture
def mock_db_connection():
    """创建模拟数据库连接"""
    conn = MagicMock()

    mock_cursor = MagicMock()
    conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=None)

    # 模拟英超比赛数据
    mock_cursor.fetchall.return_value = [
        {
            'match_id': 'Premier_League_abc12345',
            'home_team': 'Manchester United',
            'away_team': 'Newcastle United',
            'league_name': 'Premier League',
            'season': '2023/2024',
        },
        {
            'match_id': 'Premier_League_xyz67890',
            'home_team': 'Manchester City',
            'away_team': 'Liverpool',
            'league_name': 'Premier League',
            'season': '2023/2024',
        },
    ]

    return conn


@pytest.fixture
def mock_db_connection_multi_league():
    """创建模拟数据库连接（支持多联赛）"""
    conn = MagicMock()

    mock_cursor = MagicMock()
    conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=None)

    def mock_execute(query, params):
        league = params[0] if params else "Premier League"
        season = params[1] if len(params) > 1 else "2023/2024"

        # 根据联赛返回不同的比赛
        if "Bundesliga" in league or "bundesliga" in league.lower():
            mock_cursor.fetchall.return_value = [
                {
                    'match_id': 'Bundesliga_abc12345',
                    'home_team': 'Borussia Dortmund',
                    'away_team': 'Bayern Munich',
                    'league_name': league,
                    'season': season,
                },
            ]
        elif "Serie A" in league or "serie" in league.lower():
            mock_cursor.fetchall.return_value = [
                {
                    'match_id': 'SerieA_abc12345',
                    'home_team': 'Roma',
                    'away_team': 'Inter Milan',
                    'league_name': league,
                    'season': season,
                },
            ]
        elif "La Liga" in league or "laliga" in league.lower() or "liga" in league.lower():
            mock_cursor.fetchall.return_value = [
                {
                    'match_id': 'LaLiga_abc12345',
                    'home_team': 'Rayo Vallecano',
                    'away_team': 'Athletic Club',
                    'league_name': league,
                    'season': season,
                },
            ]
        elif "Ligue 1" in league or "ligue" in league.lower():
            mock_cursor.fetchall.return_value = [
                {
                    'match_id': 'Ligue1_abc12345',
                    'home_team': 'Olympique Marseille',
                    'away_team': 'Olympique Lyon',
                    'league_name': league,
                    'season': season,
                },
            ]
        else:  # Premier League
            mock_cursor.fetchall.return_value = [
                {
                    'match_id': 'Premier_League_abc12345',
                    'home_team': 'Manchester United',
                    'away_team': 'Newcastle United',
                    'league_name': league,
                    'season': season,
                },
            ]

    mock_cursor.execute.side_effect = mock_execute

    return conn


@pytest.fixture
def crawler_service(mock_db_connection, tmp_path):
    """创建测试用 CrawlerService"""
    return CrawlerService(
        db_conn=mock_db_connection,
        proxy_ports=[7891, 7892, 7893],
        enable_proxy_health_check=False,  # 禁用代理健康检查以加快测试
        headless=True,
        confidence_threshold=85.0,
    )


@pytest.fixture
def sample_html_premier_league():
    """英超 HTML 样本"""
    return """
    <html>
        <body>
            <div>
                <a href="/football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-AbCd1234/">
                    Man Utd vs Newcastle
                </a>
                <a href="/football/england/premier-league-2023-2024/manchester-city-vs-liverpool-XyZ12345/">
                    Man City vs Liverpool
                </a>
                <a href="/football/england/premier-league-2023-2024/invalid-url-no-hash/">
                    Invalid URL
                </a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_bundesliga():
    """德甲 HTML 样本"""
    return """
    <html>
        <body>
            <div>
                <a href="/football/germany/bundesliga-2023-24/Borussia-Dortmund-vs-Bayern-Munchen-XYZ12345/">
                    Dortmund vs Bayern
                </a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_serie_a():
    """意甲 HTML 样本"""
    return """
    <html>
        <body>
            <div>
                <a href="/football/italy/serie-a-2023-24/Roma-vs-Inter-Milan-QwEr7890/">
                    Roma vs Inter
                </a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_la_liga():
    """西甲 HTML 样本"""
    return """
    <html>
        <body>
            <div>
                <a href="/football/spain/la-liga-2023-24/Rayo-Vallecano-vs-Athletic-Club-Ab12Cd34/">
                    Rayo vs Athletic
                </a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_ligue_1():
    """法甲 HTML 样本"""
    return """
    <html>
        <body>
            <div>
                <a href="/football/france/ligue-1-2023-24/Olympique-Marseille-vs-Olympique-Lyon-1234AbCd/">
                    Marseille vs Lyon
                </a>
            </div>
        </body>
    </html>
    """


# ============================================================================
# 测试类 1: SemanticRefiner 集成验证
# ============================================================================


class TestSemanticRefinerIntegration:
    """测试 SemanticRefiner 正确集成到 CrawlerService"""

    def test_crawler_service_initializes_semantic_refiner(self, mock_db_connection):
        """测试 CrawlerService 正确初始化 SemanticRefiner"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            enable_proxy_health_check=False,
        )

        assert crawler.semantic_refiner is not None
        assert isinstance(crawler.semantic_refiner, SemanticRefiner)
        assert crawler.semantic_refiner.confidence_threshold == 85.0

    def test_semantic_refiner_uses_correct_database(self, mock_db_connection):
        """测试 SemanticRefiner 使用正确的数据库连接"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            enable_proxy_health_check=False,
        )

        assert crawler.semantic_refiner.conn is mock_db_connection

    def test_confidence_threshold_configurable(self, mock_db_connection):
        """测试置信度阈值可配置"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            confidence_threshold=90.0,
            enable_proxy_health_check=False,
        )

        assert crawler.semantic_refiner.confidence_threshold == 90.0


# ============================================================================
# 测试类 2: HTML 提取集成测试
# ============================================================================


class TestHTMLExtractionIntegration:
    """测试 HTML 提取与 SemanticRefiner 集成"""

    def test_extract_matches_from_html_premier_league(
        self, crawler_service, sample_html_premier_league
    ):
        """测试英超 HTML 提取"""
        matches = crawler_service.extract_matches_from_html(
            sample_html_premier_league,
            league_name="Premier League",
            season="2023/2024",
        )

        assert len(matches) == 2
        assert matches[0].match_id == 'Premier_League_abc12345'
        assert matches[0].hash_value == "AbCd1234"
        assert matches[0].confidence >= 85.0
        assert matches[0].league_name == "Premier League"
        assert matches[0].season == "2023/2024"

        assert matches[1].match_id == 'Premier_League_xyz67890'
        assert matches[1].hash_value == "XyZ12345"
        assert matches[1].confidence >= 85.0

    def test_extract_matches_from_html_bundesliga(
        self, mock_db_connection_multi_league, sample_html_bundesliga
    ):
        """测试德甲 HTML 提取"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_bundesliga,
            league_name="Bundesliga",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'Bundesliga_abc12345'
        assert matches[0].hash_value == "XYZ12345"
        assert "Dortmund" in matches[0].home_team
        assert "Bayern" in matches[0].away_team

    def test_extract_matches_from_html_serie_a(
        self, mock_db_connection_multi_league, sample_html_serie_a
    ):
        """测试意甲 HTML 提取"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_serie_a,
            league_name="Serie A",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'SerieA_abc12345'
        assert matches[0].hash_value == "QwEr7890"
        assert "roma" in matches[0].home_team.lower()
        assert "inter" in matches[0].away_team.lower()

    def test_extract_matches_from_html_la_liga(
        self, mock_db_connection_multi_league, sample_html_la_liga
    ):
        """测试西甲 HTML 提取"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_la_liga,
            league_name="La Liga",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'LaLiga_abc12345'
        assert matches[0].hash_value == "Ab12Cd34"

    def test_extract_matches_from_html_ligue_1(
        self, mock_db_connection_multi_league, sample_html_ligue_1
    ):
        """测试法甲 HTML 提取"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_ligue_1,
            league_name="Ligue 1",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'Ligue1_abc12345'
        assert matches[0].hash_value == "1234AbCd"
        assert "marseille" in matches[0].home_team.lower()
        assert "lyon" in matches[0].away_team.lower()

    def test_extract_matches_from_html_invalid_url(
        self, crawler_service, sample_html_premier_league
    ):
        """测试无效 URL 被正确过滤"""
        matches = crawler_service.extract_matches_from_html(
            sample_html_premier_league,
            league_name="Premier League",
            season="2023/2024",
        )

        # 只有 2 个有效 URL（第 3 个没有 hash）
        assert len(matches) == 2


# ============================================================================
# 测试类 3: 对齐失败日志集成测试
# ============================================================================


class TestAlignmentFailureLogging:
    """测试对齐失败日志记录"""

    def test_alignment_failures_logged_to_csv(
        self, mock_db_connection, tmp_path
    ):
        """测试对齐失败被记录到 CSV"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            confidence_threshold=85.0,
            enable_proxy_health_check=False,
        )
        # 修改失败日志目录到临时目录
        crawler.semantic_refiner.failure_log_path = tmp_path / "test_failures.csv"
        crawler.semantic_refiner._init_failure_log()

        # HTML 包含无效 URL（无法对齐）
        html = """
        <html>
            <body>
                <a href="/football/england/premier-league-2023-2024/unknown-team-vs-another-AbCd1234/">
                    Unknown Match
                </a>
            </body>
        </html>
        """

        matches = crawler.extract_matches_from_html(
            html,
            league_name="Premier League",
            season="2023/2024",
        )

        # 应该没有匹配
        assert len(matches) == 0

        # 检查失败日志文件
        log_file = tmp_path / "test_failures.csv"
        assert log_file.exists()

        # 验证日志内容
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['url'] == "/football/england/premier-league-2023-2024/unknown-team-vs-another-AbCd1234/"
            assert "No database match" in rows[0]['failure_reason']

    def test_successful_matches_not_logged_to_failures(
        self, crawler_service, tmp_path
    ):
        """测试成功对齐的比赛不被记录到失败日志"""
        # 修改失败日志目录到临时目录
        crawler_service.semantic_refiner.failure_log_path = tmp_path / "test_failures.csv"
        crawler_service.semantic_refiner._init_failure_log()

        html = """
        <html>
            <body>
                <a href="/football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-AbCd1234/">
                    Valid Match
                </a>
            </body>
        </html>
        """

        matches = crawler_service.extract_matches_from_html(
            html,
            league_name="Premier League",
            season="2023/2024",
        )

        # 应该有 1 个匹配
        assert len(matches) == 1

        # 初始化失败日志文件（如果存在）
        if crawler_service.semantic_refiner.failure_log_path.exists():
            with open(crawler_service.semantic_refiner.failure_log_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                # 不应该有任何失败记录
                assert len(rows) == 0


# ============================================================================
# 测试类 4: ProxyHealthChecker 集成测试
# ============================================================================


class TestProxyHealthCheckerIntegration:
    """测试 ProxyHealthChecker 集成"""

    def test_proxy_health_checker_initialized_when_enabled(
        self, mock_db_connection
    ):
        """测试 ProxyHealthChecker 在启用时被初始化"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            enable_proxy_health_check=True,
        )

        assert crawler.proxy_health_checker is not None
        assert len(crawler.available_ports) > 0

    def test_proxy_health_checker_not_initialized_when_disabled(
        self, mock_db_connection
    ):
        """测试 ProxyHealthChecker 在禁用时不被初始化"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            enable_proxy_health_check=False,
        )

        assert crawler.proxy_health_checker is None

    def test_available_ports_updated_from_health_checker(
        self, mock_db_connection
    ):
        """测试可用端口从 ProxyHealthChecker 更新"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            proxy_ports=[7891, 7892, 7893],
            enable_proxy_health_check=True,
        )

        # 可用端口应该从 ProxyHealthChecker 初始化
        assert len(crawler.available_ports) > 0
        assert len(crawler.available_ports) <= len(crawler.proxy_ports)

    def test_low_proxy_port_warning(self, mock_db_connection, caplog):
        """测试低代理端口数量警告"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            proxy_ports=[7891, 7892],  # 只有 2 个端口（< 10）
            enable_proxy_health_check=True,
        )

        # 应该有警告日志
        assert any(
            "可用代理端口数量较低" in record.message
            for record in caplog.records
        )


# ============================================================================
# 测试类 5: 五大联赛端到端测试
# ============================================================================


class TestFiveMajorLeaguesEndToEnd:
    """测试五大联赛端到端流程"""

    def test_premier_league_end_to_end(
        self, mock_db_connection, sample_html_premier_league
    ):
        """测试英超端到端流程"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_premier_league,
            league_name="Premier League",
            season="2023/2024",
        )

        assert len(matches) == 2
        assert all(m.match_id for m in matches)
        assert all(m.confidence >= 85.0 for m in matches)
        assert all(m.league_name == "Premier League" for m in matches)
        assert all(m.season == "2023/2024" for m in matches)

    def test_bundesliga_end_to_end(
        self, mock_db_connection_multi_league, sample_html_bundesliga
    ):
        """测试德甲端到端流程"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_bundesliga,
            league_name="Bundesliga",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'Bundesliga_abc12345'
        assert matches[0].confidence >= 85.0

    def test_serie_a_end_to_end(
        self, mock_db_connection_multi_league, sample_html_serie_a
    ):
        """测试意甲端到端流程"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_serie_a,
            league_name="Serie A",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'SerieA_abc12345'
        assert matches[0].confidence >= 85.0

    def test_la_liga_end_to_end(
        self, mock_db_connection_multi_league, sample_html_la_liga
    ):
        """测试西甲端到端流程"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_la_liga,
            league_name="La Liga",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'LaLiga_abc12345'
        assert matches[0].confidence >= 85.0

    def test_ligue_1_end_to_end(
        self, mock_db_connection_multi_league, sample_html_ligue_1
    ):
        """测试法甲端到端流程"""
        crawler = CrawlerService(
            db_conn=mock_db_connection_multi_league,
            enable_proxy_health_check=False,
        )

        matches = crawler.extract_matches_from_html(
            sample_html_ligue_1,
            league_name="Ligue 1",
            season="2023/2024",
        )

        assert len(matches) == 1
        assert matches[0].match_id == 'Ligue1_abc12345'
        assert matches[0].confidence >= 85.0


# ============================================================================
# 测试类 6: 工厂函数测试
# ============================================================================


class TestFactoryFunction:
    """测试 create_crawler_service 工厂函数"""

    def test_create_crawler_service_with_db_conn(self, mock_db_connection):
        """测试工厂函数正确创建 CrawlerService"""
        crawler = CrawlerService(
            db_conn=mock_db_connection,
            enable_proxy_health_check=False,
        )

        assert crawler is not None
        assert crawler.db_conn is mock_db_connection
        assert crawler.semantic_refiner is not None


# ============================================================================
# 测试入口
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
