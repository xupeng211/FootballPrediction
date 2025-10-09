"""
应用监控收集器

收集应用级别的性能和业务指标。
"""



logger = logging.getLogger(__name__)


class ApplicationCollector:
    """应用监控收集器"""

    def __init__(self, metrics: SystemMetrics):
        """
        初始化应用收集器

        Args:
            metrics: 系统指标实例
        """
        self.metrics = metrics
        self.request_stats: List[Dict] = []
        self.prediction_stats: Dict[str, Dict] = {}
        self.data_collection_stats: Dict[str, Dict] = {}

    async def collect(self) -> Dict[str, any]:
        """
        收集应用指标

        Returns:
            收集到的指标值
        """
        try:
            metrics_data = {}

            # 收集请求统计
            request_stats = self._get_request_summary()
            metrics_data["requests"] = request_stats

            # 收集预测统计
            prediction_stats = self._get_prediction_summary()
            metrics_data["predictions"] = prediction_stats

            # 收集数据收集统计
            collection_stats = self._get_data_collection_summary()
            metrics_data["data_collection"] = collection_stats

            # 清理旧数据
            self._cleanup_old_data()

            logger.debug(f"应用指标收集完成: {metrics_data}")
            return metrics_data

        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")
            return {}

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """
        记录HTTP请求

        Args:
            method: HTTP方法
            endpoint: 端点
            status_code: 状态码
            duration: 请求持续时间
        """
        # 记录到Prometheus
        self.metrics.app_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()

        self.metrics.app_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

        # 保存到本地统计
        self.request_stats.append({
            "timestamp": time.time(),
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration": duration,
        })

        # 只保留最近1000条记录
        if len(self.request_stats) > 1000:
            self.request_stats = self.request_stats[-1000:]

    def record_prediction(self, model_version: str, league: str):
        """
        记录预测事件

        Args:
            model_version: 模型版本
            league: 联赛
        """
        # 记录到Prometheus
        self.metrics.business_predictions_total.labels(
            model_version=model_version,
            league=league,
        ).inc()

        # 保存到本地统计
        key = f"{model_version}.{league}"
        if key not in self.prediction_stats:
            self.prediction_stats[key] = {
                "model_version": model_version,
                "league": league,
                "count": 0,
                "last_prediction": None,
            }

        self.prediction_stats[key]["count"] += 1
        self.prediction_stats[key]["last_prediction"] = time.time()

    def record_data_collection_job(self, data_source: str, status: str):
        """
        记录数据收集任务

        Args:
            data_source: 数据源
            status: 任务状态
        """
        # 记录到Prometheus
        self.metrics.business_data_collection_jobs_total.labels(
            data_source=data_source,
            status=status,
        ).inc()

        # 保存到本地统计
        if data_source not in self.data_collection_stats:
            self.data_collection_stats[data_source] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "last_job": None,
            }

        self.data_collection_stats[data_source]["total"] += 1
        if status == "success":
            self.data_collection_stats[data_source]["success"] += 1
        else:
            self.data_collection_stats[data_source]["failed"] += 1

        self.data_collection_stats[data_source]["last_job"] = time.time()

    def record_model_inference(self, model_name: str, model_version: str, duration: float):
        """
        记录模型推理

        Args:
            model_name: 模型名称
            model_version: 模型版本
            duration: 推理持续时间
        """
        self.metrics.ml_model_inference_duration_seconds.labels(
            model_name=model_name,
            model_version=model_version,
        ).observe(duration)

    def record_model_training(self, model_name: str, model_version: str, duration: float):
        """
        记录模型训练

        Args:
            model_name: 模型名称
            model_version: 模型版本
            duration: 训练持续时间
        """
        self.metrics.ml_model_training_duration_seconds.labels(
            model_name=model_name,
            model_version=model_version,
        ).observe(duration)

    def _get_request_summary(self) -> Dict[str, any]:
        """获取请求摘要"""
        if not self.request_stats:
            return {"total_requests": 0}

        # 最近1小时的请求
        one_hour_ago = time.time() - 3600
        recent_requests = [
            r for r in self.request_stats
            if r["timestamp"] > one_hour_ago
        ]

        # 计算统计
        total_requests = len(recent_requests)
        error_requests = len([
            r for r in recent_requests
            if r["status_code"] >= 400
        ])

        # 计算平均响应时间
        avg_duration = sum(r["duration"] for r in recent_requests) / total_requests if total_requests > 0 else 0

        # 按状态码统计
        status_counts = {}
        for r in recent_requests:
            status = r["status_code"]
            status_counts[status] = status_counts.get(status, 0) + 1

        # 按端点统计
        endpoint_counts = {}
        for r in recent_requests:
            ep = r["endpoint"]
            if ep not in endpoint_counts:
                endpoint_counts[ep] = {"count": 0, "total_duration": 0}
            endpoint_counts[ep]["count"] += 1
            endpoint_counts[ep]["total_duration"] += r["duration"]

        # 计算每个端点的平均响应时间
        for ep in endpoint_counts:
            count = endpoint_counts[ep]["count"]
            endpoint_counts[ep]["avg_duration"] = endpoint_counts[ep]["total_duration"] / count
            del endpoint_counts[ep]["total_duration"]

        return {
            "total_requests": total_requests,
            "error_requests": error_requests,
            "error_rate": error_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time": avg_duration,
            "status_distribution": status_counts,
            "top_endpoints": dict(
                sorted(
                    endpoint_counts.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True
                )[:10]
            ),
        }

    def _get_prediction_summary(self) -> Dict[str, any]:
        """获取预测摘要"""
        if not self.prediction_stats:
            return {"total_predictions": 0}

        total_predictions = sum(
            stats["count"] for stats in self.prediction_stats.values()
        )

        # 最近24小时的预测
        one_day_ago = time.time() - 86400
        recent_predictions = sum(
            1 for stats in self.prediction_stats.values()
            if stats["last_prediction"] and stats["last_prediction"] > one_day_ago
        )

        return {
            "total_predictions": total_predictions,
            "recent_predictions_24h": recent_predictions,
            "models": dict(
                sorted(
                    {
                        key: stats["count"]
                        for key, stats in self.prediction_stats.items()
                    }.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ),
        }

    def _get_data_collection_summary(self) -> Dict[str, any]:
        """获取数据收集摘要"""
        if not self.data_collection_stats:
            return {"total_jobs": 0}

        total_jobs = sum(
            stats["total"] for stats in self.data_collection_stats.values()
        )
        total_success = sum(
            stats["success"] for stats in self.data_collection_stats.values()
        )

        # 最近24小时的作业
        one_day_ago = time.time() - 86400
        recent_jobs = sum(
            1 for stats in self.data_collection_stats.values()
            if stats["last_job"] and stats["last_job"] > one_day_ago
        )

        return {
            "total_jobs": total_jobs,
            "success_rate": total_success / total_jobs if total_jobs > 0 else 0,
            "recent_jobs_24h": recent_jobs,
            "by_source": {
                source: {
                    "total": stats["total"],
                    "success": stats["success"],
                    "failed": stats["failed"],
                    "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0,
                }
                for source, stats in self.data_collection_stats.items()
            },
        }

    def _cleanup_old_data(self):
        """清理旧数据"""
        # 清理超过1小时的请求记录
        one_hour_ago = time.time() - 3600
        self.request_stats = [
            r for r in self.request_stats
            if r["timestamp"] > one_hour_ago


        ]

        # 清理超过7天的预测统计
        seven_days_ago = time.time() - 604800
        self.prediction_stats = {
            key: stats for key, stats in self.prediction_stats.items()
            if not stats["last_prediction"] or stats["last_prediction"] > seven_days_ago
        }