# 性能优化使用指南

## 🎯 概述

本指南介绍足球预测系统性能优化功能的使用方法，包括缓存管理、性能监控和系统优化。

## 🚀 快速开始

### 1. 启动性能优化服务

```bash
# 确保Redis服务运行 (可选)
redis-server

# 启动应用 (性能优化自动启用)
python src/main.py
```

### 2. 验证性能优化功能

```bash
# 检查健康状态
curl http://localhost:8000/api/predictions/v2/health

# 获取优化预测 (带缓存)
curl http://localhost:8000/api/predictions/v2/matches/123/prediction
```

## 📦 核心组件

### 1. 统一缓存管理器

#### 基本使用
```python
from src.cache.unified_cache import get_cache_manager

# 获取缓存管理器
cache_mgr = get_cache_manager()

# 缓存数据
await cache_mgr.set(
    key="prediction_123",
    value={"outcome": "home_win", "confidence": 0.75},
    cache_type="prediction_result",
    ttl=1800  # 30分钟
)

# 获取缓存数据
cached_data = await cache_mgr.get("prediction_123", "prediction_result")
if cached_data:
    print("缓存命中:", cached_data)
else:
    print("缓存未命中，需要重新计算")

# 删除缓存
await cache_mgr.delete("prediction_123", "prediction_result")

# 批量清除匹配模式的缓存
await cache_mgr.invalidate_pattern("prediction_", "prediction_result")
```

#### 装饰器使用
```python
from src.cache.unified_cache import cached, performance_monitor

# 自动缓存函数结果
@cached(cache_type="prediction_result", ttl=1800)
async def calculate_prediction(match_id: int):
    # 复杂的预测计算
    result = await complex_prediction_algorithm(match_id)
    return result

# 性能监控装饰器
@performance_monitor(threshold=1.0)  # 1秒阈值
async def slow_operation():
    # 耗时操作
    await asyncio.sleep(0.5)
    return "result"

# 组合使用
@cached(cache_type="team_stats", ttl=900)
@performance_monitor(threshold=0.5)
async def get_team_statistics(team_id: int):
    # 获取团队统计
    return await fetch_team_stats(team_id)
```

### 2. 系统性能监控

#### 监控系统资源
```python
from src.performance.monitoring import get_system_monitor

# 获取系统监控器
monitor = get_system_monitor()

# 获取当前系统指标
current_metrics = monitor.get_current_metrics()
print(f"CPU使用率: {current_metrics.cpu_percent}%")
print(f"内存使用率: {current_metrics.memory_percent}%")
print(f"平均响应时间: {current_metrics.response_time_avg}ms")

# 获取历史指标摘要
summary = monitor.get_metrics_summary(minutes=5)
print(f"5分钟内平均CPU: {summary['cpu']['avg']}%")

# 检查性能警报
alerts = monitor.check_performance_alerts()
if alerts:
    for alert in alerts:
        print(f"警报: {alert['message']} (严重程度: {alert['severity']})")
```

#### 性能分析
```python
from src.performance.monitoring import get_performance_analyzer

# 获取性能分析器
analyzer = get_performance_analyzer()

# 分析性能趋势
trends = analyzer.analyze_trends(hours=1)
print(f"CPU趋势: {trends['trends']['cpu']['trend']}")

# 获取性能建议
metrics_summary = monitor.get_metrics_summary(minutes=10)
recommendations = analyzer.get_performance_recommendations(metrics_summary)
for rec in recommendations:
    print(f"建议: {rec}")
```

### 3. 数据库性能优化

#### 使用性能优化器
```python
from src.database.base import get_db
from src.performance.optimizer import get_performance_optimizer

# 获取数据库会话
async with get_db() as db_session:
    # 获取性能优化器
    optimizer = get_performance_optimizer(db_session)

    # 优化数据库索引
    index_results = await optimizer.optimize_database_indexes()
    print(f"创建索引: {len(index_results['created'])}")
    print(f"已存在索引: {len(index_results['existing'])}")

    # 分析慢查询
    query_analysis = await optimizer.optimize_slow_queries()
    for query_name, analysis in query_analysis.items():
        if 'recommendations' in analysis:
            print(f"查询 {query_name} 建议:")
            for rec in analysis['recommendations']:
                print(f"  - {rec}")

    # 实现查询缓存
    cache_results = await optimizer.implement_query_cache()
    print(f"缓存查询数量: {len(cache_results['cached'])}")

    # 优化缓存配置
    cache_optimization = await optimizer.optimize_cache_configuration()
    print("缓存优化建议:", cache_optimization['recommendations'])
```

## 🔧 配置管理

### 1. 缓存配置

```python
from src.performance.config import get_performance_config

# 获取配置管理器
config = get_performance_config()

# 查看当前缓存配置
cache_config = config.get_cache_config()
print("预测结果TTL:", cache_config['prediction']['ttl'])  # 1800秒
print("本地缓存大小:", cache_config['local']['size'])    # 1000条目

# 更新缓存配置
config.update_cache_config(
    prediction_ttl=3600,      # 预测结果缓存1小时
    local_cache_size=2000     # 本地缓存2000条目
)
```

### 2. 监控配置

```python
# 查看监控配置
monitoring_config = config.get_monitoring_config()
thresholds = monitoring_config['thresholds']

print("CPU警告阈值:", thresholds['cpu']['warning'])     # 70%
print("CPU严重阈值:", thresholds['cpu']['critical'])    # 90%
print("响应时间警告:", thresholds['response_time']['warning'])  # 1.0秒

# 更新监控配置
config.update_monitoring_config(
    cpu_warning_threshold=80.0,    # CPU警告阈值调至80%
    response_time_warning=1.5      # 响应时间警告调至1.5秒
)
```

### 3. 优化配置

```python
# 查看优化配置
optimization_config = config.get_optimization_config()
print("启用查询优化:", optimization_config['database']['enable_query_optimization'])
print("最大连接数:", optimization_config['connection_pool']['max_connections'])

# 更新优化配置
config.update_optimization_config(
    max_connections=30,           # 最大连接数增至30
    slow_query_threshold=0.5      # 慢查询阈值调至0.5秒
)
```

## 📊 API端点使用

### 1. 健康检查

```bash
# 基本健康检查
curl http://localhost:8000/api/predictions/v2/health

# 响应示例
{
  "status": "healthy",
  "timestamp": "2025-11-06T20:00:00Z",
  "cache_stats": {
    "hit_rate": 0.75,
    "local_cache_size": 850
  },
  "system_metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "response_time_avg": 0.35
  }
}
```

### 2. 优化预测端点

```bash
# 获取预测结果 (自动缓存)
curl "http://localhost:8000/api/predictions/v2/matches/123/prediction?include_details=true"

# 响应示例
{
  "status": "success",
  "data": {
    "match_id": 123,
    "predicted_outcome": "home_win",
    "confidence_score": 0.78,
    "probabilities": {
      "home_win": 0.65,
      "draw": 0.25,
      "away_win": 0.10
    }
  },
  "cached": false,
  "execution_time_ms": 245.5
}
```

### 3. 热门预测

```bash
# 获取热门预测
curl "http://localhost:8000/api/predictions/v2/popular?limit=20&time_range=24h"

# 获取用户预测历史
curl "http://localhost:8000/api/predictions/v2/user/456/history?page=1&size=10"
```

### 4. 统计信息

```bash
# 获取预测统计
curl "http://localhost:8000/api/predictions/v2/statistics?time_range=7d"

# 响应示例
{
  "status": "success",
  "data": {
    "total_predictions": 15420,
    "accuracy_rate": 0.73,
    "average_confidence": 0.76,
    "performance_metrics": {
      "avg_response_time_ms": 280.5,
      "cache_hit_rate": 0.78,
      "daily_predictions": 185
    }
  }
}
```

### 5. 缓存管理

```bash
# 缓存预热 (需要管理员权限)
curl -X POST http://localhost:8000/api/predictions/v2/cache/warmup \
  -H "Authorization: Bearer <admin_token>"

# 清除缓存 (需要管理员权限)
curl -X DELETE "http://localhost:8000/api/predictions/v2/cache/clear?pattern=prediction" \
  -H "Authorization: Bearer <admin_token>"
```

## 🎯 最佳实践

### 1. 缓存策略

```python
# ✅ 推荐: 为不同类型的数据设置合适的TTL
@cached(cache_type="prediction_result", ttl=1800)  # 预测结果30分钟
async def get_prediction(match_id):
    pass

@cached(cache_type="team_stats", ttl=3600)        # 团队统计1小时
async def get_team_stats(team_id):
    pass

@cached(cache_type="user_preferences", ttl=7200)  # 用户偏好2小时
async def get_user_preferences(user_id):
    pass
```

### 2. 性能监控

```python
# ✅ 推荐: 为关键操作添加性能监控
@performance_monitor(threshold=1.0)  # 1秒阈值
async def critical_business_operation():
    # 关键业务逻辑
    pass

# ✅ 推荐: 定期检查性能警报
monitor = get_system_monitor()
alerts = monitor.check_performance_alerts()
if alerts:
    # 发送告警通知
    await send_alert_notification(alerts)
```

### 3. 数据库优化

```python
# ✅ 推荐: 定期运行数据库优化
async def scheduled_optimization():
    async with get_db() as db_session:
        optimizer = get_performance_optimizer(db_session)

        # 每周优化索引
        await optimizer.optimize_database_indexes()

        # 分析慢查询
        await optimizer.optimize_slow_queries()
```

### 4. 错误处理

```python
# ✅ 推荐: 完善的错误处理
try:
    cached_data = await cache_mgr.get(key, cache_type)
    if cached_data is None:
        # 缓存未命中，重新计算
        data = await expensive_computation()
        await cache_mgr.set(key, data, cache_type, ttl)
    else:
        data = cached_data
except Exception as e:
    logger.error(f"缓存操作失败: {e}")
    # 降级到直接计算
    data = await expensive_computation()
```

## 📈 性能调优建议

### 1. 缓存优化

- **热点数据**: 对访问频繁的数据使用较短的TTL (5-15分钟)
- **稳定数据**: 对变化较少的数据使用较长的TTL (1-24小时)
- **本地缓存**: 合理设置本地缓存大小，避免内存溢出
- **缓存预热**: 系统启动时预热关键数据

### 2. 监控调优

- **阈值设置**: 根据业务需求调整性能阈值
- **监控频率**: 平衡监控精度和系统开销
- **告警策略**: 设置合理的告警级别和通知方式
- **趋势分析**: 定期分析性能趋势，及时发现问题

### 3. 数据库优化

- **索引策略**: 为常用查询创建合适的索引
- **查询优化**: 避免N+1查询，使用JOIN优化
- **连接池**: 合理配置数据库连接池大小
- **慢查询**: 定期分析和优化慢查询

## 🚨 故障排除

### 常见问题

1. **缓存命中率低**
   ```python
   # 检查缓存统计
   stats = await cache_mgr.get_cache_stats()
   print(f"命中率: {stats['hit_rate']}")

   # 优化缓存键设计
   # 确保缓存键的一致性
   ```

2. **内存使用过高**
   ```python
   # 调整本地缓存大小
   config.update_cache_config(local_cache_size=500)

   # 清理过期缓存
   await cache_mgr.cleanup_expired_entries()
   ```

3. **响应时间慢**
   ```python
   # 检查性能警报
   alerts = monitor.check_performance_alerts()

   # 优化慢查询
   async with get_db() as db_session:
       optimizer = get_performance_optimizer(db_session)
       await optimizer.optimize_slow_queries()
   ```

### 调试工具

```python
# 启用详细日志
import logging
logging.getLogger('src.cache').setLevel(logging.DEBUG)
logging.getLogger('src.performance').setLevel(logging.DEBUG)

# 性能分析
@performance_monitor(threshold=0.1)  # 设置较低阈值用于调试
async def debug_function():
    pass
```

## 📚 相关文档

- [性能优化完成报告](./ISSUE337_PERFORMANCE_OPTIMIZATION_COMPLETION_REPORT.md)
- [API参考文档](./API_REFERENCE.md)
- [系统架构文档](./ARCHITECTURE.md)
- [测试改进指南](./TEST_IMPROVEMENT_GUIDE.md)

---

**文档版本**: v1.0 | **更新时间**: 2025-11-06 | **维护者**: Claude Code