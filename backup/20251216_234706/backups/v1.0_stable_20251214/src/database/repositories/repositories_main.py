"""
数据仓库层 - 单一真理源（简化版）
实现数据访问和 Upsert 逻辑，确保数据一致性和去重
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from loguru import logger

from ..models import (
    League, Match, Team
)
from ...utils.normalizer import team_standardizer, league_standardizer, data_validator


class BaseRepository:
    """基础仓库类，提供通用的数据库操作"""

    def __init__(self, session: Session):
        self.session = session

    def _handle_db_error(self, error: Exception, operation: str) -> None:
        """统一的数据库错误处理"""
        logger.error(f"Database error during {operation}: {str(error)}")
        if isinstance(error, IntegrityError):
            logger.error(f"Integrity constraint violation: {error}")
        raise error


class TeamRepository(BaseRepository):
    """球队数据仓库"""

    def upsert_team(self, name: str, external_id: Optional[str] = None, **kwargs) -> Team:
        """
        插入或更新球队数据
        Args:
            name: 球队名称
            external_id: 外部API球队ID
            **kwargs: 其他球队属性（如country, founded_year, stadium等）
        Returns:
            Team: 球队对象
        """
        try:
            # 标准化队名
            standard_name = team_standardizer.normalize_team_name(name)

            # 首先尝试通过外部ID查找
            team = None
            if external_id:
                team = self.session.query(Team).filter(
                    Team.external_id == external_id
                ).first()

            # 如果没找到，通过标准化名称查找
            if not team:
                team = self.session.query(Team).filter(
                    Team.name == standard_name
                ).first()

            if team:
                # 更新现有记录
                if team.name != standard_name:
                    team.name = standard_name
                    logger.debug(f"Updated team name: {name} → {standard_name}")
                if external_id and team.external_id != external_id:
                    team.external_id = external_id

                # 更新其他属性
                for key, value in kwargs.items():
                    if hasattr(team, key) and value is not None:
                        setattr(team, key, value)

                team.updated_at = datetime.utcnow()
                logger.debug(f"Team updated: {standard_name}")
            else:
                # 创建新记录，确保必填字段有默认值
                team_data = {
                    'name': standard_name,
                    'external_id': external_id,
                    'country': 'Unknown',  # 为必填字段提供默认值
                }
                # 添加其他字段
                for key, value in kwargs.items():
                    if hasattr(Team, key):
                        team_data[key] = value

                team = Team(**team_data)
                self.session.add(team)
                logger.debug(f"Team created: {standard_name}")

            self.session.commit()
            return team

        except SQLAlchemyError as e:
            self.session.rollback()
            self._handle_db_error(e, f"upsert_team({name})")

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """根据名称获取球队"""
        standard_name = team_standardizer.normalize_team_name(name)
        return self.session.query(Team).filter(
            Team.name == standard_name
        ).first()

    def get_team_by_external_id(self, external_id: str) -> Optional[Team]:
        """根据外部ID获取球队"""
        return self.session.query(Team).filter(
            Team.external_id == external_id
        ).first()

    def get_all_teams(self) -> List[Team]:
        """获取所有球队"""
        return self.session.query(Team).all()


class LeagueRepository(BaseRepository):
    """联赛数据仓库"""

    def upsert_league(self,
                      name: str,
                      external_id: Optional[str] = None,
                      **kwargs) -> League:
        """
        插入或更新联赛数据
        Args:
            name: 联赛名称
            external_id: 外部API联赛ID
            **kwargs: 其他联赛属性（如country, season等）
        Returns:
            League: 联赛对象
        """
        try:
            # 标准化联赛名称
            standard_name = league_standardizer.normalize_league_name(name)

            # 查找现有联赛
            league = None
            if external_id:
                league = self.session.query(League).filter(
                    League.external_id == external_id
                ).first()

            if not league:
                league = self.session.query(League).filter(
                    League.name == standard_name
                ).first()

            if league:
                # 更新现有记录
                if league.name != standard_name:
                    league.name = standard_name
                if external_id and league.external_id != external_id:
                    league.external_id = external_id

                # 更新其他属性
                for key, value in kwargs.items():
                    if hasattr(league, key) and value is not None:
                        setattr(league, key, value)

                league.updated_at = datetime.utcnow()
                logger.debug(f"League updated: {standard_name}")
            else:
                # 创建新记录，确保必填字段有默认值
                league_data = {
                    'name': standard_name,
                    'external_id': external_id,
                    'country': 'Unknown',  # 为必填字段提供默认值
                    'season': '2023-24',  # 为必填字段提供默认值
                }
                # 添加其他字段
                for key, value in kwargs.items():
                    if hasattr(League, key):
                        league_data[key] = value

                league = League(**league_data)
                self.session.add(league)
                logger.debug(f"League created: {standard_name}")

            self.session.commit()
            return league

        except SQLAlchemyError as e:
            self.session.rollback()
            self._handle_db_error(e, f"upsert_league({name})")

    def get_league_by_name(self, name: str) -> Optional[League]:
        """根据名称获取联赛"""
        standard_name = league_standardizer.normalize_league_name(name)
        return self.session.query(League).filter(
            League.name == standard_name
        ).first()


class MatchRepository(BaseRepository):
    """比赛数据仓库 - 核心的 Upsert 逻辑"""

    def upsert_match(self, match_data: Dict) -> Tuple[Match, bool]:
        """
        插入或更新比赛数据
        实现严格的数据去重和更新逻辑

        Args:
            match_data: 比赛数据字典
        Returns:
            Tuple[Match, bool]: (比赛对象, 是否为新记录)
        """
        try:
            # 1. 数据验证
            is_valid, errors = data_validator.validate_match_data(match_data)
            if not is_valid:
                logger.error(f"Invalid match data: {errors}")
                raise ValueError(f"Invalid match data: {', '.join(errors)}")

            # 2. 标准化数据
            normalized_data = self._normalize_match_data(match_data)

            # 3. 查找现有比赛（按优先级）
            existing_match = self._find_existing_match(normalized_data)

            if existing_match:
                # 4. 更新现有比赛
                updated_match = self._update_match(existing_match, normalized_data)
                self.session.commit()
                logger.debug(f"Match updated: {normalized_data['home_team']} vs {normalized_data['away_team']}")
                return updated_match, False
            else:
                # 5. 创建新比赛
                new_match = self._create_match(normalized_data)
                self.session.commit()
                logger.debug(f"Match created: {normalized_data['home_team']} vs {normalized_data['away_team']}")
                return new_match, True

        except (SQLAlchemyError, ValueError) as e:
            self.session.rollback()
            self._handle_db_error(e, f"upsert_match")

    def _normalize_match_data(self, match_data: Dict) -> Dict:
        """标准化比赛数据"""
        normalized = match_data.copy()

        # 标准化队名
        if 'home_team' in match_data and 'away_team' in match_data:
            home_team, away_team = team_standardizer.normalize_team_pair(
                match_data['home_team'], match_data['away_team']
            )
            normalized['home_team'] = home_team
            normalized['away_team'] = away_team

        # 标准化联赛名
        if 'league' in match_data:
            normalized['league'] = league_standardizer.normalize_league_name(match_data['league'])

        # 确保时间格式
        if 'match_date' in normalized and isinstance(normalized['match_date'], str):
            try:
                normalized['match_date'] = datetime.fromisoformat(normalized['match_date'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid date format: {normalized['match_date']}")
                # 如果日期格式无效，使用当前时间
                normalized['match_date'] = datetime.utcnow()

        return normalized

    def _find_existing_match(self, match_data: Dict) -> Optional[Match]:
        """
        查找现有比赛记录
        查找优先级：外部ID → 比赛+日期+队伍组合
        """
        # 方式1：通过外部ID查找（最精确）
        if 'external_id' in match_data and match_data['external_id']:
            match = self.session.query(Match).filter(
                Match.fotmob_id == match_data['external_id']
            ).first()
            if match:
                logger.debug(f"Found match by fotmob_id: {match_data['external_id']}")
                return match

        # 方式2：通过比赛时间和队伍组合查找（兜底方案）
        if all(key in match_data for key in ['home_team', 'away_team', 'match_date']):
            team_repo = TeamRepository(self.session)

            # 获取主客队对象
            home_team = team_repo.upsert_team(match_data['home_team'])
            away_team = team_repo.upsert_team(match_data['away_team'])

            # 查找匹配的比赛
            match = self.session.query(Match).filter(
                and_(
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.match_date == match_data['match_date']
                )
            ).first()

            if match:
                logger.debug(f"Found match by teams and date: {home_team.name} vs {away_team.name}")
                return match

        return None

    def _update_match(self, match: Match, match_data: Dict) -> Match:
        """更新现有比赛记录"""
        # 更新基本信息
        if 'status' in match_data:
            match.status = match_data['status']

        # 更新比分（只有在新数据更完整时才更新）
        if match_data.get('home_score') is not None and match_data.get('away_score') is not None:
            # 如果原来没有比分，或者新的比分更可靠
            if match.home_score is None or match.away_score is None:
                match.home_score = match_data['home_score']
                match.away_score = match_data['away_score']
                # 自动计算胜者
                if match.home_score > match.away_score:
                    match.winner = 'home'
                elif match.away_score > match.home_score:
                    match.winner = 'away'
                else:
                    match.winner = 'draw'

        # 更新统计数据
        # 注意：使用现有模型中的正确字段名
        for field in ['home_xg', 'away_xg', 'home_possession', 'away_possession']:
            if field in match_data and match_data[field] is not None:
                setattr(match, field, match_data[field])

        # 现有模型可能没有赔率字段，暂时跳过赔率更新
        # 赔率数据可能存储在 JSON 字段中，需要特殊处理

        # 现有模型可能没有 data_completeness 和 updated_at 字段，暂时跳过这些更新
        return match

    def _create_match(self, match_data: Dict) -> Match:
        """创建新的比赛记录"""
        team_repo = TeamRepository(self.session)
        league_repo = LeagueRepository(self.session)

        # 获取或创建主客队
        home_team = team_repo.upsert_team(match_data['home_team'])
        away_team = team_repo.upsert_team(match_data['away_team'])

        # 获取或创建联赛
        league = None
        if 'league' in match_data:
            league = league_repo.upsert_league(match_data['league'])

        # 创建比赛记录，只使用现有模型中存在的字段
        match = Match(
            fotmob_id=match_data.get('external_id'),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id if league else None,
            match_date=match_data['match_date'],
            status=match_data.get('status', 'scheduled'),
            home_score=match_data.get('home_score'),
            away_score=match_data.get('away_score'),
            home_xg=match_data.get('home_xg'),
            away_xg=match_data.get('away_xg'),
            home_possession=match_data.get('home_possession'),  # 使用正确的字段名
            away_possession=match_data.get('away_possession'),   # 使用正确的字段名
            # 使用JSON字段存储其他数据
            odds={"home_win": match_data.get('home_win_odds'),
                  "draw": match_data.get('draw_odds'),
                  "away_win": match_data.get('away_win_odds')} if any(match_data.get(k) for k in ['home_win_odds', 'draw_odds', 'away_win_odds']) else None
        )

        self.session.add(match)
        return match

    def _determine_winner(self, home_score: Optional[int], away_score: Optional[int]) -> Optional[str]:
        """根据比分确定胜者"""
        if home_score is None or away_score is None:
            return None

        if home_score > away_score:
            return 'home'
        elif away_score > home_score:
            return 'away'
        else:
            return 'draw'

    def get_match_by_external_id(self, external_id: str) -> Optional[Match]:
        """根据外部ID获取比赛"""
        return self.session.query(Match).filter(
            Match.fotmob_id == external_id
        ).first()

    def get_matches_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Match]:
        """获取日期范围内的比赛"""
        return self.session.query(Match).filter(
            and_(
                Match.match_date >= start_date,
                Match.match_date <= end_date
            )
        ).order_by(Match.match_date).all()

    def get_unprocessed_matches(self) -> List[Match]:
        """获取未处理的比赛（用于特征工程）"""
        return self.session.query(Match).filter(
            Match.is_processed == False
        ).all()