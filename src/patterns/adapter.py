"""
适配器模式实现

用于集成外部系统和API
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import aiohttp

from src.core.logging import get_logger


@dataclass
class ExternalData:
    """外部数据通用格式"""

    source: str
    data: Any
    timestamp: datetime
    metadata: Dict[str, Any]


class ExternalAPI(ABC):
    """外部API抽象接口"""

    @abstractmethod
    async def fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """获取数据"""
        pass

    @abstractmethod
    async def send_data(self, endpoint: str, data: Any) -> Any:
        """发送数据"""
        pass


class APIAdapter(ABC):
    """API适配器抽象基类"""

    def __init__(self, external_api: ExternalAPI):  # type: ignore
        self.external_api = external_api
        self.logger = get_logger(f"adapter.{self.__class__.__name__}")

    @abstractmethod
    async def get_match_data(self, match_id: int) -> ExternalData:
        """获取比赛数据"""
        pass

    @abstractmethod
    async def get_team_stats(self, team_id: int) -> ExternalData:
        """获取球队统计"""
        pass

    @abstractmethod
    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """转换数据格式"""
        pass


class FootballAPIImpl(ExternalAPI):
    """足球API实现示例"""

    def __init__(self, api_key: str, base_url: str):  # type: ignore
        self.api_key = api_key
        self.base_url = base_url
        self.logger = get_logger("api.football")
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"X-API-Key": self.api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        return self.session

    async def fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """获取数据"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API error: {response.status}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to fetch data from {url}: {str(e)}")
            raise

    async def send_data(self, endpoint: str, data: Any) -> Any:
        """发送数据"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"

        try:
            async with session.post(url, json=data) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    raise Exception(f"API error: {response.status}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to send data to {url}: {str(e)}")
            raise

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()


class WeatherAPIImpl(ExternalAPI):
    """天气API实现示例"""

    def __init__(self, api_key: str, base_url: str):  # type: ignore
        self.api_key = api_key
        self.base_url = base_url
        self.logger = get_logger("api.weather")
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session

    async def fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """获取天气数据"""
        session = await self._get_session()
        params["appid"] = self.api_key
        url = f"{self.base_url}/{endpoint}"

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Weather API error: {response.status}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to fetch weather data: {str(e)}")
            raise

    async def send_data(self, endpoint: str, data: Any) -> Any:
        """天气API通常不需要发送数据"""
        raise NotImplementedError("Weather API does not support sending data")

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()


class OddsAPIImpl(ExternalAPI):
    """赔率API实现示例"""

    def __init__(self, api_key: str, base_url: str):  # type: ignore
        self.api_key = api_key
        self.base_url = base_url
        self.logger = get_logger("api.odds")
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"X-API-Key": self.api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        return self.session

    async def fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """获取赔率数据"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Odds API error: {response.status}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to fetch odds data: {str(e)}")
            raise

    async def send_data(self, endpoint: str, data: Any) -> Any:
        """发送赔率数据"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"

        try:
            async with session.post(url, json=data) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    raise Exception(f"Odds API error: {response.status}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to send odds data: {str(e)}")
            raise

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()


class FootballApiAdapter(APIAdapter):
    """足球API适配器"""

    async def get_match_data(self, match_id: int) -> ExternalData:
        """获取比赛数据"""
        try:
            raw_data = await self.external_api.fetch_data("matches", {"id": match_id})
            transformed_data = self.transform_data(raw_data)

            return ExternalData(
                source="football_api",
                data=transformed_data,
                timestamp=datetime.now(),
                metadata={"match_id": match_id, "original_format": "json"},
            )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to get match data for {match_id}: {str(e)}")
            raise

    async def get_team_stats(self, team_id: int) -> ExternalData:
        """获取球队统计"""
        try:
            raw_data = await self.external_api.fetch_data(
                "teams/stats", {"team": team_id}
            )
            transformed_data = self.transform_data(raw_data)

            return ExternalData(
                source="football_api",
                data=transformed_data,
                timestamp=datetime.now(),
                metadata={"team_id": team_id, "original_format": "json"},
            )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to get team stats for {team_id}: {str(e)}")
            raise

    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """转换足球数据格式"""
        if isinstance(raw_data, dict):
            return {
                "id": raw_data.get("id"),
                "name": raw_data.get("name"),
                "home_team": raw_data.get("homeTeam"),
                "away_team": raw_data.get("awayTeam"),
                "score": {
                    "home": raw_data.get("score", {}).get("fullTime", {}).get("home"),
                    "away": raw_data.get("score", {}).get("fullTime", {}).get("away"),
                },
                "status": raw_data.get("status"),
                "competition": raw_data.get("competition"),
                "last_updated": raw_data.get("lastUpdated"),
            }
        return {}


class WeatherApiAdapter(APIAdapter):
    """天气API适配器"""

    async def get_weather_data(self, location: str, date: datetime) -> ExternalData:
        """获取天气数据"""
        try:
            raw_data = await self.external_api.fetch_data(
                "weather", {"q": location, "dt": int(date.timestamp())}
            )
            transformed_data = self.transform_data(raw_data)

            return ExternalData(
                source="weather_api",
                data=transformed_data,
                timestamp=datetime.now(),
                metadata={"location": location, "date": date.isoformat()},
            )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to get weather data for {location}: {str(e)}")
            raise

    async def get_match_data(self, match_id: int) -> ExternalData:
        """不适用"""
        raise NotImplementedError("Weather API does not provide match data")

    async def get_team_stats(self, team_id: int) -> ExternalData:
        """不适用"""
        raise NotImplementedError("Weather API does not provide team stats")

    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """转换天气数据格式"""
        if isinstance(raw_data, dict):
            main = raw_data.get("main", {})
            weather = raw_data.get("weather", [{}])[0]
            wind = raw_data.get("wind", {})
            rain = raw_data.get("rain", {})

            return {
                "temperature": {
                    "current": main.get("temp"),
                    "feels_like": main.get("feels_like"),
                    "min": main.get("temp_min"),
                    "max": main.get("temp_max"),
                },
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),
                "weather": {
                    "main": weather.get("main"),
                    "description": weather.get("description"),
                },
                "wind": {"speed": wind.get("speed"), "direction": wind.get("deg")},
                "rain": rain.get("1h", 0),
                "visibility": raw_data.get("visibility"),
                "clouds": raw_data.get("clouds", {}).get("all"),
            }
        return {}


class OddsApiAdapter(APIAdapter):
    """赔率API适配器"""

    async def get_match_odds(self, match_id: int) -> ExternalData:
        """获取比赛赔率"""
        try:
            raw_data = await self.external_api.fetch_data("odds", {"match": match_id})
            transformed_data = self.transform_data(raw_data)

            return ExternalData(
                source="odds_api",
                data=transformed_data,
                timestamp=datetime.now(),
                metadata={"match_id": match_id, "original_format": "json"},
            )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to get match odds for {match_id}: {str(e)}")
            raise

    async def get_match_data(self, match_id: int) -> ExternalData:
        """不适用"""
        raise NotImplementedError("Odds API does not provide match data")

    async def get_team_stats(self, team_id: int) -> ExternalData:
        """不适用"""
        raise NotImplementedError("Odds API does not provide team stats")

    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """转换赔率数据格式"""
        if isinstance(raw_data, dict):
            bookmakers = raw_data.get("bookmakers", [])
            odds_data = {}

            for bookmaker in bookmakers:
                bookmaker_name = bookmaker.get("title")
                odds_data[bookmaker_name] = {}

                for market in bookmaker.get("markets", []):
                    market_name = market.get("key")
                    odds_data[bookmaker_name][market_name] = {}

                    for outcome in market.get("outcomes", []):
                        outcome_name = outcome.get("name")
                        odds_data[bookmaker_name][market_name][outcome_name] = {
                            "price": outcome.get("price"),
                            "last_update": outcome.get("last_update"),
                        }

            return {
                "match_id": raw_data.get("id"),
                "sport": raw_data.get("sport_key"),
                "commence_time": raw_data.get("commence_time"),
                "home_team": raw_data.get("home_team"),
                "away_team": raw_data.get("away_team"),
                "bookmakers": odds_data,
            }
        return {}


class AdapterFactory:
    """适配器工厂"""

    _adapters: Dict[str, type] = {
        "football": FootballApiAdapter,
        "weather": WeatherApiAdapter,
        "odds": OddsApiAdapter,
    }

    @classmethod
    def create_adapter(cls, adapter_type: str, external_api: ExternalAPI) -> APIAdapter:
        """创建适配器"""
        if adapter_type not in cls._adapters:
            raise ValueError(f"Unknown adapter type: {adapter_type}")

        return cls._adapters[adapter_type](external_api)

    @classmethod
    def register_adapter(cls, adapter_type: str, adapter_class: type):  # type: ignore
        """注册新的适配器类型"""
        cls._adapters[adapter_type] = adapter_class


class UnifiedDataCollector:
    """统一数据收集器"""

    def __init__(self):  # type: ignore
        self.adapters: Dict[str, APIAdapter] = {}
        self.logger = get_logger("collector.unified")

    def add_adapter(self, name: str, adapter: APIAdapter):  # type: ignore
        """添加适配器"""
        self.adapters[name] = adapter
        self.logger.info(f"Added adapter: {name}")

    async def collect_match_data(self, match_id: int) -> Dict[str, ExternalData]:
        """收集所有适配器的比赛数据"""
        results = {}

        tasks = []
        adapter_names = []

        for name, adapter in self.adapters.items():
            if isinstance(adapter, FootballApiAdapter):
                tasks.append(adapter.get_match_data(match_id))
                adapter_names.append(name)
            elif isinstance(adapter, OddsApiAdapter):
                tasks.append(adapter.get_match_odds(match_id))
                adapter_names.append(name)

        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for name, response in zip(adapter_names, responses):
                if isinstance(response, Exception):
                    self.logger.error(f"Failed to collect from {name}: {str(response)}")
                else:
                    results[name] = response

        return results

    async def collect_team_stats(self, team_id: int) -> Dict[str, ExternalData]:
        """收集球队统计"""
        results = {}

        for name, adapter in self.adapters.items():
            if isinstance(adapter, FootballApiAdapter):
                try:
                    data = await adapter.get_team_stats(team_id)
                    results[name] = data
                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    self.logger.error(
                        f"Failed to collect team stats from {name}: {str(e)}"
                    )

        return results

    async def collect_weather_data(
        self, location: str, date: datetime
    ) -> Optional[ExternalData]:
        """收集天气数据"""
        for name, adapter in self.adapters.items():
            if isinstance(adapter, WeatherApiAdapter):
                try:
                    return await adapter.get_weather_data(location, date)
                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    self.logger.error(
                        f"Failed to collect weather from {name}: {str(e)}"
                    )

        return None

    async def close_all(self):
        """关闭所有适配器"""
        for adapter in self.adapters.values():
            if hasattr(adapter.external_api, "close"):
                await adapter.external_api.close()


# 示例使用
async def example_usage():
    """示例使用"""
    # 创建API实现
    football_api = FootballAPIImpl("key123", "https://api.football.com/v4")
    weather_api = WeatherAPIImpl("key456", "https://api.openweathermap.org/data/2.5")
    odds_api = OddsAPIImpl("key789", "https://api.the-odds-api.com/v4")

    # 创建适配器
    football_adapter = AdapterFactory.create_adapter("football", football_api)
    weather_adapter = AdapterFactory.create_adapter("weather", weather_api)
    odds_adapter = AdapterFactory.create_adapter("odds", odds_api)

    # 创建统一收集器
    collector = UnifiedDataCollector()
    collector.add_adapter("football", football_adapter)
    collector.add_adapter("weather", weather_adapter)
    collector.add_adapter("odds", odds_adapter)

    # 收集数据
    match_data = await collector.collect_match_data(12345)
    weather_data = await collector.collect_weather_data("London", datetime.now())

    logger.info(f"Match data: {match_data}")
    logger.info(f"Weather data: {weather_data}")

    # 清理
    await collector.close_all()
