"""
ProxyPool 单元测试
Proxy Pool Unit Tests

该模块测试代理池系统的核心功能，包括：
1. Proxy 数据类的创建和操作
2. ProxyProvider 协议实现
3. ProxyPool 的代理获取、轮询、健康评分和黑名单机制
4. 多策略轮询算法
5. 自动剔除失效代理逻辑

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

from src.collectors.proxy_pool import (
    Proxy,
    ProxyProtocol,
    ProxyStatus,
    RotationStrategy,
    ProxyProvider,
    StaticProxyProvider,
    FileProxyProvider,
    ProxyPool,
    create_proxy_pool,
    create_file_proxy_pool,
)


class TestProxy:
    """Proxy 数据类测试"""

    def test_proxy_creation_basic(self):
        """测试基础代理创建"""
        proxy = Proxy(
            url="http://127.0.0.1:8080",
            protocol=ProxyProtocol.HTTP,
            host="127.0.0.1",
            port=8080
        )

        assert proxy.url == "http://127.0.0.1:8080"
        assert proxy.protocol == ProxyProtocol.HTTP
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080
        assert proxy.score == 100.0
        assert proxy.fail_count == 0
        assert proxy.success_count == 0
        assert proxy.status == ProxyStatus.ACTIVE

    def test_proxy_from_url_http(self):
        """测试从HTTP URL创建代理"""
        proxy = Proxy.from_url("http://127.0.0.1:8080")

        assert proxy.url == "http://127.0.0.1:8080"
        assert proxy.protocol == ProxyProtocol.HTTP
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080
        assert proxy.username is None
        assert proxy.password is None

    def test_proxy_from_url_with_auth(self):
        """测试从带认证的URL创建代理"""
        proxy = Proxy.from_url("http://user:pass@127.0.0.1:8080")

        assert proxy.url == "http://user:pass@127.0.0.1:8080"
        assert proxy.protocol == ProxyProtocol.HTTP
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080
        assert proxy.username == "user"
        assert proxy.password == "pass"

    def test_proxy_from_url_auto_protocol(self):
        """测试自动添加协议"""
        proxy = Proxy.from_url("127.0.0.1:8080")

        assert proxy.url == "http://127.0.0.1:8080"
        assert proxy.protocol == ProxyProtocol.HTTP

    def test_proxy_from_url_socks(self):
        """测试SOCKS代理URL解析"""
        proxy = Proxy.from_url("socks5://127.0.0.1:1080")

        assert proxy.protocol == ProxyProtocol.SOCKS5
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 1080

    def test_proxy_from_url_invalid(self):
        """测试无效URL"""
        with pytest.raises(ValueError):
            Proxy.from_url("invalid-url")

    def test_proxy_properties(self):
        """测试代理属性方法"""
        proxy = Proxy.from_url("http://127.0.0.1:8080")

        # 初始状态
        assert proxy.is_active is True
        assert proxy.is_banned is False
        assert proxy.is_healthy is True

        # 禁用代理
        proxy.ban()
        assert proxy.is_active is False
        assert proxy.is_banned is True
        assert proxy.is_healthy is False

        # 重新激活
        proxy.reactivate()
        assert proxy.is_active is True
        assert proxy.is_banned is False
        assert proxy.is_healthy is True

    def test_proxy_record_success(self):
        """测试记录成功使用"""
        proxy = Proxy.from_url("http://127.0.0.1:8080")

        # 记录成功，不指定响应时间
        proxy.record_success()
        assert proxy.success_count == 1
        assert proxy.fail_count == 0
        assert proxy.score == 100.0  # 已经是最高分

        # 降低分数后记录成功
        proxy.score = 90.0
        proxy.record_success(150.0)
        assert proxy.success_count == 2
        assert proxy.fail_count == 0
        assert proxy.score == 95.0  # 增加5分
        assert proxy.response_time == 150.0

    def test_proxy_record_failure(self):
        """测试记录失败使用"""
        proxy = Proxy.from_url("http://127.0.0.1:8080")

        # 记录失败
        proxy.record_failure()
        assert proxy.fail_count == 1
        assert proxy.success_count == 0
        assert proxy.score == 90.0  # 减少10分

        # 继续记录失败
        proxy.record_failure()
        assert proxy.fail_count == 2
        assert proxy.score == 80.0

    def test_proxy_to_dict(self):
        """测试转换为字典"""
        proxy = Proxy.from_url("http://user:pass@127.0.0.1:8080")
        proxy.score = 85.5
        proxy.fail_count = 2
        proxy.success_count = 8

        data = proxy.to_dict()

        assert data['url'] == "http://user:pass@127.0.0.1:8080"
        assert data['protocol'] == "http"
        assert data['host'] == "127.0.0.1"
        assert data['port'] == 8080
        assert data['username'] == "user"
        assert data['password'] == "***"  # 密码被隐藏
        assert data['score'] == 85.5
        assert data['fail_count'] == 2
        assert data['success_count'] == 8
        assert data['is_active'] is True
        assert data['is_banned'] is False
        assert data['is_healthy'] is True

    def test_proxy_str_representation(self):
        """测试字符串表示"""
        proxy = Proxy.from_url("http://127.0.0.1:8080")
        proxy.score = 85.5

        str_repr = str(proxy)
        assert "http://127.0.0.1:8080" in str_repr
        assert "85.5" in str_repr
        assert "active" in str_repr


class TestStaticProxyProvider:
    """StaticProxyProvider 测试"""

    def test_static_provider_init(self):
        """测试静态提供者初始化"""
        proxy_urls = [
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081",
            "socks5://127.0.0.1:1080"
        ]

        provider = StaticProxyProvider(proxy_urls)

        assert len(provider.proxies) == 3
        assert provider.proxies[0].url == "http://127.0.0.1:8080"
        assert provider.proxies[1].url == "http://127.0.0.1:8081"
        assert provider.proxies[2].url == "socks5://127.0.0.1:1080"

    @pytest.mark.asyncio
    async def test_static_provider_load_proxies(self):
        """测试加载代理列表"""
        proxy_urls = ["http://127.0.0.1:8080", "http://127.0.0.1:8081"]
        provider = StaticProxyProvider(proxy_urls)

        proxies = await provider.load_proxies()

        assert len(proxies) == 2
        assert proxies[0].url == "http://127.0.0.1:8080"
        assert proxies[1].url == "http://127.0.0.1:8081"

        # 确保返回的是副本，不是原始对象
        assert proxies is not provider.proxies

    @pytest.mark.asyncio
    async def test_static_provider_refresh_proxies(self):
        """测试刷新代理列表"""
        proxy_urls = ["http://127.0.0.1:8080"]
        provider = StaticProxyProvider(proxy_urls)

        proxies = await provider.refresh_proxies()

        assert len(proxies) == 1
        assert proxies[0].url == "http://127.0.0.1:8080"


class TestFileProxyProvider:
    """FileProxyProvider 测试"""

    @pytest.fixture
    def temp_proxy_file(self):
        """创建临时代理文件"""
        proxy_content = """
# 代理列表
http://127.0.0.1:8080
http://user:pass@127.0.0.1:8081
socks5://127.0.0.1:1080

# 这是注释
https://secure-proxy:8080
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(proxy_content)
            temp_path = f.name

        yield temp_path

        # 清理
        Path(temp_path).unlink()

    @pytest.fixture
    def temp_proxy_file_with_invalid(self):
        """创建包含无效格式的临时代理文件"""
        proxy_content = """
http://127.0.0.1:8080
invalid-proxy-url
http://127.0.0.1:8081
another-invalid
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(proxy_content)
            temp_path = f.name

        yield temp_path

        Path(temp_path).unlink()

    def test_file_provider_init(self):
        """测试文件提供者初始化"""
        provider = FileProxyProvider("/path/to/proxies.txt")

        assert provider.file_path == Path("/path/to/proxies.txt")
        assert provider.encoding == 'utf-8'
        assert provider._cached_proxies is None
        assert provider._last_modified is None

    @pytest.mark.asyncio
    async def test_file_provider_load_proxies(self, temp_proxy_file):
        """测试从文件加载代理"""
        provider = FileProxyProvider(temp_proxy_file)

        proxies = await provider.load_proxies()

        assert len(proxies) == 4
        assert proxies[0].url == "http://127.0.0.1:8080"
        assert proxies[1].url == "http://user:pass@127.0.0.1:8081"
        assert proxies[2].url == "socks5://127.0.0.1:1080"
        assert proxies[3].url == "https://secure-proxy:8080"

    @pytest.mark.asyncio
    async def test_file_provider_load_with_invalid_lines(self, temp_proxy_file_with_invalid):
        """测试加载包含无效行的文件"""
        provider = FileProxyProvider(temp_proxy_file_with_invalid)

        # 应该只加载有效的代理
        proxies = await provider.load_proxies()
        assert len(proxies) == 2
        assert proxies[0].url == "http://127.0.0.1:8080"
        assert proxies[1].url == "http://127.0.0.1:8081"

    @pytest.mark.asyncio
    async def test_file_provider_file_not_found(self):
        """测试文件不存在的情况"""
        provider = FileProxyProvider("/nonexistent/file.txt")

        with pytest.raises(FileNotFoundError):
            await provider.load_proxies()

    @pytest.mark.asyncio
    async def test_file_provider_caching(self, temp_proxy_file):
        """测试文件缓存机制"""
        provider = FileProxyProvider(temp_proxy_file)

        # 第一次加载
        proxies1 = await provider.load_proxies()
        assert provider._cached_proxies is not None

        # 第二次加载应该使用缓存
        proxies2 = await provider.load_proxies()
        assert proxies1 is proxies2  # 应该是同一个对象

        # 强制刷新
        proxies3 = await provider.refresh_proxies()
        assert proxies1 is not proxies3  # 应该是不同的对象
        assert len(proxies1) == len(proxies3)  # 但数量应该相同


class TestProxyPool:
    """ProxyPool 管理器测试"""

    @pytest.fixture
    def mock_provider(self):
        """创建模拟代理提供者"""
        proxies = [
            Proxy.from_url("http://127.0.0.1:8080"),
            Proxy.from_url("http://127.0.0.1:8081"),
            Proxy.from_url("http://127.0.0.1:8082"),
        ]
        provider = Mock(spec=ProxyProvider)
        provider.load_proxies.return_value = proxies
        provider.refresh_proxies.return_value = proxies
        return provider

    @pytest.fixture
    async def proxy_pool(self, mock_provider):
        """创建代理池实例"""
        pool = ProxyPool(
            provider=mock_provider,
            strategy=RotationStrategy.RANDOM,
            max_fail_count=3,
            min_score_threshold=40.0,
            auto_health_check=False,  # 禁用自动健康检查
        )
        await pool.initialize()
        yield pool
        await pool.close()

    def test_proxy_pool_init(self, mock_provider):
        """测试代理池初始化"""
        pool = ProxyPool(
            provider=mock_provider,
            strategy=RotationStrategy.ROUND_ROBIN,
            max_fail_count=5,
            min_score_threshold=30.0,
        )

        assert pool.provider == mock_provider
        assert pool.strategy == RotationStrategy.ROUND_ROBIN
        assert pool.max_fail_count == 5
        assert pool.min_score_threshold == 30.0
        assert pool.health_check_url == "http://httpbin.org/ip"
        assert pool.health_check_timeout == 10.0
        assert pool.auto_health_check is True

    @pytest.mark.asyncio
    async def test_proxy_pool_initialize(self, mock_provider):
        """测试代理池初始化"""
        pool = ProxyPool(mock_provider, auto_health_check=False)
        await pool.initialize()

        assert len(pool.proxies) == 3
        assert pool.proxies[0].url == "http://127.0.0.1:8080"
        mock_provider.load_proxies.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_proxy_random_strategy(self, mock_provider):
        """测试随机策略获取代理"""
        pool = ProxyPool(
            mock_provider,
            strategy=RotationStrategy.RANDOM,
            auto_health_check=False
        )
        await pool.initialize()

        # 多次获取代理，应该返回不同的代理（随机性）
        proxies = set()
        for _ in range(10):
            proxy = await pool.get_proxy()
            assert proxy is not None
            proxies.add(proxy.url)

        # 应该至少获取到2个不同的代理
        assert len(proxies) >= 2

    @pytest.mark.asyncio
    async def test_get_proxy_round_robin_strategy(self, mock_provider):
        """测试轮询策略获取代理"""
        pool = ProxyPool(
            mock_provider,
            strategy=RotationStrategy.ROUND_ROBIN,
            auto_health_check=False
        )
        await pool.initialize()

        # 按顺序获取代理
        proxy1 = await pool.get_proxy()
        proxy2 = await pool.get_proxy()
        proxy3 = await pool.get_proxy()
        proxy4 = await pool.get_proxy()  # 应该回到第一个

        assert proxy1.url == "http://127.0.0.1:8080"
        assert proxy2.url == "http://127.0.0.1:8081"
        assert proxy3.url == "http://127.0.0.1:8082"
        assert proxy4.url == "http://127.0.0.1:8080"

    @pytest.mark.asyncio
    async def test_get_proxy_weighted_random_strategy(self, mock_provider):
        """测试加权随机策略获取代理"""
        # 设置不同的分数
        mock_provider.load_proxies.return_value[0].score = 100.0
        mock_provider.load_proxies.return_value[1].score = 50.0
        mock_provider.load_proxies.return_value[2].score = 10.0

        pool = ProxyPool(
            mock_provider,
            strategy=RotationStrategy.WEIGHTED_RANDOM,
            auto_health_check=False
        )
        await pool.initialize()

        # 统计获取次数
        proxy_counts = {"8080": 0, "8081": 0, "8082": 0}
        for _ in range(100):
            proxy = await pool.get_proxy()
            if "8080" in proxy.url:
                proxy_counts["8080"] += 1
            elif "8081" in proxy.url:
                proxy_counts["8081"] += 1
            elif "8082" in proxy.url:
                proxy_counts["8082"] += 1

        # 高分代理应该被更多选择
        assert proxy_counts["8080"] > proxy_counts["8081"]
        assert proxy_counts["8081"] > proxy_counts["8082"]

    @pytest.mark.asyncio
    async def test_get_proxy_health_first_strategy(self, mock_provider):
        """测试健康优先策略获取代理"""
        # 设置不同的分数
        mock_provider.load_proxies.return_value[0].score = 100.0
        mock_provider.load_proxies.return_value[1].score = 80.0
        mock_provider.load_proxies.return_value[2].score = 60.0

        pool = ProxyPool(
            mock_provider,
            strategy=RotationStrategy.HEALTH_FIRST,
            auto_health_check=False
        )
        await pool.initialize()

        # 应该总是返回分数最高的代理
        proxy = await pool.get_proxy()
        assert proxy.score == 100.0
        assert proxy.url == "http://127.0.0.1:8080"

    @pytest.mark.asyncio
    async def test_get_proxy_no_healthy_proxies(self, mock_provider):
        """测试没有健康代理时的处理"""
        # 设置所有代理都不健康
        for proxy in mock_provider.load_proxies.return_value:
            proxy.score = 20.0  # 低于健康阈值50

        pool = ProxyPool(mock_provider, auto_health_check=False)
        await pool.initialize()

        # 没有健康代理，应该尝试重新激活
        with patch.object(pool, '_reactivate_banned_proxies') as mock_reactivate:
            proxy = await pool.get_proxy()
            mock_reactivate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_proxy_empty_pool(self):
        """测试空代理池"""
        empty_provider = Mock(spec=ProxyProvider)
        empty_provider.load_proxies.return_value = []

        pool = ProxyPool(empty_provider, auto_health_check=False)
        await pool.initialize()

        proxy = await pool.get_proxy()
        assert proxy is None

    @pytest.mark.asyncio
    async def test_record_proxy_result_success(self, proxy_pool):
        """测试记录代理成功结果"""
        proxy = await proxy_pool.get_proxy()
        original_score = proxy.score
        original_success_count = proxy.success_count

        await proxy_pool.record_proxy_result(proxy, True, 150.0)

        assert proxy.success_count == original_success_count + 1
        assert proxy.fail_count == 0
        assert proxy.response_time == 150.0
        assert proxy.score >= original_score  # 分数应该增加或保持最大值

    @pytest.mark.asyncio
    async def test_record_proxy_result_failure(self, proxy_pool):
        """测试记录代理失败结果"""
        proxy = await proxy_pool.get_proxy()
        original_score = proxy.score
        original_fail_count = proxy.fail_count

        await proxy_pool.record_proxy_result(proxy, False)

        assert proxy.fail_count == original_fail_count + 1
        assert proxy.score < original_score  # 分数应该减少

    @pytest.mark.asyncio
    async def test_auto_ban_mechanism(self, proxy_pool):
        """测试自动禁用机制"""
        proxy = await proxy_pool.get_proxy()

        # 记录多次失败，触发禁用
        for _i in range(proxy_pool.max_fail_count):
            await proxy_pool.record_proxy_result(proxy, False)

        assert proxy.is_banned is True
        assert proxy.score == 0.0

    @pytest.mark.asyncio
    async def test_ban_by_score_threshold(self, proxy_pool):
        """测试分数阈值禁用机制"""
        proxy = await proxy_pool.get_proxy()

        # 降低分数到阈值以下
        proxy.score = proxy_pool.min_score_threshold - 1.0
        await proxy_pool.record_proxy_result(proxy, False)

        assert proxy.is_banned is True

    @pytest.mark.asyncio
    async def test_reactivate_banned_proxies(self, proxy_pool):
        """测试重新激活被禁用的代理"""
        # 禁用一些代理
        proxy_pool.proxies[0].ban()
        proxy_pool.proxies[1].ban()

        banned_count = len([p for p in proxy_pool.proxies if p.is_banned])
        assert banned_count == 2

        # 重新激活
        await proxy_pool._reactivate_banned_proxies()

        # 应该有部分代理被重新激活
        reactivated_count = len([p for p in proxy_pool.proxies if p.is_active and not p.is_banned])
        assert reactivated_count > 0

    @pytest.mark.asyncio
    async def test_refresh_proxies(self, proxy_pool):
        """测试刷新代理列表"""
        # 创建新的代理列表
        new_proxies = [
            Proxy.from_url("http://127.0.0.1:8090"),
            Proxy.from_url("http://127.0.0.1:8091"),
        ]
        proxy_pool.provider.refresh_proxies.return_value = new_proxies

        # 记录原始代理的一些统计信息
        original_proxy = proxy_pool.proxies[0]
        original_proxy.success_count = 10
        original_proxy.score = 85.0

        await proxy_pool.refresh_proxies()

        # 应该保留原始代理的统计信息（如果URL相同）
        # 由于URL不同，应该使用新的代理列表
        assert len(proxy_pool.proxies) == 2
        assert proxy_pool.proxies[0].url == "http://127.0.0.1:8090"

    def test_get_stats(self, proxy_pool):
        """测试获取统计信息"""
        # 设置不同的状态
        proxy_pool.proxies[0].score = 90.0
        proxy_pool.proxies[0].response_time = 150.0
        proxy_pool.proxies[0].status = ProxyStatus.ACTIVE

        proxy_pool.proxies[1].score = 70.0
        proxy_pool.proxies[1].response_time = 200.0
        proxy_pool.proxies[1].status = ProxyStatus.ACTIVE

        proxy_pool.proxies[2].ban()  # 禁用一个代理

        stats = proxy_pool.get_stats()

        assert stats['total'] == 3
        assert stats['active'] == 2
        assert stats['banned'] == 1
        assert stats['healthy'] == 2  # 分数>50的代理
        assert stats['avg_score'] == 53.33  # (90+70+0)/3
        assert stats['avg_response_time'] == 175.0  # (150+200)/2

    def test_get_proxies_info(self, proxy_pool):
        """测试获取代理详细信息"""
        # 设置一些属性
        proxy_pool.proxies[0].score = 85.5
        proxy_pool.proxies[0].fail_count = 2
        proxy_pool.proxies[0].success_count = 8

        info = proxy_pool.get_proxies_info()

        assert len(info) == 3
        assert info[0]['url'] == "http://127.0.0.1:8080"
        assert info[0]['score'] == 85.5
        assert info[0]['fail_count'] == 2
        assert info[0]['success_count'] == 8
        assert info[0]['is_active'] is True
        assert info[0]['is_healthy'] is True

    @pytest.mark.asyncio
    async def test_health_check_single_proxy_success(self, proxy_pool):
        """测试单个代理健康检查成功"""
        proxy = proxy_pool.proxies[0]

        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = '{"origin": "127.0.0.1"}'

            mock_get.return_value.__aenter__.return_value = mock_response

            result = await proxy_pool._check_single_proxy(proxy)

            assert result is True
            assert proxy.success_count > 0
            assert proxy.fail_count == 0
            assert proxy.response_time is not None

    @pytest.mark.asyncio
    async def test_health_check_single_proxy_failure(self, proxy_pool):
        """测试单个代理健康检查失败"""
        proxy = proxy_pool.proxies[0]

        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟失败响应
            mock_get.side_effect = Exception("Connection failed")

            result = await proxy_pool._check_single_proxy(proxy)

            assert result is False
            assert proxy.fail_count > 0

    @pytest.mark.asyncio
    async def test_proxy_pool_close(self):
        """测试关闭代理池"""
        pool = ProxyPool(Mock(spec=ProxyProvider), auto_health_check=True)

        with patch.object(pool, '_health_check_task') as mock_task:
            await pool.close()
            mock_task.cancel.assert_called_once()


class TestConvenienceFunctions:
    """便利函数测试"""

    def test_create_proxy_pool(self):
        """测试创建代理池便利函数"""
        proxy_urls = [
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081"
        ]

        pool = create_proxy_pool(
            proxy_urls,
            strategy=RotationStrategy.RANDOM,
            max_fail_count=5
        )

        assert isinstance(pool.provider, StaticProxyProvider)
        assert pool.strategy == RotationStrategy.RANDOM
        assert pool.max_fail_count == 5
        assert len(pool.provider.proxies) == 2

    def test_create_file_proxy_pool(self):
        """测试创建基于文件的代理池便利函数"""
        pool = create_file_proxy_pool(
            "/path/to/proxies.txt",
            strategy=RotationStrategy.ROUND_ROBIN,
            health_check_timeout=15.0
        )

        assert isinstance(pool.provider, FileProxyProvider)
        assert pool.strategy == RotationStrategy.ROUND_ROBIN
        assert pool.health_check_timeout == 15.0


class TestProtocolCompliance:
    """协议合规性测试"""

    def test_proxy_provider_protocol_compliance(self):
        """测试代理提供者协议合规性"""
        static_provider = StaticProxyProvider(["http://127.0.0.1:8080"])

        # 检查是否实现了协议
        assert isinstance(static_provider, ProxyProvider)

        # 检查是否有必需的方法
        assert hasattr(static_provider, 'load_proxies')
        assert hasattr(static_provider, 'refresh_proxies')
        assert callable(static_provider.load_proxies)
        assert callable(static_provider.refresh_proxies)

    @pytest.mark.asyncio
    async def test_static_provider_protocol_methods(self):
        """测试静态提供者协议方法"""
        provider = StaticProxyProvider(["http://127.0.0.1:8080"])

        # 测试协议方法
        proxies = await provider.load_proxies()
        assert isinstance(proxies, list)
        assert len(proxies) == 1

        refreshed = await provider.refresh_proxies()
        assert isinstance(refreshed, list)
        assert len(refreshed) == 1


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_provider_load_error(self):
        """测试提供者加载错误"""
        provider = Mock(spec=ProxyProvider)
        provider.load_proxies.side_effect = Exception("Load failed")

        pool = ProxyPool(provider, auto_health_check=False)

        with pytest.raises(Exception):
            await pool.initialize()

    @pytest.mark.asyncio
    async def test_provider_refresh_error(self, proxy_pool):
        """测试提供者刷新错误"""
        proxy_pool.provider.refresh_proxies.side_effect = Exception("Refresh failed")

        # 应该不抛出异常，而是打印错误信息
        await proxy_pool.refresh_proxies()

        # 代理列表应该保持不变
        assert len(proxy_pool.proxies) == 3

    def test_proxy_from_url_edge_cases(self):
        """测试代理URL解析的边界情况"""
        # 测试IPv6地址
        proxy = Proxy.from_url("http://[::1]:8080")
        assert proxy.host == "::1"
        assert proxy.port == 8080

        # 测试带路径的URL（应该忽略路径）
        proxy = Proxy.from_url("http://127.0.0.1:8080/path")
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080

        # 测试带查询参数的URL（应该忽略查询参数）
        proxy = Proxy.from_url("http://127.0.0.1:8080?param=value")
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080


@pytest.mark.asyncio
async def test_integration_workflow():
    """集成测试：完整的代理池工作流程"""
    print("🧪 开始代理池集成测试...")

    # 1. 创建模拟代理
    proxy_urls = [
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8082",
        "http://127.0.0.1:8083",
    ]

    # 2. 创建代理池
    pool = create_proxy_pool(
        proxy_urls,
        strategy=RotationStrategy.WEIGHTED_RANDOM,
        max_fail_count=3,
        auto_health_check=False
    )

    await pool.initialize()
    print(f"✅ 代理池初始化完成，加载了 {len(pool.proxies)} 个代理")

    # 3. 获取代理并模拟使用
    used_proxies = []
    for i in range(10):
        proxy = await pool.get_proxy()
        assert proxy is not None, f"第{i+1}次获取代理失败"

        # 模拟80%成功率
        if i % 5 != 0:  # 4/5的概率成功
            response_time = 100 + i * 10  # 模拟递增的响应时间
            await pool.record_proxy_result(proxy, True, response_time)
            print(f"✅ 代理 {proxy.url} 使用成功，响应时间: {response_time}ms")
        else:
            await pool.record_proxy_result(proxy, False)
            print(f"❌ 代理 {proxy.url} 使用失败")

        used_proxies.append(proxy.url)

    # 4. 检查代理分布
    proxy_counts = {}
    for url in used_proxies:
        proxy_counts[url] = proxy_counts.get(url, 0) + 1

    print(f"📊 代理使用分布: {proxy_counts}")

    # 5. 检查统计信息
    stats = pool.get_stats()
    print(f"📈 代理池统计: {stats}")

    # 6. 强制禁用一个代理
    target_proxy = pool.proxies[0]
    print(f"🚫 强制禁用代理: {target_proxy.url}")
    for _ in range(pool.max_fail_count):
        await pool.record_proxy_result(target_proxy, False)

    assert target_proxy.is_banned, "代理应该被禁用"
    print(f"✅ 代理 {target_proxy.url} 已被禁用")

    # 7. 验证禁用后不再被选择
    selected_proxies = set()
    for _ in range(20):
        proxy = await pool.get_proxy()
        if proxy:
            selected_proxies.add(proxy.url)

    assert target_proxy.url not in selected_proxies, "被禁用的代理不应该被选择"
    print(f"✅ 被禁用的代理不再被选择，可用代理数: {len(selected_proxies)}")

    # 8. 测试重新激活机制
    await pool._reactivate_banned_proxies()
    if target_proxy.is_active:
        print(f"🔄 代理 {target_proxy.url} 已被重新激活")

    # 9. 清理
    await pool.close()
    print("🎉 代理池集成测试完成！")

    # 验证关键指标
    assert len(proxy_counts) >= 2, "应该使用多个不同的代理"
    assert stats['total'] == 4, "总代理数应该为4"
    assert stats['banned'] >= 1, "至少应该有1个被禁用的代理"


if __name__ == "__main__":
    # 运行集成测试
    asyncio.run(test_integration_workflow())
