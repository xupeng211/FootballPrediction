# Week 1 监控系统培训材料
# 基础设施监控培训 - FootballPrediction项目

---

## 📚 培训大纲

### 🎯 培训目标
- 掌握Prometheus监控系统的使用
- 熟练使用Grafana进行数据可视化
- 理解告警系统的配置和处理
- 掌握基础设施监控的最佳实践

### 👥 培训对象
- DevOps工程师
- 后端开发工程师
- QA工程师
- 项目经理

### ⏰ 培训时长
- 总时长: 4小时
- 理论培训: 2小时
- 实践操作: 2小时

---

## 📖 第一部分: 监控系统概述 (30分钟)

### 🎯 什么是监控？

监控是系统性的观测、收集、分析和报告系统运行状态的过程。

#### 监控的核心价值
1. **问题发现** - 及时发现系统异常
2. **性能分析** - 分析系统性能瓶颈
3. **容量规划** - 为系统扩容提供数据支持
4. **故障定位** - 快速定位问题根因
5. **业务洞察** - 了解业务运行状况

### 🏗️ 监控系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   FootballPrediction监控架构              │
├─────────────────────────────────────────────────────────┤
│  📊 Grafana (可视化层)                                   │
│  ├─ 系统概览仪表板                                        │
│  ├─ 应用性能仪表板                                        │
│  └─ 业务指标仪表板                                        │
├─────────────────────────────────────────────────────────┤
│  🔔 AlertManager (告警层)                               │
│  ├─ 告警规则引擎                                          │
│  ├─ 通知渠道管理                                          │
│  └─ 告警升级策略                                          │
├─────────────────────────────────────────────────────────┤
│  📈 Prometheus (指标收集层)                              │
│  ├─ 应用指标收集                                          │
│  ├─ 系统指标收集                                          │
│  └─ 指标聚合计算                                          │
├─────────────────────────────────────────────────────────┤
│  🖥️ Node Exporter (系统监控)                             │
│  ├─ CPU、内存、磁盘监控                                   │
│  ├─ 网络指标监控                                          │
│  └─ 系统负载监控                                          │
├─────────────────────────────────────────────────────────┤
│  🐳 cAdvisor (容器监控)                                  │
│  ├─ 容器资源监控                                          │
│  ├─ 容器网络监控                                          │
│  └─ 容器生命周期监控                                      │
└─────────────────────────────────────────────────────────┘
```

### 📊 监控指标分类

#### 1. 基础设施指标
- **CPU使用率**: 系统CPU资源使用情况
- **内存使用率**: 系统内存资源使用情况
- **磁盘使用率**: 磁盘空间使用情况
- **网络流量**: 网络IO数据传输情况
- **系统负载**: 系统平均负载情况

#### 2. 应用性能指标
- **响应时间**: API请求响应时间
- **吞吐量**: 单位时间处理的请求数
- **错误率**: 请求失败的比例
- **并发连接数**: 同时处理的连接数量
- **队列长度**: 待处理任务队列长度

#### 3. 业务指标
- **用户活跃度**: 活跃用户数量
- **预测请求量**: 预测API调用次数
- **预测准确率**: 预测结果的准确性
- **数据质量**: 数据完整性和准确性

---

## 📖 第二部分: Prometheus深度解析 (45分钟)

### 🎯 Prometheus简介

Prometheus是一个开源的监控系统，具有以下特点：
- **时间序列数据库**: 专门存储时序数据
- **多维度数据模型**: 使用标签标识数据
- **灵活的查询语言**: PromQL强大查询能力
- **高效的存储**: 本地存储和远程存储
- **简单的部署**: 单一二进制文件

### 🏗️ Prometheus核心概念

#### 1. 指标 (Metrics)
```yaml
# 指标名称和标签
http_requests_total{method="GET",endpoint="/api/v1/predict"} 1024

# 指标类型
- Counter: 计数器 (只增不减)
- Gauge: 仪表盘 (可增可减)
- Histogram: 直方图 (分布统计)
- Summary: 摘要 (分布统计)
```

#### 2. 标签 (Labels)
```yaml
# 标签用于区分和过滤数据
http_requests_total{
  method="GET",           # HTTP方法
  endpoint="/api/v1/predict",  # API端点
  status="200",           # 响应状态
  instance="10.0.1.100:8000"   # 实例地址
}
```

#### 3. PromQL查询语言
```promql
# 基础查询
http_requests_total                    # 所有HTTP请求数

# 标签过滤
http_requests_total{method="GET"}      # GET请求数

# 聚合操作
sum(http_requests_total)               # 总请求数
avg(http_requests_total)               # 平均请求数

# 时间序列计算
rate(http_requests_total[5m])          # 5分钟内请求速率
increase(http_requests_total[1h])      # 1小时内增量

# 多维度聚合
sum by (endpoint) (http_requests_total)  # 按端点聚合
```

### 🔧 Prometheus配置详解

#### 1. 全局配置
```yaml
global:
  scrape_interval: 15s      # 抓取间隔
  evaluation_interval: 15s  # 规则评估间隔
  external_labels:          # 外部标签
    cluster: 'football-prediction'
    environment: 'production'
```

#### 2. 抓取配置
```yaml
scrape_configs:
  - job_name: 'football-api'
    static_configs:
      - targets: ['football-api-service:8000']
    metrics_path: /metrics
    scrape_interval: 30s
    scrape_timeout: 10s
```

#### 3. 告警规则配置
```yaml
rule_files:
  - "alert_rules.yml"

# 告警规则示例
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API错误率过高"
```

### 📊 实践演示

#### 演示1: Prometheus Web界面
1. 访问 http://localhost:9090
2. 查看 Targets 页面
3. 执行 PromQL 查询
4. 查看告警状态

#### 演示2: 指标查询练习
```promql
# 练习1: 查看所有up指标
up

# 练习2: 查看CPU使用率
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 练习3: 查看内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 练习4: 查看API错误率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

---

## 📖 第三部分: Grafana可视化实战 (45分钟)

### 🎯 Grafana简介

Grafana是一个开源的可视化平台，特点：
- **丰富的数据源支持**: Prometheus, InfluxDB, Elasticsearch等
- **强大的仪表板功能**: 灵活的图表和面板
- **告警集成**: 支持多种告警通知
- **用户权限管理**: 完整的权限控制
- **插件生态**: 丰富的第三方插件

### 🏗️ Grafana核心概念

#### 1. 数据源 (Data Sources)
```yaml
# Prometheus数据源配置
{
  "name": "Prometheus",
  "type": "prometheus",
  "url": "http://prometheus:9090",
  "access": "proxy",
  "isDefault": true
}
```

#### 2. 仪表板 (Dashboards)
- **面板 (Panels)**: 显示单个图表
- **行 (Rows)**: 组织面板布局
- **变量 (Variables)**: 动态参数化
- **注释 (Annotations)**: 事件标记

#### 3. 图表类型
- **时间序列图**: 显示趋势变化
- **统计图表**: 显示分布情况
- **表格**: 显示详细数据
- **热力图**: 显示密度分布
- **仪表盘**: 显示关键指标

### 🎨 仪表板设计最佳实践

#### 1. 布局设计
```
┌─────────────────────────────────────────────────┐
│                系统概览仪表板                    │
├─────────────────────────────────────────────────┤
│  关键指标 (单值图)        │  趋势图 (时间序列)   │
├─────────────────────────────────────────────────┤
│  系统资源使用 (多图表)    │  告警状态 (表格)     │
├─────────────────────────────────────────────────┤
│  API性能指标 (详细图表)   │  日志摘要 (列表)     │
└─────────────────────────────────────────────────┘
```

#### 2. 颜色编码
- **绿色**: 正常状态
- **黄色**: 警告状态
- **红色**: 严重问题
- **蓝色**: 信息提示
- **灰色**: 未知状态

#### 3. 交互设计
- **缩放功能**: 支持时间范围调整
- **钻取功能**: 支持数据深入分析
- **筛选功能**: 支持标签过滤
- **导出功能**: 支持图表和数据导出

### 📊 实践演示

#### 演示1: 创建第一个仪表板
1. 登录Grafana (admin/admin123)
2. 创建新仪表板
3. 添加第一个面板
4. 配置查询和显示选项

#### 演示2: 系统监控仪表板
```json
{
  "title": "系统概览",
  "panels": [
    {
      "title": "CPU使用率",
      "type": "stat",
      "targets": [
        {
          "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
        }
      ]
    }
  ]
}
```

#### 演示3: API性能仪表板
```json
{
  "title": "API性能监控",
  "panels": [
    {
      "title": "请求速率",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}"
        }
      ]
    }
  ]
}
```

### 🎯 实践练习

#### 练习1: 创建系统资源仪表板
1. 创建新仪表板 "系统资源监控"
2. 添加CPU使用率面板
3. 添加内存使用率面板
4. 添加磁盘使用率面板
5. 添加网络流量面板

#### 练习2: 创建应用性能仪表板
1. 创建新仪表板 "API性能监控"
2. 添加请求速率面板
3. 添加响应时间面板
4. 添加错误率面板
5. 添加并发连接数面板

---

## 📖 第四部分: 告警系统配置 (30分钟)

### 🎯 AlertManager简介

AlertManager是Prometheus的告警管理组件，功能：
- **告警路由**: 根据规则分发告警
- **告警分组**: 合并相关告警
- **告警抑制**: 防止告警风暴
- **告警升级**: 分级通知机制
- **多渠道通知**: 邮件、Slack、钉钉等

### 🏗️ 告警系统架构

```
┌─────────────────────────────────────────────────┐
│                   告警处理流程                    │
├─────────────────────────────────────────────────┤
│  Prometheus                                       │
│  ├─ 规则评估                                        │
│  ├─ 告警触发                                        │
│  └─ 发送到AlertManager                             │
├─────────────────────────────────────────────────┤
│  AlertManager                                     │
│  ├─ 告警路由                                        │
│  ├─ 告警分组                                        │
│  ├─ 告警抑制                                        │
│  └─ 通知发送                                        │
├─────────────────────────────────────────────────┤
│  通知渠道                                          │
│  ├─ 邮件通知                                        │
│  ├─ Slack通知                                      │
│  ├─ 钉钉通知                                        │
│  └─ 短信通知                                        │
└─────────────────────────────────────────────────┘
```

### 🔧 告警规则配置

#### 1. 规则定义
```yaml
groups:
  - name: system_alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
          service: system
        annotations:
          summary: "CPU使用率过高"
          description: "实例 {{ $labels.instance }} CPU使用率超过80%"
```

#### 2. 规则类型
- **系统告警**: CPU、内存、磁盘、网络
- **应用告警**: API响应时间、错误率、吞吐量
- **业务告警**: 用户活跃度、预测准确率
- **基础设施告警**: 数据库、缓存、消息队列

#### 3. 告警级别
- **critical**: 严重问题，需要立即处理
- **warning**: 警告问题，需要关注
- **info**: 信息提示，仅供参考

### 📞 通知渠道配置

#### 1. 邮件通知
```yaml
receivers:
  - name: email-alerts
    email_configs:
      - to: 'team@footballprediction.com'
        from: 'alerts@footballprediction.com'
        smarthost: 'smtp.gmail.com:587'
        subject: '[Alert] {{ .GroupLabels.alertname }}'
```

#### 2. Slack通知
```yaml
receivers:
  - name: slack-alerts
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts'
        title: 'FootballPrediction Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### 📊 实践演示

#### 演示1: 创建告警规则
1. 编辑告警规则文件
2. 定义CPU使用率告警
3. 重新加载Prometheus配置
4. 验证告警触发

#### 演示2: 配置邮件通知
1. 配置AlertManager邮件设置
2. 设置SMTP服务器信息
3. 测试邮件发送功能
4. 验证告警通知

---

## 📖 第五部分: 实践操作 (90分钟)

### 🎯 实验环境准备

#### 环境要求
- Docker和Docker Compose已安装
- 监控系统已部署完成
- 网络连接正常
- 足够的系统资源

#### 验证环境
```bash
# 检查容器状态
docker ps

# 检查服务可访问性
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

### 🔬 实践练习

#### 练习1: Prometheus操作 (30分钟)
1. **指标查询练习**
   ```promql
   # 查看所有运行中的实例
   up{job="node-exporter"}

   # 查看CPU使用率
   100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

   # 查看内存使用率
   (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

   # 查看磁盘使用率
   (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
   ```

2. **告警规则创建**
   - 创建高CPU使用率告警
   - 创建高内存使用率告警
   - 创建磁盘空间不足告警

3. **PromQL高级查询**
   - 计算系统负载
   - 分析网络流量
   - 统计API调用次数

#### 练习2: Grafana仪表板创建 (30分钟)
1. **创建系统监控仪表板**
   - 添加CPU使用率单值图
   - 添加内存使用率趋势图
   - 添加磁盘使用率图表
   - 添加网络流量图表

2. **创建应用性能仪表板**
   - 添加API请求速率图表
   - 添加响应时间分布图
   - 添加错误率趋势图
   - 添加并发连接数图表

3. **仪表板美化**
   - 调整颜色主题
   - 设置合理的阈值
   - 添加说明文字
   - 配置自动刷新

#### 练习3: 告警配置 (30分钟)
1. **配置告警规则**
   ```yaml
   # CPU使用率告警
   - alert: HighCPUUsage
     expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: "CPU使用率过高 - {{ $labels.instance }}"
       description: "CPU使用率 {{ $value }}%，超过80%阈值"
   ```

2. **配置通知渠道**
   - 设置邮件通知
   - 配置Slack通知 (可选)
   - 测试告警发送

3. **告警测试**
   - 手动触发告警条件
   - 验证告警通知发送
   - 检查告警内容准确性

---

## 📖 第六部分: 最佳实践和故障排除 (20分钟)

### 🎯 监控最佳实践

#### 1. 指标设计原则
- **有意义**: 指标应该有明确的业务含义
- **可操作**: 指标变化应该能触发相应行动
- **可理解**: 指标名称和标签应该易于理解
- **一致性**: 指标命名应该保持一致性

#### 2. 告警策略设计
- **分级告警**: critical/warning/info三级告警
- **合理阈值**: 基于历史数据和业务需求
- **告警抑制**: 避免告警风暴
- **升级机制**: 确保关键问题及时处理

#### 3. 仪表板设计
- **层次化**: 从概览到详细的多层仪表板
- **关键指标突出**: 重要指标放在显眼位置
- **合理布局**: 相关指标放在一起
- **交互友好**: 支持缩放、钻取等操作

### 🔧 常见故障排除

#### 1. Prometheus问题
**问题**: Prometheus无法抓取指标
```
检查步骤:
1. 确认目标服务是否正常运行
   curl http://target:port/metrics

2. 检查网络连接
   telnet target port

3. 查看Prometheus日志
   docker logs prometheus

4. 检查配置文件语法
   promtool check config prometheus.yml
```

**问题**: 指标数据不完整
```
检查步骤:
1. 确认抓取间隔配置
2. 检查目标服务指标暴露
3. 查看Prometheus存储状态
4. 检查系统资源使用情况
```

#### 2. Grafana问题
**问题**: 数据源连接失败
```
检查步骤:
1. 确认Prometheus服务状态
2. 检查网络连接
3. 验证URL配置
4. 查看Grafana日志
```

**问题**: 图表显示异常
```
检查步骤:
1. 检查PromQL查询语法
2. 确认时间范围设置
3. 验证数据源配置
4. 检查指标标签匹配
```

#### 3. 告警问题
**问题**: 告警不触发
```
检查步骤:
1. 检查告警规则语法
2. 确认指标数据存在
3. 验证阈值设置
4. 查看Prometheus告警状态
```

**问题**: 告警通知发送失败
```
检查步骤:
1. 检查AlertManager配置
2. 验证通知渠道设置
3. 查看AlertManager日志
4. 测试通知渠道连通性
```

### 📚 学习资源

#### 官方文档
- [Prometheus官方文档](https://prometheus.io/docs/)
- [Grafana官方文档](https://grafana.com/docs/)
- [AlertManager配置指南](https://prometheus.io/docs/alerting/latest/alertmanager/)

#### 社区资源
- [Prometheus社区](https://prometheus.io/community/)
- [Grafana社区](https://grafana.com/community/)
- [监控最佳实践博客](https://grafana.com/blog/)

#### 推荐书籍
- 《Prometheus监控实战》
- 《Grafana可视化指南》
- 《云原生监控最佳实践》

---

## 📝 培训总结

### 🎯 培训收获
1. **掌握Prometheus核心概念和使用方法**
2. **熟练使用Grafana创建监控仪表板**
3. **理解告警系统配置和最佳实践**
4. **具备监控系统故障排除能力**

### 📚 后续学习建议
1. **深入学习PromQL查询语言**
2. **探索更多Grafana图表类型**
3. **学习Kubernetes监控方案**
4. **了解APM和分布式追踪**

### 🎯 实践项目
1. **完善现有监控系统**
2. **创建更多业务监控仪表板**
3. **优化告警规则和阈值**
4. **编写监控最佳实践文档**

---

**培训材料版本**: v1.0
**最后更新**: 2025-10-31
**培训讲师**: 监控团队
**联系方式**: monitoring@footballprediction.com