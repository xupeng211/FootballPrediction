"""
特征计算器
Feature Calculator

负责计算各种特征。
"""




class FeatureCalculator(BaseCalculator):
    """扩展的特征计算器"""

    async def calculate_and_store_team_features(
        self,
        team_id: int,
        calculation_date: Optional[datetime] = None,
        repository=None,
    ) -> bool:
        """
        计算并存储球队特征

        Args:
            team_id: 球队ID
            calculation_date: 计算日期
            repository: 特征仓库实例

        Returns:
            bool: 存储是否成功
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        try:
            # 计算特征
            features = await self.calculate_recent_performance_features(
                team_id, calculation_date
            )

            # 转换为 DataFrame
            df = pd.DataFrame(
                [
                    {
                        "team_id": features.team_id,
                        "recent_5_wins": features.recent_5_wins,
                        "recent_5_draws": features.recent_5_draws,
                        "recent_5_losses": features.recent_5_losses,
                        "recent_5_goals_for": features.recent_5_goals_for,
                        "recent_5_goals_against": features.recent_5_goals_against,
                        "recent_5_points": features.recent_5_points,
                        "recent_5_home_wins": features.recent_5_home_wins,
                        "recent_5_away_wins": features.recent_5_away_wins,
                        "recent_5_home_goals_for": features.recent_5_home_goals_for,
                        "recent_5_away_goals_for": features.recent_5_away_goals_for,
                        "event_timestamp": calculation_date,
                    }
                ]
            )

            # 推送到在线存储
            if repository:
                return await repository.push_features_to_online_store(
                    "team_recent_performance", df
                )
            else:
                # 如果没有仓库，直接推送到 Feast 存储

                store = FeatureStore()
                store.push(push_source_name="team_recent_performance_push_source", df=df)
                return True

        except Exception as e:
            print(f"计算并存储球队特征失败: {e}")
            return False

    async def calculate_and_store_match_features(
        self,
        match_entity: MatchEntity,
        calculation_date: Optional[datetime] = None,
        repository=None,
    ) -> bool:
        """
        计算并存储比赛特征

        Args:
            match_entity: 比赛实体
            calculation_date: 计算日期
            repository: 特征仓库实例

        Returns:
            bool: 存储是否成功
        """
        if calculation_date is None:
            calculation_date = match_entity.match_time

        try:
            # 计算历史对战特征



            h2h_features = await self.calculate_historical_matchup_features(
                match_entity.home_team_id, match_entity.away_team_id, calculation_date
            )

            # 计算赔率特征
            odds_features = await self.calculate_odds_features(
                match_entity.match_id, calculation_date
            )

            # 存储历史对战特征
            h2h_df = pd.DataFrame(
                [
                    {
                        "match_id": match_entity.match_id,
                        "home_team_id": h2h_features.home_team_id,
                        "away_team_id": h2h_features.away_team_id,
                        "h2h_total_matches": h2h_features.h2h_total_matches,
                        "h2h_home_wins": h2h_features.h2h_home_wins,
                        "h2h_away_wins": h2h_features.h2h_away_wins,
                        "h2h_draws": h2h_features.h2h_draws,
                        "h2h_home_goals_total": h2h_features.h2h_home_goals_total,
                        "h2h_away_goals_total": h2h_features.h2h_away_goals_total,
                        "event_timestamp": calculation_date,
                    }
                ]
            )

            # 存储赔率特征
            odds_df = pd.DataFrame(
                [
                    {
                        "match_id": odds_features.match_id,
                        "home_odds_avg": (
                            float(odds_features.home_odds_avg)
                            if odds_features.home_odds_avg
                            else None
                        ),
                        "draw_odds_avg": (
                            float(odds_features.draw_odds_avg)
                            if odds_features.draw_odds_avg
                            else None
                        ),
                        "away_odds_avg": (
                            float(odds_features.away_odds_avg)
                            if odds_features.away_odds_avg
                            else None
                        ),
                        "home_implied_probability": odds_features.home_implied_probability,
                        "draw_implied_probability": odds_features.draw_implied_probability,
                        "away_implied_probability": odds_features.away_implied_probability,
                        "bookmaker_count": odds_features.bookmaker_count,
                        "bookmaker_consensus": odds_features.bookmaker_consensus,
                        "event_timestamp": calculation_date,
                    }
                ]
            )

            # 推送到在线存储
            if repository:
                h2h_success = await repository.push_features_to_online_store(
                    "historical_matchup", h2h_df
                )
                odds_success = await repository.push_features_to_online_store(
                    "odds_features", odds_df
                )
            else:
                # 如果没有仓库，直接推送到 Feast 存储

                store = FeatureStore()
                store.push(push_source_name="historical_matchup_push_source", df=h2h_df)
                store.push(push_source_name="odds_features_push_source", df=odds_df)
                h2h_success = odds_success = True

            return h2h_success and odds_success

        except Exception as e:
            print(f"计算并存储比赛特征失败: {e}")
            return False