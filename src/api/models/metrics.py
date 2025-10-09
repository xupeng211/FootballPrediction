"""
模型指标端点
Model Metrics Endpoint

提供获取模型性能指标的API接口。
"""




logger = logging.getLogger(__name__)


async def get_model_metrics(
    model_name: str = Query("football_baseline_model", description="模型名称"),
    time_window: str = Query("7d", description="时间窗口：1d, 7d, 30d"),
    session: AsyncSession = None,
) -> Dict[str, Any]:
    """
    获取模型性能指标

    Args:
        model_name: 模型名称
        time_window: 时间窗口
        session: 数据库会话

    Returns:
        API响应，包含模型性能指标
    """
    try:
        logger.info(f"获取模型 {model_name} 的性能指标，时间窗口: {time_window}")

        # 计算时间范围
        end_date = datetime.now()
        if time_window == "1d":
            start_date = end_date - timedelta(days=1)
        elif time_window == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_window == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            raise HTTPException(
                status_code=400, detail={"error": "无效的时间窗口，支持: 1d, 7d, 30d"}
            )

        # 查询预测统计
        metrics_query = text(
            """
            SELECT
                model_version,
                COUNT(*) as total_predictions,
                AVG(confidence_score) as avg_confidence,
                SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END)::float /
                NULLIF(
                    SUM(CASE WHEN is_correct IS NOT NULL THEN 1 ELSE 0 END), 0
                ) as accuracy,
                COUNT(
                    CASE WHEN predicted_result = 'home' THEN 1 END
                ) as home_predictions,
                COUNT(
                    CASE WHEN predicted_result = 'draw' THEN 1 END
                ) as draw_predictions,
                COUNT(
                    CASE WHEN predicted_result = 'away' THEN 1 END
                ) as away_predictions,
                COUNT(
                    CASE WHEN is_correct IS NOT NULL THEN 1 END
                ) as verified_predictions,
                COUNT(CASE WHEN is_correct = true THEN 1 END) as correct_predictions,
                MIN(created_at) as first_prediction,
                MAX(created_at) as last_prediction
            FROM predictions
            WHERE model_name = :model_name
              AND created_at >= :start_date
              AND created_at <= :end_date
            GROUP BY model_version
            ORDER BY model_version DESC
        """
        )

        result = await session.execute(
            metrics_query,
            {"model_name": model_name, "start_date": start_date, "end_date": end_date},
        )

        metrics = []
        total_predictions = 0
        total_correct = 0
        total_verified = 0

        for row in result:
            metric_data = {
                "model_version": row.model_version,
                "total_predictions": row.total_predictions,
                "avg_confidence": (
                    float(row.avg_confidence) if row.avg_confidence else 0.0
                ),
                "accuracy": float(row.accuracy) if row.accuracy else None,
                "predictions_by_result": {
                    "home": row.home_predictions,
                    "draw": row.draw_predictions,
                    "away": row.away_predictions,
                },
                "verified_predictions": row.verified_predictions,
                "correct_predictions": row.correct_predictions,
                "first_prediction": (
                    row.first_prediction.isoformat() if row.first_prediction else None
                ),
                "last_prediction": (
                    row.last_prediction.isoformat() if row.last_prediction else None
                ),
            }
            metrics.append(metric_data)

            # 累计统计
            total_predictions += row.total_predictions
            total_correct += row.correct_predictions or 0
            total_verified += row.verified_predictions or 0

        # 计算总体准确率
        overall_accuracy = (
            (total_correct / total_verified) if total_verified > 0 else None
        )

        # 查询最近预测趋势
        trend_query = text(
            """
            SELECT
                DATE(created_at) as prediction_date,
                COUNT(*) as daily_predictions,
                AVG(confidence_score) as daily_avg_confidence
            FROM predictions
            WHERE model_name = :model_name
              AND created_at >= :start_date
              AND created_at <= :end_date
            GROUP BY DATE(created_at)
            ORDER BY prediction_date
        """
        )

        trend_result = await session.execute(
            trend_query,
            {"model_name": model_name, "start_date": start_date, "end_date": end_date},
        )




        daily_trends = []
        for row in trend_result:
            daily_trends.append(
                {
                    "date": row.prediction_date.isoformat(),
                    "predictions": row.daily_predictions,
                    "avg_confidence": float(row.daily_avg_confidence),
                }
            )

        return APIResponse.success(
            data={
                "model_name": model_name,
                "time_window": time_window,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "overall_statistics": {
                    "total_predictions": total_predictions,
                    "total_verified": total_verified,
                    "total_correct": total_correct,
                    "overall_accuracy": overall_accuracy,
                },
                "metrics_by_version": metrics,
                "daily_trends": daily_trends,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型指标失败: {e}")
        raise HTTPException(status_code=500, detail={"error": "获取模型指标失败"})