# API 文档
# API Documentation

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API版本**: v1
- **内容类型**: `application/json`

## 认证

API使用JWT Bearer Token认证：

```bash
Authorization: Bearer <your-token>
```

## API端点

### 1. 健康检查

#### GET `/api/health`

检查API健康状态。

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-10-14T10:00:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "cache": "healthy"
  }
}
```

### 2. 预测模块

#### 获取比赛预测

**GET** `/api/predictions/matches/{match_id}`

获取特定比赛的预测信息。

**路径参数**:
- `match_id` (int): 比赛ID

**响应示例**:
```json
{
  "match_id": 12345,
  "prediction": {
    "home_win": 0.45,
    "draw": 0.30,
    "away_win": 0.25,
    "confidence": 0.85
  },
  "created_at": "2024-10-14T10:00:00Z",
  "model_version": "v2.1"
}
```

#### 创建预测

**POST** `/api/predictions/matches/{match_id}/predict`

为特定比赛生成新预测。

**路径参数**:
- `match_id` (int): 比赛ID

**请求体**:
```json
{
  "model": "neural_network",
  "features": {
    "home_team_form": "WWWDW",
    "away_team_form": "DWLWD",
    "head_to_head": {
      "wins": 3,
      "draws": 2,
      "losses": 5
    }
  }
}
```

**响应示例**:
```json
{
  "prediction_id": "pred_123456",
  "match_id": 12345,
  "prediction": {
    "home_win": 0.48,
    "draw": 0.28,
    "away_win": 0.24
  },
  "model_used": "neural_network",
  "processing_time_ms": 150,
  "created_at": "2024-10-14T10:00:00Z"
}
```

#### 批量预测

**POST** `/api/predictions/batch`

批量生成多个比赛的预测。

**请求体**:
```json
{
  "predictions": [
    {
      "match_id": 12345,
      "model": "neural_network"
    },
    {
      "match_id": 12346,
      "model": "statistical"
    }
  ]
}
```

**响应示例**:
```json
{
  "batch_id": "batch_789",
  "predictions": [
    {
      "match_id": 12345,
      "prediction": {...},
      "status": "success"
    },
    {
      "match_id": 12346,
      "prediction": {...},
      "status": "success"
    }
  ],
  "total_processed": 2,
  "total_success": 2,
  "created_at": "2024-10-14T10:00:00Z"
}
```

### 3. 数据模块

#### 获取比赛列表

**GET** `/api/data/matches`

获取比赛列表，支持分页和过滤。

**查询参数**:
- `page` (int, optional): 页码，默认1
- `limit` (int, optional): 每页数量，默认20
- `league_id` (int, optional): 联赛ID过滤
- `date_from` (string, optional): 开始日期 (YYYY-MM-DD)
- `date_to` (string, optional): 结束日期 (YYYY-MM-DD)

**响应示例**:
```json
{
  "matches": [
    {
      "id": 12345,
      "home_team": {
        "id": 100,
        "name": "Team A",
        "logo": "https://example.com/logo.png"
      },
      "away_team": {
        "id": 101,
        "name": "Team B",
        "logo": "https://example.com/logo.png"
      },
      "league": {
        "id": 1,
        "name": "Premier League",
        "country": "England"
      },
      "date": "2024-10-14T20:00:00Z",
      "status": "completed",
      "score": {
        "home": 2,
        "away": 1
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 500,
    "pages": 25
  }
}
```

#### 获取球队信息

**GET** `/api/data/teams/{team_id}`

获取特定球队的详细信息。

**路径参数**:
- `team_id` (int): 球队ID

**响应示例**:
```json
{
  "id": 100,
  "name": "Team A",
  "short_name": "TA",
  "logo": "https://example.com/logo.png",
  "founded": 1890,
  "stadium": "Stadium Name",
  "capacity": 50000,
  "city": "City",
  "country": "Country",
  "league": "Premier League",
  "current_season": {
    "played": 10,
    "won": 6,
    "drawn": 2,
    "lost": 2,
    "points": 20,
    "position": 3
  }
}
```

### 4. 赛事模块

#### 获取联赛积分榜

**GET** `/api/competitions/{league_id}/standings`

获取联赛积分榜。

**路径参数**:
- `league_id` (int): 联赛ID

**查询参数**:
- `season` (string): 赛季，格式 "2024-2025"

**响应示例**:
```json
{
  "league": {
    "id": 1,
    "name": "Premier League",
    "season": "2024-2025"
  },
  "standings": [
    {
      "position": 1,
      "team": {
        "id": 100,
        "name": "Team A"
      },
      "played": 10,
      "won": 8,
      "drawn": 1,
      "lost": 1,
      "goals_for": 20,
      "goals_against": 8,
      "goal_difference": 12,
      "points": 25
    }
  ]
}
```

### 5. 用户模块

#### 用户注册

**POST** `/api/auth/register`

注册新用户。

**请求体**:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**响应示例**:
```json
{
  "user_id": "user_123456",
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "created_at": "2024-10-14T10:00:00Z"
}
```

#### 用户登录

**POST** `/api/auth/login`

用户登录获取访问令牌。

**请求体**:
```json
{
  "username": "john_doe",
  "password": "securepassword123"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_123456",
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

### 6. 统计模块

#### 获取预测统计

**GET** `/api/statistics/predictions`

获取预测性能统计。

**查询参数**:
- `date_from` (string, optional): 开始日期
- `date_to` (string, optional): 结束日期
- `model` (string, optional): 模型过滤

**响应示例**:
```json
{
  "period": {
    "from": "2024-10-01",
    "to": "2024-10-14"
  },
  "total_predictions": 1500,
  "accuracy": {
    "overall": 0.65,
    "home_win": 0.70,
    "draw": 0.60,
    "away_win": 0.55
  },
  "by_model": {
    "neural_network": {
      "predictions": 800,
      "accuracy": 0.68
    },
    "statistical": {
      "predictions": 700,
      "accuracy": 0.62
    }
  },
  "daily_accuracy": [
    {
      "date": "2024-10-14",
      "predictions": 100,
      "accuracy": 0.72
    }
  ]
}
```

## 错误响应

API使用标准HTTP状态码和错误格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  },
  "timestamp": "2024-10-14T10:00:00Z",
  "path": "/api/predictions/matches/12345/predict"
}
```

### 常见错误代码

- `400 Bad Request`: 请求格式错误
- `401 Unauthorized`: 需要认证
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 数据验证失败
- `429 Too Many Requests`: 请求过于频繁
- `500 Internal Server Error`: 服务器内部错误

## 限流规则

- 未认证用户：100请求/分钟
- 认证用户：1000请求/分钟
- 批量操作：10请求/分钟

## SDK和客户端库

### Python SDK示例

```python
from football_prediction_client import FootballPredictionClient

# 初始化客户端
client = FootballPredictionClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# 获取预测
prediction = client.predictions.get_match_prediction(12345)
print(prediction)

# 创建预测
new_prediction = client.predictions.create_prediction(
    match_id=12346,
    model="neural_network",
    features={...}
)
```

## WebSocket API

### 实时预测更新

**连接**: `ws://localhost:8000/ws/predictions`

**消息格式**:
```json
{
  "type": "prediction_update",
  "data": {
    "match_id": 12345,
    "prediction": {...},
    "timestamp": "2024-10-14T10:00:00Z"
  }
}
```

## 版本更新

API版本通过URL路径管理：
- v1: `/api/v1/...` (当前版本)
- v2: `/api/v2/...` (未来版本)

## 支持

如需技术支持，请联系：
- 邮箱：support@footballprediction.com
- 文档：https://docs.footballprediction.com
- GitHub：https://github.com/yourorg/football-prediction