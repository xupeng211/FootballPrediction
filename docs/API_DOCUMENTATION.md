# API文档

## 概述

足球预测API是一个基于FastAPI构建的RESTful API服务，提供足球比赛预测、数据管理和监控功能。

## 基本信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1
- **协议**: HTTP/HTTPS
- **数据格式**: JSON

## 认证

目前API使用Bearer Token认证（开发中）：

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/predictions
```

## 端点概览

### 健康检查

#### GET /api/health
系统健康检查端点

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "football-prediction-api",
  "version": "1.0.0",
  "uptime": 3600.0,
  "response_time_ms": 5.2,
  "checks": {
    "database": {
      "healthy": true,
      "status": "healthy",
      "response_time_ms": 2.1
    },
    "redis": {
      "healthy": true,
      "status": "healthy",
      "response_time_ms": 1.5
    }
  }
}
```

#### GET /api/health/liveness
存活性检查（Kubernetes兼容）

**响应**: `200 OK` 如果服务运行中

#### GET /api/health/readiness
就绪性检查（Kubernetes兼容）

**响应**: `200 OK` 如果服务就绪

### 预测API

#### POST /api/v1/predictions
创建新的比赛预测

**请求体**:
```json
{
  "home_team": "Team A",
  "away_team": "Team B",
  "match_date": "2024-01-15",
  "league": "Premier League"
}
```

**响应**:
```json
{
  "id": 1,
  "home_team": "Team A",
  "away_team": "Team B",
  "prediction": "2-1",
  "confidence": 0.75,
  "probability": {
    "home_win": 0.55,
    "draw": 0.25,
    "away_win": 0.20
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/predictions/{prediction_id}
获取预测详情

**路径参数**:
- `prediction_id`: 预测ID

**响应**:
```json
{
  "id": 1,
  "home_team": "Team A",
  "away_team": "Team B",
  "prediction": "2-1",
  "confidence": 0.75,
  "status": "completed",
  "actual_result": "2-0",
  "accuracy": true
}
```

#### GET /api/v1/predictions
获取预测列表

**查询参数**:
- `limit`: 返回数量（默认: 10）
- `offset`: 偏移量（默认: 0）
- `status`: 过滤状态 (pending/completed)
- `league`: 过滤联赛

**响应**:
```json
{
  "total": 100,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "home_team": "Team A",
      "away_team": "Team B",
      "prediction": "2-1",
      "confidence": 0.75
    }
  ]
}
```

### 数据管理

#### GET /api/v1/data/matches
获取比赛数据

**查询参数**:
- `league`: 联赛名称
- `season`: 赛季
- `start_date`: 开始日期
- `end_date`: 结束日期

**响应**:
```json
{
  "matches": [
    {
      "id": 1,
      "home_team": "Team A",
      "away_team": "Team B",
      "date": "2024-01-15",
      "league": "Premier League",
      "season": "2023-24"
    }
  ]
}
```

#### POST /api/v1/data/import
导入外部数据

**请求体**:
```json
{
  "source": "api-football",
  "data_type": "matches",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  }
}
```

### 特征管理

#### GET /api/v1/features
获取可用特征列表

**响应**:
```json
{
  "features": [
    {
      "name": "home_win_rate",
      "type": "numeric",
      "description": "主队胜率"
    },
    {
      "name": "recent_form",
      "type": "categorical",
      "description": "最近状态"
    }
  ]
}
```

#### POST /api/v1/features/calculate
计算特征值

**请求体**:
```json
{
  "match_id": 1,
  "features": ["home_win_rate", "away_win_rate"]
}
```

### 监控API

#### GET /api/v1/monitoring/metrics
获取系统指标

**响应**:
```json
{
  "requests_total": 1000,
  "requests_per_second": 10.5,
  "avg_response_time_ms": 150,
  "error_rate": 0.01,
  "active_connections": 25
}
```

#### GET /api/v1/monitoring/model-performance
获取模型性能指标

**响应**:
```json
{
  "accuracy": 0.68,
  "precision": 0.72,
  "recall": 0.65,
  "f1_score": 0.68,
  "predictions_count": 500,
  "last_updated": "2024-01-01T12:00:00Z"
}
```

## 错误处理

### 错误响应格式

```json
{
  "detail": "错误描述",
  "status_code": 400,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### HTTP状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 验证失败
- `500 Internal Server Error`: 服务器错误
- `503 Service Unavailable`: 服务不可用

## 速率限制

- **默认限制**: 100 请求/分钟
- **认证用户**: 1000 请求/分钟

超过限制时返回 `429 Too Many Requests`

## 数据模型

### Match（比赛）

```json
{
  "id": "integer",
  "home_team": "string",
  "away_team": "string",
  "date": "string (ISO 8601)",
  "league": "string",
  "season": "string",
  "home_score": "integer | null",
  "away_score": "integer | null",
  "status": "scheduled | live | completed | postponed"
}
```

### Prediction（预测）

```json
{
  "id": "integer",
  "match_id": "integer",
  "prediction": "string",
  "confidence": "float (0-1)",
  "probability": {
    "home_win": "float",
    "draw": "float",
    "away_win": "float"
  },
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

## 使用示例

### Python

```python
import requests

# 健康检查
response = requests.get("http://localhost:8000/api/health")
print(response.json())

# 创建预测
prediction_data = {
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "match_date": "2024-01-15",
    "league": "Premier League"
}
response = requests.post(
    "http://localhost:8000/api/v1/predictions",
    json=prediction_data,
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
print(response.json())
```

### cURL

```bash
# 健康检查
curl http://localhost:8000/api/health

# 创建预测
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "match_date": "2024-01-15",
    "league": "Premier League"
  }'
```

### JavaScript/TypeScript

```javascript
// 使用fetch
const response = await fetch('http://localhost:8000/api/health');
const data = await response.json();
console.log(data);

// 创建预测
const prediction = await fetch('http://localhost:8000/api/v1/predictions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    home_team: 'Manchester United',
    away_team: 'Liverpool',
    match_date: '2024-01-15',
    league: 'Premier League'
  })
});
```

## 交互式文档

访问以下URL查看交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 健康检查端点
- 预测CRUD操作
- 基础监控功能

## 联系和支持

- **问题反馈**: GitHub Issues
- **文档**: `/docs` 目录
- **邮件**: support@example.com

## 许可

本API文档遵循项目许可证。
