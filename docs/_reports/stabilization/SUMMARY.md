# Stabilization Sprint Summary

## 完成的检查点
1. **Step 0 - 预备动作**：建立分支、日志与 Python 3.11 配置；目录隔离见 `docs/_reports/stabilization/CHECKPOINT_LOG.md`。
2. **Step 1 - 最小 API 启动**：`docker-compose.minimal.yml` + `.env.minimal` 验证 `/health` 返回 200；日志 `01_minimal_api.log`。
3. **Step 2 - pytest 收集**：迁移遗留测试到 `tests/legacy/` 并保留占位用例；日志 `02_pytest_collect.log`。
4. **Step 3 - Ruff 止血**：仅检查致命规则，错误降至 0；日志 `03_ruff_downsizing.log`。
5. **Step 4 - 烟囱用例**：新增 `tests/unit/api/test_health_smoke.py`，生成覆盖率输出 `04_smoke_test.log`。
6. **Step 5 - 安全扫描**：记录高危依赖于 `SECURITY_RISK_ACCEPTED.md`，执行忽略策略后安全扫描通过；日志 `05_security.log`。
7. **Step 6 - 最小 CI**：`.github/workflows/ci.yml` 仅运行 Ruff/Mypy/Smoke；已在看板和日志中登记。
8. **Step 7 - 基本可用测试**：`pytest tests/unit -q` 通过；日志 `07_basic_ready.log`。

## 遗留风险与后续工作
- `tests/legacy/` 下保留了原有单元/集成/E2E 测试与大部分工具脚本，需要在后续迭代中逐批修复并移回主目录。
- `SECURITY_RISK_ACCEPTED.md` 记录的依赖漏洞（mlflow、knack、feast、protobuf、sqlalchemy-utils）需在 D3 阶段完成升级或删除。
- 当前覆盖率仍低（`src/api` 多数模块未执行），但烟囱用例验证了健康检查路径；后续迭代应补充核心功能测试。
- CI 仅执行最小校验，恢复完整流水线前需逐步扩展。

## 建议的下一步
1. 评估 `tests/legacy/` 中优先级最高的模块，逐批恢复并添加新的 smoke/回归测试。
2. 规划依赖升级或替换，特别是 MLflow/Feast 相关功能；缺省情况下保持在隔离状态。
3. 扩展 Ruff 搜查范围，逐步 re-enable 其他规则并修复低级别问题。
4. 在 CI 中逐步追加更多测试矩阵（如 mypy src/utils、更多 pytest 子集）。
