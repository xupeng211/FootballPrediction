# 📚 足球预测API文档

**版本**: 1.0.0
**生成时间**: 2025-11-11 01:44:14
**API覆盖率**: 39% (基于实际测试覆盖率)

## 🎯 概述

足球预测系统API提供了完整的足球数据查询、预测生成和系统监控功能。基于FastAPI构建，支持现代化的RESTful API设计。

### 🏗️ 技术栈
- **框架**: FastAPI + SQLAlchemy 2.0
- **数据库**: PostgreSQL + Redis
- **架构**: DDD + CQRS + 依赖注入
- **测试覆盖率**: 39%

### 🌐 服务器地址
- **开发环境**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc

## 📋 API分类

### 🔍 健康检查
提供API服务健康状态检查功能。

### ⚽ 预测服务
核心的足球比赛预测功能，支持单个预测和批量预测。

### 📊 数据服务
足球数据查询，包括比赛、球队、联赛等信息。

### 📈 监控服务
系统监控和指标收集，提供详细的系统和业务指标。

## 🛠️ API端点详情

### 健康检查

#### GET /api/v1/health/

**描述**: 基础健康检查

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

#### GET /api/v1/health/system

**描述**: 系统健康检查

**响应示例**:
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

---

### 预测服务

#### GET /predictions/

**描述**: 获取所有预测

**响应示例**:
```json
{
  "predictions": [],
  "total": 0
}
```

---

#### GET /predictions/{match_id}

**描述**: 获取特定比赛的预测

**响应示例**:
```json
{
  "match_id": 1,
  "prediction": {
    "result": "win",
    "confidence": 0.85
  }
}
```

---

#### POST /predictions/{match_id}/predict

**描述**: 为特定比赛生成预测

**请求体**:
```json
{
  "model_type": "ml",
  "features": {}
}
```

**响应示例**:
```json
{
  "prediction_id": "pred_123",
  "result": "win",
  "confidence": 0.85
}
```

---

#### POST /predictions/batch

**描述**: 批量预测

**请求体**:
```json
{
  "match_ids": [
    1,
    2,
    3
  ]
}
```

**响应示例**:
```json
{
  "predictions": [],
  "total_processed": 3
}
```

---

### 数据服务

#### GET /data/matches

**描述**: 获取比赛数据

**参数**:
- `league_id` (integer): 联赛ID
- `team_id` (integer): 球队ID
- `limit` (integer): 限制数量 (默认: 100)

**响应示例**:
```json
{
  "matches": [],
  "total": 0,
  "page": 1
}
```

---

#### GET /data/teams

**描述**: 获取球队数据

**参数**:
- `league_id` (integer): 联赛ID

**响应示例**:
```json
{
  "teams": [],
  "total": 0
}
```

---

#### GET /data/leagues

**描述**: 获取联赛数据

**响应示例**:
```json
{
  "leagues": [],
  "total": 0
}
```

---

### 监控服务

#### GET /monitoring/metrics

**描述**: 获取系统指标

**响应示例**:
```json
{
  "status": "ok",
  "system": {
    "cpu_percent": 45.2,
    "memory": {
      "percent": 68.5
    }
  },
  "database": {
    "healthy": true,
    "response_time_ms": 12.5
  },
  "business": {
    "24h_predictions": 150,
    "model_accuracy_30d": 78.5
  }
}
```

---

#### GET /monitoring/status

**描述**: 获取服务状态

**响应示例**:
```json
{
  "status": "healthy",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy"
  }
}
```

---

#### GET /monitoring/metrics/prometheus

**描述**: 获取Prometheus格式指标

**响应示例**:
```json
"# HELP http_requests_total Total HTTP requests\nhttp_requests_total 1000\n"
```

---

## 🚀 API使用示例

### 健康检查

**描述**: 检查API服务状态

**Curl示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/health/" -H "accept: application/json"
```

**Python示例**:
```python
import requests

response = requests.get("http://localhost:8000/api/v1/health/")
if response.status_code == 200:
    print(f"API状态: {response.json()['status']}")
else:
    print(f"健康检查失败: {response.status_code}")
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

### 获取预测列表

**描述**: 获取所有可用的预测

**Curl示例**:
```bash
curl -X GET "http://localhost:8000/predictions/" -H "accept: application/json"
```

**Python示例**:
```python
import requests

response = requests.get("http://localhost:8000/predictions/")
if response.status_code == 200:
    predictions = response.json()
    print(f"找到 {len(predictions.get('predictions', []))} 个预测")
else:
    print(f"获取预测失败: {response.status_code}")
```

**响应示例**:
```json
{
  "predictions": [
    {
      "prediction_id": "pred_123",
      "match_id": 1,
      "result": "win",
      "confidence": 0.85,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 生成比赛预测

**描述**: 为指定比赛生成新的预测

**Curl示例**:
```bash
curl -X POST "http://localhost:8000/predictions/1/predict" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "ml", "features": {"team_form": [1, 0, 1], "head_to_head": [2, 1]}}'
```

**Python示例**:
```python
import requests

prediction_data = {
    "model_type": "ml",
    "features": {
        "team_form": [1, 0, 1],
        "head_to_head": [2, 1]
    }
}

response = requests.post(
    "http://localhost:8000/predictions/1/predict",
    json=prediction_data
)

if response.status_code == 200:
    prediction = response.json()
    print(f"预测结果: {prediction['result']}")
    print(f"置信度: {prediction['confidence']:.2f}")
else:
    print(f"预测生成失败: {response.status_code}")
```

**响应示例**:
```json
{
  "prediction_id": "pred_456",
  "match_id": 1,
  "result": "win",
  "confidence": 0.87,
  "created_at": "2024-01-01T12:05:00Z"
}
```

---

### 获取系统指标

**描述**: 获取详细的系统和业务指标

**Curl示例**:
```bash
curl -X GET "http://localhost:8000/monitoring/metrics" -H "accept: application/json"
```

**Python示例**:
```python
import requests

response = requests.get("http://localhost:8000/monitoring/metrics")
if response.status_code == 200:
    metrics = response.json()
    print(f"系统状态: {metrics['status']}")
    print(f"CPU使用率: {metrics['system']['cpu_percent']:.1f}%")
    print(f"24小时预测数: {metrics['business']['24h_predictions']}")
    print(f"30天准确率: {metrics['business']['model_accuracy_30d']:.1f}%")
else:
    print(f"获取指标失败: {response.status_code}")
```

**响应示例**:
```json
{
  "status": "ok",
  "response_time_ms": 15.2,
  "system": {
    "cpu_percent": 45.2,
    "memory": {
      "total": 8589934592,
      "available": 2705326080,
      "percent": 68.5
    }
  },
  "database": {
    "healthy": true,
    "response_time_ms": 12.5,
    "statistics": {
      "teams_count": 150,
      "matches_count": 2500,
      "predictions_count": 1800
    }
  },
  "business": {
    "24h_predictions": 150,
    "upcoming_matches_7d": 25,
    "model_accuracy_30d": 78.5,
    "last_updated": "2024-01-01T12:00:00Z"
  }
}
```

---

## ❌ 错误处理

### 标准HTTP状态码

- **200 OK**: 请求成功
- **400 Bad Request**: 请求参数错误
- **401 Unauthorized**: 认证失败
- **404 Not Found**: 资源不存在
- **422 Unprocessable Entity**: 请求格式错误
- **500 Internal Server Error**: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息",
  "status_code": 400,
  "error_type": "ValidationError"
}
```

## 🔐 认证

当前版本不需要认证，但建议在生产环境中添加适当的认证机制。

## 📈 限流

为了保护系统稳定性，API实现了基本的限流机制：
- 每个IP每分钟最多100个请求
- 超出限制将返回429状态码

## 📞 支持

如有问题，请联系技术支持：
- 📧 Email: support@footballprediction.com
- 📖 文档: http://localhost:8000/docs
- 🐛 问题反馈: GitHub Issues

---

**📊 文档统计**:
- API端点数量: {len(api_endpoints)}
- 示例数量: {len(api_examples)}
- 覆盖率: 39%
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*此文档基于当前API架构自动生成，确保与实际API保持同步。*
