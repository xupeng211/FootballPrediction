# API参考文档

## API 参考文档

足球比赛结果预测系统 - 完整API接口参考手册

Version: 1.0.0
Update: 2025-11-10
Author: Claude Code

---

## 📋 目录

- [API概述](#api概述)
- [认证与授权](#认证与授权)
- [通用响应格式](#通用响应格式)
- [错误处理](#错误处理)
- [API端点](#api端点)
  - [系统管理](#系统管理)
  - [健康检查](#健康检查)
  - [预测服务](#预测服务)
  - [数据管理](#数据管理)
  - [用户服务](#用户服务)
- [数据模型](#数据模型)
- [性能指南](#性能指南)
- [SDK支持](#sdk支持)

---

## 🎯 API概述

### 基础信息

- **基础URL**: `https://api.football-prediction.com/v1`
- **协议**: HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8
- **API版本**: v1.0.0

### 技术特性

- **异步架构**: FastAPI + asyncio
- **认证方式**: JWT Bearer Token
- **缓存策略**: Redis智能缓存
- **限流控制**: 请求频率限制
- **监控指标**: APM性能监控
- **文档标准**: OpenAPI 3.0规范

### 支持的HTTP方法

- `GET` - 获取资源
- `POST` - 创建资源
- `PUT` - 更新资源
- `DELETE` - 删除资源
- `PATCH` - 部分更新资源
- `OPTIONS` - 预检请求

---

## 🔐 认证与授权

### JWT Bearer认证

```http
Authorization: Bearer <jwt_token>
```

### 获取Token

#### POST /auth/token

**请求体**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**响应**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**请求示例**:

```python
import requests

response = requests.post(
    "https://api.football-prediction.com/v1/auth/token",
    json={
        "username": "your_username",
        "password": "your_password"
    }
)

if response.status_code == 200:
    data = response.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
```

```javascript
const response = await fetch('https://api.football-prediction.com/v1/auth/token', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'your_username',
        password: 'your_password'
    })
});

const data = await response.json();
const token = data.access_token;
const headers = { 'Authorization': `Bearer ${token}` };
```

```java
import java.net.http.*;
import java.net.URI;

var client = HttpClient.newHttpClient();
var requestBody = "{\"username\":\"your_username\",\"password\":\"your_password\"}";

var request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.football-prediction.com/v1/auth/token"))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
    .build();

var response = client.send(request, HttpResponse.BodyHandlers.ofString());
var data = new JSONObject(response.body());
var token = data.getString("access_token");
```

---

## 📊 通用响应格式

### 成功响应格式

```json
{
  "success": true,
  "data": {
    // 响应数据
  },
  "meta": {
    "timestamp": "2025-11-10T14:30:00Z",
    "request_id": "req_123456789",
    "version": "v1.0.0"
  }
}
```

### 分页响应格式

```json
{
  "success": true,
  "data": [
    // 数据项
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 100,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    },
    "timestamp": "2025-11-10T14:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "输入数据验证失败",
    "details": {
      "field": "match_id",
      "reason": "required field is missing"
    }
  },
  "meta": {
    "timestamp": "2025-11-10T14:30:00Z",
    "request_id": "req_123456789"
  }
}
```

---

## ⚠️ 错误处理

### HTTP状态码

| 状态码 | 说明 | 含义 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未授权访问 |
| 403 | Forbidden | 禁止访问 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求频率超限 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

### 错误代码详解

#### 认证错误 (AUTH_*)
- `AUTH_001`: Token缺失或格式错误
- `AUTH_002`: Token已过期
- `AUTH_003`: Token无效
- `AUTH_004`: 用户名或密码错误
- `AUTH_005`: 账户已被禁用

#### 验证错误 (VALIDATION_*)
- `VALIDATION_001`: 必填字段缺失
- `VALIDATION_002`: 字段格式错误
- `VALIDATION_003`: 字段值超出范围
- `VALIDATION_004`: 日期时间格式错误
- `VALIDATION_005`: 邮箱格式错误

#### 业务错误 (BUSINESS_*)
- `BUSINESS_001`: 比赛不存在
- `BUSINESS_002`: 预测服务暂时不可用
- `BUSINESS_003`: 重复预测请求
- `BUSINESS_004`: 超出预测限额
- `BUSINESS_005`: 数据处理中

#### 系统错误 (SYSTEM_*)
- `SYSTEM_001`: 数据库连接失败
- `SYSTEM_002`: 外部服务不可用
- `SYSTEM_003`: 缓存服务异常
- `SYSTEM_004`: 文件系统错误
- `SYSTEM_005`: 内存不足

### 错误处理示例

```python
import requests
from requests.exceptions import HTTPError

def handle_api_error(response):
    """处理API错误响应"""
    try:
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        status_code = response.status_code
        error_data = response.json()

        if status_code == 401:
            print("认证失败，请重新登录")
        elif status_code == 429:
            print("请求过于频繁，请稍后再试")
        elif status_code >= 500:
            print("服务器错误，请联系技术支持")
        else:
            error_code = error_data.get("error", {}).get("code", "UNKNOWN")
            error_message = error_data.get("error", {}).get("message", "未知错误")
            print(f"错误 {error_code}: {error_message}")

        raise

# 使用示例
try:
    response = requests.get("https://api.football-prediction.com/v1/predictions")
    data = handle_api_error(response)
except Exception as e:
    print(f"请求失败: {e}")
```

---

## 🔗 API端点

## 系统管理

### GET /api/info

获取API基本信息。

**认证要求**: 无

**请求参数**: 无

**响应示例**:
```json
{
  "success": true,
  "data": {
    "api_version": "1.0.0",
    "system_status": "operational",
    "uptime_seconds": 86400,
    "supported_features": [
      "predictions",
      "match_data",
      "real_time_updates"
    ]
  },
  "meta": {
    "timestamp": "2025-11-10T14:30:00Z",
    "request_id": "req_info_123"
  }
}
```

### GET /api/metrics

获取系统性能指标。

**认证要求**: 需要管理员权限

**请求参数**: 无

**响应示例**:
```json
{
  "success": true,
  "data": {
    "performance": {
      "cpu_usage": 45.2,
      "memory_usage": 67.8,
      "disk_usage": 23.1
    },
    "api_stats": {
      "requests_per_minute": 150,
      "avg_response_time": 120,
      "error_rate": 0.02
    }
  },
  "meta": {
    "timestamp": "2025-11-10T14:30:00Z",
    "request_id": "req_metrics_456"
  }
}
```

---

## 健康检查

### GET /health

基础健康检查。

**认证要求**: 无

**请求参数**: 无

**响应示例**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-11-10T14:30:00Z",
    "version": "1.0.0"
  }
}
```

### GET /health/detailed

详细健康检查。

**认证要求**: 无

**请求参数**: 无

**响应示例**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "checks": {
      "database": {
        "status": "healthy",
        "response_time_ms": 5,
        "details": "PostgreSQL连接正常"
      },
      "redis": {
        "status": "healthy",
        "response_time_ms": 2,
        "details": "Redis缓存服务正常"
      },
      "external_apis": {
        "status": "degraded",
        "response_time_ms": 1200,
        "details": "外部API响应较慢"
      }
    },
    "timestamp": "2025-11-10T14:30:00Z"
  }
}
```

---

## 预测服务

### POST /predictions/enhanced

创建增强预测请求。

**认证要求**: 需要

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| match_id | string | 是 | 比赛ID | "match_12345" |
| home_team | string | 是 | 主队名称 | "Manchester United" |
| away_team | string | 是 | 客队名称 | "Liverpool" |
| match_date | string | 是 | 比赛日期(ISO 8601) | "2025-11-15T20:00:00Z" |
| league | string | 是 | 联赛名称 | "Premier League" |
| features | object | 否 | 特征数据 | 见下方 |

**features字段结构**:
```json
{
  "team_form": {
    "home_last_5": [3, 1, 0, 3, 1],
    "away_last_5": [1, 0, 3, 1, 0]
  },
  "head_to_head": {
    "home_wins": 8,
    "away_wins": 6,
    "draws": 4
  },
  "player_stats": {
    "home_key_players_available": true,
    "away_key_players_available": false
  }
}
```

**请求示例**:
```json
{
  "match_id": "match_12345",
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "match_date": "2025-11-15T20:00:00Z",
  "league": "Premier League",
  "features": {
    "team_form": {
      "home_last_5": [3, 1, 0, 3, 1],
      "away_last_5": [1, 0, 3, 1, 0]
    }
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "prediction_id": "pred_abcdef123456",
    "match_id": "match_12345",
    "prediction": {
      "home_win_probability": 0.42,
      "draw_probability": 0.28,
      "away_win_probability": 0.30,
      "recommended_bet": "home_win",
      "confidence_score": 0.75
    },
    "model_info": {
      "model_version": "v2.1.0",
      "training_data_period": "2020-2025",
      "accuracy_score": 0.82
    },
    "created_at": "2025-11-10T14:30:00Z"
  },
  "meta": {
    "request_id": "req_pred_789",
    "timestamp": "2025-11-10T14:30:00Z"
  }
}
```

### GET /predictions/{prediction_id}

获取预测结果。

**认证要求**: 需要

**路径参数**:
- `prediction_id`: 预测ID

**响应示例**:
```json
{
  "success": true,
  "data": {
    "prediction_id": "pred_abcdef123456",
    "status": "completed",
    "result": {
      "final_score": {
        "home": 2,
        "away": 1
      },
      "prediction_accuracy": true,
      "performance_metrics": {
        "calibration_score": 0.88,
        "ranking_correlation": 0.75
      }
    },
    "created_at": "2025-11-10T14:30:00Z",
    "completed_at": "2025-11-15T22:15:00Z"
  }
}
```

### GET /predictions/history

获取预测历史记录。

**认证要求**: 需要

**查询参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量 |
| status | string | 否 | - | 状态筛选 |
| date_from | string | 否 | - | 开始日期 |
| date_to | string | 否 | - | 结束日期 |

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "prediction_id": "pred_123",
      "match_id": "match_12345",
      "home_team": "Manchester United",
      "away_team": "Liverpool",
      "prediction": "home_win",
      "actual_result": "home_win",
      "status": "completed",
      "created_at": "2025-11-10T14:30:00Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 100,
      "total_pages": 5
    }
  }
}
```

### POST /predictions/batch

批量创建预测。

**认证要求**: 需要

**请求参数**:
```json
{
  "predictions": [
    {
      "match_id": "match_123",
      "home_team": "Team A",
      "away_team": "Team B",
      "match_date": "2025-11-15T20:00:00Z",
      "league": "Premier League"
    }
  ]
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_789",
    "predictions": [
      {
        "prediction_id": "pred_123",
        "status": "processing"
      }
    ],
    "processing_estimated_time": 30
  }
}
```

---

## 数据管理

### GET /matches

获取比赛列表。

**认证要求**: 需要

**查询参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| league | string | 否 | - | 联赛筛选 |
| date_from | string | 否 | - | 开始日期 |
| date_to | string | 否 | - | 结束日期 |
| status | string | 否 | - | 比赛状态 |
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量 |

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "match_id": "match_123",
      "home_team": "Manchester United",
      "away_team": "Liverpool",
      "league": "Premier League",
      "match_date": "2025-11-15T20:00:00Z",
      "status": "scheduled",
      "venue": "Old Trafford"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 50,
      "total_pages": 3
    }
  }
}
```

### GET /matches/{match_id}

获取比赛详情。

**认证要求**: 需要

**路径参数**:
- `match_id`: 比赛ID

**响应示例**:
```json
{
  "success": true,
  "data": {
    "match_id": "match_123",
    "home_team": {
      "name": "Manchester United",
      "form": ["W", "D", "W", "L", "W"],
      "position": 3
    },
    "away_team": {
      "name": "Liverpool",
      "form": ["W", "W", "D", "W", "W"],
      "position": 1
    },
    "head_to_head": {
      "matches": 10,
      "home_wins": 4,
      "away_wins": 4,
      "draws": 2
    },
    "match_date": "2025-11-15T20:00:00Z",
    "venue": "Old Trafford",
    "weather": "Cloudy, 12°C"
  }
}
```

### GET /leagues

获取联赛列表。

**认证要求**: 需要

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "league_id": "premier_league",
      "name": "Premier League",
      "country": "England",
      "season": "2025-2026",
      "total_teams": 20,
      "current_matchday": 12
    }
  ]
}
```

---

## 用户服务

### GET /user/profile

获取用户配置信息。

**认证要求**: 需要

**响应示例**:
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "username": "john_doe",
    "email": "john@example.com",
    "subscription": {
      "plan": "premium",
      "expires_at": "2026-11-10",
      "features": ["unlimited_predictions", "real_time_updates"]
    },
    "preferences": {
      "favorite_teams": ["Manchester United"],
      "notification_settings": {
        "predictions": true,
        "match_results": true
      }
    }
  }
}
```

### PUT /user/profile

更新用户配置信息。

**认证要求**: 需要

**请求参数**:
```json
{
  "preferences": {
    "favorite_teams": ["Manchester United", "Liverpool"],
    "notification_settings": {
      "predictions": false,
      "match_results": true
    }
  }
}
```

### GET /user/statistics

获取用户统计信息。

**认证要求**: 需要

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_predictions": 150,
    "successful_predictions": 95,
    "success_rate": 0.633,
    "favorite_league": "Premier League",
    "monthly_stats": [
      {
        "month": "2025-10",
        "predictions": 25,
        "success_rate": 0.68
      }
    ]
  }
}
```

---

## 📋 数据模型

### Match (比赛)

```json
{
  "match_id": "string",
  "home_team": "string",
  "away_team": "string",
  "league": "string",
  "match_date": "string (ISO 8601)",
  "status": "scheduled|live|completed|postponed",
  "venue": "string",
  "score": {
    "home": "integer",
    "away": "integer"
  }
}
```

### Prediction (预测)

```json
{
  "prediction_id": "string",
  "match_id": "string",
  "probabilities": {
    "home_win": "number (0-1)",
    "draw": "number (0-1)",
    "away_win": "number (0-1)"
  },
  "recommended_bet": "string",
  "confidence_score": "number (0-1)",
  "model_version": "string",
  "created_at": "string (ISO 8601)",
  "status": "processing|completed|failed"
}
```

### Team (球队)

```json
{
  "team_id": "string",
  "name": "string",
  "league": "string",
  "country": "string",
  "founded_year": "integer",
  "stadium": "string",
  "current_form": ["string"],
  "position": "integer",
  "points": "integer"
}
```

### User (用户)

```json
{
  "user_id": "string",
  "username": "string",
  "email": "string",
  "subscription": {
    "plan": "string",
    "expires_at": "string (ISO 8601)",
    "features": ["string"]
  },
  "preferences": {
    "favorite_teams": ["string"],
    "notification_settings": {
      "predictions": "boolean",
      "match_results": "boolean"
    }
  }
}
```

---

## ⚡ 性能指南

### 请求优化

#### 缓存策略
- **预测结果**: 缓存24小时
- **比赛数据**: 缓存1小时
- **用户配置**: 缓存30分钟

#### 限流控制
- **免费用户**: 100请求/小时
- **付费用户**: 1000请求/小时
- **企业用户**: 无限制

#### 批量操作
- 批量预测支持最多50场比赛
- 批量结果查询优化分页加载
- 使用WebSocket获取实时更新

### 响应时间目标

| 操作类型 | 目标响应时间 | 95%分位数 |
|----------|-------------|-----------|
| 健康检查 | < 50ms | < 100ms |
| 用户认证 | < 200ms | < 400ms |
| 数据查询 | < 300ms | < 600ms |
| 预测生成 | < 2000ms | < 5000ms |
| 批量处理 | < 10000ms | < 20000ms |

### 最佳实践

#### 请求优化
```python
# ✅ 好的做法 - 使用适当的超时
response = requests.get(
    "https://api.football-prediction.com/v1/matches",
    headers=headers,
    timeout=(3.05, 27)  # 连接超时3秒，读取超时27秒
)

# ✅ 好的做法 - 使用连接池
session = requests.Session()
session.mount('https://api.football-prediction.com',
              HTTPAdapter(pool_connections=10, pool_maxsize=100))

# ❌ 避免的做法 - 阻塞式等待
time.sleep(1)  # 不要使用固定延迟
```

#### 错误处理
```python
# ✅ 好的做法 - 指数退避重试
import time
from requests.exceptions import RequestException

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            time.sleep(wait_time)
```

#### 数据处理
```python
# ✅ 好的做法 - 流式处理大数据
import json
from contextlib import closing

def process_large_prediction_batch(batch_id):
    url = f"https://api.football-prediction.com/v1/predictions/batch/{batch_id}/stream"

    with closing(requests.get(url, headers=headers, stream=True)) as response:
        for line in response.iter_lines():
            if line:
                prediction = json.loads(line)
                process_prediction(prediction)
```

---

## 🛠️ SDK支持

### 官方Python SDK

#### 安装
```bash
pip install football-prediction-sdk
```

#### 使用示例
```python
from football_prediction_sdk import FootballPredictionClient

# 初始化客户端
client = FootballPredictionClient(
    base_url="https://api.football-prediction.com/v1",
    api_key="your_api_key"
)

# 创建预测
prediction = client.predictions.create(
    match_id="match_123",
    home_team="Manchester United",
    away_team="Liverpool",
    match_date="2025-11-15T20:00:00Z",
    league="Premier League"
)

print(f"预测ID: {prediction.id}")
print(f"主胜概率: {prediction.home_win_probability:.2%}")
```

### JavaScript SDK

#### 安装
```bash
npm install @football-prediction/sdk
```

#### 使用示例
```javascript
import { FootballPredictionClient } from '@football-prediction/sdk';

const client = new FootballPredictionClient({
  baseURL: 'https://api.football-prediction.com/v1',
  apiKey: 'your_api_key'
});

const prediction = await client.predictions.create({
  matchId: 'match_123',
  homeTeam: 'Manchester United',
  awayTeam: 'Liverpool',
  matchDate: '2025-11-15T20:00:00Z',
  league: 'Premier League'
});

console.log(`预测ID: ${prediction.id}`);
console.log(`主胜概率: ${(prediction.homeWinProbability * 100).toFixed(1)}%`);
```

### Java SDK

#### Maven依赖
```xml
<dependency>
    <groupId>com.football-prediction</groupId>
    <artifactId>sdk</artifactId>
    <version>1.0.0</version>
</dependency>
```

#### 使用示例
```java
import com.football.prediction.sdk.FootballPredictionClient;
import com.football.prediction.sdk.model.Prediction;

public class Example {
    public static void main(String[] args) {
        FootballPredictionClient client = new FootballPredictionClient
            .Builder("your_api_key")
            .baseUrl("https://api.football-prediction.com/v1")
            .build();

        Prediction prediction = client.predictions()
            .create(PredictionRequest.builder()
                .matchId("match_123")
                .homeTeam("Manchester United")
                .awayTeam("Liverpool")
                .matchDate("2025-11-15T20:00:00Z")
                .league("Premier League")
                .build());

        System.out.println("预测ID: " + prediction.getId());
        System.out.println("主胜概率: " + String.format("%.1f%%",
            prediction.getHomeWinProbability() * 100));
    }
}
```

---

## 📞 支持与帮助

### 技术支持
- **邮箱**: support@football-prediction.com
- **文档**: https://docs.football-prediction.com
- **状态页面**: https://status.football-prediction.com

### 常见问题
- Q: 如何获取API密钥？
  A: 在用户控制台的"API设置"页面生成API密钥。

- Q: 请求频率限制是多少？
  A: 免费用户100请求/小时，付费用户1000请求/小时。

- Q: 如何获取实时比赛更新？
  A: 使用WebSocket连接 `wss://api.football-prediction.com/v1/ws`

- Q: 预测准确率如何？
  A: 平均预测准确率约为75-85%，具体取决于联赛和数据质量。

### 更新日志
- **v1.0.0** (2025-11-10): 初始API版本发布
- **v0.9.0** (2025-10-15): Beta版本测试
- **v0.8.0** (2025-09-20): Alpha版本发布

---

*文档版本: v1.0.0 | 最后更新: 2025-11-10 | 维护者: Claude Code*
