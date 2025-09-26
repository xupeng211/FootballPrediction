# API Documentation Style Guide

## 1. General Principles

1. **Bilingual Documentation**: All public APIs and major components should have both Chinese and English documentation.
2. **Consistent Structure**: Follow a consistent structure for all docstrings and API documentation.
3. **Clear Examples**: Provide clear usage examples where appropriate.
4. **Type Annotations**: Use proper type annotations in Python code.

## 2. Docstring Format Standards

### 2.1 Class Docstrings

```python
class PredictionService:
    """
    预测服务 / Prediction Service

    提供实时比赛预测功能，支持：
    - 从MLflow加载最新生产模型
    - 实时特征获取和预测
    - 预测结果存储到数据库
    - Prometheus指标导出

    Provides real-time match prediction functionality, including:
    - Loading latest production model from MLflow
    - Real-time feature retrieval and prediction
    - Storing prediction results to database
    - Prometheus metrics export
    """

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5002"):
        """
        初始化预测服务 / Initialize Prediction Service

        Args:
            mlflow_tracking_uri (str): MLflow跟踪服务器URI / MLflow tracking server URI
                Defaults to "http://localhost:5002"

        Attributes:
            db_manager (DatabaseManager): 数据库管理器实例 / Database manager instance
            feature_store (FootballFeatureStore): 特征存储实例 / Feature store instance
            mlflow_tracking_uri (str): MLflow跟踪URI / MLflow tracking URI
            metrics_exporter (ModelMetricsExporter): 指标导出器实例 / Metrics exporter instance
        """
```

### 2.2 Method Docstrings

```python
    async def predict_match(self, match_id: int) -> PredictionResult:
        """
        对指定比赛进行实时预测 / Predict match result in real-time

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            PredictionResult: 包含预测结果的预测对象 / Prediction object containing results
                - match_id (int): 比赛ID / Match ID
                - model_version (str): 模型版本 / Model version
                - home_win_probability (float): 主队获胜概率 (0-1) / Home win probability (0-1)
                - draw_probability (float): 平局概率 (0-1) / Draw probability (0-1)
                - away_win_probability (float): 客队获胜概率 (0-1) / Away win probability (0-1)
                - predicted_result (str): 预测结果 ('home', 'draw', 'away') / Predicted result
                - confidence_score (float): 预测置信度 (0-1) / Prediction confidence score

        Raises:
            ValueError: 当比赛不存在时抛出 / Raised when match does not exist
            Exception: 当预测过程发生错误时抛出 / Raised when prediction process fails

        Example:
            ```python
            service = PredictionService()
            result = await service.predict_match(12345)
            print(f"预测结果: {result.predicted_result}, 置信度: {result.confidence_score}")
            ```

        Note:
            该方法会自动从特征存储获取最新特征并使用生产模型进行预测。
            This method automatically retrieves latest features from feature store and uses
            production model for prediction.
        """
```

### 2.3 Data Class Docstrings

```python
@dataclass
class PredictionResult:
    """
    预测结果数据类 / Prediction Result Data Class

    存储比赛预测的完整结果，包括概率、置信度和元数据。
    Stores complete match prediction results including probabilities, confidence scores and metadata.

    Attributes:
        match_id (int): 比赛唯一标识符 / Unique match identifier
        model_version (str): 使用的模型版本 / Model version used
        model_name (str): 模型名称，默认为"football_baseline_model" / Model name, defaults to "football_baseline_model"
        home_win_probability (float): 主队获胜概率，范围0-1 / Home win probability, range 0-1
        draw_probability (float): 平局概率，范围0-1 / Draw probability, range 0-1
        away_win_probability (float): 客队获胜概率，范围0-1 / Away win probability, range 0-1
        predicted_result (str): 预测结果，'home'/'draw'/'away' / Predicted result, 'home'/'draw'/'away'
        confidence_score (float): 预测置信度，范围0-1 / Prediction confidence score, range 0-1
        features_used (Optional[Dict[str, Any]]): 使用的特征字典 / Dictionary of features used
        prediction_metadata (Optional[Dict[str, Any]]): 预测元数据 / Prediction metadata
        created_at (Optional[datetime]): 预测创建时间 / Prediction creation time
        actual_result (Optional[str]): 实际比赛结果 / Actual match result
        is_correct (Optional[bool]): 预测是否正确 / Whether prediction is correct
        verified_at (Optional[datetime]): 验证时间 / Verification time
    """
```

## 3. API Documentation Standards

### 3.1 FastAPI Endpoint Documentation

```python
@router.get(
    "/{match_id}",
    summary="获取比赛预测结果 / Get Match Prediction",
    description="获取指定比赛的预测结果，如果不存在则实时生成 / Get prediction result for specified match, generate in real-time if not exists",
    responses={
        200: {
            "description": "成功获取预测结果 / Successfully retrieved prediction",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "match_id": 12345,
                            "match_info": {
                                "match_id": 12345,
                                "home_team_id": 10,
                                "away_team_id": 20,
                                "league_id": 1,
                                "match_time": "2025-09-15T15:00:00",
                                "match_status": "scheduled",
                                "season": "2024-25"
                            },
                            "prediction": {
                                "model_version": "1.0",
                                "home_win_probability": 0.45,
                                "draw_probability": 0.30,
                                "away_win_probability": 0.25,
                                "predicted_result": "home",
                                "confidence_score": 0.45
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "比赛不存在 / Match not found"},
        500: {"description": "服务器内部错误 / Internal server error"}
    }
)
async def get_match_prediction(
    match_id: int = Path(
        ...,
        description="比赛唯一标识符 / Unique match identifier",
        ge=1,
        example=12345
    ),
    force_predict: bool = Query(
        default=False,
        description="是否强制重新预测 / Whether to force re-prediction"
    ),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    获取指定比赛的预测结果 / Get Prediction for Specified Match

    该端点首先检查数据库中是否存在该比赛的缓存预测结果。
    如果存在且未设置force_predict参数，则直接返回缓存结果。
    否则，实时生成新的预测结果并存储到数据库。

    This endpoint first checks if there's a cached prediction result for the match in the database.
    If it exists and force_predict is not set, it returns the cached result directly.
    Otherwise, it generates a new prediction in real-time and stores it in the database.

    Args:
        match_id (int): 比赛唯一标识符，必须大于0 / Unique match identifier, must be greater than 0
        force_predict (bool): 是否强制重新预测，默认为False / Whether to force re-prediction, defaults to False
        session (AsyncSession): 数据库会话，由依赖注入提供 / Database session, provided by dependency injection

    Returns:
        Dict[str, Any]: API响应字典 / API response dictionary
            - success (bool): 请求是否成功 / Whether request was successful
            - data (Dict): 预测数据 / Prediction data
                - match_id (int): 比赛ID / Match ID
                - match_info (Dict): 比赛信息 / Match information
                - prediction (Dict): 预测结果 / Prediction result

    Raises:
        HTTPException:
            - 404: 当比赛不存在时 / When match does not exist
            - 500: 当预测过程发生错误时 / When prediction process fails
    """
```

## 4. Module Documentation

### 4.1 Module-Level Docstrings

```python
"""
模型预测服务 / Model Prediction Service

提供实时比赛预测功能，支持：
- 从MLflow加载最新生产模型
- 实时特征获取和预测
- 预测结果存储到数据库
- Prometheus指标导出

Provides real-time match prediction functionality, including:
- Loading latest production model from MLflow
- Real-time feature retrieval and prediction
- Storing prediction results to database
- Prometheus metrics export

主要类 / Main Classes:
    PredictionService: 核心预测服务类 / Core prediction service class
    PredictionResult: 预测结果数据类 / Prediction result data class

主要方法 / Main Methods:
    PredictionService.predict_match(): 对单场比赛进行预测 / Predict single match
    PredictionService.batch_predict_matches(): 批量预测比赛 / Batch predict matches
    PredictionService.verify_prediction(): 验证预测结果 / Verify prediction results

使用示例 / Usage Example:
    ```python
    from src.models.prediction_service import PredictionService

    service = PredictionService(mlflow_tracking_uri="http://localhost:5002")
    result = await service.predict_match(12345)
    print(f"预测结果: {result.predicted_result}")
    ```

环境变量 / Environment Variables:
    MLFLOW_TRACKING_URI: MLflow跟踪服务器URI，默认为http://localhost:5002
                     MLflow tracking server URI, defaults to http://localhost:5002

依赖 / Dependencies:
    - mlflow: 模型管理和跟踪 / Model management and tracking
    - scikit-learn: 机器学习模型加载 / Machine learning model loading
    - sqlalchemy: 数据库操作 / Database operations
"""
```

## 5. Best Practices

1. **Consistency**: Maintain consistent terminology and structure across all documentation
2. **Brevity**: Keep descriptions concise but informative
3. **Examples**: Include practical examples where beneficial
4. **Cross-references**: Link related components and functions
5. **Versioning**: Document API version and compatibility
6. **Error Handling**: Clearly document possible exceptions and error conditions
7. **Performance Notes**: Include performance considerations where relevant
