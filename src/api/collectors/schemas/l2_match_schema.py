#!/usr/bin/env python3
"""
V37.0 L2 采集器 Pydantic Schema
=============================
工业级数据完整性校验层，防止脏数据污染训练集

核心功能:
1. 定义 L2 比赛详情数据的标准模型
2. 数据质量分级 (FULL/PARTIAL/WARNING)
3. 核心预测特征强制校验

作者: ML Architect
日期: 2025-12-29
Phase: Production-Grade Refactor
Version: V37.0
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class L2DataQuality(str, Enum):
    """
    L2 数据质量标记

    - FULL: 完整数据，包含所有核心预测特征
    - PARTIAL: 部分缺失，但可用于训练
    - WARNING: 关键特征缺失，需要人工审核
    """

    FULL = "full"
    PARTIAL = "partial"
    WARNING = "warning"


class L2MatchStats(BaseModel):
    """
    L2 比赛统计数据核心字段

    这些是 V26.7/V26.8 模型的核心预测特征:
    - xG: Expected Goals (预期进球)
    - shots_on_target: 射正次数
    - possession: 控球率
    - team_rating: 球队评分
    """

    xg: list[float] | None = Field(default=None, description="Expected Goals [home, away]")
    shots_on_target: list[int] | None = Field(
        default=None, description="Shots on Target [home, away]"
    )
    possession: list[float] | None = Field(default=None, description="Possession % [home, away]")
    team_rating: list[float] | None = Field(default=None, description="Team Rating [home, away]")

    @field_validator("xg", "shots_on_target", "possession", "team_rating")
    @classmethod
    def validate_list_length(cls, v: list | None) -> list | None:
        """校验列表长度（必须是 [home, away] 格式）"""
        if v is not None and len(v) != 2:
            raise ValueError(f"统计字段必须是 [home, away] 格式，当前长度: {len(v)}")
        return v


class L2MatchDetailSchema(BaseModel):
    """
    L2 比赛详情数据标准模型

    这是数据入库前的最后一道校验关口
    任何不符合此模型的数据都将被记录为 WARNING 或 PARTIAL
    """

    # 核心标识
    match_id: str = Field(..., min_length=1, description="FotMob Match ID (纯数字)")
    fetched_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    # 数据质量标记
    data_quality: L2DataQuality = Field(default=L2DataQuality.FULL, description="数据质量等级")

    # 核心统计数据
    stats: L2MatchStats | None = Field(default=None, description="比赛统计数据")

    # 额外元数据
    # FotMob API 返回嵌套字典结构: {darkMode: {...}, lightMode: {...}, ...}
    team_colors: dict[str, Any] | None = Field(default=None, description="球队颜色配置（嵌套结构）")
    has_lineup: bool = Field(default=False, description="是否包含阵容数据")
    has_shotmap: bool = Field(default=False, description="是否包含射门图数据")

    # 原始数据引用（用于完整存储）
    raw_data: dict[str, Any] | None = Field(default=None, description="原始 API 响应数据")

    # ==================== 防御性校验 ====================

    @field_validator("match_id")
    @classmethod
    def validate_match_id(cls, v: str) -> str:
        """
        V37.0 核心防御：Match ID 格式校验

        必须是纯数字，与 L1 保持一致
        """
        if not v.isdigit():
            raise ValueError(f"❌ Match ID 必须是纯数字，当前值: '{v}'")
        return v

    @field_validator("stats", mode="before")
    @classmethod
    def validate_stats(cls, v: dict | L2MatchStats | None) -> L2MatchStats | None:
        """校验并转换统计数据"""
        if v is None:
            return None
        # 如果已经是 L2MatchStats 对象，直接返回
        if isinstance(v, L2MatchStats):
            return v
        # 如果是 dict，转换为 L2MatchStats
        try:
            return L2MatchStats(**v)
        except Exception as e:
            raise ValueError(f"统计数据格式异常: {e}") from e

    @model_validator(mode="after")
    def validate_data_quality(self) -> "L2MatchDetailSchema":
        """
        动态评估数据质量

        质量标准（基于 V26.7/V26.8 模型的特征依赖）:
        - FULL: stats 存在且包含 xG（最关键特征）
        - PARTIAL: stats 存在但 xG 缺失
        - WARNING: stats 完全缺失

        V139.1: WARNING 级别数据仍会保留，包含 match_id、team_colors、fetched_at
                等基础信息，可用于 L3 URL 匹配（降级存储策略）。
        """
        if self.stats is None:
            self.data_quality = L2DataQuality.WARNING
        elif self.stats.xg is None or len(self.stats.xg) < 2:
            self.data_quality = L2DataQuality.PARTIAL
        else:
            self.data_quality = L2DataQuality.FULL

        return self

    def to_dict(self) -> dict:
        """
        转换为字典（用于 JSONB 存储）

        保存格式:
        {
            "match_id": "4813374",
            "fetched_at": "2025-12-29T...",
            "data_quality": "full",
            "stats": {...},
            "raw_data": {...}
        }
        """
        return {
            "match_id": self.match_id,
            "fetched_at": self.fetched_at,
            "data_quality": self.data_quality.value,
            "stats": self.stats.model_dump() if self.stats else None,
            "team_colors": self.team_colors,
            "has_lineup": self.has_lineup,
            "has_shotmap": self.has_shotmap,
            "raw_data": self.raw_data,
        }


class L2CollectionSummary(BaseModel):
    """
    L2 采集摘要模型

    用于结构化监控和可观测性
    """

    collection_start_time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    collection_end_time: str | None = Field(default=None)

    # 统计数据
    total_attempted: int = Field(default=0, description="尝试采集的比赛数")
    total_success: int = Field(default=0, description="成功采集的比赛数")
    total_failed: int = Field(default=0, description="采集失败的比赛数")

    # 数据质量分布
    quality_distribution: dict[str, int] = Field(
        default_factory=dict, description={"full": 95, "partial": 3, "warning": 2}
    )

    # 性能指标
    total_api_time: float = Field(default=0.0, description="API 请求总耗时（秒）")
    total_db_time: float = Field(default=0.0, description="DB 写入总耗时（秒）")

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_attempted == 0:
            return 0.0
        return (self.total_success / self.total_attempted) * 100

    @property
    def full_data_rate(self) -> float:
        """完整数据率"""
        if self.total_success == 0:
            return 0.0
        full_count = self.quality_distribution.get("full", 0)
        return (full_count / self.total_success) * 100

    def add_success(self, quality: L2DataQuality, api_time: float = 0.0) -> None:
        """记录成功采集"""
        self.total_attempted += 1
        self.total_success += 1
        self.total_api_time += api_time

        q = quality.value
        self.quality_distribution[q] = self.quality_distribution.get(q, 0) + 1

    def add_failure(self) -> None:
        """记录失败采集"""
        self.total_attempted += 1
        self.total_failed += 1

    def add_db_time(self, db_time: float) -> None:
        """记录 DB 写入耗时"""
        self.total_db_time += db_time

    def finalize(self) -> None:
        """完成采集，记录结束时间"""
        self.collection_end_time = datetime.now(UTC).isoformat()

    def to_report(self) -> str:
        """生成可读报告"""
        duration = "N/A"
        if self.collection_end_time:
            start = datetime.fromisoformat(self.collection_start_time)
            end = datetime.fromisoformat(self.collection_end_time)
            duration = str(end - start)

        avg_api_time = (self.total_api_time / self.total_success) if self.total_success > 0 else 0
        avg_db_time = (self.total_db_time / self.total_attempted) if self.total_attempted > 0 else 0

        report = f"""
╔════════════════════════════════════════════════════════════╗
║           L2 采集摘要报告 (V37.0 Production-Grade)        ║
╚════════════════════════════════════════════════════════════╝

📊 采集统计:
   尝试: {self.total_attempted} 场
   成功: {self.total_success} 场
   失败: {self.total_failed} 场
   成功率: {self.success_rate:.2f}%

📈 数据质量分布:"""
        for quality in ["full", "partial", "warning"]:
            count = self.quality_distribution.get(quality, 0)
            pct = (count / self.total_success * 100) if self.total_success > 0 else 0
            icon = {"full": "✅", "partial": "⚠️", "warning": "❌"}.get(quality, "•")
            report += f"\n   {icon} {quality.upper()}: {count} 场 ({pct:.1f}%)"

        report += f"""
⏱️  性能指标:
   总耗时: {duration}
   平均 API 延迟: {avg_api_time:.2f} 秒
   平均 DB 延迟: {avg_db_time:.3f} 秒"""

        report += "\n╚════════════════════════════════════════════════════════════╝"
        return report
