"""
数据模型定义
使用 SQLAlchemy 定义数据库表结构和约束
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class League(Base):
    """联赛表"""
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="联赛名称")
    external_id = Column(String(50), unique=True, nullable=True, comment="外部API联赛ID")
    country = Column(String(50), nullable=True, comment="国家")
    season = Column(String(10), nullable=True, comment="赛季")

    # 关联比赛
    matches = relationship("Match", back_populates="league")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Team(Base):
    """球队表"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="标准队名")
    external_id = Column(String(50), nullable=True, comment="外部API球队ID")
    alternative_names = Column(Text, nullable=True, comment="备用队名，JSON格式存储")
    country = Column(String(50), nullable=True, comment="国家")
    founded_year = Column(Integer, nullable=True, comment="成立年份")
    stadium = Column(String(255), nullable=True, comment="主场")

    # 关联比赛（主队和客队）
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Match(Base):
    """比赛表"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(50), nullable=True, comment="外部API比赛ID")

    # 基本信息
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, comment="主队ID")
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, comment="客队ID")
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True, comment="联赛ID")

    # 比赛时间和状态
    match_date = Column(DateTime, nullable=False, comment="比赛时间")
    status = Column(String(20), default="scheduled", comment="比赛状态: scheduled, live, finished, postponed")

    # 比赛结果
    home_score = Column(Integer, nullable=True, comment="主队得分")
    away_score = Column(Integer, nullable=True, comment="客队得分")
    winner = Column(String(10), nullable=True, comment="胜者: home/away/draw")

    # 统计数据
    home_xg = Column(Float, nullable=True, comment="主队期望进球")
    away_xg = Column(Float, nullable=True, comment="客队期望进球")
    possession_home = Column(Float, nullable=True, comment="主队控球率")
    possession_away = Column(Float, nullable=True, comment="客队控球率")

    # 赔率数据
    home_win_odds = Column(Float, nullable=True, comment="主胜赔率")
    draw_odds = Column(Float, nullable=True, comment="平局赔率")
    away_win_odds = Column(Float, nullable=True, comment="客胜赔率")

    # 数据质量标记
    data_completeness = Column(String(20), default="partial", comment="数据完整性: partial/complete")
    is_processed = Column(Boolean, default=False, comment="是否已处理特征工程")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    league = relationship("League", back_populates="matches")

    # 关键约束：防止重复比赛数据
    __table_args__ = (
        # 方式1：基于外部ID的唯一约束（如果有外部ID）
        UniqueConstraint('external_id', name='uq_match_external_id'),
        # 方式2：基于比赛时间和队伍组合的唯一约束（兜底方案）
        UniqueConstraint('match_date', 'home_team_id', 'away_team_id', name='uq_match_teams_date'),
        # 索引优化查询性能
        {'extend_existing': True}
    )


class MatchEvent(Base):
    """比赛事件表（进球、黄牌等）"""
    __tablename__ = "match_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    event_type = Column(String(20), nullable=False, comment="事件类型: goal, yellow_card, red_card, substitution")
    event_minute = Column(Integer, nullable=True, comment="事件发生时间(分钟)")
    player_name = Column(String(100), nullable=True, comment="球员姓名")

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    match = relationship("Match")
    team = relationship("Team")

    # 防止重复事件
    __table_args__ = (
        UniqueConstraint('match_id', 'event_type', 'event_minute', 'player_name', name='uq_match_event'),
    )


class DataSourceLog(Base):
    """数据源日志表 - 追踪数据采集记录"""
    __tablename__ = "data_source_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(50), nullable=False, comment="数据源名称")
    endpoint = Column(String(200), nullable=True, comment="API端点")
    records_processed = Column(Integer, default=0, comment="处理记录数")
    success_count = Column(Integer, default=0, comment="成功记录数")
    error_count = Column(Integer, default=0, comment="错误记录数")
    error_message = Column(Text, nullable=True, comment="错误信息")

    execution_time_seconds = Column(Float, nullable=True, comment="执行时间(秒)")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 防止重复日志记录
    __table_args__ = (
        UniqueConstraint('source_name', 'endpoint', 'created_at', name='uq_data_source_log'),
    )


class ModelTraining(Base):
    """模型训练记录表"""
    __tablename__ = "model_training"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(50), nullable=False, comment="模型名称")
    model_version = Column(String(20), nullable=False, comment="模型版本")
    model_path = Column(String(200), nullable=True, comment="模型文件路径")

    # 训练参数
    training_date = Column(DateTime, nullable=False, comment="训练日期")
    training_matches_count = Column(Integer, nullable=True, comment="训练样本数")
    test_matches_count = Column(Integer, nullable=True, comment="测试样本数")

    # 模型性能指标
    accuracy = Column(Float, nullable=True, comment="准确率")
    precision = Column(Float, nullable=True, comment="精确率")
    recall = Column(Float, nullable=True, comment="召回率")
    f1_score = Column(Float, nullable=True, comment="F1分数")

    # 特征重要性
    feature_importance = Column(Text, nullable=True, comment="特征重要性，JSON格式")

    created_at = Column(DateTime, default=datetime.utcnow)

    # 确保模型版本唯一性
    __table_args__ = (
        UniqueConstraint('model_name', 'model_version', name='uq_model_version'),
    )