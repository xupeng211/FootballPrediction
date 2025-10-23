# 开发指南

## 📋 概述

本指南为足球预测系统的开发者提供完整的开发环境搭建、编码规范、调试和贡献流程。项目采用现代Python技术栈，遵循企业级开发标准。

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+ (推荐 3.11.5)
- **操作系统**: Linux/macOS/Windows 10+
- **内存**: 最少 8GB RAM (推荐 16GB)
- **存储**: 最少 10GB 可用空间
- **Docker**: 20.10+ (用于容器化开发)

### 5分钟快速上手

```bash
# 1. 克隆项目
git clone <repository-url>
cd FootballPrediction

# 2. 一键安装和配置
make install

# 3. 加载项目上下文
make context

# 4. 启动开发环境
make up

# 5. 运行测试验证
make test

# 6. 查看API文档
open http://localhost:8000/docs
```

## 🛠️ 开发环境搭建

### 1. 环境准备

#### 安装依赖管理工具

```bash
# 安装Poetry (推荐的Python依赖管理器)
curl -sSL https://install.python-poetry.org | python3 -

# 或使用pipx (推荐)
pip install pipx
pipx install poetry

# 验证安装
poetry --version
```

#### 安装开发工具

```bash
# 安装make (Linux/macOS)
sudo apt-get install build-essential  # Ubuntu/Debian
brew install make                      # macOS

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 项目初始化

```bash
# 创建项目目录并克隆
mkdir -p ~/projects/football-prediction
cd ~/projects/football-prediction
git clone <repository-url> .

# 使用项目提供的工具链
make install          # 安装所有依赖
make env-check        # 检查环境健康度
make context          # 加载项目上下文
```

### 3. 数据库设置

```bash
# 启动数据库服务
make up

# 等待数据库就绪
make test-env-status

# 运行数据库迁移
make db-migrate

# 初始化种子数据 (可选)
make db-seed
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

**关键环境变量配置**:

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD=your_password

# Redis配置
REDIS_URL=redis://localhost:6379/0

# API配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# 安全配置
SECRET_KEY=your-jwt-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# 监控配置
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

## 🏗️ 项目结构

### 目录说明

```
FootballPrediction/
├── src/                     # 源代码目录
│   ├── api/                # API层 (FastAPI路由)
│   ├── core/               # 核心业务逻辑
│   ├── database/           # 数据访问层 (SQLAlchemy)
│   ├── services/           # 服务层
│   ├── domain/             # 领域模型 (DDD)
│   ├── cache/              # 缓存层 (Redis)
│   ├── monitoring/         # 监控系统
│   ├── streaming/          # 流处理 (Kafka)
│   └── utils/              # 工具函数
├── tests/                  # 测试代码
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── e2e/                # 端到端测试
├── docs/                   # 项目文档
├── scripts/                # 开发脚本
├── config/                 # 配置文件
├── requirements/           # 依赖文件
├── docker/                 # Docker配置
└── Makefile               # 开发工具命令
```

### 核心文件说明

- **`src/main.py`**: FastAPI应用入口
- **`src/core/di.py`**: 依赖注入容器
- **`src/database/connection.py`**: 数据库连接管理
- **`pyproject.toml`**: 项目配置和依赖
- **`Makefile`**: 开发工具命令集合
- **`docker-compose.yml`**: 容器编排配置

## 🎯 开发工作流

### 🤖 AI辅助开发流程

项目支持使用Claude AI助手进行开发，遵循以下最佳实践：

#### AI开发工作流
1. **环境检查** - `make env-check` 确保开发环境健康
2. **加载上下文** - `make context` 为AI加载项目上下文
3. **开发和编码** - AI辅助编写代码和解决问题
4. **质量验证** - `make ci` 运行完整质量检查
5. **预提交验证** - `make prepush` 完整的预推送验证

#### AI使用指南
```bash
# AI开发前准备
make env-check    # 检查环境
make context      # 加载项目上下文

# AI开发完成后
make test         # 运行测试
make lint         # 代码检查
make ci           # 完整质量检查
make prepush      # 预推送验证
```

#### AI辅助开发最佳实践
- **始终使用Makefile命令** - 避免直接运行pytest单个文件
- **理解项目架构** - 参考系统架构和领域模型设计
- **遵循编码规范** - 使用项目统一的代码风格
- **测试驱动开发** - 编写测试用例验证功能
- **文档同步更新** - 代码变更时更新相关文档

### 1. 分支策略

```bash
# 主分支
main                    # 生产环境代码
develop                 # 开发环境代码

# 功能分支
feature/预测算法优化      # 功能开发
bugfix/修复数据库连接     # 错误修复
hotfix/紧急安全补丁      # 紧急修复
release/v1.2.0         # 发布准备
```

### 2. 日常开发流程

```bash
# 1. 同步最新代码
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/新功能开发

# 3. 开发和测试
make install             # 安装新依赖
make test                # 运行测试
make coverage            # 检查覆盖率
make lint                # 代码质量检查
make type-check          # 类型检查

# 4. 提交代码
git add .
git commit -m "feat: 添加新的预测算法"

# 5. 推送分支
git push origin feature/新功能开发

# 6. 创建Pull Request
# 在GitHub/GitLab上创建PR

# 7. 代码审查和合并
# 审查通过后合并到develop分支
```

### 3. 开发命令速查

```bash
# 环境管理
make env-check          # 检查环境健康度
make venv               # 创建虚拟环境
make install            # 安装依赖
make clean-env          # 清理环境

# 开发服务器
make up                 # 启动所有服务
make down               # 停止所有服务
make logs               # 查看服务日志
make restart            # 重启服务

# 测试相关
make test               # 运行所有测试
make test-unit          # 运行单元测试
make test-integration   # 运行集成测试
make coverage           # 检查测试覆盖率
make test-all           # 完整测试流程

# 代码质量
make lint               # 代码规范检查
make fmt                # 代码格式化
make type-check         # 类型检查
make prepush            # 预提交检查
make ci                 # 模拟CI流程

# 数据库操作
make db-init            # 初始化数据库
make db-migrate         # 运行迁移
make db-seed            # 填充种子数据
make db-backup          # 备份数据库
make db-reset           # 重置数据库

# 性能分析
make benchmark          # 性能基准测试
make profile-app        # 应用性能分析
make flamegraph         # 生成火焰图
```

## 📝 编码规范

### 1. Python代码规范

项目使用严格的代码规范，基于以下工具：

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
```

#### 代码风格要求

```python
# ✅ 正确示例
from typing import Optional, List, Dict
import asyncio
import logging

logger = logging.getLogger(__name__)

class PredictionService:
    """预测服务类

    提供足球比赛预测功能，支持多种预测模型。

    Attributes:
        model_version: 模型版本号
        confidence_threshold: 置信度阈值
    """

    def __init__(
        self,
        model_version: str = "v1.0.0",
        confidence_threshold: float = 0.6,
    ) -> None:
        """初始化预测服务"""
        self.model_version = model_version
        self.confidence_threshold = confidence_threshold

    async def predict_match(
        self,
        match_id: int,
        features: Dict[str, float]
    ) -> Optional[Dict[str, float]]:
        """预测比赛结果

        Args:
            match_id: 比赛ID
            features: 特征数据字典

        Returns:
            预测结果字典，包含各结果的概率

        Raises:
            ValueError: 当特征数据无效时
        """
        if not features:
            raise ValueError("特征数据不能为空")

        # 实现预测逻辑
        return {"home_win": 0.5, "draw": 0.3, "away_win": 0.2}
```

#### 代码质量要求

- **类型注解**: 所有公共函数必须包含类型注解
- **文档字符串**: 所有类和公共方法必须有docstring
- **错误处理**: 使用适当的异常处理机制
- **日志记录**: 关键操作必须记录日志
- **测试覆盖**: 新功能必须有对应的测试

### 2. 命名规范

```python
# 类名：大驼峰命名法
class PredictionEngine:
    pass

class DatabaseManager:
    pass

# 函数和变量：小写下划线命名法
def calculate_prediction_confidence():
    pass

user_service = UserService()
match_data = {}

# 常量：大写下划线命名法
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.football.com"

# 私有方法：前缀下划线
def _internal_method():
    pass

class MyClass:
    def __init__(self):
        self._private_var = "private"
        self.__very_private = "very private"
```

### 3. 项目特定规范

#### 异步代码规范

```python
# ✅ 推荐的异步编程模式
async def fetch_match_data(match_id: int) -> Optional[Dict]:
    """异步获取比赛数据"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}/matches/{match_id}"
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        logger.error(f"获取比赛数据失败: {e}")
        return None

# 批量异步操作
async def fetch_multiple_matches(match_ids: List[int]) -> List[Dict]:
    """批量获取比赛数据"""
    tasks = [fetch_match_data(match_id) for match_id in match_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]
```

#### 数据库操作规范

```python
# ✅ 推荐的数据库操作模式
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user_by_email(
    db: AsyncSession,
    email: str
) -> Optional[User]:
    """根据邮箱获取用户"""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_prediction(
    db: AsyncSession,
    prediction_data: PredictionCreate
) -> Prediction:
    """创建预测记录"""
    db_prediction = Prediction(**prediction_data.model_dump())
    db.add(db_prediction)
    await db.commit()
    await db.refresh(db_prediction)
    return db_prediction
```

## 🧪 测试策略

### 1. 测试分层

```
测试金字塔:
    E2E Tests (5%)        # 端到端测试
   ┌─────────────────┐
  │ Integration Tests │     # 集成测试 (15%)
 ┌─────────────────────────┐
│    Unit Tests (80%)      │  # 单元测试 (主要部分)
└─────────────────────────┘
```

### 2. 测试编写规范

```python
# tests/unit/services/test_prediction_service.py
import pytest
from unittest.mock import AsyncMock, patch
from src.services.prediction_service import PredictionService

class TestPredictionService:
    """预测服务测试类"""

    @pytest.fixture
    def prediction_service(self):
        """预测服务fixture"""
        return PredictionService(model_version="test-v1.0.0")

    @pytest.mark.asyncio
    async def test_predict_match_success(self, prediction_service):
        """测试成功预测比赛"""
        # Arrange
        match_id = 123
        features = {"team_strength": 0.8, "home_advantage": 0.1}

        # Act
        result = await prediction_service.predict_match(match_id, features)

        # Assert
        assert result is not None
        assert "home_win" in result
        assert "draw" in result
        assert "away_win" in result
        assert sum(result.values()) == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_predict_match_empty_features(self, prediction_service):
        """测试空特征数据异常"""
        # Arrange
        match_id = 123
        features = {}

        # Act & Assert
        with pytest.raises(ValueError, match="特征数据不能为空"):
            await prediction_service.predict_match(match_id, features)

    @pytest.mark.parametrize("features,expected_min_confidence", [
        ({"team_strength": 1.0}, 0.8),
        ({"team_strength": 0.5}, 0.6),
        ({"team_strength": 0.1}, 0.4),
    ])
    async def test_predict_match_confidence_levels(
        self,
        prediction_service,
        features,
        expected_min_confidence
    ):
        """测试不同特征强度下的置信度"""
        # Act
        result = await prediction_service.predict_match(123, features)

        # Assert
        max_prob = max(result.values())
        assert max_prob >= expected_min_confidence
```

### 3. 测试运行命令

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/unit/services/test_prediction_service.py -v

# 运行带覆盖率的测试
pytest tests/ --cov=src --cov-report=html

# 运行特定标记的测试
pytest -m "unit and not slow"
pytest -m "integration"
pytest -m "api"

# 并行运行测试
pytest -n auto

# 生成覆盖率报告
make coverage
make coverage-html
```

## 🐛 调试指南

### 1. 本地调试

#### 启动调试模式

```bash
# 开发模式启动
export DEBUG=true
make dev

# 或者直接运行
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 使用调试器

```python
# 在代码中添加断点
import pdb; pdb.set_trace()  # 标准调试器
import ipdb; ipdb.set_trace()  # 增强调试器
import web_pdb; web_pdb.set_trace()  # Web调试器

# 或者使用breakpoint() (Python 3.7+)
breakpoint()
```

#### VS Code调试配置

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "jinja": true,
            "justMyCode": false,
            "env": {
                "DEBUG": "true"
            }
        }
    ]
}
```

### 2. 日志调试

```python
import logging
from src.core.logging import get_logger

logger = get_logger(__name__)

async def some_function():
    logger.info("函数开始执行")

    try:
        # 业务逻辑
        result = await some_operation()
        logger.info(f"操作成功，结果: {result}")
        return result
    except Exception as e:
        logger.error(f"操作失败: {e}", exc_info=True)
        raise
```

#### 日志配置

```python
# src/core/logging.py
import logging
import sys
from pathlib import Path

def setup_logging():
    """设置日志配置"""

    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 文件处理器
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
```

### 3. 数据库调试

```bash
# 查看数据库连接
make logs | grep "database"

# 连接数据库
docker exec -it football-prediction_db_1 psql -U football_user -d football_prediction_dev

# 查看表结构
\dt
\d matches

# 查询数据
SELECT * FROM matches LIMIT 10;
SELECT COUNT(*) FROM predictions;
```

## 🚀 性能优化

### 1. 代码性能分析

```bash
# 运行性能分析
make profile-app

# 生成火焰图
make flamegraph

# 性能基准测试
make benchmark
```

### 2. 数据库性能优化

```python
# 批量操作
async def create_predictions_batch(
    db: AsyncSession,
    predictions: List[PredictionCreate]
) -> List[Prediction]:
    """批量创建预测记录"""
    db_predictions = [Prediction(**p.model_dump()) for p in predictions]
    db.add_all(db_predictions)
    await db.commit()

    # 刷新以获取ID
    for prediction in db_predictions:
        await db.refresh(prediction)

    return db_predictions

# 使用索引查询
async def get_predictions_by_date_range(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime
) -> List[Prediction]:
    """按日期范围查询预测"""
    stmt = (
        select(Prediction)
        .where(Prediction.prediction_time >= start_date)
        .where(Prediction.prediction_time <= end_date)
        .order_by(Prediction.prediction_time.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

### 3. 缓存优化

```python
from src.cache.redis_manager import RedisManager

class PredictionService:
    def __init__(self):
        self.cache = RedisManager()

    async def get_prediction_cached(self, match_id: int) -> Optional[Dict]:
        """获取缓存的预测结果"""
        cache_key = f"prediction:{match_id}"
        return await self.cache.get(cache_key)

    async def set_prediction_cache(
        self,
        match_id: int,
        prediction: Dict,
        ttl: int = 3600
    ) -> None:
        """设置预测结果缓存"""
        cache_key = f"prediction:{match_id}"
        await self.cache.set(cache_key, prediction, ttl=ttl)
```

## 📊 监控和诊断

### 1. 健康检查

```bash
# 检查应用健康状态
curl http://localhost:8000/health

# 检查数据库健康状态
curl http://localhost:8000/health/database

# 检查Redis健康状态
curl http://localhost:8000/health/cache
```

### 2. 性能监控

```bash
# 查看应用指标
curl http://localhost:8000/metrics

# 查看Prometheus指标
curl http://localhost:9090/metrics

# 查看Grafana仪表板
open http://localhost:3000
```

### 3. 日志监控

```bash
# 实时查看日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log

# 查看特定模块日志
grep "prediction_service" logs/app.log
```

## 🤝 贡献指南

### 1. 代码贡献流程

1. **Fork项目** - 在GitHub上fork项目到个人账户
2. **创建分支** - 基于develop分支创建功能分支
3. **开发功能** - 遵循编码规范编写代码
4. **编写测试** - 确保测试覆盖率达到要求
5. **提交代码** - 使用规范的提交信息格式
6. **创建PR** - 提供详细的PR描述
7. **代码审查** - 响应审查意见并修改
8. **合并代码** - 审查通过后合并到主分支

### 2. 提交信息规范

```bash
# 提交信息格式
<type>(<scope>): <subject>

<body>

<footer>

# 示例
feat(prediction): 添加新的预测算法

实现了基于随机森林的预测算法，提高了预测准确性。

- 添加了RandomForestPredictionService类
- 集成了特征重要性分析
- 添加了相应的单元测试

Closes #123
```

**提交类型**:
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建或辅助工具的变动

### 3. 代码审查标准

- **功能性**: 代码是否实现了预期功能
- **正确性**: 是否有潜在的bug或错误
- **性能**: 是否有性能问题或优化空间
- **可读性**: 代码是否清晰易懂
- **测试性**: 是否有足够的测试覆盖
- **安全性**: 是否存在安全隐患

## 📚 学习资源

### 1. 技术栈学习

- **FastAPI**: [FastAPI官方文档](https://fastapi.tiangolo.com/)
- **SQLAlchemy**: [SQLAlchemy 2.0文档](https://docs.sqlalchemy.org/)
- **Pydantic**: [Pydantic文档](https://pydantic-docs.helpmanual.io/)
- **Pytest**: [Pytest文档](https://docs.pytest.org/)
- **Docker**: [Docker官方文档](https://docs.docker.com/)

### 2. 最佳实践

- **Python代码规范**: [PEP 8](https://peps.python.org/pep-0008/)
- **类型注解**: [PEP 484](https://peps.python.org/pep-0484/)
- **异步编程**: [asyncio文档](https://docs.python.org/3/library/asyncio.html)
- **测试驱动开发**: [TDD最佳实践](https://testdriven.io/)

### 3. 项目内部资源

#### 🔗 核心文档
- **数据库架构**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - 数据库设计和表结构
- **数据采集配置**: [DATA_COLLECTION_SETUP.md](DATA_COLLECTION_SETUP.md) - 数据采集和处理流程
- **机器学习模型**: [../ml/ML_MODEL_GUIDE.md](../ml/ML_MODEL_GUIDE.md) - ML模型开发和部署
- **监控系统**: [MONITORING_GUIDE.md](MONITORING_GUIDE.md) - 监控和告警配置
- **API文档**: [API_REFERENCE.md](API_REFERENCE.md) - REST API接口说明
- **术语表**: [glossary.md](glossary.md) - 项目术语和概念定义

#### 🏗️ 架构和设计
- [系统架构文档](../architecture/ARCHITECTURE.md) - 整体系统架构设计
- [数据架构设计](DATABASE_SCHEMA.md) - 数据层架构
- [缓存实现设计](../architecture/CACHING_IMPLEMENTATION_DESIGN.md) - 缓存策略设计
- [重试机制设计](../architecture/RETRY_MECHANISM_DESIGN.md) - 重试和容错机制

#### 🛠️ 运维和部署
- [生产部署指南](../ops/PRODUCTION_READINESS_PLAN.md) - 生产环境部署流程
- [运维手册](../ops/runbooks/README.md) - 运维操作指南
- [Staging环境配置](../how-to/STAGING_ENVIRONMENT.md) - 测试环境配置
- [系统监控](../ops/monitoring.md) - 监控系统配置

#### 🧪 测试和质量
- [测试策略文档](../testing/TEST_IMPROVEMENT_GUIDE.md) - 测试策略和方法论
- [CI Guardian系统](../testing/CI_GUARDIAN_GUIDE.md) - CI/CD质量门禁
- [测试优化报告](../_reports/TEST_IMPROVEMENT_AUDIT.md) - 测试优化总结
- [性能测试方案](../testing/performance_tests.md) - 性能测试指南

#### 📖 快速开始
- [完整系统演示](../how-to/COMPLETE_DEMO.md) - 系统功能演示
- [快速开始工具指南](../how-to/QUICKSTART_TOOLS.md) - 开发工具使用
- [Makefile使用指南](../how-to/MAKEFILE_GUIDE.md) - 项目工具命令

## ❓ 常见问题

### Q1: 如何解决依赖冲突？

```bash
# 清理虚拟环境
make clean-env

# 重新创建环境
make venv
make install

# 如果仍有问题，手动解决
pip install --upgrade pip
pip install -r requirements/requirements.lock
```

### Q2: 数据库连接失败怎么办？

```bash
# 检查数据库服务状态
docker ps | grep postgres

# 查看数据库日志
make logs | grep db

# 重启数据库服务
docker-compose restart db

# 检查连接配置
cat .env | grep DB_
```

### Q3: 测试失败如何调试？

```bash
# 运行单个测试文件获取详细信息
pytest tests/unit/services/test_prediction_service.py -v -s

# 运行失败的特定测试
pytest tests/unit/services/test_prediction_service.py::TestPredictionService::test_predict_match_success -v -s

# 查看详细错误信息
pytest --tb=long

# 调试模式运行测试
pytest --pdb
```

### Q4: 如何提高开发效率？

```bash
# 使用IDE插件
# - Python插件
# - Docker插件
# - Git插件
# - 远程开发插件

# 配置代码片段
# - 创建常用代码模板
# - 配置自动补全
# - 设置快捷键

# 使用项目提供的工具
make help  # 查看所有可用命令
make dev   # 快速启动开发环境
```

## 📞 获取帮助

如果您在开发过程中遇到问题，可以通过以下方式获取帮助：

1. **项目文档**: 查看docs/目录下的详细文档
2. **代码示例**: 参考tests/目录下的测试用例
3. **团队沟通**: 通过团队沟通工具联系
4. **Issue追踪**: 在GitHub上创建Issue
5. **代码审查**: 提交PR获取团队反馈

---

## 📋 文档信息

- **文档版本**: v2.0 (AI增强版)
- **适用框架**: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- **Python版本**: 3.11+
- **最后更新**: 2025-10-23
- **维护团队**: 开发团队 + Claude AI助手
- **审核状态**: ✅ 已审核

**版本历史**:
- v1.0 (2025-09-01): 初始开发指南
- v1.5 (2025-10-01): 添加性能优化和监控章节
- v2.0 (2025-10-23): 添加AI辅助开发流程和链接修复

## 🔗 相关资源

### 📚 必读文档
- **[CLAUDE.md](../../CLAUDE.md)** - Claude AI助手开发指导
- **[数据库架构](DATABASE_SCHEMA.md)** - 数据库设计和表结构
- **[API文档](API_REFERENCE.md)** - REST API接口说明
- **[测试策略](../testing/TEST_IMPROVEMENT_GUIDE.md)** - 测试策略和方法

### 🛠️ 开发工具
- **[Makefile工具指南](../project/TOOLS.md)** - 120+开发命令详解
- **[快速开始工具](../how-to/QUICKSTART_TOOLS.md)** - 5分钟开发环境搭建
- **[容器化开发](../how-to/STAGING_ENVIRONMENT.md)** - Docker开发环境

### 🚀 部署和运维
- **[生产部署指南](../ops/PRODUCTION_READINESS_PLAN.md)** - 生产环境部署
- **[监控配置](../ops/MONITORING.md)** - 系统监控和告警
- **[安全配置](../maintenance/SECURITY_AUDIT_GUIDE.md)** - 安全最佳实践
