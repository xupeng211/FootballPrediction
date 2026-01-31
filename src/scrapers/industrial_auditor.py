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

V41.283 异步修复：
    - 修复 Modal Smasher 异步调用问题
    - 正确使用 await add_init_script()

架构说明：
    - Initial_Price: 初始价格（后 3 位）
    - Closing_Price: 当前价格（前 3 位）
    - Movement_History: 中间过渡序列

Usage:
    from src.scrapers.industrial_auditor import IndustrialAuditor, AuditorConfig

    config = AuditorConfig(target_url="https://example.com")
    auditor = IndustrialAuditor(config)
    result = await auditor.audit()

Author: V41.232 Engineering Team
Date: 2026-01-19
Version: V41.283 "The Final Launchpad - Async Fix"
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from pathlib import Path
import re
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

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

    @property
    def values(self) -> list[float]:
        """所有价格值的合并列表（V41.268 修复）"""
        return self.initial + self.closing + self.movement

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
    raw_html: str = ""  # V41.268: 原始 HTML 源码（用于取证）

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
    min_value_threshold: float = 1.01  # V41.272: 调优至 1.01，依赖物理约束（CHECK）
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
        """
        标准完整结构处理（≥6 位）

        V41.257 修复：
            - 添加异常值检测 (如固定值 8.75)
            - 验证赔率值合理性 (1.01 - 1000.0)
            - 检测列顺序一致性
        """
        # V41.257: 提取候选值
        closing_candidate = values[:3]  # [0:3]
        initial_candidate = values[-3:]  # [-3:]
        movement = values[3:-3]  # 中间序列

        # V41.257: 异常值检测
        KNOWN_ANOMALIES = [8.75]  # 已知异常值列表

        # 检查 closing 是否包含异常值
        if any(abs(v - anomaly) < 0.01 for v in closing_candidate for anomaly in KNOWN_ANOMALIES):
            logger.warning(f"V41.257: Anomaly detected in closing values: {closing_candidate}")
            # 尝试从 movement 寻找替代值
            if len(movement) >= 3:
                # 使用 movement 的最后 3 个元素作为 closing
                closing_candidate = movement[-3:]
                logger.info(f"V41.257: Using movement[-3:] as closing: {closing_candidate}")

        # 验证赔率值合理性 (1.01 - 1000.0)
        def validate_odds(odds_list: list[float]) -> bool:
            return all(1.01 <= v <= 1000.0 for v in odds_list if v > 0)

        if not validate_odds(closing_candidate):
            logger.warning(f"V41.257: Invalid closing odds: {closing_candidate}")
            return PriceVector(
                initial=[], closing=[], movement=[],
                quality=MatrixQuality.INSUFFICIENT, deviation_pct=0.0
            )

        if not validate_odds(initial_candidate):
            logger.warning(f"V41.257: Invalid initial odds: {initial_candidate}")
            return PriceVector(
                initial=[], closing=[], movement=[],
                quality=MatrixQuality.INSUFFICIENT, deviation_pct=0.0
            )

        closing = closing_candidate
        initial = initial_candidate

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
            # 注意：timeout 参数在 new_context() 中不支持，在页面级设置
        )

        self.page = await self.context.new_page()

        # V41.231: 设置页面默认超时
        self.page.set_default_timeout(self.config.navigation_timeout)

        # V41.281: 弹窗粉碎器 - 自动屏蔽常见 Cookie 弹窗和对话框
        await self._inject_anti_modal_script()

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

    async def _inject_anti_modal_script(self) -> None:
        """
        V41.281: 弹窗粉碎器 - 自动屏蔽常见 Cookie 弹窗和对话框

        功能：
        1. 隐藏常见 Cookie 同意横幅
        2. 移除模态遮罩层
        3. 阻止对话框弹出
        4. 确保 1X2 表格永远可见
        """
        if not self.page:
            logger.warning("Page not initialized, skipping anti-modal script injection")
            return

        anti_modal_script = """
        (function() {
            'use strict';

            // 1. 移除常见 Cookie 弹窗选择器
            const modalSelectors = [
                // 通用 Cookie 横幅
                '[id*="cookie"]', '[class*="cookie"]',
                '[id*="consent"]', '[class*="consent"]',
                '[id*="gdpr"]', '[class*="gdpr"]',
                // OddsPortal 特定
                '#onetrust-consent-sdk', '.ot-consent-sdk',
                '.cookie-banner', '.consent-banner',
                // 通用模态框
                '[role="dialog"]', '[role="alertdialog"]',
                '.modal', '.popup', '.overlay',
                '.cookie-consent', '.gdpr-banner'
            ];

            // 2. 移除现有模态框
            function removeModals() {
                modalSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        el.style.display = 'none !important';
                        el.style.visibility = 'hidden !important';
                        el.style.opacity = '0 !important';
                        el.remove();
                    });
                });
            }

            // 3. 阻止新模态框显示
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {  // Element node
                            const element = node;
                            modalSelectors.forEach(selector => {
                                if (element.matches && element.matches(selector)) {
                                    element.style.display = 'none !important';
                                    element.remove();
                                }
                                // 检查子元素
                                const children = element.querySelectorAll?.(selector);
                                children?.forEach(child => {
                                    child.style.display = 'none !important';
                                    child.remove();
                                });
                            });
                        }
                    });
                });
            });

            // 4. 立即执行一次清理
            removeModals();

            // 5. 持续监听 DOM 变化
            observer.observe(document.documentElement, {
                childList: true,
                subtree: true
            });

            // 6. 覆盖常见弹窗 API
            if (window.alert) window.alert = function() {};
            if (window.confirm) window.confirm = function() { return true; };
            if (window.prompt) window.prompt = function() { return null; };

            console.log('[V41.281] Anti-modal script injected and active');
        })();
        """

        await self.page.add_init_script(anti_modal_script)
        logger.debug("V41.281: Anti-modal script injected")

    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or parsed.path

    async def perform_lazy_scroll(self) -> None:
        """
        V41.242 执行激进滚动水合 - 激光手术刀版

        策略：
        1. 暴力滚动到页面底部触发懒加载
        2. 鼠标悬停模拟激活表格
        3. 增加等待时间让 DOM 完全渲染
        4. 分段滚动确保所有表格区域被触发
        """
        if not self.page:
            raise RuntimeError("Page not initialized")

        logger.debug("V41.242 Starting aggressive scroll hydration")

        # 策略 1: 暴力滚动到底部
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.0)  # V41.242: 增加等待时间

        # 策略 2: 分段滚动（触发中间区域的表格）
        for i in range(3):
            scroll_position = (_document_body_scroll_height := await self.page.evaluate(
                "document.body.scrollHeight"
            )) * (i + 1) / 4
            await self.page.evaluate(f"window.scrollTo(0, {scroll_position})")
            await asyncio.sleep(0.5)

        # 策略 3: 悬停激活（模拟用户浏览）
        try:
            # 查找所有表格元素并悬停
            tables = await self.page.locator("table").all()
            for table in tables[:5]:  # 只激活前 5 个表格
                try:
                    if await table.is_visible():
                        await table.hover(timeout=1000)
                        await asyncio.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

        # 策略 4: 回到顶部并最终等待
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1.0)  # V41.242: 最终水合等待

        logger.debug("V41.242 Aggressive scroll hydration complete")

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

        try:
            for attempt in range(1, self.config.max_retries + 1):
                try:

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


                    await self.perform_lazy_scroll()

                    # V41.268: 捕获原始 HTML 用于取证
                    raw_html = ""
                    try:
                        if self.page and not self.page.is_closed():
                            raw_html = await self.page.locator("html").inner_html() or ""
                    except Exception as e:
                        logger.debug(f"Failed to capture raw HTML: {e}")

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
                        raw_html=raw_html,  # V41.268: 添加原始 HTML
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
                    logger.warning(f"Attempt [{attempt}] failed: {e}")

                    # V41.232: 异常时也尝试截图
                    try:
                        if self.page and not self.page.is_closed():
                            await self._capture_failure_screenshot(attempt, error=str(e))
                    except Exception:
                        pass

                    # 清理资源准备重试
                    with contextlib.suppress(Exception):
                        await self.cleanup()

                    # 如果还有重试机会，等待后继续
                    if attempt < self.config.max_retries:
                        wait_time = attempt * 2  # 递增等待：2s, 4s, 6s
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    # 所有重试都失败
                    logger.exception(f"All {self.config.max_retries} attempts failed")
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
        """
        V41.242 提取所有实体价格向量 - 激光手术刀版

        策略层级：
        1. 表格行直接提取（OddsPortal 传统结构）
        2. 文本模式锚点（现代 SPA 结构回退）
        """
        self.page_main_width = await self._get_page_width()
        logger.debug(f"Page width: {self.page_main_width}px")

        all_vectors = []
        anchor_index = 0

        # ================================================================
        # 策略 1: 表格行直接提取（V41.242 新增 - OddsPortal 传统结构）
        # ================================================================
        logger.debug("V41.242 Strategy 1: Table-row extraction")
        try:
            table_vectors = await self._extract_from_tables()
            all_vectors.extend(table_vectors)
            logger.info(f"V41.242 Table strategy extracted {len(table_vectors)} vectors")
        except Exception as e:
            logger.debug(f"V41.242 Table strategy failed: {e}")

        # ================================================================
        # 策略 2: 文本模式锚点（原始逻辑保留）
        # ================================================================
        if len(all_vectors) == 0:  # 仅在表格策略失败时使用
            logger.debug("V41.242 Strategy 2: Pattern-based anchor (fallback)")
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
        else:
            logger.debug("V41.242 Skipping pattern strategy - table extraction succeeded")

        return all_vectors

    async def _extract_from_tables(self) -> list[PriceVector]:
        """
        V41.271 现代 div 布局提取 - 1X2 视觉标签锚定版

        核心改进：
        - 视觉标签锚定：仅提取包含 "Full Time" 或 "1X2" 的表格
        - 物理隔绝亚盘：拒绝所有不属于 1X2 表格区域的赔率数据

        策略：
        1. 定位 1X2/Full Time 表格区域
        2. 仅从该区域提取 div[class*='odd'] 元素
        3. 拒绝其他表格（亚盘、让球等）
        """
        vectors = []

        try:
            # ================================================================
            # V41.271 Step 1: 视觉标签锚定 - 定位 1X2 表格区域
            # ================================================================
            logger.info("V41.271 Step 1: Visual Labeling - Locating 1X2/Full Time table")

            # 尝试查找 "Full Time" 或 "1X2" 标签
            table_found = False
            table_container = None

            # 尝试多种可能的 1X2 表格标识
            x2_labels = ["Full Time", "1X2", "1x2", "full-time-result", "ft-result"]

            for label in x2_labels:
                try:
                    # 查找包含标签的元素
                    label_elements = await self.page.get_by_text(label, exact=False).all()
                    logger.info(f"V41.271 Searching for label: '{label}', found {len(label_elements)} elements")

                    for label_elem in label_elements:
                        if not await label_elem.is_visible():
                            continue

                        # 回溯查找父容器（表格区域）
                        container = await self._find_table_container(label_elem)
                        if container:
                            table_found = True
                            table_container = container
                            logger.info(f"V41.271 ✓ 1X2 table located with label: '{label}'")
                            break

                    if table_found:
                        break

                except Exception as e:
                    logger.debug(f"V41.271 Label search error for '{label}': {e}")
                    continue

            if not table_found:
                logger.warning("V41.271 ⚠️  NO 1X2 TABLE FOUND - Falling back to global extraction (RISKY)")
                # 继续使用全局提取（但有警告）
            else:
                logger.info("V41.271 ✓ 1X2 table container located - extracting ONLY from this region")

            # ================================================================
            # V41.271 Step 2: 从 1X2 表格区域提取赔率
            # ================================================================
            odd_divs = []
            if table_found and table_container:
                # 仅从 1X2 表格容器内提取
                try:
                    container_divs = await table_container.locator("div[class*='odd']").all()
                    odd_divs = container_divs
                    logger.info(f"V41.271 Found {len(odd_divs)} div[class*='odd'] elements in 1X2 table region")
                except Exception as e:
                    logger.debug(f"V41.271 Container extraction error: {e}")
                    # 回退到全局提取
                    odd_divs = await self.page.locator("div[class*='odd']").all()
                    logger.warning("V41.271 ⚠️  Fallback to global extraction due to container error")
            else:
                # 无 1X2 表格时使用全局提取（但有警告）
                odd_divs = await self.page.locator("div[class*='odd']").all()
                logger.warning(f"V41.271 ⚠️  Using GLOBAL extraction (risk of Asian Handicap contamination): {len(odd_divs)} elements")

            logger.info(f"V41.271 Total div[class*='odd'] elements to process: {len(odd_divs)}")

            if len(odd_divs) > 0:
                # 提取所有可见 div 的文本
                all_values = []
                for idx, div in enumerate(odd_divs):
                    try:
                        if not await div.is_visible():
                            continue

                        div_text = await div.inner_text() or ""
                        # 提取数值
                        values = self._extract_values(div_text)
                        all_values.extend(values)

                    except Exception as e:
                        logger.debug(f"V41.242 div[{idx}] error: {e}")
                        continue

                logger.info(f"V41.242 Extracted {len(all_values)} total odds values from div elements")

                if len(all_values) >= 3:
                    # ====================================================================
                    # V41.273 Step 1: 软性锚点 - Overround 概率逆推
                    # ====================================================================
                    # 如果没有找到视觉标签，使用软性锚点来识别 1X2 数据
                    if not table_found:
                        logger.info("V41.273 Step 1: Fuzzy Anchoring - Using Overround to identify 1X2 data")
                        fuzzy_triplet, fuzzy_overround = await self._fuzzy_anchoring(all_values)

                        if fuzzy_triplet:
                            # 使用软性锚点找到的三元组
                            vector = SequenceProcessor.process(
                                fuzzy_triplet,
                                enable_degraded=self.config.enable_degraded_mode
                            )

                            logger.info(f"V41.273 Fuzzy Anchoring vector quality: {vector.quality}, Overround: {fuzzy_overround:.4f}")

                            if vector.quality != MatrixQuality.INSUFFICIENT:
                                vectors.append(vector)
                                logger.info("V41.273 ✓ VALID vector from Fuzzy Anchoring")
                        else:
                            # 软性锚点失败，回退到常规序列处理
                            logger.warning("V41.273 ⚠️ Fuzzy Anchoring failed, falling back to standard sequence processing")
                            vector = SequenceProcessor.process(
                                all_values,
                                enable_degraded=self.config.enable_degraded_mode
                            )

                            if vector.quality != MatrixQuality.INSUFFICIENT:
                                vectors.append(vector)
                                logger.info("V41.273 VALID vector from standard processing (no visual label)")
                    else:
                        # 找到了视觉标签，使用标准序列处理
                        vector = SequenceProcessor.process(
                            all_values,
                            enable_degraded=self.config.enable_degraded_mode
                        )

                        logger.info(f"V41.242 Vector quality: {vector.quality}, values: {len(vector.values)}")

                        if vector.quality != MatrixQuality.INSUFFICIENT:
                            vectors.append(vector)
                            logger.info("V41.242 VALID vector extracted from div structure")

        except Exception as e:
            logger.exception(f"V41.242 div extraction error: {e}")

        # 策略 2: 回退到全文提取（如果策略 1 失败）
        if len(vectors) == 0:
            logger.info("V41.242 Fallback: extracting from page body text")
            try:
                body_text = await self.page.locator("body").inner_text() or ""
                values = self._extract_values(body_text)
                logger.info(f"V41.242 Body text extraction: {len(values)} values")

                if len(values) >= 3:
                    vector = SequenceProcessor.process(
                        values,
                        enable_degraded=self.config.enable_degraded_mode
                    )

                    if vector.quality != MatrixQuality.INSUFFICIENT:
                        vectors.append(vector)
                        logger.info("V41.242 VALID vector from body text fallback")
            except Exception as e:
                logger.debug(f"V41.242 Fallback extraction error: {e}")

        return vectors

    async def _find_table_container(self, label_element) -> Any | None:
        """
        V41.271 查找 1X2 表格容器

        从标签元素回溯查找包含赔率数据的父容器。

        策略：
        1. 向上遍历 DOM 树
        2. 查找包含 div[class*='odd'] 元素的父容器
        3. 最多回溯 10 层

        Args:
            label_element: 包含 "1X2" 或 "Full Time" 文本的元素

        Returns:
            表格容器元素，如果未找到则返回 None
        """
        if not self.page:
            return None

        try:
            return await label_element.evaluate("""
                (element) => {
                    let current = element;
                    const maxIterations = 10;

                    for (let i = 0; i < maxIterations && current; i++) {
                        // 检查当前容器是否包含 div[class*='odd']
                        const oddDivs = current.querySelectorAll ? current.querySelectorAll("div[class*='odd']") : [];

                        if (oddDivs && oddDivs.length >= 3) {
                            // 找到包含至少 3 个 odd 元素的容器
                            return current;
                        }

                        // 停止条件
                        if (current.tagName === 'BODY' || current.tagName === 'HTML') {
                            break;
                        }

                        current = current.parentElement;
                    }

                    return null;
                }
            """)


        except Exception as e:
            logger.debug(f"V41.271 _find_table_container error: {e}")
            return None

    async def _get_page_width(self) -> int:
        """获取页面宽度"""
        if not self.page:
            return 0

        return await self.page.evaluate("""
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

    def _calculate_overround(self, odds_triplet: list) -> Optional[float]:
        """
        V41.273 计算 Overround

        Overround = (1/Home + 1/Draw + 1/Away)

        Args:
            odds_triplet: 赔率三元组 [home, draw, away]

        Returns:
            Overround 值 (四舍五入到 4 位小数)，无效时返回 None
        """
        if not odds_triplet or len(odds_triplet) < 3:
            return None

        try:
            h, d, a = odds_triplet[:3]
            if None in (h, d, a) or any(x is None or x <= 0 for x in (h, d, a)):
                return None
            overround = (1.0 / h) + (1.0 / d) + (1.0 / a)
            return round(overround, 4)
        except (TypeError, ZeroDivisionError):
            return None

    def _validate_overround(self, overround: Optional[float]) -> bool:
        """
        V41.273 验证 Overround 是否在有效范围内

        1X2 赔率的 Overround 应该在 0.95 - 1.20 之间。

        Args:
            overround: Overround 值

        Returns:
            是否有效
        """
        if overround is None:
            return False
        return 0.95 <= overround <= 1.20

    async def _fuzzy_anchoring(self, all_values: list[float]) -> tuple[list[float], Optional[float]]:
        """
        V41.273 软性锚点 - Overround 概率逆推

        当找不到 "Full Time" 或 "1X2" 视觉标签时，通过数学方法识别 1X2 表格。

        逻辑：
        1. 将所有提取的数值组成连续的三元组
        2. 计算每个三元组的 Overround
        3. 选择 Overround 在 0.95-1.20 范围内的三元组
        4. 如果有多个有效三元组，选择 Overround 最接近 1.00 的

        Args:
            all_values: 所有提取的赔率值

        Returns:
            (有效的赔率值列表, 计算出的 Overround)
        """
        if len(all_values) < 3:
            return [], None

        best_triplet = None
        best_overround = None
        best_deviation = float("inf")

        # 滑动窗口检查所有可能的三元组
        for i in range(len(all_values) - 2):
            triplet = all_values[i:i+3]

            # 检查是否在有效范围内
            if all(self.config.min_value_threshold <= v <= self.config.max_value_threshold for v in triplet):
                overround = self._calculate_overround(triplet)

                if self._validate_overround(overround):
                    # 计算 Overround 与 1.00 的偏差
                    deviation = abs(overround - 1.00)

                    if deviation < best_deviation:
                        best_deviation = deviation
                        best_triplet = triplet
                        best_overround = overround

        if best_triplet:
            logger.info(
                f"V41.273 ✓ Fuzzy Anchoring: Found valid 1X2 triplet with Overround={best_overround:.4f} "
                f"(deviation from 1.00: {best_deviation:.4f})"
            )
            return best_triplet, best_overround

        logger.warning("V41.273 ⚠️ Fuzzy Anchoring: No valid 1X2 triplet found")
        return [], None

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
                with contextlib.suppress(Exception):
                    self.page = None

        # 步骤 2: 强制关闭 Context
        if self.context:
            try:
                await self.context.close()
                cleanup_count += 1
                logger.debug("Context closed successfully")
            except Exception as e:
                errors.append(f"Context cleanup: {e}")
                with contextlib.suppress(Exception):
                    self.context = None

        # 步骤 3: 强制关闭 Browser
        if self.browser:
            try:
                if self.browser.is_connected():
                    await self.browser.close()
                    cleanup_count += 1
                    logger.debug("Browser closed successfully")
            except Exception as e:
                errors.append(f"Browser cleanup: {e}")
                with contextlib.suppress(Exception):
                    self.browser = None

        # 步骤 4: 强制停止 Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
                cleanup_count += 1
                logger.debug("Playwright stopped successfully")
            except Exception as e:
                errors.append(f"Playwright cleanup: {e}")
                with contextlib.suppress(Exception):
                    self.playwright = None

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
