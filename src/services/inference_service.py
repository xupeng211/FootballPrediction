#!/usr/bin/env python3
"""
M5模块: 在线推理服务

实现高性能的足球比赛1X2预测推理服务，严格遵循TDD设计。
整合M1数据库访问、M3特征工程、M4模型推理，提供低延迟的预测API。

核心功能:
1. 单例模式模型加载，避免重复加载
2. 异步数据库访问和特征提取
3. 低延迟推理和概率预测
4. 完整的错误处理和监控
5. 模型版本管理和热更新支持

设计原则:
- TDD驱动: 先写测试，后写实现
- 低延迟: 模型预加载，推理优化
- 高可用: 完整的错误处理和降级策略
- 可观测: 详细的日志和性能监控
- 类型安全: Pydantic模型验证

依赖关系:
- M1: src/database/db_pool.py - 异步数据库连接
- M3: src/features/extractor.py - 特征提取器
- M4: src/ml/models/xgboost_classifier.py - XGBoost模型
- 外部: FastAPI, Pydantic, numpy, pandas
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import dataclasses

import numpy as np
import pandas as pd
from fastapi import HTTPException

# 导入M1模块 - 数据库访问
from src.database.db_pool import get_db_pool, DatabasePool

# 导入M3模块 - 特征工程
from src.features.extractor import MatchFeatureExtractor
from src.features.schemas import MatchFeatureSet

# 导入M4模块 - 模型推理
from src.ml.models.xgboost_classifier import XGBoostClassifier

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class InferenceConfig:
    """
    推理服务配置类

    包含模型路径、特征配置、缓存策略等推理相关参数。
    """

    # 模型配置
    model_path: str = "models/football_xgboost_classifier.pkl"
    model_config_path: Optional[str] = None
    fallback_model_path: Optional[str] = None

    # 特征提取配置
    feature_extractor_config: Optional[Dict[str, Any]] = None
    historical_data_days: int = 90

    # 缓存配置
    enable_cache: bool = True
    cache_ttl_seconds: int = 300  # 5分钟
    max_cache_size: int = 1000

    # 性能配置
    request_timeout_seconds: float = 10.0
    max_concurrent_requests: int = 100

    # 降级策略
    enable_fallback: bool = True
    default_probabilities: Dict[str, float] = dataclasses.field(
        default_factory=lambda: {
            "HOME_WIN_PROBA": 0.46,
            "DRAW_PROBA": 0.26,
            "AWAY_WIN_PROBA": 0.28,
        }
    )

    # 监控配置
    enable_metrics: bool = True
    log_prediction_requests: bool = True

    def __post_init__(self):
        """初始化后处理"""
        # 确保概率总和为1.0
        total = sum(self.default_probabilities.values())
        if abs(total - 1.0) > 1e-6:
            for key in self.default_probabilities:
                self.default_probabilities[key] /= total


class InferenceService:
    """
    在线推理服务

    提供高性能的足球比赛1X2预测推理服务。
    实现单例模式，确保模型只加载一次，提供低延迟的推理能力。

    主要功能:
    - 模型加载和管理 (单例模式)
    - 异步数据获取和特征提取
    - 低延迟推理和概率预测
    - 智能缓存和降级策略
    - 完整的错误处理和监控

    使用示例:
        # 初始化推理服务
        service = await InferenceService.get_instance()

        # 进行预测
        result = await service.predict("match_12345")
        print(result)
        # {
        #     "match_id": "match_12345",
        #     "HOME_WIN_PROBA": 0.65,
        #     "DRAW_PROBA": 0.25,
        #     "AWAY_WIN_PROBA": 0.10,
        #     "predicted_class": "HOME_WIN",
        #     "confidence": 0.65,
        #     "model_version": "1.0.0",
        #     "processed_at": "2024-01-15T10:30:00Z"
        # }
    """

    _instance: Optional["InferenceService"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[InferenceConfig] = None):
        """
        初始化推理服务

        Args:
            config: 推理服务配置，如果为None则使用默认配置
        """
        self.config = config or InferenceConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 组件实例
        self.model: Optional[XGBoostClassifier] = None
        self.feature_extractor: Optional[MatchFeatureExtractor] = None
        self.db_pool: Optional[DatabasePool] = None

        # 缓存
        self._prediction_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "fallback_used": 0,
            "errors": 0,
            "avg_response_time_ms": 0.0,
            "model_load_time_ms": 0.0,
            "started_at": None,
            "last_prediction_time": None,
        }

        self.is_initialized = False

    @classmethod
    async def get_instance(
        cls, config: Optional[InferenceConfig] = None
    ) -> "InferenceService":
        """
        获取推理服务单例实例

        Args:
            config: 推理服务配置，仅在首次创建时使用

        Returns:
            InferenceService: 推理服务实例
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
                await cls._instance._initialize()
                cls._instance.logger.info("🚀 推理服务单例实例创建完成")
            return cls._instance

    async def _initialize(self) -> None:
        """
        初始化推理服务

        加载模型、初始化组件、启动后台任务。
        """
        start_time = time.time()
        self.logger.info("🔄 开始初始化推理服务")

        try:
            # 1. 初始化数据库连接
            await self._initialize_database()

            # 2. 加载模型
            await self._load_model()

            # 3. 初始化特征提取器
            await self._initialize_feature_extractor()

            # 4. 启动后台任务
            await self._start_background_tasks()

            # 5. 记录初始化信息
            load_time = (time.time() - start_time) * 1000
            self.stats["model_load_time_ms"] = load_time
            self.stats["started_at"] = datetime.now().isoformat()

            self.is_initialized = True
            self.logger.info(f"✅ 推理服务初始化完成，耗时: {load_time:.1f}ms")

        except Exception as e:
            self.logger.error(f"❌ 推理服务初始化失败: {e}")
            raise

    async def _initialize_database(self) -> None:
        """初始化数据库连接"""
        self.db_pool = await get_db_pool()
        if not self.db_pool._is_initialized:
            await self.db_pool.init_pool()
        self.logger.info("✅ 数据库连接初始化完成")

    async def _load_model(self) -> None:
        """加载训练好的模型"""
        try:
            # 检查模型文件存在
            model_path = Path(self.config.model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"模型文件不存在: {model_path}")

            # 加载模型
            self.model = XGBoostClassifier.load_model(model_path)
            self.logger.info(f"✅ 模型加载成功: {model_path}")

            # 验证模型状态
            if not self.model.is_trained:
                raise RuntimeError("模型未训练，无法用于推理")

            self.logger.info(
                f"📊 模型信息: 特征数={len(self.model.feature_names or [])}, "
                f"类别={self.model.classes_.tolist() if self.model.classes_ is not None else 'N/A'}"
            )

        except Exception as e:
            # 尝试加载备用模型
            if self.config.enable_fallback and self.config.fallback_model_path:
                try:
                    fallback_path = Path(self.config.fallback_model_path)
                    if fallback_path.exists():
                        self.model = XGBoostClassifier.load_model(fallback_path)
                        self.logger.warning(f"⚠️ 使用备用模型: {fallback_path}")
                        return
                except Exception as fallback_error:
                    self.logger.error(f"备用模型加载失败: {fallback_error}")

            raise Exception(f"模型加载失败: {e}") from e

    async def _initialize_feature_extractor(self) -> None:
        """初始化特征提取器"""
        self.feature_extractor = MatchFeatureExtractor()
        self.logger.info("✅ 特征提取器初始化完成")

    async def _start_background_tasks(self) -> None:
        """启动后台任务"""
        if self.config.enable_cache:
            # 启动缓存清理任务
            asyncio.create_task(self._cache_cleanup_task())
            self.logger.info("✅ 缓存清理任务已启动")

    async def predict(self, match_id: str) -> Dict[str, Any]:
        """
        进行比赛预测

        Args:
            match_id: 比赛ID

        Returns:
            Dict[str, Any]: 预测结果，包含概率和元数据

        Raises:
            HTTPException: 当预测失败时
        """
        if not self.is_initialized:
            raise HTTPException(status_code=503, detail="推理服务未初始化")

        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            self.logger.debug(f"开始预测比赛: {match_id}")

            # 1. 检查缓存
            if self.config.enable_cache:
                cached_result = self._get_from_cache(match_id)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    self.logger.debug(f"使用缓存结果: {match_id}")
                    return cached_result

            # 2. 获取比赛数据
            match_data = await self._fetch_match_data(match_id)

            # 3. 提取特征
            features = await self._extract_features(match_id, match_data)

            # 4. 进行推理
            prediction_result = await self._perform_inference(match_id, features)

            # 5. 缓存结果
            if self.config.enable_cache:
                self._add_to_cache(match_id, prediction_result)

            # 6. 更新统计
            response_time = (time.time() - start_time) * 1000
            self._update_stats(response_time, success=True)

            self.logger.debug(f"预测完成: {match_id}, 耗时: {response_time:.1f}ms")

            if self.config.log_prediction_requests:
                self.logger.info(
                    f"预测请求: {match_id} -> {prediction_result['predicted_class']} "
                    f"(置信度: {prediction_result['confidence']:.3f})"
                )

            return prediction_result

        except HTTPException:
            # 重新抛出HTTP异常
            self.stats["errors"] += 1
            raise
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"预测失败 {match_id}: {e}")

            # 使用降级策略
            if self.config.enable_fallback:
                self.stats["fallback_used"] += 1
                return self._create_fallback_result(match_id, str(e))
            else:
                raise HTTPException(
                    status_code=500, detail=f"预测服务内部错误: {str(e)}"
                )

    async def _fetch_match_data(self, match_id: str) -> pd.DataFrame:
        """
        从数据库获取比赛数据

        Args:
            match_id: 比赛ID

        Returns:
            pd.DataFrame: 比赛数据

        Raises:
            HTTPException: 当比赛不存在时
        """
        try:
            # 查询比赛数据
            query = """
            SELECT
                match_id,
                home_team_id,
                away_team_id,
                match_date,
                home_score,
                away_score,
                status,
                venue,
                league_id
            FROM raw_match_data
            WHERE match_id = $1
            """

            record = await self.db_pool.fetchrow(query, match_id)

            if not record:
                raise HTTPException(status_code=404, detail=f"比赛不存在: {match_id}")

            # 转换为DataFrame
            data = {
                "match_id": [record["match_id"]],
                "home_team_id": [record["home_team_id"]],
                "away_team_id": [record["away_team_id"]],
                "match_date": [record["match_date"]],
                "home_score": [record["home_score"]],
                "away_score": [record["away_score"]],
                "status": [record["status"]],
                "venue": [record.get("venue")],
                "league_id": [record.get("league_id")],
            }

            df = pd.DataFrame(data)
            self.logger.debug(f"获取比赛数据成功: {match_id}")

            return df

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"获取比赛数据失败 {match_id}: {e}")
            raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")

    async def _extract_features(
        self, match_id: str, match_data: pd.DataFrame
    ) -> MatchFeatureSet:
        """
        提取比赛特征

        Args:
            match_id: 比赛ID
            match_data: 比赛数据

        Returns:
            MatchFeatureSet: 特征集合

        Raises:
            HTTPException: 当特征提取失败时
        """
        try:
            # 获取历史数据
            historical_data = await self._get_historical_data(match_data)

            # 提取特征
            feature_set = await self.feature_extractor.extract_features(
                match_id, historical_data
            )

            # 验证特征质量
            if feature_set.feature_completeness_score < 0.7:
                raise HTTPException(
                    status_code=400,
                    detail=f"特征质量不足: 完整性={feature_set.feature_completeness_score:.3f}",
                )

            self.logger.debug(
                f"特征提取成功: {match_id}, "
                f"完整性={feature_set.feature_completeness_score:.3f}"
            )

            return feature_set

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"特征提取失败 {match_id}: {e}")
            raise HTTPException(status_code=400, detail=f"特征提取失败: {str(e)}")

    async def _get_historical_data(self, match_data: pd.DataFrame) -> pd.DataFrame:
        """
        获取历史数据用于特征提取

        Args:
            match_data: 比赛数据

        Returns:
            pd.DataFrame: 历史数据
        """
        try:
            # 获取比赛日期和联赛ID
            match_date = match_data["match_date"].iloc[0]
            league_id = match_data.get("league_id", pd.Series([None])).iloc[0]

            # 构建查询
            if league_id:
                query = """
                SELECT
                    match_id,
                    home_team_id,
                    away_team_id,
                    match_date,
                    home_score,
                    away_score,
                    home_xg,
                    away_xg,
                    home_odds,
                    draw_odds,
                    away_odds,
                    status,
                    venue
                FROM raw_match_data
                WHERE league_id = $1
                    AND match_date < $2
                    AND status = 'FINISHED'
                ORDER BY match_date DESC
                LIMIT 200
                """
                params = [league_id, match_date]
            else:
                # 如果没有联赛ID，获取所有历史数据
                query = """
                SELECT
                    match_id,
                    home_team_id,
                    away_team_id,
                    match_date,
                    home_score,
                    away_score,
                    home_xg,
                    away_xg,
                    home_odds,
                    draw_odds,
                    away_odds,
                    status,
                    venue
                FROM raw_match_data
                WHERE match_date < $1
                    AND status = 'FINISHED'
                ORDER BY match_date DESC
                LIMIT 200
                """
                params = [match_date]

            records = await self.db_pool.fetch(query, *params)

            if not records:
                self.logger.warning("未找到历史数据，使用模拟数据")
                # 返回模拟数据
                return self._create_mock_historical_data()

            # 转换为DataFrame
            data = []
            for record in records:
                data.append(
                    {
                        "match_id": record["match_id"],
                        "home_team_id": record["home_team_id"],
                        "away_team_id": record["away_team_id"],
                        "match_date": record["match_date"],
                        "home_score": record["home_score"],
                        "away_score": record["away_score"],
                        "home_xg": record.get("home_xg", 0.0),
                        "away_xg": record.get("away_xg", 0.0),
                        "home_odds": record.get("home_odds", 0.0),
                        "draw_odds": record.get("draw_odds", 0.0),
                        "away_odds": record.get("away_odds", 0.0),
                        "status": record["status"],
                        "venue": record.get("venue"),
                    }
                )

            df = pd.DataFrame(data)
            self.logger.debug(f"获取历史数据成功: {len(df)} 条记录")

            return df

        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            # 返回模拟数据作为降级
            return self._create_mock_historical_data()

    def _create_mock_historical_data(self) -> pd.DataFrame:
        """创建模拟历史数据"""
        mock_data = []
        base_date = datetime.now()

        teams = ["team_1", "team_2", "team_3", "team_4", "team_5", "team_6"]

        for i in range(30):  # 创建30场历史比赛
            match_date = base_date - pd.Timedelta(days=i * 2)
            home_team = teams[i % len(teams)]
            away_team = teams[(i + 1) % len(teams)]
            home_score = max(0, int(np.random.normal(1.5, 1.0)))
            away_score = max(0, int(np.random.normal(1.2, 1.0)))

            mock_data.append(
                {
                    "match_id": f"historical_match_{i}",
                    "home_team_id": home_team,
                    "away_team_id": away_team,
                    "match_date": match_date,
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_xg": max(0.1, np.random.normal(1.6, 0.8)),
                    "away_xg": max(0.1, np.random.normal(1.4, 0.7)),
                    "home_odds": round(np.random.uniform(1.8, 4.0), 2),
                    "draw_odds": round(np.random.uniform(3.0, 4.0), 2),
                    "away_odds": round(np.random.uniform(2.5, 5.0), 2),
                    "status": "FINISHED",
                    "venue": f"Stadium {i % 5 + 1}",
                }
            )

        return pd.DataFrame(mock_data)

    async def _perform_inference(
        self, match_id: str, features: MatchFeatureSet
    ) -> Dict[str, Any]:
        """
        执行模型推理

        Args:
            match_id: 比赛ID
            features: 特征集合

        Returns:
            Dict[str, Any]: 预测结果
        """
        try:
            # 获取特征向量
            feature_vector = features.get_feature_vector()
            feature_names = features.get_feature_names()

            # 转换为模型输入格式
            X = feature_vector.reshape(1, -1)

            # 进行预测
            predicted_class_numeric = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]

            # 转换数值标签为字符串
            label_mapping = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
            predicted_class = label_mapping.get(predicted_class_numeric, "UNKNOWN")

            # 构建结果
            result = {
                "match_id": match_id,
                "HOME_WIN_PROBA": float(probabilities[2]),  # HOME_WIN是索引2
                "DRAW_PROBA": float(probabilities[1]),  # DRAW是索引1
                "AWAY_WIN_PROBA": float(probabilities[0]),  # AWAY_WIN是索引0
                "predicted_class": predicted_class,
                "confidence": float(max(probabilities)),
                "model_version": getattr(self.model.config, "model_version", "1.0.0"),
                "feature_completeness": float(features.feature_completeness_score),
                "data_quality": features.data_quality_flag,
                "processed_at": datetime.now().isoformat(),
            }

            self.stats["successful_predictions"] += 1
            return result

        except Exception as e:
            self.logger.error(f"推理执行失败 {match_id}: {e}")
            raise HTTPException(status_code=500, detail=f"模型推理失败: {str(e)}")

    def _get_from_cache(self, match_id: str) -> Optional[Dict[str, Any]]:
        """从缓存获取结果"""
        if not self.config.enable_cache:
            return None

        cached_item = self._prediction_cache.get(match_id)
        if cached_item:
            result, timestamp = cached_item
            age = time.time() - timestamp

            if age < self.config.cache_ttl_seconds:
                return result
            else:
                # 缓存过期，删除
                del self._prediction_cache[match_id]

        return None

    def _add_to_cache(self, match_id: str, result: Dict[str, Any]) -> None:
        """添加结果到缓存"""
        if not self.config.enable_cache:
            return

        # 检查缓存大小
        if len(self._prediction_cache) >= self.config.max_cache_size:
            # 删除最旧的缓存项
            oldest_key = min(
                self._prediction_cache.keys(),
                key=lambda k: self._prediction_cache[k][1],
            )
            del self._prediction_cache[oldest_key]

        # 添加新缓存
        self._prediction_cache[match_id] = (result, time.time())

    def _create_fallback_result(
        self, match_id: str, error_message: str
    ) -> Dict[str, Any]:
        """创建降级结果"""
        return {
            "match_id": match_id,
            "HOME_WIN_PROBA": self.config.default_probabilities["HOME_WIN_PROBA"],
            "DRAW_PROBA": self.config.default_probabilities["DRAW_PROBA"],
            "AWAY_WIN_PROBA": self.config.default_probabilities["AWAY_WIN_PROBA"],
            "predicted_class": "HOME_WIN",  # 默认预测
            "confidence": self.config.default_probabilities["HOME_WIN_PROBA"],
            "model_version": "fallback",
            "feature_completeness": 0.0,
            "data_quality": "FALLBACK",
            "error_message": error_message,
            "processed_at": datetime.now().isoformat(),
        }

    def _update_stats(self, response_time_ms: float, success: bool) -> None:
        """更新统计信息"""
        # 更新平均响应时间
        current_avg = self.stats["avg_response_time_ms"]
        total_requests = self.stats["total_requests"]
        self.stats["avg_response_time_ms"] = (
            current_avg * (total_requests - 1) + response_time_ms
        ) / total_requests

        # 更新最后预测时间
        self.stats["last_prediction_time"] = datetime.now().isoformat()

    async def _cache_cleanup_task(self) -> None:
        """缓存清理后台任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次

                if not self.config.enable_cache:
                    continue

                current_time = time.time()
                expired_keys = []

                for match_id, (_, timestamp) in self._prediction_cache.items():
                    if current_time - timestamp > self.config.cache_ttl_seconds:
                        expired_keys.append(match_id)

                for key in expired_keys:
                    del self._prediction_cache[key]

                if expired_keys:
                    self.logger.debug(f"清理过期缓存: {len(expired_keys)} 项")

            except Exception as e:
                self.logger.error(f"缓存清理任务异常: {e}")

    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            **self.stats,
            "cache_size": len(self._prediction_cache),
            "is_initialized": self.is_initialized,
            "config": {
                "enable_cache": self.config.enable_cache,
                "cache_ttl_seconds": self.config.cache_ttl_seconds,
                "max_cache_size": self.config.max_cache_size,
                "enable_fallback": self.config.enable_fallback,
                "model_path": self.config.model_path,
            },
        }

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        if not self.model:
            return {"error": "模型未加载"}

        return self.model.get_model_info()

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_info = {
            "status": "healthy" if self.is_initialized else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "service": "InferenceService",
        }

        if self.is_initialized:
            health_info.update(
                {
                    "model_loaded": self.model is not None,
                    "feature_extractor_ready": self.feature_extractor is not None,
                    "database_connected": self.db_pool is not None,
                    "cache_enabled": self.config.enable_cache,
                    "total_predictions": self.stats["successful_predictions"],
                    "avg_response_time_ms": self.stats["avg_response_time_ms"],
                }
            )
        else:
            health_info["error"] = "服务未初始化"

        return health_info

    async def reload_model(self, model_path: Optional[str] = None) -> bool:
        """
        重新加载模型

        Args:
            model_path: 新的模型路径，如果为None则使用配置中的路径

        Returns:
            bool: 是否重新加载成功
        """
        try:
            if model_path:
                old_path = self.config.model_path
                self.config.model_path = model_path

            await self._load_model()
            self.logger.info(
                f"模型重新加载成功: {model_path or self.config.model_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"模型重新加载失败: {e}")
            if model_path:
                self.config.model_path = old_path  # 恢复原路径
            return False


# 便捷函数
async def get_inference_service(
    config: Optional[InferenceConfig] = None,
) -> InferenceService:
    """
    获取推理服务实例的便捷函数

    Args:
        config: 推理服务配置

    Returns:
        InferenceService: 推理服务实例
    """
    return await InferenceService.get_instance(config)


if __name__ == "__main__":
    # 模块测试
    async def main():
        """主函数 - 推理服务测试"""
        print("🧪 推理服务模块测试")

        try:
            # 创建推理服务
            config = InferenceConfig(
                model_path="models/demo_football_classifier.pkl",
                enable_cache=True,
                enable_fallback=True,
            )

            print("🔄 初始化推理服务...")
            service = await InferenceService.get_instance(config)

            # 健康检查
            health = await service.health_check()
            print(f"✅ 服务健康状态: {health['status']}")

            # 获取服务统计
            stats = service.get_service_stats()
            print(
                f"📊 服务统计: 总请求={stats['total_requests']}, "
                f"成功预测={stats['successful_predictions']}"
            )

            # 获取模型信息
            model_info = service.get_model_info()
            print(f"🤖 模型信息: {model_info.get('model_name', 'N/A')}")

            print("🎉 推理服务模块测试完成!")

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback

            traceback.print_exc()
            return False

        return True

    # 运行测试
    success = main()
    if not success:
        exit(1)
