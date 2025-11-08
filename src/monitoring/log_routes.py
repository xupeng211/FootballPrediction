"""
日志聚合分析API路由
Log Aggregation and Analysis API Routes

提供日志查询、分析、统计等功能的REST API接口。
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .log_aggregator import (
    LogEntry,
    LogLevel,
    LogQuery,
    LogSource,
    log_analyzer,
    log_collector,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# ============================================================================
# Pydantic模型
# ============================================================================


class LogQueryRequest(BaseModel):
    """日志查询请求"""

    keyword: str | None = Field(None, description="关键词搜索")
    level: LogLevel | None = Field(None, description="日志级别")
    source: LogSource | None = Field(None, description="日志来源")
    module: str | None = Field(None, description="模块名称")
    start_time: datetime | None = Field(None, description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    tags: list[str] = Field(default_factory=list, description="标签过滤")
    metadata_filter: dict[str, str] = Field(
        default_factory=dict, description="元数据过滤"
    )
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


class LogEntryResponse(BaseModel):
    """日志条目响应"""

    id: str
    timestamp: datetime
    level: LogLevel
    source: LogSource
    message: str
    module: str | None = None
    function: str | None = None
    line_number: int | None = None
    thread_id: str | None = None
    process_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status_code: int | None = None
    response_time: float | None = None
    tags: list[str] = []
    metadata: dict[str, str] = {}


class LogStatisticsResponse(BaseModel):
    """日志统计响应"""

    total_count: int
    level_counts: dict[LogLevel, int]
    source_counts: dict[LogSource, int]
    hourly_counts: dict[str, int]
    error_rate: float
    avg_response_time: float
    top_errors: list[dict[str, any]]
    top_modules: list[dict[str, any]]


class LogFileWatchRequest(BaseModel):
    """日志文件监视请求"""

    file_path: str = Field(..., description="日志文件路径")
    source: LogSource = Field(LogSource.APPLICATION, description="日志来源")


class IngestLogRequest(BaseModel):
    """日志摄取请求"""

    message: str = Field(..., description="日志消息")
    source: LogSource = Field(LogSource.APPLICATION, description="日志来源")


# ============================================================================
# 日志查询和搜索
# ============================================================================


@router.post("/search", response_model=list[LogEntryResponse])
async def search_logs(query: LogQueryRequest):
    """搜索日志"""
    try:
        # 创建查询对象
        log_query = LogQuery(
            keyword=query.keyword,
            level=query.level,
            source=query.source,
            module=query.module,
            start_time=query.start_time,
            end_time=query.end_time,
            tags=query.tags,
            metadata_filter=query.metadata_filter,
            limit=query.limit,
            offset=query.offset,
        )

        # 执行查询
        logs = log_collector.get_logs(log_query)

        # 转换为响应格式
        return [
            LogEntryResponse(
                id=log.id,
                timestamp=log.timestamp,
                level=log.level,
                source=log.source,
                message=log.message,
                module=log.module,
                function=log.function,
                line_number=log.line_number,
                thread_id=log.thread_id,
                process_id=log.process_id,
                user_id=log.user_id,
                session_id=log.session_id,
                request_id=log.request_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                status_code=log.status_code,
                response_time=log.response_time,
                tags=log.tags,
                metadata=log.metadata,
            )
            for log in logs
        ]

    except Exception as e:
        logger.error(f"搜索日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索日志失败: {str(e)}") from e


@router.get("/recent", response_model=list[LogEntryResponse])
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    level: LogLevel | None = Query(None, description="日志级别过滤"),
    source: LogSource | None = Query(None, description="日志来源过滤"),
):
    """获取最近日志"""
    try:
        # 创建查询对象
        log_query = LogQuery(
            level=level,
            source=source,
            limit=limit,
            offset=0,
        )

        # 执行查询
        logs = log_collector.get_logs(log_query)

        # 转换为响应格式
        return [
            LogEntryResponse(
                id=log.id,
                timestamp=log.timestamp,
                level=log.level,
                source=log.source,
                message=log.message,
                module=log.module,
                function=log.function,
                line_number=log.line_number,
                thread_id=log.thread_id,
                process_id=log.process_id,
                user_id=log.user_id,
                session_id=log.session_id,
                request_id=log.request_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                status_code=log.status_code,
                response_time=log.response_time,
                tags=log.tags,
                metadata=log.metadata,
            )
            for log in logs
        ]

    except Exception as e:
        logger.error(f"获取最近日志失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取最近日志失败: {str(e)}"
        ) from e


# ============================================================================
# 日志分析和统计
# ============================================================================


@router.get("/statistics", response_model=LogStatisticsResponse)
async def get_log_statistics(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
):
    """获取日志统计"""
    try:
        # 创建查询对象
        query = LogQuery(limit=10000)

        # 分析日志
        stats = log_analyzer.analyze_logs(query, hours)

        return LogStatisticsResponse(
            total_count=stats.total_count,
            level_counts=stats.level_counts,
            source_counts=stats.source_counts,
            hourly_counts=stats.hourly_counts,
            error_rate=stats.error_rate,
            avg_response_time=stats.avg_response_time,
            top_errors=stats.top_errors,
            top_modules=stats.top_modules,
        )

    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取日志统计失败: {str(e)}"
        ) from e


@router.get("/errors", response_model=list[dict[str, any]])
async def get_error_logs(
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
):
    """获取错误日志"""
    try:
        # 创建查询对象，只查询ERROR和CRITICAL级别
        query = LogQuery(
            start_time=datetime.now() - timedelta(hours=hours),
            end_time=datetime.now(),
            limit=limit * 2,  # 获取更多数据用于过滤
        )

        logs = log_collector.get_logs(query)

        # 过滤错误日志
        error_logs = [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "level": log.level.value,
                "source": log.source.value,
                "message": log.message,
                "module": log.module,
                "metadata": log.metadata,
            }
            for log in logs
            if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]

        return error_logs[:limit]

    except Exception as e:
        logger.error(f"获取错误日志失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取错误日志失败: {str(e)}"
        ) from e


@router.get("/modules")
async def get_log_modules():
    """获取所有日志模块"""
    try:
        # 获取最近的日志
        query = LogQuery(limit=1000)
        logs = log_collector.get_logs(query)

        # 收集所有模块
        modules = set()
        for log in logs:
            if log.module:
                modules.add(log.module)

        return {"modules": sorted(modules)}

    except Exception as e:
        logger.error(f"获取日志模块失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取日志模块失败: {str(e)}"
        ) from e


# ============================================================================
# 日志收集和摄取
# ============================================================================


@router.post("/ingest")
async def ingest_log(request: IngestLogRequest):
    """摄取日志"""
    try:
        await log_collector.parse_and_store(request.message, request.source)
        return {"status": "success", "message": "日志已摄取"}

    except Exception as e:
        logger.error(f"摄取日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"摄取日志失败: {str(e)}") from e


@router.post("/watch-file")
async def watch_log_file(request: LogFileWatchRequest):
    """监视日志文件"""
    try:
        await log_collector.watch_file(request.file_path, request.source)
        return {"status": "success", "message": f"开始监视文件: {request.file_path}"}

    except Exception as e:
        logger.error(f"监视日志文件失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"监视日志文件失败: {str(e)}"
        ) from e


@router.delete("/watch-file/{file_path:path}")
async def stop_watch_log_file(file_path: str):
    """停止监视日志文件"""
    try:
        import urllib.parse

        # 解析文件路径
        decoded_path = urllib.parse.unquote(file_path)

        if decoded_path in log_collector._file_watchers:
            task = log_collector._file_watchers[decoded_path]
            task.cancel()
            del log_collector._file_watchers[decoded_path]
            return {"status": "success", "message": f"已停止监视文件: {decoded_path}"}
        else:
            raise HTTPException(status_code=404, detail="文件未在监视列表中")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止监视日志文件失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"停止监视日志文件失败: {str(e)}"
        ) from e


@router.get("/watched-files")
async def get_watched_files():
    """获取正在监视的文件列表"""
    try:
        import urllib.parse

        watched_files = []
        for file_path, task in log_collector._file_watchers.items():
            watched_files.append(
                {
                    "file_path": file_path,
                    "status": "running" if not task.done() else "stopped",
                    "encoded_path": urllib.parse.quote(file_path, safe=""),
                }
            )

        return {"watched_files": watched_files}

    except Exception as e:
        logger.error(f"获取监视文件列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取监视文件列表失败: {str(e)}"
        ) from e


# ============================================================================
# 日志收集器控制
# ============================================================================


@router.post("/collector/start")
async def start_log_collector():
    """启动日志收集器"""
    try:
        await log_collector.start_collection()
        return {"status": "success", "message": "日志收集器已启动"}

    except Exception as e:
        logger.error(f"启动日志收集器失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"启动日志收集器失败: {str(e)}"
        ) from e


@router.post("/collector/stop")
async def stop_log_collector():
    """停止日志收集器"""
    try:
        await log_collector.stop_collection()
        return {"status": "success", "message": "日志收集器已停止"}

    except Exception as e:
        logger.error(f"停止日志收集器失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"停止日志收集器失败: {str(e)}"
        ) from e


@router.get("/collector/status")
async def get_collector_status():
    """获取日志收集器状态"""
    try:
        return {
            "status": "success",
            "data": {
                "running": log_collector._running,
                "buffer_size": len(log_collector.log_buffer),
                "parsers_count": len(log_collector.parsers),
                "listeners_count": len(log_collector.listeners),
                "watched_files_count": len(log_collector._file_watchers),
                "max_buffer_size": log_collector.log_buffer.maxlen,
            },
        }

    except Exception as e:
        logger.error(f"获取收集器状态失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取收集器状态失败: {str(e)}"
        ) from e


# ============================================================================
# 测试和调试
# ============================================================================


@router.post("/test")
async def test_log_system():
    """测试日志系统"""
    try:
        import uuid

        # 创建测试日志
        test_logs = [
            {"message": "这是一条测试日志", "source": LogSource.APPLICATION},
            {"message": "ERROR: 测试错误日志", "source": LogSource.ERROR},
            {"message": "INFO: 应用程序启动成功", "source": LogSource.SYSTEM},
        ]

        results = []
        for log_data in test_logs:
            log_entry = LogEntry(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                source=log_data["source"],
                message=log_data["message"],
                module="test_module",
            )

            # 添加到缓冲区
            log_collector.log_buffer.append(log_entry)
            results.append(
                {
                    "id": log_entry.id,
                    "message": log_entry.message,
                    "source": log_entry.source.value,
                    "level": log_entry.level.value,
                    "timestamp": log_entry.timestamp.isoformat(),
                }
            )

        return {"status": "success", "message": "测试日志已创建", "logs": results}

    except Exception as e:
        logger.error(f"测试日志系统失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"测试日志系统失败: {str(e)}"
        ) from e


def setup_log_routes(app):
    """设置日志路由"""
    app.include_router(router)
    logger.info("日志路由已注册")
