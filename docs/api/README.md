# API文档

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
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

#### 2. 创建预测
```bash
curl -X POST "http://localhost:8000/api/predictions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": 123,
    "home_score_prediction": 2,
    "away_score_prediction": 1,
    "confidence_score": 0.85
  }'
```

#### 3. 获取预测列表
```bash
curl -X GET "http://localhost:8000/api/predictions" \
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
