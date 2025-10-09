"""
数据验证模块
Data Validation Module

负责验证采集的数据的质量和完整性。
"""



logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """数据验证错误"""
    pass


class DataValidator:
    """数据验证器"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DataValidator")

    def validate_fixtures_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证赛程数据"""
        errors = []
        warnings = []
        valid_count = 0

        required_fields = ["id", "home_team", "away_team", "date", "league"]

        for item in data:
            if not isinstance(item, dict):
                errors.append(f"无效的数据格式: {type(item)}")
                continue

            # 检查必需字段
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                errors.append(f"比赛 {item.get('id', 'unknown')} 缺少字段: {missing_fields}")
                continue

            # 检查日期格式
            try:
                if isinstance(item["date"], str):
                    datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                warnings.append(f"比赛 {item['id']} 日期格式无效: {item['date']}")

            valid_count += 1

        return {
            "valid": valid_count,
            "errors": len(errors),
            "warnings": len(warnings),
            "error_details": errors[:10],  # 只保留前10个错误
            "warning_details": warnings[:10],
        }

    def validate_odds_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证赔率数据"""
        errors = []
        warnings = []
        valid_count = 0

        required_fields = ["match_id", "bookmaker", "odds"]

        for item in data:
            if not isinstance(item, dict):
                errors.append(f"无效的数据格式: {type(item)}")
                continue

            # 检查必需字段
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                errors.append(f"赔率数据缺少字段: {missing_fields}")
                continue

            # 检查赔率值
            odds = item.get("odds", {})
            if not isinstance(odds, dict):
                errors.append(f"赔率格式无效: {type(odds)}")
                continue

            # 检查赔率是否为正数
            for market, values in odds.items():
                if isinstance(values, (int, float)) and values <= 0:
                    warnings.append(f"赔率值无效: {market} = {values}")

            valid_count += 1

        return {
            "valid": valid_count,
            "errors": len(errors),
            "warnings": len(warnings),
            "error_details": errors[:10],
            "warning_details": warnings[:10],
        }

    def validate_scores_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证比分数据"""
        errors = []
        warnings = []
        valid_count = 0

        required_fields = ["match_id", "status"]

        for item in data:
            if not isinstance(item, dict):
                errors.append(f"无效的数据格式: {type(item)}")
                continue

            # 检查必需字段
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                errors.append(f"比分数据缺少字段: {missing_fields}")
                continue

            # 检查状态值
            valid_statuses = ["NS", "LIVE", "HT", "FT", "AET", "PST", "CANC", "ABD", "INT", "PST", "WO", "AWD"]
            if item["status"] not in valid_statuses:
                warnings.append(f"未知的比赛状态: {item['status']}")

            # 检查比分格式
            if "score" in item:
                score = item["score"]
                if not isinstance(score, dict):
                    errors.append(f"比分格式无效: {type(score)}")
                elif "home" not in score or "away" not in score:
                    errors.append("比分缺少主客队得分")

            valid_count += 1

        return {
            "valid": valid_count,
            "errors": len(errors),
            "warnings": len(warnings),
            "error_details": errors[:10],
            "warning_details": warnings[:10],
        }


@app.task(base=DataCollectionTask, bind=True)
def validate_collected_data(
    self,
    data_type: str,
    data: Union[List[Dict[str, Any]], Dict[str, Any]],
    validation_rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    验证采集的数据

    Args:
        data_type: 数据类型 (fixtures, odds, scores, historical)
        data: 要验证的数据
        validation_rules: 自定义验证规则

    Returns:
        验证结果字典
    """
    logger.info(f"开始验证 {data_type} 数据")

    try:
        validator = DataValidator()



        # 根据数据类型选择验证器
        if data_type == "fixtures":
            if not isinstance(data, list):
                raise DataValidationError("赛程数据必须是列表格式")
            result = validator.validate_fixtures_data(data)

        elif data_type == "odds":
            if not isinstance(data, list):
                raise DataValidationError("赔率数据必须是列表格式")
            result = validator.validate_odds_data(data)

        elif data_type == "scores":
            if not isinstance(data, list):
                raise DataValidationError("比分数据必须是列表格式")
            result = validator.validate_scores_data(data)

        elif data_type == "historical":
            # 历史数据验证（简化版）
            if not isinstance(data, (list, dict)):
                raise DataValidationError("历史数据格式无效")

            result = {
                "valid": len(data) if isinstance(data, list) else 1,
                "errors": 0,
                "warnings": 0,
                "error_details": [],
                "warning_details": [],
            }

        else:
            raise DataValidationError(f"未知的数据类型: {data_type}")

        # 应用自定义验证规则
        if validation_rules:
            logger.info("应用自定义验证规则")
            # TODO: 实现自定义验证规则逻辑

        # 计算验证通过率
        total_items = result["valid"] + result["errors"]
        pass_rate = (result["valid"] / total_items * 100) if total_items > 0 else 0

        # 记录验证结果
        if result["errors"] > 0:
            logger.warning(
                f"数据验证完成: {data_type} - 通过率 {pass_rate:.1f}%, "
                f"错误 {result['errors']} 个, 警告 {result['warnings']} 个"
            )
        else:
            logger.info(
                f"数据验证完成: {data_type} - 通过率 {pass_rate:.1f}%, "
                f"警告 {result['warnings']} 个"
            )

        return {
            "status": "success",
            "data_type": data_type,
            "validation_result": result,
            "pass_rate": pass_rate,
            "timestamp": datetime.now().isoformat(),
        }

    except DataValidationError as exc:
        logger.error(f"数据验证失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "data_type": data_type,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"验证过程中发生未知错误: {str(exc)}")

        # 记录验证失败
        CollectionTaskMixin.log_data_collection_error(
            self,
            data_source="validation",
            collection_type="data_validation",
            error=exc,
            data_type=data_type,
        )

        return {
            "status": "failed",
            "error": f"验证失败: {str(exc)}",
            "data_type": data_type,
            "timestamp": datetime.now().isoformat(),
        }