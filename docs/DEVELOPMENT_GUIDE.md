# 开发指南
# Development Guide

## 目录
- [环境设置](#环境设置)
- [项目结构](#项目结构)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [部署指南](#部署指南)

## 环境设置

### 系统要求
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Git

### 快速开始

```bash
# 1. 克隆项目
git clone <repository-url>
cd FootballPrediction

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 3. 安装依赖
make install

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加必要的环境变量

# 5. 初始化数据库
make db-init

# 6. 运行应用
make run
```

## 项目结构

```
FootballPrediction/
├── src/                    # 源代码
│   ├── api/               # FastAPI路由和API层
│   │   ├── predictions/   # 预测相关API
│   │   ├── models/        # API模型
│   │   └── health/        # 健康检查
│   ├── core/              # 核心业务逻辑
│   │   ├── config/        # 配置管理
│   │   ├── logging/       # 日志系统
│   │   └── di/           # 依赖注入
│   ├── domain/            # 领域模型
│   │   ├── models/        # 领域实体
│   │   └── services/      # 领域服务
│   ├── services/          # 应用服务层
│   ├── database/          # 数据库层
│   │   ├── models/        # 数据模型
│   │   ├── repositories/  # 数据访问层
│   │   └── migrations/    # 数据库迁移
│   ├── adapters/          # 外部适配器
│   │   ├── football/      # 足球数据适配器
│   │   └── cache/         # 缓存适配器
│   ├── cache/             # 缓存系统
│   ├── utils/             # 工具类
│   └── security/          # 安全模块
├── tests/                  # 测试代码
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── e2e/               # 端到端测试
├── scripts/               # 辅助脚本
├── config/                # 配置文件
├── docs/                  # 文档
└── requirements/          # 依赖文件
```

## 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发代码

- 遵循代码规范
- 编写测试
- 更新文档

### 3. 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试
make test-unit

# 检查覆盖率
make coverage
```

### 4. 代码质量检查

```bash
# 运行所有质量检查
make quality

# 或分别运行
make lint        # 代码检查
make fmt         # 代码格式化
make type-check   # 类型检查
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能"
git push origin feature/your-feature-name
```

### 6. 创建Pull Request

- 在GitHub上创建PR
- 等待代码审查
- 合并到主分支

## 代码规范

### Python代码风格

项目使用以下工具确保代码质量：

1. **Ruff** - 代码检查和格式化
   - 配置文件：`pyproject.toml`
   - 行长度：88字符

2. **MyPy** - 类型检查
   - 配置文件：`mypy.ini`
   - 分层类型检查策略

3. **Black** - 代码格式化（兼容性）

### 命名规范

- 类名：`PascalCase`
- 函数名：`snake_case`
- 常量：`UPPER_CASE`
- 私有成员：`_private`
- 文件名：`snake_case.py`

### 文档字符串

所有公共函数和类必须包含文档字符串：

```python
def example_function(param1: str, param2: int) -> bool:
    """
    函数简短描述（一句话）

    详细描述：解释函数的功能、算法或流程。

    Args:
        param1: 参数1的描述
        param2: 参数2的描述

    Returns:
        返回值的描述

    Raises:
        ValueError: 错误条件和描述
    """
    pass
```

## 测试指南

### 测试类型

1. **单元测试** (`tests/unit/`)
   - 测试单个函数或类
   - 使用pytest框架
   - 模拟外部依赖

2. **集成测试** (`tests/integration/`)
   - 测试多个组件的交互
   - 测试数据库集成
   - 测试API端点

3. **端到端测试** (`tests/e2e/`)
   - 测试完整用户流程
   - 测试真实环境

### 编写测试

```python
import pytest
from src.utils.dict_utils import DictUtils

class TestDictUtils:
    def test_get_nested_success(self):
        """测试获取嵌套字典值 - 成功案例"""
        data = {"a": {"b": {"c": 1}}}
        assert DictUtils.get_nested(data, "a.b.c") == 1

    def test_get_nested_default(self):
        """测试获取嵌套字典值 - 默认值"""
        data = {}
        assert DictUtils.get_nested(data, "a.b", "default") == "default"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/utils/test_dict_utils.py

# 运行带标记的测试
pytest -m "unit and not slow"

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## API开发指南

### 创建新的API端点

1. 在 `src/api/` 下创建或编辑路由文件
2. 定义Pydantic模型（请求/响应）
3. 实现业务逻辑
4. 添加错误处理
5. 编写测试

示例：

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/example", tags=["example"])

class ExampleRequest(BaseModel):
    name: str
    value: int

class ExampleResponse(BaseModel):
    id: int
    name: str
    value: int
    processed: bool

@router.post("/", response_model=ExampleResponse)
async def create_example(request: ExampleRequest):
    """创建示例数据"""
    try:
        # 业务逻辑
        result = process_example(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 数据库操作

### 模型定义

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.database.base import Base

class Example(Base):
    __tablename__ = "examples"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)
```

### Repository模式

```python
from sqlalchemy.orm import Session
from src.database.models.example import Example

class ExampleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, example_data: dict) -> Example:
        example = Example(**example_data)
        self.db.add(example)
        self.db.commit()
        self.db.refresh(example)
        return example
```

## 缓存使用

### Redis缓存

```python
from src.cache.redis.core import RedisManager

# 获取缓存实例
redis = RedisManager()

# 设置缓存
await redis.set("key", {"data": "value"}, ttl=3600)

# 获取缓存
data = await redis.get("key")
```

### 缓存装饰器

```python
from src.cache.decorators import cache_result

@cache_result(ttl=300)
async def expensive_operation(param: str) -> dict:
    # 耗时操作
    return {"result": param}
```

## 错误处理

### 自定义异常

```python
class CustomError(Exception):
    """自定义异常基类"""
    pass

class ValidationError(CustomError):
    """验证错误"""
    pass
```

### 全局异常处理

```python
from fastapi import Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )
```

## 日志记录

### 使用日志

```python
from src.core.logging import get_logger

logger = get_logger(__name__)

async def some_function():
    logger.info("函数开始执行")
    try:
        # 业务逻辑
        result = do_something()
        logger.info(f"操作成功: {result}")
        return result
    except Exception as e:
        logger.error(f"操作失败: {e}", exc_info=True)
        raise
```

## 性能优化

### 异步编程

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def async_process_items(items: list):
    """异步处理列表"""
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, process_item, item)
            for item in items
        ]
        results = await asyncio.gather(*tasks)
    return results
```

### 批量操作

```python
from sqlalchemy.dialects.postgresql import insert

def bulk_insert_data(db: Session, data_list: list):
    """批量插入数据"""
    stmt = insert(Example).values(data_list)
    db.execute(stmt)
    db.commit()
```

## 安全最佳实践

### 输入验证

```python
from pydantic import BaseModel, validator

class UserData(BaseModel):
    name: str
    email: str

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

### SQL注入防护

```python
# 使用参数化查询
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

## 部署指南

### 开发环境

```bash
make run-dev
```

### 生产环境

```bash
# 1. 构建Docker镜像
docker build -t football-prediction .

# 2. 运行容器
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 环境变量

生产环境必须设置以下环境变量：

```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-secret-key
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 故障排除

### 常见问题

1. **导入错误**
   - 检查PYTHONPATH
   - 激活虚拟环境
   - 运行 `pip install -r requirements.txt`

2. **数据库连接错误**
   - 检查数据库服务状态
   - 验证连接字符串
   - 检查防火墙设置

3. **测试失败**
   - 更新测试依赖：`pip install -e .[test]`
   - 检查环境变量
   - 运行 `make test-env-start`

### 调试技巧

```python
import pdb

def debug_function():
    pdb.set_trace()  # 设置断点
    # 调试代码
    pass
```

## 有用的资源

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [pytest文档](https://docs.pytest.org/)
- [Python类型提示](https://docs.python.org/3/library/typing.html)

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 确保所有测试通过
5. 提交Pull Request
6. 等待代码审查

---

*最后更新：2024-10-14*