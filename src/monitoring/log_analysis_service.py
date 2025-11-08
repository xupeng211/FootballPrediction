"""
增强日志分析服务
Enhanced Log Analysis Service

提供完整的日志聚合、分析和监控功能。
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .log_aggregator import (
    AccessLogParser,
    ErrorLogParser,
    LogCollector,
    LogLevel,
    LogQuery,
    LogSource,
    PythonLogParser,
)

logger = logging.getLogger(__name__)


class LogAnalysisService:
    """日志分析服务"""

    def __init__(self):
        self.collector = LogCollector()
        self.analysis_results: dict[str, Any] = {}
        self._running = False

    async def start(self):
        """启动日志分析服务"""
        if self._running:
            return

        self._running = True

        # 添加解析器
        self.collector.add_parser(PythonLogParser())
        self.collector.add_parser(AccessLogParser())
        self.collector.add_parser(ErrorLogParser())

        # 启动收集器
        await self.collector.start_collection()

        logger.info("日志分析服务已启动")

    async def stop(self):
        """停止日志分析服务"""
        self._running = False
        await self.collector.stop_collection()
        logger.info("日志分析服务已停止")

    async def analyze_log_file(self, file_path: str, source_type: str = "application"):
        """分析日志文件"""
        if not Path(file_path).exists():
            logger.warning(f"日志文件不存在: {file_path}")
            return {"error": "文件不存在"}

        try:
            source_map = {
                "application": LogSource.APPLICATION,
                "access": LogSource.ACCESS,
                "error": LogSource.ERROR,
                "system": LogSource.SYSTEM,
                "audit": LogSource.AUDIT,
            }
            source = source_map.get(source_type.lower(), LogSource.APPLICATION)

            # 监视文件
            await self.collector.watch_file(file_path, source)

            # 等待一段时间让文件内容被处理
            await asyncio.sleep(2)

            # 生成分析报告
            report = await self._generate_analysis_report()

            return report

        except Exception as e:
            logger.error(f"分析日志文件失败: {e}")
            return {"error": str(e)}

    async def analyze_log_string(
        self, log_content: str, source_type: str = "application"
    ):
        """分析日志字符串内容"""
        try:
            source_map = {
                "application": LogSource.APPLICATION,
                "access": LogSource.ACCESS,
                "error": LogSource.ERROR,
                "system": LogSource.SYSTEM,
                "audit": LogSource.AUDIT,
            }
            source = source_map.get(source_type.lower(), LogSource.APPLICATION)

            # 处理每一行日志
            for line in log_content.strip().split("\n"):
                if line.strip():
                    await self.collector.parse_and_store(line, source)

            # 生成分析报告
            report = await self._generate_analysis_report()

            return report

        except Exception as e:
            logger.error(f"分析日志内容失败: {e}")
            return {"error": str(e)}

    async def _generate_analysis_report(self) -> dict[str, Any]:
        """生成分析报告"""
        logs = list(self.collector.log_buffer)

        if not logs:
            return {"message": "没有日志数据可分析"}

        # 基础统计
        total_logs = len(logs)
        error_count = len([log for log in logs if log.level == LogLevel.ERROR])
        warning_count = len([log for log in logs if log.level == LogLevel.WARNING])
        info_count = len([log for log in logs if log.level == LogLevel.INFO])

        # 错误分析
        error_logs = [log for log in logs if log.level == LogLevel.ERROR]
        common_errors = self._analyze_common_errors(error_logs)

        # 时间分析
        recent_errors = self._analyze_recent_errors(logs)

        # 源分析
        source_analysis = self._analyze_log_sources(logs)

        report = {
            "summary": {
                "total_logs": total_logs,
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "error_rate": (
                    f"{(error_count/total_logs*100):.2f}%" if total_logs > 0 else "0%"
                ),
            },
            "error_analysis": {
                "common_errors": common_errors,
                "recent_errors": recent_errors,
                "critical_errors": [
                    log.message for log in error_logs if "CRITICAL" in log.message
                ],
            },
            "source_analysis": source_analysis,
            "recommendations": self._generate_recommendations(
                error_count, warning_count, total_logs
            ),
            "timestamp": datetime.now().isoformat(),
        }

        self.analysis_results = report
        return report

    def _analyze_common_errors(self, error_logs: list) -> dict[str, int]:
        """分析常见错误"""
        error_messages = [log.message for log in error_logs]
        error_counts = {}

        for message in error_messages:
            # 提取错误类型（简化版）
            if "ConnectionError" in message:
                error_type = "连接错误"
            elif "TimeoutError" in message:
                error_type = "超时错误"
            elif "ValueError" in message:
                error_type = "值错误"
            elif "KeyError" in message:
                error_type = "键错误"
            elif "AttributeError" in message:
                error_type = "属性错误"
            else:
                error_type = "其他错误"

            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return error_counts

    def _analyze_recent_errors(self, logs: list) -> dict[str, Any]:
        """分析最近的错误"""
        now = datetime.now()
        recent_threshold = now - timedelta(hours=1)

        recent_error_logs = [
            log
            for log in logs
            if log.level == LogLevel.ERROR and log.timestamp >= recent_threshold
        ]

        return {
            "count": len(recent_error_logs),
            "rate": f"{len(recent_error_logs)} 错误/小时",
            "latest": recent_error_logs[-1].message if recent_error_logs else None,
        }

    def _analyze_log_sources(self, logs: list) -> dict[str, Any]:
        """分析日志来源"""
        source_counts = {}

        for log in logs:
            source_name = (
                log.source.value if hasattr(log.source, "value") else str(log.source)
            )
            source_counts[source_name] = source_counts.get(source_name, 0) + 1

        return {
            "sources": source_counts,
            "most_active": (
                max(source_counts, key=source_counts.get) if source_counts else None
            ),
        }

    def _generate_recommendations(
        self, error_count: int, warning_count: int, total_logs: int
    ) -> list[str]:
        """生成建议"""
        recommendations = []

        if error_count > 0:
            error_rate = (error_count / total_logs) * 100 if total_logs > 0 else 0
            if error_rate > 10:
                recommendations.append("❌ 错误率过高，需要立即关注系统稳定性")
            elif error_rate > 5:
                recommendations.append("⚠️ 错误率较高，建议优先修复关键错误")
            else:
                recommendations.append("✅ 错误率在可接受范围内")

        if warning_count > error_count * 2:
            recommendations.append("⚠️ 警告数量较多，可能存在潜在问题")

        if total_logs == 0:
            recommendations.append("📋 没有检测到日志数据，请检查日志配置")

        if len(recommendations) == 0:
            recommendations.append("✅ 系统运行状态良好")

        return recommendations

    def get_logs_by_level(self, level: LogLevel, limit: int = 100) -> list:
        """按级别获取日志"""
        query = LogQuery(level=level, limit=limit)
        return self.collector.get_logs(query)

    def get_logs_by_time_range(self, start_time: datetime, end_time: datetime) -> list:
        """按时间范围获取日志"""
        query = LogQuery(start_time=start_time, end_time=end_time)
        return self.collector.get_logs(query)

    def export_analysis_report(self, file_path: str):
        """导出分析报告"""
        if not self.analysis_results:
            logger.warning("没有分析报告可导出")
            return False

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.analysis_results, f, indent=2, ensure_ascii=False, default=str
                )

            logger.info(f"分析报告已导出到: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出分析报告失败: {e}")
            return False


# 全局日志分析服务实例
_log_analysis_service: LogAnalysisService | None = None


async def get_log_analysis_service() -> LogAnalysisService:
    """获取全局日志分析服务实例"""
    global _log_analysis_service

    if _log_analysis_service is None:
        _log_analysis_service = LogAnalysisService()
        await _log_analysis_service.start()

    return _log_analysis_service
