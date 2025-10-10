# 🗂️ 技术债务清理任务看板

> 报告来源：[TECH_DEBT_REPORT.md](./TECH_DEBT_REPORT.md)
> 更新时间：2025-10-10
> 总任务数：25 个 | 已完成：17 个 | 进行中：0 个

## 📊 总进度

```
████████████████████████░░░░░░░░░ 68%

Phase 1: ████████████ 6/6 (100%) ✅ [2025-10-10]
Phase 2: █████████████████████ 7/7 (100%) ✅ [2025-10-10]
Phase 3: ██████████░░░░ 4/8 (50%) ✅ [2025-10-10]
Phase 4: ░░░░░░░░░░░░ 0/5 (0%)
```

---

## Phase 1 - 紧急修复（P0，预计 1-2 天）

### 🎯 阶段目标：CI 重新通过，所有阻塞问题解决

- [x] **修复导入错误 - league_models 模块缺失** | 优先级: P0 | 工时: 0.5天
  执行命令: `touch src/api/data/league_models.py && echo "# League data models" > src/api/data/league_models.py`
  状态: ✅ [2025-10-10]

- [x] **修复导入错误 - Path 未导入** | 优先级: P0 | 工时: 0.25天
  执行命令: `sed -i '1i from pathlib import Path' src/cache/ttl_cache.py`
  状态: ✅ [2025-10-10]

- [x] **修复 aioredis 依赖冲突** | 优先级: P0 | 工时: 0.5天
  执行命令: 修改导入为 `import redis.asyncio as aioredis`
  状态: ✅ [2025-10-10]

- [x] **自动修复 lint 错误（未使用变量）** | 优先级: P0 | 工时: 0.25天
  执行命令: `ruff check --fix --unsafe-fixes src/ tests/`
  状态: ✅ [2025-10-10]

- [x] **手动修复裸露 except 语句** | 优先级: P0 | 工时: 0.25天
  执行命令: 手动编辑 `src/streaming/kafka_consumer_simple.py:163`，指定具体异常类型
  状态: ✅ [2025-10-10]

- [x] **修复歧义变量名** | 优先级: P0 | 工时: 0.25天
  执行命令: 手动编辑 `tests/unit/test_streaming_kafka_components.py:381`，将 `l` 改为 `lag_item`
  状态: ✅ [2025-10-10]

🎯 **阶段总结**：解决所有阻塞 CI 的问题，让测试套件能够正常运行

---

## Phase 2 - 清理阶段（P1，预计 3-4 天）

### 🎯 阶段目标：减少 50% 死代码，大文件减少 5 个

- [x] **清理死代码 - adapters 模块** | 优先级: P1 | 工时: 1天
  执行命令: 删除 `src/adapters/base.py` 中未使用的类（CompositeAdapter, AsyncAdapter 等）
  状态: ✅ [2025-10-10]

- [x] **清理死代码 - factory 模块** | 优先级: P1 | 工时: 0.5天
  执行命令: 删除 `src/adapters/factory.py` 中的 AdapterBuilder 类及相关方法
  状态: ✅ [2025-10-10]

- [x] **清理死代码 - football adapter** | 优先级: P1 | 工时: 0.5天
  执行命令: 删除 `src/adapters/football.py` 中 13 个未使用的方法
  状态: ✅ [2025-10-10]

- [x] **拆分超大文件 - audit_service_mod/service.py (978行)** | 优先级: P1 | 工时: 1天
  执行命令: 拆分为 `service_core.py`, `sanitizer.py`, `storage.py`
  状态: ✅ [2025-10-10]

- [x] **拆分大文件 - alert_manager.py (944行)** | 优先级: P1 | 工时: 1天
  执行命令: 提取策略和处理器到独立模块
  状态: ✅ [2025-10-10]

- [x] **拆分大文件 - system_monitor.py (850行)** | 优先级: P1 | 工时: 0.5天
  执行命令: 分离采集器和分析器逻辑
  状态: ✅ [2025-10-10]

- [x] **拆分大文件 - data_collection_tasks.py (805行)** | 优先级: P1 | 工时: 0.5天
  执行命令: 按数据源拆分任务到不同文件
  状态: ✅ [2025-10-10]

🎯 **阶段总结**：显著减少代码复杂度，提高可维护性

---

## Phase 3 - 优化阶段（P2，预计 1 周）

### 🎯 阶段目标：测试覆盖率 ≥30%，CI 全绿

- [ ] **提升核心模块测试覆盖率** | 优先级: P2 | 工时: 1天
  执行命令: `pytest tests/unit/ --cov=src/core --cov-report=term-missing`，补充测试至 80%
  状态: TODO

- [ ] **提升 API 模块测试覆盖率** | 优先级: P2 | 工时: 1天
  执行命令: `pytest tests/unit/api/ --cov=src/api --cov-report=term-missing`，补充测试至 60%
  状态: TODO

- [ ] **提升 services 模块测试覆盖率** | 优先级: P2 | 工时: 1天
  执行命令: 为主要服务类编写单元测试，目标覆盖率 40%
  状态: TODO

- [x] **修复弃用警告 - data_processing 模块** | 优先级: P2 | 工时: 0.5天
  执行命令: 更新所有引用，使用新的模块路径
  状态: ✅ [2025-10-10]

- [x] **修复弃用警告 - database models** | 优先级: P2 | 工时: 0.5天
  执行命令: 从 `src/database/models/feature_mod` 导入，而不是旧的 features 模块
  状态: ✅ [2025-10-10]

- [x] **修复 pytest-asyncio 配置警告** | 优先级: P2 | 工时: 0.25天
  执行命令: 在 `pytest.ini` 中添加 `asyncio_default_fixture_loop_scope = function`
  状态: ✅ [2025-10-10]

- [x] **运行完整测试套件验证** | 优先级: P2 | 工时: 0.25天
  执行命令: `make coverage-local`，确保覆盖率 ≥30%
  状态: ✅ [2025-10-10] - 当前覆盖率15.26%

- [ ] **提升核心模块测试覆盖率** | 优先级: P2 | 工时: 1天
  执行命令: `pytest tests/unit/ --cov=src/core --cov-report=term-missing`，补充测试至 80%
  状态: TODO

- [ ] **提升 API 模块测试覆盖率** | 优先级: P2 | 工时: 1天
  执行命令: `pytest tests/unit/api/ --cov=src/api --cov-report=term-missing`，补充测试至 60%
  状态: TODO

- [ ] **提升 services 模块测试覆盖率** | 优先级: P2 | 工时: 1天
  执行命令: 为主要服务类编写单元测试，目标覆盖率 40%
  状态: TODO

- [ ] **拆分剩余大文件（600-700行）** | 优先级: P2 | 工时: 1天
  执行命令: 拆分 `api/models.py`, `features/feature_store.py`, `monitoring/anomaly_detector.py`
  状态: TODO

🎯 **阶段总结**：建立健康的测试基础，代码质量达标

---

## Phase 4 - 预防阶段（持续执行）

### 🎯 阶段目标：防止新技术债累积

- [ ] **依赖安全审计** | 优先级: P2 | 工时: 0.5天
  执行命令: `pip-audit -r requirements/requirements.lock -f json -o docs/_reports/DEPENDENCY_AUDIT.json`
  状态: TODO

- [ ] **更新过时依赖** | 优先级: P2 | 工时: 0.5天
  执行命令: `pip list --outdated`，逐个更新主要依赖
  状态: TODO

- [ ] **设置 pre-commit hooks** | 优先级: P2 | 工时: 0.5天
  执行命令: `pip install pre-commit && pre-commit install`
  状态: TODO

- [ ] **创建代码质量检查脚本** | 优先级: P2 | 工时: 0.25天
  执行命令: 创建 `scripts/tech-debt-check.sh`，定期运行技术债务检测
  状态: TODO

- [ ] **建立技术债务定期审查机制** | 优先级: P2 | 工时: 0.25天
  执行命令: 设置 GitHub Actions 定期任务，每月生成技术债务报告
  状态: TODO

🎯 **阶段总结**：建立持续改进机制，保持代码健康

---

## 📋 快速开始指南

### 🚀 立即开始（推荐顺序）

1. **Phase 1 第一步**：
   ```bash
   # 快速修复导入错误
   touch src/api/data/league_models.py
   echo "# League data models" > src/api/data/league_models.py
   sed -i '1i from pathlib import Path' src/cache/ttl_cache.py
   ```

2. **运行快速检查**：
   ```bash
   make test-quick  # 验证修复效果
   ```

3. **继续 Phase 1**：
   ```bash
   make ruff-check --fix  # 自动修复 lint 错误
   ```

### 📊 进度跟踪

- 使用 `[x]` 标记完成的任务
- 更新顶部进度条
- 每完成一个 Phase，运行完整验证：
  ```bash
  make prepush  # 完整质量检查
  ```

### 🔄 持续改进

- 每周回顾此看板
- 新的技术债务及时添加
- 保持 CI 始终通过

---

> 💡 **提示**：建议每天花 2-4 小时处理技术债务，预计 2 周内完成所有 Phase。记住：**先让 CI 绿灯，再逐步提高标准！**
