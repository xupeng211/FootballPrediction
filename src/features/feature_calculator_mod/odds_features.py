"""
赔率特征计算模块

负责计算与赔率相关的各种特征，包括平均赔率、方差、隐含概率等。
"""





class OddsFeaturesCalculator:
    """赔率特征计算器"""

    def __init__(self, db_manager: Any):
        """
        初始化计算器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager

    async def calculate(
        self,
        match_id: int,
        calculation_date: datetime,
        session: Optional[AsyncSession] = None,
    ) -> OddsFeatures:
        """
        计算赔率特征

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期
            session: 数据库会话（可选）

        Returns:
            OddsFeatures: 赔率特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_odds_features(
                    session, match_id, calculation_date
                )
        else:
            return await self._calculate_odds_features(
                session, match_id, calculation_date
            )

    async def _calculate_odds_features(
        self, session: AsyncSession, match_id: int, calculation_date: datetime
    ) -> OddsFeatures:
        """内部赔率特征计算逻辑"""

        # 查询比赛相关赔率
        odds_query = select(Odds).where(
            and_(
                Odds.match_id == match_id,
                Odds.collected_at <= calculation_date,
                Odds.market_type == "1x2",  # 胜平负市场
            )
        )

        result = await session.execute(odds_query)
        odds_list = result.scalars().all()

        # 初始化特征
        features = OddsFeatures(match_id=match_id, calculation_date=calculation_date)

        if not odds_list:
            return features

        # 提取赔率数据
        home_odds_values = []
        draw_odds_values = []
        away_odds_values = []

        for odds in odds_list:
            if odds.home_odds is not None:
                home_odds_values.append(float(odds.home_odds))
            if odds.draw_odds is not None:
                draw_odds_values.append(float(odds.draw_odds))
            if odds.away_odds is not None:
                away_odds_values.append(float(odds.away_odds))

        # 计算平均赔率
        if home_odds_values:
            features.home_odds_avg = Decimal(str(statistics.mean(home_odds_values)))
            features.max_home_odds = Decimal(str(max(home_odds_values)))
            features.min_home_odds = Decimal(str(min(home_odds_values)))
            features.odds_range_home = max(home_odds_values) - min(home_odds_values)
            features.odds_variance_home = (
                statistics.variance(home_odds_values)
                if len(home_odds_values) > 1
                else 0.0
            )

        if draw_odds_values:
            features.draw_odds_avg = Decimal(str(statistics.mean(draw_odds_values)))
            features.odds_variance_draw = (
                statistics.variance(draw_odds_values)
                if len(draw_odds_values) > 1
                else 0.0
            )

        if away_odds_values:
            features.away_odds_avg = Decimal(str(statistics.mean(away_odds_values)))
            features.odds_variance_away = (
                statistics.variance(away_odds_values)
                if len(away_odds_values) > 1
                else 0.0
            )

        # 计算隐含概率
        if features.home_odds_avg:
            features.home_implied_probability = 1.0 / float(features.home_odds_avg)
        if features.draw_odds_avg:
            features.draw_implied_probability = 1.0 / float(features.draw_odds_avg)
        if features.away_odds_avg:
            features.away_implied_probability = 1.0 / float(features.away_odds_avg)

        # 博彩公司数量
        features.bookmaker_count = len(set(odds.bookmaker for odds in odds_list))

        return features

    async def calculate_market_movement(
        self,
        match_id: int,
        calculation_date: datetime,
        hours_before_match: int = 24,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        计算赔率市场变动特征

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期
            hours_before_match: 比赛前多少小时的数据
            session: 数据库会话（可选）

        Returns:
            dict: 市场变动特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_market_movement(
                    session, match_id, calculation_date, hours_before_match
                )
        else:
            return await self._calculate_market_movement(
                session, match_id, calculation_date, hours_before_match
            )

    async def _calculate_market_movement(
        self,
        session: AsyncSession,
        match_id: int,
        calculation_date: datetime,
        hours_before_match: int,
    ) -> dict:
        """内部市场变动计算逻辑"""


        start_time = calculation_date - timedelta(hours=hours_before_match)

        odds_query = select(Odds).where(
            and_(
                Odds.match_id == match_id,
                Odds.collected_at.between(start_time, calculation_date),
                Odds.market_type == "1x2",
            )
        ).order_by(Odds.collected_at)

        result = await session.execute(odds_query)
        odds_list = result.scalars().all()

        if len(odds_list) < 2:
            return {"error": "Insufficient odds data for movement analysis"}

        # 按博彩公司分组
        bookmaker_odds = {}
        for odds in odds_list:
            if odds.bookmaker not in bookmaker_odds:
                bookmaker_odds[odds.bookmaker] = []
            bookmaker_odds[odds.bookmaker].append(odds)

        # 计算每个博彩公司的赔率变动
        movements = []
        for bookmaker, odds_data in bookmaker_odds.items():
            if len(odds_data) >= 2:
                first_odds = odds_data[0]
                last_odds = odds_data[-1]

                movement = {
                    "bookmaker": bookmaker,
                    "home_odds_change": float(last_odds.home_odds - first_odds.home_odds) if first_odds.home_odds and last_odds.home_odds else 0,
                    "draw_odds_change": float(last_odds.draw_odds - first_odds.draw_odds) if first_odds.draw_odds and last_odds.draw_odds else 0,
                    "away_odds_change": float(last_odds.away_odds - first_odds.away_odds) if first_odds.away_odds and last_odds.away_odds else 0,
                    "price_volatility": self._calculate_price_volatility(odds_data),
                }
                movements.append(movement)

        # 计算整体市场趋势
        avg_movements = self._calculate_average_movements(movements)

        return {
            "match_id": match_id,
            "analysis_period_hours": hours_before_match,
            "bookmaker_count": len(bookmaker_odds),
            "individual_movements": movements,
            "average_movements": avg_movements,
            "market_trend": self._determine_market_trend(avg_movements),
        }

    def _calculate_price_volatility(self, odds_data: List[Odds]) -> float:
        """计算价格波动率"""
        if len(odds_data) < 2:
            return 0.0

        home_odds = [float(o.home_odds) for o in odds_data if o.home_odds is not None]
        if len(home_odds) < 2:
            return 0.0

        return statistics.stdev(home_odds) if len(home_odds) > 1 else 0.0

    def _calculate_average_movements(self, movements: List[dict]) -> dict:
        """计算平均赔率变动"""
        if not movements:
            return {}

        return {
            "avg_home_odds_change": sum(m["home_odds_change"] for m in movements) / len(movements),
            "avg_draw_odds_change": sum(m["draw_odds_change"] for m in movements) / len(movements),
            "avg_away_odds_change": sum(m["away_odds_change"] for m in movements) / len(movements),
            "avg_price_volatility": sum(m["price_volatility"] for m in movements) / len(movements),
        }

    def _determine_market_trend(self, avg_movements: dict) -> str:
        """判断市场趋势"""
        if not avg_movements:
            return "unknown"

        home_change = avg_movements.get("avg_home_odds_change", 0)
        away_change = avg_movements.get("avg_away_odds_change", 0)

        if abs(home_change) < 0.05 and abs(away_change) < 0.05:
            return "stable"
        elif home_change > 0.1:
            return "home_drifting"
        elif home_change < -0.1:
            return "home_steam"
        elif away_change > 0.1:
            return "away_drifting"
        elif away_change < -0.1:
            return "away_steam"
        else:
            return "minor_movement"

    async def calculate_value_betting_features(
        self,
        match_id: int,
        calculation_date: datetime,
        true_probabilities: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        计算价值投注特征

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期
            true_probabilities: 真实概率（来自模型）
            session: 数据库会话（可选）

        Returns:
            dict: 价值投注特征
        """
        odds_features = await self.calculate(match_id, calculation_date, session)

        if not odds_features.home_odds_avg:
            return {"error": "No odds data available"}

        # 如果没有提供真实概率，使用隐含概率作为基准
        if true_probabilities is None:
            true_probabilities = {



                "home": odds_features.home_implied_probability,
                "draw": odds_features.draw_implied_probability,
                "away": odds_features.away_implied_probability,
            }

        # 计算价值
        value_features = {
            "match_id": match_id,
            "calculation_date": calculation_date,
            "average_odds": {
                "home": float(odds_features.home_odds_avg),
                "draw": float(odds_features.draw_odds_avg),
                "away": float(odds_features.away_odds_avg),
            },
            "implied_probabilities": {
                "home": odds_features.home_implied_probability,
                "draw": odds_features.draw_implied_probability,
                "away": odds_features.away_implied_probability,
            },
            "true_probabilities": true_probabilities,
        }

        # 计算期望价值和价值投注机会
        for outcome in ["home", "draw", "away"]:
            odds = float(getattr(odds_features, f"{outcome}_odds_avg", 0))
            true_prob = true_probabilities.get(outcome, 0)

            if odds > 0 and true_prob > 0:
                expected_value = (odds * true_prob) - 1
                value_features[f"{outcome}_expected_value"] = expected_value
                value_features[f"{outcome}_is_value_bet"] = expected_value > 0
                value_features[f"{outcome}_edge"] = expected_value * 100  # 百分比
            else:
                value_features[f"{outcome}_expected_value"] = 0
                value_features[f"{outcome}_is_value_bet"] = False
                value_features[f"{outcome}_edge"] = 0

        return value_features