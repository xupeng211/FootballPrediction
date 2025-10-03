# 测试概览报告

## 运行的命令与结果
- `python scripts/run_tests_with_report.py` → 生成 BUGFIX 报告，但内部 `pytest -n` 失败（禁用了 xdist）
- `pytest -q -ra --maxfail=1` → ❌ 导入 `tests/integration/models/test_model_integration.py` 时触发 `IndentationError`
- `pytest -q -ra -n auto --dist=loadscope --cov=src ...` → ❌ `-n` 与 `--dist` 不被允许（`pytest.ini` 禁用了 xdist）
- `pytest tests/unit -k "not slow" -q --maxfail=1`（重复 2 次）→ ❌ `tests/unit/api/test_api_models.py` 出现 `SyntaxError`

## 失败与错误定位
- `tests/integration/models/test_model_integration.py:361`：`IndentationError: unexpected indent`（Prometheus 指标断言块未缩进在测试函数内部）。
- `tests/integration/test_mlflow_database_integration.py:124`：`IndentationError`，`assert experiment_id` 行错位。
- `tests/performance/test_performance_benchmarks.py:92`：`SyntaxError: 'await' outside async function`，异步调用位于普通函数。
- `tests/unit/api/test_api_models.py:140`：`SyntaxError`，`assert` 不在 `try` 块内部；多个断言缩进错误。
- `tests/unit/api/test_api_predictions.py:47-76`、`tests/unit/api/test_api_monitoring.py:84-117`：断言脱离 `try/except` 与 `with` 块，导致语法错误（`black` 同样无法格式化）。

## Flaky / 重复运行
- 两次执行 `pytest tests/unit -k "not slow"` 得到完全相同的导入错误，尚未进入用例执行阶段，无法判定 Flaky。

## 跳过 / xfail
- 本轮所有命令均在收集阶段终止，未产生新的 skip/xfail 统计。

## 覆盖率状态
- 本次执行未生成新的覆盖率；使用最新的 `coverage.xml`（时间戳 2025-09-29 20:39）作为参考：
  - 行覆盖率：17.25%（2072/12013），分支覆盖率：0.5%。
  - Top 20 缺失（按缺失行数排序）：
    1. `src/services/data_processing.py` — 457/503 行未覆盖
    2. `src/data/quality/anomaly_detector.py` — 412/458
    3. `src/cache/redis_manager.py` — 364/429
    4. `src/services/audit_service.py` — 359/359
    5. `src/monitoring/quality_monitor.py` — 323/323
    6. `src/data/storage/data_lake_storage.py` — 296/322
    7. `src/monitoring/anomaly_detector.py` — 248/248
    8. `src/tasks/backup_tasks.py` — 242/242
    9. `src/streaming/kafka_consumer.py` — 242/242
    10. `src/monitoring/alert_manager.py` — 233/233
    11. `src/streaming/kafka_producer.py` — 211/211
    12. `src/monitoring/metrics_collector.py` — 198/248
    13. `src/api/models.py` — 192/192
    14. `src/api/features.py` — 189/189
    15. `src/features/feature_calculator.py` — 188/217
    16. `src/database/connection.py` — 185/282
    17. `src/api/data.py` — 181/181
    18. `src/models/prediction_service.py` — 179/231
    19. `src/models/model_training.py` — 178/208
    20. `src/api/health.py` — 178/178

## 建议下一步
- 先修复导入阶段的语法错误，再重新执行 `pytest -q -ra --maxfail=1`。
- 统一 `pytest.ini` 与辅助脚本的并行参数，避免 `-n` 相关错误。
- 补充高优先级模块（Top 20）测试后重新生成覆盖率。
