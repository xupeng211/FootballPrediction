"""
赔率分析器
Odds Analyzer

分析赔率数据，识别价值投注机会
"""


logger = logging.getLogger(__name__)


class OddsAnalyzer:
    """赔率分析器"""

    def __init__(self, redis_manager=None):
        """
        初始化分析器

        Args:
            redis_manager: Redis管理器
        """
        self.redis_manager = redis_manager

    async def identify_value_bets(
        self, odds_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        识别价值投注机会

        Args:
            odds_data: 赔率数据

        Returns:
            价值投注列表
        """
        value_bets = []

        # 获取模型预测概率（如果有）
        match_id = odds_data["match_id"]
        model_prob = await self._get_model_prediction(match_id)

        if not model_prob:
            return value_bets

        # 比较博彩公司赔率和模型预测
        for bookmaker in odds_data.get("bookmakers", []):
            # 计算凯利值
            for outcome in ["home_win", "draw", "away_win"]:
                bookmaker_odds = bookmaker[outcome]
                model_outcome = outcome.replace("_win", "")
                model_probability = model_prob.get(model_outcome, 0)

                if bookmaker_odds and model_probability > 0:
                    # 计算价值
                    implied_prob = 1 / bookmaker_odds
                    value = (bookmaker_odds * model_probability) - 1

                    if value > 0:  # 有价值
                        # 计算凯利比例
                        kelly_fraction = (bookmaker_odds * model_probability - 1) / (
                            bookmaker_odds - 1
                        )

                        # 风险评估
                        risk_level = self._assess_risk(value, model_probability)

                        value_bets.append(
                            {
                                "bookmaker": bookmaker["name"],
                                "outcome": outcome,
                                "odds": bookmaker_odds,
                                "model_probability": model_probability,
                                "implied_probability": implied_prob,
                                "value": value,
                                "kelly_fraction": kelly_fraction,
                                "expected_value": value * 100,  # 百分比
                                "risk_level": risk_level,
                                "confidence": self._calculate_confidence(
                                    value, model_probability
                                ),
                            }
                        )

        # 按价值排序
        value_bets.sort(key=lambda x: x["value"], reverse=True)

        return value_bets[:5]  # 返回前5个价值最高的投注

    async def _get_model_prediction(self, match_id: int) -> Optional[Dict[str, float]]:
        """
        获取模型预测概率

        Args:
            match_id: 比赛ID

        Returns:
            预测概率
        """
        try:
            if not self.redis_manager:
                return None

            # 从Redis缓存获取预测
            cache_key = f"model_prediction:{match_id}"
            prediction = await self.redis_manager.aget(cache_key)

            if prediction:
                return {
                    "home": prediction.get("home_win_probability", 0),
                    "draw": prediction.get("draw_probability", 0),
                    "away": prediction.get("away_win_probability", 0),
                }

            # 这里可以添加从数据库获取预测的逻辑
            return None

        except Exception as e:
            logger.error(f"获取模型预测失败: {e}")
            return None

    def _assess_risk(self, value: float, probability: float) -> str:
        """
        评估风险等级

        Args:
            value: 价值
            probability: 概率

        Returns:
            风险等级
        """
        if value > 0.2 and probability > 0.6:
            return "low"
        elif value > 0.1 and probability > 0.5:
            return "medium"
        else:
            return "high"

    def _calculate_confidence(self, value: float, probability: float) -> str:
        """
        计算置信度

        Args:
            value: 价值
            probability: 概率

        Returns:
            置信度
        """
        if value > 0.2 and probability > 0.65:
            return "high"
        elif value > 0.05 and probability > 0.45:
            return "medium"
        else:
            return "low"

    def analyze_market_efficiency(
        self, odds_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析市场效率

        Args:
            odds_data: 赔率数据

        Returns:
            市场效率分析
        """
        analysis = {
            "bookmaker_count": len(odds_data.get("bookmakers", [])),
            "margin_analysis": {},
            "price_discrepancy": {},
            "market_consensus": {},
        }

        # 分析博彩公司边际
        margins = []
        for bookmaker in odds_data.get("bookmakers", []):
            # 计算隐含概率
            total_prob = 0
            for outcome in ["home_win", "draw", "away_win"]:
                if outcome in bookmaker and bookmaker[outcome]:
                    total_prob += 1 / bookmaker[outcome]

            margin = (total_prob - 1) * 100
            margins.append(margin)

        if margins:
            analysis["margin_analysis"] = {
                "average_margin": sum(margins) / len(margins),
                "min_margin": min(margins),
                "max_margin": max(margins),
                "margin_range": max(margins) - min(margins),
            }

        # 分析价格离散度
        if odds_data.get("best_odds") and odds_data.get("average_odds"):
            best = odds_data["best_odds"]
            avg = odds_data["average_odds"]

            for outcome in ["home_win", "draw", "away_win"]:
                if outcome in best and outcome in avg:
                    discrepancy = ((best[outcome] - avg[outcome]) / avg[outcome]) * 100
                    analysis["price_discrepancy"][outcome] = discrepancy

        return analysis

    def calculate_arbitrage_opportunities(
        self, odds_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        计算套利机会

        Args:
            odds_data: 赔率数据

        Returns:
            套利机会列表
        """
        opportunities = []


        # 收集所有博彩公司的最佳赔率
        best_home = {"odds": 0, "bookmaker": None}
        best_draw = {"odds": 0, "bookmaker": None}
        best_away = {"odds": 0, "bookmaker": None}

        for bookmaker in odds_data.get("bookmakers", []):
            if bookmaker.get("home_win", 0) > best_home["odds"]:
                best_home = {"odds": bookmaker["home_win"], "bookmaker": bookmaker["name"]}

            if bookmaker.get("draw", 0) > best_draw["odds"]:
                best_draw = {"odds": bookmaker["draw"], "bookmaker": bookmaker["name"]}

            if bookmaker.get("away_win", 0) > best_away["odds"]:
                best_away = {"odds": bookmaker["away_win"], "bookmaker": bookmaker["name"]}

        # 检查套利机会
        if all([best_home["odds"], best_draw["odds"], best_away["odds"]]):
            # 计算总隐含概率
            total_implied = (
                1 / best_home["odds"] +
                1 / best_draw["odds"] +
                1 / best_away["odds"]
            )

            if total_implied < 1:
                # 发现套利机会
                profit_margin = (1 - total_implied) * 100

                opportunities.append({
                    "type": "three-way arbitrage",
                    "home": best_home,
                    "draw": best_draw,
                    "away": best_away,
                    "total_implied_probability": total_implied,
                    "profit_margin": profit_margin,
                    "investment_distribution": {
                        "home": (1 / best_home["odds"]) / total_implied,
                        "draw": (1 / best_draw["odds"]) / total_implied,
                        "away": (1 / best_away["odds"]) / total_implied,
                    }
                })

        return opportunities