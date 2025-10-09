"""
历史对战特征计算模块

负责计算两队之间的历史对战记录特征。
"""





class HistoricalMatchupCalculator:
    """历史对战特征计算器"""

    def __init__(self, db_manager: Any):
        """
        初始化计算器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager

    async def calculate(
        self,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
        session: Optional[AsyncSession] = None,
    ) -> HistoricalMatchupFeatures:
        """
        计算历史对战特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            calculation_date: 计算日期
            session: 数据库会话（可选）

        Returns:
            HistoricalMatchupFeatures: 历史对战特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_historical_matchup(
                    session, home_team_id, away_team_id, calculation_date
                )
        else:
            return await self._calculate_historical_matchup(
                session, home_team_id, away_team_id, calculation_date
            )

    async def _calculate_historical_matchup(
        self,
        session: AsyncSession,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
    ) -> HistoricalMatchupFeatures:
        """内部历史对战计算逻辑"""

        # 查询所有历史对战
        h2h_query = (
            select(Match)
            .where(
                and_(
                    or_(
                        and_(
                            Match.home_team_id == home_team_id,
                            Match.away_team_id == away_team_id,
                        ),
                        and_(
                            Match.home_team_id == away_team_id,
                            Match.away_team_id == home_team_id,
                        ),
                    ),
                    Match.match_time < calculation_date,
                    Match.match_status == MatchStatus.FINISHED,
                )
            )
            .order_by(desc(Match.match_time))
        )

        result = await session.execute(h2h_query)
        h2h_matches = result.scalars().all()

        # 初始化特征
        features = HistoricalMatchupFeatures(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            calculation_date=calculation_date,
        )

        total_matches = len(h2h_matches)
        home_wins = away_wins = draws = 0
        home_goals_total = away_goals_total = 0

        # 近5次对战统计
        recent_5_home_wins = recent_5_away_wins = recent_5_draws = 0

        for i, match in enumerate(h2h_matches):
            # 确定当前比赛的主客队
            if match.home_team_id == home_team_id:
                # 主队是home_team_id
                match_home_score = match.home_score or 0
                match_away_score = match.away_score or 0
            else:
                # 主队是away_team_id，需要调换
                match_home_score = match.away_score or 0
                match_away_score = match.home_score or 0

            home_goals_total += match_home_score
            away_goals_total += match_away_score

            # 计算胜负平
            if match_home_score > match_away_score:
                home_wins += 1
                if i < 5:  # 近5次
                    recent_5_home_wins += 1
            elif match_home_score == match_away_score:
                draws += 1
                if i < 5:  # 近5次
                    recent_5_draws += 1
            else:
                away_wins += 1
                if i < 5:  # 近5次
                    recent_5_away_wins += 1

        # 更新特征
        features.h2h_total_matches = total_matches
        features.h2h_home_wins = home_wins
        features.h2h_away_wins = away_wins
        features.h2h_draws = draws
        features.h2h_home_goals_total = home_goals_total
        features.h2h_away_goals_total = away_goals_total
        features.h2h_recent_5_home_wins = recent_5_home_wins
        features.h2h_recent_5_away_wins = recent_5_away_wins
        features.h2h_recent_5_draws = recent_5_draws

        return features

    async def calculate_extended_h2h(
        self,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
        match_limit: int = 20,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        计算扩展的历史对战统计

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            calculation_date: 计算日期
            match_limit: 查询的比赛数量限制
            session: 数据库会话（可选）

        Returns:
            dict: 扩展的历史对战统计
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_extended_h2h(
                    session, home_team_id, away_team_id, calculation_date, match_limit
                )
        else:
            return await self._calculate_extended_h2h(
                session, home_team_id, away_team_id, calculation_date, match_limit
            )

    async def _calculate_extended_h2h(
        self,
        session: AsyncSession,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
        match_limit: int,
    ) -> dict:
        """内部扩展历史对战计算逻辑"""

        h2h_query = (
            select(Match)
            .where(
                and_(
                    or_(
                        and_(
                            Match.home_team_id == home_team_id,
                            Match.away_team_id == away_team_id,
                        ),
                        and_(
                            Match.home_team_id == away_team_id,
                            Match.away_team_id == home_team_id,
                        ),
                    ),
                    Match.match_time < calculation_date,
                    Match.match_status == MatchStatus.FINISHED,
                )
            )
            .order_by(desc(Match.match_time))
            .limit(match_limit)
        )

        result = await session.execute(h2h_query)
        h2h_matches = result.scalars().all()

        stats = {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "calculation_date": calculation_date,
            "total_matches": len(h2h_matches),
            "home_wins": 0,
            "away_wins": 0,
            "draws": 0,
            "home_goals": 0,
            "away_goals": 0,
            "both_teams_score": 0,
            "over_2_5_goals": 0,
            "home_clean_sheets": 0,
            "away_clean_sheets": 0,
            "home_advantage": {"wins": 0, "goals": 0},
            "recent_form": {"home": [], "away": []},
        }

        for match in h2h_matches:
            # 确定主客队得分
            if match.home_team_id == home_team_id:
                home_score = match.home_score or 0
                away_score = match.away_score or 0
                is_home_team = True
            else:
                home_score = match.away_score or 0
                away_score = match.home_score or 0
                is_home_team = False

            # 基础统计
            stats["home_goals"] += home_score
            stats["away_goals"] += away_score

            # 胜负平统计
            if home_score > away_score:
                stats["home_wins"] += 1
                if is_home_team:
                    stats["home_advantage"]["wins"] += 1
            elif home_score == away_score:
                stats["draws"] += 1
            else:
                stats["away_wins"] += 1

            # 进球相关统计
            if home_score > 0 and away_score > 0:
                stats["both_teams_score"] += 1
            if home_score + away_score > 2:
                stats["over_2_5_goals"] += 1

            # 零封统计
            if home_score == 0:
                stats["home_clean_sheets"] += 1
            if away_score == 0:
                stats["away_clean_sheets"] += 1

            # 主场优势进球
            if is_home_team:
                stats["home_advantage"]["goals"] += home_score

            # 记录最近表现
            if len(stats["recent_form"]["home"]) < 5:
                if is_home_team:
                    result = "W" if home_score > away_score else "D" if home_score == away_score else "L"
                    stats["recent_form"]["home"].append(result)
                else:
                    result = "W" if away_score > home_score else "D" if away_score == home_score else "L"
                    stats["recent_form"]["away"].append(result)

        # 计算衍生指标
        total = len(h2h_matches)
        if total > 0:
            stats["home_win_rate"] = stats["home_wins"] / total
            stats["away_win_rate"] = stats["away_wins"] / total
            stats["draw_rate"] = stats["draws"] / total
            stats["avg_home_goals"] = stats["home_goals"] / total
            stats["avg_away_goals"] = stats["away_goals"] / total
            stats["avg_total_goals"] = (stats["home_goals"] + stats["away_goals"]) / total
            stats["both_teams_score_rate"] = stats["both_teams_score"] / total
            stats["over_2_5_rate"] = stats["over_2_5_goals"] / total
        else:
            stats.update({
                "home_win_rate": 0.0,
                "away_win_rate": 0.0,
                "draw_rate": 0.0,
                "avg_home_goals": 0.0,
                "avg_away_goals": 0.0,
                "avg_total_goals": 0.0,
                "both_teams_score_rate": 0.0,
                "over_2_5_rate": 0.0,
            })

        return stats

    def calculate_head_to_head_trend(
        self, h2h_matches: list, recent_matches: int = 5
    ) -> dict:
        """
        分析历史对战趋势

        Args:
            h2h_matches: 历史对战比赛列表
            recent_matches: 分析的最近比赛数量

        Returns:
            dict: 对战趋势分析
        """
        if not h2h_matches:
            return {"trend": "no_data", "dominance": "balanced"}

        recent_matches = h2h_matches[:recent_matches]
        home_wins = sum(1 for m in recent_matches if m.home_score > m.away_score)
        away_wins = sum(1 for m in recent_matches if m.away_score > m.home_score)



        draws = sum(1 for m in recent_matches if m.home_score == m.away_score)

        # 判断趋势
        if home_wins > away_wins + draws:
            trend = "home_dominant"
        elif away_wins > home_wins + draws:
            trend = "away_dominant"
        elif draws > home_wins and draws > away_wins:
            trend = "drawish"
        else:
            trend = "balanced"

        return {
            "trend": trend,
            "dominance": "home" if home_wins > away_wins else "away" if away_wins > home_wins else "balanced",
            "recent_home_wins": home_wins,
            "recent_away_wins": away_wins,
            "recent_draws": draws,
            "analyzed_matches": len(recent_matches),
        }