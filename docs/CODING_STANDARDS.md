# 📝 编码规范

## 📋 概述
本文档定义了足球预测系统的编码规范和最佳实践，确保代码质量和团队协作效率。

## 🐍 Python编码规范

### 基础规范 (PEP 8)
- **行长度**: 最大88字符 (Black格式化器标准)
- **缩进**: 4个空格，不使用制表符
- **空行**: 类和函数之间使用2个空行，类方法之间使用1个空行
- **导入**: 每行一个导入，标准库 → 第三方库 → 本地模块

### 命名规范
```python
# 变量和函数 - snake_case
user_name = "john"
def calculate_prediction():
    pass

# 常量 - UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# 类 - PascalCase
class PredictionService:
    pass

# 私有成员 - 前缀下划线
class User:
    def __init__(self):
        self._private_field = "private"
        self.__very_private = "very private"

# 模块级别常量
API_BASE_URL = "https://api.example.com"
DATABASE_URL = "postgresql://localhost/football"
```

### 类型注解
```python
from typing import List, Dict, Optional, Union
from uuid import UUID

# 函数类型注解
def create_prediction(
    match_id: int,
    user_id: UUID,
    prediction_data: Dict[str, Union[str, int]]
) -> Optional[Prediction]:
    """创建新的预测记录"""
    pass

# 类属性类型注解
class Prediction:
    id: UUID
    match_id: int
    user_id: UUID
    result: Optional[str]

# 复杂类型使用TypeAlias
PredictionData = Dict[str, Union[str, int, float]]
APIResponse = Dict[str, Union[bool, str, List[Dict]]]
```

## 🏗️ 项目结构规范

### 目录组织
```
src/
├── domain/           # 领域层
│   ├── entities/     # 实体
│   ├── services/     # 领域服务
│   ├── strategies/   # 策略模式
│   └── events/       # 领域事件
├── api/              # 应用层
│   ├── routes/       # API路由
│   ├── middleware/   # 中间件
│   └── dependencies/ # 依赖注入
├── database/         # 数据访问层
│   ├── models/       # 数据模型
│   ├── repositories/ # 仓储实现
│   └── migrations/   # 数据库迁移
├── services/         # 应用服务
├── cache/            # 缓存层
└── core/             # 核心配置
```

### 模块导入规范
```python
# 标准库导入
import os
import sys
from typing import List, Dict, Optional

# 第三方库导入
from fastapi import FastAPI, HTTPException
from sqlalchemy import Column, Integer, String
import redis

# 本地模块导入
from src.domain.entities.prediction import Prediction
from src.api.routes.predictions import router
from src.database.models.base import BaseModel
```

## 🧪 测试规范

### 测试文件组织
```
tests/
├── unit/             # 单元测试
│   ├── domain/       # 领域层测试
│   ├── api/          # API层测试
│   └── services/     # 服务层测试
├── integration/      # 集成测试
├── e2e/             # 端到端测试
└── conftest.py      # pytest配置
```

### 测试命名规范
```python
# 测试类和函数命名
class TestPredictionService:
    def test_create_prediction_success(self):
        """测试成功创建预测"""
        pass

    def test_create_prediction_with_invalid_data_should_raise_error(self):
        """测试无效数据创建预测应该抛出错误"""
        pass

    def test_get_prediction_by_id_when_not_found_should_return_none(self):
        """测试根据ID获取预测，当不存在时返回None"""
        pass
```

### 测试结构 (AAA模式)
```python
def test_prediction_crud_operations():
    # Arrange - 准备测试数据
    prediction_data = {
        "match_id": 123,
        "user_id": "user-123",
        "prediction": "home_win"
    }
    service = PredictionService()

    # Act - 执行操作
    created_prediction = service.create_prediction(prediction_data)
    retrieved_prediction = service.get_prediction(created_prediction.id)

    # Assert - 验证结果
    assert created_prediction is not None
    assert retrieved_prediction.id == created_prediction.id
    assert retrieved_prediction.prediction == "home_win"
```

## 📝 文档字符串规范

### Google风格文档字符串
```python
def calculate_prediction_accuracy(
    predictions: List[Prediction],
    actual_results: Dict[int, str]
) -> float:
    """计算预测准确率

    Args:
        predictions: 预测记录列表
        actual_results: 实际比赛结果字典，键为match_id，值为结果

    Returns:
        预测准确率，范围0.0-1.0

    Raises:
        ValueError: 当predictions为空或actual_results为空时

    Example:
        >>> predictions = [Prediction(match_id=1, result="home_win")]
        >>> results = {1: "home_win"}
        >>> calculate_prediction_accuracy(predictions, results)
        1.0
    """
    if not predictions or not actual_results:
        raise ValueError("预测数据和实际结果不能为空")

    correct_predictions = sum(
        1 for p in predictions
        if actual_results.get(p.match_id) == p.result
    )
    return correct_predictions / len(predictions)
```

### 类文档字符串
```python
class PredictionStrategy:
    """预测策略基类

    定义了预测策略的通用接口，所有具体策略都应该继承此类。

    Attributes:
        name: 策略名称
        version: 策略版本
        config: 策略配置

    Example:
        >>> strategy = MLPredictionStrategy("ml_v1")
        >>> prediction = strategy.predict(match_data, team_data)
    """

    def __init__(self, name: str, version: str = "1.0"):
        """初始化预测策略

        Args:
            name: 策略名称
            version: 策略版本，默认为"1.0"
        """
        self.name = name
        self.version = version
        self.config = {}

    def predict(
        self,
        match_data: Dict,
        team_data: Dict
    ) -> Dict[str, float]:
        """执行预测

        Args:
            match_data: 比赛数据
            team_data: 球队数据

        Returns:
            预测结果字典，包含各结果的概率

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现predict方法")
```

## 🔧 异常处理规范

### 异常类定义
```python
# 自定义异常类
class PredictionError(Exception):
    """预测相关错误的基类"""
    pass

class InvalidPredictionDataError(PredictionError):
    """无效预测数据错误"""
    pass

class PredictionNotFoundError(PredictionError):
    """预测记录未找到错误"""
    pass
```

### 异常处理模式
```python
# 1. 具体异常处理
try:
    prediction = service.create_prediction(data)
except InvalidPredictionDataError as e:
    logger.error(f"预测数据无效: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseError as e:
    logger.error(f"数据库错误: {e}")
    raise HTTPException(status_code=500, detail="内部服务器错误")

# 2. 资源管理 - 使用context manager
def process_large_dataset(file_path: str):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            # 处理数据...
    except FileNotFoundError:
        logger.error(f"文件未找到: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        raise ValueError(f"无效的JSON文件: {e}")

# 3. 异常链 - 保持原始异常信息
try:
    result = external_api_call()
except ExternalAPIError as e:
    logger.error(f"外部API调用失败")
    raise PredictionError("预测服务不可用") from e
```

## 🗄️ 数据库操作规范

### SQLAlchemy模型定义
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

class Prediction(BaseModel):
    """预测模型"""
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(Integer, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    prediction = Column(String(50), nullable=False)
    confidence = Column(Integer, nullable=False)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    user = relationship("User", back_populates="predictions")

    def __repr__(self):
        return f"<Prediction(id={self.id}, match_id={self.match_id})>"
```

### 仓储模式实现
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy.orm import Session

class PredictionRepository(ABC):
    """预测仓储接口"""

    @abstractmethod
    def create(self, prediction_data: Dict) -> Prediction:
        pass

    @abstractmethod
    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        pass

    @abstractmethod
    def get_by_user(self, user_id: UUID) -> List[Prediction]:
        pass

class SQLAlchemyPredictionRepository(PredictionRepository):
    """基于SQLAlchemy的预测仓储实现"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create(self, prediction_data: Dict) -> Prediction:
        prediction = Prediction(**prediction_data)
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        return self.db.query(Prediction).filter(
            Prediction.id == prediction_id
        ).first()
```

## 🚀 API设计规范

### FastAPI路由定义
```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.post("/",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新预测",
    description="为指定比赛创建预测记录"
)
async def create_prediction(
    request: CreatePredictionRequest,
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> PredictionResponse:
    """创建预测"""
    try:
        prediction = await prediction_service.create_prediction(
            match_id=request.match_id,
            user_id=current_user.id,
            prediction_data=request.dict()
        )
        return PredictionResponse.from_entity(prediction)
    except InvalidPredictionDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### Pydantic模型定义
```python
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class CreatePredictionRequest(BaseModel):
    """创建预测请求模型"""
    match_id: int
    prediction: str  # "home_win", "away_win", "draw"
    confidence: int  # 0-100

    @validator('prediction')
    def validate_prediction(cls, v):
        allowed_values = ["home_win", "away_win", "draw"]
        if v not in allowed_values:
            raise ValueError(f"预测结果必须是: {allowed_values}")
        return v

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("置信度必须在0-100之间")
        return v

class PredictionResponse(BaseModel):
    """预测响应模型"""
    id: UUID
    match_id: int
    prediction: str
    confidence: int
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, prediction: Prediction) -> "PredictionResponse":
        return cls(
            id=prediction.id,
            match_id=prediction.match_id,
            prediction=prediction.prediction,
            confidence=prediction.confidence,
            created_at=prediction.created_at
        )
```

## 🔍 日志记录规范

### 日志级别使用
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG - 详细的调试信息
logger.debug(f"处理预测请求: {prediction_data}")

# INFO - 一般信息记录
logger.info(f"用户 {user_id} 创建了预测 {prediction_id}")

# WARNING - 警告信息
logger.warning(f"预测数据缺少置信度，使用默认值: {default_confidence}")

# ERROR - 错误信息
logger.error(f"创建预测失败: {error_message}")

# CRITICAL - 严重错误
logger.critical(f"数据库连接失败: {connection_error}")
```

### 结构化日志
```python
import json
from datetime import datetime

def log_prediction_event(event_type: str, prediction_id: UUID, **kwargs):
    """记录预测相关事件"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "prediction_id": str(prediction_id),
        **kwargs
    }
    logger.info(f"Prediction event: {json.dumps(log_data)}")

# 使用示例
log_prediction_event(
    "prediction_created",
    prediction.id,
    user_id=str(user.id),
    match_id=match_id,
    prediction="home_win"
)
```

## 🔒 安全编码规范

### 输入验证
```python
from pydantic import validator
import re

class UserRegistrationRequest(BaseModel):
    username: str
    email: str
    password: str

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError("用户名长度必须在3-20个字符之间")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v

    @validator('email')
    def validate_email(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式无效")
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密码长度至少8个字符")
        if not re.search(r'[A-Z]', v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not re.search(r'[a-z]', v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not re.search(r'\d', v):
            raise ValueError("密码必须包含至少一个数字")
        return v
```

### 敏感数据处理
```python
import os
from typing import Optional

# 使用环境变量存储敏感信息
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

# 日志中避免记录敏感信息
def log_user_login(user_id: UUID, success: bool):
    """记录用户登录事件"""
    log_data = {
        "user_id": str(user_id),
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    # 不记录密码、令牌等敏感信息
    logger.info(f"User login: {json.dumps(log_data)}")

# 数据脱敏
def mask_email(email: str) -> str:
    """邮箱脱敏"""
    local, domain = email.split('@')
    if len(local) > 2:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    else:
        masked_local = '*' * len(local)
    return f"{masked_local}@{domain}"
```

## 📊 性能优化规范

### 数据库查询优化
```python
# 1. 使用索引优化查询
class Prediction(BaseModel):
    match_id = Column(Integer, nullable=False, index=True)  # 添加索引
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# 2. 避免N+1查询问题
def get_predictions_with_user_data(user_ids: List[UUID]):
    return db.query(Prediction).options(
        joinedload(Prediction.user)  # 预加载关联数据
    ).filter(Prediction.user_id.in_(user_ids)).all()

# 3. 使用批量操作
def create_predictions_batch(predictions_data: List[Dict]):
    predictions = [Prediction(**data) for data in predictions_data]
    db.bulk_save_objects(predictions)  # 批量插入
    db.commit()
```

### 缓存策略
```python
import redis
from functools import wraps
import json
from typing import Any, Optional

# 缓存装饰器
def cache_result(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            return result
        return wrapper
    return decorator

# 使用示例
@cache_result("user_predictions", ttl=1800)
async def get_user_predictions(user_id: UUID, limit: int = 10):
    """获取用户预测列表（缓存30分钟）"""
    return prediction_service.get_user_predictions(user_id, limit)
```

## 🧹 代码清理规范

### 代码注释规范
```python
# 1. 解释复杂业务逻辑
def calculate_prediction_weight(
    prediction: Prediction,
    historical_accuracy: float
) -> float:
    # 权重计算：基础权重 * 历史准确率修正因子
    # 历史准确率越高，预测权重越大
    base_weight = 0.5
    accuracy_factor = min(historical_accuracy * 1.2, 1.0)  # 限制最大修正为20%
    return base_weight * accuracy_factor

# 2. 标记临时解决方案
# TODO: 重构此方法，使用策略模式替代当前的条件判断
def determine_prediction_strategy(match_type: str) -> str:
    if match_type == "friendly":
        return "statistical"  # 友谊赛使用统计模型
    elif match_type == "league":
        return "ml_model"     # 联赛使用机器学习模型
    else:
        return "historical"   # 其他比赛使用历史模型

# 3. 解释重要的设计决策
# 使用延迟加载来避免不必要的数据库查询
# 因为用户信息不是所有API都需要
@property
def user_info(self) -> Optional[UserInfo]:
    if not hasattr(self, '_user_info'):
        self._user_info = self._load_user_info()
    return self._user_info
```

### 代码重构原则
```python
# 1. 单一职责原则 - 每个函数只做一件事
# 坏例子：一个函数既验证数据又保存到数据库
def create_and_validate_prediction(data: Dict) -> Prediction:
    # 验证逻辑...
    # 保存逻辑...
    pass

# 好例子：分离验证和保存逻辑
def validate_prediction_data(data: Dict) -> Dict:
    """验证预测数据"""
    # 验证逻辑...
    return validated_data

def save_prediction(validated_data: Dict) -> Prediction:
    """保存预测到数据库"""
    # 保存逻辑...
    return prediction

# 2. 提取复杂逻辑到独立函数
# 坏例子：复杂的内联逻辑
result = (
    sum(1 for p in predictions if p.confidence > 70 and p.prediction == actual_results.get(p.match_id))
    / len(predictions)
    if predictions
    else 0.0
)

# 好例子：提取为独立函数
def calculate_high_confidence_accuracy(predictions: List[Prediction]) -> float:
    """计算高置信度预测的准确率"""
    if not predictions:
        return 0.0

    high_confidence_predictions = [
        p for p in predictions if p.confidence > 70
    ]

    correct_predictions = sum(
        1 for p in high_confidence_predictions
        if p.prediction == actual_results.get(p.match_id)
    )

    return correct_predictions / len(high_confidence_predictions)

result = calculate_high_confidence_accuracy(predictions)
```

---

## 📚 参考资料

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/best-practices/)
- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

---

💡 **记住**: 编码规范的目的是提高代码的可读性、可维护性和团队协作效率。保持一致性和持续改进是关键！
