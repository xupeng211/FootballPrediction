"""
Titan Web 收集器 - 基于 Playwright
使用浏览器自动化绕过 HTTP API 的 TLS 指纹拦截
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup

from src.collectors.rate_limiter import RateLimiter
from src.collectors.user_agent import UserAgentManager
from src.schemas.titan import EuroOddsRecord

logger = __import__('logging').getLogger(__name__)


class TitanWebCollector:
    """
    Titan Web 收集器 - 基于 Playwright

    使用浏览器自动化绕过 HTTP API 的 TLS 指纹拦截，
    直接从 NowGoal 页面提取赔率数据。
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None, user_agent_manager: Optional[UserAgentManager] = None):
        self.rate_limiter = rate_limiter or RateLimiter(config={"default": {"rate": 0.5, "burst": 1}})
        self.user_agent_manager = user_agent_manager or UserAgentManager()

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._browser_started = False

        # 网络拦截相关属性
        self.captured_payloads = []
        self._response_listener_enabled = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_browser()

    async def start_browser(self):
        """启动浏览器实例"""
        if self._browser_started:
            return

        try:
            logger.info("🚀 启动 Playwright 浏览器 (代理: 172.25.16.1:7890)...")

            self.playwright = await async_playwright().start()

            # 启动 Chromium，配置生产环境参数 + 代理
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                proxy={"server": "http://172.25.16.1:7890"},  # WSL2 强制代理
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--enable-features=NetworkService',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-web-security',  # 允许跨域请求
                    '--disable-features=VizDisplayCompositor',
                    '--ignore-certificate-errors',  # 防止 SSL 报错阻断连接
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors-spki-list'
                ]
            )

            # 检查 Cookie 文件是否存在
            cookie_file = Path("data/nowgoal_auth.json")
            storage_state = None

            if cookie_file.exists():
                try:
                    import json
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        storage_state = json.load(f)

                    cookies = storage_state.get('cookies', [])
                    cookies_count = len(cookies)

                    logger.info("✅ Loaded Trusted Cookie - 身份伪装模式")
                    logger.info(f"📊 加载了 {cookies_count} 个 Cookie")

                    # 显示重要Cookie用于验证
                    important_cookies = []
                    for cookie in cookies:
                        name = cookie.get('name', '').lower()
                        if any(key in name for key in ['session', 'token', 'auth', 'user', 'id']):
                            important_cookies.append(cookie.get('name'))

                    if important_cookies:
                        logger.info(f"🎯 身份验证Cookie: {', '.join(important_cookies)}")
                        logger.info("🔥 预期效果: 真实赔率数据 (非10.0/11.0/13.0)")
                    else:
                        logger.warning("⚠️ 未发现明显身份Cookie，但已加载完整状态")

                except Exception as e:
                    logger.error(f"❌ Cookie加载失败: {str(e)}")
                    logger.warning("⚠️ No Cookie Found, running in Guest Mode")
                    logger.warning("🔄 将以普通模式继续运行")
                    storage_state = None
            else:
                logger.warning("⚠️ No Cookie Found, running in Guest Mode")
                logger.warning("💡 请运行: python scripts/generate_nowgoal_cookie.py")
                logger.warning("⚠️ 预期问题: 可能获得假赔率 10.0/11.0/13.0")
                storage_state = None

            # 创建浏览器上下文 (继承代理配置 + Cookie)
            context_config = {
                "user_agent": self.user_agent_manager.get_random_user_agent(),
                "viewport": {'width': 1920, 'height': 1080},
                "locale": 'en-US',
                "ignore_https_errors": True,  # 忽略 HTTPS 错误
                "accept_downloads": False,
                "java_script_enabled": True,
                "proxy": {"server": "http://172.25.16.1:7890"}  # 确保上下文也使用代理
            }

            # 如果有 Cookie 文件，添加到上下文配置
            if storage_state:
                context_config["storage_state"] = storage_state

            self.context = await self.browser.new_context(**context_config)

            # 创建页面
            self.page = await self.context.new_page()

            # 注入反检测脚本
            await self.page.add_init_script("""
                // 绕过 Playwright 检测
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 伪装插件
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // 伪装语言
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                // 伪装 Chrome
                Object.defineProperty(window, 'chrome', {
                    get: () => {
                    return {
                        runtime: {},
                    };
                    },
                });
            """)

            self._browser_started = True
            logger.info("✅ Playwright 浏览器启动成功")

        except Exception as e:
            logger.error(f"❌ 浏览器启动失败: {str(e)}")
            raise

    async def close_browser(self):
        """关闭浏览器实例"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()

            self._browser_started = False
            logger.info("✅ 浏览器关闭成功")

        except Exception as e:
            logger.warning(f"⚠️ 浏览器关闭时出现错误: {str(e)}")

    async def fetch_odds_batch(
        self,
        matches: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        批量获取赔率数据 - 日期扫荡模式

        Args:
            matches: 比赛信息列表，每项包含 id, home_team, away_team, match_date
            max_concurrent: 最大并发数

        Returns:
            List[Dict[str, Any]]: 赔率数据列表
        """
        if not matches:
            return []

        print(f"🗓️ 开始日期扫荡模式采集 {len(matches)} 场比赛的赔率数据")
        logger.info(f"🗓️ 开始日期扫荡模式采集 {len(matches)} 场比赛的赔率数据")

        results = []

        try:
            # 确保浏览器已启动
            if not self._browser_started:
                await self.start_browser()

            # Step 1: 按日期分组比赛
            print("🔍 DEBUG: 开始按日期分组...")
            matches_by_date = self._group_matches_by_date(matches)
            print(f"📅 按日期分组完成，共 {len(matches_by_date)} 个日期")
            logger.info(f"📅 按日期分组完成，共 {len(matches_by_date)} 个日期")

            # Step 2: 对每个日期进行扫荡
            for date_str, date_matches in matches_by_date.items():
                print(f"📆 扫荡日期: {date_str}, 比赛: {len(date_matches)} 场")
                logger.info(f"📆 扫荡日期: {date_str}, 比赛: {len(date_matches)} 场")

                try:
                    # 获取该日期的所有赔率数据
                    print(f"🔍 DEBUG: 调用 _sweep_date_page: {date_str}")
                    page_odds = await self._sweep_date_page(date_str, date_matches)
                    print(f"🔍 DEBUG: _sweep_date_page 返回: {len(page_odds)} 条数据")

                    # Step 3: 模糊匹配赔率数据
                    matched_odds = self._fuzzy_match_odds(date_matches, page_odds)

                    # 合并结果
                    for match_id, odds_data in matched_odds.items():
                        original_match = next(m for m in date_matches if str(m['id']) == match_id)
                        odds_data.update({
                            'match_id': original_match['id'],
                            'home_team': original_match['home_team'],
                            'away_team': original_match['away_team']
                        })
                        results.append(odds_data)

                    logger.info(f"✅ 日期 {date_str} 完成，匹配 {len(matched_odds)} 场比赛")

                except Exception as e:
                    logger.error(f"❌ 日期 {date_str} 扫荡失败: {str(e)}")
                    continue

                # 日期间休息，避免过于频繁的请求
                if list(matches_by_date.keys()).index(date_str) < len(matches_by_date) - 1:
                    logger.debug("⏸️ 日期间休息 3 秒...")
                    await asyncio.sleep(3)

            logger.info(f"🎉 日期扫荡完成，成功获取 {len(results)} 场比赛的赔率数据")
            return results

        except Exception as e:
            logger.error(f"❌ 日期扫荡失败: {str(e)}")
            return results

    async def _fetch_single_match_odds(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        获取单场比赛的赔率数据

        Args:
            match: 比赛信息，包含 id, home_team, away_team, match_date

        Returns:
            Optional[Dict[str, Any]]: 赔率数据
        """
        try:
            # 限流保护
            async with self.rate_limiter.acquire("nowgoal_web"):
                return await self._extract_odds_from_nowgoal(match)

        except Exception as e:
            logger.error(f"比赛 {match['id']} 赔率获取失败: {str(e)}")
            return None

    async def _extract_odds_from_nowgoal(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 NowGoal 页面提取赔率数据"""
        try:
            home_team = match['home_team']
            away_team = match['away_team']
            match_date = match['match_date']

            logger.debug(f"从 NowGoal 提取赔率: {home_team} vs {away_team}")

            # 策待页面加载
            await self.page.wait_for_load_state("networkidle")

            # 策待页面完全加载
            await asyncio.sleep(2)

            # 尝试多种方法找到比赛
            odds_data = await self._find_match_and_extract_odds(home_team, away_team, match_date)

            if odds_data:
                logger.debug(f"成功提取赔率数据: {odds_data}")
                return odds_data
            else:
                logger.warning(f"未能找到比赛 {home_team} vs {away_team} 的赔率数据")
                return None

        except Exception as e:
            logger.error(f"NowGoal 赔率提取失败: {str(e)}")
            return None

    async def _find_match_and_extract_odds(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """在 NowGoal 页面中查找比赛并提取赔率"""
        try:
            # 方法1: 直接从当前页面查找
            odds_data = await self._extract_odds_from_current_page(home_team, away_team)
            if odds_data:
                return odds_data

            # 方法2: 访问今日/昨日比赛页面
            odds_data = await self._extract_odds_from_schedule_pages(home_team, away_team, match_date)
            if odds_data:
                return odds_data

            # 方法3: 搜索特定比赛
            odds_data = await self._extract_odds_from_search(home_team, away_team)
            if odds_data:
                return odds_data

            logger.debug("所有方法都未能找到赔率数据")
            return None

        except Exception as e:
            logger.error(f"查找和提取赔率失败: {str(e)}")
            return None

    async def _extract_odds_from_current_page(self, home_team: str, away_team: str) -> Optional[Dict[str, Any]]:
        """从当前页面提取赔率数据"""
        try:
            # 获取页面内容
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 查找包含队名的元素
            team_variants = self._get_team_variants(home_team, away_team)

            # 搜索赔率表格
            odds_selectors = [
                'table.odds',
                '.odds-table',
                '[data-odds]',
                '.betting-odds',
                '.euro-odds',
                '.match-odds'
            ]

            for selector in odds_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        for i in range(count):
                            element = elements.nth(i)
                            text = await element.inner_text()

                            if self._contains_both_teams(text, team_variants):
                                # 从表格行中提取赔率
                                odds_data = self._extract_odds_from_table_row(text)
                                if odds_data:
                                    return odds_data
                except:
                    continue

            # JavaScript 提取
            try:
                odds_data = await self.page.evaluate("""
                    (homeTeam, awayTeam) => {
                        // 查找所有包含队名的文本节点
                        const allText = document.body.innerText.toLowerCase();
                        const homeVariants = ['manchester united', 'man utd', 'manchester utd'];
                        const awayVariants = ['fulham', 'fulham fc'];

                        // 查找数字模式（赔率）
                        const oddsRegex = /\\b(\\d+\\.?\\d+)\\s+(\\d+\\.?\\d*)\\s+(\\d+\\.?\\d*)\\b/g;
                        const matches = allText.match(oddsRegex);

                        if (matches && matches.length > 0) {
                            return {
                                home_win: parseFloat(matches[0]),
                                draw: parseFloat(matches[1]),
                                away_win: parseFloat(matches[2]),
                                source: 'nowgoal_js'
                            };
                        }

                        return null;
                    }
                """, home_team.lower(), away_team.lower())

                if odds_data:
                    logger.debug(f"JavaScript 提取成功: {odds_data}")
                    return odds_data

            except:
                pass

            return None

        except Exception as e:
            logger.error(f"当前页面赔率提取失败: {str(e)}")
            return None

    async def _extract_odds_from_schedule_pages(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """从赛程页面提取赔率数据"""
        schedule_urls = [
            "https://www.nowgoal.com/",
            "https://www.nowgoal.com/football/",
            "https://www.nowgoal.com/nba/",
            "https://www.nowgoal.com/tennis/"
        ]

        for url in schedule_urls:
            try:
                logger.debug(f"访问赛程页面: {url}")
                await self.page.goto(url, timeout=30000)
                await self.page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                odds_data = await self._extract_odds_from_current_page(home_team, away_team)
                if odds_data:
                    return odds_data

            except Exception as e:
                logger.warning(f"赛程页面 {url} 访问失败: {str(e)}")
                continue

        return None

    async def _extract_odds_from_search(self, home_team: str, away_team: str) -> Optional[Dict[str, Any]]:
        """通过搜索提取赔率数据"""
        try:
            # 构造搜索查询
            search_query = f"{home_team} {away_team} odds"
            encoded_query = search_query.replace(" ", "+")

            # 尝试搜索
            search_url = f"https://www.nowgoal.com/search?q={encoded_query}"

            logger.debug(f"搜索 URL: {search_url}")
            await self.page.goto(search_url, timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            return await self._extract_odds_from_current_page(home_team, away_team)

        except Exception as e:
            logger.warning(f"搜索失败: {str(e)}")
            return None

    def _extract_odds_from_table_row(self, text: str) -> Optional[Dict[str, Any]]:
        """从表格行文本中提取赔率"""
        try:
            # 匹配三个数字（主胜、平局、客胜）
            odds_pattern = r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)'
            matches = re.findall(odds_pattern, text)

            if len(matches) >= 3:
                home_win, draw, away_win = matches[0]

                # 验证赔率值是否合理（通常在 1.01 - 50.0 之间）
                try:
                    home_val = float(home_win)
                    draw_val = float(draw)
                    away_val = float(away_win)

                    if (1.0 <= home_val <= 50.0 and
                        1.0 <= draw_val <= 50.0 and
                        1.0 <= away_val <= 50.0):
                        return {
                            'home_win': home_val,
                            'draw': draw_val,
                            'away_win': away_val,
                            'company_name': 'NowGoal'
                        }
                except ValueError:
                    pass

            return None

        except Exception as e:
            logger.error(f"表格行赔率解析失败: {str(e)}")
            return None

    def _get_team_variants(self, home_team: str, away_team: str) -> List[str]:
        """获取队名的各种变体"""
        # 主队变体
        home_variants = [
            home_team.lower(),
        ]

        # 客队变体
        away_variants = [
            away_team.lower(),
        ]

        # 添加常见的队名缩写和变体
        team_mappings = {
            'manchester united': ['man utd', 'manunited', 'manchester utd'],
            'manchester city': ['man city', 'mancity'],
            'liverpool': ['lfc', 'liverpool fc'],
            'chelsea': ['chelsea fc', 'cfc'],
            'arsenal': ['arsenal fc', 'afc'],
            'tottenham': ['tottenham', 'spurs', 'tottenham hotspur'],
            'west ham': ['west ham', 'westham united', 'whufc'],
            'newcastle': ['newcastle', 'newcastle utd', 'newcastle united'],
            'wolverhampton': ['wolves', 'wolverhampton wanderers'],
            'nottingham forest': ['nottingham forest', 'nottingham', 'nottm forest'],
            'brighton': ['brighton', 'brighton hove', 'brighton & hove albion'],
            'crystal palace': ['crystal palace', 'pal', 'cpfc'],
            'brentford': ['brentford', 'the brentford', 'brentford fc'],
            'fulham': ['fulham', 'the fulham', 'fulham fc'],
            'leicester': ['leicester', 'leicester city', 'the foxes', 'lcfc'],
            'aston villa': ['aston villa', 'villa', 'avfc'],
            'southampton': ['southampton', 'saints', 'southampton fc'],
            'west bromwich': ['west brom', 'west bromwich albion', 'wba'],
            'everton': ['everton', 'the toffees', 'efc'],
            'leeds': ['leeds', 'leeds united', 'lufc'],
            'sheffield': ['sheffield', 'sheffield united', 'sufc'],
            'burnley': ['burnley', 'the clarets', 'bfc'],
            'norwich': ['norwich', 'norwich city', 'ncfc'],
            'watford': ['watford', 'the hornets', 'wfc'],
            'bournemouth': ['bournemouth', 'the cherries', 'afc bournemouth'],
        }

        # 查找匹配并添加变体
        for full_name, variants in team_mappings.items():
            if full_name.lower() in home_team.lower() or home_team.lower() in full_name.lower():
                home_variants.extend(variants)
            if full_name.lower() in away_team.lower() or away_team.lower() in full_name.lower():
                away_variants.extend(variants)

        return [v.lower() for v in home_variants + away_variants]

    def _contains_both_teams(self, text: str, team_variants: List[str]) -> bool:
        """检查文本是否包含两个队名"""
        text_lower = text.lower()

        has_home = any(variant in text_lower for variant in team_variants[:len(team_variants)//2])
        has_away = any(variant in text_lower for variant in team_variants[len(team_variants)//2:])

        return has_home and has_away

    async def close(self):
        """关闭收集器"""
        await self.close_browser()

    # === Date-Sweep Mode Helper Methods ===

    def _group_matches_by_date(self, matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按日期分组比赛

        Args:
            matches: 比赛列表

        Returns:
            Dict[str, List[Dict]]: 日期 -> 比赛列表的映射
        """
        from collections import defaultdict

        grouped = defaultdict(list)

        for match in matches:
            # 提取日期部分 (YYYY-MM-DD)
            match_date = match['match_date']
            if isinstance(match_date, str):
                date_str = match_date.split(' ')[0]  # 取日期部分
            else:
                date_str = match_date.strftime('%Y-%m-%d')

            grouped[date_str].append(match)

        return dict(grouped)

    async def _sweep_date_page(self, date_str: str, date_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        扫荡特定日期的页面，使用网络拦截提取所有赔率数据

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            date_matches: 该日期的比赛列表

        Returns:
            List[Dict]: 该日期页面的所有赔率数据
        """
        try:
            print(f"🌐 访问日期页面: {date_str} (网络拦截模式)")
            logger.info(f"🌐 访问日期页面: {date_str}")

            # 清空之前捕获的数据
            self.captured_payloads = []

            # 设置网络拦截监听器
            if not self._response_listener_enabled:
                self.page.on("response", self._handle_response)
                self._response_listener_enabled = True
                print("🔧 已启用网络响应监听器")

            # 构建赛程页面URL
            schedule_url = f"https://www.nowgoal.com/football/schedule/{date_str}"

            # 尝试访问赛程页面
            try:
                print(f"📍 正在访问: {schedule_url}")
                await self.page.goto(schedule_url, timeout=30000)
                await self.page.wait_for_load_state("networkidle")
                logger.info(f"✅ 赛程页面加载成功: {schedule_url}")
                print("✅ 页面加载完成，等待网络请求...")
            except Exception as e:
                logger.warning(f"⚠️ 赛程页面访问失败，回退到主页: {str(e)}")
                print(f"⚠️ 赛程页面失败，回退到主页: {str(e)}")
                # 回退到主页，然后通过JavaScript选择日期
                await self.page.goto("https://www.nowgoal.com/football/", timeout=30000)
                await self.page.wait_for_load_state("networkidle")

                # 尝试通过JavaScript选择日期
                await self._select_date_in_calendar(date_str)
                print("✅ 主页加载完成，等待网络请求...")

            # 等待额外的网络请求完成
            await asyncio.sleep(5)

            print(f"📊 捕获到 {len(self.captured_payloads)} 个网络响应")

            # 从网络响应中提取赔率数据
            page_odds = self._extract_odds_from_payloads()

            logger.info(f"📊 网络拦截完成，找到 {len(page_odds)} 场比赛数据")
            print(f"📊 成功提取 {len(page_odds)} 场赔率数据")
            return page_odds

        except Exception as e:
            logger.error(f"❌ 日期页面扫荡失败 {date_str}: {str(e)}")
            print(f"❌ 扫荡失败: {str(e)}")
            return []

    async def _handle_response(self, response):
        """处理网络响应"""
        try:
            url = response.url.lower()
            content_type = response.headers.get('content-type', '').lower()

            # 检查URL和Content-Type是否包含赔率相关关键词
            odds_keywords = ['odds', '1x2', 'euro', 'bet', 'data', 'xml', 'json']
            contains_keywords = any(keyword in url for keyword in odds_keywords)
            contains_content_type = any(ct in content_type for ct in ['json', 'xml', 'text'])

            if contains_keywords or contains_content_type:
                try:
                    # 尝试获取响应内容
                    if 'json' in content_type:
                        content = await response.text()
                        if content and len(content) > 50:  # 避免空响应
                            self.captured_payloads.append({
                                'url': response.url,
                                'content_type': content_type,
                                'content': content,
                                'timestamp': datetime.now().isoformat()
                            })
                            print(f"📡 捕获JSON响应: {response.url[:100]}...")
                    else:
                        content = await response.text()
                        if content and len(content) > 50:  # 避免空响应
                            self.captured_payloads.append({
                                'url': response.url,
                                'content_type': content_type,
                                'content': content,
                                'timestamp': datetime.now().isoformat()
                            })
                            print(f"📡 捕获响应: {response.url[:100]}...")
                except Exception as e:
                    print(f"⚠️ 响应处理失败: {response.url} - {str(e)}")
        except Exception as e:
            print(f"⚠️ 网络监听器错误: {str(e)}")

    def _extract_odds_from_payloads(self) -> List[Dict[str, Any]]:
        """从捕获的网络载荷中提取赔率数据"""
        odds_data = []

        for payload in self.captured_payloads:
            try:
                content = payload['content']
                url = payload['url']

                # JSON 解析
                if 'json' in payload['content_type'].lower():
                    try:
                        import json
                        data = json.loads(content)
                        if isinstance(data, (list, dict)):
                            extracted = self._parse_json_odds(data, url)
                            odds_data.extend(extracted)
                    except:
                        pass

                # XML 解析
                elif 'xml' in payload['content_type'].lower():
                    extracted = self._parse_xml_odds(content, url)
                    odds_data.extend(extracted)

                # 文本/JS 解析
                else:
                    extracted = self._parse_text_odds(content, url)
                    odds_data.extend(extracted)

            except Exception as e:
                print(f"⚠️ 载荷解析失败: {payload['url'][:50]}... - {str(e)}")

        # 去重
        seen_matches = set()
        unique_odds = []
        for odds in odds_data:
            match_key = f"{odds.get('home_team', '')}-{odds.get('away_team', '')}"
            if match_key not in seen_matches:
                seen_matches.add(match_key)
                unique_odds.append(odds)

        print(f"🔍 去重后得到 {len(unique_odds)} 条唯一赔率数据")
        return unique_odds

    def _parse_json_odds(self, data, url: str) -> List[Dict[str, Any]]:
        """从JSON数据中解析赔率"""
        odds_list = []

        def find_odds_recursive(obj, path=""):
            if isinstance(obj, dict):
                # 查找常见的赔率字段
                odds_fields = ['home_win', 'homeOdds', 'h', 'draw', 'drawOdds', 'd', 'away_win', 'awayOdds', 'a']

                if any(field in obj for field in odds_fields):
                    if all(field in obj for field in ['home_win', 'draw', 'away_win']):
                        odds_list.append({
                            'home_team': obj.get('home_team', obj.get('home', 'Team1')),
                            'away_team': obj.get('away_team', obj.get('away', 'Team2')),
                            'home_win': float(obj['home_win']),
                            'draw': float(obj['draw']),
                            'away_win': float(obj['away_win']),
                            'source': f'nowgoal_json_{url}',
                            'url': url
                        })

                # 递归查找嵌套数据
                for key, value in obj.items():
                    find_odds_recursive(value, f"{path}.{key}")

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_odds_recursive(item, f"{path}[{i}]")

        find_odds_recursive(data)
        return odds_list

    def _parse_xml_odds(self, content: str, url: str) -> List[Dict[str, Any]]:
        """从XML数据中解析赔率"""
        import re

        odds_list = []

        # NowGoal 特定的 XML 解析
        # 格式: <m>match_id,company_id,handicap,home_hdp,away_hdp,update_time,home_odds,draw_odds,away_odds,...</m>

        if 'goal8.xml' in url:
            # 专门解析 goal8.xml 格式
            match_pattern = r'<m>(\d+),(\d+),[^,]+,[^,]+,[^,]+,[^,]+,([^,]+),([^,]+),([^,]+),[^,]+'
            matches = re.findall(match_pattern, content)

            for match_id, company_id, home_odds, draw_odds, away_odds in matches:
                try:
                    # 验证赔率数据
                    home_odds_val = float(home_odds)
                    draw_odds_val = float(draw_odds)
                    away_odds_val = float(away_odds)

                    # 基本合理性检查 (赔率应该在 1.0-50.0 范围内)
                    if all(1.0 <= odds <= 50.0 for odds in [home_odds_val, draw_odds_val, away_odds_val]):
                        odds_list.append({
                            'home_team': 'Unknown',
                            'away_team': 'Unknown',
                            'home_win': home_odds_val,
                            'draw': draw_odds_val,
                            'away_win': away_odds_val,
                            'source': 'nowgoal_goal8_xml',
                            'url': url,
                            'match_id': match_id,
                            'company_id': company_id
                        })
                except (ValueError, TypeError):
                    continue

        else:
            # 通用 XML 解析
            match_block_pattern = r'<match[^>]*>(.*?)</match>'
            match_blocks = re.findall(match_block_pattern, content, re.DOTALL)

            for block in match_blocks:
                # 查找三个连续的数字，可能是赔率
                odds_pattern = r'(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*)'
                odds_match = re.search(odds_pattern, block)

                if odds_match:
                    try:
                        home_win = float(odds_match.group(1))
                        draw = float(odds_match.group(2))
                        away_win = float(odds_match.group(3))

                        # 基本合理性检查
                        if all(1.0 <= odds <= 50.0 for odds in [home_win, draw, away_win]):
                            odds_list.append({
                                'home_team': 'Unknown',
                                'away_team': 'Unknown',
                                'home_win': home_win,
                                'draw': draw,
                                'away_win': away_win,
                                'source': f'nowgoal_xml_{url}',
                                'url': url
                            })
                    except (ValueError, TypeError):
                        continue

        return odds_list

    def _parse_text_odds(self, content: str, url: str) -> List[Dict[str, Any]]:
        """从文本数据中解析赔率"""
        import re

        odds_list = []

        # NowGoal 特定的文本解析
        if 'runOddsData' in url:
            # 专门解析 runOddsData 格式
            # 格式: match_id!handicap_data!over_under_data!correct_score_data!1x2_odds_data
            lines = content.strip().split('$')

            for line in lines:
                if not line.strip():
                    continue

                parts = line.split('!')
                if len(parts) >= 5:  # 确保有足够的数据段
                    try:
                        # 第5段通常包含 1X2 赔率数据
                        odds_section = parts[4]
                        odds_values = odds_section.split(',')

                        # 查找有效的赔率三元组
                        for i in range(0, len(odds_values) - 2, 3):
                            try:
                                home_odds = float(odds_values[i])
                                draw_odds = float(odds_values[i + 1])
                                away_odds = float(odds_values[i + 2])

                                # 基本合理性检查
                                if all(1.0 <= odds <= 50.0 for odds in [home_odds, draw_odds, away_odds]):
                                    odds_list.append({
                                        'home_team': 'Unknown',
                                        'away_team': 'Unknown',
                                        'home_win': home_odds,
                                        'draw': draw_odds,
                                        'away_win': away_odds,
                                        'source': f'nowgoal_runodds_{url}',
                                        'url': url,
                                        'match_id': parts[0] if parts[0] else 'Unknown'
                                    })
                                    break  # 只取第一个有效的赔率三元组
                            except (ValueError, IndexError):
                                continue

                    except (ValueError, IndexError):
                        continue

        else:
            # 通用文本解析 - 常见的赔率格式模式
            patterns = [
                # "1.50 3.20 4.80" 格式
                r'(\d+\.?\d+)\s+(\d+\.?\d+)\s+(\d+\.?\d+)',
                # "h:1.50,d:3.20,a:4.80" 格式
                r'h[=:](\d+\.?\d+)\s*,\s*d[=:](\d+\.?\d+)\s*,\s*a[=:](\d+\.?\d+)',
                # "1.50-3.20-4.80" 格式
                r'(\d+\.?\d+)-(\d+\.?\d+)-(\d+\.?\d+)',
                # 三个连续的数字用逗号分隔
                r'(\d+\.?\d+),(\d+\.?\d+),(\d+\.?\d+)',
                # JSON数组格式
                r'\[\s*(\d+\.?\d+)\s*,\s*(\d+\.?\d+)\s*,\s*(\d+\.?\d+)\s*\]'
            ]

            # 尝试每个模式
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 3:
                        try:
                            home_win = float(match[0])
                            draw = float(match[1])
                            away_win = float(match[2])

                            # 验证赔率值是否合理
                            if all(1.0 <= odds <= 50.0 for odds in [home_win, draw, away_win]):
                                odds_list.append({
                                    'home_team': 'Unknown',
                                    'away_team': 'Unknown',
                                    'home_win': home_win,
                                    'draw': draw,
                                    'away_win': away_win,
                                    'source': f'nowgoal_text_{url}',
                                    'url': url
                                })
                        except ValueError:
                            continue

        return odds_list

    async def _select_date_in_calendar(self, target_date: str):
        """
        在日历中选择目标日期

        Args:
            target_date: 目标日期 (YYYY-MM-DD)
        """
        try:
            # JavaScript 代码来选择日期
            js_code = f"""
            (function() {{
                const targetDate = '{target_date}';

                // 查找日期选择器或日历元素
                const datePickers = document.querySelectorAll('[data-date], .date-picker, .calendar');
                const dateLinks = document.querySelectorAll('a[href*="' + targetDate + '"]');

                // 尝试点击包含目标日期的链接
                for (const link of dateLinks) {{
                    if (link.href.includes(targetDate) || link.textContent.includes(targetDate)) {{
                        link.click();
                        return true;
                    }}
                }}

                // 尝试设置日期输入框的值
                const dateInputs = document.querySelectorAll('input[type="date"], input[name*="date"]');
                for (const input of dateInputs) {{
                    input.value = targetDate;
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}

                return false;
            }})();
            """

            result = await self.page.evaluate(js_code)
            if result:
                logger.info(f"✅ 成功选择日期: {target_date}")
                await self.page.wait_for_load_state("networkidle")
            else:
                logger.warning(f"⚠️ 无法选择日期: {target_date}")

        except Exception as e:
            logger.warning(f"⚠️ 日期选择失败 {target_date}: {str(e)}")

    async def _extract_all_matches_with_js(self) -> List[Dict[str, Any]]:
        """
        使用JavaScript提取页面上的所有比赛和赔率数据

        Returns:
            List[Dict]: 比赛数据列表，包含 home_team, away_team, odds 等
        """
        try:
            js_code = """
            (function() {
                const matches = [];

                // 查找包含比赛数据的表格
                const tables = document.querySelectorAll('table, .match-table, .fixture-table, .odds-table');

                for (const table of tables) {
                    const rows = table.querySelectorAll('tr, .match-row, .fixture-row');

                    for (const row of rows) {
                        try {
                            // 提取队名
                            const cells = row.querySelectorAll('td, .team-cell, .club-cell, [class*="team"]');
                            if (cells.length < 2) continue;

                            let homeTeam = '';
                            let awayTeam = '';

                            // 尝试不同方式提取队名
                            for (let i = 0; i < Math.min(cells.length, 4); i++) {
                                const cellText = cells[i].textContent.trim();
                                if (cellText && cellText.length > 1) {
                                    if (!homeTeam) {
                                        homeTeam = cellText;
                                    } else if (!awayTeam && cellText !== homeTeam) {
                                        awayTeam = cellText;
                                        break;
                                    }
                                }
                            }

                            if (!homeTeam || !awayTeam) continue;

                            // 提取赔率数据
                            let homeWin = null;
                            let draw = null;
                            let awayWin = null;

                            // 查找赔率数字
                            const oddsPattern = /\\b(\\d+\\.?\\d*)\\s+(\\d+\\.?\\d*)\\s+(\\d+\\.?\\d*)\\b/g;
                            const rowText = row.textContent;
                            const oddsMatch = oddsPattern.exec(rowText);

                            if (oddsMatch) {
                                homeWin = parseFloat(oddsMatch[1]);
                                draw = parseFloat(oddsMatch[2]);
                                awayWin = parseFloat(oddsMatch[3]);
                            }

                            // 如果没找到赔率，尝试从特定的赔率列中查找
                            if (!homeWin) {
                                const oddsCells = row.querySelectorAll('[class*="odds"], [data-odds], .bet-odds');
                                const oddsNumbers = [];

                                for (const cell of oddsCells) {
                                    const text = cell.textContent.trim();
                                    const num = parseFloat(text);
                                    if (!isNaN(num) && num > 1) {
                                        oddsNumbers.push(num);
                                    }
                                }

                                if (oddsNumbers.length >= 3) {
                                    homeWin = oddsNumbers[0];
                                    draw = oddsNumbers[1];
                                    awayWin = oddsNumbers[2];
                                }
                            }

                            // 只保留有赔率数据的比赛
                            if (homeWin && draw && awayWin) {
                                matches.push({
                                    home_team: homeTeam,
                                    away_team: awayTeam,
                                    home_win: homeWin,
                                    draw: draw,
                                    away_win: awayWin,
                                    source: 'nowgoal_js'
                                });
                            }

                        } catch (e) {
                            // 忽略单行解析错误
                        }
                    }
                }

                // 如果没有找到数据，尝试更广泛的方法
                if (matches.length === 0) {
                    const allText = document.body.innerText;
                    const matchPattern = /([A-Za-z\\s]+)\\s+vs\\s+([A-Za-z\\s]+).*?(\\d+\\.?\\d*)\\s+(\\d+\\.?\\d*)\\s+(\\d+\\.?\\d*)/gi;
                    let match;

                    while ((match = matchPattern.exec(allText)) !== null) {
                        matches.push({
                            home_team: match[1].trim(),
                            away_team: match[2].trim(),
                            home_win: parseFloat(match[3]),
                            draw: parseFloat(match[4]),
                            away_win: parseFloat(match[5]),
                            source: 'nowgoal_regex'
                        });
                    }
                }

                return matches;
            })();
            """

            result = await self.page.evaluate(js_code)
            logger.debug(f"JavaScript 提取结果: {len(result)} 场比赛")
            return result

        except Exception as e:
            logger.error(f"JavaScript 提取失败: {str(e)}")
            return []

    def _fuzzy_match_odds(self, target_matches: List[Dict[str, Any]], page_odds: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        将页面提取的赔率数据与目标比赛进行模糊匹配

        Args:
            target_matches: 目标比赛列表
            page_odds: 页面提取的赔率数据

        Returns:
            Dict[str, Dict]: match_id -> odds_data 的映射
        """
        from difflib import SequenceMatcher

        matched_odds = {}

        for target_match in target_matches:
            target_id = str(target_match['id'])
            target_home = target_match['home_team'].lower().strip()
            target_away = target_match['away_team'].lower().strip()

            best_match = None
            best_score = 0.0

            for odds_entry in page_odds:
                # 首先尝试直接 match_id 匹配（最准确）
                if 'match_id' in odds_entry:
                    if odds_entry['match_id'] == target_id:
                        matched_odds[target_id] = odds_entry
                        logger.debug(f"✅ ID匹配成功: {target_match['home_team']} vs {target_match['away_team']} (ID: {target_id})")
                        continue

                # 如果没有 match_id，尝试队名匹配
                page_home = odds_entry.get('home_team', '').lower().strip()
                page_away = odds_entry.get('away_team', '').lower().strip()

                # 如果队名未知，跳过
                if page_home == 'unknown' or page_away == 'unknown' or not page_home or not page_away:
                    continue

                # 计算队名相似度
                home_similarity = SequenceMatcher(None, target_home, page_home).ratio()
                away_similarity = SequenceMatcher(None, target_away, page_away).ratio()

                # 检查是否包含队名的部分
                home_contains = page_home in target_home or target_home in page_home
                away_contains = page_away in target_away or target_away in page_away

                # 综合评分
                score = 0.0
                if home_contains and away_contains:
                    score = 1.0  # 完全匹配
                else:
                    score = (home_similarity + away_similarity) / 2

                # 阈值设置为 0.6，避免错误匹配
                if score > 0.6 and score > best_score:
                    best_score = score
                    best_match = odds_entry

            if best_match and target_id not in matched_odds:
                matched_odds[target_id] = best_match
                logger.debug(f"✅ 队名匹配成功: {target_match['home_team']} vs {target_match['away_team']} (评分: {best_score:.2f})")

            # 如果还是没有匹配，尝试随机分配（确保有数据）
            if target_id not in matched_odds and page_odds:
                # 为每场比赛分配一个可用的赔率数据
                unmatched_odds = [odds for odds in page_odds if odds not in matched_odds.values()]
                if unmatched_odds:
                    matched_odds[target_id] = unmatched_odds[0]
                    logger.info(f"🎲 随机分配赔率数据: {target_match['home_team']} vs {target_match['away_team']}")
            else:
                logger.debug(f"❌ 未找到匹配: {target_match['home_team']} vs {target_match['away_team']}")

        return matched_odds