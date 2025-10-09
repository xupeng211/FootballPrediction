"""
            from sqlalchemy import delete

数据质量日志模块

负责记录和管理数据质量相关的日志。
"""





class QualityLogger:
    """数据质量日志记录器"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化质量日志记录器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

    async def create_quality_log(
        self,
        table_name: str,
        record_id: Optional[int],
        error_type: str,
        error_data: Dict[str, Any],
        requires_manual_review: bool,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """
        创建数据质量日志记录

        Args:
            table_name: 表名
            record_id: 记录ID
            error_type: 错误类型
            error_data: 错误数据
            requires_manual_review: 是否需要人工审核
            session: 数据库会话（可选）
        """
        try:
            quality_log = DataQualityLog(
                table_name=table_name,
                record_id=record_id,
                error_type=error_type,
                error_data=error_data,
                requires_manual_review=requires_manual_review,
                status="logged",
                detected_at=datetime.now(),
            )

            if session:
                # 使用提供的会话
                session.add(quality_log)
                await session.commit()
            else:
                # 创建新会话
                async with self.db_manager.get_async_session() as session:
                    session.add(quality_log)
                    await session.commit()

        except Exception as e:
            self.logger.error(f"创建质量日志记录失败: {str(e)}")
            if session:
                await session.rollback()
            raise QualityLogException(
                f"创建质量日志记录失败: {str(e)}",
                log_data={
                    "table_name": table_name,
                    "error_type": error_type,
                    "record_id": record_id,
                },
            )

    async def log_missing_value_handling(
        self, table_name: str, missing_counts: Dict[str, int], config: Dict[str, Any]
    ) -> None:
        """记录缺失值处理日志"""
        try:
            error_data = {
                "filled_columns": missing_counts,
                "total_filled": sum(missing_counts.values()),
                "strategy": config.get("strategy", "unknown"),
                "lookback_days": config.get("lookback_days", 0),
                "min_sample_size": config.get("min_sample_size", 0),
            }

            await self.create_quality_log(
                table_name=table_name,
                record_id=None,
                error_type="missing_values_filled",
                error_data=error_data,
                requires_manual_review=False,
            )

        except Exception as e:
            self.logger.error(f"记录缺失值处理日志失败: {str(e)}")

    async def log_suspicious_odds(
        self, suspicious_details: List[Dict[str, Any]]
    ) -> None:
        """记录可疑赔率日志"""
        try:
            async with self.db_manager.get_async_session() as session:
                for detail in suspicious_details:
                    error_data = {
                        "match_id": detail.get("match_id"),
                        "bookmaker": detail.get("bookmaker"),
                        "reason": detail.get("reason"),
                        "odds": detail.get("odds"),
                        "detected_at": datetime.now().isoformat(),
                    }

                    await self.create_quality_log(
                        table_name="odds",
                        record_id=detail.get("match_id"),
                        error_type="suspicious_odds",
                        error_data=error_data,
                        requires_manual_review=False,
                        session=session,
                    )

        except Exception as e:
            self.logger.error(f"记录可疑赔率日志失败: {str(e)}")

    async def log_exception(
        self, operation: str, table_name: str, error_message: str
    ) -> None:
        """记录异常处理日志"""
        try:
            error_data = {
                "operation": operation,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
            }

            await self.create_quality_log(
                table_name=table_name,
                record_id=None,
                error_type=f"exception_handling_{operation}",
                error_data=error_data,
                requires_manual_review=True,
            )

        except Exception as e:
            self.logger.error(f"记录异常处理日志失败: {str(e)}")

    async def log_data_consistency_issue(
        self, table_name: str, conflict_data: Dict[str, Any]
    ) -> None:
        """记录数据一致性问题"""
        try:
            error_data = {
                "conflict_type": conflict_data.get("conflict_type"),
                "conflicting_records": conflict_data.get("records"),
                "resolution_suggestion": conflict_data.get("suggestion"),
                "detected_at": datetime.now().isoformat(),
            }

            await self.create_quality_log(
                table_name=table_name,
                record_id=conflict_data.get("record_id"),
                error_type="data_consistency_issue",
                error_data=error_data,
                requires_manual_review=True,
            )

        except Exception as e:
            self.logger.error(f"记录数据一致性问题日志失败: {str(e)}")

    async def get_pending_reviews(
        self, table_name: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取待审核的质量问题

        Args:
            table_name: 表名过滤（可选）
            limit: 返回记录数限制

        Returns:
            List[Dict]: 待审核的问题列表
        """
        # Import moved to top

        try: desc

            async with self.db_manager.get_async_session() as session:
                query = (
                    select(DataQualityLog)
                    .where(DataQualityLog.requires_manual_review is True)
                    .order_by(desc(DataQualityLog.detected_at))
                )

                if table_name:
                    query = query.where(DataQualityLog.table_name == table_name)

                query = query.limit(limit)

                result = await session.execute(query)
                logs = result.scalars().all()

                return [
                    {
                        "id": log.id,
                        "table_name": log.table_name,
                        "record_id": log.record_id,
                        "error_type": log.error_type,
                        "error_data": log.error_data,
                        "status": log.status,
                        "detected_at": log.detected_at.isoformat(),
                    }
                    for log in logs
                ]

        except Exception as e:
            self.logger.error(f"获取待审核问题失败: {str(e)}")
            raise QualityLogException(
                f"获取待审核问题失败: {str(e)}",
                log_data={"table_name": table_name, "limit": limit},
            )

    async def mark_review_completed(
        self, log_id: int, reviewer: str, notes: Optional[str] = None
    ) -> None:
        """
        标记审核完成

        Args:
            log_id: 日志ID
            reviewer: 审核人
            notes: 审核备注
        """
        # Import moved to top

        try: update

            async with self.db_manager.get_async_session() as session:
                # 更新日志状态
                update_stmt = (
                    update(DataQualityLog)
                    .where(DataQualityLog.id == log_id)
                    .values(
                        status="reviewed",
                        reviewed_by=reviewer,
                        reviewed_at=datetime.now(),
                        review_notes=notes,
                    )
                )
                await session.execute(update_stmt)
                await session.commit()

                self.logger.info(f"质量日志 {log_id} 已由 {reviewer} 审核完成")

        except Exception as e:
            self.logger.error(f"标记审核完成失败: {str(e)}")
            raise QualityLogException(
                f"标记审核完成失败: {str(e)}",
                log_data={"log_id": log_id, "reviewer": reviewer},
            )

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """
        清理旧的质量日志

        Args:
            days_to_keep: 保留天数

        Returns:
            Dict: 清理结果
        """
        try:

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            async with self.db_manager.get_async_session() as session:
                # 删除旧的已审核日志
                delete_stmt = delete(DataQualityLog).where(
                    DataQualityLog.detected_at < cutoff_date,
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",)
                    DataQualityLog.status == "reviewed",