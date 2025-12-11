"""Titan007 数据模型 - 双表架构 (Latest + History)
Titan007 Data Models - Dual Table Architecture (Latest + History).

实施"最新快照 + 历史记录"双表策略，解决变盘数据覆盖问题：
- Latest表：存储每个公司每场比赛的最新赔率（单条记录，支持更新）
- History表：存储所有赔率变动历史（多条记录，支持时间序列查询）

这个架构设计确保了：
1. 最新赔率的快速查询（Latest表）
2. 完整的变盘历史追踪（History表）
3. 高性能的数据写入（分离读写场景）
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from src.database.base import BaseModel


class TitanBookmaker(BaseModel):
    """Titan007 博彩公司模型 - 支持双表架构"""

    __tablename__ = "titan_bookmakers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, unique=True, nullable=False, index=True)  # Titan公司ID
    company_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=True)  # 显示名称
    country = Column(String(50), nullable=True)  # 国家
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义在模型类外部（避免循环引用）
    # euro_odds_latest, euro_odds_history, asian_odds_latest, asian_odds_history, overunder_odds_latest, overunder_odds_history

    def __repr__(self):
        return f"<TitanBookmaker(id={self.id}, name={self.company_name})>"


class TitanEuroOddsLatest(BaseModel):
    """Titan007 欧赔最新数据表 (1X2)

    存储每个博彩公司每场比赛的最新赔率数据。
    特点：
    - 单条记录：(match_id, bookmaker_id) 唯一约束
    - 支持更新操作：新数据覆盖旧数据
    - 快速查询：用于显示当前最新赔率
    """

    __tablename__ = "titan_euro_odds_latest"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), nullable=False, index=True, comment="Titan比赛ID")
    bookmaker_id = Column(
        Integer,
        ForeignKey("titan_bookmakers.id"),
        nullable=False,
        index=True,
        comment="博彩公司ID",
    )

    # 赔率字段 (使用 Numeric 确保精度)
    home_odds = Column(Numeric(10, 4), nullable=True, comment="主胜赔率")
    draw_odds = Column(Numeric(10, 4), nullable=True, comment="平局赔率")
    away_odds = Column(Numeric(10, 4), nullable=True, comment="客胜赔率")

    # 开盘赔率
    home_open = Column(Numeric(10, 4), nullable=True, comment="主胜开盘赔率")
    draw_open = Column(Numeric(10, 4), nullable=True, comment="平局开盘赔率")
    away_open = Column(Numeric(10, 4), nullable=True, comment="客胜开盘赔率")

    # 时间戳和元数据
    update_time = Column(
        DateTime, nullable=False, comment="赔率更新时间（来自Titan API）"
    )
    is_live = Column(Boolean, default=False, comment="是否为实时赔率")
    confidence_score = Column(Numeric(5, 3), nullable=True, comment="置信度分数 0-1")

    # Titan 原始数据保留
    raw_data = Column(Text, nullable=True, comment="Titan API原始数据")

    # 记录时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="记录创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="记录更新时间",
    )

    # 最新表的索引和约束 - 确保每场比赛每家公司只有一条最新记录
    __table_args__ = (
        UniqueConstraint(
            "match_id", "bookmaker_id", name="uq_titan_euro_latest_match_bookmaker"
        ),
        Index("idx_titan_euro_latest_match_bookmaker", "match_id", "bookmaker_id"),
        Index("idx_titan_euro_latest_update_time", "update_time"),
    )

    # 关系
    bookmaker = relationship("TitanBookmaker", back_populates="euro_odds_latest")

    def __repr__(self):
        return f"<TitanEuroOddsLatest(match={self.match_id}, bookmaker={self.bookmaker_id}, home={self.home_odds})>"


class TitanEuroOddsHistory(BaseModel):
    """Titan007 欧赔历史数据表 (1X2)

    存储所有赔率变动历史记录，用于分析和趋势追踪。
    特点：
    - 多条记录：同一公司同一场比赛可以有多个历史记录
    - 只增不改：历史记录一旦写入永不修改
    - 时间序列：按 update_time 排序支持历史查询
    - 去重优化：相同赔率不重复记录（可选）
    """

    __tablename__ = "titan_euro_odds_history"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), nullable=False, index=True, comment="Titan比赛ID")
    bookmaker_id = Column(
        Integer,
        ForeignKey("titan_bookmakers.id"),
        nullable=False,
        index=True,
        comment="博彩公司ID",
    )

    # 赔率字段 (使用 Numeric 确保精度)
    home_odds = Column(Numeric(10, 4), nullable=True, comment="主胜赔率")
    draw_odds = Column(Numeric(10, 4), nullable=True, comment="平局赔率")
    away_odds = Column(Numeric(10, 4), nullable=True, comment="客胜赔率")

    # 开盘赔率
    home_open = Column(Numeric(10, 4), nullable=True, comment="主胜开盘赔率")
    draw_open = Column(Numeric(10, 4), nullable=True, comment="平局开盘赔率")
    away_open = Column(Numeric(10, 4), nullable=True, comment="客胜开盘赔率")

    # 时间戳和元数据
    update_time = Column(
        DateTime, nullable=False, comment="赔率更新时间（来自Titan API）"
    )
    is_live = Column(Boolean, default=False, comment="是否为实时赔率")
    confidence_score = Column(Numeric(5, 3), nullable=True, comment="置信度分数 0-1")

    # Titan 原始数据保留
    raw_data = Column(Text, nullable=True, comment="Titan API原始数据")

    # 记录时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="历史记录创建时间")

    # 历史表的索引和约束 - 优化时间序列查询
    __table_args__ = (
        # 注意：历史表没有 (match_id, bookmaker_id) 的唯一约束，允许重复记录
        Index("idx_titan_euro_history_match_time", "match_id", "update_time"),
        Index("idx_titan_euro_history_bookmaker_time", "bookmaker_id", "update_time"),
        Index("idx_titan_euro_history_update_time", "update_time"),
        # 唯一约束用于去重：同一公司同一场比赛同一时间点只允许一条记录
        UniqueConstraint(
            "match_id",
            "bookmaker_id",
            "update_time",
            name="uq_titan_euro_history_match_bookmaker_time",
        ),
    )

    # 关系
    bookmaker = relationship("TitanBookmaker", back_populates="euro_odds_history")

    def __repr__(self):
        return f"<TitanEuroOddsHistory(match={self.match_id}, bookmaker={self.bookmaker_id}, time={self.update_time}, home={self.home_odds})>"


class TitanAsianOddsLatest(BaseModel):
    """Titan007 亚盘最新数据表 (让球盘)

    存储每个博彩公司每场比赛的最新亚盘数据。
    """

    __tablename__ = "titan_asian_odds_latest"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), nullable=False, index=True, comment="Titan比赛ID")
    bookmaker_id = Column(
        Integer,
        ForeignKey("titan_bookmakers.id"),
        nullable=False,
        index=True,
        comment="博彩公司ID",
    )

    # 亚盘字段
    upper_odds = Column(Numeric(10, 4), nullable=True, comment="上盘赔率")
    lower_odds = Column(Numeric(10, 4), nullable=True, comment="下盘赔率")
    handicap = Column(String(20), nullable=True, comment="盘口 (如: -0.5, +0.25)")

    # 开盘赔率
    upper_open = Column(Numeric(10, 4), nullable=True, comment="上盘开盘赔率")
    lower_open = Column(Numeric(10, 4), nullable=True, comment="下盘开盘赔率")
    handicap_open = Column(String(20), nullable=True, comment="开盘盘口")

    # 时间戳和元数据
    update_time = Column(
        DateTime, nullable=False, comment="赔率更新时间（来自Titan API）"
    )
    is_live = Column(Boolean, default=False, comment="是否为实时赔率")
    confidence_score = Column(Numeric(5, 3), nullable=True, comment="置信度分数 0-1")

    # Titan 原始数据保留
    raw_data = Column(Text, nullable=True, comment="Titan API原始数据")

    # 记录时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="记录创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="记录更新时间",
    )

    # 最新表的索引和约束
    __table_args__ = (
        UniqueConstraint(
            "match_id", "bookmaker_id", name="uq_titan_asian_latest_match_bookmaker"
        ),
        Index("idx_titan_asian_latest_match_bookmaker", "match_id", "bookmaker_id"),
        Index("idx_titan_asian_latest_update_time", "update_time"),
    )

    # 关系
    bookmaker = relationship("TitanBookmaker", back_populates="asian_odds_latest")

    def __repr__(self):
        return f"<TitanAsianOddsLatest(match={self.match_id}, bookmaker={self.bookmaker_id}, handicap={self.handicap})>"


class TitanAsianOddsHistory(BaseModel):
    """Titan007 亚盘历史数据表 (让球盘)

    存储所有亚盘变动历史记录，用于盘口变化分析。
    """

    __tablename__ = "titan_asian_odds_history"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), nullable=False, index=True, comment="Titan比赛ID")
    bookmaker_id = Column(
        Integer,
        ForeignKey("titan_bookmakers.id"),
        nullable=False,
        index=True,
        comment="博彩公司ID",
    )

    # 亚盘字段
    upper_odds = Column(Numeric(10, 4), nullable=True, comment="上盘赔率")
    lower_odds = Column(Numeric(10, 4), nullable=True, comment="下盘赔率")
    handicap = Column(String(20), nullable=True, comment="盘口 (如: -0.5, +0.25)")

    # 开盘赔率
    upper_open = Column(Numeric(10, 4), nullable=True, comment="上盘开盘赔率")
    lower_open = Column(Numeric(10, 4), nullable=True, comment="下盘开盘赔率")
    handicap_open = Column(String(20), nullable=True, comment="开盘盘口")

    # 时间戳和元数据
    update_time = Column(
        DateTime, nullable=False, comment="赔率更新时间（来自Titan API）"
    )
    is_live = Column(Boolean, default=False, comment="是否为实时赔率")
    confidence_score = Column(Numeric(5, 3), nullable=True, comment="置信度分数 0-1")

    # Titan 原始数据保留
    raw_data = Column(Text, nullable=True, comment="Titan API原始数据")

    # 记录时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="历史记录创建时间")

    # 历史表的索引和约束 - 优化时间序列查询
    __table_args__ = (
        # 优化查询的复合索引
        Index("idx_titan_asian_history_match_time", "match_id", "update_time"),
        Index("idx_titan_asian_history_bookmaker_time", "bookmaker_id", "update_time"),
        Index("idx_titan_asian_history_update_time", "update_time"),
        # 去重约束：同一公司同一场比赛同一时间点只允许一条记录
        UniqueConstraint(
            "match_id",
            "bookmaker_id",
            "update_time",
            name="uq_titan_asian_history_match_bookmaker_time",
        ),
    )

    # 关系
    bookmaker = relationship("TitanBookmaker", back_populates="asian_odds_history")

    def __repr__(self):
        return f"<TitanAsianOddsHistory(match={self.match_id}, bookmaker={self.bookmaker_id}, time={self.update_time}, handicap={self.handicap})>"


class TitanOverUnderOddsLatest(BaseModel):
    """Titan007 大小球最新数据表 (进球数)

    存储每个博彩公司每场比赛的最新大小球数据。
    """

    __tablename__ = "titan_overunder_odds_latest"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), nullable=False, index=True, comment="Titan比赛ID")
    bookmaker_id = Column(
        Integer,
        ForeignKey("titan_bookmakers.id"),
        nullable=False,
        index=True,
        comment="博彩公司ID",
    )

    # 大小球字段
    over_odds = Column(Numeric(10, 4), nullable=True, comment="大球赔率")
    under_odds = Column(Numeric(10, 4), nullable=True, comment="小球赔率")
    overunder = Column(String(20), nullable=True, comment="盘口 (如: 2.5, 3.0, 2.5/3)")

    # 开盘赔率
    over_open = Column(Numeric(10, 4), nullable=True, comment="大球开盘赔率")
    under_open = Column(Numeric(10, 4), nullable=True, comment="小球开盘赔率")
    overunder_open = Column(String(20), nullable=True, comment="开盘盘口")

    # 时间戳和元数据
    update_time = Column(
        DateTime, nullable=False, comment="赔率更新时间（来自Titan API）"
    )
    is_live = Column(Boolean, default=False, comment="是否为实时赔率")
    confidence_score = Column(Numeric(5, 3), nullable=True, comment="置信度分数 0-1")

    # Titan 原始数据保留
    raw_data = Column(Text, nullable=True, comment="Titan API原始数据")

    # 记录时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="记录创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="记录更新时间",
    )

    # 最新表的索引和约束
    __table_args__ = (
        UniqueConstraint(
            "match_id", "bookmaker_id", name="uq_titan_overunder_latest_match_bookmaker"
        ),
        Index("idx_titan_overunder_latest_match_bookmaker", "match_id", "bookmaker_id"),
        Index("idx_titan_overunder_latest_update_time", "update_time"),
    )

    # 关系
    bookmaker = relationship("TitanBookmaker", back_populates="overunder_odds_latest")

    def __repr__(self):
        return f"<TitanOverUnderOddsLatest(match={self.match_id}, bookmaker={self.bookmaker_id}, line={self.overunder})>"


class TitanOverUnderOddsHistory(BaseModel):
    """Titan007 大小球历史数据表 (进球数)

    存储所有大小球变动历史记录，用于盘口变化分析。
    """

    __tablename__ = "titan_overunder_odds_history"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), nullable=False, index=True, comment="Titan比赛ID")
    bookmaker_id = Column(
        Integer,
        ForeignKey("titan_bookmakers.id"),
        nullable=False,
        index=True,
        comment="博彩公司ID",
    )

    # 大小球字段
    over_odds = Column(Numeric(10, 4), nullable=True, comment="大球赔率")
    under_odds = Column(Numeric(10, 4), nullable=True, comment="小球赔率")
    overunder = Column(String(20), nullable=True, comment="盘口 (如: 2.5, 3.0, 2.5/3)")

    # 开盘赔率
    over_open = Column(Numeric(10, 4), nullable=True, comment="大球开盘赔率")
    under_open = Column(Numeric(10, 4), nullable=True, comment="小球开盘赔率")
    overunder_open = Column(String(20), nullable=True, comment="开盘盘口")

    # 时间戳和元数据
    update_time = Column(
        DateTime, nullable=False, comment="赔率更新时间（来自Titan API）"
    )
    is_live = Column(Boolean, default=False, comment="是否为实时赔率")
    confidence_score = Column(Numeric(5, 3), nullable=True, comment="置信度分数 0-1")

    # Titan 原始数据保留
    raw_data = Column(Text, nullable=True, comment="Titan API原始数据")

    # 记录时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="历史记录创建时间")

    # 历史表的索引和约束 - 优化时间序列查询
    __table_args__ = (
        # 优化查询的复合索引
        Index("idx_titan_overunder_history_match_time", "match_id", "update_time"),
        Index(
            "idx_titan_overunder_history_bookmaker_time", "bookmaker_id", "update_time"
        ),
        Index("idx_titan_overunder_history_update_time", "update_time"),
        # 去重约束：同一公司同一场比赛同一时间点只允许一条记录
        UniqueConstraint(
            "match_id",
            "bookmaker_id",
            "update_time",
            name="uq_titan_overunder_history_match_bookmaker_time",
        ),
    )

    # 关系
    bookmaker = relationship("TitanBookmaker", back_populates="overunder_odds_history")

    def __repr__(self):
        return f"<TitanOverUnderOddsHistory(match={self.match_id}, bookmaker={self.bookmaker_id}, time={self.update_time}, line={self.overunder})>"


# 更新 TitanBookmaker 的关系定义，以支持新的双表结构
# 将原有的关系更新为支持最新表和历史表的关系
TitanBookmaker.euro_odds_latest = relationship(
    "TitanEuroOddsLatest", back_populates="bookmaker", cascade="all, delete-orphan"
)
TitanBookmaker.euro_odds_history = relationship(
    "TitanEuroOddsHistory", back_populates="bookmaker", cascade="all, delete-orphan"
)
TitanBookmaker.asian_odds_latest = relationship(
    "TitanAsianOddsLatest", back_populates="bookmaker", cascade="all, delete-orphan"
)
TitanBookmaker.asian_odds_history = relationship(
    "TitanAsianOddsHistory", back_populates="bookmaker", cascade="all, delete-orphan"
)
TitanBookmaker.overunder_odds_latest = relationship(
    "TitanOverUnderOddsLatest", back_populates="bookmaker", cascade="all, delete-orphan"
)
TitanBookmaker.overunder_odds_history = relationship(
    "TitanOverUnderOddsHistory",
    back_populates="bookmaker",
    cascade="all, delete-orphan",
)


# 导出的类列表 - 更新为双表结构
__all__ = [
    "TitanBookmaker",
    # 欧赔双表
    "TitanEuroOddsLatest",
    "TitanEuroOddsHistory",
    # 亚盘双表
    "TitanAsianOddsLatest",
    "TitanAsianOddsHistory",
    # 大小球双表
    "TitanOverUnderOddsLatest",
    "TitanOverUnderOddsHistory",
]
