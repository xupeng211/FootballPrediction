"""数据验证器 - 重写版本.

验证处理后的数据质量和完整性
Data Validator - Rewritten Version
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd


class DataValidator:
    """数据验证器 - 简化版本.

    提供数据质量和完整性验证功能
    """

    def __init__(self):
        """初始化验证器."""
        self.logger = logging.getLogger(f"processing.{self.__class__.__name__}")

        # 验证规则配置
        self.validation_rules = {
            "match_data": {
                "required_fields": ["match_id", "home_team", "away_team", "match_date"],
                "numeric_fields": ["home_score", "away_score"],
                "date_fields": ["match_date"],
                "string_fields": ["home_team", "away_team", "venue", "competition"],
            },
            "team_data": {
                "required_fields": ["team_id", "team_name"],
                "string_fields": ["team_name", "league", "country"],
            },
            "prediction_data": {
                "required_fields": ["match_id", "prediction_type", "confidence"],
                "numeric_fields": ["confidence"],
                "range_fields": {"confidence": {"min": 0.0, "max": 1.0}},
            },
        }

    async def validate_data(
        self, data: dict | list[dict], data_type: str = "match_data"
    ) -> dict[str, Any]:
        """验证数据."""
        try:
            if isinstance(data, dict):
                return await self._validate_single_record(data, data_type)
            elif isinstance(data, list):
                return await self._validate_multiple_records(data, data_type)
            else:
                return self._create_result(False, "不支持的数据格式", {})

        except Exception as e:
            self.logger.error(f"数据验证失败: {e}")
            return self._create_result(False, f"验证过程中发生错误: {str(e)}", {})

    async def _validate_single_record(
        self, record: dict[str, Any], data_type: str
    ) -> dict[str, Any]:
        """验证单条记录."""
        errors = []
        warnings = []
        validation_stats = {}

        rules = self.validation_rules.get(data_type, {})

        # 验证必需字段
        if "required_fields" in rules:
            missing_fields = await self._check_required_fields(
                record, rules["required_fields"]
            )
            if missing_fields:
                errors.extend([f"缺少必需字段: {', '.join(missing_fields)}"])

        # 验证数值字段
        if "numeric_fields" in rules:
            numeric_errors = await self._validate_numeric_fields(
                record, rules["numeric_fields"]
            )
            errors.extend(numeric_errors)

        # 验证日期字段
        if "date_fields" in rules:
            date_errors = await self._validate_date_fields(record, rules["date_fields"])
            errors.extend(date_errors)

        # 验证范围字段
        if "range_fields" in rules:
            range_errors = await self._validate_range_fields(
                record, rules["range_fields"]
            )
            errors.extend(range_errors)

        # 验证字符串字段
        if "string_fields" in rules:
            string_warnings = await self._validate_string_fields(
                record, rules["string_fields"]
            )
            warnings.extend(string_warnings)

        validation_stats = {
            "total_fields": len(record),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "validated_at": datetime.utcnow(),
        }

        is_valid = len(errors) == 0
        result_type = "success" if is_valid else "error"

        return {
            "is_valid": is_valid,
            "result_type": result_type,
            "errors": errors,
            "warnings": warnings,
            "validation_stats": validation_stats,
        }

    async def _validate_multiple_records(
        self, records: list[dict[str, Any]], data_type: str
    ) -> dict[str, Any]:
        """验证多条记录."""
        total_errors = []
        total_warnings = []
        valid_records = 0
        invalid_records = 0

        for i, record in enumerate(records):
            result = await self._validate_single_record(record, data_type)

            if result["is_valid"]:
                valid_records += 1
            else:
                invalid_records += 1

            # 添加记录标识到错误和警告
            record_errors = [f"记录{i + 1}: {error}" for error in result["errors"]]
            record_warnings = [
                f"记录{i + 1}: {warning}" for warning in result["warnings"]
            ]

            total_errors.extend(record_errors)
            total_warnings.extend(record_warnings)

        validation_stats = {
            "total_records": len(records),
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "success_rate": round(
                (valid_records / len(records) * 100) if records else 0, 2
            ),
            "total_errors": len(total_errors),
            "total_warnings": len(total_warnings),
            "validated_at": datetime.utcnow(),
        }

        is_valid = invalid_records == 0
        result_type = "success" if is_valid else "error"

        return {
            "is_valid": is_valid,
            "result_type": result_type,
            "errors": total_errors,
            "warnings": total_warnings,
            "validation_stats": validation_stats,
        }

    async def _check_required_fields(
        self, record: dict[str, Any], required_fields: list[str]
    ) -> list[str]:
        """检查必需字段."""
        missing_fields = []
        for field in required_fields:
            if field not in record or record[field] is None or record[field] == "":
                missing_fields.append(field)
        return missing_fields

    async def _validate_numeric_fields(
        self, record: dict[str, Any], numeric_fields: list[str]
    ) -> list[str]:
        """验证数值字段."""
        errors = []
        for field in numeric_fields:
            if field in record and record[field] is not None:
                try:
                    float(record[field])
                except (ValueError, TypeError):
                    errors.append(f"字段 {field} 不是有效的数值: {record[field]}")
        return errors

    async def _validate_date_fields(
        self, record: dict[str, Any], date_fields: list[str]
    ) -> list[str]:
        """验证日期字段."""
        errors = []
        for field in date_fields:
            if field in record and record[field] is not None:
                if not isinstance(record[field], datetime):
                    try:
                        # 尝试解析字符串日期
                        if isinstance(record[field], str):
                            datetime.strptime(record[field], "%Y-%m-%d")
                        else:
                            errors.append(
                                f"字段 {field} 不是有效的日期格式: {record[field]}"
                            )
                    except ValueError:
                        errors.append(f"字段 {field} 日期格式无效: {record[field]}")
        return errors

    async def _validate_range_fields(
        self, record: dict[str, Any], range_fields: dict[str, dict]
    ) -> list[str]:
        """验证字段值范围."""
        errors = []
        for field, range_config in range_fields.items():
            if field in record and record[field] is not None:
                try:
                    value = float(record[field])
                    min_val = range_config.get("min", float("-inf"))
                    max_val = range_config.get("max", float("inf"))

                    if value < min_val or value > max_val:
                        errors.append(
                            f"字段 {field} 值 {value} 超出范围 [{min_val}, {max_val}]"
                        )
                except (ValueError, TypeError):
                    errors.append(f"字段 {field} 不是有效数值: {record[field]}")
        return errors

    async def _validate_string_fields(
        self, record: dict[str, Any], string_fields: list[str]
    ) -> list[str]:
        """验证字符串字段."""
        warnings = []
        for field in string_fields:
            if field in record and record[field] is not None:
                str_value = str(record[field])
                if len(str_value.strip()) == 0:
                    warnings.append(f"字段 {field} 为空字符串")
                elif len(str_value) > 255:
                    warnings.append(f"字段 {field} 长度超过255字符")
        return warnings

    def _create_result(
        self, is_valid: bool, message: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """创建验证结果."""
        return {
            "is_valid": is_valid,
            "result_type": "success" if is_valid else "error",
            "message": message,
            "data": data,
            "validated_at": datetime.utcnow(),
        }

    async def validate_dataframe(
        self, df: pd.DataFrame, data_type: str = "match_data"
    ) -> dict[str, Any]:
        """验证DataFrame数据."""
        try:
            # 转换为字典列表
            records = df.to_dict("records")
            return await self._validate_multiple_records(records, data_type)

        except Exception as e:
            self.logger.error(f"DataFrame验证失败: {e}")
            return self._create_result(False, f"DataFrame验证失败: {str(e)}", {})

    async def validate_data_quality(self, data: dict | list[dict]) -> dict[str, Any]:
        """评估数据质量."""
        try:
            if isinstance(data, dict):
                data = [data]

            quality_metrics = {
                "completeness": await self._calculate_completeness(data),
                "consistency": await self._calculate_consistency(data),
                "accuracy": await self._calculate_accuracy(data),
                "timeliness": await self._calculate_timeliness(data),
            }

            overall_quality = sum(quality_metrics.values()) / len(quality_metrics)

            return {
                "overall_quality_score": round(overall_quality, 2),
                "quality_metrics": quality_metrics,
                "quality_grade": self._get_quality_grade(overall_quality),
                "evaluated_at": datetime.utcnow(),
            }

        except Exception as e:
            self.logger.error(f"数据质量评估失败: {e}")
            return {
                "overall_quality_score": 0.0,
                "quality_grade": "F",
                "error": str(e),
                "evaluated_at": datetime.utcnow(),
            }

    async def _calculate_completeness(self, data: list[dict]) -> float:
        """计算完整性得分."""
        if not data:
            return 0.0

        total_fields = sum(len(record) for record in data)
        non_null_fields = sum(
            sum(1 for value in record.values() if value is not None and value != "")
            for record in data
        )

        return (non_null_fields / total_fields * 100) if total_fields > 0 else 0.0

    async def _calculate_consistency(self, data: list[dict]) -> float:
        """计算一致性得分."""
        if not data:
            return 0.0

        # 检查字段一致性
        first_record_fields = set(data[0].keys())
        consistent_records = 0

        for record in data:
            if set(record.keys()) == first_record_fields:
                consistent_records += 1

        return (consistent_records / len(data) * 100) if data else 0.0

    async def _calculate_accuracy(self, data: list[dict]) -> float:
        """计算准确性得分 (简化版本)."""
        # 这里可以实现更复杂的准确性检查逻辑
        # 现在返回基于数据格式的准确性评估
        if not data:
            return 0.0

        format_issues = 0
        total_checks = 0

        for record in data:
            for _key, value in record.items():
                total_checks += 1
                if value is None or value == "":
                    format_issues += 1

        return (
            ((total_checks - format_issues) / total_checks * 100)
            if total_checks > 0
            else 0.0
        )

    async def _calculate_timeliness(self, data: list[dict]) -> float:
        """计算时效性得分."""
        if not data:
            return 0.0

        # 假设数据中有时间戳字段
        timely_records = 0
        total_records_with_timestamp = 0

        for record in data:
            timestamp_fields = ["created_at", "updated_at", "timestamp", "date"]
            for field in timestamp_fields:
                if field in record and record[field] is not None:
                    total_records_with_timestamp += 1
                    try:
                        if isinstance(record[field], str):
                            timestamp = datetime.strptime(
                                record[field], "%Y-%m-%d %H:%M:%S"
                            )
                        else:
                            timestamp = record[field]

                        # 假设30天内的数据是及时的
                        if datetime.utcnow() - timestamp <= timedelta(days=30):
                            timely_records += 1
                        break
                    except (ValueError, TypeError):
                        continue

        return (
            (timely_records / total_records_with_timestamp * 100)
            if total_records_with_timestamp > 0
            else 80.0
        )

    def _get_quality_grade(self, score: float) -> str:
        """获取质量等级."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
