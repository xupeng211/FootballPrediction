# Batch-Γ 覆盖率提升任务清单 - Phase 5.3.2.2

## 任务目标

将整体测试覆盖率从当前基线提升到 ≥30%

## 执行策略

1. 优先处理影响分数最高的文件（代码量大 + 覆盖率低）
2. 每个文件创建专门的测试文件
3. 使用系统性测试方法确保覆盖率稳定提升
4. 解决pandas/numpy/mlflow等依赖的懒加载问题

## Batch-Γ 任务清单

### Batch-Γ-001: src/services/data_processing.py

- **当前覆盖率**: 7.0%
- **代码行数**: 503 行
- **影响分数**: 467.8
- **目标覆盖率**: 32.0%
- **测试文件**: tests/unit/services_data_processing_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-002: src/data/quality/anomaly_detector.py

- **当前覆盖率**: 8.0%
- **代码行数**: 458 行
- **影响分数**: 421.4
- **目标覆盖率**: 33.0%
- **测试文件**: tests/unit/data_quality_anomaly_detector_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-003: src/cache/redis_manager.py

- **当前覆盖率**: 15.0%
- **代码行数**: 429 行
- **影响分数**: 364.6
- **目标覆盖率**: 40.0%
- **测试文件**: tests/unit/cache_redis_manager_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-004: src/services/audit_service.py

- **当前覆盖率**: 11.0%
- **代码行数**: 359 行
- **影响分数**: 319.5
- **目标覆盖率**: 46.0%
- **测试文件**: tests/unit/services_audit_service_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-005: src/data/storage/data_lake_storage.py

- **当前覆盖率**: 6.0%
- **代码行数**: 322 行
- **影响分数**: 302.7
- **目标覆盖率**: 41.0%
- **测试文件**: tests/unit/data_storage_data_lake_storage_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-006: src/monitoring/quality_monitor.py

- **当前覆盖率**: 8.0%
- **代码行数**: 323 行
- **影响分数**: 297.2
- **目标覆盖率**: 43.0%
- **测试文件**: tests/unit/monitoring_quality_monitor_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-007: src/monitoring/anomaly_detector.py

- **当前覆盖率**: 12.0%
- **代码行数**: 248 行
- **影响分数**: 218.2
- **目标覆盖率**: 47.0%
- **测试文件**: tests/unit/monitoring_anomaly_detector_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-008: src/streaming/kafka_consumer.py

- **当前覆盖率**: 10.0%
- **代码行数**: 242 行
- **影响分数**: 217.8
- **目标覆盖率**: 45.0%
- **测试文件**: tests/unit/streaming_kafka_consumer_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-009: src/monitoring/metrics_collector.py

- **当前覆盖率**: 18.0%
- **代码行数**: 248 行
- **影响分数**: 203.4
- **目标覆盖率**: 53.0%
- **测试文件**: tests/unit/monitoring_metrics_collector_batch_gamma_.py
- **优先级**: 🟡 中

### Batch-Γ-010: src/tasks/backup_tasks.py

- **当前覆盖率**: 16.0%
- **代码行数**: 242 行
- **影响分数**: 203.3
- **目标覆盖率**: 51.0%
- **测试文件**: tests/unit/tasks_backup_tasks_batch_gamma_.py
- **优先级**: 🟡 中

## 执行计划

1. **阶段1**: 处理影响分数 > 500 的文件（0 个）
2. **阶段2**: 处理影响分数 200-500 的文件（10 个）
3. **阶段3**: 处理影响分数 < 200 的文件（0 个）

## 预期效果

- **当前整体覆盖率**: 21.67%
- **目标整体覆盖率**: ≥30%
- **提升幅度**: ≥8.33%

## 质量保证

- 所有测试必须通过pytest验证
- 测试代码必须包含中文注释
- 遵循Arrange-Act-Assert模式
- 解决依赖导入问题，不绕过pytest
