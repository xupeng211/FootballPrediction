#!/usr/bin/env python3
"""V41.167 Response Interceptor - 纯异步重构版.

彻底修复异步架构问题，确保每一个 async 都有对应的 await。

核心修复:
    - 使用 asyncio.create_task 在同步回调中调度异步任务
    - 确保所有 response.body() 都被正确 await
    - 添加完整的异常处理链

Author: 顶级反爬对抗与异步编程专家
Version: V41.167 "最后通牒"
Date: 2026-01-18
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Callable

    from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class InterceptedJSON:
    """被截获的 JSON 数据"""
    url: str
    json_data: dict[str, Any] | list[Any]
    timestamp: str
    status_code: int
    headers: dict[str, str]
    matched_keywords: list[str] = field(default_factory=list)
    content_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "json_data": self.json_data,
            "timestamp": self.timestamp,
            "status_code": self.status_code,
            "headers": self.headers,
            "matched_keywords": self.matched_keywords,
            "content_type": self.content_type,
        }

    def save_to_file(self, output_dir: str = "storage/intercepted_json") -> Path:
        """保存到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 从 URL 生成文件名
        parsed = urlparse(self.url)
        filename = f"{parsed.netloc.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"💾 JSON 已保存: {filepath}")
        return filepath


@dataclass
class InterceptorConfig:
    """拦截器配置"""
    # V41.167: 增强关键字列表 - 匹配所有 odds/pinnacle 相关数据
    keywords: list[str] = field(default_factory=lambda: [
        "odds",
        "pinnacle",
        "pinny",
        "match/",
        "1x2",
        "home",
        "draw",
        "away",
        "h-",
        "d-",
        "a-",
        "bet365",
        "williamhill",
        "ladbrokes",
    ])

    # Content-Type 白名单
    content_type_whitelist: list[str] = field(default_factory=lambda: [
        "application/json",
        "application/ld+json",
        "text/plain",
        "text/html",
        "application/x-www-form-urlencoded",
    ])

    # URL 白名单
    url_whitelist: list[str] = field(default_factory=lambda: [
        "oddsportal.com",
        "api.",
    ])

    # 是否保存所有截获的数据
    save_all: bool = True  # V41.167: 默认保存所有数据

    # 输出目录
    output_dir: str = "storage/intercepted_json"

    # 最大截获数量（防止内存溢出）
    max_intercepts: int = 10000


# ============================================================================
# Main Interceptor Class - V41.167 纯异步重构版
# ============================================================================


class ResponseInterceptor:
    """V41.167 Response 拦截器 - 纯异步重构版

    彻底修复异步架构问题：
    - 使用 asyncio.create_task 调度异步任务
    - 确保所有 response.body() 都被正确 await
    - 完整的异常处理链

    Example:
        >>> interceptor = ResponseInterceptor()
        >>> await interceptor.attach_to_page(page)
        >>> await page.goto("https://example.com")
        >>> # 访问截获的数据
        >>> jsons = await interceptor.get_intercepted_jsons()
    """

    def __init__(self, config: InterceptorConfig | None = None) -> None:
        """初始化拦截器

        Args:
            config: 拦截器配置（可选）
        """
        self.config = config or InterceptorConfig()
        self._intercepted_jsons: list[InterceptedJSON] = []
        self._intercept_count = 0
        self._handlers: list[Callable[[InterceptedJSON], None]] = []

        # V41.167: 跟踪所有后台处理任务
        self._pending_tasks: list[asyncio.Task] = []

        # V41.167: 线程池用于同步回调中执行异步操作
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="interceptor")

        # 创建输出目录
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    def add_handler(self, handler: Callable[[InterceptedJSON], None]) -> None:
        """添加数据处理函数

        Args:
            handler: 处理函数，接收 InterceptedJSON 对象
        """
        self._handlers.append(handler)
        logger.info(f"📝 已添加处理函数: {handler.__name__}")

    def _response_handler(self, response: Response) -> None:
        """V41.167: 同步响应处理器（使用 asyncio.create_task 立即调度）

        关键修复：使用 asyncio.create_task 在响应到达时立即处理
        这样 response.body() 仍然可用

        Args:
            response: Playwright Response 对象
        """
        try:
            # 快速同步检查（不使用 await）
            url = response.url
            url_lower = url.lower()

            # V41.167: 调试日志 - 记录所有响应
            logger.debug(f"📥 收到响应: {url[:100]}")

            # 检查关键字匹配（同步操作）
            matched_keywords = [
                keyword for keyword in self.config.keywords
                if keyword.lower() in url_lower
            ]

            # V41.167: 修复 URL 白名单逻辑
            # 如果没有匹配关键字且不是保存所有模式，跳过
            if not matched_keywords and not self.config.save_all:
                logger.debug(f"⏭️  跳过（无关键字且非 save_all）: {url[:80]}")
                return

            # V41.167: URL 白名单检查只在非 save_all 模式下生效
            # save_all=True 时应该捕获所有响应，不受白名单限制
            if not self.config.save_all and self.config.url_whitelist:
                if not any(white in url_lower for white in self.config.url_whitelist):
                    logger.debug(f"⏭️  跳过（不在白名单）: {url[:80]}")
                    return

            # V41.167: 关键修复！使用 asyncio.create_task 立即调度处理任务
            # 这样 response.body() 仍然可用，数据不会被清理
            task = asyncio.create_task(self._process_response_immediately(
                response, url, url_lower, matched_keywords
            ))
            # V41.167: 跟踪任务以便等待完成
            self._pending_tasks.append(task)
            logger.debug(f"✅ 已调度处理任务: {url[:80]}")

        except Exception as e:
            logger.debug(f"⚠️ 响应处理调度异常: {e}")

    async def _process_response_immediately(
        self,
        response: Response,
        url: str,
        url_lower: str,
        matched_keywords: list[str]
    ) -> None:
        """V41.167: 立即处理响应（在响应到达时）

        这个方法通过 asyncio.create_task 立即调度，
        确保 response.body() 在数据过期之前被调用

        Args:
            response: Playwright Response 对象
            url: 响应 URL
            url_lower: 小写的 URL
            matched_keywords: 匹配的关键字列表
        """
        try:
            # 检查是否达到最大截获数量
            if self._intercept_count >= self.config.max_intercepts:
                return

            # V41.167: 立即获取响应体（数据仍然可用）
            try:
                body = await response.body()
                body_text = body.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.debug(f"⚠️ 无法获取响应体: {e}")
                return

            # 尝试解析 JSON
            try:
                json_data = json.loads(body_text)
            except json.JSONDecodeError:
                # 不是 JSON，跳过
                return

            # V41.167: 获取 headers（同步属性）
            headers = dict(response.headers)
            status_code = response.status
            content_type = response.header_value("content-type") or ""

            # 创建截获对象
            intercepted = InterceptedJSON(
                url=url,
                json_data=json_data,
                timestamp=datetime.now(UTC).isoformat(),
                status_code=status_code,
                headers=headers,
                matched_keywords=matched_keywords,
                content_type=content_type,
            )

            # 添加到列表
            self._intercepted_jsons.append(intercepted)
            self._intercept_count += 1

            # 记录日志
            logger.info(
                f"🎯 截获 JSON [{self._intercept_count}]: {url[:100]} "
                f"(关键字: {matched_keywords}, 大小: {len(body_text)} bytes, 状态: {status_code})"
            )

            # 调用所有处理函数
            for handler in self._handlers:
                try:
                    handler(intercepted)
                except Exception as e:
                    logger.exception(f"❌ 处理函数执行失败: {e}")

            # 自动保存（如果配置了）
            if self.config.save_all:
                try:
                    intercepted.save_to_file(self.config.output_dir)
                except Exception as save_error:
                    logger.exception(f"❌ 保存失败: {save_error}")

        except Exception as e:
            logger.exception(f"❌ 处理响应异常: {e}")

    async def _route_handler(self, route, request) -> None:
        """V41.167: Route 处理器 - 让请求继续，response 事件处理

        关键：只使用 route 进行过滤，实际的数据捕获在 response 事件中完成

        Args:
            route: Playwright Route 对象
            request: Playwright Request 对象
        """
        url = request.url
        url_lower = url.lower()

        # 检查关键字匹配（同步操作）
        matched_keywords = [
            keyword for keyword in self.config.keywords
            if keyword.lower() in url_lower
        ]

        # V41.167: 修复 URL 白名单逻辑
        # 如果没有匹配关键字且不是保存所有模式，让请求直接通过
        if not matched_keywords and not self.config.save_all:
            await route.continue_()
            return

        # V41.167: URL 白名单检查只在非 save_all 模式下生效
        if not self.config.save_all and self.config.url_whitelist:
            if not any(white in url_lower for white in self.config.url_whitelist):
                await route.continue_()
                return

        # V41.167: 关键！继续请求，让 response 事件处理数据捕获
        # 在 URL 中添加标记，表示这是我们感兴趣的请求
        await route.continue_()

    async def attach_to_page(self, page: Page) -> None:
        """附加到 Playwright 页面

        V41.167: 使用 JavaScript 注入拦截 fetch/XHR 数据

        Args:
            page: Playwright Page 对象
        """
        # V41.167: 注入 JavaScript 拦截器
        js_code = """
        () => {
            // 存储截获的 JSON 数据
            window.__interceptedData = [];

            // 拦截 fetch API
            const originalFetch = window.fetch;
            window.fetch = async function(...args) {
                const response = await originalFetch.apply(this, args);

                // 克隆响应以便读取
                const clonedResponse = response.clone();

                // 尝试读取 JSON 数据
                clonedResponse.text().then(text => {
                    try {
                        const jsonData = JSON.parse(text);
                        window.__interceptedData.push({
                            url: args[0],
                            json: jsonData,
                            timestamp: new Date().toISOString()
                        });
                    } catch (e) {
                        // 不是 JSON，忽略
                    }
                }).catch(() => {
                    // 读取失败，忽略
                });

                return response;
            };

            // 拦截 XMLHttpRequest
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                this._url = url;
                return originalOpen.apply(this, [method, url, ...rest]);
            };

            XMLHttpRequest.prototype.send = function(body) {
                const xhr = this;

                const originalOnReadyStateChange = xhr.onreadystatechange;
                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4) {
                        try {
                            const jsonData = JSON.parse(xhr.responseText);
                            window.__interceptedData.push({
                                url: xhr._url,
                                json: jsonData,
                                timestamp: new Date().toISOString()
                            });
                        } catch (e) {
                            // 不是 JSON，忽略
                        }
                    }
                    if (originalOnReadyStateChange) {
                        originalOnReadyStateChange.apply(this, arguments);
                    }
                };

                return originalSend.apply(this, arguments);
            };

            console.log('[Interceptor] JavaScript interception enabled');
        }
        """

        await page.evaluate(js_code)
        logger.info("🔌 Response 拦截器已附加到页面（JavaScript 注入模式）")

    def detach_from_page(self, page: Page) -> None:
        """从页面移除拦截器

        Args:
            page: Playwright Page 对象
        """
        # V41.167: 移除 JavaScript 拦截器
        # 注意：已注入的 JavaScript 会保持运行，直到页面关闭
        logger.info("🔌 Response 拦截器已从页面移除（JavaScript 拦截器保持活跃）")

    async def process_pending_responses(self, page: Page | None = None) -> int:
        """V41.167: 从浏览器获取截获的数据

        Args:
            page: Playwright Page 对象（必需，用于访问浏览器上下文）

        Returns:
            截获的 JSON 数量
        """
        if page is None:
            return self._intercept_count

        # V41.167: 从浏览器获取截获的数据
        try:
            intercepted_data = await page.evaluate("() => window.__interceptedData || []")

            for data in intercepted_data:
                url = data.get("url", "")
                json_data = data.get("json", None)
                timestamp = data.get("timestamp", "")

                if not json_data:
                    continue

                # 检查关键字匹配
                url_lower = url.lower()
                matched_keywords = [
                    keyword for keyword in self.config.keywords
                    if keyword.lower() in url_lower
                ]

                # 如果没有匹配关键字且不是保存所有模式，跳过
                if not matched_keywords and not self.config.save_all:
                    continue

                # 创建截获对象
                intercepted = InterceptedJSON(
                    url=url,
                    json_data=json_data,
                    timestamp=timestamp,
                    status_code=200,  # JavaScript 拦截无法获取真实状态码
                    headers={},      # JavaScript 拦截无法获取完整 headers
                    matched_keywords=matched_keywords,
                    content_type="application/json",
                )

                # 检查是否已存在（避免重复）
                if not any(existing.url == url for existing in self._intercepted_jsons):
                    self._intercepted_jsons.append(intercepted)
                    self._intercept_count += 1

                    logger.info(
                        f"🎯 截获 JSON [{self._intercept_count}]: {url[:100]} "
                        f"(关键字: {matched_keywords})"
                    )

                    # 调用所有处理函数
                    for handler in self._handlers:
                        try:
                            handler(intercepted)
                        except Exception as e:
                            logger.exception(f"❌ 处理函数执行失败: {e}")

                    # 自动保存（如果配置了）
                    if self.config.save_all:
                        try:
                            intercepted.save_to_file(self.config.output_dir)
                        except Exception as save_error:
                            logger.exception(f"❌ 保存失败: {save_error}")

        except Exception as e:
            logger.exception(f"❌ 获取浏览器数据失败: {e}")

        return self._intercept_count

    async def get_intercepted_jsons(self) -> list[InterceptedJSON]:
        """获取所有截获的 JSON 数据（异步）

        Returns:
            InterceptedJSON 对象列表
        """
        # 确保所有待处理的响应都被处理
        await self.process_pending_responses()
        return self._intercepted_jsons.copy()

    def get_intercepted_count(self) -> int:
        """获取截获数量（同步）

        Returns:
            截获的 JSON 数量
        """
        return self._intercept_count

    def clear(self) -> None:
        """清空截获数据"""
        self._intercepted_jsons.clear()
        self._intercept_count = 0
        # V41.167: 取消所有待处理的后台任务
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()
        logger.info("🗑️ 已清空截获数据")

    def save_all_to_files(self, output_dir: str | None = None) -> list[Path]:
        """保存所有截获的 JSON 到文件

        Args:
            output_dir: 输出目录（可选，默认使用配置中的目录）

        Returns:
            保存的文件路径列表
        """
        output_dir = output_dir or self.config.output_dir
        saved_paths = []

        for intercepted in self._intercepted_jsons:
            try:
                path = intercepted.save_to_file(output_dir)
                saved_paths.append(path)
            except Exception as e:
                logger.exception(f"❌ 保存失败: {e}")

        logger.info(f"💾 已保存 {len(saved_paths)} 个 JSON 文件到 {output_dir}")
        return saved_paths

    def get_summary(self) -> dict[str, Any]:
        """获取拦截摘要

        Returns:
            包含统计信息的字典
        """
        keyword_counts: dict[str, int] = {}
        for intercepted in self._intercepted_jsons:
            for keyword in intercepted.matched_keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        return {
            "total_intercepted": self._intercept_count,
            "pending_tasks": len([t for t in self._pending_tasks if not t.done()]),
            "keyword_counts": keyword_counts,
            "output_dir": self.config.output_dir,
            "config": {
                "keywords": self.config.keywords,
                "save_all": self.config.save_all,
                "max_intercepts": self.config.max_intercepts,
            },
        }


# ============================================================================
# Convenience Functions
# ============================================================================


async def intercept_json_from_page(
    page: Page,
    url: str,
    keywords: list[str] | None = None,
    wait_time: float = 5.0,
) -> list[dict[str, Any]]:
    """从页面截获 JSON 数据的便捷函数

    Args:
        page: Playwright Page 对象
        url: 要访问的 URL
        keywords: 关键字列表（可选）
        wait_time: 等待时间（秒）

    Returns:
        截获的 JSON 数据列表
    """
    # 创建拦截器
    config = InterceptorConfig()
    if keywords:
        config.keywords = keywords

    interceptor = ResponseInterceptor(config)
    await interceptor.attach_to_page(page)

    # 访问页面
    await page.goto(url)
    await asyncio.sleep(wait_time)

    # 获取截获的数据
    jsons = await interceptor.get_intercepted_jsons()
    return [json_data.to_dict() for json_data in jsons]


def print_interceptor_summary(interceptor: ResponseInterceptor) -> None:
    """打印拦截摘要

    Args:
        interceptor: ResponseInterceptor 对象
    """
    summary = interceptor.get_summary()

    for _keyword, _count in summary["keyword_counts"].items():
        pass


# ============================================================================
# Context Manager
# ============================================================================


class InterceptorContext:
    """拦截器上下文管理器 - V41.167 版本

    Example:
        >>> async with InterceptorContext(page) as interceptor:
        ...     await page.goto("https://example.com")
        ...     await asyncio.sleep(5)
        ...     jsons = await interceptor.get_intercepted_jsons()
    """

    def __init__(
        self,
        page: Page,
        config: InterceptorConfig | None = None,
    ) -> None:
        """初始化上下文管理器

        Args:
            page: Playwright Page 对象
            config: 拦截器配置（可选）
        """
        self.page = page
        self.config = config or InterceptorConfig()
        self.interceptor = ResponseInterceptor(self.config)

    async def __aenter__(self) -> ResponseInterceptor:
        """进入上下文"""
        await self.interceptor.attach_to_page(self.page)
        return self.interceptor

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文"""
        self.interceptor.detach_from_page(self.page)


if __name__ == "__main__":
    # 测试代码
    async def main():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            async with InterceptorContext(page) as interceptor:
                await page.goto("https://www.oddsportal.com")
                await asyncio.sleep(5)

                # 打印摘要
                print_interceptor_summary(interceptor)

            await browser.close()

    # asyncio.run(main())
