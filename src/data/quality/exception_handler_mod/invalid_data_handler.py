"""
无效数据处理模块

负责处理无效数据，记录到质量日志供人工排查。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .exceptions import InvalidDataException


class InvalidDataHandler:
    """无效数据处理器"""

    def __init__(self, db_manager: Any, config: Dict[str, Any] = None):
        """
        初始化无效数据处理器

        Args:
            db_manager: 数据库管理器
            config: 配置参数
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 默认配置
        self.config = config or {
            "require_manual_review": True,
            "batch_size": 100,
            "max_retry_attempts": 3,
        }

    async def handle_invalid_data(
        self, table_name: str, invalid_records: List[Dict[str, Any]], error_type: str
    ) -> Dict[str, Any]:
        """
        处理无效数据

        Args:
            table_name: 表名
            invalid_records: 无效记录列表
            error_type: 错误类型

        Returns:
            Dict: 处理结果
        """
        try:
            logged_count = 0
            failed_count = 0
            batch_results = []

            # 分批处理记录
            batch_size = self.config.get("batch_size", 100)
            for i in range(0, len(invalid_records), batch_size):
                batch = invalid_records[i:i + batch_size]
                batch_result = await self._process_batch(
                    table_name, batch, error_type
                )
                batch_results.append(batch_result)
                logged_count += batch_result["logged_count"]
                failed_count += batch_result["failed_count"]

            # 汇总结果
            total_result = {
                "table_name": table_name,
                "error_type": error_type,
                "invalid_records_count": len(invalid_records),
                "logged_count": logged_count,
                "failed_count": failed_count,
                "success_rate": logged_count / len(invalid_records) if invalid_records else 0,
                "batch_count": len(batch_results),
                "requires_manual_review": self.config.get("require_manual_review", True),
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.warning(
                f"无效数据处理完成：表 {table_name}，错误类型 {error_type}，"
                f"成功记录 {logged_count}/{len(invalid_records)} 条（成功率：{total_result['success_rate']:.2%}）"
            )

            return total_result

        except Exception as e:
            self.logger.error(f"处理无效数据失败: {str(e)}")
            raise InvalidDataException(
                f"处理无效数据失败: {str(e)}",
                table_name=table_name
            )

    async def _process_batch(
        self, table_name: str, batch: List[Dict[str, Any]], error_type: str
    ) -> Dict[str, Any]:
        """
        处理一批无效数据

        Args:
            table_name: 表名
            batch: 批量记录
            error_type: 错误类型

        Returns:
            Dict: 批处理结果
        """
        logged_count = 0
        failed_count = 0

        try:
            from .quality_logger import QualityLogger

            logger = QualityLogger(self.db_manager)

            for record in batch:
                try:
                    # 写入数据质量日志表
                    await logger.create_quality_log(
                        table_name=table_name,
                        record_id=record.get("id"),
                        error_type=error_type,
                        error_data=record,
                        requires_manual_review=self.config.get("require_manual_review", True),
                    )
                    logged_count += 1

                except Exception as e:
                    self.logger.error(
                        f"记录无效数据失败（记录ID: {record.get('id')}）: {str(e)}"
                    )
                    failed_count += 1

            return {
                "batch_size": len(batch),
                "logged_count": logged_count,
                "failed_count": failed_count,
                "success_rate": logged_count / len(batch) if batch else 0,
            }

        except Exception as e:
            self.logger.error(f"批处理无效数据失败: {str(e)}")
            raise InvalidDataException(
                f"批处理无效数据失败: {str(e)}",
                table_name=table_name
            )

    async def validate_data_integrity(
        self, table_name: str, records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证数据完整性

        Args:
            table_name: 表名
            records: 待验证的记录列表

        Returns:
            Dict: 验证结果
        """
        try:
            validation_result = {
                "table_name": table_name,
                "total_records": len(records),
                "valid_records": 0,
                "invalid_records": 0,
                "validation_errors": {},
                "timestamp": datetime.now().isoformat(),
            }

            # 根据表名选择验证规则
            if table_name == "matches":
                validation_result = await self._validate_match_records(
                    records, validation_result
                )
            elif table_name == "odds":
                validation_result = await self._validate_odds_records(
                    records, validation_result
                )

            # 计算验证统计
            validation_result["validity_rate"] = (
                validation_result["valid_records"] / validation_result["total_records"]
                if validation_result["total_records"] > 0 else 0
            )

            self.logger.info(
                f"数据完整性验证完成：表 {table_name}，"
                f"有效记录 {validation_result['valid_records']}/{validation_result['total_records']} "
                f"（有效率：{validation_result['validity_rate']:.2%}）"
            )

            return validation_result

        except Exception as e:
            self.logger.error(f"验证数据完整性失败: {str(e)}")
            raise InvalidDataException(
                f"验证数据完整性失败: {str(e)}",
                table_name=table_name
            )

    async def _validate_match_records(
        self, records: List[Dict[str, Any]], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证比赛记录"""
        validation_errors = []

        for record in records:
            is_valid = True
            errors = []

            # 检查必需字段
            required_fields = ["home_team_id", "away_team_id", "match_time"]
            for field in required_fields:
                if record.get(field) is None:
                    is_valid = False
                    errors.append(f"Missing required field: {field}")

            # 检查比分合理性
            if record.get("match_status") == "finished":
                home_score = record.get("home_score")
                away_score = record.get("away_score")

                if home_score is not None and home_score < 0:
                    is_valid = False
                    errors.append("Invalid home score (negative value)")

                if away_score is not None and away_score < 0:
                    is_valid = False
                    errors.append("Invalid away score (negative value)")

                # 检查比分是否过大
                max_reasonable_score = 99
                if (home_score and home_score > max_reasonable_score or
                    away_score and away_score > max_reasonable_score):
                    is_valid = False
                    errors.append(f"Score exceeds reasonable limit ({max_reasonable_score})")

            # 记录验证结果
            if is_valid:
                result["valid_records"] += 1
            else:
                result["invalid_records"] += 1
                validation_errors.append({
                    "record_id": record.get("id"),
                    "errors": errors,
                })

        result["validation_errors"]["matches"] = validation_errors
        return result

    async def _validate_odds_records(
        self, records: List[Dict[str, Any]], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证赔率记录"""
        validation_errors = []

        for record in records:
            is_valid = True
            errors = []

            # 检查必需字段
            required_fields = ["match_id", "bookmaker"]
            for field in required_fields:
                if record.get(field) is None:
                    is_valid = False
                    errors.append(f"Missing required field: {field}")

            # 检查赔率值
            odds_fields = ["home_odds", "draw_odds", "away_odds"]
            for field in odds_fields:
                odds_value = record.get(field)
                if odds_value is not None:
                    if odds_value <= 1.0:
                        is_valid = False
                        errors.append(f"Invalid {field} (must be > 1.0)")
                    if odds_value > 10000:
                        is_valid = False
                        errors.append(f"Invalid {field} (exceeds maximum limit)")

            # 记录验证结果
            if is_valid:
                result["valid_records"] += 1
            else:
                result["invalid_records"] += 1
                validation_errors.append({
                    "record_id": record.get("id"),
                    "errors": errors,
                })

        result["validation_errors"]["odds"] = validation_errors
        return result

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            new_config: 新的配置参数
        """
        self.config.update(new_config)
        self.logger.info(f"无效数据处理器配置已更新: {new_config}")