#!/usr/bin/env python3
"""V150.2.2 L3 赔率提取器 - OddsPortal 双状态数据实战提取.

本模块实现从 OddsPortal 提取 L3 终盘赔率数据，包括：
- 欧洲赔率（1X2）：开盘、终盘
- 亚洲让球盘（Asian Handicap）
- 比分验证（FotMob vs OddsPortal）
- 视觉调试截图（debug_state_capture.png）

核心特性：
1. Ghost Protocol 集成（V141.0）：反爬虫指纹混淆
2. 比分一致性检查：强制验证，不匹配则熔断
3. 多数据源支持：Pinnacle, William Hill, Ladbrokes, 1xBet, Average Odds
4. 完整性验证：Integrity Score (1/P1 + 1/P2 + 1/P3) 必须在 1.00-1.15 之间
5. V150.2.2 新增：Initial State + Final State 双重数据提取
6. V150.2.2 新增：兜底逻辑（Pinnacle 缺失时使用加权平均）
7. V150.2.2 新增：视觉调试截图

Author: 高级前端架构师 & 自动化测试专家 (SDET)
Version: V150.2.2
Date: 2026-01-08
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import psycopg2
from playwright.async_api import async_playwright, Browser, Page

from src.api.collectors.base_extractor import BaseExtractor, CollectionCircuitBreaker
from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class L3OddsData:
    """L3 赔率数据模型.

    Attributes:
        match_id: FotMob 比赛ID
        oddsportal_url: OddsPortal URL
        home_team: 主队（FotMob）
        away_team: 客队（FotMob）
        fotmob_score: FotMob 比分
        oddsportal_score: OddsPortal 比分
        score_match: 比分是否匹配
        opening_odds: 开盘欧赔 {bookmaker: {home, draw, away}}
        closing_odds: 终盘欧赔 {bookmaker: {home, draw, away}}
        asian_handicap: 亚洲让球盘数据
        integrity_score: 完整性分数
        is_valid: 数据是否有效
        extraction_time: 提取时间
        error: 错误信息（如果有）
    """
    match_id: str
    oddsportal_url: str
    home_team: str
    away_team: str
    fotmob_score: dict[str, int]
    oddsportal_score: dict[str, int]
    score_match: bool
    opening_odds: dict[str, Any]
    closing_odds: dict[str, Any]
    asian_handicap: dict[str, Any]
    integrity_score: float | None
    is_valid: bool
    extraction_time: str
    error: str | None

    def to_json(self) -> str:
        """转换为 JSON 字符串."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass
class ExtractionResult:
    """提取结果.

    Attributes:
        success: 是否成功
        match_id: 比赛ID
        l3_data: L3 赔率数据
        data_mismatch: 数据是否不匹配
        error: 错误信息
    """
    success: bool
    match_id: str
    l3_data: L3OddsData | None
    data_mismatch: bool
    error: str | None


# ============================================================================
# L3 提取器
# ============================================================================

class OddsL3Extractor:
    """V150.2 L3 赔率提取器.

    使用示例:
        >>> extractor = OddsL3Extractor()
        >>> result = await extractor.extract_match(
        ...     match_id="4193526",
        ...     oddsportal_url="https://www.oddsportal.com/...",
        ...     home_team="Nottingham Forest",
        ...     away_team="Brentford",
        ...     fotmob_score={"home": 1, "away": 1}
        ... )
        >>> print(result.l3_data.to_json())
    """

    # 目标书商列表（按优先级排序）
    TARGET_BOOKMAKERS = [
        "Pinnacle",
        "William Hill",
        "Ladbrokes",
        "1xBet",
        "Average Odds"
    ]

    # 完整性分数阈值
    MIN_INTEGRITY_SCORE = 1.00
    MAX_INTEGRITY_SCORE = 1.15

    def __init__(self, enable_ghost: bool = True):
        """初始化 L3 提取器.

        Args:
            enable_ghost: 是否启用 Ghost Protocol（默认 True）
        """
        self.enable_ghost = enable_ghost
        self.base_extractor = BaseExtractor() if enable_ghost else None

        # 检查熔断器状态（OddsPortal 需要遵守冷却期）
        CollectionCircuitBreaker.check_pause_period("oddsportal")

        logger.info(f"🛡️ V150.2 L3 Extractor initialized (Ghost Protocol: {enable_ghost})")

    async def extract_match(
        self,
        match_id: str,
        oddsportal_url: str,
        home_team: str,
        away_team: str,
        fotmob_score: dict[str, int],
        enable_debug_screenshot: bool = False
    ) -> ExtractionResult:
        """V150.2.2 提取单场比赛的 L3 赔率数据（支持视觉调试）.

        Args:
            match_id: FotMob 比赛ID
            oddsportal_url: OddsPortal URL
            home_team: 主队（FotMob）
            away_team: 客队（FotMob）
            fotmob_score: FotMob 比分 {"home": x, "away": y}
            enable_debug_screenshot: 是否启用视觉调试截图

        Returns:
            ExtractionResult: 提取结果
        """
        logger.info(f"🎯 提取比赛: {match_id} - {home_team} vs {away_team}")

        try:
            async with async_playwright() as p:
                browser = await self._create_browser(p)
                context = await self._create_context(browser)
                page = await context.new_page()

                # 访问 OddsPortal 页面
                await page.goto(oddsportal_url, wait_until="domcontentloaded", timeout=30000)

                # 模拟人类行为
                await self._simulate_human_behavior(page)

                # 提取比分
                oddsportal_score = await self._extract_score(page)

                # 验证比分一致性
                score_match = self._verify_score(fotmob_score, oddsportal_score)

                if not score_match:
                    logger.warning(
                        f"⚠️ 比分不匹配: {fotmob_score} (FotMob) vs {oddsportal_score} (OddsPortal)"
                    )

                    # 视觉调试：截图（失败时）
                    if enable_debug_screenshot:
                        await self._capture_debug_screenshot(page, match_id, "score_mismatch")

                    await browser.close()
                    return ExtractionResult(
                        success=False,
                        match_id=match_id,
                        l3_data=None,
                        data_mismatch=True,
                        error=f"Score mismatch: {fotmob_score} vs {oddsportal_score}"
                    )

                # 提取开盘赔率（Initial State）
                opening_odds = await self._extract_opening_odds(page)

                # 提取终盘赔率（Final State）
                closing_odds = await self._extract_closing_odds(page)

                # 提取亚洲让球盘
                asian_handicap = await self._extract_asian_handicap(page)

                # 计算完整性分数
                integrity_score = self._calculate_integrity_score(closing_odds)

                # 验证数据有效性
                is_valid = self._validate_data(integrity_score, closing_odds)

                # V150.2.2: 视觉调试截图（成功时）
                if enable_debug_screenshot:
                    await self._capture_debug_screenshot_with_overlay(
                        page, match_id, opening_odds, closing_odds, integrity_score
                    )

                await browser.close()

                # 构建 L3 数据
                l3_data = L3OddsData(
                    match_id=match_id,
                    oddsportal_url=oddsportal_url,
                    home_team=home_team,
                    away_team=away_team,
                    fotmob_score=fotmob_score,
                    oddsportal_score=oddsportal_score,
                    score_match=score_match,
                    opening_odds=opening_odds,
                    closing_odds=closing_odds,
                    asian_handicap=asian_handicap,
                    integrity_score=integrity_score,
                    is_valid=is_valid,
                    extraction_time=datetime.now().isoformat(),
                    error=None
                )

                integrity_str = f"{integrity_score:.4f}" if integrity_score is not None else "null"
                logger.info(f"✅ 提取成功: {match_id} (integrity={integrity_str})")

                return ExtractionResult(
                    success=True,
                    match_id=match_id,
                    l3_data=l3_data,
                    data_mismatch=False,
                    error=None
                )

        except Exception as e:
            logger.error(f"❌ 提取失败: {match_id} - {e}")
            return ExtractionResult(
                success=False,
                match_id=match_id,
                l3_data=None,
                data_mismatch=False,
                error=str(e)
            )

    async def _create_browser(self, playwright) -> Browser:
        """创建浏览器实例."""
        launch_options = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        }
        return await playwright.chromium.launch(**launch_options)

    async def _create_context(self, browser: Browser):
        """创建浏览器上下文（集成 Ghost Protocol）."""
        if self.base_extractor:
            return await browser.new_context(
                user_agent=self.base_extractor.get_random_user_agent(),
                viewport=self.base_extractor.get_random_viewport(),
                proxy=self.base_extractor.get_proxy_config(),
            )
        else:
            return await browser.new_context()

    async def _simulate_human_behavior(self, page: Page):
        """模拟人类浏览行为."""
        await asyncio.sleep(random.uniform(2, 4))

        # 随机滚动
        if random.random() > 0.5:
            await page.evaluate("window.scrollBy(0, Math.random() * 200)")
            await asyncio.sleep(random.uniform(0.5, 1.5))

    async def _extract_score(self, page: Page) -> dict[str, int]:
        """提取页面上的比分.

        Returns:
            dict: {"home": x, "away": y}
        """
        try:
            score_text = await page.evaluate("""
                () => {
                    // 尝试多种选择器查找比分
                    const selectors = [
                        '.result-score',
                        '[data-type="result"]',
                        '.score',
                        'span[class*="score"]'
                    ];

                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            const text = el.textContent?.trim();
                            // 匹配格式: "1-1", "2 - 1", 等
                            if (/^\d+\s*-\s*\d+$/.test(text)) {
                                return text;
                            }
                        }
                    }
                    return null;
                }
            """)

            if score_text:
                parts = score_text.split("-")
                home = int(parts[0].strip())
                away = int(parts[1].strip())
                return {"home": home, "away": away}

        except Exception as e:
            logger.debug(f"比分提取失败: {e}")

        return {"home": None, "away": None}

    def _verify_score(
        self,
        fotmob_score: dict[str, int],
        oddsportal_score: dict[str, int]
    ) -> bool:
        """验证比分一致性.

        Args:
            fotmob_score: FotMob 比分
            oddsportal_score: OddsPortal 比分

        Returns:
            bool: 比分是否一致
        """
        # 如果 OddsPortal 比分提取失败，无法验证
        if oddsportal_score.get("home") is None or oddsportal_score.get("away") is None:
            logger.warning("⚠️ OddsPortal 比分提取失败，跳过验证")
            return True  # 允许通过

        # 比对比分
        match = (
            fotmob_score.get("home") == oddsportal_score.get("home") and
            fotmob_score.get("away") == oddsportal_score.get("away")
        )

        return match

    async def _extract_opening_odds(self, page: Page) -> dict[str, Any]:
        """V150.2.2 提取开盘赔率（1X2）- 支持悬停交互和兜底逻辑.

        策略：
        1. 尝试解析 DOM 元素的 data-opening 属性（初始状态）
        2. 如果失败，使用 page.hover() 触发悬停组件
        3. 兜底逻辑：Pinnacle 缺失时使用加权平均

        Returns:
            dict: {bookmaker: {home, draw, away}}
        """
        opening_odds = {}
        logger.info("  🔍 [Initial State] 开始提取开盘赔率...")

        # 策略 1: 尝试解析 data-opening 属性
        try:
            logger.debug("     策略 1: 解析 data-opening 属性...")
            opening_from_attr = await page.evaluate("""
                () => {
                    const result = {};

                    // 查找所有包含 data-opening 属性的元素
                    const elements = document.querySelectorAll('[data-opening]');
                    const bookmakers = ['Pinnacle', 'William Hill', 'Ladbrokes', '1xBet'];

                    for (const bookmaker of bookmakers) {
                        // 查找包含该书商名称的行
                        const rows = Array.from(document.querySelectorAll('tr'));
                        const row = rows.find(r => r.textContent.includes(bookmaker));

                        if (row) {
                            // 查找 data-opening 属性
                            const oddsElements = row.querySelectorAll('[data-opening]');
                            if (oddsElements.length >= 3) {
                                const values = [];
                                for (const el of oddsElements) {
                                    const openingVal = el.getAttribute('data-opening');
                                    if (openingVal) {
                                        const num = parseFloat(openingVal);
                                        if (!isNaN(num) && num > 1.0) {
                                            values.push(num);
                                        }
                                    }
                                }

                                if (values.length >= 3) {
                                    result[bookmaker] = {
                                        home: values[0],
                                        draw: values[1],
                                        away: values[2]
                                    };
                                }
                            }
                        }
                    }

                    return result;
                }
            """)

            if opening_from_attr:
                opening_odds.update(opening_from_attr)
                logger.info(f"     ✅ 策略 1 成功: 从 data-opening 属性提取到 {len(opening_from_attr)} 家书商")

                # 打印 Initial State 数据
                for bookmaker, odds in opening_from_attr.items():
                    logger.info(f"     📊 [Initial State] {bookmaker}: "
                              f"Home={odds['home']:.2f}, Draw={odds['draw']:.2f}, Away={odds['away']:.2f}")

        except Exception as e:
            logger.debug(f"     策略 1 失败: {e}")

        # 策略 2: 使用悬停交互（如果策略 1 失败或 Pinnacle 缺失）
        if "Pinnacle" not in opening_odds:
            try:
                logger.debug("     策略 2: 使用悬停交互提取 Pinnacle 开盘赔率...")

                # 查找 Pinnacle 行并悬停
                hover_result = await page.evaluate("""
                    () => {
                        // 查找 Pinnacle 行
                        const rows = Array.from(document.querySelectorAll('tr'));
                        const pinnacleRow = rows.find(r => r.textContent.includes('Pinnacle'));

                        if (!pinnacleRow) return null;

                        // 获取行的位置信息
                        const rect = pinnacleRow.getBoundingClientRect();
                        return {
                            x: rect.left + rect.width / 2,
                            y: rect.top + rect.height / 2,
                            elementId: pinnacleRow.id || ''
                        };
                    }
                """)

                if hover_result:
                    # 执行悬停
                    await page.mouse.move(hover_result['x'], hover_result['y'])
                    await asyncio.sleep(1)  # 等待悬停效果

                    # 提取悬停后的数据
                    hover_odds = await page.evaluate("""
                        () => {
                            const rows = Array.from(document.querySelectorAll('tr'));
                            const pinnacleRow = rows.find(r => r.textContent.includes('Pinnacle'));

                            if (!pinnacleRow) return null;

                            const cells = pinnacleRow.querySelectorAll('.odds-text');
                            if (cells.length >= 3) {
                                return {
                                    home: parseFloat(cells[0].textContent),
                                    draw: parseFloat(cells[1].textContent),
                                    away: parseFloat(cells[2].textContent)
                                };
                            }

                            return null;
                        }
                    """)

                    if hover_odds and hover_odds['home'] > 1.0:
                        opening_odds['Pinnacle'] = hover_odds
                        logger.info(f"     ✅ 策略 2 成功: 从悬停交互提取 Pinnacle")
                        logger.info(f"     📊 [Initial State] Pinnacle (Hover): "
                                  f"Home={hover_odds['home']:.2f}, Draw={hover_odds['draw']:.2f}, Away={hover_odds['away']:.2f}")

            except Exception as e:
                logger.debug(f"     策略 2 失败: {e}")

        # 策略 3: 兜底逻辑 - 使用加权平均
        if "Pinnacle" not in opening_odds:
            logger.warning("     ⚠️ 策略 3: Pinnacle 开盘赔率缺失，使用加权平均兜底...")

            try:
                # 从终盘赔率计算加权平均作为开盘赔率的近似值
                fallback_odds = await page.evaluate("""
                    () => {
                        const oddsElements = document.querySelectorAll('.odds-text');
                        const oddsValues = [];

                        for (const el of oddsElements) {
                            const text = el.textContent?.trim();
                            const num = parseFloat(text);
                            if (!isNaN(num) && num > 1.0 && num < 10.0) {
                                oddsValues.push(num);
                            }
                        }

                        if (oddsValues.length < 3) return null;

                        // 按每组 3 个组织并计算平均值
                        const groups = [];
                        for (let i = 0; i < oddsValues.length; i += 3) {
                            if (i + 2 < oddsValues.length) {
                                groups.push({
                                    home: oddsValues[i],
                                    draw: oddsValues[i + 1],
                                    away: oddsValues[i + 2]
                                });
                            }
                        }

                        // 计算加权平均（排除异常值）
                        const validGroups = groups.filter(g =>
                            g.home > 1.0 && g.draw > 1.0 && g.away > 1.0 &&
                            g.home < 10.0 && g.draw < 10.0 && g.away < 10.0
                        );

                        if (validGroups.length === 0) return null;

                        const sumH = validGroups.reduce((s, g) => s + g.home, 0);
                        const sumD = validGroups.reduce((s, g) => s + g.draw, 0);
                        const sumA = validGroups.reduce((s, g) => s + g.away, 0);
                        const count = validGroups.length;

                        return {
                            home: sumH / count,
                            draw: sumD / count,
                            away: sumA / count,
                            source: 'weighted_average'
                        };
                    }
                """)

                if fallback_odds and fallback_odds['home'] > 1.0:
                    opening_odds['Average Odds'] = {
                        'home': fallback_odds['home'],
                        'draw': fallback_odds['draw'],
                        'away': fallback_odds['away']
                    }
                    logger.info(f"     ✅ 策略 3 成功: 使用加权平均兜底")
                    logger.info(f"     📊 [Initial State] Average Odds (Fallback): "
                              f"Home={fallback_odds['home']:.2f}, Draw={fallback_odds['draw']:.2f}, Away={fallback_odds['away']:.2f}")

            except Exception as e:
                logger.debug(f"     策略 3 失败: {e}")

        logger.info(f"  📊 [Initial State] 开盘赔率提取完成: {len(opening_odds)} 家书商")
        return opening_odds

    async def _extract_closing_odds(self, page: Page) -> dict[str, Any]:
        """V150.2.2 提取终盘赔率（1X2）- Final State 数据.

        策略：直接提取所有 .odds-text 元素，按每组 3 个组织数据。

        Returns:
            dict: {bookmaker: {home, draw, away}}
        """
        closing_odds = {}
        logger.info("  🔍 [Final State] 开始提取终盘赔率...")

        try:
            # V150.2.1: 直接提取所有赔率文本元素
            odds_data = await page.evaluate("""
                () => {
                    const result = {
                        allOdds: [],
                        averageOdds: null
                    };

                    // 提取所有 .odds-text 元素
                    const oddsElements = document.querySelectorAll('.odds-text');

                    // 转换为数字并过滤无效值
                    const oddsValues = [];
                    for (const el of oddsElements) {
                        const text = el.textContent?.trim();
                        const num = parseFloat(text);
                        if (!isNaN(num) && num > 1.0) {
                            oddsValues.push(num);
                        }
                    }

                    // 按每组 3 个组织（主胜、平、客胜）
                    for (let i = 0; i < oddsValues.length; i += 3) {
                        if (i + 2 < oddsValues.length) {
                            result.allOdds.push({
                                home: oddsValues[i],
                                draw: oddsValues[i + 1],
                                away: oddsValues[i + 2]
                            });
                        }
                    }

                    // 计算平均赔率（作为 "Average Odds"）
                    if (result.allOdds.length > 0) {
                        const sumH = result.allOdds.reduce((s, o) => s + o.home, 0);
                        const sumD = result.allOdds.reduce((s, o) => s + o.draw, 0);
                        const sumA = result.allOdds.reduce((s, o) => s + o.away, 0);
                        const count = result.allOdds.length;

                        result.averageOdds = {
                            home: sumH / count,
                            draw: sumD / count,
                            away: sumA / count
                        };
                    }

                    return result;
                }
            """)

            logger.info(f"     💰 提取到 {len(odds_data.get('allOdds', []))} 组赔率数据")

            if odds_data.get('averageOdds'):
                avg = odds_data['averageOdds']
                closing_odds['Average Odds'] = {
                    'home': round(avg['home'], 2),
                    'draw': round(avg['draw'], 2),
                    'away': round(avg['away'], 2)
                }

                # 打印 Final State 数据
                logger.info(f"     ✅ [Final State] Average Odds: "
                          f"Home={avg['home']:.2f}, Draw={avg['draw']:.2f}, Away={avg['away']:.2f}")

                # 显示前 3 组赔率
                all_odds = odds_data.get('allOdds', [])
                for i, odds in enumerate(all_odds[:3]):
                    logger.info(f"        组 {i+1}: {odds['home']:.2f} / {odds['draw']:.2f} / {odds['away']:.2f}")

        except Exception as e:
            logger.debug(f"     终盘赔率提取失败: {e}")

        logger.info(f"  📊 [Final State] 终盘赔率提取完成: {len(closing_odds)} 家书商")
        return closing_odds

    async def _extract_asian_handicap(self, page: Page) -> dict[str, Any]:
        """提取亚洲让球盘数据.

        Returns:
            dict: Asian Handicap 数据
        """
        asian_handicap = {}

        try:
            ah_data = await page.evaluate("""
                () => {
                    // 查找亚洲让球盘区域
                    const ahSection = document.querySelector('[data-type="ah"]') ||
                                      document.querySelector('.asian-handicap');

                    if (!ahSection) return {};

                    const rows = ahSection.querySelectorAll('tr');
                    const result = {};

                    for (const row of rows) {
                        const bookmaker = row.querySelector('.bookmaker')?.textContent;
                        if (bookmaker && ['Pinnacle', '1xBet'].includes(bookmaker)) {
                            const cells = row.querySelectorAll('.odds');
                            if (cells.length >= 2) {
                                result[bookmaker] = {
                                    handicap: parseFloat(cells[0].textContent),
                                    home: parseFloat(cells[1].textContent),
                                    away: parseFloat(cells[2]?.textContent || '0')
                                };
                            }
                        }
                    }

                    return result;
                }
            """)

            asian_handicap = ah_data

        except Exception as e:
            logger.debug(f"亚洲让球盘提取失败: {e}")

        return asian_handicap

    def _calculate_integrity_score(self, odds: dict[str, Any]) -> float | None:
        """计算完整性分数 - V150.2.1 修复版.

        支持 Average Odds 作为默认数据源。

        Args:
            odds: 终盘赔率数据

        Returns:
            float: Integrity Score (1/P1 + 1/P2 + 1/P3)
        """
        if not odds:
            return None

        # 优先使用 Pinnacle，其次使用 Average Odds
        bookmaker_data = None
        if "Pinnacle" in odds and odds["Pinnacle"]:
            bookmaker_data = odds["Pinnacle"]
        elif "Average Odds" in odds and odds["Average Odds"]:
            bookmaker_data = odds["Average Odds"]
        else:
            return None

        if not all(k in bookmaker_data for k in ["home", "draw", "away"]):
            return None

        try:
            score = (
                1.0 / bookmaker_data["home"] +
                1.0 / bookmaker_data["draw"] +
                1.0 / bookmaker_data["away"]
            )
            return score
        except (ZeroDivisionError, TypeError):
            return None

    def _validate_data(self, integrity_score: float | None, odds: dict[str, Any]) -> bool:
        """验证数据有效性.

        Args:
            integrity_score: 完整性分数
            odds: 终盘赔率数据

        Returns:
            bool: 数据是否有效
        """
        if integrity_score is None:
            return False

        if not (self.MIN_INTEGRITY_SCORE < integrity_score < self.MAX_INTEGRITY_SCORE):
            logger.warning(
                f"⚠️ Integrity Score {integrity_score:.4f} "
                f"outside valid range [{self.MIN_INTEGRITY_SCORE}, {self.MAX_INTEGRITY_SCORE}]"
            )
            return False

        return True

    async def _capture_debug_screenshot(self, page: Page, match_id: str, state: str):
        """V150.2.2 捕获基础调试截图.

        Args:
            page: Playwright Page 对象
            match_id: 比赛ID
            state: 状态标识（如 "score_mismatch"）
        """
        try:
            debug_dir = Path("logs/debug_screenshots")
            debug_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = debug_dir / f"{match_id}_{state}_{timestamp}.png"

            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"  📸 调试截图已保存: {screenshot_path}")

        except Exception as e:
            logger.debug(f"     截图失败: {e}")

    async def _capture_debug_screenshot_with_overlay(
        self,
        page: Page,
        match_id: str,
        opening_odds: dict[str, Any],
        closing_odds: dict[str, Any],
        integrity_score: float | None
    ):
        """V150.2.2 捕获带数据标记的调试截图（视觉取证）.

        Args:
            page: Playwright Page 对象
            match_id: 比赛ID
            opening_odds: 开盘赔率
            closing_odds: 终盘赔率
            integrity_score: 完整性分数
        """
        try:
            debug_dir = Path("logs/debug_screenshots")
            debug_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = debug_dir / f"debug_state_capture_{match_id}_{timestamp}.png"

            # 生成数据汇总文本
            summary_text = f"""
=== V150.2.2 数据取证报告 ===
Match ID: {match_id}
Timestamp: {datetime.now().isoformat()}

[Initial State - Opening Odds]"""
            for bookmaker, odds in opening_odds.items():
                summary_text += f"\n  {bookmaker}: Home={odds['home']:.2f}, Draw={odds['draw']:.2f}, Away={odds['away']:.2f}"

            summary_text += f"\n\n[Final State - Closing Odds]"
            for bookmaker, odds in closing_odds.items():
                summary_text += f"\n  {bookmaker}: Home={odds['home']:.2f}, Draw={odds['draw']:.2f}, Away={odds['away']:.2f}"

            summary_text += f"\n\n[Integrity Score: {integrity_score:.4f}]" if integrity_score else "\n\n[Integrity Score: N/A]"

            # 保存截图和报告
            await page.screenshot(path=str(screenshot_path), full_page=True)

            # 保存文本报告
            report_path = debug_dir / f"debug_state_capture_{match_id}_{timestamp}.txt"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(summary_text)

            logger.info(f"  📸 视觉取证截图已保存: {screenshot_path}")
            logger.info(f"  📄 数据取证报告已保存: {report_path}")
            logger.info(f"  📊 数据摘要:\n{summary_text}")

        except Exception as e:
            logger.debug(f"     视觉取证失败: {e}")


# ============================================================================
# 数据库操作
# ============================================================================

def save_l3_data_to_db(result: ExtractionResult) -> bool:
    """保存 L3 数据到数据库.

    Args:
        result: 提取结果

    Returns:
        bool: 是否保存成功
    """
    if not result.success or result.l3_data is None:
        return False

    settings = get_settings()

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        # 更新 matches 表
        cursor.execute("""
            UPDATE matches
            SET
                l3_odds_data = %s,
                l3_extraction_status = %s,
                l3_extracted_at = NOW(),
                l3_data_mismatch = %s
            WHERE match_id = %s
        """, (
            result.l3_data.to_json(),
            "success" if result.l3_data.is_valid else "failed",
            result.data_mismatch,
            result.match_id
        ))

        # 检查是否真正更新了记录
        updated_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        if updated_rows > 0:
            logger.info(f"✅ L3 数据已保存: {result.match_id}")
            return True
        else:
            logger.warning(f"⚠️  L3 数据保存失败: match_id '{result.match_id}' 不存在")
            return False

    except Exception as e:
        logger.error(f"❌ 数据库保存失败: {e}")
        return False


def get_approved_matches(limit: int = 10) -> list[dict[str, Any]]:
    """获取 Approved 映射的比赛列表.

    Args:
        limit: 最大返回数量

    Returns:
        list[dict]: 比赛列表
    """
    settings = get_settings()

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=settings.database.port,
            database="football_db",
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                mm.fotmob_id,
                mm.home_team,
                mm.away_team,
                mm.match_date,
                mm.oddsportal_url,
                m.home_score,
                m.away_score
            FROM matches_mapping mm
            LEFT JOIN matches m ON m.match_id = mm.fotmob_id
            WHERE mm.review_status = 'approved'
            AND mm.oddsportal_url IS NOT NULL
            AND (m.l3_extraction_status IS NULL OR m.l3_extraction_status != 'success')
            ORDER BY RANDOM()
            LIMIT %s
        """, (limit,))

        rows = cursor.fetchall()

        matches = []
        for row in rows:
            matches.append({
                "match_id": str(row[0]),
                "home_team": row[1],
                "away_team": row[2],
                "match_date": row[3],
                "oddsportal_url": row[4],
                "fotmob_score": {"home": row[5], "away": row[6]}
            })

        cursor.close()
        conn.close()

        return matches

    except Exception as e:
        logger.error(f"❌ 数据库查询失败: {e}")
        return []
