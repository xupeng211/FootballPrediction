from typing import Any, Dict, List, Optional, Union
"""
足球API适配器
Football API Adapters

集成各种足球数据API。
Integrate various football data APIs.
"""

import asyncio
import aiohttp
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .base import Adapter, AdapterStatus, Adaptee, Target
from src.core.exceptions import AdapterError


class MatchStatus(Enum):
    """比赛状态"""

    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


@dataclass
class FootballMatch:
    """足球比赛数据模型"""

    id: str
    home_team: str
    away_team: str
    competition: str
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    competition_id: Optional[str] = None
    match_date: Optional[datetime] = None
    status: Optional[MatchStatus] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None
    weather: Optional[Dict[str, Any]] = None
@dataclass
class FootballTeam:
    """足球队数据模型"""

    id: str
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    stadium: Optional[str] = None
    logo_url: Optional[str] = None
@dataclass
class FootballPlayer:
    """足球运动员数据模型"""

    id: str
    name: str
    team_id: str
    position: Optional[str] = None
    age: Optional[int] = None
    nationality: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    photo_url: Optional[str] = None
class FootballApiAdaptee(Adaptee):
    """足球API被适配者基类"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    async def initialize(self) -> None:
        """初始化HTTP会话"""
        self.session = aiohttp.ClientSession()

    async def cleanup(self) -> None:
        """清理HTTP会话"""
        if self.session:
            await self.session.close()

    async def get_data(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取API数据"""
        if not self.session:
            raise RuntimeError("Adapter not initialized")

        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()

        async with self.session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            return await response.json()  # type: ignore

    async def send_data(self, data: Any) -> Any:
        """发送数据（足球API通常只读）"""
        raise NotImplementedError("Football APIs are typically read-only")

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "X-Auth-Token": self.api_key,
            "Content-Type[Any]": "application/json",
        }


class ApiFootballAdaptee(FootballApiAdaptee):
    """API-Football被适配者"""

    def __init__(self, api_key: str):
        super().__init__(api_key, "https://v3.football.api-sports.io")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-apisports-key": self.api_key,
            "x-apisports-host": "v3.football.api-sports.io",
        }


class OptaDataAdaptee(FootballApiAdaptee):
    """Opta数据被适配者"""

    def __init__(self, api_key: str, customer_id: str):
        super().__init__(api_key, "https://api.optasports.com")
        self.customer_id = customer_id

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-Auth-Token": self.api_key,
            "X-Customer-ID": self.customer_id,
            "Content-Type[Any]": "application/json",
        }


class FootballDataTransformer:
    """足球数据转换器"""

    def __init__(self, source_format: str):
        self.source_format = source_format

    async def transform(self, data: Any, target_type: str = "match", **kwargs) -> Any:
        """转换数据格式"""
        if target_type == "match":
            return await self._transform_match(data)
        elif target_type == "team":
            return await self._transform_team(data)
        elif target_type == "player":
            return await self._transform_player(data)
        else:
            raise ValueError(f"Unknown target type: {target_type}")

    async def _transform_match(self, data: Dict[str, Any]) -> FootballMatch:
        """转换比赛数据"""
        if self.source_format == "api-football":
            return FootballMatch(
                id=str(data["fixture"]["id"]),
                home_team=data["teams"]["home"]["name"],
                away_team=data["teams"]["away"]["name"],
                home_team_id=str(data["teams"]["home"]["id"]),
                away_team_id=str(data["teams"]["away"]["id"]),
                competition=data["league"]["name"],
                competition_id=str(data["league"]["id"]),
                match_date=datetime.fromisoformat(data["fixture"]["date"]),
                status=MatchStatus(data["fixture"]["status"]["short"]),
                home_score=data["goals"]["home"],
                away_score=data["goals"]["away"],
                venue=data["fixture"]["venue"]["name"]
                if data["fixture"]["venue"]
                else None,
            )
        elif self.source_format == "opta":
            # Opta格式转换逻辑
            return FootballMatch(
                id=str(data["match_id"]),
                home_team=data["home_team"]["name"],
                away_team=data["away_team"]["name"],
                home_team_id=str(data["home_team"]["id"]),
                away_team_id=str(data["away_team"]["id"]),
                competition=data["competition"]["name"],
                competition_id=str(data["competition"]["id"]),
                match_date=datetime.fromisoformat(data["date"]),
                status=MatchStatus(data["status"]),
                home_score=data.get("score", {}).get("home"),
                away_score=data.get("score", {}).get("away"),
            )
        else:
            raise ValueError(f"Unknown source format: {self.source_format}")

    async def _transform_team(self, data: Dict[str, Any]) -> FootballTeam:
        """转换球队数据"""
        if self.source_format == "api-football":
            return FootballTeam(
                id=str(data["team"]["id"]),
                name=data["team"]["name"],
                short_name=data["team"].get("shortName"),
                country=data["team"]["country"],
                founded=data["team"].get("founded"),
                stadium=data["venue"].get("name") if data.get("venue") else None,
                logo_url=data["team"].get("logo"),
            )
        else:
            raise ValueError(f"Unknown source format: {self.source_format}")

    async def _transform_player(self, data: Dict[str, Any]) -> FootballPlayer:
        """转换球员数据"""
        if self.source_format == "api-football":
            return FootballPlayer(
                id=str(data["player"]["id"]),
                name=data["player"]["name"],
                team_id=str(data["statistics"][0]["team"]["id"]),
                position=data["statistics"][0]["games"].get("position"),
                age=data["player"]["age"],
                nationality=data["player"]["nationality"],
                height=data["player"].get("height"),
                weight=data["player"].get("weight"),
                photo_url=data["player"].get("photo"),
            )
        else:
            raise ValueError(f"Unknown source format: {self.source_format}")

    def get_source_schema(self) -> Dict[str, Any]:
        """获取源数据结构"""
        if self.source_format == "api-football":
            return {
                "fixture": {
                    "id": "int",
                    "date": "datetime",
                    "status": "object",
                    "venue": "object",
                },
                "teams": {
                    "home": "object",
                    "away": "object",
                },
                "goals": {
                    "home": "int",
                    "away": "int",
                },
            }
        else:
            return {}

    def get_target_schema(self) -> Dict[str, Any]:
        """获取目标数据结构"""
        return {
            "id": "str",
            "home_team": "str",
            "away_team": "str",
            "home_team_id": "str",
            "away_team_id": "str",
            "competition": "str",
            "competition_id": "str",
            "match_date": "datetime",
            "status": "MatchStatus",
            "home_score": "int",
            "away_score": "int",
            "venue": "str",
        }


class FootballApiAdapter(Adapter):
    """足球API适配器基类"""

    def __init__(self, adaptee: FootballApiAdaptee, transformer: Optional['FootballDataTransformer'] = None):
        super().__init__(adaptee)
        self.transformer = transformer

    async def _initialize(self) -> None:
        """初始化适配器"""
        await self.adaptee.initialize()  # type: ignore

    async def _cleanup(self) -> None:
        """清理适配器"""
        await self.adaptee.cleanup()  # type: ignore

    async def get_matches(
        self,
        date: Optional[datetime] = None,
        league_id: Optional[str] = None,
        team_id: Optional[str] = None,
        live: bool = False,
    ) -> List[FootballMatch]:
        """获取比赛列表"""
        params = {}
        if date:
            params["date"] = date.strftime("%Y-%m-%d")
        if league_id:
            params["league"] = league_id
        if team_id:
            params["team"] = team_id
        if live:
            params["live"] = "all"

        endpoint = "fixtures"
        _data = await self.adaptee.get_data(endpoint, params)

        # 转换数据
        _matches = []
        for match_data in data.get("response", []):
            match = await self.transformer.transform(match_data, target_type="match")
            matches.append(match)

        return matches

    async def get_match(self, match_id: str) -> Optional[FootballMatch]:
        """获取单个比赛"""
        endpoint = f"fixtures?id={match_id}"
        _data = await self.adaptee.get_data(endpoint)

        if data.get("response"):
            match_data = data["response"][0]
            return await self.transformer.transform(match_data, target_type="match")  # type: ignore
        return None

    async def get_teams(self, league_id: Optional[str] = None) -> List[FootballTeam]:
        """获取球队列表"""
        params = {}
        if league_id:
            params["league"] = league_id

        endpoint = "teams"
        _data = await self.adaptee.get_data(endpoint, params)

        _teams = []
        for team_data in data.get("response", []):
            team = await self.transformer.transform(team_data, target_type="team")
            teams.append(team)

        return teams

    async def get_team(self, team_id: str) -> Optional[FootballTeam]:
        """获取单个球队"""
        endpoint = f"teams?id={team_id}"
        _data = await self.adaptee.get_data(endpoint)

        if data.get("response"):
            team_data = data["response"][0]
            return await self.transformer.transform(team_data, target_type="team")  # type: ignore
        return None

    async def get_players(
        self, team_id: str, season: Optional[str] = None
    ) -> List[FootballPlayer]:
        """获取球员列表"""
        params = {}
        if season:
            params["season"] = season

        endpoint = f"players/squads?team={team_id}"
        _data = await self.adaptee.get_data(endpoint, params)

        players = []
        for player_data in data.get("response", []):
            # 获取球员详细信息
            player_detail = await self.get_player(player_data["player"]["id"])
            if player_detail:
                players.append(player_detail)

        return players

    async def get_player(self, player_id: str) -> Optional[FootballPlayer]:
        """获取单个球员"""
        endpoint = f"players?id={player_id}&season=2023"
        _data = await self.adaptee.get_data(endpoint)

        if _data.get("response"):
            player_data = _data["response"][0]
            return await self.transformer.transform(player_data, target_type="player")  # type: ignore
        return None

    async def get_standings(self, league_id: str, season: str) -> List[Dict[str, Any]]:
        """获取积分榜"""
        params = {"league": league_id, "season": season}
        endpoint = "standings"
        _data = await self.adaptee.get_data(endpoint, params)
        return data.get("response", [])  # type: ignore

    async def _request(self, *args, **kwargs) -> Any:
        """处理请求"""
        # 根据参数调用相应的方法
        if args and args[0] == "matches":
            return await self.get_matches(**kwargs)
        elif args and args[0] == "teams":
            return await self.get_teams(**kwargs)
        else:
            raise ValueError(f"Unknown request: {args}")


class ApiFootballAdapter(FootballApiAdapter):
    """API-Football适配器"""

    def __init__(self, api_key: str):
        adaptee = ApiFootballAdaptee(api_key)
        transformer = FootballDataTransformer("api-football")
        super().__init__(adaptee, transformer)


class OptaDataAdapter(FootballApiAdapter):
    """Opta数据适配器"""

    def __init__(self, api_key: str, customer_id: str):
        adaptee = OptaDataAdaptee(api_key, customer_id)
        transformer = FootballDataTransformer("opta")
        super().__init__(adaptee, transformer)


class CompositeFootballAdapter(Adapter):
    """复合适配器，集成多个足球数据源"""

    def __init__(self):
        super().__init__(None, "CompositeFootballAdapter")
        self.adapters: List[FootballApiAdapter] = []
        self.primary_source: Optional[FootballApiAdapter] = None
    def add_adapter(
        self, adapter: FootballApiAdapter, is_primary: bool = False
    ) -> None:
        """添加适配器"""
        self.adapters.append(adapter)
        if is_primary or not self.primary_source:
            self.primary_source = adapter

    async def _initialize(self) -> None:
        """初始化所有适配器"""
        for adapter in self.adapters:
            await adapter.initialize()

    async def _cleanup(self) -> None:
        """清理所有适配器"""
        for adapter in self.adapters:
            await adapter.cleanup()

    async def _request(self, *args, **kwargs) -> Any:
        """使用主数据源，失败时使用备用源"""
        if not self.adapters:
            raise RuntimeError("No adapters configured")

        # 先尝试主数据源
        if self.primary_source and self.primary_source.status == AdapterStatus.ACTIVE:
            try:
                return await self.primary_source._request(*args, **kwargs)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
                pass

        # 尝试其他数据源
        for adapter in self.adapters:
            if (
                adapter != self.primary_source
                and adapter.status == AdapterStatus.ACTIVE
            ):
                try:
                    return await adapter._request(*args, **kwargs)
                except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
                    continue

        raise RuntimeError("All football data sources failed")

    async def get_matches_aggregated(
        self,
        date: Optional[datetime] = None,
        league_id: Optional[str] = None,
    ) -> Dict[str, List[FootballMatch]]:
        """从多个数据源聚合比赛数据"""
        results = {}
        tasks = []

        for adapter in self.adapters:
            if adapter.status == AdapterStatus.ACTIVE:
                task = asyncio.create_task(
                    adapter.get_matches(date=date, league_id=league_id)
                )
                tasks.append((adapter.name, task))

        for name, task in tasks:
            try:
                _matches = await task
                results[name] = matches
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                results[name] = f"Error: {str(e)}"

        return results


class FootballDataAdapter:
    """足球数据适配器（简化版用于测试）"""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self.initialized = False
        self.client = None

    async def initialize(self):
        """初始化适配器"""
        self.initialized = True

    async def get_match_data(self, match_id: int, **kwargs) -> Dict[str, Any]:
        """获取比赛数据"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(f"/matches/{match_id}")  # type: ignore
        return {"matches": [{"id": match_id}]}

    async def get_team_data(self, team_id: int, **kwargs) -> Dict[str, Any]:
        """获取队伍数据"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(f"/teams/{team_id}")  # type: ignore
        return {"id": team_id, "name": f"Team {team_id}"}

    async def get_league_data(self, league_id: int, **kwargs) -> Dict[str, Any]:
        """获取联赛数据"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(f"/competitions/{league_id}")  # type: ignore
        return {"id": league_id, "name": f"League {league_id}"}

    async def get_player_data(self, player_id: int, **kwargs) -> Dict[str, Any]:
        """获取球员数据"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(f"/players/{player_id}")  # type: ignore
        return {"id": player_id, "name": f"Player {player_id}"}

    async def search_teams(self, name: str, **kwargs) -> Dict[str, Any]:
        """搜索队伍"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(f"/teams?name={name}")  # type: ignore
        return {"teams": [{"name": f"{name} Team"}]}

    async def get_upcoming_matches(self, team_id: int, **kwargs) -> Dict[str, Any]:
        """获取即将到来的比赛"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(f"/teams/{team_id}/matches?status=SCHEDULED")  # type: ignore
        return {"matches": [{"status": "SCHEDULED"}]}

    async def get_historical_matches(
        self, team_id: int, limit: int = 10, **kwargs
    ) -> Dict[str, Any]:
        """获取历史比赛"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(  # type: ignore
                f"/teams/{team_id}/matches?status=FINISHED&limit={limit}"
            )
        return {"matches": [{"status": "FINISHED"}]}

    async def get_standings(
        self, league_id: int, season: int, **kwargs
    ) -> Dict[str, Any]:
        """获取积分榜"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(  # type: ignore
                f"/competitions/{league_id}/standings?season={season}"
            )
        return {"standings": [{"table": []}]}

    async def get_top_scorers(
        self, league_id: int, season: int, limit: int = 10, **kwargs
    ) -> Dict[str, Any]:
        """获取射手榜"""
        if not self.initialized:
            raise AdapterError("Adapter not initialized")
        if self.client:
            return await self.client.get(  # type: ignore
                f"/competitions/{league_id}/scorers?season={season}&limit={limit}"
            )
        return {"scorers": []}

    async def batch_get_matches(self, match_ids: List[int]) -> List[Dict[str, Any]]:
        """批量获取比赛"""
        results = []
        for match_id in match_ids:
            _result = await self.get_match_data(match_id)
            results.append(result)
        return results

    async def close(self):
        """关闭适配器"""
        self.initialized = False
        if self.client:
            await self.client.close()

    def _build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """构建URL"""
        if params:
            query_str = "&".join([f"{k}={v}" for k, v in params.items()])
            return f"{path}?{query_str}"
        return path

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期"""
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """验证响应"""
        return "status" in response or "data" in response or "matches" in response
