# Phase 4 TODO Issues

本文档记录了Phase 4中需要处理的复杂TODO项，这些项需要额外的工作量，已转化为GitHub Issue。

## 🔴 高优先级

### 1. 实现数据存储功能
- **文件**: `src/data/features/feature_store.py`
- **TODO**:
  - 实现从数据库查询比赛的逻辑
  - 实现具体的清理逻辑（清理Redis在线存储中的过期特征）
- **工时估算**: 8-12小时
- **Issue**: #链接待创建

### 2. 实现数据收集器功能
- **文件**: `src/data/collectors/odds_collector.py`
- **TODO**:
  - 从数据库或配置获取博彩公司列表
  - 实现数据源适配器
  - 处理不同的数据格式
- **工时估算**: 10-15小时
- **Issue**: #链接待创建

## 🟡 中优先级

### 3. 实现性能监控功能
- **文件**: `src/performance/api.py`
- **TODO**:
  - 计算实际趋势
  - 从数据库或时序数据库获取历史数据
  - 实现阈值更新逻辑
  - 从配置获取实际阈值
- **工时估算**: 6-8小时
- **Issue**: #链接待创建

### 4. 实现数据质量监控
- **文件**: `src/data/quality/data_quality_monitor.py`
- **TODO**:
  - 实现数据质量检查逻辑
  - 配置质量规则
  - 生成质量报告
- **工时估算**: 8-10小时
- **Issue**: #链接待创建

## 🟢 低优先级

### 5. 实现告警功能
- **文件**: `src/performance/integration.py`
- **TODO**:
  - 实现告警设置
  - 配置告警规则
  - 发送告警通知
- **工时估算**: 4-6小时
- **Issue**: #链接待创建

### 6. 实现缺失比赛检测
- **文件**: `src/data/collectors/fixtures_collector.py`
- **TODO**:
  - 实现缺失比赛检测逻辑
  - 从数据库查询应该存在的比赛
- **工时估算**: 3-4小时
- **Issue**: #链接待创建

### 7. 实现其他数据收集器功能
- **文件**: `src/data/collectors/scores_collector.py`
- **TODO**:
  - 实现比分收集逻辑
  - 处理实时比分更新
- **工时估算**: 5-7小时
- **Issue**: #链接待创建

## 📊 统计

- **总TODO数**: 56个
- **已删除**: 约25个（过时的迁移注释）
- **已实现**: 1个（parent_run功能）
- **剩余复杂TODO**: 7个（需要创建GitHub Issue）
- **其他简单TODO**: 约23个（可以在后续迭代中快速实现）

## 🎯 下一步行动

1. 为上述复杂TODO创建GitHub Issue
2. 优先实现高优先级的功能
3. 在每个冲刺中处理2-3个TODO项
4. 定期更新此文档
