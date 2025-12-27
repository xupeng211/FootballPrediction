---
name: data-collection
description: Collect football data from external APIs including FotMob L2 data, odds information, and real-time match statistics. Use when gathering match data, collecting historical statistics, or updating prediction datasets.
---

# Data Collection Skill

## 概述
专业的足球数据收集技能，支持从多个外部API获取实时和历史数据，为预测系统提供高质量的数据源。

## 核心功能

### 1. FotMob API 数据收集
- **L2级别数据提取**: 增强型数据收集器
- **实时比赛数据**: 比分、事件、球员评分
- **深度统计**: xG、传球、射门等高级指标
- **赔率数据**: 实时赔率变化

### 2. 数据验证与清洗
- **数据完整性检查**: 确保关键字段完整
- **异常值检测**: 识别和处理异常数据
- **重复数据去除**: 避免数据重复
- **格式标准化**: 统一数据格式

### 3. 批量数据处理
- **历史数据回填**: 填充历史比赛数据
- **增量更新**: 只更新新增数据
- **并行收集**: 多线程数据收集
- **错误重试**: 自动重试失败请求

## 使用方法

### 单场比赛数据收集
```bash
python scripts/collectors/fotmob_api_collector.py --match_id "12345"
```

### 批量数据收集
```bash
python scripts/collectors/enhanced_fotmob_collector.py --league "Premier League" --days 30
```

### 实时数据收集
```python
from scripts.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector

collector = EnhancedFotMobCollector()
data = collector.collect_live_match(match_id="12345")
```

## 数据源

### 1. FotMob API (主要)
- **Base URL**: https://api.fotmob.com
- **数据类型**: 比赛实时数据、历史数据、统计数据
- **更新频率**: 实时（比赛进行中）
- **数据质量**: 高质量L2级别数据

### 2. 赔率数据 (可选)
- **来源**: 多个博彩公司API
- **数据类型**: 胜平负赔率、亚洲盘、大小球
- **更新频率**: 每分钟更新

### 3. 其他数据源
- **球员数据**: 转会信息、伤病情况
- **天气数据**: 比赛天气条件
- **裁判数据**: 裁判执法统计

## 输出格式

### JSON格式（推荐）
```json
{
  "match_id": "12345",
  "home_team": "Manchester United",
  "away_team": "Arsenal",
  "score": {
    "home": 2,
    "away": 1
  },
  "statistics": {
    "possession": {"home": 55, "away": 45},
    "shots": {"home": 15, "away": 8},
    "xg": {"home": 2.1, "away": 0.8}
  },
  "events": [
    {
      "minute": 25,
      "type": "goal",
      "player": "Bruno Fernandes",
      "team": "home"
    }
  ]
}
```

### 数据库存储
- **PostgreSQL**: 主数据存储
- **表结构**: normalized设计
- **索引优化**: 快速查询支持

## 配置管理

### API配置
```python
# .env.dev
FOTMOB_BASE_URL=https://api.fotmob.com
FOTMOB_X_MAS_HEADER=your_header_value
FOTMOB_RATE_LIMIT=100  # requests per minute
```

### 收集配置
```python
DATA_COLLECTION_CONFIG = {
    "retry_attempts": 3,
    "timeout": 30,
    "batch_size": 100,
    "parallel_workers": 4
}
```

## 性能优化

### 缓存策略
- **Redis缓存**: 减少重复API调用
- **本地缓存**: 临时数据存储
- **TTL设置**: 24小时数据有效期

### 并发控制
- **连接池**: HTTP连接复用
- **限流器**: 避免API限制
- **批量处理**: 提高收集效率

## 错误处理

### 常见错误类型
1. **API限制**: 429 Too Many Requests
2. **网络错误**: 连接超时
3. **数据格式**: API响应格式变化
4. **认证失败**: API密钥问题

### 处理策略
```python
try:
    data = collector.collect_match(match_id)
except RateLimitError:
    time.sleep(60)  # 等待1分钟后重试
except NetworkError:
    retry_with_backoff(match_id)
except DataFormatError:
    log_error_and_continue(match_id)
```

## 监控指标

### 收集性能
- **成功率**: 成功收集的比赛数量
- **延迟**: API响应时间
- **吞吐量**: 每分钟收集的比赛数
- **错误率**: 失败请求比例

### 数据质量
- **完整性**: 必需字段完整率
- **准确性**: 数据验证通过率
- **及时性**: 数据更新延迟

## 使用场景

### 1. 日常数据更新
- **定时任务**: 每小时收集最新数据
- **实时收集**: 比赛进行中实时更新
- **数据验证**: 确保数据质量

### 2. 历史数据回填
- **批量导入**: 导入历史赛季数据
- **数据修复**: 修复缺失的历史数据
- **数据迁移**: 从旧系统迁移数据

### 3. 特殊数据收集
- **重点赛事**: 世界杯、欧洲杯等
- **特定联赛**: 用户关注的联赛
- **研究项目**: 特定的分析需求

## 最佳实践

### 1. 数据收集原则
- **增量优先**: 避免全量重复收集
- **质量第一**: 确保数据准确性
- **及时更新**: 保持数据时效性
- **错误处理**: 优雅处理异常情况

### 2. 性能优化
- **合理缓存**: 减少不必要的API调用
- **批量处理**: 提高收集效率
- **并发控制**: 避免过载API
- **监控告警**: 及时发现问题

### 3. 数据管理
- **版本控制**: 跟踪数据版本
- **备份策略**: 定期备份重要数据
- **清理机制**: 清理过期数据
- **文档记录**: 维护数据字典

## 相关脚本

- `scripts/collectors/enhanced_fotmob_collector.py` - 主要收集器
- `scripts/collectors/fotmob_api_collector.py` - 基础收集器
- `scripts/collectors/base_collector.py` - 基础类
- `scripts/data_collector_v2.py` - V2收集器

## 集成点

### 与预测系统集成
```python
# 数据收集 → 特征工程 → 模型预测
data = collector.collect_match(match_id)
features = feature_engineer.process(data)
prediction = model.predict(features)
```

### 与监控系统集成
```python
# 收集性能指标
metrics.collector_success_rate.inc()
metrics.collection_duration.observe(time.time() - start)
```

## 注意事项

### API使用限制
- 遵守各API的使用条款
- 实施合理的限流策略
- 避免过度频繁的请求

### 数据合规
- 确保数据使用合法合规
- 尊重数据隐私
- 必要时进行数据脱敏

### 成本控制
- 监控API调用成本
- 优化数据收集策略
- 避免不必要的重复收集

## 相关技能
- `v26-harvest`: V26.1 收割流水线
- `data-engineering`: ETL 数据管道
- `database-operations`: 数据库操作