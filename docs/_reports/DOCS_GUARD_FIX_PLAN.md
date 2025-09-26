# 📑 Docs Guard 问题修复路线图

## 🎯 文档目标
本路线图旨在分阶段修复 **Docs Guard** 检测出的 **103 个问题**，确保文档结构健康、链接完整、无孤儿文件。  

---

## 📊 问题分类统计（首次运行结果）
- **坏链 (Dead Links)**: 19 个  
- **孤儿文档 (Orphaned Docs)**: 83 个  
- **目录违规 (Invalid Structure)**: 6 个  
- **必需文件缺失**: 0 个（已确认存在 `README.md` 和 `INDEX.md`）  

> ⚠️ 具体数字请根据 `scripts/docs_guard.py` 的输出补充。  

---

## 🛠️ 修复优先级
1. **P1 - 高优先级**
   - 坏链修复  
   - 必需文件检查  
2. **P2 - 中优先级**
   - 孤儿文档处理（决定是保留、归档还是合并）  
3. **P3 - 低优先级**
   - 目录结构微调  
   - legacy 文档标记  

---

## 📅 修复阶段计划

### Phase 1 - 坏链修复
- [ ] 收集坏链清单（从 `docs_guard.py` 输出中复制前 30 条）  
- [ ] 批量修复或归档对应文件  
- [ ] 提交 PR：\`fix/docs-broken-links\`  

### Phase 2 - 孤儿文档处理
- [ ] 确认孤儿文档的用途  
- [ ] 若仍需保留 → 添加索引或 cross-link  
- [ ] 若已过时 → 移入 \`legacy/\`  
- [ ] 提交 PR：\`fix/docs-orphans\`  

### Phase 3 - 目录结构规范化
- [ ] 检查是否存在非规范顶层目录  
- [ ] 调整文件归类  
- [ ] 提交 PR：\`fix/docs-structure\`  

### Phase 4 - 长期维护
- [ ] 在 \`CONTRIBUTING.md\` 中写明 **必须通过 \`make docs.check\`**  
- [ ] 定期跑 \`make docs.check\` 确认健康度  
- [ ] 在每次发布前执行一次全量验证  

---

## ✅ 验收标准
- CI (Docs Guard) 全绿 ✅  
- 坏链数清零 ✅  
- 孤儿文档归类完成 ✅  
- 目录规范通过 ✅  

---

## 📋 具体问题清单（从 docs_guard.py 输出提取）

### 坏链清单（19 个）
- ❌ Dead link: docs/SECURITY.md -> ./DEPLOYMENT.md
- ❌ Dead link: docs/SECURITY.md -> ./OPERATIONS.md  
- ❌ Dead link: docs/README.md -> glossary.md
- ❌ Dead link: docs/CI_GUARDIAN_GUIDE.md -> ci_defense_mechanisms.md
- ❌ Dead link: docs/testing/performance_tests.md -> performance_trend.png
- ❌ Dead link: docs/how-to/DEPLOYMENT_GUIDE.md -> docs/DATABASE_SCHEMA.md
- ❌ Dead link: docs/how-to/DEPLOYMENT_GUIDE.md -> docs/DEVELOPMENT_GUIDE.md
- ❌ Dead link: docs/how-to/DEPLOYMENT_GUIDE.md -> docs/MONITORING_GUIDE.md
- ❌ Dead link: docs/archive/README_ASYNC_DB_TESTING.md -> docs/async_database_testing_guide.md
- ❌ Dead link: docs/archive/README_ASYNC_DB_TESTING.md -> templates/async_database_test_template.py
- ❌ Dead link: docs/archive/README_ASYNC_DB_TESTING.md -> examples/refactored_test_index_existence.py
- ...（更多详见完整输出）

### 目录违规（6 个）
- ❌ Disallowed top-level directory: docs/runbooks/
- ❌ Disallowed top-level directory: docs/stats/
- ❌ Disallowed top-level directory: docs/assets/
- ❌ Disallowed top-level directory: docs/archive/
- ❌ Disallowed top-level directory: docs/reports_archive/
- ❌ Disallowed top-level directory: docs/security/

### 主要孤儿文档（前20个）
- ⚠️ Orphaned document: docs/DATA_COLLECTION_SETUP.md
- ⚠️ Orphaned document: docs/SECURITY.md
- ⚠️ Orphaned document: docs/COVERAGE_PROGRESS.md
- ⚠️ Orphaned document: docs/PHASE6_PROGRESS.md
- ⚠️ Orphaned document: docs/security-checklist.md
- ⚠️ Orphaned document: docs/PHASE5_COMPLETION_REPORT.md
- ⚠️ Orphaned document: docs/USAGE_EXAMPLES.md
- ⚠️ Orphaned document: docs/TEST_STRATEGY.md
- ⚠️ Orphaned document: docs/RELEASE_CHECKLIST.md
- ⚠️ Orphaned document: docs/COVERAGE_PROGRESS_NEW.md
- ...（更多详见完整输出）

---

## 🎯 快速修复建议

### 立即可修复的目录问题
1. **runbooks/** → 移入 ops/runbooks/
2. **assets/** → 保持原位（图片资源目录）
3. **security/** → 移入 ops/security/
4. **stats/** → 移入 ops/stats/
5. **archive/** → 已存在，保持 legacy/archive/
6. **reports_archive/** → 已存在，保持 legacy/reports_archive/

### 坏链快速修复策略
1. **缺失文件**：创建占位符或删除相关链接
2. **路径错误**：更新为正确路径
3. **外部资源**：移至 assets/ 或更新链接

### 孤儿文档处理策略
1. **保留并添加索引**：重要文档添加到 INDEX.md
2. **归类到正确目录**：移动到相应主题目录
3. **归档到 legacy/**：过期文档移入 legacy/

---

## 📈 进度追踪

| 阶段 | 状态 | PR | 完成时间 |
|------|------|----|----------|
| Phase 1 - 坏链修复 | ⏳ 待开始 | - | - |
| Phase 2 - 孤儿文档处理 | ⏳ 待开始 | - | - |
| Phase 3 - 目录结构规范化 | ⏳ 待开始 | - | - |
| Phase 4 - 长期维护 | ⏳ 待开始 | - | - |

---

## 🔧 相关工具和命令

```bash
# 运行文档检查
python scripts/docs_guard.py

# 查看详细问题
python scripts/docs_guard.py | grep -E "(❌|⚠️)"

# 验证修复效果
git checkout -b fix/docs-issues
# ... 进行修复 ...
python scripts/docs_guard.py  # 应该显示 "✅ All checks passed!"
```
