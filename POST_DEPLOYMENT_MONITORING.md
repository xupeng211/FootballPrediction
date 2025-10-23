# 上线后监控指南
# Post-Deployment Monitoring Guide

## 🎯 概述

本文档详细描述了足球预测系统上线后的监控策略，确保系统在运行过程中的稳定性、性能和安全性。

## 📊 监控体系架构

### 监控层级
```
┌─────────────────────────────────────────────────────────┐
│                 业务监控层                               │
│  • API调用统计  • 用户行为  • 预测准确率  • 业务指标      │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                 应用监控层                               │
│  • 响应时间  • 错误率  • 吞吐量  • 应用健康状态           │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                 基础设施监控层                            │
│  • CPU/内存  • 磁盘/网络  • 数据库  • 缓存              │
└─────────────────────────────────────────────────────────┘
```

### 监控工具栈
- **指标收集**: Prometheus + Node Exporter
- **可视化**: Grafana
- **日志聚合**: Loki + Promtail
- **告警**: AlertManager
- **链路追踪**: Jaeger (可选)
- **健康检查**: 自定义健康检查端点

## 🔍 关键性能指标 (KPI)

### 1. 系统可用性指标

#### 服务可用性
- **服务在线率**: > 99.9%
- **健康检查成功率**: > 99.5%
- **平均故障恢复时间 (MTTR)**: < 15分钟

#### 监控配置
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'health-check'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/health'
    scrape_interval: 30s
    scrape_timeout: 10s
```

### 2. 性能指标

#### API性能
| 指标 | 目标值 | 告警阈值 | 说明 |
|------|--------|----------|------|
| P95响应时间 | < 500ms | > 1s | 95%的请求响应时间 |
| P99响应时间 | < 1s | > 2s | 99%的请求响应时间 |
| 平均响应时间 | < 200ms | > 500ms | 所有请求平均响应时间 |
| 请求吞吐量 | > 100 RPS | < 50 RPS | 每秒请求数 |
| 错误率 | < 1% | > 5% | HTTP 5xx错误率 |

#### 数据库性能
| 指标 | 目标值 | 告警阈值 | 说明 |
|------|--------|----------|------|
| 查询响应时间 | < 100ms | > 500ms | 数据库查询平均时间 |
| 连接池使用率 | < 80% | > 90% | 数据库连接池使用率 |
| 慢查询数量 | < 5/小时 | > 20/小时 | 执行时间>1秒的查询 |
| 数据库CPU使用率 | < 70% | > 85% | 数据库服务器CPU使用率 |

### 3. 业务指标

#### 预测业务指标
| 指标 | 目标值 | 告警阈值 | 说明 |
|------|--------|----------|------|
| 预测API调用成功率 | > 99% | < 95% | 预测接口调用成功率 |
| 预测响应时间 | < 300ms | > 1s | 预测计算响应时间 |
| 每日预测数量 | > 1000 | < 500 | 每日生成的预测数量 |
| 预测准确率 | > 85% | < 75% | 预测结果准确率 |

#### 用户行为指标
| 指标 | 目标值 | 告警阈值 | 说明 |
|------|--------|----------|------|
| 活跃用户数 | 持续增长 | 下降20% | 日活跃用户数 |
| API调用频率 | 稳定 | 异常波动 | 用户API调用模式 |
| 用户会话时长 | > 5分钟 | < 2分钟 | 用户平均使用时长 |

## 📈 监控仪表板配置

### 1. 系统概览仪表板

#### 主要图表
- **系统总览**: CPU、内存、磁盘、网络使用率
- **服务状态**: 各服务运行状态和健康检查结果
- **请求流量**: 实时请求数量和响应时间趋势
- **错误率**: HTTP错误状态码分布和趋势

#### Grafana面板配置
```json
{
  "dashboard": {
    "title": "足球预测系统 - 系统概览",
    "panels": [
      {
        "title": "API响应时间",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95响应时间"
          }
        ]
      },
      {
        "title": "请求成功率",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status!~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "legendFormat": "成功率"
          }
        ]
      }
    ]
  }
}
```

### 2. 应用性能仪表板

#### 关键指标
- **API性能**: 各端点响应时间和吞吐量
- **错误分析**: 错误类型分布和趋势
- **数据库性能**: 查询性能和连接池状态
- **缓存命中率**: Redis缓存性能指标

### 3. 业务指标仪表板

#### 业务相关图表
- **预测统计**: 每日预测数量和准确率趋势
- **用户活跃度**: 活跃用户数和使用模式
- **数据质量**: 数据同步状态和质量指标
- **模型性能**: ML模型预测性能趋势

## 🚨 告警配置

### 1. 告警规则定义

#### 系统级告警
```yaml
# alert_rules.yml
groups:
  - name: system_alerts
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU使用率过高"
          description: "CPU使用率 {{ $value }}% 超过阈值"

      - alert: HighMemoryUsage
        expr: memory_usage_percent > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率 {{ $value }}% 超过阈值"

      - alert: DiskSpaceLow
        expr: disk_usage_percent > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "磁盘空间不足"
          description: "磁盘使用率 {{ $value }}% 超过阈值"
```

#### 应用级告警
```yaml
  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100 > 5
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "API错误率过高"
          description: "5分钟内API错误率 {{ $value }}% 超过阈值"

      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API响应时间过长"
          description: "P95响应时间 {{ $value }}s 超过阈值"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服务宕机"
          description: "服务 {{ $labels.instance }} 已宕机"
```

#### 业务级告警
```yaml
  - name: business_alerts
    rules:
      - alert: LowPredictionAccuracy
        expr: prediction_accuracy_rate < 75
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "预测准确率下降"
          description: "预测准确率 {{ $value }}% 低于阈值"

      - alert: DataSyncFailure
        expr: data_sync_status != 1
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "数据同步失败"
          description: "数据同步服务异常"
```

### 2. 告警通知配置

#### AlertManager配置
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@example.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'team@example.com'
        subject: '[足球预测系统] {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          告警: {{ .Annotations.summary }}
          描述: {{ .Annotations.description }}
          时间: {{ .StartsAt }}
          {{ end }}

    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: '足球预测系统告警'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### 3. 告警级别和处理

#### 告警级别定义
- **Critical (P0)**: 系统宕机、数据丢失、安全事件 - 5分钟内响应
- **Warning (P1)**: 性能下降、错误率上升 - 15分钟内响应
- **Info (P2)**: 指标异常、配置变更 - 1小时内响应

#### 告警处理流程
1. **告警触发** → 系统自动发送通知
2. **初步评估** → 值班人员评估影响范围
3. **问题定位** → 使用监控工具定位问题
4. **紧急处理** → 执行应急预案或临时修复
5. **根本解决** → 找到根本原因并彻底解决
6. **事后分析** → 编写事故报告和改进方案

## 📋 监控检查清单

### 日常监控 (每日)
- [ ] 检查系统可用性报告
- [ ] 查看关键性能指标趋势
- [ ] 确认告警规则正常工作
- [ ] 检查数据备份状态
- [ ] 查看用户反馈和错误报告

### 周期性监控 (每周)
- [ ] 分析性能趋势和容量规划
- [ ] 检查监控覆盖范围完整性
- [ ] 更新告警阈值和规则
- [ ] 清理过期监控数据和日志
- [ ] 进行监控系统维护

### 月度监控 (每月)
- [ ] 生成月度性能报告
- [ ] 评估监控体系效果
- [ ] 优化监控配置和仪表板
- [ ] 更新监控文档和流程
- [ ] 进行监控系统演练

## 🔧 监控工具使用

### 1. Prometheus查询示例

#### 常用PromQL查询
```promql
# API响应时间P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 错误率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# 请求吞吐量
rate(http_requests_total[5m])

# 数据库连接数
pg_stat_database_numbackends

# CPU使用率
100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

### 2. Grafana仪表板模板

#### 导入模板
```bash
# 导入系统监控模板
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/system-overview.json

# 导入应用监控模板
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/application-performance.json
```

### 3. 日志查询和分析

#### Loki查询示例
```logql
# 查询应用错误日志
{app="football-prediction"} |= "ERROR" | level != "debug"

# 查询特定时间段内的慢请求
{app="football-prediction"} |= "slow" |= "timeout"

# 统计错误类型
count by (level) ({app="football-prediction"} |= "ERROR")
```

## 📊 监控报告

### 1. 日报模板
```markdown
# 系统监控日报 - YYYY-MM-DD

## 系统概览
- 可用性: 99.9%
- 平均响应时间: 250ms
- 错误率: 0.5%
- 请求数量: 50,000

## 性能指标
- CPU平均使用率: 45%
- 内存平均使用率: 60%
- 磁盘使用率: 35%

## 告警统计
- Critical告警: 0
- Warning告警: 2
- Info告警: 5

## 异常事件
[描述当天发生的异常事件和处理结果]

## 明日关注重点
[列出明天需要重点关注的指标和事项]
```

### 2. 周报和月报
- 性能趋势分析
- 容量规划建议
- 系统优化方案
- 监控改进计划

---

*最后更新: 2025-10-22*