# API错误代码参考

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
