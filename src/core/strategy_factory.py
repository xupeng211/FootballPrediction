"""
策略工厂 V1.0
根据配置创建沙盒/实战模式的策略引擎
"""

import logging

from src.core.config import Config, get_config
from src.logic.strategy_engine import BettingParameters, StrategyEngine, StrategyMode

logger = logging.getLogger(__name__)


class StrategyFactory:
    """策略工厂类"""

    @staticmethod
    def create_engine(config: Config | None = None) -> StrategyEngine:
        """
        根据配置创建策略引擎

        Args:
            config: 配置对象，如果为None则使用默认配置

        Returns:
            StrategyEngine: 配置好的策略引擎
        """
        if config is None:
            config = get_config()

        # 确定策略模式
        if config.strategy.is_live_mode():
            mode = StrategyMode.LIVE
            logger.info("🔥 创建实战模式策略引擎")
        else:
            mode = StrategyMode.SANDBOX
            logger.info("🧪 创建沙盒模式策略引擎")

        # 创建下注参数
        betting_params = BettingParameters(
            max_single_bet_pct=config.strategy.max_single_bet_pct,
            max_daily_bets=config.strategy.max_daily_bets,
            max_consecutive_losses=config.strategy.max_consecutive_losses,
            max_total_exposure=config.strategy.max_total_exposure,
            kelly_fraction=config.strategy.kelly_fraction,
            max_kelly_pct=config.strategy.max_kelly_pct,
            min_kelly_pct=config.strategy.min_kelly_pct,
            min_edge_threshold=config.strategy.min_edge_threshold,
            min_expected_value=config.strategy.min_expected_value,
            confidence_threshold=config.strategy.confidence_threshold,
            min_odds=config.strategy.min_odds,
            max_odds=config.strategy.max_odds,
            odds_range_factor=config.strategy.odds_range_factor,
        )

        # 创建策略引擎
        engine = StrategyEngine(params=betting_params, mode=mode)

        logger.info(f"✅ 策略引擎创建完成 - 模式: {mode.value}")
        logger.info(
            f"   风控参数: 单场{config.strategy.max_single_bet_pct:.1%} | "
            f"每日{config.strategy.max_daily_bets}次 | "
            f"Kelly系数{config.strategy.kelly_fraction:.2f}"
        )

        return engine

    @staticmethod
    def get_current_mode(config: Config | None = None) -> str:
        """获取当前策略模式"""
        if config is None:
            config = get_config()

        return config.strategy.mode

    @staticmethod
    def switch_mode(new_mode: str, config: Config | None = None) -> bool:
        """
        切换策略模式

        Args:
            new_mode: 新模式 ('SANDBOX' 或 'LIVE')
            config: 配置对象

        Returns:
            bool: 切换是否成功
        """
        if new_mode.upper() not in ["SANDBOX", "LIVE"]:
            logger.error(f"无效的策略模式: {new_mode}")
            return False

        if config is None:
            config = get_config()

        old_mode = config.strategy.mode
        config.strategy.mode = new_mode.upper()

        logger.warning(f"⚠️ 策略模式切换: {old_mode} → {new_mode.upper()}")

        if new_mode.upper() == "LIVE":
            logger.warning("🚨 警告: 已切换到实战模式！将进行真实下注！")
        else:
            logger.info("✅ 已切换到沙盒模式，仅进行分析和建议")

        return True


# 全局策略引擎实例（延迟加载）
_strategy_engine: StrategyEngine | None = None


def get_strategy_engine() -> StrategyEngine:
    """
    获取全局策略引擎实例（单例模式）

    Returns:
        StrategyEngine: 全局策略引擎实例
    """
    global _strategy_engine

    if _strategy_engine is None:
        _strategy_engine = StrategyFactory.create_engine()

    return _strategy_engine


def reset_strategy_engine():
    """重置全局策略引擎实例"""
    global _strategy_engine
    _strategy_engine = None
    logger.info("🔄 策略引擎实例已重置")


def is_live_mode() -> bool:
    """检查是否为实战模式"""
    config = get_config()
    return config.strategy.is_live_mode()


def is_sandbox_mode() -> bool:
    """检查是否为沙盒模式"""
    config = get_config()
    return config.strategy.is_sandbox_mode()


def switch_to_live_mode() -> bool:
    """切换到实战模式"""
    return StrategyFactory.switch_mode("LIVE")


def switch_to_sandbox_mode() -> bool:
    """切换到沙盒模式"""
    return StrategyFactory.switch_mode("SANDBOX")


# 便利函数
def get_strategy_mode() -> str:
    """获取当前策略模式"""
    return StrategyFactory.get_current_mode()


def get_strategy_info() -> dict:
    """获取策略信息摘要"""
    config = get_config()
    engine = get_strategy_engine()

    return {
        "mode": config.strategy.mode,
        "is_live": config.strategy.is_live_mode(),
        "risk_parameters": {
            "max_single_bet_pct": config.strategy.max_single_bet_pct,
            "max_daily_bets": config.strategy.max_daily_bets,
            "max_consecutive_losses": config.strategy.max_consecutive_losses,
            "kelly_fraction": config.strategy.kelly_fraction,
        },
        "portfolio_status": {
            "current_capital": engine.portfolio.current_capital,
            "consecutive_losses": engine.portfolio.consecutive_losses,
            "daily_bets": engine.portfolio.daily_bets,
            "risk_level": engine.portfolio.risk_level.value,
        },
        "system_metrics": engine.risk_metrics,
    }
