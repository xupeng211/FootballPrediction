# 核心模块命名规范

## 概述
本文档定义了 Football Prediction System 核心模块的正式命名规范，确保代码的一致性和可维护性。

## 核心服务模块命名

### 1. 推理服务 (Inference Service)
```python
# ✅ 正确命名
from src.services.inference_service import InferenceService

# 实例化
inference_service = InferenceService()

# 测试Mock
mock_inference_service = AsyncMock()

# 配置
inference_service_config = {
    "model_path": "/app/models/xgboost_v2.pkl",
    "cache_enabled": True,
    "timeout_seconds": 10.0
}

# ❌ 错误命名 (已废弃)
InferenceServiceV2      # 不要使用
InferenceServiceV3      # 不要使用
inference_service_v2    # 不要使用
```

### 2. 数据收集服务 (Collection Service)
```python
# ✅ 正确命名
from src.services.collection_service import CollectionService, FotMobCollectionService

# 实例化
collection_service = CollectionService()
fotmob_service = FotMobCollectionService()

# 任务类
collection_task = FotMobCollectionTask(
    match_id="match_001",
    data_type="l2_features"
)

# ❌ 错误命名
DataCollectorService     # 使用CollectionService
FotMobCollector          # 使用FotMobCollectionService
```

### 3. 可解释性服务 (Explainability Service)
```python
# ✅ 正确命名
from src.services.explainability_service import ExplainabilityService

# 实例化
explainability_service = ExplainabilityService()

# 方法调用
explanations = await explainability_service.explain_prediction(
    match_features=features,
    prediction_result=prediction,
    model_name="xgboost_v2"
)
```

### 4. 基础服务 (Base Service)
```python
# ✅ 正确命名
from src.services.base_service import BaseService

# 继承
class CustomService(BaseService):
    def __init__(self, name: str):
        super().__init__(name=name)
        # 自定义初始化

# 生命周期管理
async with CustomService("my_service") as service:
    await service.do_work()
```

### 5. 服务管理器 (Service Manager)
```python
# ✅ 正确命名
from src.services.service_manager import ServiceManager

# 实例化
service_manager = ServiceManager()

# 服务注册
await service_manager.register_service("inference", InferenceService())

# 批量初始化
await service_manager.initialize_all()
```

## ML推理层命名

### 1. 模型加载器 (Model Loader)
```python
# ✅ 正确命名
from src.ml.inference.model_loader import ModelLoader, ModelLoadError

# 实例化
model_loader = ModelLoader(
    cache_directory="/app/models",
    max_cache_size=100
)

# 加载模型
model = await model_loader.load_model("xgboost_v2")

# 异常处理
try:
    model = await model_loader.load_model("nonexistent_model")
except ModelLoadError as e:
    logger.error(f"Failed to load model: {e}")
```

### 2. 预测器 (Predictor)
```python
# ✅ 正确命名
from src.ml.inference.predictor import MatchPredictor, PredictionError

# 实例化
match_predictor = MatchPredictor(
    model_loader=model_loader,
    cache_manager=cache_manager
)

# 预测
result = await match_predictor.predict(features)

# 异常处理
try:
    result = await match_predictor.predict(invalid_features)
except PredictionError as e:
    logger.error(f"Prediction failed: {e}")
```

### 3. 缓存管理器 (Cache Manager)
```python
# ✅ 正确命名
from src.ml.inference.cache_manager import PredictionCache

# 实例化
prediction_cache = PredictionCache(
    max_size=1000,
    ttl_seconds=300
)

# 缓存操作
await prediction_cache.set(cache_key, prediction_result)
cached_result = await prediction_cache.get(cache_key)

# 清理
await prediction_cache.clear_all()
```

## 特征工程命名

### 1. 特征提取器 (Feature Extractor)
```python
# ✅ 正确命名
from src.ml.features.extractor import MatchFeatureExtractor

# 实例化
feature_extractor = MatchFeatureExtractor()

# 特征提取
features = await feature_extractor.extract_features(
    match_id="match_001",
    historical_data=data
)

# 高级特征转换器
from src.ml.features.advanced_feature_transformer import AdvancedFeatureTransformer
advanced_transformer = AdvancedFeatureTransformer()
transformed_features = await advanced_transformer.transform_features(raw_features)
```

### 2. 专业计算器
```python
# ✅ 正确命名
from src.ml.features.h2h_calculator import H2HCalculator, H2HStats
from src.ml.features.venue_analyzer import VenueAnalyzer
from src.ml.features.poisson_features import PoissonFeatureCalculator
from src.ml.features.elo_rating_system import EloRatingSystem

# 实例化
h2h_calculator = H2HCalculator(min_matches=5)
venue_analyzer = VenueAnalyzer()
poisson_calculator = PoissonFeatureCalculator()
elo_system = EloRatingSystem()

# 使用
h2h_stats = await h2h_calculator.calculate_h2h_stats(team_a, team_b, match_date)
venue_advantage = await venue_analyzer.analyze_venue_impact(home_team, venue)
poisson_features = await poisson_calculator.calculate_poisson_features(match_data)
elo_ratings = await elo_system.update_ratings(match_results)
```

## 数据库层命名

### 1. 连接管理
```python
# ✅ 正确命名
from src.database.connection import DatabaseConnection
from src.database.db_pool import DatabasePool

# 实例化
db_connection = DatabaseConnection(connection_string)
db_pool = DatabasePool(min_connections=5, max_connections=20)

# 使用
async with db_pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM matches")
```

### 2. 配置管理
```python
# ✅ 正确命名
from src.database.config import DatabaseConfig

# 实例化
db_config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="football_prediction",
    user="football_user",
    password="football_pass"
)

# 连接字符串
connection_string = db_config.get_connection_string()
```

## API层命名

### 1. 路由命名
```python
# ✅ 正确命名
from src.api.health import health_router
from src.api.predictions.predict_router import prediction_router

# FastAPI应用
from src.main import app

# 注册路由
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(prediction_router, prefix="/predictions", tags=["predictions"])
```

### 2. 模式定义
```python
# ✅ 正确命名
from src.api.schemas import (
    PredictionRequest,
    PredictionResponse,
    HealthCheckResponse,
    ServiceCheck
)

# 使用
prediction_request = PredictionRequest(
    home_team="Manchester United",
    away_team="Arsenal",
    model_name="xgboost_v2"
)
```

## 配置模块命名

### 1. 安全配置
```python
# ✅ 正确命名
from src.config_secure import get_settings, Settings

# 获取配置
settings = get_settings()

# 访问配置
db_config = settings.database
api_config = settings.api
ml_config = settings.ml

# ❌ 错误命名 (已废弃)
from src.config import Settings     # 使用config_secure
```

### 2. 环境变量命名
```bash
# ✅ 正确的环境变量命名
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=football_user
DB_PASSWORD=football_pass

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

MODEL_PATH=/app/models/xgboost_v2.pkl
INFERENCE_SERVICE_V2_ENABLED=true

# ❌ 错误的环境变量命名
DATABASE_HOST=localhost     # 使用DB_HOST
REDIS_ADDR=localhost         # 使用REDIS_HOST
SERVICE_PORT=8000            # 使用API_PORT
```

## 工具和常量命名

### 1. 业务常量
```python
# ✅ 正确的常量命名
from src.constants import (
    FOOTBALL,
    PROBABILITY,
    STATISTICAL,
    VALIDATOR,
    MATH
)

# 使用
result_mapping = FOOTBALL.RESULT_MAPPING
prob_epsilon = PROBABILITY.PROBABILITY_EPSILON
min_sample_size = STATISTICAL.MIN_RELIABLE_SAMPLE_SIZE
```

### 2. 工具函数
```python
# ✅ 正确的工具命名
from src.utils import (
    validate_team_name,
    normalize_team_name,
    calculate_confidence,
    format_prediction_output
)

# 使用
is_valid = validate_team_name("Manchester United")
normalized = normalize_team_name("manchester united")
confidence = calculate_confidence(probabilities)
output = format_prediction_output(prediction_result)
```

## 测试命名规范

### 1. 测试类命名
```python
# ✅ 正确的测试类命名
class TestInferenceService:
    """推理服务测试"""
    pass

class TestModelLoader:
    """模型加载器测试"""
    pass

class TestH2HCalculator:
    """历史交锋计算器测试"""
    pass

# ❌ 错误的测试类命名
class InferenceServiceTest:        # 使用TestInferenceService
class TestInferenceServiceV2:     # 不要包含版本号
class test_model_loader:           # 类名使用PascalCase
```

### 2. 测试方法命名
```python
# ✅ 正确的测试方法命名
def test_inference_service_initialization():
    """测试推理服务初始化"""
    pass

def test_model_loader_load_model_success():
    """测试模型加载成功场景"""
    pass

def test_h2h_calculator_insufficient_matches():
    """测试历史交锋计算器不足场次场景"""
    pass

async def test_async_prediction_workflow():
    """测试异步预测工作流"""
    pass

# ❌ 错误的测试方法命名
def test_service():                    # 太笼统
def test_model_loader():               # 不够具体
def test_good():                       # 不描述测试内容
def TestAsyncWorkflow():                # 方法名使用snake_case
```

## 文件命名规范

### 1. 源代码文件
```python
# ✅ 正确的文件命名
src/services/inference_service.py
src/ml/inference/predictor.py
src/ml/features/h2h_calculator.py
src/api/health.py
src/config_secure.py

# ❌ 错误的文件命名
src/services/inference_service_v2.py     # 不要包含版本号
src/ml/inference/Predictor.py            # 使用snake_case
src/Health.py                             # 使用snake_case
src/config.py                              # 使用config_secure.py
```

### 2. 测试文件
```python
# ✅ 正确的测试文件命名
tests/unit/test_inference_service.py
tests/unit/test_model_loader.py
tests/integration/test_service_integration.py
tests/e2e/test_prediction_workflow.py

# ❌ 错误的测试文件命名
tests/unit/InferenceServiceTest.py       # 使用snake_case加test_前缀
tests/integration/service_test.py         # 不够具体
tests/e2e/prediction.py                  # 添加test_前缀
```

## 命名约定总结

### 1. 模块和类名
- 使用PascalCase（首字母大写）
- 避免版本号后缀（V2, v3等）
- 使用描述性的名称

### 2. 函数和方法名
- 使用snake_case（小写下划线）
- 以动词开头，描述功能
- 测试方法以test_开头

### 3. 变量和常量
- 变量使用snake_case
- 常量使用UPPER_CASE
- 使用描述性名称

### 4. 文件和目录
- 使用snake_case
- 避免版本号和时间戳
- 测试文件以test_开头

## 迁移指南

### 从旧命名到新命名
```python
# 旧命名 (需要迁移)
InferenceServiceV2 -> InferenceService
inference_service_v2.py -> inference_service.py
test_inference_v2.py -> test_inference_service.py

# 新命名 (推荐)
InferenceService
inference_service.py
test_inference_service.py
```

这个命名规范确保了代码的一致性、可读性和可维护性。所有新代码都应该遵循这个规范，现有代码应该逐步迁移。