"""
外部球队数据模型
External Team Data Model
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ExternalTeam(Base):
    """外部球队数据模型"""

    __tablename__ = "external_teams"

    id = Column(Integer,
    primary_key=True,
    autoincrement=True)
    external_id = Column(
        String(50),
    unique=True,
    nullable=False,
    index=True,
    comment="外部API的球队ID"
    )

    # 球队基本信息
    name = Column(String(100),
    nullable=False,
    comment="球队名称")
    short_name = Column(String(50),
    nullable=True,
    comment="球队简称")
    tla = Column(String(3),
    nullable=True,
    comment="三字母缩写")
    crest = Column(Text,
    nullable=True,
    comment="队徽URL")

    # 球队详细信息
    address = Column(Text,
    nullable=True,
    comment="地址")
    website = Column(String(200),
    nullable=True,
    comment="官方网站")
    founded = Column(Integer,
    nullable=True,
    comment="成立年份")
    club_colors = Column(String(100),
    nullable=True,
    comment="俱乐部颜色")
    venue = Column(String(100),
    nullable=True,
    comment="主场球场")

    # 地理信息
    area_id = Column(Integer,
    nullable=True,
    comment="地区ID")
    area_name = Column(String(100),
    nullable=True,
    comment="地区名称")
    area_code = Column(String(3),
    nullable=True,
    comment="地区代码")
    area_flag = Column(Text,
    nullable=True,
    comment="地区旗帜URL")

    # 联赛关联信息
    competition_id = Column(Integer,
    nullable=True,
    comment="所属联赛ID")
    competition_name = Column(String(100),
    nullable=True,
    comment="所属联赛名称")
    competition_code = Column(String(10),
    nullable=True,
    comment="所属联赛代码")

    # 元数据
    last_updated = Column(DateTime,
    nullable=True,
    comment="API最后更新时间")
    raw_data = Column(JSON,
    nullable=True,
    comment="原始API数据")
    created_at = Column(DateTime,
    default=datetime.utcnow,
    comment="创建时间")
    updated_at = Column(
        DateTime,
    default=datetime.utcnow,
    onupdate=datetime.utcnow,
    comment="更新时间"
    )

    # 状态标志
    is_processed = Column(Boolean,
    default=False,
    comment="是否已处理")
    is_active = Column(Boolean,
    default=True,
    comment="是否激活")
    data_quality_score = Column(Integer, default=0, comment="数据质量评分(0-100)")

    def __repr__(self):
        return f"<ExternalTeam(id={self.id}, external_id={self.external_id}, name={self.name})>"

    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.short_name or self.name

    @property
    def has_complete_info(self) -> bool:
        """是否有完整信息"""
        required_fields = ["name",
    "external_id"]
        return all(getattr(self,
    field) for field in required_fields)

    @property
    def is_premium_data(self) -> bool:
        """是否为高级数据"""
        premium_fields = ["address",
    "website",
    "founded",
    "club_colors",
    "venue"]
        return sum(1 for field in premium_fields if getattr(self, field)) >= 3

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "name": self.name,
            "short_name": self.short_name,
            "tla": self.tla,
            "crest": self.crest,
            "address": self.address,
            "website": self.website,
            "founded": self.founded,
            "club_colors": self.club_colors,
            "venue": self.venue,
            "area_id": self.area_id,
            "area_name": self.area_name,
            "area_code": self.area_code,
            "area_flag": self.area_flag,
            "competition_id": self.competition_id,
            "competition_name": self.competition_name,
            "competition_code": self.competition_code,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
    "created_at": self.created_at.isoformat() if self.created_at else None,
    "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    "is_processed": self.is_processed,

            "is_active": self.is_active,
            "data_quality_score": self.data_quality_score,
            "display_name": self.display_name,
            "has_complete_info": self.has_complete_info,
            "is_premium_data": self.is_premium_data,
        }

    @classmethod
    def from_api_data(
        cls,
    data: dict[str,
    Any],
    competition_info: dict[str,
    Any] | None = None
    ) -> "ExternalTeam":
        """从API数据创建实例"""
        try:
            # 解析地区信息
            area = data.get("area", {})

            # 解析最后更新时间
            last_updated = None
            last_updated_str = data.get("lastUpdated")
            if last_updated_str:
                try:
                    last_updated = datetime.fromisoformat(
                        last_updated_str.replace("Z",
    "+00:00")
                    )
                except ValueError:
                    pass

            # 计算数据质量评分
            quality_score = cls._calculate_data_quality_score(data)

            # 创建实例
            team = cls(
                external_id=str(data.get("id")),
    name=data.get("name"),
    short_name=data.get("shortName"),

                tla=data.get("tla"),
    crest=data.get("crest"),
    address=data.get("address"),
    website=data.get("website"),

                founded=data.get("founded"),
    club_colors=data.get("clubColors"),
    venue=data.get("venue"),
    area_id=area.get("id"),

                area_name=area.get("name"),
    area_code=area.get("code"),
    area_flag=area.get("flag"),
    last_updated=last_updated,

                raw_data=data,
                data_quality_score=quality_score,
            )

            # 设置联赛关联信息
            if competition_info:
                team.competition_id = competition_info.get("id")
                team.competition_name = competition_info.get("name")
                team.competition_code = competition_info.get("code")

            return team

        except Exception as e:
            # 创建错误记录
            return cls(
                external_id=str(data.get("id",
    "")),
    name=data.get("name",
    "Unknown Team"),

                raw_data={"error": str(e),
    "original_data": data},
    data_quality_score=0,
    )

    @staticmethod
    def _calculate_data_quality_score(data: dict[str,
    Any]) -> int:
        """计算数据质量评分"""
        score = 0

        # 基础信息 (40分)
        basic_fields = ["name", "shortName", "tla", "crest"]
        score += sum(10 for field in basic_fields if data.get(field))

        # 详细信息 (30分)
        detail_fields = ["address",
    "website",
    "founded",
    "clubColors",
    "venue"]
        score += sum(6 for field in detail_fields if data.get(field))

        # 地理信息 (20分)
        if data.get("area") and isinstance(data["area"],
    dict):
            area_data = data["area"]
            area_keys = ["id",
    "name",
    "code",
    "flag"]
            score += sum(5 for key in area_keys if area_data.get(key))

        # 更新时间 (10分)
        if data.get("lastUpdated"):
            score += 10

        return min(score,
    100)  # 最高100分

    def update_from_api_data(self,
    data: dict[str,
    Any]) -> bool:
        """从API数据更新实例"""
        try:
            # 检查外部ID是否匹配
            if str(data.get("id")) != self.external_id:
                return False

            # 更新基础信息
            self.name = data.get("name",
    self.name)
            self.short_name = data.get("shortName",
    self.short_name)
            self.tla = data.get("tla",
    self.tla)
            self.crest = data.get("crest",
    self.crest)

            # 更新详细信息
            self.address = data.get("address",
    self.address)
            self.website = data.get("website",
    self.website)
            self.founded = data.get("founded",
    self.founded)
            self.club_colors = data.get("clubColors",
    self.club_colors)
            self.venue = data.get("venue",
    self.venue)

            # 更新地理信息
            area = data.get("area", {})
            if area:
                self.area_id = area.get("id",
    self.area_id)
                self.area_name = area.get("name",
    self.area_name)
                self.area_code = area.get("code",
    self.area_code)
                self.area_flag = area.get("flag",
    self.area_flag)

            # 更新元数据
            self.raw_data = data
            self.data_quality_score = self._calculate_data_quality_score(data)

            # 更新最后更新时间
            last_updated_str = data.get("lastUpdated")
            if last_updated_str:
                try:
                    self.last_updated = datetime.fromisoformat(
                        last_updated_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            self.updated_at = datetime.utcnow()
            return True

        except Exception as e:
            # 记录错误但不抛出异常
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error updating team {self.external_id}: {e}")
            return False

    def merge_competition_info(self, competition_info: dict[str, Any]) -> None:
        """合并联赛信息"""
        if competition_info:
            self.competition_id = competition_info.get("id")
            self.competition_name = competition_info.get("name")
            self.competition_code = competition_info.get("code")
            self.updated_at = datetime.utcnow()
