"""
模型预测服务 / Model Prediction Service

提供实时比赛预测功能，支持：
- 从MLflow加载最新生产模型
- 实时特征获取和预测
- 预测结果存储到数据库
- Prometheus指标导出
- 带TTL的缓存机制
- MLflow服务调用重试机制

Provides real-time match prediction functionality, including:
- Loading latest production model from MLflow
- Real-time feature retrieval and prediction
- Storing prediction results to database
- Prometheus metrics export
- TTL-based caching mechanism
- MLflow service call retry mechanism

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口。
建议使用：from src.models.prediction import <class_name>

主要类 / Main Classes:
    PredictionService: 核心预测服务类 / Core prediction service class
    PredictionResult: 预测结果数据类 / Prediction result data class

主要方法 / Main Methods:
    PredictionService.predict_match(): 对单场比赛进行预测 / Predict single match
    PredictionService.batch_predict_matches(): 批量预测比赛 / Batch predict matches
    PredictionService.verify_prediction(): 验证预测结果 / Verify prediction results

使用示例 / Usage Example:
    ```python
    from src.models.prediction_service_mod import PredictionService

    service = PredictionService(mlflow_tracking_uri="http://localhost:5002")
    result = await service.predict_match(12345)
    logger.info(f"预测结果: {result.predicted_result}")
    ```

环境变量 / Environment Variables:
    MLFLOW_TRACKING_URI: MLflow跟踪服务器URI，默认为http://localhost:5002
                     MLflow tracking server URI, defaults to http://localhost:5002
    MODEL_CACHE_TTL_HOURS: 模型缓存TTL小时数，默认为1
                      Model cache TTL in hours, defaults to 1
    PREDICTION_CACHE_TTL_MINUTES: 预测结果缓存TTL分钟数，默认为30
                              Prediction result cache TTL in minutes, defaults to 30
    MLFLOW_RETRY_MAX_ATTEMPTS: MLflow重试最大尝试次数，默认3
                          MLflow retry max attempts, default 3
    MLFLOW_RETRY_BASE_DELAY: MLflow重试基础延迟秒数，默认2.0
                         MLflow retry base delay in seconds, default 2.0

依赖 / Dependencies:
    - mlflow: 模型管理和跟踪 / Model management and tracking
    - scikit-learn: 机器学习模型加载 / Machine learning model loading
    - sqlalchemy: 数据库操作 / Database operations
    - src.cache.ttl_cache: TTL缓存管理 / TTL cache management
    - src.utils.retry: 重试机制 / Retry mechanism

重构历史 / Refactoring History:
    - 原始文件：1118行，包含所有预测相关功能
    - 重构为模块化结构：
      - models.py: 预测结果数据模型
      - metrics.py: Prometheus监控指标
      - cache.py: 预测缓存管理
      - mlflow_client.py: MLflow客户端封装
      - feature_processor.py: 特征处理器
      - service.py: 核心预测服务
"""

# 为了向后兼容性，从新的模块化结构中导入所有内容
from .prediction import (PredictionCache,  # 数据模型; 核心服务; 缓存; 监控指标
                         PredictionResult, PredictionService, cache_hit_ratio,
                         model_load_duration_seconds, prediction_accuracy,
                         prediction_duration_seconds, predictions_total)

# 重新导出以保持原始接口
__all__ = [
    # 数据模型
    "PredictionResult",
    # 核心服务
    "PredictionService",
    # 缓存
    "PredictionCache",
    # 监控指标
    "predictions_total",
    "prediction_duration_seconds",
    "prediction_accuracy",
    "model_load_duration_seconds",
    "cache_hit_ratio",
]

# 原始实现已移至 src/models/prediction/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有功能：
# - PredictionResult: 预测结果数据类
# - PredictionService: 核心预测服务类
#   - predict_match: 预测单场比赛
#   - batch_predict_matches: 批量预测比赛
#   - verify_prediction: 验证预测结果
#   - get_prediction_statistics: 获取预测统计信息
# - PredictionCache: 预测缓存管理器
# - MLflowModelClient: MLflow客户端封装
# - FeatureProcessor: 特征处理器
# - Prometheus监控指标：predictions_total, prediction_duration_seconds等
