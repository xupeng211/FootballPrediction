# 🔄 Git工作流规范

## 📋 概述

本项目采用 **Git Flow** 工作流程，结合现代化的CI/CD实践，确保代码质量和协作效率。

## 🎯 核心原则

### 分支策略
- **main**: 生产就绪代码，只接受来自release和hotfix的合并
- **develop**: 开发集成分支，功能开发的目标分支
- **feature**: 功能开发分支，从develop创建
- **release**: 发布准备分支，从develop创建
- **hotfix**: 紧急修复分支，从main创建

### 协作原则
- **主分支保护**: main和develop分支受保护，需要PR和审查
- **自动化验证**: 所有PR必须通过CI/CD检查
- **代码审查**: 所有代码变更必须经过审查
- **版本管理**: 使用语义化版本控制

## 🌳 分支模型

```
main (生产)
├── hotfix/fix-quick-bug (紧急修复)
└── release/v1.2.0 (发布准备)
    └── develop (开发)
        ├── feature/user-authentication (新功能)
        ├── feature/payment-system (新功能)
        └── feature/api-optimization (新功能)
```

## 📝 分支命名规范

### 主分支
- `main` - 生产环境代码
- `develop` - 开发集成分支

### 功能分支
```
feature/功能描述
示例:
feature/user-authentication
feature/payment-integration
feature/dashboard-redesign
feature/api-performance-optimization
```

### 修复分支
```
fix/问题描述
示例:
fix/login-validation-error
fix/database-connection-pool
fix/memory-leak-in-service
```

### 发布分支
```
release/版本号
示例:
release/v1.2.0
release/v2.0.0
release/v1.2.1-hotfix
```

### 紧急修复分支
```
hotfix/问题描述
示例:
hotfix/critical-security-patch
hotfix/production-down-issue
hotfix/data-corruption-fix
```

### 文档分支
```
docs/文档内容
示例:
docs/api-documentation-update
docs/deployment-guide
docs/developer-onboarding
```

## 🔄 工作流程

### 1. 功能开发流程

#### 创建功能分支
```bash
# 1. 同步最新代码
git checkout main
git pull origin main
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/your-feature-name

# 3. 推送到远程
git push -u origin feature/your-feature-name
```

#### 开发过程
```bash
# 1. 定期同步develop分支
git fetch origin
git rebase origin/develop

# 2. 提交代码 (遵循提交信息规范)
git add .
git commit -m "feat(api): add user authentication endpoint"

# 3. 推送进度
git push origin feature/your-feature-name
```

#### 提交PR
```bash
# 1. 确保分支是最新的
git fetch origin
git rebase origin/develop

# 2. 推送到远程
git push origin feature/your-feature-name --force-with-lease

# 3. 在GitHub上创建PR到develop分支
# 使用PR模板填写详细信息
```

### 2. 发布流程

#### 创建发布分支
```bash
# 1. 从develop创建发布分支
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# 2. 更新版本信息
# 更新package.json, CHANGELOG.md等

# 3. 提交版本更新
git add .
git commit -m "chore: bump version to v1.2.0"

# 4. 推送发布分支
git push -u origin release/v1.2.0
```

#### 发布测试
```bash
# 1. 部署发布分支到测试环境
# 2. 执行完整测试
# 3. 修复发现的问题（直接在发布分支上修复）
git commit -m "fix: resolve testing issue found in release"
git push origin release/v1.2.0
```

#### 合并发布
```bash
# 1. 合并到main分支
git checkout main
git merge --no-ff release/v1.2.0
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin main --tags

# 2. 合并回develop分支
git checkout develop
git merge --no-ff release/v1.2.0
git push origin develop

# 3. 删除发布分支
git branch -d release/v1.2.0
git push origin --delete release/v1.2.0
```

### 3. 紧急修复流程

#### 创建紧急修复分支
```bash
# 1. 从main创建修复分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# 2. 修复问题
# 编辑代码...

# 3. 提交修复
git add .
git commit -m "fix: resolve critical security vulnerability"

# 4. 推送修复分支
git push -u origin hotfix/critical-security-fix
```

#### 验证和发布
```bash
# 1. 创建PR到main分支
# 2. 紧急审查和测试
# 3. 合并到main
git checkout main
git merge --no-ff hotfix/critical-security-fix
git tag -a v1.2.1 -m "Hotfix version 1.2.1"
git push origin main --tags

# 4. 合并回develop
git checkout develop
git merge --no-ff hotfix/critical-security-fix
git push origin develop

# 5. 删除修复分支
git branch -d hotfix/critical-security-fix
git push origin --delete hotfix/critical-security-fix
```

## 📝 提交信息规范

### 提交信息格式
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### 提交类型
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档变更
- `style`: 代码格式变更
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动
- `ci`: CI/CD相关
- `build`: 构建系统或依赖变更

### 示例
```bash
git commit -m "feat(auth): add JWT token validation"
git commit -m "fix(api): resolve memory leak in request handler"
git commit -m "docs(readme): update installation instructions"
git commit -m "refactor(database): optimize query performance"
git commit -m "test(auth): add unit tests for authentication service"
```

## 🔒 分支保护规则

### main分支保护
- **禁止直接推送**: 只能通过PR合并
- **必需审查**: 至少1个审查者批准
- **必需状态检查**:
  - CI/CD流水线通过
  - 代码质量检查通过
  - 测试覆盖率检查通过
- **管理员约束**: 管理员也必须遵守规则

### develop分支保护
- **禁止直接推送**: 只能通过PR合并
- **必需审查**: 至少1个审查者批准
- **必需状态检查**:
  - CI/CD流水线通过
  - 代码质量检查通过
- **允许强制推送**: 管理员可强制推送（紧急情况）

## 🔧 GitHub配置

### 分支保护设置

#### main分支
```yaml
branch_protection:
  main:
    required_status_checks:
      strict: true
      contexts:
        - "CI/CD Pipeline"
        - "Code Quality Check"
        - "Test Coverage"
    enforce_admins: true
    required_pull_request_reviews:
      required_approving_review_count: 1
      dismiss_stale_reviews: true
      require_code_owner_reviews: false
    restrictions:
      users: []
      teams: ["core-developers"]
```

#### develop分支
```yaml
branch_protection:
  develop:
    required_status_checks:
      strict: false
      contexts:
        - "CI/CD Pipeline"
        - "Code Quality Check"
    enforce_admins: false
    required_pull_request_reviews:
      required_approving_review_count: 1
      dismiss_stale_reviews: true
      require_code_owner_reviews: false
    restrictions:
      users: []
      teams: ["developers"]
```

### 必需状态检查
- **CI/CD Pipeline**: GitHub Actions工作流
- **Code Quality Check**: Ruff代码检查
- **Test Coverage**: 测试覆盖率检查
- **Security Scan**: 安全扫描检查

## 🤖 自动化集成

### GitHub Actions工作流
```yaml
# .github/workflows/branch-protection.yml
name: Branch Protection

on:
  pull_request:
    branches: [main, develop]

jobs:
  protection-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: make install

      - name: Run tests
        run: make test

      - name: Code quality check
        run: make lint

      - name: Security check
        run: make security
```

### 自动合并配置
```yaml
# 启用自动合并条件
auto_merge:
  enabled: true
  require_status_checks: true
  wait_for_minutes: 5
  delete_branch_on_merge: true
```

## 📊 最佳实践

### 日常开发
1. **频繁提交**: 小步快跑，频繁提交代码
2. **及时同步**: 定期同步主分支代码
3. **清晰的提交信息**: 遵循提交信息规范
4. **保护主分支**: 不直接在main和develop分支开发

### 分支管理
1. **短期分支**: 功能分支生命周期控制在1-2周内
2. **及时清理**: 合并后及时删除已完成的分支
3. **命名规范**: 严格遵循分支命名规范
4. **描述性名称**: 分支名称要能清楚表达用途

### PR管理
1. **小PR**: 保持PR规模适中，便于审查
2. **完整描述**: 使用PR模板，提供完整信息
3. **及时响应**: 及时处理审查反馈
4. **自动化检查**: 确保所有自动检查通过

## 🚨 常见问题处理

### 合并冲突
```bash
# 1. 同步最新代码
git fetch origin
git rebase origin/develop

# 2. 解决冲突
# 编辑冲突文件...

# 3. 标记冲突已解决
git add .
git rebase --continue

# 4. 强制推送
git push origin feature-branch --force-with-lease
```

### 撤销提交
```bash
# 撤销最后一次提交（保留修改）
git reset --soft HEAD~1

# 撤销最后一次提交（丢弃修改）
git reset --hard HEAD~1

# 撤销已推送的提交
git revert HEAD
git push origin branch-name
```

### 分支恢复
```bash
# 恢复已删除的分支
git checkout -b recovered-branch origin/deleted-branch

# 从特定提交创建分支
git checkout -b new-branch <commit-hash>
```

## 📚 相关文档

- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [CODE_REVIEW_STANDARDS.md](CODE_REVIEW_STANDARDS.md) - 代码审查规范
- [REVIEW_CHECKLIST.md](REVIEW_CHECKLIST.md) - 审查检查清单
- [CLAUDE.md](CLAUDE.md) - 项目开发指南

## 🔧 工具推荐

### Git客户端
- **命令行**: Git Bash / Terminal
- **图形化**: SourceTree, GitKraken, VS Code Git
- **IDE集成**: PyCharm, VS Code

### 辅助工具
- **Pre-commit hooks**: 代码提交前检查
- **Git hooks**: 自动化工作流
- **GitHub CLI**: 命令行GitHub操作

---

## 📞 获取帮助

如果在使用Git工作流过程中遇到问题：

1. 📖 **查阅文档**: 查看相关文档和最佳实践
2. 💬 **团队讨论**: 在团队频道讨论和求助
3. 👨‍💻 **导师指导**: 请教有经验的开发者
4. 🎯 **GitHub支持**: 查看GitHub官方文档

---

**记住**: 好的Git工作流是团队协作的基础！🚀

*文档版本: v1.0 | 最后更新: 2025-11-03*
