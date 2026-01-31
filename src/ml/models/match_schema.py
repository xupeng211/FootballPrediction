#!/usr/bin/env python3
"""
V41.155 Match Schema - 统一比赛数据模型
========================================

功能:
- 定义 Source_F (FotMob 基础元数据) 和 Source_O (OddsPortal 市场数据) 的统一数据模型
- 强制规范后续所有脚本的字段读写标准
- 提供数据验证和转换功能

Author: V41.155 Joint Auditor
Date: 2026-01-17
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# 枚举定义
# ============================================================================


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    FIXTURE = "Fixture"
    LIVE = "Live"
    FINISHED = "Finished"
    POSTPONED = "Postponed"
    CANCELLED = "Cancelled"
    ABANDONED = "Abandoned"
    UNKNOWN = "Unknown"


class DataSourceType(str, Enum):
    """数据源类型枚举"""

    FOTMOB = "Source_F"  # 基础元数据来源
    ODDSPORTAL = "Source_O"  # 市场度量数据来源


class MatchQuality(str, Enum):
    """数据质量评级"""

    EXCELLENT = "Excellent"  # Fusion_Score >= 90
    GOOD = "Good"  # 80 <= Fusion_Score < 90
    FAIR = "Fair"  # 60 <= Fusion_Score < 80
    POOR = "Poor"  # Fusion_Score < 60


# ============================================================================
# Source_F: FotMob 基础元数据模型
# ============================================================================


class SourceFData(BaseModel):
    """Source_F: FotMob 基础元数据

    包含比赛的基础信息:
    - ID, 队名, 时间, 结果
    - 联赛信息, 赛季信息
    """

    match_id: str = Field(..., min_length=1, description="比赛唯一标识符")
    home_team: str = Field(..., min_length=1, max_length=200, description="主队名称")
    away_team: str = Field(..., min_length=1, max_length=200, description="客队名称")
    match_time: datetime = Field(..., description="比赛时间 (UTC)")
    league_name: str = Field(..., min_length=1, max_length=200, description="联赛名称")
    season: str = Field(..., min_length=1, max_length=20, description="赛季")
    status: MatchStatus = Field(default=MatchStatus.FIXTURE, description="比赛状态")

    # 可选字段
    home_score: int | None = Field(None, ge=0, description="主队得分")
    away_score: int | None = Field(None, ge=0, description="客队得分")
    venue_name: str | None = Field(None, max_length=200, description="场地名称")
    referee_name: str | None = Field(None, max_length=100, description="裁判姓名")

    # 元数据
    collection_status: str = Field(default="pending", description="采集状态")
    l1_collected_at: datetime | None = Field(None, description="L1 采集时间")

    @model_validator(mode="after")
    def validate_teams_different(self):
        """确保主客队不同"""
        if self.home_team and self.away_team and self.home_team == self.away_team:
            raise ValueError("主队和客队不能相同")
        return self

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """标准化比赛状态"""
        if isinstance(v, str):
            status_map = {
                "fixture": "Fixture",
                "live": "Live",
                "finished": "Finished",
                "postponed": "Postponed",
                "cancelled": "Cancelled",
                "abandoned": "Abandoned",
            }
            return status_map.get(v.lower(), v)
        return v


# ============================================================================
# Source_O: OddsPortal 市场数据模型
# ============================================================================


class SourceOData(BaseModel):
    """Source_O: OddsPortal 市场度量数据

    包含市场数据:
    - 哈希URL (oddsportal_hash)
    - 价格列表 (init/final odds)
    - 完整性分数
    """

    match_id: str = Field(..., min_length=1, description="比赛唯一标识符")
    oddsportal_hash: str | None = Field(None, max_length=8, description="OddsPortal 哈希 (8字符)")
    oddsportal_url: str | None = Field(None, max_length=500, description="OddsPortal URL")

    # 初盘赔率
    init_h: float | None = Field(None, ge=1.01, le=50.00, description="初盘主胜赔率")
    init_d: float | None = Field(None, ge=1.01, le=50.00, description="初盘平局赔率")
    init_a: float | None = Field(None, ge=1.01, le=50.00, description="初盘客胜赔率")

    # 终盘赔率
    final_h: float | None = Field(None, ge=1.01, le=50.00, description="终盘主胜赔率")
    final_d: float | None = Field(None, ge=1.01, le=50.00, description="终盘平局赔率")
    final_a: float | None = Field(None, ge=1.01, le=50.00, description="终盘客胜赔率")

    # 数据质量指标
    integrity_score: float | None = Field(
        None, ge=0.90, le=1.20, description="完整性分数 (1/P1+1/P2+1/P3)"
    )
    is_valid: bool = Field(default=False, description="数据是否有效")

    # 元数据
    source_name: str = Field(default="Entity_P", description="数据源名称")
    l3_collected_at: datetime | None = Field(None, description="L3 采集时间")

    @model_validator(mode="after")
    def calculate_integrity_score(self) -> "SourceOData":
        """计算完整性分数"""
        if all([self.final_h, self.final_d, self.final_a]):
            self.integrity_score = 1.0 / self.final_h + 1.0 / self.final_d + 1.0 / self.final_a
            # 有效范围: 1.02 < integrity_score < 1.08
            self.is_valid = 1.02 < self.integrity_score < 1.08
        return self


# ============================================================================
# MatchSchema: 统一比赛数据模型
# ============================================================================


class MatchSchema(BaseModel):
    """V41.155 统一比赛数据模型

    整合 Source_F 和 Source_O 数据，提供完整比赛信息。
    所有脚本必须遵循此模型进行数据读写。

    字段组成:
    - 基础信息 (40%): ID, 队名, 时间, 联赛, 赛季, 状态
    - 哈希对齐 (30%): oddsportal_hash, oddsportal_url
    - 价格数据 (30%): init/final odds, integrity_score
    """

    # === 基础信息 (来自 Source_F) ===
    match_id: str = Field(..., min_length=1, description="比赛唯一标识符")
    home_team: str = Field(..., min_length=1, max_length=200, description="主队名称")
    away_team: str = Field(..., min_length=1, max_length=200, description="客队名称")
    match_time: datetime = Field(..., description="比赛时间 (UTC)")
    league_name: str = Field(..., min_length=1, max_length=200, description="联赛名称")
    season: str = Field(..., min_length=1, max_length=20, description="赛季")
    status: MatchStatus = Field(default=MatchStatus.FIXTURE, description="比赛状态")

    # 可选基础字段
    home_score: int | None = Field(None, ge=0, description="主队得分")
    away_score: int | None = Field(None, ge=0, description="客队得分")
    venue_name: str | None = Field(None, max_length=200, description="场地名称")

    # === 哈希对齐 (来自 Source_O) ===
    oddsportal_hash: str | None = Field(None, max_length=8, description="OddsPortal 哈希 (8字符)")
    oddsportal_url: str | None = Field(None, max_length=500, description="OddsPortal URL")

    # === 价格数据 (来自 Source_O) ===
    init_h: float | None = Field(None, ge=1.01, le=50.00, description="初盘主胜赔率")
    init_d: float | None = Field(None, ge=1.01, le=50.00, description="初盘平局赔率")
    init_a: float | None = Field(None, ge=1.01, le=50.00, description="初盘客胜赔率")

    final_h: float | None = Field(None, ge=1.01, le=50.00, description="终盘主胜赔率")
    final_d: float | None = Field(None, ge=1.01, le=50.00, description="终盘平局赔率")
    final_a: float | None = Field(None, ge=1.01, le=50.00, description="终盘客胜赔率")

    integrity_score: float | None = Field(None, ge=0.90, le=1.20, description="完整性分数")
    is_valid: bool = Field(default=False, description="数据是否有效")

    # === 元数据 ===
    source_f_available: bool = Field(default=False, description="Source_F 数据是否可用")
    source_o_available: bool = Field(default=False, description="Source_O 数据是否可用")
    fusion_score: float = Field(default=0.0, ge=0.0, le=100.0, description="融合分数 (0-100)")
    quality_rating: MatchQuality = Field(default=MatchQuality.POOR, description="数据质量评级")

    # 时间戳
    l1_collected_at: datetime | None = Field(None, description="L1 采集时间")
    l3_collected_at: datetime | None = Field(None, description="L3 采集时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @model_validator(mode="after")
    def calculate_fusion_score(self) -> "MatchSchema":
        """计算融合分数 (Fusion_Score)

        评分标准 (适配当前数据库结构):
        - 基础信息全 (50%): match_id, home_team, away_team, match_time, league_name, season
        - 哈希对齐 (50%): oddsportal_hash 非空

        注意: 由于当前数据库中 metrics_multi_source_data 表可能不存在，
        价格数据评分暂时禁用。
        """
        score = 0.0

        # 基础信息全 (50%)
        if (
            self.match_id
            and self.home_team
            and self.away_team
            and self.match_time
            and self.league_name
            and self.season
        ):
            score += 50.0

        # 哈希对齐 (50%)
        if self.oddsportal_hash:
            score += 50.0

        self.fusion_score = score

        # 设置质量评级
        if score >= 90:
            self.quality_rating = MatchQuality.EXCELLENT
        elif score >= 80:
            self.quality_rating = MatchQuality.GOOD
        elif score >= 60:
            self.quality_rating = MatchQuality.FAIR
        else:
            self.quality_rating = MatchQuality.POOR

        return self

    @model_validator(mode="after")
    def detect_source_availability(self) -> "MatchSchema":
        """检测数据源可用性"""
        # Source_F 可用: 基础信息存在
        self.source_f_available = bool(
            self.match_id
            and self.home_team
            and self.away_team
            and self.match_time
            and self.league_name
        )

        # Source_O 可用: 有哈希或价格数据
        self.source_o_available = bool(
            self.oddsportal_hash
            or any(
                [self.init_h, self.init_d, self.init_a, self.final_h, self.final_d, self.final_a]
            )
        )

        return self

    @classmethod
    def from_database_row(cls, row: dict[str, Any]) -> "MatchSchema":
        """从数据库行创建 MatchSchema 实例

        Args:
            row: 数据库查询结果字典

        Returns:
            MatchSchema 实例
        """
        # 从 matches 表的基础数据
        match_id = row.get("match_id") or row.get("external_id")

        # 从 matches_mapping 表的映射数据
        oddsportal_hash = row.get("hash") or row.get("oddsportal_hash")
        oddsportal_url = row.get("url") or row.get("oddsportal_url")

        # 从 metrics_multi_source_data 表的价格数据
        init_h = row.get("init_h")
        init_d = row.get("init_d")
        init_a = row.get("init_a")
        final_h = row.get("final_h")
        final_d = row.get("final_d")
        final_a = row.get("final_a")
        integrity_score = row.get("integrity_score")

        # 标准化比赛状态
        status_value = row.get("status")
        if status_value:
            status_map = {
                "Fixture": "Fixture",
                "Live": "Live",
                "Finished": "Finished",
                "FT": "Finished",
                "Postponed": "Postponed",
                "Cancelled": "Cancelled",
                "Abandoned": "Abandoned",
                "Scheduled": "Fixture",  # 标准化
                "NS": "Fixture",  # Not Started
                "Unknown": "Unknown",
            }
            status = MatchStatus(status_map.get(status_value, "Fixture"))
        else:
            status = MatchStatus.FIXTURE

        return cls(
            match_id=match_id or "",
            home_team=row.get("home_team", ""),
            away_team=row.get("away_team", ""),
            match_time=row.get("match_time") or row.get("match_date"),
            league_name=row.get("league_name", ""),
            season=row.get("season", ""),
            status=status,
            home_score=row.get("home_score") or row.get("home_goals"),
            away_score=row.get("away_score") or row.get("away_goals"),
            venue_name=row.get("venue_name"),
            oddsportal_hash=oddsportal_hash,
            oddsportal_url=oddsportal_url,
            init_h=init_h,
            init_d=init_d,
            init_a=init_a,
            final_h=final_h,
            final_d=final_d,
            final_a=final_a,
            integrity_score=integrity_score,
            is_valid=bool(integrity_score and 1.02 < integrity_score < 1.08),
        )


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "DataSourceType",
    "MatchQuality",
    "MatchSchema",
    "MatchStatus",
    "SourceFData",
    "SourceOData",
]
