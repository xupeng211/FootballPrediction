"""
赔率数据源管理
Odds Data Sources Management

管理多个博彩公司的API数据源
"""



logger = logging.getLogger(__name__)


class OddsSourceManager:
    """赔率数据源管理器"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化数据源管理器

        Args:
            api_key: API密钥
        """
        self.api_key = api_key or os.getenv("ODDS_API_TOKEN")

        # API端点配置
        self.api_endpoints = {
            "odds_api": os.getenv("ODDS_API_URL", "https://api.the-odds-api.com/v4"),
            "betfair": os.getenv("BETFAIR_URL", "https://api.betfair.com/exchange/betting/rest/v1.0"),
            "pinnacle": os.getenv("PINNACLE_URL", "https://api.pinnacle.com/v1"),
        }

        # 支持的博彩公司
        self.bookmakers = [
            "bet365",
            "william_hill",
            "ladbrokes",
            "betfair",
            "pinnacle",
            "betway",
            "888sport",
            "unibet",
            "betfred",
            "coral",
        ]

        # 重试配置
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
        )

    @retry(RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
    ))
    async def fetch_odds_from_apis(
        self,
        match_id: int,
        bookmakers: List[str],
        markets: List[str],
    ) -> Dict[str, Any]:
        """
        从多个API获取赔率数据

        Args:
            match_id: 比赛ID
            bookmakers: 博彩公司列表
            markets: 市场类型列表

        Returns:
            所有数据源的赔率数据
        """
        all_odds = {}

        # 尝试多个数据源
        tasks = []
        for source_name, base_url in self.api_endpoints.items():
            task = self._fetch_from_source(source_name, match_id, bookmakers, markets)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, (source_name, result) in enumerate(zip(self.api_endpoints.keys(), results)):
            if isinstance(result, Exception):
                logger.warning(f"从 {source_name} 获取赔率失败: {result}")
                continue
            if result:
                all_odds[source_name] = result

        return all_odds

    async def _fetch_from_source(
        self,
        source: str,
        match_id: int,
        bookmakers: List[str],
        markets: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        从指定数据源获取赔率

        Args:
            source: 数据源名称
            match_id: 比赛ID
            bookmakers: 博彩公司列表
            markets: 市场类型列表

        Returns:
            赔率数据
        """
        if source == "odds_api":
            return await self._fetch_from_odds_api(match_id, bookmakers)
        elif source == "betfair":
            return await self._fetch_from_betfair(match_id, markets)
        elif source == "pinnacle":
            return await self._fetch_from_pinnacle(match_id)

        return None

    async def _fetch_from_odds_api(
        self,
        match_id: int,
        bookmakers: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        从The Odds API获取赔率

        Args:
            match_id: 比赛ID
            bookmakers: 博彩公司列表

        Returns:
            赔率数据
        """
        if not self.api_key:
            return None

        # 构建API URL
        regions = "uk,eu,us"
        markets = "h2h,ou,bts,cs,ah"
        bookmakers_str = ",".join(bookmakers[:10])  # API限制

        url = (
            f"{self.api_endpoints['odds_api']}/sports/soccer/odds"
            f"?apiKey={self.api_key}"
            f"&regions={regions}"
            f"&markets={markets}"
            f"&bookmakers={bookmakers_str}"
            f"&oddsFormat=decimal"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 查找指定比赛
                        for game in data:
                            if game.get("id") == match_id:
                                return self._transform_odds_api_data(game)
                        return None
                    else:
                        logger.warning(f"Odds API请求失败: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"从Odds API获取数据失败: {e}")
            return None

    async def _fetch_from_betfair(
        self,
        match_id: int,
        markets: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        从Betfair获取赔率（简化实现）

        Args:
            match_id: 比赛ID
            markets: 市场类型列表

        Returns:
            赔率数据
        """
        # Betfair需要更复杂的认证和会话管理
        # 这里提供占位实现
        return None

    async def _fetch_from_pinnacle(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        从Pinnacle获取赔率（简化实现）

        Args:
            match_id: 比赛ID

        Returns:
            赔率数据
        """
        # Pinnacle需要特定的认证
        # 这里提供占位实现
        return None

    def _transform_odds_api_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换Odds API数据格式

        Args:
            data: 原始API数据

        Returns:
            转换后的数据
        """
        transformed = {
            "match_id": data.get("id"),
            "sport_key": data.get("sport_key"),
            "commence_time": data.get("commence_time"),
            "bookmakers": [],
        }




        for bookmaker in data.get("bookmakers", []):
            bookmaker_data = {
                "key": bookmaker.get("key"),
                "title": bookmaker.get("title"),
                "markets": {},
            }

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                if market_key == "h2h":
                    # Match winner market
                    outcomes = {
                        o["name"]: o["price"] for o in market.get("outcomes", [])
                    }
                    bookmaker_data["markets"]["match_winner"] = {
                        "home_win": outcomes.get("Home"),
                        "draw": outcomes.get("Draw"),
                        "away_win": outcomes.get("Away"),
                    }
                elif market_key == "ou":
                    # Over/Under market
                    outcomes = {
                        o["name"]: o["price"] for o in market.get("outcomes", [])
                    }
                    over_line = None
                    if "Over" in outcomes:
                        # 提取盘口线
                        match = re.search(
                            r"Over (\d+\.?\d*)",
                            market.get("outcomes", [{}])[0].get("name", ""),
                        )
                        if match:
                            over_line = float(match.group(1))

                    bookmaker_data["markets"]["over_under"] = {
                        "line": over_line,
                        "over_odds": outcomes.get("Over"),
                        "under_odds": outcomes.get("Under"),
                    }
                elif market_key == "bts":
                    # Both teams to score
                    outcomes = {
                        o["name"]: o["price"] for o in market.get("outcomes", [])
                    }
                    bookmaker_data["markets"]["both_teams_score"] = {
                        "yes": outcomes.get("Yes"),
                        "no": outcomes.get("No"),
                    }

            transformed["bookmakers"].append(bookmaker_data)

        return transformed