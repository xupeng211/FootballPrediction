"""增强版数据采集器 - 集成反爬对抗组件
Enhanced Data Collector - Integrated Anti-Scraping Components.

整合代理池、User-Agent随机化、频率控制等反爬技术。
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
import backoff
from playwright.async_api import async_playwright

from src.collectors.proxy_pool import ProxyConfig, get_proxy_pool
from src.collectors.rate_limiter import RateLimitStrategy, get_rate_limiter, wait_for_request_slot
from src.collectors.user_agent import get_realistic_headers, get_user_agent_manager
from src.core.logging import get_logger

logger = get_logger(__name__)


class EnhancedHTTPClient:
    """增强版HTTP客户端 - 集成反爬技术."""

    def __init__(
        self,
        use_proxy: bool = True,
        use_random_ua: bool = True,
        rate_limit_strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.use_proxy = use_proxy
        self.use_random_ua = use_random_ua
        self.rate_limit_strategy = rate_limit_strategy
        self.timeout = timeout
        self.max_retries = max_retries

        self.proxy_pool = None  # Will be initialized lazily when needed
        self.ua_manager = get_user_agent_manager() if use_random_ua else None
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.set_strategy(rate_limit_strategy)

        # 请求统计
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

        logger.info("增强版HTTP客户端初始化完成")

    async def _ensure_proxy_pool(self):
        """确保代理池已初始化."""
        if self.use_proxy and self.proxy_pool is None:
            try:
                self.proxy_pool = await get_proxy_pool()
            except Exception as e:
                logger.warning(f"代理池初始化失败，继续不使用代理: {e}")
                self.proxy_pool = None
                self.use_proxy = False

    async def get(
        self,
        url: str,
        domain: str = None,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """发送GET请求."""
        # 将 params 添加到 kwargs 中
        if params:
            kwargs['params'] = params
        return await self._request("GET", url, domain, headers, **kwargs)

    async def post(
        self,
        url: str,
        domain: str = None,
        headers: dict[str, str] = None,
        json: dict[str, Any] = None,
        data: Any = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """发送POST请求."""
        # 将 json 和 data 添加到 kwargs 中
        if json:
            kwargs['json'] = json
        if data:
            kwargs['data'] = data
        return await self._request("POST", url, domain, headers, **kwargs)

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        base=2,
        max_value=30
    )
    async def _request(
        self,
        method: str,
        url: str,
        domain: str = None,
        headers: dict[str, str] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """发送HTTP请求的核心方法."""
        # 提取域名
        if domain is None:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc

        # 等待请求时机
        await wait_for_request_slot(domain)
        start_time = time.time()

        try:
            # 准备请求头
            request_headers = await self._prepare_headers(headers)

            # 确保代理池已初始化
            await self._ensure_proxy_pool()

            # 准备代理
            proxy_config = None
            proxy_url = None
            if self.use_proxy and self.proxy_pool:
                proxy_config = await self.proxy_pool.get_proxy()
                if proxy_config:
                    proxy_url = proxy_config.url
                    logger.debug(f"使用代理: {proxy_config}")

            # 设置超时
            timeout = aiohttp.ClientTimeout(total=self.timeout)

            # 发送请求
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    proxy=proxy_url,
                    **kwargs
                ) as response:
                    response_time = time.time() - start_time

                    # 记录成功
                    await self._record_success(domain, response_time, proxy_config)

                    logger.debug(f"请求成功: {method} {url} - {response.status} ({response_time:.2f}s)")
                    return response

        except Exception as e:
            response_time = time.time() - start_time
            # 记录错误
            await self._record_error(domain, str(e), proxy_config)
            raise

    async def _prepare_headers(self, custom_headers: dict[str, str] = None) -> dict[str, str]:
        """准备请求头."""
        headers = {}

        # 获取随机User-Agent
        if self.use_random_ua and self.ua_manager:
            headers = self.ua_manager.get_realistic_headers()
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

        # 合并自定义请求头
        if custom_headers:
            headers.update(custom_headers)

        return headers

    async def _record_success(self, domain: str, response_time: float, proxy_config: ProxyConfig = None):
        """记录成功请求."""
        self.request_count += 1
        self.success_count += 1

        # 记录到频率控制器
        await self.rate_limiter.record_success(domain, response_time)

        # 记录到代理池
        if proxy_config and self.proxy_pool:
            await self.proxy_pool.mark_proxy_success(proxy_config, response_time)

    async def _record_error(self, domain: str, error_msg: str, proxy_config: ProxyConfig = None):
        """记录错误请求."""
        self.request_count += 1
        self.error_count += 1

        # 记录到频率控制器
        await self.rate_limiter.record_error(domain, error_msg)

        # 记录到代理池
        if proxy_config and self.proxy_pool:
            await self.proxy_pool.mark_proxy_failed(proxy_config, Exception(error_msg))

    def get_stats(self) -> dict[str, Any]:
        """获取客户端统计信息."""
        stats = {
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(self.request_count, 1),
            "settings": {
                "use_proxy": self.use_proxy,
                "use_random_ua": self.use_random_ua,
                "rate_limit_strategy": self.rate_limit_strategy.value,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
        }

        # 添加代理池统计
        if self.proxy_pool:
            stats["proxy_pool"] = self.proxy_pool.get_stats()

        # 添加频率控制器统计
        stats["rate_limiter"] = self.rate_limiter.get_global_stats()

        # 添加User-Agent统计
        if self.ua_manager:
            stats["user_agent"] = self.ua_manager.get_stats()

        return stats

    async def close(self):
        """关闭HTTP客户端并清理资源."""
        # 如果有代理池，在这里可以做一些清理工作
        if self.proxy_pool:
            logger.debug("HTTP客户端关闭，代理池保持全局状态")

        logger.debug("HTTP客户端已关闭")


class EnhancedPlaywrightCollector:
    """增强版Playwright采集器."""

    def __init__(
        self,
        use_proxy: bool = True,
        use_random_ua: bool = True,
        headless: bool = True,
        stealth_mode: bool = True,
    ):
        self.use_proxy = use_proxy
        self.use_random_ua = use_random_ua
        self.headless = headless
        self.stealth_mode = stealth_mode

        self.proxy_pool = None  # Will be initialized lazily when needed
        self.ua_manager = get_user_agent_manager() if use_random_ua else None
        self.rate_limiter = get_rate_limiter()

        self.playwright = None
        self.browser = None
        self.context = None

        logger.info("增强版Playwright采集器初始化完成")

    async def _ensure_proxy_pool(self):
        """确保代理池已初始化."""
        if self.use_proxy and self.proxy_pool is None:
            try:
                self.proxy_pool = await get_proxy_pool()
            except Exception as e:
                logger.warning(f"代理池初始化失败，继续不使用代理: {e}")
                self.proxy_pool = None
                self.use_proxy = False

    async def start(self):
        """启动浏览器."""
        self.playwright = await async_playwright().start()

        # 启动参数
        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
        ]

        if self.stealth_mode:
            launch_args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-networking",
            ])

        # 确保代理池已初始化
        await self._ensure_proxy_pool()

        # 代理配置
        proxy_config = None
        if self.use_proxy and self.proxy_pool:
            proxy_obj = await self.proxy_pool.get_proxy()
            if proxy_obj:
                proxy_config = {
                    "server": f"http://{proxy_obj.host}:{proxy_obj.port}",
                }
                if proxy_obj.username and proxy_obj.password:
                    proxy_config["username"] = proxy_obj.username
                    proxy_config["password"] = proxy_obj.password

        # 启动浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            proxy=proxy_config
        )

        # 创建浏览器上下文
        context_options = {}
        if self.use_random_ua and self.ua_manager:
            user_agent = self.ua_manager.get_random_user_agent()
            context_options["user_agent"] = user_agent

        if self.stealth_mode:
            context_options.update({
                "viewport": {"width": 1920, "height": 1080},
                "locale": "zh-CN",
                "timezone_id": "Asia/Shanghai",
                "permissions": [],
                "ignore_https_errors": True,
            })

        self.context = await self.browser.new_context(**context_options)

        # 隐身模式设置
        if self.stealth_mode:
            await self.context.add_init_script("""
                // 移除webdriver标识
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 伪造插件数量
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        }
                    ],
                });

                // 伪造语言
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
            """)

        logger.info("浏览器启动完成")

    async def create_page(self, domain: str = None):
        """创建新页面."""
        page = await self.context.new_page()

        # 等待请求时机
        if domain:
            await wait_for_request_slot(domain)

        # 设置请求拦截
        if self.stealth_mode:
            await page.route("**/*", self._handle_request)

        return page

    async def _handle_request(self, route, request):
        """处理请求（可选的请求拦截）."""
        # 这里可以添加请求拦截逻辑，比如过滤某些请求
        await route.continue_()

    async def close(self):
        """关闭浏览器."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口."""
        await self.close()


# 便捷函数
async def create_enhanced_http_client(**kwargs) -> EnhancedHTTPClient:
    """创建增强版HTTP客户端."""
    return EnhancedHTTPClient(**kwargs)


async def create_enhanced_playwright_collector(**kwargs) -> EnhancedPlaywrightCollector:
    """创建增强版Playwright采集器."""
    return EnhancedPlaywrightCollector(**kwargs)
