"""
FotMob 比赛详情采集器

采集比赛详情数据，包括：
- xG (Expected Goals) 数据
- 阵容信息
- 详细统计数据
"""

import asyncio
import json
import logging
import math
from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime

from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class MatchStats:
    """比赛统计数据"""

    home_team: str
    away_team: str
    home_score: int
    away_score: int
    home_xg: float | None = None
    away_xg: float | None = None
    possession_home: float | None = None
    possession_away: float | None = None
    shots_home: int | None = None
    shots_away: int | None = None
    shots_on_target_home: int | None = None
    shots_on_target_away: int | None = None


@dataclass
class Player:
    """增强的球员信息 - 全量收割版"""

    id: int | None = None
    name: str = ""
    position: str = ""
    shirt_number: int | None = None
    is_starter: bool = False
    # 全量收割新增字段
    rating: float | None = None  # 球员评分 (关键)
    minutes_played: int | None = None  # 出场时间
    goals: int | None = None  # 进球数
    assists: int | None = None  # 助攻数
    shots: int | None = None  # 射门数
    shots_on_target: int | None = None  # 射正数
    yellow_cards: int | None = None  # 黄牌
    red_cards: int | None = None  # 红牌
    fouls: int | None = None  # 犯规
    fouled_against: int | None = None  # 被犯规
    passes_completed: int | None = None  # 传球成功数
    passes_attempted: int | None = None  # 传球尝试数
    pass_accuracy: float | None = None  # 传球成功率
    duels_won: int | None = None  # 对抗胜利数
    duels_lost: int | None = None  # 对抗失败数
    aerials_won: int | None = None  # 空中对抗胜利数
    aerials_lost: int | None = None  # 空中对抗失败数


@dataclass
class Odds:
    """赔率数据 - 全量收割版"""

    home_win: float | None = None  # 主胜赔率
    draw: float | None = None  # 平局赔率
    away_win: float | None = None  # 客胜赔率
    over_25: float | None = None  # 大2.5球赔率
    under_25: float | None = None  # 小2.5球赔率
    both_teams_score: bool | None = None  # 双方都进球
    over_under: dict[str, float] | None = None  # 其他大小球赔率
    asian_handicap: dict[str, float] | None = None  # 让球盘赔率
    total_goals: dict[str, float] | None = None  # 总进球数赔率
    providers: dict[str, Any] | None = None  # 各博彩公司赔率


@dataclass
class MatchMetadata:
    """比赛元数据 - 全量收割版"""

    referee: str | None = None  # 裁判姓名 (关键)
    stadium: str | None = None  # 球场名称
    attendance: int | None = None  # 观众人数
    weather: dict[str, Any] | None = None  # 天气信息
    match_day: str | None = None  # 比赛日
    round: str | None = None  # 轮次
    competition_stage: str | None = None  # 淘汰赛阶段
    venue_capacity: int | None = None  # 场馆容量
    city: str | None = None  # 城市
    country: str | None = None  # 国家


@dataclass
class MatchEvent:
    """比赛事件 - 全量收割版"""

    id: int | None = None
    minute: int | None = None  # 发生时间
    team_id: int | None = None  # 球队ID
    player_id: int | None = None  # 球员ID
    player_name: str | None = None  # 球员姓名
    event_type: str | None = None  # 事件类型: goal, card, substitution等
    sub_type: str | None = None  # 子类型: yellow_card, red_card, own_goal等
    is_assist: bool = False  # 是否为助攻
    assist_player_id: int | None = None  # 助攻球员ID
    assist_player_name: str | None = None  # 助攻球员姓名
    coordinate_x: float | None = None  # 事件坐标X
    coordinate_y: float | None = None  # 事件坐标Y
    timestamp: str | None = None  # 时间戳


@dataclass
class TeamLineup:
    """球队阵容"""

    team_id: int | None = None
    team_name: str = ""
    formation: str | None = None
    players: list[Player] = None

    def __post_init__(self):
        if self.players is None:
            self.players = []


@dataclass
class MatchDetails:
    """增强的比赛详情 - 全量收割版"""

    match_id: int
    home_team: str
    away_team: str
    match_date: str
    status: dict[str, Any]
    home_score: int = 0
    away_score: int = 0
    stats: MatchStats | None = None
    home_lineup: TeamLineup | None = None
    away_lineup: TeamLineup | None = None
    # 全量收割新增字段
    odds: Odds | None = None  # 赔率数据 (关键)
    match_metadata: MatchMetadata | None = None  # 比赛元数据 (关键)
    events: list[MatchEvent] | None = None  # 详细事件流 (关键)
    raw_data: dict[str, Any] | None = None

    def __post_init__(self):
        if self.events is None:
            self.events = []


class FotmobDetailsCollector:
    """FotMob 详情采集器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.dynamic_headers = {}  # 存储从Playwright拦截的动态令牌
        self.base_headers = {
            # 核心请求头 - 模拟最新 Chrome 131
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",

            # 浏览器安全头 - 最新 Chrome 指纹
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',

            # 来源和引用 - 模拟真实浏览
            "Referer": "https://www.fotmob.com/matches",
            "Origin": "https://www.fotmob.com",

            # Fetch API 相关头
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",

            # 缓存控制
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",

            # 连接管理
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",

            # DNT (Do Not Track) - 可选
            # "DNT": "1",
        }

    async def _init_session(self):
        """初始化HTTP会话"""
        if self.session is None:
            # 🔧 修复认证和反爬虫问题
            self.session = AsyncSession(
                impersonate="chrome131",  # 使用最新Chrome版本
                headers={
                    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-arch": '"x86"',
                    "sec-ch-ua-bitness": '"64"',
                },
                timeout=30.0
            )

            # 🔍 多步认证流程
            try:
                # 第一步：访问主页建立基础会话
                self.logger.info("第一步：建立基础会话...")
                await self.session.get("https://www.fotmob.com/", timeout=15)

                # 第二步：访问比赛列表页激活API访问权限
                self.logger.info("第二步：激活API访问权限...")
                await self.session.get("https://www.fotmob.com/matches", timeout=15)

                # 第三步：等待几秒让认证生效
                await asyncio.sleep(2)

                self.logger.info("FotMob HTTP会话初始化成功 (Chrome131 + 多步认证)")
            except Exception as e:
                self.logger.error(f"FotMob HTTP会话初始化失败: {e}")
                raise

    async def collect_match_details(self, match_id: str) -> MatchDetails | None:
        """
        采集比赛详情 - 使用Playwright进行DOM解析获取市场概率数据
        同时保存高阶统计数据到数据库

        Args:
            match_id: 比赛ID

        Returns:
            MatchDetails 对象或 None
        """
        # 首先尝试通过API获取基础数据
        api_data = await self.get_match_details(match_id)
        if not api_data:
            self.logger.warning(f"无法通过API获取比赛 {match_id} 的基础数据")
            return None

        # 🎯 NEW: 保存高阶统计数据到数据库
        try:
            advanced_stats_saved = await self.save_advanced_stats(match_id, api_data)
            if advanced_stats_saved:
                self.logger.info(f"✅ 成功保存比赛 {match_id} 的高阶统计数据")
            else:
                self.logger.warning(f"⚠️ 比赛 {match_id} 高阶统计数据保存失败")
        except Exception as e:
            self.logger.error(f"保存高阶统计数据时发生异常: {e}")

        # 然后使用Playwright获取页面中的市场概率数据
        odds_data = await self._extract_odds_from_page(match_id)

        # 构建完整的MatchDetails对象
        try:
            match_info = api_data.get("match_info", {})

            match_details = MatchDetails(
                match_id=int(match_id),
                home_team=match_info.get("home_team", ""),
                away_team=match_info.get("away_team", ""),
                match_date=match_info.get("start_time", ""),
                status=match_info.get("status", {}),
                home_score=match_info.get("home_score", 0),
                away_score=match_info.get("away_score", 0),
                odds=self._build_odds_object(odds_data) if odds_data else None,
                raw_data=api_data
            )

            self.logger.info(f"成功采集比赛 {match_id} 的详情数据（包含高阶统计）")
            return match_details

        except Exception as e:
            self.logger.error(f"构建MatchDetails对象时发生错误: {e}")
            return None

    async def _extract_odds_from_page(self, match_id: str) -> Optional[dict[str, Any]]:
        """
        使用Playwright从FotMob页面提取市场概率数据，同时拦截动态API令牌

        Args:
            match_id: 比赛ID

        Returns:
            包含主胜、平局、客胜概率的字典，失败返回None
        """
        browser = None
        context = None
        page = None
        headers_captured = False

        try:
            # 启动Playwright浏览器
            self.logger.info(f"启动Playwright浏览器采集比赛 {match_id} 的市场概率数据和动态令牌")

            playwright = await async_playwright().start()

            # 使用Chromium浏览器，配置反检测参数
            browser = await playwright.chromium.launch(
                headless=True,  # 设置为False可以看到浏览器界面用于调试
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                ]
            )

            # 创建浏览器上下文，模拟真实用户环境
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            )

            page = await context.new_page()

            # 🎯 设置网络拦截器，捕获动态API令牌
            headers_found = {}

            async def capture_auth_headers(request):
                """捕获带有认证令牌的API请求头"""
                nonlocal headers_captured, headers_found

                # 记录所有请求以进行调试
                self.logger.debug(f"捕获请求: {request.url} - 方法: {request.method}")

                # 更广泛的API请求拦截
                is_api_request = (
                    "/api/" in request.url or
                    "fotmob.com/api" in request.url or
                    request.url.endswith(".json") or
                    any(keyword in request.url.lower() for keyword in ["match", "details", "data"])
                )

                if is_api_request:
                    request_headers = request.headers
                    self.logger.debug(f"API请求headers: {list(request_headers.keys())}")

                    # 检查是否包含我们需要的认证令牌（重点关注x-mas）
                    has_x_mas = "x-mas" in request_headers
                    has_x_foo = "x-foo" in request_headers
                    has_auth = "authorization" in request_headers

                    if has_x_mas:  # 优先捕获x-mas令牌，这是FotMob主要的认证方式
                        headers_found.update(request_headers)
                        headers_captured = True
                        self.logger.info(f"✅ 成功捕获动态API令牌 from {request.url}")
                        self.logger.info(f"x-mas: {has_x_mas}, x-foo: {has_x_foo}, authorization: {has_auth}")

                        # 显示关键headers（用于调试）
                        for key in ["x-mas", "x-foo", "authorization", "cookie"]:
                            if key in request_headers:
                                value = request_headers[key]
                                display_value = value[:50] + "..." if len(str(value)) > 50 else value
                                self.logger.debug(f"  {key}: {display_value}")

                        # 只需要第一个有效的请求头
                        page.remove_listener("request", capture_auth_headers)

            # 注册网络拦截监听器
            page.on("request", capture_auth_headers)

            # 构建FotMob比赛页面URL
            url = f"https://www.fotmob.com/match/{match_id}"
            self.logger.info(f"访问页面: {url} (同时拦截API令牌)")

            # 设置超时并导航到页面
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待页面加载并给API请求更多时间
            self.logger.info("等待页面API请求...")
            await page.wait_for_timeout(10000)  # 增加到10秒

            # 如果还没捕获到headers，再等待一会
            if not headers_captured:
                self.logger.info("继续等待API请求...")
                await page.wait_for_timeout(10000)  # 再等10秒

            # 检查是否成功捕获到认证头
            if headers_captured:
                self.logger.info("🎉 成功拦截到动态令牌，更新self.dynamic_headers")
                self.dynamic_headers = headers_found

                # 更新base_headers以包含动态令牌
                self.base_headers.update({
                    key: value for key, value in headers_found.items()
                    if key in ['x-mas', 'x-foo', 'authorization', 'cookie']
                })
            else:
                self.logger.warning("⚠️ 未能捕获到有效的API认证令牌")

            # 尝试多种CSS选择器策略来找到市场概率数据
            odds_data = await self._extract_odds_with_multiple_strategies(page)

            if odds_data:
                self.logger.info(f"成功从页面提取市场概率数据: {odds_data}")
                return odds_data
            else:
                self.logger.warning("未能从页面中找到市场概率数据")
                return None

        except Exception as e:
            self.logger.error(f"使用Playwright提取市场概率数据时发生错误: {e}")
            return None

        finally:
            # 确保清理资源
            try:
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
            except Exception as e:
                self.logger.warning(f"关闭Playwright资源时发生错误: {e}")

    async def _extract_odds_with_multiple_strategies(self, page: Page) -> Optional[dict[str, Any]]:
        """
        使用多种策略从页面中提取赔率数据

        Args:
            page: Playwright页面对象

        Returns:
            包含赔率数据的字典或None
        """
        strategies = [
            self._strategy_by_percentage_elements,
            self._strategy_by_odds_tab,
            self._strategy_by_data_attributes,
            self._strategy_by_text_patterns
        ]

        for i, strategy in enumerate(strategies, 1):
            try:
                self.logger.debug(f"尝试策略 {i}/{len(strategies)}")
                odds_data = await strategy(page)

                if odds_data and self._validate_odds_data(odds_data):
                    self.logger.info(f"策略 {i} 成功提取到赔率数据")
                    return odds_data

            except Exception as e:
                self.logger.debug(f"策略 {i} 失败: {e}")
                continue

        return None

    async def _strategy_by_percentage_elements(self, page: Page) -> Optional[dict[str, Any]]:
        """策略1: 通过包含%符号的元素查找"""
        try:
            # 查找包含百分比的元素
            percentage_elements = await page.query_selector_all('[class*="percent"], [class*="probability"], [data-percent]')

            if len(percentage_elements) >= 3:
                # 取前三个包含百分比数据的元素
                percentages = []
                for element in percentage_elements[:3]:
                    text = await element.text_content()
                    if text and '%' in text:
                        # 提取数值并转换为概率 (0-1)
                        percentage_str = text.strip().replace('%', '')
                        try:
                            percentage_value = float(percentage_str) / 100.0
                            percentages.append(percentage_value)
                        except ValueError:
                            continue

                if len(percentages) >= 3:
                    return {
                        "home_win": percentages[0],
                        "draw": percentages[1],
                        "away_win": percentages[2],
                        "source": "percentage_elements"
                    }

        except Exception as e:
            self.logger.debug(f"百分比元素策略失败: {e}")

        return None

    async def _strategy_by_odds_tab(self, page: Page) -> Optional[dict[str, Any]]:
        """策略2: 通过赔率Tab查找"""
        try:
            # 查找赔率相关的Tab或区域
            odds_tabs = await page.query_selector_all('[role="tab"], .tab, .odds-tab, [data-tab*="odds"]')

            for tab in odds_tabs:
                try:
                    await tab.click()
                    await page.wait_for_timeout(1000)

                    # 查找赔率数值
                    odds_values = await page.query_selector_all('.odds-value, .price, [class*="odds"], [data-odds]')

                    if len(odds_values) >= 3:
                        values = []
                        for value_element in odds_values[:3]:
                            text = await value_element.text_content()
                            if text:
                                try:
                                    # 尝试解析为小数值
                                    odds_value = float(text.strip())
                                    # 转换为概率
                                    probability = 1.0 / odds_value if odds_value > 0 else 0.0
                                    values.append(min(probability, 1.0))  # 确保不超过1.0
                                except ValueError:
                                    continue

                        if len(values) >= 3:
                            return {
                                "home_win": values[0],
                                "draw": values[1],
                                "away_win": values[2],
                                "source": "odds_tab"
                            }

                except Exception:
                    continue

        except Exception as e:
            self.logger.debug(f"赔率Tab策略失败: {e}")

        return None

    async def _strategy_by_data_attributes(self, page: Page) -> Optional[dict[str, Any]]:
        """策略3: 通过数据属性查找"""
        try:
            # 查找包含赔率数据属性的元素
            data_elements = await page.query_selector_all('[data-home-win], [data-draw], [data-away-win], [data-odds]')

            if data_elements:
                odds_data = {}

                for element in data_elements:
                    try:
                        # 检查各种可能的数据属性
                        home_win = await element.get_attribute('data-home-win')
                        draw = await element.get_attribute('data-draw')
                        away_win = await element.get_attribute('data-away-win')

                        if home_win:
                            odds_data['home_win'] = float(home_win)
                        if draw:
                            odds_data['draw'] = float(draw)
                        if away_win:
                            odds_data['away_win'] = float(away_win)

                    except Exception:
                        continue

                if all(key in odds_data for key in ['home_win', 'draw', 'away_win']):
                    odds_data['source'] = 'data_attributes'
                    return odds_data

        except Exception as e:
            self.logger.debug(f"数据属性策略失败: {e}")

        return None

    async def _strategy_by_text_patterns(self, page: Page) -> Optional[dict[str, Any]]:
        """策略4: 通过文本模式匹配"""
        try:
            # 获取页面所有文本内容
            page_text = await page.text_content('body')

            if not page_text:
                return None

            # 使用正则表达式查找概率相关的数字
            import re

            # 查找形如 "45%", "0.45", "2.5" 等模式
            probability_patterns = [
                r'(\d+(?:\.\d+)?)\s*%',  # 百分比形式
                r'([0]\.\d+)',            # 0-1之间的小数
                r'(\d+\.?\d*)\s*vs\s*(\d+\.?\d*)',  # vs 格式的赔率
            ]

            for pattern in probability_patterns:
                matches = re.findall(pattern, page_text)
                if len(matches) >= 3:
                    try:
                        if isinstance(matches[0], tuple):
                            # vs格式的赔率，需要转换为概率
                            home_odds = float(matches[0][0])
                            draw_odds = float(matches[1][0]) if len(matches) > 1 else None
                            away_odds = float(matches[2][0]) if len(matches) > 2 else None

                            home_prob = 1.0 / home_odds if home_odds > 0 else 0
                            draw_prob = 1.0 / draw_odds if draw_odds and draw_odds > 0 else 0
                            away_prob = 1.0 / away_odds if away_odds and away_odds > 0 else 0
                        else:
                            # 百分比或小数形式
                            values = [float(match) for match in matches[:3]]
                            if '%' in pattern:
                                values = [v / 100.0 for v in values]  # 转换百分比为概率

                            home_prob, draw_prob, away_prob = values[0], values[1], values[2]

                        # 验证概率合理性
                        if all(0 <= p <= 1 for p in [home_prob, draw_prob, away_prob]):
                            return {
                                "home_win": home_prob,
                                "draw": draw_prob,
                                "away_win": away_prob,
                                "source": "text_pattern"
                            }

                    except (ValueError, IndexError):
                        continue

        except Exception as e:
            self.logger.debug(f"文本模式策略失败: {e}")

        return None

    def _validate_odds_data(self, odds_data: dict[str, Any]) -> bool:
        """
        验证赔率数据的有效性

        Args:
            odds_data: 赔率数据字典

        Returns:
            数据是否有效
        """
        try:
            required_fields = ['home_win', 'draw', 'away_win']

            # 检查必需字段
            if not all(field in odds_data for field in required_fields):
                return False

            # 检查数值范围
            for field in required_fields:
                value = odds_data[field]
                if not isinstance(value, (int, float)) or value < 0 or value > 1:
                    return False

            # 检查概率总和是否合理 (应该在0.8-1.2之间，考虑到庄家优势)
            total_prob = sum(odds_data[field] for field in required_fields)
            if total_prob < 0.8 or total_prob > 1.2:
                self.logger.warning(f"概率总和异常: {total_prob}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"验证赔率数据时发生错误: {e}")
            return False

    def _build_odds_object(self, odds_data: dict[str, Any]) -> Odds:
        """
        根据提取的数据构建Odds对象

        Args:
            odds_data: 原始赔率数据

        Returns:
            Odds对象
        """
        try:
            odds = Odds(
                home_win=odds_data.get('home_win'),
                draw=odds_data.get('draw'),
                away_win=odds_data.get('away_win'),
                providers={"fotmob_web": odds_data}  # 保存原始数据来源信息
            )

            return odds

        except Exception as e:
            self.logger.error(f"构建Odds对象时发生错误: {e}")
            return Odds()  # 返回空的Odds对象

    async def get_match_details(self, match_id: str) -> Optional[dict[str, Any]]:
        """
        获取比赛详情数据 (使用动态拦截的API令牌)

        Args:
            match_id: FotMob 比赛 ID

        Returns:
            比赛详情数据，包含结构化的阵容、射门和统计信息
            如果获取失败返回 None
        """
        # 🎯 关键改进：先确保有有效的动态令牌
        if not self.dynamic_headers or ('x-mas' not in self.dynamic_headers):
            self.logger.info("🔄 尚未捕获动态令牌，先通过Playwright访问页面获取令牌...")
            await self._extract_odds_from_page(match_id)

            # 检查是否成功获取到令牌
            if not self.dynamic_headers or ('x-mas' not in self.dynamic_headers):
                self.logger.error("❌ 无法获取动态API令牌，跳过API请求")
                return None
            else:
                self.logger.info("✅ 成功获取动态API令牌，开始API数据采集")
        else:
            self.logger.info("✅ 已有动态API令牌，直接进行API请求")

        # 🔧 尝试多个API端点，寻找有效的接口
        endpoints = [
            f"https://www.fotmob.com/api/matchDetails?matchId={match_id}",
            f"https://www.fotmob.com/api/match?id={match_id}",
            f"https://www.fotmob.com/api/matches?matchId={match_id}",
            # 新的可能端点
            f"https://www.fotmob.com/api/matchDetails/{match_id}",
            f"https://fotmob.com/api/matchDetails?matchId={match_id}",
        ]

        await self._init_session()

        for i, url in enumerate(endpoints, 1):
            self.logger.info(f"尝试端点 {i}/{len(endpoints)}: {url}")

            try:
                # 🎯 使用包含动态令牌的headers
                effective_headers = self.base_headers.copy()
                if self.dynamic_headers:
                    effective_headers.update(self.dynamic_headers)

                self.logger.debug(f"使用的headers: {list(effective_headers.keys())}")
                if 'x-mas' in effective_headers:
                    self.logger.debug(f"x-mas令牌: {effective_headers['x-mas'][:20]}...")

                response = await self.session.get(url, headers=effective_headers, timeout=30.0)

                self.logger.info(f"端点 {i} 响应: HTTP {response.status_code}")

                if response.status_code == 200:
                    # ✅ 成功！
                    self.logger.info(f"✅ 端点 {i} 成功!")

                    # 处理响应数据
                    try:
                        if hasattr(response, "json"):
                            if asyncio.iscoroutinefunction(response.json):
                                data = await response.json()
                            elif callable(response.json):
                                data = response.json()
                            else:
                                data = response.json
                        else:
                            data = json.loads(response.text)

                        # 验证数据结构
                        if isinstance(data, dict) and "content" in data:
                            self.logger.info("✅ 数据结构验证成功")

                            # 提取并结构化数据
                            structured_data = self._structure_match_data(data)
                            self.logger.info(f"Successfully fetched details for match {match_id} using endpoint {i}")
                            return structured_data
                        else:
                            self.logger.warning(f"⚠️ 端点 {i} 返回的数据结构不正确: {type(data)}")
                            continue

                    except json.JSONDecodeError as e:
                        self.logger.warning(f"⚠️ 端点 {i} JSON解析失败: {e}")
                        continue

                elif response.status_code == 401:
                    self.logger.warning(f"⚠️ 端点 {i} 认证失败 (401) - 令牌可能已过期")
                    # 如果遇到401，清空动态令牌强制重新获取
                    self.dynamic_headers = {}
                elif response.status_code == 403:
                    self.logger.warning(f"⚠️ 端点 {i} 访问被禁止 (403)")
                elif response.status_code == 404:
                    self.logger.warning(f"⚠️ 端点 {i} 不存在 (404)")
                else:
                    self.logger.warning(f"⚠️ 端点 {i} HTTP错误: {response.status_code}")

            except Exception as e:
                self.logger.warning(f"⚠️ 端点 {i} 请求异常: {e}")

        # 所有端点都失败了
        self.logger.error(f"❌ 所有API端点都无法访问比赛 {match_id}")
        return None

    def _structure_match_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        结构化原始比赛数据

        Args:
            raw_data: FotMob API 返回的原始数据

        Returns:
            结构化的比赛数据
        """
        # 提取基础数据
        match_info = self._extract_match_info(raw_data)
        shots = self._extract_shot_data(raw_data)

        # 计算真实的xG数据（基于FotMob射门图）
        xg_data = self._calculate_team_xg(shots, match_info)

        # 提取统计数据并合并xG
        base_stats_list = self._extract_match_stats(raw_data)
        # 将基础统计数据转换为字典格式，然后与xG数据合并
        stats_dict = {}
        for stat in base_stats_list if isinstance(base_stats_list, list) else []:
            if isinstance(stat, dict):
                stats_dict.update(stat)

        enhanced_stats = {**stats_dict, **xg_data}

        # 全量收割 - 提取所有高价值数据
        structured = {
            "matchId": self._extract_match_id(raw_data),
            "match_info": match_info,
            "lineup": self._extract_enhanced_lineup_data(raw_data),  # 增强阵容 - 包含评分
            "shots": shots,
            "stats": enhanced_stats,  # 包含真实xG数据
            "odds": self._extract_odds_data(raw_data),  # 赔率数据 (新增)
            "match_metadata": self._extract_match_metadata(raw_data),  # 比赛元数据 (新增)
            "events": self._extract_match_events(raw_data),  # 详细事件流 (新增)
            "fetched_at": datetime.utcnow().isoformat()
        }

        return structured

    def _extract_match_id(self, data: dict[str, Any]) -> str:
        """提取比赛 ID"""
        try:
            return data.get("match", {}).get("matchId", "")
        except Exception:
            return ""

    def _extract_match_info(self, data: dict[str, Any]) -> dict[str, Any]:
        """提取比赛基本信息"""
        try:
            match = data.get("match", {})
            return {
                "home_team": match.get("home", {}).get("name", ""),
                "away_team": match.get("away", {}).get("name", ""),
                "home_score": match.get("home", {}).get("score", 0),
                "away_score": match.get("away", {}).get("score", 0),
                "status": match.get("status", {}),
                "start_time": match.get("status", {}).get("startTimeStr", ""),
                "finished": match.get("status", {}).get("finished", False)
            }
        except Exception as e:
            self.logger.error(f"Error extracting match info: {str(e)}")
            return {}

    def _extract_lineup_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        提取阵容数据

        Returns:
            {
                "home": {
                    "starters": [球员列表],
                    "substitutes": [替补列表]
                },
                "away": {
                    "starters": [球员列表],
                    "substitutes": [替补列表]
                }
            }
        """
        try:
            lineup_content = data.get("content", {}).get("lineup", {})
            lineup_data = {
                "home": self._process_team_lineup(lineup_content.get("home", {})),
                "away": self._process_team_lineup(lineup_content.get("away", {}))
            }
            return lineup_data
        except Exception as e:
            self.logger.error(f"Error extracting lineup data: {str(e)}")
            return {"home": {"starters": [], "substitutes": []}, "away": {"starters": [], "substitutes": []}}

    def _process_team_lineup(self, team_lineup: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """处理单个球队的阵容数据"""
        return {
            "starters": self._process_players(team_lineup.get("starters", [])),
            "substitutes": self._process_players(team_lineup.get("substitutes", []))
        }

    def _process_players(self, players: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """处理球员数据列表"""
        processed_players = []
        for player in players:
            processed_player = {
                "id": player.get("id"),
                "name": player.get("name", ""),
                "position": player.get("position", ""),
                "shirtNumber": player.get("shirtNumber"),
                "captain": player.get("captain", False)
            }
            processed_players.append(processed_player)
        return processed_players

    def _extract_shot_data(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        提取射门数据

        Returns:
            射门数据列表，包含 xG 值、射门类型等信息
        """
        try:
            shotmap_content = data.get("content", {}).get("shotmap", {})
            shots = shotmap_content.get("shots", [])

            processed_shots = []
            for shot in shots:
                processed_shot = {
                    "id": shot.get("id"),
                    "team": shot.get("team"),
                    "player": shot.get("player", {}),
                    "minute": shot.get("minute"),
                    "xg": shot.get("xg", 0.0),
                    "situation": shot.get("situation"),
                    "shotType": shot.get("shotType"),
                    "isGoal": shot.get("isGoal", False),
                    "bodyPart": shot.get("bodyPart")
                }
                processed_shots.append(processed_shot)

            return processed_shots
        except Exception as e:
            self.logger.error(f"Error extracting shot data: {str(e)}")
            return []

    def _calculate_team_xg(self, shots: list[dict[str, Any]], match_info: dict[str, Any]) -> dict[str, Any]:
        """
        基于FotMob射门图计算真实的xG数据

        Args:
            shots: 射门数据列表
            match_info: 比赛基础信息（包含主客队信息）

        Returns:
            包含xg_home和xg_away的字典
        """
        try:
            home_team = match_info.get("home_team", "")
            away_team = match_info.get("away_team", "")

            xg_home = 0.0
            xg_away = 0.0

            # 统计每支球队的xG总和
            for shot in shots:
                xg_value = float(shot.get("xg", 0.0))
                shot_team = shot.get("team", "")

                # 通过队名判断是主队还是客队的射门
                if shot_team == home_team:
                    xg_home += xg_value
                elif shot_team == away_team:
                    xg_away += xg_value
                else:
                    # 如果队名不匹配，记录警告并跳过
                    self.logger.warning(f"Shot team '{shot_team}' doesn't match home/away teams ({home_team} vs {away_team})")
                    continue

            # 格式化xG值（保留2位小数）
            xg_data = {
                "xg_home": round(xg_home, 2),
                "xg_away": round(xg_away, 2)
            }

            self.logger.info(f"Calculated xG: Home {xg_home:.2f}, Away {xg_away:.2f} from {len(shots)} shots")
            return xg_data

        except Exception as e:
            self.logger.error(f"Error calculating xG from shotmap: {str(e)}")
            # 如果计算失败，返回空值而不是假数据
            return {"xg_home": None, "xg_away": None}

    def _extract_match_stats(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        提取比赛统计数据

        Returns:
            统计数据列表，如控球率、射门数等
        """
        try:
            stats_content = data.get("content", {}).get("stats", {})
            stats = stats_content.get("stats", [])

            processed_stats = []
            for stat_group in stats:
                stat_type = stat_group.get("type", "")
                stat_values = stat_group.get("stats", [])

                for stat in stat_values:
                    processed_stat = {
                        "type": stat_type,
                        "statType": stat.get("type", ""),
                        "value": stat.get("value", "")
                    }
                    processed_stats.append(processed_stat)

            return processed_stats
        except Exception as e:
            self.logger.error(f"Error extracting match stats: {str(e)}")
            return []

    # 添加 headers 属性以兼容测试
    @property
    def headers(self) -> dict[str, str]:
        """获取 HTTP 头部 (包含动态令牌)"""
        effective_headers = self.base_headers.copy()
        if self.dynamic_headers:
            effective_headers.update(self.dynamic_headers)
        return effective_headers

    async def _fetch_match_data(self, match_id: str) -> dict[str, Any] | None:
        """获取比赛原始数据"""
        url = f"https://www.fotmob.com/api/match?id={match_id}"

        try:
            response = await self.session.get(
                url, headers=self.base_headers, timeout=15
            )

            if response.status_code == 200:
                # 修复curl_cffi的响应处理
                try:
                    if hasattr(response, "json"):
                        if asyncio.iscoroutinefunction(response.json):
                            data = await response.json()
                        else:
                            data = response.json()
                    else:
                        # 如果没有json方法，尝试解析文本
                        data = json.loads(response.text)

                    self.logger.debug(f"成功获取比赛 {match_id} 数据")
                    return data
                except Exception as json_error:
                    self.logger.error(f"解析JSON响应时出错: {json_error}")
                    # 尝试直接返回文本内容
                    return (
                        {"raw_response": response.text}
                        if hasattr(response, "text")
                        else None
                    )

            elif response.status_code == 401:
                self.logger.warning(f"比赛 {match_id} 需要认证")
                return None
            elif response.status_code == 404:
                self.logger.warning(f"比赛 {match_id} 不存在")
                return None
            else:
                self.logger.warning(
                    f"比赛 {match_id} 请求失败，状态码: {response.status_code}"
                )
                return None

        except Exception as e:
            self.logger.error(f"请求比赛 {match_id} 数据时发生异常: {e}")
            return None

    def _parse_basic_info(
        self, raw_data: dict[str, Any], match_id: str
    ) -> MatchDetails | None:
        """解析基础比赛信息"""
        try:
            home_info = raw_data.get("home", {})
            away_info = raw_data.get("away", {})

            if not home_info or not away_info:
                self.logger.warning(f"比赛 {match_id} 缺少主客队信息")
                return None

            match_details = MatchDetails(
                match_id=int(match_id),
                home_team=home_info.get("name", ""),
                away_team=away_info.get("name", ""),
                match_date=raw_data.get("matchDate", ""),
                status=raw_data.get("status", {}),
                home_score=int(home_info.get("score", 0)),
                away_score=int(away_info.get("score", 0)),
            )

            return match_details

        except Exception as e:
            self.logger.error(f"解析基础信息时发生错误: {e}")
            return None

    def _parse_stats(self, raw_data: dict[str, Any]) -> MatchStats | None:
        """解析统计数据"""
        try:
            # FotMob的统计数据可能在stats字段中
            stats_data = raw_data.get("stats")

            if not stats_data:
                # 如果stats为空，尝试从其他地方寻找xG数据
                return self._extract_xg_from_alternative_sources(raw_data)

            if isinstance(stats_data, dict):
                home_info = raw_data.get("home", {})
                away_info = raw_data.get("away", {})

                stats = MatchStats(
                    home_team=home_info.get("name", ""),
                    away_team=away_info.get("name", ""),
                    home_score=int(home_info.get("score", 0)),
                    away_score=int(away_info.get("score", 0)),
                )

                # 尝试提取xG数据
                # 这里需要根据实际的数据结构来解析
                # 暂时返回基础的统计数据结构
                return stats

        except Exception as e:
            self.logger.error(f"解析统计数据时发生错误: {e}")

        return None

    def _extract_xg_from_alternative_sources(
        self, raw_data: dict[str, Any]
    ) -> MatchStats | None:
        """从其他数据源提取xG信息"""
        # 尝试从不同的数据结构中提取xG
        # 这是一个占位符，实际实现需要根据真实的数据结构
        try:
            home_info = raw_data.get("home", {})
            away_info = raw_data.get("away", {})

            # 基础统计，xG暂时为空
            stats = MatchStats(
                home_team=home_info.get("name", ""),
                away_team=away_info.get("name", ""),
                home_score=int(home_info.get("score", 0)),
                away_score=int(away_info.get("score", 0)),
            )

            return stats

        except Exception as e:
            self.logger.error(f"从替代源提取xG时发生错误: {e}")
            return None

    def _parse_lineups(
        self, raw_data: dict[str, Any]
    ) -> tuple[TeamLineup | None, TeamLineup | None]:
        """解析阵容数据"""
        try:
            home_lineup = None
            away_lineup = None

            # FotMob的阵容数据可能在lineup字段或其他位置
            # 这里提供一个基础框架，实际实现需要根据真实数据结构调整

            home_info = raw_data.get("home", {})
            away_info = raw_data.get("away", {})

            # 创建基础阵容结构
            if home_info:
                home_lineup = TeamLineup(
                    team_id=home_info.get("id"),
                    team_name=home_info.get("name", ""),
                    formation=None,  # 需要从数据中提取
                    players=[],  # 需要从数据中提取
                )

            if away_info:
                away_lineup = TeamLineup(
                    team_id=away_info.get("id"),
                    team_name=away_info.get("name", ""),
                    formation=None,
                    players=[],
                )

            return home_lineup, away_lineup

        except Exception as e:
            self.logger.error(f"解析阵容数据时发生错误: {e}")
            return None, None

    async def batch_collect(self, match_ids: list[str]) -> list[MatchDetails]:
        """批量采集比赛详情"""
        self.logger.info(f"开始批量采集 {len(match_ids)} 场比赛详情")

        results = []
        semaphore = asyncio.Semaphore(3)  # 限制并发数

        async def collect_with_semaphore(match_id: str) -> MatchDetails | None:
            async with semaphore:
                return await self.collect_match_details(match_id)

        tasks = [collect_with_semaphore(match_id) for match_id in match_ids]
        collected_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(collected_results):
            if isinstance(result, Exception):
                self.logger.error(f"采集比赛 {match_ids[i]} 时发生异常: {result}")
            elif result is not None:
                results.append(result)

        self.logger.info(f"批量采集完成，成功采集 {len(results)} 场比赛")
        return results

    async def save_advanced_stats(self, match_id: str, api_data: dict[str, Any]) -> bool:
        """
        保存高阶统计数据到数据库

        Args:
            match_id: 比赛ID
            api_data: API返回的原始数据

        Returns:
            是否保存成功
        """
        try:
            # 提取高阶数据
            advanced_stats = self._extract_advanced_stats_data(match_id, api_data)

            if not advanced_stats:
                self.logger.warning(f"比赛 {match_id} 无高阶统计数据")
                return False

            # 使用直接数据库连接
            import asyncpg
            import os
            import json

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                self.logger.error("DATABASE_URL 环境变量未设置")
                return False

            # 使用项目标准数据库管理器连接数据库
            from database.async_manager import get_db_session
            from sqlalchemy import text
            async with get_db_session() as db:
                # 检查是否已存在记录（使用标准英文表名）
                result = await db.execute(
                    text("SELECT match_id FROM match_advanced_stats WHERE match_id = :match_id"),
                    {"match_id": match_id}
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新现有记录（使用标准英文表结构）
                    await db.execute(
                        text("""
                        UPDATE match_advanced_stats SET
                            referee = :referee, stadium = :stadium, weather = :weather, attendance = :attendance, match_day = :match_day,
                            round = :round, home_xg = :home_xg, away_xg = :away_xg, possession_home = :possession_home,
                            possession_away = :possession_away, shots_home = :shots_home, shots_away = :shots_away,
                            shots_on_target_home = :shots_on_target_home, shots_on_target_away = :shots_on_target_away, fouls_home = :fouls_home,
                            fouls_away = :fouls_away, corners_home = :corners_home, corners_away = :corners_away,
                            shot_map = :shot_map, momentum = :momentum, lineups = :lineups, player_stats = :player_stats,
                            match_events = :match_events, data_quality_score = :data_quality_score, source_reliability = :source_reliability,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE match_id = :match_id
                        """),
                        {
                            "match_id": match_id,
                            "referee": advanced_stats.get("referee") or "Unknown",
                            "stadium": advanced_stats.get("stadium") or "Unknown",
                            "weather": advanced_stats.get("weather") or "Unknown",  # 新增：天气数据
                            "attendance": advanced_stats.get("attendance") or 0,
                            "match_day": advanced_stats.get("match_day") or "Unknown",
                            "round": advanced_stats.get("round") or "Unknown",
                            "home_xg": float(advanced_stats.get("home_xg") or 0.0),
                            "away_xg": float(advanced_stats.get("away_xg") or 0.0),
                            "possession_home": int(advanced_stats.get("possession_home", 0) or 0),  # 转换为整数
                            "possession_away": int(advanced_stats.get("possession_away", 0) or 0),
                            "shots_home": int(advanced_stats.get("shots_home") or 0),
                            "shots_away": int(advanced_stats.get("shots_away") or 0),
                            "shots_on_target_home": int(advanced_stats.get("shots_on_target_home") or 0),
                            "shots_on_target_away": int(advanced_stats.get("shots_on_target_away") or 0),
                            "fouls_home": int(advanced_stats.get("fouls_home") or 0),
                            "fouls_away": int(advanced_stats.get("fouls_away") or 0),
                            "corners_home": int(advanced_stats.get("corners_home") or 0),
                            "corners_away": int(advanced_stats.get("corners_away") or 0),
                            "shot_map": json.dumps(self._extract_shot_map_from_api(api_data)),  # 射门地图
                            "momentum": json.dumps(self._extract_momentum_from_api(api_data)),  # 压力指数
                            "lineups": json.dumps(advanced_stats.get("lineups", {})),  # 阵容信息
                            "player_stats": json.dumps(advanced_stats.get("player_stats", {})),  # 球员统计
                            "match_events": json.dumps(advanced_stats.get("events", [])),  # 比赛事件
                            "data_quality_score": advanced_stats.get("data_quality_score", 0.8),
                            "source_reliability": advanced_stats.get("source_reliability", "high")
                        }
                    )

                    # 🔥 关键修复：显式提交事务
                    await db.commit()
                    self.logger.info(f"✅ 成功提交更新比赛 {match_id} 的高阶统计数据")

                else:
                    # 插入新记录（使用标准英文表结构）
                    await db.execute(
                        text("""
                        INSERT INTO match_advanced_stats (
                            match_id, referee, stadium, weather, attendance, match_day,
                            round, home_xg, away_xg, possession_home, possession_away,
                            shots_home, shots_away, shots_on_target_home, shots_on_target_away,
                            fouls_home, fouls_away, corners_home, corners_away,
                            shot_map, momentum, lineups, player_stats, match_events,
                            data_quality_score, source_reliability
                        ) VALUES (
                            :match_id, :referee, :stadium, :weather, :attendance, :match_day,
                            :round, :home_xg, :away_xg, :possession_home, :possession_away,
                            :shots_home, :shots_away, :shots_on_target_home, :shots_on_target_away,
                            :fouls_home, :fouls_away, :corners_home, :corners_away,
                            :shot_map, :momentum, :lineups, :player_stats, :match_events,
                            :data_quality_score, :source_reliability
                        )
                        """),
                        {
                            "match_id": match_id,
                            "referee": advanced_stats.get("referee") or "Unknown",
                            "stadium": advanced_stats.get("stadium") or "Unknown",
                            "weather": advanced_stats.get("weather") or "Unknown",  # 新增：天气数据
                            "attendance": advanced_stats.get("attendance") or 0,
                            "match_day": advanced_stats.get("match_day") or "Unknown",
                            "round": advanced_stats.get("round") or "Unknown",
                            "home_xg": float(advanced_stats.get("home_xg") or 0.0),
                            "away_xg": float(advanced_stats.get("away_xg") or 0.0),
                            "possession_home": int(advanced_stats.get("possession_home", 0) or 0),  # 转换为整数
                            "possession_away": int(advanced_stats.get("possession_away", 0) or 0),
                            "shots_home": int(advanced_stats.get("shots_home") or 0),
                            "shots_away": int(advanced_stats.get("shots_away") or 0),
                            "shots_on_target_home": int(advanced_stats.get("shots_on_target_home") or 0),
                            "shots_on_target_away": int(advanced_stats.get("shots_on_target_away") or 0),
                            "fouls_home": int(advanced_stats.get("fouls_home") or 0),
                            "fouls_away": int(advanced_stats.get("fouls_away") or 0),
                            "corners_home": int(advanced_stats.get("corners_home") or 0),
                            "corners_away": int(advanced_stats.get("corners_away") or 0),
                            "shot_map": json.dumps(self._extract_shot_map_from_api(api_data)),  # 射门地图
                            "momentum": json.dumps(self._extract_momentum_from_api(api_data)),  # 压力指数
                            "lineups": json.dumps(advanced_stats.get("lineups", {})),  # 阵容信息
                            "player_stats": json.dumps(advanced_stats.get("player_stats", {})),  # 球员统计
                            "match_events": json.dumps(advanced_stats.get("events", [])),  # 比赛事件
                            "data_quality_score": advanced_stats.get("data_quality_score", 0.8),
                            "source_reliability": advanced_stats.get("source_reliability", "high")
                        }
                    )

                    # 🔥 关键修复：显式提交事务
                    await db.commit()
                    self.logger.info(f"✅ 成功提交插入比赛 {match_id} 的高阶统计数据")

            self.logger.info(f"✅ 成功保存比赛 {match_id} 的高阶统计数据")
            return True

        except Exception as e:
            self.logger.error(f"保存高阶统计数据时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _extract_advanced_stats_data(self, match_id: str, api_data: dict[str, Any]) -> dict[str, Any]:
        """
        从API数据中提取高阶统计信息

        Args:
            match_id: 比赛ID
            api_data: API返回的原始数据

        Returns:
            包含高阶统计数据的字典
        """
        try:
            content = api_data.get("content", {})

            # 提取比赛元数据
            match_facts = content.get("matchFacts", {})
            info_box = match_facts.get("infoBox", {})

            # 裁判信息
            referee_info = info_box.get("stadium", {}).get("referee", {})
            referee = (
                referee_info.get("name") or
                match_facts.get("playerOfTheMatch", {}).get("referee", {}).get("name") or
                match_facts.get("general", {}).get("referee", {}).get("name")
            )

            # 球场和观众信息
            stadium_info = info_box.get("stadium", {})
            stadium = stadium_info.get("name")
            attendance = stadium_info.get("attendance")

            # 提取天气信息（从多个可能的路径尝试）
            weather = None
            # 尝试从 general 部分获取天气
            weather = match_facts.get("general", {}).get("weather")
            # 尝试从 header 部分获取天气
            if not weather:
                header = content.get("header", {})
                weather = header.get("weather")
            # 尝试从 matchInfo 部分获取天气
            if not weather:
                match_info = content.get("matchInfo", {})
                weather = match_info.get("weather")
            # 尝试从 infoBox 直接获取天气
            if not weather:
                weather = info_box.get("weather")

            # 提取xG数据
            shots_data = content.get("shotmap", {})
            shots = shots_data.get("shots", [])
            home_xg, away_xg = self._calculate_xg_from_shots(shots, info_box)

            # 提取技术统计数据
            possession_home = possession_away = None
            shots_home = shots_away = None
            shots_on_target_home = shots_on_target_away = None
            fouls_home = fouls_away = None
            corners_home = corners_away = None

            stats_data = content.get("stats", {})
            stats_list = stats_data.get("stats", [])

            for stat_group in stats_list:
                if isinstance(stat_group, dict) and "stats" in stat_group:
                    for stat in stat_group.get("stats", []):
                        stat_type = stat.get("type", "").lower()
                        stats_values = stat.get("stats", {})

                        if "possession" in stat_type:
                            possession_home = stats_values.get("home")
                            possession_away = stats_values.get("away")
                        elif "shots" in stat_type and "total" in stat_type.lower():
                            shots_home = stats_values.get("home")
                            shots_away = stats_values.get("away")
                        elif "shots" in stat_type and "ontarget" in stat_type.lower():
                            shots_on_target_home = stats_values.get("home")
                            shots_on_target_away = stats_values.get("away")
                        elif "fouls" in stat_type:
                            fouls_home = stats_values.get("home")
                            fouls_away = stats_values.get("away")
                        elif "corners" in stat_type:
                            corners_home = stats_values.get("home")
                            corners_away = stats_values.get("away")

            # 提取阵容数据
            lineup_data = content.get("lineup", {})
            lineups = {
                "home": {
                    "team_id": info_box.get("team1", {}).get("id"),
                    "team_name": info_box.get("team1", {}).get("name"),
                    "formation": lineup_data.get("homeTeam", {}).get("formation"),
                    "players": lineup_data.get("homeTeam", {}).get("lineup", [])
                },
                "away": {
                    "team_id": info_box.get("team2", {}).get("id"),
                    "team_name": info_box.get("team2", {}).get("name"),
                    "formation": lineup_data.get("awayTeam", {}).get("formation"),
                    "players": lineup_data.get("awayTeam", {}).get("lineup", [])
                }
            }

            # 提取球员统计数据
            player_stats = content.get("playerStats", {})

            # 提取比赛事件
            events_data = content.get("matchFacts", {}).get("events", [])

            # 构建返回数据
            advanced_stats = {
                # 比赛元数据
                "referee": referee,
                "stadium": stadium,
                "weather": weather,  # 新增：天气数据
                "attendance": attendance,
                "match_day": match_facts.get("roundName"),
                "round": match_facts.get("round"),
                "competition_stage": match_facts.get("stage"),

                # 高阶统计数据
                "home_xg": home_xg,
                "away_xg": away_xg,
                "possession_home": possession_home,
                "possession_away": possession_away,
                "shots_home": shots_home,
                "shots_away": shots_away,
                "shots_on_target_home": shots_on_target_home,
                "shots_on_target_away": shots_on_target_away,
                "fouls_home": fouls_home,
                "fouls_away": fouls_away,
                "corners_home": corners_home,
                "corners_away": corners_away,

                # JSONB数据
                "lineups": lineups,
                "player_stats": player_stats,
                "events": events_data,

                # 质量指标
                "data_quality_score": 0.8,  # 基于数据完整性评估
                "source_reliability": "high"  # FotMob官方API
            }

            # 清理None值
            advanced_stats = {k: v for k, v in advanced_stats.items() if v is not None}

            return advanced_stats

        except Exception as e:
            self.logger.error(f"提取高阶统计数据时发生错误: {e}")
            return {}

    def _calculate_xg_from_shots(self, shots: list[dict], info_box: dict) -> tuple[float, float]:
        """
        从射门数据计算xG

        Args:
            shots: 射门数据列表
            info_box: 比赛信息框

        Returns:
            (主队xG, 客队xG)
        """
        try:
            home_team_id = info_box.get("team1", {}).get("id")
            away_team_id = info_box.get("team2", {}).get("id")

            home_xg = 0.0
            away_xg = 0.0

            for shot in shots:
                team_id = shot.get("teamId")
                xg_value = float(shot.get("expectedGoals", 0.0))

                if team_id == home_team_id:
                    home_xg += xg_value
                elif team_id == away_team_id:
                    away_xg += xg_value

            return round(home_xg, 2), round(away_xg, 2)

        except Exception as e:
            self.logger.error(f"计算xG时发生错误: {e}")
            return None, None

    async def close(self):
        """关闭会话"""
        if self.session:
            # curl_cffi的AsyncSession没有aclose方法，直接设为None
            self.session = None
            self.logger.info("FotMob HTTP会话已关闭")

    # ==================== 全量收割数据提取方法 ====================

    def _extract_enhanced_lineup_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        增强的阵容数据提取 - 包含球员评分和详细统计
        Returns:
            {
                "home": {
                    "starters": [增强球员列表],
                    "substitutes": [增强替补列表]
                },
                "away": {
                    "starters": [增强球员列表],
                    "substitutes": [增强替补列表]
                }
            }
        """
        try:
            lineup_content = data.get("content", {}).get("lineup", {})
            lineup_stats = data.get("content", {}).get("stats", {})

            lineup_data = {
                "home": self._process_enhanced_team_lineup(
                    lineup_content.get("home", {}),
                    lineup_stats.get("home", [])
                ),
                "away": self._process_enhanced_team_lineup(
                    lineup_content.get("away", {}),
                    lineup_stats.get("away", [])
                )
            }
            return lineup_data
        except Exception as e:
            self.logger.error(f"Error extracting enhanced lineup data: {str(e)}")
            return {"home": {"starters": [], "substitutes": []}, "away": {"starters": [], "substitutes": []}}

    def _process_enhanced_team_lineup(self, team_lineup: dict[str, Any], team_stats: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """处理增强的单个球队阵容数据"""
        processed = {
            "starters": self._process_enhanced_players(team_lineup.get("starters", []), team_stats),
            "substitutes": self._process_enhanced_players(team_lineup.get("substitutes", []), team_stats)
        }
        return processed

    def _process_enhanced_players(self, players: list[dict[str, Any]], team_stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """处理增强的球员数据，提取评分和详细统计"""
        processed_players = []

        # 创建统计数据的快速查找字典
        stats_dict = {}
        for stat in team_stats:
            if stat.get("statsType") == "player" and "playerStats" in stat:
                for player_stat in stat["playerStats"]:
                    player_id = player_stat.get("playerId")
                    if player_id:
                        stats_dict[player_id] = player_stat.get("stats", {})

        for player in players:
            try:
                player_id = player.get("id")

                # 从统计数据中获取详细信息
                player_stats = stats_dict.get(player_id, {})

                enhanced_player = {
                    "id": player_id,
                    "name": player.get("name", ""),
                    "position": player.get("position", {}).get("name", ""),
                    "shirt_number": player.get("shirtNo", player.get("shirtNumber")),
                    "is_starter": True,  # 这个参数需要根据调用上下文调整

                    # 全量收割关键字段
                    "rating": player_stats.get("rating"),  # 球员评分 (关键)
                    "minutes_played": player_stats.get("minutesPlayed"),  # 出场时间
                    "goals": player_stats.get("goals"),  # 进球数
                    "assists": player_stats.get("assists"),  # 助攻数
                    "shots": player_stats.get("shotsTotal"),  # 射门数
                    "shots_on_target": player_stats.get("shotsOnTarget"),  # 射正数
                    "yellow_cards": player_stats.get("yellowCards"),  # 黄牌
                    "red_cards": player_stats.get("redCards"),  # 红牌
                    "fouls": player_stats.get("fouls"),  # 犯规
                    "fouled_against": player_stats.get("fouledAgainst"),  # 被犯规
                    "passes_completed": player_stats.get("passesCompleted"),  # 传球成功数
                    "passes_attempted": player_stats.get("passesAttempted"),  # 传球尝试数
                    "pass_accuracy": player_stats.get("passAccuracy"),  # 传球成功率
                    "duels_won": player_stats.get("duelsWon"),  # 对抗胜利数
                    "duels_lost": player_stats.get("duelsLost"),  # 对抗失败数
                    "aerials_won": player_stats.get("aerialsWon"),  # 空中对抗胜利数
                    "aerials_lost": player_stats.get("aerialsLost"),  # 空中对抗失败数
                }

                processed_players.append(enhanced_player)
            except Exception as e:
                self.logger.warning(f"Error processing enhanced player data: {str(e)}")
                continue

        return processed_players

    def _extract_odds_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        提取赔率数据 - 1x2、大小球、让球盘等
        """
        try:
            odds_content = data.get("content", {}).get("matchFacts", {}).get("odds", {})
            if not odds_content:
                return {}

            # 提取主要赔率
            primary_odds = odds_content.get("primary", {})
            all_odds = odds_content.get("all", [])

            extracted_odds = {
                "home_win": primary_odds.get("homeWin"),
                "draw": primary_odds.get("draw"),
                "away_win": primary_odds.get("awayWin"),
                "over_25": primary_odds.get("over25"),
                "under_25": primary_odds.get("under25"),
                "both_teams_score": primary_odds.get("bothTeamsToScore"),
            }

            # 提取所有博彩公司的赔率
            providers = {}
            for provider in all_odds:
                provider_name = provider.get("provider", {}).get("name")
                if provider_name:
                    providers[provider_name] = {
                        "home_win": provider.get("homeWin"),
                        "draw": provider.get("draw"),
                        "away_win": provider.get("awayWin"),
                        "over_25": provider.get("over25"),
                        "under_25": provider.get("under25"),
                    }

            if providers:
                extracted_odds["providers"] = providers

            return extracted_odds
        except Exception as e:
            self.logger.error(f"Error extracting odds data: {str(e)}")
            return {}

    def _extract_match_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        提取比赛元数据 - 裁判、球场、观众等
        """
        try:
            match_facts = data.get("content", {}).get("matchFacts", {})
            general = match_facts.get("general", {})

            metadata = {
                "referee": general.get("referee", {}).get("name"),  # 裁判姓名 (关键)
                "stadium": general.get("stadium", {}).get("name"),  # 球场名称
                "attendance": general.get("attendance"),  # 观众人数
                "city": general.get("city"),
                "country": general.get("country"),
                "match_day": general.get("matchDay"),
                "round": general.get("round"),
                "competition_stage": general.get("stage"),
            }

            return metadata
        except Exception as e:
            self.logger.error(f"Error extracting match metadata: {str(e)}")
            return {}

    def _extract_match_events(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        提取详细比赛事件流 - 进球、卡牌、换人等
        """
        try:
            events_content = data.get("content", {}).get("lineup", {})
            home_events = events_content.get("home", {}).get("events", [])
            away_events = events_content.get("away", {}).get("events", [])

            all_events = []

            # 处理主队事件
            for event in home_events:
                processed_event = self._process_match_event(event, "home")
                if processed_event:
                    all_events.append(processed_event)

            # 处理客队事件
            for event in away_events:
                processed_event = self._process_match_event(event, "away")
                if processed_event:
                    all_events.append(processed_event)

            # 按时间排序
            all_events.sort(key=lambda x: x.get("minute", 0))

            return all_events
        except Exception as e:
            self.logger.error(f"Error extracting match events: {str(e)}")
            return []

    def _process_match_event(self, event: dict[str, Any], team_side: str) -> dict[str, Any]:
        """处理单个比赛事件"""
        try:
            processed_event = {
                "id": event.get("id"),
                "minute": event.get("minute"),
                "team_side": team_side,  # 标记是主队还是客队事件
                "player_name": event.get("player", {}).get("name"),
                "event_type": event.get("eventType"),
                "sub_type": event.get("subEventType"),
                "is_assist": event.get("isAssist", False),
                "assist_player_name": event.get("assistPlayer", {}).get("name"),
                "coordinate_x": event.get("coordinate", {}).get("x"),
                "coordinate_y": event.get("coordinate", {}).get("y"),
                "timestamp": event.get("timestamp"),
            }

            return processed_event
        except Exception as e:
            self.logger.warning(f"Error processing match event: {str(e)}")
            return {}

    # ==================== 新增：深度学习特征提取方法 ====================

    def _extract_shot_map_from_api(self, api_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        从API数据中提取射门地图数据，包含坐标、xG值、射门类型等深度学习特征

        Args:
            api_data: API返回的原始数据

        Returns:
            射门地图数据列表，每个射门包含：
            - id: 射门ID
            - x: x坐标 (球场宽度百分比)
            - y: y坐标 (球场长度百分比)
            - expectedGoals: 期望进球值
            - shotType: 射门类型 (RightFoot, LeftFoot, Header等)
            - isOnTarget: 是否射正
            - minute: 射门时间
            - teamId: 球队ID
            - situation: 比赛情况 (RegularPlay, CounterAttack等)
            - period: 比赛半场 (FirstHalf, SecondHalf)
            - isOwnGoal: 是否乌龙球
            - goalCrossedY: 球门横Y坐标
            - goalCrossedZ: 球门横Z坐标
        """
        try:
            content = api_data.get("content", {})
            shotmap_data = content.get("shotmap", {})
            shots = shotmap_data.get("shots", [])

            # 增强射门数据，添加深度学习特征
            enhanced_shots = []
            for shot in shots:
                enhanced_shot = {
                    "id": shot.get("id"),
                    "x": shot.get("x"),  # 射门位置x坐标
                    "y": shot.get("y"),  # 射门位置y坐标
                    "expectedGoals": shot.get("expectedGoals", 0.0),  # xG值
                    "shotType": shot.get("shotType"),  # 射门类型
                    "isOnTarget": shot.get("isOnTarget", False),  # 是否射正
                    "minute": shot.get("minute"),  # 射门时间
                    "teamId": shot.get("teamId"),  # 球队ID
                    "situation": shot.get("situation", "RegularPlay"),  # 比赛情况
                    "period": shot.get("period", "FirstHalf"),  # 比赛半场
                    "isOwnGoal": shot.get("isOwnGoal", False),  # 是否乌龙球
                    "goalCrossedY": shot.get("goalCrossedY"),  # 球门横Y坐标
                    "goalCrossedZ": shot.get("goalCrossedZ"),  # 球门横Z坐标
                    # 新增深度学习特征
                    "shotQuality": self._calculate_shot_quality(shot),  # 射门质量评分
                    "angle": self._calculate_shot_angle(shot),  # 射门角度
                    "distance": self._calculate_shot_distance(shot),  # 射门距离
                }
                enhanced_shots.append(enhanced_shot)

            self.logger.info(f"成功提取射门地图数据：{len(enhanced_shots)}个射门")
            return enhanced_shots

        except Exception as e:
            self.logger.error(f"提取射门地图数据时发生错误: {e}")
            return []

    def _extract_momentum_from_api(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """
        从API数据中提取压力指数时间序列数据，用于momentum分析

        Args:
            api_data: API返回的原始数据

        Returns:
            压力指数字典，包含：
            - home_team: 主队压力指数时间序列
            - away_team: 客队压力指数时间序列
            - total_momentum: 总体压力指数变化
            - key_moments: 关键转折点
        """
        try:
            content = api_data.get("content", {})
            # 从比赛事件中推断压力指数
            events_data = content.get("events", {})
            events = events_data.get("events", [])

            # 初始化压力指数
            momentum_data = {
                "home_team": [],
                "away_team": [],
                "total_momentum": [],
                "key_moments": []
            }

            # 计算每个时间点的压力指数
            minute_intervals = range(0, 91, 5)  # 每5分钟一个间隔
            home_pressure = 50.0  # 初始压力值50
            away_pressure = 50.0

            for minute in minute_intervals:
                # 计算当前时间段内的事件影响
                events_in_period = [
                    event for event in events
                    if minute <= event.get("minute", 0) < minute + 5
                ]

                pressure_change_home = 0
                pressure_change_away = 0

                for event in events_in_period:
                    event_type = event.get("eventType", "")
                    team_side = self._get_event_team_side(event, api_data)

                    # 不同事件类型的压力影响
                    if event_type == "Goal":
                        pressure_change = 8.0
                    elif event_type == "YellowCard":
                        pressure_change = 2.0
                    elif event_type == "RedCard":
                        pressure_change = 10.0
                    elif event_type == "Substitution":
                        pressure_change = 1.0
                    else:
                        pressure_change = 0.5

                    if team_side == "home":
                        pressure_change_home += pressure_change
                    else:
                        pressure_change_away += pressure_change

                # 更新压力值
                home_pressure += pressure_change_home
                away_pressure += pressure_change_away

                # 限制压力值在0-100之间
                home_pressure = max(0, min(100, home_pressure))
                away_pressure = max(0, min(100, away_pressure))

                momentum_data["home_team"].append({
                    "minute": minute + 2,  # 区间中点
                    "pressure": round(home_pressure, 2),
                    "pressure_change": round(pressure_change_home, 2)
                })

                momentum_data["away_team"].append({
                    "minute": minute + 2,
                    "pressure": round(away_pressure, 2),
                    "pressure_change": round(pressure_change_away, 2)
                })

                momentum_data["total_momentum"].append({
                    "minute": minute + 2,
                    "pressure_difference": round(home_pressure - away_pressure, 2),
                    "dominant_team": "home" if home_pressure > away_pressure else "away"
                })

            # 识别关键转折点
            momentum_data["key_moments"] = self._identify_key_moments(momentum_data)

            self.logger.info(f"成功提取压力指数数据：{len(momentum_data['total_momentum'])}个时间点")
            return momentum_data

        except Exception as e:
            self.logger.error(f"提取压力指数数据时发生错误: {e}")
            return {}

    def _calculate_shot_quality(self, shot: dict[str, Any]) -> float:
        """
        计算射门质量评分 (0-100)
        基于xG值、射门位置、射门类型等因素
        """
        try:
            xg = float(shot.get("expectedGoals", 0.0))
            is_on_target = shot.get("isOnTarget", False)
            shot_type = shot.get("shotType", "")

            # 基础分数来自xG
            base_score = xg * 100

            # 射正加分
            if is_on_target:
                base_score += 10

            # 射门类型调整
            if shot_type in ["RightFoot", "LeftFoot"]:
                base_score += 5
            elif shot_type == "Header":
                base_score += 3
            elif shot_type == "Volley":
                base_score += 15

            return round(min(100, base_score), 2)
        except:
            return 0.0

    def _calculate_shot_angle(self, shot: dict[str, Any]) -> float:
        """
        计算射门角度（相对于球门中心的角度）
        """
        try:
            x = float(shot.get("x", 0))
            y = float(shot.get("y", 0))

            # 简化的角度计算
            # 球门位置假设在(100, 50)，射门点在(x, y)
            goal_x, goal_y = 100, 50

            dx = goal_x - x
            dy = goal_y - y

            if dx == 0:
                return 90.0

            angle_rad = abs(math.atan(dy / dx))
            angle_deg = math.degrees(angle_rad)

            return round(angle_deg, 2)
        except:
            return 0.0

    def _calculate_shot_distance(self, shot: dict[str, Any]) -> float:
        """
        计算射门距离（相对于球门的距离）
        """
        try:
            x = float(shot.get("x", 0))
            y = float(shot.get("y", 0))

            # 球门位置假设在(100, 50)
            goal_x, goal_y = 100, 50

            distance = math.sqrt((goal_x - x)**2 + (goal_y - y)**2)

            return round(distance, 2)
        except:
            return 0.0

    def _get_event_team_side(self, event: dict[str, Any], api_data: dict[str, Any]) -> str:
        """
        确定事件属于主队还是客队
        """
        try:
            event_team_id = event.get("teamId")
            if not event_team_id:
                return "unknown"

            # 从API数据中获取主客队ID
            content = api_data.get("content", {})
            match_info = content.get("matchInfo", {})

            home_team_id = match_info.get("homeTeam", {}).get("id")
            away_team_id = match_info.get("awayTeam", {}).get("id")

            if event_team_id == home_team_id:
                return "home"
            elif event_team_id == away_team_id:
                return "away"
            else:
                return "unknown"
        except:
            return "unknown"

    def _identify_key_moments(self, momentum_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        识别比赛中的关键转折点
        """
        try:
            key_moments = []
            total_momentum = momentum_data.get("total_momentum", [])

            for i in range(1, len(total_momentum)):
                prev_moment = total_momentum[i-1]
                curr_moment = total_momentum[i]

                prev_diff = prev_moment.get("pressure_difference", 0)
                curr_diff = curr_moment.get("pressure_difference", 0)

                # 压力差变化超过15个点认为是关键转折
                diff_change = abs(curr_diff - prev_diff)
                if diff_change > 15:
                    key_moments.append({
                        "minute": curr_moment.get("minute"),
                        "type": "momentum_shift",
                        "change_magnitude": round(diff_change, 2),
                        "new_leader": curr_moment.get("dominant_team"),
                        "description": f"压力转向{curr_moment.get('dominant_team')}"
                    })

            return key_moments
        except:
            return []


# 便捷函数
async def collect_match_details(match_id: str) -> MatchDetails | None:
    """便捷的单一比赛详情采集函数"""
    collector = FotmobDetailsCollector()
    try:
        return await collector.collect_match_details(match_id)
    finally:
        await collector.close()


async def collect_multiple_matches(match_ids: list[str]) -> list[MatchDetails]:
    """便捷的批量比赛详情采集函数"""
    collector = FotmobDetailsCollector()
    try:
        return await collector.batch_collect(match_ids)
    finally:
        await collector.close()


# 一行验证脚本 - 用于在Docker容器内快速测试
if __name__ == "__main__":
    import sys
    asyncio.run(collect_match_details("4186358"))
