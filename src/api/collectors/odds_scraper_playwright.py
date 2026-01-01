#!/usr/bin/env python3
"""
V53.3 OddsPortal 赔率采集器 - Playwright 版本
===============================================

功能:
- 使用 Playwright 访问 OddsPortal 获取历史赔率
- V53.3 双向采集法 - 同时提取初盘和终赔
- 严格 Margin 校验 - 仅接受 1.02 < Margin < 1.08 的数据
- 通过 team_name_mapping 表关联球队
- 更新 prematch_features 表的赔率字段

核心改进 (V53.3):
1. 智能容器提取法 - JavaScript 直接查找 odds-link 容器
2. 【新增】初盘提取 - 从 title 属性提取开盘赔率
3. 【新增】走势特征 - 计算 Drift = (Closing - Opening) / Opening
4. 备用策略 - 从所有赔率中推导 1X2 组合
5. 双向 Margin 校验 - 严格下限 (1.02) 和上限 (1.08)

Author: Senior Data Engineer
Version: V53.3
Date: 2025-12-31
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class OddsMatch:
    """单场比赛赔率数据 - 扩展版本

    遵循 Single Source 原则：所有赔率来自同一个 Primary_Source 机构
    """
    match_id: str
    home_team: str
    away_team: str
    league_name: str
    match_date: datetime

    # ====== 第一阶段：单一源赔率数据 ======
    # 来自同一个 Data_Provider 行的三个系数
    primary_provider: str | None = None  # 数据提供者名称
    opening_home_odds: float | None = None
    opening_draw_odds: float | None = None
    opening_away_odds: float | None = None
    closing_home_odds: float | None = None
    closing_draw_odds: float | None = None
    closing_away_odds: float | None = None

    # ====== 第二阶段：扩展数据维度 ======
    # 市场平均值（页面底部的全场平均值）
    market_avg_home: float | None = None
    market_avg_draw: float | None = None
    market_avg_away: float | None = None

    # 元数据
    data_timestamp: datetime | None = None  # 数据采集时间戳
    is_valid: bool = True  # 数据是否通过校验
    validation_error: str | None = None  # 校验失败原因

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league_name": self.league_name,
            "match_date": self.match_date,
            "primary_provider": self.primary_provider,
            "opening_home_odds": self.opening_home_odds,
            "opening_draw_odds": self.opening_draw_odds,
            "opening_away_odds": self.opening_away_odds,
            "closing_home_odds": self.closing_home_odds,
            "closing_draw_odds": self.closing_draw_odds,
            "closing_away_odds": self.closing_away_odds,
            "market_avg_home": self.market_avg_home,
            "market_avg_draw": self.market_avg_draw,
            "market_avg_away": self.market_avg_away,
            "data_timestamp": self.data_timestamp,
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
        }


class OddsPortalScraper:
    """
    OddsPortal 赔率采集器 - Playwright 版本

    特性:
    - 使用真实浏览器绕过基础反爬
    - User-Agent 轮换
    - 随机延迟避免封禁
    - 通过映射表关联球队
    """

    # ====== 配置常量 ======

    # 用户代理池 (第四阶段：优化的 UA 伪装)
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    # OddsPortal 联赛映射
    LEAGUE_MAPPING = {
        "Premier League": "england/premier-league",
        "La Liga": "spain/la-liga",
        "Bundesliga": "germany/bundesliga",
        "Serie A": "italy/serie-a",
        "Ligue 1": "france/ligue-1",
        "英超": "england/premier-league",  # 中文别名
    }

    # ====== 第一阶段：优先数据提供者列表 ======
    # 按优先级排序的 Data_Provider 列表
    # 用于 Single Source 原则：定位到第一个可用的机构行
    PREFERRED_PROVIDERS = [
        "bet365",           # 优先级 1: 全球最大
        "Pinnacle",         # 优先级 2: 专业盘口
        "William Hill",     # 优先级 3: 老牌英国
        "Unibet",           # 优先级 4: 欧洲主流
        "BetVictor",        # 优先级 5: 高限额
        "10Bet",            # 优先级 6: 备用
    ]

    # ====== CSS 选择器配置 ======
    # 注意：选择器需要根据实际页面结构调整
    SELECTORS = {
        #赔率表格容器
        "odds_table": "table.odds-table",

        # 机构名称列（用于定位目标行）
        "provider_column": "td[data-bookmaker]",

        # 初始系数
        "opening_home": "td.odds-home.opening",
        "opening_draw": "td.odds-draw.opening",
        "opening_away": "td.odds-away.opening",

        # 最终系数
        "closing_home": "td.odds-home.closing",
        "closing_draw": "td.odds-draw.closing",
        "closing_away": "td.odds-away.closing",

        # 市场平均值（第二阶段）
        "market_avg_section": "div.market-average",
        "market_avg_home": "span.avg-home",
        "market_avg_draw": "span.avg-draw",
        "market_avg_away": "span.avg-away",
    }

    # ====== 第三阶段：数学有效性校验配置 (V53 生产级) ======
    # 赔率乘积阈值（1/A + 1/B + 1/C 应该在此范围内）
    MIN_ODDS_PRODUCT = 1.02  # V53: 严格下限（防止异常低赔率）
    MAX_ODDS_PRODUCT = 1.08  # V53: 严格上限（防止异常高抽水）

    # ====== 第四阶段：人类行为模拟配置 ======
    # 随机延迟范围（秒）
    HUMAN_DELAY_MIN = 1.5
    HUMAN_DELAY_MAX = 4.0
    # 鼠标移动模拟
    ENABLE_MOUSE_MOVEMENT = True

    def __init__(
        self,
        headless: bool = True,
        batch_size: int = 50,
        delay_min: float = None,  # 使用类默认值
        delay_max: float = None,  # 使用类默认值
        enable_mouse: bool = True,
    ):
        self.headless = headless
        self.batch_size = batch_size
        self.delay_min = delay_min or self.HUMAN_DELAY_MIN
        self.delay_max = delay_max or self.HUMAN_DELAY_MAX
        self.enable_mouse = enable_mouse
        self.browser = None
        self.context = None
        self.page = None

        # 数据库连接
        self.settings = get_settings()
        self._conn = None
        self._team_mapping_cache = {}

        # 统计信息
        self._stats = {
            "total_fetched": 0,
            "success_count": 0,
            "validation_failed": 0,
            "provider_not_found": 0,
        }

    def get_db_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def load_team_mapping(self):
        """加载球队映射表到内存"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT fotmob_name, oddsportal_name, fotmob_league
            FROM team_name_mapping
            WHERE mapping_status = 'approved'
        """)

        for row in cursor.fetchall():
            key = (row["fotmob_name"], row["fotmob_league"])
            self._team_mapping_cache[key] = row["oddsportal_name"]

        logger.info(f"加载球队映射: {len(self._team_mapping_cache)} 条")

    def get_oddsportal_team_name(self, fotmob_name: str, league: str) -> str | None:
        """获取 OddsPortal 球队名称"""
        key = (fotmob_name, league)
        return self._team_mapping_cache.get(key)

    async def start(self):
        """启动浏览器"""
        logger.info("启动 Playwright 浏览器...")
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        self.context = await self.browser.new_context(
            user_agent=random.choice(self.UA_POOL),
            viewport={"width": 1920, "height": 1080},
        )

        self.page = await self.context.new_page()
        logger.info("浏览器启动成功")

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        if self._conn:
            self._conn.close()
        logger.info("浏览器已关闭")

    async def _random_delay(self):
        """第四阶段：模拟人类操作的随机延迟

        包含：
        - 基础随机延迟 (1.5-4.0 秒)
        - 可选的鼠标移动模拟
        - 随机的微抖动（模拟真实用户行为）
        """
        # 基础延迟
        base_delay = random.uniform(self.delay_min, self.delay_max)

        # 模拟真实用户的微抖动 (±20%)
        jitter = base_delay * random.uniform(-0.2, 0.2)
        final_delay = max(0.5, base_delay + jitter)

        logger.debug(f"延迟 {final_delay:.2f} 秒 (模拟人类行为)")
        await asyncio.sleep(final_delay)

    # ============================================================
    # 第一阶段：核心解析逻辑 - V53 智能容器提取法
    # ============================================================

    async def _parse_primary_provider_row(self, page) -> dict[str, Any] | None:
        """
        【多路径探测】核心解析函数 - 兼容即时页面与历史归档页面

        路径 A: Vue/Flex 探测（现代布局）
        路径 B: Legacy Table 探测（历史归档）
        路径 C: 初盘深度挖掘（Opening Odds）

        Args:
            page: Playwright Page 对象

        Returns:
            包含 provider, 初盘/终赔的字典，失败返回 None
        """
        await asyncio.sleep(2)  # 等待页面渲染

        # ============================================================
        # 路径 A: Vue/Flex 探测（针对现代布局）
        # ============================================================
        vue_data = await page.evaluate("""
            () => {
                const results = [];
                const containers = document.querySelectorAll('div[class*="odds"], div.row, div[data-v-]');

                for (const container of containers) {
                    const oddsLinks = container.querySelectorAll('a.odds-link');

                    if (oddsLinks.length >= 3) {
                        const closingValues = [];
                        const openingValues = [];

                        oddsLinks.forEach(link => {
                            const text = link.textContent.trim();
                            if (/^\\d+\\.\\d{2}$/.test(text)) {
                                closingValues.push(parseFloat(text));
                            }

                            // 探测初盘属性
                            const title = link.getAttribute('title') || '';
                            const dataOpening = link.getAttribute('data-opening') || '';
                            const dataOdds = link.getAttribute('data-odds') || '';

                            // 正则提取初盘
                            const openingRegex = /(?:opening|initial|initial odds|开盘)[:\\s]*([\\d.]+)/i;
                            let openingMatch = title.match(openingRegex);
                            if (!openingMatch && dataOpening) openingMatch = dataOpening.match(/([\\d.]+)/);
                            if (!openingMatch && dataOdds) openingMatch = dataOdds.match(/([\\d.]+)/);

                            if (openingMatch && /^\\d+\\.\\d{2}$/.test(openingMatch[1])) {
                                openingValues.push(parseFloat(openingMatch[1]));
                            }
                        });

                        if (closingValues.length >= 3) {
                            results.push({
                                closing: closingValues.slice(0, 3),
                                opening: openingValues.length >= 3 ? openingValues.slice(0, 3) : null
                            });
                        }
                    }
                }
                return results;
            }
        """)

        if vue_data:
            data = vue_data[0]
            closing = data["closing"]

            # Margin 校验
            margin = (1.0 / closing[0] + 1.0 / closing[1] + 1.0 / closing[2])
            if 1.02 < margin < 1.08:
                result = {
                    "provider": "Vue-Flex-Extract",
                    "closing_home": closing[0],
                    "closing_draw": closing[1],
                    "closing_away": closing[2],
                }
                if data["opening"] and len(data["opening"]) == 3:
                    result["opening_home"] = data["opening"][0]
                    result["opening_draw"] = data["opening"][1]
                    result["opening_away"] = data["opening"][2]
                logger.debug("路径 A 成功: Vue/Flex 布局")
                return result

        # ============================================================
        # 路径 B: Legacy Table 探测（针对历史归档）
        # ============================================================
        legacy_data = await page.evaluate("""
            (providers) => {
                const results = [];
                const rows = document.querySelectorAll('tr');

                for (const row of rows) {
                    const rowText = row.textContent.toLowerCase();

                    for (const provider of providers) {
                        if (rowText.includes(provider.toLowerCase())) {
                            const oddsPattern = /[0-9]\\.[0-9]{2}/g;
                            const matches = rowText.match(oddsPattern);

                            if (matches && matches.length >= 3) {
                                const values = matches.slice(0, 3).map(v => parseFloat(v));
                                results.push({
                                    provider: provider,
                                    values: values
                                });
                                break;
                            }
                        }
                    }
                }
                return results;
            }
        """, self.PREFERRED_PROVIDERS)

        if legacy_data:
            data = legacy_data[0]
            values = data["values"]

            # Margin 校验
            margin = (1.0 / values[0] + 1.0 / values[1] + 1.0 / values[2])
            if 1.02 < margin < 1.08:
                result = {
                    "provider": f"Legacy-Table-{data['provider']}",
                    "closing_home": values[0],
                    "closing_draw": values[1],
                    "closing_away": values[2],
                }
                logger.debug(f"路径 B 成功: Legacy Table ({data['provider']})")
                return result

        # ============================================================
        # 路径 C: 全页初盘深度挖掘（兜底策略）
        # ============================================================
        fallback_data = await page.evaluate("""
            () => {
                const results = [];
                const oddsLinks = document.querySelectorAll('a.odds-link');

                for (const link of oddsLinks) {
                    // 探测所有初盘属性
                    const title = link.getAttribute('title') || '';
                    const dataOpening = link.getAttribute('data-opening') || '';
                    const dataOdds = link.getAttribute('data-odds') || '';

                    const openingRegex = /(?:opening|initial|initial odds|开盘)[:\\s]*([\\d.]+)/i;

                    let openingMatch = title.match(openingRegex);
                    if (!openingMatch && dataOpening) openingMatch = dataOpening.match(/([\\d.]+)/);
                    if (!openingMatch && dataOdds) openingMatch = dataOdds.match(/([\\d.]+)/);

                    if (openingMatch) {
                        const value = parseFloat(openingMatch[1]);
                        if (/^\\d+\\.\\d{2}$/.test(openingMatch[1])) {
                            results.push(value);
                        }
                    }
                }

                return results;
            }
        """)

        if fallback_data and len(fallback_data) >= 3:
            # 取前三个有效值
            values = fallback_data[:3]

            # Margin 校验
            margin = (1.0 / values[0] + 1.0 / values[1] + 1.0 / values[2])
            if 1.02 < margin < 1.08:
                logger.debug("路径 C 成功: 初盘深度挖掘")
                return {
                    "provider": "Opening-Odds-Mining",
                    "closing_home": values[0],
                    "closing_draw": values[1],
                    "closing_away": values[2],
                }

        logger.warning("所有路径探测失败")
        self._stats["provider_not_found"] += 1
        return None

    # ============================================================
    # 第二阶段：扩展数据维度提取
    # ============================================================

    async def _parse_market_average(self, page) -> dict[str, float] | None:
        """
        【第二阶段】提取市场平均值（Market Average）

        通常位于页面底部的特殊区域，表示全场平均值

        Args:
            page: Playwright Page 对象

        Returns:
            包含 home/draw/away 平均值的字典
        """
        try:
            avg_section = await page.query_selector(self.SELECTORS["market_avg_section"])
            if not avg_section:
                logger.debug("未找到市场平均值区域")
                return None

            async def parse_avg(selector: str) -> float | None:
                elem = await avg_section.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    try:
                        return float(text.strip())
                    except (ValueError, TypeError):
                        return None
                return None

            return {
                "home": await parse_avg(self.SELECTORS["market_avg_home"]),
                "draw": await parse_avg(self.SELECTORS["market_avg_draw"]),
                "away": await parse_avg(self.SELECTORS["market_avg_away"]),
            }

        except Exception as e:
            logger.warning(f"提取市场平均值时出错: {e}")
            return None

    # ============================================================
    # 第三阶段：数学有效性校验
    # ============================================================

    def validate_odds_data(self, odds_match: OddsMatch) -> bool:
        """
        【V53 生产级】自动化拦截：数学有效性校验

        校验公式：
        1.02 < 1/A + 1/B + 1/C < 1.08

        原理：
        - 如果赔率来自真实市场，庄家会抽水（overround）
        - 正常情况下 Margin 应该在 1.02 - 1.08 之间
        - 过低（<1.02）可能为异常数据或套利机会
        - 过高（>1.08）可能为错误数据或极端市场

        Args:
            odds_match: 赔率数据对象

        Returns:
            True 表示数据有效，False 表示无效
        """
        # 使用最终系数进行校验
        home_odds = odds_match.closing_home_odds
        draw_odds = odds_match.closing_draw_odds
        away_odds = odds_match.closing_away_odds

        # 检查是否所有系数都存在
        if not all([home_odds, draw_odds, away_odds]):
            odds_match.is_valid = False
            odds_match.validation_error = "缺少必要系数"
            self._stats["validation_failed"] += 1
            return False

        # 计算 Margin = 1/A + 1/B + 1/C
        try:
            margin = (1.0 / home_odds +
                     1.0 / draw_odds +
                     1.0 / away_odds)
        except ZeroDivisionError:
            odds_match.is_valid = False
            odds_match.validation_error = "系数为零值"
            self._stats["validation_failed"] += 1
            return False

        # ========== V53 生产级严格校验 ==========
        # 下限校验：防止异常低赔率
        if margin < self.MIN_ODDS_PRODUCT:
            odds_match.is_valid = False
            odds_match.validation_error = (
                f"Margin 过低: {margin:.4f} < {self.MIN_ODDS_PRODUCT} "
                f"(可能为异常数据)"
            )
            self._stats["validation_failed"] += 1
            logger.warning(
                f"数据异常 [{odds_match.home_team} vs {odds_match.away_team}]: "
                f"{odds_match.validation_error}"
            )
            return False

        # 上限校验：防止异常高抽水
        if margin > self.MAX_ODDS_PRODUCT:
            odds_match.is_valid = False
            odds_match.validation_error = (
                f"Margin 过高: {margin:.4f} > {self.MAX_ODDS_PRODUCT} "
                f"(可能为错误数据或极端市场)"
            )
            self._stats["validation_failed"] += 1
            logger.warning(
                f"数据异常 [{odds_match.home_team} vs {odds_match.away_team}]: "
                f"{odds_match.validation_error}"
            )
            return False

        # V53 生产级校验通过
        odds_match.is_valid = True
        logger.info(f"✓ V53 校验通过: Margin = {margin:.4f} (范围: {self.MIN_ODDS_PRODUCT}-{self.MAX_ODDS_PRODUCT})")
        return True

    def _calculate_drift(
        self,
        opening: float | None,
        closing: float
    ) -> float:
        """
        【V53.3 新增】计算赔率走势特征 (Drift)

        Drift = (Closing - Opening) / Opening

        Args:
            opening: 初盘赔率（可能为 None）
            closing: 终盘赔率

        Returns:
            走势值。正数表示赔率上升（热度下降），负数表示赔率下降（热度上升）
            如果初盘缺失，返回 0.0
        """
        if opening is None or opening == 0:
            return 0.0

        return (closing - opening) / opening

    # ============================================================
    # 第四阶段：人类行为模拟优化
    # ============================================================

    async def _simulate_human_behavior(self, page):
        """
        【第四阶段】模拟真实人类操作

        包含：
        - 随机鼠标移动
        - 随机滚动
        - 模拟阅读停顿
        """
        if not self.enable_mouse:
            return

        try:
            # 随机鼠标移动到页面随机位置
            viewport_size = page.viewport_size
            if viewport_size:
                x = random.randint(100, viewport_size["width"] - 100)
                y = random.randint(100, viewport_size["height"] - 100)
                await page.mouse.move(x, y, steps=random.randint(5, 15))

                # 随机小幅滚动
                scroll_delta = random.randint(-100, 100)
                await page.evaluate(f"window.scrollBy(0, {scroll_delta})")

        except Exception as e:
            logger.debug(f"人类行为模拟时出错: {e}")

    # ============================================================
    # 整合后的主解析函数
    # ============================================================

    async def fetch_match_odds_from_oddsportal(self, match_info: dict) -> OddsMatch | None:
        """
        【整合版】从 Primary_Source 获取单场比赛赔率

        完整流程：
        1. 构造目标 URL
        2. 访问页面并模拟人类行为
        3. 【第一阶段】从单一机构行提取赔率
        4. 【第二阶段】提取市场平均值
        5. 【第三阶段】数学有效性校验
        6. 【第四阶段】人类行为模拟延迟

        Args:
            match_info: 比赛信息 {match_id, home_team, away_team, league_name, match_date}

        Returns:
            OddsMatch or None
        """
        self._stats["total_fetched"] += 1

        home_team = match_info["home_team"]
        away_team = match_info["away_team"]
        league = match_info["league_name"]

        # 获取 OddsPortal 球队名
        oddsportal_home = self.get_oddsportal_team_name(home_team, league)
        oddsportal_away = self.get_oddsportal_team_name(away_team, league)

        if not oddsportal_home or not oddsportal_away:
            logger.warning(f"球队映射缺失: {home_team} vs {away_team} ({league})")
            return None

        # 构造 OddsPortal URL
        league_path = self.LEAGUE_MAPPING.get(league)
        if not league_path:
            logger.warning(f"联赛不支持: {league}")
            return None

        # 构造真实 OddsPortal URL (V53 生产环境)
        base_url = "https://www.oddsportal.com/football"
        url = f"{base_url}/{league_path}/{oddsportal_home}-{oddsportal_away}"

        try:
            # 访问页面
            logger.debug(f"访问: {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=30000)

            # 【第四阶段】模拟人类行为
            await self._simulate_human_behavior(self.page)
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # 【第一阶段】核心解析：从单一机构行提取数据
            provider_data = await self._parse_primary_provider_row(self.page)

            if not provider_data:
                logger.warning(f"未找到可用的 Primary_Source: {home_team} vs {away_team}")
                return None

            # 【第二阶段】提取市场平均值
            market_avg = await self._parse_market_average(self.page)

            # 构造赔率对象
            odds_match = OddsMatch(
                match_id=match_info["match_id"],
                home_team=home_team,
                away_team=away_team,
                league_name=league,
                match_date=match_info["match_date"],
                primary_provider=provider_data.get("provider"),
                opening_home_odds=provider_data.get("opening_home"),
                opening_draw_odds=provider_data.get("opening_draw"),
                opening_away_odds=provider_data.get("opening_away"),
                closing_home_odds=provider_data.get("closing_home"),
                closing_draw_odds=provider_data.get("closing_draw"),
                closing_away_odds=provider_data.get("closing_away"),
                market_avg_home=market_avg.get("home") if market_avg else None,
                market_avg_draw=market_avg.get("draw") if market_avg else None,
                market_avg_away=market_avg.get("away") if market_avg else None,
                data_timestamp=datetime.now(),
            )

            # 【第三阶段】数学有效性校验
            if not self.validate_odds_data(odds_match):
                logger.warning(
                    f"数据校验失败，已标记为 invalid: {home_team} vs {away_team}"
                )
                # 仍然返回对象，但标记为无效
                return odds_match

            # 校验通过
            self._stats["success_count"] += 1
            logger.info(f"✓ 成功提取: {home_team} vs {away_team} (来源: {provider_data.get('provider')})")

            return odds_match

        except Exception as e:
            logger.error(f"获取赔率失败 [{home_team} vs {away_team}]: {e}")
            return None

    async def collect_matches_by_year(self, year: int = 2026) -> list[OddsMatch]:
        """
        采集指定年份的比赛赔率

        Args:
            year: 目标年份（默认 2026）

        Returns:
            List[OddsMatch]: 成功采集的比赛赔率列表
        """
        # 加载球队映射
        self.load_team_mapping()

        # 获取指定年份的比赛列表
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                match_id,
                home_team,
                away_team,
                league_name,
                match_date
            FROM matches
            WHERE match_date >= %s
              AND match_date <= %s
            ORDER BY match_date DESC
        """, (f"{year}-01-01", f"{year}-12-31"))

        matches = cursor.fetchall()
        logger.info(f"找到 {len(matches)} 场 {year} 年比赛")

        results = []
        missing_mapping = []

        for i, match in enumerate(matches, 1):
            match_info = {
                "match_id": match["match_id"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "league_name": match["league_name"],
                "match_date": match["match_date"],
            }

            odds_match = await self.fetch_match_odds_from_oddsportal(match_info)

            if odds_match:
                results.append(odds_match)
                logger.info(f"[{i}/{len(matches)}] ✓ {match['home_team']} vs {match['away_team']}")
            else:
                # 检查是否为映射缺失
                if not self.get_oddsportal_team_name(match["home_team"], match["league_name"]):
                    missing_mapping.append(f"{match['home_team']} ({match['league_name']})")
                if not self.get_oddsportal_team_name(match["away_team"], match["league_name"]):
                    missing_mapping.append(f"{match['away_team']} ({match['league_name']})")

            # 随机延迟
            if i < len(matches):
                await self._random_delay()

            # 进度报告
            if i % 50 == 0:
                logger.info(f"进度: {i}/{len(matches)} ({i/len(matches)*100:.1f}%)")

        # 报告缺失映射
        if missing_mapping:
            unique_missing = sorted(set(missing_mapping))
            logger.warning(f"")
            logger.warning(f"【Missing Mapping 报警】")
            logger.warning(f"以下 {len(unique_missing)} 支球队缺少映射:")
            for team in unique_missing[:20]:
                logger.warning(f"  - {team}")
            if len(unique_missing) > 20:
                logger.warning(f"  ... 还有 {len(unique_missing) - 20} 支球队")

        return results

    def save_odds_to_prematch_features(self, odds_matches: list[OddsMatch]) -> dict[str, Any]:
        """
        【扩展版】将赔率数据保存到 prematch_features 表

        新增字段支持：
        - primary_provider: 数据来源机构
        - market_avg_*: 市场平均值
        - is_valid: 数据是否通过校验
        - validation_error: 校验失败原因
        - data_timestamp: 采集时间戳

        Args:
            odds_matches: 赔率数据列表

        Returns:
            保存结果统计
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # 检查表结构是否支持新字段（包括 drift）
        check_columns_sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'prematch_features'
              AND column_name IN ('primary_provider', 'market_avg_home',
                                 'is_valid', 'validation_error', 'data_timestamp',
                                 'home_odds_drift', 'draw_odds_drift', 'away_odds_drift')
        """
        cursor.execute(check_columns_sql)
        existing_columns = {row["column_name"] for row in cursor.fetchall()}

        # 根据表结构动态构建 SQL
        has_drift = all(col in existing_columns for col in ["home_odds_drift", "draw_odds_drift", "away_odds_drift"])

        if all(col in existing_columns for col in ["primary_provider", "is_valid"]):
            # 新表结构：包含所有字段
            if has_drift:
                update_sql = """
                    UPDATE prematch_features
                    SET
                        primary_provider = %s,
                        opening_home_odds = %s,
                        opening_draw_odds = %s,
                        opening_away_odds = %s,
                        closing_home_odds = %s,
                        closing_draw_odds = %s,
                        closing_away_odds = %s,
                        home_odds_drift = %s,
                        draw_odds_drift = %s,
                        away_odds_drift = %s,
                        market_avg_home = %s,
                        market_avg_draw = %s,
                        market_avg_away = %s,
                        is_valid = %s,
                        validation_error = %s,
                        data_timestamp = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """
            else:
                update_sql = """
                    UPDATE prematch_features
                    SET
                        primary_provider = %s,
                        opening_home_odds = %s,
                        opening_draw_odds = %s,
                        opening_away_odds = %s,
                        closing_home_odds = %s,
                        closing_draw_odds = %s,
                        closing_away_odds = %s,
                        market_avg_home = %s,
                        market_avg_draw = %s,
                        market_avg_away = %s,
                        is_valid = %s,
                        validation_error = %s,
                        data_timestamp = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """
        else:
            # 旧表结构：仅包含基础字段
            update_sql = """
                UPDATE prematch_features
                SET
                    opening_home_odds = %s,
                    opening_draw_odds = %s,
                    opening_away_odds = %s,
                    closing_home_odds = %s,
                    closing_draw_odds = %s,
                    closing_away_odds = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """

        stats = {
            "total": len(odds_matches),
            "saved": 0,
            "skipped_invalid": 0,
            "skipped_no_opening": 0,
            "errors": 0,
        }

        for odds_match in odds_matches:
            # 【V53.3 新增】检查是否有初盘数据
            has_opening = all([
                odds_match.opening_home_odds,
                odds_match.opening_draw_odds,
                odds_match.opening_away_odds
            ])

            # 【第三阶段】自动拦截：不保存校验失败的数据
            if not odds_match.is_valid:
                stats["skipped_invalid"] += 1
                logger.debug(f"跳过无效数据: {odds_match.match_id}")
                continue

            # 【V53.3 新增】跳过无初盘的数据（可选，根据需求）
            # if not has_opening:
            #     stats["skipped_no_opening"] += 1
            #     logger.debug(f"跳过无初盘数据: {odds_match.match_id}")
            #     continue

            try:
                # 【V53.3 新增】计算 drift 值
                home_drift = self._calculate_drift(
                    odds_match.opening_home_odds,
                    odds_match.closing_home_odds
                )
                draw_drift = self._calculate_drift(
                    odds_match.opening_draw_odds,
                    odds_match.closing_draw_odds
                )
                away_drift = self._calculate_drift(
                    odds_match.opening_away_odds,
                    odds_match.closing_away_odds
                )

                if "primary_provider" in existing_columns:
                    # 新表结构
                    if has_drift:
                        cursor.execute(update_sql, (
                            odds_match.primary_provider,
                            odds_match.opening_home_odds,
                            odds_match.opening_draw_odds,
                            odds_match.opening_away_odds,
                            odds_match.closing_home_odds,
                            odds_match.closing_draw_odds,
                            odds_match.closing_away_odds,
                            home_drift,
                            draw_drift,
                            away_drift,
                            odds_match.market_avg_home,
                            odds_match.market_avg_draw,
                            odds_match.market_avg_away,
                            odds_match.is_valid,
                            odds_match.validation_error,
                            odds_match.data_timestamp,
                            odds_match.match_id,
                        ))
                    else:
                        cursor.execute(update_sql, (
                            odds_match.primary_provider,
                            odds_match.opening_home_odds,
                            odds_match.opening_draw_odds,
                            odds_match.opening_away_odds,
                            odds_match.closing_home_odds,
                            odds_match.closing_draw_odds,
                            odds_match.closing_away_odds,
                            odds_match.market_avg_home,
                            odds_match.market_avg_draw,
                            odds_match.market_avg_away,
                            odds_match.is_valid,
                            odds_match.validation_error,
                            odds_match.data_timestamp,
                            odds_match.match_id,
                        ))
                else:
                    # 旧表结构
                    cursor.execute(update_sql, (
                        odds_match.opening_home_odds,
                        odds_match.opening_draw_odds,
                        odds_match.opening_away_odds,
                        odds_match.closing_home_odds,
                        odds_match.closing_draw_odds,
                        odds_match.closing_away_odds,
                        odds_match.match_id,
                    ))

                if cursor.rowcount > 0:
                    stats["saved"] += 1

            except Exception as e:
                logger.error(f"保存失败 [{odds_match.match_id}]: {e}")
                stats["errors"] += 1

        conn.commit()

        # 记录统计信息
        logger.info(f"")
        logger.info(f"【V53.3 保存统计】")
        logger.info(f"  总数: {stats['total']}")
        logger.info(f"  成功: {stats['saved']}")
        logger.info(f"  跳过（校验失败）: {stats['skipped_invalid']}")
        logger.info(f"  跳过（无初盘）: {stats['skipped_no_opening']}")
        logger.info(f"  错误: {stats['errors']}")

        return stats

    def get_statistics(self) -> dict[str, Any]:
        """
        获取采集统计信息

        Returns:
            统计数据字典
        """
        return self._stats.copy()


# ============================================================
# 便捷函数
# ============================================================

async def quick_collect_2025_odds() -> dict[str, Any]:
    """
    快速采集 2025 年赔率数据（保留兼容性）

    Returns:
        采集结果摘要
    """
    return await quick_collect_odds_by_year(2025)


async def quick_collect_odds_by_year(year: int = 2026) -> dict[str, Any]:
    """
    快速采集指定年份的赔率数据

    Args:
        year: 目标年份（默认 2026）

    Returns:
        采集结果摘要
    """
    scraper = None
    try:
        scraper = OddsPortalScraper(headless=True)
        await scraper.start()

        # 采集比赛
        odds_matches = await scraper.collect_matches_by_year(year)

        # 保存到数据库
        saved_stats = scraper.save_odds_to_prematch_features(odds_matches)

        # 统计初盘数据
        with_opening = sum(1 for m in odds_matches
                          if all([m.opening_home_odds, m.opening_draw_odds, m.opening_away_odds]))

        return {
            "status": "success",
            "year": year,
            "total_matches": len(odds_matches),
            "with_opening_closing": with_opening,
            "saved_records": saved_stats.get("saved", 0),
            "skipped_invalid": saved_stats.get("skipped_invalid", 0),
            "skipped_no_opening": saved_stats.get("skipped_no_opening", 0),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"采集失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        if scraper:
            await scraper.close()


if __name__ == "__main__":
    # 测试采集
    result = asyncio.run(quick_collect_2025_odds())
    print()
    print("=" * 60)
    print("【采集服务运行状态报告】")
    print("=" * 60)
    print()
    print(f"状态: {result['status']}")
    if result['status'] == 'success':
        print(f"成功采集: {result['total_matches']} 场比赛")
        print(f"保存记录: {result['saved_records']} 条")
        print(f"完成时间: {result['timestamp']}")
    else:
        print(f"错误: {result.get('error', 'Unknown')}")
    print()
    print("=" * 60)
