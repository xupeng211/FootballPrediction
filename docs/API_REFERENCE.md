# API 参考文档

## 概述

本文档描述了足球预测系统的核心API接口和使用方法。

## 核心架构

### 模块结构

```
src/
├── api/                 # API路由和处理
│   ├── betting_api.py   # 投注相关API
│   ├── predictions.py   # 预测相关API
│   ├── auth.py         # 认证相关API
│   └── data_router.py  # 数据查询API
├── core/               # 核心功能
│   ├── constants.py    # 系统常量
│   ├── container.py    # 依赖注入容器
│   └── di.py          # 依赖注入实现
├── domain/            # 领域层
│   ├── models/        # 业务实体
│   ├── strategies/    # 预测策略
│   └── events/        # 领域事件
├── services/          # 业务服务层
├── utils/             # 工具类
└── database/          # 数据访问层
```

## API 端点

### 认证相关

#### 用户注册
```http
POST /auth/register
Content-Type: application/json

{
  "username": "test_user",
  "email": "test@example.com",
  "password": "secure_password"
}
```

#### 用户登录
```http
POST /auth/login
Content-Type: application/json

{
  "username": "test_user",
  "password": "secure_password"
}
```

### 投注相关

#### 获取投注建议
```http
POST /betting/recommendations
Authorization: Bearer <token>
Content-Type: application/json

{
  "match_id": "12345",
  "strategy": "kelly_criterion",
  "bankroll": 1000
}
```

#### 更新赔率
```http
POST /betting/odds/update
Authorization: Bearer <token>
Content-Type: application/json

{
  "match_id": "12345",
  "home_odds": 2.5,
  "away_odds": 3.2,
  "draw_odds": 3.0
}
```

### 预测相关

#### 创建预测
```http
POST /predictions/create
Authorization: Bearer <token>
Content-Type: application/json

{
  "match_id": "12345",
  "strategy": "ml_model",
  "parameters": {
    "confidence": 0.75,
    "risk_level": "medium"
  }
}
```

#### 获取预测结果
```http
GET /predictions/{prediction_id}
Authorization: Bearer <token>
```

## 数据模型

### 响应格式

所有API响应都遵循统一格式：

```json
{
  "status": "success|error",
  "data": { ... },
  "message": "描述信息",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### 错误处理

错误响应包含详细的错误信息：

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "field": "email",
      "reason": "邮箱格式不正确"
    }
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## 认证机制

系统使用JWT (JSON Web Token) 进行认证：

1. 用户登录后获得访问令牌
2. 在API请求中添加 `Authorization: Bearer <token>` 头
3. 令牌有效期：30分钟
4. 支持令牌刷新机制

## 限流规则

- 每个IP每分钟最多100个请求
- 每个用户每分钟最多200个请求
- 超出限制返回429状态码

## 版本信息

当前API版本：v1.0.0

## 联系方式

如有问题，请联系开发团队。
