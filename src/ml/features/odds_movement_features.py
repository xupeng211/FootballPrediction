#!/usr/bin/env python3
"""
赔率变动特征系统 - Market Steam捕获分析

Phase 5 Advanced Features 核心组件之三

专门分析博彩市场赔率变动模式，捕获市场情绪和资金流向信号：
- 初盘vs终盘变动分析
- Market Steam识别和强度计算
- 赔率变动速度检测
- 异常变动预警
- 赔率效率评估

核心指标：
- Steam Strength = Σ(Weight × PriceMovement) / Σ(Weight)
- Price Movement = |ln(P1/P0)| × 100
- Weight = Volume × Recency × MarketSignificance

应用场景：
- 市场情绪分析
- 内幕信息检测
- 投注时机优化
- 风险管理

Author: Football Prediction Team
Version: 1.0.0
"""

from datetime import datetime, timedelta
import logging
from typing import Any

import numpy as np
from scipy import stats
from scipy.signal import savgol_filter

logger = logging.getLogger(__name__)


class OddsMovementAnalyzer:
    """
    赔率变动分析器

    主要功能：
    1. 检测Market Steam信号
    2. 分析赔率变动模式
    3. 计算市场情绪指标
    4. 生成交易信号
    """

    # 默认参数
    MIN_ODDS_SAMPLES = 5  # 最少赔率样本数
    STEAM_THRESHOLD = 0.15  # Steam检测阈值
    SIGNIFICANT_MOVE_THRESHOLD = 0.10  # 显著变动阈值
    TIME_WINDOW_HOURS = 24  # 分析时间窗口

    # 赔率变动权重参数
    VOLUME_WEIGHT = 0.4  # 成交量权重
    RECENCY_WEIGHT = 0.3  # 时效性权重
    MARKET_WEIGHT = 0.3  # 市场重要性权重

    # 异常检测参数
    OUTLIER_THRESHOLD = 3.0  # 异常值阈值（标准差倍数）
    MIN_TREND_POINTS = 5  # 趋势分析最少点数

    def __init__(
        self,
        steam_threshold: float = STEAM_THRESHOLD,
        significant_move_threshold: float = SIGNIFICANT_MOVE_THRESHOLD,
        time_window_hours: int = TIME_WINDOW_HOURS,
        enable_anomaly_detection: bool = True,
        enable_trend_analysis: bool = True,
        smoothing_window: int = 5,
    ):
        """
        初始化赔率变动分析器

        Args:
            steam_threshold: Steam检测阈值
            significant_move_threshold: 显著变动阈值
            time_window_hours: 分析时间窗口（小时）
            enable_anomaly_detection: 是否启用异常检测
            enable_trend_analysis: 是否启用趋势分析
            smoothing_window: 平滑窗口大小
        """
        self.steam_threshold = steam_threshold
        self.significant_move_threshold = significant_move_threshold
        self.time_window_hours = time_window_hours
        self.enable_anomaly_detection = enable_anomaly_detection
        self.enable_trend_analysis = enable_trend_analysis
        self.smoothing_window = smoothing_window

        # 存储赔率历史数据
        self.odds_history: dict[str, list[dict[str, Any]]] = {}

        # 存储分析结果
        self.analysis_cache: dict[str, dict[str, Any]] = {}

        # 统计信息
        self.stats = {
            "total_analyses": 0,
            "steam_signals_detected": 0,
            "significant_moves": 0,
            "anomalies_detected": 0,
            "last_updated": None,
        }

        logger.info(
            f"赔率变动分析器初始化完成: Steam阈值={steam_threshold}, "
            f"显著变动阈值={significant_move_threshold}, "
            f"时间窗口={time_window_hours}小时"
        )

    def add_odds_data(
        self,
        match_id: str,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        timestamp: datetime | None = None,
        bookmaker: str = "default",
        volume: float | None = None,
        market_importance: float = 1.0,
    ) -> dict[str, Any]:
        """
        添加赔率数据

        Args:
            match_id: 比赛ID
            home_odds: 主胜赔率
            draw_odds: 平局赔率
            away_odds: 客胜赔率
            timestamp: 时间戳
            bookmaker: 博彩公司
            volume: 成交量
            market_importance: 市场重要性

        Returns:
            Dict[str, Any]: 添加结果
        """
        timestamp = timestamp or datetime.now()

        odds_entry = {
            "timestamp": timestamp,
            "home_odds": home_odds,
            "draw_odds": draw_odds,
            "away_odds": away_odds,
            "bookmaker": bookmaker,
            "volume": volume or 1.0,
            "market_importance": market_importance,
            "implied_prob_home": self._odds_to_probability(home_odds),
            "implied_prob_draw": self._odds_to_probability(draw_odds),
            "implied_prob_away": self._odds_to_probability(away_odds),
        }

        if match_id not in self.odds_history:
            self.odds_history[match_id] = []

        self.odds_history[match_id].append(odds_entry)

        # 清理缓存（新数据需要重新分析）
        if match_id in self.analysis_cache:
            del self.analysis_cache[match_id]

        return {
            "status": "success",
            "match_id": match_id,
            "timestamp": timestamp.isoformat(),
            "total_samples": len(self.odds_history[match_id]),
        }

    def analyze_odds_movement(
        self, match_id: str, time_window_hours: int | None = None
    ) -> dict[str, Any]:
        """
        分析赔率变动

        Args:
            match_id: 比赛ID
            time_window_hours: 分析时间窗口

        Returns:
            Dict[str, Any]: 分析结果
        """
        if match_id not in self.odds_history:
            return {"error": f"比赛 {match_id} 无赔率数据"}

        odds_data = self.odds_history[match_id]
        if len(odds_data) < self.MIN_ODDS_SAMPLES:
            return {"error": f"数据不足，需要至少{self.MIN_ODDS_SAMPLES}个样本"}

        # 时间窗口过滤
        time_window = time_window_hours or self.time_window_hours
        cutoff_time = datetime.now() - timedelta(hours=time_window)
        recent_data = [entry for entry in odds_data if entry["timestamp"] >= cutoff_time]

        if len(recent_data) < 3:
            logger.warning(f"比赛 {match_id} 时间窗口内数据不足，使用全部数据")
            recent_data = odds_data

        # 按时间排序
        recent_data.sort(key=lambda x: x["timestamp"])

        # 执行分析
        analysis_result = self._perform_comprehensive_analysis(match_id, recent_data)

        # 缓存结果
        self.analysis_cache[match_id] = analysis_result

        # 更新统计信息
        self._update_analysis_stats(analysis_result)

        return analysis_result

    def _perform_comprehensive_analysis(
        self, match_id: str, odds_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """执行综合分析"""
        # 基础统计
        basic_stats = self._calculate_basic_statistics(odds_data)

        # 赔率变动分析
        movement_analysis = self._analyze_price_movements(odds_data)

        # Market Steam检测
        steam_signals = self._detect_steam_signals(odds_data)

        # 趋势分析
        trend_analysis = self._analyze_trends(odds_data) if self.enable_trend_analysis else {}

        # 异常检测
        anomaly_detection = (
            self._detect_anomalies(odds_data) if self.enable_anomaly_detection else {}
        )

        # 市场情绪分析
        sentiment_analysis = self._analyze_market_sentiment(odds_data)

        # 效率评估
        efficiency_metrics = self._calculate_market_efficiency(odds_data)

        # 生成交易信号
        trading_signals = self._generate_trading_signals(
            movement_analysis, steam_signals, sentiment_analysis
        )

        # 提取模型特征
        model_features = self._extract_odds_movement_features(
            odds_data, movement_analysis, steam_signals, sentiment_analysis
        )

        return {
            "match_id": match_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "data_summary": {
                "total_samples": len(odds_data),
                "time_range_hours": self._get_time_range_hours(odds_data),
                "bookmakers": list({entry["bookmaker"] for entry in odds_data}),
            },
            "basic_statistics": basic_stats,
            "movement_analysis": movement_analysis,
            "steam_signals": steam_signals,
            "trend_analysis": trend_analysis,
            "anomaly_detection": anomaly_detection,
            "sentiment_analysis": sentiment_analysis,
            "efficiency_metrics": efficiency_metrics,
            "trading_signals": trading_signals,
            "model_features": model_features,
        }

    def _calculate_basic_statistics(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """计算基础统计信息"""
        home_odds = [entry["home_odds"] for entry in odds_data]
        draw_odds = [entry["draw_odds"] for entry in odds_data]
        away_odds = [entry["away_odds"] for entry in odds_data]

        return {
            "home_odds": {
                "current": home_odds[-1],
                "initial": home_odds[0],
                "mean": np.mean(home_odds),
                "std": np.std(home_odds),
                "min": np.min(home_odds),
                "max": np.max(home_odds),
                "change_pct": ((home_odds[-1] - home_odds[0]) / home_odds[0]) * 100,
            },
            "draw_odds": {
                "current": draw_odds[-1],
                "initial": draw_odds[0],
                "mean": np.mean(draw_odds),
                "std": np.std(draw_odds),
                "min": np.min(draw_odds),
                "max": np.max(draw_odds),
                "change_pct": ((draw_odds[-1] - draw_odds[0]) / draw_odds[0]) * 100,
            },
            "away_odds": {
                "current": away_odds[-1],
                "initial": away_odds[0],
                "mean": np.mean(away_odds),
                "std": np.std(away_odds),
                "min": np.min(away_odds),
                "max": np.max(away_odds),
                "change_pct": ((away_odds[-1] - away_odds[0]) / away_odds[0]) * 100,
            },
        }

    def _analyze_price_movements(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """分析价格变动"""
        movements = {"home": [], "draw": [], "away": []}

        for i in range(1, len(odds_data)):
            prev_entry = odds_data[i - 1]
            curr_entry = odds_data[i]

            # 计算价格变动百分比
            home_move = self._calculate_price_move(prev_entry["home_odds"], curr_entry["home_odds"])
            draw_move = self._calculate_price_move(prev_entry["draw_odds"], curr_entry["draw_odds"])
            away_move = self._calculate_price_move(prev_entry["away_odds"], curr_entry["away_odds"])

            # 考虑权重
            weight = self._calculate_movement_weight(curr_entry)

            movements["home"].append(
                {
                    "timestamp": curr_entry["timestamp"],
                    "move_pct": home_move,
                    "weight": weight,
                    "abs_move": abs(home_move),
                    "volume": curr_entry.get("volume", 1.0),
                }
            )
            movements["draw"].append(
                {
                    "timestamp": curr_entry["timestamp"],
                    "move_pct": draw_move,
                    "weight": weight,
                    "abs_move": abs(draw_move),
                    "volume": curr_entry.get("volume", 1.0),
                }
            )
            movements["away"].append(
                {
                    "timestamp": curr_entry["timestamp"],
                    "move_pct": away_move,
                    "weight": weight,
                    "abs_move": abs(away_move),
                    "volume": curr_entry.get("volume", 1.0),
                }
            )

        # 计算统计指标
        summary = {}
        for outcome in ["home", "draw", "away"]:
            outcome_moves = movements[outcome]
            if outcome_moves:
                moves = [m["move_pct"] for m in outcome_moves]
                weights = [m["weight"] for m in outcome_moves]

                summary[outcome] = {
                    "total_moves": len(outcome_moves),
                    "avg_move": np.mean(moves),
                    "weighted_avg_move": np.average(moves, weights=weights),
                    "max_move": np.max([m["abs_move"] for m in outcome_moves]),
                    "move_std": np.std(moves),
                    "significant_moves": len(
                        [
                            m
                            for m in outcome_moves
                            if m["abs_move"] > self.significant_move_threshold
                        ]
                    ),
                    "total_weighted_move": sum(m["move_pct"] * m["weight"] for m in outcome_moves),
                }
            else:
                summary[outcome] = {
                    "total_moves": 0,
                    "avg_move": 0,
                    "weighted_avg_move": 0,
                    "max_move": 0,
                    "move_std": 0,
                    "significant_moves": 0,
                    "total_weighted_move": 0,
                }

        return {
            "detailed_movements": movements,
            "summary": summary,
        }

    def _detect_steam_signals(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """检测Market Steam信号"""
        steam_signals = []

        # 检测连续同向变动
        for outcome in ["home", "draw", "away"]:
            signal = self._detect_outcome_steam(odds_data, outcome)
            if signal:
                steam_signals.append(signal)

        # 检测跨市场Steam
        cross_market_steam = self._detect_cross_market_steam(odds_data)
        if cross_market_steam:
            steam_signals.append(cross_market_steam)

        # 计算整体Steam强度
        overall_steam = self._calculate_overall_steam_strength(steam_signals)

        return {
            "signals": steam_signals,
            "steam_detected": len(steam_signals) > 0,
            "overall_strength": overall_steam,
            "signal_count": len(steam_signals),
        }

    def _detect_outcome_steam(
        self, odds_data: list[dict[str, Any]], outcome: str
    ) -> dict[str, Any] | None:
        """检测单个结果的Steam信号"""
        if len(odds_data) < 3:
            return None

        # 获取赔率序列
        odds_key = f"{outcome}_odds"
        odds_sequence = [entry[odds_key] for entry in odds_data]

        # 计算变动方向
        directions = []
        for i in range(1, len(odds_sequence)):
            if odds_sequence[i] < odds_sequence[i - 1]:
                directions.append("down")  # 赔率下降
            elif odds_sequence[i] > odds_sequence[i - 1]:
                directions.append("up")  # 赔率上升
            else:
                directions.append("stable")

        # 检测连续同向变动
        if len(directions) >= 3:
            # 检查最后3个变动是否同向
            recent_directions = directions[-3:]
            if all(d == recent_directions[0] for d in recent_directions):
                # 计算强度
                total_move = 0
                total_weight = 0

                for i in range(1, len(odds_sequence)):
                    move = self._calculate_price_move(odds_sequence[i - 1], odds_sequence[i])
                    weight = self._calculate_movement_weight(odds_data[i])

                    if directions[i - 1] == recent_directions[0]:
                        total_move += abs(move) * weight
                        total_weight += weight

                if total_weight > 0:
                    steam_strength = total_move / total_weight

                    if steam_strength > self.steam_threshold:
                        return {
                            "outcome": outcome,
                            "direction": recent_directions[0],
                            "strength": steam_strength,
                            "duration": len([d for d in directions if d == recent_directions[0]]),
                            "total_move": total_move,
                            "confidence": min(1.0, steam_strength / self.steam_threshold),
                            "start_timestamp": odds_data[-(len(recent_directions) + 1)][
                                "timestamp"
                            ].isoformat(),
                            "end_timestamp": odds_data[-1]["timestamp"].isoformat(),
                        }

        return None

    def _detect_cross_market_steam(self, odds_data: list[dict[str, Any]]) -> dict[str, Any] | None:
        """检测跨市场Steam信号"""
        if len(odds_data) < 3:
            return None

        # 分析所有结果的综合变动
        total_volume = sum(entry.get("volume", 1.0) for entry in odds_data)

        if total_volume == 0:
            return None

        weighted_moves = {"home": 0, "draw": 0, "away": 0}

        for i in range(1, len(odds_data)):
            prev_entry = odds_data[i - 1]
            curr_entry = odds_data[i]
            weight = curr_entry.get("volume", 1.0) / total_volume

            home_move = self._calculate_price_move(prev_entry["home_odds"], curr_entry["home_odds"])
            draw_move = self._calculate_price_move(prev_entry["draw_odds"], curr_entry["draw_odds"])
            away_move = self._calculate_price_move(prev_entry["away_odds"], curr_entry["away_odds"])

            weighted_moves["home"] += abs(home_move) * weight
            weighted_moves["draw"] += abs(draw_move) * weight
            weighted_moves["away"] += abs(away_move) * weight

        # 检查是否有明显的跨市场Steam
        max_move = max(weighted_moves.values())
        if max_move > self.steam_threshold * 0.8:  # 稍微降低阈值用于跨市场检测
            dominant_outcome = max(weighted_moves, key=weighted_moves.get)

            return {
                "outcome": "cross_market",
                "dominant_outcome": dominant_outcome,
                "strength": max_move,
                "weighted_moves": weighted_moves,
                "confidence": min(1.0, max_move / (self.steam_threshold * 0.8)),
            }

        return None

    def _calculate_overall_steam_strength(self, steam_signals: list[dict[str, Any]]) -> float:
        """计算整体Steam强度"""
        if not steam_signals:
            return 0.0

        # 加权平均强度
        total_strength = sum(signal["strength"] for signal in steam_signals)
        total_confidence = sum(signal.get("confidence", 0.5) for signal in steam_signals)

        if total_confidence > 0:
            return total_strength / len(steam_signals)
        return total_strength / len(steam_signals)

    def _analyze_trends(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """分析趋势"""
        if len(odds_data) < self.MIN_TREND_POINTS:
            return {"error": "数据点不足，无法进行趋势分析"}

        trends = {}

        for outcome in ["home", "draw", "away"]:
            odds_key = f"{outcome}_odds"
            odds_values = [entry[odds_key] for entry in odds_data]

            # 线性回归趋势
            x = np.arange(len(odds_values))
            slope, _intercept, r_value, p_value, _std_err = stats.linregress(x, odds_values)

            # 移动平均趋势
            window_size = min(self.smoothing_window, len(odds_values) // 2)
            if window_size >= 2:
                smoothed = savgol_filter(odds_values, window_size, 3)
                trend_direction = "up" if smoothed[-1] > smoothed[0] else "down"
            else:
                smoothed = odds_values
                trend_direction = "stable"

            trends[outcome] = {
                "linear_slope": slope,
                "linear_r_squared": r_value**2,
                "linear_p_value": p_value,
                "trend_direction": trend_direction,
                "volatility": np.std(odds_values),
                "smoothed_current": (float(smoothed[-1]) if len(smoothed) > 0 else odds_values[-1]),
                "smoothed_change": (float(smoothed[-1] - smoothed[0]) if len(smoothed) > 1 else 0),
            }

        return {
            "trends": trends,
            "analysis_period_hours": self._get_time_range_hours(odds_data),
        }

    def _detect_anomalies(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """检测异常值"""
        anomalies = []

        for outcome in ["home", "draw", "away"]:
            odds_key = f"{outcome}_odds"
            odds_values = [entry[odds_key] for entry in odds_data]

            if len(odds_values) < 3:
                continue

            # Z-score异常检测
            z_scores = np.abs(stats.zscore(odds_values))

            for i, (entry, z_score) in enumerate(zip(odds_data, z_scores, strict=False)):
                if z_score > self.OUTLIER_THRESHOLD:
                    anomalies.append(
                        {
                            "timestamp": entry["timestamp"].isoformat(),
                            "outcome": outcome,
                            "odds_value": entry[odds_key],
                            "z_score": float(z_score),
                            "anomaly_type": "statistical_outlier",
                            "severity": min(
                                1.0,
                                (z_score - self.OUTLIER_THRESHOLD) / self.OUTLIER_THRESHOLD,
                            ),
                        }
                    )

            # 变动幅度异常检测
            if i > 0:
                prev_odds = odds_data[i - 1][odds_key]
                curr_odds = entry[odds_key]
                price_move = self._calculate_price_move(prev_odds, curr_odds)

                if price_move > self.significant_move_threshold * 2:  # 2倍阈值
                    anomalies.append(
                        {
                            "timestamp": entry["timestamp"].isoformat(),
                            "outcome": outcome,
                            "price_move": price_move,
                            "anomaly_type": "large_price_movement",
                            "severity": min(
                                1.0, price_move / (self.significant_move_threshold * 3)
                            ),
                        }
                    )

        return {
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
            "anomaly_rate": len(anomalies) / len(odds_data) if odds_data else 0,
        }

    def _analyze_market_sentiment(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """分析市场情绪"""
        if len(odds_data) < 2:
            return {"error": "数据不足，无法分析市场情绪"}

        # 计算隐含概率的变化
        prob_changes = {"home": [], "draw": [], "away": []}

        for i in range(1, len(odds_data)):
            prev_entry = odds_data[i - 1]
            curr_entry = odds_data[i]

            for outcome in ["home", "draw", "away"]:
                prob_key = f"implied_prob_{outcome}"
                prob_change = curr_entry[prob_key] - prev_entry[prob_key]
                prob_changes[outcome].append(prob_change)

        # 计算情绪指标
        sentiment_metrics = {}
        for outcome in ["home", "draw", "away"]:
            changes = prob_changes[outcome]
            if changes:
                sentiment_metrics[outcome] = {
                    "avg_change": np.mean(changes),
                    "total_change": sum(changes),
                    "volatility": np.std(changes),
                    "momentum": changes[-1] if changes else 0,  # 最近变化
                    "consistency": len([c for c in changes if c * changes[0] > 0]) / len(changes),
                }

        # 确定主导情绪
        dominant_sentiment = (
            max(sentiment_metrics.items(), key=lambda x: abs(x[1]["total_change"]))
            if sentiment_metrics
            else ("none", {"total_change": 0})
        )

        return {
            "sentiment_metrics": sentiment_metrics,
            "dominant_sentiment": dominant_sentiment[0],
            "sentiment_strength": abs(dominant_sentiment[1]["total_change"]),
            "market_consensus": self._calculate_market_consensus(odds_data),
        }

    def _calculate_market_efficiency(self, odds_data: list[dict[str, Any]]) -> dict[str, Any]:
        """计算市场效率指标"""
        if len(odds_data) < 3:
            return {"error": "数据不足，无法计算市场效率"}

        # 计算赔率序列的变异系数
        efficiency_metrics = {}

        for outcome in ["home", "draw", "away"]:
            odds_key = f"{outcome}_odds"
            odds_values = [entry[odds_key] for entry in odds_data]

            # 赔率稳定性
            cv = (
                np.std(odds_values) / np.mean(odds_values)
                if np.mean(odds_values) > 0
                else float("inf")
            )

            # 价格冲击
            max_drawdown = self._calculate_max_drawdown(odds_values)

            # 效率分数（0-1，1表示完全高效）
            efficiency_score = max(0, 1 - (cv + max_drawdown) / 2)

            efficiency_metrics[outcome] = {
                "coefficient_of_variation": cv,
                "max_drawdown": max_drawdown,
                "efficiency_score": efficiency_score,
                "stability": 1.0 / (1.0 + cv),  # 稳定性指标
            }

        # 整体市场效率
        overall_efficiency = np.mean(
            [metrics["efficiency_score"] for metrics in efficiency_metrics.values()]
        )

        return {
            "outcome_efficiency": efficiency_metrics,
            "overall_efficiency": overall_efficiency,
            "market_classification": self._classify_market_efficiency(overall_efficiency),
        }

    def _generate_trading_signals(
        self,
        movement_analysis: dict[str, Any],
        steam_signals: dict[str, Any],
        sentiment_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """生成交易信号"""
        signals = []

        # Steam信号
        if steam_signals.get("steam_detected", False):
            for steam in steam_signals["signals"]:
                if steam["strength"] > self.steam_threshold:
                    signals.append(
                        {
                            "type": "steam",
                            "outcome": steam["outcome"],
                            "direction": steam.get("direction", "unknown"),
                            "strength": steam["strength"],
                            "confidence": steam.get("confidence", 0.5),
                            "reasoning": f"Market steam detected with strength {steam['strength']:.2f}",
                        }
                    )

        # 趋势信号
        summary = movement_analysis.get("summary", {})
        for outcome, metrics in summary.items():
            if metrics["total_weighted_move"] > self.significant_move_threshold:
                direction = "down" if metrics["total_weighted_move"] < 0 else "up"
                signals.append(
                    {
                        "type": "trend",
                        "outcome": outcome,
                        "direction": direction,
                        "strength": abs(metrics["total_weighted_move"]),
                        "confidence": min(
                            1.0, metrics["significant_moves"] / metrics["total_moves"]
                        ),
                        "reasoning": f"Significant trend movement: {metrics['total_weighted_move']:.2f}%",
                    }
                )

        # 情绪信号
        dominant_sentiment = sentiment_analysis.get("dominant_sentiment")
        sentiment_strength = sentiment_analysis.get("sentiment_strength", 0)

        if sentiment_strength > 0.05 and dominant_sentiment != "none":
            sentiment_metrics = sentiment_analysis.get("sentiment_metrics", {}).get(
                dominant_sentiment, {}
            )
            momentum = sentiment_metrics.get("momentum", 0)

            if abs(momentum) > 0.02:
                signals.append(
                    {
                        "type": "sentiment",
                        "outcome": dominant_sentiment,
                        "direction": "positive" if momentum > 0 else "negative",
                        "strength": abs(momentum),
                        "confidence": sentiment_metrics.get("consistency", 0.5),
                        "reasoning": f"Strong market sentiment momentum: {momentum:.3f}",
                    }
                )

        # 信号优先级排序
        priority_signals = sorted(
            signals, key=lambda x: x["strength"] * x["confidence"], reverse=True
        )

        return {
            "signals": priority_signals[:5],  # 返回前5个最强信号
            "signal_count": len(signals),
            "strongest_signal": priority_signals[0] if priority_signals else None,
            "overall_signal_strength": np.sum([s["strength"] * s["confidence"] for s in signals]),
        }

    def _extract_odds_movement_features(
        self,
        odds_data: list[dict[str, Any]],
        movement_analysis: dict[str, Any],
        steam_signals: dict[str, Any],
        sentiment_analysis: dict[str, Any],
    ) -> dict[str, float]:
        """提取用于机器学习的特征"""
        features = {}

        # 基础变动特征
        summary = movement_analysis.get("summary", {})
        for outcome in ["home", "draw", "away"]:
            if outcome in summary:
                metrics = summary[outcome]
                features[f"{outcome}_total_weighted_move"] = metrics["total_weighted_move"]
                features[f"{outcome}_significant_moves_ratio"] = metrics["significant_moves"] / max(
                    metrics["total_moves"], 1
                )
                features[f"{outcome}_move_volatility"] = metrics["move_std"]
                features[f"{outcome}_avg_move"] = metrics["avg_move"]

        # Steam特征
        steam_detected = steam_signals.get("steam_detected", False)
        features["steam_detected"] = float(steam_detected)
        features["steam_strength"] = steam_signals.get("overall_strength", 0)
        features["steam_signal_count"] = steam_signals.get("signal_count", 0)

        # 市场情绪特征
        sentiment_analysis.get("dominant_sentiment", "none")
        features["dominant_sentiment_strength"] = sentiment_analysis.get("sentiment_strength", 0)

        sentiment_metrics = sentiment_analysis.get("sentiment_metrics", {})
        for outcome in ["home", "draw", "away"]:
            if outcome in sentiment_metrics:
                metrics = sentiment_metrics[outcome]
                features[f"{outcome}_sentiment_momentum"] = metrics["momentum"]
                features[f"{outcome}_sentiment_consistency"] = metrics["consistency"]
                features[f"{outcome}_sentiment_volatility"] = metrics["volatility"]

        # 市场效率特征
        efficiency_metrics = movement_analysis.get("efficiency_metrics", {})
        if "overall_efficiency" in efficiency_metrics:
            features["market_efficiency"] = efficiency_metrics["overall_efficiency"]

        # 时间序列特征
        if len(odds_data) >= 3:
            # 最近变动幅度
            latest_moves = []
            for outcome in ["home", "draw", "away"]:
                odds_key = f"{outcome}_odds"
                if len(odds_data) >= 2:
                    latest_move = self._calculate_price_move(
                        odds_data[-2][odds_key], odds_data[-1][odds_key]
                    )
                    latest_moves.append(abs(latest_move))
                    features[f"{outcome}_latest_move"] = latest_move

            features["avg_latest_move"] = np.mean(latest_moves) if latest_moves else 0
            features["max_latest_move"] = np.max(latest_moves) if latest_moves else 0

        return features

    def _calculate_price_move(self, prev_odds: float, curr_odds: float) -> float:
        """计算价格变动百分比"""
        if prev_odds == 0:
            return 0
        return ((curr_odds - prev_odds) / prev_odds) * 100

    def _calculate_movement_weight(self, entry: dict[str, Any]) -> float:
        """计算变动权重"""
        volume_weight = entry.get("volume", 1.0) ** self.VOLUME_WEIGHT

        # 时效性权重（越新权重越高）
        time_diff = (datetime.now() - entry["timestamp"]).total_seconds() / 3600  # 小时
        recency_weight = max(0.1, np.exp(-time_diff / 24)) ** self.RECENCY_WEIGHT

        # 市场重要性权重
        market_weight = entry.get("market_importance", 1.0) ** self.MARKET_WEIGHT

        return volume_weight * recency_weight * market_weight

    def _odds_to_probability(self, odds: float) -> float:
        """将赔率转换为隐含概率"""
        if odds <= 0:
            return 0
        return 1.0 / odds

    def _get_time_range_hours(self, odds_data: list[dict[str, Any]]) -> float:
        """获取数据时间范围（小时）"""
        if len(odds_data) < 2:
            return 0
        time_diff = odds_data[-1]["timestamp"] - odds_data[0]["timestamp"]
        return time_diff.total_seconds() / 3600

    def _calculate_max_drawdown(self, values: list[float]) -> float:
        """计算最大回撤"""
        if len(values) < 2:
            return 0

        peak = values[0]
        max_drawdown = 0

        for value in values:
            peak = max(peak, value)
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _classify_market_efficiency(self, efficiency_score: float) -> str:
        """分类市场效率"""
        if efficiency_score >= 0.9:
            return "highly_efficient"
        if efficiency_score >= 0.7:
            return "efficient"
        if efficiency_score >= 0.5:
            return "moderately_efficient"
        if efficiency_score >= 0.3:
            return "inefficient"
        return "highly_inefficient"

    def _calculate_market_consensus(self, odds_data: list[dict[str, Any]]) -> float:
        """计算市场共识度"""
        if len(odds_data) < 2:
            return 0

        # 计算隐含概率的方差（作为共识度的反向指标）
        latest_entry = odds_data[-1]
        probabilities = [
            latest_entry["implied_prob_home"],
            latest_entry["implied_prob_draw"],
            latest_entry["implied_prob_away"],
        ]

        # 标准化后计算方差
        max_prob = max(probabilities)
        if max_prob > 0:
            normalized_probs = [p / max_prob for p in probabilities]
            consensus = 1.0 - np.var(normalized_probs)  # 方差越小，共识越高
            return max(0, consensus)

        return 0

    def _update_analysis_stats(self, analysis_result: dict[str, Any]) -> None:
        """更新分析统计信息"""
        self.stats["total_analyses"] += 1

        # 更新Steam信号统计
        steam_signals = analysis_result.get("steam_signals", {})
        if steam_signals.get("steam_detected", False):
            self.stats["steam_signals_detected"] += 1

        # 更新显著变动统计
        movement_summary = analysis_result.get("movement_analysis", {}).get("summary", {})
        total_significant = sum(
            metrics.get("significant_moves", 0) for metrics in movement_summary.values()
        )
        if total_significant > 0:
            self.stats["significant_moves"] += 1

        # 更新异常检测统计
        anomaly_data = analysis_result.get("anomaly_detection", {})
        if anomaly_data.get("total_anomalies", 0) > 0:
            self.stats["anomalies_detected"] += 1

        self.stats["last_updated"] = datetime.now().isoformat()

    def get_system_stats(self) -> dict[str, Any]:
        """获取系统统计信息"""
        return {
            "configuration": {
                "steam_threshold": self.steam_threshold,
                "significant_move_threshold": self.significant_move_threshold,
                "time_window_hours": self.time_window_hours,
                "enable_anomaly_detection": self.enable_anomaly_detection,
                "enable_trend_analysis": self.enable_trend_analysis,
                "smoothing_window": self.smoothing_window,
            },
            "statistics": self.stats,
            "data_coverage": {
                "matches_analyzed": len(self.analysis_cache),
                "total_odds_samples": sum(len(data) for data in self.odds_history.values()),
                "avg_samples_per_match": (
                    np.mean([len(data) for data in self.odds_history.values()])
                    if self.odds_history
                    else 0
                ),
            },
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"OddsMovementAnalyzer(matches={len(self.analysis_cache)}, "
            f"analyses={self.stats['total_analyses']}, "
            f"steam_signals={self.stats['steam_signals_detected']})"
        )
