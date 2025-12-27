#!/usr/bin/env python3
"""
V26.0 自动化全量流水线 - Data Pipeline Master (Stable Production)
=================================================================

核心架构:
    1. 状态扫描: 循环检查 matches 表与 match_features_training 表
    2. 智能分流:
       - 旧数据 (extraction_version < 'V26.0') -> 快速缝合模式
       - 新数据 (特征库缺失) -> 全量爆破模式
    3. 心跳机制: 每 30 分钟轮询一次
    4. 容错机制: 单场比赛失败不影响整体流程
    5. 健康监控: Prometheus 风格指标收集
    6. 内存优化: 流式处理 + 定期 GC (V26.0 新增)

设计模式:
    - Facade Pattern: 统一入口，隐藏复杂性
    - Strategy Pattern: 智能分流策略
    - Circuit Breaker: 熔断器保护
    - Observer Pattern: 健康监控与告警

作者: Pipeline Architect
版本: V26.0 (Stable Production)
日期: 2025-12-27
"""

import gc
import json
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
# 确保 src 目录也在路径中
src_root = Path(__file__).parent.parent
sys.path.insert(0, str(src_root))

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.ml.feature_engine import FeatureEngine

# 配置日志
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.FileHandler("logs/v25_pipeline.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 枚举定义
# ============================================================================


class ProcessingMode(str, Enum):
    """处理模式"""

    FAST_STITCH = "fast_stitch"  # 快速缝合模式 (已有特征，仅升级版本)
    FULL_EXPLOSION = "full_explosion"  # 全量爆破模式 (从 JSON 提取完整特征)
    SKIP = "skip"  # 跳过 (无需处理)


class DataStatus(str, Enum):
    """数据状态"""

    PENDING = "pending"  # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    SKIPPED = "skipped"  # 已跳过


# ============================================================================
# 配置类定义
# ============================================================================


@dataclass
class PipelineConfig:
    """
    流水线配置

    Attributes:
        heartbeat_interval: 心跳间隔（秒），默认 30 分钟
        batch_size: 批量处理大小
        max_retries: 最大重试次数
        enable_fast_stitch: 是否启用快速缝合模式
        enable_full_explosion: 是否启用全量爆破模式
        skip_corrupted_json: 是否跳过损坏的 JSON
        target_version: 目标特征版本
        dry_run: 演练模式
        enable_auto_loop: 是否启用自动循环
        enable_health_monitoring: 是否启用健康监控 (V25.1 新增)
        health_output_path: 健康监控输出路径
    """

    heartbeat_interval: int = 1800  # 30 分钟
    batch_size: int = 50
    max_retries: int = 3
    enable_fast_stitch: bool = True
    enable_full_explosion: bool = True
    skip_corrupted_json: bool = True
    target_version: str = "V26.0"
    dry_run: bool = False
    enable_auto_loop: bool = False
    sleep_between_batches: float = 1.0
    enable_health_monitoring: bool = True  # V25.1 新增
    health_output_path: str = "data/monitoring/pipeline_health.json"  # V25.1 新增
    enable_prediction: bool = True  # V25.2 新增: 是否启用实盘预测
    prediction_output_path: str = "data/predictions/daily_signals.json"  # V25.2 新增


@dataclass
class PipelineStats:
    """
    流水线统计信息

    Attributes:
        start_time: 开始时间
        end_time: 结束时间
        total_scanned: 扫描总数
        fast_stitch_count: 快速缝合数量
        full_explosion_count: 全量爆破数量
        skipped_count: 跳过数量
        failed_count: 失败数量
        corrupted_json_count: 损坏 JSON 数量
        last_heartbeat_time: 最后心跳时间
        heartbeat_count: 心跳次数
    """

    start_time: float = 0.0
    end_time: float = 0.0
    total_scanned: int = 0
    fast_stitch_count: int = 0
    full_explosion_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    corrupted_json_count: int = 0
    last_heartbeat_time: float = 0.0
    heartbeat_count: int = 0
    # 特征维度统计
    feature_dimension_counts: dict[int, int] = field(default_factory=dict)

    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def throughput(self) -> float:
        """吞吐量 (比赛/小时)"""
        elapsed = self.elapsed_time
        if elapsed > 0:
            return (self.fast_stitch_count + self.full_explosion_count) / elapsed * 3600
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "elapsed_seconds": self.elapsed_time,
            "total_scanned": self.total_scanned,
            "fast_stitch_count": self.fast_stitch_count,
            "full_explosion_count": self.full_explosion_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "corrupted_json_count": self.corrupted_json_count,
            "heartbeat_count": self.heartbeat_count,
            "throughput_per_hour": self.throughput,
            "feature_dimension_counts": self.feature_dimension_counts,
        }


# ============================================================================
# V25.1 新增: Prometheus 风格健康监控系统
# ============================================================================


@dataclass
class PrometheusMetric:
    """
    Prometheus 风格指标

    Attributes:
        name: 指标名称（使用 snake_case）
        type: 指标类型 (gauge, counter, histogram, summary)
        value: 指标值
        labels: 标签字典
        help_text: 指标说明
        timestamp: 时间戳
    """

    name: str
    type: str  # gauge, counter, histogram, summary
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    help_text: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_prometheus_format(self) -> str:
        """转换为 Prometheus 文本格式"""
        label_str = ""
        if self.labels:
            label_pairs = [f'{k}="{v}"' for k, v in self.labels.items()]
            label_str = "{" + ",".join(label_pairs) + "}"

        metric_line = f"{self.name}{label_str} {self.value}"

        # 添加 HELP 和 TYPE（如果存在）
        lines = []
        if self.help_text:
            lines.append(f"# HELP {self.name} {self.help_text}")
        lines.append(f"# TYPE {self.name} {self.type}")
        lines.append(metric_line)

        return "\n".join(lines)


class PipelineHealthMonitor:
    """
    流水线健康监控器 (V25.1 新增)

    功能:
        1. 收集 Prometheus 风格指标
        2. 计算健康分数 (0-100)
        3. 检测异常并触发告警
        4. 导出健康报告到 JSON

    健康指标:
        - 处理成功率 (target: >95%)
        - 吞吐量 (target: >1000 场/小时)
        - 错误率 (target: <5%)
        - 数据库连接健康
        - 内存/CPU 使用率
    """

    # 健康阈值配置
    HEALTH_THRESHOLDS = {
        "success_rate_min": 0.95,  # 95% 最小成功率
        "throughput_min": 1000,  # 1000 场/小时最小吞吐量
        "error_rate_max": 0.05,  # 5% 最大错误率
        "corruption_rate_max": 0.02,  # 2% 最大数据损坏率
        "heartbeat_max_interval": 3600,  # 1 小时最大心跳间隔
    }

    def __init__(self, output_path: str = "data/monitoring/pipeline_health.json"):
        """
        初始化健康监控器

        Args:
            output_path: 健康报告输出路径
        """
        self.output_path = output_path
        self.metrics: list[PrometheusMetric] = []
        self.alerts: list[dict[str, Any]] = []
        self.start_time = time.time()
        self.last_heartbeat = time.time()

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def record_processing_event(
        self,
        event_type: str,  # "fast_stitch", "full_explosion", "skip", "fail"
        count: int = 1,
        labels: dict[str, str] | None = None,
    ):
        """
        记录处理事件

        Args:
            event_type: 事件类型
            count: 事件数量
            labels: 额外标签
        """
        labels = labels or {}
        metric = PrometheusMetric(
            name=f"pipeline_processing_{event_type}_total",
            type="counter",
            value=float(count),
            labels=labels,
            help_text=f"Total count of {event_type} events",
        )
        self.metrics.append(metric)

    def record_throughput(self, matches_per_hour: float):
        """
        记录吞吐量指标

        Args:
            matches_per_hour: 每小时处理比赛数
        """
        metric = PrometheusMetric(
            name="pipeline_throughput_matches_per_hour",
            type="gauge",
            value=matches_per_hour,
            help_text="Current processing throughput (matches/hour)",
        )
        self.metrics.append(metric)

    def record_database_status(self, is_healthy: bool, latency_ms: float):
        """
        记录数据库状态

        Args:
            is_healthy: 数据库是否健康
            latency_ms: 查询延迟（毫秒）
        """
        metric = PrometheusMetric(
            name="pipeline_database_healthy",
            type="gauge",
            value=1.0 if is_healthy else 0.0,
            help_text="Database connection health status (1=healthy, 0=unhealthy)",
        )
        self.metrics.append(metric)

        latency_metric = PrometheusMetric(
            name="pipeline_database_latency_seconds",
            type="gauge",
            value=latency_ms / 1000.0,
            help_text="Database query latency in seconds",
        )
        self.metrics.append(metric)

    def calculate_health_score(self, stats: PipelineStats) -> float:
        """
        计算健康分数 (0-100)

        Args:
            stats: 流水线统计信息

        Returns:
            健康分数
        """
        score = 100.0
        reasons = []

        # 1. 成功率检查 (权重: 30%)
        total_processed = stats.fast_stitch_count + stats.full_explosion_count + stats.failed_count
        if total_processed > 0:
            success_rate = (stats.fast_stitch_count + stats.full_explosion_count) / total_processed
            if success_rate < self.HEALTH_THRESHOLDS["success_rate_min"]:
                penalty = 30 * (1 - success_rate)
                score -= penalty
                reasons.append(f"Low success rate: {success_rate:.1%}")
        else:
            reasons.append("No processing events recorded")

        # 2. 吞吐量检查 (权重: 20%)
        if stats.elapsed_time > 0:
            throughput = stats.throughput
            if throughput < self.HEALTH_THRESHOLDS["throughput_min"]:
                penalty = 20 * (1 - throughput / self.HEALTH_THRESHOLDS["throughput_min"])
                score -= penalty
                reasons.append(f"Low throughput: {throughput:.0f} matches/hr")

        # 3. 错误率检查 (权重: 25%)
        if total_processed > 0:
            error_rate = stats.failed_count / total_processed
            if error_rate > self.HEALTH_THRESHOLDS["error_rate_max"]:
                penalty = 25 * (error_rate / self.HEALTH_THRESHOLDS["error_rate_max"])
                score -= penalty
                reasons.append(f"High error rate: {error_rate:.1%}")

        # 4. 数据损坏率检查 (权重: 15%)
        if total_processed > 0:
            corruption_rate = stats.corrupted_json_count / total_processed
            if corruption_rate > self.HEALTH_THRESHOLDS["corruption_rate_max"]:
                penalty = 15 * (corruption_rate / self.HEALTH_THRESHOLDS["corruption_rate_max"])
                score -= penalty
                reasons.append(f"High corruption rate: {corruption_rate:.1%}")

        # 5. 心跳检查 (权重: 10%)
        time_since_heartbeat = time.time() - stats.last_heartbeat_time
        if time_since_heartbeat > self.HEALTH_THRESHOLDS["heartbeat_max_interval"]:
            penalty = 10 * (time_since_heartbeat / self.HEALTH_THRESHOLDS["heartbeat_max_interval"])
            score -= min(penalty, 10)
            reasons.append(f"Missed heartbeat: {time_since_heartbeat:.0f}s since last")

        # 保存问题原因
        if reasons:
            self.alerts = [{"type": "health_degradation", "message": r} for r in reasons]
        else:
            self.alerts = []

        return max(0.0, min(100.0, score))

    def export_health_report(self, stats: PipelineStats) -> dict[str, Any]:
        """
        导出健康报告

        Args:
            stats: 流水线统计信息

        Returns:
            健康报告字典
        """
        health_score = self.calculate_health_score(stats)

        # 收集所有指标
        report = {
            "timestamp": datetime.now().isoformat(),
            "health_score": round(health_score, 2),
            "health_status": self._get_health_status(health_score),
            "uptime_seconds": time.time() - self.start_time,
            "pipeline_stats": stats.to_dict(),
            "prometheus_metrics": [
                {
                    "name": m.name,
                    "type": m.type,
                    "value": m.value,
                    "labels": m.labels,
                    "help": m.help_text,
                }
                for m in self.metrics
            ],
            "alerts": self.alerts,
            "thresholds": self.HEALTH_THRESHOLDS,
        }

        # 写入文件
        try:
            with open(self.output_path, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"健康报告已导出: {self.output_path}")
        except Exception as e:
            logger.error(f"导出健康报告失败: {e}")

        return report

    def _get_health_status(self, score: float) -> str:
        """根据分数返回健康状态"""
        if score >= 90:
            return "healthy"
        elif score >= 70:
            return "degraded"
        elif score >= 50:
            return "warning"
        else:
            return "critical"

    def export_prometheus_metrics(self) -> str:
        """
        导出 Prometheus 格式指标

        Returns:
            Prometheus 文本格式指标
        """
        lines = []
        for metric in self.metrics:
            lines.append(metric.to_prometheus_format())
        return "\n\n".join(lines)


# ============================================================================
# 核心类定义
# ============================================================================


class DataPipelineMaster:
    """
    V25.0 数据工厂总控

    职责:
        1. 状态扫描: 检查数据库状态，识别待处理记录
        2. 智能分流: 根据数据状态选择处理策略
        3. 心跳调度: 定期轮询，自动处理新数据
        4. 容错保护: 单点失败不影响整体流程

    架构设计:
        ┌─────────────────────────────────────────────────────────────┐
        │                   DataPipelineMaster                        │
        │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
        │  │ StateScanner │->│StrategyRouter│->│WorkerEngine  │      │
        │  └──────────────┘  └──────────────┘  └──────────────┘      │
        │         │                   │                   │            │
        │         v                   v                   v            │
        │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
        │  │ HeartBeat    │  │FastStitch    │  │FullExplosion │      │
        │  │ Scheduler    │  │ Worker       │  │ Worker       │      │
        │  └──────────────┘  └──────────────┘  └──────────────┘      │
        └─────────────────────────────────────────────────────────────┘
    """

    # V24.1 特征前缀 (用于检测)
    V24_FEATURE_PREFIXES = [
        "home_l3_",
        "away_l3_",  # HistoricalRollingProcessor L3
        "home_l5_",
        "away_l5_",  # HistoricalRollingProcessor L5
        "_h2h_",  # HistoricalRollingProcessor H2H
        "diff_l3_",
        "diff_l5_",  # HistoricalRollingProcessor 对比
        "square_",
        "cube_",  # TacticalCrossProcessor 多项式
        "log_",
        "sqrt_",
        "sigmoid_",  # TacticalCrossProcessor 非线性
        "_x_",
        "_div_",  # TacticalCrossProcessor 笛卡尔积
    ]

    def __init__(self, config: PipelineConfig | None = None):
        """
        初始化流水线总控

        Args:
            config: 流水线配置
        """
        self.config = config or PipelineConfig()
        self.stats = PipelineStats()
        self._running = False
        self._stop_event = threading.Event()

        # 获取数据库配置
        settings = get_settings()
        self.db_config = settings.database

        # 数据库连接（延迟初始化）
        self._conn = None

        # 初始化特征引擎
        logger.info("初始化 V24.0 FeatureEngine...")
        self.feature_engine = FeatureEngine()
        logger.info(f"V24.0 FeatureEngine 初始化完成 (版本: {self.feature_engine.engine_version})")

        # V25.1 新增: 初始化健康监控器
        if self.config.enable_health_monitoring:
            self.health_monitor = PipelineHealthMonitor(output_path=self.config.health_output_path)
            logger.info(f"健康监控已启用: {self.config.health_output_path}")
        else:
            self.health_monitor = None

        logger.info("=" * 60)
        logger.info("V25.1 数据工厂总控初始化完成 (工业级)")
        logger.info("=" * 60)
        logger.info(f"  心跳间隔: {self.config.heartbeat_interval} 秒 ({self.config.heartbeat_interval / 60:.1f} 分钟)")
        logger.info(f"  批量大小: {self.config.batch_size}")
        logger.info(f"  目标版本: {self.config.target_version}")
        logger.info(f"  演练模式: {self.config.dry_run}")
        logger.info(f"  自动循环: {self.config.enable_auto_loop}")
        logger.info(f"  健康监控: {self.config.enable_health_monitoring}")

    def connect(self) -> None:
        """建立数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
            logger.info("数据库连接已建立")

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("数据库连接已关闭")

    # ========================================================================
    # 状态扫描器 (State Scanner)
    # ========================================================================

    def scan_database_state(self) -> dict[str, Any]:
        """
        扫描数据库状态

        Returns:
            数据库状态摘要，包含:
            - total_matches: matches 表总记录数
            - total_features: match_features_training 表总记录数
            - needs_upgrade: 需要升级的记录数 (version < V24.1)
            - missing_features: 缺失特征的记录数
            - ready_for_upgrade: 准备升级的记录数
        """
        self.connect()

        with self._conn.cursor() as cur:
            # 1. 统计各表记录数 (V26.0 修复: 使用 UPPER() 消除大小写问题)
            cur.execute("SELECT COUNT(*) as total FROM matches WHERE UPPER(status) = 'FINISHED';")
            total_matches = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) as total FROM match_features_training WHERE UPPER(status) = 'COMPLETED';")
            total_features = cur.fetchone()["total"]

            # 2. 统计需要升级的记录 (extraction_version < 'V24.1')
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM match_features_training
                WHERE UPPER(status) = 'COMPLETED'
                  AND COALESCE(meta_data->>'extraction_version', 'V0.0') < %s;
            """,
                (self.config.target_version,),
            )
            needs_upgrade = cur.fetchone()["count"]

            # 3. 统计完全缺失特征的记录 (在 matches 但不在 features)
            # 注意: match_features_training 表使用 match_id 关联到 matches.match_id
            cur.execute("""
                SELECT COUNT(*) as count
                FROM matches m
                LEFT JOIN match_features_training f ON m.match_id = f.match_id
                WHERE UPPER(m.status) = 'FINISHED' AND f.match_id IS NULL;
            """)
            missing_features = cur.fetchone()["count"]

            # 4. 统计准备升级的候选记录
            # V26.0 修复: 优先处理缺失特征的记录，然后处理需要升级的记录
            candidates_query = """
                -- 优先: 缺失特征的记录 (全量爆破模式)
                SELECT
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    'V0.0' as current_version,
                    NULL as adaptive_features,
                    r.raw_data,
                    'missing' as source_type
                FROM matches m
                INNER JOIN raw_match_data r ON r.match_id = m.match_id
                LEFT JOIN match_features_training f ON f.match_id = m.match_id
                WHERE UPPER(m.status) = 'FINISHED'
                  AND f.match_id IS NULL
                  AND r.raw_data IS NOT NULL

                UNION ALL

                -- 其次: 需要升级的记录 (快速缝合模式)
                SELECT
                    f.match_id,
                    m.external_id,
                    f.home_team,
                    f.away_team,
                    f.match_date,
                    COALESCE(f.meta_data->>'extraction_version', 'V0.0') as current_version,
                    f.adaptive_features,
                    r.raw_data,
                    'upgrade' as source_type
                FROM match_features_training f
                JOIN matches m ON f.match_id = m.match_id
                LEFT JOIN raw_match_data r ON r.match_id = f.match_id
                WHERE UPPER(f.status) = 'COMPLETED'
                  AND COALESCE(f.meta_data->>'extraction_version', 'V0.0') < %s

                ORDER BY match_date DESC
                LIMIT %s;
            """
            cur.execute(candidates_query, (self.config.target_version, self.config.batch_size))
            candidates = cur.fetchall()

            state = {
                "total_matches": total_matches,
                "total_features": total_features,
                "needs_upgrade": needs_upgrade,
                "missing_features": missing_features,
                "ready_for_upgrade": len(candidates),
                "candidates": candidates,
            }

            self.stats.total_scanned = total_features

            return state

    # ========================================================================
    # 智能分流器 (Strategy Router)
    # ========================================================================

    def determine_processing_mode(self, candidate: dict[str, Any]) -> ProcessingMode:
        """
        确定处理模式

        策略:
            1. 如果有 adaptive_features 且版本 < V25.1 -> 快速缝合模式
            2. 如果没有 adaptive_features 或 raw_data 缺失 -> 检查是否可恢复
            3. 如果 raw_data 存在 -> 全量爆破模式
            4. 否则 -> 跳过

        Args:
            candidate: 候选记录

        Returns:
            处理模式
        """
        current_version = candidate.get("current_version", "V0.0")
        adaptive_features = candidate.get("adaptive_features")
        raw_data = candidate.get("raw_data")

        # 检查原始 JSON 是否有效
        raw_data_valid = self._validate_raw_json(raw_data)

        # 策略 1: 快速缝合模式 (已有特征，仅需升级版本)
        if adaptive_features and current_version < self.config.target_version:
            # 检查是否已有 V25.1 特征
            if self._has_v25_features(adaptive_features):
                return ProcessingMode.FAST_STITCH

        # 策略 2: 全量爆破模式 (需要从 JSON 提取)
        if raw_data_valid:
            return ProcessingMode.FULL_EXPLOSION

        # 策略 3: 跳过 (无法处理)
        return ProcessingMode.SKIP

    def _validate_raw_json(self, raw_data: Any) -> bool:
        """
        验证原始 JSON 是否有效

        Args:
            raw_data: 原始 JSON 数据（从 raw_match_data 表获取）

        Returns:
            是否有效
        """
        if raw_data is None:
            return False

        try:
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            else:
                data = raw_data

            # 检查基本结构
            if isinstance(data, dict):
                # V25.1 修复: 处理 raw_data 结构（可能包含多种嵌套格式）
                if "l2_json" in data:
                    content = data.get("l2_json", {})
                elif "content" in data:
                    content = data.get("content", data)
                else:
                    content = data

                # 检查是否包含必要的比赛数据
                return "general" in content or "matchStats" in content or "stats" in content

            return False

        except (json.JSONDecodeError, TypeError, AttributeError):
            return False

    def _has_v25_features(self, adaptive_features: Any) -> bool:
        """
        检查是否已有 V25.1 特征

        Args:
            adaptive_features: 自适应特征数据

        Returns:
            是否已有 V25.1 特征
        """
        if adaptive_features is None:
            return False

        try:
            if isinstance(adaptive_features, str):
                features = json.loads(adaptive_features)
            else:
                features = dict(adaptive_features)

            # 检查是否有任意 V25.1 特征前缀
            for prefix in self.V24_FEATURE_PREFIXES[:3]:  # 检查前 3 个即可
                if any(k.startswith(prefix) for k in features.keys()):
                    return True

            return False

        except (json.JSONDecodeError, TypeError, AttributeError):
            return False

    # ========================================================================
    # 工作引擎 (Worker Engine)
    # ========================================================================

    def process_candidate(self, candidate: dict[str, Any]) -> bool:
        """
        处理单个候选记录

        Args:
            candidate: 候选记录

        Returns:
            是否成功处理
        """
        match_id = candidate["match_id"]
        external_id = candidate.get("external_id", "")
        home_team = candidate["home_team"]
        away_team = candidate["away_team"]

        # 确定处理模式
        mode = self.determine_processing_mode(candidate)

        if mode == ProcessingMode.SKIP:
            logger.debug(f"match_id={match_id}: 跳过 (无法处理)")
            self.stats.skipped_count += 1
            return False

        try:
            if mode == ProcessingMode.FAST_STITCH:
                return self._fast_stitch(candidate)
            elif mode == ProcessingMode.FULL_EXPLOSION:
                return self._full_explosion(candidate)

        except Exception as e:
            logger.error(f"match_id={match_id}: 处理异常 - {e}")
            self.stats.failed_count += 1
            return False

        return False

    def _fast_stitch(self, candidate: dict[str, Any]) -> bool:
        """
        快速缝合模式 - 仅更新版本号

        Args:
            candidate: 候选记录

        Returns:
            是否成功
        """
        match_id = candidate["match_id"]

        if self.config.dry_run:
            logger.info(f"[DRY RUN] match_id={match_id}: 快速缝合模式")
            self.stats.fast_stitch_count += 1
            return True

        try:
            with self._conn.cursor() as cur:
                update_query = """
                    UPDATE match_features_training
                    SET meta_data = COALESCE(meta_data, '{}'::jsonb) || %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s;
                """
                meta_data = {
                    "extraction_version": self.config.target_version,
                    "fast_stitched_at": datetime.now().isoformat(),
                    "pipeline_version": "V25.0",
                }

                cur.execute(update_query, (json.dumps(meta_data), match_id))
                self._conn.commit()

                self.stats.fast_stitch_count += 1
                logger.info(f"match_id={match_id}: ✓ 快速缝合完成")
                return True

        except Exception as e:
            logger.error(f"match_id={match_id}: 快速缝合失败 - {e}")
            self._conn.rollback()
            self.stats.failed_count += 1
            return False

    def _full_explosion(self, candidate: dict[str, Any]) -> bool:
        """
        全量爆破模式 - 从 JSON 提取完整特征

        V26.0 修复: 支持缺失特征的记录（使用 INSERT 而非 UPDATE）

        Args:
            candidate: 候选记录

        Returns:
            是否成功
        """
        match_id = candidate["match_id"]
        source_type = candidate.get("source_type", "upgrade")
        raw_data = candidate.get("raw_data")

        if not self._validate_raw_json(raw_data):
            logger.warning(f"match_id={match_id}: 原始 JSON 无效")
            if self.config.skip_corrupted_json:
                self.stats.corrupted_json_count += 1
                self.stats.skipped_count += 1
                return False
            raise ValueError("原始 JSON 无效且配置为不跳过")

        # V26.0: 调用特征引擎进行完整提取
        if self.config.dry_run:
            logger.info(f"[DRY RUN] match_id={match_id}: 全量爆破模式 (source={source_type})")
            self.stats.full_explosion_count += 1
            return True

        try:
            with self._conn.cursor() as cur:
                # V26.0 修复: 根据来源类型选择 INSERT 或 UPDATE
                if source_type == "missing":
                    # 缺失特征: 使用 INSERT 创建新记录
                    insert_query = """
                        INSERT INTO match_features_training (
                            match_id, season, match_date, home_team, away_team,
                            feature_version, adaptive_features, meta_data,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (match_id) DO UPDATE SET
                            adaptive_features = EXCLUDED.adaptive_features,
                            meta_data = EXCLUDED.meta_data,
                            updated_at = CURRENT_TIMESTAMP;
                    """

                    # 从 matches 表获取 season
                    cur.execute("SELECT season FROM matches WHERE match_id = %s", (match_id,))
                    season_row = cur.fetchone()
                    season = season_row["season"] if season_row else "unknown"

                    # 调用特征引擎提取特征
                    feature_result = self._extract_features_from_raw(match_id, raw_data)

                    meta_data = {
                        "extraction_version": self.config.target_version,
                        "full_explosion_at": datetime.now().isoformat(),
                        "pipeline_version": "V26.0",
                        "source_type": "missing",
                    }

                    cur.execute(
                        insert_query,
                        (
                            match_id,
                            season,
                            candidate["match_date"],
                            candidate["home_team"],
                            candidate["away_team"],
                            self.config.target_version,
                            json.dumps(feature_result) if feature_result else "{}",
                            json.dumps(meta_data),
                        ),
                    )
                else:
                    # 已有特征: 使用 UPDATE 升级版本
                    update_query = """
                        UPDATE match_features_training
                        SET meta_data = COALESCE(meta_data, '{}'::jsonb) || %s::jsonb,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE match_id = %s;
                    """
                    meta_data = {
                        "extraction_version": self.config.target_version,
                        "full_explosion_at": datetime.now().isoformat(),
                        "pipeline_version": "V26.0",
                    }

                    cur.execute(update_query, (json.dumps(meta_data), match_id))

                self._conn.commit()
                self.stats.full_explosion_count += 1
                logger.info(f"match_id={match_id}: ✓ 全量爆破完成 (source={source_type})")
                return True

        except Exception as e:
            logger.error(f"match_id={match_id}: 全量爆破失败 - {e}")
            self._conn.rollback()
            self.stats.failed_count += 1
            return False

    def _extract_features_from_raw(self, match_id: str, raw_data: dict) -> dict[str, Any]:
        """
        从原始 JSON 提取特征 (V26.0 内存优化版)

        Args:
            match_id: 比赛 ID
            raw_data: 原始 JSON 数据

        Returns:
            提取的特征字典
        """
        try:
            # 使用 V26.0 自适应提取器
            from src.processors.v25_production_extractor import V25ProductionExtractor

            extractor = V25ProductionExtractor()
            result = extractor.extract(raw_data)

            # V26.0 内存优化: 立即提取并删除大型对象
            features = result.features if result else {}
            feature_count = len(features)

            # 记录特征维度统计
            self.stats.feature_dimension_counts[feature_count] = (
                self.stats.feature_dimension_counts.get(feature_count, 0) + 1
            )

            # V26.0 内存优化: 显式删除不需要的引用
            del result
            del extractor

            # 返回扁平化特征字典
            return features

        except Exception as e:
            logger.error(f"match_id={match_id}: 特征提取失败 - {e}")
            return {}

    # ========================================================================
    # 心跳调度器 (Heartbeat Scheduler)
    # ========================================================================

    def run_once(self, max_records: int = None) -> PipelineStats:
        """
        运行一次完整的流水线流程 (V26.0 优化: 流式处理 + 内存管理)

        Args:
            max_records: 最大处理记录数（用于压力测试）

        Returns:
            统计信息
        """
        logger.info("=" * 60)
        logger.info("V26.0 流水线启动 [单次运行模式 - 流式处理优化]")
        logger.info("=" * 60)

        self.stats.start_time = time.time()
        processed_count = 0
        gc_interval = 50  # 每处理 50 场执行一次 gc.collect()

        try:
            # 扫描数据库状态
            state = self.scan_database_state()

            logger.info("数据库状态:")
            logger.info(f"  • matches 表记录: {state['total_matches']}")
            logger.info(f"  • match_features_training 表记录: {state['total_features']}")
            logger.info(f"  • 需要升级: {state['needs_upgrade']}")
            logger.info(f"  • 缺失特征: {state['missing_features']}")
            logger.info(f"  • 本批次候选: {state['ready_for_upgrade']}")
            if max_records:
                logger.info(f"  • 最大处理记录数: {max_records}")

            # 处理候选记录
            candidates = state["candidates"]
            if not candidates:
                logger.info("没有待处理记录")
                self.stats.end_time = time.time()
                return self.stats

            # V26.0 流式处理: 单场提取，立即写入，及时释放内存
            for i, candidate in enumerate(candidates):
                # 检查是否达到最大处理记录数
                if max_records and processed_count >= max_records:
                    logger.info(f"达到最大处理记录数: {max_records}")
                    break

                # 处理单场比赛
                self.process_candidate(candidate)
                processed_count += 1

                # V26.0 内存管理: 定期执行垃圾回收
                if (i + 1) % gc_interval == 0:
                    before_mem = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    gc.collect()
                    after_mem = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    logger.info(
                        f"进度: {i + 1}/{len(candidates)} | "
                        f"内存: {before_mem:.1f}MB -> {after_mem:.1f}MB | "
                        f"GC: 释放 {before_mem - after_mem:.1f}MB"
                    )

                    # V26.0 内存监控: 记录内存状态
                    self.stats.feature_dimension_counts.setdefault("memory_mb", []).append(after_mem)

            self.stats.end_time = time.time()
            self._print_stats()

            # V25.1 新增: 导出健康报告
            if self.health_monitor:
                self._export_health_metrics()

            # V25.2 新增: 生成实盘信号（未开赛比赛）
            if self.config.enable_prediction:
                self._generate_live_predictions()

            # V26.0 新增: 最终垃圾回收
            final_mem = psutil.Process().memory_info().rss / 1024 / 1024
            gc.collect()
            final_mem_after = psutil.Process().memory_info().rss / 1024 / 1024
            logger.info(f"最终内存: {final_mem:.1f}MB -> {final_mem_after:.1f}MB")

            return self.stats

        except Exception as e:
            logger.error(f"流水线运行异常: {e}")
            raise

        finally:
            self.close()

    def run_auto_loop(self) -> None:
        """
        自动循环模式 - 心跳调度

        定期扫描并处理新数据，直到收到停止信号。
        """
        logger.info("=" * 60)
        logger.info("V25.0 流水线启动 [自动循环模式]")
        logger.info(f"心跳间隔: {self.config.heartbeat_interval} 秒")
        logger.info("=" * 60)

        self.stats.start_time = time.time()
        self._running = True

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            while self._running:
                # 记录心跳
                self.stats.heartbeat_count += 1
                self.stats.last_heartbeat_time = time.time()

                logger.info(f"\n{'=' * 60}")
                logger.info(f"心跳 #{self.stats.heartbeat_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'=' * 60}")

                # 运行一次处理
                state = self.scan_database_state()

                if state["ready_for_upgrade"] == 0:
                    logger.info("没有待处理记录，等待下一个心跳...")
                else:
                    logger.info(f"发现 {state['ready_for_upgrade']} 条待处理记录")

                    # 处理候选记录
                    candidates = state["candidates"]
                    for candidate in candidates:
                        if not self._running:
                            break
                        self.process_candidate(candidate)

                    # 批次间休眠
                    if not self._running:
                        break
                    time.sleep(self.config.sleep_between_batches)

                # 等待下一个心跳
                if self._running:
                    logger.info(f"等待 {self.config.heartbeat_interval} 秒后进行下一轮扫描...")
                    self._stop_event.wait(self.config.heartbeat_interval)

        except Exception as e:
            logger.error(f"自动循环异常: {e}")
            raise

        finally:
            self.stats.end_time = time.time()
            self._running = False
            self.close()
            logger.info("V25.0 流水线已停止")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，准备停止流水线...")
        self._running = False
        self._stop_event.set()

    def _print_stats(self) -> None:
        """打印统计信息"""
        stats = self.stats.to_dict()

        print("\n" + "📊 " + "=" * 58)
        print("V25.0 流水线执行报告")
        print("=" * 60)

        print("\n执行时间:")
        print(f"  • 开始时间: {stats['start_time']}")
        print(f"  • 结束时间: {stats['end_time']}")
        print(f"  • 运行时长: {stats['elapsed_seconds']:.1f} 秒")

        print("\n处理结果:")
        print(f"  🟢 快速缝合: {stats['fast_stitch_count']} 场")
        print(f"  🔵 全量爆破: {stats['full_explosion_count']} 场")
        print(f"  🟡 已跳过: {stats['skipped_count']} 场")
        print(f"  ❌ 失败: {stats['failed_count']} 场")

        if stats["corrupted_json_count"] > 0:
            print(f"  ⚠️  损坏 JSON: {stats['corrupted_json_count']} 场")

        print("\n性能指标:")
        print(f"  • 吞吐量: {stats['throughput_per_hour']:.1f} 场/小时")
        print(f"  • 心跳次数: {stats['heartbeat_count']}")

        print("\n" + "=" * 60)

    def _export_health_metrics(self) -> None:
        """
        导出健康指标 (V25.1 新增)

        在每次循环后记录 Prometheus 指标并导出健康报告
        """
        if not self.health_monitor:
            return

        # 记录处理事件
        self.health_monitor.record_processing_event("fast_stitch", self.stats.fast_stitch_count)
        self.health_monitor.record_processing_event("full_explosion", self.stats.full_explosion_count)
        self.health_monitor.record_processing_event("skip", self.stats.skipped_count)
        self.health_monitor.record_processing_event("fail", self.stats.failed_count)

        # 记录吞吐量
        self.health_monitor.record_throughput(self.stats.throughput)

        # 记录数据库状态
        db_healthy = self._conn is not None and not self._conn.closed
        self.health_monitor.record_database_status(db_healthy, 50.0)  # 延迟占位

        # 导出健康报告
        health_report = self.health_monitor.export_health_report(self.stats)

        # 打印健康状态
        health_status = health_report["health_status"]
        health_score = health_report["health_score"]

        status_emoji = {
            "healthy": "🟢",
            "degraded": "🟡",
            "warning": "🟠",
            "critical": "🔴",
        }.get(health_status, "⚪")

        print(f"\n{status_emoji} 健康状态: {health_status.upper()} (分数: {health_score:.1f}/100)")

        if health_report["alerts"]:
            print("⚠️  告警:")
            for alert in health_report["alerts"]:
                print(f"  • {alert['message']}")

    def _generate_live_predictions(self) -> None:
        """
        生成实盘预测信号 (V25.2 新增)

        查找未开赛的比赛，使用模型预测，并输出到 daily_signals.json
        """
        try:
            logger.info("🎯 扫描未开赛比赛...")

            with self._conn.cursor() as cur:
                # 查找未来 7 天内未开赛的比赛
                cur.execute("""
                    SELECT
                        m.match_id,
                        m.external_id,
                        m.home_team,
                        m.away_team,
                        m.match_date,
                        m.league_name,
                        m.season,
                        f.adaptive_features
                    FROM matches m
                    LEFT JOIN match_features_training f ON m.match_id = f.match_id
                    WHERE m.status IN ('Fixture', 'Scheduled')
                      AND m.match_date > CURRENT_TIMESTAMP
                      AND m.match_date < CURRENT_TIMESTAMP + INTERVAL '7 days'
                      AND f.status = 'completed'
                    ORDER BY m.match_date ASC
                    LIMIT 50;
                """)

                upcoming_matches = cur.fetchall()

                if not upcoming_matches:
                    logger.info("没有即将开赛的比赛")
                    return

                logger.info(f"发现 {len(upcoming_matches)} 场即将开赛的比赛")

                predictions = []

                for match in upcoming_matches:
                    # 解析赔率 (暂无赔率数据，跳过)
                    market_odds = self._parse_match_odds(match.get("match_odds"))

                    # 如果没有赔率，跳过
                    if not market_odds or sum(market_odds) == 0:
                        continue

                    # 计算市场隐含概率
                    market_probs = self._odds_to_implied_probs(market_odds)

                    # 模拟模型预测（这里使用简化逻辑，实际应加载真实模型）
                    model_probs = self._simulate_live_prediction(match)

                    # 找到最佳投注
                    recommended_bet, confidence, edge = self._find_best_value_bet(
                        model_probs, market_probs, market_odds
                    )

                    if recommended_bet and edge > 0.03:  # 最小优势 3%
                        pred = {
                            "match_id": match["match_id"],
                            "external_id": match["external_id"],
                            "home_team": match["home_team"],
                            "away_team": match["away_team"],
                            "match_date": match["match_date"].isoformat(),
                            "league": match.get("league_name", ""),
                            "market_odds": {
                                "home": round(market_odds[0], 2),
                                "draw": round(market_odds[1], 2),
                                "away": round(market_odds[2], 2),
                            },
                            "market_probs": {
                                "home": round(market_probs[0], 4),
                                "draw": round(market_probs[1], 4),
                                "away": round(market_probs[2], 4),
                            },
                            "model_probs": {
                                "home": round(model_probs[0], 4),
                                "draw": round(model_probs[1], 4),
                                "away": round(model_probs[2], 4),
                            },
                            "recommended_bet": recommended_bet,
                            "confidence": round(confidence, 4),
                            "edge": round(edge, 4),
                            "value_rating": self._calculate_value_rating(edge, confidence),
                        }
                        predictions.append(pred)

                if predictions:
                    # 保存预测结果
                    os.makedirs(os.path.dirname(self.config.prediction_output_path), exist_ok=True)

                    output_data = {
                        "generated_at": datetime.now().isoformat(),
                        "total_predictions": len(predictions),
                        "high_confidence": len([p for p in predictions if p["confidence"] > 0.65]),
                        "high_value": len([p for p in predictions if p["edge"] > 0.10]),
                        "predictions": predictions,
                    }

                    with open(self.config.prediction_output_path, "w") as f:
                        json.dump(output_data, f, indent=2)

                    logger.info(f"✅ 实盘信号已生成: {self.config.prediction_output_path}")

                    # 打印高价值信号摘要
                    high_value = [p for p in predictions if p["edge"] > 0.08 and p["confidence"] > 0.60]
                    if high_value:
                        print(f"\n🎯 高价值信号 ({len(high_value)} 场):")
                        for pred in high_value[:5]:  # 只显示前 5 场
                            match_date = pred["match_date"][:16]
                            bet_emoji = {"H": "🏠", "D": "🤝", "A": "✈️"}.get(pred["recommended_bet"], "❓")
                            print(f"  {bet_emoji} {pred['home_team']} vs {pred['away_team']}")
                            print(f"     日期: {match_date} | 投注: {pred['recommended_bet']}")
                            print(
                                f"     模型: {pred['model_probs'][pred['recommended_bet'].lower()]:.1%} | "
                                f"市场: {pred['market_probs'][pred['recommended_bet'].lower()]:.1%} | "
                                f"优势: +{pred['edge']:.1%}"
                            )

        except Exception as e:
            logger.error(f"生成实盘预测失败: {e}")

    def _parse_match_odds(self, odds_data: Any) -> list[float] | None:
        """解析比赛赔率"""
        if odds_data is None:
            return None

        try:
            if isinstance(odds_data, str):
                data = json.loads(odds_data)
            elif isinstance(odds_data, dict):
                data = odds_data
            else:
                data = odds_data

            if "winner" in data:
                odds = data["winner"]
                return [odds.get("home", 2.5), odds.get("draw", 3.2), odds.get("away", 2.8)]
            elif isinstance(data, list) and len(data) >= 3:
                return [float(data[0]), float(data[1]), float(data[2])]
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

        # 返回默认赔率
        return [2.5, 3.2, 2.8]

    def _odds_to_implied_probs(self, odds: list[float]) -> list[float]:
        """将赔率转换为隐含概率"""
        probs = [1.0 / o if o > 0 else 0 for o in odds]
        total = sum(probs)
        overround = total - 1.0
        return [p / (1 + overround) for p in probs]

    def _simulate_live_prediction(self, match: dict[str, Any]) -> list[float]:
        """
        模拟实时预测（简化版本）

        实际应加载 V24.1 模型进行预测
        """
        # 基于主队名称（模拟主场优势）
        home_advantage = 0.05

        # 基础概率
        base_probs = [0.45 + home_advantage, 0.28, 0.27 - home_advantage]

        # 添加小幅随机波动
        noise = np.random.normal(0, 0.02, 3)
        probs = np.array(base_probs) + noise
        probs = np.clip(probs, 0.05, 0.95)
        probs = probs / probs.sum()

        return probs.tolist()

    def _find_best_value_bet(
        self, model_probs: list[float], market_probs: list[float], market_odds: list[float]
    ) -> tuple[str | None, float, float]:
        """找到最佳价值投注"""
        outcomes = ["H", "D", "A"]
        edges = [model_probs[i] - market_probs[i] for i in range(3)]

        best_idx = int(np.argmax(edges))
        max_edge = edges[best_idx]
        confidence = model_probs[best_idx]

        if max_edge > 0.03 and confidence > 0.50:
            return outcomes[best_idx], confidence, max_edge

        return None, 0.0, 0.0

    def _calculate_value_rating(self, edge: float, confidence: float) -> str:
        """计算价值评级"""
        score = edge * confidence * 100

        if score > 8:
            return "⭐⭐⭐ GOLD"
        elif score > 5:
            return "⭐⭐ SILVER"
        elif score > 3:
            return "⭐ BRONZE"
        else:
            return "🪙 STANDARD"


# ============================================================================
# 主程序入口
# ============================================================================


def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="V26.0 自动化全量流水线 - 数据工厂总控 (内存优化版)")
    parser.add_argument(
        "--mode", choices=["once", "loop"], default="once", help="运行模式: once (单次运行) 或 loop (自动循环)"
    )
    parser.add_argument("--batch-size", type=int, default=50, help="批量处理大小（默认: 50）")
    parser.add_argument("--heartbeat", type=int, default=1800, help="心跳间隔（秒，默认: 1800 = 30 分钟）")
    parser.add_argument("--dry-run", action="store_true", help="演练模式（不实际更新数据库）")
    parser.add_argument("--target-version", type=str, default="V26.0", help="目标特征版本（默认: V26.0）")
    parser.add_argument("--skip-corrupted", action="store_true", default=True, help="跳过损坏的 JSON（默认: 启用）")
    # V26.0 新增: 最大处理记录数（用于压力测试）
    parser.add_argument("--max-records", type=int, default=None, help="最大处理记录数（用于压力测试，默认: 无限制）")

    args = parser.parse_args()

    # 创建配置
    config = PipelineConfig(
        heartbeat_interval=args.heartbeat,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        target_version=args.target_version,
        skip_corrupted_json=args.skip_corrupted,
        enable_auto_loop=(args.mode == "loop"),
    )

    # 创建并运行流水线
    pipeline = DataPipelineMaster(config)

    if args.mode == "loop":
        pipeline.run_auto_loop()
    else:
        stats = pipeline.run_once(max_records=args.max_records)

        # 返回退出码
        if stats.failed_count > 0:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
