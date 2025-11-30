from typing import Optional

#!/usr/bin/env python3
"""
OddsPortal集成测试脚本
Test OddsPortal Integration
"""

import pytest

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 在路径修改后导入模块
try:
    from src.collectors.oddsportal_integration import (
        OddsPortalAdapter,
        OddsPortalIntegration,
    )
    from src.core.logging_system import get_logger

    logger = get_logger(__name__)
except ImportError:
    # 如果导入失败，创建mock
    class OddsPortalAdapter:
        pass

    class OddsPortalIntegration:
        pass

    def get_logger(name):
        import logging

        return logging.getLogger(name)

    logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_integration_initialization():
    """测试集成初始化"""
    logger.info("Testing OddsPortal Integration Initialization...")

    try:
        integration = OddsPortalIntegration()
        await integration.initialize()

        # 验证初始化状态
        assert integration.is_initialized
        assert integration.scraper is not None

        await integration.cleanup()

        logger.info("✅ Integration initialization test passed")
        return True
    except Exception:
        logger.error(f"❌ Integration initialization test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_configuration_loading():
    """测试配置加载"""
    logger.info("Testing configuration loading...")

    try:
        integration = OddsPortalIntegration()

        # 验证配置加载
        assert integration.config is not None
        assert "basic" in integration.config
        assert "request" in integration.config
        assert "scraping" in integration.config

        # 验证配置内容
        assert integration.config["basic"]["name"] == "OddsPortal"
        assert integration.config["basic"]["enabled"] is True

        logger.info("✅ Configuration loading test passed")
        return True
    except Exception:
        logger.error(f"❌ Configuration loading test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_source_info():
    """测试数据源信息获取"""
    logger.info("Testing source info retrieval...")

    try:
        integration = OddsPortalIntegration()
        await integration.initialize()

        # 获取数据源信息
        info = await integration.get_source_info()

        # 验证信息结构
        assert isinstance(info, dict)
        assert "name" in info
        assert "type" in info
        assert "base_url" in info
        assert "supported_sports" in info

        assert info["name"] == "OddsPortal"
        assert info["type"] == "web_scraper"
        assert info["base_url"] == "https://www.oddsportal.com"

        await integration.cleanup()

        logger.info("✅ Source info test passed")
        return True
    except Exception:
        logger.error(f"❌ Source info test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查"""
    logger.info("Testing health check...")

    try:
        integration = OddsPortalIntegration()
        await integration.initialize()

        # 执行健康检查
        health = await integration.health_check()

        # 验证健康检查结果
        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health

        await integration.cleanup()

        logger.info("✅ Health check test passed")
        return True
    except Exception:
        logger.error(f"❌ Health check test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_adapter_interface():
    """测试适配器接口"""
    logger.info("Testing adapter interface...")

    try:
        from src.collectors.data_sources import DataSourceAdapter

        adapter = OddsPortalAdapter()

        # 验证实现了正确的接口
        assert isinstance(adapter, DataSourceAdapter)
        assert hasattr(adapter, "fetch_matches")
        assert hasattr(adapter, "test_connection")
        assert hasattr(adapter, "get_source_info")

        # 测试接口方法
        info = await adapter.get_source_info()
        assert isinstance(info, dict)
        assert info["name"] == "OddsPortal"

        logger.info("✅ Adapter interface test passed")
        return True
    except Exception:
        logger.error(f"❌ Adapter interface test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_data_conversion():
    """测试数据转换"""
    logger.info("Testing data conversion...")

    try:
        from datetime import datetime

        from src.collectors.oddsportal_scraper import OddsPortalMatch

        integration = OddsPortalIntegration()

        # 创建测试OddsPortalMatch
        oddsportal_match = OddsPortalMatch(
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

        # 转换为MatchData
        match_data = integration._convert_to_match_data(oddsportal_match)

        # 验证转换结果
        assert match_data is not None
        assert match_data.home_team == "Manchester City"
        assert match_data.away_team == "Liverpool"
        assert match_data.league == "Premier League"
        # MatchData不包含source和odds字段，这些通过OddsData单独处理

        logger.info("✅ Data conversion test passed")
        return True
    except Exception:
        logger.error(f"❌ Data conversion test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    logger.info("Testing error handling...")

    try:
        # 测试无效配置路径
        integration = OddsPortalIntegration("/invalid/path/config.yaml")

        # 应该使用默认配置而不是抛出异常
        assert integration.config is not None
        assert "basic" in integration.config

        logger.info("✅ Error handling test passed")
        return True
    except Exception:
        logger.error(f"❌ Error handling test failed: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("Starting OddsPortal Integration Tests...")

    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("Integration Initialization", test_integration_initialization),
        ("Source Info", test_source_info),
        ("Health Check", test_health_check),
        ("Adapter Interface", test_adapter_interface),
        ("Data Conversion", test_data_conversion),
        ("Error Handling", test_error_handling),
    ]

    results = {}
    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'=' * 50}")

        try:
            result = await test_func()
            results[test_name] = result
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False

    # 测试总结
    logger.info(f"\n{'=' * 50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'=' * 50}")
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    logger.info(f"Success Rate: {passed / total * 100:.1f}%")

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")

    if passed == total:
        logger.info(
            "\n🎉 All tests passed! OddsPortal integration is working correctly."
        )
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
    except Exception:
        logger.error(f"Test execution failed: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
