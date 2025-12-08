"""
虚拟采集器实现
Dummy Collector Implementation

该模块提供了一个简单的采集器实现，用于：
1. 验证BaseCollectorProtocol接口的完整性
2. 作为其他采集器实现的参考模板
3. 在开发和测试阶段提供模拟数据

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .interface import (
    BaseCollectorProtocol,
    FixtureData,
    MatchDetailData,
    TeamInfoData,
    HealthStatus,
    CollectorError,
    DataNotFoundError,
    AuthenticationError,
)
from .rate_limiter import RateLimiter


class DummyCollector(BaseCollectorProtocol):
    """
    虚拟采集器实现

    实现BaseCollectorProtocol的所有接口方法，返回模拟数据。
    用于开发阶段的接口验证和测试。
    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        初始化虚拟采集器

        Args:
            config: 配置字典，可包含:
                - delay_range: tuple - 请求延迟范围(秒)
                - error_rate: float - 模拟错误率(0.0-1.0)
                - failure_mode: bool - 是否启用失败模式
            rate_limiter: 速率限制器实例，用于控制请求频率
        """
        self.config = config or {}
        self.delay_range = self.config.get(
            "delay_range", (0.01, 0.05)
        )  # 更快的默认延迟
        self.error_rate = self.config.get("error_rate", 0.05)
        self.failure_mode = self.config.get("failure_mode", False)
        self.request_count = 0
        self.error_count = 0
        self._closed = False

        # 注入速率限制器
        self.rate_limiter = rate_limiter or RateLimiter(
            {"dummy": {"rate": 10.0, "burst": 20}}  # 默认10 QPS，突发20
        )

    async def _simulate_delay(self) -> None:
        """模拟网络延迟"""
        if self.delay_range:
            delay = random.uniform(*self.delay_range)
            await asyncio.sleep(delay)

    async def _check_for_errors(self) -> None:
        """根据配置模拟错误"""
        if self.failure_mode or random.random() < self.error_rate:
            self.error_count += 1
            error_types = [
                CollectorError("模拟通用错误"),
                AuthenticationError("模拟认证失败"),
                DataNotFoundError("模拟数据未找到"),
            ]
            raise random.choice(error_types)

    async def collect_fixtures(
        self, league_id: int, season_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        采集联赛赛程数据（模拟）

        Args:
            league_id: 联赛ID
            season_id: 赛季ID

        Returns:
            模拟的赛程数据列表
        """
        if self._closed:
            raise CollectorError("采集器已关闭")

        # 使用速率限制器控制请求频率
        async with self.rate_limiter.acquire("dummy"):
            await self._simulate_delay()
            await self._check_for_errors()

            self.request_count += 1

            # 生成模拟赛程数据
            num_fixtures = random.randint(5, 15)
            fixtures = []

            teams = [
                "Manchester United",
                "Liverpool",
                "Chelsea",
                "Arsenal",
                "Manchester City",
                "Tottenham",
                "Newcastle",
                "Leicester",
                "West Ham",
                "Aston Villa",
                "Southampton",
                "Everton",
            ]

            for i in range(num_fixtures):
                home_team = random.choice(teams)
                away_team = random.choice([t for t in teams if t != home_team])

                fixture: FixtureData = {
                    "match_id": f"dummy_match_{league_id}_{i:03d}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_time": datetime.now(timezone.utc).isoformat(),
                    "venue": f"Stadium {i}",
                    "status": random.choice(["scheduled", "live", "finished"]),
                    "league_id": league_id,
                    "season_id": season_id or "2024-2025",
                }
                fixtures.append(fixture)

            return fixtures

    async def collect_match_details(self, match_id: str) -> dict[str, Any]:
        """
        采集比赛详情数据（模拟）

        Args:
            match_id: 比赛ID

        Returns:
            模拟的比赛详情数据
        """
        if self._closed:
            raise CollectorError("采集器已关闭")

        await self._simulate_delay()
        await self._check_for_errors()

        self.request_count += 1

        # 生成模拟比赛详情数据
        home_score = random.randint(0, 5)
        away_score = random.randint(0, 5)
        home_xg = round(random.uniform(0.1, 4.5), 2)
        away_xg = round(random.uniform(0.1, 4.5), 2)

        match_details: MatchDetailData = {
            "match_id": match_id,
            "home_score": home_score,
            "away_score": away_score,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "shots": {
                "home_total": random.randint(5, 25),
                "away_total": random.randint(5, 25),
                "home_on_target": random.randint(2, 10),
                "away_on_target": random.randint(2, 10),
            },
            "possession": {
                "home": round(random.uniform(30, 70), 1),
                "away": round(random.uniform(30, 70), 1),
            },
            "events": [
                {
                    "minute": random.randint(1, 90),
                    "team": random.choice(["home", "away"]),
                    "type": random.choice(["goal", "yellow_card", "substitution"]),
                    "player": f"Player {random.randint(1, 30)}",
                }
                for _ in range(random.randint(0, 8))
            ],
            "lineups": {
                "home": [f"Home Player {i}" for i in range(1, 12)],
                "away": [f"Away Player {i}" for i in range(1, 12)],
            },
            "odds": (
                {
                    "home_win": round(random.uniform(1.5, 5.0), 2),
                    "draw": round(random.uniform(2.5, 4.0), 2),
                    "away_win": round(random.uniform(1.5, 5.0), 2),
                }
                if random.random() > 0.3
                else None
            ),
        }

        return match_details

    async def collect_team_info(self, team_id: str) -> dict[str, Any]:
        """
        采集球队信息（模拟）

        Args:
            team_id: 球队ID

        Returns:
            模拟的球队信息数据
        """
        if self._closed:
            raise CollectorError("采集器已关闭")

        await self._simulate_delay()
        await self._check_for_errors()

        self.request_count += 1

        team_names = [
            "Manchester United",
            "Liverpool",
            "Chelsea",
            "Arsenal",
            "Manchester City",
            "Tottenham",
            "Newcastle",
            "Leicester",
        ]
        team_name = team_names[hash(team_id) % len(team_names)]

        team_info: TeamInfoData = {
            "team_id": team_id,
            "name": team_name,
            "country": "England",
            "founded": random.randint(1870, 2000),
            "stadium": f"{team_name} Stadium",
            "logo_url": f"https://dummy-logo.com/{team_id}.png",
            "city": random.choice(["Manchester", "London", "Liverpool", "Newcastle"]),
        }

        return team_info

    async def check_health(self) -> dict[str, Any]:
        """
        检查采集器健康状态

        Returns:
            采集器的健康状态信息
        """
        start_time = datetime.now()

        # 模拟健康检查延迟
        await self._simulate_delay()

        end_time = datetime.now()
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        # 计算错误率
        total_requests = self.request_count
        error_rate = (self.error_count / total_requests) if total_requests > 0 else 0.0

        # 确定健康状态
        if error_rate > 0.5 or self.failure_mode:
            status = "unhealthy"
        elif error_rate > 0.2:
            status = "degraded"
        else:
            status = "healthy"

        health: HealthStatus = {
            "status": status,
            "response_time_ms": round(response_time_ms, 2),
            "last_check": datetime.now(timezone.utc).isoformat(),
            "error_count": self.error_count,
            "total_requests": total_requests,
            "error_rate": round(error_rate, 3),
            "details": {
                "collector_type": "dummy",
                "config": self.config,
                "closed": self._closed,
            },
        }

        return health

    async def close(self) -> None:
        """
        清理资源并关闭采集器
        """
        if self._closed:
            return  # 已经关闭，无需重复操作

        await self._simulate_delay()

        # 模拟资源清理
        await asyncio.sleep(0.1)

        self._closed = True

        # 清理配置（可选）
        if hasattr(self, "config"):
            self.config.clear()


# 便利函数
def create_dummy_collector(
    config: Optional[dict[str, Any]] = None, rate_limiter: Optional[RateLimiter] = None
) -> DummyCollector:
    """
    创建虚拟采集器实例

    Args:
        config: 配置字典
        rate_limiter: 速率限制器实例

    Returns:
        DummyCollector实例
    """
    return DummyCollector(config, rate_limiter)


# 模块导出
__all__ = [
    "DummyCollector",
    "create_dummy_collector",
]
