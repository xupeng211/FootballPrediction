# 🔍 监控系统文档

## 概述

FootballPrediction项目内置了完整的监控系统，提供系统性能指标、业务统计和服务健康状态监控。

## 监控端点

### 1. 📊 性能指标 - `/api/v1/metrics`

获取详细的系统性能和业务指标。

#### 响应示例

```json
{
  "status": "ok",
  "response_time_ms": 1033.08,
  "system": {
    "cpu_percent": 0.5,
    "memory": {
      "total": 8328015872,
      "available": 3384762368,
      "percent": 59.4,
      "used": 4725329920
    },
    "disk": {
      "total": 1081101176832,
      "free": 1003440873472,
      "percent": 2.2
    },
    "load_average": [0.87, 0.99, 0.77]
  },
  "database": {
    "healthy": true,
    "response_time_ms": 0.87,
    "statistics": {
      "teams_count": 20,
      "matches_count": 1500,
      "predictions_count": 8000,
      "active_connections": 5
    }
  },
  "runtime": {
    "uptime_seconds": 1.03,
    "timestamp": "2025-09-09T04:03:29.135646",
    "python_version": "3.11.13",
    "environment": "development"
  },
  "business": {
    "24h_predictions": 150,
    "upcoming_matches_7d": 25,
    "model_accuracy_30d": 78.5,
    "last_updated": "2025-09-09T04:03:29.136691"
  }
}
```

#### 指标说明

**系统指标 (system)**

- `cpu_percent`: CPU使用率百分比
- `memory.total`: 总内存容量(字节)
- `memory.available`: 可用内存(字节)
- `memory.percent`: 内存使用率百分比
- `memory.used`: 已使用内存(字节)
- `disk.total`: 总磁盘容量(字节)
- `disk.free`: 可用磁盘空间(字节)
- `disk.percent`: 磁盘使用率百分比
- `load_average`: 系统负载均值 [1分钟, 5分钟, 15分钟]

**数据库指标 (database)**

- `healthy`: 数据库连接状态
- `response_time_ms`: 数据库响应时间(毫秒)
- `statistics.teams_count`: 球队总数
- `statistics.matches_count`: 比赛总数
- `statistics.predictions_count`: 预测总数
- `statistics.active_connections`: 活跃连接数

**运行时指标 (runtime)**

- `uptime_seconds`: 应用运行时间(秒)
- `timestamp`: 当前时间戳
- `python_version`: Python版本
- `environment`: 运行环境

**业务指标 (business)**

- `24h_predictions`: 24小时内预测数量
- `upcoming_matches_7d`: 7天内即将开始的比赛数
- `model_accuracy_30d`: 30天内模型准确率(%)
- `last_updated`: 业务指标更新时间

### 2. 🏥 服务状态 - `/api/v1/status`

快速检查所有关键服务状态，适用于负载均衡器健康检查。

#### 响应示例

```json
{
  "status": "healthy",
  "timestamp": "2025-09-09T04:03:33.346010",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy"
  }
}
```

#### 状态说明

- `healthy`: 服务正常运行
- `degraded`: 部分服务异常，但系统仍可用
- `unhealthy`: 关键服务故障

## 使用场景

### 1. 性能监控

```bash
# 获取系统性能指标
curl http://localhost:8000/api/v1/metrics | jq .system

# 监控内存使用率
curl -s http://localhost:8000/api/v1/metrics | jq .system.memory.percent
```

### 2. 健康检查

```bash
# 负载均衡器健康检查
curl -f http://localhost:8000/api/v1/status

# 检查数据库状态
curl -s http://localhost:8000/api/v1/metrics | jq .database.healthy
```

### 3. 业务监控

```bash
# 查看模型准确率
curl -s http://localhost:8000/api/v1/metrics | jq .business.model_accuracy_30d

# 查看最近活动
curl -s http://localhost:8000/api/v1/metrics | jq .business
```

## 监控集成

### Prometheus集成

监控端点兼容Prometheus格式，可直接用于指标收集。

### 告警配置

推荐告警规则：

- CPU使用率 > 80%
- 内存使用率 > 85%
- 磁盘使用率 > 90%
- 数据库响应时间 > 1000ms
- 任何服务状态为 unhealthy

### 日志监控

监控API会记录详细日志，包括：

- 指标获取异常
- 数据库连接问题
- 业务指标计算错误

## 性能考虑

- 监控API响应时间通常 < 2秒
- 系统指标获取有1秒CPU采样时间
- 数据库查询使用连接池，影响较小
- 建议监控频率：30-60秒一次

## 故障排除

### 常见问题

1. **监控端点404**
   - 检查路由是否正确注册
   - 确认应用已重启加载新路由

2. **数据库指标为null**
   - 检查数据库连接权限
   - 确认相关表已创建

3. **系统指标异常**
   - 检查psutil模块是否安装
   - 确认容器有足够权限读取系统信息

### 调试命令

```bash
# 检查监控API
curl -v http://localhost:8000/api/v1/status

# 查看应用日志
docker-compose logs app | grep -i monitoring

# 测试数据库连接
curl -s http://localhost:8000/health | jq .checks.database
```
