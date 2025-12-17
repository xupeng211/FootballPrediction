# 全链路可观测性系统设置指南

## 📊 监控系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App    │    │    Prometheus   │    │     Grafana     │
│                 │    │                 │    │                 │
│ • /metrics 端点   │◄──►│ • 数据收集       │◄──►│ • 可视化仪表盘    │
│ • 业务指标埋点     │    │ • 报警规则       │    │ • 自动配置数据源  │
│ • HTTP监控        │    │ • 时序数据存储   │    │ • 预制面板       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │  Redis Exporter │    │  Node Exporter  │
│                 │    │                 │    │                 │
│ • 缓存层         │    │ • Redis指标      │    │ • 系统指标       │
│ • Celery队列     │    │ • 命中率监控     │    │ • CPU/内存/磁盘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 快速启动

```bash
# 启动完整的监控系统
docker-compose up -d

# 查看服务状态
docker-compose ps

# 访问监控界面
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin123)
```

## 📈 关键指标说明

### API 性能指标
- **QPS**: `rate(flask_http_request_total[5m])`
- **P95延迟**: `histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))`
- **错误率**: `rate(flask_http_request_exceptions_total[5m]) / rate(flask_http_request_total[5m]) * 100`

### 业务指标
- **预测请求率**: `rate(prediction_requests_total[5m])`
- **模型推理延迟**: `histogram_quantile(0.95, rate(model_inference_latency_seconds_bucket[5m]))`
- **预测准确率**: `prediction_accuracy_total`

### 系统资源指标
- **CPU使用率**: `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- **内存使用率**: `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`
- **磁盘使用率**: `(node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100`

### 缓存健康指标
- **Redis命中率**: `redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100`
- **Redis内存使用**: `redis_memory_used_bytes`

## ⚠️ 报警规则

### API 性能报警
- **APIHighErrorRate**: 错误率 > 5% 持续2分钟
- **APIHighLatency**: P95延迟 > 1秒 持续5分钟
- **APIDown**: API服务宕机超过1分钟

### 业务指标报警
- **PredictionRequestsDropping**: 预测请求率 < 0.1/s 持续10分钟
- **ModelInferenceLatencyHigh**: 模型推理P95延迟 > 2秒 持续5分钟

### 系统资源报警
- **HighCPUUsage**: CPU使用率 > 80% 持续10分钟
- **HighMemoryUsage**: 内存使用率 > 85% 持续10分钟
- **HighDiskUsage**: 磁盘使用率 > 90% 持续5分钟

### 缓存健康报警
- **RedisDown**: Redis服务宕机超过1分钟
- **RedisHighMemoryUsage**: Redis内存使用 > 90% 持续5分钟
- **RedisLowHitRate**: 缓存命中率 < 50% 持续15分钟

## 🔧 Grafana 仪表盘

### 访问方式
1. 打开 http://localhost:3000
2. 使用 admin/admin123 登录
3. 选择 "Football Prediction System v2.0" 仪表盘

### 面板说明
- **系统概览**: CPU、内存使用率实时监控
- **API性能**: QPS、P95/P50延迟趋势图
- **业务指标**: 预测请求率、模型推理延迟
- **异步任务**: Celery连接数、队列状态
- **缓存健康**: Redis命中率、内存使用
- **服务状态**: 各服务健康状态统计

## 📝 开发集成

### 添加自定义指标

```python
from src.main import prediction_requests_total, model_inference_latency

# 记录预测请求
prediction_requests_total.labels(
    model_name="xgboost_v2",
    prediction_type="single"
).inc()

# 记录模型推理时间
with model_inference_latency.labels(model_name="xgboost_v2").time():
    result = model.predict(features)
```

### 环境变量配置
```bash
# 启用/禁用指标收集
ENABLE_METRICS=true

# 指标收集间隔
METRICS_SCRAPE_INTERVAL=15s

# 报警配置
ALERT_WEBHOOK_URL=https://your-webhook-url.com
```

## 🔍 故障排查

### 指标缺失
1. 检查应用是否启动：`curl http://localhost:8000/health`
2. 检查指标端点：`curl http://localhost:8000/metrics`
3. 检查Prometheus配置：访问 http://localhost:9090/targets

### Grafana无法访问
1. 检查Grafana容器状态：`docker-compose logs grafana`
2. 验证数据源配置：Settings → Data Sources
3. 检查仪表盘导入：Dashboard → Manage

### 报警不生效
1. 检查Prometheus报警规则：http://localhost:9090/alerts
2. 验证规则表达式语法
3. 检查Alertmanager配置（如果使用）

## 📚 相关文档
- [Prometheus官方文档](https://prometheus.io/docs/)
- [Grafana官方文档](https://grafana.com/docs/)
- [FastAPI集成指南](https://github.com/trallnag/prometheus-fastapi-instrumentator)