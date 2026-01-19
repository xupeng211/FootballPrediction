#!/usr/bin/env python3
"""V41.164 Response Interceptor - JSON 截胡器.

专门用于拦截并提取 OddsPortal 等网站的纯金 JSON 数据。
不使用 BeautifulSoup 解析 HTML，直接在 Playwright Response 层截获数据。

核心功能:
    - Response 拦截器: 拦截所有网络请求的响应
    - JSON 提取器: 从响应中提取 JSON 数据
    - 关键字匹配: 识别 `match/1-1-` 等关键字
    - 数据验证: 验证 JSON 完整性和有效性
    - 批量存储: 支持批量存储截获的 JSON 数据

Author: 高级反爬虫对抗专家
Version: V41.164 "泰坦补丁"
Date: 2026-01-18
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

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

    # 关键字列表
    keywords: list[str] = field(default_factory=lambda: [
        "match/1-1-",
        "match/1-X-",
        "match/X-1-",
        "match/2-1-",
        "/football/",
        "oddsportal.com/football",
        "pinnacle",
        "bet365",
    ])

    # Content-Type 白名单
    content_type_whitelist: list[str] = field(default_factory=lambda: [
        "application/json",
        "application/ld+json",
        "text/plain",
        "text/html",
    ])

    # URL 白名单
    url_whitelist: list[str] = field(default_factory=lambda: [
        "oddsportal.com",
        "api.",
    ])

    # 是否保存所有截获的数据
    save_all: bool = False

    # 输出目录
    output_dir: str = "storage/intercepted_json"

    # 最大截获数量（防止内存溢出）
    max_intercepts: int = 10000


# ============================================================================
# Main Interceptor Class
# ============================================================================


class ResponseInterceptor:
    """Response 拦截器 - JSON 截胡器

    拦截 Playwright 页面的所有网络响应，提取包含特定关键字的 JSON 数据。

    Example:
        >>> interceptor = ResponseInterceptor()
        >>> await interceptor.attach_to_page(page)
        >>> await page.goto("https://example.com")
        >>> # 访问截获的数据
        >>> for json_data in interceptor.get_intercepted_jsons():
        ...     print(json_data.url)
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
        # V41.166: 待处理响应列表（在同步回调中收集，稍后异步处理）
        self._pending_responses: list[Response] = []

        # 创建输出目录
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    def add_handler(self, handler: Callable[[InterceptedJSON], None]) -> None:
        """添加数据处理函数

        当截获到 JSON 数据时，会调用所有注册的处理函数。

        Args:
            handler: 处理函数，接收 InterceptedJSON 对象
        """
        self._handlers.append(handler)
        logger.info(f"📝 已添加处理函数: {handler.__name__}")

    def _response_handler(self, response: Response) -> None:
        """处理响应（内部函数）- V41.166 修复版

        重要：这是同步回调函数，被 page.on("response") 调用
        所有异步操作都被移除，改为在页面关闭后批量处理

        Args:
            response: Playwright Response 对象
        """
        try:
            # 检查是否达到最大截获数量
            if self._intercept_count >= self.config.max_intercepts:
                return

            # 获取 URL
            url = response.url
            url_lower = url.lower()

            # 检查关键字匹配
            matched_keywords = [
                keyword for keyword in self.config.keywords
                if keyword.lower() in url_lower
            ]

            # 如果没有匹配关键字且不是保存所有模式，跳过
            if not matched_keywords and not self.config.save_all:
                return

            # 检查 URL 白名单（如果配置了）
            if self.config.url_whitelist:
                if not any(white in url_lower for white in self.config.url_whitelist):
                    return

            # V41.166: 修复 - header_value 是同步方法，不需要 await
            content_type = response.header_value("content-type") or ""

            # 检查 Content-Type 白名单
            if self.config.content_type_whitelist:
                if not any(
                    allowed in content_type.lower()
                    for allowed in self.config.content_type_whitelist
                ):
                    return

            # V41.166: 同步获取响应体（使用 all_raw_headers 或缓存响应）
            # 注意：response.body() 是异步的，不能在同步回调中使用
            # 解决方案：将响应对象存储起来，稍后批量处理
            self._pending_responses.append(response)

        except Exception as e:
            logger.debug(f"⚠️ 响应处理异常: {e}")

    async def attach_to_page(self, page: Page) -> None:
        """附加到 Playwright 页面

        Args:
            page: Playwright Page 对象
        """
        page.on("response", self._response_handler)
        logger.info("🔌 Response 拦截器已附加到页面")

    async def process_pending_responses(self) -> int:
        """V41.166: 批量处理待处理的响应（异步）

        在页面操作完成后调用此方法来处理所有收集到的响应。

        Returns:
            处理的响应数量
        """
        processed = 0

        for response in self._pending_responses:
            try:
                # 检查是否达到最大截获数量
                if self._intercept_count >= self.config.max_intercepts:
                    break

                # 获取 URL 和关键字匹配
                url = response.url
                url_lower = url.lower()

                matched_keywords = [
                    keyword for keyword in self.config.keywords
                    if keyword.lower() in url_lower
                ]

                # 如果没有匹配关键字且不是保存所有模式，跳过
                if not matched_keywords and not self.config.save_all:
                    continue

                # 获取 Content-Type（同步方法）
                content_type = response.header_value("content-type") or ""

                # 检查 Content-Type 白名单
                if self.config.content_type_whitelist:
                    if not any(
                        allowed in content_type.lower()
                        for allowed in self.config.content_type_whitelist
                    ):
                        continue

                # 异步获取响应体
                try:
                    body = await response.body()
                    body_text = body.decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.debug(f"⚠️ 无法获取响应体: {e}")
                    continue

                # 尝试解析 JSON
                try:
                    json_data = json.loads(body_text)
                except json.JSONDecodeError:
                    # 不是 JSON，跳过
                    continue

                # 创建截获对象
                intercepted = InterceptedJSON(
                    url=url,
                    json_data=json_data,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status_code=response.status,
                    headers=dict(response.headers),
                    matched_keywords=matched_keywords,
                    content_type=content_type,
                )

                # 添加到列表
                self._intercepted_jsons.append(intercepted)
                self._intercept_count += 1
                processed += 1

                # 记录日志
                logger.info(
                    f"🎯 截获 JSON [{self._intercept_count}]: {url[:100]} "
                    f"(关键字: {matched_keywords}, 大小: {len(body_text)} bytes)"
                )

                # 调用所有处理函数
                for handler in self._handlers:
                    try:
                        handler(intercepted)
                    except Exception as e:
                        logger.error(f"❌ 处理函数执行失败: {e}")

                # 自动保存（如果配置了）
                if self.config.save_all:
                    intercepted.save_to_file(self.config.output_dir)

            except Exception as e:
                logger.debug(f"⚠️ 处理响应异常: {e}")
                continue

        # 清空待处理列表
        self._pending_responses.clear()

        return processed

    def detach_from_page(self, page: Page) -> None:
        """从页面移除拦截器

        Args:
            page: Playwright Page 对象
        """
        page.remove_listener("response", self._response_handler)
        logger.info("🔌 Response 拦截器已从页面移除")

    def get_intercepted_jsons(self) -> list[InterceptedJSON]:
        """获取所有截获的 JSON 数据

        Returns:
            InterceptedJSON 对象列表
        """
        return self._intercepted_jsons.copy()

    def get_intercepted_count(self) -> int:
        """获取截获数量

        Returns:
            截获的 JSON 数量
        """
        return self._intercept_count

    def clear(self) -> None:
        """清空截获数据"""
        self._intercepted_jsons.clear()
        self._intercept_count = 0
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
                logger.error(f"❌ 保存失败: {e}")

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
) -> list[InterceptedJSON]:
    """从页面截获 JSON 数据的便捷函数

    Args:
        page: Playwright Page 对象
        url: 要访问的 URL
        keywords: 关键字列表（可选）
        wait_time: 等待时间（秒）

    Returns:
        截获的 JSON 数据列表

    Example:
        >>> from playwright.async_api import async_playwright
        >>> async with async_playwright() as p:
        ...     browser = await p.chromium.launch()
        ...     page = await browser.new_page()
        ...     jsons = await intercept_json_from_page(page, "https://example.com")
        ...     print(f"截获了 {len(jsons)} 个 JSON")
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

    # 返回截获的数据
    return interceptor.get_intercepted_jsons()


def print_interceptor_summary(interceptor: ResponseInterceptor) -> None:
    """打印拦截摘要

    Args:
        interceptor: ResponseInterceptor 对象
    """
    summary = interceptor.get_summary()

    print("\n" + "=" * 60)
    print("📊 Response Interceptor 摘要")
    print("=" * 60)
    print(f"总截获数量: {summary['total_intercepted']}")
    print(f"\n关键字统计:")
    for keyword, count in summary['keyword_counts'].items():
        print(f"  - {keyword}: {count}")
    print(f"\n输出目录: {summary['output_dir']}")
    print("=" * 60 + "\n")


# ============================================================================
# Context Manager
# ============================================================================


class InterceptorContext:
    """拦截器上下文管理器

    Example:
        >>> async with InterceptorContext(page) as interceptor:
        ...     await page.goto("https://example.com")
        ...     await asyncio.sleep(5)
        ...     # 自动获取截获的数据
        ...     jsons = interceptor.get_intercepted_jsons()
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
    import asyncio
    from playwright.async_api import async_playwright

    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 使用上下文管理器
            async with InterceptorContext(page) as interceptor:
                await page.goto("https://www.oddsportal.com")
                await asyncio.sleep(5)

                # 打印摘要
                print_interceptor_summary(interceptor)

            await browser.close()

    # asyncio.run(main())
