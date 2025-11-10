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

#### 📚 完整API参考
- **文档**: [完整API参考手册](COMPLETE_API_REFERENCE.md)
- **覆盖**: 所有API端点的详细说明和使用示例
- **功能**: 企业级API完整指南

#### 🔍 端点映射分析
- **文档**: [API端点映射分析](ENDPOINTS_MAPPING.md)
- **覆盖**: 代码实际端点与文档覆盖率分析
- **功能**: 文档完整性和缺失端点识别

#### 🚀 快速入门
- **文档**: [快速入门指南](GETTING_STARTED_GUIDE.md)
- **覆盖**: 从环境配置到第一个API调用
- **功能**: 开发者友好的学习路径

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
- **Swagger UI**: http://localhost:8000/docs - 交互式API文档
- **ReDoc**: http://localhost:8000/redoc - 生产就绪的API文档
- **OpenAPI JSON**: http://localhost:8000/openapi.json - 原始API规范

### 🔧 开发工具
- **Postman集合**: [下载链接](../tools/postman_collection.json) - 预配置的API请求集合
- **OpenAPI规范**: [查看规范](openapi-config.json) - 完整的API配置文件
- **SDK示例**: [Python SDK](../examples/python/), [JavaScript SDK](../examples/javascript/) - 官方开发库

### 📊 API状态和限制
- **当前状态**: 🟢 正常运行
- **API版本**: v2.0.0
- **请求限制**: 每分钟最多1000次请求
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **HTTPS**: 生产环境强制要求

### 🎯 核心功能
- **比赛预测**: 基于机器学习的智能预测
- **实时数据**: 比赛直播和比分更新
- **数据分析**: 历史数据和趋势分析
- **用户管理**: 安全的用户认证和授权

### 📞 技术支持
- **错误代码**: 查看[错误代码参考](errors.md) - 详细的错误说明和解决方案
- **API文档**: [预测API](predictions.md) - 预测相关接口详细说明
- **健康检查**: [健康检查API](health.md) - 系统监控接口
- **支持邮箱**: api-support@footballprediction.com
- **问题反馈**: [GitHub Issues](https://github.com/xupeng211/FootballPrediction/issues)

### 🚀 快速部署
```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 启动服务
make up

# 访问API文档
open http://localhost:8000/docs
```

---

**文档版本**: v2.0.0
**最后更新**: 2025-11-09
**维护团队**: API开发团队
**许可证**: MIT License
