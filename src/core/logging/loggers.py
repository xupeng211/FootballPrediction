"""
结构化日志器
Structured Loggers
"""




class StructuredLogger:
    """结构化日志器"""

    def __init__(
        self,
        name: str,
        category: LogCategory = LogCategory.API,
        level: LogLevel = LogLevel.INFO,
        enable_json: bool = True,
        enable_console: bool = True,
        enable_file: bool = True,
        log_file: Optional[str] = None,
    ):
        self.name = name
        self.category = category
        self.logger = logging.getLogger(f"{category.value}.{name}")
        self.logger.setLevel(getattr(logging, level.value))

        # 创建处理器管理器
        self.handler_manager = LogHandlerManager(name, enable_json)

        # 添加处理器
        if enable_console:
            console_handler = self.handler_manager.create_console_handler()
            self.logger.addHandler(console_handler)

        if enable_file:
            file_handler = self.handler_manager.create_file_handler(log_file)
            self.logger.addHandler(file_handler)

        # 防止重复日志
        self.logger.propagate = False

    def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[bool] = None,
    ):
        """记录日志"""
        # 添加标准字段
        log_extra = {
            "category": self.category.value,
            "service": "football-prediction",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": os.getenv("APP_VERSION", "1.0.0"),
        }

        # 添加额外字段
        if extra:
            log_extra.update(extra)

        # 记录日志
        getattr(self.logger, level.value.lower())(
            message, extra=log_extra, exc_info=exc_info
        )

    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(LogLevel.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(LogLevel.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(LogLevel.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log(LogLevel.ERROR, message, kwargs, exc_info=True)

    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log(LogLevel.CRITICAL, message, kwargs, exc_info=True)

    # 特殊日志方法
    def audit(self, action: str, user_id: Optional[str] = None, **kwargs):
        """审计日志"""
        self.info(
            f"AUDIT: {action}",
            audit_action=action,
            user_id=user_id,
            audit_timestamp=datetime.now().isoformat(),
            **kwargs,
        )

    def performance(
        self, operation: str, duration: float, success: bool = True, **kwargs
    ):
        """性能日志"""
        self.info(
            f"PERFORMANCE: {operation}",
            operation=operation,
            duration_ms=duration * 1000,
            success=success,
            **kwargs,
        )

    def api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None,
        **kwargs,
    ):
        """API请求日志"""
        self.info(
            f"API: {method} {path} - {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration * 1000,
            user_id=user_id,
            **kwargs,
        )

    def prediction(
        self,
        match_id: int,
        model_version: str,
        prediction: str,
        confidence: float,
        success: bool = True,
        **kwargs,
    ):
        """预测日志"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"PREDICTION: Match {match_id} - {prediction} (confidence: {confidence:.3f})"

        self._log(
            level,
            message,
            {
                "match_id": match_id,
                "model_version": model_version,
                "prediction": prediction,
                "confidence": confidence,
                "success": success,
                **kwargs,
            },
        )

    def data_collection(
        self,
        source: str,
        data_type: str,
        records_count: int,
        success: bool = True,
        **kwargs,
    ):
        """数据收集日志"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"DATA COLLECTION: {source} - {data_type} ({records_count} records)"

        self._log(
            level,
            message,
            {
                "source": source,
                "data_type": data_type,
                "records_count": records_count,
                "success": success,
                **kwargs,
            },
        )

    def cache_operation(
        self,
        operation: str,
        key: str,
        hit: Optional[bool] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ):
        """缓存操作日志"""
        message = f"CACHE {operation.upper()}: {key}"
        extra = {"operation": operation, "key": key}

        if hit is not None:
            extra["hit"] = str(hit)
            message += f" - {'HIT' if hit else 'MISS'}"

        if duration_ms is not None:
            extra["duration_ms"] = str(duration_ms)

        extra.update(kwargs)

        self.debug(message, **extra)

    def security_event(
        self,
        event_type: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ):
        """安全事件日志"""
        self.warning(
            f"SECURITY: {event_type}",
            security_event=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address, Dict, Optional


            **kwargs,
        )