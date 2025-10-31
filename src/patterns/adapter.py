"""
适配器模式实现
Adapter Pattern Implementation

提供统一的数据接口适配功能，用于整合不同外部API和数据源.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExternalData:
    """外部数据结构"""
    source: str
    data: Dict[str, Any]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ExternalAPI(ABC):
    """外部API抽象基类"""

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.is_connected = False
        self.last_error: Optional[str] = None

    @abstractmethod
    async def connect(self) -> bool:
        """连接到外部API"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> ExternalData:
        """获取数据"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass


class APIAdapter(ExternalAPI):
    """API适配器基类"""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        super().__init__(name, base_url)
        self.api_key = api_key
        self.rate_limit = 100  # 每分钟请求数
        self.timeout = 30  # 超时时间（秒）

    async def connect(self) -> bool:
        """连接到API"""
        try:
            # 模拟连接逻辑
            await asyncio.sleep(0.1)
            self.is_connected = True
            logger.info(f"Connected to {self.name}")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to connect to {self.name}: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        self.is_connected = False
        logger.info(f"Disconnected from {self.name}")

    async def health_check(self) -> bool:
        """健康检查"""
        if not self.is_connected:
            return await self.connect()
        return True


class FootballApiAdapter(APIAdapter):
    """足球API适配器"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__("football_api", base_url, api_key)

    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> ExternalData:
        """获取足球数据"""
        if not self.is_connected:
            await self.connect()

        # 模拟获取足球数据
        await asyncio.sleep(0.1)

        mock_data = {
            "matches": [
                {"id": 1, "home": "Team A", "away": "Team B", "score": "2-1"},
                {"id": 2, "home": "Team C", "away": "Team D", "score": "1-1"}
            ],
            "teams": [
                {"id": 1, "name": "Team A", "league": "Premier League"},
                {"id": 2, "name": "Team B", "league": "Premier League"}
            ]
        }

        return ExternalData(
            source=self.name,
            data=mock_data,
            timestamp=datetime.utcnow(),
            metadata={"endpoint": endpoint, "params": params}
        )


class WeatherApiAdapter(APIAdapter):
    """天气API适配器"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__("weather_api", base_url, api_key)

    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> ExternalData:
        """获取天气数据"""
        if not self.is_connected:
            await self.connect()

        # 模拟获取天气数据
        await asyncio.sleep(0.1)

        mock_data = {
            "temperature": 22,
            "humidity": 65,
            "condition": "partly_cloudy",
            "wind_speed": 15,
            "location": params.get("location", "Unknown") if params else "Unknown"
        }

        return ExternalData(
            source=self.name,
            data=mock_data,
            timestamp=datetime.utcnow(),
            metadata={"endpoint": endpoint, "params": params}
        )


class OddsApiAdapter(APIAdapter):
    """赔率API适配器"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__("odds_api", base_url, api_key)

    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> ExternalData:
        """获取赔率数据"""
        if not self.is_connected:
            await self.connect()

        # 模拟获取赔率数据
        await asyncio.sleep(0.1)

        mock_data = {
            "odds": [
                {"match_id": 1, "home_win": 2.1, "draw": 3.2, "away_win": 3.8},
                {"match_id": 2, "home_win": 1.8, "draw": 3.5, "away_win": 4.2}
            ],
            "bookmakers": ["Bookmaker A", "Bookmaker B"]
        }

        return ExternalData(
            source=self.name,
            data=mock_data,
            timestamp=datetime.utcnow(),
            metadata={"endpoint": endpoint, "params": params}
        )


class UnifiedDataCollector:
    """统一数据收集器"""

    def __init__(self):
        self.adapters: Dict[str, APIAdapter] = {}
        self.is_initialized = False

    def register_adapter(self, adapter: APIAdapter):
        """注册适配器"""
        self.adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name}")

    def unregister_adapter(self, name: str):
        """注销适配器"""
        if name in self.adapters:
            del self.adapters[name]
            logger.info(f"Unregistered adapter: {name}")

    async def initialize_all(self):
        """初始化所有适配器"""
        tasks = []
        for adapter in self.adapters.values():
            tasks.append(adapter.connect())

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for result in results if result is True)
            logger.info(f"Initialized {success_count}/{len(tasks)} adapters")

        self.is_initialized = True

    async def shutdown_all(self):
        """关闭所有适配器"""
        tasks = []
        for adapter in self.adapters.values():
            tasks.append(adapter.disconnect())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Shutdown all adapters")

    async def collect_all_data(self, endpoint: str, params: Optional[Dict] = None) -> List[ExternalData]:
        """从所有适配器收集数据"""
        if not self.is_initialized:
            await self.initialize_all()

        tasks = []
        for adapter in self.adapters.values():
            try:
                tasks.append(adapter.fetch_data(endpoint, params))
            except Exception as e:
                logger.error(f"Error preparing fetch for {adapter.name}: {e}")

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        collected_data = []
        for result in results:
            if isinstance(result, ExternalData):
                collected_data.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error collecting data: {result}")

        return collected_data

    async def get_health_status(self) -> Dict[str, bool]:
        """获取所有适配器的健康状态"""
        tasks = []
        for name, adapter in self.adapters.items():
            tasks.append((name, adapter.health_check()))

        results = {}
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False

        return results


class AdapterFactory:
    """适配器工厂类"""

    @staticmethod
    def create_football_adapter(base_url: str, api_key: Optional[str] = None) -> FootballApiAdapter:
        """创建足球API适配器"""
        return FootballApiAdapter(base_url, api_key)

    @staticmethod
    def create_weather_adapter(base_url: str, api_key: Optional[str] = None) -> WeatherApiAdapter:
        """创建天气API适配器"""
        return WeatherApiAdapter(base_url, api_key)

    @staticmethod
    def create_odds_adapter(base_url: str, api_key: Optional[str] = None) -> OddsApiAdapter:
        """创建赔率API适配器"""
        return OddsApiAdapter(base_url, api_key)

    @staticmethod
    def create_unified_collector() -> UnifiedDataCollector:
        """创建统一数据收集器"""
        return UnifiedDataCollector()

    @staticmethod
    def create_adapter(adapter_type: str, base_url: str, api_key: Optional[str] = None) -> APIAdapter:
        """根据类型创建适配器"""
        adapter_map = {
            "football": AdapterFactory.create_football_adapter,
            "weather": AdapterFactory.create_weather_adapter,
            "odds": AdapterFactory.create_odds_adapter,
        }

        if adapter_type not in adapter_map:
            raise ValueError(f"Unknown adapter type: {adapter_type}")

        return adapter_map[adapter_type](base_url, api_key)

    @classmethod
    def create_standard_setup(cls, config: Dict[str, Any]) -> UnifiedDataCollector:
        """创建标准设置"""
        collector = cls.create_unified_collector()

        # 注册足球适配器
        if "football_api" in config:
            football_config = config["football_api"]
            football_adapter = cls.create_football_adapter(
                football_config["base_url"],
                football_config.get("api_key")
            )
            collector.register_adapter(football_adapter)

        # 注册天气适配器
        if "weather_api" in config:
            weather_config = config["weather_api"]
            weather_adapter = cls.create_weather_adapter(
                weather_config["base_url"],
                weather_config.get("api_key")
            )
            collector.register_adapter(weather_adapter)

        # 注册赔率适配器
        if "odds_api" in config:
            odds_config = config["odds_api"]
            odds_adapter = cls.create_odds_adapter(
                odds_config["base_url"],
                odds_config.get("api_key")
            )
            collector.register_adapter(odds_adapter)

        return collector


# 导出的公共接口
__all__ = [
    "ExternalData",
    "ExternalAPI",
    "APIAdapter",
    "FootballApiAdapter",
    "WeatherApiAdapter",
    "OddsApiAdapter",
    "UnifiedDataCollector",
    "AdapterFactory"
]
