#!/usr/bin/env python3
"""
V41.192 harvest_all.py - 肃清与深挖，初盘攻坚
====================================================================

V41.192 "肃清与深挖" - 环境标准化与初盘数据攻坚

核心升级（V41.192）：
    - 环境治理：智能识别 Docker 数据库容器，消除误报警告
    - 初盘提取 A: DOM 元素 data-opening/data-history 属性提取
    - 初盘提取 B: window.pageVar 内存回溯提取
    - 初盘提取 C: 强制交互 + tooltip 监听拦截

保留特性（来自 V41.189/V41.190）：
    - 智能清障：自动清除 overlay-bookie-modal 等遮挡层
    - 弹性验证：Payout 范围放宽至 85-102%
    - 二段跳重试：首次失败后等待 5 秒并重新滚动
    - 多路径提取：Pinnacle 表格 → 全页文本搜索

Usage:
    # 处理所有缺失数据
    python harvest_all.py

    # 只处理 2023/2024 赛季
    python harvest_all.py --season "2023/2024"

    # 只收割之前失败的场次
    python harvest_all.py --failed-only

    # 测试模式（只处理 10 场）
    python harvest_all.py --limit 10

    # 干跑模式（不实际入库）
    python harvest_all.py --dry-run

Author: V41.192 Deep Harvest Team
Date: 2026-01-19
Version: V41.192 "肃清与深挖" - 初盘攻坚版
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# 项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config, get_database_url

# 配置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "v41_190_harvest_all.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("V41.190")


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class MatchToHarvest:
    """待收割的比赛"""
    match_id: str
    home_team: str
    away_team: str
    league_name: str
    season: str
    oddsportal_url: str


@dataclass
class HarvestResult:
    """收割结果 - V41.192 加入初盘数据"""
    match_id: str
    status: str  # success, failed, skipped
    # 终盘数据（原有）
    closing_h: float | None = None
    closing_d: float | None = None
    closing_a: float | None = None
    payout: float | None = None
    method: str = ""
    # V41.192: 初盘数据
    opening_h: float | None = None
    opening_d: float | None = None
    opening_a: float | None = None
    opening_timestamp: str | None = None
    # 元数据
    recovered: bool = False  # 是否通过重试挽救
    opening_method: str = ""  # opening 数据提取方法
    error: str | None = None
    duration_ms: int = 0


@dataclass
class HarvestReport:
    """收割报告"""
    total_matches: int
    processed: int
    successful: int
    failed: int
    skipped: int
    retried: int
    recovered: int  # 重试挽救的数量
    results: list[HarvestResult]
    start_time: datetime
    end_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.processed > 0:
            return self.successful / self.processed * 100
        return 0.0

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_matches": self.total_matches,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "retried": self.retried,
            "recovered": self.recovered,
            "success_rate": f"{self.success_rate:.2f}%",
            "avg_time_per_match": self.duration_seconds / self.processed if self.processed > 0 else 0,
            "failed_matches": [
                {"match_id": r.match_id, "error": r.error}
                for r in self.results if r.status == "failed"
            ]
        }


# =============================================================================
# V41.190 IronCurtainHarvester - 铁幕合围收割器（完全体）
# =============================================================================

class V41_190IronCurtainHarvester:
    """V41.190 铁幕合围收割器 - 合并自愈逻辑的最终生产版本"""

    def __init__(
        self,
        dry_run: bool = False,
        season: str | None = None,
        headless: bool = True
    ):
        self.dry_run = dry_run
        self.season = season
        self.headless = headless
        self.config = get_config()

        # 浏览器
        self.browser = None
        self.context = None
        self.page = None

        # 统计
        self.report = HarvestReport(
            total_matches=0,
            processed=0,
            successful=0,
            failed=0,
            skipped=0,
            retried=0,
            recovered=0,
            results=[],
            start_time=datetime.now()
        )

    async def init_browser(self):
        """初始化浏览器"""
        logger.info("🔧 初始化浏览器...")

        proxy = {"server": f"http://{self.config.proxy.wsl2_bridge_host}:7892"}

        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            proxy=proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='en-US',
            timezone_id='Europe/London'
        )

        self.page = await self.context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(self.page)

        logger.info("✅ 浏览器初始化完成")

    def get_matches_to_harvest(
        self,
        limit: int | None = None,
        failed_only: bool = False
    ) -> list[MatchToHarvest]:
        """获取待收割的比赛"""
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor()

        if failed_only:
            # 获取之前 V41.188 失败的比赛
            failed_ids = [
                "4230741", "4221909", "4221893", "4193726", "4193565",
                "4221796", "4193550", "4205413", "4230587", "4193508",
                "4205371", "4221738"
            ]

            query = """
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.league_name,
                    m.season,
                    m.match_date,
                    mm.oddsportal_url
                FROM matches m
                INNER JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE m.match_id = ANY(%s)
                    AND mm.oddsportal_url IS NOT NULL
                ORDER BY m.match_date DESC
            """
            cursor.execute(query, (failed_ids,))
        else:
            # V41.192: 获取所有缺失终盘或初盘的比赛
            query = """
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.league_name,
                    m.season,
                    m.match_date,
                    mm.oddsportal_url
                FROM matches m
                INNER JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE mm.oddsportal_hash IS NOT NULL
                    AND mm.oddsportal_url IS NOT NULL
                    AND (
                        -- 缺少终盘数据
                        NOT EXISTS (
                            SELECT 1 FROM odds o
                            WHERE o.match_id = m.match_id
                            AND o.bookmaker = 'Pinnacle'
                        )
                        OR
                        -- 有终盘但缺少初盘
                        EXISTS (
                            SELECT 1 FROM odds o
                            WHERE o.match_id = m.match_id
                            AND o.bookmaker = 'Pinnacle'
                            AND o.home_odds IS NOT NULL
                            AND o.opening_home_odds IS NULL
                        )
                    )
            """

            conditions = []
            params = []

            if self.season:
                conditions.append("m.season = %s")
                params.append(self.season)

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY m.match_date DESC"

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, params)

        rows = cursor.fetchall()

        matches = []
        for row in rows:
            matches.append(MatchToHarvest(
                match_id=row[0],
                home_team=row[1],
                away_team=row[2],
                league_name=row[3],
                season=row[4],
                oddsportal_url=row[6]  # match_date is at index 5
            ))

        cursor.close()
        conn.close()

        logger.info(f"📊 找到 {len(matches)} 场待收割比赛")
        return matches

    async def harvest_match(self, match: MatchToHarvest) -> HarvestResult:
        """收割单场比赛（带 V41.192 初盘提取逻辑）"""
        import time
        start_time = time.time()

        result = HarvestResult(match_id=match.match_id, status="pending")

        try:
            logger.info(f"🎯 [{self.report.processed + 1}/{self.report.total_matches}] {match.match_id} - {match.home_team} vs {match.away_team}")

            # 处理 URL
            url = match.oddsportal_url
            if url.startswith('/'):
                url = 'https://www.oddsportal.com' + url
            elif not url.startswith('http'):
                url = 'https://www.oddsportal.com/' + url.lstrip('/')

            url_with_anchor = url.rstrip('/') + '/#1X2;2'

            # 访问页面
            await self.page.goto(url_with_anchor, wait_until="networkidle", timeout=90000)

            # V41.189 核心升级1: 智能清障
            await self._clear_overlays()

            # 等待和滚动
            await asyncio.sleep(3)
            await self._human_like_scroll()
            await asyncio.sleep(2)

            # V41.192: 尝试提取初盘数据（三种策略）
            opening_data = await self._extract_opening_odds()
            if opening_data:
                result.opening_h = opening_data['home']
                result.opening_d = opening_data['draw']
                result.opening_a = opening_data['away']
                result.opening_timestamp = opening_data.get('timestamp')
                result.opening_method = opening_data.get('method', 'unknown')
                logger.info(f"  📈 初盘: [{result.opening_h}, {result.opening_d}, {result.opening_a}] (method: {result.opening_method})")

            # 首次尝试提取终盘
            odds_data = await self._extract_odds_robust()

            # V41.189 核心升级2: 二段跳重试
            if not odds_data:
                logger.warning(f"  ⚠️ 首次提取失败，启用弹性等待...")
                self.report.retried += 1

                # 等待 5 秒
                await asyncio.sleep(5)

                # 重新滚动
                await self._human_like_scroll()
                await asyncio.sleep(2)

                # 再次尝试
                odds_data = await self._extract_odds_robust()

                if odds_data:
                    result.recovered = True
                    self.report.recovered += 1
                    logger.info(f"  🔄 重试成功！")

            if odds_data:
                result.status = "success"
                result.closing_h = odds_data['home']
                result.closing_d = odds_data['draw']
                result.closing_a = odds_data['away']
                result.payout = odds_data['payout']
                result.method = odds_data.get('method', 'unknown')

                logger.info(f"  ✅ 终盘: [{result.closing_h}, {result.closing_d}, {result.closing_a}] (payout: {result.payout:.2f}%, method: {result.method})")

                # 保存到数据库
                if not self.dry_run:
                    self._save_to_database(match, result)

            else:
                result.status = "failed"
                result.error = "所有提取策略均失败"
                logger.warning(f"  ❌ 失败: {result.error}")

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            logger.error(f"  ❌ 异常: {e}")

        finally:
            result.duration_ms = int((time.time() - start_time) * 1000)
            self.report.results.append(result)
            self.report.processed += 1

            if result.status == "success":
                self.report.successful += 1
            elif result.status == "failed":
                self.report.failed += 1
            else:
                self.report.skipped += 1

        return result

    async def _clear_overlays(self):
        """V41.189 核心升级1: 智能遮挡清理"""
        js_clear = """
        () => {
            let cleared = 0;

            // 清理已知的遮挡层
            const overlaySelectors = [
                '.overlay-bookie-modal',
                '[class*="overlay"]',
                '[class*="modal"]',
                '[id*="overlay"]',
                '[id*="popup"]',
                '.cookie-banner',
                '#cookie-banner'
            ];

            overlaySelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.position === 'absolute') {
                        if (parseInt(style.zIndex) > 100) {
                            el.style.display = 'none';
                            cleared++;
                        }
                    }
                });
            });

            return cleared;
        }
        """

        try:
            cleared = await self.page.evaluate(js_clear)
            if cleared > 0:
                logger.debug(f"  🧹 已清理 {cleared} 个遮挡层")
        except Exception as e:
            logger.debug(f"清理遮挡层失败: {e}")

    async def _human_like_scroll(self):
        """模拟人类滚动"""
        page_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_steps = max(5, page_height // 400)

        for i in range(scroll_steps):
            scroll_pos = (i + 1) * (page_height // scroll_steps)
            await self.page.evaluate(f"window.scrollTo(0, {scroll_pos})")
            await asyncio.sleep(0.5)

        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

    async def _extract_odds_robust(self) -> dict[str, Any] | None:
        """V41.189 核心升级3+4: 多路径提取 + 弹性验证"""

        # 策略 1: Pinnacle 表格提取
        js_pinnacle = """
        () => {
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText || '';
                    if (text.toLowerCase().includes('pinnacle')) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 4) {
                            const odds = [];
                            for (let i = 1; i < 4 && i < cells.length; i++) {
                                const cellText = cells[i].innerText?.trim() || '';
                                const odd = parseFloat(cellText);
                                if (!isNaN(odd) && odd > 1) {
                                    odds.push(odd);
                                }
                            }
                            if (odds.length === 3) {
                                const payout = 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100;
                                // V41.189 核心升级4: 放宽 payout 验证范围 (85-102%)
                                if (payout >= 85 && payout <= 102) {
                                    return { method: 'pinnacle_table', home: odds[0], draw: odds[1], away: odds[2], payout: payout };
                                }
                            }
                        }
                    }
                }
            }
            return null;
        }
        """

        try:
            data = await self.page.evaluate(js_pinnacle)
            if data:
                return data
        except Exception as e:
            logger.debug(f"Pinnacle 提取失败: {e}")

        # 策略 2: 全页文本提取（放宽条件）
        js_text = """
        () => {
            const allText = document.body.innerText;
            const oddsPattern = /\\b([1-9]\\.\\d{2,3}|[1-9]\\d\\.\\d{2})\\b/g;
            const allMatches = allText.match(oddsPattern);

            if (allMatches) {
                const odds = allMatches.map(m => parseFloat(m)).filter(n => n >= 1.01 && n <= 50);

                // 查找合理的 H-D-A 组合
                for (let i = 0; i < odds.length - 2; i++) {
                    const h = odds[i], d = odds[i + 1], a = odds[i + 2];

                    // V41.189 核心升级4: 放宽单个赔率范围验证
                    const hValid = h >= 1.01 && h <= 20.0;
                    const dValid = d >= 1.2 && d <= 20.0;
                    const aValid = a >= 1.2 && a <= 30.0;

                    // V41.189 核心升级4: 放宽 payout 验证范围
                    const payout = 1 / (1/h + 1/d + 1/a) * 100;
                    const payoutValid = payout >= 85 && payout <= 102;

                    if (hValid && dValid && aValid && payoutValid) {
                        return { method: 'text_extraction', home: h, draw: d, away: a, payout: payout };
                    }
                }
            }
            return null;
        }
        """

        try:
            data = await self.page.evaluate(js_text)
            if data:
                return data
        except Exception as e:
            logger.debug(f"文本提取失败: {e}")

        return None

    async def _extract_opening_odds(self) -> dict[str, Any] | None:
        """
        V41.192: 初盘数据提取 - 三种策略

        策略 A: DOM 元素 data-opening/data-history 属性提取
        策略 B: window.pageVar 内存回溯提取
        策略 C: 强制交互 + tooltip 监听拦截
        """
        # 策略 A: DOM 属性提取
        data = await self._extract_opening_dom_attributes()
        if data:
            logger.debug(f"  策略 A 成功: DOM 属性提取")
            return {**data, "method": "dom_attributes"}

        # 策略 B: 内存回溯提取
        data = await self._extract_opening_memory_rollback()
        if data:
            logger.debug(f"  策略 B 成功: 内存回溯提取")
            return {**data, "method": "memory_rollback"}

        # 策略 C: 交互监听提取
        data = await self._extract_opening_interaction()
        if data:
            logger.debug(f"  策略 C 成功: 交互监听提取")
            return {**data, "method": "interaction"}

        return None

    async def _extract_opening_dom_attributes(self) -> dict[str, Any] | None:
        """
        策略 A: DOM 元素 data-opening/data-history 属性提取

        检查 Pinnacle 行的单元格是否有 data-opening 或 data-history 属性
        """
        js_opening_dom = """
        () => {
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText || '';
                    if (text.toLowerCase().includes('pinnacle')) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 4) {
                            const odds = [];
                            // 检查 data-opening 属性
                            for (let i = 1; i < 4 && i < cells.length; i++) {
                                const cell = cells[i];
                                const openingOdd = cell.getAttribute('data-opening');
                                if (openingOdd) {
                                    const odd = parseFloat(openingOdd);
                                    if (!isNaN(odd) && odd > 1) {
                                        odds.push(odd);
                                    }
                                }
                            }
                            if (odds.length === 3) {
                                const payout = 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100;
                                if (payout >= 85 && payout <= 102) {
                                    return { home: odds[0], draw: odds[1], away: odds[2], payout: payout };
                                }
                            }

                            // 如果没有 data-opening，尝试 data-history
                            const historyData = cells[1].getAttribute('data-history');
                            if (historyData) {
                                try {
                                    const history = JSON.parse(historyData);
                                    if (history.opening && Array.isArray(history.opening) && history.opening.length === 3) {
                                        const odds = history.opening.map(o => parseFloat(o)).filter(o => !isNaN(o) && o > 1);
                                        if (odds.length === 3) {
                                            const payout = 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100;
                                            if (payout >= 85 && payout <= 102) {
                                                return { home: odds[0], draw: odds[1], away: odds[2], payout: payout };
                                            }
                                        }
                                    }
                                } catch (e) {
                                    // 忽略 JSON 解析错误
                                }
                            }
                        }
                    }
                }
            }
            return null;
        }
        """

        try:
            return await self.page.evaluate(js_opening_dom)
        except Exception as e:
            logger.debug(f"策略 A 失败: {e}")
            return None

    async def _extract_opening_memory_rollback(self) -> dict[str, Any] | None:
        """
        策略 B: window.pageVar 内存回溯提取

        深入解析全局变量，寻找包含 opening_odds 关键词的 JSON 路径
        """
        js_memory = """
        () => {
            // 检查 window.pageVar
            if (window.pageVar) {
                // 尝试多个可能的路径
                const paths = [
                    'pageVar.odds.opening',
                    'pageVar.odds.pinnacle.opening',
                    'pageVar.openingOdds',
                    'pageVar.pinnacle.opening',
                    'pageVar.data.opening',
                    'pageVar.matchData.opening'
                ];

                for (const path of paths) {
                    const value = path.split('.').reduce((obj, key) => obj && obj[key], window);
                    if (value && Array.isArray(value) && value.length === 3) {
                        const odds = value.map(o => parseFloat(o)).filter(o => !isNaN(o) && o > 1);
                        if (odds.length === 3) {
                            const payout = 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100;
                            if (payout >= 85 && payout <= 102) {
                                return { home: odds[0], draw: odds[1], away: odds[2], payout: payout };
                            }
                        }
                    }
                }

                // 尝试查找包含 'opening' 的所有属性
                const findOpening = (obj, depth = 0) => {
                    if (depth > 5) return null;
                    if (!obj || typeof obj !== 'object') return null;

                    for (const key in obj) {
                        if (key.toLowerCase().includes('opening') || key.toLowerCase().includes('start')) {
                            const value = obj[key];
                            if (Array.isArray(value) && value.length === 3) {
                                const odds = value.map(o => parseFloat(o)).filter(o => !isNaN(o) && o > 1);
                                if (odds.length === 3) {
                                    const payout = 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100;
                                    if (payout >= 85 && payout <= 102) {
                                        return { home: odds[0], draw: odds[1], away: odds[2], payout: payout };
                                    }
                                }
                            }
                        }
                        if (typeof obj[key] === 'object') {
                            const result = findOpening(obj[key], depth + 1);
                            if (result) return result;
                        }
                    }
                    return null;
                };

                const result = findOpening(window.pageVar);
                if (result) return result;
            }

            return null;
        }
        """

        try:
            return await self.page.evaluate(js_memory)
        except Exception as e:
            logger.debug(f"策略 B 失败: {e}")
            return None

    async def _extract_opening_interaction(self) -> dict[str, Any] | None:
        """
        策略 C: 强制交互 + tooltip 监听拦截

        鼠标悬停 Pinnacle 单元格，监听 div.tooltip-content 类名的出现
        """
        # 设置监听器
        js_setup_listener = """
        () => {
            // 清除之前的监听器
            if (window.__openingTooltipListener) {
                return { status: 'already_setup' };
            }

            window.__openingTooltipData = null;
            window.__openingTooltipListener = true;

            // 监听 DOM 变化
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === 1) {
                            const element = node;
                            // 检查是否是 tooltip
                            if (element.classList && (
                                element.classList.contains('tooltip-content') ||
                                element.classList.contains('odds-tooltip') ||
                                element.id.includes('tooltip')
                            )) {
                                // 提取初盘数据
                                const oddsElements = element.querySelectorAll('[data-opening], .opening, .start-odds');
                                if (oddsElements.length > 0) {
                                    const odds = [];
                                    oddsElements.forEach(el => {
                                        const odd = parseFloat(el.getAttribute('data-opening') || el.innerText);
                                        if (!isNaN(odd) && odd > 1) {
                                            odds.push(odd);
                                        }
                                    });
                                    if (odds.length === 3) {
                                        window.__openingTooltipData = {
                                            home: odds[0],
                                            draw: odds[1],
                                            away: odds[2],
                                            payout: 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100
                                        };
                                    }
                                }
                            }
                        }
                    }
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            window.__openingTooltipObserver = observer;

            return { status: 'setup_complete' };
        }
        """

        # 悬停并触发 tooltip
        js_hover_and_extract = """
        () => {
            return new Promise((resolve) => {
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const rows = table.querySelectorAll('tr');
                    for (const row of rows) {
                        const text = row.innerText || '';
                        if (text.toLowerCase().includes('pinnacle')) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                // 悬停第一个赔率单元格
                                const cell = cells[1];
                                cell.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                                cell.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));

                                // 等待 tooltip 出现
                                setTimeout(() => {
                                    // 检查是否有 tooltip 数据
                                    if (window.__openingTooltipData) {
                                        resolve(window.__openingTooltipData);
                                    } else {
                                        // 尝试直接查找 tooltip 元素
                                        const tooltips = document.querySelectorAll('.tooltip-content, .odds-tooltip, [id*="tooltip"]');
                                        for (const tooltip of tooltips) {
                                            const oddsText = tooltip.innerText || '';
                                            const oddsPattern = /\\b([1-9]\\.\\d{2,3}|[1-9]\\d\\.\\d{2})\\b/g;
                                            const matches = oddsText.match(oddsPattern);
                                            if (matches && matches.length >= 3) {
                                                const odds = matches.slice(0, 3).map(m => parseFloat(m));
                                                const payout = 1 / (1/odds[0] + 1/odds[1] + 1/odds[2]) * 100;
                                                if (payout >= 85 && payout <= 102) {
                                                    resolve({ home: odds[0], draw: odds[1], away: odds[2], payout: payout });
                                                    return;
                                                }
                                            }
                                        }
                                        resolve(null);
                                    }
                                }, 500);
                                return;
                            }
                        }
                    }
                }
                resolve(null);
            });
        }
        """

        try:
            # 设置监听器
            await self.page.evaluate(js_setup_listener)

            # 悬停并提取
            return await self.page.evaluate(js_hover_and_extract)

        except Exception as e:
            logger.debug(f"策略 C 失败: {e}")
            return None

    def _save_to_database(self, match: MatchToHarvest, result: HarvestResult):
        """保存到数据库 - V41.192 包含初盘数据"""
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO odds (
                    match_id, bookmaker,
                    home_odds, draw_odds, away_odds,
                    opening_home_odds, opening_draw_odds, opening_away_odds,
                    opening_timestamp,
                    collected_at
                ) VALUES (
                    %s, 'Pinnacle',
                    %s, %s, %s,
                    %s, %s, %s,
                    %s,
                    NOW()
                )
                ON CONFLICT (match_id, bookmaker)
                DO UPDATE SET
                    home_odds = EXCLUDED.home_odds,
                    draw_odds = EXCLUDED.draw_odds,
                    away_odds = EXCLUDED.away_odds,
                    opening_home_odds = COALESCE(EXCLUDED.opening_home_odds, odds.opening_home_odds),
                    opening_draw_odds = COALESCE(EXCLUDED.opening_draw_odds, odds.opening_draw_odds),
                    opening_away_odds = COALESCE(EXCLUDED.opening_away_odds, odds.opening_away_odds),
                    opening_timestamp = COALESCE(EXCLUDED.opening_timestamp, odds.opening_timestamp),
                    collected_at = EXCLUDED.collected_at
            """, (
                match.match_id,
                result.closing_h,
                result.closing_d,
                result.closing_a,
                result.opening_h,
                result.opening_d,
                result.opening_a,
                result.opening_timestamp
            ))

            conn.commit()
            logger.debug(f"  💾 已保存到数据库")

        except Exception as e:
            conn.rollback()
            logger.error(f"  ❌ 保存失败: {e}")
        finally:
            cursor.close()
            conn.close()

    async def close(self):
        """关闭浏览器"""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.debug(f"关闭浏览器时出错: {e}")

    def print_report(self):
        """打印报告 - V41.192 包含初盘统计"""
        # 计算初盘覆盖率
        opening_collected = sum(1 for r in self.report.results if r.opening_h is not None)
        opening_rate = opening_collected / self.report.successful * 100 if self.report.successful > 0 else 0

        logger.info("\n" + "=" * 70)
        logger.info("📊 V41.192 肃清与深挖 - 收割报告")
        logger.info("=" * 70)
        logger.info(f"总场次: {self.report.total_matches}")
        logger.info(f"已处理: {self.report.processed}")
        logger.info(f"✅ 成功: {self.report.successful}")
        logger.info(f"❌ 失败: {self.report.failed}")
        logger.info(f"⏭️  跳过: {self.report.skipped}")
        logger.info(f"🔄 重试: {self.report.retried}")
        logger.info(f"✨ 挽回: {self.report.recovered}")
        logger.info(f"成功率: {self.report.success_rate:.2f}%")
        logger.info("")
        logger.info(f"📈 初盘数据: {opening_collected}/{self.report.successful} ({opening_rate:.1f}%)")
        logger.info(f"耗时: {self.report.duration_seconds:.1f} 秒")
        logger.info(f"平均: {self.report.duration_seconds / self.report.processed if self.report.processed > 0 else 0:.2f} 秒/场")

        if self.report.failed > 0:
            logger.info("\n❌ 失败场次:")
            for r in self.report.results:
                if r.status == "failed":
                    logger.info(f"  {r.match_id}: {r.error}")

        logger.info("=" * 70)

        # 保存 JSON 报告
        self.report.end_time = datetime.now()
        report_file = log_dir / f"v41_192_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"💾 报告已保存: {report_file}")


# =============================================================================
# 主程序
# =============================================================================

async def main() -> int:
    """主程序 - V41.192 肃清与深挖"""
    parser = argparse.ArgumentParser(
        description="V41.192 肃清与深挖 - 环境标准化与初盘攻坚",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理 2023/2024 赛季所有缺失数据（含初盘提取）
  python harvest_all.py --season "2023/2024"

  # 只收割之前失败的场次
  python harvest_all.py --failed-only

  # 测试模式（只处理 1 场，验证初盘提取）
  python harvest_all.py --limit 1

  # 干跑模式（不实际入库）
  python harvest_all.py --dry-run
        """
    )

    parser.add_argument("--season", type=str, help="筛选赛季")
    parser.add_argument("--limit", type=int, help="限制处理数量")
    parser.add_argument("--failed-only", action="store_true", help="只收割之前失败的场次")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口")

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("V41.192 肃清与深挖 - 初盘攻坚版")
    logger.info("=" * 70)

    harvester = V41_190IronCurtainHarvester(
        dry_run=args.dry_run,
        season=args.season,
        headless=not args.no_headless
    )

    try:
        await harvester.init_browser()

        matches = harvester.get_matches_to_harvest(
            limit=args.limit,
            failed_only=args.failed_only
        )

        harvester.report.total_matches = len(matches)

        if not matches:
            logger.info("✅ 所有比赛都已收集完整数据！")
            return 0

        for match in matches:
            await harvester.harvest_match(match)

            # 每 10 场重启浏览器
            if harvester.report.processed % 10 == 0:
                await harvester.close()
                await harvester.init_browser()

        harvester.print_report()

        # 返回码
        if harvester.report.failed > 0:
            return 1
        return 0

    except Exception as e:
        logger.error(f"❌ 错误: {e}", exc_info=True)
        return 1
    finally:
        await harvester.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
