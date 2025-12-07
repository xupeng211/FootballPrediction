"""
P0-4 ML Pipeline 监控和日志模块
提供统一的监控、日志和指标收集功能
"""

from __future__ import annotations

import logging
import time
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

import pandas as pd

from .config import PipelineConfig


@dataclass
class TrainingMetrics:
    """训练指标数据结构"""

    algorithm: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_time: float
    model_size_mb: float
    sample_count: int
    feature_count: int
    timestamp: datetime
    status: str = "completed"


@dataclass
class SystemMetrics:
    """系统指标数据结构"""

    cpu_usage: float
    memory_usage_mb: float
    disk_usage_gb: float
    timestamp: datetime


class PipelineLogger:
    """Pipeline专用日志记录器"""

    def __init__(self, config: PipelineConfig):
        """初始化日志记录器"""
        self.config = config
        self.setup_logging()

    def setup_logging(self):
        """设置日志配置"""
        # 创建日志目录
        log_dir = Path(self.config.project_root) / self.config.training.log_dir
        log_dir.mkdir(exist_ok=True)

        # 配置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # 配置文件处理器
        log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format))

        # 配置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(
            logging.DEBUG if self.config.debug_mode else logging.INFO
        )
        console_handler.setFormatter(logging.Formatter(log_format))

        # 配置根日志记录器
        root_logger = logging.getLogger("pipeline")
        root_logger.setLevel(logging.DEBUG if self.config.debug_mode else logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # 防止重复添加
        root_logger.propagate = False

        self.logger = root_logger

    def log_training_start(self, algorithm: str, sample_count: int, feature_count: int):
        """记录训练开始"""
        self.logger.info(
            f"🚀 训练开始 - 算法: {algorithm}, "
            f"样本数: {sample_count}, 特征数: {feature_count}"
        )

    def log_training_complete(self, metrics: TrainingMetrics):
        """记录训练完成"""
        self.logger.info(
            f"✅ 训练完成 - 算法: {metrics.algorithm}, "
            f"准确率: {metrics.accuracy:.3f}, "
            f"训练时间: {metrics.training_time:.2f}s"
        )

    def log_model_saved(self, model_name: str, model_path: str, size_mb: float):
        """记录模型保存"""
        self.logger.info(
            f"💾 模型已保存 - 名称: {model_name}, "
            f"路径: {model_path}, 大小: {size_mb:.2f}MB"
        )

    def log_error(self, error: Exception, context: str = ""):
        """记录错误"""
        self.logger.error(f"❌ 错误发生 - {context}: {str(error)}", exc_info=True)

    def log_warning(self, message: str):
        """记录警告"""
        self.logger.warning(f"⚠️ {message}")

    def log_info(self, message: str):
        """记录信息"""
        self.logger.info(f"ℹ️ {message}")

    def log_debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(f"🔍 {message}")


class MetricsCollector:
    """指标收集器"""

    def __init__(self, config: PipelineConfig):
        """初始化指标收集器"""
        self.config = config
        self.metrics_dir = Path(config.project_root) / "artifacts" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.training_metrics: list[TrainingMetrics] = []
        self.system_metrics: list[SystemMetrics] = []

    def record_training_metrics(self, metrics: TrainingMetrics):
        """记录训练指标"""
        self.training_metrics.append(metrics)
        self._save_training_metrics()

    def record_system_metrics(self):
        """记录系统指标"""
        try:
            import psutil

            metrics = SystemMetrics(
                cpu_usage=psutil.cpu_percent(),
                memory_usage_mb=psutil.virtual_memory().used / 1024 / 1024,
                disk_usage_gb=psutil.disk_usage("/").used / 1024 / 1024 / 1024,
                timestamp=datetime.now(),
            )

            self.system_metrics.append(metrics)

            # 保持最近1000条记录
            if len(self.system_metrics) > 1000:
                self.system_metrics = self.system_metrics[-1000:]

        except ImportError:
            # psutil未安装，跳过系统指标收集
            pass

    def _save_training_metrics(self):
        """保存训练指标到文件"""
        metrics_file = self.metrics_dir / "training_metrics.json"

        # 转换为可序列化格式
        serializable_metrics = []
        for metric in self.training_metrics:
            metric_dict = asdict(metric)
            metric_dict["timestamp"] = metric.timestamp.isoformat()
            serializable_metrics.append(metric_dict)

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(serializable_metrics, f, indent=2, ensure_ascii=False)

    def get_training_summary(self) -> dict[str, Any]:
        """获取训练指标摘要"""
        if not self.training_metrics:
            return {}

        df = pd.DataFrame([asdict(m) for m in self.training_metrics])

        summary = {
            "total_trainings": len(df),
            "algorithms": df["algorithm"].unique().tolist(),
            "average_accuracy": df["accuracy"].mean(),
            "best_accuracy": df["accuracy"].max(),
            "average_training_time": df["training_time"].mean(),
            "total_training_time": df["training_time"].sum(),
            "latest_training": (
                df["timestamp"].max().isoformat() if not df.empty else None
            ),
        }

        # 按算法分组统计
        algorithm_stats = (
            df.groupby("algorithm")
            .agg({"accuracy": ["mean", "max", "count"], "training_time": "mean"})
            .round(4)
        )

        summary["algorithm_performance"] = algorithm_stats.to_dict()

        return summary

    def export_metrics_csv(self, output_path: Optional[str] = None):
        """导出指标为CSV格式"""
        if not self.training_metrics:
            return None

        if output_path is None:
            output_path = self.metrics_dir / "training_metrics.csv"

        df = pd.DataFrame([asdict(m) for m in self.training_metrics])
        df.to_csv(output_path, index=False)

        return output_path


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, config: PipelineConfig):
        """初始化性能监控器"""
        self.config = config
        self.logger = PipelineLogger(config)
        self.metrics_collector = MetricsCollector(config)

    def monitor_training(self, algorithm: str):
        """训练过程监控上下文管理器"""
        return TrainingContext(self, algorithm)

    def record_training_result(
        self,
        algorithm: str,
        result: dict[str, Any],
        training_time: float,
        sample_count: int,
        feature_count: int,
        model_size_mb: float,
    ):
        """记录训练结果"""
        metrics = TrainingMetrics(
            algorithm=algorithm,
            accuracy=result.get("accuracy", 0.0),
            precision=result.get("precision", 0.0),
            recall=result.get("recall", 0.0),
            f1_score=result.get("f1_score", 0.0),
            training_time=training_time,
            model_size_mb=model_size_mb,
            sample_count=sample_count,
            feature_count=feature_count,
            timestamp=datetime.now(),
        )

        self.metrics_collector.record_training_metrics(metrics)
        self.logger.log_training_complete(metrics)

    def get_performance_dashboard(self) -> dict[str, Any]:
        """获取性能仪表板数据"""
        summary = self.metrics_collector.get_training_summary()

        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "P0-4",
            "training_summary": summary,
            "system_health": self._get_system_health(),
        }

        return dashboard

    def _get_system_health(self) -> dict[str, str]:
        """获取系统健康状态"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent

            # 简单的健康评估
            if cpu_percent < 70 and memory_percent < 80 and disk_percent < 90:
                health_status = "healthy"
            elif cpu_percent < 90 and memory_percent < 90 and disk_percent < 95:
                health_status = "warning"
            else:
                health_status = "critical"

            return {
                "status": health_status,
                "cpu_usage": f"{cpu_percent:.1f}%",
                "memory_usage": f"{memory_percent:.1f}%",
                "disk_usage": f"{disk_percent:.1f}%",
            }

        except ImportError:
            return {
                "status": "unknown",
                "cpu_usage": "N/A",
                "memory_usage": "N/A",
                "disk_usage": "N/A",
            }


class TrainingContext:
    """训练上下文管理器"""

    def __init__(self, monitor: PerformanceMonitor, algorithm: str):
        """初始化训练上下文"""
        self.monitor = monitor
        self.algorithm = algorithm
        self.start_time = None
        self.sample_count = 0
        self.feature_count = 0

    def __enter__(self):
        """进入训练上下文"""
        self.start_time = time.time()
        self.monitor.logger.log_training_start(
            self.algorithm, self.sample_count, self.feature_count
        )

        # 记录系统指标
        self.monitor.metrics_collector.record_system_metrics()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出训练上下文"""
        training_time = time.time() - self.start_time

        if exc_type is not None:
            self.monitor.logger.log_error(exc_val, f"训练失败 - 算法: {self.algorithm}")
        else:
            self.monitor.logger.log_info(
                f"训练上下文结束 - 算法: {self.algorithm}, "
                f"耗时: {training_time:.2f}s"
            )

        # 记录系统指标
        self.monitor.metrics_collector.record_system_metrics()


# 便捷函数
def create_monitor(config: PipelineConfig) -> PerformanceMonitor:
    """创建性能监控器"""
    return PerformanceMonitor(config)


def get_logger(config: PipelineConfig) -> PipelineLogger:
    """获取Pipeline日志记录器"""
    return PipelineLogger(config)
