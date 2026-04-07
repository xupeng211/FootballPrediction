from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.config.common import MAX_BATCH_SIZE_LIMIT


@dataclass
class FotMobAPIConfig:
    """FotMob API 配置。"""

    base_url: str = "https://www.fotmob.com/api"
    base_web_url: str = "https://www.fotmob.com"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    LEAGUE_IDS: dict[str, int] = field(
        default_factory=lambda: {
            "Premier League": 47,
            "Championship": 48,
            "La Liga": 87,
            "Segunda División": 94,
            "Bundesliga": 54,
            "2. Bundesliga": 95,
            "Serie A": 55,
            "Serie B": 127,
            "Ligue 1": 53,
            "Liga Portugal": 155,
            "Eredivisie": 129,
            "Jupiler Pro League": 118,
            "Scottish Premiership": 157,
            "Süper Lig": 201,
            "Super League Greece": 96,
            "Premier League Russia": 153,
            "Premier Liha": 186,
            "MLS": 203,
            "Serie A Brazil": 274,
            "Liga Profesional": 275,
            "Liga MX": 298,
            "J-League Division 1": 345,
            "Chinese Super League": 322,
            "K-League 1": 353,
            "Saudi Pro League": 410,
            "ADNOC Pro League": 411,
            "A-League": 312,
            "Indian Super League": 397,
            "Premier Soccer League": 288,
            "Premier League Egypt": 287,
            "NPFL": 412,
        }
    )
    SEASON_MAPPING: dict[str, str] = field(
        default_factory=lambda: {
            "2020/2021": "2021",
            "2021/2022": "2122",
            "2022/2023": "2223",
            "2023/2024": "2324",
            "2024/2025": "2425",
            "2021": "2020/2021",
            "2122": "2021/2022",
            "2223": "2022/2023",
            "2324": "2023/2024",
            "2425": "2024/2025",
            "20/21": "2020/2021",
            "21/22": "2021/2022",
            "22/23": "2022/2023",
            "23/24": "2023/2024",
            "24/25": "2024/2025",
        }
    )
    AVAILABLE_SEASONS: list[str] = field(
        default_factory=lambda: [
            "2020/2021",
            "2021/2022",
            "2022/2023",
            "2023/2024",
            "2024/2025",
        ]
    )
    ENDPOINTS: dict[str, str] = field(
        default_factory=lambda: {
            "match_details": "matchDetails",
            "leagues": "leagues",
            "teams": "teams",
            "all_leagues": "allLeagues",
        }
    )

    def __post_init__(self) -> None:
        if not self.headers:
            self.headers = {
                "User-Agent": "FootballPrediction/1.0",
                "Accept": "application/json",
                "Referer": self.base_web_url,
                "Origin": self.base_web_url,
            }

    def get_league_id(self, league_name: str) -> int | None:
        return self.LEAGUE_IDS.get(league_name)

    def normalize_season(self, season: str) -> str:
        return self.SEASON_MAPPING.get(season, season)

    def build_url(self, endpoint: str, **params: Any) -> str:
        endpoint_path = self.ENDPOINTS.get(endpoint, endpoint)
        url = f"{self.base_url}/{endpoint_path}"
        query_parts = [f"{key}={value}" for key, value in params.items() if value is not None]
        if query_parts:
            url += "?" + "&".join(query_parts)
        return url


class MLSettingsMixin(BaseModel):
    """外部 API、模型与业务参数配置。"""

    fotmob_base_url: str = Field(default="https://www.fotmob.com/api", description="FotMob API")
    fotmob_web_url: str = Field(default="https://www.fotmob.com", description="FotMob 网站")
    fotmob_x_mas_header: str | None = Field(default=None, description="FotMob X-MAS Header")
    fotmob_x_foo_header: str | None = Field(default=None, description="FotMob X-FOO Header")
    oddsportal_base_url: str = Field(
        default="https://www.oddsportal.com",
        description="OddsPortal 基础 URL",
    )
    oddsportal_timeout_ms: int = Field(default=30000, description="OddsPortal 超时")
    oddsportal_retry_attempts: int = Field(default=3, description="OddsPortal 重试次数")
    model_path: str = Field(
        default="model_zoo/production/v19.4_draw_sensitivity_model.pkl",
        description="模型文件路径",
    )
    model_version: str = Field(default="xgboost_v2", description="模型版本")
    enable_metrics: bool = Field(default=True, description="启用指标收集")
    metrics_port: int = Field(default=9090, description="指标端口")
    enable_tracing: bool = Field(default=False, description="启用链路追踪")
    cache_ttl_seconds: int = Field(default=300, description="缓存 TTL")
    cache_max_size: int = Field(default=1000, description="缓存最大条目数")
    default_confidence_threshold: float = Field(default=0.6, description="默认置信度阈值")
    max_batch_size: int = Field(default=100, description="最大批量处理大小")
    prediction_timeout_seconds: int = Field(default=30, description="预测超时时间")
    supported_leagues: dict[str, Any] = Field(
        default_factory=lambda: {
            "serie_a": {
                "id": 135,
                "name": "Serie A",
                "country": "Italy",
                "active": True,
                "priority": 1,
            },
            "la_liga": {
                "id": 87,
                "name": "La Liga",
                "country": "Spain",
                "active": True,
                "priority": 2,
            },
            "bundesliga": {
                "id": 54,
                "name": "Bundesliga",
                "country": "Germany",
                "active": True,
                "priority": 3,
            },
        },
        description="三联赛原生支持配置",
    )
    min_edge: float = Field(default=7.0, description="最小边际值")
    min_confidence: float = Field(default=45.0, description="最小置信度")
    target_roi: float = Field(default=13.35, description="目标 ROI")
    data_retention_days: int = Field(default=365, description="数据保留天数")
    harvest_batch_size: int = Field(default=50, description="数据收集批量大小")
    harvest_delay_seconds: float = Field(default=1.0, description="数据收集间隔")
    collection_pause_until: str | None = Field(default=None, description="IP 冷却期截止时间")
    match_status_finished: str = Field(default="FINISHED", description="比赛完成状态")
    match_status_scheduled: str = Field(default="SCHEDULED", description="比赛计划状态")
    match_status_live: str = Field(default="LIVE", description="比赛进行中状态")
    match_status_postponed: str = Field(default="POSTPONED", description="比赛推迟状态")
    feature_status_pending: str = Field(default="PENDING", description="特征待提取状态")
    feature_status_processing: str = Field(default="PROCESSING", description="特征提取中状态")
    feature_status_completed: str = Field(default="COMPLETED", description="特征提取完成状态")
    feature_status_failed: str = Field(default="FAILED", description="特征提取失败状态")
    pipeline_batch_size: int = Field(default=50, description="流水线批次处理大小")
    pipeline_gc_interval: int = Field(default=50, description="GC 调用间隔")
    max_l2_concurrency: int = Field(default=2, description="L2 最大并发数")
    pipeline_target_version: str = Field(default="V26.0", description="目标特征版本")

    @field_validator("default_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("置信度阈值必须在 0.0-1.0 之间")
        return value

    @field_validator("max_batch_size")
    @classmethod
    def validate_batch_size(cls, value: int) -> int:
        if not 1 <= value <= MAX_BATCH_SIZE_LIMIT:
            raise ValueError("批量大小必须在 1-1000 之间")
        return value

    @property
    def fotmob_api(self) -> FotMobAPIConfig:
        headers: dict[str, str] = {}
        if self.fotmob_x_mas_header:
            headers["X-MAS"] = self.fotmob_x_mas_header
        if self.fotmob_x_foo_header:
            headers["X-FOO"] = self.fotmob_x_foo_header
        return FotMobAPIConfig(base_url=self.fotmob_base_url, headers=headers)

    def get_model_path(self) -> Path:
        return Path(self.model_path)


@dataclass
class StrategyConfig:
    """策略配置。"""

    kelly_max_stake: float = 0.05
    kelly_daily_limit: float = 0.20
    kelly_risk_alert: float = 0.03
    tuner_trials: int = 50
    tuner_timeout: int = 1800
    tuner_early_stopping: int = 15
    tuner_min_improvement: float = 0.01


__all__ = [
    "FotMobAPIConfig",
    "MLSettingsMixin",
    "StrategyConfig",
]
