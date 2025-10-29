#!/usr/bin/env python3
"""
OddsPortal爬虫模块
OddsPortal Scraper Module

提供从OddsPortal网站抓取赔率数据的功能
支持实时数据流和历史数据获取
"""

import asyncio
import aiohttp
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

from src.core.logging_system import get_logger

logger = get_logger(__name__)


@dataclass
class OddsPortalMatch:
    """OddsPortal比赛数据结构"""

    match_id: str
    home_team: str
    away_team: str
    league: str
    match_date: datetime
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None
    over_under: Optional[float] = None
    asian_handicap: Optional[float] = None
    source: str = "oddsportal"


class OddsPortalScraper:
    """OddsPortal爬虫类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化OddsPortal爬虫

        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.base_url = "https://www.oddsportal.com"
        self.session = None
        self.user_agent =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_retries = 3
        self.retry_delay = 2
        self.robots_parser = RobotFileParser()
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 秒
        self.logger = get_logger(self.__class__.__name__)

        # 请求限制
        self.rate_limit_requests_per_minute = 60
        self.request_times = []

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def _init_session(self):
        """初始化HTTP会话"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q =
    0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )

    async def _check_rate_limit(self):
        """检查并遵守速率限制"""
        current_time = datetime.now()

        # 清理旧的请求记录（超过1分钟）
        self.request_times = [
            t for t in self.request_times if (current_time - t).total_seconds() < 60
        ]

        # 检查是否超过速率限制
        if len(self.request_times) >= self.rate_limit_requests_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0]).total_seconds()
            if sleep_time > 0:
                self.logger.info(
                    f"Rate limit reached, sleeping for {sleep_time:.1f} seconds"
                )
                await asyncio.sleep(sleep_time)

        # 检查最小请求间隔
        time_since_last = (current_time - self.last_request_time).total_seconds()
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = current_time
        self.request_times.append(current_time)

    async def _fetch_page(
        self, url: str, max_retries: Optional[int] = None
    ) -> Optional[str]:
        """
        获取网页内容

        Args:
            url: 网页URL
            max_retries: 最大重试次数

        Returns:
            网页内容或None
        """
        if max_retries is None:
            max_retries = self.max_retries

        await self._check_rate_limit()

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Fetching URL: {url} (attempt {attempt + 1})")

                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.logger.debug(
                            f"Successfully fetched {len(content)} characters"
                        )
                        return content
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 30))
                        self.logger.warning(
                            f"Rate limited, retrying after {retry_after} seconds"
                        )
                        await asyncio.sleep(retry_after)
                    else:
                        self.logger.warning(f"HTTP {response.status} for URL: {url}")
                        return None

            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout for URL: {url} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
            except Exception as e:
                self.logger.error(f"Error fetching URL {url}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))

        return None

    async def _check_robots_txt(self, path: str) -> bool:
        """
        检查robots.txt是否允许访问

        Args:
            path: URL路径

        Returns:
            是否允许访问
        """
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            content = await self._fetch_page(robots_url, max_retries=1)

            if content:
                self.robots_parser.parse(content)
                return self.robots_parser.can_fetch(self.user_agent, path)

            return True  # 如果没有robots.txt，允许访问

        except Exception as e:
            self.logger.warning(f"Error checking robots.txt: {e}")
            return True  # 出错时默认允许访问

    def _parse_match_data(self, html: str, league: str) -> List[OddsPortalMatch]:
        """
        解析比赛数据

        Args:
            html: HTML内容
            league: 联赛名称

        Returns:
            比赛数据列表
        """
        matches = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # 查找比赛表格或列表
            # OddsPortal通常使用表格显示赔率数据
            tables = soup.find_all("table")

            for table in tables:
                # 检查是否是赔率表格
                if self._is_odds_table(table):
                    table_matches = self._parse_odds_table(table, league)
                    matches.extend(table_matches)

            # 如果没有找到表格，尝试其他方式解析
            if not matches:
                # 尝试解析比赛列表页面
                matches = self._parse_match_list(soup, league)

        except Exception as e:
            self.logger.error(f"Error parsing match data: {e}")

        return matches

    def _is_odds_table(self, table) -> bool:
        """检查是否是赔率表格"""
        # 检查表头是否包含赔率相关关键词
        headers = table.find_all("th")
        header_text = [th.get_text().strip().lower() for th in headers]

        odds_keywords = [
            "1",
            "x",
            "2",
            "home",
            "draw",
            "away",
            "胜",
            "平",
            "负",
            "odds",
        ]
        return any(keyword in " ".join(header_text) for keyword in odds_keywords)

    def _parse_odds_table(self, table, league: str) -> List[OddsPortalMatch]:
        """解析赔率表格"""
        matches = []

        try:
            rows = table.find_all("tr")

            # 跳过表头
            if rows and rows[0].find_all("th"):
                rows = rows[1:]

            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:  # 至少需要主队、客队、赔率
                    continue

                try:
                    # 解析队伍名称和赔率
                    match_data = self._parse_odds_row(cells, league)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Error parsing odds row: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error parsing odds table: {e}")

        return matches

    def _parse_odds_row(self, cells, league: str) -> Optional[OddsPortalMatch]:
        """解析赔率行数据"""
        try:
            # 简化实现：假设前两个单元格是主客队，后面是赔率
            if len(cells) < 3:
                return None

            home_team = cells[0].get_text().strip()
            away_team = cells[1].get_text().strip()

            if not home_team or not away_team:
                return None

            # 解析赔率数据
            odds_home = None
            odds_draw = None
            odds_away = None

            # 简单实现：假设第3、4、5个单元格是1、X、2的赔率
            if len(cells) >= 6:
                try:
                    odds_home = self._parse_odds_value(cells[2].get_text())
                    odds_draw = self._parse_odds_value(cells[3].get_text())
                    odds_away = self._parse_odds_value(cells[4].get_text())
                except ValueError:
                    pass

            # 生成比赛ID
            match_id = f"{home_team}_vs_{away_team}_{datetime.now().strftime('%Y%m%d')}"

            return OddsPortalMatch(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=datetime.now(),
                status="upcoming",
                odds_home_win=odds_home,
                odds_draw=odds_draw,
                odds_away_win=odds_away,
                source="oddsportal",
            )

        except Exception as e:
            self.logger.warning(f"Error parsing odds row: {e}")
            return None

    def _parse_odds_value(self, text: str) -> Optional[float]:
        """解析赔率值"""
        try:
            # 移除空白字符
            text = text.strip()

            # 处理不同的赔率格式
            # 例如：2.50, 5/2, 2.5等
            if "/" in text:
                numerator, denominator = text.split("/")
                return float(numerator) / float(denominator)

            # 尝试解析小数
            return float(text)

        except (ValueError, ZeroDivisionError):
            return None

    def _parse_match_list(self, soup, league: str) -> List[OddsPortalMatch]:
        """解析比赛列表"""
        matches = []

        try:
            # 查找包含比赛信息的元素
            match_elements = soup.find_all(
                ["div", "tr"], class_=re.compile(r"match|game|event")
            )

            for element in match_elements:
                try:
                    # 尝试从元素中提取比赛信息
                    match_data = self._extract_match_from_element(element, league)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Error extracting match from element: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error parsing match list: {e}")

        return matches

    def _extract_match_from_element(
        self, element, league: str
    ) -> Optional[OddsPortalMatch]:
        """从HTML元素中提取比赛信息"""
        try:
            # 查找队伍名称
            text = element.get_text().strip()

            # 使用正则表达式匹配比赛格式
            # 例如：Team A vs Team B
            match_pattern = r"(.+?)\s+vs\s+(.+)"
            match = re.search(match_pattern, text, re.IGNORECASE)

            if not match:
                return None

            home_team = match.group(1).strip()
            away_team = match.group(2).strip()

            # 生成比赛ID
            match_id = f"{home_team}_vs_{away_team}_{datetime.now().strftime('%Y%m%d')}"

            return OddsPortalMatch(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=datetime.now(),
                status="upcoming",
                source="oddsportal",
            )

        except Exception as e:
            self.logger.warning(f"Error extracting match from element: {e}")
            return None

    async def scrape_league_matches(
        self, league_url: str, league_name: str
    ) -> List[OddsPortalMatch]:
        """
        抓取联赛比赛数据

        Args:
            league_url: 联赛URL
            league_name: 联赛名称

        Returns:
            比赛数据列表
        """
        self.logger.info(f"Scraping league matches from: {league_url}")

        # 检查robots.txt
        path = urlparse(league_url).path
        if not await self._check_robots_txt(path):
            self.logger.warning(f"Robots.txt disallows access to: {league_url}")
            return []

        # 获取网页内容
        html = await self._fetch_page(league_url)
        if not html:
            self.logger.error(f"Failed to fetch page: {league_url}")
            return []

        # 解析比赛数据
        matches = self._parse_match_data(html, league_name)

        self.logger.info(f"Found {len(matches)} matches for league: {league_name}")
        return matches

    async def scrape_today_matches(self) -> List[OddsPortalMatch]:
        """
        抓取今日比赛数据

        Returns:
            今日比赛数据列表
        """
        datetime.now().strftime("%Y-%m-%d")

        # OddsPortal今日比赛URL（需要根据实际网站结构调整）
        today_url = f"{self.base_url}/football/england/premier-league/today-matches"

        self.logger.info(f"Scraping today's matches from: {today_url}")

        matches = await self.scrape_league_matches(today_url, "Premier League")

        # 如果今日比赛URL不工作，尝试其他URL
        if not matches:
            alternative_urls = [
                f"{self.base_url}/football/england/premier-league/matches",
                f"{self.base_url}/football/matches/today",
            ]

            for url in alternative_urls:
                self.logger.info(f"Trying alternative URL: {url}")
                matches = await self.scrape_league_matches(url, "Premier League")
                if matches:
                    break

        return matches

    async def scrape_live_matches(self) -> List[OddsPortalMatch]:
        """
        抓取实时比赛数据

        Returns:
            实时比赛数据列表
        """
        # OddsPortal实时比赛URL（需要根据实际网站结构调整）
        live_url = f"{self.base_url}/football/live-matches"

        self.logger.info(f"Scraping live matches from: {live_url}")

        matches = await self.scrape_league_matches(live_url, "Live Matches")

        return matches

    def convert_to_data_source_format(
        self, oddsportal_matches: List[OddsPortalMatch]
    ) -> List[MatchData]:
        """
        转换为标准数据源格式

        Args:
            oddsportal_matches: OddsPortal比赛数据

        Returns:
            标准格式比赛数据
        """
        matches = []

        for op_match in oddsportal_matches:
            try:
                # 转换赔率数据
                odds_list = []
                if (
                    op_match.odds_home_win is not None
                    and op_match.odds_draw is not None
                    and op_match.odds_away_win is not None
                ):
                    odds_list.append(
                        OddsData(
                            match_id=hash(op_match.match_id),
                            home_win=op_match.odds_home_win,
                            draw=op_match.odds_draw,
                            away_win=op_match.odds_away_win,
                            source="oddsportal",
                            timestamp=datetime.now(),
                        )
                    )

                # 转换比赛数据
                match = MatchData(
                    id=hash(op_match.match_id),
                    home_team=op_match.home_team,
                    away_team=op_match.away_team,
                    match_date=op_match.match_date,
                    league=op_match.league,
                    status=op_match.status,
                    home_score=op_match.home_score,
                    away_score=op_match.away_score,
                )

                matches.append(match)

            except Exception as e:
                self.logger.warning(f"Error converting match {op_match.match_id}: {e}")
                continue

        return matches

    async def get_matches(
        self,
        league_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MatchData]:
        """
        获取比赛列表（实现DataSourceAdapter接口）

        Args:
            league_id: 联赛ID
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            比赛数据列表
        """
        try:
            # 确定要抓取的联赛
            if league_id == 39:  # 英超
                league_name = "Premier League"
                league_url = f"{self.base_url}/football/england/premier-league/matches"
            elif league_id == 140:  # 西甲
                league_name = "La Liga"
                league_url = f"{self.base_url}/football/spain/laliga/matches"
            elif league_id == 78:  # 德甲
                league_name = "Bundesliga"
                league_url = f"{self.base_url}/football/germany/bundesliga/matches"
            elif league_id == 135:  # 意甲
                league_name = "Serie A"
                league_url = f"{self.base_url}/football/italy/serie-a/matches"
            elif league_id == 61:  # 法甲
                league_name = "Ligue 1"
                league_url = f"{self.base_url}/football/france/ligue-1/matches"
            else:
                # 默认抓取英超
                league_name = "Premier League"
                league_url = f"{self.base_url}/football/england/premier-league/matches"

            # 如果有日期范围，可能需要调整URL
            if date_from or date_to:
                self.logger.info(
                    "Date filtering not implemented for OddsPortal scraper"
                )

            # 抓取比赛数据
            oddsportal_matches = await self.scrape_league_matches(
                league_url, league_name
            )

            # 转换为标准格式
            matches = self.convert_to_data_source_format(oddsportal_matches)

            self.logger.info(f"Retrieved {len(matches)} matches from OddsPortal")
            return matches

        except Exception as e:
            self.logger.error(f"Error getting matches from OddsPortal: {e}")
            return []

    async def get_teams(self, league_id: Optional[int] = None) -> List[TeamData]:
        """
        获取球队列表（实现DataSourceAdapter接口）

        Args:
            league_id: 联赛ID

        Returns:
            球队数据列表
        """
        # OddsPortal球队数据抓取实现
        teams = []

        try:
            # 从已获取的比赛中提取球队信息
            matches = await self.get_matches(league_id)
            team_names = set()

            for match in matches:
                team_names.add(match.home_team)
                team_names.add(match.away_team)

            # 创建球队数据
            for i, team_name in enumerate(team_names):
                team = TeamData(
                    id=i + 1,
                    name=team_name,
                    short_name=(
                        team_name[:3].upper() if len(team_name) > 3 else team_name
                    ),
                    venue=None,
                    website=None,
                )
                teams.append(team)

            self.logger.info(f"Extracted {len(teams)} teams from OddsPortal matches")

        except Exception as e:
            self.logger.error(f"Error getting teams from OddsPortal: {e}")

        return teams

    async def get_odds(self, match_id: int) -> List[OddsData]:
        """
        获取赔率数据（实现DataSourceAdapter接口）

        Args:
            match_id: 比赛ID

        Returns:
            赔率数据列表
        """
        # OddsPortal赔率数据获取实现
        odds_list = []

        try:
            # 这里可以实现更详细的赔率数据抓取逻辑
            # 例如：访问特定比赛页面获取详细赔率信息

            self.logger.info(f"Getting odds for match_id: {match_id}")

            # 简化实现：返回空列表
            # 在实际应用中，需要访问具体比赛页面获取赔率数据

        except Exception as e:
            self.logger.error(f"Error getting odds for match {match_id}: {e}")

        return odds_list


# 便捷函数
async def scrape_oddsportal_league(
    league_name: str, config: Optional[Dict[str, Any]] = None
) -> List[OddsPortalMatch]:
    """
    抓取指定联赛的赔率数据

    Args:
        league_name: 联赛名称
        config: 配置参数

    Returns:
        赔赛数据列表
    """
    async with OddsPortalScraper(config) as scraper:
        # 根据联赛名称确定URL
        league_urls = {
            "Premier League": f"{scraper.base_url}/football/england/premier-league/matches",
            "La Liga": f"{scraper.base_url}/football/spain/laliga/matches",
            "Bundesliga": f"{scraper.base_url}/football/germany/bundesliga/matches",
            "Serie A": f"{scraper.base_url}/football/italy/serie-a/matches",
            "Ligue 1": f"{scraper.base_url}/football/france/ligue-1/matches",
        }

        league_url = league_urls.get(league_name)
        if not league_url:
            raise ValueError(f"Unsupported league: {league_name}")

        matches = await scraper.scrape_league_matches(league_url, league_name)
        return matches


# 测试函数
async def test_oddsportal_scraper():
    """测试OddsPortal爬虫"""
    logger.info("Testing OddsPortal scraper...")

    config = {"timeout": 10, "max_retries": 2, "min_request_interval": 2.0}

    async with OddsPortalScraper(config) as scraper:
        # 测试抓取今日比赛
        today_matches = await scraper.scrape_today_matches()
        logger.info(f"Today's matches: {len(today_matches)}")

        # 显示前几个比赛
        for i, match in enumerate(today_matches[:3]):
            logger.info(f"Match {i+1}: {match.home_team} vs {match.away_team}")
            if match.odds_home_win:
                logger.info(
                    f"  Odds: Home =
    {match.odds_home_win:.2f}, Draw={match.odds_draw:.2f}, Away={match.odds_away_win:.2f}"
                )

    logger.info("OddsPortal scraper test completed")


if __name__ == "__main__":
    asyncio.run(test_oddsportal_scraper())
