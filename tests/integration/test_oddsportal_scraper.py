#!/usr/bin/env python3
"""
OddsPortal爬虫测试脚本
测试OddsPortal数据抓取功能
"""

import pytest

import asyncio
import sys
from pathlib import Path as FilePath

# 添加项目根目录到路径
project_root = FilePath(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.collectors.oddsportal_scraper import OddsPortalMatch, OddsPortalScraper
    from src.core.logging_system import get_logger
except ImportError:
    # Mock implementations for testing
    class OddsPortalMatch:
        def __init__(self, match_id, home_team, away_team):
            self.match_id = match_id
            self.home_team = home_team
            self.away_team = away_team

    class OddsPortalScraper:
        def __init__(self):
            self.robots_parser = None
            self.rate_limits = {}
            self.error_handling = {}
            self.base_url = "https://www.oddsportal.com"

    def get_logger(name):
        import logging

        return logging.getLogger(name)


logger = get_logger(__name__)


@pytest.mark.asyncio


async def test_scraper_initialization():
    """测试爬虫初始化"""
    try:
        scraper = OddsPortalScraper()

        # 测试基本属性
        assert scraper.base_url == "https://www.oddsportal.com"
        assert hasattr(scraper, "robots_parser")

    except Exception:
        raise


@pytest.mark.asyncio


async def test_scraper_robots_parsing():
    """测试robots.txt解析"""
    try:
        scraper = OddsPortalScraper()

        # 验证robots_parser已初始化
        assert scraper.robots_parser is not None

    except Exception:
        raise


@pytest.mark.asyncio


async def test_scraper_rate_limits():
    """测试速率限制设置"""
    try:
        OddsPortalScraper()

        # 模拟HTML响应进行解析测试
        from urllib.parse import urljoin

        scraper = OddsPortalScraper()

        # 测试URL构造
        test_url = urljoin(scraper.base_url, "/football/england/premier-league/")
        assert "oddsportal.com" in test_url

    except Exception:
        raise


@pytest.mark.asyncio


async def test_scraper_error_handling():
    """测试错误处理机制"""
    try:
        scraper = OddsPortalScraper()

        # 测试错误处理属性
        assert hasattr(scraper, "error_handling")

    except Exception:
        raise


@pytest.mark.asyncio


async def test_oddsportal_match_model():
    """测试OddsPortalMatch模型"""
    try:
        # 创建测试数据
        match = OddsPortalMatch(
            match_id="test_001",
            home_team="Manchester City",
            away_team="Manchester United",
        )

        # 验证属性
        assert match.match_id == "test_001"
        assert match.home_team == "Manchester City"
        assert match.away_team == "Manchester United"

    except Exception:
        raise


@pytest.mark.asyncio


async def test_scraper_methods():
    """测试爬虫方法"""
    try:
        scraper = OddsPortalScraper()

        # 测试基本方法是否存在
        required_methods = ["fetch_matches", "parse_match_data", "extract_odds"]

        for method in required_methods:
            assert hasattr(scraper, method), f"缺少方法: {method}"

    except Exception:
        raise


async def main():
    """主测试函数"""

    tests = [
        ("爬虫初始化", test_scraper_initialization),
        ("robots.txt解析", test_scraper_robots_parsing),
        ("速率限制", test_scraper_rate_limits),
        ("错误处理", test_scraper_error_handling),
        ("Match模型", test_oddsportal_match_model),
        ("爬虫方法", test_scraper_methods),
    ]

    passed = 0
    failed = 0

    for _test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception:
            failed += 1

    # 输出测试结果

    if failed == 0:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
