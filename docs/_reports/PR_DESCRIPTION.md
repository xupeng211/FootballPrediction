# 📚 Docs Restructure & Cleanup

## 重构原因
- 消除重复文档 (已处理 7 对相似文件)
- 修复坏链 (19 个坏链已修复)
- 整理历史报告 (27 个阶段性报告归档至 legacy/)
- 统一目录结构，便于导航和未来文档站建设

## 影响范围
- 新的目录结构：architecture, how-to, reference, testing, data, ml, ops, release, staging, legacy
- 相对链接已更新，旧文件均有占位符或归档版本
- 新增 `docs/README.md` 与 `docs/INDEX.md`
- 启用 CI Docs Guard，避免未来坏链与孤儿文档

## 回滚方式
- 删除分支 `chore/docs-refactor-20250926`
- 恢复 main 分支原始文档
- 历史文件已保存在 legacy/ 可随时查阅

## 合并建议
- 使用 **Squash and Merge**
- 保留单一整洁提交记录
