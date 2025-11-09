# 健康检查API文档

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
