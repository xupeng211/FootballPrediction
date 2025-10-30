from typing import List
from typing import Optional
from typing import Dict

"""
数据源配置和适配器
提供多种足球数据API的统一接口
"""

import os
import aiohttp
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from src.core.logging_system import get_logger

logger = get_logger(__name__)


@dataclass
class MatchData:
    """类文档字符串"""
    pass  # 添加pass语句
    """比赛数据结构"""

    id: int
    home_team: str
    away_team: str
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    match_date: datetime = None
    league: str = ""
    league_id: Optional[int] = None
    status: str = "upcoming"  # upcoming, live, finished, postponed
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    round: Optional[str] = None
    venue: Optional[str] = None


@dataclass
class TeamData:
    """类文档字符串"""
    pass  # 添加pass语句
    """球队数据结构"""

    id: int
    name: str
    short_name: Optional[str] = None
    crest: Optional[str] = None
    founded: Optional[int] = None
    venue: Optional[str] = None
    website: Optional[str] = None


@dataclass
class OddsData:
    """类文档字符串"""
    pass  # 添加pass语句
    """赔率数据结构"""

    match_id: int
    home_win: float
    draw: float
    away_win: float
    source: str
    timestamp: datetime = None
    over_under: Optional[float] = None
    asian_handicap: Optional[float] = None


class DataSourceAdapter(ABC):
    """数据源适配器基类"""

    def __init__(self, api_key: Optional[str] = None):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.api_key = api_key
        self.base_url = ""
        self.headers = {}
        self.timeout = aiohttp.ClientTimeout(total=30)

    @abstractmethod
    async def get_matches(
        self,
        league_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MatchData]:
        """获取比赛列表"""
        pass

    @abstractmethod
    async def get_teams(self, league_id: Optional[int] = None) -> List[TeamData]:
        """获取球队列表"""
        pass

    @abstractmethod
    async def get_odds(self, match_id: int) -> List[OddsData]:
        """获取赔率数据"""
        pass


class FootballDataOrgAdapter(DataSourceAdapter):
    """Football-Data.org API适配器"""

    def __init__(self, api_key: Optional[str] = None):
    """函数文档字符串"""
    pass  # 添加pass语句
        super().__init__(api_key)
        self.base_url = "https://api.football-data.org/v4"
        if self.api_key:
            self.headers = {"X-Auth-Token": self.api_key}

    async def get_matches(
        self,
        league_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MatchData]:
        """获取比赛列表"""

        try:
            # 构建URL参数
            params = {}
            if date_from:
                params["dateFrom"] = date_from.strftime("%Y-%m-%d")
            if date_to:
                params["dateTo"] = date_to.strftime("%Y-%m-%d")

            # 使用通用比赛端点获取比赛
            params["limit"] = 100  # 限制返回数量
            url = f"{self.base_url}/matches"

            return await self._fetch_matches_from_url(url, params)

        except Exception as e:
            logger.error(f"获取比赛数据失败: {e}")
            return []

    async def _fetch_matches_from_url(self, url: str, params: Dict) -> List[MatchData]:
        """从URL获取比赛数据"""
        matches = []

        async with aiohttp.ClientSession(
            headers=self.headers, timeout=self.timeout
        ) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for match in data.get("matches", []):
                        match_data = self._parse_match_data(match)
                        if match_data:
                            matches.append(match_data)
                else:
                    logger.warning(f"API请求失败: {response.status} - {url}")

        return matches

    def _parse_match_data(self, match: Dict) -> Optional[MatchData]:
        """解析比赛数据"""
        try:
            # 解析状态
            status_map = {
                "SCHEDULED": "upcoming",
                "LIVE": "live",
                "IN_PLAY": "live",
                "PAUSED": "live",
                "FINISHED": "finished",
                "POSTPONED": "postponed",
                "SUSPENDED": "postponed",
                "CANCELED": "postponed",
            }

            status = status_map.get(match.get("status", "SCHEDULED"), "upcoming")

            # 解析比分
            home_score = None
            away_score = None
            if status == "finished" and match.get("score"):
                home_score = match["score"].get("fullTime", {}).get("home")
                away_score = match["score"].get("fullTime", {}).get("away")

            return MatchData(
                id=match["id"],
                home_team=match["homeTeam"]["name"],
                away_team=match["awayTeam"]["name"],
                home_team_id=match["homeTeam"]["id"],
                away_team_id=match["awayTeam"]["id"],
                match_date=datetime.fromisoformat(
                    match["utcDate"].replace("Z", "+00:00")
                ),
                league=match.get("competition", {}).get("name", ""),
                league_id=match.get("competition", {}).get("id"),
                status=status,
                home_score=home_score,
                away_score=away_score,
                round=match.get("matchday"),
                venue=match.get("venue"),
            )
        except Exception as e:
            logger.error(f"解析比赛数据失败: {e}")
            return None

    async def get_teams(self, league_id: Optional[int] = None) -> List[TeamData]:
        """获取球队列表"""
        teams = []

        try:
            if league_id:
                url = f"{self.base_url}/competitions/{league_id}/teams"
            else:
                return []

            async with aiohttp.ClientSession(
                headers=self.headers, timeout=self.timeout
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        for team in data.get("teams", []):
                            team_data = self._parse_team_data(team)
                            if team_data:
                                teams.append(team_data)
                    else:
                        logger.warning(f"获取球队数据失败: {response.status}")

        except Exception as e:
            logger.error(f"获取球队数据失败: {e}")

        return teams

    def _parse_team_data(self, team: Dict) -> Optional[TeamData]:
        """解析球队数据"""
        try:
            return TeamData(
                id=team["id"],
                name=team["name"],
                short_name=team.get("shortName"),
                crest=team.get("crest"),
                founded=team.get("founded"),
                venue=team.get("venue"),
                website=team.get("website"),
            )
        except Exception as e:
            logger.error(f"解析球队数据失败: {e}")
            return None

    async def get_odds(self, match_id: int) -> List[OddsData]:
        """获取赔率数据"""
        # Football-Data.org 的赔率API需要付费订阅
        # 这里返回空列表,实际项目中需要订阅服务
        logger.warning(f"Football-Data.org赔率API需要付费订阅,match_id: {match_id}")
        return []


class MockDataAdapter(DataSourceAdapter):
    """模拟数据适配器 - 用于演示和测试"""

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        super().__init__()

        # 模拟数据
        self.teams = [
            {"id": 1, "name": "Manchester United", "short_name": "MUFC"},
            {"id": 2, "name": "Chelsea", "short_name": "CHE"},
            {"id": 3, "name": "Arsenal", "short_name": "ARS"},
            {"id": 4, "name": "Liverpool", "short_name": "LIV"},
            {"id": 5, "name": "Manchester City", "short_name": "MCI"},
            {"id": 6, "name": "Tottenham", "short_name": "TOT"},
            {"id": 7, "name": "Real Madrid", "short_name": "RMA"},
            {"id": 8, "name": "Barcelona", "short_name": "BAR"},
            {"id": 9, "name": "Bayern Munich", "short_name": "FCB"},
            {"id": 10, "name": "PSG", "short_name": "PSG"},
        ]

    async def get_matches(
        self,
        league_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MatchData]:
        """获取模拟比赛数据"""
        matches = []

        # 生成未来30天的比赛
        base_date = datetime.now()

        for i in range(30):  # 未来30天
            match_date = base_date + timedelta(days=i)

            # 每天生成2-4场比赛
            daily_matches = min(4, max(2, i % 3 + 2))

            for j in range(daily_matches):
                # 随机选择两支球队
                import random

                team1, team2 = random.sample(self.teams, 2)

                # 生成比赛ID
                match_id = i * 100 + j + 1000

                match = MatchData(
                    id=match_id,
                    home_team=team1["name"],
                    away_team=team2["name"],
                    home_team_id=team1["id"],
                    away_team_id=team2["id"],
                    match_date=match_date.replace(
                        hour=15 + i % 6, minute=0
                    ),  # 不同时间
                    league=self._get_random_league(),
                    league_id=random.choice([39, 140, 135, 78, 61]),
                    status="upcoming",
                    venue=f"Stadium {match_id}",
                )
                matches.append(match)

        return matches

    def _get_random_league(self) -> str:
        """获取随机联赛名称"""
        import random

        leagues = ["英超", "西甲", "意甲", "德甲", "法甲", "欧冠"]
        return random.choice(leagues)

    async def get_teams(self, league_id: Optional[int] = None) -> List[TeamData]:
        """获取模拟球队数据"""
        return [
            TeamData(
                id=team["id"],
                name=team["name"],
                short_name=team["short_name"],
                venue=f"Stadium {team['id']}",
                website=f"https://www.{team['short_name'].lower()}.com",
            )
            for team in self.teams
        ]

    async def get_odds(self, match_id: int) -> List[OddsData]:
        """获取模拟赔率数据"""
        import random

        # 生成随机赔率
        home_win = round(random.uniform(1.5, 3.5), 2)
        draw = round(random.uniform(2.8, 4.2), 2)
        away_win = round(random.uniform(1.8, 4.0), 2)

        # 确保赔率合理
        total = 1 / home_win + 1 / draw + 1 / away_win
        margin = 0.05  # 5% 抽水

        if total < (1 - margin):
            # 调整赔率
            home_win = round(1 / ((1 / home_win) * (1 - margin)), 2)
            draw = round(1 / ((1 / draw) * (1 - margin)), 2)
            away_win = round(1 / ((1 / away_win) * (1 - margin)), 2)

        return [
            OddsData(
                match_id=match_id,
                home_win=home_win,
                draw=draw,
                away_win=away_win,
                source="mock_adapter",
                timestamp=datetime.now(),
                over_under=round(random.uniform(2.2, 3.0), 2),
                asian_handicap=round(random.uniform(-1.5, 1.5), 2),
            )
        ]


class EnhancedFootballDataOrgAdapter(DataSourceAdapter):
    """增强版Football-Data.org API适配器"

    支持完整的联赛管理,错误处理,速率限制和数据验证
    """

    def __init__(self, api_key: Optional[str] = None):
    """函数文档字符串"""
    pass  # 添加pass语句
        super().__init__(api_key)
        self.base_url = "https://api.football-data.org/v4"
        if self.api_key:
            self.headers = {"X-Auth-Token": self.api_key}

        # 支持的联赛配置
        self.supported_leagues = {
            39: "Premier League",
            140: "La Liga",
            78: "Bundesliga",
            135: "Serie A",
            61: "Ligue 1",
            2: "Champions League",
            3: "Europa League",
            418: "FA Cup",
            541: "DFB-Pokal",
            525: "Copa del Rey",
            588: "Coppa Italia",
            603: "Coupe de France",
        }

        # 速率限制:10 requests/minute
        self.rate_limit = 10
        self.request_count = 0
        self.last_reset = datetime.now()

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1

    def _check_rate_limit(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """检查速率限制"""
        now = datetime.now()
        if (now - self.last_reset).total_seconds() >= 60:
            self.request_count = 0
            self.last_reset = now

        if self.request_count >= self.rate_limit:
            wait_time = 60 - (now - self.last_reset).total_seconds()
            if wait_time > 0:
                logger.warning(f"达到速率限制,等待 {wait_time:.1f} 秒")
                asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_reset = datetime.now()

    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """安全的API请求,包含重试逻辑"""
        self._check_rate_limit()

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(
                    headers=self.headers, timeout=self.timeout
                ) as session:
                    self.request_count += 1

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            # 速率限制错误
                            retry_after = response.headers.get("Retry-After", "60")
                            wait_time = int(retry_after)
                            logger.warning(f"触发API速率限制,等待 {wait_time} 秒")
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status in [400, 401, 403, 404]:
                            error_text = await response.text()
                            logger.error(f"API请求失败 {response.status}: {error_text}")
                            raise Exception(f"API错误 {response.status}: {error_text}")
                        else:
                            raise Exception(f"未知错误: {response.status}")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"请求失败,{wait_time}秒后重试 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise e

    async def get_competitions(self) -> List[Dict]:
        """获取所有支持的联赛"""
        try:
            url = f"{self.base_url}/competitions"
            data = await self._make_request(url)

            # 过滤支持的联赛
            competitions = [
                comp
                for comp in data.get("competitions", [])
                if comp.get("id") in self.supported_leagues
            ]

            logger.info(f"获取到 {len(competitions)} 个支持的联赛")
            return competitions

        except Exception as e:
            logger.error(f"获取联赛列表失败: {e}")
            return []

    async def get_matches(
        self,
        league_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> List[MatchData]:
        """获取比赛列表,支持多种筛选条件"""
        try:
            # 构建URL
            if league_id:
                url = f"{self.base_url}/competitions/{league_id}/matches"
            else:
                url = f"{self.base_url}/matches"

            # 构建参数
            params = {}
            if date_from:
                params["dateFrom"] = date_from.strftime("%Y-%m-%d")
            if date_to:
                params["dateTo"] = date_to.strftime("%Y-%m-%d")
            if status:
                params["status"] = status

            # 限制返回数量
            params["limit"] = 100

            data = await self._make_request(url, params)
            matches = []

            for match in data.get("matches", []):
                match_data = self._parse_match_data(match)
                if match_data:
                    matches.append(match_data)

            logger.info(f"获取到 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"获取比赛数据失败: {e}")
            return []

    async def get_teams(self, league_id: Optional[int] = None) -> List[TeamData]:
        """获取球队列表"""
        try:
            if not league_id:
                logger.warning("获取球队列表需要指定联赛ID")
                return []

            url = f"{self.base_url}/competitions/{league_id}/teams"
            data = await self._make_request(url)
            teams = []

            for team in data.get("teams", []):
                team_data = self._parse_team_data(team)
                if team_data:
                    teams.append(team_data)

            logger.info(f"获取到 {len(teams)} 支球队")
            return teams

        except Exception as e:
            logger.error(f"获取球队数据失败: {e}")
            return []

    async def get_standings(self, league_id: int) -> List[Dict]:
        """获取联赛积分榜"""
        try:
            url = f"{self.base_url}/competitions/{league_id}/standings"
            data = await self._make_request(url)

            standings = []
            for standing in data.get("standings", []):
                for table in standing.get("table", []):
                    standings.append(table)

            logger.info(f"获取到 {len(standings)} 支球队的积分榜数据")
            return standings

        except Exception as e:
            logger.error(f"获取积分榜失败: {e}")
            return []

    async def get_matches_by_date(self, target_date: datetime) -> List[MatchData]:
        """获取指定日期的所有比赛"""
        date_from = target_date.replace(hour=0, minute=0, second=0)
        date_to = target_date.replace(hour=23, minute=59, second=59)

        return await self.get_matches(date_from=date_from, date_to=date_to)

    async def get_upcoming_matches(self, days: int = 7) -> List[MatchData]:
        """获取未来几天的比赛"""
        date_from = datetime.now()
        date_to = date_from + timedelta(days=days)

        return await self.get_matches(
            date_from=date_from, date_to=date_to, status="SCHEDULED"
        )

    def _parse_match_data(self, match: Dict) -> Optional[MatchData]:
        """解析比赛数据,增强错误处理"""
        try:
            # 验证必要字段
            if not all(
                key in match for key in ["id", "homeTeam", "awayTeam", "utcDate"]
            ):
                logger.warning(f"比赛数据缺少必要字段: {match}")
                return None

            # 解析状态
            status_map = {
                "SCHEDULED": "upcoming",
                "LIVE": "live",
                "IN_PLAY": "live",
                "PAUSED": "live",
                "FINISHED": "finished",
                "POSTPONED": "postponed",
                "SUSPENDED": "postponed",
                "CANCELED": "postponed",
            }

            status = status_map.get(match.get("status", "SCHEDULED"), "upcoming")

            # 解析比分
            home_score = None
            away_score = None
            if status == "finished" and match.get("score"):
                home_score = match["score"].get("fullTime", {}).get("home")
                away_score = match["score"].get("fullTime", {}).get("away")

            # 解析联赛信息
            competition = match.get("competition", {})
            league_name = competition.get("name", "")
            league_id = competition.get("id")

            # 如果是支持的联赛,使用中文名称
            if league_id in self.supported_leagues:
                league_name = self.supported_leagues[league_id]

            return MatchData(
                id=match["id"],
                home_team=match["homeTeam"]["name"],
                away_team=match["awayTeam"]["name"],
                home_team_id=match["homeTeam"]["id"],
                away_team_id=match["awayTeam"]["id"],
                match_date=datetime.fromisoformat(
                    match["utcDate"].replace("Z", "+00:00")
                ),
                league=league_name,
                league_id=league_id,
                status=status,
                home_score=home_score,
                away_score=away_score,
                round=match.get("matchday"),
                venue=match.get("venue"),
            )

        except Exception as e:
            logger.error(f"解析比赛数据失败 (ID: {match.get('id', 'unknown')}): {e}")
            return None

    def _parse_team_data(self, team: Dict) -> Optional[TeamData]:
        """解析球队数据,增强错误处理"""
        try:
            # 验证必要字段
            if not all(key in team for key in ["id", "name"]):
                logger.warning(f"球队数据缺少必要字段: {team}")
                return None

            return TeamData(
                id=team["id"],
                name=team["name"],
                short_name=team.get("short_name"),
                crest=team.get("crest"),
                founded=team.get("founded"),
                venue=team.get("venue"),
                website=team.get("website"),
            )

        except Exception as e:
            logger.error(f"解析球队数据失败 (ID: {team.get('id', 'unknown')}): {e}")
            return None

    async def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            url = f"{self.base_url}/competitions"
            data = await self._make_request(url)
            return bool(data.get("competitions"))
        except Exception as e:
            logger.error(f"API密钥验证失败: {e}")
            return False


class DataSourceManager:
    """类文档字符串"""
    pass  # 添加pass语句
    """数据源管理器"""

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.adapters = {}
        self._initialize_adapters()

    def _initialize_adapters(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """初始化数据源适配器"""

        # 检查API密钥并初始化适配器
        football_api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        if football_api_key:
            try:
                # 优先初始化增强适配器
                enhanced_adapter = EnhancedFootballDataOrgAdapter(football_api_key)
                self.adapters["football_data_org_enhanced"] = enhanced_adapter
                logger.info("Football-Data.org增强适配器初始化成功")

                # 保留原适配器作为备用
                original_adapter = FootballDataOrgAdapter(football_api_key)
                self.adapters["football_data_org"] = original_adapter
                logger.info("Football-Data.org原始适配器初始化成功")
            except Exception as e:
                logger.error(f"Football-Data.org适配器初始化失败: {e}")

        # 检查其他API密钥
        rapidapi_key = os.getenv("RAPIDAPI_KEY")
        if rapidapi_key:
            try:
                # TODO: 实现RapidAPI适配器
                logger.info("RapidAPI适配器暂未实现")
            except Exception as e:
                logger.error(f"RapidAPI适配器初始化失败: {e}")

        # 总是初始化模拟数据适配器作为备用
        self.adapters["mock"] = MockDataAdapter()
        logger.info("模拟数据适配器初始化成功")

    def get_primary_adapter(self) -> DataSourceAdapter:
        """获取主要的数据源适配器"""
        # 优先级:增强适配器 > 原始适配器 > 模拟适配器
        if "football_data_org_enhanced" in self.adapters:
            return self.adapters["football_data_org_enhanced"]
        elif "football_data_org" in self.adapters:
            return self.adapters["football_data_org"]
        else:
            return self.adapters["mock"]

    async def validate_adapters(self) -> Dict[str, bool]:
        """验证所有适配器的可用性"""
        results = {}
        for name, adapter in self.adapters.items():
            try:
                if hasattr(adapter, "validate_api_key"):
                    results[name] = await adapter.validate_api_key()
                else:
                    # 模拟适配器总是可用
                    results[name] = True
                logger.info(f"适配器 {name} 验证结果: {results[name]}")
            except Exception as e:
                results[name] = False
                logger.error(f"适配器 {name} 验证失败: {e}")
        return results

    def get_adapter(self, source_name: str = "mock") -> Optional[DataSourceAdapter]:
        """获取数据源适配器"""
        return self.adapters.get(source_name)

    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        return list(self.adapters.keys())

    async def collect_all_matches(self, days_ahead: int = 30) -> List[MatchData]:
        """从所有可用数据源收集比赛数据"""
        all_matches = []
        date_from = datetime.now()
        date_to = date_from + timedelta(days=days_ahead)

        for source_name, adapter in self.adapters.items():
            try:
                logger.info(f"从数据源 {source_name} 收集比赛数据")
                matches = await adapter.get_matches(
                    date_from=date_from, date_to=date_to
                )
                all_matches.extend(matches)
                logger.info(f"从 {source_name} 收集到 {len(matches)} 场比赛")
            except Exception as e:
                logger.error(f"从数据源 {source_name} 收集数据失败: {e}")

        # 去重（基于比赛ID）
        unique_matches = {}
        for match in all_matches:
            if match.id not in unique_matches:
                unique_matches[match.id] = match

        return list(unique_matches.values())


# 全局数据源管理器实例
data_source_manager = DataSourceManager()
