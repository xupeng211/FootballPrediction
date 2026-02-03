#!/usr/bin/env python3
"""V113.0 Prometheus 风格指标统计模块 + DLQ 数据库持久化.

提供生产级指标统计功能：
1. 同步成功率
2. 延迟直方图
3. 供应商分歧率
4. 熔断器触发统计
5. 失败数据数据库持久化 (V113.0)

Usage:
    >>> from src.collectors.prometheus_metrics import HarvestMetrics
    >>> metrics = HarvestMetrics()
    >>> metrics.record_extraction_success(vendor="Entity_P", duration=1.23)
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

# V113.0: Optional database support
try:
    import psycopg2

    from src.config_unified import get_settings

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ============================================================================
# V106.0 Prometheus Metrics
# ============================================================================

# Extraction metrics
extraction_total = Counter(
    "market_extraction_total", "Total number of extraction attempts", ["vendor", "status"]
)

extraction_duration_seconds = Histogram(
    "market_extraction_duration_seconds",
    "Extraction duration in seconds",
    ["vendor"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

extraction_success_rate = Gauge(
    "market_extraction_success_rate", "Extraction success rate (0-100)", ["vendor"]
)

# Vendor divergence metrics
vendor_divergence = Gauge(
    "market_vendor_divergence_score",
    "Vendor divergence score (integrity difference from average)",
    ["vendor"],
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
    ["breaker_name"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total", "Total circuit breaker failures", ["breaker_name"]
)

# Database metrics
database_operations = Counter(
    "database_operations_total", "Total database operations", ["operation", "status"]
)

database_operation_duration = Histogram(
    "database_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

# Dead letter queue metrics
failed_market_data_total = Counter(
    "failed_market_data_total", "Total failed market data records", ["reason"]
)

dead_letter_queue_size = Gauge("dead_letter_queue_size", "Current size of dead letter queue")


# ============================================================================
# V106.0 Metrics Collector
# ============================================================================


@dataclass
class HarvestMetrics:
    """Prometheus 风格指标收集器.

    提供线程安全的指标记录功能。
    """

    lock: Lock = field(default_factory=Lock)
    vendor_stats: dict[str, dict[str, Any]] = field(
        default_factory=lambda: defaultdict(
            lambda: {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "durations": [],
            }
        )
    )

    def record_extraction_attempt(self, vendor: str) -> None:
        """记录提取尝试"""
        with self.lock:
            self.vendor_stats[vendor]["attempts"] += 1

    def record_extraction_success(
        self, vendor: str, duration: float, integrity_score: float | None = None
    ) -> None:
        """记录提取成功"""
        with self.lock:
            stats = self.vendor_stats[vendor]
            stats["successes"] += 1
            stats["durations"].append(duration)

        # Update Prometheus metrics
        extraction_total.labels(vendor=vendor, status="success").inc()
        extraction_duration_seconds.labels(vendor=vendor).observe(duration)

        # Update success rate
        with self.lock:
            total = stats["attempts"]
            success_rate = (stats["successes"] / total * 100) if total > 0 else 0
            extraction_success_rate.labels(vendor=vendor).set(success_rate)

        # Update divergence if integrity score available
        if integrity_score is not None:
            vendor_divergence.labels(vendor=vendor).set(abs(integrity_score - 1.05))

    def record_extraction_failure(self, vendor: str, reason: str = "unknown") -> None:
        """记录提取失败"""
        with self.lock:
            self.vendor_stats[vendor]["failures"] += 1

        # Update Prometheus metrics
        extraction_total.labels(vendor=vendor, status="failure").inc()
        failed_market_data_total.labels(reason=reason).inc()

    def record_database_operation(
        self, operation: str, duration: float, success: bool = True
    ) -> None:
        """记录数据库操作"""
        status = "success" if success else "failure"
        database_operations.labels(operation=operation, status=status).inc()
        database_operation_duration.labels(operation=operation).observe(duration)

    def record_circuit_breaker_state(
        self,
        breaker_name: str,
        state: str,  # "CLOSED", "OPEN", "HALF_OPEN"
    ) -> None:
        """记录熔断器状态"""
        state_map = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}
        circuit_breaker_state.labels(breaker_name=breaker_name).set(state_map.get(state, 0))

    def record_circuit_breaker_failure(self, breaker_name: str) -> None:
        """记录熔断器失败"""
        circuit_breaker_failures.labels(breaker_name=breaker_name).inc()

    def get_vendor_summary(self) -> dict[str, dict[str, Any]]:
        """获取供应商统计摘要"""
        with self.lock:
            summary = {}
            for vendor, stats in self.vendor_stats.items():
                total = stats["attempts"]
                success_rate = (stats["successes"] / total * 100) if total > 0 else 0
                avg_duration = (
                    sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0
                )

                summary[vendor] = {
                    "attempts": total,
                    "successes": stats["successes"],
                    "failures": stats["failures"],
                    "success_rate": round(success_rate, 2),
                    "avg_duration": round(avg_duration, 3),
                }
            return summary

    def reset(self) -> None:
        """重置所有指标"""
        with self.lock:
            self.vendor_stats.clear()


# ============================================================================
# V106.0 Dead Letter Queue Manager
# ============================================================================


@dataclass
class FailedMarketData:
    """失败的市场数据记录.

    用于死信队列思维管理失败数据。
    """

    match_id: str
    vendor: str
    failure_reason: str
    extracted_at: datetime
    retry_count: int = 0
    last_retry_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "vendor": self.vendor,
            "failure_reason": self.failure_reason,
            "extracted_at": self.extracted_at.isoformat(),
            "retry_count": self.retry_count,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "metadata": self.metadata,
        }


class DeadLetterQueue:
    """死信队列管理器 (V113.0 + 数据库持久化).

    跟踪和管理失败的提取任务，支持重试和审计。
    V113.0 新增：自动将失败记录写入 failed_market_data 表。
    """

    def __init__(self, persist_to_db: bool = True) -> None:
        """初始化死信队列

        Args:
            persist_to_db: 是否将失败记录持久化到数据库 (默认 True)
        """
        self._failed_records: list[FailedMarketData] = []
        self._metrics = HarvestMetrics()
        self._persist_to_db = persist_to_db and DB_AVAILABLE

    def add_failure(
        self, match_id: str, vendor: str, reason: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """添加失败记录"""
        record = FailedMarketData(
            match_id=match_id,
            vendor=vendor,
            failure_reason=reason,
            extracted_at=datetime.now(),
            metadata=metadata or {},
        )
        self._failed_records.append(record)

        # Update metrics
        self._metrics.record_extraction_failure(vendor, reason)
        dead_letter_queue_size.set(len(self._failed_records))

        # V113.0: Persist to database
        if self._persist_to_db:
            self._persist_to_database(record, metadata)

    def _persist_to_database(
        self, record: FailedMarketData, metadata: dict[str, Any] | None = None
    ) -> None:
        """V113.0: 将失败记录写入数据库"""
        try:
            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            cursor = conn.cursor()

            # 提取 URL 从 metadata
            url = metadata.get("url") if metadata else None

            cursor.execute(
                """
                INSERT INTO failed_market_data (
                    match_id, vendor, failure_reason, error_details, url
                ) VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    record.match_id,
                    record.vendor,
                    record.failure_reason,
                    str(metadata) if metadata else None,
                    url,
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            # 静默失败，不影响主流程
            pass

    def get_failures_by_vendor(self, vendor: str) -> list[FailedMarketData]:
        """按供应商获取失败记录"""
        return [r for r in self._failed_records if r.vendor == vendor]

    def get_failures_by_reason(self, reason: str) -> list[FailedMarketData]:
        """按原因获取失败记录"""
        return [r for r in self._failed_records if reason.lower() in r.failure_reason.lower()]

    def get_retry_candidates(self, max_retry_count: int = 3) -> list[FailedMarketData]:
        """获取可重试的记录"""
        return [r for r in self._failed_records if r.retry_count < max_retry_count]

    def mark_retry(self, record: FailedMarketData, success: bool) -> None:
        """标记重试结果"""
        record.retry_count += 1
        record.last_retry_at = datetime.now()

        if success:
            self._failed_records.remove(record)

        dead_letter_queue_size.set(len(self._failed_records))

    def get_summary(self) -> dict[str, Any]:
        """获取死信队列摘要"""
        by_vendor: dict[str, int] = defaultdict(int)
        by_reason: dict[str, int] = defaultdict(int)

        for record in self._failed_records:
            by_vendor[record.vendor] += 1
            by_reason[record.failure_reason] += 1

        return {
            "total_failed": len(self._failed_records),
            "by_vendor": dict(by_vendor),
            "by_reason": dict(by_reason),
            "retry_candidates": len(self.get_retry_candidates()),
        }


# ============================================================================
# Global instances
# ============================================================================

# 全局指标收集器
metrics = HarvestMetrics()

# 全局死信队列
dead_letter_queue = DeadLetterQueue()


# ============================================================================
# Helper functions
# ============================================================================


def record_extraction_metrics(
    vendor: str,
    success: bool,
    duration: float,
    integrity_score: float | None = None,
    failure_reason: str | None = None,
) -> None:
    """记录提取指标的辅助函数"""
    metrics.record_extraction_attempt(vendor)

    if success:
        metrics.record_extraction_success(vendor, duration, integrity_score)
    else:
        metrics.record_extraction_failure(vendor, failure_reason or "unknown")


def setup_metrics_exporter(port: int = 9090) -> None:
    """设置 Prometheus 指标导出器.

    Args:
        port: Prometheus 指标端口（默认 9090）
    """
    from prometheus_client import start_http_server

    start_http_server(port)


# ============================================================================
# Exported names
# ============================================================================

__all__ = [
    "DeadLetterQueue",
    "FailedMarketData",
    # Classes
    "HarvestMetrics",
    "circuit_breaker_failures",
    "circuit_breaker_state",
    "database_operation_duration",
    "database_operations",
    "dead_letter_queue",
    "dead_letter_queue_size",
    "extraction_duration_seconds",
    "extraction_success_rate",
    # Prometheus metrics
    "extraction_total",
    "failed_market_data_total",
    # Global instances
    "metrics",
    # Helpers
    "record_extraction_metrics",
    "setup_metrics_exporter",
    "vendor_divergence",
]
