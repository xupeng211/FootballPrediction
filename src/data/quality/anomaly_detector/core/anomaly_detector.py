"""
高级异常检测器

整合统计学和机器学习方法的高级异常检测器。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import text

from src.database.connection import DatabaseManager

from ..machine_learning.ml_detector import MachineLearningAnomalyDetector
from ..metrics.prometheus_metrics import (
    anomaly_detection_coverage,
    anomaly_detection_duration_seconds,
)
from ..statistical.statistical_detector import StatisticalAnomalyDetector
from .result import AnomalyDetectionResult


class AdvancedAnomalyDetector:
    """高级异常检测器 - 整合统计学和机器学习方法"""

    def __init__(self):
        """初始化高级异常检测器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 初始化子检测器
        self.statistical_detector = StatisticalAnomalyDetector()
        self.ml_detector = MachineLearningAnomalyDetector()

        # 检测配置
        self.detection_config = {
            "matches": {
                "enabled_methods": ["3sigma", "iqr", "isolation_forest", "data_drift"],
                "key_columns": ["home_score", "away_score", "match_time"],
                "drift_baseline_days": 30,
            },
            "odds": {
                "enabled_methods": [
                    "3sigma",
                    "iqr",
                    "isolation_forest",
                    "distribution_shift",
                ],
                "key_columns": ["home_odds", "draw_odds", "away_odds"],
                "drift_baseline_days": 7,
            },
            "predictions": {
                "enabled_methods": ["3sigma", "clustering", "data_drift"],
                "key_columns": [
                    "home_win_probability",
                    "draw_probability",
                    "away_win_probability",
                ],
                "drift_baseline_days": 14,
            },
        }

    async def run_comprehensive_detection(
        self, table_name: str, time_window_hours: int = 24
    ) -> List[AnomalyDetectionResult]:
        """
        运行综合异常检测

        Args:
            table_name: 表名
            time_window_hours: 检测时间窗口（小时）

        Returns:
            List[AnomalyDetectionResult]: 异常检测结果列表
        """
        start_time = datetime.now()
        results: List = []

        try:
            self.logger.info(f"开始对表 {table_name} 进行综合异常检测")

            # 获取表配置
            if table_name not in self.detection_config:
                self.logger.warning(f"表 {table_name} 没有配置异常检测规则")
                return results

            config = self.detection_config[table_name]

            # 获取数据
            current_data = await self._get_table_data(table_name, time_window_hours)
            if current_data.empty:
                self.logger.warning(f"表 {table_name} 没有数据")
                return results

            # 更新覆盖率指标
            total_records = await self._get_total_records(table_name)
            coverage = len(current_data) / max(total_records, 1)
            anomaly_detection_coverage.labels(table_name=table_name).set(coverage)

            # 执行各种检测方法
            for method in config["enabled_methods"]:
                try:
                    if method == "3sigma":
                        results.extend(
                            await self._run_3sigma_detection(
                                table_name, current_data, config
                            )
                        )

                    elif method == "iqr":
                        results.extend(
                            await self._run_iqr_detection(
                                table_name, current_data, config
                            )
                        )

                    elif method == "isolation_forest":
                        if len(current_data) >= 10:  # 需要足够的数据
                            result = self.ml_detector.detect_anomalies_isolation_forest(
                                current_data, table_name
                            )
                            results.append(result)

                    elif method == "clustering":
                        if len(current_data) >= 20:  # 需要更多数据进行聚类
                            result = self.ml_detector.detect_anomalies_clustering(
                                current_data, table_name
                            )
                            results.append(result)

                    elif method == "data_drift":
                        drift_results = await self._run_data_drift_detection(
                            table_name, current_data, config
                        )
                        results.extend(drift_results)

                    elif method == "distribution_shift":
                        shift_results = await self._run_distribution_shift_detection(
                            table_name, current_data, config
                        )
                        results.extend(shift_results)

                except Exception as method_error:
                    self.logger.error(f"检测方法 {method} 执行失败: {method_error}")
                    continue

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="comprehensive"
            ).observe(duration)

            self.logger.info(
                f"表 {table_name} 综合异常检测完成, "
                f"执行了 {len(config['enabled_methods'])} 种方法, "
                f"发现 {len(results)} 个异常结果, "
                f"耗时 {duration:.2f} 秒"
            )

            return results

        except Exception as e:
            self.logger.error(f"综合异常检测失败: {e}")
            raise

    async def _get_table_data(
        self, table_name: str, time_window_hours: int
    ) -> pd.DataFrame:
        """获取表数据"""
        try:
            # 检查数据库管理器是否已初始化
            if not self.db_manager or not hasattr(self.db_manager, "get_async_session"):
                self.logger.error("数据库连接未初始化，请先调用 initialize()")
                return pd.DataFrame()

            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

            async with self.db_manager.get_async_session() as session:
                if table_name == "matches":
                    query = text(
                        """
                        SELECT home_score, away_score, home_ht_score, away_ht_score,
                               minute, match_time, created_at, updated_at
                        FROM matches
                        WHERE updated_at >= :cutoff_time
                        ORDER BY updated_at DESC
                        LIMIT 1000
                    """
                    )
                elif table_name == "odds":
                    query = text(
                        """
                        SELECT home_odds, draw_odds, away_odds, over_odds, under_odds,
                               collected_at, created_at
                        FROM odds
                        WHERE collected_at >= :cutoff_time
                        ORDER BY collected_at DESC
                        LIMIT 1000
                    """
                    )
                elif table_name == "predictions":
                    query = text(
                        """
                        SELECT home_win_probability, draw_probability, away_win_probability,
                               confidence_score, created_at
                        FROM predictions
                        WHERE created_at >= :cutoff_time
                        ORDER BY created_at DESC
                        LIMIT 1000
                    """
                    )
                else:
                    return pd.DataFrame()

                result = await session.execute(query, {"cutoff_time": cutoff_time})
                rows = result.fetchall()

                if rows:
                    columns = result.keys()
                    return pd.DataFrame(rows, columns=columns)
                else:
                    return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取表 {table_name} 数据失败: {e}")
            return pd.DataFrame()

    async def _get_total_records(self, table_name: str) -> int:
        """获取表总记录数"""
        try:
            # 检查数据库管理器是否已初始化
            if not self.db_manager or not hasattr(self.db_manager, "get_async_session"):
                self.logger.error("数据库连接未初始化，请先调用 initialize()")
                return 0

            async with self.db_manager.get_async_session() as session:
                # Use whitelist validation to prevent SQL injection
                allowed_tables = ["matches", "odds", "predictions"]
                if table_name not in allowed_tables:
                    return 0

                # Use table mapping for safe query construction
                table_queries = {
                    "matches": text("SELECT COUNT(*) FROM matches"),
                    "odds": text("SELECT COUNT(*) FROM odds"),
                    "predictions": text("SELECT COUNT(*) FROM predictions"),
                }

                query = table_queries[table_name]
                result = await session.execute(query)
                count = result.scalar()
                return int(count) if count is not None else 0
        except Exception as e:
            self.logger.error(f"获取表 {table_name} 记录数失败: {e}")
            return 0

    async def _run_3sigma_detection(
        self, table_name: str, data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行3σ检测"""
        results: List = []
        for column in config["key_columns"]:
            if column in data.columns and data[column].dtype in ["int64", "float64"]:
                try:
                    result = self.statistical_detector.detect_outliers_3sigma(
                        data[column].dropna(), table_name, column
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"列 {column} 的3σ检测失败: {e}")
        return results

    async def _run_iqr_detection(
        self, table_name: str, data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行IQR检测"""
        results: List = []
        for column in config["key_columns"]:
            if column in data.columns and data[column].dtype in ["int64", "float64"]:
                try:
                    result = self.statistical_detector.detect_outliers_iqr(
                        data[column].dropna(), table_name, column
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"列 {column} 的IQR检测失败: {e}")
        return results

    async def _run_data_drift_detection(
        self, table_name: str, current_data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行数据漂移检测"""
        try:
            # 获取基准数据
            baseline_days = config.get(str("drift_baseline_days"), 30)
            baseline_data = await self._get_baseline_data(table_name, baseline_days)

            if baseline_data.empty:
                self.logger.warning(f"表 {table_name} 没有足够的基准数据进行漂移检测")
                return []

            return self.ml_detector.detect_data_drift(
                baseline_data, current_data, table_name
            )

        except Exception as e:
            self.logger.error(f"数据漂移检测失败: {e}")
            return []

    async def _run_distribution_shift_detection(
        self, table_name: str, current_data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行分布偏移检测"""
        results: List = []
        try:
            # 获取基准数据
            baseline_days = config.get(str("drift_baseline_days"), 30)
            baseline_data = await self._get_baseline_data(table_name, baseline_days)

            if baseline_data.empty:
                return results

            for column in config["key_columns"]:
                if column in current_data.columns and column in baseline_data.columns:
                    if current_data[column].dtype in [
                        "int64",
                        "float64",
                    ] and baseline_data[column].dtype in ["int64", "float64"]:
                        try:
                            result = (
                                self.statistical_detector.detect_distribution_shift(
                                    baseline_data[column].dropna(),
                                    current_data[column].dropna(),
                                    table_name,
                                    column,
                                )
                            )
                            results.append(result)
                        except Exception as e:
                            self.logger.warning(f"列 {column} 的分布偏移检测失败: {e}")

            return results

        except Exception as e:
            self.logger.error(f"分布偏移检测失败: {e}")
            return []

    async def _get_baseline_data(
        self, table_name: str, baseline_days: int
    ) -> pd.DataFrame:
        """获取基准数据"""
        try:
            start_time = datetime.now() - timedelta(days=baseline_days + 7)
            end_time = datetime.now() - timedelta(days=7)

            async with self.db_manager.get_async_session() as session:
                if table_name == "matches":
                    query = """
                        SELECT home_score, away_score, home_ht_score, away_ht_score,
                               minute, match_time
                        FROM matches
                        WHERE updated_at BETWEEN %s AND %s
                        ORDER BY updated_at
                        LIMIT 2000
                    """
                elif table_name == "odds":
                    query = """
                        SELECT home_odds, draw_odds, away_odds, over_odds, under_odds
                        FROM odds
                        WHERE collected_at BETWEEN %s AND %s
                        ORDER BY collected_at
                        LIMIT 2000
                    """
                elif table_name == "predictions":
                    query = """
                        SELECT home_win_probability, draw_probability, away_win_probability,
                               confidence_score
                        FROM predictions
                        WHERE created_at BETWEEN %s AND %s
                        ORDER BY created_at
                        LIMIT 2000
                    """
                else:
                    return pd.DataFrame()

                result = await session.execute(query, (start_time, end_time))
                rows = result.fetchall()

                if rows:
                    columns = result.keys()
                    return pd.DataFrame(rows, columns=columns)
                else:
                    return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取基准数据失败: {e}")
            return pd.DataFrame()

    async def get_anomaly_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取异常检测摘要

        Args:
            hours: 时间窗口（小时）

        Returns:
            Dict[str, Any]: 异常检测摘要
        """
        try:
            # 运行各表的异常检测
            all_results = {}
            for table_name in self.detection_config.keys():
                results = await self.run_comprehensive_detection(table_name, hours)
                all_results[table_name] = results

            # 生成摘要
            summary = {
                "detection_period": {
                    "hours": hours,
                    "start_time": (datetime.now() - timedelta(hours=hours)).isoformat(),
                    "end_time": datetime.now().isoformat(),
                },
                "tables_analyzed": list(self.detection_config.keys()),
                "total_anomalies": sum(
                    len(results) for results in all_results.values()
                ),
                "anomalies_by_table": {},
                "anomalies_by_severity": {
                    "low": 0,
                    "medium": 0,
                    "high": 0,
                    "critical": 0,
                },
                "anomalies_by_method": {},
                "anomalies_by_type": {},
            }

            # 统计各表异常
            for table_name, results in all_results.items():
                table_summary = {
                    "total_anomalies": len(results),
                    "methods_used": list(set(r.detection_method for r in results)),
                    "severity_breakdown": {
                        "low": 0,
                        "medium": 0,
                        "high": 0,
                        "critical": 0,
                    },
                    "anomaly_types": list(set(r.anomaly_type for r in results)),
                }

                for result in results:
                    # 按严重程度统计
                    severity = result.severity
                    table_summary["severity_breakdown"][severity] += 1
                    summary["anomalies_by_severity"][severity] += 1

                    # 按方法统计
                    method = result.detection_method
                    if method not in summary["anomalies_by_method"]:
                        summary["anomalies_by_method"][method] = 0
                    summary["anomalies_by_method"][method] += 1

                    # 按类型统计
                    anomaly_type = result.anomaly_type
                    if anomaly_type not in summary["anomalies_by_type"]:
                        summary["anomalies_by_type"][anomaly_type] = 0
                    summary["anomalies_by_type"][anomaly_type] += 1

                summary["anomalies_by_table"][table_name] = table_summary

            return summary

        except Exception as e:
            self.logger.error(f"生成异常检测摘要失败: {e}")
            raise