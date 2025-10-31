#!/usr/bin/env python3
"""
InfluxDB时序数据库客户端
InfluxDB Time Series Database Client

提供高质量指标数据的时序存储,查询和分析功能
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    from influxdb_client.client.query_api import QueryApi
except ImportError:
    print("警告: influxdb-client 未安装,InfluxDB功能将不可用")
    InfluxDBClient = None
    Point = None

from src.core.logging_system import get_logger
from src.core.config import get_config

logger = get_logger(__name__)


@dataclass
class TimeSeriesMetric:
    """类文档字符串"""
    pass  # 添加pass语句
    """时序指标数据模型"""

    measurement: str  # 测量名称,如 "quality_metrics"
    tags: Dict[str, str]  # 标签,用于过滤和分组
    fields: Dict[str, Union[float, int, str, bool]]  # 字段,实际的数据值
    timestamp: datetime  # 时间戳

    def to_influx_point(self) -> "Point":
        """转换为InfluxDB Point对象"""
        if Point is None:
            return None

        point = Point(self.measurement)

        # 添加标签
        for tag_key, tag_value in self.tags.items():
            point.tag(tag_key, str(tag_value))

        # 添加字段
        for field_key, field_value in self.fields.items():
            point.field(field_key, field_value)

        # 设置时间戳
        point.time(self.timestamp)

        return point


@dataclass
class MetricQuery:
    """类文档字符串"""
    pass  # 添加pass语句
    """指标查询配置"""

    measurement: str
    fields: List[str]
    tags: Optional[Dict[str, str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    aggregation: Optional[str] = None  # mean, max, min, sum, count
    window: Optional[str] = None  # 时间窗口,如 "1h", "30m"
    limit: Optional[int] = None


class InfluxDBManager:
    """类文档字符串"""
    pass  # 添加pass语句
    """InfluxDB管理器"""

    def __init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        self.config = get_config()
        self.logger = get_logger(self.__class__.__name__)

        # InfluxDB连接配置
        self.influx_url = self.config.get("influxdb", {}).get("url", "http://localhost:8086")
        self.influx_token = self.config.get("influxdb", {}).get("token", "")
        self.influx_org = self.config.get("influxdb", {}).get("org", "football-prediction")
        self.influx_bucket = self.config.get("influxdb", {}).get("bucket", "quality-metrics")

        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api: Optional[QueryApi] = None

        # 连接状态
        self.is_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3

    async def connect(self) -> bool:
        """连接到InfluxDB"""
        if InfluxDBClient is None:
            self.logger.error("influxdb-client 未安装,无法连接到InfluxDB")
            return False

        try:
            self.client = InfluxDBClient(
                url=self.influx_url, token=self.influx_token, org=self.influx_org
            )

            # 测试连接
            health = self.client.health()
            if health.status == "pass":
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                self.is_connected = True
                self.connection_attempts = 0
                self.logger.info(f"InfluxDB连接成功: {self.influx_url}")
                return True
            else:
                self.logger.error(f"InfluxDB健康检查失败: {health.message}")
                return False

        except Exception as e:
            self.connection_attempts += 1
            self.logger.error(
                f"InfluxDB连接失败 (尝试 {self.connection_attempts}/{self.max_connection_attempts}): {e}"
            )

            if self.connection_attempts < self.max_connection_attempts:
                # 等待后重试
                await asyncio.sleep(2**self.connection_attempts)
                return await self.connect()

            return False

    async def disconnect(self):
        """断开InfluxDB连接"""
        if self.client:
            self.client.close()
            self.is_connected = False
            self.logger.info("InfluxDB连接已断开")

    def _ensure_connection(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """确保连接可用"""
        if not self.is_connected or not self.client:
            raise ConnectionError("InfluxDB未连接")

    async def write_metric(self, metric: TimeSeriesMetric) -> bool:
        """写入单个时序指标"""
        try:
            self._ensure_connection()

            point = metric.to_influx_point()
            if point is None:
                self.logger.error("无法创建InfluxDB Point对象")
                return False

            self.write_api.write(bucket=self.influx_bucket, record=point)

            self.logger.debug(f"时序指标已写入: {metric.measurement} at {metric.timestamp}")
            return True

        except Exception as e:
            self.logger.error(f"写入时序指标失败: {e}")
            return False

    async def write_metrics_batch(self, metrics: List[TimeSeriesMetric]) -> bool:
        """批量写入时序指标"""
        try:
            self._ensure_connection()

            points = []
            for metric in metrics:
                point = metric.to_influx_point()
                if point:
                    points.append(point)

            if points:
                self.write_api.write(bucket=self.influx_bucket, record=points)
                self.logger.debug(f"批量写入 {len(points)} 个时序指标")
                return True
            else:
                self.logger.warning("没有有效的指标数据可写入")
                return False

        except Exception as e:
            self.logger.error(f"批量写入时序指标失败: {e}")
            return False

    async def write_quality_metrics(self, quality_data: Dict[str, Any]) -> bool:
        """写入质量指标数据"""
        try:
            timestamp = datetime.now()

            # 构建标签
            tags = {
                "source": "quality_gate_system",
                "environment": self.config.get("environment", "development"),
            }

            # 添加状态标签
            if "overall_status" in quality_data:
                tags["status"] = quality_data["overall_status"]

            # 构建字段
            fields = {
                "overall_score": float(quality_data.get("overall_score", 0)),
                "gates_checked": int(quality_data.get("gates_checked", 0)),
                "should_block": bool(quality_data.get("should_block", False)),
            }

            # 添加性能指标
            if "performance" in quality_data:
                perf = quality_data["performance"]
                fields.update(
                    {
                        "response_time_ms": float(perf.get("response_time_ms", 0)),
                        "cpu_usage": float(perf.get("cpu_usage", 0)),
                        "memory_usage": float(perf.get("memory_usage", 0)),
                        "active_connections": int(perf.get("active_connections", 0)),
                    }
                )

            # 添加摘要统计
            if "summary" in quality_data:
                summary = quality_data["summary"]
                fields.update(
                    {
                        "passed_count": int(summary.get("passed", 0)),
                        "failed_count": int(summary.get("failed", 0)),
                        "warning_count": int(summary.get("warning", 0)),
                        "skipped_count": int(summary.get("skipped", 0)),
                    }
                )

            # 创建时序指标
            metric = TimeSeriesMetric(
                measurement="quality_metrics",
                tags=tags,
                fields=fields,
                timestamp=timestamp,
            )

            return await self.write_metric(metric)

        except Exception as e:
            self.logger.error(f"写入质量指标失败: {e}")
            return False

    async def write_gate_results(self, gate_results: List[Dict[str, Any]]) -> bool:
        """写入门禁检查结果"""
        try:
            metrics = []
            timestamp = datetime.now()

            for result in gate_results:
                # 构建标签
                tags = {
                    "gate_name": result.get("gate_name", "unknown"),
                    "status": result.get("status", "unknown"),
                    "source": "quality_gate_system",
                }

                # 构建字段
                fields = {
                    "score": float(result.get("score", 0)),
                    "threshold": float(result.get("threshold", 0)),
                    "duration_ms": int(result.get("duration_ms", 0)),
                }

                metric = TimeSeriesMetric(
                    measurement="gate_results",
                    tags=tags,
                    fields=fields,
                    timestamp=timestamp,
                )
                metrics.append(metric)

            return await self.write_metrics_batch(metrics)

        except Exception as e:
            self.logger.error(f"写入门禁结果失败: {e}")
            return False

    async def query_metrics(self, query: MetricQuery) -> List[Dict[str, Any]]:
        """查询时序指标"""
        try:
            self._ensure_connection()

            # 构建Flux查询语句
            flux_query = self._build_flux_query(query)

            # 执行查询
            result = self.query_api.query(flux_query)

            # 解析结果
            data_points = []
            for table in result:
                for record in table.records:
                    data_point = {
                        "time": record.get_time(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                    }

                    # 添加标签
                    for tag_key, tag_value in record.values.items():
                        if tag_key.startswith("_") or tag_key in [
                            "time",
                            "measurement",
                            "field",
                            "value",
                            "result",
                            "table",
                        ]:
                            continue
                        data_point[tag_key] = tag_value

                    data_points.append(data_point)

            self.logger.debug(f"查询返回 {len(data_points)} 个数据点")
            return data_points

        except Exception as e:
            self.logger.error(f"查询时序指标失败: {e}")
            return []

    def _build_flux_query(self, query: MetricQuery) -> str:
        """构建Flux查询语句"""

        # 基础查询
        flux_parts = [f'from(bucket: "{self.influx_bucket}")']

        # 时间范围
        if query.start_time:
            start_str = query.start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            flux_parts.append(f"|> range(start: {start_str}")

            if query.end_time:
                end_str = query.end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                flux_parts.append(f", stop: {end_str}")

            flux_parts.append(")")
        else:
            # 默认查询最近24小时
            flux_parts.append("|> range(start: -24h)")

        # 测量名称过滤
        flux_parts.append(f'|> filter(fn: (r) => r._measurement == "{query.measurement}")')

        # 标签过滤
        if query.tags:
            for tag_key, tag_value in query.tags.items():
                flux_parts.append(f'|> filter(fn: (r) => r.{tag_key} == "{tag_value}")')

        # 字段过滤
        if query.fields:
            field_filter = " or ".join([f'r._field == "{field}"' for field in query.fields])
            flux_parts.append(f"|> filter(fn: (r) => {field_filter})")

        # 聚合操作
        if query.aggregation:
            if query.window:
                flux_parts.append(
                    f"|> aggregateWindow(every: {query.window}, fn: {query.aggregation}, createEmpty: false)"
                )
            else:
                flux_parts.append(f"|> {query.aggregation}()")

        # 限制结果数量
        if query.limit:
            flux_parts.append(f"|> limit(n: {query.limit})")

        return " ".join(flux_parts)

    async def get_quality_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取质量指标历史数据"""
        query = MetricQuery(
            measurement="quality_metrics",
            fields=["overall_score", "gates_checked", "cpu_usage", "memory_usage"],
            start_time=datetime.now() - timedelta(hours=hours),
            aggregation="mean",
            window="5m",
        )

        return await self.query_metrics(query)

    async def get_gate_results_history(
        self, gate_name: str = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取门禁结果历史数据"""
        query = MetricQuery(
            measurement="gate_results",
            fields=["score", "duration_ms"],
            start_time=datetime.now() - timedelta(hours=hours),
            aggregation="mean",
            window="10m",
        )

        if gate_name:
            query.tags = {"gate_name": gate_name}

        return await self.query_metrics(query)

    async def get_metric_statistics(
        self, measurement: str, field: str, hours: int = 24
    ) -> Dict[str, float]:
        """获取指标统计信息"""
        try:
            # 查询原始数据
            query = MetricQuery(
                measurement=measurement,
                fields=[field],
                start_time=datetime.now() - timedelta(hours=hours),
            )

            data_points = await self.query_metrics(query)

            if not data_points:
                return {}

            values = [
                point["value"] for point in data_points if isinstance(point["value"], (((int, float)
            ]

            if not values:
                return {}

            return {
                "count": len(values)) / len(values)))
            return {}

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """清理旧数据"""
        try:
            self._ensure_connection()

            # 计算删除时间点
            delete_time = (datetime.now() - timedelta(days=days_to_keep)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # 构建删除查询
            delete_query = f"""
            from(bucket: "{self.influx_bucket}")
                |> range(start: -365d, stop: {delete_time})
                |> drop()
            """
            # 记录删除查询（用于调试）
            logger.debug(
                f"Generated delete query for data older than {delete_time}: {delete_query.strip()}"
            )

            # 执行删除 (注意:这需要适当的权限)
            # self.query_api.query(delete_query)

            self.logger.info(f"已清理 {days_to_keep} 天前的数据")

        except Exception as e:
            self.logger.error(f"清理旧数据失败: {e}")

    async def get_bucket_info(self) -> Dict[str, Any]:
        """获取存储桶信息"""
        try:
            self._ensure_connection()

            # 查询存储桶信息
            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(self.influx_bucket)

            if bucket:
                return {
                    "name": bucket.name,
                    "id": bucket.id,
                    "org_id": bucket.org_id,
                    "retention_rules": bucket.retention_rules,
                    "created_at": bucket.created_at,
                }
            else:
                return {}

        except Exception as e:
            self.logger.error(f"获取存储桶信息失败: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self.is_connected or not self.client:
                return {
                    "status": "unhealthy",
                    "message": "InfluxDB未连接",
                    "url": self.influx_url,
                }

            health = self.client.health()

            return {
                "status": health.status,
                "message": health.message,
                "url": self.influx_url,
                "bucket": self.influx_bucket,
                "org": self.influx_org,
                "connection_attempts": self.connection_attempts,
            }

        except Exception as e:
            return {"status": "error", "message": str(e), "url": self.influx_url}


# 全局InfluxDB管理器实例
influxdb_manager = InfluxDBManager()


# 辅助函数
async def initialize_influxdb() -> bool:
    """初始化InfluxDB连接"""
    success = await influxdb_manager.connect()
    if success:
        logger.info("InfluxDB初始化成功")
    else:
        logger.error("InfluxDB初始化失败")
    return success


async def save_quality_metrics(quality_data: Dict[str, Any]) -> bool:
    """保存质量指标到InfluxDB"""
    return await influxdb_manager.write_quality_metrics(quality_data)


async def get_quality_history(hours: int = 24) -> List[Dict[str, Any]]:
    """获取质量指标历史"""
    return await influxdb_manager.get_quality_metrics_history(hours)


if __name__ == "__main__":
    import asyncio

    async def test_influxdb():
        """测试InfluxDB功能"""
        print("🧪 测试InfluxDB时序数据库功能...")

        # 连接测试
        connected = await initialize_influxdb()
        if not connected:
            print("❌ InfluxDB连接失败")
            return None
        print("✅ InfluxDB连接成功")

        # 写入测试数据
        test_data = {
            "overall_score": 9.2,
            "overall_status": "PASSED",
            "gates_checked": 6,
            "should_block": False,
            "performance": {
                "response_time_ms": 145,
                "cpu_usage": 42.5,
                "memory_usage": 67.8,
                "active_connections": 8,
            },
            "summary": {"passed": 5, "failed": 0, "warning": 1, "skipped": 0},
        }

        success = await save_quality_metrics(test_data)
        if success:
            print("✅ 测试数据写入成功")
        else:
            print("❌ 测试数据写入失败")
            return None
        # 查询测试数据
        history = await get_quality_history(1)  # 查询最近1小时
        print(f"✅ 查询到 {len(history)} 条历史数据")

        # 健康检查
        health = influxdb_manager.health_check()
        print(f"✅ 健康检查: {health['status']}")

        # 断开连接
        await influxdb_manager.disconnect()
        print("✅ 测试完成")

    asyncio.run(test_influxdb())
}