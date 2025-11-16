# 足球预测系统 API 文档
# Football Prediction System API Documentation

## 目录
- [概述](#概述)
- [认证](#认证)
- [基础信息](#基础信息)
- [核心API](#核心api)
- [多租户API](#多租户api)
- [性能管理API](#性能管理api)
- [错误处理](#错误处理)
- [限流](#限流)
- [示例代码](#示例代码)

## 概述

足球预测系统提供完整的RESTful API，支持足球比赛预测、用户管理、多租户管理等功能。

### 基础URL
- 开发环境: `http://localhost:8000`
- 生产环境: `https://api.football-prediction.com`

### API版本
- 当前版本: `v1`
- 版本策略: URL路径版本控制 `/api/v1/`

## 认证

系统支持JWT令牌认证，所有需要认证的API都需要在请求头中包含有效的JWT令牌。

### 获取访问令牌

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**响应示例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "user@example.com"
  }
}
```

### 使用访问令牌

在API请求中添加Authorization头：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 刷新令牌

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## 基础信息

### 通用响应格式

所有API响应都遵循统一的格式：

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2025-10-30T15:30:00Z",
  "request_id": "req_123456789"
}
```

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "field": "username",
      "reason": "用户名不能为空"
    }
  },
  "timestamp": "2025-10-30T15:30:00Z",
  "request_id": "req_123456789"
}
```

### HTTP状态码

- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证或认证失败
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `429 Too Many Requests` - 请求频率超限
- `500 Internal Server Error` - 服务器内部错误

## 核心API

### 预测管理

#### 创建预测

```http
POST /api/v1/predictions
Authorization: Bearer {token}
Content-Type: application/json

{
  "match_id": 123,
  "prediction_type": "match_result",
  "predicted_result": "home_win",
  "confidence": 0.85,
  "reasoning": "主队近期状态良好，历史交锋占优"
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": 456,
    "match_id": 123,
    "prediction_type": "match_result",
    "predicted_result": "home_win",
    "confidence": 0.85,
    "reasoning": "主队近期状态良好，历史交锋占优",
    "status": "pending",
    "created_at": "2025-10-30T15:30:00Z",
    "updated_at": "2025-10-30T15:30:00Z"
  }
}
```

#### 获取预测列表

```http
GET /api/v1/predictions?match_id=123&status=completed&limit=20&offset=0
Authorization: Bearer {token}
```

**查询参数:**
- `match_id` (可选) - 比赛ID
- `status` (可选) - 预测状态 (`pending`, `completed`, `failed`)
- `limit` (可选) - 返回数量限制，默认20
- `offset` (可选) - 偏移量，默认0

#### 获取预测详情

```http
GET /api/v1/predictions/{prediction_id}
Authorization: Bearer {token}
```

#### 更新预测

```http
PUT /api/v1/predictions/{prediction_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "confidence": 0.90,
  "reasoning": "更新后的分析原因"
}
```

#### 删除预测

```http
DELETE /api/v1/predictions/{prediction_id}
Authorization: Bearer {token}
```

### 比赛管理

#### 获取比赛列表

```http
GET /api/v1/matches?league_id=1&status=scheduled&date_from=2025-10-30&date_to=2025-11-30
Authorization: Bearer {token}
```

**查询参数:**
- `league_id` (可选) - 联赛ID
- `status` (可选) - 比赛状态 (`scheduled`, `live`, `completed`, `cancelled`)
- `date_from` (可选) - 开始日期
- `date_to` (可选) - 结束日期
- `team_id` (可选) - 球队ID

#### 获取比赛详情

```http
GET /api/v1/matches/{match_id}
Authorization: Bearer {token}
```

### 用户管理

#### 获取用户信息

```http
GET /api/v1/users/profile
Authorization: Bearer {token}
```

#### 更新用户信息

```http
PUT /api/v1/users/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "first_name": "张",
  "last_name": "三",
  "bio": "足球预测爱好者",
  "preferences": {
    "favorite_teams": [1, 2, 3],
    "notification_enabled": true
  }
}
```

#### 修改密码

```http
POST /api/v1/users/change-password
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

## 多租户API

### 租户管理

#### 创建租户

```http
POST /api/v1/tenants
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "测试租户",
  "slug": "test-tenant",
  "contact_email": "admin@test.com",
  "company_name": "测试公司",
  "plan": "professional",
  "max_users": 50
}
```

#### 获取租户详情

```http
GET /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
```

#### 更新租户信息

```http
PUT /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "更新后的租户名称",
  "description": "更新后的描述",
  "contact_email": "new-email@test.com"
}
```

#### 激活/暂停租户

```http
POST /api/v1/tenants/{tenant_id}/activate
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan": "enterprise"
}
```

```http
POST /api/v1/tenants/{tenant_id}/suspend
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "违规操作"
}
```

### 角色和权限管理

#### 分配用户角色

```http
POST /api/v1/tenants/{tenant_id}/users/{user_id}/roles
Authorization: Bearer {token}
Content-Type: application/json

{
  "role_code": "analyst",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

#### 撤销用户角色

```http
DELETE /api/v1/tenants/{tenant_id}/users/{user_id}/roles/{role_code}
Authorization: Bearer {token}
```

#### 检查用户权限

```http
POST /api/v1/tenants/{tenant_id}/permissions/check
Authorization: Bearer {token}
Content-Type: application/json

{
  "permission_code": "predictions.create",
  "resource_context": {
    "match_id": 123
  }
}
```

### 资源配额管理

#### 检查资源配额

```http
GET /api/v1/tenants/{tenant_id}/quota/{resource_type}?amount=1
Authorization: Bearer {token}
```

**资源类型:**
- `users` - 用户数配额
- `predictions_daily` - 每日预测配额
- `api_calls_hourly` - 每小时API调用配额
- `storage` - 存储配额

#### 更新使用指标

```http
POST /api/v1/tenants/{tenant_id}/usage/update
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_users": 25,
  "daily_predictions": 150,
  "hourly_api_calls": 800,
  "storage_used_mb": 450
}
```

## 性能管理API

### 系统监控

#### 获取性能指标

```http
GET /api/v1/performance/metrics?time_range_minutes=60&endpoint_filter=/predictions
Authorization: Bearer {token}
```

#### 获取性能仪表板

```http
GET /api/v1/performance/dashboard
Authorization: Bearer {token}
```

#### 获取性能告警

```http
GET /api/v1/performance/alerts?severity=critical&status=active
Authorization: Bearer {token}
```

### 数据库优化

#### 启动数据库优化

```http
POST /api/v1/performance/database/optimize
Authorization: Bearer {token}
Content-Type: application/json

{
  "optimize_indexes": true,
  "cleanup_data": true,
  "analyze_tables": true,
  "refresh_views": true
}
```

#### 获取数据库分析

```http
GET /api/v1/performance/database/analysis
Authorization: Bearer {token}
```

### 缓存管理

#### 管理缓存

```http
POST /api/v1/performance/cache/manage
Authorization: Bearer {token}
Content-Type: application/json

{
  "operation": "clear",
  "pattern": "api_cache:*"
}
```

#### 获取缓存统计

```http
GET /api/v1/performance/cache/statistics
Authorization: Bearer {token}
```

## 错误处理

### 常见错误码

| 错误码 | HTTP状态码 | 描述 |
|--------|------------|------|
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| `AUTHENTICATION_FAILED` | 401 | 认证失败 |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `RESOURCE_CONFLICT` | 409 | 资源冲突 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `QUOTA_EXCEEDED` | 429 | 配额超限 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

### 错误响应示例

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "field_errors": [
        {
          "field": "email",
          "message": "邮箱格式不正确"
        },
        {
          "field": "password",
          "message": "密码长度至少8位"
        }
      ]
    }
  },
  "timestamp": "2025-10-30T15:30:00Z",
  "request_id": "req_123456789"
}
```

## 限流

### 限流策略

系统实现了多层次的限流策略：

1. **全局限流**: 每个IP每分钟最多1000个请求
2. **用户限流**: 每个用户每分钟最多500个请求
3. **端点限流**: 特定端点有独立的限流规则
4. **租户限流**: 基于租户配额的限流

### 限流响应

当触发限流时，API返回以下响应：

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "请求频率超限",
    "details": {
      "limit": 1000,
      "remaining": 0,
      "reset_time": "2025-10-30T15:31:00Z",
      "retry_after": 60
    }
  }
}
```

### 响应头

限流相关的响应头：

- `X-RateLimit-Limit`: 限流上限
- `X-RateLimit-Remaining`: 剩余请求数
- `X-RateLimit-Reset`: 重置时间
- `Retry-After`: 建议重试间隔（秒）

## 示例代码

### Python示例

```python
import requests
import json

class FootballPredictionAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = self._login(username, password)

    def _login(self, username, password):
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.session.headers.update({
            "Authorization": f"Bearer {data['access_token']}"
        })
        return data['access_token']

    def create_prediction(self, match_id, predicted_result, confidence, reasoning=""):
        """创建预测"""
        data = {
            "match_id": match_id,
            "prediction_type": "match_result",
            "predicted_result": predicted_result,
            "confidence": confidence,
            "reasoning": reasoning
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/predictions",
            json=data
        )
        response.raise_for_status()
        return response.json()

    def get_predictions(self, match_id=None, status=None, limit=20):
        """获取预测列表"""
        params = {"limit": limit}
        if match_id:
            params["match_id"] = match_id
        if status:
            params["status"] = status

        response = self.session.get(
            f"{self.base_url}/api/v1/predictions",
            params=params
        )
        response.raise_for_status()
        return response.json()

# 使用示例
api = FootballPredictionAPI(
    base_url="http://localhost:8000",
    username="your_username",
    password="your_password"
)

# 创建预测
prediction = api.create_prediction(
    match_id=123,
    predicted_result="home_win",
    confidence=0.85,
    reasoning="主队近期状态良好"
)
print(f"预测ID: {prediction['data']['id']}")

# 获取预测列表
predictions = api.get_predictions(match_id=123)
print(f"找到 {len(predictions['data'])} 个预测")
```

### JavaScript示例

```javascript
class FootballPredictionAPI {
    constructor(baseUrl, username, password) {
        this.baseUrl = baseUrl;
        this.token = null;
    }

    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error(`登录失败: ${response.statusText}`);
        }

        const data = await response.json();
        this.token = data.access_token;
        return data;
    }

    async _makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(url, {
            ...options,
            headers
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || response.statusText);
        }

        return response.json();
    }

    async createPrediction(matchId, predictedResult, confidence, reasoning = '') {
        return this._makeRequest('/api/v1/predictions', {
            method: 'POST',
            body: JSON.stringify({
                match_id: matchId,
                prediction_type: 'match_result',
                predicted_result: predictedResult,
                confidence: confidence,
                reasoning: reasoning
            })
        });
    }

    async getPredictions(filters = {}) {
        const params = new URLSearchParams(filters);
        return this._makeRequest(`/api/v1/predictions?${params}`);
    }
}

// 使用示例
const api = new FootballPredictionAPI('http://localhost:8000');

async function example() {
    try {
        // 登录
        await api.login('your_username', 'your_password');

        // 创建预测
        const prediction = await api.createPrediction(
            123,
            'home_win',
            0.85,
            '主队近期状态良好'
        );
        console.log('预测创建成功:', prediction);

        // 获取预测列表
        const predictions = await api.getPredictions({ match_id: 123 });
        console.log('预测列表:', predictions);

    } catch (error) {
        console.error('API调用失败:', error);
    }
}

example();
```

## 更新日志

### v1.0.0 (2025-10-30)
- 初始版本发布
- 基础预测功能
- 用户认证和授权
- 多租户支持
- 性能监控API
- 完整的错误处理和限流

---

*文档最后更新: 2025-10-30*
*版本: v1.0.0*
