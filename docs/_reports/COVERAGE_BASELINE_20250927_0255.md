# 📊 Coverage Baseline (2025-09-27 02:55:56)

- 当前总覆盖率：**7.7%**
- 目标阈值（阶段 1）：**40%**
- 估算尚需新增覆盖行数：**7874** 行（粗略）

## 从哪里下手（优先 15 个高收益文件）
| 文件 | 覆盖率 | 语句数 | 未覆盖 | 建议 |
|------|--------|--------|--------|------|
| scripts/defense_validator.py | 0.0% | 504 | 504 | 为脚本入口函数补用例 |
| scripts/auto_ci_updater.py | 0.0% | 379 | 379 | 为脚本入口函数补用例 |
| src/services/audit_service.py | 0.0% | 359 | 359 | 补单元测试+mock外部依赖 |
| tests/external_mocks.py | 0.0% | 329 | 329 | 补单元测试+mock外部依赖 |
| src/monitoring/quality_monitor.py | 0.0% | 323 | 323 | 补单元测试+mock外部依赖 |
| scripts/ci_issue_analyzer.py | 0.0% | 316 | 316 | 为脚本入口函数补用例 |
| tests/unit/streaming_kafka_consumer_batch_gamma_.py | 0.0% | 307 | 307 | 补单元测试+mock外部依赖 |
| scripts/ci_guardian.py | 0.0% | 301 | 301 | 为脚本入口函数补用例 |
| comprehensive_mcp_health_check.py | 0.0% | 290 | 290 | 补单元测试+mock外部依赖 |
| test_metrics_collector.py | 0.0% | 287 | 287 | 补单元测试+mock外部依赖 |
| scripts/retrain_pipeline.py | 0.0% | 275 | 275 | 为脚本入口函数补用例 |
| test_lineage_reporter.py | 0.0% | 274 | 274 | 补单元测试+mock外部依赖 |
| test_feature_calculator.py | 0.0% | 273 | 273 | 补单元测试+mock外部依赖 |
| tests/unit/data_storage_data_lake_storage_batch_gamma_.py | 0.0% | 271 | 271 | 补单元测试+mock外部依赖 |
| test_kafka_producer.py | 0.0% | 269 | 269 | 补单元测试+mock外部依赖 |