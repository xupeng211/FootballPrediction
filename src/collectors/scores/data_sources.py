"""
数据源
Data Sources

定义各种比分数据源的接口和实现。
"""




logger = __import__("logging").getLogger(__name__)


class BaseScoreSource(ABC):
    """比分数据源基类"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化数据源

        Args:
            api_key: API密钥
        """
        self.api_key = api_key

    @abstractmethod
    async def fetch_match_score(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛比分

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]]: 比分数据
        """
        pass

    @abstractmethod
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换数据格式

        Args:
            data: 原始数据

        Returns:
            Dict[str, Any]: 转换后的数据
        """
        pass


class FootballAPISource(BaseScoreSource):
    """Football-Data API 数据源"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = os.getenv(
            "FOOTBALL_API_URL", "https://api.football-data.org/v4"
        )

    @retry(lambda: None)
    async def fetch_match_score(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从Football-Data API获取比分"""
        if not self.api_key:
            logger.warning("Football API密钥未配置")
            return None

        url = f"{self.base_url}/matches/{match_id}"
        headers = {"X-Auth-Token": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.transform_data(data)
                    else:
                        logger.warning(f"Football API请求失败: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"从Football API获取数据失败: {e}")
            return None

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换Football API数据格式"""
        match = data.get("match", {})
        score = match.get("score", {})

        return {
            "match_id": match.get("id"),
            "home_score": score.get("fullTime", {}).get("home", 0),
            "away_score": score.get("fullTime", {}).get("away", 0),
            "home_half_score": score.get("halfTime", {}).get("home", 0),
            "away_half_score": score.get("halfTime", {}).get("away", 0),
            "match_time": match.get("utcDate"),
            "match_status": match.get("status"),
            "last_updated": utc_now().isoformat(),
            "events": [],  # 可从其他端点获取
        }


class ApiSportsSource(BaseScoreSource):
    """API-Sports 数据源"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = os.getenv(
            "API_SPORTS_URL", "https://v3.football.api-sports.io"
        )

    @retry(lambda: None)
    async def fetch_match_score(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从API-Sports获取比分"""
        if not self.api_key:
            logger.warning("API-Sports密钥未配置")
            return None

        url = f"{self.base_url}/fixtures?id={match_id}&live=all"
        headers = {"x-apisports-key": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("response"):
                            return self.transform_data(data["response"][0])
                        return None
                    else:
                        logger.warning(f"API-Sports请求失败: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"从API-Sports获取数据失败: {e}")
            return None

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换API-Sports数据格式"""
        return {
            "match_id": data.get("fixture", {}).get("id"),
            "home_score": data.get("goals", {}).get("home", 0),
            "away_score": data.get("goals", {}).get("away", 0),
            "home_half_score": data.get("score", {}).get("halftime", {}).get("home", 0),
            "away_half_score": data.get("score", {}).get("halftime", {}).get("away", 0),
            "match_time": data.get("fixture", {}).get("date"),
            "match_status": data.get("fixture", {}).get("status", {}).get("long"),
            "last_updated": utc_now().isoformat(),
            "events": data.get("events", []),
        }


class ScorebatSource(BaseScoreSource):
    """Scorebat 数据源（主要用于视频）"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = os.getenv(
            "SCOREBAT_URL", "https://www.scorebat.com/video/api/v1"
        )

    async def fetch_match_score(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从Scorebat获取比分（简化实现）"""
        # Scorebat主要提供视频，这里作为备用数据源
        logger.debug("Scorebat数据源暂不实现比分获取")
        return None

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换Scorebat数据格式"""
        return {
            "match_id": data.get("id"),
            "title": data.get("title"),
            "embed": data.get("embed"),
            "url": data.get("url"),
            "thumbnail": data.get("thumbnail"),
        }


class ScoreSourceManager:
    """数据源管理器"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化数据源管理器

        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self.sources = {
            "football_api": FootballAPISource(api_key),
            "api_sports": ApiSportsSource(api_key),
            "scorebat": ScorebatSource(api_key),
        }

    async def fetch_match_score(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        从所有数据源获取比赛比分

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]]: 比分数据
        """
        # 按优先级尝试数据源
        for source_name, source in self.sources.items():
            try:
                score_data = await source.fetch_match_score(match_id)
                if score_data:
                    logger.debug(f"从 {source_name} 成功获取比赛 {match_id} 比分")
                    return score_data
            except Exception as e:
                logger.warning(f"从 {source_name} 获取比赛 {match_id} 比分失败: {e}")
                continue

        logger.warning(f"所有数据源均无法获取比赛 {match_id} 的比分")
        return None

    def get_source(self, source_name: str) -> Optional[BaseScoreSource]:
        """
        获取指定数据源

        Args:
            source_name: 数据源名称

        Returns:
            Optional[BaseScoreSource]: 数据源实例
        """
        return self.sources.get(source_name)
import os

import aiohttp

from src.utils.time_utils import utc_now

