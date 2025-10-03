# Football Prediction System - 生产环境API参考

## 概述

本文档提供了Football Prediction System生产环境的完整API参考。

## 基础信息

- **基础URL**: `https://api.football-prediction.com/v1`
- **API版本**: v1
- **认证方式**: Bearer Token (JWT)
- **内容类型**: application/json

## 认证

所有API请求都需要认证，使用JWT Bearer Token：

```http
Authorization: Bearer <your-jwt-token>
```

### 获取访问令牌

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=your_username&password=your_password
```

响应：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## API端点

### 1. 预测服务

#### 获取比赛预测

```http
GET /predictions/matches/{match_id}
```

**参数**:
- `match_id` (路径参数): 比赛ID
- `model_version` (查询参数, 可选): 模型版本，默认为最新

**响应示例**:
```json
{
  "match_id": "20240102_001",
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "prediction": {
    "home_win": 0.45,
    "draw": 0.25,
    "away_win": 0.30,
    "confidence": 0.87,
    "model_version": "v2.1.0"
  },
  "features": {
    "home_form": 3.2,
    "away_form": 2.8,
    "head_to_head": 0.6,
    "injuries": {
      "home": 1,
      "away": 0
    }
  },
  "metadata": {
    "generated_at": "2025-01-02T12:00:00Z",
    "processing_time": 0.045
  }
}
```

#### 批量获取预测

```http
POST /predictions/batch
Content-Type: application/json

{
  "match_ids": ["20240102_001", "20240102_002", "20240102_003"],
  "model_version": "v2.1.0"
}
```

**响应示例**:
```json
{
  "predictions": [
    {
      "match_id": "20240102_001",
      "prediction": {...}
    },
    {
      "match_id": "20240102_002",
      "prediction": {...}
    }
  ],
  "summary": {
    "total": 3,
    "successful": 3,
    "failed": 0
  }
}
```

### 2. 比赛管理

#### 获取比赛列表

```http
GET /matches
```

**查询参数**:
- `league` (可选): 联赛ID
- `date_from` (可选): 开始日期 (YYYY-MM-DD)
- `date_to` (可选): 结束日期 (YYYY-MM-DD)
- `status` (可选): 状态 (scheduled, in_progress, finished)
- `limit` (可选): 返回数量限制，默认50
- `offset` (可选): 偏移量，默认0

**响应示例**:
```json
{
  "matches": [
    {
      "id": "20240102_001",
      "home_team": "Manchester United",
      "away_team": "Liverpool",
      "league": "premier_league",
      "date": "2025-01-02T15:00:00Z",
      "status": "scheduled",
      "venue": "Old Trafford"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 50,
    "offset": 0
  }
}
```

#### 获取比赛详情

```http
GET /matches/{match_id}
```

### 3. 模型服务

#### 获取模型信息

```http
GET /models/info
```

**响应示例**:
```json
{
  "current_version": "v2.1.0",
  "available_versions": ["v2.1.0", "v2.0.0"],
  "performance_metrics": {
    "accuracy": 0.687,
    "precision": 0.695,
    "recall": 0.672,
    "f1_score": 0.683
  },
  "training_data": {
    "last_updated": "2025-01-01T00:00:00Z",
    "matches_count": 12500
  }
}
```

#### 获取模型特征重要性

```http
GET /models/features
```

**响应示例**:
```json
{
  "features": [
    {
      "name": "home_form",
      "importance": 0.234,
      "description": "主队最近5场平均得分"
    },
    {
      "name": "away_form",
      "importance": 0.198,
      "description": "客队最近5场平均得分"
    }
  ]
}
```

### 4. 健康检查

#### 服务健康状态

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-02T12:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "model_service": "healthy"
  },
  "version": "1.0.0"
}
```

#### 详细的健康检查

```http
GET /health/detailed
```

**响应示例**:
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "connection_pool": {
        "active": 5,
        "idle": 15,
        "total": 20
      },
      "response_time": "5ms"
    },
    "redis": {
      "status": "healthy",
      "connected_clients": 42,
      "used_memory": "256MB"
    },
    "model_service": {
      "status": "healthy",
      "model_version": "v2.1.0",
      "inference_time": "45ms"
    }
  }
}
```

### 5. 监控指标

#### API指标

```http
GET /metrics
```

返回Prometheus格式的指标数据。

#### 性能指标

```http
GET /performance
```

**响应示例**:
```json
{
  "api": {
    "requests_per_second": 125.5,
    "average_response_time": 45.2,
    "error_rate": 0.02
  },
  "predictions": {
    "today": 15420,
    "success_rate": 99.8,
    "average_confidence": 0.76
  }
}
```

## 错误处理

所有API在发生错误时返回标准化的错误响应：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Match not found",
    "details": "Match ID 'invalid_id' does not exist"
  },
  "request_id": "req_123456789",
  "timestamp": "2025-01-02T12:00:00Z"
}
```

### 常见错误码

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_REQUEST | 请求格式错误 |
| 401 | UNAUTHORIZED | 未授权 |
| 403 | FORBIDDEN | 权限不足 |
| 404 | RESOURCE_NOT_FOUND | 资源不存在 |
| 429 | RATE_LIMITED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
| 503 | SERVICE_UNAVAILABLE | 服务暂时不可用 |

## 速率限制

- **默认限制**: 每分钟1000次请求
- **突发限制**: 每分钟100次请求
- **限制类型**: 基于IP和用户令牌

响应头包含当前限制信息：
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641148800
```

## 缓存策略

API使用多级缓存以提高性能：

### 缓存头
- `Cache-Control: public, max-age=300` - 公共数据缓存5分钟
- `Cache-Control: private, max-age=60` - 私人数据缓存1分钟

### 预测缓存
- 预测结果缓存30分钟
- 比赛数据缓存5分钟
- 模型信息缓存24小时

## WebSocket端点

### 实时预测更新

```
wss://api.football-prediction.com/v1/ws/predictions
```

**订阅消息**:
```json
{
  "action": "subscribe",
  "match_ids": ["20240102_001", "20240102_002"]
}
```

**更新消息**:
```json
{
  "type": "prediction_update",
  "match_id": "20240102_001",
  "data": {
    "prediction": {...},
    "last_updated": "2025-01-02T12:00:00Z"
  }
}
```

## SDK和客户端

### Python SDK

```python
from football_prediction_sdk import FootballPredictionAPI

# 初始化客户端
client = FootballPredictionAPI(
    api_key="your-api-key",
    base_url="https://api.football-prediction.com/v1"
)

# 获取预测
prediction = client.get_prediction("20240102_001")
print(prediction.home_win)
```

### JavaScript SDK

```javascript
import { FootballPredictionAPI } from 'football-prediction-sdk';

const client = new FootballPredictionAPI({
  apiKey: 'your-api-key',
  baseURL: 'https://api.football-prediction.com/v1'
});

// 获取预测
const prediction = await client.getPrediction('20240102_001');
console.log(prediction.home_win);
```

## 最佳实践

1. **重试机制**：实现指数退避重试
2. **批量请求**：使用批量端点减少请求次数
3. **缓存利用**：利用客户端缓存减少API调用
4. **错误处理**：正确处理所有错误码
5. **监控**：监控API使用情况和性能

## 更新日志

### v1.2.0 (2025-01-02)
- 新增批量预测端点
- 添加WebSocket实时更新
- 优化性能指标API

### v1.1.0 (2024-12-15)
- 新增模型特征重要性端点
- 改进错误响应格式
- 添加性能指标

### v1.0.0 (2024-12-01)
- 初始版本发布
- 基础预测功能
- 认证和授权系统

## 支持

- **API文档**: https://docs.football-prediction.com/api
- **技术支持**: api-support@football-prediction.com
- **状态页面**: https://status.football-prediction.com

---

*最后更新: 2025-01-02*