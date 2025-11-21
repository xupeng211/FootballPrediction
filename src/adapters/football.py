"""football 主模块
Football Main Module.

此文件由长文件拆分工具自动生成
拆分策略: complexity_split
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 导入基础模型
from .adapters.football_models import (
    FootballData,
    MatchStatus,
)
from .adapters.football_models import (
    Match as FootballMatch,
)
from .adapters.football_models import (
    Player as FootballPlayer,
)
from .adapters.football_models import (
    Team as FootballTeam,
)

# 为了向后兼容，创建基础适配器类
from .base import BaseAdapter, AdapterStatus


class FootballAdapterError(Exception):
    """Football适配器异常基类."""

    pass


class FootballAdapterConnectionError(FootballAdapterError):
    """Football适配器连接错误."""

    pass


class FootballDataAdapter(BaseAdapter):
    """足球数据适配器基类."""

    pass


class ApiFootballAdapter(FootballDataAdapter):
    """API Football适配器 - 使用Football-Data.org API."""

    def __init__(self, name: str = "Football-Data.org"):
        """初始化API适配器."""
        super().__init__(name)
        self.base_url = "https://api.football-data.org/v4"
        self.api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not self.api_key:
            self.status = AdapterStatus.ERROR
            self._set_error(Exception("FOOTBALL_DATA_API_KEY环境变量未设置"))
        else:
            self.headers = {"X-Auth-Token": self.api_key}

    async def _do_initialize(self) -> bool:
        """初始化适配器."""
        try:
            # 验证API Key有效性
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/competitions", headers=self.headers
                )
                if response.status_code == 200:
                    return True
                else:
                    raise FootballAdapterConnectionError(
                        f"API验证失败，状态码: {response.status_code}"
                    )
        except httpx.ConnectError as e:
            raise FootballAdapterConnectionError(f"网络连接失败: {e}")
        except httpx.TimeoutException as e:
            raise FootballAdapterConnectionError(f"请求超时: {e}")
        except Exception as e:
            raise FootballAdapterError(f"初始化失败: {e}")

    async def _do_cleanup(self) -> None:
        """清理适配器资源."""
        pass

    async def get_data(self, request: Any) -> Any:
        """获取原始数据."""
        return await self.get_fixtures(**request)

    async def send_data(self, data: Any) -> bool:
        """发送数据."""
        return True

    async def request(self, data: Any) -> Any:
        """标准请求方法."""
        return await self.get_fixtures(**data)

    async def get_fixtures(
        self, league_code: str = "PL", season: int = 2024
    ) -> list[dict[str, Any]]:
        """
        获取比赛赛程数据。

        Args:
            league_code: 联赛代码，默认为"PL"（英超）
            season: 赛季年份，默认为2024

        Returns:
            比赛数据列表
        """
        if not self.api_key:
            raise FootballAdapterError("FOOTBALL_DATA_API_KEY未配置")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 获取比赛数据
                url = f"{self.base_url}/competitions/{league_code}/matches"
                params = {
                    "season": season,
                    "limit": 100,  # 限制返回数量
                }

                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code != 200:
                    error_msg = f"API请求失败: HTTP {response.status_code}"
                    if response.status_code == 403:
                        error_msg += " - 可能是API Key无效或订阅过期"
                    elif response.status_code == 404:
                        error_msg += " - 联赛代码或赛季不存在"
                    raise FootballAdapterConnectionError(error_msg)

                data = response.json()
                matches = data.get("matches", [])

                if not matches:
                    logger.warning(f"联赛 {league_code} 赛季 {season} 没有找到比赛数据")

                return matches

        except httpx.ConnectError as e:
            raise FootballAdapterConnectionError(f"网络连接失败: {e}")
        except httpx.TimeoutException as e:
            raise FootballAdapterConnectionError(f"请求超时: {e}")
        except httpx.HTTPStatusError as e:
            raise FootballAdapterConnectionError(f"HTTP错误: {e}")
        except Exception as e:
            raise FootballAdapterError(f"获取比赛数据失败: {e}")

    async def get_teams(self, league_code: str = "PL") -> list[dict[str, Any]]:
        """
        获取球队数据。

        Args:
            league_code: 联赛代码

        Returns:
            球队数据列表
        """
        if not self.api_key:
            raise FootballAdapterError("FOOTBALL_DATA_API_KEY未配置")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/competitions/{league_code}/teams"

                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    raise FootballAdapterConnectionError(
                        f"获取球队数据失败: HTTP {response.status_code}"
                    )

                data = response.json()
                return data.get("teams", [])

        except httpx.ConnectError as e:
            raise FootballAdapterConnectionError(f"网络连接失败: {e}")
        except httpx.TimeoutException as e:
            raise FootballAdapterConnectionError(f"请求超时: {e}")
        except Exception as e:
            raise FootballAdapterError(f"获取球队数据失败: {e}")

    async def get_competitions(self) -> list[dict[str, Any]]:
        """
        获取可用的联赛列表。

        Returns:
            联赛数据列表
        """
        if not self.api_key:
            raise FootballAdapterError("FOOTBALL_DATA_API_KEY未配置")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/competitions", headers=self.headers
                )

                if response.status_code != 200:
                    raise FootballAdapterConnectionError(
                        f"获取联赛列表失败: HTTP {response.status_code}"
                    )

                data = response.json()
                return data.get("competitions", [])

        except httpx.ConnectError as e:
            raise FootballAdapterConnectionError(f"网络连接失败: {e}")
        except httpx.TimeoutException as e:
            raise FootballAdapterConnectionError(f"请求超时: {e}")
        except Exception as e:
            raise FootballAdapterError(f"获取联赛列表失败: {e}")


class OptaDataAdapter(FootballDataAdapter):
    """Opta数据适配器."""

    pass


class CompositeFootballAdapter(FootballDataAdapter):
    """复合足球适配器."""

    pass


# 其他兼容类别名
class FootballApiAdapter(ApiFootballAdapter):
    pass


class ApiFootballAdaptee(FootballData):
    pass


class OptaDataAdaptee(FootballData):
    pass


class FootballApiAdaptee(FootballData):
    pass


class FootballDataTransformer:
    """足球数据转换器."""

    pass


# 导出所有公共接口
__all__ = [
    "MatchStatus",
    "FootballMatch",
    "FootballTeam",
    "FootballPlayer",
    "FootballData",
    "FootballApiAdaptee",
    "ApiFootballAdaptee",
    "OptaDataAdaptee",
    "FootballDataTransformer",
    "FootballApiAdapter",
    "ApiFootballAdapter",
    "OptaDataAdapter",
    "CompositeFootballAdapter",
    "FootballDataAdapter",
]
