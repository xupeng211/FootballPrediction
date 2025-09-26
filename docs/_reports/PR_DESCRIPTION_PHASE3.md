# 📚 Docs Guard 修复计划 - Phase 3 (目录结构违规修复)

## 🎯 修复目标
- 修复 Docs Guard 报告的 6 个非规范顶层目录  
- 确保 docs/ 下仅包含允许的目录结构  

## 🔧 修复成果
- 将 security/ 下文件迁移至 ops/security/  
- 将 runbooks/ 下文件迁移至 ops/runbooks/  
- 将 archive/ 与 reports_archive/ 整合至 legacy/  
- 将 assets/ 下的资源文件迁移至 legacy/  
- 移除了不符合规范的顶层目录  

## 📊 累计进展
- Phase 1: 修复 19 个坏链  
- Phase 2: 修复 82 个孤儿文档（孤儿数清零 ✅）  
- Phase 3: 修复 6 个目录违规  

## ✅ 验收标准
- Docs Guard 全绿 ✅  
- CI 检查通过 ✅  
- 目录结构合规 ✅  

## 🔄 后续计划
- Phase 4: 长期维护机制 (CI + CONTRIBUTING.md 更新)  
