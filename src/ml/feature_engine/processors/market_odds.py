"""
MarketOddsProcessor - 市场赔率与偏见处理器
==============================================

负责提取市场赔率层面的深度特征，包括:
    - 博彩公司抽水率（识别比赛离散度）
    - 平局偏见分析（市场对平局的倾向）
    - 隐含概率偏差（市场与模型预期差异）

设计模式:
    - 套利分析: 从赔率中提取市场预期
    - 偏见检测: 识别市场非理性定价
    - 概率校准: 赔率转隐含概率

作者: FootballPrediction Architecture Team
版本: V23.0-alpha
"""

from typing import Any, Dict, Optional
import logging
import statistics
from decimal import Decimal

from ..base import BaseProcessor, ProcessorResult, ProcessorConfig
from ..models import MatchData

logger = logging.getLogger(__name__)


class MarketOddsProcessorConfig(ProcessorConfig):
    """
    MarketOddsProcessor 配置

    Attributes:
        enable_bias_analysis: 是否启用偏见分析
        enable_margin_calculation: 是否启用抽水率计算
        overround_threshold: 抽水率阈值（超过则警告）
        min_bookmakers: 最少博彩公司数量（确保数据可靠性）
    """
    enable_bias_analysis: bool = True
    enable_margin_calculation: bool = True
    overround_threshold: float = 0.08  # 8% 抽水率阈值
    min_bookmakers: int = 3


class MarketOddsProcessor(BaseProcessor[MatchData]):
    """
    市场赔率与偏见处理器

    职责:
        1. 解析赔率数据（从 content.odds 或 metadata 注入）
        2. 计算博彩公司抽水率（识别比赛离散度）
        3. 分析平局偏见（市场对平局的倾向）
        4. 计算隐含概率偏差（市场 vs 模型）

    特征输出:
        - odds_home_win, odds_draw, odds_away_win: 平均赔率
        - odds_bookmaker_margin: 抽水率（识别离散度）
        - odds_draw_bias: 平局偏见指数
        - odds_implied_prob_home/away/draw: 隐含概率
        - odds_market_confidence: 市场信心度
        - odds_price_volatility: 赔率波动率
        - odds_value_bet_home/away/draw: 价值投注指数

    数据来源:
        - content.odds.* (FotMob API 内置赔率)
        - metadata.odds (外部注入赔率数据)

    Example:
        >>> processor = MarketOddsProcessor()
        >>> result = processor.execute(match_data)
        >>> print(result.data["odds_bookmaker_margin"])
        0.065  # 6.5% 抽水率
    """

    processor_name = "MarketOddsProcessor"
    processor_version = "23.0.0"
    priority = 55  # 在 LineupValueProcessor 之后执行

    def __init__(self, config: Optional[MarketOddsProcessorConfig] = None) -> None:
        super().__init__(config or MarketOddsProcessorConfig())
        self.config: MarketOddsProcessorConfig = self.config

    def process(
        self, data: MatchData, context: Any
    ) -> ProcessorResult:
        """
        提取市场赔率特征

        Args:
            data: 比赛数据
            context: 处理上下文

        Returns:
            ProcessorResult: 包含赔率特征的处理器结果
        """
        features: Dict[str, float] = {}
        warnings: list[str] = []

        try:
            # 1. 提取赔率数据
            odds_data = self._extract_odds_data(data, context)

            if not odds_data:
                logger.warning(f"No odds data available for match {data.match_id}")
                # 返回默认值（零填充）
                return self._create_default_result(warnings)

            # 2. 解析赔率（主/平/客）
            home_odds, draw_odds, away_odds = self._parse_odds(odds_data)

            if not all([home_odds, draw_odds, away_odds]):
                warnings.append("incomplete_odds_data")
                return self._create_default_result(warnings)

            # 3. 基础赔率特征
            features["odds_home_win"] = round(home_odds, 4)
            features["odds_draw"] = round(draw_odds, 4)
            features["odds_away_win"] = round(away_odds, 4)

            # 4. 抽水率计算
            if self.config.enable_margin_calculation:
                margin_features = self._compute_margin_features(
                    home_odds, draw_odds, away_odds
                )
                features.update(margin_features)

            # 5. 平局偏见分析
            if self.config.enable_bias_analysis:
                bias_features = self._analyze_draw_bias(
                    home_odds, draw_odds, away_odds
                )
                features.update(bias_features)

            # 6. 隐含概率计算
            prob_features = self._compute_implied_probabilities(
                home_odds, draw_odds, away_odds
            )
            features.update(prob_features)

            # 7. 市场信心度
            confidence_features = self._compute_market_confidence(
                odds_data, home_odds, draw_odds, away_odds
            )
            features.update(confidence_features)

            # 8. 价值投注指数
            value_features = self._compute_value_indices(features)
            features.update(value_features)

            result = ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "odds_source": odds_data.get("source", "unknown"),
                }
            )

            # 添加警告
            for warning in warnings:
                result.with_warning(warning)

            return result

        except Exception as e:
            logger.error(f"MarketOddsProcessor failed for match {data.match_id}: {e}")
            return ProcessorResult.failure_result(str(e))

    def _extract_odds_data(
        self, data: MatchData, context: Any
    ) -> Optional[Dict[str, Any]]:
        """
        提取赔率数据

        数据来源优先级:
            1. context.odds (外部注入)
            2. data.raw_data.content.odds (FotMob API)
            3. data.raw_data.general.providersOdds (备用)

        Args:
            data: 比赛数据
            context: 处理上下文

        Returns:
            赔率数据字典，如果无数据则返回 None
        """
        # 优先从 context 获取外部注入的赔率
        if context and context.get_cached("odds"):
            odds_data = context.get_cached("odds")
            odds_data["source"] = "external_injection"
            return odds_data

        # 从 raw_data 中提取
        if data.raw_data:
            # 尝试 content.odds 路径
            content = data.raw_data.get("content", {})
            if "odds" in content:
                odds = content["odds"]
                odds["source"] = "content_odds"
                return odds

            # 尝试 general.providersOdds 路径
            general = data.raw_data.get("general", {})
            if "providersOdds" in general:
                odds = {"providers": general["providersOdds"]}
                odds["source"] = "general_odds"
                return odds

        return None

    def _parse_odds(
        self, odds_data: Dict[str, Any]
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        解析赔率数据

        支持多种数据格式:
            - {"home": 2.50, "draw": 3.20, "away": 2.80}
            - {"providers": [...]} (多博彩公司平均)

        Args:
            odds_data: 赔率数据

        Returns:
            (主胜赔率, 平局赔率, 客胜赔率)
        """
        # 格式 1: 直接的 home/draw/away
        if "home" in odds_data and "draw" in odds_data and "away" in odds_data:
            return (
                float(odds_data["home"]),
                float(odds_data["draw"]),
                float(odds_data["away"]),
            )

        # 格式 2: providers 列表（取平均）
        if "providers" in odds_data:
            providers = odds_data["providers"]
            if not providers or len(providers) < self.config.min_bookmakers:
                return None, None, None

            home_odds_list = []
            draw_odds_list = []
            away_odds_list = []

            for provider in providers:
                # 适配不同数据结构的赔率字段
                home_odds = self._extract_provider_odds(provider, "home")
                draw_odds = self._extract_provider_odds(provider, "draw")
                away_odds = self._extract_provider_odds(provider, "away")

                if home_odds:
                    home_odds_list.append(home_odds)
                if draw_odds:
                    draw_odds_list.append(draw_odds)
                if away_odds:
                    away_odds_list.append(away_odds)

            if home_odds_list and draw_odds_list and away_odds_list:
                # 使用中位数（更稳健）
                return (
                    statistics.median(home_odds_list),
                    statistics.median(draw_odds_list),
                    statistics.median(away_odds_list),
                )

        return None, None, None

    def _extract_provider_odds(
        self, provider: Dict[str, Any], outcome: str
    ) -> Optional[float]:
        """从单个博彩公司数据中提取赔率"""
        # 常见字段名变体
        possible_keys = [
            outcome,  # "home", "draw", "away"
            f"{outcome}Odds",
            f"odds{outcome.capitalize()}",
            outcome + "_price",
            outcome + "_odd",
        ]

        for key in possible_keys:
            if key in provider:
                value = provider[key]
                if isinstance(value, (int, float)):
                    return float(value)
                # 如果是字符串，尝试解析
                if isinstance(value, str):
                    try:
                        return float(value)
                    except ValueError:
                        continue

        return None

    def _compute_margin_features(
        self,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
    ) -> Dict[str, float]:
        """
        计算抽水率特征

        抽水率 (Overround) = (1/home + 1/draw + 1/away) - 1

        抽水率越高，博彩公司利润空间越大，市场离散度越高
        """
        features = {}

        # 计算隐含概率
        home_prob = 1.0 / home_odds
        draw_prob = 1.0 / draw_odds
        away_prob = 1.0 / away_odds

        # 抽水率
        margin = home_prob + draw_prob + away_prob - 1.0
        features["odds_bookmaker_margin"] = round(margin, 4)

        # 抽水率分类
        if margin < 0.02:
            features["odds_margin_category"] = 0  # 极低（罕见）
        elif margin < 0.05:
            features["odds_margin_category"] = 1  # 低（竞争激烈）
        elif margin < 0.08:
            features["odds_margin_category"] = 2  # 正常
        else:
            features["odds_margin_category"] = 3  # 高（离散度高）

        # 真实概率（去除抽水）
        if margin > 0:
            total_prob = home_prob + draw_prob + away_prob
            features["odds_real_prob_home"] = round(home_prob / total_prob, 4)
            features["odds_real_prob_draw"] = round(draw_prob / total_prob, 4)
            features["odds_real_prob_away"] = round(away_prob / total_prob, 4)
        else:
            features["odds_real_prob_home"] = round(home_prob, 4)
            features["odds_real_prob_draw"] = round(draw_prob, 4)
            features["odds_real_prob_away"] = round(away_prob, 4)

        return features

    def _analyze_draw_bias(
        self,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
    ) -> Dict[str, float]:
        """
        分析平局偏见

        计算市场对平局的倾向程度：
        - 如果 draw_odds 相对较低，说明市场认为平局概率高
        """
        features = {}

        # 平局隐含概率
        draw_implied_prob = 1.0 / draw_odds
        home_implied_prob = 1.0 / home_odds
        away_implied_prob = 1.0 / away_odds

        # 平局偏见指数（实际概率 vs "公平"概率）
        # 在无偏见情况下，平局概率通常约 25-27%
        expected_draw_prob = 0.26
        features["odds_draw_bias"] = round(draw_implied_prob - expected_draw_prob, 4)

        # 平局相对赔率（vs 主/客胜）
        features["odds_draw_vs_home"] = round(draw_odds / home_odds, 4)
        features["odds_draw_vs_away"] = round(draw_odds / away_odds, 4)

        # 平局赔率离散度（评估市场对平局的不确定性）
        total_implied = draw_implied_prob + home_implied_prob + away_implied_prob
        if total_implied > 0:
            features["odds_draw_concentration"] = round(draw_implied_prob / total_implied, 4)
        else:
            features["odds_draw_concentration"] = 0.0

        # 平局预期分类
        if features["odds_draw_bias"] > 0.05:
            features["odds_draw_sentiment"] = 2  # 看好平局
        elif features["odds_draw_bias"] < -0.05:
            features["odds_draw_sentiment"] = 0  # 看衰平局
        else:
            features["odds_draw_sentiment"] = 1  # 中性

        return features

    def _compute_implied_probabilities(
        self,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
    ) -> Dict[str, float]:
        """计算隐含概率（未经抽水调整）"""
        features = {}

        features["odds_implied_prob_home"] = round(1.0 / home_odds, 4)
        features["odds_implied_prob_draw"] = round(1.0 / draw_odds, 4)
        features["odds_implied_prob_away"] = round(1.0 / away_odds, 4)

        # 最可能结果
        probs = {
            "home": features["odds_implied_prob_home"],
            "draw": features["odds_implied_prob_draw"],
            "away": features["odds_implied_prob_away"],
        }
        most_likely = max(probs.items(), key=lambda x: x[1])

        # 最可能结果编码
        if most_likely[0] == "home":
            features["odds_favorite"] = 1  # 主队
        elif most_likely[0] == "draw":
            features["odds_favorite"] = 2  # 平局
        else:
            features["odds_favorite"] = 3  # 客队

        # 领先优势
        sorted_probs = sorted(probs.values(), reverse=True)
        if len(sorted_probs) >= 2:
            features["odds_favorite_margin"] = round(
                sorted_probs[0] - sorted_probs[1], 4
            )
        else:
            features["odds_favorite_margin"] = 0.0

        return features

    def _compute_market_confidence(
        self,
        odds_data: Dict[str, Any],
        home_odds: float,
        draw_odds: float,
        away_odds: float,
    ) -> Dict[str, float]:
        """
        计算市场信心度

        基于：
        1. 博彩公司数量（越多越可信）
        2. 赔率标准差（越小越一致）
        """
        features = {}

        # 博彩公司数量
        if "providers" in odds_data:
            num_providers = len(odds_data["providers"])
            features["odds_provider_count"] = float(num_providers)
        else:
            features["odds_provider_count"] = 1.0

        # 如果有多家博彩公司，计算标准差
        if "providers" in odds_data and len(odds_data["providers"]) >= 2:
            home_odds_list = []
            draw_odds_list = []
            away_odds_list = []

            for provider in odds_data["providers"]:
                h = self._extract_provider_odds(provider, "home")
                d = self._extract_provider_odds(provider, "draw")
                a = self._extract_provider_odds(provider, "away")

                if h:
                    home_odds_list.append(h)
                if d:
                    draw_odds_list.append(d)
                if a:
                    away_odds_list.append(a)

            # 计算波动率（标准差 / 均值）
            if home_odds_list:
                home_cv = (
                    statistics.stdev(home_odds_list) / statistics.mean(home_odds_list)
                    if len(home_odds_list) > 1
                    else 0.0
                )
                features["odds_home_volatility"] = round(home_cv, 4)

            if draw_odds_list:
                draw_cv = (
                    statistics.stdev(draw_odds_list) / statistics.mean(draw_odds_list)
                    if len(draw_odds_list) > 1
                    else 0.0
                )
                features["odds_draw_volatility"] = round(draw_cv, 4)

            if away_odds_list:
                away_cv = (
                    statistics.stdev(away_odds_list) / statistics.mean(away_odds_list)
                    if len(away_odds_list) > 1
                    else 0.0
                )
                features["odds_away_volatility"] = round(away_cv, 4)

            # 总体市场一致性（1 - 平均变异系数）
            all_cv = [
                features.get("odds_home_volatility", 0),
                features.get("odds_draw_volatility", 0),
                features.get("odds_away_volatility", 0),
            ]
            avg_cv = statistics.mean(all_cv) if all_cv else 0
            features["odds_market_confidence"] = round(max(0, 1 - avg_cv), 4)
        else:
            # 单一数据源，默认中等信心
            features["odds_market_confidence"] = 0.5
            features["odds_home_volatility"] = 0.0
            features["odds_draw_volatility"] = 0.0
            features["odds_away_volatility"] = 0.0

        return features

    def _compute_value_indices(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        计算价值投注指数

        价值投注 = 模型概率 - 市场隐含概率

        注意：这里需要模型预测的概率作为基准
        如果没有模型预测，使用 xG 差值作为代理
        """
        value_features = {}

        # 基础隐含概率
        home_implied = features.get("odds_implied_prob_home", 0.33)
        draw_implied = features.get("odds_implied_prob_draw", 0.33)
        away_implied = features.get("odds_implied_prob_away", 0.33)

        # 使用"公平概率"（去除抽水）作为模型预期的代理
        # 实际应用中，这里应该用模型预测的概率
        home_real = features.get("odds_real_prob_home", home_implied)
        draw_real = features.get("odds_real_prob_draw", draw_implied)
        away_real = features.get("odds_real_prob_away", away_implied)

        # 价值指数 = 真实概率 - 隐含概率
        # 正值表示价值投注机会
        value_features["odds_value_home"] = round(home_real - home_implied, 4)
        value_features["odds_value_draw"] = round(draw_real - draw_implied, 4)
        value_features["odds_value_away"] = round(away_real - away_implied, 4)

        # 最大价值投注
        values = [
            value_features["odds_value_home"],
            value_features["odds_value_draw"],
            value_features["odds_value_away"],
        ]
        max_value = max(values)
        value_features["odds_max_value"] = round(max_value, 4)

        # 最佳投注方向
        if max_value > 0.02:  # 2% 以上阈值
            if values.index(max_value) == 0:
                value_features["odds_best_bet"] = 1  # 主
            elif values.index(max_value) == 1:
                value_features["odds_best_bet"] = 2  # 平
            else:
                value_features["odds_best_bet"] = 3  # 客
        else:
            value_features["odds_best_bet"] = 0  # 无明显价值

        return value_features

    def _create_default_result(self, warnings: list[str]) -> ProcessorResult:
        """创建默认结果（零填充）"""
        default_features = {
            # 赔率（中性值：1.67 = 均等概率）
            "odds_home_win": 2.50,
            "odds_draw": 3.20,
            "odds_away_win": 2.80,
            # 抽水率
            "odds_bookmaker_margin": 0.06,
            "odds_margin_category": 2,
            # 概率
            "odds_implied_prob_home": 0.40,
            "odds_implied_prob_draw": 0.31,
            "odds_implied_prob_away": 0.36,
            # 偏见
            "odds_draw_bias": 0.05,
            # 信心度
            "odds_market_confidence": 0.5,
        }

        return ProcessorResult.success_result(
            data=default_features,
            metadata={"feature_count": len(default_features), "default_values": True},
        ).with_warning("using_default_odds_values")

    def get_feature_schema(self) -> Dict[str, type]:
        """获取输出特征的 Schema"""
        return {
            # 基础赔率
            "odds_home_win": float,
            "odds_draw": float,
            "odds_away_win": float,
            # 抽水率
            "odds_bookmaker_margin": float,
            "odds_margin_category": int,
            # 隐含概率
            "odds_implied_prob_home": float,
            "odds_implied_prob_draw": float,
            "odds_implied_prob_away": float,
            # 偏见
            "odds_draw_bias": float,
            "odds_draw_sentiment": int,
            # 信心度
            "odds_market_confidence": float,
            "odds_provider_count": float,
            # 价值投注
            "odds_value_home": float,
            "odds_value_draw": float,
            "odds_value_away": float,
        }
