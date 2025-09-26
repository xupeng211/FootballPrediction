# 📝 TODO Replacement Plan

本计划旨在分阶段替换所有测试文件中的 TODO 占位符，确保测试断言逐步从占位过渡到真实业务逻辑验证。

## 📊 当前统计
- 总计 TODO 占位符: **57**
- 受影响的测试文件数: **38**

## ✅ 阶段 1 完成情况
- **完成时间**: 已完成
- **替换数量**: 20 个 TODO（scripts 模块）

## ✅ 阶段 2 完成情况
- **完成时间**: 刚刚完成
- **替换数量**: 19 个 TODO（src/tasks + src/models 模块）
- **累计完成**: 39 个 TODO
- **总体完成率**: 40.2% (39/97)

## 📂 剩余文件分布
- tests/unit/test_setup.py: 1 个 TODO
- tests/unit/test_src_data_features_examples.py: 10 个 TODO
- tests/unit/test_src_streaming_stream_processor.py: 1 个 TODO
- tests/unit/test_src_data_quality_anomaly_detector.py: 1 个 TODO
- tests/unit/test_src_data_quality_data_quality_monitor.py: 1 个 TODO
- tests/unit/test_src_monitoring_alert_manager.py: 1 个 TODO
- tests/unit/test_src_data_quality_exception_handler.py: 1 个 TODO
- tests/unit/test_src_data_collectors_scores_collector.py: 1 个 TODO
- tests/unit/test_src_data_collectors_base_collector.py: 1 个 TODO
- tests/unit/test_src_data_collectors_odds_collector.py: 1 个 TODO
- tests/unit/test_src_data_storage_data_lake_storage.py: 1 个 TODO
- tests/unit/test_src_data_quality_ge_prometheus_exporter.py: 1 个 TODO
- tests/unit/test_src_data_quality_great_expectations_config.py: 1 个 TODO
- tests/unit/test_src_services_data_processing.py: 1 个 TODO
- tests/unit/test_src_streaming_kafka_producer.py: 1 个 TODO
- tests/unit/test_src_monitoring_metrics_exporter.py: 1 个 TODO
- tests/unit/test_src_cache_redis_manager.py: 1 个 TODO
- tests/unit/test_src_data_features_feature_store.py: 1 个 TODO
- tests/unit/test_src_lineage_metadata_manager.py: 1 个 TODO
- tests/unit/test_src_data_processing_football_data_cleaner.py: 1 个 TODO
- tests/unit/test_src_data_collectors_streaming_collector.py: 1 个 TODO
- tests/unit/test_src_features_feature_calculator.py: 1 个 TODO
- tests/unit/test_src_monitoring_quality_monitor.py: 1 个 TODO
- tests/unit/test_src_lineage_lineage_reporter.py: 1 个 TODO
- tests/unit/test_src_features_feature_store.py: 1 个 TODO
- tests/unit/test_src_data_processing_missing_data_handler.py: 1 个 TODO
- tests/unit/test_src_monitoring_metrics_collector.py: 1 个 TODO
- tests/unit/test_scripts_end_to_end_verification.py: 1 个 TODO
- tests/unit/test_src_streaming_kafka_consumer.py: 1 个 TODO
- tests/unit/test_scripts_refresh_materialized_views.py: 1 个 TODO
- tests/unit/test_src_models_model_training.py: 1 个 TODO
- tests/unit/test_src_monitoring_anomaly_detector.py: 1 个 TODO
- tests/unit/test_scripts_env_checker.py: 1 个 TODO
- tests/unit/test_scripts_ci_monitor.py: 1 个 TODO
- tests/unit/test_scripts_generate-passwords.py: 9 个 TODO
- tests/unit/test_src_data_collectors_fixtures_collector.py: 1 个 TODO
- tests/unit/api/test_predictions_core.py: 1 个 TODO
- tests/unit/data/test_odds_collector.py: 3 个 TODO

## 🚀 后续计划
3. **阶段 3 (两周后)** - 再清理 20 个 TODO
   - 针对 `src/data/` 和 `src/monitoring/`，保证关键接口都有真实断言

4. **阶段 4 (三周后)** - 清理剩余 TODO，全面替换完成
   - 清理零散分布的 TODO

## ✅ 验收标准
- 所有测试用例必须有真实断言，不得存在 TODO 占位
- CI (scripts/check_todo_tests.py) 全绿
- 覆盖率逐步提升，达到 30% → 40% → 50% 的里程碑
