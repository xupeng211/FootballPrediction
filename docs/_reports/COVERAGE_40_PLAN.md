# 🚀 Coverage Improvement Plan → 40%

- 基线时间：2025-09-27 02:55:56
- 当前覆盖率：**7.7%**
- 阶段目标：**提升至 ≥ 40%**

## 优先清单（按收益排序）
| 次序 | 文件 | 覆盖率 | 语句数 | 建议用例 |
|------|------|--------|--------|----------|
| 1 | scripts/defense_validator.py | 0.0% | 504 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 2 | scripts/auto_ci_updater.py | 0.0% | 379 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 3 | src/services/audit_service.py | 0.0% | 359 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 4 | tests/external_mocks.py | 0.0% | 329 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 5 | src/monitoring/quality_monitor.py | 0.0% | 323 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 6 | scripts/ci_issue_analyzer.py | 0.0% | 316 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 7 | tests/unit/streaming_kafka_consumer_batch_gamma_.py | 0.0% | 307 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 8 | scripts/ci_guardian.py | 0.0% | 301 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 9 | comprehensive_mcp_health_check.py | 0.0% | 290 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 10 | test_metrics_collector.py | 0.0% | 287 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 11 | scripts/retrain_pipeline.py | 0.0% | 275 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 12 | test_lineage_reporter.py | 0.0% | 274 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 13 | test_feature_calculator.py | 0.0% | 273 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 14 | tests/unit/data_storage_data_lake_storage_batch_gamma_.py | 0.0% | 271 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |
| 15 | test_kafka_producer.py | 0.0% | 269 | 核心函数最小化输入/输出 + 异常分支 + 边界值；mock I/O/网络/DB |

## 执行步骤
1. 按上表顺序为每个文件补充 2–4 个高价值用例（命中主干分支和异常分支）。
2. 使用 `pytest -k <模块名> --maxfail=1 -q` 就近迭代。
3. 完成一批后运行 `pytest --cov --cov-report=term-missing --cov-report=json:coverage.json` 更新覆盖率。
4. 达到 ≥40% 后，更新 Kanban：本阶段移至 ✅ 已完成，并将下一阶段（40%→50%）置为 🚧 进行中。