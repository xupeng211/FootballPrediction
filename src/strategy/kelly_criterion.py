#!/usr/bin/env python3
"""
凯利公式资金管理系统 - 金融级精度版本

Sprint 5 核心组件之四

基于凯利准则的最优投注比例计算系统，确保长期资本增长：
- 完整凯利公式实现：f* = (bp - q) / b
- 分数凯利（Fractional Kelly）支持
- 多投注选项并行计算
- 风险管理和仓位控制
- 回撤控制和资金保护

LaTeX数学公式：
f^* = \frac{bp - q}{b} = \frac{p(b + 1) - 1}{b}

其中：
- f*: 最优投注比例（资金百分比）
- b: 净赔率（decimal odds - 1）
- p: 预测胜率
- q: 失败概率 = 1 - p

分数凯利：
f_{fractional} = k \times f^*, 其中 0 < k ≤ 1

Author: Football Prediction Team
Version: 1.0.0
"""

import logging
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, getcontext, Context
from dataclasses import dataclass
from enum import Enum

from ...constants import FOOTBALL, MATH, PROBABILITY, ODDS
from ...config_secure import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ProductionSafetyConfig:
    """生产环境安全配置"""
    enabled: bool = True
    max_stake_percentage_of_bankroll: Decimal = Decimal("0.05")  # 单笔最大投注比例（5%）
    max_daily_stake_percentage: Decimal = Decimal("0.20")          # 日最大投注比例（20%）
    emergency_stop_enabled: bool = True                            # 紧急停止开关
    manual_override_required: bool = False                         # 需要人工确认
    audit_log_enabled: bool = True                                 # 审计日志
    risk_alert_threshold: Decimal = Decimal("0.03")                # 风险告警阈值（3%）


class ProductionSafetyValidator:
    """生产环境安全验证器"""

    def __init__(self, config: ProductionSafetyConfig):
        self.config = config
        self.settings = get_settings()
        self.daily_stake_total = Decimal("0")
        self.high_value_bets_count = 0

    def validate_stake_amount(self, bankroll: Decimal, stake_amount: Decimal) -> Dict[str, Any]:
        """
        验证投注金额安全性

        Args:
            bankroll: 当前资金池
            stake_amount: 建议投注金额

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            "valid": True,
            "action": "allow",
            "reason": "",
            "requires_manual_review": False,
            "logged": False
        }

        # 检查是否启用安全控制
        if not self.config.enabled:
            validation_result["reason"] = "安全控制已禁用"
            return validation_result

        # 计算投注比例
        stake_percentage = (stake_amount / bankroll) * Decimal("100")

        # 检查单笔投注限制
        if stake_percentage > self.config.max_stake_percentage_of_bankroll * Decimal("100"):
            validation_result["valid"] = False
            validation_result["action"] = "reject"
            validation_result["reason"] = (
                f"单笔投注比例 {stake_percentage:.2f}% 超过安全限制 "
                f"{self.config.max_stake_percentage_of_bankroll * Decimal('100'):.2f}%"
            )
            validation_result["requires_manual_review"] = True
            validation_result["logged"] = True

            # 记录CRITICAL日志
            logger.critical(
                f"🚨 生产安全风险: 建议投注 {stake_amount:.2f} ({stake_percentage:.2f}%) "
                f"超过安全限制 {self.config.max_stake_percentage_of_bankroll * Decimal('100'):.2f}%"
            )
            logger.critical(
                f"💰 资金池: {bankroll:.2f}, 建议投注: {stake_amount:.2f}, "
                f"风险金额: {stake_amount - (bankroll * self.config.max_stake_percentage_of_bankroll):.2f}"
            )

            return validation_result

        # 检查日投注总额限制
        new_daily_total = self.daily_stake_total + stake_amount
        daily_percentage = (new_daily_total / bankroll) * Decimal("100")

        if daily_percentage > self.config.max_daily_stake_percentage * Decimal("100"):
            validation_result["valid"] = False
            validation_result["action"] = "reject"
            validation_result["reason"] = (
                f"日投注总额 {daily_percentage:.2f}% 将超过限制 "
                f"{self.config.max_daily_stake_percentage * Decimal('100'):.2f}%"
            )
            validation_result["requires_manual_review"] = True

            logger.warning(
                f"⚠️ 日投注限制: 当前总额 {self.daily_stake_total:.2f} ({(self.daily_stake_total / bankroll * Decimal('100')):.2f}%), "
                f"新增投注后将达到 {new_daily_total:.2f} ({daily_percentage:.2f}%)"
            )

            return validation_result

        # 检查高风险投注数量
        if stake_percentage > self.config.risk_alert_threshold * Decimal("100"):
            self.high_value_bets_count += 1

            if self.high_value_bets_count > 3:  # 同一时间段内高风险投注过多
                validation_result["requires_manual_review"] = True
                validation_result["reason"] = "高风险投注频率过高，需要人工确认"

                logger.warning(
                    f"⚠️ 高风险投注频率过高: {self.high_value_bets_count} 次高风险投注"
                )

        # 检查是否需要人工确认
        if self.config.manual_override_required and stake_percentage > Decimal("2"):
            validation_result["requires_manual_review"] = True
            validation_result["reason"] = "大额投注需要人工确认"

        return validation_result

    def update_daily_stake(self, stake_amount: Decimal):
        """更新日投注总额"""
        self.daily_stake_total += stake_amount

    def reset_daily_counters(self):
        """重置日计数器（应在每天开始时调用）"""
        self.daily_stake_total = Decimal("0")
        self.high_value_bets_count = 0

    def log_bet_decision(self, decision_data: Dict[str, Any]):
        """记录投注决策（审计日志）"""
        if not self.config.audit_log_enabled:
            return

        logger.info(
            f"📝 投注决策审计: {decision_data}",
            extra={
                "audit_type": "bet_decision",
                "timestamp": datetime.now().isoformat(),
                "stake_amount": decision_data.get("stake_amount", 0),
                "risk_level": decision_data.get("risk_level", "unknown"),
                "requires_review": decision_data.get("requires_manual_review", False)
            }
        )


class KellyStrategy(Enum):
    """凯利策略类型"""
    FULL_KELLY = "full_kelly"           # 完整凯利
    FRACTIONAL_KELLY = "fractional"    # 分数凯利
    CONSERVATIVE_KELLY = "conservative"  # 保守凯利
    AGGRESSIVE_KELLY = "aggressive"    # 激进凯利
    DYNAMIC_KELLY = "dynamic"          # 动态凯利


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class BetRecommendation:
    """投注建议"""
    outcome: str                    # 投注结果（home/draw/away）
    odds: Decimal                   # 赔率
    predicted_prob: Decimal         # 预测概率
    kelly_fraction: Decimal         # 凯利比例
    stake_amount: Decimal           # 建议投注金额
    expected_value: Decimal         # 期望值
    confidence: Decimal             # 置信度
    risk_level: RiskLevel           # 风险等级
    reasoning: str                  # 推理说明


@dataclass
class PortfolioState:
    """投资组合状态"""
    total_bankroll: Decimal         # 总资金
    available_cash: Decimal         # 可用现金
    committed_stakes: Decimal       # 已投注金额
    max_drawdown: Decimal           # 最大回撤
    current_drawdown: Decimal       # 当前回撤
    win_rate: Decimal               # 胜率
    total_bets: int                 # 总投注次数
    winning_bets: int               # 获胜投注次数


class KellyCriterion:
    """
    凯利准则资金管理系统

    主要功能：
    1. 计算最优投注比例
    2. 风险管理和仓位控制
    3. 投资组合优化
    4. 回撤控制
    5. 业绩分析和报告

    核心特性：
    - 金融级Decimal精度
    - 多策略支持
    - 动态风险管理
    - 实时资金保护
    """

    # 默认参数
    DEFAULT_FRACTION = Decimal("0.25")      # 默认分数凯利比例（25%）
    MIN_EDGE_THRESHOLD = Decimal("0.05")   # 最小优势阈值（5%）
    MAX_STAKE_PERCENTAGE = Decimal("0.10")  # 最大单笔投注比例（10%）
    SAFETY_MULTIPLIER = Decimal("0.8")     # 安全系数

    # 风险控制参数
    MAX_DRAWDOWN_LIMIT = Decimal("0.20")    # 最大回撤限制（20%）
    MIN_BANKROLL_RESERVE = Decimal("0.10") # 最小资金储备（10%）
    MAX_CONCURRENT_BETS = 5                # 最大同时投注数量

    # 动态调整参数
    CONFIDENCE_THRESHOLD = Decimal("0.60") # 置信度阈值
    VOLATILITY_WINDOW = 20                 # 波动率计算窗口
    PERFORMANCE_WINDOW = 50                # 业绩评估窗口

    def __init__(
        self,
        initial_bankroll: Union[float, str, Decimal],
        kelly_strategy: KellyStrategy = KellyStrategy.FRACTIONAL_KELLY,
        fraction_multiplier: Union[float, str, Decimal] = DEFAULT_FRACTION,
        min_edge_threshold: Union[float, str, Decimal] = MIN_EDGE_THRESHOLD,
        max_stake_percentage: Union[float, str, Decimal] = MAX_STAKE_PERCENTAGE,
        enable_dynamic_adjustment: bool = True,
        enable_risk_management: bool = True,
        precision_context: Optional[Context] = None,
        production_safety_config: Optional[ProductionSafetyConfig] = None,
    ):
        """
        初始化凯利准则系统

        Args:
            initial_bankroll: 初始资金
            kelly_strategy: 凯利策略
            fraction_multiplier: 分数凯利乘数
            min_edge_threshold: 最小优势阈值
            max_stake_percentage: 最大投注比例
            enable_dynamic_adjustment: 是否启用动态调整
            enable_risk_management: 是否启用风险管理
            precision_context: 精度上下文
        """
        # 设置精度上下文
        self.precision_context = precision_context or MATH.PrecisionContext.high_precision()

        # 转换为Decimal
        self.initial_bankroll = Decimal(str(initial_bankroll))
        self.kelly_strategy = kelly_strategy
        self.fraction_multiplier = Decimal(str(fraction_multiplier))
        self.min_edge_threshold = Decimal(str(min_edge_threshold))
        self.max_stake_percentage = Decimal(str(max_stake_percentage))
        self.enable_dynamic_adjustment = enable_dynamic_adjustment
        self.enable_risk_management = enable_risk_management

        # 初始化投资组合状态
        self.portfolio = PortfolioState(
            total_bankroll=self.initial_bankroll,
            available_cash=self.initial_bankroll,
            committed_stakes=Decimal("0"),
            max_drawdown=Decimal("0"),
            current_drawdown=Decimal("0"),
            win_rate=Decimal("0"),
            total_bets=0,
            winning_bets=0,
        )

        # 历史记录
        self.bet_history: List[Dict[str, Any]] = []
        self.performance_history: List[Tuple[datetime, Decimal]] = []

        # 动态调整参数
        self.volatility_history: List[Decimal] = []
        self.confidence_adjustments: Dict[str, Decimal] = {}

        # 生产环境安全验证器
        settings = get_settings()
        if production_safety_config is None:
            # 从环境变量读取配置，或使用默认值
            production_safety_config = ProductionSafetyConfig(
                enabled=settings.application.environment == "production",
                max_stake_percentage_of_bankroll=Decimal(
                    os.getenv("KELLY_MAX_STAKE_PERCENTAGE", "0.05")
                ),
                max_daily_stake_percentage=Decimal(
                    os.getenv("KELLY_MAX_DAILY_STAKE_PERCENTAGE", "0.20")
                ),
                emergency_stop_enabled=os.getenv("KELLY_EMERGENCY_STOP", "true").lower() == "true",
                manual_override_required=os.getenv("KELLY_MANUAL_OVERRIDE", "false").lower() == "true",
                audit_log_enabled=settings.application.environment == "production",
                risk_alert_threshold=Decimal(
                    os.getenv("KELLY_RISK_ALERT_THRESHOLD", "0.03")
                )
            )

        self.safety_validator = ProductionSafetyValidator(production_safety_config)

        # 统计信息
        self.stats = {
            "total_recommendations": 0,
            "accepted_bets": 0,
            "rejected_bets": 0,
            "safety_blocks": 0,
            "manual_reviews": 0,
            "total_profit_loss": Decimal("0"),
            "max_single_win": Decimal("0"),
            "max_single_loss": Decimal("0"),
            "avg_kelly_fraction": Decimal("0"),
            "last_updated": None,
        }

        logger.info(
            f"凯利准则系统初始化完成: 初始资金={self.initial_bankroll}, "
            f"策略={kelly_strategy.value}, 分数比例={self.fraction_multiplier}, "
            f"安全控制={'启用' if self.safety_validator.config.enabled else '禁用'}"
        )

    def get_safety_status(self) -> Dict[str, Any]:
        """
        获取安全系统状态

        Returns:
            Dict[str, Any]: 安全状态信息
        """
        return {
            "safety_enabled": self.safety_validator.config.enabled,
            "max_stake_percentage": float(self.safety_validator.config.max_stake_percentage_of_bankroll * 100),
            "max_daily_stake_percentage": float(self.safety_validator.config.max_daily_stake_percentage * 100),
            "emergency_stop_enabled": self.safety_validator.config.emergency_stop_enabled,
            "manual_override_required": self.safety_validator.config.manual_override_required,
            "audit_log_enabled": self.safety_validator.config.audit_log_enabled,
            "daily_stake_total": float(self.safety_validator.daily_stake_total),
            "high_value_bets_count": self.safety_validator.high_value_bets_count,
            "safety_blocks_count": self.stats["safety_blocks"],
            "manual_reviews_count": self.stats["manual_reviews"]
        }

    def emergency_stop(self, reason: str = "手动紧急停止"):
        """
        紧急停止所有投注

        Args:
            reason: 停止原因
        """
        if self.safety_validator.config.emergency_stop_enabled:
            self.safety_validator.config.enabled = False
            logger.critical(f"🚨 紧急停止已激活: {reason}")
            return True
        else:
            logger.warning("⚠️ 紧急停止功能已禁用")
            return False

    def reset_daily_counters(self):
        """重置日计数器"""
        self.safety_validator.reset_daily_counters()
        logger.info("📅 日计数器已重置")

    def enable_manual_override(self, reason: str = "人工覆盖激活"):
        """
        启用人工覆盖模式

        Args:
            reason: 激活原因
        """
        self.safety_validator.config.manual_override_required = True
        logger.info(f"👥 人工覆盖模式已启用: {reason}")

    def disable_manual_override(self, reason: str = "人工覆盖禁用"):
        """
        禁用人工覆盖模式

        Args:
            reason: 禁用原因
        """
        self.safety_validator.config.manual_override_required = False
        logger.info(f"🤖 人工覆盖模式已禁用: {reason}")

    def calculate_kelly_fraction(
        self,
        decimal_odds: Union[float, str, Decimal],
        predicted_prob: Union[float, str, Decimal],
        outcome: str = "unknown",
        confidence: Union[float, str, Decimal] = Decimal("1.0"),
    ) -> Dict[str, Any]:
        """
        计算凯利投注比例

        Args:
            decimal_odds: 小数赔率
            predicted_prob: 预测概率
            outcome: 投注结果
            confidence: 置信度

        Returns:
            Dict[str, Any]: 凯利计算结果
        """
        with self.precision_context:
            # 转换为Decimal
            odds = Decimal(str(decimal_odds))
            prob = Decimal(str(predicted_prob))
            conf = Decimal(str(confidence))

            # 验证输入
            validation_result = self._validate_inputs(odds, prob)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "kelly_fraction": Decimal("0"),
                    "edge": Decimal("0"),
                    "expected_value": Decimal("0"),
                }

            # 计算净赔率
            net_odds = odds - Decimal("1")

            # 计算优势（Edge）
            edge = (prob * odds) - Decimal("1")

            # 检查是否值得投注
            if edge < self.min_edge_threshold:
                return {
                    "success": True,
                    "kelly_fraction": Decimal("0"),
                    "edge": edge,
                    "expected_value": edge,
                    "reasoning": f"优势 {edge:.3f} 低于最小阈值 {self.min_edge_threshold}",
                    "should_bet": False,
                }

            # 计算完整凯利比例
            full_kelly = (prob * net_odds - (Decimal("1") - prob)) / net_odds

            # 应用策略调整
            adjusted_kelly = self._apply_strategy_adjustment(
                full_kelly, prob, odds, outcome, conf
            )

            # 应用风险控制
            final_kelly = self._apply_risk_controls(adjusted_kelly, outcome)

            # 计算期望值
            expected_value = edge

            # 评估风险等级
            risk_level = self._assess_risk_level(final_kelly, edge, prob)

            # 生成推理说明
            reasoning = self._generate_reasoning(
                full_kelly, final_kelly, edge, prob, odds, risk_level
            )

            result = {
                "success": True,
                "kelly_fraction": final_kelly,
                "full_kelly": full_kelly,
                "edge": edge,
                "expected_value": expected_value,
                "net_odds": net_odds,
                "risk_level": risk_level.value,
                "should_bet": final_kelly > 0,
                "confidence_adjustment": self._get_confidence_adjustment(outcome, conf),
                "reasoning": reasoning,
                "strategy_applied": self.kelly_strategy.value,
            }

            # 更新统计信息
            self._update_calculation_stats(final_kelly)

            return result

    def generate_bet_recommendation(
        self,
        outcomes: Dict[str, Dict[str, Union[float, str, Decimal]]],
        bankroll: Optional[Union[float, str, Decimal]] = None,
        max_concurrent_bets: Optional[int] = None,
    ) -> List[BetRecommendation]:
        """
        生成投注建议

        Args:
            outcomes: 投注选项数据 {outcome: {odds: x, probability: y}}
            bankroll: 可用资金（如果不提供则使用当前资金）
            max_concurrent_bets: 最大同时投注数量

        Returns:
            List[BetRecommendation]: 投注建议列表
        """
        current_bankroll = Decimal(str(bankroll)) if bankroll is not None else self.portfolio.available_cash
        max_bets = max_concurrent_bets or self.MAX_CONCURRENT_BETS

        recommendations = []

        # 计算每个选项的凯利比例
        kelly_results = {}
        for outcome, data in outcomes.items():
            odds = data["odds"]
            prob = data["probability"]
            confidence = data.get("confidence", Decimal("1.0"))

            kelly_result = self.calculate_kelly_fraction(
                odds, prob, outcome, confidence
            )
            kelly_results[outcome] = kelly_result

        # 排序并选择最优选项
        valid_outcomes = [
            (outcome, result)
            for outcome, result in kelly_results.items()
            if result.get("should_bet", False)
        ]

        # 按凯利比例排序
        valid_outcomes.sort(key=lambda x: x[1]["kelly_fraction"], reverse=True)

        # 应用并发投注限制
        selected_outcomes = valid_outcomes[:max_bets]

        # 计算总投注比例
        total_kelly_fraction = sum(
            result["kelly_fraction"] for _, result in selected_outcomes
        )

        # 如果总比例超过安全限制，进行缩放
        if total_kelly_fraction > self.SAFETY_MULTIPLIER:
            scaling_factor = self.SAFETY_MULTIPLIER / total_kelly_fraction
        else:
            scaling_factor = Decimal("1")

        # 生成最终建议
        for outcome, result in selected_outcomes:
            scaled_kelly = result["kelly_fraction"] * scaling_factor

            # 计算投注金额
            stake_amount = current_bankroll * scaled_kelly

            # 确保不超过最大投注限制
            max_stake = current_bankroll * self.max_stake_percentage
            stake_amount = min(stake_amount, max_stake)

            # 确保不超过可用资金
            stake_amount = min(stake_amount, current_bankroll)

            # 🔒 生产环境安全验证
            safety_validation = self.safety_validator.validate_stake_amount(
                current_bankroll, stake_amount
            )

            # 更新统计信息
            if not safety_validation["valid"]:
                self.stats["safety_blocks"] += 1
                logger.warning(
                    f"🛡️ 投注被安全系统拦截: {safety_validation['reason']}"
                )

            if safety_validation["requires_manual_review"]:
                self.stats["manual_reviews"] += 1
                logger.warning(
                    f"👥 投注需要人工审查: {safety_validation['reason']}"
                )

            # 记录审计日志
            self.safety_validator.log_bet_decision({
                "outcome": outcome,
                "stake_amount": stake_amount,
                "current_bankroll": current_bankroll,
                "kelly_fraction": scaled_kelly,
                "safety_validation": safety_validation,
                "risk_level": result["risk_level"],
                "requires_manual_review": safety_validation["requires_manual_review"]
            })

            # 只有通过安全验证的投注才会被接受
            if stake_amount > 0 and safety_validation["valid"]:
                recommendation = BetRecommendation(
                    outcome=outcome,
                    odds=Decimal(str(outcomes[outcome]["odds"])),
                    predicted_prob=Decimal(str(outcomes[outcome]["probability"])),
                    kelly_fraction=scaled_kelly,
                    stake_amount=stake_amount,
                    expected_value=result["expected_value"],
                    confidence=Decimal(str(outcomes[outcome].get("confidence", Decimal("1.0")))),
                    risk_level=RiskLevel(result["risk_level"]),
                    reasoning=result["reasoning"],
                )
                recommendations.append(recommendation)

                # 更新日投注总额
                self.safety_validator.update_daily_stake(stake_amount)

        # 更新统计信息
        self.stats["total_recommendations"] += 1
        if recommendations:
            self.stats["accepted_bets"] += 1
        else:
            self.stats["rejected_bets"] += 1

        logger.info(
            f"生成了 {len(recommendations)} 个投注建议，总投注比例: {total_kelly_fraction:.3f}"
        )

        return recommendations

    def place_bet(
        self,
        recommendation: BetRecommendation,
        actual_stake: Optional[Union[float, str, Decimal]] = None,
    ) -> Dict[str, Any]:
        """
        执行投注

        Args:
            recommendation: 投注建议
            actual_stake: 实际投注金额（覆盖建议金额）

        Returns:
            Dict[str, Any]: 投注结果
        """
        stake = Decimal(str(actual_stake)) if actual_stake is not None else recommendation.stake_amount

        # 检查资金充足性
        if stake > self.portfolio.available_cash:
            return {
                "success": False,
                "error": f"资金不足：需要 {stake}，可用 {self.portfolio.available_cash}",
                "bet_id": None,
            }

        # 更新投资组合状态
        self.portfolio.available_cash -= stake
        self.portfolio.committed_stakes += stake
        self.portfolio.total_bets += 1

        # 记录投注
        bet_record = {
            "bet_id": len(self.bet_history) + 1,
            "timestamp": datetime.now(),
            "outcome": recommendation.outcome,
            "odds": recommendation.odds,
            "stake": stake,
            "predicted_prob": recommendation.predicted_prob,
            "kelly_fraction": recommendation.kelly_fraction,
            "expected_value": recommendation.expected_value,
            "status": "pending",
            "result": None,
            "profit_loss": None,
        }

        self.bet_history.append(bet_record)

        logger.info(
            f"投注已执行：{recommendation.outcome} 赔率={recommendation.odds} "
            f"金额={stake} 凯利比例={recommendation.kelly_fraction:.3f}"
        )

        return {
            "success": True,
            "bet_id": bet_record["bet_id"],
            "remaining_cash": self.portfolio.available_cash,
            "committed_stakes": self.portfolio.committed_stakes,
        }

    def settle_bet(
        self,
        bet_id: int,
        actual_outcome: str,
        result_profit_loss: Optional[Union[float, str, Decimal]] = None,
    ) -> Dict[str, Any]:
        """
        结算投注

        Args:
            bet_id: 投注ID
            actual_outcome: 实际结果
            result_profit_loss: 结果盈亏（如果不提供则自动计算）

        Returns:
            Dict[str, Any]: 结算结果
        """
        # 查找投注记录
        bet_record = None
        for record in self.bet_history:
            if record["bet_id"] == bet_id:
                bet_record = record
                break

        if not bet_record:
            return {"success": False, "error": f"投注ID {bet_id} 未找到"}

        if bet_record["status"] != "pending":
            return {"success": False, "error": f"投注 {bet_id} 已结算"}

        with self.precision_context:
            # 计算盈亏
            if result_profit_loss is not None:
                profit_loss = Decimal(str(result_profit_loss))
            else:
                if actual_outcome == bet_record["outcome"]:
                    # 获胜
                    profit_loss = bet_record["stake"] * bet_record["odds"] - bet_record["stake"]
                    self.portfolio.winning_bets += 1
                else:
                    # 失败
                    profit_loss = -bet_record["stake"]

            # 更新投注记录
            bet_record["status"] = "settled"
            bet_record["result"] = actual_outcome
            bet_record["profit_loss"] = profit_loss
            bet_record["settled_at"] = datetime.now()

            # 更新投资组合
            self.portfolio.committed_stakes -= bet_record["stake"]
            self.portfolio.available_cash += bet_record["stake"] + profit_loss
            self.portfolio.total_bankroll = (
                self.portfolio.available_cash + self.portfolio.committed_stakes
            )

            # 更新统计信息
            self.stats["total_profit_loss"] += profit_loss
            if profit_loss > self.stats["max_single_win"]:
                self.stats["max_single_win"] = profit_loss
            if profit_loss < self.stats["max_single_loss"]:
                self.stats["max_single_loss"] = profit_loss

            # 更新胜率
            self.portfolio.win_rate = (
                Decimal(str(self.portfolio.winning_bets)) / Decimal(str(self.portfolio.total_bets))
            )

            # 更新回撤
            self._update_drawdown()

            # 记录业绩历史
            self.performance_history.append((datetime.now(), self.portfolio.total_bankroll))

            # 更新波动率历史
            if profit_loss != 0:
                return_rate = profit_loss / bet_record["stake"]
                self.volatility_history.append(return_rate)
                if len(self.volatility_history) > self.VOLATILITY_WINDOW:
                    self.volatility_history.pop(0)

            logger.info(
                f"投注结算完成：ID={bet_id} 结果={actual_outcome} "
                f"盈亏={profit_loss} 总资金={self.portfolio.total_bankroll}"
            )

        return {
            "success": True,
            "bet_id": bet_id,
            "profit_loss": float(profit_loss),
            "total_bankroll": float(self.portfolio.total_bankroll),
            "current_win_rate": float(self.portfolio.win_rate),
            "current_drawdown": float(self.portfolio.current_drawdown),
        }

    def _validate_inputs(
        self,
        odds: Decimal,
        prob: Decimal
    ) -> Dict[str, Any]:
        """验证输入参数"""
        if odds <= Decimal("1"):
            return {
                "valid": False,
                "error": f"赔率必须大于1，当前值: {odds}"
            }

        if not (Decimal("0") <= prob <= Decimal("1")):
            return {
                "valid": False,
                "error": f"概率必须在[0,1]范围内，当前值: {prob}"
            }

        if odds * prob < Decimal("0.5"):
            return {
                "valid": False,
                "error": "预期回报过低，风险收益比不合理"
            }

        return {"valid": True}

    def _apply_strategy_adjustment(
        self,
        full_kelly: Decimal,
        prob: Decimal,
        odds: Decimal,
        outcome: str,
        confidence: Decimal,
    ) -> Decimal:
        """应用策略调整"""
        if self.kelly_strategy == KellyStrategy.FULL_KELLY:
            return full_kelly

        elif self.kelly_strategy == KellyStrategy.FRACTIONAL_KELLY:
            return full_kelly * self.fraction_multiplier

        elif self.kelly_strategy == KellyStrategy.CONSERVATIVE_KELLY:
            # 保守策略：使用更小的分数
            conservative_fraction = self.fraction_multiplier * Decimal("0.5")
            return full_kelly * conservative_fraction

        elif self.kelly_strategy == KellyStrategy.AGGRESSIVE_KELLY:
            # 激进策略：使用更大的分数，但有上限
            aggressive_fraction = min(
                self.fraction_multiplier * Decimal("1.5"),
                Decimal("0.5")  # 最大50%
            )
            return full_kelly * aggressive_fraction

        elif self.kelly_strategy == KellyStrategy.DYNAMIC_KELLY:
            # 动态策略：基于历史表现调整
            return self._calculate_dynamic_kelly(full_kelly, prob, odds, outcome, confidence)

        else:
            return full_kelly * self.fraction_multiplier

    def _calculate_dynamic_kelly(
        self,
        full_kelly: Decimal,
        prob: Decimal,
        odds: Decimal,
        outcome: str,
        confidence: Decimal,
    ) -> Decimal:
        """计算动态凯利比例"""
        base_fraction = self.fraction_multiplier

        # 基于历史胜率调整
        if self.portfolio.total_bets >= 10:
            historical_win_rate = self.portfolio.win_rate
            predicted_win_rate = prob

            # 如果历史胜率高于预测，增加投注比例
            if historical_win_rate > predicted_win_rate:
                win_rate_bonus = (historical_win_rate - predicted_win_rate) * Decimal("2")
                base_fraction += win_rate_bonus
            else:
                # 如果历史胜率低于预测，减少投注比例
                win_rate_penalty = (predicted_win_rate - historical_win_rate) * Decimal("1")
                base_fraction -= win_rate_penalty

        # 基于当前回撤调整
        drawdown_penalty = self.portfolio.current_drawdown * Decimal("2")
        base_fraction -= drawdown_penalty

        # 基于波动率调整
        if len(self.volatility_history) >= 5:
            recent_volatility = np.std([float(v) for v in self.volatility_history[-5:]])
            if recent_volatility > 0.3:  # 高波动率
                base_fraction *= Decimal("0.8")

        # 基于置信度调整
        if confidence < self.CONFIDENCE_THRESHOLD:
            confidence_penalty = (self.CONFIDENCE_THRESHOLD - confidence) * Decimal("2")
            base_fraction -= confidence_penalty

        # 确保在合理范围内
        base_fraction = max(Decimal("0.05"), min(Decimal("0.4"), base_fraction))

        return full_kelly * base_fraction

    def _apply_risk_controls(
        self,
        kelly_fraction: Decimal,
        outcome: str
    ) -> Decimal:
        """应用风险控制"""
        if not self.enable_risk_management:
            return kelly_fraction

        # 检查最大投注比例
        if kelly_fraction > self.max_stake_percentage:
            kelly_fraction = self.max_stake_percentage

        # 检查当前回撤
        if self.portfolio.current_drawdown > self.MAX_DRAWDOWN_LIMIT:
            # 回撤过大时减少投注
            drawdown_reduction = (
                (self.portfolio.current_drawdown - self.MAX_DRAWDOWN_LIMIT) * Decimal("5")
            )
            kelly_fraction = max(Decimal("0"), kelly_fraction - drawdown_reduction)

        # 检查资金储备
        reserve_requirement = self.portfolio.total_bankroll * self.MIN_BANKROLL_RESERVE
        available_for_betting = self.portfolio.available_cash - reserve_requirement

        if available_for_betting <= 0:
            return Decimal("0")

        # 检查并发投注数量
        active_bets = sum(
            1 for record in self.bet_history if record["status"] == "pending"
        )
        if active_bets >= self.MAX_CONCURRENT_BETS:
            return Decimal("0")

        return kelly_fraction

    def _assess_risk_level(
        self,
        kelly_fraction: Decimal,
        edge: Decimal,
        prob: Decimal
    ) -> RiskLevel:
        """评估风险等级"""
        # 综合考虑凯利比例、优势和概率
        risk_score = 0

        # 凯利比例风险
        if kelly_fraction > Decimal("0.15"):
            risk_score += 3
        elif kelly_fraction > Decimal("0.10"):
            risk_score += 2
        elif kelly_fraction > Decimal("0.05"):
            risk_score += 1

        # 优势风险
        if edge < Decimal("0.05"):
            risk_score += 2
        elif edge < Decimal("0.10"):
            risk_score += 1

        # 概率风险
        if prob < Decimal("0.3") or prob > Decimal("0.7"):
            risk_score += 1

        # 确定风险等级
        if risk_score >= 5:
            return RiskLevel.EXTREME
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_reasoning(
        self,
        full_kelly: Decimal,
        final_kelly: Decimal,
        edge: Decimal,
        prob: Decimal,
        odds: Decimal,
        risk_level: RiskLevel,
    ) -> str:
        """生成推理说明"""
        reasoning_parts = []

        # 基础计算
        reasoning_parts.append(
            f"完整凯利: {full_kelly:.3f} (优势: {edge:.3f}, 概率: {prob:.3f}, 赔率: {odds:.2f})"
        )

        # 策略调整
        if self.kelly_strategy != KellyStrategy.FULL_KELLY:
            reasoning_parts.append(f"应用{self.kelly_strategy.value}策略")
            if self.kelly_strategy == KellyStrategy.DYNAMIC_KELLY:
                reasoning_parts.append(f"动态调整基于历史表现和当前风险")

        # 风险控制
        if final_kelly != full_kelly:
            adjustment = full_kelly - final_kelly
            reasoning_parts.append(f"风险控制调整: -{adjustment:.3f}")

        # 风险等级
        reasoning_parts.append(f"风险等级: {risk_level.value}")

        # 最终建议
        reasoning_parts.append(f"建议投注比例: {final_kelly:.3f}")

        return "; ".join(reasoning_parts)

    def _get_confidence_adjustment(
        self,
        outcome: str,
        confidence: Decimal
    ) -> Decimal:
        """获取置信度调整系数"""
        if confidence >= Decimal("0.8"):
            return Decimal("1.0")
        elif confidence >= Decimal("0.6"):
            return Decimal("0.9")
        elif confidence >= Decimal("0.4"):
            return Decimal("0.8")
        else:
            return Decimal("0.7")

    def _update_calculation_stats(self, kelly_fraction: Decimal) -> None:
        """更新计算统计信息"""
        self.stats["total_recommendations"] += 1

        # 更新平均凯利比例
        total_recs = self.stats["total_recommendations"]
        current_avg = self.stats["avg_kelly_fraction"]
        self.stats["avg_kelly_fraction"] = (
            (current_avg * (total_recs - 1) + kelly_fraction) / total_recs
        )

        self.stats["last_updated"] = datetime.now().isoformat()

    def _update_drawdown(self) -> None:
        """更新回撤指标"""
        if len(self.performance_history) < 2:
            return

        # 当前资金
        current_bankroll = self.portfolio.total_bankroll

        # 计算历史最高点
        historical_peak = max(
            record[1] for record in self.performance_history
        )

        # 计算当前回撤
        if historical_peak > 0:
            self.portfolio.current_drawdown = (
                (historical_peak - current_bankroll) / historical_peak
            )
            self.portfolio.max_drawdown = max(
                self.portfolio.max_drawdown,
                self.portfolio.current_drawdown
            )

    def get_performance_report(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取业绩报告"""
        cutoff_date = datetime.now() - timedelta(days=days)

        # 筛选指定期间的记录
        recent_bets = [
            bet for bet in self.bet_history
            if bet["timestamp"] >= cutoff_date
        ]

        settled_bets = [bet for bet in recent_bets if bet["status"] == "settled"]
        winning_bets = [bet for bet in settled_bets if bet.get("profit_loss", 0) > 0]

        # 计算业绩指标
        total_staked = sum(bet["stake"] for bet in settled_bets)
        total_return = sum(
            bet["stake"] + bet.get("profit_loss", 0) for bet in settled_bets
        )
        total_profit = sum(bet.get("profit_loss", 0) for bet in settled_bets)

        roi = (total_profit / total_staked) if total_staked > 0 else Decimal("0")

        # 计算夏普比率
        if len(self.volatility_history) >= 2:
            avg_return = np.mean([float(v) for v in self.volatility_history])
            std_return = np.std([float(v) for v in self.volatility_history])
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # 计算最大连续亏损
        max_consecutive_losses = self._calculate_max_consecutive_losses(settled_bets)

        return {
            "period_days": days,
            "summary": {
                "total_bets": len(settled_bets),
                "winning_bets": len(winning_bets),
                "win_rate": float(len(winning_bets) / len(settled_bets)) if settled_bets else 0,
                "total_staked": float(total_staked),
                "total_return": float(total_return),
                "total_profit": float(total_profit),
                "roi": float(roi),
                "sharpe_ratio": sharpe_ratio,
                "max_consecutive_losses": max_consecutive_losses,
            },
            "current_portfolio": {
                "total_bankroll": float(self.portfolio.total_bankroll),
                "available_cash": float(self.portfolio.available_cash),
                "committed_stakes": float(self.portfolio.committed_stakes),
                "current_drawdown": float(self.portfolio.current_drawdown),
                "max_drawdown": float(self.portfolio.max_drawdown),
            },
            "risk_metrics": {
                "avg_kelly_fraction": float(self.stats["avg_kelly_fraction"]),
                "max_single_win": float(self.stats["max_single_win"]),
                "max_single_loss": float(self.stats["max_single_loss"]),
                "volatility": np.std([float(v) for v in self.volatility_history]) if self.volatility_history else 0,
            },
            "recommendation_stats": {
                "total_recommendations": self.stats["total_recommendations"],
                "accepted_bets": self.stats["accepted_bets"],
                "rejected_bets": self.stats["rejected_bets"],
                "acceptance_rate": (
                    float(self.stats["accepted_bets"]) / self.stats["total_recommendations"]
                    if self.stats["total_recommendations"] > 0 else 0
                ),
            },
        }

    def _calculate_max_consecutive_losses(
        self,
        settled_bets: List[Dict[str, Any]]
    ) -> int:
        """计算最大连续亏损"""
        max_consecutive = 0
        current_consecutive = 0

        for bet in sorted(settled_bets, key=lambda x: x["timestamp"]):
            if bet.get("profit_loss", 0) < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def get_portfolio_state(self) -> Dict[str, Any]:
        """获取投资组合状态"""
        return {
            "bankroll": {
                "total": float(self.portfolio.total_bankroll),
                "available": float(self.portfolio.available_cash),
                "committed": float(self.portfolio.committed_stakes),
                "initial": float(self.initial_bankroll),
                "growth": float(
                    (self.portfolio.total_bankroll - self.initial_bankroll) / self.initial_bankroll
                ),
            },
            "performance": {
                "total_bets": self.portfolio.total_bets,
                "winning_bets": self.portfolio.winning_bets,
                "win_rate": float(self.portfolio.win_rate),
                "current_drawdown": float(self.portfolio.current_drawdown),
                "max_drawdown": float(self.portfolio.max_drawdown),
            },
            "risk_status": {
                "risk_level": self._assess_current_risk_level(),
                "safety_margin": float(
                    (self.portfolio.available_cash - self.portfolio.total_bankroll * self.MIN_BANKROLL_RESERVE)
                    / self.portfolio.total_bankroll
                ),
                "leverage": float(self.portfolio.committed_stakes / self.portfolio.total_bankroll),
            },
        }

    def _assess_current_risk_level(self) -> str:
        """评估当前风险等级"""
        risk_score = 0

        # 回撤风险
        if self.portfolio.current_drawdown > Decimal("0.15"):
            risk_score += 3
        elif self.portfolio.current_drawdown > Decimal("0.10"):
            risk_score += 2
        elif self.portfolio.current_drawdown > Decimal("0.05"):
            risk_score += 1

        # 杠杆风险
        leverage = self.portfolio.committed_stakes / self.portfolio.total_bankroll
        if leverage > Decimal("0.3"):
            risk_score += 2
        elif leverage > Decimal("0.2"):
            risk_score += 1

        # 流动性风险
        cash_ratio = self.portfolio.available_cash / self.portfolio.total_bankroll
        if cash_ratio < Decimal("0.7"):
            risk_score += 2
        elif cash_ratio < Decimal("0.8"):
            risk_score += 1

        if risk_score >= 5:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "configuration": {
                "initial_bankroll": float(self.initial_bankroll),
                "kelly_strategy": self.kelly_strategy.value,
                "fraction_multiplier": float(self.fraction_multiplier),
                "min_edge_threshold": float(self.min_edge_threshold),
                "max_stake_percentage": float(self.max_stake_percentage),
                "enable_dynamic_adjustment": self.enable_dynamic_adjustment,
                "enable_risk_management": self.enable_risk_management,
            },
            "statistics": {
                "total_recommendations": self.stats["total_recommendations"],
                "accepted_bets": self.stats["accepted_bets"],
                "rejected_bets": self.stats["rejected_bets"],
                "total_profit_loss": float(self.stats["total_profit_loss"]),
                "max_single_win": float(self.stats["max_single_win"]),
                "max_single_loss": float(self.stats["max_single_loss"]),
                "avg_kelly_fraction": float(self.stats["avg_kelly_fraction"]),
            },
            "current_state": self.get_portfolio_state(),
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"KellyCriterion(bankroll={self.portfolio.total_bankroll:.2f}, "
            f"strategy={self.kelly_strategy.value}, "
            f"bets={self.portfolio.total_bets}, "
            f"win_rate={self.portfolio.win_rate:.1%})"
        )