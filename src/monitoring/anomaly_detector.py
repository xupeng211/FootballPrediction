"""
import asyncio
统计学异常检测器

实现基于统计学方法的数据异常检测，包括3σ规则、IQR方法、
Z-score分析等多种异常检测算法。

基于 DATA_DESIGN.md 数据质量监控设计。
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """异常类型枚举"""

    OUTLIER = "outlier"  # 离群值
    TREND_CHANGE = "trend_change"  # 趋势变化
    PATTERN_BREAK = "pattern_break"  # 模式中断
    VALUE_RANGE = "value_range"  # 数值范围异常
    FREQUENCY = "frequency"  # 频率异常
    NULL_SPIKE = "null_spike"  # 空值激增


class AnomalySeverity(Enum):
    """异常严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyResult:
    """异常检测结果"""

    def __init__(
        self,
        table_name: str,
        column_name: str,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity,
        anomalous_values: List[Any],
        anomaly_score: float,
        detection_method: str,
        description: str,
        detected_at: Optional[datetime] = None,
    ):
        """
        初始化异常检测结果

        Args:
            table_name: 表名
            column_name: 列名
            anomaly_type: 异常类型
            severity: 严重程度
            anomalous_values: 异常值列表
            anomaly_score: 异常得分
            detection_method: 检测方法
            description: 异常描述
            detected_at: 检测时间
        """
        self.table_name = table_name
        self.column_name = column_name
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.anomalous_values = anomalous_values
        self.anomaly_score = anomaly_score
        self.detection_method = detection_method
        self.description = description
        self.detected_at = detected_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "anomalous_values": self.anomalous_values,
            "anomaly_score": round(self.anomaly_score, 4),
            "detection_method": self.detection_method,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
        }


class AnomalyDetector:
    """
    统计学异常检测器主类

    提供多种异常检测方法：
    - 3σ规则检测
    - IQR方法检测
    - Z-score分析
    - 时间序列异常检测
    - 频率分布异常检测
    """

    def __init__(self):
        """初始化异常检测器"""
        self.db_manager = DatabaseManager()

        # 检测配置
        self.detection_config = {
            "matches": {
                "numeric_columns": ["home_score", "away_score", "minute"],
                "time_columns": ["match_time"],
                "categorical_columns": ["match_status"],
                "thresholds": {
                    "home_score": {"min": 0, "max": 20},
                    "away_score": {"min": 0, "max": 20},
                    "minute": {"min": 0, "max": 120},
                },
            },
            "odds": {
                "numeric_columns": ["home_odds", "draw_odds", "away_odds"],
                "time_columns": ["collected_at"],
                "categorical_columns": ["bookmaker", "market_type"],
                "thresholds": {
                    "home_odds": {"min": 1.01, "max": 100.0},
                    "draw_odds": {"min": 1.01, "max": 100.0},
                    "away_odds": {"min": 1.01, "max": 100.0},
                },
            },
            "predictions": {
                "numeric_columns": [
                    "home_win_probability",
                    "draw_probability",
                    "away_win_probability",
                ],
                "time_columns": ["created_at"],
                "categorical_columns": ["model_name"],
                "thresholds": {
                    "home_win_probability": {"min": 0.0, "max": 1.0},
                    "draw_probability": {"min": 0.0, "max": 1.0},
                    "away_win_probability": {"min": 0.0, "max": 1.0},
                },
            },
        }

        logger.info("异常检测器初始化完成")

    async def detect_anomalies(
        self,
        table_names: Optional[List[str]] = None,
        methods: Optional[List[str]] = None,
    ) -> List[AnomalyResult]:
        """
        执行异常检测

        Args:
            table_names: 要检测的表名列表
            methods: 要使用的检测方法列表

        Returns:
            List[AnomalyResult]: 异常检测结果列表
        """
        if table_names is None:
            table_names = list(self.detection_config.keys())

        if methods is None:
            methods = ["three_sigma", "iqr", "z_score", "range_check"]

        all_anomalies = []

        async with self.db_manager.get_async_session() as session:
            for table_name in table_names:
                try:
                    table_anomalies = await self._detect_table_anomalies(
                        session, table_name, methods
                    )
                    all_anomalies.extend(table_anomalies)
                    logger.debug(
                        f"表 {table_name} 异常检测完成，发现 {len(table_anomalies)} 个异常"
                    )
                except Exception as e:
                    logger.error(f"检测表 {table_name} 异常失败: {e}")

        logger.info(f"异常检测完成，总共发现 {len(all_anomalies)} 个异常")
        return all_anomalies

    async def _detect_table_anomalies(
        self, session: AsyncSession, table_name: str, methods: List[str]
    ) -> List[AnomalyResult]:
        """
        检测单个表的异常

        Args:
            session: 数据库会话
            table_name: 表名
            methods: 检测方法列表

        Returns:
            List[AnomalyResult]: 异常检测结果
        """
        anomalies: List[AnomalyResult] = []
        config = self.detection_config.get(table_name, {})

        if not config:
            logger.warning(f"表 {table_name} 没有检测配置")
            return anomalies

        # 获取表数据
        table_data = await self._get_table_data(session, table_name)

        if table_data.empty:
            logger.warning(f"表 {table_name} 没有数据")
            return anomalies

        # 数值列异常检测
        numeric_columns = config.get("numeric_columns", [])
        for column in numeric_columns:
            if column in table_data.columns:
                column_anomalies = await self._detect_column_anomalies(
                    table_data, table_name, column, methods, "numeric"
                )
                anomalies.extend(column_anomalies)

        # 分类列异常检测
        categorical_columns = config.get("categorical_columns", [])
        for column in categorical_columns:
            if column in table_data.columns:
                column_anomalies = await self._detect_column_anomalies(
                    table_data, table_name, column, methods, "categorical"
                )
                anomalies.extend(column_anomalies)

        # 时间列异常检测
        time_columns = config.get("time_columns", [])
        for column in time_columns:
            if column in table_data.columns:
                column_anomalies = await self._detect_column_anomalies(
                    table_data, table_name, column, methods, "time"
                )
                anomalies.extend(column_anomalies)

        return anomalies

    async def _get_table_data(
        self, session: AsyncSession, table_name: str
    ) -> pd.DataFrame:
        """
        获取表数据

        Args:
            session: 数据库会话
            table_name: 表名

        Returns:
            pd.DataFrame: 表数据
        """
        try:
            # 获取最近1000条记录进行异常检测
            # Safe: table_name is validated against whitelist above
            # Note: Using f-string here is safe as table_name is validated against whitelist
            result = await session.execute(
                text(
                    f"""
                    SELECT * FROM {table_name}
                    ORDER BY id DESC
                    LIMIT 1000
                """  # nosec B608 - table_name is validated against whitelist
                )
            )

            # 转换为DataFrame
            rows = result.fetchall()
            data = pd.DataFrame([dict(row._mapping) for row in rows])
            return data

        except Exception as e:
            logger.error(f"获取表 {table_name} 数据失败: {e}")
            return pd.DataFrame()

    async def _detect_column_anomalies(
        self,
        data: pd.DataFrame,
        table_name: str,
        column_name: str,
        methods: List[str],
        column_type: str,
    ) -> List[AnomalyResult]:
        """
        检测单列的异常

        Args:
            data: 数据框
            table_name: 表名
            column_name: 列名
            methods: 检测方法
            column_type: 列类型

        Returns:
            List[AnomalyResult]: 异常结果列表
        """
        anomalies: List[AnomalyResult] = []
        column_data = data[column_name].dropna()

        if len(column_data) == 0:
            return anomalies

        # 根据列类型和方法进行检测
        if column_type == "numeric":
            if "three_sigma" in methods:
                anomalies.extend(
                    self._detect_three_sigma_anomalies(
                        column_data, table_name, column_name
                    )
                )

            if "iqr" in methods:
                anomalies.extend(
                    self._detect_iqr_anomalies(column_data, table_name, column_name)
                )

            if "z_score" in methods:
                anomalies.extend(
                    self._detect_z_score_anomalies(column_data, table_name, column_name)
                )

            if "range_check" in methods:
                anomalies.extend(
                    self._detect_range_anomalies(column_data, table_name, column_name)
                )

        elif column_type == "categorical":
            if "frequency" in methods:
                anomalies.extend(
                    self._detect_frequency_anomalies(
                        column_data, table_name, column_name
                    )
                )

        elif column_type == "time":
            if "time_gap" in methods:
                anomalies.extend(
                    self._detect_time_gap_anomalies(
                        column_data, table_name, column_name
                    )
                )

        return anomalies

    def _detect_three_sigma_anomalies(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        3σ规则异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            mean = data.mean()
            std = data.std()

            if std == 0:
                return []  # 无变化数据不检测异常

            # 3σ异常阈值
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std

            # 检测异常值
            outliers = data[(data < lower_bound) | (data > upper_bound)]

            if len(outliers) > 0:
                # 计算异常得分
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.OUTLIER,
                        severity=severity,
                        anomalous_values=outliers.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="3sigma",
                        description=f"发现 {len(outliers)} 个3σ规则异常值，超出范围 [{lower_bound:.2f}, {upper_bound:.2f}]",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"3σ规则检测失败 {table_name}.{column_name}: {e}")
            return []

    def _detect_iqr_anomalies(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        IQR方法异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1

            if IQR == 0:
                return []  # IQR为0时不检测异常

            # IQR异常阈值
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # 检测异常值
            outliers = data[(data < lower_bound) | (data > upper_bound)]

            if len(outliers) > 0:
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.OUTLIER,
                        severity=severity,
                        anomalous_values=outliers.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="iqr",
                        description=f"发现 {len(outliers)} 个IQR方法异常值，超出范围 [{lower_bound:.2f}, {upper_bound:.2f}]",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"IQR方法检测失败 {table_name}.{column_name}: {e}")
            return []

    def _detect_z_score_anomalies(
        self, data: pd.Series, table_name: str, column_name: str, threshold: float = 3.0
    ) -> List[AnomalyResult]:
        """
        Z-score异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名
            threshold: Z-score阈值

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            mean = data.mean()
            std = data.std()

            if std == 0:
                return []

            # 计算Z-score
            z_scores = np.abs((data - mean) / std)

            # 检测异常值
            outliers = data[z_scores > threshold]
            outlier_scores = z_scores[z_scores > threshold]

            if len(outliers) > 0:
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.OUTLIER,
                        severity=severity,
                        anomalous_values=outliers.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="z_score",
                        description=f"发现 {len(outliers)} 个Z-score异常值，最大Z-score: {outlier_scores.max():.2f}",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"Z-score检测失败 {table_name}.{column_name}: {e}")
            return []

    def _detect_range_anomalies(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        范围检查异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            # 获取配置的阈值
            config = self.detection_config.get(table_name, {})
            thresholds = config.get("thresholds", {}).get(column_name, {})

            if not thresholds:
                return []

            min_val = thresholds.get("min")
            max_val = thresholds.get("max")

            outliers = []

            if min_val is not None:
                outliers.extend(data[data < min_val].tolist())

            if max_val is not None:
                outliers.extend(data[data > max_val].tolist())

            if len(outliers) > 0:
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.VALUE_RANGE,
                        severity=severity,
                        anomalous_values=outliers,
                        anomaly_score=anomaly_score,
                        detection_method="range_check",
                        description=f"发现 {len(outliers)} 个范围异常值，预期范围: [{min_val}, {max_val}]",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"范围检查失败 {table_name}.{column_name}: {e}")
            return []

    def _detect_frequency_anomalies(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        频率分布异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            # 计算值频率
            value_counts = data.value_counts()
            total_count = len(data)

            # 检测频率异常（出现次数过少或过多）
            expected_freq = total_count / len(value_counts)  # 平均频率

            anomalous_values = []
            for value, count in value_counts.items():
                # 频率异常：大于平均频率的5倍或小于平均频率的1/10
                if count > expected_freq * 5 or count < expected_freq * 0.1:
                    anomalous_values.append(value)

            if len(anomalous_values) > 0:
                anomaly_score = len(anomalous_values) / len(value_counts)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.FREQUENCY,
                        severity=severity,
                        anomalous_values=anomalous_values,
                        anomaly_score=anomaly_score,
                        detection_method="frequency",
                        description=f"发现 {len(anomalous_values)} 个频率异常值，预期频率: {expected_freq:.1f}",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"频率检测失败 {table_name}.{column_name}: {e}")
            return []

    def _detect_time_gap_anomalies(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        时间间隔异常检测

        Args:
            data: 时间数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            # 转换为时间戳并排序
            time_data = pd.to_datetime(data).sort_values()

            if len(time_data) < 2:
                return []

            # 计算时间间隔
            time_diffs = time_data.diff().dt.total_seconds().dropna()

            # 使用IQR方法检测时间间隔异常
            Q1 = time_diffs.quantile(0.25)
            Q3 = time_diffs.quantile(0.75)
            IQR = Q3 - Q1

            if IQR == 0:
                return []

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # 检测异常时间间隔
            anomalous_gaps = time_diffs[
                (time_diffs < lower_bound) | (time_diffs > upper_bound)
            ]

            if len(anomalous_gaps) > 0:
                anomaly_score = len(anomalous_gaps) / len(time_diffs)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.PATTERN_BREAK,
                        severity=severity,
                        anomalous_values=anomalous_gaps.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="time_gap",
                        description=f"发现 {len(anomalous_gaps)} 个时间间隔异常，正常范围: {lower_bound:.0f}-{upper_bound:.0f}秒",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"时间间隔检测失败 {table_name}.{column_name}: {e}")
            return []

    def _calculate_severity(self, anomaly_score: float) -> AnomalySeverity:
        """
        计算异常严重程度

        Args:
            anomaly_score: 异常得分（0-1）

        Returns:
            AnomalySeverity: 严重程度
        """
        if anomaly_score >= 0.2:
            return AnomalySeverity.CRITICAL
        elif anomaly_score >= 0.1:
            return AnomalySeverity.HIGH
        elif anomaly_score >= 0.05:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    async def get_anomaly_summary(
        self, anomalies: List[AnomalyResult]
    ) -> Dict[str, Any]:
        """
        获取异常摘要

        Args:
            anomalies: 异常结果列表

        Returns:
            Dict[str, Any]: 异常摘要
        """
        if not anomalies:
            return {
                "total_anomalies": 0,
                "by_severity": {},
                "by_type": {},
                "by_table": {},
                "summary_time": datetime.now().isoformat(),
            }

        # 按严重程度统计
        by_severity: Dict[str, int] = {}
        for anomaly in anomalies:
            severity = anomaly.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # 按类型统计
        by_type: Dict[str, int] = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.anomaly_type.value
            by_type[anomaly_type] = by_type.get(anomaly_type, 0) + 1

        # 按表统计
        by_table: Dict[str, int] = {}
        for anomaly in anomalies:
            table = anomaly.table_name
            by_table[table] = by_table.get(table, 0) + 1

        return {
            "total_anomalies": len(anomalies),
            "by_severity": by_severity,
            "by_type": by_type,
            "by_table": by_table,
            "critical_anomalies": len(
                [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
            ),
            "high_priority_anomalies": len(
                [
                    a
                    for a in anomalies
                    if a.severity in [AnomalySeverity.CRITICAL, AnomalySeverity.HIGH]
                ]
            ),
            "most_affected_table": (
                max(by_table.items(), key=lambda x: x[1])[0] if by_table else None
            ),
            "summary_time": datetime.now().isoformat(),
        }
