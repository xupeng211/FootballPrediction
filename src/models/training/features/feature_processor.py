"""
from src.database.models import Match, MatchStatus
from src.features.feature_store import FootballFeatureStore

特征处理器

负责处理训练数据的获取和预处理
"""





logger = logging.getLogger(__name__)


class FeatureProcessor:
    """特征处理器"""

    def __init__(self):
        """初始化特征处理器"""
        self.db_manager = DatabaseManager()
        self.feature_store = FootballFeatureStore()

        # 特征配置
        self.feature_refs = [
            # 球队近期表现特征
            "team_recent_performance:recent_5_wins",
            "team_recent_performance:recent_5_draws",
            "team_recent_performance:recent_5_losses",
            "team_recent_performance:recent_5_goals_for",
            "team_recent_performance:recent_5_goals_against",
            "team_recent_performance:recent_5_points",
            "team_recent_performance:recent_5_home_wins",
            "team_recent_performance:recent_5_away_wins",
            # 历史对战特征
            "historical_matchup:h2h_total_matches",
            "historical_matchup:h2h_home_wins",
            "historical_matchup:h2h_away_wins",
            "historical_matchup:h2h_draws",
            "historical_matchup:h2h_recent_5_home_wins",
            "historical_matchup:h2h_recent_5_away_wins",
            # 赔率特征
            "odds_features:home_odds_avg",
            "odds_features:draw_odds_avg",
            "odds_features:away_odds_avg",
            "odds_features:home_implied_probability",
            "odds_features:draw_implied_probability",
            "odds_features:away_implied_probability",
            "odds_features:bookmaker_count",
        ]

    async def prepare_training_data(
        self, start_date: datetime, end_date: datetime, min_samples: int = 1000
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        从特征仓库获取训练数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            min_samples: 最小样本数量

        Returns:
            特征DataFrame和目标变量Series
        """
        logger.info(f"开始准备训练数据，时间范围：{start_date} 到 {end_date}")

        # 获取历史比赛数据
        matches_df = await self._get_historical_matches(start_date, end_date)
        logger.info(f"获取到 {len(matches_df)} 场历史比赛")

        if len(matches_df) < min_samples:
            raise ValueError(
                f"训练数据不足，需要至少 {min_samples} 条记录，实际获取 {len(matches_df)} 条"
            )

        # 准备实体DataFrame用于特征获取
        entity_df = pd.DataFrame(
            {
                "match_id": matches_df["id"],
                "team_id": matches_df["home_team_id"],  # Feast需要团队ID作为实体
                "event_timestamp": matches_df["match_time"],
            }
        )

        # 从Feast特征存储获取特征
        logger.info("从特征仓库获取特征数据...")
        try:
            features_df = await self.feature_store.get_historical_features(
                entity_df=entity_df,
                feature_refs=self.feature_refs,
                full_feature_names=True,
            )
            logger.info(f"获取到 {len(features_df)} 条特征记录")
        except Exception as e:
            logger.error(f"从特征仓库获取特征失败: {e}")
            # 如果特征仓库失败，使用简化特征
            features_df = await self._get_simplified_features(matches_df)
            logger.info(f"使用简化特征，获取到 {len(features_df)} 条记录")

        # 合并比赛结果作为目标变量
        features_df = features_df.merge(
            matches_df[["id", "result"]], left_on="match_id", right_on="id", how="inner"
        )

        # 分离特征和目标变量
        target_col = "result"
        feature_cols = [
            col
            for col in features_df.columns
            if col not in ["match_id", "team_id", "event_timestamp", "id", target_col]
        ]

        X = features_df[feature_cols].fillna(0)  # 填充缺失值
        y = features_df[target_col]

        logger.info(f"训练数据准备完成：{len(X)} 条样本，{len(feature_cols)} 个特征")
        return X, y

    async def _get_historical_matches(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """获取历史比赛数据"""
        async with self.db_manager.get_async_session() as session:
            # 查询已完成的比赛
            query = (
                select(
                    Match.id,
                    Match.home_team_id,
                    Match.away_team_id,
                    Match.league_id,
                    Match.match_time,
                    Match.home_score,
                    Match.away_score,
                    Match.season,
                )
                .where(
                    and_(
                        Match.match_time >= start_date,
                        Match.match_time <= end_date,
                        Match.match_status == MatchStatus.FINISHED,
                        Match.home_score.isnot(None),
                        Match.away_score.isnot(None),
                    )
                )
                .order_by(Match.match_time)
            )

            result = await session.execute(query)
            matches = result.fetchall()

            # 转换为DataFrame
            df = pd.DataFrame(
                [
                    {
                        "id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time,
                        "home_score": match.home_score,
                        "away_score": match.away_score,
                        "season": match.season,
                    }
                    for match in matches
                ]
            )

            if not df.empty:
                # 计算比赛结果
                df["result"] = df.apply(calculate_match_result, axis=1)

            return df

    async def _get_simplified_features(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """获取简化特征（当特征仓库不可用时）"""
        features_list = []

        async with self.db_manager.get_async_session() as session:
            for _, match in matches_df.iterrows():
                # 计算简化特征
                home_features = await self._calculate_team_simple_features(
                    session, match["home_team_id"], match["match_time"]
                )
                away_features = await self._calculate_team_simple_features(
                    session, match["away_team_id"], match["match_time"]
                )

                # 组合特征
                match_features = {
                    "match_id": match["id"],
                    "team_id": match["home_team_id"],
                    "event_timestamp": match["match_time"],
                    # 主队特征
                    "home_recent_wins": home_features["recent_wins"],
                    "home_recent_goals_for": home_features["recent_goals_for"],
                    "home_recent_goals_against": home_features["recent_goals_against"],
                    # 客队特征
                    "away_recent_wins": away_features["recent_wins"],
                    "away_recent_goals_for": away_features["recent_goals_for"],
                    "away_recent_goals_against": away_features["recent_goals_against"],
                    # 对战特征
                    "h2h_home_advantage": 0.5,  # 默认值
                }

                features_list.append(match_features)

        return pd.DataFrame(features_list)

    async def _calculate_team_simple_features(
        self, session: AsyncSession, team_id: int, match_time: datetime
    ) -> Dict[str, Any]:
        """计算球队简化特征"""
        # 查询最近5场比赛
        recent_matches_query = (
            select(Match)
            .where(
                and_(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.match_time < match_time,
                    Match.match_status == MatchStatus.FINISHED,
                )
            )



            .order_by(desc(Match.match_time))
            .limit(5)
        )

        result = await session.execute(recent_matches_query)
        recent_matches = result.scalars().all()

        # 计算统计指标
        wins = 0
        goals_for = 0
        goals_against = 0

        for match in recent_matches:
            if match.home_team_id == team_id:
                # 主场比赛
                if match.home_score > match.away_score:
                    wins += 1
                goals_for += match.home_score or 0
                goals_against += match.away_score or 0
            else:
                # 客场比赛
                if match.away_score > match.home_score:
                    wins += 1
                goals_for += match.away_score or 0
                goals_against += match.home_score or 0

        return {
            "recent_wins": wins,
            "recent_goals_for": goals_for,
            "recent_goals_against": goals_against,
        }