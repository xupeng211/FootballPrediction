#!/usr/bin/env python3
"""
API文档详细化工具
为API端点添加详细的说明、模型和示例
"""

from pathlib import Path


def create_detailed_api_docs():
    """创建详细的API文档"""

    api_docs_dir = Path("docs/api")
    api_docs_dir.mkdir(parents=True, exist_ok=True)

    # 创建预测API详细文档
    predictions_doc = """# 预测API文档

## 📋 概述

预测API提供了完整的足球比赛预测功能，包括预测创建、查询、统计等功能。

## 🔐 认证

所有预测API都需要JWT Bearer Token认证：

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
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
"""

    # 写入预测API文档
    with open(api_docs_dir / "predictions.md", 'w', encoding='utf-8') as f:
        f.write(predictions_doc)

    # 创建健康检查API文档
    health_doc = """# 健康检查API文档

## 📋 概述

健康检查API提供了系统状态监控和诊断功能，用于监控系统运行状态。

## 🏥 核心端点

### 1. 基础健康检查

**GET** `/health`

基础的系统健康状态检查。

#### 响应
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00Z",
  "version": "1.0.0",
  "uptime": 86400
}
```

### 2. 详细系统信息

**GET** `/health/detailed`

详细的系统状态信息。

#### 响应
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00Z",
  "version": "1.0.0",
  "uptime": 86400,
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 15,
      "connections": {
        "active": 5,
        "idle": 10,
        "total": 15
      }
    },
    "redis": {
      "status": "healthy",
      "response_time": 2,
      "memory_usage": "45MB",
      "connected_clients": 3
    },
    "prediction_service": {
      "status": "healthy",
      "model_version": "v2.1.0",
      "cache_hit_rate": 0.85
    }
  },
  "metrics": {
    "requests_per_minute": 120,
    "error_rate": 0.02,
    "average_response_time": 150
  }
}
```

### 3. 组件健康检查

**GET** `/health/components/{component_name}`

检查特定组件的健康状态。

#### 路径参数
- `component_name`: 组件名称 (database, redis, prediction_service)

#### 响应
```json
{
  "component": "database",
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00Z",
  "details": {
    "connection_pool": {
      "active": 5,
      "idle": 10,
      "total": 15
    },
    "last_check": "2024-01-01T09:59:30Z",
    "response_time": 15
  },
  "checks": [
    {
      "name": "connection",
      "status": "pass",
      "response_time": 15
    },
    {
      "name": "query_performance",
      "status": "pass",
      "response_time": 25
    }
  ]
}
```

## 📊 监控指标

### 系统指标
- **响应时间**: 各组件的响应时间监控
- **错误率**: 系统错误率统计
- **资源使用**: CPU、内存、磁盘使用情况
- **连接状态**: 数据库和缓存连接状态

### 业务指标
- **预测准确率**: 实时预测准确率统计
- **用户活跃度**: 当前在线用户数
- **API调用量**: 每分钟API调用次数
- **预测处理量**: 每小时处理的预测数量

## 🚨 健康状态

### 状态定义
- **healthy**: 系统正常运行
- **degraded**: 系统部分功能受限
- **unhealthy**: 系统无法正常服务
- **unknown**: 无法确定系统状态

### 自动恢复
- 数据库连接断开自动重连
- Redis缓存故障自动降级
- 预测服务异常自动切换备用模型

---

*文档版本: v1.0.0 | 最后更新: 2024-01-01*
"""

    # 写入健康检查API文档
    with open(api_docs_dir / "health.md", 'w', encoding='utf-8') as f:
        f.write(health_doc)

    # 创建错误代码参考文档
    errors_doc = """# API错误代码参考

## 📋 概述

本文档包含了API的所有错误代码、详细描述和解决方案。

## 🔐 认证错误 (401)

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `TOKEN_MISSING` | 缺少认证令牌 | 在请求头中添加Authorization: Bearer token |
| `TOKEN_INVALID` | 认证令牌无效 | 获取新的JWT令牌 |
| `TOKEN_EXPIRED` | 认证令牌已过期 | 刷新令牌或重新登录 |
| `USER_NOT_FOUND` | 用户不存在 | 检查用户名或注册新账户 |

## 🚫 权限错误 (403)

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `INSUFFICIENT_PERMISSIONS` | 权限不足 | 联系管理员获取相应权限 |
| `RESOURCE_ACCESS_DENIED` | 资源访问被拒绝 | 检查用户权限或资源所有权 |
| `ADMIN_REQUIRED` | 需要管理员权限 | 使用管理员账户操作 |

## 📝 请求错误 (400)

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `INVALID_REQUEST_FORMAT` | 请求格式无效 | 检查JSON格式和Content-Type |
| `MISSING_REQUIRED_FIELD` | 缺少必填字段 | 补充必填字段 |
| `INVALID_FIELD_VALUE` | 字段值无效 | 检查字段值是否符合要求 |
| `VALIDATION_FAILED` | 数据验证失败 | 检查数据格式和约束 |

## 🎯 预测相关错误

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `PREDICTION_NOT_FOUND` | 预测不存在 | 检查预测ID |
| `MATCH_NOT_FOUND` | 比赛不存在 | 检查比赛ID |
| `MATCH_STARTED` | 比赛已开始 | 比赛开始后不能修改预测 |
| `DUPLICATE_PREDICTION` | 重复预测 | 用户已对该比赛创建预测 |
| `PREDICTION_DEADLINE_PASSED` | 预测截止时间已过 | 在比赛开始前提交预测 |
| `INVALID_SCORE` | 无效比分 | 比分必须是非负整数 |
| `CONFIDENCE_OUT_OF_RANGE` | 置信度超出范围 | 置信度必须在0-1之间 |

## 🏆 统计相关错误

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `STATISTICS_NOT_AVAILABLE` | 统计数据不可用 | 稍后重试或联系管理员 |
| `INSUFFICIENT_DATA` | 数据不足 | 需要更多历史数据 |
| `CALCULATION_ERROR` | 计算错误 | 检查输入参数或联系技术支持 |

## 🗄️ 数据相关错误

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `DATABASE_CONNECTION_FAILED` | 数据库连接失败 | 检查数据库状态或联系管理员 |
| `DATA_INTEGRITY_VIOLATION` | 数据完整性违规 | 检查数据关联性 |
| `RESOURCE_NOT_FOUND` | 资源不存在 | 检查资源ID |
| `RESOURCE_LOCKED` | 资源被锁定 | 等待资源解锁或联系管理员 |

## ⚡ 系统错误 (500)

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `INTERNAL_SERVER_ERROR` | 内部服务器错误 | 联系技术支持 |
| `SERVICE_UNAVAILABLE` | 服务不可用 | 稍后重试或检查系统状态 |
| `TIMEOUT_ERROR` | 请求超时 | 减少请求数据量或重试 |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限 | 降低请求频率 |

## 🔧 错误响应格式

### 标准错误响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {
      "field": "具体字段信息",
      "value": "错误值"
    },
    "timestamp": "2024-01-01T10:00:00Z"
  }
}
```

### 验证错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "数据验证失败",
    "details": {
      "errors": [
        {
          "field": "confidence_score",
          "message": "置信度必须在0-1之间",
          "value": 1.5
        },
        {
          "field": "home_score_prediction",
          "message": "比分必须是非负整数",
          "value": -1
        }
      ]
    }
  }
}
```

## 📞 错误处理最佳实践

### 客户端处理
1. **检查HTTP状态码**: 根据状态码确定错误类型
2. **解析错误代码**: 根据错误代码提供具体解决方案
3. **实现重试机制**: 对于临时性错误实现自动重试
4. **用户友好提示**: 将技术错误转换为用户友好的消息

### 重试策略
- **401错误**: 刷新令牌后重试
- **429错误**: 使用指数退避重试
- **500错误**: 短暂延迟后重试最多3次
- **网络错误**: 实现网络重连机制

### 监控和日志
- 记录所有错误到日志系统
- 监控错误率和趋势
- 设置关键错误的告警
- 定期分析错误模式

---

*文档版本: v1.0.0 | 最后更新: 2024-01-01*
"""

    # 写入错误代码参考文档
    with open(api_docs_dir / "errors.md", 'w', encoding='utf-8') as f:
        f.write(errors_doc)


def update_main_readme():
    """更新API文档主索引"""

    readme_content = """# API文档

## 📚 足球预测系统 RESTful API

### 🏗️ 基础信息
- **基础URL**: `http://localhost:8000`
- **API版本**: `v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON

### 📋 核心API模块

#### 🎯 预测服务
- **文档**: [预测API详细说明](predictions.md)
- **端点**: `/api/predictions/*`
- **功能**: 比赛预测创建、查询、统计

#### 🏥 健康检查
- **文档**: [健康检查API](health.md)
- **端点**: `/health/*`
- **功能**: 系统状态监控和诊断

#### 📊 错误处理
- **文档**: [错误代码参考](errors.md)
- **覆盖**: 所有API错误代码和解决方案

### 🔐 快速开始

#### 1. 获取访问令牌
```bash
curl -X POST "http://localhost:8000/auth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username=your_username&password=your_password"
```

#### 2. 创建预测
```bash
curl -X POST "http://localhost:8000/api/predictions" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "match_id": 123,
    "home_score_prediction": 2,
    "away_score_prediction": 1,
    "confidence_score": 0.85
  }'
```

#### 3. 获取预测列表
```bash
curl -X GET "http://localhost:8000/api/predictions" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 📖 在线文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 🔧 开发工具
- **Postman集合**: [下载链接](../tools/postman_collection.json)
- **OpenAPI规范**: [查看规范](openapi-config.json)
- **SDK示例**: [Python SDK](../examples/python/), [JavaScript SDK](../examples/javascript/)

### 📞 技术支持
- **错误代码**: 查看[错误代码参考](errors.md)
- **API限制**: 每分钟最多1000次请求
- **支持邮箱**: api-support@football-prediction.com

---

**文档版本**: v1.0.0
**最后更新**: 2024-01-01
**维护团队**: API开发团队
"""

    api_docs_dir = Path("docs/api")
    with open(api_docs_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)


def main():
    """主函数"""

    create_detailed_api_docs()

    update_main_readme()



if __name__ == "__main__":
    main()
