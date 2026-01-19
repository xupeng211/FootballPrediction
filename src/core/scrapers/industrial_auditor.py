"""
V41.232 Industrial Auditor - 生产级内容审计器（防弹级增强版）
======================================================================

核心功能：
    - 基于矩阵内容提取与序列对齐
    - 三位一组切片算法（Triplets Slicing）
    - 生产级异常处理与降级策略
    - 标准化字段输出

V41.231 网络韧性升级：
    - 导航策略降级：networkidle → domcontentloaded + 5s 硬性等待
    - 超时参数扩展：90s 全局超时
    - 自动重试机制：最多 3 次自动重试
    - 代理配置透传：确保 HTTP_PROXY 正确传递

V41.232 防弹级加固：
    - 资源暴力回收：强制关闭所有 Page/Context 防止内存堆积
    - 视觉失效存证：anchors=0 时自动截图
    - 全链路稳定性：确保重试循环中零泄漏

架构说明：
    - Initial_Price: 初始价格（后 3 位）
    - Closing_Price: 当前价格（前 3 位）
    - Movement_History: 中间过渡序列

Usage:
    from src.core.scrapers.industrial_auditor import IndustrialAuditor, AuditorConfig

    config = AuditorConfig(target_url="https://example.com")
    auditor = IndustrialAuditor(config)
    result = await auditor.audit()

Author: V41.232 Engineering Team
Date: 2026-01-19
Version: V41.232 "Bulletproof Finalization"
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.config_unified import get_config

logger = logging.getLogger("IndustrialAuditor")


# =============================================================================
# 数据模型 (Data Models)
# =============================================================================


class MatrixQuality(str, Enum):
    """矩阵质量评级"""
    EXCELLENT = "excellent"  # 完整 3+3 结构
    GOOD = "good"  # 部分降级但可用
    DEGRADED = "degraded"  # 非标准结构已降级
    INSUFFICIENT = "insufficient"  # 数据不足


@dataclass(frozen=True)
class PriceVector:
    """价格向量 - 标准化输出结构"""
    initial: list[float]  # Initial_Price: 初始价格（后 3 位）
    closing: list[float]  # Closing_Price: 当前价格（前 3 位）
    movement: list[float]  # Movement_History: 中间过渡序列
    quality: MatrixQuality  # 质量评级
    deviation_pct: float  # 百分比偏差

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（标准化字段名）"""
        return {
            "Initial_Price": self.initial,
            "Closing_Price": self.closing,
            "Movement_History": self.movement,
            "Quality_Rating": self.quality.value,
            "Deviation_Percentage": round(self.deviation_pct, 4),
        }


@dataclass
class ExtractionResult:
    """提取结果"""
    timestamp: str
    target_url: str
    entities_extracted: int
    entities: list[PriceVector] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "target_url": self.target_url,
            "entities_extracted": self.entities_extracted,
            "entities": [e.to_dict() for e in self.entities],
            "metadata": self.metadata,
        }


@dataclass
class AuditorConfig:
    """审计器配置"""
    target_url: str
    target_patterns: list[str] = field(default_factory=lambda: ["Opening", "Closing", "Movement"])
    consent_cookie_name: str = "consent"
    consent_cookie_value: str = "accepted"
    scroll_iterations: int = 5
    scroll_delay_ms: int = 800
    network_idle_timeout: int = 30000
    headless: bool = True
    proxy_port: int = 7892

    # V41.230 新增配置
    min_value_threshold: float = 1.01  # 最小数值阈值
    max_value_threshold: float = 50.00  # 最大数值阈值
    enable_degraded_mode: bool = True  # 启用降级模式
    container_width_ratio: float = 0.3  # 容器宽度阈值比例

    # V41.231 网络韧性配置
    navigation_timeout: int = 90000  # 导航超时（90s）
    max_retries: int = 3  # 最大重试次数
    wait_after_load: int = 5000  # 加载后硬性等待（5s）
    wait_strategy: str = "domcontentloaded"  # 导航等待策略

    # V41.235 配置解耦 - 输出目录
    output_dir: str = "logs"  # 审计结果输出目录


# =============================================================================
# 核心算法 (Core Algorithms)
# =============================================================================


class SequenceProcessor:
    """V41.230 序列处理器 - 三位一组切片算法"""

    # 标准三元组大小
    TRIPLET_SIZE = 3

    @staticmethod
    def process(values: list[float], enable_degraded: bool = True) -> PriceVector:
        """
        处理数值序列，提取价格向量

        标准逻辑：
        - [0:3] → Closing_Price（当前状态）
        - [-3:] → Initial_Price（初始状态）
        - 中间序列 → Movement_History

        降级处理：
        - 非标准长度序列的智能降级
        - 不足 3 位时的部分提取策略

        Args:
            values: 输入数值序列
            enable_degraded: 是否启用降级模式

        Returns:
            PriceVector: 标准化价格向量
        """
        if not values:
            return PriceVector(
                initial=[], closing=[], movement=[],
                quality=MatrixQuality.INSUFFICIENT, deviation_pct=0.0
            )

        total = len(values)

        # 标准完整结构（≥6 位）
        if total >= 6:
            return SequenceProcessor._process_standard(values)

        # 降级处理（3-5 位）
        if enable_degraded and total >= 3:
            return SequenceProcessor._process_degraded(values)

        # 数据不足
        return PriceVector(
            initial=[], closing=[], movement=[],
            quality=MatrixQuality.INSUFFICIENT, deviation_pct=0.0
        )

    @staticmethod
    def _process_standard(values: list[float]) -> PriceVector:
        """标准完整结构处理（≥6 位）"""
        closing = values[:3]  # [0:3]
        initial = values[-3:]  # [-3:]
        movement = values[3:-3]  # 中间序列

        deviation = SequenceProcessor._calculate_deviation(closing, initial)

        return PriceVector(
            initial=initial,
            closing=closing,
            movement=movement,
            quality=MatrixQuality.EXCELLENT,
            deviation_pct=deviation,
        )

    @staticmethod
    def _process_degraded(values: list[float]) -> PriceVector:
        """
        降级模式处理（3-5 位）

        降级策略：
        - 5 位: closing=[:2], initial=[-2:], movement=[2:-2]
        - 4 位: closing=[:2], initial=[-2:], movement=[2:-2]
        - 3 位: closing=[:1], initial=[-1:], movement=[1:-1]
        """
        total = len(values)

        if total == 5:
            closing = values[:2]
            initial = values[-2:]
            movement = values[2:-2]  # [2:3] = 1 位
        elif total == 4:
            closing = values[:2]
            initial = values[-2:]
            movement = values[2:-2]  # [2:2] = 空
        else:  # total == 3
            closing = values[:1]
            initial = values[-1:]
            movement = values[1:-1]  # [1:2] = 1 位

        deviation = SequenceProcessor._calculate_deviation(closing, initial)

        return PriceVector(
            initial=initial,
            closing=closing,
            movement=movement,
            quality=MatrixQuality.DEGRADED,
            deviation_pct=deviation,
        )

    @staticmethod
    def _calculate_deviation(current: list[float], initial: list[float]) -> float:
        """
        计算百分比偏差

        算法：
        1. 对应位置相减取绝对差值
        2. 计算相对于初始值的百分比偏差
        3. 返回平均偏差百分比
        """
        if not current or not initial:
            return 0.0

        # 确保长度一致（以较短者为准）
        min_len = min(len(current), len(initial))
        if min_len == 0:
            return 0.0

        deviations = []
        for i in range(min_len):
            c_val = current[i]
            i_val = initial[i]
            if i_val != 0:
                dev = abs((c_val - i_val) / i_val) * 100
                deviations.append(dev)

        return sum(deviations) / len(deviations) if deviations else 0.0


# =============================================================================
# 工业级审计器 (Industrial Auditor)
# =============================================================================


class IndustrialAuditor:
    """
    V41.230 工业级审计器

    核心特性：
    - 生产级异常处理
    - 标准化输出字段
    - 降级模式支持
    - 统一日志格式
    """

    # 数值正则模式：匹配 X.XX 格式的浮点数
    FLOAT_PATTERN = re.compile(r"\b(\d+\.\d{2,3})\b")

    def __init__(self, config: AuditorConfig):
        self.config = config
        self.unified_config = get_config()

        # 浏览器实例
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        # 结果存储
        self.result: ExtractionResult | None = None

        # 页面宽度统计
        self.page_main_width: int = 0

    async def initialize(self) -> None:
        """
        初始化浏览器环境 - V41.231 网络韧性增强

        增强：
        - 显式设置 90s 超时
        - 代理配置透传验证
        """
        logger.debug("Initializing browser environment")

        # V41.231: 代理配置透传
        proxy_config = {
            "server": f"http://{self.unified_config.proxy.wsl2_bridge_host}:{self.config.proxy_port}"
        }
        logger.debug(f"Proxy configuration: {proxy_config['server']}")

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            proxy=proxy_config,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # V41.231: 显式设置超时配置
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="Europe/London",
            # V41.231: 全局超时配置（90s）
            timeout=self.config.navigation_timeout,
        )

        self.page = await self.context.new_page()

        # V41.231: 设置页面默认超时
        self.page.set_default_timeout(self.config.navigation_timeout)

        logger.debug("Browser initialization complete")

    async def inject_consent_cookie(self) -> None:
        """注入 consent Cookie"""
        if not self.context:
            raise RuntimeError("Browser context not initialized")

        await self.context.add_cookies([{
            "name": self.config.consent_cookie_name,
            "value": self.config.consent_cookie_value,
            "domain": self._extract_domain(self.config.target_url),
            "path": "/",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        }])

        logger.debug(f"Consent cookie injected: {self.config.consent_cookie_name}")

    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or parsed.path

    async def perform_lazy_scroll(self) -> None:
        """执行懒加载滚动"""
        if not self.page:
            raise RuntimeError("Page not initialized")

        for _ in range(self.config.scroll_iterations):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(self.config.scroll_delay_ms / 1000)
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(self.config.scroll_delay_ms / 2000)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(self.config.scroll_delay_ms / 2000)

        logger.debug("Lazy scroll complete")

    async def audit(self) -> ExtractionResult:
        """
        执行完整审计流程 - V41.232 防弹级增强

        V41.231 网络韧性：
        - 自动重试机制（最多 3 次）
        - 导航策略降级（networkidle → domcontentloaded）
        - 5 秒硬性水合等待

        V41.232 防弹级加固：
        - 视觉失效存证：entities=0 时自动截图
        - 资源暴力回收：确保重试循环中零泄漏
        """
        logger.info("Starting industrial audit process (V41.232)")

        # V41.231: 重试计数器
        last_error = None

        try:
            for attempt in range(1, self.config.max_retries + 1):
                try:
                    print(f"Attempt [{attempt}]: Navigating...")

                    await self.initialize()
                    await self.inject_consent_cookie()

                    # V41.231: 导航策略降级
                    logger.info(f"Navigating to target (strategy: {self.config.wait_strategy})")
                    await self.page.goto(
                        self.config.target_url,
                        wait_until=self.config.wait_strategy,
                        timeout=self.config.navigation_timeout,
                    )

                    # V41.231: 5 秒硬性水合等待
                    await self.page.wait_for_timeout(self.config.wait_after_load)

                    print("Network Delay Handled: Yes")

                    await self.perform_lazy_scroll()

                    # 提取所有实体
                    all_vectors = await self._extract_entities()

                    # V41.232: 视觉失效存证
                    if len(all_vectors) == 0:
                        logger.warning("No entities extracted - capturing forensic screenshot")
                        await self._capture_failure_screenshot(attempt)

                    self.result = ExtractionResult(
                        timestamp=datetime.now().isoformat(),
                        target_url=self.config.target_url,
                        entities_extracted=len(all_vectors),
                        entities=all_vectors,
                        metadata={
                            "page_width": self.page_main_width,
                            "config": {
                                "patterns": self.config.target_patterns,
                                "degraded_mode": self.config.enable_degraded_mode,
                                "navigation_strategy": self.config.wait_strategy,
                                "attempt": attempt,
                            },
                        },
                    )

                    logger.info(f"Audit complete: {len(all_vectors)} entities extracted")
                    return self.result

                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt [{attempt}] failed: {e}")

                    # V41.232: 异常时也尝试截图
                    try:
                        if self.page and not self.page.is_closed():
                            await self._capture_failure_screenshot(attempt, error=str(e))
                    except Exception:
                        pass

                    # 清理资源准备重试
                    try:
                        await self.cleanup()
                    except Exception:
                        pass

                    # 如果还有重试机会，等待后继续
                    if attempt < self.config.max_retries:
                        wait_time = attempt * 2  # 递增等待：2s, 4s, 6s
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # 所有重试都失败
                        logger.error(f"All {self.config.max_retries} attempts failed")
                        raise RuntimeError(f"Audit failed after {self.config.max_retries} attempts: {e}") from e

        finally:
            await self.cleanup()

    async def _capture_failure_screenshot(self, attempt: int, error: str | None = None) -> None:
        """
        V41.232 视觉失效存证 - 自动截图（V41.235: 使用配置化目录）

        当 entities_extracted == 0 或发生异常时触发
        """
        if not self.page or self.page.is_closed():
            logger.debug("Cannot capture screenshot: page not available")
            return

        try:
            log_dir = Path(self.config.output_dir)
            log_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"last_extraction_failure_{timestamp}_attempt{attempt}.png"
            screenshot_path = log_dir / filename

            await self.page.screenshot(path=str(screenshot_path), full_page=True)

            logger.info(f"Forensic screenshot saved: {screenshot_path}")

        except Exception as e:
            logger.debug(f"Failed to capture screenshot: {e}")

    async def _extract_entities(self) -> list[PriceVector]:
        """提取所有实体价格向量"""
        self.page_main_width = await self._get_page_width()
        logger.debug(f"Page width: {self.page_main_width}px")

        all_vectors = []
        anchor_index = 0

        for pattern in self.config.target_patterns:
            logger.debug(f"Searching pattern: {pattern}")

            try:
                elements = await self.page.get_by_text(pattern, exact=False).all()

                for element in elements:
                    if not await element.is_visible():
                        continue

                    # 容器回溯提取
                    container_info = await self._backtrack_container(element)
                    if not container_info:
                        continue

                    # 提取数值
                    values = self._extract_values(container_info["innerText"])
                    if not values:
                        continue

                    # 序列处理
                    vector = SequenceProcessor.process(
                        values,
                        enable_degraded=self.config.enable_degraded_mode
                    )

                    if vector.quality != MatrixQuality.INSUFFICIENT:
                        all_vectors.append(vector)
                        anchor_index += 1

            except Exception as e:
                logger.debug(f"Error processing pattern '{pattern}': {e}")
                continue

        return all_vectors

    async def _get_page_width(self) -> int:
        """获取页面宽度"""
        if not self.page:
            return 0

        width = await self.page.evaluate("""
            () => {
                const body = document.body;
                const html = document.documentElement;
                return Math.max(
                    body?.scrollWidth || 0,
                    html?.scrollWidth || 0,
                    window.innerWidth || 0
                );
            }
        """)
        return width

    async def _backtrack_container(self, element) -> dict[str, Any] | None:
        """容器回溯算法"""
        if not self.page:
            return None

        container_info = await element.evaluate("""
            (element) => {
                let current = element;
                let bestContainer = null;
                let bestWidth = 0;
                const maxIterations = 15;

                for (let i = 0; i < maxIterations && current; i++) {
                    const rect = current.getBoundingClientRect();
                    const width = rect.width;

                    if (width > bestWidth && width > 100) {
                        bestContainer = current;
                        bestWidth = width;
                    }

                    if (current.tagName === 'BODY' || current.tagName === 'HTML') {
                        break;
                    }
                    current = current.parentElement;
                }

                if (!bestContainer) return null;

                return {
                    tagName: bestContainer.tagName,
                    width: Math.round(bestWidth),
                    innerText: bestContainer.innerText || bestContainer.textContent || ''
                };
            }
        """)

        if not container_info:
            return None

        # 宽度阈值检查
        min_width = int(self.page_main_width * self.config.container_width_ratio)
        if container_info["width"] < min_width:
            logger.debug(f"Container width {container_info['width']} below threshold {min_width}")
            return None

        return container_info

    def _extract_values(self, text: str) -> list[float]:
        """从文本提取数值"""
        matches = self.FLOAT_PATTERN.findall(text)
        extracted = []

        for m in matches:
            try:
                val = float(m)
                if self.config.min_value_threshold <= val <= self.config.max_value_threshold:
                    extracted.append(val)
            except ValueError:
                continue

        return extracted

    async def cleanup(self) -> None:
        """
        V41.232 资源暴力回收 - 防止内存堆积

        增强：
        - 强制关闭所有 Page（即使 is_closed 为 False）
        - 强制关闭所有 Context
        - 强制关闭 Browser
        - 强制停止 Playwright
        - 多重异常容错，确保每个步骤独立执行
        """
        # V41.232: 资源回收计数器
        cleanup_count = 0
        errors = []

        # 步骤 1: 强制关闭 Page
        if self.page:
            try:
                if not self.page.is_closed():
                    await self.page.close()
                    cleanup_count += 1
                    logger.debug("Page closed successfully")
            except Exception as e:
                errors.append(f"Page cleanup: {e}")
                # V41.232: 尝试暴力关闭
                try:
                    self.page = None
                except Exception:
                    pass

        # 步骤 2: 强制关闭 Context
        if self.context:
            try:
                await self.context.close()
                cleanup_count += 1
                logger.debug("Context closed successfully")
            except Exception as e:
                errors.append(f"Context cleanup: {e}")
                try:
                    self.context = None
                except Exception:
                    pass

        # 步骤 3: 强制关闭 Browser
        if self.browser:
            try:
                if self.browser.is_connected():
                    await self.browser.close()
                    cleanup_count += 1
                    logger.debug("Browser closed successfully")
            except Exception as e:
                errors.append(f"Browser cleanup: {e}")
                try:
                    self.browser = None
                except Exception:
                    pass

        # 步骤 4: 强制停止 Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
                cleanup_count += 1
                logger.debug("Playwright stopped successfully")
            except Exception as e:
                errors.append(f"Playwright cleanup: {e}")
                try:
                    self.playwright = None
                except Exception:
                    pass

        # V41.232: 清理摘要日志
        if cleanup_count > 0:
            logger.debug(f"Cleanup complete: {cleanup_count} resources released")
        if errors:
            logger.debug(f"Cleanup errors: {'; '.join(errors)}")

    def save_result(self, output_path: str | None = None) -> Path:
        """保存审计结果（V41.235: 使用配置化输出目录）"""
        if not self.result:
            raise RuntimeError("No result to save")

        if output_path is None:
            output_path = f"{self.config.output_dir}/industrial_audit_result.json"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        import json
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Result saved: {output_file}")
        return output_file
