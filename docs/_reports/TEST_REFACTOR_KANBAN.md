# 📝 Test Refactor Kanban

本看板用于推进单测/集成测试体系的重构。状态说明：
- 🟢 已完成
- 🟡 进行中
- ⚪ 待开始
- 🔴 阻塞

## Phase 1 – 稳固入口
1. 🟢 在 `tests/conftest.py` 建立全局 Mock fixture，统一替换 MLflow、Redis、Kafka、外部 HTTP 客户端。
2. 🟢 新增 `tests/helpers/` 工具模块（内存 SQLite、MLflow stub、Redis stub 等），并在改造后的测试中引用。
3. 🟢 为遗留测试打标记：将依赖真实服务的用例标记为 `@pytest.mark.legacy`，在 CI 默认跳过。
4. 🟢 在 CI 新增基础覆盖率流水线（针对已 Mock 的目录执行 `pytest --cov`）。

## Phase 2 – 分批清理单测
1. 🟢 整理 `tests/unit/api`：迁移遗留单测到 Mock 架构、去除真连接依赖。
2. 🟢 整理 `tests/unit/services`：使用统一 fixture、内存数据库；迁移完成后移除 legacy 标记。
3. 🟢 整理 `tests/unit/database` 与相关工具模块，统一走 SQLite 工具。
4. 🟢 对保留的真实依赖测试迁移至 `tests/legacy/` 并文档化运行指南。

## Phase 3 – 全量覆盖率与真实环境
1. 🟢 恢复全量 `pytest tests/unit --cov`，将覆盖率结果纳入 CI，并设定初始阈值（40%）。
2. 🟢 为真实依赖测试建立独立 job（docker compose 启动 Postgres/Redis/MLflow），拟定执行频率。
3. 🟢 更新文档（`docs/TEST_GUIDE.md`）：说明三层测试结构、运行命令、依赖准备步骤。
4. 🟢 评估覆盖率阈值提升路线（例如 40%→50%），并制定后续迭代计划。

---

> 本看板将在每个阶段推进时更新状态，并附上对应 PR/脚本链接。
