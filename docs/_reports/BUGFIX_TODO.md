# 🐞 AI Bugfix TODO Board

自动更新于: 2025-09-29 21:29:49

## 📊 来源报告
- 深度体检: DEEP_DIAG_REPORT.md
- 测试概览: TEST_SUMMARY.md
- 依赖扫描: DEPENDENCY_ISSUES.md

## ✅ 已完成任务
- [x] 历史：修复 pytest 配置冲突与多处缩进语法错误（2025-09-27）

## 🚨 阻塞级（优先级: BLOCKER）
- [ ] 修复 `tests/integration/models/test_model_integration.py:352-368` 缩进错误，恢复导入（`pytest -q -k model_integration`）
- [ ] 修复 `tests/integration/test_mlflow_database_integration.py:120-133` 缩进错误，确保 MLflow 集成测试可导入
- [ ] 修复 `tests/unit/api/test_api_models.py:136-169`、`tests/unit/api/test_api_predictions.py:43-78`、`tests/unit/api/test_api_monitoring.py:78-118` 的 try/except 缩进与断言位置
- [ ] 将 `tests/performance/test_performance_benchmarks.py:86-104` 中的同步函数改为 `async def` 或移除 `await`

## ⚠️ 重要问题（优先级: MAJOR）
- [ ] 评估 `pytest.ini` 中 `-p no:xdist` 与脚本默认 `-n auto` 的冲突，统一并更新 `scripts/run_tests_with_report.py`
- [ ] 替换 `src/database/sql_compatibility.py:222-290` 及监控模块的字符串拼接 SQL，改为参数化查询
- [ ] 升级 `knack>=0.12.1`、`feast` 等存在 CVE 的依赖，执行 `pip install --upgrade knack feast` 并复测
- [ ] 针对 `coverage.xml` Top 20 零覆盖模块补充测试（如 `src/api/data.py`, `src/services/data_processing.py`）

## 🟢 快速收益（Quick Wins）
- [ ] 运行 `ruff check tests/unit/api` 聚焦修复语法提示
- [ ] 使用 `python scripts/fix_test_syntax.py`（如可用）对自动生成测试进行批量校验
- [ ] 在 `.env.template` 与 `env.example` 中补充缺失的只读/读写数据库账号占位符

## 📌 推荐执行命令
```bash
python scripts/run_tests_with_report.py
pytest -q -ra --maxfail=1
python scripts/generate_fix_plan.py
```
