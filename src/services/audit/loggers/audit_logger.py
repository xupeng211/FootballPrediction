"""

"""




    """审计状态枚举（临时定义）"""


    """审计日志记录器"""

        """初始化日志记录器"""

        """


        """








        """


        """









审计日志记录器
负责将审计事件记录到数据库。
    AuditAction,
    AuditLog,
    AuditSeverity,
)
class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger(f"audit.{self.__class__.__name__}")
    async def log_operation(
        self,
        action: AuditAction,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        记录操作到审计日志
        Args:
            action: 操作类型
            table_name: 表名
            record_id: 记录ID
            old_values: 旧值
            new_values: 新值
            severity: 严重程度
            status: 状态
            error_message: 错误信息
            execution_time_ms: 执行时间（毫秒）
            context: 操作上下文
        Returns:
            int: 审计日志ID
        session_obj = None
        try:
            # 1. 获取上下文信息
            sanitizer = DataSanitizer()
            context_dict = context or {}
            # 2. 分析操作属性
            is_sensitive = sanitizer.is_sensitive_table(table_name) if table_name else False
            is_high_risk = sanitizer.is_high_risk_action(action)
            # 3. 处理敏感数据
            if old_values:
                old_values = sanitizer.sanitize_data(old_values)
            if new_values:
                new_values = sanitizer.sanitize_data(new_values)
            # 4. 创建审计日志条目
            audit_entry = AuditLog(
                user_id=context_dict.get("user_id"),
                username=context_dict.get("username"),
                user_role=context_dict.get("user_role"),
                session_id=context_dict.get("session_id"),
                ip_address=context_dict.get("ip_address"),
                user_agent=context_dict.get("user_agent"),
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                severity=severity,
                status=status,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
                is_sensitive=is_sensitive,
                is_high_risk=is_high_risk,
                timestamp=datetime.utcnow(),
            )
            # 5. 保存到数据库
            async with get_async_session() as session:
                session.add(audit_entry)
                await session.commit()
                await session.refresh(audit_entry)
                log_id = audit_entry.id
            # 6. 记录成功日志
            self.logger.info(
                "审计日志已记录",
                extra={
                    "operation": "audit_log",
                    "log_id": log_id,
                    "action": action.value,
                    "table_name": table_name,
                    "user_id": context_dict.get("user_id"),
                },
            )
            return log_id
        except Exception as e:
            self.logger.error(f"记录审计日志失败: {e}", exc_info=True)
            return None
    async def log_batch_operations(
        self,
        operations: list[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> list[int]:
        批量记录审计操作
        Args:
            operations: 操作列表
            context: 操作上下文
        Returns:
            list[int]: 审计日志ID列表
        log_ids = []
        async with get_async_session() as session:
            try:
                # 开始事务
                await session.begin()
                # 批量创建审计日志
                audit_logs = []
                for op in operations:
                    audit_log = AuditLog(**op)
                    audit_logs.append(audit_log)
                # 批量保存
                session.add_all(audit_logs)
                await session.flush()
                # 获取ID
                log_ids = [log.id for log in audit_logs]
                # 提交事务
                await session.commit()
                self.logger.info(
                    "批量审计日志已记录",
                    extra={
                        "operation": "batch_audit_log",
                        "count": len(operations),
                        "log_ids": log_ids,
                    },
                )
                return log_ids
            except Exception as e:
                await session.rollback()
                self.logger.error(f"批量记录审计日志失败: {e}", exc_info=True)
                return []