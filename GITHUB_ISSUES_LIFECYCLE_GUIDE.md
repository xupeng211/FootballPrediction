# 📋 GitHub Issues 生命周期管理指南

**版本**: v1.0
**更新时间**: 2025-11-08
**状态**: ✅ 生产就绪

---

## 📖 概述

本指南定义了GitHub Issues的创建、管理、更新和关闭的标准流程，旨在提高项目管理效率，避免重复工作，保持Issue列表的整洁和准确。

---

## 🎯 Issue生命周期阶段

### 1. 创建阶段 (Creation)
#### 何时创建Issue
- 发现新的bug或问题
- 需要新功能或增强
- 识别技术债务
- 需要文档或改进
- 发现重复或低效的工作流程

#### Issue创建规范
```markdown
# Issue标题格式
[类型] 简洁明确的描述

## 📋 概述
**状态**: 🔄 待开始
**优先级**: high/medium/low
**预计工作量**: X小时/天/周
**创建时间**: YYYY-MM-DD

## 📝 描述
清晰描述问题或需求

## 🎯 目标
具体的目标列表，使用checkbox格式

## 🛠️ 技术任务
详细的实施步骤

## 📊 成功指标
可量化的成功标准

## 🔧 相关资源
链接、文档、工具等

---
**标签**: bug,enhancement,documentation等
**预计完成**: YYYY-MM-DD
**负责人**: @username
```

### 2. 活跃阶段 (Active)
#### Issue状态管理
- **🔄 进行中**: 正在处理的工作
- **⏸️ 阻塞**: 遇到阻碍，需要外部帮助
- **📋 待验证**: 工作完成，等待测试或review
- **🔄 待开始**: 已规划，等待开始

#### 更新规范
```markdown
## 📈 进度更新

### 2025-11-08 更新
- ✅ 完成第一步：环境设置
- ⏸️ 阻塞第二步：依赖问题
- 📋 下一步：解决依赖并继续
```

### 3. 完成阶段 (Completion)
#### 完成标准
- [ ] 主要目标已实现
- [ ] 代码已提交并测试
- [ ] 文档已更新（如需要）
- [ ] 相关Issues已关联和更新

#### 关闭规范
```markdown
## ✅ 完成总结

### 🎉 成果
- 实现的功能A
- 修复的问题B
- 改进的流程C

### 📊 指标达成
- 指标1: 结果
- 指标2: 结果

### 🔗 相关资源
- PR链接: #xxx
- 文档链接: [文档名称](url)
```

---

## 🏷️ 标签规范

### 优先级标签
- `priority-critical`: 阻塞生产环境的问题
- `priority-high`: 高优先级，影响核心功能
- `priority-medium`: 中等优先级，改进性工作
- `priority-low`: 低优先级，锦上添花的工作

### 类型标签
- `bug`: 错误修复
- `enhancement`: 功能增强
- `documentation`: 文档相关
- `quality-improvement`: 质量改进
- `performance`: 性能相关
- `security`: 安全相关

### 状态标签
- `in-progress`: 进行中
- `blocked`: 被阻塞
- `needs-review`: 需要审查
- `ready-for-merge`: 准备合并

### 特殊标签
- `good-first-issue`: 适合新手的Issue
- `help-wanted`: 需要帮助
- `wontfix`: 不计划修复
- `duplicate`: 重复问题

---

## 🔄 Issue管理工作流

### 每日检查 (Daily)
```bash
# 检查新Issues
gh issue list --state open --limit 10 --json | jq '.[] | {number: .number, title: .title}'

# 检查即将到期的Issues
gh issue list --search "milestone:next-week" --state open
```

### 每周清理 (Weekly)
```bash
# 检查长时间未更新的Issues
gh issue list --search "updated:<2025-11-01" --state open

# 检查重复Issues
gh issue list --search "duplicate" --state open
```

### 每月整理 (Monthly)
- 清理已完成但未关闭的Issues
- 合并相关或重复的Issues
- 更新里程碑和优先级
- 归档已完成的Issues

---

## 📊 Issue质量指标

### 健康指标
- **Issue周转时间**: < 30天
- **完成率**: > 80%
- **重复Issue率**: < 5%
- **过期Issue率**: < 10%

### 监控命令
```bash
# Issue统计
gh issue list --state all --json | jq '{
  total: length,
  open: map(select(.state == "OPEN")) | length,
  closed: map(select(.state == "CLOSED")) | length
}'

# 优先级分布
gh issue list --state open --json | jq '[
  group_by(.labels[]? | select(.name | startswith("priority-")) | .name // "unprioritized") |
  map({priority: .[0], count: length})
] | sort_by(.count) | reverse'
```

---

## 🚫 避免的不良实践

### Issue创建问题
- ❌ 模糊的标题和描述
- ❌ 缺少明确的成功标准
- ❌ 重复现有的Issue
- ❌ 过于宽泛或无法实现的目标

### Issue管理问题
- ❌ 长时间不更新进度
- ❌ 完成后不及时关闭
- ❌ 忽略相关Issue的关联
- ❌ 标签使用不规范

### 关闭问题
- ❌ 关闭时没有说明原因
- ❌ 关闭后立即重新打开类似Issue
- ❌ 关闭已完成但未记录成果

---

## 🛠️ 自动化工具

### GitHub CLI命令
```bash
# 快速创建Issue模板
gh issue create --title "Bug: [描述]" --body "$(cat .github/ISSUE_TEMPLATE/bug.md)" --label "bug"

# 批量关闭重复Issues
for issue in $(gh issue list --search "duplicate" --state open --json | jq -r '.[].number'); do
  gh issue close $issue --comment "Duplicate issue, see #master-issue"
done

# 查看Issue统计
gh issue list --state all --json | jq '{total: length, open: map(select(.state == "OPEN")) | length, closed: map(select(.state == "CLOSED")) | length}'
```

### Issue模板
在 `.github/ISSUE_TEMPLATE/` 目录下创建：

1. `bug.md` - Bug报告模板
2. `feature.md` - 功能请求模板
3. `improvement.md` - 改进建议模板
4. `question.md` - 问题咨询模板

### 自动化脚本
```python
# scripts/issues_cleanup.py
import subprocess
import json

def cleanup_old_issues():
    """清理超过90天未更新的Issues"""
    cutoff_date = "2025-08-08"  # 90天前
    cmd = f'gh issue list --search "updated:<{cutoff_date}" --state open --json'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        issues = json.loads(result.stdout)
        for issue in issues:
            print(f"Issue #{issue['number']}: {issue['title']}")
            # 可以选择自动关闭或提醒
    else:
        print(f"Error: {result.stderr}")

if __name__ == "__main__":
    cleanup_old_issues()
```

---

## 📚 最佳实践

### Issue编写
1. **具体明确**: 使用具体的问题描述，避免模糊语言
2. **可执行**: 确保Issue有明确的可执行步骤
3. **可测量**: 定义清晰的成功标准和指标
4. **及时更新**: 定期更新进度和状态

### Issue管理
1. **定期清理**: 定期清理过时和重复的Issues
2. **标签规范**: 使用一致的标签系统
3. **关联管理**: 及时关联相关Issues和PRs
4. **文档记录**: 记录重要决策和解决方案

### 团队协作
1. **明确分工**: 指定负责人和截止日期
2. **及时沟通**: 使用评论和@提及保持沟通
3. **知识分享**: 在Issue中分享解决方案和经验
4. **持续改进**: 定期review和改进Issue管理流程

---

## 🔍 故障排除

### 常见问题

#### Q: Issue太多，难以管理
**A**:
- 定期清理和归档
- 使用标签分类
- 创建里程碑进行分组管理
- 使用自动化工具辅助管理

#### Q: Issue重复创建
**A**:
- 搜索现有Issues再创建新的
- 使用标准模板
- 培训团队成员创建规范

#### Q: Issue长期未处理
**A**:
- 定期review和更新状态
- 重新评估优先级
- 分解大Issue为小Issue
- 考虑关闭或重新规划

### 问题诊断命令
```bash
# 查看Issue状态分布
gh issue list --state open --json | jq 'group_by(.labels[]? | select(.name | startswith("priority-")) | .name // "unprioritized") | map({priority: .[0], count: length})'

# 查看长时间未更新的Issues
gh issue list --search "updated:<2025-10-01" --state open

# 查看我的Issues
gh issue list --assignee @me --state open
```

---

## 📞 联系和支持

如有问题或建议，请联系：
- 项目维护者：@xupeng211
- 技术支持：创建Issue并标记`help-wanted`
- 流程改进：创建Issue并标记`enhancement`

---

**文档维护**: Claude Code (claude.ai/code)
**最后更新**: 2025-11-08 23:30
**版本**: v1.0

*"良好的Issue管理是高效项目协作的基础。通过标准化流程，我们可以提高工作效率，减少重复工作，确保每个Issue都有明确的目标和结果。"*