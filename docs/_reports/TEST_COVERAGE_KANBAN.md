# 📝 Test Coverage Improvement Kanban

本看板用于追踪 **TODO 替换** 与 **测试覆盖率提升** 的进度，由 AI 工具和开发者共同维护。
规则：
1. AI 执行任务前，必须先读取本文件，找到「🚧 进行中」任务。
2. 任务完成后，必须更新状态（移到 ✅ 已完成，并把下一个任务移到 🚧 进行中）。
3. 确保覆盖率目标逐步提升，TODO 替换逐步清零。

---

## 📊 当前目标
- 覆盖率阶段目标: 30% → 40% → 50% → 80%
- TODO 替换目标: 97 → 0
- 当前完成率: 40.2%

---

## ✅ 已完成
- [x] Phase 1: 替换 scripts 模块的 20 个 TODO (PR #31)
- [x] Phase 2: 替换 src/tasks 和 src/models 模块的 19 个 TODO (PR #32)

---

## 🚧 进行中
- [ ] Phase 3: 替换 apps/api 和 apps/data_pipeline 模块的 20 个 TODO
  ⏳ 状态: 待执行
  📂 涉及目录: tests/unit/test_apps_api*.py, tests/unit/test_apps_data_pipeline*.py
  🎯 覆盖率提升预期: +5%

---

## 📅 待办
- [ ] Phase 4: 替换 src/data 和 src/monitoring 模块的 20 个 TODO
  📂 涉及目录: tests/unit/test_src_data*.py, tests/unit/test_src_monitoring*.py
  🎯 覆盖率提升预期: +5%

- [ ] Phase 5: 替换剩余零散 TODO (约 18 个)
  📂 涉及目录: tests/unit/test_misc*.py
  🎯 覆盖率提升预期: +2% ~ +3%