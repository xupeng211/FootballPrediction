#!/usr/bin/env python3
"""
增强模型监控系统

功能：
1. 特征分布漂移度监控（KL散度）
2. 预测置信度分布监控
3. 模型性能指标实时监控
4. Prometheus指标导出
5. 告警和通知机制
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

import numpy as np
from prometheus_client import (CollectorRegistry, Counter, Gauge, Histogram,
                               start_http_server)
from scipy.stats import entropy, ks_2samp
from sqlalchemy import Integer, and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logging import get_logger  # noqa: E402
from src.database.connection import get_async_session  # noqa: E402
from src.database.models.features import Features  # noqa: E402
from src.database.models.match import Match  # noqa: E402
from src.database.models.predictions import Predictions  # noqa: E402

logger = get_logger(__name__)


class EnhancedModelMonitor:
    """增强模型监控器"""

    def __init__(
        self, prometheus_port: int = 8001, registry: Optional[CollectorRegistry] = None
    ):
        """
        初始化增强监控器

        Args:
            prometheus_port: Prometheus指标导出端口
            registry: Prometheus注册器（可选）
        """
        self.session: Optional[AsyncSession] = None
        self.prometheus_port = prometheus_port
        self.registry = registry or CollectorRegistry()

        # 初始化Prometheus指标
        self._init_prometheus_metrics()

        # 历史数据缓存
        self._baseline_features: Dict[str, Dict[str, np.ndarray]] = {}
        self._baseline_confidence: Dict[str, np.ndarray] = {}

        # 监控配置
        self.drift_threshold = 0.1  # KL散度阈值
        self.confidence_bins = np.arange(0, 1.1, 0.1)  # 置信度分布区间

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = get_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    def _init_prometheus_metrics(self):
        """初始化Prometheus指标"""

        # 模型准确率指标
        self.accuracy_gauge = Gauge(
            "model_accuracy",
            "Model accuracy",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        # 预测数量计数器
        self.prediction_counter = Counter(
            "model_predictions_total",
            "Total number of predictions",
            ["model_name", "model_version", "result"],
            registry=self.registry,
        )

        # 置信度分布直方图
        self.confidence_histogram = Histogram(
            "model_confidence_distribution",
            "Distribution of model confidence scores",
            ["model_name", "model_version"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry,
        )

        # 特征漂移度指标
        self.feature_drift_gauge = Gauge(
            "feature_drift_kl_divergence",
            "KL divergence for feature drift detection",
            ["model_name", "feature_name"],
            registry=self.registry,
        )

        # 整体模型漂移指标
        self.model_drift_gauge = Gauge(
            "model_drift_score",
            "Overall model drift score",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        # 预测延迟指标
        self.prediction_latency = Histogram(
            "prediction_latency_seconds",
            "Prediction processing latency",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        # 模型健康状态
        self.model_health = Gauge(
            "model_health_status",
            "Model health status (1=healthy, 0=unhealthy)",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        # 特征覆盖率
        self.feature_coverage = Gauge(
            "feature_coverage_ratio",
            "Ratio of features with valid values",
            ["model_name", "feature_name"],
            registry=self.registry,
        )

    def start_prometheus_server(self):
        """启动Prometheus指标服务器"""
        try:
            start_http_server(self.prometheus_port, registry=self.registry)
            logger.info(f"Prometheus指标服务器已启动，端口: {self.prometheus_port}")
        except Exception as e:
            logger.error(f"启动Prometheus服务器失败: {e}")
            raise

    async def collect_baseline_data(
        self, model_name: str, days_back: int = 7
    ) -> Dict[str, Any]:
        """
        收集基线数据用于漂移检测

        Args:
            model_name: 模型名称
            days_back: 回看天数

        Returns:
            Dict[str, Any]: 基线数据
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.info(f"收集模型 {model_name} 的基线数据（过去{days_back}天）")

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # 获取基线期间的预测和特征数据
        stmt = (
            select(Predictions, Features)
            .join(Features, Predictions.match_id == Features.match_id)
            .join(Match, Predictions.match_id == Match.id)
            .where(
                and_(
                    Predictions.model_name == model_name,
                    Predictions.predicted_at >= cutoff_date,
                    Predictions.predicted_at
                    <= cutoff_date + timedelta(days=days_back // 2),  # 取前半段作为基线
                )
            )
            .limit(1000)  # 限制数据量
        )

        result = await self.session.execute(stmt)
        baseline_data = result.all()

        if not baseline_data:
            logger.warning(f"未找到模型 {model_name} 的基线数据")
            return {}

        # 处理特征数据
        baseline_features: Dict[str, List[float]] = {}
        baseline_confidence: List[float] = []

        for prediction, feature in baseline_data:
            # 收集置信度数据
            max_prob = max(
                float(prediction.home_win_probability),
                float(prediction.draw_probability),
                float(prediction.away_win_probability),
            )
            baseline_confidence.append(max_prob)

            # 收集特征数据
            if hasattr(feature, "feature_data") and feature.feature_data:
                feature_dict = (
                    feature.feature_data
                    if isinstance(feature.feature_data, dict)
                    else json.loads(feature.feature_data)
                )

                for feature_name, feature_value in feature_dict.items():
                    if isinstance(feature_value, (int, float)) and not np.isnan(
                        feature_value
                    ):
                        if feature_name not in baseline_features:
                            baseline_features[feature_name] = []
                        baseline_features[feature_name].append(feature_value)

        baseline_result = {
            "model_name": model_name,
            "baseline_period": f"{cutoff_date} to {cutoff_date + timedelta(days=days_back//2)}",
            "sample_size": len(baseline_data),
            "features": {
                name: np.array(values) for name, values in baseline_features.items()
            },
            "confidence_scores": np.array(baseline_confidence),
            "collected_at": datetime.utcnow(),
        }

        # 缓存基线数据
        self._baseline_features[model_name] = cast(
            Dict[str, np.ndarray], baseline_result["features"]
        )
        self._baseline_confidence[model_name] = cast(
            np.ndarray, baseline_result["confidence_scores"]
        )

        logger.info(f"收集了 {len(baseline_data)} 条基线数据，{len(baseline_features)} 个特征")
        return baseline_result

    def calculate_kl_divergence(
        self, baseline_dist: np.ndarray, current_dist: np.ndarray, bins: int = 20
    ) -> float:
        """
        计算KL散度

        Args:
            baseline_dist: 基线分布数据
            current_dist: 当前分布数据
            bins: 直方图bins数量

        Returns:
            float: KL散度值
        """
        if len(baseline_dist) == 0 or len(current_dist) == 0:
            return float("inf")

        try:
            # 确定分布范围
            min_val = min(np.min(baseline_dist), np.min(current_dist))
            max_val = max(np.max(baseline_dist), np.max(current_dist))

            # 创建bins
            bin_edges = np.linspace(min_val, max_val, bins + 1)

            # 计算概率分布
            baseline_hist, _ = np.histogram(baseline_dist, bins=bin_edges, density=True)
            current_hist, _ = np.histogram(current_dist, bins=bin_edges, density=True)

            # 归一化
            baseline_prob = baseline_hist / (np.sum(baseline_hist) + 1e-10)
            current_prob = current_hist / (np.sum(current_hist) + 1e-10)

            # 添加平滑项避免零值
            baseline_prob += 1e-10
            current_prob += 1e-10

            # 重新归一化
            baseline_prob /= np.sum(baseline_prob)
            current_prob /= np.sum(current_prob)

            # 计算KL散度
            kl_div = entropy(current_prob, baseline_prob)

            return float(kl_div) if not np.isnan(kl_div) else float("inf")

        except Exception as e:
            logger.error(f"计算KL散度失败: {e}")
            return float("inf")

    async def detect_feature_drift(
        self, model_name: str, hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        检测特征漂移

        Args:
            model_name: 模型名称
            hours_back: 检测时间窗口（小时）

        Returns:
            Dict[str, Any]: 漂移检测结果
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.info(f"检测模型 {model_name} 过去{hours_back}小时的特征漂移")

        # 如果没有基线数据，先收集
        if model_name not in self._baseline_features:
            await self.collect_baseline_data(model_name)

        if model_name not in self._baseline_features:
            return {"error": "No baseline data available"}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        # 获取当前时间窗口的数据
        stmt = (
            select(Predictions, Features)
            .join(Features, Predictions.match_id == Features.match_id)
            .where(
                and_(
                    Predictions.model_name == model_name,
                    Predictions.predicted_at >= cutoff_time,
                )
            )
            .limit(1000)
        )

        result = await self.session.execute(stmt)
        current_data = result.all()

        if not current_data:
            return {"error": "No current data available"}

        # 提取当前特征数据
        current_features: Dict[str, List[float]] = {}
        for prediction, feature in current_data:
            if hasattr(feature, "feature_data") and feature.feature_data:
                feature_dict = (
                    feature.feature_data
                    if isinstance(feature.feature_data, dict)
                    else json.loads(feature.feature_data)
                )

                for feature_name, feature_value in feature_dict.items():
                    if isinstance(feature_value, (int, float)) and not np.isnan(
                        feature_value
                    ):
                        if feature_name not in current_features:
                            current_features[feature_name] = []
                        current_features[feature_name].append(feature_value)

        # 计算每个特征的KL散度
        drift_results = {}
        baseline_features = self._baseline_features[model_name]

        for feature_name in baseline_features.keys():
            if (
                feature_name in current_features
                and len(current_features[feature_name]) > 10
            ):
                baseline_dist = baseline_features[feature_name]
                current_dist = np.array(current_features[feature_name])

                kl_divergence = self.calculate_kl_divergence(
                    baseline_dist, current_dist
                )

                drift_results[feature_name] = {
                    "kl_divergence": kl_divergence,
                    "is_drifting": kl_divergence > self.drift_threshold,
                    "baseline_samples": len(baseline_dist),
                    "current_samples": len(current_dist),
                    "baseline_mean": float(np.mean(baseline_dist)),
                    "current_mean": float(np.mean(current_dist)),
                    "baseline_std": float(np.std(baseline_dist)),
                    "current_std": float(np.std(current_dist)),
                }

                # 更新Prometheus指标
                self.feature_drift_gauge.labels(
                    model_name=model_name, feature_name=feature_name
                ).set(kl_divergence)

                # 更新特征覆盖率
                coverage = len(current_features[feature_name]) / len(current_data)
                self.feature_coverage.labels(
                    model_name=model_name, feature_name=feature_name
                ).set(coverage)

        # 计算整体漂移分数
        if drift_results:
            drift_scores = [
                result["kl_divergence"]
                for result in drift_results.values()
                if not np.isinf(result["kl_divergence"])
            ]
            overall_drift = np.mean(drift_scores) if drift_scores else 0.0
        else:
            overall_drift = 0.0

        result_summary = {
            "model_name": model_name,
            "detection_window_hours": hours_back,
            "features_analyzed": len(drift_results),
            "features_drifting": sum(
                1 for r in drift_results.values() if r["is_drifting"]
            ),
            "overall_drift_score": overall_drift,
            "drift_threshold": self.drift_threshold,
            "feature_drift_details": drift_results,
            "detected_at": datetime.utcnow(),
        }

        # 更新整体漂移指标
        model_versions = await self._get_active_model_versions(model_name)
        for version in model_versions:
            self.model_drift_gauge.labels(
                model_name=model_name, model_version=version
            ).set(overall_drift)

        logger.info(
            f"漂移检测完成: {len(drift_results)}个特征，{result_summary['features_drifting']}个发生漂移"
        )
        return result_summary

    async def monitor_confidence_distribution(
        self, model_name: str, hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        监控预测置信度分布

        Args:
            model_name: 模型名称
            hours_back: 监控时间窗口（小时）

        Returns:
            Dict[str, Any]: 置信度分布监控结果
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.info(f"监控模型 {model_name} 过去{hours_back}小时的置信度分布")

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        # 获取当前时间窗口的预测数据
        stmt = (
            select(
                Predictions.model_version,
                Predictions.home_win_probability,
                Predictions.draw_probability,
                Predictions.away_win_probability,
                Predictions.confidence_score,
                Predictions.predicted_at,
            )
            .where(
                and_(
                    Predictions.model_name == model_name,
                    Predictions.predicted_at >= cutoff_time,
                )
            )
            .order_by(desc(Predictions.predicted_at))
        )

        result = await self.session.execute(stmt)
        predictions = result.all()

        if not predictions:
            return {"error": "No prediction data available"}

        # 计算置信度分布
        confidence_scores = []
        max_probabilities = []
        model_versions = set()

        for pred in predictions:
            model_versions.add(pred.model_version)

            # 最大概率作为置信度
            max_prob = max(
                float(pred.home_win_probability),
                float(pred.draw_probability),
                float(pred.away_win_probability),
            )
            max_probabilities.append(max_prob)

            # 如果有显式置信度分数，也使用它
            if pred.confidence_score:
                confidence_scores.append(float(pred.confidence_score))

        # 使用最大概率作为主要置信度指标
        confidence_data = np.array(max_probabilities)

        # 计算分布统计
        confidence_stats = {
            "mean": float(np.mean(confidence_data)),
            "std": float(np.std(confidence_data)),
            "median": float(np.median(confidence_data)),
            "min": float(np.min(confidence_data)),
            "max": float(np.max(confidence_data)),
            "percentiles": {
                "p25": float(np.percentile(confidence_data, 25)),
                "p75": float(np.percentile(confidence_data, 75)),
                "p90": float(np.percentile(confidence_data, 90)),
                "p95": float(np.percentile(confidence_data, 95)),
            },
        }

        # 计算分布直方图
        hist, bin_edges = np.histogram(
            confidence_data, bins=self.confidence_bins, density=True
        )
        distribution = {
            "bins": bin_edges.tolist(),
            "counts": hist.tolist(),
            "bin_centers": ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist(),
        }

        # 与基线对比（如果有基线数据）
        baseline_comparison = {}
        if model_name in self._baseline_confidence:
            baseline_data = self._baseline_confidence[model_name]

            # KL散度
            kl_div = self.calculate_kl_divergence(
                baseline_data, confidence_data, bins=len(self.confidence_bins) - 1
            )

            # Kolmogorov-Smirnov检验
            ks_stat, ks_pvalue = ks_2samp(baseline_data, confidence_data)

            baseline_comparison = {
                "kl_divergence": kl_div,
                "ks_statistic": float(ks_stat),
                "ks_pvalue": float(ks_pvalue),
                "distribution_changed": ks_pvalue < 0.05,
                "baseline_mean": float(np.mean(baseline_data)),
                "baseline_std": float(np.std(baseline_data)),
            }

        # 更新Prometheus指标
        for version in model_versions:
            # 更新置信度直方图
            for conf_score in confidence_data:
                self.confidence_histogram.labels(
                    model_name=model_name, model_version=version
                ).observe(conf_score)

        result_summary = {
            "model_name": model_name,
            "monitoring_window_hours": hours_back,
            "total_predictions": len(predictions),
            "model_versions": list(model_versions),
            "confidence_statistics": confidence_stats,
            "distribution": distribution,
            "baseline_comparison": baseline_comparison,
            "monitored_at": datetime.utcnow(),
        }

        logger.info(
            f"置信度监控完成: {len(predictions)}个预测，平均置信度 {confidence_stats['mean']:.3f}"
        )
        return result_summary

    async def update_model_health_metrics(self, model_name: str) -> Dict[str, Any]:
        """
        更新模型健康状态指标

        Args:
            model_name: 模型名称

        Returns:
            Dict[str, Any]: 健康状态结果
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.debug(f"更新模型 {model_name} 健康状态指标")

        # 获取过去24小时的性能数据
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        stmt = (
            select(
                Predictions.model_version,
                func.count().label("total_predictions"),
                func.sum(func.cast(Predictions.is_correct, Integer)).label(
                    "correct_predictions"
                ),
                func.avg(
                    func.greatest(
                        Predictions.home_win_probability,
                        Predictions.draw_probability,
                        Predictions.away_win_probability,
                    )
                ).label("avg_confidence"),
            )
            .where(
                and_(
                    Predictions.model_name == model_name,
                    Predictions.predicted_at >= cutoff_time,
                    Predictions.verified_at.isnot(None),
                )
            )
            .group_by(Predictions.model_version)
        )

        result = await self.session.execute(stmt)
        model_stats = result.all()

        health_results = {}

        for stat in model_stats:
            version = stat.model_version
            total_preds = stat.total_predictions
            correct_preds = stat.correct_predictions or 0
            avg_confidence = float(stat.avg_confidence) if stat.avg_confidence else 0.0

            accuracy = correct_preds / total_preds if total_preds > 0 else 0.0

            # 健康状态评估
            is_healthy = (
                total_preds >= 5
                and accuracy >= 0.3  # 至少有5个预测
                and avg_confidence >= 0.4  # 准确率不低于30%  # 平均置信度不低于40%
            )

            health_score = 1.0 if is_healthy else 0.0

            # 更新Prometheus指标
            self.accuracy_gauge.labels(
                model_name=model_name, model_version=version
            ).set(accuracy)

            self.model_health.labels(model_name=model_name, model_version=version).set(
                health_score
            )

            # 更新预测计数
            self.prediction_counter.labels(
                model_name=model_name, model_version=version, result="total"
            )._value._value = total_preds

            self.prediction_counter.labels(
                model_name=model_name, model_version=version, result="correct"
            )._value._value = correct_preds

            health_results[version] = {
                "total_predictions": total_preds,
                "correct_predictions": correct_preds,
                "accuracy": accuracy,
                "avg_confidence": avg_confidence,
                "is_healthy": is_healthy,
                "health_score": health_score,
            }

        return {
            "model_name": model_name,
            "health_by_version": health_results,
            "updated_at": datetime.utcnow(),
        }

    async def _get_active_model_versions(self, model_name: str) -> List[str]:
        """获取活跃的模型版本列表"""
        if not self.session:
            return []

        try:
            stmt = (
                select(Predictions.model_version)
                .where(
                    and_(
                        Predictions.model_name == model_name,
                        Predictions.predicted_at
                        >= datetime.utcnow() - timedelta(days=1),
                    )
                )
                .distinct()
            )

            result = await self.session.execute(stmt)
            versions = [row.model_version for row in result]
            return versions
        except Exception as e:
            logger.error(f"获取模型版本失败: {e}")
            return []

    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        """
        运行完整的监控周期

        Returns:
            Dict[str, Any]: 监控结果
        """
        logger.info("开始模型监控周期")

        cycle_start = datetime.utcnow()
        results: Dict[str, Any] = {
            "start_time": cycle_start,
            "models_monitored": 0,
            "drift_detections": {},
            "confidence_monitoring": {},
            "health_updates": {},
            "errors": [],
        }

        try:
            # 获取需要监控的模型
            stmt = (
                select(Predictions.model_name)
                .where(
                    Predictions.predicted_at >= datetime.utcnow() - timedelta(hours=24)
                )
                .distinct()
            )

            if self.session is None:
                raise RuntimeError("Session not initialized")

            result = await self.session.execute(stmt)
            active_models = [row.model_name for row in result]

            results["models_monitored"] = len(active_models)
            logger.info(f"找到 {len(active_models)} 个活跃模型需要监控")

            # 逐个监控模型
            for model_name in active_models:
                try:
                    logger.info(f"监控模型: {model_name}")

                    # 特征漂移检测
                    drift_result = await self.detect_feature_drift(model_name)
                    results["drift_detections"][model_name] = drift_result

                    # 置信度分布监控
                    confidence_result = await self.monitor_confidence_distribution(
                        model_name
                    )
                    results["confidence_monitoring"][model_name] = confidence_result

                    # 健康状态更新
                    health_result = await self.update_model_health_metrics(model_name)
                    results["health_updates"][model_name] = health_result

                    logger.info(f"模型 {model_name} 监控完成")

                except Exception as e:
                    error_msg = f"监控模型 {model_name} 失败: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"监控周期执行失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        results["end_time"] = datetime.utcnow()
        results["duration_seconds"] = (
            results["end_time"] - cycle_start
        ).total_seconds()

        logger.info(f"监控周期完成，用时 {results['duration_seconds']:.1f} 秒")
        return results

    async def start_continuous_monitoring(self, interval_minutes: int = 30):
        """
        启动连续监控模式

        Args:
            interval_minutes: 监控间隔（分钟）
        """
        logger.info(f"启动连续监控模式，间隔 {interval_minutes} 分钟")

        while True:
            try:
                cycle_results = await self.run_monitoring_cycle()

                # 记录监控结果
                logger.info(f"监控周期完成: 监控了 {cycle_results['models_monitored']} 个模型")

                if cycle_results["errors"]:
                    logger.warning(f"本周期发现 {len(cycle_results['errors'])} 个错误")

                # 等待下一个周期
                await asyncio.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                logger.info("接收到中断信号，停止监控")
                break
            except Exception as e:
                logger.error(f"监控周期异常: {e}")
                # 出现异常时等待较短时间后重试
                await asyncio.sleep(60)


async def main():
    """主函数示例"""
    # 启动监控器
    async with EnhancedModelMonitor(prometheus_port=8001) as monitor:
        # 启动Prometheus服务器
        monitor.start_prometheus_server()

        # 运行单次监控周期
        results = await monitor.run_monitoring_cycle()

        print("监控结果:")
        print(f"- 监控模型数: {results['models_monitored']}")
        print(f"- 漂移检测: {len(results['drift_detections'])} 个模型")
        print(f"- 置信度监控: {len(results['confidence_monitoring'])} 个模型")
        print(f"- 错误数量: {len(results['errors'])}")


if __name__ == "__main__":
    asyncio.run(main())
