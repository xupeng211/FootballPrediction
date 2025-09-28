# 🧪 Kanban Audit 故意破坏场景指南

## 1. 目的

验证 `kanban-audit.yml` 工作流在出现配置错误或文件缺失时，能否正确输出 ❌ 并生成详细的审计报告。

**核心目标**：
- 测试工作流的错误检测能力
- 验证报告生成机制的鲁棒性
- 确保合并不会被审计失败阻塞
- 检查修复建议的准确性

---

## 2. 测试场景

### 场景 1: 删除 Kanban 文件
**测试目标**: 验证核心看板文件缺失检测

**操作步骤**：
```bash
# 删除 Kanban 看板文件
rm docs/_reports/TEST_OPTIMIZATION_KANBAN.md

# 创建测试分支
git checkout -b test-break-kanban-file

# 提交破坏性修改
git add .
git commit -m "test: break scenario 1 - remove kanban file"

# 推送到远程
git push origin test-break-kanban-file
```

**预期结果**：
- ✅ 审计报告中标注 ❌ Kanban 文件缺失
- ✅ CI 日志输出红色 ❌ 和具体原因
- ✅ 合并仍然允许，不被阻塞
- ✅ 报告生成并自动提交

**审计报告应包含**：
```markdown
- ❌ **文件 docs/_reports/TEST_OPTIMIZATION_KANBAN.md 是否存在**
  *原因: Kanban 看板文件不存在*
```

---

### 场景 2: 注释掉 pre-commit hook
**测试目标**: 验证本地 hook 检测机制

**操作步骤**：
```bash
# 注释 pre-commit hook 内容
echo "# Disabled for testing" > .git/hooks/pre-commit

# 创建测试分支
git checkout -b test-break-pre-commit

# 提交破坏性修改
git add .git/hooks/pre-commit
git commit -m "test: break scenario 2 - disable pre-commit hook"

# 推送到远程
git push origin test-break-pre-commit
```

**预期结果**：
- ✅ 审计报告中标注 ❌ pre-commit hook 缺少检查逻辑
- ✅ 给出修复建议：恢复 hook 检查逻辑
- ✅ 不影响其他检查项的执行

**审计报告应包含**：
```markdown
- ❌ **pre-commit hook 是否包含检查逻辑**
  *原因: pre-commit hook 缺少检查逻辑*
```

---

### 场景 3: 删除 Makefile 目标
**测试目标**: 验证工具链完整性检查

**操作步骤**：
```bash
# 注释或删除 setup-hooks 目标
sed -i '/^setup-hooks:/,/^[a-z_-]*:/ s/^setup-hooks:/# setup-hooks:/' Makefile

# 创建测试分支
git checkout -b test-break-makefile-target

# 提交破坏性修改
git add Makefile
git commit -m "test: break scenario 3 - remove setup-hooks target"

# 推送到远程
git push origin test-break-makefile-target
```

**预期结果**：
- ✅ 审计报告中标注 ❌ setup-hooks 目标缺失
- ✅ 给出修复建议：恢复目标定义
- ✅ 其他 Makefile 目标检查正常

**审计报告应包含**：
```markdown
- ❌ **Makefile 是否有 setup-hooks 目标**
  *原因: Makefile 缺少 setup-hooks 目标*
```

---

### 场景 4: 删除 CI 缓存配置
**测试目标**: 验证 CI 优化配置检查

**操作步骤**：
```bash
# 注释掉缓存步骤
sed -i '/- name: Cache hooks and Kanban file/,/^$/ s/^/#/' .github/workflows/kanban-check.yml

# 创建测试分支
git checkout -b test-break-ci-cache

# 提交破坏性修改
git add .github/workflows/kanban-check.yml
git commit -m "test: break scenario 4 - disable CI cache"

# 推送到远程
git push origin test-break-ci-cache
```

**预期结果**：
- ✅ 审计报告中标注 ❌ 缓存配置缺失
- ✅ 日志提示 "cache step not found"
- ✅ 其他 CI 检查项继续执行

**审计报告应包含**：
```markdown
- ❌ **是否有统一的缓存步骤**
  *原因: 缺少统一的缓存步骤*
```

---

### 场景 5: 删除 README 徽章
**测试目标**: 验证项目集成完整性

**操作步骤**：
```bash
# 删除 Test Improvement Guide 徽章
sed -i '/Test Improvement Guide.*blue/d' README.md

# 创建测试分支
git checkout -b test-break-readme-badge

# 提交破坏性修改
git add README.md
git commit -m "test: break scenario 5 - remove readme badge"

# 推送到远程
git push origin test-break-readme-badge
```

**预期结果**：
- ✅ 审计报告中标注 ❌ 缺少指南徽章
- ✅ 提示需补回链接
- ✅ 其他 README 集成检查正常

**审计报告应包含**：
```markdown
- ❌ **README.md 顶部是否有 Test Improvement Guide 徽章**
  *原因: 缺少指南徽章*
```

---

### 场景 6: 综合破坏测试
**测试目标**: 验证多错误同时检测能力

**操作步骤**：
```bash
# 同时执行多个破坏操作
rm docs/_reports/TEST_OPTIMIZATION_KANBAN.md
echo "# Disabled" > .git/hooks/pre-commit
sed -i '/^setup-hooks:/ s/^/#/' Makefile

# 创建测试分支
git checkout -b test-break-multiple

# 提交破坏性修改
git add .
git commit -m "test: break scenario 6 - multiple failures"

# 推送到远程
git push origin test-break-multiple
```

**预期结果**：
- ✅ 审计报告中标注多个 ❌ 项目
- ✅ 每个错误都有明确的修复建议
- ✅ 通过率正确计算（例如：21/25 = 84%）
- ✅ 合并仍然不被阻塞

---

## 3. 操作步骤

### 3.1 准备阶段
1. **备份当前状态**：
   ```bash
   git checkout main
   git branch -b backup-before-break-tests
   ```

2. **选择测试场景**：
   - 从上述 6 个场景中选择一个
   - 建议从简单场景开始，逐步增加复杂度

### 3.2 执行测试
1. **创建破坏性修改**：
   ```bash
   # 执行选定场景的破坏操作
   # 创建专用测试分支
   git checkout -b test-break-[scenario-name]
   ```

2. **提交并推送**：
   ```bash
   git add .
   git commit -m "test: break scenario [number] - [description]"
   git push origin test-break-[scenario-name]
   ```

3. **创建 PR**：
   - 在 GitHub 上创建 PR
   - PR 标题：`test: [scenario] - audit break test`
   - PR 描述说明这是破坏性测试

4. **合并 PR**：
   - 合并以触发 `kanban-audit` 工作流
   - 观察工作流执行日志

### 3.3 验证结果
1. **检查工作流日志**：
   - 访问 GitHub Actions 页面
   - 查看 `kanban-audit` job 执行日志
   - 确认错误检测和报告生成

2. **检查审计报告**：
   ```bash
   # 查看生成的审计报告
   cat docs/_reports/TEST_IMPROVEMENT_AUDIT.md
   ```

3. **验证修复建议**：
   - 确认每个 ❌ 都有具体原因
   - 检查修复建议是否实用

### 3.4 恢复环境
1. **恢复被破坏的文件**：
   ```bash
   git checkout main
   # 恢复到破坏前的状态
   ```

2. **清理测试分支**：
   ```bash
   git branch -D test-break-[scenario-name]
   git push origin --delete test-break-[scenario-name]
   ```

---

## 4. 验证标准

### 4.1 必须通过的检查项
- ✅ **CI 不报错退出**：即使有审计失败，工作流仍成功完成
- ✅ **报告必须生成**：`docs/_reports/TEST_IMPROVEMENT_AUDIT.md` 文件存在
- ✅ **错误标注正确**：报告中必须包含 ❌ 并写明原因
- ✅ **修复建议明确**：每个错误都有具体的修复指导
- ✅ **合并不被阻塞**：PR 合并过程不受审计结果影响

### 4.2 期望的审计结果
```markdown
## 📈 审计统计
- **总检查项**: 25
- **通过项**: [具体数字]
- **失败项**: [具体数字]
- **通过率**: [计算出的百分比]%

## 🎯 审计结论
⚠️ **发现 [X] 个问题需要修复。**

### 🔧 待修复任务
请根据上述 ❌ 标记的检查项进行修复：
1. 优先修复影响核心功能的问题
2. 确保所有文件和配置正确
3. 验证修复后的功能正常工作
```

### 4.3 日志验证点
工作流日志应包含：
- ✅ 详细的逐项检查过程
- ✅ 清晰的 ✅/❌ 标识
- ✅ 失败项目的具体原因
- ✅ 最终的通过率统计
- ✅ 报告提交成功的确认

---

## 5. 测试记录

### 测试执行记录
| 场景 | 执行时间 | PR编号 | 通过率 | 预期vs实际 | 备注 |
|------|----------|--------|--------|-------------|------|
| 场景1 | [待执行] | - | - | - | 未执行 |
| 场景2 | [待执行] | - | - | - | 未执行 |
| 场景3 | [待执行] | - | - | - | 未执行 |
| 场景4 | [待执行] | - | - | - | 未执行 |
| 场景5 | [待执行] | - | - | - | 未执行 |
| 场景6 | [待执行] | - | - | - | 未执行 |

### 问题记录
- **[待记录]**: 发现的问题和解决方案
- **[待记录]**: 工作流优化建议
- **[待记录]**: 测试过程中的经验总结

---

## 6. 最佳实践

### 6.1 测试顺序建议
1. **场景1** → **场景2** → **场景3** → **场景4** → **场景5** → **场景6**
2. 每次只测试一个场景，避免混淆结果
3. 完成一个场景后，完全恢复环境再测试下一个

### 6.2 安全注意事项
- **不要在主分支直接执行破坏操作**
- **测试前创建备份**
- **测试后及时清理**
- **避免影响其他开发者的工作**

### 6.3 文档维护
- 每次测试后更新记录表格
- 记录发现的问题和解决方案
- 根据测试结果优化工作流逻辑

---

## 7. 故障排除

### 7.1 常见问题
**问题**: 工作流根本没有触发
- **原因**: PR 没有正确合并
- **解决**: 确认 PR 的 merged 状态为 true

**问题**: 审计报告没有生成
- **原因**: 权限问题或路径错误
- **解决**: 检查 GitHub Actions 写入权限

**问题**: 检查结果与预期不符
- **原因**: 审计逻辑需要调整
- **解决**: 修改工作流中的检查条件

### 7.2 调试技巧
- 使用 `echo` 输出调试信息
- 分步执行检查逻辑
- 查看原始的错误日志

---

**文档版本**: v1.0
**创建时间**: 2025-09-28
**维护者**: 开发团队
**更新频率**: 根据测试结果定期更新