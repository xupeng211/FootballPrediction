# 足球预测系统 API 参考文档

## 📋 概述

本文档提供足球预测系统的完整API参考，包括RESTful API、WebSocket API、认证授权、错误处理等详细信息。

## 🌐 基础信息

- **基础URL**: `http://localhost:8000/api/v1`
- **WebSocket URL**: `ws://localhost:8000/realtime/ws`
- **API版本**: v1
- **内容类型**: `application/json`
- **认证方式**: JWT Bearer Token

## 🔐 认证授权

### JWT认证

#### 获取访问令牌
```http
POST /auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 使用访问令牌
```http
GET /api/v1/predictions
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

#### 刷新令牌
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 权限级别

| 级别 | 权限描述 | API限制 |
|------|----------|---------|
| `guest` | 访客 | 只读公共数据 |
| `user` | 普通用户 | 基础预测功能 |
| `premium` | 高级用户 | 高级分析功能 |
| `admin` | 管理员 | 全部功能 |

## 📊 数据模型

### 比赛 (Match)
```json
{
  "id": 1,
  "home_team": "曼联",
  "away_team": "切尔西",
  "league": "英超",
  "match_date": "2025-10-29T20:00:00Z",
  "status": "upcoming|live|finished",
  "home_score": 0,
  "away_score": 0,
  "venue": "老特拉福德球场",
  "created_at": "2025-10-29T10:00:00Z",
  "updated_at": "2025-10-29T10:00:00Z"
}
```

### 预测 (Prediction)
```json
{
  "id": 123,
  "match_id": 1,
  "strategy": "ml_ensemble",
  "home_win_prob": 0.65,
  "draw_prob": 0.25,
  "away_win_prob": 0.10,
  "confidence": 0.75,
  "prediction": "home_win",
  "expected_value": 0.12,
  "recommendation": "投注主胜",
  "created_at": "2025-10-29T10:30:00Z",
  "updated_at": "2025-10-29T10:30:00Z"
}
```

### 用户 (User)
```json
{
  "id": "user123",
  "username": "john_doe",
  "email": "john@example.com",
  "subscription_tier": "premium",
  "preferences": {
    "preferred_leagues": ["英超", "西甲"],
    "min_confidence": 0.7,
    "notifications_enabled": true
  },
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-10-29T09:00:00Z"
}
```

## 🔍 RESTful API

### 比赛管理

#### 获取比赛列表
```http
GET /api/v1/matches
```

**查询参数**:
- `league`: 联赛筛选 (可选)
- `status`: 比赛状态筛选 (可选)
- `date_from`: 开始日期 (可选)
- `date_to`: 结束日期 (可选)
- `limit`: 返回数量限制 (默认50)
- `offset`: 偏移量 (默认0)

**示例请求**:
```http
GET /api/v1/matches?league=英超&status=upcoming&limit=10
```

**响应**:
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/v1/matches?limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": 1,
      "home_team": "曼联",
      "away_team": "切尔西",
      "league": "英超",
      "match_date": "2025-10-29T20:00:00Z",
      "status": "upcoming"
    }
  ]
}
```

#### 获取单个比赛
```http
GET /api/v1/matches/{match_id}
```

**响应**:
```json
{
  "id": 1,
  "home_team": "曼联",
  "away_team": "切尔西",
  "league": "英超",
  "match_date": "2025-10-29T20:00:00Z",
  "status": "upcoming",
  "home_score": null,
  "away_score": null,
  "venue": "老特拉福德球场",
  "odds": {
    "home_win": 2.15,
    "draw": 3.25,
    "away_win": 3.40
  }
}
```

### 预测管理

#### 获取预测列表
```http
GET /api/v1/predictions
```

**查询参数**:
- `match_id`: 比赛ID筛选 (可选)
- `strategy`: 策略筛选 (可选)
- `confidence_min`: 最小置信度 (可选)
- `date_from`: 开始日期 (可选)
- `date_to`: 结束日期 (可选)
- `limit`: 返回数量限制 (默认50)
- `offset`: 偏移量 (默认0)

**示例请求**:
```http
GET /api/v1/predictions?confidence_min=0.8&limit=20
```

**响应**:
```json
{
  "count": 156,
  "results": [
    {
      "id": 123,
      "match_id": 1,
      "strategy": "ml_ensemble",
      "home_win_prob": 0.65,
      "draw_prob": 0.25,
      "away_win_prob": 0.10,
      "confidence": 0.75,
      "prediction": "home_win",
      "expected_value": 0.12,
      "created_at": "2025-10-29T10:30:00Z"
    }
  ]
}
```

#### 创建预测
```http
POST /api/v1/predictions
Content-Type: application/json
Authorization: Bearer {token}

{
  "match_id": 1,
  "strategy": "ml_ensemble",
  "custom_params": {
    "min_confidence": 0.7
  }
}
```

**响应**:
```json
{
  "id": 124,
  "match_id": 1,
  "strategy": "ml_ensemble",
  "home_win_prob": 0.65,
  "draw_prob": 0.25,
  "away_win_prob": 0.10,
  "confidence": 0.75,
  "prediction": "home_win",
  "expected_value": 0.12,
  "task_id": "pred_1_20251029_103000_12345",
  "status": "processing",
  "created_at": "2025-10-29T10:30:00Z"
}
```

#### 获取预测状态
```http
GET /api/v1/predictions/{prediction_id}/status
```

**响应**:
```json
{
  "prediction_id": 124,
  "task_id": "pred_1_20251029_103000_12345",
  "status": "completed",
  "progress": 100,
  "result": {
    "home_win_prob": 0.65,
    "draw_prob": 0.25,
    "away_win_prob": 0.10,
    "confidence": 0.75,
    "prediction": "home_win",
    "expected_value": 0.12
  },
  "created_at": "2025-10-29T10:30:00Z",
  "completed_at": "2025-10-29T10:30:15Z"
}
```

### 分析统计

#### 获取系统统计
```http
GET /api/v1/analytics/stats
```

**响应**:
```json
{
  "total_matches": 1250,
  "total_predictions": 3456,
  "accuracy_rate": 0.73,
  "avg_confidence": 0.76,
  "top_strategies": [
    {
      "strategy": "ml_ensemble",
      "predictions": 1234,
      "accuracy": 0.75
    }
  ],
  "league_performance": [
    {
      "league": "英超",
      "matches": 156,
      "accuracy": 0.78
    }
  ]
}
```

#### 获取预测历史趋势
```http
GET /api/v1/analytics/trends
```

**查询参数**:
- `period`: 时间周期 (7d|30d|90d)
- `metric`: 指标类型 (accuracy|confidence|volume)

**响应**:
```json
{
  "period": "30d",
  "metric": "accuracy",
  "data": [
    {
      "date": "2025-10-01",
      "value": 0.72
    },
    {
      "date": "2025-10-02",
      "value": 0.74
    }
  ]
}
```

### 用户管理

#### 获取用户信息
```http
GET /api/v1/users/me
Authorization: Bearer {token}
```

**响应**:
```json
{
  "id": "user123",
  "username": "john_doe",
  "email": "john@example.com",
  "subscription_tier": "premium",
  "preferences": {
    "preferred_leagues": ["英超", "西甲"],
    "min_confidence": 0.7,
    "notifications_enabled": true
  },
  "statistics": {
    "total_predictions": 156,
    "accuracy_rate": 0.71,
    "roi": 0.15
  }
}
```

#### 更新用户偏好
```http
PUT /api/v1/users/me/preferences
Content-Type: application/json
Authorization: Bearer {token}

{
  "preferred_leagues": ["英超", "西甲", "德甲"],
  "min_confidence": 0.75,
  "notifications_enabled": true
}
```

## 📡 WebSocket API

### 连接端点

#### 主WebSocket端点
```
ws://localhost:8000/realtime/ws?user_id={user_id}&token={token}
```

#### 专用预测端点
```
ws://localhost:8000/realtime/ws/predictions?match_ids={ids}&min_confidence={value}
```

#### 专用比赛端点
```
ws://localhost:8000/realtime/ws/matches?match_ids={ids}&leagues={names}
```

### 消息格式

#### 客户端发送消息
```json
{
  "type": "subscribe|unsubscribe|heartbeat|get_stats",
  "data": {
    "subscription_type": "predictions|matches|odds|system_alerts",
    "filters": {
      "match_ids": [1, 2, 3],
      "leagues": ["英超", "西甲"],
      "min_confidence": 0.7,
      "event_types": ["prediction_created", "match_started"]
    }
  },
  "request_id": "req_123456"
}
```

#### 服务器推送消息
```json
{
  "event_type": "prediction_created|match_started|odds_updated|system_alert",
  "data": {
    // 事件数据
  },
  "timestamp": "2025-10-29T10:30:00Z",
  "source": "prediction_service",
  "correlation_id": "corr_123456"
}
```

### 事件类型详解

#### 预测事件
```json
{
  "event_type": "prediction_created",
  "data": {
    "prediction_id": 124,
    "match_id": 1,
    "home_team": "曼联",
    "away_team": "切尔西",
    "prediction": "home_win",
    "confidence": 0.75,
    "expected_value": 0.12,
    "strategy": "ml_ensemble"
  },
  "timestamp": "2025-10-29T10:30:00Z"
}
```

#### 比赛事件
```json
{
  "event_type": "match_score_changed",
  "data": {
    "match_id": 1,
    "home_score": 1,
    "away_score": 0,
    "scoring_team": "home",
    "minute": 25,
    "scorer": "布鲁诺·费尔南德斯"
  },
  "timestamp": "2025-10-29T20:25:00Z"
}
```

#### 系统事件
```json
{
  "event_type": "system_alert",
  "data": {
    "alert_type": "warning",
    "message": "预测服务响应延迟",
    "component": "prediction_service",
    "severity": "medium",
    "details": {
      "response_time": 2500,
      "threshold": 2000
    }
  },
  "timestamp": "2025-10-29T10:30:00Z"
}
```

## ⚠️ 错误处理

### HTTP状态码

| 状态码 | 描述 | 示例场景 |
|--------|------|----------|
| 200 | 成功 | 请求成功处理 |
| 201 | 已创建 | 资源创建成功 |
| 400 | 请求错误 | 参数验证失败 |
| 401 | 未授权 | 认证失败 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 429 | 请求过多 | 速率限制 |
| 500 | 服务器错误 | 内部服务器错误 |

### 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "field": "match_id",
      "message": "match_id必须是正整数"
    },
    "request_id": "req_123456",
    "timestamp": "2025-10-29T10:30:00Z"
  }
}
```

### 常见错误码

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| `INVALID_TOKEN` | 无效的访问令牌 | 重新获取令牌 |
| `TOKEN_EXPIRED` | 令牌已过期 | 使用刷新令牌 |
| `INSUFFICIENT_PERMISSIONS` | 权限不足 | 升级订阅等级 |
| `RESOURCE_NOT_FOUND` | 资源不存在 | 检查资源ID |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限 | 降低请求频率 |
| `SERVICE_UNAVAILABLE` | 服务不可用 | 稍后重试 |

## 📊 分页和过滤

### 分页参数

所有列表API都支持分页：

- `limit`: 每页返回数量 (1-100，默认50)
- `offset`: 偏移量 (默认0)

**示例**:
```http
GET /api/v1/predictions?limit=20&offset=40
```

### 排序参数

- `sort`: 排序字段
- `order`: 排序方向 (asc|desc，默认desc)

**示例**:
```http
GET /api/v1/predictions?sort=created_at&order=desc
```

### 过滤参数

不同的API支持不同的过滤参数，详见各API文档。

**通用过滤**:
- 日期范围: `date_from`, `date_to`
- 状态筛选: `status`
- 类别筛选: `type`, `category`

## 🔄 批量操作

### 批量预测
```http
POST /api/v1/predictions/batch
Content-Type: application/json
Authorization: Bearer {token}

{
  "match_ids": [1, 2, 3, 4, 5],
  "strategy": "ml_ensemble",
  "priority": "high"
}
```

**响应**:
```json
{
  "batch_id": "batch_123456",
  "total_tasks": 5,
  "tasks": [
    {
      "match_id": 1,
      "task_id": "pred_1_20251029_103000_12345",
      "status": "queued"
    }
  ]
}
```

### 批量状态查询
```http
GET /api/v1/predictions/batch/{batch_id}/status
```

## 📈 速率限制

### 限制规则

| 用户等级 | 每分钟请求数 | 每日请求数 |
|----------|-------------|-----------|
| guest | 60 | 1,000 |
| user | 120 | 5,000 |
| premium | 300 | 20,000 |
| admin | 无限制 | 无限制 |

### 限制响应

当超过速率限制时，返回429状态码：

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "请求频率超过限制",
    "details": {
      "limit": 120,
      "window": "60s",
      "retry_after": 30
    }
  }
}
```

### 请求头

响应中包含限制信息头：

```
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 119
X-RateLimit-Reset: 1635511200
```

## 🧪 API测试

### 使用curl测试

```bash
# 获取访问令牌
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password123"}'

# 获取比赛列表
curl -X GET http://localhost:8000/api/v1/matches \
  -H "Authorization: Bearer {token}"

# 创建预测
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"match_id": 1, "strategy": "ml_ensemble"}'
```

### 使用Postman测试

导入以下环境变量：

```
base_url = http://localhost:8000
token = eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### WebSocket测试

```javascript
const ws = new WebSocket('ws://localhost:8000/realtime/ws?user_id=test123');

ws.onopen = function() {
  // 订阅预测事件
  ws.send(JSON.stringify({
    type: 'subscribe',
    data: {
      subscription_type: 'predictions',
      filters: { min_confidence: 0.7 }
    }
  }));
};

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('收到事件:', data);
};
```

## 🔧 SDK和客户端库

### Python SDK

```python
from football_prediction_sdk import FootballPredictionAPI

# 初始化客户端
client = FootballPredictionAPI(
    base_url="http://localhost:8000",
    token="your_token_here"
)

# 获取比赛列表
matches = client.matches.list(league="英超", limit=10)

# 创建预测
prediction = client.predictions.create(
    match_id=1,
    strategy="ml_ensemble"
)

# WebSocket客户端
ws_client = client.websocket
ws_client.subscribe("predictions", min_confidence=0.7)
ws_client.on_prediction_created(lambda event: print(event))
```

### JavaScript/TypeScript SDK

```typescript
import { FootballPredictionAPI } from 'football-prediction-sdk';

// 初始化客户端
const client = new FootballPredictionAPI({
  baseURL: 'http://localhost:8000',
  token: 'your_token_here'
});

// 获取比赛列表
const matches = await client.matches.list({
  league: '英超',
  limit: 10
});

// 创建预测
const prediction = await client.predictions.create({
  matchId: 1,
  strategy: 'ml_ensemble'
});

// WebSocket客户端
const wsClient = client.websocket;
wsClient.subscribe('predictions', { minConfidence: 0.7 });
wsClient.on('predictionCreated', (event) => console.log(event));
```

## 📚 示例代码

### 完整的预测流程

```python
import asyncio
import aiohttp
import json

async def prediction_workflow():
    """完整的预测工作流程示例"""

    # 1. 登录获取令牌
    async with aiohttp.ClientSession() as session:
        login_response = await session.post(
            'http://localhost:8000/auth/login',
            json={
                'username': 'user@example.com',
                'password': 'password123'
            }
        )
        token_data = await login_response.json()
        token = token_data['access_token']

        headers = {'Authorization': f'Bearer {token}'}

        # 2. 获取即将开始的比赛
        matches_response = await session.get(
            'http://localhost:8000/api/v1/matches',
            params={'status': 'upcoming', 'limit': 5},
            headers=headers
        )
        matches = await matches_response.json()

        # 3. 为每场比赛创建预测
        for match in matches['results']:
            prediction_response = await session.post(
                'http://localhost:8000/api/v1/predictions',
                json={
                    'match_id': match['id'],
                    'strategy': 'ml_ensemble'
                },
                headers=headers
            )
            prediction = await prediction_response.json()

            print(f"已为比赛 {match['home_team']} VS {match['away_team']} 创建预测")
            print(f"预测ID: {prediction['id']}, 状态: {prediction['status']}")

# 运行示例
asyncio.run(prediction_workflow())
```

### WebSocket实时监听

```javascript
class PredictionMonitor {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.handlers = {};
  }

  connect() {
    const wsUrl = `ws://localhost:8000/realtime/ws?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket连接已建立');
      this.subscribe();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleEvent(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      // 自动重连
      setTimeout(() => this.connect(), 5000);
    };
  }

  subscribe() {
    const message = {
      type: 'subscribe',
      data: {
        subscription_type: 'predictions',
        filters: {
          min_confidence: 0.7
        }
      }
    };
    this.ws.send(JSON.stringify(message));
  }

  handleEvent(event) {
    const handler = this.handlers[event.event_type];
    if (handler) {
      handler(event.data);
    }
  }

  on(eventType, handler) {
    this.handlers[eventType] = handler;
  }
}

// 使用示例
const monitor = new PredictionMonitor('your_token_here');
monitor.connect();

monitor.on('prediction_created', (data) => {
  console.log(`新预测: ${data.home_team} VS ${data.away_team}`);
  console.log(`预测结果: ${data.prediction}, 置信度: ${data.confidence}`);
});

monitor.on('match_score_changed', (data) => {
  console.log(`比分更新: ${data.home_team} ${data.home_score} - ${data.away_score} ${data.away_team}`);
});
```

---

## 📞 技术支持

如有API相关问题，请联系开发团队或查看以下资源：

- **系统架构文档**: [SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md)
- **WebSocket文档**: [WEBSOCKET_REALTIME_COMMUNICATION.md](../architecture/WEBSOCKET_REALTIME_COMMUNICATION.md)
- **部署指南**: [DEPLOYMENT_GUIDE.md](../ops/DEPLOYMENT_GUIDE.md)
- **故障排除**: [TROUBLESHOOTING.md](../project/TROUBLESHOOTING.md)

**文档版本**: v1.0
**最后更新**: 2025-10-29
**维护团队**: Football Prediction Development Team