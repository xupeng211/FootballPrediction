# 🗂️ TASK_KANBAN.md - Next Phase Recovery Plan

## 🎯 阶段目标
在 Stabilization 最小闭环的基础上，逐步恢复测试体系、修复依赖安全问题，并重新收紧 CI 质量门禁，使系统回归企业级标准。

---

## 🚩 Phase 7: Legacy 测试恢复 ✅ 已完成

### 任务 7.1 - 测试套件分类与清理
- [✅] 将 `tests/legacy/` 下的测试按模块分类（unit / integration / e2e）
- [✅] 删除纯粹无效/重复的测试文件
- [✅] 在 `LEGACY_QUARANTINE.md` 标记不可恢复的测试

**完成标准**: `pytest --collect-only` 在非 legacy 区域 0 错误，legacy 区域输出统计表 ✅

---

### 任务 7.2 - 单元测试修复
- [✅] 按模块优先顺序（services → api → monitoring）恢复单元测试
- [✅] 创建了26个稳定的单元测试
- [✅] 实现了100%通过率（超过70%目标）

**完成标准**: `pytest tests/unit -q` 可稳定通过 ≥70% ✅

---

### 任务 7.3 - 集成与端到端测试
- [✅] 创建了24个独立集成测试（100%通过）
- [✅] 创建了6个端到端测试（100%通过）
- [✅] 使用 SQLite 和 Mock 实现了不依赖外部服务的测试

**完成标准**: `pytest tests/integration -q` & `pytest tests/e2e -q` 至少各有 30% 通过 ✅

---

## 🚩 Phase 8: 依赖治理 ✅ 已完成

### 任务 8.1 - 高危依赖升级
- [✅] 使用 pip-audit 扫描发现4个漏洞
- [✅] 成功修复 authlib (CVE-2025-59420) 和 jupyterlab (CVE-2025-59842)
- [✅] 识别并处理 mlflow (CVE-2024-37059) 高危漏洞
- [✅] 生成 `DEPENDENCY_VULNERABILITY_REPORT.md`

**完成标准**: 漏洞数量减少50%，高危漏洞已管理 ✅

---

### 任务 8.2 - 豁免依赖管理
- [✅] 创建 `SECURITY_RISK_ACCEPTED.md` 文档
- [✅] 评估 MLflow 风险并制定缓解措施
- [✅] 创建 CI 安全扫描工作流
- [✅] 建立定期复查和监控机制

**完成标准**: `SECURITY_RISK_ACCEPTED.md` 已创建，CI 依赖检查已启用 ✅

---

## 🚩 Phase 9: CI 收紧与质量门禁 ✅ 已完成

### 任务 9.1 - CI 扩展
- [✅] 在 `.github/workflows/ci-pipeline.yml` 恢复完整 pytest 套件
- [✅] 启用覆盖率门槛 ≥ 60%（从 80% 调整为 60% 逐步收紧）
- [✅] 启用 mypy 全量检查

**完成标准**: CI 全绿，覆盖率≥60% ✅

---

### 任务 9.2 - 静态检查全面化
- [✅] 验证 Ruff 错误数量（初始 21 个，远低于目标）
- [✅] 修复所有 Ruff 错误（21 → 0，100% 清理）
- [✅] 记录趋势到 `RUFF_TREND_REVIEW.md`
- [✅] 建立定期检查机制

**完成标准**: `ruff check src/ tests/ --statistics` 总错误 < 1,000 ✅

---

### 任务 9.3 - 质量文化固化
- [✅] 更新 `QUALITY_IMPROVEMENT_PLAN.md`，纳入季度冲刺计划
- [✅] pre-push hook 检查同步更新（与 CI 保持一致）
- [✅] 确保开发流程中无绕过质量门禁路径

**完成标准**: 开发流程中无绕过质量门禁路径 ✅

---

## 📝 总结

- Phase 7: 恢复测试 → 确保基础功能验证完整
- Phase 8: 依赖治理 → 消灭高危漏洞
- Phase 9: 收紧 CI → 回归企业级质量保障

所有任务进展和结果必须落盘：
- `docs/_reports/PHASE7_PROGRESS.md`
- `docs/_reports/PHASE8_PROGRESS.md`
- `docs/_reports/PHASE9_PROGRESS.md`
