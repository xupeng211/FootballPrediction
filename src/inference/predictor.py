"""
Predictor
统一预测入口

提供统一的预测接口，支持多种模型和预测类型。
包含预测校准、置信度计算和结果验证功能。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from .loader import get_model_loader, LoadedModel
from .feature_builder import get_feature_builder
from .cache import get_prediction_cache
from .schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelType,
    PredictionType,
)
from .errors import PredictionError, ModelLoadError, FeatureBuilderError, ErrorCode

logger = logging.getLogger(__name__)


class PredictionResult:
    """预测结果容器"""

    def __init__(
        self,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        predicted_outcome: str,
        confidence: float,
        model_name: str,
        model_version: str,
        model_type: ModelType,
        features_used: list[str],
        prediction_time_ms: float,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.home_win_prob = home_win_prob
        self.draw_prob = draw_prob
        self.away_win_prob = away_win_prob
        self.predicted_outcome = predicted_outcome
        self.confidence = confidence
        self.model_name = model_name
        self.model_version = model_version
        self.model_type = model_type
        self.features_used = features_used
        self.prediction_time_ms = prediction_time_ms
        self.metadata = metadata or {}

        # 验证概率和
        prob_sum = home_win_prob + draw_prob + away_win_prob
        if abs(prob_sum - 1.0) > 0.001:
            # 归一化概率
            total = max(prob_sum, 0.001)
            self.home_win_prob /= total
            self.draw_prob /= total
            self.away_win_prob /= total

    def to_response(
        self, request_id: str, match_id: str, cached: bool = False
    ) -> PredictionResponse:
        """转换为响应对象"""
        return PredictionResponse(
            request_id=request_id,
            match_id=match_id,
            predicted_at=datetime.utcnow(),
            home_win_prob=self.home_win_prob,
            draw_prob=self.draw_prob,
            away_win_prob=self.away_win_prob,
            predicted_outcome=self.predicted_outcome,
            confidence=self.confidence,
            model_name=self.model_name,
            model_version=self.model_version,
            model_type=self.model_type,
            features_used=self.features_used,
            prediction_time_ms=self.prediction_time_ms,
            cached=cached,
            metadata=self.metadata,
        )


class Predictor:
    """
    统一预测器

    提供以下功能：
    1. 单场比赛预测
    2. 批量预测
    3. 多模型集成预测
    4. 预测结果校准
    5. 缓存管理
    6. 性能监控
    """

    def __init__(self, max_workers: int = 4):
        """
        初始化预测器

        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._prediction_stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_prediction_time": 0.0,
        }

        # 预测历史（用于监控）
        self._prediction_history = []

    async def predict(self, request: PredictionRequest) -> PredictionResponse:
        """
        单场比赛预测

        Args:
            request: 预测请求

        Returns:
            PredictionResponse: 预测响应

        Raises:
            PredictionError: 预测失败
        """
        start_time = datetime.now()
        request_id = str(uuid.uuid4())

        try:
            # 检查缓存
            if not request.force_recalculate:
                cached_result = await self._get_cached_prediction(request)
                if cached_result:
                    self._prediction_stats["cache_hits"] += 1
                    logger.info(f"Cache hit for prediction {request.match_id}")
                    return cached_result.to_response(
                        request_id, request.match_id, cached=True
                    )

            self._prediction_stats["cache_misses"] += 1

            # 执行预测
            result = await self._execute_prediction(request)

            # 缓存结果
            await self._cache_prediction(request, result)

            # 更新统计
            self._prediction_stats["total_predictions"] += 1
            self._prediction_stats["successful_predictions"] += 1
            self._update_prediction_time_stats(result.prediction_time_ms)

            # 记录预测历史
            self._record_prediction(request, result)

            logger.info(
                f"Prediction completed for {request.match_id}: {result.predicted_outcome}"
            )
            return result.to_response(request_id, request.match_id, cached=False)

        except Exception as e:
            self._prediction_stats["total_predictions"] += 1
            self._prediction_stats["failed_predictions"] += 1

            error_msg = f"Prediction failed for match {request.match_id}: {str(e)}"
            logger.error(error_msg)

            if isinstance(e, ModelLoadError | FeatureBuilderError | PredictionError):
                raise
            else:
                raise PredictionError(error_msg, prediction_id=request_id)

        finally:
            # 记录总耗时
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"Total prediction time: {total_time:.2f}ms")

    async def predict_batch(
        self, request: BatchPredictionRequest
    ) -> BatchPredictionResponse:
        """
        批量预测

        Args:
            request: 批量预测请求

        Returns:
            BatchPredictionResponse: 批量预测响应
        """
        start_time = datetime.now()
        batch_id = request.batch_id or str(uuid.uuid4())

        logger.info(f"Starting batch prediction: {len(request.requests)} requests")

        predictions = []
        errors = []
        cached_count = 0

        try:
            if request.parallel:
                # 并行处理
                tasks = [self.predict(req) for req in request.requests]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        errors.append(
                            {
                                "request_index": i,
                                "match_id": request.requests[i].match_id,
                                "error": str(result),
                            }
                        )
                    else:
                        predictions.append(result)
                        if result.cached:
                            cached_count += 1
            else:
                # 串行处理
                for i, req in enumerate(request.requests):
                    try:
                        result = await self.predict(req)
                        predictions.append(result)
                        if result.cached:
                            cached_count += 1
                    except Exception as e:
                        errors.append(
                            {
                                "request_index": i,
                                "match_id": req.match_id,
                                "error": str(e),
                            }
                        )

            batch_time = (datetime.now() - start_time).total_seconds() * 1000

            response = BatchPredictionResponse(
                batch_id=batch_id,
                total_requests=len(request.requests),
                successful_predictions=len(predictions),
                failed_predictions=len(errors),
                predictions=predictions,
                errors=errors,
                batch_time_ms=batch_time,
                cached_count=cached_count,
            )

            logger.info(
                f"Batch prediction completed: {len(predictions)}/{len(request.requests)} successful, "
                f"{cached_count} from cache, {batch_time:.2f}ms"
            )

            return response

        except Exception as e:
            raise PredictionError(f"Batch prediction failed: {str(e)}")

    async def _execute_prediction(self, request: PredictionRequest) -> PredictionResult:
        """执行预测逻辑"""
        start_time = datetime.now()

        # 1. 获取模型
        model_loader = await get_model_loader()
        loaded_model = await model_loader.get(request.model_name)

        # 2. 构建特征
        feature_builder = await get_feature_builder()

        # 准备原始数据（这里需要从数据库或其他源获取）
        raw_data = await self._get_match_data(request.match_id)
        match_info = await self._get_match_info(request.match_id)
        historical_data = await self._get_historical_data(request.match_id)

        # 使用自定义特征（如果提供）
        if request.features:
            raw_data.update(request.features)

        # 构建特征
        features_df = await feature_builder.build_features(
            raw_data=raw_data, match_info=match_info, historical_data=historical_data
        )

        # 3. 执行预测
        prediction_result = await self._predict_with_model(
            loaded_model.model, features_df, request.prediction_type
        )

        # 4. 后处理
        processed_result = await self._post_process_prediction(
            prediction_result, loaded_model, request
        )

        # 5. 计算预测耗时
        prediction_time = (datetime.now() - start_time).total_seconds() * 1000

        # 6. 创建结果
        result = PredictionResult(
            home_win_prob=processed_result["home_win_prob"],
            draw_prob=processed_result["draw_prob"],
            away_win_prob=processed_result["away_win_prob"],
            predicted_outcome=processed_result["predicted_outcome"],
            confidence=processed_result["confidence"],
            model_name=loaded_model.metadata.model_info.model_name,
            model_version=loaded_model.metadata.model_info.model_version,
            model_type=loaded_model.metadata.model_info.model_type,
            features_used=list(features_df.columns),
            prediction_time_ms=prediction_time,
            metadata=processed_result.get("metadata", {}),
        )

        return result

    async def _predict_with_model(
        self, model: Any, features_df: pd.DataFrame, prediction_type: PredictionType
    ) -> dict[str, Any]:
        """使用模型进行预测"""

        def predict_sync():
            try:
                if prediction_type == PredictionType.PROBABILITY:
                    # 概率预测
                    if hasattr(model, "predict_proba"):
                        probabilities = model.predict_proba(features_df)
                        if probabilities.shape[1] >= 3:
                            # 假设顺序为 [away, draw, home]
                            away_prob, draw_prob, home_prob = probabilities[0]
                        else:
                            # 二分类结果，处理为三分类
                            home_prob = (
                                probabilities[0][1]
                                if probabilities.shape[1] == 2
                                else 0.33
                            )
                            draw_prob = 0.34
                            away_prob = 1 - home_prob - draw_prob
                    else:
                        # 没有概率输出，使用预测结果
                        prediction = model.predict(features_df)[0]
                        if isinstance(prediction, int | np.integer):
                            # 整数输出，转换为概率
                            if prediction == 2:  # home win
                                home_prob, draw_prob, away_prob = 0.7, 0.2, 0.1
                            elif prediction == 1:  # draw
                                home_prob, draw_prob, away_prob = 0.3, 0.4, 0.3
                            else:  # away win
                                home_prob, draw_prob, away_prob = 0.1, 0.2, 0.7
                        else:
                            # 浮点数输出
                            if prediction > 0.5:
                                home_prob, draw_prob, away_prob = 0.7, 0.2, 0.1
                            else:
                                home_prob, draw_prob, away_prob = 0.1, 0.2, 0.7

                elif prediction_type == PredictionType.WINNER:
                    # 胜者预测
                    prediction = model.predict(features_df)[0]
                    if hasattr(model, "predict_proba"):
                        probabilities = model.predict_proba(features_df)[0]
                        if probabilities.shape[1] >= 3:
                            away_prob, draw_prob, home_prob = probabilities
                        else:
                            home_prob = (
                                probabilities[1]
                                if probabilities.shape[1] == 2
                                else 0.33
                            )
                            draw_prob = 0.34
                            away_prob = 1 - home_prob - draw_prob
                    else:
                        if prediction == 2:  # home win
                            home_prob, draw_prob, away_prob = 0.7, 0.2, 0.1
                        elif prediction == 1:  # draw
                            home_prob, draw_prob, away_prob = 0.3, 0.4, 0.3
                        else:  # away win
                            home_prob, draw_prob, away_prob = 0.1, 0.2, 0.7

                elif prediction_type == PredictionType.SCORE:
                    # 比分预测（简化处理）
                    # 这里可以扩展为真正的比分预测
                    prediction = model.predict(features_df)[0]
                    if hasattr(model, "predict_proba"):
                        probabilities = model.predict_proba(features_df)[0]
                        if probabilities.shape[1] >= 3:
                            away_prob, draw_prob, home_prob = probabilities
                        else:
                            home_prob = (
                                probabilities[1]
                                if probabilities.shape[1] == 2
                                else 0.33
                            )
                            draw_prob = 0.34
                            away_prob = 1 - home_prob - draw_prob
                    else:
                        home_prob, draw_prob, away_prob = 0.4, 0.3, 0.3

                else:
                    # 默认处理
                    prediction = model.predict(features_df)[0]
                    home_prob, draw_prob, away_prob = 0.33, 0.34, 0.33

                return {
                    "home_win_prob": float(home_prob),
                    "draw_prob": float(draw_prob),
                    "away_win_prob": float(away_prob),
                    "raw_prediction": prediction if "prediction" in locals() else None,
                }

            except Exception as e:
                raise RuntimeError(f"Model prediction failed: {str(e)}")

        # 在线程池中执行同步预测
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, predict_sync
        )

    async def _post_process_prediction(
        self,
        prediction_result: dict[str, Any],
        loaded_model: LoadedModel,
        request: PredictionRequest,
    ) -> dict[str, Any]:
        """后处理预测结果"""
        result = prediction_result.copy()

        # 1. 概率归一化
        prob_sum = (
            result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]
        )
        if prob_sum > 0:
            result["home_win_prob"] /= prob_sum
            result["draw_prob"] /= prob_sum
            result["away_win_prob"] /= prob_sum

        # 2. 确定预测结果
        probs = [
            ("home_win", result["home_win_prob"]),
            ("draw", result["draw_prob"]),
            ("away_win", result["away_win_prob"]),
        ]
        result["predicted_outcome"] = max(probs, key=lambda x: x[1])[0]

        # 3. 计算置信度
        max_prob = max(probs, key=lambda x: x[1])[1]
        second_max_prob = sorted(probs, key=lambda x: x[1])[-2][1]
        confidence = max_prob - second_max_prob
        result["confidence"] = float(confidence)

        # 4. 应用校准（如果需要）
        if self._should_calibrate(loaded_model):
            result = await self._calibrate_prediction(result)

        # 5. 添加元数据
        result["metadata"] = {
            "model_accuracy": loaded_model.metadata.model_info.accuracy,
            "calibration_applied": self._should_calibrate(loaded_model),
            "prediction_type": request.prediction_type.value,
            "feature_count": len(loaded_model.metadata.model_info.features),
        }

        return result

    def _should_calibrate(self, loaded_model: LoadedModel) -> bool:
        """判断是否需要校准"""
        # 基于模型类型和准确率决定
        if loaded_model.metadata.model_info.model_type == ModelType.XGBOOST:
            return True
        elif loaded_model.metadata.model_info.accuracy:
            return loaded_model.metadata.model_info.accuracy < 0.8
        return False

    async def _calibrate_prediction(
        self, prediction_result: dict[str, Any]
    ) -> dict[str, Any]:
        """校准预测结果"""
        # 简单的校准逻辑，可以根据需要扩展
        calibrated = prediction_result.copy()

        # 温度缩放校准
        temperature = 1.2  # 校准参数
        probs = np.array(
            [
                calibrated["away_win_prob"],
                calibrated["draw_prob"],
                calibrated["home_win_prob"],
            ]
        )

        # 应用温度缩放
        exp_probs = np.exp(np.log(probs + 1e-8) / temperature)
        calibrated_probs = exp_probs / np.sum(exp_probs)

        calibrated["away_win_prob"] = float(calibrated_probs[0])
        calibrated["draw_prob"] = float(calibrated_probs[1])
        calibrated["home_win_prob"] = float(calibrated_probs[2])

        return calibrated

    async def _get_cached_prediction(
        self, request: PredictionRequest
    ) -> Optional[PredictionResult]:
        """获取缓存的预测结果"""
        try:
            cache = await get_prediction_cache()
            cache_key = self._generate_cache_key(request)
            cached_data = await cache.get_prediction(cache_key)

            if cached_data:
                return PredictionResult(**cached_data)

        except Exception as e:
            logger.warning(f"Failed to get cached prediction: {e}")

        return None

    async def _cache_prediction(
        self, request: PredictionRequest, result: PredictionResult
    ):
        """缓存预测结果"""
        try:
            cache = await get_prediction_cache()
            cache_key = self._generate_cache_key(request)

            # 准备缓存数据
            cache_data = {
                "home_win_prob": result.home_win_prob,
                "draw_prob": result.draw_prob,
                "away_win_prob": result.away_win_prob,
                "predicted_outcome": result.predicted_outcome,
                "confidence": result.confidence,
                "model_name": result.model_name,
                "model_version": result.model_version,
                "model_type": result.model_type,
                "features_used": result.features_used,
                "prediction_time_ms": result.prediction_time_ms,
                "metadata": result.metadata,
                "cached_at": datetime.utcnow().isoformat(),
            }

            await cache.set_prediction(cache_key, cache_data)

        except Exception as e:
            logger.warning(f"Failed to cache prediction: {e}")

    def _generate_cache_key(self, request: PredictionRequest) -> str:
        """生成缓存键"""
        key_parts = [
            "prediction",
            request.match_id,
            request.model_name,
            request.model_version or "latest",
            request.prediction_type.value,
        ]

        if request.features:
            # 对自定义特征进行安全哈希
            import hashlib

            features_hash = hashlib.sha256(
                str(sorted(request.features.items())).encode()
            ).hexdigest()[:8]
            key_parts.append(features_hash)

        return ":".join(key_parts)

    async def _get_match_data(self, match_id: str) -> dict[str, Any]:
        """获取比赛数据"""
        # 这里应该从数据库或其他数据源获取实际数据
        # 暂时返回模拟数据
        return {
            "home_goals": np.random.randint(0, 5),
            "away_goals": np.random.randint(0, 5),
            "home_possession": np.random.uniform(30, 70),
            "away_possession": np.random.uniform(30, 70),
            "home_shots": np.random.randint(5, 25),
            "away_shots": np.random.randint(5, 25),
            "home_corners": np.random.randint(2, 12),
            "away_corners": np.random.randint(2, 12),
        }

    async def _get_match_info(self, match_id: str) -> dict[str, Any]:
        """获取比赛信息"""
        # 暂时返回模拟数据
        return {
            "home_team": f"Team_A_{match_id}",
            "away_team": f"Team_B_{match_id}",
            "match_date": datetime.now().isoformat(),
            "league_id": "league_123",
        }

    async def _get_historical_data(self, match_id: str) -> dict[str, Any]:
        """获取历史数据"""
        # 暂时返回模拟数据
        return {
            "team_history": {
                f"Team_A_{match_id}": [
                    {
                        "goals": np.random.randint(0, 5),
                        "shots": np.random.randint(5, 25),
                    }
                    for _ in range(10)
                ],
                f"Team_B_{match_id}": [
                    {
                        "goals": np.random.randint(0, 5),
                        "shots": np.random.randint(5, 25),
                    }
                    for _ in range(10)
                ],
            }
        }

    def _update_prediction_time_stats(self, prediction_time_ms: float):
        """更新预测时间统计"""
        current_avg = self._prediction_stats["average_prediction_time"]
        total_count = self._prediction_stats["successful_predictions"]

        # 计算新的平均值
        new_avg = (current_avg * (total_count - 1) + prediction_time_ms) / total_count
        self._prediction_stats["average_prediction_time"] = new_avg

    def _record_prediction(self, request: PredictionRequest, result: PredictionResult):
        """记录预测历史"""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "match_id": request.match_id,
            "model_name": result.model_name,
            "predicted_outcome": result.predicted_outcome,
            "confidence": result.confidence,
            "prediction_time_ms": result.prediction_time_ms,
        }

        self._prediction_history.append(record)

        # 保持历史记录在合理范围内
        if len(self._prediction_history) > 1000:
            self._prediction_history = self._prediction_history[-1000:]

    def get_prediction_stats(self) -> dict[str, Any]:
        """获取预测统计信息"""
        total_requests = (
            self._prediction_stats["successful_predictions"]
            + self._prediction_stats["failed_predictions"]
        )

        success_rate = (
            self._prediction_stats["successful_predictions"] / total_requests * 100
            if total_requests > 0
            else 0
        )

        cache_total = (
            self._prediction_stats["cache_hits"]
            + self._prediction_stats["cache_misses"]
        )

        cache_hit_rate = (
            self._prediction_stats["cache_hits"] / cache_total * 100
            if cache_total > 0
            else 0
        )

        return {
            **self._prediction_stats,
            "success_rate": round(success_rate, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "history_count": len(self._prediction_history),
        }

    async def cleanup(self):
        """清理资源"""
        # 关闭线程池
        self._executor.shutdown(wait=True)

        # 清理历史记录
        self._prediction_history.clear()

        logger.info("Predictor cleanup completed")


# 全局实例
_predictor: Optional[Predictor] = None


async def get_predictor() -> Predictor:
    """获取全局预测器实例"""
    global _predictor

    if _predictor is None:
        _predictor = Predictor()

    return _predictor
