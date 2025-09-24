# 日志采集与管理策略

## 概述

FootballPrediction 系统的日志管理策略，涵盖日志分级、采集、存储、分析和监控，确保系统可观测性和问题追踪能力。

## 📊 日志分级策略

### 日志级别定义

#### DEBUG (调试级别)
- **用途**: 开发和调试阶段的详细信息
- **内容**: 函数调用、变量值、执行路径
- **环境**: 仅在开发环境启用
- **示例**:
```python
logger.debug("Processing match data: %s", match_data)
logger.debug("Feature calculation result: %s", features)
```

#### INFO (信息级别)
- **用途**: 重要业务事件和操作记录
- **内容**: 业务流程关键节点、状态变更
- **环境**: 所有环境
- **示例**:
```python
logger.info("Data collection started for date: %s", date)
logger.info("Model prediction completed, confidence: %.2f", confidence)
logger.info("User %s requested predictions for %d matches", user_id, count)
```

#### WARNING (警告级别)
- **用途**: 潜在问题或异常情况
- **内容**: 重试操作、数据异常、性能问题
- **环境**: 所有环境
- **示例**:
```python
logger.warning("API rate limit reached, retrying in %d seconds", delay)
logger.warning("Data quality check failed for %s, using fallback", source)
logger.warning("Response time exceeded threshold: %.2fs", duration)
```

#### ERROR (错误级别)
- **用途**: 严重错误和异常
- **内容**: 操作失败、异常堆栈、错误恢复
- **环境**: 所有环境
- **示例**:
```python
logger.error("Database connection failed: %s", str(e))
logger.error("Model prediction failed for match %d: %s", match_id, str(e))
logger.error("Failed to process message: %s", message, exc_info=True)
```

#### CRITICAL (致命级别)
- **用途**: 系统级别的严重问题
- **内容**: 服务不可用、数据丢失、安全事件
- **环境**: 所有环境
- **示例**:
```python
logger.critical("Application startup failed: %s", str(e))
logger.critical("Data corruption detected in table: %s", table_name)
logger.critical("Security breach attempt from IP: %s", ip_address)
```

## 🏗️ 日志采集架构

### 推荐方案：ELK Stack

#### 组件架构
```
Application Logs → Filebeat → Logstash → Elasticsearch → Kibana
                       ↓
               Structured JSON Logs
```

#### 备选方案：Loki Stack
```
Application Logs → Promtail → Loki → Grafana
                       ↓
              Label-based Indexing
```

### 日志格式标准

#### 结构化日志格式 (推荐)
```json
{
  "timestamp": "2023-01-01T10:00:00.000Z",
  "level": "INFO",
  "logger": "src.api.predictions",
  "message": "Prediction request processed successfully",
  "request_id": "req_123456",
  "user_id": "user_789",
  "match_id": 12345,
  "prediction_confidence": 0.85,
  "processing_time_ms": 250,
  "metadata": {
    "endpoint": "/api/v1/predictions",
    "method": "POST",
    "status_code": 200
  }
}
```

#### 应用配置示例
```python
# src/core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加请求上下文
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)
```

## 📍 请求追踪与关联

### Request ID 生成
```python
# middleware/request_tracking.py
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 添加到响应头
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### Trace ID 集成
```python
# src/core/tracing.py
import logging
from contextvars import ContextVar

# 上下文变量
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
span_id_var: ContextVar[str] = ContextVar('span_id', default='')

class TraceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        trace_id = trace_id_var.get()
        span_id = span_id_var.get()

        if trace_id:
            self.extra['trace_id'] = trace_id
        if span_id:
            self.extra['span_id'] = span_id

        return msg, kwargs
```

## 🔧 ELK Stack 集成配置

### 1. Filebeat 配置
```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  fields:
    service: football-prediction
    environment: production
  fields_under_root: true
  multiline.pattern: '^{'
  multiline.negate: true
  multiline.match: after

output.logstash:
  hosts: ["logstash:5044"]

processors:
- add_host_metadata:
    when.not.contains.tags: forwarded
- add_docker_metadata: ~
```

### 2. Logstash 配置
```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [service] == "football-prediction" {
    json {
      source => "message"
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    mutate {
      add_field => { "[@metadata][index]" => "football-logs-%{+YYYY.MM.dd}" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][index]}"
  }
}
```

### 3. Elasticsearch 索引模板
```json
{
  "template": "football-logs-*",
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index.mapping.total_fields.limit": 2000
  },
  "mappings": {
    "properties": {
      "timestamp": {
        "type": "date"
      },
      "level": {
        "type": "keyword"
      },
      "logger": {
        "type": "keyword"
      },
      "message": {
        "type": "text",
        "analyzer": "standard"
      },
      "request_id": {
        "type": "keyword"
      },
      "user_id": {
        "type": "keyword"
      },
      "processing_time_ms": {
        "type": "integer"
      }
    }
  }
}
```

## 🎯 Loki Stack 集成配置 (备选)

### 1. Promtail 配置
```yaml
# promtail.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
- job_name: football-app
  static_configs:
  - targets:
      - localhost
    labels:
      job: football-app
      service: football-prediction
      __path__: /app/logs/*.log

  pipeline_stages:
  - json:
      expressions:
        level: level
        timestamp: timestamp
        logger: logger
        request_id: request_id

  - labels:
      level:
      logger:

  - timestamp:
      source: timestamp
      format: RFC3339
```

### 2. Loki 配置
```yaml
# loki.yml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

### 3. Grafana 日志查询示例
```logql
# 查询错误日志
{service="football-prediction"} |= "ERROR"

# 查询特定请求的所有日志
{service="football-prediction"} | json | request_id="req_123456"

# 统计错误率
rate({service="football-prediction"} |= "ERROR" [5m])

# 查询慢请求
{service="football-prediction"} | json | processing_time_ms > 1000
```

## 📁 日志存储和轮转

### 本地日志配置
```python
# src/core/logging.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'src.core.logging.JSONFormatter',
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'src': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'uvicorn': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    }
}
```

### Docker 日志配置
```yaml
# docker-compose.yml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service,environment"
```

## 🔍 日志分析和监控

### 常用查询模式

#### 1. 错误分析
```bash
# Elasticsearch
GET football-logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "aggs": {
    "error_by_logger": {
      "terms": {"field": "logger"}
    }
  }
}

# Loki
{service="football-prediction"} |= "ERROR" | json | __error__=""
```

#### 2. 性能分析
```bash
# 慢请求分析
{service="football-prediction"}
| json
| processing_time_ms > 1000
| line_format "{{.timestamp}} - {{.message}} ({{.processing_time_ms}}ms)"
```

#### 3. 用户行为分析
```bash
# 用户请求模式
{service="football-prediction"}
| json
| user_id != ""
| stats count() by user_id
```

### 告警规则配置

#### Prometheus 告警规则
```yaml
# log_alerts.yml
groups:
  - name: log_alerts
    rules:
    - alert: HighErrorRate
      expr: rate(log_entries_total{level="ERROR"}[5m]) > 0.1
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"

    - alert: NoLogsReceived
      expr: absent(rate(log_entries_total[5m]))
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "No logs received in the last 5 minutes"
```

#### 日志监控指标
```python
# src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 日志计数器
log_entries_total = Counter(
    'log_entries_total',
    'Total number of log entries',
    ['level', 'logger']
)

# 响应时间直方图
request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method', 'status']
)

# 错误率计量器
error_rate = Gauge(
    'error_rate',
    'Current error rate',
    ['service']
)
```

## 🛡️ 日志安全和合规

### 敏感信息脱敏
```python
# src/core/sanitizer.py
import re
from typing import Any, Dict

class LogSanitizer:
    SENSITIVE_PATTERNS = {
        'password': re.compile(r'"password":\s*"[^"]*"'),
        'token': re.compile(r'"token":\s*"[^"]*"'),
        'api_key': re.compile(r'"api_key":\s*"[^"]*"'),
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
    }

    @classmethod
    def sanitize_log_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏日志数据中的敏感信息"""
        sanitized = data.copy()

        for field in ['password', 'token', 'api_key']:
            if field in sanitized:
                sanitized[field] = '***MASKED***'

        return sanitized
```

### 访问控制
```yaml
# elasticsearch.yml
xpack.security.enabled: true
xpack.security.authc:
  realms:
    native:
      native1:
        order: 0

# kibana.yml
elasticsearch.username: "kibana_user"
elasticsearch.password: "${KIBANA_PASSWORD}"
```

## 📊 日志仪表盘模板

### Kibana 仪表盘组件

#### 1. 系统概览
- 日志总量趋势
- 错误率变化
- 响应时间分布
- 活跃用户数

#### 2. 错误分析
- 错误类型分布
- 错误发生频率
- 异常堆栈分析
- 受影响用户统计

#### 3. 性能监控
- 接口响应时间
- 数据库查询耗时
- 缓存命中率
- 资源使用情况

#### 4. 业务监控
- 预测请求量
- 数据采集状态
- 用户活跃度
- 功能使用统计

### Grafana 日志面板
```json
{
  "dashboard": {
    "title": "Football Prediction Logs",
    "panels": [
      {
        "title": "Log Volume",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(loki_log_entries_total[5m]))",
            "legendFormat": "Logs/sec"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate({service=\"football-prediction\"} |= \"ERROR\" [5m])",
            "legendFormat": "Errors/sec"
          }
        ]
      }
    ]
  }
}
```

## 🚀 部署和维护

### 容器化部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

# 创建日志目录
RUN mkdir -p /app/logs
VOLUME ["/app/logs"]

# 日志轮转配置
COPY logrotate.conf /etc/logrotate.d/app
```

### 日志轮转配置
```bash
# logrotate.conf
/app/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        /bin/kill -USR1 `cat /var/run/app.pid 2> /dev/null` 2> /dev/null || true
    endscript
}
```

### 监控脚本
```bash
#!/bin/bash
# scripts/log_health_check.sh

LOG_DIR="/app/logs"
MAX_LOG_AGE=300  # 5分钟

# 检查日志文件是否存在和新鲜度
if [ ! -f "$LOG_DIR/app.log" ]; then
    echo "ERROR: app.log not found"
    exit 1
fi

LAST_MODIFIED=$(stat -f "%m" "$LOG_DIR/app.log" 2>/dev/null || stat -c "%Y" "$LOG_DIR/app.log")
CURRENT_TIME=$(date +%s)
AGE=$((CURRENT_TIME - LAST_MODIFIED))

if [ $AGE -gt $MAX_LOG_AGE ]; then
    echo "WARNING: app.log is too old (${AGE}s)"
    exit 1
fi

echo "OK: Logs are healthy"
```

## 📞 故障排查指南

### 常见问题

#### 1. 日志丢失
```bash
# 检查磁盘空间
df -h /app/logs

# 检查文件权限
ls -la /app/logs/

# 检查进程是否运行
ps aux | grep filebeat
```

#### 2. 日志格式错误
```bash
# 验证JSON格式
tail -n 10 /app/logs/app.log | jq .

# 检查Logstash处理
curl -X GET "elasticsearch:9200/_cat/indices/football-logs-*"
```

#### 3. 搜索性能问题
```bash
# 检查Elasticsearch集群状态
curl -X GET "elasticsearch:9200/_cluster/health"

# 优化查询
curl -X POST "elasticsearch:9200/football-logs-*/_forcemerge"
```

---

**注意**: 根据实际环境调整配置参数，定期审查日志策略以适应业务变化。