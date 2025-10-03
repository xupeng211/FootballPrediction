# 🤖 AI 开发者工作指南

本指南专门为 AI 工具（Claude Code、Cursor、GPT-5-Codex 等）编写，帮助它们在本项目中正确执行测试与修复流程。

---

## 1. 如何找到任务

AI 需要从以下文件中读取任务：
- **看板**: `docs/_reports/TEST_COVERAGE_KANBAN.md`
  - 查看 `🚧 进行中` 的任务
  - 找到当前阶段的目标（如：覆盖率提升、Bug 修复）
- **Bugfix 报告**: `docs/_reports/BUGFIX_REPORT_*.md`
  - 查看最新的错误用例和日志
- **修复计划**: `docs/_reports/COVERAGE_FIX_PLAN.md`
  - 查看低覆盖率文件列表，优先修复或补测

---

## 2. 如何分析问题

- 读取 `pytest` 运行日志，找出 ❌ 错误堆栈
- 确认报错文件、函数、类
- 区分：
  - **语法错误** → 修改源代码
  - **逻辑错误** → 修改实现逻辑
  - **测试缺失** → 编写/补充测试用例

---

## 3. 如何修复 bug

修复步骤：
1. 修改对应源代码或测试文件
2. 本地运行测试：
   ```bash
   pytest --maxfail=5 --disable-warnings -q --cov=. --cov-report=term-missing
   ```

3. 确保：
   - 所有测试用例通过 ✅
   - 覆盖率不下降（最好增加）

---

## 4. 如何提交 PR

AI 修复完成后，必须遵循以下流程：

1. 创建分支：
   ```bash
   git checkout -b fix/bug-<timestamp>
   ```

2. 提交修改：
   ```bash
   git add src/ tests/
   git commit -m "fix: auto bugfix from BUGFIX_REPORT_xxx"
   git push origin HEAD
   ```

3. 创建 PR：
   ```bash
   gh pr create --base main --head fix/bug-<timestamp> \
     --title "fix: auto bugfix from BUGFIX_REPORT_xxx" \
     --body "Automated bugfix based on latest Bugfix Report."
   gh pr merge --squash --auto
   ```

---

## 5. 循环闭环

AI 应该始终遵循以下闭环：

1. 运行测试 → 生成 Bugfix 报告
2. 从 Bugfix 报告读取任务
3. 自动修复并提交 PR
4. 更新 Kanban & Dashboard
5. 重复步骤 1，直到没有失败用例且覆盖率达到目标

---

## 6. 质量标准

- 所有修复必须通过 **Test Guard CI**
- 禁止提交包含 `TODO` 占位符的测试
- 每次迭代必须更新 **Kanban** 和 **Dashboard**

---

📝 提示：本指南就是 AI 的"操作说明书"，任何 AI 工具都应严格遵循以上流程执行。