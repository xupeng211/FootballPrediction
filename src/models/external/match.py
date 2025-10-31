"""
外部比赛数据模型
External Match Data Model
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

Base = declarative_base()


class ExternalMatch(Base):
    """外部比赛数据模型"""

    __tablename__ = 'external_matches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(50), unique=True, nullable=False, index=True, comment='外部API的比赛ID')

    # 比赛基本信息
    competition_id = Column(Integer, nullable=False, comment='联赛ID')
    competition_name = Column(String(100), nullable=False, comment='联赛名称')
    competition_code = Column(String(10), nullable=False, comment='联赛代码')

    # 比赛时间信息
    match_date = Column(DateTime, nullable=True, comment='比赛时间')
    status = Column(String(20), nullable=False, comment='比赛状态')
    matchday = Column(Integer, nullable=True, comment='轮次')
    stage = Column(String(50), nullable=True, comment='阶段')
    venue = Column(String(100), nullable=True, comment='比赛场地')

    # 主队信息
    home_team_id = Column(Integer, nullable=False, comment='主队ID')
    home_team_name = Column(String(100), nullable=False, comment='主队名称')
    home_team_short_name = Column(String(50), nullable=True, comment='主队简称')
    home_team_crest = Column(Text, nullable=True, comment='主队队徽URL')

    # 客队信息
    away_team_id = Column(Integer, nullable=False, comment='客队ID')
    away_team_name = Column(String(100), nullable=False, comment='客队名称')
    away_team_short_name = Column(String(50), nullable=True, comment='客队简称')
    away_team_crest = Column(Text, nullable=True, comment='客队队徽URL')

    # 比分信息
    home_score = Column(Integer, default=0, comment='主队得分')
    away_score = Column(Integer, default=0, comment='客队得分')
    result = Column(String(20), nullable=True, comment='比赛结果(home_win/away_win/draw)')

    # 比赛详情
    score_detail = Column(JSON, nullable=True, comment='详细比分信息')
    referees = Column(JSON, nullable=True, comment='裁判信息')
    odds = Column(JSON, nullable=True, comment='赔率信息')

    # 元数据
    last_updated = Column(DateTime, nullable=True, comment='最后更新时间')
    raw_data = Column(JSON, nullable=True, comment='原始API数据')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 状态标志
    is_processed = Column(Boolean, default=False, comment='是否已处理')
    is_active = Column(Boolean, default=True, comment='是否激活')

    def __repr__(self):
        return f"<ExternalMatch(id={self.id}, external_id={self.external_id}, {self.home_team_name} vs {self.away_team_name})>"

    @property
    def match_title(self) -> str:
        """比赛标题"""
        return f"{self.home_team_name} vs {self.away_team_name}"

    @property
    def score_string(self) -> str:
        """比分字符串"""
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score} - {self.away_score}"
        return "未开始"

    @property
    def is_finished(self) -> bool:
        """是否已结束"""
        return self.status in ['finished', 'awarded']

    @property
    def is_live(self) -> bool:
        """是否正在进行"""
        return self.status in ['live', 'in_play', 'paused']

    @property
    def is_scheduled(self) -> bool:
        """是否已安排"""
        return self.status in ['scheduled', 'timed']

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'external_id': self.external_id,
            'competition_id': self.competition_id,
            'competition_name': self.competition_name,
            'competition_code': self.competition_code,
            'match_date': self.match_date.isoformat() if self.match_date else None,
            'status': self.status,
            'matchday': self.matchday,
            'stage': self.stage,
            'venue': self.venue,
            'home_team_id': self.home_team_id,
            'home_team_name': self.home_team_name,
            'home_team_short_name': self.home_team_short_name,
            'home_team_crest': self.home_team_crest,
            'away_team_id': self.away_team_id,
            'away_team_name': self.away_team_name,
            'away_team_short_name': self.away_team_short_name,
            'away_team_crest': self.away_team_crest,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'result': self.result,
            'score_detail': self.score_detail,
            'referees': self.referees,
            'odds': self.odds,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_processed': self.is_processed,
            'is_active': self.is_active,
            'match_title': self.match_title,
            'score_string': self.score_string,
            'is_finished': self.is_finished,
            'is_live': self.is_live,
            'is_scheduled': self.is_scheduled
        }

    @classmethod
    def from_api_data(cls, data: dict) -> 'ExternalMatch':
        """从API数据创建实例"""
        try:
            # 获取基本信息
            home_team = data.get('homeTeam', {})
            away_team = data.get('awayTeam', {})
            score = data.get('score', {})
            competition = data.get('competition', {})

            # 获取比分
            full_time_score = score.get('fullTime', {})
            home_score = full_time_score.get('home') or 0
            away_score = full_time_score.get('away') or 0

            # 判断比赛结果
            winner = score.get('winner')
            if winner == 'HOME_TEAM':
                result = 'home_win'
            elif winner == 'AWAY_TEAM':
                result = 'away_win'
            elif winner == 'DRAW':
                result = 'draw'
            else:
                result = None

            # 解析比赛时间
            match_date = None
            utc_date = data.get('utcDate')
            if utc_date:
                try:
                    match_date = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))
                except ValueError:
                    pass

            # 解析最后更新时间
            last_updated = None
            last_updated_str = data.get('lastUpdated')
            if last_updated_str:
                try:
                    last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                except ValueError:
                    pass

            return cls(
                external_id=str(data.get('id')),
                competition_id=competition.get('id'),
                competition_name=competition.get('name'),
                competition_code=competition.get('code'),
                match_date=match_date,
                status=data.get('status', '').lower(),
                matchday=data.get('matchday'),
                stage=data.get('stage'),
                venue=None,  # API中不包含venue信息
                home_team_id=home_team.get('id'),
                home_team_name=home_team.get('name'),
                home_team_short_name=home_team.get('shortName'),
                home_team_crest=home_team.get('crest'),
                away_team_id=away_team.get('id'),
                away_team_name=away_team.get('name'),
                away_team_short_name=away_team.get('shortName'),
                away_team_crest=away_team.get('crest'),
                home_score=home_score,
                away_score=away_score,
                result=result,
                score_detail=score,
                referees=data.get('referees'),
                odds=data.get('odds'),
                last_updated=last_updated,
                raw_data=data
            )

        except Exception as e:
            # 创建错误记录
            return cls(
                external_id=str(data.get('id', '')),
                competition_name=data.get('competition', {}).get('name', 'Unknown'),
                home_team_name=data.get('homeTeam', {}).get('name', 'Unknown Home'),
                away_team_name=data.get('awayTeam', {}).get('name', 'Unknown Away'),
                status='error',
                raw_data={'error': str(e), 'original_data': data}
            )

    def update_from_api_data(self, data: dict) -> bool:
        """
        从API数据更新实例

        Args:
            data: API数据

        Returns:
            是否更新成功
        """
        try:
            # 检查外部ID是否匹配
            if str(data.get('id')) != self.external_id:
                return False

            # 更新关键字段
            score = data.get('score', {})
            competition = data.get('competition', {})

            # 更新比分
            full_time_score = score.get('fullTime', {})
            self.home_score = full_time_score.get('home') or 0
            self.away_score = full_time_score.get('away') or 0

            # 更新结果
            winner = score.get('winner')
            if winner == 'HOME_TEAM':
                self.result = 'home_win'
            elif winner == 'AWAY_TEAM':
                self.result = 'away_win'
            elif winner == 'DRAW':
                self.result = 'draw'
            else:
                self.result = None

            # 更新状态
            self.status = data.get('status', '').lower()

            # 更新时间
            utc_date = data.get('utcDate')
            if utc_date:
                try:
                    self.match_date = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))
                except ValueError:
                    pass

            # 更新详细信息
            self.score_detail = score
            self.referees = data.get('referees')
            self.odds = data.get('odds')
            self.raw_data = data

            # 更新最后更新时间
            last_updated_str = data.get('lastUpdated')
            if last_updated_str:
                try:
                    self.last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                except ValueError:
                    pass

            self.updated_at = datetime.utcnow()
            return True

        except Exception as e:
            # 记录错误但不抛出异常
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating match {self.external_id}: {e}")
            return False