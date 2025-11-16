# 📚 API参考文档

## 概述

足球预测系统提供RESTful API，支持预测、数据查询、系统管理等功能。

## 🔗 基础信息

- **Base URL**: `http://localhost:8000`
- **API Version**: `v1`
- **Content-Type**: `application/json`
- **认证**: JWT Token (生产环境)

## 🎯 核心端点

### 1. 预测 API

#### 创建预测

```http
POST /api/v1/predictions
Content-Type: application/json
Authorization: Bearer <token>

{
  "match_id": 12345,
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "league": "Premier League",
  "season": "2024-25",
  "match_date": "2024-12-15T20:00:00Z",
  "venue": "Old Trafford"
}
```

**响应**:
```json
{
  "id": "pred_123456",
  "match_id": 12345,
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "predicted_home_score": 2,
  "predicted_away_score": 1,
  "predicted_result": "home_win",
  "confidence": 0.78,
  "strategy_used": "enhanced_ml_model",
  "created_at": "2024-12-10T15:30:00Z"
}
```

### 2. 系统管理 API

#### 健康检查

```http
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-10T15:30:00Z",
  "version": "1.0.0",
  "environment": "production"
}
```

## 🔐 认证

使用JWT Token认证，在请求头中添加：
```
Authorization: Bearer <token>
```

## 📝 响应格式

### 成功响应
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败"
  }
}
```

## 🚫 限制

- **请求频率**: 1000 requests/hour (认证用户)
- **批量预测**: 最多50个比赛/次
- **数据查询**: 最多1000条记录/次

---

**版本**: v1.0 | **更新**: 2025-11-16