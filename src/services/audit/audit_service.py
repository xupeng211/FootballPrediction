"""

"""





    """

    """

        """初始化审计服务"""


        """


        """


        """获取审计摘要"""

        """获取用户活动记录"""

        """检测异常活动"""

        """获取操作统计"""


        """生成摘要报告"""

        """生成详细报告"""

        """生成异常报告"""


        """


        """






        """


        """






        """对敏感数据进行哈希处理（兼容性方法）"""

        """对敏感数据进行哈希处理（兼容性方法）"""

        """清理数据中的敏感信息（兼容性方法）"""

        """检查是否为敏感数据（兼容性方法）"""
审计服务主类
整合所有审计功能模块。
    AuditAction,
    AuditLog,
    AuditLogSummary,
    AuditSeverity,
)
class AuditService:
    审计服务主类
    整合审计日志记录、数据分析、报告生成等功能。
    def __init__(self):
        self.logger = logging.getLogger(f"audit.{self.__class__.__name__}")
        self.sanitizer = DataSanitizer()
        self.audit_logger = AuditLogger()
        self.analyzer = AuditAnalyzer()
        self.report_generator = AuditReportGenerator()
    # ========== 日志记录 ==========
    async def log_operation(
        self,
        action: AuditAction,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[int]:
        记录审计操作
        Args:
            action: 操作类型
            table_name: 表名
            record_id: 记录ID
            old_values: 旧值
            new_values: 新值
            severity: 严重程度
            context: 操作上下文
        Returns:
            int: 审计日志ID
        return await self.audit_logger.log_operation(
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            severity=severity,
            context=context or audit_context.get(),
            **kwargs,
        )
    # ========== 数据分析 ==========
    async def get_audit_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> Optional[AuditLogSummary]:
        return await self.analyzer.get_audit_summary(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            table_name=table_name,
        )
    async def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        return await self.analyzer.get_user_activity(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    async def detect_anomalies(
        self,
        hours: int = 24,
        failed_threshold: int = 10,
        high_risk_threshold: int = 5,
    ) -> List[Dict[str, Any]]:
        return await self.analyzer.detect_anomalies(
            hours=hours,
            failed_threshold=failed_threshold,
            high_risk_threshold=high_risk_threshold,
        )
    async def get_operation_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return await self.analyzer.get_operation_statistics(
            start_date=start_date,
            end_date=end_date,
        )
    # ========== 报告生成 ==========
    def generate_summary_report(
        self,
        summary: AuditLogSummary,
        format: str = "json",
    ) -> Union[str, bytes]:
        return self.report_generator.generate_summary_report(
            summary=summary,
            format=format,
        )
    def generate_detailed_report(
        self,
        audit_logs: List[AuditLog],
        format: str = "json",
    ) -> Union[str, bytes]:
        return self.report_generator.generate_detailed_report(
            audit_logs=audit_logs,
            format=format,
        )
    def generate_anomaly_report(
        self,
        anomalies: List[Dict[str, Any]],
        format: str = "json",
    ) -> Union[str, bytes]:
        return self.report_generator.generate_anomaly_report(
            anomalies=anomalies,
            format=format,
        )
    # ========== 便捷方法 ==========
    async def get_recent_activity(
        self,
        hours: int = 24,
        limit: int = 100,
        action: Optional[AuditAction] = None,
        table_name: Optional[str] = None,
    ) -> List[AuditLog]:
        获取最近的活动记录
        Args:
            hours: 最近多少小时
            limit: 返回记录数
            action: 过滤操作类型
            table_name: 过滤表名
        Returns:
            List[AuditLog]: 审计日志列表
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            async with get_async_session() as session:
                query = (
                    session.query(AuditLog)
                    .filter(AuditLog.timestamp >= start_time)
                    .order_by(desc(AuditLog.timestamp))
                    .limit(limit)
                )
                if action:
                    query = query.filter(AuditLog.action == action)
                if table_name:
                    query = query.filter(AuditLog.table_name == table_name)
                result = await session.execute(query)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"获取最近活动失败: {e}", exc_info=True)
            return []
    async def search_audit_logs(
        self,
        keyword: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        搜索审计日志
        Args:
            keyword: 搜索关键词
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回记录数
        Returns:
            List[AuditLog]: 审计日志列表
        try:
            async with get_async_session() as session:
                query = (
                    session.query(AuditLog)
                    .filter(
                        or_(
                            AuditLog.username.ilike(f"%{keyword}%"),
                            AuditLog.table_name.ilike(f"%{keyword}%"),
                            AuditLog.error_message.ilike(f"%{keyword}%"),
                        )
                    )
                    .order_by(desc(AuditLog.timestamp))
                    .limit(limit)
                )
                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)
                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)
                result = await session.execute(query)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"搜索审计日志失败: {e}", exc_info=True)
            return []
    # ========== 兼容性方法（保持向后兼容） ==========
    def _hash_sensitive_value(self, value: str) -> str:
        return self.sanitizer.hash_sensitive_value(value)
    def _hash_sensitive_data(self, data: str) -> str:
        return self.sanitizer.hash_sensitive_value(data)
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.sanitizer.sanitize_data(data)
    def _is_sensitive_data(self, table_name: Optional[str], column_name: Optional[str]) -> bool:
        if table_name and self.sanitizer.is_sensitive_table(table_name):
            return True
        if column_name and self.sanitizer.is_sensitive_column(column_name):
            return True
        return False