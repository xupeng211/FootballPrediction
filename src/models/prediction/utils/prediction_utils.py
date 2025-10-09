"""
预测工具模块

提供预测相关的工具函数和辅助方法
"""




logger = logging.getLogger(__name__)


class PredictionUtils:
    """
    预测工具类

    提供预测结果处理、格式化和分析的工具方法
    """

    @staticmethod
    def serialize_prediction(result: PredictionResult) -> Dict[str, Any]:
        """
        序列化预测结果为字典

        Args:
            result: 预测结果对象

        Returns:
            Dict[str, Any]: 序列化的结果
        """
        return {
            "match_id": result.match_id,
            "model_version": result.model_version,
            "model_name": result.model_name,
            "home_win_probability": result.home_win_probability,
            "draw_probability": result.draw_probability,
            "away_win_probability": result.away_win_probability,
            "predicted_result": result.predicted_result,
            "confidence_score": result.confidence_score,
            "features_used": result.features_used,
            "prediction_metadata": result.prediction_metadata,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None,
        }

    @staticmethod
    def deserialize_prediction(data: Dict[str, Any]) -> PredictionResult:
        """
        从字典反序列化预测结果

        Args:
            data: 序列化的数据

        Returns:
            PredictionResult: 预测结果对象
        """
        # 处理时间字段
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        else:
            created_at = datetime.now()

        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        else:
            updated_at = None

        return PredictionResult(
            match_id=data["match_id"],
            model_version=data["model_version"],
            model_name=data.get("model_name", "football_baseline_model"),
            home_win_probability=data.get("home_win_probability", 0.0),
            draw_probability=data.get("draw_probability", 0.0),
            away_win_probability=data.get("away_win_probability", 0.0),
            predicted_result=data.get("predicted_result", "draw"),
            confidence_score=data.get("confidence_score", 0.0),
            features_used=data.get("features_used"),
            prediction_metadata=data.get("prediction_metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def calculate_prediction_entropy(
        home_prob: float, draw_prob: float, away_prob: float
    ) -> float:
        """
        计算预测的熵值（不确定性度量）

        Args:
            home_prob: 主胜概率
            draw_prob: 平局概率
            away_prob: 客胜概率

        Returns:
            float: 熵值（0-1.099，越高越不确定）
        """
        probabilities = np.array([home_prob, draw_prob, away_prob])
        
        # 避免log(0)
        probabilities = probabilities[probabilities > 0]
        
        if len(probabilities) == 0:
            return 0.0
        
        # 计算熵
        entropy = -np.sum(probabilities * np.log2(probabilities))
        return float(entropy)

    @staticmethod
    def get_prediction_certainty_level(confidence_score: float) -> str:
        """
        根据置信度获取确定性等级

        Args:
            confidence_score: 置信度分数

        Returns:
            str: 确定性等级（low/medium/high/very_high）
        """
        if confidence_score >= 0.8:
            return "very_high"
        elif confidence_score >= 0.6:
            return "high"
        elif confidence_score >= 0.4:
            return "medium"
        else:
            return "low"

    @staticmethod
    def calculate_betting_value(
        home_prob: float, draw_prob: float, away_prob: float,
        home_odds: float, draw_odds: float, away_odds: float
    ) -> Dict[str, float]:
        """
        计算投注价值

        Args:
            home_prob: 主胜概率
            draw_prob: 平局概率
            away_prob: 客胜概率
            home_odds: 主胜赔率
            draw_odds: 平局赔率
            away_odds: 客胜赔率

        Returns:
            Dict[str, float]: 各结果的投注价值
        """
        # 转换赔率为隐含概率
        home_implied = 1.0 / home_odds if home_odds > 0 else 0
        draw_implied = 1.0 / draw_odds if draw_odds > 0 else 0
        away_implied = 1.0 / away_odds if away_odds > 0 else 0
        
        # 计算价值（预测概率 - 隐含概率）
        home_value = home_prob - home_implied
        draw_value = draw_prob - draw_implied
        away_value = away_prob - away_implied
        
        return {
            "home_value": home_value,
            "draw_value": draw_value,
            "away_value": away_value,
            "max_value": max(home_value, draw_value, away_value)
        }

    @staticmethod
    def aggregate_predictions(predictions: List[PredictionResult]) -> Dict[str, Any]:
        """
        聚合多个预测结果

        Args:
            predictions: 预测结果列表

        Returns:
            Dict[str, Any]: 聚合统计信息
        """
        if not predictions:
            return {
                "count": 0,
                "avg_confidence": 0.0,
                "result_distribution": {},
                "probability_averages": {
                    "home": 0.0, "draw": 0.0, "away": 0.0
                }
            }
        
        # 统计预测结果分布
        result_counts = {"home": 0, "draw": 0, "away": 0}
        total_confidence = 0.0
        home_probs = []
        draw_probs = []
        away_probs = []
        
        for pred in predictions:
            result_counts[pred.predicted_result] += 1
            total_confidence += pred.confidence_score
            home_probs.append(pred.home_win_probability)
            draw_probs.append(pred.draw_probability)
            away_probs.append(pred.away_win_probability)
        
        # 计算平均值
        count = len(predictions)
        avg_confidence = total_confidence / count
        
        return {
            "count": count,
            "avg_confidence": avg_confidence,
            "result_distribution": {
                "home": result_counts["home"],
                "draw": result_counts["draw"],
                "away": result_counts["away"]
            },
            "result_percentages": {
                "home": result_counts["home"] / count * 100,
                "draw": result_counts["draw"] / count * 100,
                "away": result_counts["away"] / count * 100
            },
            "probability_averages": {
                "home": np.mean(home_probs),
                "draw": np.mean(draw_probs),
                "away": np.mean(away_probs)
            },
            "probability_std": {
                "home": np.std(home_probs),
                "draw": np.std(draw_probs),
                "away": np.std(away_probs)
            }
        }

    @staticmethod
    def filter_predictions_by_confidence(
        predictions: List[PredictionResult],
        min_confidence: float = 0.5,
        max_confidence: float = 1.0
    ) -> List[PredictionResult]:
        """
        根据置信度过滤预测结果

        Args:
            predictions: 预测结果列表
            min_confidence: 最小置信度
            max_confidence: 最大置信度

        Returns:
            List[PredictionResult]: 过滤后的预测结果
        """
        filtered = [
            pred for pred in predictions
            if min_confidence <= pred.confidence_score <= max_confidence
        ]
        
        logger.info(
            f"根据置信度过滤：{len(filtered)}/{len(predictions)} 个结果符合条件"
            f"（置信度范围：{min_confidence}-{max_confidence}）"
        )
        
        return filtered

    @staticmethod
    def export_predictions_to_csv(
        predictions: List[PredictionResult],
        file_path: str
    ) -> None:
        """
        导出预测结果到CSV文件

        Args:
            predictions: 预测结果列表
            file_path: 输出文件路径
        """
        if not predictions:
            logger.warning("没有预测结果可导出")
            return
        
        # 转换为DataFrame
        data = []
        for pred in predictions:
            row = {
                "match_id": pred.match_id,
                "model_version": pred.model_version,
                "model_name": pred.model_name,
                "predicted_result": pred.predicted_result,
                "confidence_score": pred.confidence_score,
                "home_win_probability": pred.home_win_probability,
                "draw_probability": pred.draw_probability,
                "away_win_probability": pred.away_win_probability,
                "created_at": pred.created_at.isoformat() if pred.created_at else None,
            }
            
            # 添加元数据
            if pred.prediction_metadata:
                for key, value in pred.prediction_metadata.items():
                    row[f"meta_{key}"] = value
            
            data.append(row)
        
        # 创建DataFrame并保存
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)
        
        logger.info(f"成功导出 {len(predictions)} 个预测结果到 {file_path}")

    @staticmethod
    def calculate_prediction_metrics(
        predictions: List[PredictionResult],
        actual_results: Dict[int, str]
    ) -> Dict[str, Any]:
        """
        计算预测准确率指标

        Args:
            predictions: 预测结果列表
            actual_results: 实际结果字典 {match_id: result}

        Returns:
            Dict[str, Any]: 准确率指标
        """
        if not predictions or not actual_results:
            return {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "coverage": 0.0
            }
        
        correct = 0
        total = 0
        confidence_sum = 0.0
        correct_confidence_sum = 0.0
        
        for pred in predictions:
            if pred.match_id in actual_results:
                total += 1
                actual = actual_results[pred.match_id]
                
                if pred.predicted_result == actual:
                    correct += 1
                    correct_confidence_sum += pred.confidence_score
                
                confidence_sum += pred.confidence_score
        
        # 计算指标
        accuracy = correct / total if total > 0 else 0.0
        coverage = total / len(predictions) if predictions else 0.0
        avg_confidence = confidence_sum / total if total > 0 else 0.0
        avg_correct_confidence = correct_confidence_sum / correct if correct > 0 else 0.0
        
        return {
            "total_predictions": len(predictions),
            "matched_results": total,
            "correct_predictions": correct,
            "accuracy": accuracy,
            "coverage": coverage,
            "avg_confidence": avg_confidence,
            "avg_correct_confidence": avg_correct_confidence,
            "confidence_calibration": avg_correct_confidence - avg_confidence
        }

    @staticmethod
    def generate_prediction_report(
        predictions: List[PredictionResult],
        title: str = "预测分析报告"
    ) -> str:
        """
        生成预测分析报告

        Args:
            predictions: 预测结果列表
            title: 报告标题

        Returns:
            str: 报告文本
        """
        if not predictions:
            return f"{title}\n没有预测数据可分析\n"
        
        # 聚合统计
        stats = PredictionUtils.aggregate_predictions(predictions)
        
        # 生成报告
        report = [
            f"{title}",
            f"{'='*50}",
            "",
            f"总预测数：{stats['count']}",
            f"平均置信度：{stats['avg_confidence']:.3f}",
            "",
            "预测结果分布：",
            f"  主胜：{stats['result_distribution']['home']} 次"
            f"（{stats['result_percentages']['home']:.1f}%）",
            f"  平局：{stats['result_distribution']['draw']} 次"
            f"（{stats['result_percentages']['draw']:.1f}%）",
            f"  客胜：{stats['result_distribution']['away']} 次"
            f"（{stats['result_percentages']['away']:.1f}%）",
            "",
            "平均概率预测：",
            f"  主胜概率：{stats['probability_averages']['home']:.3f}"
            f"（±{stats['probability_std']['home']:.3f}）",
            f"  平局概率：{stats['probability_averages']['draw']:.3f}"
            f"（±{stats['probability_std']['draw']:.3f}）",
            f"  客胜概率：{stats['probability_averages']['away']:.3f}"
            f"（±{stats['probability_std']['away']:.3f}）",
        ]
        
        # 添加高置信度预测统计
        high_confidence = PredictionUtils.filter_predictions_by_confidence(
            predictions, 0.7
        )
        if high_confidence:
            high_stats = PredictionUtils.aggregate_predictions(high_confidence)
            report.extend([
                "",
                "高置信度预测（≥0.7）：",
                f"  数量：{len(high_confidence)} 个",
                f"  占比：{len(high_confidence)/len(predictions)*100:.1f}%",
                f"  平均置信度：{high_stats['avg_confidence']:.3f}",
            ])
        
        report.append(f"\n报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(report)

    @staticmethod
    def get_recent_predictions(
        predictions: List[PredictionResult],
        hours: int = 24
    ) -> List[PredictionResult]:
        """
        获取最近时间范围内的预测

        Args:
            predictions: 预测结果列表
            hours: 时间范围（小时）

        Returns:
            List[PredictionResult]: 最近的预测结果
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent = [
            pred for pred in predictions
            if pred.created_at and pred.created_at >= cutoff_time
        ]
        



        logger.info(
            f"获取最近 {hours} 小时的预测：{len(recent)}/{len(predictions)} 个结果"
        )
        
        return recent