# 预测API文档

## 📋 概述

预测API提供了完整的足球比赛预测功能，包括预测创建、查询、统计等功能。

## 🔐 认证

所有预测API都需要JWT Bearer Token认证：

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/predictions
```

## 📊 核心端点

### 1. 创建预测

**POST** `/api/predictions`

创建新的比赛预测。

#### 请求体
```json
{
  "match_id": 123,
  "home_score_prediction": 2,
  "away_score_prediction": 1,
  "confidence_score": 0.85,
  "prediction_type": "EXACT_SCORE",
  "strategy_used": "ml_model_v2",
  "input_features": {
    "team_form": [3, 1, 2, 1],
    "head_to_head": [1, 0, 2],
    "injuries": ["none", "midfielder"]
  }
}
```

#### 响应
```json
{
  "success": true,
  "data": {
    "id": 456,
    "match_id": 123,
    "user_id": 789,
    "home_score_prediction": 2,
    "away_score_prediction": 1,
    "confidence_score": 0.85,
    "prediction_type": "EXACT_SCORE",
    "status": "PENDING",
    "created_at": "2024-01-01T10:00:00Z"
  },
  "message": "预测创建成功"
}
```

#### 错误响应
- `400 Bad Request`: 请求参数无效
- `401 Unauthorized`: 认证失败
- `409 Conflict`: 重复预测（同一用户同一比赛）

### 2. 获取预测列表

**GET** `/api/predictions`

获取用户的预测列表，支持分页和过滤。

#### 查询参数
- `limit`: 每页数量 (默认: 20, 最大: 100)
- `offset`: 偏移量 (默认: 0)
- `status`: 预测状态过滤 (PENDING, COMPLETED, CANCELLED)
- `match_id`: 特定比赛的预测
- `start_date`: 开始日期过滤
- `end_date`: 结束日期过滤

#### 示例请求
```bash
curl "http://localhost:8000/api/predictions?limit=10&status=COMPLETED"
```

#### 响应
```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "id": 456,
        "match_id": 123,
        "home_score_prediction": 2,
        "away_score_prediction": 1,
        "confidence_score": 0.85,
        "status": "COMPLETED",
        "result_status": "CORRECT",
        "points_earned": 10,
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "total": 45,
    "limit": 10,
    "offset": 0,
    "has_next": true
  },
  "message": "获取预测列表成功"
}
```

### 3. 获取预测详情

**GET** `/api/predictions/{prediction_id}`

获取特定预测的详细信息。

#### 路径参数
- `prediction_id`: 预测ID

#### 响应
```json
{
  "success": true,
  "data": {
    "id": 456,
    "match_id": 123,
    "user_id": 789,
    "home_score_prediction": 2,
    "away_score_prediction": 1,
    "confidence_score": 0.85,
    "prediction_type": "EXACT_SCORE",
    "strategy_used": "ml_model_v2",
    "input_features": {
      "team_form": [3, 1, 2, 1],
      "head_to_head": [1, 0, 2]
    },
    "calculation_details": {
      "model_confidence": 0.82,
      "historical_accuracy": 0.78,
      "risk_factor": "low"
    },
    "status": "COMPLETED",
    "result_status": "CORRECT",
    "accuracy_score": 1.0,
    "points_earned": 10,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-02T20:00:00Z"
  },
  "message": "获取预测详情成功"
}
```

### 4. 更新预测

**PUT** `/api/predictions/{prediction_id}`

更新现有的预测（仅在比赛开始前允许）。

#### 请求体
```json
{
  "home_score_prediction": 3,
  "away_score_prediction": 1,
  "confidence_score": 0.90
}
```

### 5. 删除预测

**DELETE** `/api/predictions/{prediction_id}`

删除预测（仅在比赛开始前允许）。

#### 响应
```json
{
  "success": true,
  "data": null,
  "message": "预测删除成功"
}
```

## 📈 统计端点

### 获取用户预测统计

**GET** `/api/predictions/statistics/user`

获取用户的预测统计信息。

#### 响应
```json
{
  "success": true,
  "data": {
    "total_predictions": 50,
    "correct_predictions": 32,
    "accuracy_rate": 0.64,
    "total_points": 280,
    "current_streak": 5,
    "best_streak": 12,
    "average_confidence": 0.78,
    "prediction_types": {
      "EXACT_SCORE": 30,
      "WINNER": 15,
      "OVER_UNDER": 5
    },
    "monthly_stats": [
      {
        "month": "2024-01",
        "predictions": 15,
        "correct": 10,
        "points": 85
      }
    ]
  },
  "message": "获取统计成功"
}
```

### 获取比赛预测统计

**GET** `/api/predictions/statistics/match/{match_id}`

获取特定比赛的所有预测统计。

#### 响应
```json
{
  "success": true,
  "data": {
    "match_id": 123,
    "total_predictions": 150,
    "popular_prediction": {
      "home_score": 2,
      "away_score": 1,
      "percentage": 0.45
    },
    "confidence_distribution": {
      "high": 0.3,
      "medium": 0.5,
      "low": 0.2
    },
    "prediction_types": {
      "EXACT_SCORE": 120,
      "WINNER": 25,
      "OVER_UNDER": 5
    }
  },
  "message": "获取比赛统计成功"
}
```

## 🚨 错误代码

| 代码 | 描述 | 解决方案 |
|------|------|----------|
| `PREDICTION_NOT_FOUND` | 预测不存在 | 检查预测ID是否正确 |
| `MATCH_STARTED` | 比赛已开始，无法修改 | 比赛开始后不能更新预测 |
| `DUPLICATE_PREDICTION` | 重复预测 | 用户已对该比赛创建预测 |
| `INVALID_SCORE` | 无效的比分 | 比分必须是非负整数 |
| `CONFIDENCE_OUT_OF_RANGE` | 置信度超出范围 | 置信度必须在0-1之间 |
| `STRATEGY_NOT_FOUND` | 预测策略不存在 | 使用有效的策略名称 |

## 📝 数据模型

### PredictionRequest
```python
class PredictionRequest(BaseModel):
    match_id: int
    home_score_prediction: int = Field(..., ge=0, description="主队预测得分")
    away_score_prediction: int = Field(..., ge=0, description="客队预测得分")
    confidence_score: float = Field(..., ge=0, le=1, description="预测置信度")
    prediction_type: str = Field(default="EXACT_SCORE", description="预测类型")
    strategy_used: Optional[str] = Field(None, description="使用的预测策略")
    input_features: Optional[Dict[str, Any]] = Field(None, description="输入特征")
```

### PredictionResponse
```python
class PredictionResponse(BaseModel):
    id: int
    match_id: int
    user_id: int
    home_score_prediction: int
    away_score_prediction: int
    confidence_score: float
    prediction_type: str
    status: str
    result_status: Optional[str]
    points_earned: int
    created_at: datetime
    updated_at: Optional[datetime]
```

## 🔧 SDK示例

### Python SDK
```python
from football_prediction_sdk import PredictionAPI

# 初始化客户端
client = PredictionAPI(
    base_url="http://localhost:8000",
    token="your_jwt_token"
)

# 创建预测
prediction = client.create_prediction(
    match_id=123,
    home_score=2,
    away_score=1,
    confidence=0.85
)

# 获取预测列表
predictions = client.get_predictions(
    limit=20,
    status="COMPLETED"
)

# 获取统计
stats = client.get_user_statistics()
```

### JavaScript SDK
```javascript
import { PredictionAPI } from 'football-prediction-sdk';

const client = new PredictionAPI({
  baseURL: 'http://localhost:8000',
  token: 'your_jwt_token'
});

// 创建预测
const prediction = await client.createPrediction({
  matchId: 123,
  homeScore: 2,
  awayScore: 1,
  confidence: 0.85
});

// 获取预测列表
const predictions = await client.getPredictions({
  limit: 20,
  status: 'COMPLETED'
});
```

---

*文档版本: v1.0.0 | 最后更新: 2024-01-01*
