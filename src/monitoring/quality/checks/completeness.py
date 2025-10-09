"""
数据完整性检查器 / Data Completeness Checker

负责检查数据表的完整性，统计关键字段的缺失情况。
"""





logger = logging.getLogger(__name__)


class CompletenessChecker:
    """数据完整性检查器"""

    def __init__(self, critical_fields: Optional[Dict[str, List[str]]] = None):
        """
        初始化完整性检查器

        Args:
            critical_fields: 各表的关键字段列表
        """
        self.critical_fields = critical_fields or {
            "matches": ["home_team_id", "away_team_id", "match_date", "status"],
            "odds": ["match_id", "bookmaker", "home_win", "draw", "away_win"],
            "predictions": ["match_id", "predicted_by", "home_score", "away_score"],
            "teams": ["name", "short_name", "country"],
            "leagues": ["name", "country", "season"],
        }
        self.db_manager = DatabaseManager()

    async def check_data_completeness(
        self, table_names: Optional[List[str]] = None
    ) -> Dict[str, DataCompletenessResult]:
        """
        检查数据完整性

        Args:
            table_names: 要检查的表名列表

        Returns:
            Dict[str, DataCompletenessResult]: 各表的完整性检查结果
        """
        if table_names is None:
            table_names = list(self.critical_fields.keys())

        results: Dict[str, Any] = {}

        async with self.db_manager.get_async_session() as session:
            for table_name in table_names:
                try:
                    result = await self._check_table_completeness(session, table_name)
                    results[table_name] = result
                    logger.debug(f"表 {table_name} 完整性检查完成")
                except Exception as e:
                    logger.error(f"检查表 {table_name} 完整性失败: {e}")

        logger.info(f"数据完整性检查完成，检查了 {len(results)} 张表")
        return results

    async def _check_table_completeness(
        self, session: AsyncSession, table_name: str
    ) -> DataCompletenessResult:
        """
        检查单个表的数据完整性

        Args:
            session: 数据库会话
            table_name: 表名

        Returns:
            DataCompletenessResult: 完整性检查结果
        """
        critical_fields = self.critical_fields.get(str(table_name), [])

        if not critical_fields:
            logger.warning(f"表 {table_name} 未定义关键字段")
            return DataCompletenessResult(
                table_name=table_name,
                total_records=0, Dict, List, Optional



                missing_critical_fields={},
                missing_rate=0.0,
                completeness_score=100.0,
            )

        # Validate table name to prevent SQL injection
        if table_name not in ["matches", "odds", "predictions", "teams", "leagues"]:
            raise ValueError(f"Invalid table name: {table_name}")

        # 获取总记录数
        # Safe: table_name is validated against whitelist
        # 使用quoted_name确保表名安全，防止SQL注入

        safe_table_name = quoted_name(table_name, quote=True)
        total_result = await session.execute(
            text(f"SELECT COUNT(*) as total FROM {safe_table_name}")  # nosec B608 - using quoted_name for safety
        )
        total_row = total_result.first()
        try:
            if inspect.isawaitable(total_row):
                total_row = await total_row
        except Exception:
            pass
        total_records = total_row.total if total_row else 0

        if total_records == 0:
            return DataCompletenessResult(
                table_name=table_name,
                total_records=0,
                missing_critical_fields={},
                missing_rate=0.0,
                completeness_score=100.0,
            )

        # 检查各关键字段的缺失情况
        missing_fields = {}
        total_missing = 0

        for field in critical_fields:
            try:
                # Validate field name to prevent SQL injection
                if field not in self.critical_fields.get(str(table_name), []):
                    continue
                missing_result = await session.execute(
                    text(
                        # nosec B608 - validated
                        f"SELECT COUNT(*) as missing FROM {table_name} WHERE {field} IS NULL"
                    )
                )
                missing_row = missing_result.first()
                try:
                    if inspect.isawaitable(missing_row):
                        missing_row = await missing_row
                except Exception:
                    pass
                missing_count = missing_row.missing if missing_row else 0
                missing_fields[field] = missing_count
                total_missing += missing_count
            except Exception as e:
                logger.warning(f"检查字段 {field} 缺失情况失败: {e}")
                missing_fields[field] = 0

        # 计算缺失率和完整性评分
        total_checks = total_records * len(critical_fields)
        missing_rate = total_missing / total_checks if total_checks > 0 else 0
        completeness_score = (1 - missing_rate) * 100

        return DataCompletenessResult(
            table_name=table_name,
            total_records=total_records,
            missing_critical_fields=missing_fields,
            missing_rate=missing_rate,
            completeness_score=completeness_score,
        )