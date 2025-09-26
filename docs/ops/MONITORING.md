# 数据质量监控与告警机制

本文档描述了足球预测系统的数据质量监控和告警机制的设计与实现。

## 概述

数据质量监控系统确保系统中的数据保持高质量、高可用性，并在数据出现问题时及时发出告警。系统包含三个核心组件：

- **质量监控器** (`quality_monitor.py`) - 监控数据新鲜度、完整性和一致性
- **异常检测器** (`anomaly_detector.py`) - 基于统计学方法检测数据异常
- **告警管理器** (`alert_manager.py`) - 管理告警规则和发送告警通知

## 质量监控 (Quality Monitor)

### 监控维度

#### 1. 数据新鲜度 (Data Freshness)
监控数据的最后更新时间，确保数据及时性：

```python
freshness_thresholds = {
    "matches": 24,      # 比赛数据24小时内更新
    "odds": 1,          # 赔率数据1小时内更新
    "predictions": 2,   # 预测数据2小时内更新
    "teams": 168,       # 球队数据1周内更新
    "leagues": 720      # 联赛数据1月内更新
}
```

#### 2. 数据完整性 (Data Completeness)
检查关键字段的缺失情况：

```python
critical_fields = {
    "matches": ["home_team_id", "away_team_id", "league_id", "match_time"],
    "odds": ["match_id", "bookmaker", "home_odds", "away_odds"],
    "predictions": ["match_id", "model_name", "home_win_probability"]
}
```

#### 3. 数据一致性 (Data Consistency)
验证数据间的关联关系：

- **外键一致性**: 检查matches表中的team_id是否在teams表中存在
- **赔率一致性**: 验证赔率数据的合理性（和值接近1，范围合理）
- **比赛状态一致性**: 确保比赛状态转换的逻辑正确性

### 质量评分

系统计算综合质量得分（0-1），基于以下权重：
- 数据新鲜度: 40%
- 数据完整性: 35%
- 数据一致性: 25%

质量等级划分：
- **优秀** (0.9-1.0): 数据质量极佳
- **良好** (0.8-0.9): 数据质量良好
- **一般** (0.7-0.8): 数据质量一般，需要注意
- **较差** (0.6-0.7): 数据质量较差，需要改进
- **很差** (0.0-0.6): 数据质量很差，需要紧急处理

## 异常检测 (Anomaly Detection)

### 检测方法

#### 1. 3σ规则检测
基于正态分布的异常检测：
```python
lower_bound = mean - 3 * std
upper_bound = mean + 3 * std
```

#### 2. IQR方法检测
基于四分位距的异常检测：
```python
Q1 = data.quantile(0.25)
Q3 = data.quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
```

#### 3. Z-score分析
计算标准化得分识别异常：
```python
z_scores = abs((data - mean) / std)
outliers = data[z_scores > threshold]
```

#### 4. 范围检查
基于业务规则的范围验证：
```python
thresholds = {
    "home_odds": {"min": 1.01, "max": 100.0},
    "home_score": {"min": 0, "max": 20},
    "minute": {"min": 0, "max": 120}
}
```

#### 5. 频率分布检测
检测分类数据的频率异常：
```python
# 检测频率过高或过低的值
expected_freq = total_count / unique_values
anomalous = count > expected_freq * 5 or count < expected_freq * 0.1
```

#### 6. 时间间隔检测
检测时间序列数据的间隔异常：
```python
time_diffs = time_data.diff().dt.total_seconds()
# 使用IQR方法检测异常间隔
```

### 异常类型

- **OUTLIER**: 离群值
- **TREND_CHANGE**: 趋势变化
- **PATTERN_BREAK**: 模式中断
- **VALUE_RANGE**: 数值范围异常
- **FREQUENCY**: 频率异常
- **NULL_SPIKE**: 空值激增

### 严重程度

- **LOW**: 轻微异常，可以忽略
- **MEDIUM**: 中等异常，需要关注
- **HIGH**: 严重异常，需要处理
- **CRITICAL**: 关键异常，需要立即处理

## 告警机制 (Alert Management)

### 告警级别

- **INFO**: 信息性告警
- **WARNING**: 警告级别
- **ERROR**: 错误级别
- **CRITICAL**: 关键级别

### 告警渠道

- **LOG**: 日志输出
- **PROMETHEUS**: Prometheus指标
- **WEBHOOK**: Webhook通知
- **EMAIL**: 邮件通知

### 默认告警规则

#### 数据新鲜度告警
```yaml
data_freshness_critical:
  condition: "freshness_hours > 24"
  level: CRITICAL
  throttle: 30分钟

data_freshness_warning:
  condition: "freshness_hours > 12"
  level: WARNING
  throttle: 1小时
```

#### 数据完整性告警
```yaml
data_completeness_critical:
  condition: "completeness_ratio < 0.8"
  level: CRITICAL
  throttle: 15分钟

data_completeness_warning:
  condition: "completeness_ratio < 0.95"
  level: WARNING
  throttle: 30分钟
```

#### 数据质量告警
```yaml
data_quality_critical:
  condition: "quality_score < 0.7"
  level: CRITICAL
  throttle: 15分钟
```

#### 异常检测告警
```yaml
anomaly_critical:
  condition: "anomaly_score > 0.2"
  level: CRITICAL
  throttle: 5分钟

anomaly_warning:
  condition: "anomaly_score > 0.1"
  level: WARNING
  throttle: 10分钟
```

### 告警去重

系统实现告警去重机制，避免重复告警：
- 基于告警ID（标题+来源+标签的hash）去重
- 配置可调的去重时间窗口
- 相同告警在时间窗口内只触发一次

## Prometheus指标

### 数据质量指标

```prometheus
# 数据新鲜度（小时）
data_freshness_hours{table_name="matches"} 2.5

# 数据完整性比例
data_completeness_ratio{table_name="matches"} 0.98

# 数据质量得分
data_quality_score{table_name="matches"} 0.92
```

### 异常检测指标

```prometheus
# 检测到的异常总数
anomalies_detected_total{table_name="odds",column_name="home_odds",anomaly_type="outlier",severity="high"} 5

# 异常得分
anomaly_score{table_name="odds",column_name="home_odds"} 0.15
```

### 告警指标

```prometheus
# 触发的告警总数
alerts_fired_total{level="critical",source="quality_monitor",rule_id="data_freshness_critical"} 3

# 活跃告警数
active_alerts{level="critical"} 2

# 监控检查耗时
monitoring_check_duration_seconds{check_type="quality_monitor"} 1.23

# 监控错误总数
monitoring_errors_total{error_type="database_connection"} 1
```

## 使用方法

### 质量监控

```python
from src.monitoring.quality_monitor import QualityMonitor

# 创建监控器
monitor = QualityMonitor()

# 检查数据新鲜度
freshness_results = await monitor.check_data_freshness()

# 检查数据完整性
completeness_results = await monitor.check_data_completeness()

# 检查数据一致性
consistency_results = await monitor.check_data_consistency()

# 计算综合质量得分
quality_score = await monitor.calculate_overall_quality_score()
```

### 异常检测

```python
from src.monitoring.anomaly_detector import AnomalyDetector

# 创建检测器
detector = AnomalyDetector()

# 执行异常检测
anomalies = await detector.detect_anomalies(
    table_names=["matches", "odds"],
    methods=["three_sigma", "iqr", "range_check"]
)

# 获取异常摘要
summary = await detector.get_anomaly_summary(anomalies)
```

### 告警管理

```python
from src.monitoring.alert_manager import AlertManager, AlertLevel

# 创建告警管理器
alert_manager = AlertManager()

# 手动触发告警
alert = alert_manager.fire_alert(
    title="数据异常告警",
    message="检测到赔率数据异常",
    level=AlertLevel.WARNING,
    source="manual",
    labels={"table": "odds"}
)

# 获取活跃告警
active_alerts = alert_manager.get_active_alerts()

# 解决告警
alert_manager.resolve_alert(alert.alert_id)
```

### 集成使用

```python
# 完整的监控流程
async def run_monitoring():
    monitor = QualityMonitor()
    detector = AnomalyDetector()
    alert_manager = AlertManager()

    # 1. 质量监控
    quality_data = {
        "freshness": await monitor.check_data_freshness(),
        "completeness": await monitor.check_data_completeness(),
        "consistency": await monitor.check_data_consistency()
    }

    # 2. 异常检测
    anomalies = await detector.detect_anomalies()

    # 3. 更新指标
    alert_manager.update_quality_metrics(quality_data)
    alert_manager.update_anomaly_metrics(anomalies)

    # 4. 检查并触发告警
    quality_alerts = alert_manager.check_and_fire_quality_alerts(quality_data)
    anomaly_alerts = alert_manager.check_and_fire_anomaly_alerts(anomalies)

    return {
        "quality_data": quality_data,
        "anomalies": len(anomalies),
        "alerts_fired": len(quality_alerts) + len(anomaly_alerts)
    }
```

## 配置说明

### 监控配置

在 `quality_monitor.py` 中配置：

```python
# 新鲜度阈值（小时）
freshness_thresholds = {
    "matches": 24,
    "odds": 1,
    "predictions": 2
}

# 关键字段
critical_fields = {
    "matches": ["home_team_id", "away_team_id", "league_id"],
    "odds": ["match_id", "bookmaker", "home_odds"]
}
```

### 异常检测配置

在 `anomaly_detector.py` 中配置：

```python
detection_config = {
    "matches": {
        "numeric_columns": ["home_score", "away_score"],
        "thresholds": {
            "home_score": {"min": 0, "max": 20}
        }
    }
}
```

### 告警配置

在 `alert_manager.py` 中配置：

```python
# 添加自定义告警规则
alert_manager.add_rule(AlertRule(
    rule_id="custom_rule",
    name="自定义告警",
    condition="custom_condition",
    level=AlertLevel.WARNING,
    channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
    throttle_seconds=600
))

# 注册自定义处理器
def custom_handler(alert):
    # 自定义处理逻辑
    pass

alert_manager.register_handler(AlertChannel.WEBHOOK, custom_handler)
```

## 最佳实践

### 1. 监控频率
- 数据新鲜度: 每30分钟检查一次
- 数据完整性: 每小时检查一次
- 异常检测: 每2小时检查一次

### 2. 告警管理
- 设置合理的去重时间，避免告警风暴
- 区分不同级别的告警处理方式
- 定期清理已解决的告警

### 3. 指标监控
- 使用Grafana可视化Prometheus指标
- 设置仪表板监控系统健康状态
- 配置告警规则自动处理异常

### 4. 性能优化
- 限制监控查询的数据量
- 使用异步处理提高性能
- 合理配置数据库索引

## 故障排除

### 常见问题

1. **监控超时**
   - 检查数据库连接
   - 优化查询性能
   - 增加超时配置

2. **异常检测误报**
   - 调整检测阈值
   - 排除已知的正常异常
   - 使用多种方法交叉验证

3. **告警过多**
   - 增加去重时间
   - 调整告警阈值
   - 优化告警规则

4. **指标不更新**
   - 检查Prometheus配置
   - 验证指标标签
   - 重启监控服务

### 日志查看

```bash
# 查看监控日志
tail -f logs/monitoring.log

# 查看告警日志
grep "ALERT" logs/app.log

# 查看异常检测日志
grep "anomaly" logs/monitoring.log
```

## 扩展开发

### 添加新的监控维度

1. 在 `QualityMonitor` 中添加新的检查方法
2. 更新配置文件
3. 添加相应的Prometheus指标
4. 配置告警规则

### 集成新的告警渠道

1. 在 `AlertChannel` 枚举中添加新渠道
2. 实现对应的处理器函数
3. 注册处理器到 `AlertManager`
4. 更新告警规则配置

### 自定义异常检测算法

1. 在 `AnomalyDetector` 中添加新的检测方法
2. 定义新的异常类型
3. 更新检测配置
4. 添加测试用例

这个监控系统为足球预测系统提供了全面的数据质量保障，确保系统数据的准确性、及时性和可靠性。
