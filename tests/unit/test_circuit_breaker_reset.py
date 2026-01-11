#!/usr/bin/env python3
"""
Unit Test: CircuitBreakerManager Proxy Reset Functionality (TDD First)

测试目标：验证 reset_all_proxies() 方法能够正确清理所有代理状态

Author: 高级 SRE (Staff SRE)
Date: 2026-01-11
Version: V32.0 (Proxy Health Reset)
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.scrapers.oddsportal import (
    CircuitBreakerManager,
    CircuitBreakerConfig,
)


class TestCircuitBreakerReset:
    """测试熔断器代理复位功能 (TDD)"""

    @pytest.fixture
    def sample_proxies(self):
        """示例代理池"""
        return ["http://proxy1:7890", "http://proxy2:7891", "http://proxy3:7892"]

    @pytest.fixture
    def config(self):
        """熔断器配置"""
        return CircuitBreakerConfig(
            failure_threshold=3,
            cooldown_timeout=300,
            emergency_stop_threshold=0.3
        )

    @pytest.fixture
    def manager(self, sample_proxies, config):
        """熔断器管理器实例"""
        return CircuitBreakerManager(config, sample_proxies)

    def test_reset_clears_blacklist(self, manager, sample_proxies):
        """测试：reset_all_proxies() 清除黑名单状态"""
        beijing_tz = ZoneInfo("Asia/Shanghai")

        # 设置一个代理为黑名单状态
        blacklist_end = datetime.now(beijing_tz) + timedelta(minutes=15)
        manager.blacklist_until[sample_proxies[0]] = blacklist_end
        manager.forbidden_counts[sample_proxies[0]] = 3

        # 验证代理在黑名单中
        assert sample_proxies[0] in manager.blacklist_until
        assert manager.forbidden_counts[sample_proxies[0]] == 3
        assert not manager.is_available(sample_proxies[0])

        # 调用 reset_all_proxies()
        if hasattr(manager, 'reset_all_proxies'):
            manager.reset_all_proxies()
        else:
            pytest.skip("reset_all_proxies() method not implemented yet")

        # 验证黑名单已清除
        assert sample_proxies[0] not in manager.blacklist_until
        assert manager.forbidden_counts[sample_proxies[0]] == 0
        assert manager.is_available(sample_proxies[0])

    def test_reset_clears_cooldown(self, manager, sample_proxies):
        """测试：reset_all_proxies() 清除冷却状态"""
        beijing_tz = ZoneInfo("Asia/Shanghai")

        # 设置一个代理为冷却状态
        cooldown_end = datetime.now(beijing_tz) + timedelta(seconds=300)
        manager.cooldown_until[sample_proxies[1]] = cooldown_end
        manager.failed_counts[sample_proxies[1]] = 5

        # 验证代理在冷却中
        assert sample_proxies[1] in manager.cooldown_until
        assert manager.failed_counts[sample_proxies[1]] == 5
        assert not manager.is_available(sample_proxies[1])

        # 调用 reset_all_proxies()
        if hasattr(manager, 'reset_all_proxies'):
            manager.reset_all_proxies()
        else:
            pytest.skip("reset_all_proxies() method not implemented yet")

        # 验证冷却已清除
        assert sample_proxies[1] not in manager.cooldown_until
        assert manager.failed_counts[sample_proxies[1]] == 0
        assert manager.is_available(sample_proxies[1])

    def test_reset_clears_all_states(self, manager, sample_proxies):
        """测试：reset_all_proxies() 清除所有状态（混合场景）"""
        beijing_tz = ZoneInfo("Asia/Shanghai")

        # 设置多种状态
        # 代理 0: 黑名单
        manager.blacklist_until[sample_proxies[0]] = datetime.now(beijing_tz) + timedelta(minutes=15)
        manager.forbidden_counts[sample_proxies[0]] = 3

        # 代理 1: 冷却
        manager.cooldown_until[sample_proxies[1]] = datetime.now(beijing_tz) + timedelta(seconds=300)
        manager.failed_counts[sample_proxies[1]] = 5

        # 代理 2: 正常但有失败计数
        manager.failed_counts[sample_proxies[2]] = 2

        # 验证初始状态
        assert not manager.is_available(sample_proxies[0])
        assert not manager.is_available(sample_proxies[1])
        assert manager.get_status()["active_proxies"] == 1

        # 调用 reset_all_proxies()
        if hasattr(manager, 'reset_all_proxies'):
            manager.reset_all_proxies()
        else:
            pytest.skip("reset_all_proxies() method not implemented yet")

        # 验证所有状态已清除
        assert len(manager.blacklist_until) == 0
        assert len(manager.cooldown_until) == 0
        assert len(manager.forbidden_counts) == 0
        assert len(manager.failed_counts) == 0

        # 验证所有代理可用
        for proxy in sample_proxies:
            assert manager.is_available(proxy)

        # 验证状态报告
        status = manager.get_status()
        assert status["active_proxies"] == len(sample_proxies)
        assert status["blacklisted_proxies"] == 0
        assert status["availability_rate"] == "100.0%"

    def test_reset_returns_summary(self, manager, sample_proxies):
        """测试：reset_all_proxies() 返回复位摘要"""
        beijing_tz = ZoneInfo("Asia/Shanghai")

        # 设置一些状态
        manager.blacklist_until[sample_proxies[0]] = datetime.now(beijing_tz) + timedelta(minutes=15)
        manager.cooldown_until[sample_proxies[1]] = datetime.now(beijing_tz) + timedelta(seconds=300)

        # 调用 reset_all_proxies()
        if hasattr(manager, 'reset_all_proxies'):
            result = manager.reset_all_proxies()

            # 验证返回值
            assert isinstance(result, dict)
            assert "blacklisted_cleared" in result
            assert "cooldown_cleared" in result
            assert "total_cleared" in result
            assert result["blacklisted_cleared"] == 1
            assert result["cooldown_cleared"] == 1
            assert result["total_cleared"] == 2
        else:
            pytest.skip("reset_all_proxies() method not implemented yet")

    def test_reset_with_empty_manager(self, manager):
        """测试：reset_all_proxies() 在空状态下也能正常工作"""
        # 确保初始状态为空
        assert len(manager.blacklist_until) == 0
        assert len(manager.cooldown_until) == 0

        # 调用 reset_all_proxies()
        if hasattr(manager, 'reset_all_proxies'):
            result = manager.reset_all_proxies()

            # 验证不会出错
            assert result["total_cleared"] == 0
            assert result["blacklisted_cleared"] == 0
            assert result["cooldown_cleared"] == 0
        else:
            pytest.skip("reset_all_proxies() method not implemented yet")
