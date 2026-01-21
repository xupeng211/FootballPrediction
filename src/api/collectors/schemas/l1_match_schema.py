#!/usr/bin/env python3
"""
V36.0 L1 采集器 Pydantic Schema
=============================
工业级数据完整性校验层，防止元数据污染

核心功能:
1. 定义 FotMob API 返回数据的标准模型
2. 联赛元数据白名单校验
3. 强制类型校验，防止脏数据入库

作者: ML Architect
日期: 2025-12-28
Phase: Production-Grade Refactor
Version: V36.0
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class LeagueId(str, Enum):
    """
    FotMob League ID 枚举（白名单机制）

    V36.2 修复：使用正确的 FotMob League ID（基于 config/target_leagues.json）

    只有在此列表中的 League ID 才被允许通过校验
    这是防止"Premier League"标签污染的第一道防线
    """

    PREMIER_LEAGUE = "47"
    LA_LIGA = "87"  # V36.2 修复：从 55 改为 87
    BUNDESLIGA = "54"
    LIGUE_1 = "53"  # V36.2 修复：从 61 改为 53
    SERIE_A = "55"  # V36.2 修复：从 135 改为 55（135 是 EFL Cup）
    CHAMPIONS_LEAGUE = "42"

    @classmethod
    def get_league_name(cls, league_id: str) -> str:
        """获取 League ID 对应的英文名称"""
        mapping = {
            "47": "Premier League",
            "87": "La Liga",  # V36.2 修复
            "54": "Bundesliga",
            "53": "Ligue 1",  # V36.2 修复
            "55": "Serie A",  # V36.2 修复
            "42": "Champions League",
        }
        return mapping.get(league_id, "Unknown League")

    @classmethod
    def is_valid_id(cls, league_id: int | str) -> bool:
        """检查 League ID 是否在白名单中"""
        try:
            cls(str(league_id))
            return True
        except ValueError:
            return False


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    FINISHED = "finished"
    ONGOING = "ongoing"
    SCHEDULED = "scheduled"


class L1MatchData(BaseModel):
    """
    L1 比赛数据标准模型

    这是数据入库前的最后一道校验关口
    任何不符合此模型的数据都将被拒绝
    """

    # 核心标识
    match_id: str = Field(..., min_length=1, description="FotMob Match ID")
    league_id: str = Field(..., description="FotMob League ID")
    league_name: str = Field(..., min_length=1, description="League Name")

    # 赛季信息
    season_id: str = Field(..., description="Season ID (e.g., '2324')")
    season_name: str = Field(..., description="Season Display Name (e.g., '23/24')")

    # 球队信息
    home_team: str = Field(..., min_length=1, description="Home Team Name")
    away_team: str = Field(..., min_length=1, description="Away Team Name")
    home_team_id: int = Field(..., ge=1, description="Home Team FotMob ID")
    away_team_id: int = Field(..., ge=1, description="Away Team FotMob ID")

    # 比赛状态
    status: MatchStatus = Field(default=MatchStatus.SCHEDULED, description="Match Status")
    match_time_utc: str = Field(default="", description="Match UTC Time")

    # 比分（可选）
    home_score: int | None = Field(default=None, ge=0, description="Home Score")
    away_score: int | None = Field(default=None, ge=0, description="Away Score")

    # 元数据
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # ==================== 防御性校验 ====================

    @field_validator("league_id")
    @classmethod
    def validate_league_id(cls, v: str) -> str:
        """
        V36.0 核心防御：League ID 白名单校验

        这是防止"Premier League"标签污染的第一道防线
        只有白名单中的 League ID 才能通过此校验
        """
        if not LeagueId.is_valid_id(v):
            raise ValueError(
                f"❌ 拒绝非法 League ID: {v}。合法的 League IDs: {[lid.value for lid in LeagueId]}"
            )
        return v

    @field_validator("league_name")
    @classmethod
    def validate_league_name(cls, v: str, info: Any) -> str:
        """
        V36.0 核心防御：League Name 与 ID 一致性校验

        这是防止"Premier League"标签污染的第二道防线
        确保 league_name 与 league_id 匹配
        """
        # 获取 league_id
        league_id = info.data.get("league_id")
        if not league_id:
            raise ValueError("❌ league_id 必须在 league_name 之前校验")

        # 检查 league_name 是否与 league_id 匹配
        expected_name = LeagueId.get_league_name(league_id)

        # 允许一定的名称变体（容错）
        name_variants = {
            "Premier League": ["premier league", "Premier League", "EPL"],
            "La Liga": ["la liga", "La Liga", "Primera División"],
            "Bundesliga": ["bundesliga", "Bundesliga", "1. Bundesliga"],
            "Ligue 1": ["ligue 1", "Ligue 1", "Ligue 1 Conforama"],
            "Serie A": ["serie a", "Serie A", "Serie A TIM"],
            "Champions League": ["champions league", "Champions League", "UEFA Champions League"],
        }

        # 检查是否在合法变体中
        allowed_variants = name_variants.get(expected_name, [])
        if v not in allowed_variants:
            raise ValueError(
                f"❌ League Name 与 ID 不匹配！\n"
                f"   league_id={league_id} 期望名称: '{expected_name}'\n"
                f"   实际收到: league_name='{v}'"
            )

        return expected_name  # 返回标准化名称

    @model_validator(mode="after")
    def validate_score_consistency(self) -> "L1MatchData":
        """
        比分一致性校验

        - finished 状态必须有比分
        - scheduled 状态不能有比分
        """
        if self.status == MatchStatus.FINISHED:
            if self.home_score is None or self.away_score is None:
                raise ValueError(f"❌ finished 状态必须有比分: match_id={self.match_id}")
        elif self.status == MatchStatus.SCHEDULED:
            if self.home_score is not None or self.away_score is not None:
                raise ValueError(f"❌ scheduled 状态不能有比分: match_id={self.match_id}")
        return self

    def to_dict(self) -> dict:
        """转换为字典（用于数据库写入）"""
        return {
            "match_id": self.match_id,
            "league_id": int(self.league_id),
            "league_name": self.league_name,
            "season_id": self.season_id,
            "season_name": self.season_name,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "status": self.status.value,
            "match_time_utc": self.match_time_utc,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "fetched_at": self.fetched_at,
        }


class L1CollectionSummary(BaseModel):
    """
    L1 采集摘要模型

    用于结构化监控和可观测性
    """

    collection_start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    collection_end_time: str | None = Field(default=None)

    # 统计数据
    total_attempted: int = Field(default=0, description="尝试采集的比赛数")
    total_success: int = Field(default=0, description="成功采集的比赛数")
    total_failed: int = Field(default=0, description="采集失败的比赛数")

    # 按联赛统计
    by_league: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description={
            "47": {"attempted": 100, "success": 98, "failed": 2},
        },
    )

    # 错误分布
    error_distribution: dict[str, int] = Field(
        default_factory=dict, description={"404": 5, "ConnectionTimeout": 2, "ValidationError": 1}
    )

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_attempted == 0:
            return 0.0
        return (self.total_success / self.total_attempted) * 100

    def add_success(self, league_id: str) -> None:
        """记录成功"""
        self.total_attempted += 1
        self.total_success += 1
        self._increment_league_stat(league_id, "success")

    def add_failure(self, league_id: str, error_type: str) -> None:
        """记录失败"""
        self.total_attempted += 1
        self.total_failed += 1
        self._increment_league_stat(league_id, "failed")
        self._increment_error(error_type)

    def _increment_league_stat(self, league_id: str, key: str) -> None:
        """增加联赛统计"""
        if league_id not in self.by_league:
            self.by_league[league_id] = {"attempted": 0, "success": 0, "failed": 0}
        self.by_league[league_id]["attempted"] += 1
        self.by_league[league_id][key] += 1

    def _increment_error(self, error_type: str) -> None:
        """增加错误统计"""
        if error_type not in self.error_distribution:
            self.error_distribution[error_type] = 0
        self.error_distribution[error_type] += 1

    def finalize(self) -> None:
        """完成采集，记录结束时间"""
        self.collection_end_time = datetime.utcnow().isoformat()

    def to_report(self) -> str:
        """生成可读报告"""
        duration = "N/A"
        if self.collection_end_time:
            start = datetime.fromisoformat(self.collection_start_time)
            end = datetime.fromisoformat(self.collection_end_time)
            duration = str(end - start)

        report = f"""
╔════════════════════════════════════════════════════════════╗
║           L1 采集摘要报告 (V36.0 Production-Grade)        ║
╚════════════════════════════════════════════════════════════╝

📊 采集统计:
   尝试: {self.total_attempted} 场
   成功: {self.total_success} 场
   失败: {self.total_failed} 场
   成功率: {self.success_rate:.2f}%

⏱️  耗时: {duration}

🏆 按联赛分布:"""
        for league_id, stats in sorted(self.by_league.items()):
            league_name = LeagueId.get_league_name(league_id)
            rate = (stats["success"] / stats["attempted"] * 100) if stats["attempted"] > 0 else 0
            report += f"\n   [{league_name}]\n"
            report += (
                f"     尝试: {stats['attempted']} | "
                f"成功: {stats['success']} | "
                f"失败: {stats['failed']} | "
                f"成功率: {rate:.1f}%"
            )
        if self.error_distribution:
            report += "\n\n❌ 错误分布:\n"
            for error_type, count in sorted(self.error_distribution.items(), key=lambda x: -x[1]):
                report += f"   {error_type}: {count} 次"

        report += "\n╚════════════════════════════════════════════════════════════╝"
        return report
