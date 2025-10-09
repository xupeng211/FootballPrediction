"""
预测验证器

负责验证预测结果的有效性和业务规则
"""



logger = logging.getLogger(__name__)


class PredictionValidator:
    """
    预测验证器

    验证预测结果的合理性、完整性和业务规则
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化预测验证器

        Args:
            config: 验证配置
        """
        self.config = config or {}
        self.confidence_threshold = self.config.get("confidence_threshold", 0.3)
        self.probability_tolerance = self.config.get("probability_tolerance", 0.01)
        self.max_confidence = self.config.get("max_confidence", 0.95)

    def validate_prediction_result(self, result: PredictionResult) -> bool:
        """
        验证预测结果的完整性

        Args:
            result: 预测结果

        Returns:
            bool: 验证是否通过
        """
        # 基本字段验证
        if not self._validate_basic_fields(result):
            return False

        # 概率值验证
        if not self._validate_probabilities(result):
            return False

        # 置信度验证
        if not self._validate_confidence(result):
            return False

        # 业务规则验证
        if not self._validate_business_rules(result):
            return False

        logger.debug(f"预测结果 {result.match_id} 验证通过")
        return True

    def validate_batch_predictions(self, results: List[PredictionResult]) -> Dict[str, Any]:
        """
        批量验证预测结果

        Args:
            results: 预测结果列表

        Returns:
            Dict[str, Any]: 验证结果统计
        """
        validation_stats = {
            "total": len(results),
            "valid": 0,
            "invalid": 0,
            "errors": [],
            "warnings": []
        }

        for i, result in enumerate(results):
            try:
                if self.validate_prediction_result(result):
                    validation_stats["valid"] += 1
                else:
                    validation_stats["invalid"] += 1
                    validation_stats["errors"].append(
                        f"索引 {i}: 比赛 {result.match_id} 验证失败"
                    )
            except Exception as e:
                validation_stats["invalid"] += 1
                validation_stats["errors"].append(
                    f"索引 {i}: 比赛 {result.match_id} 验证异常: {e}"
                )

        # 计算验证通过率
        if validation_stats["total"] > 0:
            validation_stats["pass_rate"] = (
                validation_stats["valid"] / validation_stats["total"]
            )
        else:
            validation_stats["pass_rate"] = 0.0

        logger.info(
            f"批量预测验证完成：{validation_stats['valid']}/{validation_stats['total']} 通过"
            f"（通过率：{validation_stats['pass_rate']:.2%}）"
        )

        return validation_stats

    def _validate_basic_fields(self, result: PredictionResult) -> bool:
        """
        验证基本字段

        Args:
            result: 预测结果

        Returns:
            bool: 验证是否通过
        """
        # 必填字段检查
        required_fields = [
            "match_id", "model_version", "model_name",
            "predicted_result", "created_at"
        ]

        for field in required_fields:
            if getattr(result, field) is None:
                logger.warning(f"预测结果缺少必填字段：{field}")
                return False

        # match_id 必须为正整数
        if not isinstance(result.match_id, int) or result.match_id <= 0:
            logger.warning(f"无效的比赛ID：{result.match_id}")
            return False

        # predicted_result 必须为有效值
        valid_results = ["home", "draw", "away"]
        if result.predicted_result not in valid_results:
            logger.warning(f"无效的预测结果：{result.predicted_result}")
            return False

        return True

    def _validate_probabilities(self, result: PredictionResult) -> bool:
        """
        验证概率值

        Args:
            result: 预测结果

        Returns:
            bool: 验证是否通过
        """
        probabilities = [
            result.home_win_probability,
            result.draw_probability,
            result.away_win_probability
        ]

        # 检查概率值范围
        for prob in probabilities:
            if not 0.0 <= prob <= 1.0:
                logger.warning(
                    f"概率值超出范围 [0, 1]：{prob}（比赛 {result.match_id}）"
                )
                return False

        # 检查概率和是否接近1.0
        prob_sum = sum(probabilities)
        if abs(prob_sum - 1.0) > self.probability_tolerance:
            logger.warning(
                f"概率和不为1（和：{prob_sum:.3f}，比赛 {result.match_id}）"
            )
            return False

        return True

    def _validate_confidence(self, result: PredictionResult) -> bool:
        """
        验证置信度

        Args:
            result: 预测结果

        Returns:
            bool: 验证是否通过
        """
        # 置信度范围检查
        if not 0.0 <= result.confidence_score <= 1.0:
            logger.warning(
                f"置信度超出范围 [0, 1]：{result.confidence_score}"
                f"（比赛 {result.match_id}）"
            )
            return False

        # 置信度阈值检查
        if result.confidence_score < self.confidence_threshold:
            logger.warning(
                f"置信度过低：{result.confidence_score:.3f}（比赛 {result.match_id}）"
            )
            # 低置信度不是错误，只是警告

        # 置信度上限检查
        if result.confidence_score > self.max_confidence:
            logger.warning(
                f"置信度异常高：{result.confidence_score:.3f}"
                f"（比赛 {result.match_id}）"
            )

        return True

    def _validate_business_rules(self, result: PredictionResult) -> bool:
        """
        验证业务规则

        Args:
            result: 预测结果

        Returns:
            bool: 验证是否通过
        """
        # 验证预测结果与最高概率的一致性
        probabilities = {
            "home": result.home_win_probability,
            "draw": result.draw_probability,
            "away": result.away_win_probability
        }

        max_prob_result = max(probabilities, key=probabilities.get)
        if max_prob_result != result.predicted_result:
            logger.warning(
                f"预测结果与最高概率不一致：预测为 {result.predicted_result}"
                f"，但最高概率为 {max_prob_result}（比赛 {result.match_id}）"
            )
            return False

        # 验证时间戳合理性
        if result.created_at > datetime.now():
            logger.warning(
                f"创建时间在未来：{result.created_at}（比赛 {result.match_id}）"
            )
            return False

        # 验证特征数量
        if result.features_used is not None:
            feature_count = len(result.features_used)
            if feature_count == 0:
                logger.warning(
                    f"没有使用任何特征（比赛 {result.match_id}）"
                )
                return False

        return True

    def get_validation_summary(self, validation_stats: Dict[str, Any]) -> str:
        """
        生成验证摘要

        Args:
            validation_stats: 验证统计结果

        Returns:
            str: 验证摘要文本
        """
        summary = (
            f"预测验证摘要：\n"
            f"  总数：{validation_stats['total']}\n"
            f"  有效：{validation_stats['valid']}\n"
            f"  无效：{validation_stats['invalid']}\n"



            f"  通过率：{validation_stats['pass_rate']:.2%}\n"
        )

        if validation_stats["errors"]:
            summary += "\n错误：\n"
            for error in validation_stats["errors"][:5]:  # 只显示前5个错误
                summary += f"  - {error}\n"
            if len(validation_stats["errors"]) > 5:
                summary += f"  ... 还有 {len(validation_stats['errors']) - 5} 个错误\n"

        if validation_stats["warnings"]:
            summary += "\n警告：\n"
            for warning in validation_stats["warnings"][:5]:  # 只显示前5个警告
                summary += f"  - {warning}\n"
            if len(validation_stats["warnings"]) > 5:
                summary += f"  ... 还有 {len(validation_stats['warnings']) - 5} 个警告\n"

        return summary