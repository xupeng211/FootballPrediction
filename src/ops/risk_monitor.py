#!/usr/bin/env python3
"""
V19.4 自动止损哨兵系统 (Auto-Stop Loss Sentinel)
====================================================

风控监控模块，防止模型在真实市场中产生不可控回撤。

核心功能:
1. 连续亏损监控: 连续亏损超过 5 个单位时触发告警
2. 最大回撤监控: 总回撤超过初始资金的 15% 时触发熔断
3. 每日风险报告: 自动生成风险状态报告
4. TaskRunner 控制: 风控触发时自动停止预测导出

作者: V19.4 风控团队
日期: 2025-12-23
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ============================================
# V19.4.1 愿景红线系统 (Vision Guardrails)
# ============================================


class VisionViolationException(Exception):
    """项目愿景违背异常 - 当操作严重违反项目愿景时抛出"""

    pass


class VisionLimits:
    """项目愿景硬性约束 - 从 docs/PROJECT_VISION.md 提取"""

    # 财务约束
    MAX_STAKE_PCT = 0.05  # 单笔下注 ≤ 5% 本金
    MAX_DAILY_LOSS_PCT = 0.10  # 单日最大亏损 10%
    MAX_DRAWDOWN_PCT = 0.15  # 最大回撤 15%

    # EV 约束
    MIN_EV = 0.06  # 最小期望收益 6%
    MAX_EV = 0.10  # 最大期望收益 10%

    # 执行约束
    MAX_CONSECUTIVE_LOSSES = 5  # 连续亏损熔断
    LEVERAGE_ENABLED = False  # 严禁杠杆

    # 愿景参数
    TARGET_ANNUAL_RETURN = 0.25  # 目标年化收益 25%
    TARGET_EXECUTION_RATE = 0.05  # 目标执行率 < 5%


class RiskLevel(Enum):
    """风险等级"""

    NORMAL = "normal"  # 正常运行
    WARNING = "warning"  # 警告级别
    CRITICAL = "critical"  # 严重级别
    EMERGENCY = "emergency"  # 紧急熔断


@dataclass
class RiskMetrics:
    """风险指标"""

    # 当前状态
    current_balance: float = 1000.0  # 当前余额
    initial_balance: float = 1000.0  # 初始余额
    max_balance: float = 1000.0  # 历史最高余额

    # 亏损指标
    consecutive_losses: int = 0  # 连续亏损次数
    current_drawdown: float = 0.0  # 当前回撤
    max_drawdown: float = 0.0  # 最大回撤
    max_drawdown_pct: float = 0.0  # 最大回撤百分比

    # 交易统计
    total_bets: int = 0  # 总下注次数
    winning_bets: int = 0  # 盈利下注数
    losing_bets: int = 0  # 亏损下注数
    total_profit: float = 0.0  # 总盈利
    total_loss: float = 0.0  # 总亏损

    # 风险阈值配置
    max_consecutive_losses: int = 5  # 最大连续亏损次数
    max_drawdown_pct_limit: float = 0.15  # 最大回撤百分比限制 (15%)

    # 告警状态
    last_alert_time: datetime | None = None
    alert_cooldown_minutes: int = 60  # 告警冷却时间（分钟）
    is_emergency_stopped: bool = False  # 是否已紧急熔断

    def __post_init__(self):
        """初始化后处理：确保 current_balance 和 max_balance 与 initial_balance 同步"""
        if self.current_balance == 1000.0 and self.initial_balance != 1000.0:
            self.current_balance = self.initial_balance
        if self.max_balance == 1000.0 and self.initial_balance != 1000.0:
            self.max_balance = self.initial_balance
        # 确保当前余额不超过历史最高
        if self.current_balance > self.max_balance:
            self.max_balance = self.current_balance


@dataclass
class BetRecord:
    """下注记录"""

    match_id: str
    home_team: str
    away_team: str
    prediction: str  # H/D/A
    actual_result: str | None = None
    stake: float = 1.0
    odds: float = 1.0
    profit: float = 0.0
    timestamp: datetime = None
    status: str = "pending"  # pending, won, lost, void


class RiskMonitor:
    """
    自动止损哨兵系统

    核心功能:
    1. 监控下注结果，更新风险指标
    2. 检查风控阈值，触发告警或熔断
    3. 生成每日风险报告
    4. 发送告警通知
    """

    def __init__(self, initial_balance: float = 1000.0, config_path: str = None, load_state: bool = True):
        """
        初始化风控监控系统

        Args:
            initial_balance: 初始资金（默认1000单位）
            config_path: 配置文件路径
            load_state: 是否从磁盘加载历史状态（默认True，测试时可设为False）

        Raises:
            VisionViolationException: 如果配置违反项目愿景
        """
        # V19.4.1 修复：先创建 metrics，再进行愿景校验
        self.metrics = RiskMetrics(initial_balance=initial_balance)
        self.bet_records: list[BetRecord] = []
        self._initial_balance_provided = initial_balance  # 记录显式传入的初始余额

        # 加载配置
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                config = json.load(f)
                self.metrics.max_consecutive_losses = config.get("max_consecutive_losses", 5)
                self.metrics.max_drawdown_pct_limit = config.get("max_drawdown_pct_limit", 0.15)

                # V19.4.1 愿景校验：配置文件中的阈值不能违背愿景
                if self.metrics.max_drawdown_pct_limit > VisionLimits.MAX_DRAWDOWN_PCT:
                    logger.critical(
                        f"VIOLATION: 配置的回撤限制 ({self.metrics.max_drawdown_pct_limit:.0%}) "
                        f"超过愿景上限 ({VisionLimits.MAX_DRAWDOWN_PCT:.0%})"
                    )
                    raise VisionViolationException(
                        f"Max drawdown limit exceeds vision constraint: "
                        f"{self.metrics.max_drawdown_pct_limit:.0%} > {VisionLimits.MAX_DRAWDOWN_PCT:.0%}"
                    )

        # V19.4.1 愿景校验：初始化时检查配置是否符合愿景（在 metrics 创建后调用）
        self._verify_vision_compliance(initial_balance)

        # 数据存储路径
        self.data_dir = Path("/home/user/projects/FootballPrediction/data/risk")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 加载历史数据（仅在 load_state=True 时）
        if load_state:
            self._load_state()

        logger.info(f"风控监控系统初始化完成，初始资金: {initial_balance}")
        logger.info(f"V19.4.1 愿景红线已激活：单笔下注≤{VisionLimits.MAX_STAKE_PCT:.0%}，严禁杠杆")

    def _verify_vision_compliance(self, initial_balance: float):
        """
        V19.4.1 愿景校验：验证初始配置符合项目愿景

        Args:
            initial_balance: 初始资金

        Raises:
            VisionViolationException: 如果配置违反愿景
        """
        # 检查杠杆是否被禁用
        if VisionLimits.LEVERAGE_ENABLED:
            logger.critical("VIOLATION: 杠杆已被配置为启用，但项目愿景严禁使用杠杆！")
            raise VisionViolationException("Leverage is strictly forbidden by project vision (docs/PROJECT_VISION.md)")

        # 检查最大连续亏损次数
        if self.metrics.max_consecutive_losses > VisionLimits.MAX_CONSECUTIVE_LOSSES:
            logger.warning(
                f"WARNING: 连续亏损限制 ({self.metrics.max_consecutive_losses}) "
                f"大于愿景推荐值 ({VisionLimits.MAX_CONSECUTIVE_LOSSES})"
            )

        logger.info("✅ 愿景合规性检查通过")

    def _load_state(self):
        """加载历史状态"""
        state_file = self.data_dir / "risk_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    # 恢复风险指标
                    for key, value in state.items():
                        if hasattr(self.metrics, key):
                            setattr(self.metrics, key, value)
                logger.info(f"历史状态已加载，当前余额: {self.metrics.current_balance}")
            except Exception as e:
                logger.warning(f"加载历史状态失败: {e}")

    def _save_state(self):
        """保存当前状态"""
        state_file = self.data_dir / "risk_state.json"
        with open(state_file, "w") as f:
            state = {
                "current_balance": self.metrics.current_balance,
                "initial_balance": self.metrics.initial_balance,
                "max_balance": self.metrics.max_balance,
                "consecutive_losses": self.metrics.consecutive_losses,
                "current_drawdown": self.metrics.current_drawdown,
                "max_drawdown": self.metrics.max_drawdown,
                "max_drawdown_pct": self.metrics.max_drawdown_pct,
                "total_bets": self.metrics.total_bets,
                "winning_bets": self.metrics.winning_bets,
                "losing_bets": self.metrics.losing_bets,
                "total_profit": self.metrics.total_profit,
                "total_loss": self.metrics.total_loss,
                "is_emergency_stopped": self.metrics.is_emergency_stopped,
            }
            json.dump(state, f, indent=2)

    def place_bet(
        self, match_id: str, home_team: str, away_team: str, prediction: str, odds: float, stake: float = 1.0
    ) -> BetRecord:
        """
        记录下注（在比赛开始前调用）

        Args:
            match_id: 比赛ID
            home_team: 主队
            away_team: 客队
            prediction: 预测结果 (H/D/A)
            odds: 赔率
            stake: 下注金额

        Returns:
            BetRecord: 下注记录

        Raises:
            RuntimeError: 如果系统已熔断
            VisionViolationException: 如果下注违反愿景红线
        """
        # 检查是否已熔断
        if self.metrics.is_emergency_stopped:
            logger.error("系统已紧急熔断，禁止新下注！")
            raise RuntimeError("Emergency stop activated - no new bets allowed")

        # 检查风险状态
        risk_level = self.check_risk_level()
        if risk_level == RiskLevel.EMERGENCY:
            logger.error("风险等级为紧急，禁止新下注！")
            raise RuntimeError(f"Risk level is {risk_level.value} - no new bets allowed")

        # V19.4.1 愿景校验：检查下注金额是否符合愿景
        stake_pct = stake / self.metrics.current_balance
        if stake_pct > VisionLimits.MAX_STAKE_PCT:
            logger.critical(
                f"VIOLATION: 下注金额 ({stake:.2f}, {stake_pct:.1%}) 超过愿景上限 ({VisionLimits.MAX_STAKE_PCT:.0%})"
            )
            raise VisionViolationException(
                f"Stake exceeds vision limit: {stake_pct:.1%} > {VisionLimits.MAX_STAKE_PCT:.0%} "
                f"(docs/PROJECT_VISION.md - 原则一: 单笔下注 ≤ 5% 本金)"
            )

        # V19.4.1 愿景校验：检查杠杆（虽然本系统不使用杠杆，但作为防护性检查）
        if VisionLimits.LEVERAGE_ENABLED:
            logger.critical("VIOLATION: 系统检测到杠杆已启用，但项目愿景严禁使用杠杆！")
            raise VisionViolationException("Leverage is strictly forbidden by project vision (docs/PROJECT_VISION.md)")

        record = BetRecord(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            prediction=prediction,
            stake=stake,
            odds=odds,
            timestamp=datetime.now(),
            status="pending",
        )

        self.bet_records.append(record)
        self.metrics.total_bets += 1

        logger.info(
            f"✅ 下注记录已创建: {home_team} vs {away_team} | "
            f"预测: {prediction} | 赔率: {odds:.2f} | "
            f"下注: {stake:.2f} ({stake_pct:.1%}) [愿景合规]"
        )

        self._save_state()
        return record

    def settle_bet(self, match_id: str, actual_result: str) -> float | None:
        """
        结算下注（比赛结束后调用）

        Args:
            match_id: 比赛ID
            actual_result: 实际结果 (H/D/A)

        Returns:
            float: 盈亏金额
        """
        # 查找对应的下注记录
        record = None
        for r in self.bet_records:
            if r.match_id == match_id and r.status == "pending":
                record = r
                break

        if record is None:
            logger.warning(f"未找到未结算的下注记录: {match_id}")
            return None

        # 结算
        record.actual_result = actual_result
        record.status = "settled"

        if record.prediction == actual_result:
            # 预测正确
            profit = (record.odds - 1) * record.stake
            record.profit = profit
            record.status = "won"
            self.metrics.winning_bets += 1
            self.metrics.total_profit += profit
            self.metrics.consecutive_losses = 0  # 重置连续亏损
        else:
            # 预测错误
            profit = -record.stake
            record.profit = profit
            record.status = "lost"
            self.metrics.losing_bets += 1
            self.metrics.total_loss += abs(profit)
            self.metrics.consecutive_losses += 1

        # 更新余额
        self.metrics.current_balance += profit

        # 更新历史最高余额
        if self.metrics.current_balance > self.metrics.max_balance:
            self.metrics.max_balance = self.metrics.current_balance

        # 计算回撤
        self.metrics.current_drawdown = self.metrics.max_balance - self.metrics.current_balance
        drawdown_pct = self.metrics.current_drawdown / self.metrics.max_balance
        self.metrics.current_drawdown = drawdown_pct

        if drawdown_pct > self.metrics.max_drawdown_pct:
            self.metrics.max_drawdown_pct = drawdown_pct
            self.metrics.max_drawdown = self.metrics.current_drawdown

        # 保存状态
        self._save_state()

        logger.info(
            f"下注结算: {record.home_team} vs {record.away_team} "
            f"预测:{record.prediction} 实际:{actual_result} "
            f"盈亏:{profit:.2f} 余额:{self.metrics.current_balance:.2f}"
        )

        # 检查是否触发风控
        self._check_and_alert()

        return profit

    def check_risk_level(self) -> RiskLevel:
        """
        检查当前风险等级

        Returns:
            RiskLevel: 风险等级
        """
        # 检查紧急熔断条件
        if self.metrics.is_emergency_stopped:
            return RiskLevel.EMERGENCY

        # 检查连续亏损
        if self.metrics.consecutive_losses >= self.metrics.max_consecutive_losses:
            return RiskLevel.EMERGENCY

        # 检查回撤
        if self.metrics.max_drawdown_pct >= self.metrics.max_drawdown_pct_limit:
            return RiskLevel.EMERGENCY

        # 检查警告级别
        if self.metrics.consecutive_losses >= self.metrics.max_consecutive_losses - 2:
            return RiskLevel.CRITICAL

        if self.metrics.max_drawdown_pct >= self.metrics.max_drawdown_pct_limit * 0.8:
            return RiskLevel.CRITICAL

        if self.metrics.consecutive_losses >= 3:
            return RiskLevel.WARNING

        if self.metrics.max_drawdown_pct >= 0.05:  # 5% 回撤
            return RiskLevel.WARNING

        return RiskLevel.NORMAL

    def _check_and_alert(self):
        """检查风控条件并发送告警"""
        risk_level = self.check_risk_level()

        if risk_level == RiskLevel.EMERGENCY:
            # 触发紧急熔断
            self.metrics.is_emergency_stopped = True
            self._send_emergency_alert()
            self._save_state()

        elif risk_level == RiskLevel.CRITICAL:
            # 发送严重警告
            if self._should_send_alert():
                self._send_alert(risk_level)
                self.metrics.last_alert_time = datetime.now()

        elif risk_level == RiskLevel.WARNING:
            if self._should_send_alert():
                self._send_alert(risk_level)
                self.metrics.last_alert_time = datetime.now()

    def _should_send_alert(self) -> bool:
        """判断是否应该发送告警（冷却期检查）"""
        if self.metrics.last_alert_time is None:
            return True

        cooldown = timedelta(minutes=self.metrics.alert_cooldown_minutes)
        return datetime.now() - self.metrics.last_alert_time >= cooldown

    def _send_emergency_alert(self):
        """发送紧急熔断告警"""
        subject = "🚨 EMERGENCY - V19.4 策略熔断触发"
        message = self._generate_alert_message(RiskLevel.EMERGENCY)
        self._send_email(subject, message)

        # 记录到文件
        alert_file = self.data_dir / f"emergency_stop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(alert_file, "w") as f:
            f.write(message)
        logger.critical(f"紧急熔断已触发！详情已保存到: {alert_file}")

    def _send_alert(self, risk_level: RiskLevel):
        """发送风控告警"""
        subject = f"⚠️ RISK ALERT - V19.4 {risk_level.value.upper()}"
        message = self._generate_alert_message(risk_level)
        self._send_email(subject, message)
        logger.warning(f"风控告警已发送: {risk_level.value}")

    def _generate_alert_message(self, risk_level: RiskLevel) -> str:
        """生成告警消息"""
        emoji = {RiskLevel.NORMAL: "✅", RiskLevel.WARNING: "⚠️", RiskLevel.CRITICAL: "🔴", RiskLevel.EMERGENCY: "🚨"}

        message = f"""
{"=" * 70}
{emoji[risk_level]} V19.4 风控告警 - {risk_level.value.upper()}
{"=" * 70}
⏰ 触发时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📊 当前余额: {self.metrics.current_balance:.2f}
💰 初始余额: {self.metrics.initial_balance:.2f}
📈 总盈亏: {self.metrics.current_balance - self.metrics.initial_balance:+.2f}
{"─" * 70}

📉 风险指标:
├─ 连续亏损: {self.metrics.consecutive_losses} / {self.metrics.max_consecutive_losses} (阈值)
├─ 当前回撤: {self.metrics.max_drawdown_pct:.2%}
├─ 最大回撤: {self.metrics.max_drawdown_pct:.2%} / {self.metrics.max_drawdown_pct_limit:.0%} (阈值)
├─ 总下注: {self.metrics.total_bets}
├─ 盈利: {self.metrics.winning_bets} / {self.metrics.total_bets if self.metrics.total_bets > 0 else 1}
└─ 总盈亏: {self.metrics.total_profit - self.metrics.total_loss:+.2f}

{"─" * 70}
🎯 当前状态: {self.metrics.is_emergency_stopped and "已熔断 - 停止所有新下注" or "运行中"}
{"=" * 70}
"""
        return message

    def _send_email(self, subject: str, message: str):
        """发送邮件告警"""
        # TODO: 配置邮件服务器
        logger.info(f"[邮件模拟] {subject}")
        logger.info(message)

    def reset_emergency_stop(self):
        """重置紧急熔断（需手动操作）"""
        logger.warning("正在重置紧急熔断状态...")
        self.metrics.is_emergency_stopped = False
        self.metrics.consecutive_losses = 0
        self._save_state()
        logger.info("紧急熔断已重置，系统恢复正常运行")

    def generate_daily_report(self) -> pd.DataFrame:
        """
        生成每日风险报告

        Returns:
            pd.DataFrame: 每日报告数据
        """
        # 统计今天的下注
        today = datetime.now().date()
        today_bets = [r for r in self.bet_records if r.timestamp.date() == today and r.status in ["won", "lost"]]

        if not today_bets:
            logger.info("今天没有已结算的下注")
            return pd.DataFrame()

        # 统计
        today_profit = sum(r.profit for r in today_bets)
        today_wins = sum(1 for r in today_bets if r.status == "won")
        today_losses = sum(1 for r in today_bets if r.status == "lost")
        today_yield = (today_profit / len(today_bets)) * 100 if today_bets else 0

        report = pd.DataFrame(
            [
                {
                    "date": today,
                    "total_bets": len(today_bets),
                    "wins": today_wins,
                    "losses": today_losses,
                    "profit": today_profit,
                    "yield_pct": today_yield,
                    "balance": self.metrics.current_balance,
                    "drawdown_pct": self.metrics.max_drawdown_pct,
                    "risk_level": self.check_risk_level().value,
                }
            ]
        )

        # 保存报告
        report_file = self.data_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.csv"
        report.to_csv(report_file, index=False)
        logger.info(f"每日报告已保存: {report_file}")

        return report

    def get_status_summary(self) -> dict:
        """获取状态摘要"""
        return {
            "risk_level": self.check_risk_level().value,
            "balance": self.metrics.current_balance,
            "profit_loss": self.metrics.current_balance - self.metrics.initial_balance,
            "yield_pct": ((self.metrics.current_balance - self.metrics.initial_balance) / self.metrics.initial_balance)
            * 100,
            "consecutive_losses": self.metrics.consecutive_losses,
            "max_drawdown_pct": self.metrics.max_drawdown_pct,
            "is_stopped": self.metrics.is_emergency_stopped,
            "total_bets": self.metrics.total_bets,
            "win_rate": (self.metrics.winning_bets / self.metrics.total_bets * 100)
            if self.metrics.total_bets > 0
            else 0,
        }


# ============================================
# 便捷函数
# ============================================


def get_risk_monitor(config_path: str = None) -> RiskMonitor:
    """获取风控监控实例"""
    return RiskMonitor(config_path=config_path)


# ============================================
# 单元测试
# ============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 70)
    print("V19.4 风控监控系统测试")
    print("=" * 70)

    # 创建风控监控
    monitor = RiskMonitor(initial_balance=1000.0)

    # 模拟下注
    print("\n模拟下注和结算...")
    monitor.place_bet("match_1", "Team A", "Team B", "H", odds=2.0, stake=10)
    profit = monitor.settle_bet("match_1", "H")  # 胜
    print(f"  第1场: 盈亏 {profit:.2f}, 余额 {monitor.metrics.current_balance:.2f}")

    monitor.place_bet("match_2", "Team C", "Team D", "A", odds=3.0, stake=10)
    profit = monitor.settle_bet("match_2", "H")  # 负
    print(f"  第2场: 盈亏 {profit:.2f}, 余额 {monitor.metrics.current_balance:.2f}")

    # 显示状态摘要
    print("\n当前状态:")
    summary = monitor.get_status_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
