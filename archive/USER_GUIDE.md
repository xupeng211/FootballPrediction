# 🎯 足球预测系统用户指南

## 📋 目录

- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [API接口](#api接口)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 🚀 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL (可选)
- Redis (可选)

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd FootballPrediction

# 2. 安装依赖
make install

# 3. 检查环境
make env-check

# 4. 运行测试
make test.smart
```

### 启动应用

```bash
# 开发环境启动
make dev

# 或者直接使用
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 核心功能

### 1. 预测功能

系统提供多种预测策略：

```python
from src.domain.services.prediction_service import PredictionService
from src.domain.strategies.factory import PredictionStrategyFactory

# 创建预测服务
factory = PredictionStrategyFactory()
strategy = factory.create_strategy("ml_model", "enhanced_ml_model")
service = PredictionService(strategy)

# 执行预测
prediction_data = {
    "match_id": 123,
    "home_team": "Team A",
    "away_team": "Team B",
    "league": "Premier League",
    "season": "2024-25"
}

prediction = await service.create_prediction(prediction_data)
print(f"预测结果: {prediction}")
```

### 2. 数据处理

```python
from src.data.processing.data_preprocessor import DataPreprocessor

# 数据预处理
preprocessor = DataPreprocessor()
cleaned_data = preprocessor.preprocess_dataset(raw_data, "matches")
```

### 3. 缓存管理

```python
from src.cache.redis_client import RedisClient

# Redis缓存操作
redis_client = RedisClient()
await redis_client.connect()

# 设置缓存
await redis_client.set("prediction:123", prediction_data, ttl=3600)

# 获取缓存
cached_data = await redis_client.get("prediction:123")
```

## 🌐 API接口

### 基础URL
```
http://localhost:8000
```

### 主要端点

#### 1. 预测相关

```bash
# 创建预测
POST /api/v1/predictions
Content-Type: application/json

{
  "match_id": 123,
  "home_team": "Team A",
  "away_team": "Team B",
  "league": "Premier League"
}
```

#### 2. 数据查询

```bash
# 获取比赛信息
GET /api/v1/matches/{match_id}

# 获取队伍信息
GET /api/v1/teams/{team_id}

# 获取联赛信息
GET /api/v1/leagues/{league_id}
```

#### 3. 系统状态

```bash
# 健康检查
GET /health

# 系统信息
GET /api/v1/system/info
```

### API文档

启动应用后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/football_prediction

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 应用配置
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO

# API配置
API_HOSTNAME=localhost
API_PORT=8000
API_WORKERS=4
```

### 配置文件

主要配置文件位于 `config/` 目录：

- `config/app.py` - 应用配置
- `config/database.py` - 数据库配置
- `config/cache.py` - 缓存配置
- `config/logging.py` - 日志配置

### 高级配置

```python
# config/strategies.yaml
prediction_strategies:
  ml_model:
    enabled: true
    model_path: "models/ml_model.pkl"
    confidence_threshold: 0.7

  statistical:
    enabled: true
    method: "poisson_distribution"
    historical_data_days: 365
```

## 🔧 开发指南

### 测试

```bash
# 快速测试
make test.smart

# 完整测试
make test.unit

# 覆盖率测试
make coverage

# HTML覆盖率报告
make cov.html
```

### 代码质量

```bash
# 代码检查
make check-quality

# 代码格式化
make fmt

# 类型检查
make type-check
```

### Docker部署

```bash
# 开发环境
make up

# 生产环境
make deploy

# 查看日志
make logs
```

## 🚨 常见问题

### Q: 如何解决依赖安装问题？

A: 使用虚拟环境并确保Python版本正确：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
make install
```

### Q: 数据库连接失败怎么办？

A: 检查数据库配置和连接：
```bash
# 测试数据库连接
psql $DATABASE_URL -c "SELECT 1;"

# 检查数据库状态
make check-db
```

### Q: Redis连接问题？

A: 确保Redis服务运行并检查配置：
```bash
# 测试Redis连接
redis-cli -u $REDIS_URL ping

# 检查Redis状态
docker-compose exec redis redis-cli ping
```

### Q: 测试失败如何解决？

A: 使用智能修复工具：
```bash
# 运行智能修复
python3 scripts/smart_quality_fixer.py

# 或者快速修复
make fix-code
```

### Q: 如何添加新的预测策略？

A: 1. 在 `src/domain/strategies/` 创建策略类
   2. 继承 `BasePredictionStrategy`
   3. 在工厂类中注册新策略

```python
from src.domain.strategies.base import BasePredictionStrategy

class MyCustomStrategy(BasePredictionStrategy):
    def predict(self, match_data: dict) -> PredictionResult:
        # 实现自定义预测逻辑
        pass
```

## 📚 更多资源

- [架构文档](docs/claude/architecture.md)
- [测试指南](docs/testing/README.md)
- [部署文档](DEPLOYMENT.md)
- [API详细文档](docs/api/API_COMPREHENSIVE_GUIDE.md)

## 🆘 获取帮助

- 查看项目Wiki
- 提交Issue到GitHub
- 查看测试覆盖率报告
- 阅读代码注释

---

**最后更新**: 2025-11-16
**版本**: v1.0
**维护者**: 开发团队