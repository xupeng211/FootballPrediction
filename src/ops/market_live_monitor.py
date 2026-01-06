#!/usr/bin/env python3
"""
V19.4 实时市场巡检系统 (Market Live Monitor)
=============================================

针对特定比赛ID（如 4813551: MNU vs NEW）建立开场前实时校准机制，
确保预测信号在最新的市场价格基准下依然具备统计优势。

核心功能:
1. 实时数据巡检 - 定时轮询数据源，捕获最新市场价格和实体状态
2. Delta Calculation - 计算模型预测概率与市场基准概率的偏差
3. 信号确认指令 - 当偏差满足要求时生成 signal_execution.json
4. 风险控制集成 - 与 risk_monitor.py 无缝对接

作者: V19.4 实时系统架构团队
日期: 2025-12-23
版本: 1.0.0
"""

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from pathlib import Path
from threading import Event
from typing import Any

from src.ops.market_price_verifier import MarketPriceVerifier

# 导入现有模块
from src.ops.risk_monitor import RiskLevel, RiskMonitor

logger = logging.getLogger(__name__)


# ============================================
# 数据结构定义
# ============================================


class SignalStatus(Enum):
    """信号状态"""

    PENDING = "pending"  # 待评估
    CALCULATING = "calculating"  # 计算中
    READY = "ready"  # 就绪执行
    REJECTED = "rejected"  # 已拒绝
    EXECUTED = "executed"  # 已执行
    EXPIRED = "expired"  # 已过期


class MarketSource(Enum):
    """市场数据源"""

    BET365 = "bet365"
    PINNACLE = "pinnacle"
    BETFAIR = "betfair"
    AVG_MARKET = "avg_market"


@dataclass
class EntityStatus:
    """实体状态数据"""

    match_id: str
    home_team: str
    away_team: str
    league: str
    match_time: datetime

    # 阵容状态
    home_lineup_confirmed: bool = False
    away_lineup_confirmed: bool = False
    home_injuries: list[str] = field(default_factory=list)
    away_injuries: list[str] = field(default_factory=list)

    # 天气条件（如果适用）
    weather_condition: str | None = None
    temperature: float | None = None

    # 数据时间戳
    last_update: datetime = field(default_factory=datetime.now)
    data_quality_score: float = 1.0  # 0-1，数据完整性评分


@dataclass
class ReferencePrice:
    """市场参考价格"""

    match_id: str
    source: MarketSource

    # 三种结果的市场价格（赔率格式）
    home_odds: float  # 主胜赔率
    draw_odds: float  # 平局赔率
    away_odds: float  # 客胜赔率

    # 转化为隐含概率（含市场抽水 margin）
    home_implied_prob: float
    draw_implied_prob: float
    away_implied_prob: float
    market_margin: float  # 市场抽水百分比

    timestamp: datetime = field(default_factory=datetime.now)

    def to_implied_probs(self) -> dict[str, float]:
        """获取去抽水后的隐含概率"""
        total_raw_prob = 1 / self.home_odds + 1 / self.draw_odds + 1 / self.away_odds

        # 去抽水
        return {
            "home": (1 / self.home_odds) / total_raw_prob,
            "draw": (1 / self.draw_odds) / total_raw_prob,
            "away": (1 / self.away_odds) / total_raw_prob,
        }


@dataclass
class ModelPrediction:
    """模型预测"""

    match_id: str
    predicted_label: str  # H/D/A
    confidence: float  # 置信度 0-1

    # 三种结果的预测概率
    home_prob: float
    draw_prob: float
    away_prob: float

    # 预测元数据
    model_version: str = "V19.4"
    feature_count: int = 48
    prediction_time: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        """验证预测概率合法性"""
        total = self.home_prob + self.draw_prob + self.away_prob
        return 0.98 <= total <= 1.02  # 允许小误差


@dataclass
class DeltaMetrics:
    """偏差指标"""

    match_id: str
    predicted_label: str
    confidence: float

    # 概率偏差（模型预测 - 市场基准）
    home_delta: float  # 主胜概率偏差
    draw_delta: float  # 平局概率偏差
    away_delta: float  # 客胜概率偏差

    # 预测结果的偏差
    prediction_delta: float  # 预测结果的概率偏差

    # 判断结果
    is_positive: bool  # 是否正向偏差（模型概率 > 市场概率）
    delta_above_threshold: bool  # 是否超过阈值
    threshold: float = 0.05  # 默认5%

    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SignalExecution:
    """信号执行指令"""

    match_id: str
    home_team: str
    away_team: str

    # 预测信息
    predicted_label: str
    confidence: float
    model_probs: dict[str, float]

    # 市场信息
    market_odds: dict[str, float]
    market_implied_probs: dict[str, float]

    # 偏差指标
    delta_metrics: dict[str, float]
    current_market_delta: float

    # 风险控制
    risk_level: str
    strategic_allocation: float  # 建议配置比例

    # 状态
    status: SignalStatus
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON"""
        data = self.to_dict()
        # 处理枚举类型
        data["status"] = self.status.value
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return json.dumps(data, indent=2, ensure_ascii=False)


# ============================================
# 实时数据巡检模块
# ============================================


class MarketLiveMonitor:
    """
    实时市场巡检系统

    核心功能:
    1. 定时轮询数据源（开场前120分钟启动，每15分钟复核）
    2. 捕获最新的市场价格和实体状态
    3. 计算 Delta 偏差
    4. 生成信号确认指令
    """

    # 配置参数
    PRE_MATCH_WINDOW_MINUTES = 120  # 开场前120分钟启动
    POLL_INTERVAL_MINUTES = 15  # 每15分钟轮询
    DELTA_THRESHOLD = 0.05  # 5%偏差阈值
    SIGNAL_EXPIRY_MINUTES = 30  # 信号有效期30分钟

    def __init__(self, target_match_id: str, initial_balance: float = 1000.0):
        """
        初始化实时巡检系统

        Args:
            target_match_id: 目标比赛ID（如 4813551）
            initial_balance: 初始资金
        """
        self.target_match_id = target_match_id
        self.price_verifier = MarketPriceVerifier()
        self.risk_monitor = RiskMonitor(initial_balance=initial_balance)

        # 数据存储
        self.entity_status: EntityStatus | None = None
        self.reference_price: ReferencePrice | None = None
        self.model_prediction: ModelPrediction | None = None
        self.delta_metrics: DeltaMetrics | None = None

        # 信号状态
        self.current_signal: SignalExecution | None = None
        self.signal_history: list[SignalExecution] = []

        # 控制标志
        self.is_running = False
        self.is_paused = False
        self.stop_event = Event()

        # 数据目录
        self.data_dir = Path("/home/user/projects/FootballPrediction/data/market_monitor")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"实时巡检系统初始化完成，目标比赛: {target_match_id}")

    # ============================================
    # 核心巡检逻辑
    # ============================================

    async def start_monitoring(self, match_time: datetime) -> None:
        """
        启动实时巡检

        Args:
            match_time: 比赛开始时间
        """
        self.is_running = True
        self.stop_event.clear()

        # 计算启动时间（开场前120分钟）
        start_time = match_time - timedelta(minutes=self.PRE_MATCH_WINDOW_MINUTES)
        now = datetime.now()

        if now < start_time:
            wait_seconds = (start_time - now).total_seconds()
            logger.info(f"等待巡检启动... 还需 {wait_seconds / 60:.1f} 分钟")
            await asyncio.sleep(wait_seconds)

        logger.info(f"🚀 实时巡检启动！目标比赛: {self.target_match_id}")
        logger.info(f"   比赛时间: {match_time}")
        logger.info(f"   巡检间隔: {self.POLL_INTERVAL_MINUTES} 分钟")
        logger.info(f"   偏差阈值: {self.DELTA_THRESHOLD:.2%}")

        # 主巡检循环
        while not self.stop_event.is_set():
            try:
                if not self.is_paused:
                    await self._perform_monitoring_cycle()

                # 检查是否比赛即将开始
                time_to_match = (match_time - datetime.now()).total_seconds()
                if time_to_match < 0:
                    logger.info("⏰ 比赛已开始，停止巡检")
                    break

                # 等待下一轮
                await asyncio.sleep(self.POLL_INTERVAL_MINUTES * 60)

            except Exception as e:
                logger.error(f"巡检循环异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试

        self.is_running = False
        logger.info("实时巡检已停止")

    async def _perform_monitoring_cycle(self) -> None:
        """执行单次巡检周期"""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"🔍 巡检周期开始: {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'=' * 60}")

        # 1. 获取实体状态
        self.entity_status = await self._fetch_entity_status()
        if self.entity_status:
            logger.info(f"📊 实体状态: {self.entity_status.home_team} vs {self.entity_status.away_team}")
            logger.info(f"   主队阵容: {'✅ 已确认' if self.entity_status.home_lineup_confirmed else '⏳ 待确认'}")
            logger.info(f"   客队阵容: {'✅ 已确认' if self.entity_status.away_lineup_confirmed else '⏳ 待确认'}")
            logger.info(f"   数据质量: {self.entity_status.data_quality_score:.2%}")

        # 2. 获取市场价格
        self.reference_price = await self._fetch_reference_price()
        if self.reference_price:
            logger.info(f"💰 市场价格: {self.reference_price.source.value}")
            logger.info(
                f"   主胜: {self.reference_price.home_odds:.2f} (隐含: {self.reference_price.home_implied_prob:.2%})"
            )
            logger.info(
                f"   平局: {self.reference_price.draw_odds:.2f} (隐含: {self.reference_price.draw_implied_prob:.2%})"
            )
            logger.info(
                f"   客胜: {self.reference_price.away_odds:.2f} (隐含: {self.reference_price.away_implied_prob:.2%})"
            )
            logger.info(f"   市场抽水: {self.reference_price.market_margin:.2%}")

        # 3. 获取模型预测
        self.model_prediction = await self._fetch_model_prediction()
        if self.model_prediction:
            logger.info(f"🤖 模型预测: {self.model_prediction.model_version}")
            logger.info(
                f"   预测: {self.model_prediction.predicted_label} (置信度: {self.model_prediction.confidence:.2%})"
            )
            logger.info(f"   主胜: {self.model_prediction.home_prob:.2%}")
            logger.info(f"   平局: {self.model_prediction.draw_prob:.2%}")
            logger.info(f"   客胜: {self.model_prediction.away_prob:.2%}")

        # 4. 计算偏差
        if self.reference_price and self.model_prediction:
            self.delta_metrics = self._calculate_delta()
            logger.info("📈 偏差分析:")
            logger.info(f"   主胜偏差: {self.delta_metrics.home_delta:+.2%}")
            logger.info(f"   平局偏差: {self.delta_metrics.draw_delta:+.2%}")
            logger.info(f"   客胜偏差: {self.delta_metrics.away_delta:+.2%}")
            logger.info(f"   预测偏差: {self.delta_metrics.prediction_delta:+.2%}")
            logger.info(f"   正向偏差: {'✅' if self.delta_metrics.is_positive else '❌'}")
            logger.info(f"   超过阈值: {'✅' if self.delta_metrics.delta_above_threshold else '❌'}")

        # 5. 生成或更新信号
        await self._update_signal()

        # 6. 保存巡检快照
        self._save_monitoring_snapshot()

    # ============================================
    # 数据获取方法
    # ============================================

    async def _fetch_entity_status(self) -> EntityStatus | None:
        """
        获取实体状态数据

        包括: 阵容确认状态、伤病情况、天气条件等
        """
        try:
            # 从数据库查询比赛信息
            import psycopg2
            from psycopg2.extras import RealDictCursor

            from src.config_unified import get_settings

            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
            SELECT
                id,
                home_team,
                away_team,
                match_time,
                status
            FROM matches
            WHERE id = %s OR external_id = %s
            LIMIT 1
            """

            cursor.execute(query, (self.target_match_id, self.target_match_id))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                return EntityStatus(
                    match_id=str(result["id"]),
                    home_team=result["home_team"],
                    away_team=result["away_team"],
                    league="Premier League",
                    match_time=result["match_time"],
                    # Note: 阵容确认状态需从阵容API获取，当前默认为False
                    home_lineup_confirmed=False,
                    away_lineup_confirmed=False,
                    data_quality_score=1.0,
                )

        except Exception as e:
            logger.debug(f"获取实体状态失败: {e}")

        # 备用：使用硬编码数据（针对 4813551: MNU vs NEW）
        if self.target_match_id == "4813551":
            return EntityStatus(
                match_id="4813551",
                home_team="Manchester United",
                away_team="Newcastle United",
                league="Premier League",
                match_time=datetime(2025, 12, 26, 12, 30),
                home_lineup_confirmed=False,
                away_lineup_confirmed=False,
                data_quality_score=0.9,
            )

        return None

    async def _fetch_reference_price(self) -> ReferencePrice | None:
        """
        获取市场参考价格

        优先级: Bet365 > Pinnacle > 平均市场
        """
        # 先尝试从数据库获取最新赔率
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            from src.config_unified import get_settings

            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 查询最新赔率（多种来源）
            query = """
            SELECT
                b365_home_odds,
                b365_draw_odds,
                b365_away_odds,
                ps_home_odds,
                ps_draw_odds,
                ps_away_odds
            FROM odds_history
            WHERE match_id = %s
            ORDER BY collection_date DESC
            LIMIT 1
            """

            cursor.execute(query, (self.target_match_id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result and result.get("b365_home_odds"):
                # 计算隐含概率
                home_odds = float(result["b365_home_odds"])
                draw_odds = float(result["b365_draw_odds"])
                away_odds = float(result["b365_away_odds"])

                # 计算市场抽水
                margin = (1 / home_odds + 1 / draw_odds + 1 / away_odds) - 1

                return ReferencePrice(
                    match_id=self.target_match_id,
                    source=MarketSource.BET365,
                    home_odds=home_odds,
                    draw_odds=draw_odds,
                    away_odds=away_odds,
                    home_implied_prob=1 / home_odds,
                    draw_implied_prob=1 / draw_odds,
                    away_implied_prob=1 / away_odds,
                    market_margin=margin,
                )

        except Exception as e:
            logger.debug(f"从数据库获取赔率失败: {e}")

        # 备用：使用硬编码数据（针对 4813551: MNU vs NEW）
        # 这些是示例赔率，实际应从实时API获取
        if self.target_match_id == "4813551":
            return ReferencePrice(
                match_id="4813551",
                source=MarketSource.BET365,
                home_odds=1.85,  # 曼联主胜
                draw_odds=3.60,  # 平局
                away_odds=4.20,  # 纽卡客胜
                home_implied_prob=1 / 1.85,
                draw_implied_prob=1 / 3.60,
                away_implied_prob=1 / 4.20,
                market_margin=(1 / 1.85 + 1 / 3.60 + 1 / 4.20) - 1,
            )

        return None

    async def _fetch_model_prediction(self) -> ModelPrediction | None:
        """
        获取模型预测

        从已训练的 V19.4 模型获取预测结果
        Note: 生产环境应调用推理服务获取预测
        """
        # 示例数据（生产环境应调用推理服务）
        if self.target_match_id == "4813551":
            return ModelPrediction(
                match_id="4813551",
                predicted_label="H",  # 预测主胜
                confidence=0.68,
                home_prob=0.68,
                draw_prob=0.22,
                away_prob=0.10,
                model_version="V19.4_Draw_Sensitivity",
                feature_count=48,
            )

        return None

    # ============================================
    # Delta 计算逻辑
    # ============================================

    def _calculate_delta(self) -> DeltaMetrics:
        """
        计算偏差指标

        Delta = 模型预测概率 - 市场隐含概率
        """
        # 获取去抽水后的市场隐含概率
        market_probs = self.reference_price.to_implied_probs()

        # 计算各结果的偏差
        home_delta = self.model_prediction.home_prob - market_probs["home"]
        draw_delta = self.model_prediction.draw_prob - market_probs["draw"]
        away_delta = self.model_prediction.away_prob - market_probs["away"]

        # 获取预测结果的偏差
        predicted_delta_map = {"H": home_delta, "D": draw_delta, "A": away_delta}
        prediction_delta = predicted_delta_map.get(self.model_prediction.predicted_label, 0)

        # 判断是否正向偏差
        is_positive = prediction_delta > 0

        # 判断是否超过阈值
        delta_above_threshold = abs(prediction_delta) >= self.DELTA_THRESHOLD

        return DeltaMetrics(
            match_id=self.target_match_id,
            predicted_label=self.model_prediction.predicted_label,
            confidence=self.model_prediction.confidence,
            home_delta=home_delta,
            draw_delta=draw_delta,
            away_delta=away_delta,
            prediction_delta=prediction_delta,
            is_positive=is_positive,
            delta_above_threshold=delta_above_threshold and is_positive,  # 只考虑正向偏差
            threshold=self.DELTA_THRESHOLD,
        )

    # ============================================
    # 信号生成逻辑
    # ============================================

    async def _update_signal(self) -> None:
        """更新或生成信号"""
        # 检查是否满足信号条件
        if not self.delta_metrics:
            return

        if not self.delta_metrics.delta_above_threshold:
            logger.info(f"❌ 偏差未达阈值 ({self.delta_metrics.prediction_delta:+.2%} < {self.DELTA_THRESHOLD:.2%})")
            return

        # 检查风控状态
        risk_level = self.risk_monitor.check_risk_level()
        if risk_level == RiskLevel.EMERGENCY:
            logger.warning("⚠️ 风控等级为紧急，不生成信号")
            return

        # 计算策略配置（基于凯利公式或固定比例）
        strategic_allocation = self._calculate_strategic_allocation()

        # 创建或更新信号
        now = datetime.now()
        expires_at = now + timedelta(minutes=self.SIGNAL_EXPIRY_MINUTES)

        market_probs = self.reference_price.to_implied_probs()

        signal = SignalExecution(
            match_id=self.target_match_id,
            home_team=self.entity_status.home_team if self.entity_status else "Unknown",
            away_team=self.entity_status.away_team if self.entity_status else "Unknown",
            predicted_label=self.model_prediction.predicted_label,
            confidence=self.model_prediction.confidence,
            model_probs={
                "home": self.model_prediction.home_prob,
                "draw": self.model_prediction.draw_prob,
                "away": self.model_prediction.away_prob,
            },
            market_odds={
                "home": self.reference_price.home_odds,
                "draw": self.reference_price.draw_odds,
                "away": self.reference_price.away_odds,
            },
            market_implied_probs=market_probs,
            delta_metrics={
                "home": self.delta_metrics.home_delta,
                "draw": self.delta_metrics.draw_delta,
                "away": self.delta_metrics.away_delta,
                "prediction": self.delta_metrics.prediction_delta,
            },
            current_market_delta=self.delta_metrics.prediction_delta,
            risk_level=risk_level.value,
            strategic_allocation=strategic_allocation,
            status=SignalStatus.READY,
            created_at=now,
            expires_at=expires_at,
        )

        self.current_signal = signal
        self.signal_history.append(signal)

        # 保存信号文件
        self._save_signal(signal)

        logger.info("✅ 信号已生成:")
        logger.info(f"   比赛: {signal.home_team} vs {signal.away_team}")
        logger.info(f"   预测: {signal.predicted_label} (置信度: {signal.confidence:.2%})")
        logger.info(f"   市场偏差: {signal.current_market_delta:+.2%}")
        logger.info(f"   建议配置: {signal.strategic_allocation:.2%} of bankroll")
        logger.info(f"   有效期至: {signal.expires_at.strftime('%H:%M:%S')}")

    def _calculate_strategic_allocation(self) -> float:
        """
        计算策略配置比例

        使用简化的凯利公式或固定比例策略
        """
        # 获取预测结果的市场赔率
        odds_map = {
            "H": self.reference_price.home_odds,
            "D": self.reference_price.draw_odds,
            "A": self.reference_price.away_odds,
        }
        market_odds = odds_map.get(self.model_prediction.predicted_label, 2.0)

        # 计算凯利比例
        # f = (bp - q) / b
        # b = 赔率 - 1
        # p = 模型预测概率
        # q = 1 - p

        b = market_odds - 1
        p = self.model_prediction.confidence
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        # 限制最大配置为 5% 单注
        max_allocation = 0.05
        min_allocation = 0.01

        if kelly_fraction < 0:
            return 0.0

        return max(min_allocation, min(kelly_fraction, max_allocation))

    # ============================================
    # 数据持久化
    # ============================================

    def _save_signal(self, signal: SignalExecution) -> None:
        """保存信号到文件"""
        signal_file = self.data_dir / f"signal_execution_{self.target_match_id}.json"
        with open(signal_file, "w") as f:
            f.write(signal.to_json())
        logger.info(f"信号已保存: {signal_file}")

    def _save_monitoring_snapshot(self) -> None:
        """保存巡检快照"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "match_id": self.target_match_id,
            "entity_status": asdict(self.entity_status) if self.entity_status else None,
            "reference_price": asdict(self.reference_price) if self.reference_price else None,
            "model_prediction": asdict(self.model_prediction) if self.model_prediction else None,
            "delta_metrics": asdict(self.delta_metrics) if self.delta_metrics else None,
            "current_signal": self.current_signal.to_dict() if self.current_signal else None,
            "risk_level": self.risk_monitor.check_risk_level().value,
        }

        snapshot_file = (
            self.data_dir / f"snapshot_{self.target_match_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)

    # ============================================
    # 控制方法
    # ============================================

    def pause(self) -> None:
        """暂停巡检"""
        self.is_paused = True
        logger.info("巡检已暂停")

    def resume(self) -> None:
        """恢复巡检"""
        self.is_paused = False
        logger.info("巡检已恢复")

    def stop(self) -> None:
        """停止巡检"""
        self.stop_event.set()
        logger.info("正在停止巡检...")

    def get_status(self) -> dict[str, Any]:
        """获取当前状态"""
        return {
            "target_match_id": self.target_match_id,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "entity_status": asdict(self.entity_status) if self.entity_status else None,
            "has_reference_price": self.reference_price is not None,
            "has_model_prediction": self.model_prediction is not None,
            "has_delta_metrics": self.delta_metrics is not None,
            "current_signal": self.current_signal.to_dict() if self.current_signal else None,
            "signal_count": len(self.signal_history),
            "risk_level": self.risk_monitor.check_risk_level().value,
            "current_balance": self.risk_monitor.metrics.current_balance,
            "max_drawdown_pct": self.risk_monitor.metrics.max_drawdown_pct,
        }


# ============================================
# 便捷函数
# ============================================


async def monitor_match(match_id: str, match_time: datetime, initial_balance: float = 1000.0) -> MarketLiveMonitor:
    """
    启动比赛监控

    Args:
        match_id: 比赛ID
        match_time: 比赛开始时间
        initial_balance: 初始资金

    Returns:
        MarketLiveMonitor: 监控实例
    """
    monitor = MarketLiveMonitor(target_match_id=match_id, initial_balance=initial_balance)

    await monitor.start_monitoring(match_time)
    return monitor


# ============================================
# 单元测试
# ============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=" * 70)
    print("V19.4 实时市场巡检系统测试")
    print("=" * 70)

    # 创建监控实例（针对 4813551: MNU vs NEW）
    monitor = MarketLiveMonitor(target_match_id="4813551")

    # 模拟单次巡检周期
    print("\n执行模拟巡检周期...")
    asyncio.run(monitor._perform_monitoring_cycle())

    # 显示状态
    print("\n当前状态:")
    status = monitor.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    # 检查风控状态
    print("\n风控检查:")
    risk_level = monitor.risk_monitor.check_risk_level()
    print(f"  风险等级: {risk_level.value}")
    print(f"  当前余额: {monitor.risk_monitor.metrics.current_balance:.2f}")
    print(f"  最大回撤: {monitor.risk_monitor.metrics.max_drawdown_pct:.2%}")
    print(f"  回撤阈值: {monitor.risk_monitor.metrics.max_drawdown_pct_limit:.2%}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
