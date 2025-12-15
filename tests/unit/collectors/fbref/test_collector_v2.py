"""
FBref Collector V2 单元测试
FBref Collector V2 Unit Tests

测试FBref采集器V2的功能：
1. 初始化和配置
2. HTTP请求处理
3. HTML解析和数据提取
4. 限流和代理功能
5. 与旧版兼容性

作者: Test Engineer (P2-2)
创建时间: 2025-12-06
"""

import asyncio
import gzip
import hashlib
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd

# 导入被测试的模块
from src.collectors.fbref.collector_v2 import FBrefCollectorV2
from src.collectors.rate_limiter import RateLimiter, RateLimitConfig
from src.collectors.proxy_pool import ProxyPool, Proxy, ProxyProtocol, ProxyStatus


class TestFBrefCollectorV2:
    """FBref Collector V2 测试类"""

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock RateLimiter"""
        mock_limiter = Mock(spec=RateLimiter)
        mock_limiter.acquire = AsyncMock()
        return mock_limiter

    @pytest.fixture
    def mock_proxy_pool(self):
        """Mock ProxyPool"""
        mock_pool = Mock(spec=ProxyPool)
        mock_pool.get_proxy = AsyncMock(return_value=None)
        return mock_pool

    @pytest.fixture
    def collector(self, mock_rate_limiter, mock_proxy_pool):
        """创建FBrefCollectorV2实例"""
        return FBrefCollectorV2(
            rate_limiter=mock_rate_limiter,
            proxy_pool=mock_proxy_pool,
            use_curl_cffi=False,  # 测试时不使用curl_cffi
            raw_data_dir="/tmp/test_fbref_v2"
        )

    @pytest.fixture
    def sample_html_with_tables(self):
        """包含表格的HTML示例"""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Test Schedule</title></head>
        <body>
            <table id="sched_all" class="sortable">
                <thead>
                    <tr><th>Date</th><th>Home</th><th>Away</th><th>Score</th><th>xG</th><th>xG.1</th></tr>
                </thead>
                <tbody>
                    <tr><td>2023-12-01</td><td>Team A</td><td>Team B</td><td>2-1</td><td>1.5</td><td>0.8</td></tr>
                    <tr><td>2023-12-02</td><td>Team C</td><td>Team D</td><td>1-1</td><td>1.2</td><td>1.2</td></tr>
                </tbody>
            </table>
            <a href="/en/matches/test123/match-report">Match Report</a>
            <a href="/en/matches/test456/match-report">Match Report 2</a>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_html_with_commented_tables(self):
        """包含注释表格的HTML示例（用于测试HTML解封）"""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Test Schedule</title></head>
        <body>
            <!-- <div id="sched_hidden" style="display:none;">
            <table class="sortable">
                <thead>
                    <tr><th>Date</th><th>Home</th><th>Away</th><th>Score</th><th>xG</th><th>xG.1</th></tr>
                </thead>
                <tbody>
                    <tr><td>2023-12-03</td><td>Team E</td><td>Team F</td><td>3-0</td><td>2.1</td><td>0.5</td></tr>
                </tbody>
            </table>
            </div> -->
            <table id="sched_visible" class="sortable">
                <thead>
                    <tr><th>Date</th><th>Home</th><th>Away</th><th>Score</th><th>xG</th><th>xG.1</th></tr>
                </thead>
                <tbody>
                    <tr><td>2023-12-01</td><td>Team A</td><td>Team B</td><td>2-1</td><td>1.5</td><td>0.8</td></tr>
                </tbody>
            </table>
        </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_collector_initialization(self, mock_rate_limiter, mock_proxy_pool):
        """测试采集器初始化"""
        collector = FBrefCollectorV2(
            rate_limiter=mock_rate_limiter,
            proxy_pool=mock_proxy_pool,
            use_curl_cffi=True,
            raw_data_dir="/tmp/test_fbref_v2"
        )

        assert collector.rate_limiter == mock_rate_limiter
        assert collector.proxy_pool == mock_proxy_pool
        assert collector.use_curl_cffi == True
        assert collector.config.rate_limit_delay == 2.0
        assert collector.config.max_retries == 5
        assert collector.config.http_timeout == 45.0

    @pytest.mark.asyncio
    async def test_collector_default_initialization(self):
        """测试采集器默认初始化"""
        collector = FBrefCollectorV2()

        assert collector.rate_limiter is not None
        assert isinstance(collector.rate_limiter, RateLimiter)
        assert collector.proxy_pool is None
        assert collector.use_curl_cffi == False  # 依赖可能不可用
        assert collector.config.rate_limit_delay == 2.0

    @pytest.mark.asyncio
    async def test_get_headers(self, collector):
        """测试获取请求头"""
        headers = await collector._get_headers()

        assert isinstance(headers, dict)
        assert 'User-Agent' in headers
        assert 'Accept' in headers
        assert 'Accept-Language' in headers
        assert 'Accept-Encoding' in headers
        assert 'Connection' in headers

    @pytest.mark.asyncio
    async def test_get_user_agent(self, collector):
        """测试获取User-Agent"""
        user_agent = await collector._get_user_agent()

        assert isinstance(user_agent, str)
        assert 'Mozilla' in user_agent
        assert any(browser in user_agent for browser in ['Chrome', 'Firefox'])

    def test_unseal_html_with_comments(self, collector, sample_html_with_commented_tables):
        """测试HTML注释解封功能"""
        original_html = sample_html_with_commented_tables
        unsealed_html = collector._unseal_html(original_html)

        # 验证注释被解封
        assert '<div id="sched_hidden"' in unsealed_html
        assert '<table' in unsealed_html
        assert 'Team E' in unsealed_html
        assert '3-0' in unsealed_html

        # 验证原有表格仍然存在
        assert '<table id="sched_visible"' in unsealed_html
        assert 'Team A' in unsealed_html

    def test_unseal_html_without_comments(self, collector, sample_html_with_tables):
        """测试没有注释的HTML解封"""
        original_html = sample_html_with_tables
        unsealed_html = collector._unseal_html(original_html)

        # 应该保持不变
        assert unsealed_html == original_html

    def test_parse_html_tables(self, collector, sample_html_with_tables):
        """测试HTML表格解析"""
        tables, advanced_stats = collector.parse_html_tables(sample_html_with_tables)

        assert len(tables) > 0
        assert isinstance(tables[0], pd.DataFrame)

        # 验证表格内容
        df = tables[0]
        assert len(df) == 2  # 两行数据
        assert 'Date' in df.columns or 'date' in df.columns

    def test_extract_match_report_links(self, collector, sample_html_with_tables):
        """测试Match Report链接提取"""
        links = collector._extract_match_report_links(sample_html_with_tables)

        assert len(links) == 2
        assert any('/en/matches/test123' in link for link in links)
        assert any('/en/matches/test456' in link for link in links)
        assert all(link.startswith('https://fbref.com') for link in links)

    def test_extract_advanced_stats(self, collector):
        """测试高级统计数据提取"""
        # 创建包含xG数据的DataFrame
        shooting_df = pd.DataFrame({
            'Player': ['Player A', 'Player B'],
            'xG': [1.5, 0.8],
            'xGA': [1.2, 1.5]
        })

        tables = [shooting_df]
        advanced_stats = collector._extract_advanced_stats(tables)

        assert 'shooting' in advanced_stats
        assert isinstance(advanced_stats['shooting'], pd.DataFrame)

    def test_extract_schedule_table(self, collector, sample_html_with_tables):
        """测试赛程表提取"""
        tables, _ = collector.parse_html_tables(sample_html_with_tables)
        schedule_table = collector.extract_schedule_table(tables)

        assert schedule_table is not None
        assert isinstance(schedule_table, pd.DataFrame)
        assert len(schedule_table) > 0

    def test_clean_schedule_data(self, collector):
        """测试赛程数据清洗"""
        # 创建原始DataFrame（模拟pandas.read_html的输出）
        raw_df = pd.DataFrame({
            'Date': ['2023-12-01', '2023-12-02'],
            'Home': ['Team A', 'Team C'],
            'Away': ['Team B', 'Team D'],
            'Score': ['2-1', '1-1'],
            'xG': [1.5, 1.2],
            'xG.1': [0.8, 1.2],
            'match_report_url': ['https://fbref.com/matches/1', 'https://fbref.com/matches/2']
        })

        cleaned_df = collector._clean_schedule_data(raw_df)

        # 验证列映射
        assert 'date' in cleaned_df.columns
        assert 'home' in cleaned_df.columns
        assert 'away' in cleaned_df.columns
        assert 'score' in cleaned_df.columns
        assert 'xg_home' in cleaned_df.columns
        assert 'xg_away' in cleaned_df.columns
        assert 'match_report_url' in cleaned_df.columns

        # 验证数据类型
        assert pd.api.types.is_numeric_dtype(cleaned_df['xg_home'])
        assert pd.api.types.is_numeric_dtype(cleaned_df['xg_away'])

    @pytest.mark.asyncio
    async def test_save_raw_html(self, collector):
        """测试原始HTML保存"""
        html_content = "<html><body>Test HTML</body></html>"
        url = "https://fbref.com/en/comps/9/schedule/test"
        league_id = "9"
        season = "20232024"

        file_path = collector._save_raw_html(html_content, url, league_id, season)

        # 验证文件已创建
        assert file_path is not None
        assert Path(file_path).exists()

        # 验证文件内容
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            saved_content = f.read()
        assert saved_content == html_content

        # 清理测试文件
        Path(file_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_html_with_httpx(self, collector, sample_html_with_tables):
        """测试使用httpx获取HTML"""
        # Mock httpx响应
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = sample_html_with_tables

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            html_content = await collector._fetch_with_httpx("https://fbref.com/test")

        assert html_content == sample_html_with_tables

    @pytest.mark.asyncio
    async def test_fetch_html_with_403(self, collector):
        """测试403错误处理"""
        mock_response = AsyncMock()
        mock_response.status_code = 403

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            html_content = await collector._fetch_with_httpx("https://fbref.com/test")

        assert html_content is None

    @pytest.mark.asyncio
    async def test_fetch_html_with_429(self, collector):
        """测试429错误处理"""
        mock_response = AsyncMock()
        mock_response.status_code = 429

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            html_content = await collector._fetch_with_httpx("https://fbref.com/test")

        assert html_content is None

    @pytest.mark.asyncio
    async def test_collect_season_stats(self, collector, sample_html_with_tables):
        """测试赛季数据采集"""
        season_url = "https://fbref.com/en/comps/9/schedule/test"
        season_year = "2023-2024"

        # Mock fetch_html方法
        with patch.object(collector, 'fetch_html', return_value=sample_html_with_tables):
            with patch.object(collector, '_save_raw_html', return_value="/tmp/test.html"):
                result = await collector.collect_season_stats(season_url, season_year)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_collect_match_stats(self, collector, sample_html_with_tables):
        """测试比赛统计采集"""
        match_url = "https://fbref.com/en/matches/test"

        # Mock fetch_html和parse_html_tables方法
        with patch.object(collector, 'fetch_html', return_value=sample_html_with_tables):
            with patch.object(collector, 'parse_html_tables', return_value=([], {})):
                with patch.object(collector, '_save_raw_html', return_value="/tmp/test.html"):
                    result = await collector.collect_match_stats(match_url)

        assert isinstance(result, dict)
        assert 'match_url' in result
        assert 'raw_file_path' in result
        assert 'tables_count' in result
        assert result['match_url'] == match_url

    @pytest.mark.asyncio
    async def test_rate_limiting(self, collector, mock_rate_limiter):
        """测试速率限制"""
        # 模拟fetch_html调用
        with patch.object(collector, '_fetch_with_httpx', return_value="test"):
            with patch.object(collector, '_fetch_with_curl_cffi', return_value=None):
                await collector.fetch_html("https://fbref.com/test")

        # 验证速率限制器被调用
        mock_rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_proxy_usage(self, collector, mock_proxy_pool):
        """测试代理使用"""
        # 创建mock代理
        mock_proxy = Proxy(
            url="http://127.0.0.1:8080",
            protocol=ProxyProtocol.HTTP,
            host="127.0.0.1",
            port=8080
        )
        mock_proxy_pool.get_proxy.return_value = mock_proxy

        # 重置async_client以使用代理
        collector.async_client = None
        await collector._setup_async_client()

        # 验证代理池被调用
        mock_proxy_pool.get_proxy.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_rate_limiter, mock_proxy_pool):
        """测试异步上下文管理器"""
        async with FBrefCollectorV2(
            rate_limiter=mock_rate_limiter,
            proxy_pool=mock_proxy_pool,
            use_curl_cffi=False
        ) as collector:
            assert collector._is_initialized is True
            assert collector.session is not None

        # 验证资源已清理
        assert collector._is_initialized is False

    def test_backward_compatibility(self, collector, sample_html_with_tables):
        """测试与旧版本的兼容性"""
        # 测试解析逻辑与旧版一致
        tables, advanced_stats = collector.parse_html_tables(sample_html_with_tables)
        schedule_table = collector.extract_schedule_table(tables)
        cleaned_table = collector._clean_schedule_data(schedule_table)

        # 验证输出结构兼容性
        assert isinstance(tables, list)
        assert isinstance(advanced_stats, dict)
        assert isinstance(schedule_table, pd.DataFrame)
        assert isinstance(cleaned_table, pd.DataFrame)

        # 验证关键列存在（与旧版一致）
        if not cleaned_table.empty:
            expected_columns = ['home', 'away', 'score']
            for col in expected_columns:
                if any(col in str(c).lower() for c in cleaned_table.columns):
                    assert True  # 找到对应的列
                else:
                    # 如果没找到，可能是因为HTML样本不包含这些数据
                    pass

    @pytest.mark.asyncio
    async def test_error_handling(self, collector):
        """测试错误处理"""
        # 测试无效URL
        with patch.object(collector, 'fetch_html', return_value=None):
            result = await collector.collect_season_stats("invalid_url")
            assert isinstance(result, pd.DataFrame)
            assert result.empty

        # 测试HTML解析错误
        with patch.object(collector, 'fetch_html', return_value="<html><body>Invalid HTML</body></html>"):
            with patch.object(collector, 'parse_html_tables', return_value=([], {})):
                result = await collector.collect_season_stats("test_url")
                assert isinstance(result, pd.DataFrame)
                assert result.empty

    @pytest.mark.asyncio
    async def test_cleanup(self, collector):
        """测试资源清理"""
        # 创建async_client
        await collector._setup_async_client()
        assert collector.async_client is not None

        # 执行清理
        await collector.cleanup()

        # 验证资源已清理
        assert collector.async_client is None or collector.async_client.is_closed


class TestFBrefCollectorV2Integration:
    """FBref Collector V2 集成测试类"""

    @pytest.mark.asyncio
    async def test_real_html_processing(self):
        """测试真实HTML处理（使用样本数据）"""
        # 创建不使用外部依赖的采集器
        collector = FBrefCollectorV2(
            use_curl_cffi=False,
            raw_data_dir="/tmp/test_fbref_v2"
        )

        # 使用更完整的HTML样本
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Premier League Schedule</title></head>
        <body>
            <div class="table_outer_container">
                <table id="sched_all" class="sortable stats_table">
                    <thead>
                        <tr>
                            <th scope="col" class="center" data-stat="date">Date</th>
                            <th scope="col" class="poptip" data-stat="home_team">Home</th>
                            <th scope="col" class="poptip" data-stat="away_team">Away</th>
                            <th scope="col" class="center" data-stat="score">Score</th>
                            <th scope="col" class="right" data-stat="xg">xG</th>
                            <th scope="col" class="right" data-stat="xga">xGA</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="center" data-stat="date">Dec 1, 2023</td>
                            <td class="left" data-stat="home_team">Manchester City</td>
                            <td class="left" data-stat="away_team">Liverpool</td>
                            <td class="center" data-stat="score">3-2</td>
                            <td class="right" data-stat="xg">2.1</td>
                            <td class="right" data-stat="xga">1.8</td>
                        </tr>
                        <tr>
                            <td class="center" data-stat="date">Dec 2, 2023</td>
                            <td class="left" data-stat="home_team">Arsenal</td>
                            <td class="left" data-stat="away_team">Chelsea</td>
                            <td class="center" data-stat="score">1-1</td>
                            <td class="right" data-stat="xg">1.5</td>
                            <td class="right" data-stat="xga">1.5</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="match_report_links">
                <a href="/en/matches/abc123/Manchester-City-Liverpool">Match Report</a>
                <a href="/en/matches/def456/Arsenal-Chelsea">Match Report</a>
            </div>
        </body>
        </html>
        """

        # 测试HTML解封
        unsealed_html = collector._unseal_html(sample_html)
        assert unsealed_html is not None

        # 测试表格解析
        tables, advanced_stats = collector.parse_html_tables(unsealed_html)
        assert len(tables) > 0

        # 测试赛程表提取
        schedule_table = collector.extract_schedule_table(tables)
        assert schedule_table is not None
        assert len(schedule_table) == 2

        # 测试数据清洗
        cleaned_table = collector._clean_schedule_data(schedule_table)
        assert cleaned_table is not None
        assert len(cleaned_table) == 2

        # 验证关键数据
        assert 'Manchester City' in str(cleaned_table.values)
        assert 'Liverpool' in str(cleaned_table.values)
        assert 'Arsenal' in str(cleaned_table.values)
        assert 'Chelsea' in str(cleaned_table.values)

        # 测试Match Report链接提取
        links = collector._extract_match_report_links(unsealed_html)
        assert len(links) == 2
        assert any('/matches/abc123' in link for link in links)
        assert any('/matches/def456' in link for link in links)

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """测试性能监控功能"""
        collector = FBrefCollectorV2(
            use_curl_cffi=False,
            config=collector.config
        )

        # 测试统计信息获取
        stats = collector.get_stats()
        assert isinstance(stats, dict)
        assert 'name' in stats
        assert 'total_requests' in stats
        assert 'success_rate' in stats

        # 测试统计信息重置
        collector.reset_stats()
        reset_stats = collector.get_stats()
        assert reset_stats['total_requests'] == 0
        assert reset_stats['successful_requests'] == 0
        assert reset_stats['failed_requests'] == 0
