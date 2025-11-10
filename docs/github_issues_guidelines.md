# GitHub Issues 管理指南

## 📋 概述

本文档定义了项目GitHub Issues的标准流程、标签规范和最佳实践，确保项目管理的高效性和一致性。

## 🏷️ 标签规范

### 状态标签 (Status Labels)
- `status/pending` - 待处理 (新创建的Issue)
- `status/in-progress` - 进行中 (正在开发)
- `status/completed` - 已完成 (工作完成，等待关闭)
- `status/blocked` - 阻塞 (等待外部依赖)
- `status/on-hold` - 暂停 (暂时搁置)

### 优先级标签 (Priority Labels)
- `priority/critical` - 关键 (影响核心功能，需立即处理)
- `priority/high` - 高优先级 (重要功能，影响用户体验)
- `priority/medium` - 中等优先级 (重要但不紧急)
- `priority/low` - 低优先级 (锦上添花功能)

### 类型标签 (Type Labels)
- `enhancement` - 功能增强
- `bug` - 错误修复
- `documentation` - 文档更新
- `testing` - 测试相关
- `performance` - 性能优化
- `refactoring` - 代码重构
- `infrastructure` - 基础设施
- `claude-code` - Claude Code相关
- `automated` - 自动化任务

### 特殊标签 (Special Labels)
- `phase-x.y` - 阶段标记 (如 phase-5.2, phase-6.0)
- `good-first-issue` - 适合新手的Issue
- `help-wanted` - 需要帮助
- `question` - 问题咨询

## 📝 Issue创建模板

项目提供了四种标准的Issue模板：

### 1. 功能需求 (Feature Request)
**用途**: 提出新功能或改进
**文件**: `.github/ISSUE_TEMPLATE/feature_request.md`
**必填标签**: `enhancement`, `feature-request`

### 2. Bug报告 (Bug Report)
**用途**: 报告软件问题或错误
**文件**: `.github/ISSUE_TEMPLATE/bug_report.md`
**必填标签**: `bug`, `bug-report`

### 3. Phase任务 (Phase Task)
**用途**: 创建开发阶段任务
**文件**: `.github/ISSUE_TEMPLATE/phase_task.md`
**必填标签**: `enhancement`, `claude-code`, `automated`

### 4. 通用模板
**用途**: 其他类型的Issue
**文件**: `.github/ISSUE_TEMPLATE/general.md`
**必填标签**: 根据具体类型选择

## 🔄 Issue生命周期管理

### 创建阶段
1. ✅ **搜索现有Issues**: 避免重复创建
2. ✅ **选择合适模板**: 使用对应的Issue模板
3. ✅ **填写完整信息**: 提供足够的上下文
4. ✅ **添加正确标签**: 根据Issue类型添加相应标签
5. ✅ **设置合理标题**: 使用清晰的标题格式

### 进行阶段
1. **分配负责人**: 明确Issue负责人
2. **设置状态标签**: 添加 `status/in-progress`
3. **定期更新**: 每周更新进展
4. **关联相关Issues**: 建立依赖关系
5. **添加项目标签**: 如Phase标记

### 完成阶段
1. **验证完成标准**: 确保所有验收标准满足
2. **更新状态标签**: 设置 `status/completed`
3. **创建完成报告**: 详细记录成果和经验
4. **更新相关Issues**: 关联Issue指向完成报告
5. **准备关闭**: 确认所有相关任务已完成

### 关闭阶段
1. **确认无遗留问题**: 检查是否有相关工作未完成
2. **更新文档**: 更新相关文档和README
3. **关闭Issue**: 标记为已关闭
4. **归档信息**: 将重要信息归档到知识库

## 📏 Phase管理工作流

### Phase标准流程
1. **启动Phase**:
   ```bash
   python3 scripts/record_work.py start-work "Phase X.Y: 任务标题" "详细描述" type --priority priority
   ```

2. **执行子任务**:
   - 按优先级执行子任务
   - 使用细粒度任务管理
   - 每个任务1-2小时内可完成

3. **完成Phase**:
   ```bash
   python3 scripts/record_work.py complete-work work_id --deliverables "成果1,成果2"
   ```

4. **同步到GitHub**:
   ```bash
   make claude-sync
   ```

### Phase命名规范
- **格式**: `Phase <主版本>.<子版本>`
- **示例**: `Phase 5.2`, `Phase 6.0`, `Phase 8.1`
- **说明**: 主版本表示大的里程碑，子版本表示具体任务

## 📊 每周清理流程

### 自动化清理
每周运行清理脚本：
```bash
python3 scripts/weekly_issues_cleanup.py
```

### 清理内容
1. **重复检测**: 查找重复的Issues
2. **过时识别**: 识别超过30天的开放Issues
3. **状态检查**: 检查进行中但长时间未更新的Issues
4. **健康评估**: 计算项目管理健康分数

### 清理建议
- 🔄 合并重复Issues
- ✅ 关闭已完成的Issues
- 📝 更新长期未响应的Issues
- 🏷️ 统一标签使用

## 📋 最佳实践

### Issue标题格式
- **功能需求**: `[FEATURE] 简短描述`
- **Bug报告**: `[BUG] 简短问题描述`
- **Phase任务**: `Phase X.Y: 任务标题`
- **文档更新**: `[DOC] 文档类型 - 简短描述`

### Issue描述要求
1. **清晰的问题陈述**
2. **详细的上下文信息**
3. **明确的验收标准**
4. **相关的链接引用**
5. **合理的优先级设置**

### 标签使用原则
1. **状态标签**：准确反映Issue当前状态
2. **优先级标签**：基于影响程度和紧急程度
3. **类型标签**：准确分类Issue类型
4. **Phase标签**：用于关联开发阶段

### 代码集成
```bash
# 开发任务开始
python3 scripts/record_work.py start-work "任务标题" "描述" type --priority priority

# 开发任务完成
python3 scripts/record_work.py complete-work work_id --deliverables "成果1,成果2"

# 同步到GitHub
make claude-sync
```

## 📈 健康指标

### Issue数量管理
- **健康范围**: 开放Issues保持在15-25个
- **警告阈值**: 超过25个时触发清理
- **危险区域**: 超过30个时强制清理

### 响应时间要求
- **高优先级**: 3个工作日内响应
- **中优先级**: 1周内响应
- **低优先级**: 2周内响应

### 完成率目标
- **月度完成率**: 80%以上
- **Phase完成率**: 90%以上
- **Bug修复率**: 95%以上

## 🔧 工具和脚本

### 清理工具
- `scripts/github_issues_cleanup.py` - 基础清理工具
- `scripts/weekly_issues_cleanup.py` - 每周清理脚本
- `scripts/record_work.py` - 工作记录脚本

### Makefile命令
```bash
make claude-sync     # 同步工作记录到GitHub
make github-actions-test  # 测试GitHub Actions
make repo-health    # 检查仓库健康状态
```

## 📞 问题上报流程

### Bug报告流程
1. 使用Bug报告模板创建Issue
2. 添加 `bug` 和 `bug-report` 标签
3. 设置适当优先级
4. 分配给相关开发者
5. 跟踪修复进度
6. 验证修复效果

### 功能请求流程
1. 使用功能需求模板创建Issue
2. 添加 `enhancement` 和 `feature-request` 标签
3. 团队评估优先级
4. 纳入开发计划
5. 定期更新进展
6. 完成后更新文档

## 📚 相关文档

- `CLAUDE.md` - Claude Code使用指南
- `README.md` - 项目总体介绍
- `GITHUB_ISSUES_OPTIMIZATION_REPORT.md` - Issues优化报告
- `PHASE_5_2_RELEASE_SUMMARY.md` - Phase完成报告

---

*文档版本: v1.0*
*最后更新: 2025-11-10*
*维护者: 开发团队*