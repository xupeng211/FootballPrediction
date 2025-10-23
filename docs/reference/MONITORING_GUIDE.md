# 监控系统指南

## 📋 概述

足球预测系统采用企业级监控架构，提供全方位的系统可观测性。本指南详细介绍了监控系统的配置、使用和维护方法，确保系统的稳定运行和性能优化。

## 🏗️ 监控架构概览

### 监控生态系统

```
┌─────────────────────────────────────────────────────────────────┐
│                    监控数据采集层                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   应用监控      │   基础设施监控    │        业务监控              │
│  (APM)         │  (Infrastructure) │     (Business)              │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ - 请求追踪      │ - 系统资源       │ - 预测准确性                 │
│ - 错误跟踪      │ - 网络流量       │ - 数据质量                   │
│ - 性能分析      │ - 服务健康       │ - 用户活跃度                 │
│ - 自定义指标     │ - 日志聚合       │ - 收集成功率                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    数据存储与处理层                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Prometheus    │      Loki        │        InfluxDB              │
│    (时序数据)    │    (日志存储)     │        (业务数据)            │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    可视化与告警层                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│    Grafana      │  Alertmanager   │         PagerDuty             │
│   (仪表板)      │   (告警管理)     │        (通知)                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 核心组件

| 组件 | 用途 | 端口 | 状态 |
|------|------|------|------|
| **Prometheus** | 指标收集和存储 | 9090 | ✅ 运行中 |
| **Grafana** | 可视化仪表板 | 3000 | ✅ 运行中 |
| **Loki** | 日志聚合和查询 | 3100 | ✅ 运行中 |
| **Alertmanager** | 告警路由和通知 | 9093 | ✅ 运行中 |
| **Jaeger** | 分布式追踪 | 16686 | ⚠️ 配置中 |

## 🚀 快速开始

### 启动监控服务

```bash
# 启动所有监控服务
make up

# 仅启动监控服务栈
docker-compose --profile monitoring up -d

# 检查服务状态
make monitoring-status

# 查看服务日志
make logs monitoring
```

### 访问监控界面

| 服务 | 地址 | 账户 | 密码 |
|------|------|------|------|
| **Grafana** | http://localhost:3000 | admin | admin |
| **Prometheus** | http://localhost:9090 | - | - |
| **Alertmanager** | http://localhost:9093 | - | - |
| **Jaeger** | http://localhost:16686 | - | - |

## 📊 指标监控

### Prometheus 指标

#### 核心业务指标

```python
# 预测相关指标
predictions_total{model_version="v1.0.0"}  # 预测总数
prediction_duration_seconds             # 预测耗时
prediction_accuracy{model="random_forest"} # 预测准确率

# 数据质量指标
data_collection_success_rate{source="api"} # 数据收集成功率
feature_processing_duration_seconds      # 特征处理耗时
cache_hit_ratio{cache_type="prediction"}   # 缓存命中率
```

#### 系统性能指标

```python
# 应用性能指标
http_requests_total{method="GET", status="200"}  # HTTP请求总数
http_request_duration_seconds                   # HTTP请求耗时
uvicorn_workers_active                           # 活跃工作进程数

# 数据库性能指标
database_connections_active                       # 活跃数据库连接数
database_query_duration_seconds                   # 数据库查询耗时
database_connections_pool_utilization           # 连接池利用率

# 系统资源指标
system_cpu_usage_percent                          # CPU使用率
system_memory_usage_bytes                        # 内存使用量
system_disk_usage_percent                        # 磁盘使用率
```

### 自定义指标创建

```python
from src.monitoring.metrics_collector import get_metrics_collector
from prometheus_client import Counter, Histogram, Gauge

class PredictionMetrics:
    """预测指标类"""

    def __init__(self):
        self.collector = get_metrics_collector()

        # 预测计数器
        self.prediction_counter = Counter(
            'predictions_total',
            'Total number of predictions',
            ['model_version', 'status']
        )

        # 预测耗时直方图
        self.prediction_duration = Histogram(
            'prediction_duration_seconds',
            'Time spent making predictions',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        # 预测准确率仪表
        self.prediction_accuracy = Gauge(
            'prediction_accuracy',
            'Current prediction accuracy',
            ['model', 'time_range']
        )

    def record_prediction(self, model_version: str, success: bool, duration: float):
        """记录预测指标"""
        status = 'success' if success else 'failure'
        self.prediction_counter.labels(
            model_version=model_version,
            status=status
        ).inc()
        self.prediction_duration.observe(duration)

    def update_accuracy(self, model: str, accuracy: float):
        """更新准确率指标"""
        self.prediction_accuracy.labels(model=model).set(accuracy)
```

### 指标暴露配置

```python
# src/main.py
from prometheus_client import generate_latest, REGISTRY
from fastapi import Response

@app.get("/metrics")
async def metrics():
    """Prometheus指标端点"""
    if generate_latest(REGISTRY):
        return Response(
            generate_latest(REGISTRY),
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    return Response("No metrics available", status_code=404)
```

## 📈 Grafana 仪表板

### 预定义仪表板

#### 1. 系统概览仪表板
- **目的**: 整体系统健康状态监控
- **关键指标**: CPU、内存、请求量、错误率
- **刷新间隔**: 30秒

#### 2. 应用性能仪表板
- **目的**: 应用层性能分析
- **关键指标**: API响应时间、错误率、并发数
- **刷新间隔**: 15秒

#### 3. 业务指标仪表板
- **目的**: 业务指标监控
- **关键指标**: 预测量、准确率、数据收集率
- **刷新间隔**: 1分钟

#### 4. 数据库性能仪表板
- **目的**: 数据库性能监控
- **关键指标**: 连接数、查询时间、锁等待
- **刷新间隔**: 30秒

### 仪表板配置示例

```json
{
  "dashboard": {
    "title": "足球预测系统概览",
    "panels": [
      {
        "title": "API请求率",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "响应时间",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### 导入预配置仪表板

```bash
# 导入系统仪表板
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @config/monitoring/system-overview.json

# 导入业务仪表板
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @config/monitoring/business-metrics.json
```

## 🚨 告警系统

### Alertmanager 配置

```yaml
# config/monitoring/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@football-prediction.com'
  smtp_auth_username: 'alerts'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/webhook'
        send_resolved: true

  - name: 'email.notifications'
    email_configs:
      - to: 'admin@football-prediction.com'
        subject: '[Alert] Football Prediction System'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

### 告警规则定义

```yaml
# config/monitoring/alert_rules.yml
groups:
  - name: system_alerts
    rules:
      - alert: HighCPUUsage
        expr: system_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"

      - alert: HighMemoryUsage
        expr: system_memory_usage_bytes / system_memory_capacity_bytes > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 90%"

  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% for more than 2 minutes"

      - alert: LowPredictionAccuracy
        expr: prediction_accuracy{model="random_forest"} < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low prediction accuracy"
          description: "Prediction accuracy for random_forest model is below 70%"
```

### 自定义告警集成

```python
from src.monitoring.alert_manager import AlertManager, AlertSeverity, AlertType

class CustomAlertHandler:
    """自定义告警处理器"""

    def __init__(self):
        self.alert_manager = AlertManager()

    def check_prediction_accuracy(self):
        """检查预测准确率"""
        accuracy = self.get_current_accuracy()

        if accuracy < 0.7:
            self.alert_manager.create_alert(
                name="LowPredictionAccuracy",
                severity=AlertSeverity.MEDIUM,
                alert_type=AlertType.SYSTEM,
                message=f"Prediction accuracy dropped to {accuracy:.2%}"
            )

    def check_data_collection_health(self):
        """检查数据收集健康状态"""
        success_rate = self.get_collection_success_rate()

        if success_rate < 0.95:
            self.alert_manager.create_alert(
                name="DataCollectionIssues",
                severity=AlertSeverity.HIGH,
                alert_type=AlertType.DATABASE,
                message=f"Data collection success rate: {success_rate:.2%}"
            )
```

## 📝 日志管理

### Loki 日志配置

```yaml
# config/monitoring/loki.yml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

ingester:
  lifecycler:
    address: 127.0.0.1:9095
    ring:
      kvstore:
        store: inmemory
    max_transfer_retries: 0
    final_sleep: 0s
  chunk_idle_period: 1h
  max_chunk_age: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 30s
  wal:
    dir: /tmp/wal
    enabled: true

schema_config:
  configs:
    - from: 2024-01-01
      store:
        type: boltdb-shipper
        tsdb_shipper:
          active_index_directory: /tmp/loki/boltdb-shipper-active
          cache_location: /tmp/loki/boltdb-shipper-cache
          shared_store: s3
          resync_interval: 5m
```

### 结构化日志配置

```python
# src/core/logging.py
import logging
import json
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger

class StructuredLogger:
    """结构化日志器"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.setup_logger()

    def setup_logger(self):
        """设置日志器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
        ))

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_request(self, method: str, path: str, status: int, duration: float):
        """记录请求日志"""
        self.logger.info(
            "HTTP Request",
            extra={
                "event_type": "http_request",
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_prediction(self, match_id: int, model: str, success: bool, confidence: float):
        """记录预测日志"""
        self.logger.info(
            "Prediction Result",
            extra={
                "event_type": "prediction",
                "match_id": match_id,
                "model": model,
                "success": success,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

### Loki Promtail 配置

```yaml
# config/monitoring/promtail.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: football-prediction-logs
    static_configs:
      - targets:
        - localhost:8000
    labels:
      job: football-prediction
      __path__: /var/log/football-prediction/*.log

    pipeline_stages:
      - json:
          expressions:
            level: level
            message: message
            timestamp: timestamp
```

## 🔍 分布式追踪

### Jaeger 配置

```yaml
# config/monitoring/jaeger.yml
collector:
  zipkin:
    host_port: 9411

sampling:
  default_strategy:
    type: probabilistic
    param: 0.1  # 10% sampling rate

storage:
  type: memory
  memory:
    max_traces: 50000
```

### OpenTelemetry 集成

```python
# src/monitoring/apm_integration.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

class APMIntegration:
    """APM集成类"""

    def __init__(self):
        self.setup_tracing()
        self.setup_instrumentation()

    def setup_tracing(self):
        """设置追踪"""
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )

        span_processor = BatchSpanProcessor(jaeger_exporter)

        self.tracer_provider = TracerProvider(
            span_processors=[span_processor]
        )

        trace.set_tracer_provider(self.tracer_provider)

    def setup_instrumentation(self):
        """设置自动仪表化"""
        # FastAPI仪表化
        FastAPIInstrumentor().instrument()

        # SQLAlchemy仪表化
        SQLAlchemyInstrumentor().instrument()

# 在main.py中启用APM
def setup_apm():
    """设置APM"""
    apm = APMIntegration()
    return apm
```

### 自定义追踪

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("predict_match")
async def predict_match(match_id: int) -> Dict:
    """预测比赛，带追踪"""
    with tracer.start_as_current_span("load_features") as span:
        span.set_attribute("match_id", match_id)
        features = await load_match_features(match_id)

    with tracer.start_as_current_span("model_inference") as span:
        span.set_attribute("model", "random_forest")
        prediction = await run_prediction_model(features)

    with tracer.start_as_current_span("save_result") as span:
        span.set_attribute("prediction_confidence", prediction.get("confidence"))
        await save_prediction_result(match_id, prediction)

    return prediction
```

## 🛠️ 监控工具使用

### 常用PromQL查询

```promql
# 1. 系统负载监控
# CPU使用率
rate(cpu_usage_total[5m])

# 内存使用率
(system_memory_usage_bytes / system_memory_capacity_bytes) * 100

# 2. 应用性能监控
# API错误率
(rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) * 100

# 95th百分位响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 3. 业务指标监控
# 预测准确率趋势
prediction_accuracy{model="random_forest"}

# 数据收集成功率
rate(data_collection_success_total[5m]) / rate(data_collection_total[5m]) * 100

# 4. 数据库性能监控
# 慢查询
histogram_quantile(0.95, database_query_duration_seconds_bucket[5m]) > 1.0

# 连接池使用率
database_connections_active / database_connections_max * 100
```

### Grafana 查询技巧

```sql
-- 1. 时间序列对比
SELECT
  time,
  value
FROM (
    SELECT
      $__timeSeriesAlias(time, value)
    FROM (
      SELECT
        now() AS time,
        avg(rate(http_requests_total[5m])) AS value
      FROM http_requests_total
    )
  )

-- 2. 异常检测
SELECT
  time,
  value,
  value - avg(value) OVER (ORDER BY time ROWS BETWEEN 5 PRECEDING AND 5 FOLLOWING) AS anomaly
FROM metrics
WHERE metric = 'cpu_usage'
```

### 告警故障排除

```bash
# 1. 检查Alertmanager状态
curl http://localhost:9093/api/v1/status

# 2. 查看活跃告警
curl http://localhost:9093/api/v1/alerts

# 3. 验证Prometheus配置
curl http://localhost:9090/-/healthy

# 4. 检查Grafana数据源
curl -u admin:admin http://localhost:3000/api/datasources
```

## 📊 监控最佳实践

### 指标设计原则

1. **有意义**: 指标名称和标签应该清晰地表达业务含义
2. **一致性**: 相同类型的指标使用相同的命名规范
3. **可聚合**: 指标应该支持聚合操作
4. **基数控制**: 标签基数应该合理控制，避免高基数问题

### 告警设计原则

1. **可操作**: 告警应该有明确的处理建议
2. **避免噪声**: 设置合理的阈值和持续时间
3. **分级管理**: 使用不同的严重程度级别
4. **自动化**: 优先考虑自动化处理

### 日志设计原则

1. **结构化**: 使用结构化格式（JSON）
2. **上下文**: 包含足够的上下文信息
3. **级别控制**: 合理使用日志级别
4. **性能影响**: 避免日志影响应用性能

## 🚀 故障排查指南

### 常见监控问题

#### 1. 指标缺失
```bash
# 检查指标端点
curl http://localhost:8000/metrics

# 检查Prometheus配置
docker logs prometheus

# 重新加载配置
curl -X POST http://localhost:9090/-/reload
```

#### 2. 仪表板无数据
```bash
# 检查Grafana数据源配置
curl -u admin:admin http://localhost:3000/api/datasources

# 检查Prometheus查询
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=up'

# 验证数据连通性
docker exec -it prometheus promtool query instant 'up'
```

#### 3. 告警不生效
```bash
# 检查Alertmanager配置
curl http://localhost:9093/api/v1/status

# 验证告警规则
promtool check rules config/monitoring/alert_rules.yml

# 重新加载告警规则
curl -X POST http://localhost:9093/-/reload
```

### 性能优化建议

1. **指标收集优化**
   - 控制指标数量和采集频率
   - 使用批量推送减少网络开销
   - 合理设置采样率

2. **存储优化**
   - 配置数据保留策略
   - 使用合适的存储后端
   - 定期清理过期数据

3. **查询优化**
   - 使用时间范围限制
   - 避免全表扫描
   - 优化查询语句

## 📋 监控检查清单

### 日常检查项

- [ ] 检查所有服务状态
- [ ] 查看系统概览仪表板
- [ ] 检查告警状态
- [ ] 验证日志收集正常
- [ ] 确认备份任务完成

### 周期检查项

- [ ] 审查告警规则合理性
- [ ] 更新仪表板配置
- [ ] 清理过期监控数据
- [ ] 优化性能瓶颈
- [ ] 更新监控文档

### 紧急响应流程

1. **收到告警** → 查看告警详情
2. **确认影响范围** → 评估业务影响
3. **执行修复** → 按照预案处理
4. **验证恢复** → 确认问题解决
5. **更新文档** → 记录处理过程

## 📚 相关文档

- [系统架构文档](../architecture/SYSTEM_ARCHITECTURE.md)
- [开发指南](DEVELOPMENT_GUIDE.md)
- [部署指南](../ops/PRODUCTION_DEPLOYMENT_GUIDE.md)
- [数据库架构](DATABASE_SCHEMA.md)
- [术语表](glossary.md)

---

**文档版本**: 1.0
**最后更新**: 2025-10-23
**维护者**: 开发团队
