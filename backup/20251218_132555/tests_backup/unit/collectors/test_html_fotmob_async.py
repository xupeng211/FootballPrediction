#!/usr/bin/env python3
"""
HTMLFotMobCollector 异步版本单元测试
测试异步采集器的功能和性能

作者: Async架构负责人
创建时间: 2025-12-06
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.collectors.html_fotmob_collector import AsyncHTMLFotMobCollector


@pytest.mark.asyncio
class TestAsyncHTMLFotMobCollector:
    """异步HTMLFotMob采集器测试类"""

    @pytest.fixture
    async def collector(self):
        """创建采集器实例"""
        collector = AsyncHTMLFotMobCollector(
            max_retries=2, timeout=10, enable_stealth=False  # 测试时关闭隐身模式
        )
        return collector

    @pytest.fixture
    def mock_nextjs_data(self):
        """模拟Next.js数据"""
        return {
            "props": {
                "pageProps": {
                    "content": {
                        "matchFacts": {"id": "123456"},
                        "stats": {
                            "Periods": {
                                "All": {
                                    "stats": [
                                        {
                                            "title": "Expected Goals (xG)",
                                            "stats": [1.5, 0.8],
                                        }
                                    ]
                                }
                            }
                        },
                        "lineup": {"homeTeam": [], "awayTeam": []},
                        "shotmap": {"shots": []},
                        "playerStats": {"homeTeam": [], "awayTeam": []},
                    }
                }
            }
        }

    @pytest.fixture
    def mock_html_response(self, mock_nextjs_data):
        """模拟HTML响应"""
        nextjs_json = json.dumps(mock_nextjs_data)
        return f"""
        <html>
        <head>
            <title>Test Match</title>
            <script id="__NEXT_DATA__" type="application/json">
                {nextjs_json}
            </script>
        </head>
        <body>
            <div id="root"></div>
        </body>
        </html>
        """

    async def test_collector_initialization(self):
        """测试采集器初始化"""
        collector = AsyncHTMLFotMobCollector()

        assert collector.name == "AsyncHTMLFotMobCollector"
        assert collector.config.max_retries == 3
        assert collector.config.http_timeout == 30.0
        assert collector.enable_stealth is True
        assert collector.fotmob_stats["matches_collected"] == 0

    async def test_get_headers(self, collector):
        """测试获取请求头"""
        headers = await collector._get_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Encoding" in headers
        assert "Connection" in headers

    async def test_get_user_agent(self, collector):
        """测试获取User-Agent"""
        user_agent = await collector._get_user_agent()

        assert isinstance(user_agent, str)
        assert "Mozilla" in user_agent or "Chrome" in user_agent

    async def test_extract_nextjs_data(self, collector):
        """测试Next.js数据提取"""
        # 准备测试数据
        test_data = {"props": {"pageProps": {"content": {"test": "data"}}}}
        html = f'<script id="__NEXT_DATA__">{json.dumps(test_data)}</script>'

        # 执行提取
        result = await collector._extract_nextjs_data(html, "123456")

        # 验证结果
        assert result is not None
        assert result["props"]["pageProps"]["content"]["test"] == "data"

    async def test_extract_nextjs_data_with_window_format(self, collector):
        """测试window.__NEXT_DATA__格式提取"""
        test_data = {"props": {"pageProps": {"content": {"test": "data"}}}}
        html = f"<script>window.__NEXT_DATA__ = {json.dumps(test_data)};</script>"

        result = await collector._extract_nextjs_data(html, "123456")

        assert result is not None
        assert result["props"]["pageProps"]["content"]["test"] == "data"

    async def test_extract_nextjs_data_not_found(self, collector):
        """测试Next.js数据未找到"""
        html = "<html><body>No Next.js data</body></html>"

        result = await collector._extract_nextjs_data(html, "123456")

        assert result is None

    async def test_extract_content_data(self, collector, mock_nextjs_data):
        """测试content数据提取"""
        result = await collector._extract_content_data(mock_nextjs_data, "123456")

        assert result is not None
        assert "matchFacts" in result
        assert "stats" in result
        assert "lineup" in result
        assert result["matchFacts"]["id"] == "123456"

    async def test_extract_content_data_404_page(self, collector):
        """测试404页面content提取"""
        nextjs_data = {"props": {"pageProps": {}, "url": "/404"}}

        result = await collector._extract_content_data(nextjs_data, "123456")

        assert result is None

    async def test_collect_match_data_success(self, collector, mock_html_response):
        """测试成功采集比赛数据"""
        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            # 模拟HTTP响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html_response
            mock_fetch.return_value = mock_response

            # 执行采集
            result = await collector.collect_match_data("123456")

            # 验证结果
            assert result is not None
            assert result["match"]["id"] == "123456"
            assert "content" in result
            assert "matchFacts" in result["content"]

    async def test_collect_match_data_404_with_nextjs(
        self, collector, mock_html_response
    ):
        """测试404页面包含Next.js数据"""
        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            # 模拟404响应但包含数据
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = mock_html_response
            mock_fetch.return_value = mock_response

            # 执行采集
            result = await collector.collect_match_data("123456")

            # 验证结果 - 404但包含数据时应仍然提取
            assert result is not None
            assert result["match"]["id"] == "123456"

    async def test_collect_match_data_404_no_data(self, collector):
        """测试404页面无数据"""
        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            # 模拟404响应无数据
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "<html><body>404 Not Found</body></html>"
            mock_fetch.return_value = mock_response

            # 执行采集
            result = await collector.collect_match_data("123456")

            # 验证结果
            assert result is None

    async def test_collect_match_data_429_retry(self, collector, mock_html_response):
        """测试429状态码重试"""
        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            # 先返回429，然后返回200
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.text = mock_html_response

            # 设置调用序列
            mock_fetch.side_effect = [mock_response_429, mock_response_200]

            # 模拟sleep避免实际等待
            with patch("asyncio.sleep", return_value=None):
                # 执行采集
                result = await collector.collect_match_data("123456")

                # 验证结果
                assert result is not None
                assert result["match"]["id"] == "123456"

    async def test_collect_match_data_403_retry(self, collector, mock_html_response):
        """测试403状态码重试"""
        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            # 先返回403，然后返回200
            mock_response_403 = MagicMock()
            mock_response_403.status_code = 403
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.text = mock_html_response

            mock_fetch.side_effect = [mock_response_403, mock_response_200]

            # 模拟sleep和refresh_disguise
            with patch("asyncio.sleep", return_value=None):
                with patch.object(collector, "_refresh_disguise", return_value=None):
                    # 执行采集
                    result = await collector.collect_match_data("123456")

                    # 验证结果
                    assert result is not None
                    assert result["match"]["id"] == "123456"

    async def test_collect_match_data_network_error(self, collector):
        """测试网络错误处理"""
        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            # 模拟网络异常
            mock_fetch.side_effect = Exception("Network error")

            # 执行采集
            result = await collector.collect_match_data("123456")

            # 验证结果
            assert result is None

    async def test_get_stats(self, collector):
        """测试获取统计信息"""
        # 设置一些统计数据
        collector.fotmob_stats["matches_collected"] = 5
        collector.fotmob_stats["ua_switches"] = 2
        collector.fotmob_stats["retry_count"] = 1

        # 获取统计信息
        stats = await collector.get_stats()

        # 验证统计信息
        assert stats["matches_collected"] == 5
        assert stats["ua_switches"] == 2
        assert stats["retry_count"] == 1
        assert stats["stealth_mode"] is False  # 测试配置
        assert "collection_rate" in stats
        assert stats["collection_rate"] >= 0

    async def test_refresh_disguise(self, collector):
        """测试User-Agent刷新"""
        # 启用隐身模式
        collector.enable_stealth = True
        collector.last_rotation = 0  # 强制轮换

        with patch.object(collector, "_get_user_agent", return_value="test-ua"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.side_effect = [
                    0,
                    1000,
                ]  # 第一次调用返回0，第二次返回1000

                await collector._refresh_disguise()

                # 验证轮换次数增加
                assert collector.fotmob_stats["ua_switches"] >= 1

    async def test_refresh_disguise_disabled(self, collector):
        """测试隐身模式禁用时不刷新"""
        collector.enable_stealth = False
        initial_switches = collector.fotmob_stats["ua_switches"]

        await collector._refresh_disguise()

        # 验证轮换次数未增加
        assert collector.fotmob_stats["ua_switches"] == initial_switches

    async def test_xg_data_detection(self, collector):
        """测试xG数据检测"""
        # 创建包含xG数据的测试数据
        nextjs_data = {
            "props": {
                "pageProps": {
                    "content": {
                        "stats": {
                            "Periods": {
                                "All": {
                                    "stats": [
                                        {
                                            "title": "Expected Goals (xG)",
                                            "stats": [2.1, 0.9],
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }

        result = await collector._extract_content_data(nextjs_data, "123456")

        assert result is not None
        # 验证xG数据被正确识别（通过日志可以验证）

    async def test_context_manager(self, collector):
        """测试异步上下文管理器"""
        async with collector as c:
            assert c is collector
            assert c._is_initialized is True

        # 上下文退出后，session应该被清理
        assert collector.session is None or collector.session.is_closed


class TestAsyncHTMLFotMobCollectorIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_collector_with_real_mock_response(self):
        """测试使用真实模拟响应的采集器"""
        collector = AsyncHTMLFotMobCollector(enable_stealth=False)

        # 准备完整的真实响应数据
        real_nextjs_data = {
            "props": {
                "pageProps": {
                    "content": {
                        "general": {
                            "matchHead2Head": {
                                "homeTeam": {"name": "Team A", "id": 123},
                                "awayTeam": {"name": "Team B", "id": 456},
                            }
                        },
                        "matchFacts": {
                            "id": "123456",
                            "status": {
                                "finished": False,
                                "startTimeStr": "2024-01-01 15:00",
                            },
                        },
                        "stats": {
                            "Periods": {
                                "All": {
                                    "stats": [
                                        {
                                            "title": "Expected Goals (xG)",
                                            "stats": [1.8, 1.2],
                                        },
                                        {"title": "Ball Possession", "stats": [55, 45]},
                                    ]
                                }
                            }
                        },
                        "lineup": {
                            "home": [{"name": "Player A"}],
                            "away": [{"name": "Player B"}],
                        },
                    }
                }
            }
        }

        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(real_nextjs_data)}</script>'

        with patch.object(collector, "fetch_with_retry") as mock_fetch:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html
            mock_fetch.return_value = mock_response

            # 使用异步上下文管理器
            async with collector:
                result = await collector.collect_match_data("123456")

                # 验证结果
                assert result is not None
                assert result["match"]["id"] == "123456"
                assert "content" in result
                content = result["content"]
                assert "general" in content
                assert "matchFacts" in content
                assert "stats" in content
                assert "lineup" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
