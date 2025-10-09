"""
模型性能端点
Model Performance Endpoint

提供获取模型详细性能的API接口。
"""




logger = logging.getLogger(__name__)


async def get_model_performance(
    model_name: str,
    version: Optional[str] = Query(None, description="模型版本，为空则获取生产版本"),
    session: AsyncSession = None,
    mlflow_client: MlflowClient = None,
) -> Dict[str, Any]:
    """
    获取模型详细性能分析

    Args:
        model_name: 模型名称
        version: 模型版本
        session: 数据库会话
        mlflow_client: MLflow客户端

    Returns:
        API响应，包含详细性能分析
    """
    try:
        logger.info(f"获取模型 {model_name} 的详细性能分析")

        # 如果没有指定版本，获取生产版本
        if not version:
            try:
                production_versions = mlflow_client.get_latest_versions(
                    name=model_name, stages=["Production"]
                )
                if production_versions:
                    version = production_versions[0].version
                else:
                    raise HTTPException(
                        status_code=404, detail={"error": "模型没有生产版本"}
                    )
            except Exception:
                raise HTTPException(
                    status_code=404, detail={"error": "无法获取模型生产版本"}
                )

        # 获取模型版本信息
        try:
            model_version = mlflow_client.get_model_version(
                name=model_name, version=version
            )
        except Exception as e:
            if "RESOURCE_DOES_NOT_EXIST" in str(e):
                raise HTTPException(status_code=404, detail={"error": "模型不存在"})
            raise

        # 获取运行信息
        run_info = None
        if model_version.run_id:
            try:
                run = mlflow_client.get_run(model_version.run_id)
                run_info = {
                    "run_id": run.info.run_id,
                    "experiment_id": run.info.experiment_id,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                    "tags": run.data.tags,
                }
            except Exception as e:
                logger.warning(f"无法获取运行信息: {e}")

        # 查询预测性能统计
        performance_query = text(
            """
            WITH prediction_stats AS (
                SELECT
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN is_correct IS NOT NULL THEN 1 END) as verified_predictions,
                    COUNT(CASE WHEN is_correct = true THEN 1 END) as correct_predictions,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(
                        CASE WHEN predicted_result = 'home' AND is_correct = true
                        THEN 1 END
                    ) as home_correct,
                    COUNT(
                        CASE WHEN predicted_result = 'draw' AND is_correct = true
                        THEN 1 END
                    ) as draw_correct,
                    COUNT(
                        CASE WHEN predicted_result = 'away' AND is_correct = true
                        THEN 1 END
                    ) as away_correct,
                    COUNT(CASE WHEN predicted_result = 'home' THEN 1 END) as home_total,
                    COUNT(CASE WHEN predicted_result = 'draw' THEN 1 END) as draw_total,
                    COUNT(CASE WHEN predicted_result = 'away' THEN 1 END) as away_total
                FROM predictions
                WHERE model_name = :model_name AND model_version = :version
            )
            SELECT *,
                CASE WHEN verified_predictions > 0
                     THEN correct_predictions::float / verified_predictions
                     ELSE NULL END as overall_accuracy,
                CASE WHEN home_total > 0
                     THEN home_correct::float / home_total
                     ELSE NULL END as home_accuracy,
                CASE WHEN draw_total > 0
                     THEN draw_correct::float / draw_total
                     ELSE NULL END as draw_accuracy,
                CASE WHEN away_total > 0
                     THEN away_correct::float / away_total
                     ELSE NULL END as away_accuracy
            FROM prediction_stats
        """
        )

        result = await session.execute(
            performance_query, {"model_name": model_name, "version": version}
        )

        stats = result.first()




        performance_data = {
            "model_info": {
                "name": model_name,
                "version": version,
                "stage": model_version.current_stage,
                "creation_timestamp": model_version.creation_timestamp,
                "description": model_version.description,
                "tags": model_version.tags,
            },
            "training_info": run_info,
            "prediction_performance": {
                "total_predictions": stats.total_predictions if stats else 0,
                "verified_predictions": stats.verified_predictions if stats else 0,
                "correct_predictions": stats.correct_predictions if stats else 0,
                "overall_accuracy": (
                    float(stats.overall_accuracy)
                    if stats and stats.overall_accuracy
                    else None
                ),
                "average_confidence": (
                    float(stats.avg_confidence)
                    if stats and stats.avg_confidence
                    else None
                ),
                "accuracy_by_result": {
                    "home": (
                        float(stats.home_accuracy)
                        if stats and stats.home_accuracy
                        else None
                    ),
                    "draw": (
                        float(stats.draw_accuracy)
                        if stats and stats.draw_accuracy
                        else None
                    ),
                    "away": (
                        float(stats.away_accuracy)
                        if stats and stats.away_accuracy
                        else None
                    ),
                },
                "predictions_by_result": {
                    "home": stats.home_total if stats else 0,
                    "draw": stats.draw_total if stats else 0,
                    "away": stats.away_total if stats else 0,
                },
            },
        }

        return APIResponse.success(data=performance_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型性能分析失败: {e}")
        raise HTTPException(status_code=500, detail={"error": "获取模型性能分析失败"})