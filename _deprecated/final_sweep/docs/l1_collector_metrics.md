# L1 采集器运维指标定义文档

**版本**: V36.0 Production-Grade
**作者**: ML Architect
**日期**: 2025-12-28
**组件**: `src/api/collectors/production_l1_collector.py`

---

## 📊 指标架构概览

本文档定义了 V36.0 生产级 L1 采集器的完整运维监控体系。

```
┌─────────────────────────────────────────────────────────────────┐
│                    L1 采集器监控指标体系                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 采集指标     │  │ 性能指标     │  │ 可靠性指标   │          │
│  │ Collection   │  │ Performance  │  │ Reliability  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 数据质量指标 │  │ 资源指标     │  │ 业务指标     │          │
│  │ Data Quality │  │ Resource     │  │ Business     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. 采集指标 (Collection Metrics)

**定义**: 衡量数据采集任务的总体完成情况和成功率

### 1.1 总体采集统计

| 指标名称 | 数据类型 | 单位 | 来源 | 说明 |
|---------|---------|------|------|------|
| `l1_collector_total_attempted` | Counter | 场次 | `L1CollectionSummary.total_attempted` | 尝试采集的总比赛数 |
| `l1_collector_total_success` | Counter | 场次 | `L1CollectionSummary.total_success` | 成功采集的比赛数 |
| `l1_collector_total_failed` | Counter | 场次 | `L1CollectionSummary.total_failed` | 采集失败的比赛数 |
| `l1_collector_success_rate` | Gauge | 百分比 | `L1CollectionSummary.success_rate` | 采集成功率 (0-100) |

**计算公式**:
```
success_rate = (total_success / total_attempted) × 100%
```

### 1.2 按联赛统计

| 指标名称 | 标签 (Labels) | 数据类型 | 说明 |
|---------|--------------|---------|------|
| `l1_collector_league_attempted` | `league_id`, `league_name` | Counter | 各联赛尝试采集数 |
| `l1_collector_league_success` | `league_id`, `league_name` | Counter | 各联赛成功采集数 |
| `l1_collector_league_failed` | `league_id`, `league_name` | Counter | 各联赛失败采集数 |
| `l1_collector_league_success_rate` | `league_id`, `league_name` | Gauge | 各联赛成功率 |

**联赛 ID 白名单**:
- `47` - Premier League
- `55` - La Liga
- `54` - Bundesliga
- `61` - Ligue 1
- `135` - Serie A
- `42` - Champions League

### 1.3 错误分布

| 指标名称 | 标签 (Labels) | 数据类型 | 说明 |
|---------|--------------|---------|------|
| `l1_collector_error_count` | `error_type` | Counter | 各类错误发生次数 |

**错误类型分类**:
- `ConnectionError` - 网络连接失败
- `TimeoutError` - 请求超时
- `404` - 联赛不存在
- `500` - 服务器内部错误
- `503` - 服务不可用
- `ValidationError` - Pydantic 校验失败
- `RateLimitError` - 触发速率限制
- `CircuitBreakerOpen` - 熔断器打开

---

## 2. 性能指标 (Performance Metrics)

**定义**: 衡量采集器的响应时间和吞吐能力

### 2.1 延迟指标

| 指标名称 | 数据类型 | 单位 | 说明 |
|---------|---------|------|------|
| `l1_collector_request_duration_seconds` | Histogram | 秒 | API 请求耗时分布 |
| `l1_collector_parse_duration_seconds` | Histogram | 秒 | 数据解析耗时 |
| `l1_collector_validation_duration_seconds` | Histogram | 秒 | Pydantic 校验耗时 |
| `l1_collector_db_write_duration_seconds` | Histogram | 秒 | 数据库写入耗时 |

**Histogram 分位数配置**:
```python
# Prometheus Histogram buckets
buckets = [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
```

**关键分位数**:
- **p50 (中位数)**: 50% 的请求在此时间内完成
- **p95**: 95% 的请求在此时间内完成 (SLA 常用指标)
- **p99**: 99% 的请求在此时间内完成 (长尾分析)

### 2.2 吞吐量指标

| 指标名称 | 数据类型 | 单位 | 说明 |
|---------|---------|------|------|
| `l1_collector_requests_per_second` | Gauge | RPS | 当前请求速率 |
| `l1_collector_matches_per_minute` | Gauge | 场/分钟 | 采集比赛速率 |
| `l1_collector_burst_capacity` | Gauge | 场 | 剩余突发容量 |

### 2.3 并发控制指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_concurrent_requests` | Gauge | 当前并发请求数 |
| `l1_collector_concurrent_limit` | Gauge | 并发限制阈值 |
| `l1_collector_concurrent_utilization` | Gauge | 并发利用率 (0-1) |

**计算公式**:
```
concurrent_utilization = concurrent_requests / concurrent_limit
```

---

## 3. 可靠性指标 (Reliability Metrics)

**定义**: 衡量采集器的弹性机制和容错能力

### 3.1 重试机制指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_retry_attempts_total` | Counter | 重试尝试总次数 |
| `l1_collector_retry_success_total` | Counter | 重试后成功次数 |
| `l1_collector_retry_failure_total` | Counter | 重试后仍失败次数 |
| `l1_collector_retry_rate` | Gauge | 重试率 |

**计算公式**:
```
retry_rate = retry_attempts_total / total_attempted
retry_success_rate = retry_success_total / retry_attempts_total
```

### 3.2 熔断器指标

| 指标名称 | 标签 (Labels) | 数据类型 | 说明 |
|---------|--------------|---------|------|
| `l1_collector_circuit_breaker_state` | `name` | Gauge | 熔断器状态 (0=CLOSED, 1=OPEN, 2=HALF_OPEN) |
| `l1_collector_circuit_breaker_failures` | `name` | Counter | 累计失败次数 |
| `l1_collector_circuit_breaker_successes` | `name` | Counter | 累计成功次数 |
| `l1_collector_circuit_breaker_rejected_total` | `name` | Counter | 熔断器拒绝的请求数 |

**熔断器状态说明**:
- **CLOSED** (0): 正常工作，允许请求通过
- **OPEN** (1): 熔断打开，拒绝请求（连续失败超过阈值）
- **HALF_OPEN** (2): 半开状态，尝试恢复

### 3.3 速率限制指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_rate_limit_wait_seconds_total` | Counter | 速率限制累计等待时间 |
| `l1_collector_rate_limit_throttled_total` | Counter | 被速率限制阻塞的请求数 |

### 3.4 API 健康指标

| 指标名称 | 标签 (Labels) | 数据类型 | 说明 |
|---------|--------------|---------|------|
| `l1_collector_api_response_total` | `status_code` | Counter | 各 HTTP 状态码响应数 |
| `l1_collector_api_error_rate` | - | Gauge | API 错误率 (4xx/5xx) |

**计算公式**:
```
api_error_rate = (4xx_count + 5xx_count) / total_responses
```

---

## 4. 数据质量指标 (Data Quality Metrics)

**定义**: 衡量采集数据的完整性和合规性

### 4.1 Pydantic 校验指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_validation_passed_total` | Counter | Pydantic 校验通过数 |
| `l1_collector_validation_failed_total` | Counter | Pydantic 校验失败数 |
| `l1_collector_validation_failure_rate` | Gauge | 校验失败率 |

### 4.2 League ID 白名单违规

| 指标名称 | 标签 (Labels) | 数据类型 | 说明 |
|---------|--------------|---------|------|
| `l1_collector_invalid_league_id_total` | `league_id` | Counter | 非法 League ID 尝试次数 |

**白名单违规检测**:
```python
# V36.0 核心防御
VALID_LEAGUE_IDS = {47, 55, 54, 61, 135, 42}

if league_id not in VALID_LEAGUE_IDS:
    invalid_league_id_total.labels(league_id=league_id).inc()
    raise ValueError(f"拒绝非法 League ID: {league_id}")
```

### 4.3 元数据一致性指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_league_name_mismatch_total` | Counter | League Name 与 ID 不匹配次数 |
| `l1_collector_score_inconsistency_total` | Counter | 比分不一致性检测次数 |

**元数据污染防护**:
- League ID 白名单校验 (第一道防线)
- League Name 与 ID 一致性校验 (第二道防线)
- 比分一致性校验 (业务逻辑校验)

### 4.4 数据完整性指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_missing_field_total` | `field_name` | Counter | 缺失字段统计 |
| `l1_collector_duplicate_match_id_total` | Counter | 重复 match_id 检测数 |

---

## 5. 资源指标 (Resource Metrics)

**定义**: 衡量系统资源使用情况

### 5.1 内存指标

| 指标名称 | 数据类型 | 单位 | 说明 |
|---------|---------|------|------|
| `l1_collector_memory_usage_bytes` | Gauge | 字节 | 当前内存使用量 |
| `l1_collector_memory_peak_bytes` | Gauge | 字节 | 峰值内存使用 |
| `l1_collector_memory_available_bytes` | Gauge | 字节 | 可用内存 |

### 5.2 连接池指标

| 指标名称 | 数据类型 | 说明 |
|---------|---------|------|
| `l1_collector_http_pool_size` | Gauge | HTTP 连接池大小 |
| `l1_collector_http_pool_active` | Gauge | 活跃连接数 |
| `l1_collector_http_pool_idle` | Gauge | 空闲连接数 |
| `l1_collector_db_pool_size` | Gauge | 数据库连接池大小 |
| `l1_collector_db_pool_active` | Gauge | 数据库活跃连接 |

### 5.3 网络指标

| 指标名称 | 数据类型 | 单位 | 说明 |
|---------|---------|------|------|
| `l1_collector_network_bytes_sent` | Counter | 字节 | 发送字节数 |
| `l1_collector_network_bytes_received` | Counter | 字节 | 接收字节数 |
| `l1_collector_network_requests_total` | Counter | 次 | 网络请求总数 |

---

## 6. 业务指标 (Business Metrics)

**定义**: 衡量采集任务对业务的直接价值

### 6.1 数据时效性

| 指标名称 | 数据类型 | 单位 | 说明 |
|---------|---------|------|------|
| `l1_collector_freshness_seconds` | Gauge | 秒 | 最新比赛数据的时效性 |
| `l1_collector_data_lag_seconds` | Gauge | 秒 | 数据延迟 (当前时间 - 最新比赛时间) |

### 6.2 数据覆盖度

| 指标名称 | 标签 (Labels) | 数据类型 | 说明 |
|---------|--------------|---------|------|
| `l1_collector_season_coverage` | `league_id`, `season` | Gauge | 赛季数据覆盖率 |
| `l1_collector_expected_matches_total` | `league_id`, `season` | Gauge | 预期比赛总数 |
| `l1_collector_collected_matches_total` | `league_id`, `season` | Gauge | 已采集比赛数 |

**覆盖率计算**:
```
coverage = collected_matches / expected_matches × 100%
```

**各联赛预期比赛数**:
| 联赛 | 每赛季比赛数 |
|------|------------|
| Premier League | 380 |
| La Liga | 380 |
| Bundesliga | 306 |
| Ligue 1 | 380 |
| Serie A | 380 |

---

## 7. 告警阈值定义 (Alerting Thresholds)

### 7.1 严重告警 (P0 - 立即响应)

| 指标 | 阈值 | 持续时间 | 操作 |
|------|------|---------|------|
| `l1_collector_circuit_breaker_state` | = 1 (OPEN) | > 1 分钟 | 🚨 立即检查 API 可用性 |
| `l1_collector_success_rate` | < 50% | > 5 分钟 | 🚨 检查网络连接和 API 状态 |
| `l1_collector_api_error_rate` | > 50% | > 3 分钟 | 🚨 可能的 IP 封禁 |
| `l1_collector_validation_failure_rate` | > 20% | > 5 分钟 | 🚨 API 结构可能变更 |

### 7.2 警告告警 (P1 - 尽快响应)

| 指标 | 阈值 | 持续时间 | 操作 |
|------|------|---------|------|
| `l1_collector_success_rate` | < 90% | > 15 分钟 | ⚠️ 检查错误日志 |
| `l1_collector_request_duration_seconds` (p95) | > 30 秒 | > 10 分钟 | ⚠️ API 响应变慢 |
| `l1_collector_retry_rate` | > 30% | > 20 分钟 | ⚠️ 网络不稳定 |
| `l1_collector_memory_usage_bytes` | > 2GB | > 5 分钟 | ⚠️ 检查内存泄漏 |

### 7.3 提示告警 (P2 - 关注即可)

| 指标 | 阈值 | 持续时间 | 操作 |
|------|------|---------|------|
| `l1_collector_data_lag_seconds` | > 24 小时 | - | ℹ️ 数据可能过期 |
| `l1_collector_season_coverage` | < 80% | - | ℹ️ 数据采集不完整 |
| `l1_collector_invalid_league_id_total` | > 0 | - | ℹ️ 配置错误 |

---

## 8. 指标实现示例

### 8.1 Prometheus 集成示例

```python
"""
V36.0 Prometheus 指标导出示例
"""
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# 采集指标
total_attempted = Counter(
    "l1_collector_total_attempted",
    "Total attempted match collections",
    ["league_id", "league_name"]
)

total_success = Counter(
    "l1_collector_total_success",
    "Total successful match collections",
    ["league_id", "league_name"]
)

# 性能指标
request_duration = Histogram(
    "l1_collector_request_duration_seconds",
    "API request duration",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# 可靠性指标
circuit_breaker_state = Gauge(
    "l1_collector_circuit_breaker_state",
    "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
    ["name"]
)

# 使用示例
async def collect_league_season(league_id: int, season_code: str):
    league_name = LeagueId.get_league_name(str(league_id))

    with request_duration.time():
        try:
            matches = await collector._fetch_league_matches(league_id, season_code)

            for match in matches:
                total_success.labels(league_id=str(league_id), league_name=league_name).inc()

        except Exception as e:
            total_attempted.labels(league_id=str(league_id), league_name=league_name).inc()
            logger.error(f"Collection failed: {e}")

# 启动 Prometheus 服务器
if __name__ == "__main__":
    start_http_server(8000)  # 指标暴露在 :8000/metrics
```

### 8.2 Grafana 仪表板配置

```json
{
  "dashboard": {
    "title": "L1 Collector Metrics (V36.0)",
    "panels": [
      {
        "title": "采集成功率",
        "targets": [
          {
            "expr": "rate(l1_collector_total_success[5m]) / rate(l1_collector_total_attempted[5m]) * 100"
          }
        ]
      },
      {
        "title": "API 请求延迟 (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(l1_collector_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "熔断器状态",
        "targets": [
          {
            "expr": "l1_collector_circuit_breaker_state"
          }
        ]
      }
    ]
  }
}
```

---

## 9. 指标采集频率

| 指标类型 | 采集频率 | 保留时间 |
|---------|---------|---------|
| Counter (计数器) | 实时 | 90 天 |
| Gauge (仪表盘) | 每 10 秒 | 30 天 |
| Histogram (直方图) | 实时 | 90 天 |

---

## 10. 指标验证

### 10.1 单元测试覆盖

所有关键指标必须在单元测试中验证：

```python
def test_metrics_increment_on_success():
    """测试成功采集时指标正确累加"""
    summary = L1CollectionSummary()
    summary.add_success("47")

    assert summary.total_success == 1
    assert summary.total_attempted == 1
    assert summary.success_rate == 100.0

def test_circuit_breaker_metrics():
    """测试熔断器指标正确记录"""
    breaker = CircuitBreaker(failure_threshold=3)

    breaker.record_failure(Exception("test"))
    breaker.record_failure(Exception("test"))

    assert breaker.failure_count == 2
    assert breaker.is_open() == False

    breaker.record_failure(Exception("test"))
    assert breaker.is_open() == True
```

---

## 11. 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| V36.0 | 2025-12-28 | 初始版本，生产级指标体系 |

---

**文档状态**: ✅ Production Ready
**维护责任**: ML Architect / DevOps Team
