# 监控告警设置指南

## 概述

FootballPrediction 系统采用 Prometheus + Grafana + AlertManager 的完整监控告警体系，提供全面的系统和业务指标监控。

## 🏗️ 架构组件

### 核心组件
- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化仪表盘
- **AlertManager**: 告警路由和通知
- **各类 Exporter**: 系统和应用指标导出

### 已配置的监控目标
- ✅ **应用服务** (`app:8000`) - FastAPI 应用指标
- ✅ **PostgreSQL** (`postgres-exporter:9187`) - 数据库性能指标
- ✅ **Redis** (`redis-exporter:9121`) - 缓存性能指标
- ✅ **MinIO** (`minio:9000`) - 对象存储指标
- ✅ **系统资源** (`node-exporter:9100`) - CPU、内存、磁盘等
- ✅ **Prometheus 自身** (`localhost:9090`) - 监控系统健康

## 📊 关键监控指标

### 1. 应用层指标
```prometheus
# HTTP 请求指标
http_requests_total{job="football-app"}
http_request_duration_seconds{job="football-app"}
http_requests_in_flight{job="football-app"}

# 业务指标
prediction_requests_total
data_collection_success_rate
model_prediction_accuracy
feature_calculation_duration_seconds
```

### 2. 数据库指标
```prometheus
# 连接和性能
pg_up{job="postgres"}
pg_stat_database_tup_inserted{job="postgres"}
pg_stat_database_tup_updated{job="postgres"}
pg_locks_count{job="postgres"}

# 查询性能
pg_stat_statements_mean_exec_time{job="postgres"}
pg_stat_statements_calls{job="postgres"}
```

### 3. 系统资源指标
```prometheus
# CPU 使用率
node_cpu_seconds_total{job="node"}
# 内存使用
node_memory_MemAvailable_bytes{job="node"}
# 磁盘空间
node_filesystem_avail_bytes{job="node"}
```

## 🚨 告警规则配置

### 现有告警规则
已在 `monitoring/prometheus/rules/football_alerts.yml` 中配置：

#### 应用级告警
- **应用宕机**: 5分钟内无响应
- **响应时间异常**: P95 响应时间 > 2秒
- **错误率过高**: 5分钟内错误率 > 5%
- **预测服务异常**: 预测请求失败率 > 10%

#### 基础设施告警
- **数据库连接失败**: PostgreSQL 不可用
- **缓存服务异常**: Redis 连接失败
- **磁盘空间不足**: 可用空间 < 10%
- **内存使用过高**: 内存使用率 > 90%

#### 业务告警
- **数据采集失败**: 数据采集成功率 < 80%
- **模型预测异常**: 预测准确率下降 > 20%
- **特征计算超时**: 特征计算时间 > 5秒

### 告警级别定义
- **Critical**: 需要立即响应，影响核心功能
- **Warning**: 需要关注，可能影响性能
- **Info**: 信息性告警，用于趋势分析

## 📧 告警通知配置

### 接收器配置
```yaml
# 已配置的接收器
receivers:
  - default-receiver: admin@example.com
  - critical-alerts: critical-alerts@example.com + Slack
  - data-team: data-team@example.com
  - ops-team: ops-team@example.com
  - dba-team: dba-team@example.com
  - dev-team: dev-team@example.com
```

### 路由规则
- **数据相关**: data_collection, data_processing → data-team
- **运维相关**: scheduler, infrastructure → ops-team
- **数据库相关**: database → dba-team
- **应用相关**: application → dev-team
- **关键告警**: severity=critical → critical-alerts (邮件+Slack)

## 🎯 仪表盘配置

### 现有 Grafana 仪表盘
1. **足球数据仪表盘** (`football_data_dashboard.json`)
   - 数据采集状态
   - API 调用统计
   - 数据质量指标

2. **数据质量仪表盘** (`data_quality_dashboard.json`)
   - 数据完整性检查
   - 异常数据识别
   - 质量趋势分析

3. **预测性能仪表盘** (`prediction_performance_dashboard.json`)
   - 模型准确率
   - 预测延迟
   - 特征重要性

4. **权限审计仪表盘** (`permissions_audit_dashboard.json`)
   - 用户访问统计
   - API 调用审计
   - 安全事件监控

5. **数据异常检测仪表盘** (`data_anomaly_detection_dashboard.json`)
   - 异常数据识别
   - 趋势变化检测
   - 自动异常告警

## 🚀 部署和启动

### 1. 完整监控栈启动
```bash
# 启动所有监控组件
docker-compose -f docker-compose.yml up -d prometheus grafana alertmanager

# 验证服务状态
curl http://localhost:9090/targets  # Prometheus targets
curl http://localhost:3000         # Grafana (admin/admin)
curl http://localhost:9093         # AlertManager
```

### 2. 配置验证
```bash
# 检查 Prometheus 配置
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml

# 检查告警规则
docker-compose exec prometheus promtool check rules /etc/prometheus/rules/football_alerts.yml

# 检查 AlertManager 配置
docker-compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

### 3. 指标验证
```bash
# 验证应用指标
curl http://localhost:8000/metrics | grep -E "(http_requests|prediction_)"

# 验证数据库指标
curl http://localhost:9187/metrics | grep pg_up

# 验证系统指标
curl http://localhost:9100/metrics | grep node_cpu
```

## 🔧 自定义配置

### 添加新的监控目标
编辑 `monitoring/prometheus/prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'new-service'
    static_configs:
      - targets: ['new-service:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 添加新的告警规则
在 `monitoring/prometheus/rules/` 目录下创建新的 `.yml` 文件:
```yaml
groups:
  - name: custom_alerts
    rules:
      - alert: CustomAlert
        expr: custom_metric > 100
        for: 5m
        labels:
          severity: warning
          component: custom
        annotations:
          summary: "Custom metric is high"
          description: "Custom metric has been above 100 for more than 5 minutes"
```

### 配置新的通知渠道
编辑 `monitoring/alertmanager/alertmanager.yml`:
```yaml
receivers:
  - name: 'custom-receiver'
    webhook_configs:
      - url: 'http://your-webhook-url'
        send_resolved: true
```

## 📱 移动端访问

### Grafana 移动应用
- 下载 Grafana Mobile App
- 配置服务器地址: `http://your-domain:3000`
- 使用现有用户凭据登录

### 告警通知集成
- **Slack**: 已配置关键告警推送
- **邮件**: 支持 HTML 格式告警邮件
- **短信**: 可通过 webhook 集成短信服务
- **微信**: 可通过企业微信 webhook 集成

## 🔍 故障排查

### 常见问题

#### Prometheus 无法采集指标
```bash
# 检查目标状态
curl http://localhost:9090/api/v1/targets

# 检查网络连接
docker-compose exec prometheus wget -qO- http://app:8000/metrics

# 查看错误日志
docker-compose logs prometheus
```

#### AlertManager 不发送告警
```bash
# 检查告警状态
curl http://localhost:9093/api/v1/alerts

# 测试邮件配置
docker-compose exec alertmanager amtool config routes test

# 查看发送日志
docker-compose logs alertmanager
```

#### Grafana 仪表盘无数据
```bash
# 检查数据源连接
curl -u admin:admin http://localhost:3000/api/datasources

# 验证查询语句
curl "http://localhost:9090/api/v1/query?query=up"

# 检查时间范围设置
```

### 性能优化

#### Prometheus 存储优化
```yaml
# prometheus.yml
global:
  scrape_interval: 30s  # 根据需求调整采集频率
  evaluation_interval: 30s

# 存储保留策略
storage:
  tsdb:
    retention.time: 30d  # 根据磁盘空间调整
    retention.size: 50GB
```

#### 告警降噪
```yaml
# alertmanager.yml
route:
  group_wait: 30s      # 增加等待时间
  group_interval: 5m   # 增加分组间隔
  repeat_interval: 4h  # 减少重复告警频率
```

## 📈 监控最佳实践

### 1. 指标设计原则
- **USE 方法**: Utilization(使用率), Saturation(饱和度), Errors(错误)
- **RED 方法**: Rate(请求率), Errors(错误率), Duration(延迟)
- **四个黄金信号**: 延迟、流量、错误、饱和度

### 2. 告警设计原则
- **减少噪音**: 避免过多不重要的告警
- **分级处理**: 根据严重程度分级响应
- **上下文信息**: 提供足够的故障排查信息
- **自愈机制**: 配置自动恢复逻辑

### 3. 仪表盘设计原则
- **分层展示**: 从高层概览到详细指标
- **关联分析**: 相关指标放在同一视图
- **历史对比**: 提供时间序列对比功能
- **交互式过滤**: 支持动态筛选和钻取

## 📞 支持和维护

### 定期维护任务
- **每周**: 检查告警配置，清理过期指标
- **每月**: 评估存储使用，优化查询性能
- **每季度**: 审查监控指标，更新告警阈值

### 紧急联系方式
- **监控系统故障**: ops-team@example.com
- **告警配置问题**: admin@example.com
- **性能调优需求**: performance-team@example.com

---

**注意**: 请根据实际部署环境更新配置文件中的邮件地址、Slack webhook 等信息。