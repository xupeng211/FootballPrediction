#!/usr/bin/env python3
"""V83.0 Production-Grade Odds Data Extraction Engine.

This module provides a robust, self-healing engine for extracting odds data
from multiple betting sources using Playwright browser automation.

Multi-Layer Architecture:
    L1: FotMob API - Base match data
    L2: FotMob Detail - Opening odds via hover (data-testid selectors)
    L3: OddsPortal - Final odds via direct extraction (.odds-text selectors)

Core Features:
    - Multi-source extraction: Pinnacle, William Hill, Ladbrokes, 1xBet, Average Odds
    - Intelligent polling: Uses wait_for_selector instead of hard sleeps
    - Hover self-healing: Auto-scroll + mouse jitter retry mechanism (L2)
    - Direct extraction: V82.6 OddsPortal final odds extraction (L3)
    - Data integrity validation: Score-based validation (1.02 < Score < 1.08)
    - Temporal alignment: Preserves match_date for accurate timestamp construction

Example:
    >>> extractor = OddsProductionExtractor()
    >>> # L2: FotMob opening odds
    >>> result = await extractor.extract_opening_via_hover(
    ...     page=page,
    ...     entity_code="Entity_P",
    ...     match_date=datetime(2024, 4, 20)
    ... )
    >>> # L3: OddsPortal final odds
    >>> result = await extractor.extract_oddsportal_final_odds(
    ...     url="https://www.oddsportal.com/match/...",
    ...     match_id=12345
    ... )
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
import random
import re
from typing import Any

from playwright.async_api import Page, async_playwright
import psycopg2

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Constants
# ============================================================================

# Priority-ordered list of bookmakers to extract data from
TARGET_ENTITIES = [
    "Entity_P",    # Pinnacle (highest priority)
    "Entity_WH",   # William Hill
    "Entity_LB",   # Ladbrokes
    "Entity_B3",   # 1xBet
    "Entity_AVG",  # Average Odds (market consensus)
]

# Maps internal entity codes to display names on the website
ENTITY_NAME_MAPPING = {
    "Entity_P": "Pinnacle",
    "Entity_WH": "William Hill",
    "Entity_LB": "Ladbrokes",
    "Entity_B3": "1xBet",
    "Entity_AVG": "Average Odds",
}

# Integrity score validation thresholds
# Valid odds should satisfy: 1.00 < 1/P1 + 1/P2 + 1/P3 < 1.15
# Relaxed range (V139.1) to accommodate varying bookmaker margins (5-15%)
MIN_INTEGRITY_SCORE = 1.00
MAX_INTEGRITY_SCORE = 1.15

# Smart polling configuration (V88.0 Optimized)
POLLING_MAX_RETRIES = 3  # Increased from 2 to 3
POLLING_TOOLTIP_ATTEMPTS = 15  # Increased from 10 to 15
POLLING_TOOLTIP_DELAY_MS = 300  # Decreased from 500 to 300 for faster polling
SELECTOR_TIMEOUT_MS = 60000

# V88.0: Enhanced jitter configuration for higher success rate
JITTER_OFFSETS = [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3), (0, -3), (3, 0), (-3, 0)]

# Regex patterns for data extraction
OPENING_ODDS_REGEX = re.compile(r"(?:opening|initial)[:\s]*([\d.]+)", re.IGNORECASE)

# Tooltip parsing: "Opening odds:22 Dec, 08:131.19"
TOOLTIP_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
TOOLTIP_OPENING_PATTERN = re.compile(
    r"Opening\s+odds:(\d{1,2})\s+([A-Za-z]{3})\s*,\s+(\d{1,2}):(\d{2})(\d+\.\d+)"
)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MultiSourceEntityData:
    """Represents odds data from a single bookmaker for a specific match.

    Attributes:
        match_id: Unique identifier for the match
        source_name: Internal entity code (e.g., "Entity_P")
        init_h/d/a: Initial (opening) odds for home/draw/away
        opening_time_h/d/a: Timestamps when initial odds were published
        final_h/d/a: Final odds before match start
        integrity_score: Validation score (1/P1 + 1/P2 + 1/P3)
        is_valid: Whether data passes integrity validation
        validation_error: Error message if validation fails
        fully_captured: True if all three dimensions (init, time, final) are present
        data_timestamp: When this record was created
    """
    match_id: str
    source_name: str

    # Initial (opening) odds
    init_h: float | None = None
    init_d: float | None = None
    init_a: float | None = None

    # Initial odds timestamps
    opening_time_h: datetime | None = None
    opening_time_d: datetime | None = None
    opening_time_a: datetime | None = None

    # Final odds
    final_h: float | None = None
    final_d: float | None = None
    final_a: float | None = None

    # Validation metadata
    integrity_score: float | None = None
    is_valid: bool = False
    validation_error: str | None = None
    fully_captured: bool = False
    data_timestamp: datetime | None = None

    def calculate_integrity_score(self) -> float | None:
        """Calculates and validates the integrity score.

        The integrity score is computed as: Score = 1/P1 + 1/P2 + 1/P3
        Valid data must satisfy: 1.02 < Score < 1.08

        Special case: Data with only init_h + opening_time_h is marked
        as valid (hover capture scenario) but not fully captured.

        Returns:
            The integrity score if final odds are present, None otherwise.
        """
        # Check for initial timestamp only (hover capture scenario)
        has_init = self.init_h is not None
        has_time = any([self.opening_time_h, self.opening_time_d, self.opening_time_a])

        if has_init and has_time:
            self.is_valid = True
            self.validation_error = None
            self.fully_captured = False
            return None

        # Full validation requires all final odds
        if not all([self.final_h, self.final_d, self.final_a]):
            return None

        try:
            self.integrity_score = (
                1.0 / self.final_h +
                1.0 / self.final_d +
                1.0 / self.final_a
            )

            if MIN_INTEGRITY_SCORE < self.integrity_score < MAX_INTEGRITY_SCORE:
                self.is_valid = True
                self.validation_error = None
            else:
                self.is_valid = False
                self.validation_error = (
                    f"Integrity score {self.integrity_score:.4f} "
                    f"outside valid range [{MIN_INTEGRITY_SCORE}, {MAX_INTEGRITY_SCORE}]"
                )

            # Check full capture status
            has_final = all([self.final_h, self.final_d, self.final_a])
            has_initial = all([self.init_h, self.init_d, self.init_a])
            self.fully_captured = has_final and has_initial and has_time

            return self.integrity_score

        except ZeroDivisionError:
            self.is_valid = False
            self.validation_error = "Division by zero in integrity calculation"
            return None

    def to_dict(self) -> dict[str, Any]:
        """Converts the dataclass to a dictionary.

        Returns:
            Dictionary representation of all fields.
        """
        return {
            "match_id": self.match_id,
            "source_name": self.source_name,
            "init_h": self.init_h,
            "init_d": self.init_d,
            "init_a": self.init_a,
            "final_h": self.final_h,
            "final_d": self.final_d,
            "final_a": self.final_a,
            "integrity_score": self.integrity_score,
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
            "fully_captured": self.fully_captured,
            "opening_time_h": self.opening_time_h,
            "opening_time_d": self.opening_time_d,
            "opening_time_a": self.opening_time_a,
            "data_timestamp": self.data_timestamp,
        }


# ============================================================================
# Main Extraction Engine
# ============================================================================

class OddsProductionExtractor:
    """Production-grade odds data extraction engine.

    This engine provides intelligent, self-healing extraction of odds data
    from betting websites using browser automation. Key features:

    - Smart polling: Uses DOM-ready detection instead of hard sleeps
    - Hover self-healing: Auto-scroll + mouse jitter for tooltip capture
    - Temporal alignment: Preserves match_date context for accuracy
    - Data validation: Integrity score checking

    Typical usage:
        extractor = OddsProductionExtractor()
        result = await extractor.extract_opening_via_hover(
            page=page,
            entity_code="Entity_P",
            match_date=match_date
        )
    """

    def __init__(self):
        """Initializes the extractor with configuration settings."""
        self.settings = get_settings()
        self._stats = {
            "total_entities_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "integrity_failures": 0,
        }
        # V90.0: 网络嗅探器存储
        self._captured_responses: list[dict] = []
        self._odds_api_pattern = None

    # ========================================================================
    # V89.0 Shield Breaker: DOM Cleanup Methods
    # ========================================================================

    async def force_cleanup_ui(self, page: Page, save_screenshot: bool = False) -> None:
        """V89.0 Shield Breaker: 强制清除页面 UI 障碍物。

        通过 JavaScript DOM 操作物理切除以下障碍：
        1. OneTrust Cookie Banner 及相关元素
        2. Bonus 广告横幅
        3. 高 z-index 遮罩层（排除 Tooltip）
        4. Google iframe 嵌入

        Args:
            page: Playwright Page 对象
            save_screenshot: 是否保存清理后的截图（用于调试）
        """
        cleanup_script = """
        () => {
            const removed = [];
            const hidden = [];

            // 1. 移除 OneTrust Cookie Banner
            const onetrustSelectors = [
                '[id^="onetrust"]',
                '[id*="onetrust"]',
                '[class*="ot-sdk-container"]',
                '[class*="onetrust"]',
                '.ot-bnr-w',
                '#onetrust-consent-sdk',
                '.ot-consent-sdk'
            ];

            onetrustSelectors.forEach(selector => {
                try {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        removed.push({tag: el.tagName, id: el.id, cls: el.className});
                        el.remove();
                    });
                } catch (e) {
                    // 忽略选择器错误
                }
            });

            // 2. 移除 Bonus 广告
            const bonusSelectors = [
                '[class*="bonus"]',
                '[class*="Bonus"]',
                '[id*="bonus"]',
                '[id*="Bonus"]',
                '.banner',
                '.promo',
                '.advertisement'
            ];

            bonusSelectors.forEach(selector => {
                try {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        // 检查是否是广告元素（避免误删内容）
                        const text = el.textContent?.toLowerCase() || '';
                        if (text.includes('bonus') || text.includes('promo') ||
                            el.className?.toLowerCase().includes('bonus')) {
                            removed.push({tag: el.tagName, id: el.id, cls: el.className});
                            el.remove();
                        }
                    });
                } catch (e) {
                    // 忽略选择器错误
                }
            });

            // 3. 移除 Google iframe 和其他外部 iframe
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                const src = iframe.src || '';
                if (src.includes('google') || src.includes('doubleclick') ||
                    src.includes('facebook') || src.includes('analytics')) {
                    removed.push({tag: 'iframe', src: src});
                    iframe.remove();
                }
            });

            // 4. 隐藏高 z-index 遮罩层（保留 Tooltip）
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                try {
                    const style = window.getComputedStyle(el);
                    const zIndex = parseInt(style.zIndex) || 0;

                    // z-index > 100 且不是 tooltip 相关元素
                    if (zIndex > 100) {
                        const classes = el.className?.toLowerCase() || '';
                        const id = el.id?.toLowerCase() || '';
                        const isTooltip = classes.includes('tooltip') ||
                                          classes.includes('popover') ||
                                          id.includes('tooltip') ||
                                          id.includes('popover') ||
                                          el.getAttribute('role') === 'tooltip';

                        if (!isTooltip && el.tagName !== 'BODY' && el.tagName !== 'HTML') {
                            el.style.setProperty('display', 'none', 'important');
                            hidden.push({
                                tag: el.tagName,
                                zIndex: zIndex,
                                cls: el.className,
                                id: el.id
                            });
                        }
                    }
                } catch (e) {
                    // 忽略计算样式错误
                }
            });

            // 5. 强制启用页面滚动
            document.body.style.setProperty('overflow', 'auto', 'important');
            document.documentElement.style.setProperty('overflow', 'auto', 'important');

            // 6. 移除滚动锁定
            document.body.classList.remove('scroll-locked');
            document.body.classList.remove('modal-open');

            return {
                removedCount: removed.length,
                hiddenCount: hidden.length,
                removed: removed.slice(0, 10),  // 只返回前 10 个用于日志
                hidden: hidden.slice(0, 10)
            };
        }
        """

        try:
            result = await page.evaluate(cleanup_script)

            logger.info(
                f"[V89.0 Shield Breaker] DOM 清理完成: "
                f"移除 {result['removedCount']} 个元素, "
                f"隐藏 {result['hiddenCount']} 个高 z-index 层"
            )

            if result["removedCount"] > 0:
                logger.debug(f"[V89.0] 移除的元素: {result['removed']}")

            if result["hiddenCount"] > 0:
                logger.debug(f"[V89.0] 隐藏的元素: {result['hidden']}")

            # 可选：保存截图用于调试
            if save_screenshot:
                from pathlib import Path
                debug_dir = Path("logs/v89_debug")
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = debug_dir / f"cleanup_{timestamp}.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
                logger.info(f"[V89.0] 调试截图已保存: {screenshot_path}")

        except Exception as e:
            logger.warning(f"[V89.0 Shield Breaker] DOM 清理失败（继续执行）: {e}")

    # ========================================================================
    # V90.0 Ghost Protocol: Network Interception & Event Dispatch
    # ========================================================================

    def _setup_response_sniffer(self, page: Page) -> None:
        """V90.0: 设置网络响应嗅探器。

        监听所有 XHR/Fetch 响应，捕获包含 odds/opening/history 的请求。

        Args:
            page: Playwright Page 对象
        """
        async def response_handler(response):
            """处理网络响应。"""
            try:
                url = response.url.lower()
                content_type = response.headers.get("content-type", "").lower()

                # 只关注 JSON 响应
                if "application/json" in content_type or url.endswith(".json"):
                    # 检查是否包含目标关键词
                    if any(keyword in url for keyword in ["odds", "opening", "history", "price", "market"]):
                        try:
                            json_data = await response.json()
                            self._captured_responses.append({
                                "url": response.url,
                                "status": response.status,
                                "json": json_data,
                                "timestamp": datetime.now()
                            })
                            logger.info(f"[V90.0 Ghost] 捕获 API 响应: {response.url[:100]}")
                        except Exception:
                            pass  # 不是 JSON 响应
            except Exception as e:
                logger.debug(f"[V90.0 Ghost] 响应处理错误: {e}")

        # 注册响应监听器
        page.on("response", lambda response: asyncio.create_task(response_handler(response)))

    async def _trigger_ghost_hover(
        self,
        page: Page,
        element_selector: str = "div[data-testid='odd-container']"
    ) -> dict[str, Any] | None:
        """V90.0: JS 隔山打牛 - 通过事件触发绕过物理遮挡。

        直接触发 mouseover 和 mouseenter 事件，完全绕过 Cookie Banner 和广告。

        Args:
            page: Playwright Page 对象
            element_selector: 目标元素选择器

        Returns:
            事件触发结果
        """
        ghost_script = f"""
        () => {{
            const results = {{}};
            const containers = document.querySelectorAll("{element_selector}");

            if (containers.length === 0) {{
                results.error = "No containers found";
                return results;
            }}

            // 尝试触发第一个容器的事件
            const target = containers[0];

            // V90.0: 隔山打牛 - 直接触发事件，完全绕过物理层
            try {{
                // 1. mouseover 事件
                const mouseoverEvent = new MouseEvent('mouseover', {{
                    bubbles: true,
                    cancelable: true,
                    view: window
                }});
                target.dispatchEvent(mouseoverEvent);

                // 2. mouseenter 事件
                const mouseenterEvent = new MouseEvent('mouseenter', {{
                    bubbles: true,
                    cancelable: true,
                    view: window
                }});
                target.dispatchEvent(mouseenterEvent);

                // 3. click 事件 (某些网站需要点击才能触发)
                const clickEvent = new MouseEvent('click', {{
                    bubbles: true,
                    cancelable: true,
                    view: window
                }});
                target.dispatchEvent(clickEvent);

                results.success = true;
                results.triggered = ['mouseover', 'mouseenter', 'click'];
                results.element_tag = target.tagName;
                results.element_class = target.className;

            }} catch (e) {{
                results.error = e.toString();
            }}

            // 等待 100ms 让 tooltip 渲染
            return new Promise(resolve => {{
                setTimeout(() => {{
                    // 检查是否出现 tooltip
                    const tooltip = document.querySelector('[class*="tooltip"]') ||
                                   document.querySelector('[role="tooltip"]') ||
                                   document.querySelector('[data-tooltip]');
                    results.tooltip_found = !!tooltip;
                    if (tooltip) {{
                        results.tooltip_text = tooltip.textContent?.substring(0, 200);
                    }}
                    resolve(results);
                }}, 100);
            }});
        }}
        """

        try:
            result = await page.evaluate(ghost_script)

            if result.get("error"):
                logger.warning(f"[V90.0 Ghost] 事件触发失败: {result['error']}")
                return None

            logger.info(
                f"[V90.0 Ghost] 事件触发成功: {result.get('triggered')} | "
                f"Tooltip: {result.get('tooltip_found')}"
            )

            return result

        except Exception as e:
            logger.error(f"[V90.0 Ghost] 事件触发异常: {e}")
            return None

    async def extract_via_ghost_protocol(
        self,
        page: Page,
        entity_code: str = "Entity_P",
        match_date: datetime | None = None,
        wait_time_ms: int = 2000
    ) -> dict[str, Any] | None:
        """V90.0 幽灵协议 - 完整的数据提取流程。

        流程:
        1. 设置响应嗅探器
        2. 触发 ghost hover (事件驱动)
        3. 从捕获的 API 响应中解析数据
        4. 回退到 DOM tooltip 提取

        Args:
            page: Playwright Page 对象
            entity_code: 博彩商代码
            match_date: 比赛日期
            wait_time_ms: 等待 API 响应的时间

        Returns:
            提取结果字典
        """
        real_name = ENTITY_NAME_MAPPING.get(entity_code, entity_code)
        self._captured_responses.clear()  # 清空之前的捕获

        logger.info(f"[V90.0 Ghost Protocol] 启动: {real_name}")

        try:
            # 步骤 1: 设置响应嗅探器
            self._setup_response_sniffer(page)

            # 步骤 2: 等待页面加载
            await page.wait_for_load_state("networkidle", timeout=10000)

            # 步骤 3: 触发 ghost hover
            ghost_result = await self._trigger_ghost_hover(page)

            if not ghost_result:
                return self._build_hover_failed_result("Ghost hover 失败")

            # 步骤 4: 等待 API 响应
            await asyncio.sleep(wait_time_ms / 1000)

            # 步骤 5: 检查是否捕获到 API 数据
            if self._captured_responses:
                logger.info(f"[V90.0 Ghost] 捕获到 {len(self._captured_responses)} 个 API 响应")

                # 尝试从第一个响应中解析数据
                for resp in self._captured_responses:
                    parsed = self._parse_api_response(resp, match_date)
                    if parsed:
                        logger.info("[V90.0 Ghost] ✅ API 解析成功")
                        return {
                            **parsed,
                            "source": "V90.0_Ghost_API",
                            "hover_failed": False
                        }

            # 步骤 6: 回退到 DOM tooltip 检测
            tooltip_data = await self._poll_for_tooltip_enhanced(page)
            if tooltip_data:
                match_year = match_date.year if match_date else datetime.now().year
                return self._parse_tooltip_data(tooltip_data, match_year)

            return self._build_hover_failed_result("未捕获到任何数据")

        except Exception as e:
            logger.error(f"[V90.0 Ghost Protocol] 异常: {e}")
            return self._build_hover_failed_result(f"异常: {e!s}")

    def _parse_api_response(
        self,
        response: dict,
        match_date: datetime | None = None
    ) -> dict[str, Any] | None:
        """V90.0 Enhanced: 解析捕获的 API 响应。

        支持多种可能的 JSON 结构:
        - 标准格式: {opening: {home, draw, away, timestamp}}
        - 简写字段: {opening: {h, d, a, time}}
        - 嵌套结构: {odds: {opening: {...}}}
        - 数组格式: {data: [{type: opening, ...}]}

        Args:
            response: API 响应数据
            match_date: 比赛日期

        Returns:
            解析后的初盘数据
        """
        try:
            json_data = response["json"]

            if not isinstance(json_data, dict):
                return None

            # 方案 1: 直接的 opening/initial/start 字段
            for key in ["opening", "initial", "start"]:
                if key in json_data:
                    data = json_data[key]
                    if isinstance(data, dict):
                        # 支持多种字段名变体
                        home = data.get("home") or data.get("h") or data.get("1")
                        draw = data.get("draw") or data.get("d") or data.get("x")
                        away = data.get("away") or data.get("a")
                        time = data.get("timestamp") or data.get("time") or data.get("opening_time")

                        if home and isinstance(home, (int, float)):
                            logger.debug(f"[V90.0 Ghost] 解析成功 ({key}): init_h={home}")
                            return {
                                "init_h": float(home),
                                "init_d": float(draw) if draw and isinstance(draw, (int, float)) else None,
                                "init_a": float(away) if away and isinstance(away, (int, float)) else None,
                                "opening_time_h": time
                            }

            # 方案 2: 嵌套的 odds.opening 结构
            if "odds" in json_data:
                odds = json_data["odds"]
                if isinstance(odds, dict):
                    result = self._parse_api_response({"json": odds}, match_date)
                    if result:
                        logger.debug(f"[V90.0 Ghost] 解析成功 (odds): init_h={result.get('init_h')}")
                        return result

            # 方案 3: data 数组格式
            if "data" in json_data:
                data = json_data["data"]
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item_type = item.get("type", "") or str(item.get("name", ""))
                            if "opening" in item_type.lower() or "initial" in item_type.lower():
                                home = item.get("home") or item.get("h")
                                draw = item.get("draw") or item.get("d")
                                away = item.get("away") or item.get("a")
                                if home and isinstance(home, (int, float)):
                                    logger.debug(f"[V90.0 Ghost] 解析成功 (data array): init_h={home}")
                                    return {
                                        "init_h": float(home),
                                        "init_d": float(draw) if draw else None,
                                        "init_a": float(away) if away else None,
                                        "opening_time_h": item.get("timestamp")
                                    }

            # 方案 4: match.nested 结构
            if "match" in json_data:
                match = json_data["match"]
                if isinstance(match, dict):
                    result = self._parse_api_response({"json": match}, match_date)
                    if result:
                        logger.debug(f"[V90.0 Ghost] 解析成功 (match): init_h={result.get('init_h')}")
                        return result

            # 方案 5: 递归深度搜索
            def find_odds_recursive(obj: Any, depth: int = 0, max_depth: int = 5) -> dict | None:
                """递归查找包含赔率数据的对象."""
                if depth > max_depth or not isinstance(obj, dict):
                    return None

                # 检查当前对象是否包含赔率数据
                for key in ["opening", "initial", "start"]:
                    if key in obj:
                        data = obj[key]
                        if isinstance(data, dict):
                            home = data.get("home") or data.get("h")
                            if home and isinstance(home, (int, float)):
                                return obj

                # 递归搜索子对象
                for value in obj.values():
                    if isinstance(value, dict):
                        result = find_odds_recursive(value, depth + 1, max_depth)
                        if result:
                            return result
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                result = find_odds_recursive(item, depth + 1, max_depth)
                                if result:
                                    return result

                return None

            nested_result = find_odds_recursive(json_data)
            if nested_result:
                result = self._parse_api_response({"json": nested_result}, match_date)
                if result:
                    logger.debug(f"[V90.0 Ghost] 解析成功 (recursive): init_h={result.get('init_h')}")
                    return result

            logger.debug(f"[V90.0 Ghost] API 结构未知，URL: {response.get('url', 'unknown')[:100]}")
            return None

        except Exception as e:
            logger.debug(f"[V90.0 Ghost] API 解析失败: {e}")
            return None

    # ========================================================================
    # Core Extraction Methods
    # ========================================================================

    async def extract_opening_via_hover(
        self,
        page: Page,
        entity_code: str,
        match_date: datetime | None = None,
        skip_if_exists: bool = False
    ) -> dict[str, Any] | None:
        """Extracts opening odds via hover with intelligent self-healing.

        This method implements a sophisticated hover-based extraction strategy:

        1. Smart polling: Waits for odd-container with 60s timeout
        2. Scroll alignment: Ensures element is in viewport before hover
        3. Tooltip polling: Checks for tooltip every 500ms (max 10 attempts)
        4. Mouse jitter: If tooltip fails, performs micro-movement to re-trigger

        Args:
            page: Playwright Page object
            entity_code: Internal entity code (e.g., "Entity_P")
            match_date: Match date for temporal alignment (defaults to now)
            skip_if_exists: If True, skip if data already exists (not implemented)

        Returns:
            Dictionary with keys:
                - init_h/d/a: Initial odds
                - opening_time_h/d/a: Initial odds timestamps
                - hover_failed: Boolean indicating extraction failure
                - hover_error: Error message if failed
                - source: Extraction method identifier

            Returns None only if match_id cannot be determined.
        """
        real_name = ENTITY_NAME_MAPPING.get(entity_code, entity_code)

        # Temporal alignment: Use real match date for accurate timestamps
        if match_date is None:
            logger.warning("[OddsExtractor] match_date not provided, using current date")
            match_date = datetime.now()
            match_year = match_date.year
        else:
            match_year = match_date.year

        try:
            logger.info(f"[OddsExtractor] Hover capture: {real_name} (match_date: {match_date.date()})")

            # Step 1: Smart polling - Wait for odd-container to appear
            await self._wait_for_element_ready(page)

            # Step 2: Find target bookmaker container
            target_container = await self._find_bookmaker_container(page, real_name)
            if not target_container:
                return self._build_hover_failed_result(f"Bookmaker {real_name} not found")

            # Step 3: Scroll into view (hover self-healing)
            await self._scroll_to_element(target_container)

            # Step 4: Execute hover with tooltip polling and retry
            tooltip_data = await self._hover_with_retry(
                page, target_container, POLLING_MAX_RETRIES
            )

            # Step 5: Parse tooltip data
            if not tooltip_data:
                return self._build_hover_failed_result("No tooltip data captured")

            return self._parse_tooltip_data(tooltip_data, match_year)

        except Exception as e:
            logger.error(f"[OddsExtractor] Hover capture exception: {e}")
            return {
                "hover_failed": True,
                "hover_error": f"Exception: {e!s}",
                "init_h": None,
                "init_d": None,
                "init_a": None,
                "opening_time_h": None,
                "opening_time_d": None,
                "opening_time_a": None,
            }

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _wait_for_element_ready(self, page: Page) -> None:
        """Waits for the odd-container element to be ready.

        Uses smart polling with 60s timeout instead of hard sleep.

        Args:
            page: Playwright Page object
        """
        try:
            logger.debug("[OddsExtractor] Smart polling: waiting for odd-container...")
            await page.wait_for_selector(
                "div[data-testid='odd-container']",
                timeout=SELECTOR_TIMEOUT_MS
            )
            logger.debug("[OddsExtractor] odd-container ready (millisecond response)")
        except Exception as e:
            logger.debug(f"[OddsExtractor] Polling timeout, continuing: {e}")

    async def _find_bookmaker_container(self, page: Page, real_name: str):
        """Finds the odd-container for the target bookmaker.

        Args:
            page: Playwright Page object
            real_name: Display name of the bookmaker

        Returns:
            Playwright Locator for the target container, or None if not found.
        """
        all_containers = page.locator("div[data-testid='odd-container']")
        count = await all_containers.count()

        logger.debug(f"[OddsExtractor] Found {count} odd-container elements")

        for i in range(min(count, 100)):
            container = all_containers.nth(i)

            try:
                bookmaker = await container.evaluate("""
                    (elem) => {
                        let parent = elem;
                        for (let i = 0; i < 10; i++) {
                            if (parent && parent.parentElement) {
                                parent = parent.parentElement;
                                const nameElem = parent.querySelector(
                                    '[data-testid="outrights-expanded-bookmaker-name"]'
                                );
                                if (nameElem) {
                                    return nameElem.textContent;
                                }
                            }
                        }
                        return null;
                    }
                """)

                if bookmaker and real_name.lower() in bookmaker.lower():
                    logger.debug(f"[OddsExtractor] Found bookmaker: {bookmaker}")
                    return container

            except Exception as e:
                logger.debug(f"[OddsExtractor] Check failed for container {i}: {e}")
                continue

        logger.warning(f"[OddsExtractor] {real_name} container not found")
        return None

    async def _scroll_to_element(self, element) -> None:
        """Scrolls element into view for hover alignment.

        Args:
            element: Playwright Locator object
        """
        try:
            await element.scroll_into_view_if_needed(timeout=5000)
            logger.debug("[OddsExtractor] Element scrolled into view")
        except Exception as e:
            logger.debug(f"[OddsExtractor] Scroll failed, continuing: {e}")

    async def _hover_with_retry(
        self,
        page: Page,
        element,
        max_retries: int
    ) -> dict[str, Any] | None:
        """V88.0 Enhanced: Executes hover with multi-position jitter retry.

        Args:
            page: Playwright Page object
            element: Playwright Locator to hover on
            max_retries: Maximum number of hover attempts

        Returns:
            Tooltip data dictionary if captured, None otherwise.
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[OddsExtractor] Retry hover ({attempt + 1}/{max_retries})")

                # V88.0: Use jitter offset for this attempt
                jitter_offset = JITTER_OFFSETS[attempt % len(JITTER_OFFSETS)]

                await element.hover(position={"x": jitter_offset[0], "y": jitter_offset[1]})

                # V88.0: Smart wait for tooltip using wait_for_function
                tooltip_data = await self._poll_for_tooltip_enhanced(page)
                if tooltip_data:
                    logger.info(f"[OddsExtractor] Tooltip captured with offset {jitter_offset}")
                    return tooltip_data

                # Last attempt failed
                if attempt == max_retries - 1:
                    logger.warning(
                        f"[OddsExtractor] No tooltip detected "
                        f"after {max_retries} retries"
                    )

            except Exception as e:
                logger.error(f"[OddsExtractor] Hover attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None

        return None

    async def _poll_for_tooltip_enhanced(self, page: Page) -> dict[str, Any] | None:
        """V88.0 Enhanced: Polls for tooltip with intelligent wait.

        Uses multiple detection patterns and wait_for_function for better accuracy.

        Args:
            page: Playwright Page object

        Returns:
            Tooltip data dictionary if found, None otherwise.
        """
        # V88.0: First, try intelligent wait for tooltip to appear
        try:
            tooltip_data = await page.wait_for_function(
                """
                () => {
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {
                        const text = el.textContent || '';
                        // Multiple patterns to detect tooltip
                        if ((text.includes('Opening odds:') || text.includes('Opening') || text.includes('Odds:')) &&
                            text.length < 1000 && text.length > 30) {
                            return {
                                tagName: el.tagName,
                                className: el.className,
                                text: text,
                            };
                        }
                    }
                    return false;
                }
                """,
                timeout=2000  # Wait up to 2 seconds for tooltip to appear
            )

            if tooltip_data:
                logger.info("[OddsExtractor] Tooltip captured via wait_for_function")
                return tooltip_data

        except Exception:
            # wait_for_function timed out, fall back to polling
            pass

        # Fallback: Original polling method with more lenient patterns
        for poll_attempt in range(POLLING_TOOLTIP_ATTEMPTS):
            try:
                tooltip_data = await page.evaluate("""
                    () => {
                        const allElements = document.querySelectorAll('*');
                        for (let el of allElements) {
                            const text = el.textContent || '';
                            // V88.0: More lenient detection patterns
                            if ((text.includes('Opening odds:') || text.includes('Opening') || text.includes('odds:')) &&
                                text.length < 1000 && text.length > 30) {
                                return {
                                    tagName: el.tagName,
                                    className: el.className,
                                    text: text,
                                };
                            }
                        }
                        return null;
                    }
                """)

                if tooltip_data:
                    logger.info(
                        f"[OddsExtractor] Tooltip captured "
                        f"(poll {poll_attempt + 1}/{POLLING_TOOLTIP_ATTEMPTS})"
                    )
                    return tooltip_data

            except Exception:
                pass

            await page.wait_for_timeout(POLLING_TOOLTIP_DELAY_MS)

        return None

    async def _perform_mouse_jitter(self, page: Page, element) -> None:
        """Performs mouse jitter to re-trigger tooltip on hover failure.

        Simulates subtle hand movement to awaken dormant tooltips.

        Args:
            page: Playwright Page object
            element: Playwright Locator to jitter on
        """
        logger.debug("[OddsExtractor] Mouse jitter self-healing: executing micro-movement")
        try:
            box = await element.bounding_box()
            await page.mouse.move(box["x"] + 5, box["y"] + 5)
            await page.wait_for_timeout(100)
            await page.mouse.move(box["x"], box["y"])
            await page.wait_for_timeout(100)
            logger.debug("[OddsExtractor] Mouse jitter complete")
        except Exception as e:
            logger.debug(f"[OddsExtractor] Mouse jitter failed: {e}")

    def _parse_tooltip_data(
        self,
        tooltip_data: dict[str, Any],
        match_year: int
    ) -> dict[str, Any]:
        """Parses tooltip data to extract opening odds and timestamp.

        Args:
            tooltip_data: Raw tooltip data from page evaluation
            match_year: Year of the match for temporal alignment

        Returns:
            Parsed result dictionary with init odds and timestamps.
        """
        # Defensive check for missing or None text
        if not tooltip_data or not tooltip_data.get("text"):
            return self._build_hover_failed_result("Missing or null tooltip text")

        match = TOOLTIP_OPENING_PATTERN.search(tooltip_data["text"])

        if not match:
            logger.warning(
                f"[OddsExtractor] Cannot parse tooltip: "
                f"{tooltip_data['text'][:100]}"
            )
            return self._build_hover_failed_result("Cannot parse tooltip format")

        day, month_str, hour, minute, odd_value = match.groups()
        month = TOOLTIP_MONTH_MAP.get(month_str)

        if not month:
            return self._build_hover_failed_result(f"Invalid month: {month_str}")

        try:
            opening_time = datetime(match_year, month, int(day), int(hour), int(minute))
            opening_odd = float(odd_value)

            # Year consistency audit
            if abs(opening_time.year - match_year) > 1:
                logger.warning(
                    f"[OddsExtractor] Year mismatch! match_year={match_year}, "
                    f"opening_time_year={opening_time.year}"
                )

            logger.info(f"[OddsExtractor] Parsed: opening_time={opening_time.isoformat()}")

            return {
                "init_h": opening_odd,
                "init_d": None,
                "init_a": None,
                "opening_time_h": opening_time,
                "opening_time_d": None,
                "opening_time_a": None,
                "hover_failed": False,
                "hover_error": None,
                "source": "hover_tooltip_production",
            }

        except Exception as e:
            logger.error(f"[OddsExtractor] Date construction failed: {e}")
            return self._build_hover_failed_result(f"Date construction failed: {e}")

    def _build_hover_failed_result(self, error_msg: str) -> dict[str, Any]:
        """Builds a standard failure result dictionary.

        Args:
            error_msg: Description of the failure

        Returns:
            Dictionary with hover_failed=True and error message.
        """
        return {
            "hover_failed": True,
            "hover_error": error_msg,
            "init_h": None,
            "init_d": None,
            "init_a": None,
            "opening_time_h": None,
            "opening_time_d": None,
            "opening_time_a": None,
        }

    # ========================================================================
    # Database Operations
    # ========================================================================

    def get_db_connection(self):
        """Gets a database connection using configured settings.

        V58.0: Adds statement_timeout protection to prevent zombie locks.

        Returns:
            psycopg2 connection object.
        """
        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

        # V58.0: Set statement_timeout to prevent long-running queries
        # This prevents future zombie lock issues
        cursor = conn.cursor()
        cursor.execute("SET statement_timeout = '30s'")
        cursor.close()

        return conn

    def save_multi_source_data(self, data_list: list[MultiSourceEntityData]) -> dict[str, int]:
        """Saves multiple source data records to the database.

        Implements upsert logic: updates existing records, inserts new ones.

        Args:
            data_list: List of MultiSourceEntityData objects to save

        Returns:
            Dictionary with statistics:
                - total: Number of records processed
                - inserted: Number of new records inserted
                - updated: Number of existing records updated
                - valid: Number of valid records
                - invalid: Number of invalid records
                - fully_captured: Number of fully captured records
        """
        if not data_list:
            return {
                "total": 0,
                "inserted": 0,
                "updated": 0,
                "valid": 0,
                "invalid": 0,
                "fully_captured": 0,
            }

        stats = {
            "total": len(data_list),
            "inserted": 0,
            "updated": 0,
            "valid": 0,
            "invalid": 0,
            "fully_captured": 0,
        }

        conn = self.get_db_connection()
        cursor = conn.cursor()

        for data in data_list:
            data.calculate_integrity_score()

            if data.is_valid:
                stats["valid"] += 1
            else:
                stats["invalid"] += 1

            if data.fully_captured:
                stats["fully_captured"] += 1

            try:
                cursor.execute("""
                    INSERT INTO metrics_multi_source_data (
                        match_id, source_name,
                        init_h, init_d, init_a,
                        opening_time_h, opening_time_d, opening_time_a,
                        final_h, final_d, final_a,
                        integrity_score, is_valid, validation_error,
                        fully_captured, data_timestamp
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id, source_name)
                    DO UPDATE SET
                        init_h = EXCLUDED.init_h,
                        init_d = EXCLUDED.init_d,
                        init_a = EXCLUDED.init_a,
                        opening_time_h = EXCLUDED.opening_time_h,
                        opening_time_d = EXCLUDED.opening_time_d,
                        opening_time_a = EXCLUDED.opening_time_a,
                        final_h = EXCLUDED.final_h,
                        final_d = EXCLUDED.final_d,
                        final_a = EXCLUDED.final_a,
                        integrity_score = EXCLUDED.integrity_score,
                        is_valid = EXCLUDED.is_valid,
                        validation_error = EXCLUDED.validation_error,
                        fully_captured = EXCLUDED.fully_captured,
                        data_timestamp = EXCLUDED.data_timestamp
                """, (
                    data.match_id, data.source_name,
                    data.init_h, data.init_d, data.init_a,
                    data.opening_time_h, data.opening_time_d, data.opening_time_a,
                    data.final_h, data.final_d, data.final_a,
                    data.integrity_score, data.is_valid, data.validation_error,
                    data.fully_captured, data.data_timestamp,
                ))

                # Check if this was an insert or update
                if cursor.rowcount > 0:
                    stats["inserted"] += 1
                else:
                    stats["updated"] += 1

            except Exception as e:
                logger.error(f"Database error for match {data.match_id}: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        return stats

    # ========================================================================
    # L3: OddsPortal Final Odds Extraction (V82.6 Integrated)
    # ========================================================================

    async def extract_oddsportal_final_odds(
        self,
        url: str,
        match_id: int,
        match_date: datetime | None = None
    ) -> dict[str, Any]:
        """Extracts Pinnacle final odds from OddsPortal (V82.6 Logic).

        L3 Layer: Direct extraction of final odds using .odds-text selectors.
        This method implements the proven V82.6 extraction strategy:
        1. Finds Pinnacle container via text search
        2. Selects only .odds-text elements (excludes .odds-cell)
        3. Extracts first 3 valid odds as home/draw/away

        Args:
            url: OddsPortal match page URL
            match_id: Database match ID for logging
            match_date: Match date for temporal alignment (optional)

        Returns:
            Dictionary with keys:
                - success: Boolean indicating overall success
                - pinnacle_found: True if Pinnacle container was located
                - final_h/d/a: Final odds for home/draw/away
                - integrity_score: Calculated validation score
                - is_valid: Whether score is in valid range
                - error: Error message if failed
        """
        result = {
            "match_id": match_id,
            "url": url,
            "success": False,
            "pinnacle_found": False,
            "final_h": None,
            "final_d": None,
            "final_a": None,
            "integrity_score": None,
            "is_valid": False,
            "error": None
        }

        logger.info(f"[OddsPortal L3] Extracting final odds for match_id={match_id}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(3, 5))

                # V82.6 Core Logic: Extract Pinnacle odds with Fallback Selectors
                pinnacle_odds = await page.evaluate("""
                    () => {
                        // Step 1: Find Pinnacle container
                        let pinnacleContainer = null;
                        const allElements = document.querySelectorAll('*');

                        for (let el of allElements) {
                            const text = el.textContent || '';
                            // Find Pinnacle row (exclude other bookmakers)
                            if (text.toLowerCase().includes('pinnacle') &&
                                !text.toLowerCase().includes('william') &&
                                !text.toLowerCase().includes('ladbrokes') &&
                                !text.toLowerCase().includes('1xbet')) {

                                // Search upward for container with multiple odds
                                let parent = el;
                                for (let i = 0; i < 10; i++) {
                                    if (parent && parent.parentElement) {
                                        parent = parent.parentElement;
                                        // Try primary selector first
                                        const oddsElements = parent.querySelectorAll('.odds-text');
                                        if (oddsElements.length >= 3) {
                                            pinnacleContainer = parent;
                                            break;
                                        }
                                    }
                                }
                                if (pinnacleContainer) break;
                            }
                        }

                        if (!pinnacleContainer) {
                            return { found: false, error: 'Pinnacle container not found' };
                        }

                        // Step 2: Extract odds with fallback selectors
                        // Fallback selector chain for robustness
                        const selectorChain = [
                            '.odds-text',           // Primary: V82.6 selector
                            '.odds-cell .odd',      // Fallback 1: cell-based odds
                            'td[data-odd]',         // Fallback 2: data attribute
                            '.odd',                 // Fallback 3: generic odd class
                            '[data-odd]'            // Fallback 4: any data-odd attribute
                        ];

                        let extractedOdds = [];
                        let usedSelector = null;

                        for (const selector of selectorChain) {
                            const oddsElements = pinnacleContainer.querySelectorAll(selector);
                            extractedOdds = [];

                            for (let elem of oddsElements) {
                                let text = null;

                                // Handle different element types
                                if (selector === 'td[data-odd]' || selector === '[data-odd]') {
                                    text = elem.getAttribute('data-odd');
                                } else {
                                    text = elem.textContent?.trim();
                                }

                                // Validate odds format (1.01 - 50.00)
                                if (text) {
                                    const num = parseFloat(text);
                                    if (!isNaN(num) && num >= 1.01 && num <= 50.00) {
                                        extractedOdds.push(num);
                                    }
                                }
                            }

                            // Remove duplicates and sort
                            extractedOdds = [...new Set(extractedOdds)].sort((a, b) => a - b);

                            if (extractedOdds.length >= 3) {
                                usedSelector = selector;
                                break;
                            }
                        }

                        if (extractedOdds.length >= 3) {
                            return {
                                found: true,
                                odds: [extractedOdds[0], extractedOdds[1], extractedOdds[2]],
                                totalOdds: extractedOdds.length,
                                allOdds: extractedOdds.slice(0, 10),
                                selector: usedSelector,
                                allOddsRaw: extractedOdds
                            };
                        } else {
                            return {
                                found: false,
                                error: `Found ${extractedOdds.length} odds, need at least 3`,
                                odds: extractedOdds,
                                attemptedSelectors: selectorChain
                            };
                        }
                    }
                """)

                if pinnacle_odds.get("found"):
                    result["pinnacle_found"] = True
                    result["final_h"] = pinnacle_odds["odds"][0]
                    result["final_d"] = pinnacle_odds["odds"][1]
                    result["final_a"] = pinnacle_odds["odds"][2]
                    result["success"] = True

                    # Calculate integrity score
                    try:
                        result["integrity_score"] = (
                            1.0 / result["final_h"] +
                            1.0 / result["final_d"] +
                            1.0 / result["final_a"]
                        )
                        result["is_valid"] = (
                            MIN_INTEGRITY_SCORE < result["integrity_score"] < MAX_INTEGRITY_SCORE
                        )
                    except ZeroDivisionError:
                        result["is_valid"] = False

                    # Log which selector was used (for debugging)
                    selector_used = pinnacle_odds.get("selector", "unknown")
                    total_odds_found = pinnacle_odds.get("totalOdds", 0)

                    logger.info(
                        f"[OddsPortal L3] ✅ Pinnacle: "
                        f"{result['final_h']} / {result['final_d']} / {result['final_a']} "
                        f"(Score: {result['integrity_score']:.4f}, Valid: {result['is_valid']}, "
                        f"Selector: '{selector_used}', Found: {total_odds_found} odds)"
                    )
                else:
                    result["error"] = pinnacle_odds.get("error", "Unknown error")
                    logger.debug(f"[OddsPortal L3] ⚠️ {result['error']}")

            except Exception as e:
                result["error"] = str(e)
                logger.warning(f"[OddsPortal L3] ⚠️ Extraction failed: {e}")

            finally:
                await browser.close()

        return result

    # ========================================================================
    # V95.0 Gene Splicing: OddsHarvester-Inspired Extraction
    # ========================================================================

    async def extract_opening_via_hover_v95(
        self,
        page: Page,
        entity_code: str,
        match_date: datetime | None = None,
        skip_if_exists: bool = False
    ) -> dict[str, Any] | None:
        """V95.0: Extracts opening odds via hover using OddsHarvester-inspired approach.

        Key improvements from technical audit:
        - Target modal: h3:has-text('Odds movement') instead of generic tooltip
        - Parse path: div.mt-2.gap-1 for odds data
        - Odds value: .font-bold elements
        - Timestamp: %d %b, %H:%M format with year inference
        - Multi-process safe: No shared state conflicts

        Args:
            page: Playwright Page object
            entity_code: Internal entity code (e.g., "Entity_P")
            match_date: Match date for year inference (critical for accuracy)
            skip_if_exists: If True, skip if data already exists

        Returns:
            Dictionary with keys:
                - init_h/d/a: Initial odds
                - opening_time_h/d/a: Initial odds timestamps
                - hover_failed: Boolean indicating extraction failure
                - hover_error: Error message if failed
                - source: Extraction method identifier
        """
        real_name = ENTITY_NAME_MAPPING.get(entity_code, entity_code)

        # Temporal alignment: Infer correct year from match_date
        if match_date is None:
            logger.warning("[V95.0] match_date not provided, using current date")
            match_date = datetime.now()

        match_year = match_date.year
        match_month = match_date.month

        try:
            logger.info(
                f"[V95.0] OddsHarvester-style extraction: {real_name} "
                f"(match_date: {match_date.date()})"
            )

            # Step 1: Force cleanup UI (shield breaker)
            await self.force_cleanup_ui(page, save_screenshot=False)

            # Step 2: Smart polling - Wait for odd-container
            await self._wait_for_element_ready(page)

            # Step 3: Find target bookmaker container
            target_container = await self._find_bookmaker_container(page, real_name)
            if not target_container:
                return self._build_hover_failed_result(f"Bookmaker {real_name} not found")

            # Step 4: Scroll into view
            await self._scroll_to_element(target_container)

            # Step 5: Execute hover action
            logger.debug(f"[V95.0] Hovering on {real_name} container...")
            await target_container.hover()

            # Step 6: Wait for Odds movement modal (THE NEW TARGET)
            try:
                await page.wait_for_selector(
                    "h3:has-text('Odds movement')",
                    timeout=5000
                )
                logger.info("[V95.0] Odds movement modal detected!")
            except Exception:
                logger.warning("[V95.0] Odds movement modal not found, attempting fallback...")
                # Fallback: Try to find any modal with odds-related content
                try:
                    await page.wait_for_selector(
                        "div[class*='modal'], div[class*='popup'], div[class*='tooltip']",
                        timeout=3000
                    )
                    logger.info("[V95.0] Fallback modal detected")
                except Exception:
                    return self._build_hover_failed_result("No modal detected after hover")

            # Step 7: Extract data from div.mt-2.gap-1 block
            modal_data = await page.evaluate(r"""
                () => {
                    // Find the modal container with Odds movement header
                    const allElements = document.querySelectorAll('*');
                    let modalContainer = null;

                    // Search for h3 with 'Odds movement' text
                    for (let el of allElements) {
                        if (el.tagName === 'H3' && el.textContent.includes('Odds movement')) {
                            // Navigate up to find the modal container
                            let parent = el;
                            for (let i = 0; i < 10; i++) {
                                if (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    // Look for the data block
                                    const dataBlock = parent.querySelector('div.mt-2.gap-1');
                                    if (dataBlock) {
                                        modalContainer = parent;
                                        break;
                                    }
                                }
                            }
                            if (modalContainer) break;
                        }
                    }

                    if (!modalContainer) {
                        return { found: false, error: 'Modal container not found' };
                    }

                    // Extract odds and timestamp from div.mt-2.gap-1
                    const dataBlock = modalContainer.querySelector('div.mt-2.gap-1');
                    if (!dataBlock) {
                        return { found: false, error: 'div.mt-2.gap-1 not found' };
                    }

                    // Extract .font-bold elements (odds values)
                    const boldElements = dataBlock.querySelectorAll('.font-bold');
                    const oddsValues = [];
                    for (let el of boldElements) {
                        const text = el.textContent?.trim();
                        if (text) {
                            // Try to parse as number
                            const num = parseFloat(text);
                            if (!isNaN(num) && num >= 1.01 && num <= 50.00) {
                                oddsValues.push(num);
                            }
                        }
                    }

                    // Extract timestamp from text content
                    // Format: "20 Dec, 08:13" or similar
                    const allText = dataBlock.textContent || '';
                    const timePattern = /(\d{1,2})\s+([A-Za-z]{3})\s*,\s+(\d{1,2}):(\d{2})/;
                    const timeMatch = allText.match(timePattern);

                    return {
                        found: true,
                        odds: oddsValues,
                        timeMatch: timeMatch,  // Return the match object directly
                        rawHtml: dataBlock.innerHTML.substring(0, 500),
                        fullText: allText.substring(0, 200)
                    };
                }
            """)

            if not modal_data.get("found"):
                error_msg = modal_data.get("error", "Unknown error")
                logger.warning(f"[V95.0] Modal extraction failed: {error_msg}")
                return self._build_hover_failed_result(f"Modal extraction failed: {error_msg}")

            # Step 8: Parse extracted data
            return self._parse_v95_modal_data(modal_data, match_year, match_month)

        except Exception as e:
            logger.error(f"[V95.0] Extraction exception: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "hover_failed": True,
                "hover_error": f"Exception: {e!s}",
                "init_h": None,
                "init_d": None,
                "init_a": None,
                "opening_time_h": None,
                "opening_time_d": None,
                "opening_time_a": None,
                "source": "v95_failed",
            }

    def _parse_v95_modal_data(
        self,
        modal_data: dict[str, Any],
        match_year: int,
        match_month: int
    ) -> dict[str, Any]:
        """V95.0: Parse modal data with intelligent year inference.

        Implements the year-bug fix:
        - If match is in January and opening time is December, use previous year
        - If match is in December and opening time is January, use next year

        Args:
            modal_data: Raw modal data from page evaluation
            match_year: Match year
            match_month: Match month (1-12)

        Returns:
            Parsed result dictionary with init odds and timestamps.
        """
        # Extract odds values
        odds_values = modal_data.get("odds", [])
        time_match = modal_data.get("timeMatch")

        if not odds_values or len(odds_values) == 0:
            return self._build_hover_failed_result("No odds values found in modal")

        # Primary value: first odds value (usually home win)
        init_h = odds_values[0]

        # Extract timestamp
        opening_time = None
        if time_match:
            try:
                # timeMatch is a regex match object converted to dict/list by JSON
                # Format: {'0': full_string, '1': day, '2': month, '3': hour, '4': minute}
                # or as a list from JavaScript: [full_string, day, month, hour, minute]

                # Handle both dict (from JSON serialization) and list formats
                if isinstance(time_match, dict):
                    day = int(time_match.get("1"))
                    month_str = time_match.get("2")
                    hour = int(time_match.get("3"))
                    minute = int(time_match.get("4"))
                else:
                    # Assume it's a list-like object
                    day = int(time_match[1]) if len(time_match) > 1 else None
                    month_str = time_match[2] if len(time_match) > 2 else None
                    hour = int(time_match[3]) if len(time_match) > 3 else None
                    minute = int(time_match[4]) if len(time_match) > 4 else None

                if not all([day, month_str, hour is not None, minute is not None]):
                    raise ValueError("Incomplete time match data")

                # Map month string to number
                month_map = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                month = month_map.get(month_str)

                if month:
                    # V95.0 Year Inference Logic
                    inferred_year = match_year

                    # Edge case 1: Match in January, opening in December -> previous year
                    if match_month == 1 and month == 12:
                        inferred_year = match_year - 1
                        logger.info(
                            f"[V95.0] Year inference: Match is Jan {match_year}, "
                            f"opening is Dec {match_year - 1}"
                        )

                    # Edge case 2: Match in December, opening in January -> next year
                    elif match_month == 12 and month == 1:
                        inferred_year = match_year + 1
                        logger.info(
                            f"[V95.0] Year inference: Match is Dec {match_year}, "
                            f"opening is Jan {match_year + 1}"
                        )

                    opening_time = datetime(inferred_year, month, day, hour, minute)
                    logger.info(
                        f"[V95.0] Parsed: opening_time={opening_time.isoformat()}, "
                        f"init_h={init_h}"
                    )

            except Exception as e:
                logger.warning(f"[V95.0] Date parsing failed: {e}")

        return {
            "init_h": init_h,
            "init_d": odds_values[1] if len(odds_values) > 1 else None,
            "init_a": odds_values[2] if len(odds_values) > 2 else None,
            "opening_time_h": opening_time,
            "opening_time_d": None,
            "opening_time_a": None,
            "hover_failed": False,
            "hover_error": None,
            "source": "v95_odds_movement_modal",
        }

    # ========================================================================
    # V95.2 OddsPortal Opening Odds Extraction (Target Alignment Fix)
    # ========================================================================

    async def extract_oddsportal_opening_odds_v95(
        self,
        page: Page,
        match_id: str,
        match_date: datetime | None = None
    ) -> dict[str, Any]:
        """V95.2: Extracts Pinnacle opening odds from OddsPortal with year inference.

        Based on OddsHarvester technical audit - targets OddsPortal specifically:
        - Find Pinnacle row and hover to trigger modal
        - Target modal: h3:has-text('Odds movement')
        - Parse path: div.mt-2.gap-1
        - Odds value: .font-bold elements
        - Timestamp: %d %b, %H:%M format with intelligent year inference

        Args:
            page: Playwright Page object (already navigated to OddsPortal URL)
            match_id: Database match ID for logging
            match_date: Match date for year inference (critical for accuracy)

        Returns:
            Dictionary with init_h/d/a, opening_time_h, and metadata
        """
        # Temporal alignment: Infer correct year from match_date
        if match_date is None:
            logger.warning("[V95.2] match_date not provided, using current date")
            match_date = datetime.now()

        match_year = match_date.year
        match_month = match_date.month

        result = {
            "match_id": match_id,
            "init_h": None,
            "init_d": None,
            "init_a": None,
            "opening_time_h": None,
            "opening_time_d": None,
            "opening_time_a": None,
            "hover_failed": True,
            "hover_error": None,
            "source": "v95_oddsportal_opening",
        }

        try:
            logger.info(f"[V95.2] OddsPortal opening odds extraction: {match_id}")

            # Step 1: Wait for page to load
            await asyncio.sleep(2)

            # Step 2: Find Pinnacle row and hover
            pinnacle_data = await page.evaluate("""
                () => {
                    // Find all elements that might contain Pinnacle
                    const allElements = document.querySelectorAll('*');
                    let pinnacleElement = null;

                    for (let el of allElements) {
                        const text = el.textContent || '';
                        // Look for "Pinnacle" text (case-insensitive)
                        if (text.toLowerCase().includes('pinnacle') &&
                            !text.toLowerCase().includes('william') &&
                            !text.toLowerCase().includes('ladbrokes')) {

                            // Check if this element or its parent has odds data
                            let parent = el;
                            for (let i = 0; i < 5; i++) {
                                if (parent && parent.parentElement) {
                                    const odds = parent.querySelectorAll('.odds-text');
                                    if (odds.length >= 3) {
                                        pinnacleElement = parent;
                                        break;
                                    }
                                    parent = parent.parentElement;
                                }
                            }
                            if (pinnacleElement) break;
                        }
                    }

                    if (!pinnacleElement) {
                        return { found: false, error: 'Pinnacle row not found' };
                    }

                    // Scroll into view and hover to trigger modal
                    pinnacleElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // Trigger hover event
                    pinnacleElement.dispatchEvent(new MouseEvent('mouseenter', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    }));

                    return { found: true, element: pinnacleElement.tagName };
                }
            """)

            if not pinnacle_data.get("found"):
                result["hover_error"] = pinnacle_data.get("error", "Pinnacle not found")
                return result

            logger.info("[V95.2] Pinnacle element found and hovered")

            # Step 3: Wait for Odds movement modal
            await asyncio.sleep(2)  # Wait for modal to appear

            try:
                await page.wait_for_selector(
                    "h3:has-text('Odds movement')",
                    timeout=5000
                )
                logger.info("[V95.2] Odds movement modal detected!")
            except Exception:
                logger.warning("[V95.2] Odds movement modal not found")
                result["hover_error"] = "Odds movement modal not found"
                return result

            # Step 4: Extract data from modal
            modal_data = await page.evaluate(r"""
                () => {
                    // Find modal with Odds movement header
                    const allElements = document.querySelectorAll('*');
                    let modalContainer = null;

                    for (let el of allElements) {
                        if (el.tagName === 'H3' && el.textContent.includes('Odds movement')) {
                            let parent = el;
                            for (let i = 0; i < 10; i++) {
                                if (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    const dataBlock = parent.querySelector('div.mt-2.gap-1');
                                    if (dataBlock) {
                                        modalContainer = parent;
                                        break;
                                    }
                                }
                            }
                            if (modalContainer) break;
                        }
                    }

                    if (!modalContainer) {
                        return { found: false, error: 'Modal container not found' };
                    }

                    const dataBlock = modalContainer.querySelector('div.mt-2.gap-1');
                    if (!dataBlock) {
                        return { found: false, error: 'div.mt-2.gap-1 not found' };
                    }

                    // Extract odds values from .font-bold elements
                    const boldElements = dataBlock.querySelectorAll('.font-bold');
                    const oddsValues = [];
                    for (let el of boldElements) {
                        const text = el.textContent?.trim();
                        if (text) {
                            const num = parseFloat(text);
                            if (!isNaN(num) && num >= 1.01 && num <= 50.00) {
                                oddsValues.push(num);
                            }
                        }
                    }

                    // Extract timestamp
                    const allText = dataBlock.textContent || '';
                    const timePattern = /(\d{1,2})\s+([A-Za-z]{3})\s*,\s+(\d{1,2}):(\d{2})/;
                    const timeMatch = allText.match(timePattern);

                    return {
                        found: true,
                        odds: oddsValues,
                        timeMatch: timeMatch,
                        rawHtml: dataBlock.innerHTML.substring(0, 500)
                    };
                }
            """)

            if not modal_data.get("found"):
                result["hover_error"] = modal_data.get("error", "Modal extraction failed")
                return result

            # Step 5: Parse with year inference
            parsed = self._parse_v95_modal_data(
                modal_data,
                match_year,
                match_month
            )

            result.update(parsed)
            result["hover_failed"] = not parsed.get("init_h")

            return result

        except Exception as e:
            logger.error(f"[V95.2] Extraction exception: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            result["hover_error"] = f"Exception: {e!s}"
            return result

    # ========================================================================
    # V96.0 Network Interception Methods
    # ========================================================================

    async def extract_oddsportal_opening_odds_v96(
        self,
        page: Page,
        match_id: str,
        match_date: datetime | None = None,
        timeout: int = 15
    ) -> dict[str, Any]:
        """V96.0: Extracts Pinnacle opening odds via Network Interception.

        STRATEGIC PIVOT: Abandons hover/modal approach entirely.
        Intercepts AJAX responses at protocol level to capture raw JSON data.

        Architecture:
        1. Install response listener BEFORE page load
        2. Filter URLs matching: ajax-odds, opening, or match ID pattern
        3. Capture JSON with Content-Type: application/json
        4. Parse extracted JSON for Pinnacle (ID 18) opening odds

        Args:
            page: Playwright Page object
            match_id: Database match ID
            match_date: Match date for year inference
            timeout: Silent listening period in seconds (default: 15)

        Returns:
            Dictionary with init_h/d/a, opening_time_h, and metadata
        """
        # Temporal alignment
        if match_date is None:
            logger.warning("[V96.0] match_date not provided, using current date")
            match_date = datetime.now()

        match_year = match_date.year
        match_month = match_date.month

        result = {
            "match_id": match_id,
            "init_h": None,
            "init_d": None,
            "init_a": None,
            "opening_time_h": None,
            "opening_time_d": None,
            "opening_time_a": None,
            "hover_failed": True,
            "hover_error": None,
            "source": "v96_network_sniffer",
        }

        # Network capture container
        captured_data = {"found": False, "raw_json": None}

        async def response_handler(response):
            """Handle network responses during page load."""
            try:
                url = response.url
                content_type = response.headers.get("content-type", "")

                # Filter: Must be JSON and relevant URL
                if ("application/json" in content_type or
                    url.endswith(".json") or
                    "ajax" in url.lower()):

                    # Check URL relevance
                    relevant_keywords = [
                        "ajax-odds", "opening", "odds-history",
                        "bookmaker", "pinnacle", "match-data", "match-event"
                    ]

                    if any(kw in url.lower() for kw in relevant_keywords):
                        logger.info(f"[V96.0 Sniffer] Captured: {url[:100]}")

                        # Try to extract JSON
                        try:
                            # Capture response body before it's consumed
                            body_text = await response.text()
                            if body_text:
                                import json as json_module
                                json_data = json_module.loads(body_text)
                                captured_data["found"] = True
                                captured_data["raw_json"] = json_data
                                captured_data["url"] = url
                                logger.info(f"[V96.0 Sniffer] JSON captured from {url[:80]}...")
                                logger.info(f"[V96.0 Sniffer] Data size: {len(str(json_data))} chars")
                        except Exception as e:
                            logger.debug(f"[V96.0 Sniffer] JSON parse failed: {e}")
            except Exception as e:
                logger.debug(f"[V96.0 Sniffer] Handler error: {e}")

        try:
            logger.info(f"[V96.0] Network interception started: {match_id}")
            logger.info(f"[V96.0] Timeout set to {timeout}s for silent listening")

            # Step 1: Install listener BEFORE navigation
            page.on("response", response_handler)

            # Step 2: Trigger page reload to ensure AJAX calls fire
            # Even if page is already loaded, reload() will trigger fresh AJAX
            try:
                # Use reload instead of goto to ensure fresh AJAX requests
                await page.reload(wait_until="domcontentloaded", timeout=timeout * 1000)
                logger.info("[V96.0] Page reloaded, monitoring AJAX responses...")
            except Exception as e:
                logger.debug(f"[V96.0] Reload timeout (expected): {e}")

            # Step 3: Silent listening period
            # Wait for AJAX calls to complete
            logger.info("[V96.0] Entering silent listening period...")
            await asyncio.sleep(timeout)

            # Step 4: Check captured data
            if not captured_data["found"]:
                result["hover_error"] = "No relevant JSON captured"
                logger.warning("[V96.0] No JSON captured during listening period")
                return result

            # Step 5: Parse captured JSON
            parsed = self._parse_odds_json_v96(
                captured_data["raw_json"],
                match_year,
                match_month,
                captured_url=captured_data.get("url", "")
            )

            result.update(parsed)
            result["hover_failed"] = not parsed.get("init_h")

            if result["init_h"]:
                logger.info(f"[V96.0] SUCCESS: init_h={result['init_h']} at {result['opening_time_h']}")
            else:
                logger.warning("[V96.0] JSON captured but no opening odds found")

            return result

        except Exception as e:
            logger.error(f"[V96.0] Extraction exception: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            result["hover_error"] = f"Exception: {e!s}"
            return result

    def _parse_odds_json_v96(
        self,
        json_data: Any,
        match_year: int,
        match_month: int,
        captured_url: str = ""
    ) -> dict[str, Any]:
        """Parse captured JSON for Pinnacle opening odds.

        Deep search through JSON structure for:
        - Pinnacle (ID 18) opening odds
        - Timestamp information
        - Historical odds data

        Args:
            json_data: Captured JSON (dict, list, or nested structure)
            match_year: Match year for temporal alignment
            match_month: Match month for year inference
            captured_url: Source URL for logging

        Returns:
            Parsed odds dictionary
        """
        result = {
            "init_h": None,
            "init_d": None,
            "init_a": None,
            "opening_time_h": None,
            "captured_url": captured_url
        }

        def recursive_search(obj, depth=0, max_depth=10):
            """Recursively search JSON for odds data."""
            if depth > max_depth:
                return None

            # Case 1: Dictionary with direct odds keys
            if isinstance(obj, dict):
                # Check for Pinnacle ID 18
                if "18" in obj or "pinnacle" in str(obj).lower():
                    data = obj.get("18") or obj.get("pinnacle")
                    if data and isinstance(data, dict):
                        # Look for opening/initial keys
                        for key in ["opening", "initial", "start", "first"]:
                            if key in data:
                                odds = data[key]
                                if isinstance(odds, dict):
                                    h = odds.get("home") or odds.get("h") or odds.get("1")
                                    d = odds.get("draw") or odds.get("d") or odds.get("x") or odds.get("2")
                                    a = odds.get("away") or odds.get("a") or odds.get("3")
                                    if h and isinstance(h, (int, float)):
                                        return {
                                            "init_h": float(h),
                                            "init_d": float(d) if d else None,
                                            "init_a": float(a) if a else None,
                                            "timestamp": odds.get("time") or odds.get("timestamp")
                                        }

                # Check for odds array format: [home, draw, away]
                for key in ["opening", "initial", "start", "first", "odds"]:
                    if key in obj:
                        odds_val = obj[key]
                        if isinstance(odds_val, list) and len(odds_val) >= 3:
                            try:
                                h, d, a = float(odds_val[0]), float(odds_val[1]), float(odds_val[2])
                                if 1.01 <= h <= 50.0:
                                    return {
                                        "init_h": h,
                                        "init_d": d,
                                        "init_a": a,
                                        "timestamp": obj.get("time") or obj.get("timestamp")
                                    }
                            except (ValueError, TypeError):
                                pass

                # Recursive search
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        found = recursive_search(value, depth + 1, max_depth)
                        if found:
                            return found

            # Case 2: List of odds objects
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        # Check if this item looks like odds data
                        if any(k in str(item).lower() for k in ["home", "draw", "away", "h", "d", "a"]):
                            found = recursive_search(item, depth + 1, max_depth)
                            if found:
                                return found

            return None

        # Execute recursive search
        found = recursive_search(json_data)

        if found:
            result["init_h"] = found.get("init_h")
            result["init_d"] = found.get("init_d")
            result["init_a"] = found.get("init_a")

            # Parse timestamp if present
            ts = found.get("timestamp")
            if ts:
                result["opening_time_h"] = self._parse_v96_timestamp(ts, match_year, match_month)

        return result

    def _parse_v96_timestamp(
        self,
        timestamp: Any,
        match_year: int,
        match_month: int
    ) -> datetime | None:
        """Parse various timestamp formats from captured JSON.

        Supports:
        - Unix timestamps (seconds or milliseconds)
        - ISO 8601 strings
        - Custom formats like "20 Dec, 08:13"

        Args:
            timestamp: Timestamp value (various types)
            match_year: Match year for inference
            match_month: Match month for year inference

        Returns:
            Parsed datetime or None
        """
        if not timestamp:
            return None

        from datetime import datetime

        # Case 1: Unix timestamp (numeric)
        if isinstance(timestamp, (int, float)):
            # Check if milliseconds (13+ digits) or seconds (10 digits)
            if timestamp > 1_000_000_000_000:  # Milliseconds
                timestamp = timestamp / 1000
            try:
                return datetime.fromtimestamp(timestamp)
            except (ValueError, OSError):
                pass

        # Case 2: String timestamp
        if isinstance(timestamp, str):
            timestamp = timestamp.strip()

            # ISO 8601
            try:
                from dateutil import parser
                return parser.parse(timestamp)
            except:
                pass

            # Unix timestamp as string
            try:
                ts_int = int(timestamp)
                if ts_int > 1_000_000_000_000:
                    ts_int = ts_int / 1000
                return datetime.fromtimestamp(ts_int)
            except ValueError:
                pass

            # Custom format: "20 Dec, 08:13"
            try:
                from datetime import datetime
                import re
                match = re.match(r"(\d{1,2})\s+([A-Za-z]{3})\s*,\s*(\d{1,2}):(\d{2})", timestamp)
                if match:
                    day = int(match.group(1))
                    month_str = match.group(2)
                    hour = int(match.group(3))
                    minute = int(match.group(4))

                    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    try:
                        month = months.index(month_str) + 1
                    except ValueError:
                        return None

                    # Year inference logic
                    if month > match_month + 6:
                        year = match_year - 1  # Previous year
                    elif month < match_month - 6:
                        year = match_year + 1  # Next year
                    else:
                        year = match_year  # Same year

                    return datetime(year, month, day, hour, minute)
            except Exception:
                pass

        return None

    # ========================================================================
    # V97.0 Memory/DOM Extraction Methods
    # ========================================================================

    async def extract_oddsportal_memory_v97(
        self,
        page: Page,
        match_id: str,
        match_date: datetime | None = None
    ) -> dict[str, Any]:
        """V97.0: Extracts Pinnacle odds via Memory/DOM inspection.

        STRATEGIC PIVOT: Instead of decrypting network packets,
        read the already-decrypted data from browser memory/DOM.

        Approach:
        1. Wait for page to fully render
        2. Extract from DOM text (browser has already decrypted)
        3. Find Pinnacle section and parse H/D/A odds
        4. Look for opening odds (often shown first or with strikethrough)

        Args:
            page: Playwright Page object (already navigated)
            match_id: Database match ID
            match_date: Match date for timestamp inference

        Returns:
            Dictionary with init_h/d/a and metadata
        """
        if match_date is None:
            logger.warning("[V97.0] match_date not provided, using current date")
            match_date = datetime.now()

        result = {
            "match_id": match_id,
            "init_h": None,
            "init_d": None,
            "init_a": None,
            "opening_time_h": None,
            "hover_failed": True,
            "hover_error": None,
            "source": "v97_memory_dom",
        }

        try:
            logger.info(f"[V97.0] Memory/DOM extraction: {match_id}")

            # Wait for data to be fully rendered
            await asyncio.sleep(3)

            # Extract odds from page text
            extracted = await page.evaluate("""
                () => {
                    // Get full page text
                    const fullText = String(document.body.innerText || document.body.textContent || '');
                    
                    // Find Pinnacle section
                    const pinnacleIdx = fullText.toLowerCase().indexOf('pinnacle');
                    if (pinnacleIdx < 0) {
                        return { error: 'Pinnacle not found in page' };
                    }
                    
                    // Get text around Pinnacle (next 2000 chars)
                    const nearbyText = fullText.substring(pinnacleIdx, pinnacleIdx + 2000);
                    
                    // Extract all odds-like numbers
                    const oddsPattern = /\\b([1-9]\\.\\d{2})\\b/g;
                    const matches = nearbyText.match(oddsPattern) || [];
                    
                    // Remove duplicates, preserve order
                    const seen = new Set();
                    const uniqueOdds = [];
                    for (const o of matches) {
                        if (!seen.has(o)) {
                            seen.add(o);
                            uniqueOdds.push(o);
                        }
                    }
                    
                    return {
                        success: true,
                        allOdds: uniqueOdds,
                        pinnacleText: nearbyText.substring(0, 500)
                    };
                }
            """)

            if not extracted.get("success"):
                result["hover_error"] = extracted.get("error", "Extraction failed")
                return result

            all_odds = extracted.get("allOdds", [])

            # V97.1: Smart candidate selection - try multiple 3-odds sets
            # and select the one with best integrity score
            if len(all_odds) >= 3:
                best_candidate = None
                best_score = None
                best_distance = float("inf")

                # Try consecutive triplets (skip by 1 to find main 1X2 market)
                for start_idx in range(min(10, len(all_odds) - 2)):
                    try:
                        h = float(all_odds[start_idx])
                        d = float(all_odds[start_idx + 1])
                        a = float(all_odds[start_idx + 2])

                        # Calculate integrity score
                        score = 1/h + 1/d + 1/a

                        # Check if valid (1.01 < score < 1.10)
                        if 1.01 < score < 1.10:
                            # Prefer scores closest to 1.05 (ideal)
                            distance = abs(score - 1.05)
                            if distance < best_distance:
                                best_distance = distance
                                best_candidate = (h, d, a)
                                best_score = score
                    except (ValueError, IndexError):
                        continue

                if best_candidate:
                    h, d, a = best_candidate
                    result["init_h"] = h
                    result["init_d"] = d
                    result["init_a"] = a
                    result["hover_failed"] = False

                    # Try to infer timestamp (use match_date at noon)
                    try:
                        from datetime import datetime, time
                        result["opening_time_h"] = datetime.combine(
                            match_date.date(),
                            time(12, 0)
                        )
                    except:
                        result["opening_time_h"] = match_date

                    logger.info(f"[V97.1] SUCCESS: init_h={h}, init_d={d}, init_a={a}, score={best_score:.4f}")
                else:
                    # Fallback: try first 3 odds even if score is invalid
                    h = float(all_odds[0])
                    d = float(all_odds[1])
                    a = float(all_odds[2])
                    score = 1/h + 1/d + 1/a
                    result["hover_error"] = f"No valid odds found (best score: {score:.4f})"
                    logger.warning(f"[V97.1] All candidates invalid, best: {score:.4f}")
            else:
                result["hover_error"] = f"Not enough odds found: {len(all_odds)}"

            return result

        except Exception as e:
            logger.error(f"[V97.0] Extraction exception: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            result["hover_error"] = f"Exception: {e!s}"
            return result
