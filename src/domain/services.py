"""
域服务工厂

提供领域服务的工厂模式实现，管理服务依赖和生命周期。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from dataclasses import dataclass
import asyncio

from ..database.repositories.base import BaseRepository
from ..database.repositories.match import MatchRepository
from ..database.repositories.prediction import PredictionRepository
from ..database.repositories.team import TeamRepository
from ..database.repositories.user import UserRepository
from ..database.repositories.league import LeagueRepository
from ..database.repositories.odds import OddsRepository
from .match import Match
from .team import Team
from .prediction import Prediction
from .league import League
from .user import UserProfile
from .odds import Odds
from .rules import ValidationEngine, get_validation_engine

T = TypeVar("T")


@dataclass
class ServiceConfig:
    """服务配置"""

    name: str
    version: str = "1.0.0"
    enabled: bool = True
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class DomainService(ABC, Generic[T]):
    """域服务基类"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or ServiceConfig(self.__class__.__name__)
        self.name = self.config.name
        self.version = self.config.version
        self.enabled = self.config.enabled
        self.config_data = self.config.config

        # 依赖注入
        self._dependencies: Dict[str, "DomainService"] = {}
        self._repositories: Dict[str, BaseRepository] = {}

        # 验证引擎
        self._validation_engine: Optional[ValidationEngine] = None

        # 状态管理
        self._initialized = False
        self._started = False

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化服务"""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """停止服务"""
        pass

    def add_dependency(self, name: str, service: "DomainService"):
        """添加依赖服务"""
        self._dependencies[name] = service

    def add_repository(self, name: str, repository: BaseRepository):
        """添加仓储"""
        self._repositories[name] = repository

    def get_dependency(self, name: str) -> Optional["DomainService"]:
        """获取依赖服务"""
        return self._dependencies.get(name)

    def get_repository(self, name: str) -> Optional[BaseRepository]:
        """获取仓储"""
        return self._repositories.get(name)

    def set_validation_engine(self, engine: ValidationEngine):
        """设置验证引擎"""
        self._validation_engine = engine

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized

    @property
    def is_started(self) -> bool:
        """是否已启动"""
        return self._started


class MatchDomainService(DomainService[Match]):
    """比赛域服务"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        super().__init__(config or ServiceConfig("MatchDomainService"))
        self.match_repo: Optional[MatchRepository] = None
        self.team_repo: Optional[TeamRepository] = None

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.match_repo = self.get_repository("match")
            self.team_repo = self.get_repository("team")

            if not self.match_repo or not self.team_repo:
                raise ValueError("缺少必要的仓储")

            self._initialized = True
            return True
        except Exception as e:
            print(f"MatchDomainService 初始化失败: {e}")
            return False

    async def start(self) -> bool:
        """启动服务"""
        if not self._initialized:
            return False

        try:
            # 启动时的初始化逻辑
            self._started = True
            return True
        except Exception as e:
            print(f"MatchDomainService 启动失败: {e}")
            return False

    async def stop(self) -> bool:
        """停止服务"""
        self._started = False
        return True

    async def get_upcoming_matches(self, days: int = 7, limit: int = 50) -> List[Match]:
        """获取即将到来的比赛"""
        if not self._started:
            raise RuntimeError("服务未启动")

        return await self.match_repo.get_upcoming_matches(days=days, limit=limit)

    async def calculate_match_predictions(self, match_id: int) -> Dict[str, Any]:
        """计算比赛预测"""
        if not self._started:
            raise RuntimeError("服务未启动")

        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError(f"比赛 {match_id} 不存在")

        # 获取预测
        prediction_service = self.get_dependency("prediction")
        if not prediction_service:
            raise ValueError("缺少预测服务依赖")

        return await prediction_service.calculate_predictions_for_match(match)


class TeamDomainService(DomainService[Team]):
    """球队域服务"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        super().__init__(config or ServiceConfig("TeamDomainService"))
        self.team_repo: Optional[TeamRepository] = None
        self.match_repo: Optional[MatchRepository] = None

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.team_repo = self.get_repository("team")
            self.match_repo = self.get_repository("match")

            if not self.team_repo:
                raise ValueError("缺少team仓储")

            self._initialized = True
            return True
        except Exception as e:
            print(f"TeamDomainService 初始化失败: {e}")
            return False

    async def start(self) -> bool:
        """启动服务"""
        if not self._initialized:
            return False

        self._started = True
        return True

    async def stop(self) -> bool:
        """停止服务"""
        self._started = False
        return True

    async def get_team_statistics(
        self, team_id: int, last_matches: int = 10
    ) -> Dict[str, Any]:
        """获取球队统计"""
        if not self._started:
            raise RuntimeError("服务未启动")

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise ValueError(f"球队 {team_id} 不存在")

        stats = await self.team_repo.get_team_statistics(team_id, last_matches)
        return stats

    async def calculate_team_strength(self, team_id: int) -> float:
        """计算球队实力"""
        if not self._started:
            raise RuntimeError("服务未启动")

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise ValueError(f"球队 {team_id} 不存在")

        return team.get_strength_score()


class PredictionDomainService(DomainService[Prediction]):
    """预测域服务"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        super().__init__(config or ServiceConfig("PredictionDomainService"))
        self.prediction_repo: Optional[PredictionRepository] = None
        self.match_repo: Optional[MatchRepository] = None

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.prediction_repo = self.get_repository("prediction")
            self.match_repo = self.get_repository("match")

            if not self.prediction_repo:
                raise ValueError("缺少prediction仓储")

            self._initialized = True
            return True
        except Exception as e:
            print(f"PredictionDomainService 初始化失败: {e}")
            return False

    async def start(self) -> bool:
        """启动服务"""
        if not self._initialized:
            return False

        self._started = True
        return True

    async def stop(self) -> bool:
        """停止服务"""
        self._started = False
        return True

    async def create_prediction(self, prediction_data: Dict[str, Any]) -> Prediction:
        """创建预测"""
        if not self._started:
            raise RuntimeError("服务未启动")

        # 创建预测对象
        prediction = Prediction.from_dict(prediction_data)

        # 验证
        if self._validation_engine:
            result = self._validation_engine.validate(prediction)
            if not result.is_valid:
                raise ValueError(f"预测验证失败: {[v.message for v in result.errors]}")

        # 保存
        created = await self.prediction_repo.create(prediction)
        return created

    async def calculate_predictions_for_match(self, match: Match) -> Dict[str, Any]:
        """为比赛计算预测"""
        if not self._started:
            raise RuntimeError("服务未启动")

        # 获取历史数据
        team_service = self.get_dependency("team")
        if not team_service:
            raise ValueError("缺少球队服务依赖")

        home_strength = await team_service.calculate_team_strength(match.home_team_id)
        away_strength = await team_service.calculate_team_strength(match.away_team_id)

        # 简化的预测逻辑
        prediction_result = {
            "match_id": match.id,
            "home_win_prob": 0.0,
            "draw_prob": 0.0,
            "away_win_prob": 0.0,
            "confidence": 0.0,
        }

        if home_strength > 0 and away_strength > 0:
            strength_diff = home_strength - away_strength
            base_prob = 0.5 + (strength_diff / 200)  # 简化计算

            prediction_result["home_win_prob"] = min(0.9, max(0.1, base_prob))
            prediction_result["draw_prob"] = min(
                0.9, max(0.1, 0.25 - abs(strength_diff) / 200)
            )
            prediction_result["away_win_prob"] = (
                1.0
                - prediction_result["home_win_prob"]
                - prediction_result["draw_prob"]
            )
            prediction_result["confidence"] = min(
                0.9, max(0.1, 0.5 + abs(strength_diff) / 100)
            )

        return prediction_result


class LeagueDomainService(DomainService[League]):
    """联赛域服务"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        super().__init__(config or ServiceConfig("LeagueDomainService"))
        self.league_repo: Optional[LeagueRepository] = None

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.league_repo = self.get_repository("league")

            if not self.league_repo:
                raise ValueError("缺少league仓储")

            self._initialized = True
            return True
        except Exception as e:
            print(f"LeagueDomainService 初始化失败: {e}")
            return False

    async def start(self) -> bool:
        """启动服务"""
        if not self._initialized:
            return False

        self._started = True
        return True

    async def stop(self) -> bool:
        """停止服务"""
        self._started = False
        return True

    async def update_league_table(self, league_id: int) -> bool:
        """更新联赛积分榜"""
        if not self._started:
            raise RuntimeError("服务未启动")

        league = await self.league_repo.get_by_id(league_id)
        if not league:
            raise ValueError(f"联赛 {league_id} 不存在")

        # 获取最近比赛并更新积分榜
        match_service = self.get_dependency("match")
        if not match_service:
            raise ValueError("缺少比赛服务依赖")

        # 实际实现会更复杂，这里简化
        return True


class UserDomainService(DomainService[UserProfile]):
    """用户域服务"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        super().__init__(config or ServiceConfig("UserDomainService"))
        self.user_repo: Optional[UserRepository] = None

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.user_repo = self.get_repository("user")

            if not self.user_repo:
                raise ValueError("缺少user仓储")

            self._initialized = True
            return True
        except Exception as e:
            print(f"UserDomainService 初始化失败: {e}")
            return False

    async def start(self) -> bool:
        """启动服务"""
        if not self._initialized:
            return False

        self._started = True
        return True

    async def stop(self) -> bool:
        """停止服务"""
        self._started = False
        return True

    async def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """获取用户档案"""
        if not self._started:
            raise RuntimeError("服务未启动")

        user = await self.user_repo.get_by_id(user_id)
        return user


class DomainServiceFactory:
    """域服务工厂

    负责创建、配置和管理所有域服务实例。
    """

    def __init__(self):
        self._services: Dict[str, DomainService] = {}
        self._repositories: Dict[str, BaseRepository] = {}
        self._validation_engine = get_validation_engine()

    def register_repository(self, name: str, repository: BaseRepository):
        """注册仓储"""
        self._repositories[name] = repository

    def create_service(
        self, service_type: Type[DomainService], config: Optional[ServiceConfig] = None
    ) -> DomainService:
        """创建服务实例"""
        service = service_type(config)

        # 注入所有仓储
        for name, repo in self._repositories.items():
            service.add_repository(name, repo)

        # 注入验证引擎
        service.set_validation_engine(self._validation_engine)

        return service

    def create_all_services(self) -> Dict[str, DomainService]:
        """创建所有域服务"""
        services = {}

        # 创建所有服务
        services["match"] = self.create_service(MatchDomainService)
        services["team"] = self.create_service(TeamDomainService)
        services["prediction"] = self.create_service(PredictionDomainService)
        services["league"] = self.create_service(LeagueDomainService)
        services["user"] = self.create_service(UserDomainService)

        # 设置服务依赖
        services["match"].add_dependency("prediction", services["prediction"])
        services["prediction"].add_dependency("team", services["team"])
        services["team"].add_dependency("match", services["match"])
        services["league"].add_dependency("match", services["match"])

        self._services = services
        return services

    async def initialize_all_services(self) -> bool:
        """初始化所有服务"""
        for name, service in self._services.items():
            if not await service.initialize():
                print(f"服务 {name} 初始化失败")
                return False

        print("所有域服务初始化成功")
        return True

    async def start_all_services(self) -> bool:
        """启动所有服务"""
        for name, service in self._services.items():
            if not await service.start():
                print(f"服务 {name} 启动失败")
                return False

        print("所有域服务启动成功")
        return True

    async def stop_all_services(self) -> bool:
        """停止所有服务"""
        for name, service in self._services.items():
            if not await service.stop():
                print(f"服务 {name} 停止失败")

        print("所有域服务已停止")
        return True

    def get_service(self, name: str) -> Optional[DomainService]:
        """获取服务"""
        return self._services.get(name)

    def get_services(self) -> Dict[str, DomainService]:
        """获取所有服务"""
        return self._services.copy()

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = {
            "factory": "healthy",
            "services": {},
            "repositories": len(self._repositories),
            "timestamp": datetime.now().isoformat(),
        }

        for name, service in self._services.items():
            status["services"][name] = {
                "initialized": service.is_initialized,
                "started": service.is_started,
                "enabled": service.enabled,
            }

        return status


# 全局工厂实例
_domain_factory = None


def get_domain_factory() -> DomainServiceFactory:
    """获取全局域服务工厂实例"""
    global _domain_factory
    if _domain_factory is None:
        _domain_factory = DomainServiceFactory()
    return _domain_factory
