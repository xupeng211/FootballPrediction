# 🔧 AICultureKit 规则体系

## 📍 快速导航

### 🤖 AI工作规则
- **[AI_PROMPT.md](./AI_PROMPT.md)** - AI编程主要指导文档 (8.2KB)
- **[AI_WORK_GUIDE.md](./AI_WORK_GUIDE.md)** - AI工作流程指南 (2.4KB)

### 🎯 Cursor专用规则
- **[.cursor/index.mdc](./.cursor/index.mdc)** - 项目核心开发规则
- **[.cursor/rules/](./.cursor/rules/)** - 详细开发规范目录
  - [coding-standards.mdc](./.cursor/rules/coding-standards.mdc) - Python编程规范
  - [testing-workflow.mdc](./.cursor/rules/testing-workflow.mdc) - 测试工作流
  - [git-workflow.mdc](./.cursor/rules/git-workflow.mdc) - Git工作流规范
  - [documentation.mdc](./.cursor/rules/documentation.mdc) - 文档编写规范
  - [ci-pipeline.mdc](./.cursor/rules/ci-pipeline.mdc) - CI/CD流水线规范

### 👥 开发者文档
- **[docs/development-guide/](./docs/development-guide/)** - 完整开发指南
- **[docs/ai-integration/](./docs/ai-integration/)** - AI工具集成文档

## 🚀 快速开始

### 环境检查和上下文加载
```bash
make env-check  # 检查开发环境
make context    # 加载项目上下文 (⭐ 重要)
make help       # 查看所有可用命令
```

### 标准开发流程
1. **创建分支**: `git checkout -b feature/功能名`
2. **开发代码**: 遵循[coding-standards.mdc](./.cursor/rules/coding-standards.mdc)规范
3. **编写测试**: 遵循[testing-workflow.mdc](./.cursor/rules/testing-workflow.mdc)要求
4. **提交前检查**: `make prepush`
5. **提交代码**: 遵循[git-workflow.mdc](./.cursor/rules/git-workflow.mdc)格式

## 📚 规则体系说明

- **AI规则文件**: 直接指导AI编程工具的行为
- **Cursor规则**: 针对Cursor编辑器的专用配置
- **开发文档**: 为人类开发者提供的详细指南

---

> 💡 **提示**: 新项目成员应该首先阅读[AI_WORK_GUIDE.md](./AI_WORK_GUIDE.md)了解AI工作流程，然后查看具体的规则文件。
