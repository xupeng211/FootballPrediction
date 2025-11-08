# 足球比赛结果预测系统 - 综合API文档

## 📋 文档信息

| 项目 | 足球比赛结果预测系统 API |
|------|-----------------------------|
| 版本 | v1.0 |
| 创建日期 | 2025-11-06 |
| 最后更新 | 2025-11-06 |
| 作者 | Claude Code |
| 状态 | Phase 4: 文档完善 |

---

## 🎯 API概览

### 基础信息
- **基础URL**: `http://localhost:8000`
- **API版本**: v1
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **认证方式**: JWT Token (可选)

### API架构
- **框架**: FastAPI
- **文档**: 自动生成的OpenAPI/Swagger文档
- **验证**: Pydantic数据验证
- **异步支持**: 基于asyncio的异步处理

---

## 🚀 快速开始

### 1. 启动API服务

```bash
# 使用Docker Compose启动
docker-compose up -d

# 或直接启动Python服务
source .venv/bin/activate
python src/main.py
```

### 2. 访问API文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 3. 健康检查

```bash
curl http://localhost:8000/health
```

预期响应:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T08:30:00.000Z",
  "version": "1.0.0",
  "uptime": 3600
}
```

---

## 📋 API端点总览

### 健康检查端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/health` | 基础健康检查 |
| GET | `/health/system` | 系统健康状态 |
| GET | `/health/database` | 数据库连接状态 |

### 预测服务端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/predictions` | 获取预测列表 |
| GET | `/api/v1/predictions/{prediction_id}` | 获取特定预测 |
| POST | `/api/v1/predictions` | 创建新的预测请求 |
| GET | `/api/v1/predictions/match/{match_id}` | 获取比赛预测 |

### 数据管理端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/matches` | 获取比赛列表 |
| GET | `/api/v1/matches/{match_id}` | 获取比赛详情 |
| GET | `/api/v1/teams` | 获取球队列表 |
| GET | `/api/v1/teams/{team_id}` | 获取球队详情 |
| GET | `/api/v1/leagues` | 获取联赛列表 |
| GET | `/api/v1/odds` | 获取赔率数据 |

### 系统管理端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/stats` | 系统统计信息 |
| GET | `/api/v1/version` | API版本信息 |
| POST | `/api/v1/queue/status` | 队列状态查询 |

---

## 🔍 详细API文档

### 健康检查API

#### GET /health
**描述**: 获取API服务基础健康状态

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T08:30:00.000Z",
  "version": "1.0.0",
  "uptime": 3600,
  "environment": "development"
}
```

#### GET /health/system
**描述**: 获取系统资源使用情况

**响应示例**:
```json
{
  "status": "healthy",
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "disk_percent": 78.1,
    "uptime": 3600
  },
  "timestamp": "2025-11-06T08:30:00.000Z"
}
```

#### GET /health/database
**描述**: 检查数据库连接状态

**响应示例**:
```json
{
  "status": "healthy",
  "database": {
    "connection": "ok",
    "response_time_ms": 12,
    "pool_size": 10,
    "active_connections": 3
  },
  "timestamp": "2025-11-06T08:30:00.000Z"
}
```

### 预测服务API

#### GET /api/v1/predictions
**描述**: 获取预测结果列表

**查询参数**:
- `limit` (int, optional): 返回结果数量限制，默认20
- `offset` (int, optional): 偏移量，默认0
- `status` (string, optional): 预测状态过滤 (pending, completed, failed)
- `date_from` (string, optional): 开始日期 (YYYY-MM-DD)
- `date_to` (string, optional): 结束日期 (YYYY-MM-DD)

**请求示例**:
```bash
curl "http://localhost:8000/api/v1/predictions?limit=10&status=completed"
```

**响应示例**:
```json
{
  "predictions": [
    {
      "id": "pred_12345",
      "match_id": 67890,
      "home_team": "Manchester United",
      "away_team": "Liverpool",
      "predicted_result": "home_win",
      "confidence": 0.75,
      "home_win_probability": 0.65,
      "draw_probability": 0.20,
      "away_win_probability": 0.15,
      "status": "completed",
      "created_at": "2025-11-06T08:00:00.000Z",
      "updated_at": "2025-11-06T08:30:00.000Z"
    }
  ],
  "total": 150,
  "limit": 10,
  "offset": 0
}
```

#### GET /api/v1/predictions/{prediction_id}
**描述**: 获取特定预测的详细信息

**路径参数**:
- `prediction_id` (string): 预测ID

**响应示例**:
```json
{
  "id": "pred_12345",
  "match_id": 67890,
  "match": {
    "id": 67890,
    "home_team": {
      "id": 1,
      "name": "Manchester United",
      "short_name": "MU"
    },
    "away_team": {
      "id": 2,
      "name": "Liverpool",
      "short_name": "LIV"
    },
    "league": {
      "id": 39,
      "name": "Premier League",
      "country": "England"
    },
    "venue": "Old Trafford",
    "date": "2025-11-10T15:00:00.000Z"
  },
  "prediction": {
    "result": "home_win",
    "confidence": 0.75,
    "probabilities": {
      "home_win": 0.65,
      "draw": 0.20,
      "away_win": 0.15
    },
    "features": {
      "home_form": 0.85,
      "away_form": 0.72,
      "h2h_history": 0.60,
      "home_advantage": 0.15
    }
  },
  "metadata": {
    "model_version": "1.2.0",
    "training_data": "2020-2024",
    "accuracy": 0.78
  },
  "status": "completed",
  "created_at": "2025-11-06T08:00:00.000Z",
  "updated_at": "2025-11-06T08:30:00.000Z"
}
```

#### POST /api/v1/predictions
**描述**: 创建新的预测请求

**请求体**:
```json
{
  "match_id": 67890,
  "features": {
    "home_team_id": 1,
    "away_team_id": 2,
    "home_form": 0.85,
    "away_form": 0.72,
    "h2h_history": 0.60,
    "home_advantage": 0.15
  },
  "priority": "normal"
}
```

**响应示例**:
```json
{
  "id": "pred_12346",
  "status": "pending",
  "match_id": 67890,
  "estimated_completion": "2025-11-06T08:35:00.000Z",
  "created_at": "2025-11-06T08:30:00.000Z"
}
```

### 数据管理API

#### GET /api/v1/matches
**描述**: 获取比赛列表

**查询参数**:
- `limit` (int, optional): 返回结果数量限制，默认20
- `offset` (int, optional): 偏移量，默认0
- `team_id` (int, optional): 球队ID过滤
- `league_id` (int, optional): 联赛ID过滤
- `date_from` (string, optional): 开始日期
- `date_to` (string, optional): 结束日期
- `status` (string, optional): 比赛状态

**响应示例**:
```json
{
  "matches": [
    {
      "id": 67890,
      "home_team": {
        "id": 1,
        "name": "Manchester United",
        "short_name": "MU"
      },
      "away_team": {
        "id": 2,
        "name": "Liverpool",
        "short_name": "LIV"
      },
      "league": {
        "id": 39,
        "name": "Premier League"
      },
      "venue": "Old Trafford",
      "date": "2025-11-10T15:00:00.000Z",
      "status": "scheduled",
      "score": {
        "home": null,
        "away": null
      }
    }
  ],
  "total": 380,
  "limit": 20,
  "offset": 0
}
```

#### GET /api/v1/matches/{match_id}
**描述**: 获取特定比赛详情

**响应示例**:
```json
{
  "id": 67890,
  "home_team": {
    "id": 1,
    "name": "Manchester United",
    "short_name": "MU",
    "logo": "https://example.com/logos/mu.png"
  },
  "away_team": {
    "id": 2,
    "name": "Liverpool",
    "short_name": "LIV",
    "logo": "https://example.com/logos/liv.png"
  },
  "league": {
    "id": 39,
    "name": "Premier League",
    "country": "England",
    "season": "2024/25"
  },
  "venue": {
    "name": "Old Trafford",
    "capacity": 76212,
    "city": "Manchester"
  },
  "date": "2025-11-10T15:00:00.000Z",
  "status": "scheduled",
  "score": {
    "home": null,
    "away": null,
    "half_time": {
      "home": null,
      "away": null
    }
  },
  "odds": {
    "home_win": 2.10,
    "draw": 3.40,
    "away_win": 3.80
  },
  "statistics": {
    "possession": {
      "home": null,
      "away": null
    },
    "shots": {
      "home": null,
      "away": null
    },
    "corners": {
      "home": null,
      "away": null
    }
  }
}
```

### 系统管理API

#### GET /api/v1/stats
**描述**: 获取系统统计信息

**响应示例**:
```json
{
  "system": {
    "total_predictions": 15420,
    "total_matches": 12800,
    "total_teams": 50,
    "total_leagues": 10
  },
  "performance": {
    "avg_response_time_ms": 45,
    "queue_size": 25,
    "active_workers": 4,
    "success_rate": 0.98
  },
  "accuracy": {
    "overall_accuracy": 0.78,
    "last_30_days": 0.82,
    "model_performance": {
      "home_win_accuracy": 0.85,
      "draw_accuracy": 0.72,
      "away_win_accuracy": 0.79
    }
  },
  "timestamp": "2025-11-06T08:30:00.000Z"
}
```

#### GET /api/v1/version
**描述**: 获取API版本信息

**响应示例**:
```json
{
  "api_version": "1.0.0",
  "system_version": "1.2.0",
  "build_timestamp": "2025-11-06T08:00:00.000Z",
  "environment": "development",
  "features": {
    "predictions": true,
    "real_time_data": true,
    "batch_processing": true,
    "advanced_analytics": true
  }
}
```

---

## 🔐 错误处理

### HTTP状态码

| 状态码 | 含义 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未授权访问 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求频率超限 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

### 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "match_id",
      "reason": "Invalid match ID format"
    },
    "timestamp": "2025-11-06T08:30:00.000Z",
    "request_id": "req_12345"
  }
}
```

### 常见错误示例

#### 400 Bad Request
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "match_id": "must be a valid integer"
    }
  }
}
```

#### 404 Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Prediction not found",
    "details": {
      "prediction_id": "pred_invalid_id"
    }
  }
}
```

#### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "limit": 100,
      "window": "1 hour",
      "retry_after": 3600
    }
  }
}
```

---

## 🔧 API使用指南

### Python客户端示例

```python
import requests
import json

class FootballPredictionAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_health(self):
        """获取健康状态"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_predictions(self, limit=20, status=None):
        """获取预测列表"""
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = self.session.get(
            f"{self.base_url}/api/v1/predictions",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def create_prediction(self, match_id, features):
        """创建预测请求"""
        data = {
            "match_id": match_id,
            "features": features
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/predictions",
            json=data
        )
        response.raise_for_status()
        return response.json()

    def get_prediction(self, prediction_id):
        """获取特定预测"""
        response = self.session.get(
            f"{self.base_url}/api/v1/predictions/{prediction_id}"
        )
        response.raise_for_status()
        return response.json()

# 使用示例
api = FootballPredictionAPI()

# 检查健康状态
health = api.get_health()
print(f"API状态: {health['status']}")

# 获取预测列表
predictions = api.get_predictions(limit=10)
print(f"获取到 {len(predictions['predictions'])} 个预测")

# 创建新预测
features = {
    "home_team_id": 1,
    "away_team_id": 2,
    "home_form": 0.85,
    "away_form": 0.72
}
prediction = api.create_prediction(match_id=67890, features=features)
print(f"创建预测: {prediction['id']}")
```

### JavaScript客户端示例

```javascript
class FootballPredictionAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async function getHealth() {
        const response = await fetch(`${this.baseUrl}/health`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    async function getPredictions(options = {}) {
        const params = new URLSearchParams(options);
        const response = await fetch(`${this.baseUrl}/api/v1/predictions?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    async function createPrediction(matchId, features) {
        const response = await fetch(`${this.baseUrl}/api/v1/predictions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                match_id: matchId,
                features: features
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }
}

// 使用示例
const api = new FootballPredictionAPI();

// 异步获取健康状态
api.getHealth().then(health => {
    console.log('API状态:', health.status);
});

// 获取预测列表
api.getPredictions({ limit: 10 }).then(data => {
    console.log('预测数量:', data.predictions.length);
});
```

### cURL示例

```bash
# 健康检查
curl -X GET "http://localhost:8000/health"

# 获取预测列表
curl -X GET "http://localhost:8000/api/v1/predictions?limit=10"

# 创建新预测
curl -X POST "http://localhost:8000/api/v1/predictions" \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": 67890,
    "features": {
      "home_team_id": 1,
      "away_team_id": 2,
      "home_form": 0.85,
      "away_form": 0.72
    }
  }'

# 获取特定预测
curl -X GET "http://localhost:8000/api/v1/predictions/pred_12345"

# 获取系统统计
curl -X GET "http://localhost:8000/api/v1/stats"
```

---

## 📊 数据模型

### 预测模型

```json
{
  "id": "string",
  "match_id": "integer",
  "predicted_result": "string",
  "confidence": "number",
  "probabilities": {
    "home_win": "number",
    "draw": "number",
    "away_win": "number"
  },
  "features": {
    "home_form": "number",
    "away_form": "number",
    "h2h_history": "number",
    "home_advantage": "number"
  },
  "metadata": {
    "model_version": "string",
    "training_data": "string",
    "accuracy": "number"
  },
  "status": "string",
  "created_at": "string",
  "updated_at": "string"
}
```

### 比赛模型

```json
{
  "id": "integer",
  "home_team": {
    "id": "integer",
    "name": "string",
    "short_name": "string",
    "logo": "string"
  },
  "away_team": {
    "id": "integer",
    "name": "string",
    "short_name": "string",
    "logo": "string"
  },
  "league": {
    "id": "integer",
    "name": "string",
    "country": "string",
    "season": "string"
  },
  "venue": {
    "name": "string",
    "capacity": "integer",
    "city": "string"
  },
  "date": "string",
  "status": "string",
  "score": {
    "home": "integer",
    "away": "integer",
    "half_time": {
      "home": "integer",
      "away": "integer"
    }
  },
  "odds": {
    "home_win": "number",
    "draw": "number",
    "away_win": "number"
  }
}
```

---

## 🔒 认证与授权

### JWT Token认证 (未来功能)

```bash
# 获取Token
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=password"

# 使用Token访问受保护的API
curl -X GET "http://localhost:8000/api/v1/protected-endpoint" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### API密钥认证 (未来功能)

```bash
# 使用API密钥
curl -X GET "http://localhost:8000/api/v1/predictions" \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## 📈 性能优化建议

### 1. 请求优化
- **分页查询**: 使用limit和offset参数控制数据量
- **字段过滤**: 只请求需要的字段
- **缓存策略**: 合理使用客户端缓存

### 2. 批量操作
- **批量预测**: 支持一次提交多个预测请求
- **批量查询**: 支持批量查询多个资源

### 3. 异步处理
- **长时任务**: 对于耗时操作，返回任务ID后异步处理
- **状态查询**: 提供任务状态查询接口

---

## 📝 更新日志

### v1.0.0 (2025-11-06)
- ✅ 初始API版本发布
- ✅ 健康检查端点
- ✅ 预测服务API
- ✅ 数据管理API
- ✅ 系统管理API
- ✅ 错误处理机制
- ✅ 数据验证

### 未来版本计划
- v1.1.0: 用户认证和授权
- v1.2.0: 实时数据推送
- v1.3.0: 高级分析功能
- v2.0.0: 微服务架构升级

---

## 📞 联系信息

### 技术支持
- **API文档**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

### 开发团队
- **API架构**: FastAPI + SQLAlchemy 2.0
- **数据库**: PostgreSQL 13+
- **缓存**: Redis 6+
- **队列**: 自研FIFO队列系统

---

**文档版本**: v1.0
**最后更新**: 2025-11-06
**状态**: Phase 4: 文档完善