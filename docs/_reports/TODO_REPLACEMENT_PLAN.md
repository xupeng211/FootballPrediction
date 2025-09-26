# 📝 TODO Replacement Plan

本计划旨在分阶段替换所有测试文件中的 TODO 占位符，确保测试断言逐步从占位过渡到真实业务逻辑验证。

## 📊 当前统计
- 总计 TODO 占位符: **97**
- 受影响的测试文件数: **66**

## 📂 文件分布
- tests/unit/test_scripts_cursor_runner.py: 1 个 TODO
- tests/unit/test_setup.py: 1 个 TODO
- tests/unit/test_src_tasks_streaming_tasks.py: 1 个 TODO
- tests/unit/test_src_models_prediction_service.py: 1 个 TODO
- tests/unit/test_scripts_retrain_pipeline.py: 1 个 TODO
- tests/unit/test_src_data_features_examples.py: 10 个 TODO
- tests/unit/test_src_streaming_stream_processor.py: 1 个 TODO
- tests/unit/test_scripts_setup_project.py: 1 个 TODO
- tests/unit/test_src_tasks_backup_tasks.py: 1 个 TODO
- tests/unit/test_src_data_quality_anomaly_detector.py: 1 个 TODO
- tests/unit/test_src_data_quality_data_quality_monitor.py: 1 个 TODO
- tests/unit/test_scripts_fix_critical_issues.py: 1 个 TODO
- tests/unit/test_src_monitoring_alert_manager.py: 1 个 TODO
- tests/unit/test_src_data_quality_exception_handler.py: 1 个 TODO
- tests/unit/test_src_tasks_error_logger.py: 1 个 TODO
- tests/unit/test_src_data_collectors_scores_collector.py: 1 个 TODO
- tests/unit/test_src_data_collectors_base_collector.py: 1 个 TODO
- tests/unit/test_src_data_collectors_odds_collector.py: 1 个 TODO
- tests/unit/test_src_data_storage_data_lake_storage.py: 1 个 TODO
- tests/unit/test_src_data_quality_ge_prometheus_exporter.py: 1 个 TODO
- tests/unit/test_scripts_ci_guardian.py: 1 个 TODO
- tests/unit/test_scripts_project_template_generator.py: 1 个 TODO
- tests/unit/test_src_data_quality_great_expectations_config.py: 1 个 TODO
- tests/unit/test_scripts_analyze_dependencies.py: 1 个 TODO
- tests/unit/test_src_services_data_processing.py: 1 个 TODO
- tests/unit/test_scripts_alert_verification_mock.py: 1 个 TODO
- tests/unit/test_scripts_ci_issue_analyzer.py: 1 个 TODO
- tests/unit/test_src_streaming_kafka_producer.py: 1 个 TODO
- tests/unit/test_src_monitoring_metrics_exporter.py: 1 个 TODO
- tests/unit/test_src_cache_redis_manager.py: 1 个 TODO
- tests/unit/test_src_data_features_feature_store.py: 1 个 TODO
- tests/unit/test_scripts_alert_verification.py: 1 个 TODO
- tests/unit/test_src_lineage_metadata_manager.py: 1 个 TODO
- tests/unit/test_scripts_update_predictions_results.py: 1 个 TODO
- tests/unit/test_scripts_demo_ci_guardian.py: 1 个 TODO
- tests/unit/test_src_tasks_monitoring.py: 10 个 TODO
- tests/unit/test_src_tasks_data_collection_tasks.py: 1 个 TODO
- tests/unit/test_src_tasks_utils.py: 4 个 TODO
- tests/unit/test_src_data_processing_football_data_cleaner.py: 1 个 TODO
- tests/unit/test_src_data_collectors_streaming_collector.py: 1 个 TODO
- tests/unit/test_scripts_auto_ci_updater.py: 1 个 TODO
- tests/unit/test_scripts_sync_issues.py: 1 个 TODO
- tests/unit/test_src_features_feature_calculator.py: 1 个 TODO
- tests/unit/test_scripts_quality_checker.py: 1 个 TODO
- tests/unit/test_scripts_defense_generator.py: 1 个 TODO
- tests/unit/test_scripts_context_loader.py: 1 个 TODO
- tests/unit/test_src_monitoring_quality_monitor.py: 1 个 TODO
- tests/unit/test_scripts_materialized_views_examples.py: 1 个 TODO
- tests/unit/test_scripts_feast_init.py: 1 个 TODO
- tests/unit/test_src_lineage_lineage_reporter.py: 1 个 TODO
- tests/unit/test_scripts_defense_validator.py: 1 个 TODO
- tests/unit/test_src_tasks_maintenance_tasks.py: 1 个 TODO
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

## 🚀 分阶段替换策略
1. **阶段 1 (本周)** - 清理 20 个 TODO，占比约 25%
   - 优先处理 `scripts/` 相关测试（完全无覆盖 → 业务关键）

2. **阶段 2 (下周)** - 再清理 20 个 TODO
   - 覆盖 `apps/trainer/` 和 `apps/backtest/` 测试（高复杂度模块）

3. **阶段 3 (两周后)** - 再清理 20 个 TODO
   - 针对 `apps/api/` 和 `apps/data_pipeline/`，保证关键接口都有真实断言

4. **阶段 4 (三周后)** - 清理剩余 TODO，全面替换完成
   - 清理零散分布的 TODO

## ✅ 验收标准
- 所有测试用例必须有真实断言，不得存在 TODO 占位
- CI (scripts/check_todo_tests.py) 全绿
- 覆盖率逐步提升，达到 30% → 40% → 50% 的里程碑
