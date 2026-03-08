#!/usr/bin/env python3
"""
API Monitoring Module - V4.46 激活版

导出所有 Prometheus 指标和监控组件。
"""

from __future__ import annotations

# 从 prometheus_metrics 导出所有指标
from src.api.monitoring.prometheus_metrics import (
    # 类
    DeadLetterQueue,
    FailedMarketData,
    HarvestMetrics,
    # Prometheus 原生指标
    circuit_breaker_failures,
    circuit_breaker_state,
    database_operation_duration,
    database_operations,
    dead_letter_queue,
    dead_letter_queue_size,
    extraction_duration_seconds,
    extraction_success_rate,
    extraction_total,
    failed_market_data_total,
    # 全局实例
    metrics,
    # 辅助函数
    record_extraction_metrics,
    setup_metrics_exporter,
    vendor_divergence,
)

__all__ = [
    # 类
    "HarvestMetrics",
    "DeadLetterQueue",
    "FailedMarketData",
    # Prometheus 指标
    "extraction_total",
    "extraction_duration_seconds",
    "extraction_success_rate",
    "vendor_divergence",
    "circuit_breaker_state",
    "circuit_breaker_failures",
    "database_operations",
    "database_operation_duration",
    "failed_market_data_total",
    "dead_letter_queue_size",
    # 全局实例
    "metrics",
    "dead_letter_queue",
    # 辅助函数
    "record_extraction_metrics",
    "setup_metrics_exporter",
]
