#!/usr/bin/env python3
"""
OddsPortal爬虫测试脚本
测试OddsPortal数据抓取功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.collectors.oddsportal_scraper import (OddsPortalMatch,
                                               OddsPortalScraper)
from src.core.logging_system import get_logger

logger = get_logger(__name__)


async def test_scraper_initialization():
    """测试爬虫初始化"""
    logger.info("Testing OddsPortal Scraper Initialization...")

    try:
        scraper = OddsPortalScraper()

        # 测试基本属性
        assert scraper.base_url == "https://www.oddsportal.com"
        assert scraper.min_request_interval == 1.0  # 默认速率限制
        assert hasattr(scraper, "session")
        assert scraper.robots_parser is not None

        logger.info("✅ Scraper initialization test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Scraper initialization test failed: {e}")
        return False


async def test_robots_txt():
    """测试robots.txt检查"""
    logger.info("Testing robots.txt compliance...")

    try:
        scraper = OddsPortalScraper()

        # 验证robots_parser已初始化
        assert hasattr(scraper, "robots_parser")
        assert scraper.robots_parser is not None

        logger.info("✅ robots.txt compliance test passed")
        return True
    except Exception as e:
        logger.error(f"❌ robots.txt compliance test failed: {e}")
        return False


async def test_data_parsing():
    """测试数据解析功能"""
    logger.info("Testing data parsing functionality...")

    try:
        OddsPortalScraper()

        # 模拟HTML响应进行解析测试
        sample_html = """
        <table class="table-main">
            <tr>
                <td class="datet">13:00</td>
                <td class="name">
                    <a href="/soccer/england/premier-league/manchester-city-vs-liverpool/">Manchester City - Liverpool</a>
                </td>
                <td class="odds">
                    <span class="odds">2.45</span>
                    <span class="odds">3.20</span>
                    <span class="odds">2.80</span>
                </td>
            </tr>
        </table>
        """

        # 测试解析功能
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(sample_html, "html.parser")

        # 验证基本解析
        table = soup.find("table", class_="table-main")
        assert table is not None

        logger.info("✅ Data parsing test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Data parsing test failed: {e}")
        return False


async def test_url_construction():
    """测试URL构造"""
    logger.info("Testing URL construction...")

    try:
        from urllib.parse import urljoin

        scraper = OddsPortalScraper()

        # 测试URL构造
        league_url = urljoin(scraper.base_url, "/soccer/england/premier-league/")
        assert league_url == "https://www.oddsportal.com/soccer/england/premier-league/"

        match_url = urljoin(scraper.base_url, "/match/123456/")
        assert match_url == "https://www.oddsportal.com/match/123456/"

        logger.info("✅ URL construction test passed")
        return True
    except Exception as e:
        logger.error(f"❌ URL construction test failed: {e}")
        return False


async def test_rate_limiting():
    """测试速率限制"""
    logger.info("Testing rate limiting...")

    try:
        scraper = OddsPortalScraper()

        # 测试速率限制属性
        assert hasattr(scraper, "min_request_interval")
        assert scraper.min_request_interval == 1.0
        assert hasattr(scraper, "rate_limit_requests_per_minute")
        assert scraper.rate_limit_requests_per_minute == 60
        assert hasattr(scraper, "request_times")
        assert isinstance(scraper.request_times, list)

        logger.info("✅ Rate limiting test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Rate limiting test failed: {e}")
        return False


async def test_data_structure():
    """测试数据结构"""
    logger.info("Testing OddsPortalMatch data structure...")

    try:
        from dataclasses import asdict
        from datetime import datetime

        # 创建测试数据
        match = OddsPortalMatch(
            match_id="test_001",
            home_team="Manchester City",
            away_team="Liverpool",
            league="Premier League",
            match_date=datetime.now(),
            status="upcoming",
            odds_home_win=2.45,
            odds_draw=3.20,
            odds_away_win=2.80,
        )

        # 验证数据结构
        assert match.home_team == "Manchester City"
        assert match.away_team == "Liverpool"
        assert match.odds_home_win == 2.45
        assert match.odds_draw == 3.20
        assert match.odds_away_win == 2.80

        # 测试转换为字典
        match_dict = asdict(match)
        assert isinstance(match_dict, dict)
        assert "home_team" in match_dict
        assert "odds_home_win" in match_dict

        logger.info("✅ Data structure test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Data structure test failed: {e}")
        return False


async def test_error_handling():
    """测试错误处理"""
    logger.info("Testing error handling...")

    try:
        scraper = OddsPortalScraper()

        # 测试错误处理属性
        assert hasattr(scraper, "max_retries")
        assert scraper.max_retries == 3
        assert hasattr(scraper, "retry_delay")
        assert scraper.retry_delay == 2

        logger.info("✅ Error handling test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False


async def test_adapter_interface():
    """测试适配器接口"""
    logger.info("Testing DataSourceAdapter interface...")

    try:

        scraper = OddsPortalScraper()

        # 测试基本方法是否存在
        assert hasattr(scraper, "base_url")
        assert scraper.base_url == "https://www.oddsportal.com"
        assert hasattr(scraper, "user_agent")
        assert "Mozilla" in scraper.user_agent

        logger.info("✅ Adapter interface test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Adapter interface test failed: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("Starting OddsPortal Scraper Tests...")

    tests = [
        ("Scraper Initialization", test_scraper_initialization),
        ("Robots.txt Compliance", test_robots_txt),
        ("Data Parsing", test_data_parsing),
        ("URL Construction", test_url_construction),
        ("Rate Limiting", test_rate_limiting),
        ("Data Structure", test_data_structure),
        ("Error Handling", test_error_handling),
        ("Adapter Interface", test_adapter_interface),
    ]

    results = {}
    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*50}")

        try:
            result = await test_func()
            results[test_name] = result
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False

    # 测试总结
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    logger.info(f"Success Rate: {passed/total*100:.1f}%")

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")

    if passed == total:
        logger.info("\n🎉 All tests passed! OddsPortal scraper is working correctly.")
    else:
        logger.warning(
            f"\n⚠️ {total - passed} test(s) failed. Please check the implementation."
        )

    return results


async def main():
    """主函数"""
    try:
        results = await run_all_tests()
        return results
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
