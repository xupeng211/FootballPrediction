# 📊 Test Coverage Dashboard

生成时间: 2025-09-27 15:36:36

本仪表盘用于追踪项目测试覆盖率趋势和各模块差异。

## 1. 总体覆盖率

当前总覆盖率: **7.7%**

## 2. 模块覆盖率排名

### 🏆 Top 5 覆盖率最高模块

| 文件 | 覆盖率 | 缺失行数 |
|------|--------|----------|
| tests/unit/conftest.py | 100.0% | 0 |
| src/data/features/feature_definitions.py | 100.0% | 0 |
| src/core/exceptions.py | 100.0% | 0 |
| src/api/schemas.py | 100.0% | 0 |
| scripts/defense_generator.py | 100.0% | 0 |

### ⚠️ Bottom 5 覆盖率最低模块

| 文件 | 覆盖率 | 缺失行数 |
|------|--------|----------|
| analyze_coverage.py | 0.0% | 84 |
| analyze_coverage_precise.py | 0.0% | 102 |
| comprehensive_mcp_health_check.py | 0.0% | 290 |
| coverage_analysis_phase5322.py | 0.0% | 78 |
| extract_coverage.py | 0.0% | 90 |

## 3. 按目录覆盖率统计

| 目录 | 文件数 | 总行数 | 覆盖率 | 缺失行数 |
|------|--------|--------|--------|----------|
| analyze_coverage.py | 1 | 56 | 0.0% | 84 |
| analyze_coverage_precise.py | 1 | 56 | 0.0% | 102 |
| comprehensive_mcp_health_check.py | 1 | 56 | 0.0% | 290 |
| coverage_analysis_phase5322.py | 1 | 56 | 0.0% | 78 |
| extract_coverage.py | 1 | 56 | 0.0% | 90 |
| manual_coverage_analysis.py | 1 | 56 | 0.0% | 71 |
| mcp_health_check.py | 1 | 56 | 0.0% | 82 |
| scripts | 40 | 2240 | 0.0% | 5817 |
| setup.py | 1 | 56 | 0.0% | 2 |
| src | 90 | 5040 | 0.0% | 9998 |
| test_anomaly_detector.py | 1 | 56 | 0.0% | 227 |
| test_data_processing_async.py | 1 | 56 | 0.0% | 78 |
| test_data_processing_minimal.py | 1 | 56 | 0.0% | 49 |
| test_feature_calculator.py | 1 | 56 | 0.0% | 273 |
| test_feature_calculator_simple.py | 1 | 56 | 0.0% | 238 |
| test_kafka_consumer.py | 1 | 56 | 0.0% | 140 |
| test_kafka_producer.py | 1 | 56 | 0.0% | 269 |
| test_lineage_reporter.py | 1 | 56 | 0.0% | 274 |
| test_main_direct.py | 1 | 56 | 0.0% | 192 |
| test_metadata_manager.py | 1 | 56 | 0.0% | 102 |
| test_metrics_collector.py | 1 | 56 | 0.0% | 287 |
| test_metrics_collector_simple.py | 1 | 56 | 0.0% | 246 |
| test_model_training.py | 1 | 56 | 0.0% | 243 |
| test_quality_monitor.py | 1 | 56 | 0.0% | 71 |
| tests | 28 | 1568 | 0.0% | 3984 |

## 4. 改进建议

- 优先修复覆盖率最低的模块 (Bottom 5)
- 持续提升覆盖率，每周 +5% 为目标
- 新增代码必须 ≥80% 覆盖率 (CI 已守护)