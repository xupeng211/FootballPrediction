# 📚 FootballPrediction API 参考文档

## 🎯 概览

本文档提供 FootballPrediction 足球预测系统各模块的详细API参考信息。

## 📦 API 端点 (src.api)

### 健康检查 API

系统健康状态检查端点，用于监控API、数据库、缓存等服务状态。

```python
from src.api.health import router as health_router

# 健康检查端点
GET /health
```

**响应格式:**

```json
{
  "status": "healthy",
  "timestamp": "2025-09-10T02:42:16.535410",
  "service": "football-prediction-api",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time": 0.025
    },
    "redis": {
      "status": "healthy",
      "response_time": 0.008
    }
  }
}
```

### 监控 API

系统性能指标和业务监控端点。

```python
from src.api.monitoring import router as monitoring_router

# 性能指标端点
GET /metrics
```

**响应格式:**

```json
{
  "timestamp": "2025-09-10T02:42:16.535410",
  "system_metrics": {
    "cpu_percent": 15.2,
    "memory": {
      "total": 16777216000,
      "available": 12884901888,
      "percent": 23.2,
      "used": 3892314112
    }
  },
  "database_metrics": {
    "total_tables": 6,
    "total_connections": 5,
    "uptime": "7 days"
  },
  "business_metrics": {
    "total_matches": 0,
    "total_predictions": 0,
    "active_leagues": 0
  }
}
```

## 📦 数据模型 (src.database.models)

### 联赛模型 (League)

```python
from src.database.models.league import League

# 联赛实体
class League:
    id: int
    name: str
    country: str
    season: str
    logo: Optional[str]
```

### 球队模型 (Team)

```python
from src.database.models.team import Team

# 球队实体
class Team:
    id: int
    name: str
    country: str
    founded: Optional[int]
    logo: Optional[str]
```

### 比赛模型 (Match)

```python
from src.database.models.match import Match

# 比赛实体
class Match:
    id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    match_date: datetime
    status: str
    home_score: Optional[int]
    away_score: Optional[int]
```

### 预测模型 (Prediction)

```python
from src.database.models.predictions import Prediction

# 预测实体
class Prediction:
    id: int
    match_id: int
    model_name: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_score: Optional[str]
    confidence: float
```

### 赔率模型 (Odds)

```python
from src.database.models.odds import Odds

# 赔率实体
class Odds:
    id: int
    match_id: int
    bookmaker: str
    home_odds: float
    draw_odds: float
    away_odds: float
    last_updated: datetime
```

### 特征模型 (Features)

```python
from src.database.models.features import Features

# 特征实体
class Features:
    id: int
    match_id: int
    home_team_features: dict
    away_team_features: dict
    historical_features: dict
    created_at: datetime
```

## 🔧 工具函数 (src.utils)

### 字符串工具

```python
from src.utils.string_utils import clean_text, normalize_name

# 文本清理
clean_text("  Real Madrid  ") -> "Real Madrid"

# 名称标准化
normalize_name("Real Madrid CF") -> "real_madrid_cf"
```

### 时间工具

```python
from src.utils.time_utils import format_datetime, parse_match_time

# 日期时间格式化
format_datetime(datetime.now()) -> "2025-09-10 02:42:16"

# 比赛时间解析
parse_match_time("2025-09-10 15:30") -> datetime(2025, 9, 10, 15, 30)
```

### 数据验证工具

```python
from src.utils.data_validator import validate_match_data, validate_odds

# 比赛数据验证
validate_match_data(match_dict) -> ValidationResult

# 赔率数据验证
validate_odds(odds_dict) -> ValidationResult
```

### 加密工具

```python
from src.utils.crypto_utils import hash_password, verify_password

# 密码哈希
hash_password("password123") -> "hashed_string"

# 密码验证
verify_password("password123", "hashed_string") -> True
```

### 文件工具

```python
from src.utils.file_utils import read_json, write_json, ensure_dir

# JSON文件操作
data = read_json("config.json")
write_json("output.json", data)

# 目录创建
ensure_dir("logs/2025/09")
```

### 字典工具

```python
from src.utils.dict_utils import deep_merge, safe_get

# 深度合并字典
merged = deep_merge(dict1, dict2)

# 安全获取嵌套值
value = safe_get(data, "team.stats.goals", default=0)
```

## 📊 响应模式 (src.api.schemas)

### HealthCheckResponse

健康检查响应模式

```python
class HealthCheckResponse:
    status: str
    timestamp: str
    service: str
    version: str
    checks: dict
```

### MetricsResponse

监控指标响应模式

```python
class MetricsResponse:
    timestamp: str
    system_metrics: dict
    database_metrics: dict
    business_metrics: dict
```

## 🔗 数据库连接 (src.database)

### 数据库配置

```python
from src.database.config import DATABASE_URL, get_database_url

# 获取数据库连接字符串
url = get_database_url()
```

### 数据库会话

```python
from src.database.connection import get_db_session

# 获取数据库会话
async def my_function(db: Session = Depends(get_db_session)):
    # 使用数据库会话
    pass
```

## 🚀 使用示例

### 启动应用

```python
from src.main import app
import uvicorn

# 启动FastAPI应用
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### API调用示例

```bash
# 健康检查
curl http://localhost:8000/health

# 获取监控指标
curl http://localhost:8000/metrics
```

## 📋 注意事项

1. **认证**: 当前API端点暂不需要认证，未来版本将添加JWT认证
2. **限流**: 建议在生产环境中配置API限流
3. **缓存**: 监控指标已实现Redis缓存，缓存时间为60秒
4. **错误处理**: 所有API端点都包含完整的错误处理和日志记录
5. **类型安全**: 所有接口都有完整的类型注解和Pydantic模式验证

## 🔧 开发工具

使用项目提供的Makefile命令进行开发：

```bash
make test          # 运行测试
make lint          # 代码检查
make coverage      # 测试覆盖率
make ci            # 完整CI检查
```

## 🔗 相关文档链接

### 📚 核心文档
- **[系统架构文档](../architecture/ARCHITECTURE.md)** - 完整的系统架构设计和技术栈说明
- **[数据库架构](DATABASE_SCHEMA.md)** - 数据库设计和表结构详情
- **[开发指南](DEVELOPMENT_GUIDE.md)** - 开发环境搭建和编码规范
- **[CLAUDE.md](../../CLAUDE.md)** - AI辅助开发指导和工作流程

### 🛠️ API使用指南
- **[API使用示例](API_USAGE_EXAMPLES.md)** - 详细的API调用示例和最佳实践
- **[API端点详情](API_ENDPOINTS.md)** - 所有API端点的详细说明
- **[API文档风格指南](COMPREHENSIVE_API_DOCUMENTATION_STYLE_GUIDE.md)** - API文档编写规范

### 🧪 测试相关
- **[测试策略文档](../testing/TEST_IMPROVEMENT_GUIDE.md)** - 完整的测试策略和质量保证体系
- **[API测试指南](../testing/API_TESTING.md)** - API接口测试方法和工具
- **[集成测试文档](../testing/INTEGRATION_TESTING.md)** - 集成测试策略和实施

### 📊 业务和数据
- **[数据采集配置](DATA_COLLECTION_SETUP.md)** - 数据采集和处理管道配置
- **[机器学习模型指南](../ml/ML_MODEL_GUIDE.md)** - ML模型开发和部署指南
- **[术语表](glossary.md)** - 项目专业术语和概念定义

### 🔧 运维和部署
- **[生产部署指南](../ops/PRODUCTION_READINESS_PLAN.md)** - 生产环境部署和运维指南
- **[监控系统](../ops/MONITORING.md)** - 监控系统配置和告警设置
- **[运维手册](../ops/runbooks/README.md)** - 运维操作指南和故障排除

### 📖 快速开始
- **[项目索引](../INDEX.md)** - 完整的文档导航和入口
- **[快速开始指南](../how-to/QUICK_START.md)** - 5分钟快速上手指南
- **[Makefile工具指南](../project/TOOLS.md)** - 120+开发命令详解

---

**文档维护**: 本API文档与代码同步更新，如有疑问请参考相关文档或联系开发团队。
