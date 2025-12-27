---
name: performance-monitoring
description: Monitor system performance, prediction accuracy, and real-time metrics using Prometheus and Grafana. Use when checking system health, analyzing performance data, or tracking prediction accuracy.
---

# Performance Monitoring Skill

## 概述
全面的系统性能监控技能，集成Prometheus指标收集和Grafana可视化，提供实时监控和告警功能。

## 核心功能

### 1. 实时性能指标
- **API性能**: QPS、P95延迟、错误率
- **业务指标**: 预测请求率、准确率、置信度分布
- **系统资源**: CPU、内存、磁盘、网络使用率
- **缓存健康**: Redis命中率、内存使用

### 2. 可视化仪表板
- **Grafana集成**: 专业的可视化仪表板
- **实时监控**: 动态更新的图表和指标
- **历史分析**: 长期趋势和性能对比
- **自定义视图**: 按需定制的监控视图

### 3. 智能告警
- **阈值告警**: 基于指标阈值的自动告警
- **趋势分析**: 异常模式识别
- **多渠道通知**: 邮件、Slack、短信告警
- **告警升级**: 分级告警机制

## 监控架构

### 数据流
```
应用 → Prometheus → Grafana → 用户
 ↓      ↓           ↓
指标   存储       可视化
```

### 组件说明
- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化和仪表板
- **Alertmanager**: 告警路由和通知
- **Node Exporter**: 系统级指标

## 关键指标定义

### API性能指标
```python
# 自定义指标
from prometheus_client import Counter, Histogram, Gauge

# 请求计数器
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 响应时间
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# 预测准确率
PREDICTION_ACCURACY = Gauge(
    'prediction_accuracy_rate',
    'Current prediction accuracy rate'
)
```

### 业务指标
- **预测准确率**: 实时计算模型准确率
- **日活跃用户**: 使用系统的用户数
- **预测次数**: 每日预测请求总数
- **模型推理时间**: 单次预测耗时

### 系统指标
- **CPU使用率**: 应用CPU占用
- **内存使用**: 应用内存消耗
- **磁盘IO**: 读写IOPS和延迟
- **网络流量**: 入站出站流量

## 使用方法

### 启动监控服务
```bash
# 启动完整监控栈
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 访问监控界面
```bash
# Prometheus指标
http://localhost:9090

# Grafana仪表板
http://localhost:3000
# 用户名/密码: admin/admin123
```

### 查看特定指标
```bash
# 通过API查询
curl "http://localhost:9090/api/v1/query?query=http_requests_total"

# 通过PromQL查询
rate(http_requests_total[5m])
histogram_quantile(0.95, http_request_duration_seconds_bucket)
```

## 仪表板配置

### 1. API性能仪表板
- **请求量趋势**: QPS时间序列图
- **响应时间分布**: P50/P95/P99延迟
- **错误率监控**: 4xx/5xx错误比例
- **热门端点**: 最频繁访问的API

### 2. 业务指标仪表板
- **预测准确率**: 实时准确率趋势
- **用户活跃度**: DAU/MAU统计
- **模型性能**: 推理时间和吞吐量
- **置信度分布**: 预测置信度统计

### 3. 系统资源仪表板
- **CPU/内存**: 实时资源使用
- **网络I/O**: 流量和连接数
- **磁盘使用**: 存储空间和IOPS
- **容器健康**: Docker容器状态

### 4. 缓存健康仪表板
- **Redis状态**: 连接数和内存使用
- **缓存命中率**: 各类型缓存命中率
- **键空间统计**: 缓存键数量和过期
- **慢查询日志**: Redis慢查询分析

## 告警规则

### API告警规则
```yaml
# prometheus/alerts.yml
groups:
- name: api-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  - alert: HighLatency
    expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High P95 latency detected"
```

### 业务告警规则
```yaml
- alert: LowPredictionAccuracy
  expr: prediction_accuracy_rate < 0.60
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Prediction accuracy below threshold"

- alert: ModelInferenceTimeHigh
  expr: model_inference_duration_seconds > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Model inference time too high"
```

### 系统告警规则
```yaml
- alert: HighCPUUsage
  expr: cpu_usage_percent > 80
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "CPU usage above 80%"

- alert: LowCacheHitRate
  expr: redis_cache_hit_rate < 0.50
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Redis cache hit rate below 50%"
```

## 性能优化

### 指标收集优化
```python
# 使用直方图减少基数
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# 批量提交指标
from prometheus_client import CollectorRegistry
registry = CollectorRegistry()
```

### 存储优化
- **数据保留策略**: 配置合适的数据保留时间
- **采样率**: 高频指标适当降采样
- **压缩**: 启用数据压缩节省空间
- **分片**: 大规模部署时的数据分片

## 集成示例

### 应用代码集成
```python
from prometheus_client import start_http_server, Counter

# 启动指标服务器
start_http_server(8001)

# 在API中记录指标
REQUEST_COUNT.labels(
    method='POST',
    endpoint='/predict',
    status='200'
).inc()
```

### 中间件集成（FastAPI）
```python
from prometheus_client import make_asgi_app
from fastapi import FastAPI

app = FastAPI()
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)

    REQUEST_DURATION.observe(
        time.time() - start_time,
        labels={
            'method': request.method,
            'endpoint': request.url.path
        }
    )

    return response
```

## 监控最佳实践

### 1. 指标设计原则
- **有意义**: 选择真正重要的指标
- **可操作**: 指标变化应能指导行动
- **可理解**: 指标名称和标签清晰易懂
- **稳定性**: 避免频繁变更指标定义

### 2. 告警策略
- **避免告警风暴**: 合理设置告警阈值
- **分级处理**: 区分warning和critical
- **自动恢复**: 问题解决后自动清除告警
- **告警收敛**: 相关告警合并通知

### 3. 仪表板设计
- **信息密度**: 平衡信息量和可读性
- **关键指标置顶**: 最重要的指标放在前面
- **颜色编码**: 使用颜色快速识别问题
- **时间范围**: 提供多时间维度视图

## 故障排查

### 常见问题
1. **Prometheus无法采集数据**
   - 检查网络连接
   - 验证指标端点可访问性
   - 查看Prometheus日志

2. **Grafana无法连接Prometheus**
   - 检查数据源配置
   - 验证网络连通性
   - 确认Prometheus地址正确

3. **告警不触发**
   - 检查告警规则语法
   - 验证阈值设置
   - 查看Alertmanager状态

### 调试工具
```bash
# 查看Prometheus目标
curl http://localhost:9090/api/v1/targets

# 测试告警规则
curl -X POST http://localhost:9090/api/v1/alerts

# 查看指标标签
curl "http://localhost:9090/api/v1/label/__name__/values"
```

## 扩展功能

### 1. 分布式追踪
- **Jaeger集成**: 请求链路追踪
- **OpenTelemetry**: 标准化遥测数据
- **性能分析**: 识别性能瓶颈

### 2. 日志聚合
- **ELK Stack**: Elasticsearch + Logstash + Kibana
- **Fluentd**: 日志收集和转发
- **结构化日志**: JSON格式日志

### 3. APM监控
- **应用性能监控**: 代码级别性能分析
- **数据库监控**: 查询性能分析
- **缓存监控**: Redis性能优化

## 相关配置文件

- `deploy/monitoring/prometheus.yml` - Prometheus配置
- `deploy/monitoring/alerts.yml` - 告警规则
- `deploy/monitoring/telegraf.conf` - 系统指标收集
- `docker-compose.yml` - 监控服务定义

## 注意事项

### 安全考虑
- **访问控制**: 限制监控接口访问
- **数据加密**: 敏感指标数据加密
- **网络安全**: 内网部署监控服务

### 资源消耗
- **存储规划**: 监控数据存储容量规划
- **网络带宽**: 指标传输带宽控制
- **计算资源**: 监控系统资源占用

## Related Skills
- `deployment-management`: Deployment management
- `docker-devops`: Docker and DevOps best practices
- `database-operations`: Database operations
- `data-engineering`: Data pipeline engineering