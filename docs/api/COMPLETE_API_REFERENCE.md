# 📚 足球预测系统完整API参考

## 🏗️ API架构概览

基于FastAPI框架构建的企业级RESTful API，提供完整的足球预测服务。

### 🔧 核心模块
- **预测服务**: `/api/predictions/*` - 比赛预测和分析
- **健康检查**: `/health/*` - 系统状态监控
- **数据服务**: `/api/data/*` - 足球数据管理
- **用户管理**: `/api/users/*` - 用户认证和授权
- **实时流**: `/api/realtime/*` - 实时数据推送
- **性能监控**: `/api/monitoring/*` - 系统性能指标

---

## 🔐 认证和授权

### JWT Bearer Token认证
```bash
# 获取访问令牌
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# 使用令牌访问API
curl -X GET "http://localhost:8000/api/predictions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### OAuth2授权流程
```python
import requests

# 客户端凭证授权
auth_response = requests.post(
    "http://localhost:8000/auth/token",
    data={
        "grant_type": "client_credentials",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    }
)
token = auth_response.json()["access_token"]
```

---

## 📊 预测服务 API

### 1. 创建预测
```http
POST /api/predictions
Content-Type: application/json
Authorization: Bearer {token}

{
  "match_id": 12345,
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "home_score_prediction": 2,
  "away_score_prediction": 1,
  "confidence_score": 0.85,
  "prediction_type": "exact_score",
  "model_version": "v2.1"
}
```

**响应**:
```json
{
  "id": 789,
  "match_id": 12345,
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "home_score_prediction": 2,
  "away_score_prediction": 1,
  "confidence_score": 0.85,
  "prediction_type": "exact_score",
  "model_version": "v2.1",
  "created_at": "2025-11-10T12:30:00Z",
  "probability": {
    "home_win": 0.60,
    "draw": 0.25,
    "away_win": 0.15
  }
}
```

### 2. 获取预测列表
```http
GET /api/predictions?limit=10&offset=0&match_id=12345&team=Manchester%20United
Authorization: Bearer {token}
```

**响应**:
```json
{
  "items": [
    {
      "id": 789,
      "match_id": 12345,
      "home_team": "Manchester United",
      "away_team": "Liverpool",
      "prediction": {"home": 2, "away": 1},
      "confidence": 0.85,
      "status": "pending"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

### 3. 获取预测详情
```http
GET /api/predictions/{prediction_id}
Authorization: Bearer {token}
```

### 4. 更新预测结果
```http
PUT /api/predictions/{prediction_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "actual_home_score": 3,
  "actual_away_score": 1,
  "status": "completed",
  "accuracy_score": 0.75
}
```

### 5. 批量预测分析
```http
POST /api/predictions/batch-analyze
Content-Type: application/json
Authorization: Bearer {token}

{
  "match_ids": [12345, 12346, 12347],
  "analysis_type": "team_form",
  "include_confidence": true
}
```

---

## 🏥 健康检查 API

### 1. 基础健康检查
```http
GET /health/
```

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T12:30:00Z",
  "version": "v2.0.0",
  "uptime": 3600
}
```

### 2. 详细健康检查
```http
GET /health/detailed
```

**响应**:
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 15,
      "connections": 8
    },
    "redis": {
      "status": "healthy",
      "response_time": 2,
      "memory_usage": "45MB"
    },
    "prediction_model": {
      "status": "healthy",
      "model_version": "v2.1",
      "last_trained": "2025-11-01T00:00:00Z"
    }
  }
}
```

### 3. 系统指标
```http
GET /health/metrics
```

**响应**:
```json
{
  "cpu_usage": 25.5,
  "memory_usage": 512,
  "disk_usage": 1024,
  "active_connections": 45,
  "requests_per_minute": 120
}
```

---

## 📈 数据服务 API

### 1. 获取联赛列表
```http
GET /api/data/leagues?country=England&season=2024
Authorization: Bearer {token}
```

### 2. 获取球队信息
```http
GET /api/data/teams/{team_id}
Authorization: Bearer {token}
```

### 3. 获取比赛数据
```http
GET /api/data/matches?league_id=39&date_from=2025-11-01&date_to=2025-11-10
Authorization: Bearer {token}
```

### 4. 获取比赛赔率
```http
GET /api/data/odds/{match_id}
Authorization: Bearer {token}
```

---

## 👥 用户管理 API

### 1. 用户注册
```http
POST /api/users/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

### 2. 用户登录
```http
POST /api/users/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePassword123!"
}
```

### 3. 获取用户信息
```http
GET /api/users/me
Authorization: Bearer {token}
```

### 4. 更新用户配置
```http
PUT /api/users/preferences
Content-Type: application/json
Authorization: Bearer {token}

{
  "language": "en",
  "timezone": "UTC",
  "notification_preferences": {
    "email": true,
    "push": false
  }
}
```

---

## 🔄 实时流 API

### 1. WebSocket连接
```javascript
const ws = new WebSocket('ws://localhost:8000/api/realtime/match-updates');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('实时更新:', data);
};
```

### 2. 订阅比赛更新
```http
POST /api/realtime/subscribe
Content-Type: application/json
Authorization: Bearer {token}

{
  "match_ids": [12345, 12346],
  "event_types": ["score_change", "card", "substitution"]
}
```

---

## 📊 观察者系统 API

### 1. 获取系统状态
```http
GET /observers/
Authorization: Bearer {token}
```

**响应**:
```json
{
  "status": "healthy",
  "observer_count": 12,
  "subject_count": 8,
  "uptime": 86400
}
```

### 2. 获取系统指标
```http
GET /observers/metrics
Authorization: Bearer {token}
```

**响应**:
```json
{
  "system_metrics": {
    "cpu_usage": 25.5,
    "memory_usage": 512,
    "disk_usage": 1024
  },
  "prediction_metrics": {
    "total_predictions": 15000,
    "accuracy_rate": 0.78,
    "avg_response_time": 120
  }
}
```

### 3. 获取告警信息
```http
GET /observers/alerts
Authorization: Bearer {token}
```

### 4. 手动触发告警
```http
POST /observers/alerts
Content-Type: application/json
Authorization: Bearer {token}

{
  "type": "performance",
  "severity": "high",
  "message": "API响应时间超过阈值"
}
```

---

## 📊 性能监控 API

### 1. 获取系统性能指标
```http
GET /api/monitoring/performance
Authorization: Bearer {token}
```

### 2. 获取API使用统计
```http
GET /api/monitoring/usage-stats?period=24h
Authorization: Bearer {token}
```

### 3. 模型性能指标
```http
GET /api/monitoring/model-performance?model_id=v2.1
Authorization: Bearer {token}
```

---

## 🔧 高级功能 API

### 1. 批量预测优化
```http
POST /api/predictions/optimize-batch
Content-Type: application/json
Authorization: Bearer {token}

{
  "predictions": [
    {
      "match_id": 12345,
      "home_team": "Team A",
      "away_team": "Team B"
    }
  ],
  "optimization_strategy": "max_confidence"
}
```

### 2. 模型集成
```http
POST /api/predictions/ensemble
Content-Type: application/json
Authorization: Bearer {token}

{
  "match_id": 12345,
  "models": ["ml_model_v2", "statistical_model", "expert_model"],
  "weights": [0.4, 0.3, 0.3]
}
```

---

## 🚫 错误处理

### HTTP状态码
- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 认证失败
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `422 Unprocessable Entity` - 数据验证失败
- `429 Too Many Requests` - 请求频率限制
- `500 Internal Server Error` - 服务器内部错误

### 错误响应格式
```json
{
  "error": {
    "code": "PREDICTION_NOT_FOUND",
    "message": "指定的预测不存在",
    "details": {
      "prediction_id": "99999",
      "timestamp": "2025-11-10T12:30:00Z"
    }
  }
}
```

---

## 📏 请求限制

### 频率限制
- **免费用户**: 100 requests/hour
- **付费用户**: 1000 requests/hour
- **企业用户**: 10000 requests/hour

### 配额限制
```http
GET /api/quota
Authorization: Bearer {token}
```

---

## 🧪 SDK和工具

### Python SDK示例
```python
from football_prediction_sdk import FootballPredictionClient

client = FootballPredictionClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# 创建预测
prediction = client.predictions.create(
    match_id=12345,
    home_team="Manchester United",
    away_team="Liverpool",
    home_score=2,
    away_score=1
)

# 获取健康状态
health = client.health.check_detailed()
```

### JavaScript SDK示例
```javascript
import { FootballPredictionAPI } from 'football-prediction-sdk';

const api = new FootballPredictionAPI({
  baseURL: 'http://localhost:8000',
  apiKey: 'your_api_key'
});

// 创建预测
const prediction = await api.predictions.create({
  matchId: 12345,
  homeTeam: 'Manchester United',
  awayTeam: 'Liverpool',
  homeScore: 2,
  awayScore: 1
});
```

---

## 📖 在线文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 🔗 相关链接

- [预测API详细说明](predictions.md)
- [健康检查API](health.md)
- [错误代码参考](errors.md)
- [快速部署指南](../README.md)
- [开发者社区](https://github.com/xupeng211/FootballPrediction/discussions)

---

**文档版本**: v3.0.0
**最后更新**: 2025-11-10
**API版本**: v2.1.0
**维护团队**: API开发团队