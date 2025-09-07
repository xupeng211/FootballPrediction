# 🚀 Python项目模板

基于AICultureKit的Python项目模板，包含完整的开发基础设施和最佳实践配置。

## ✨ 特性

- 🏗️ **标准化项目结构** - 遵循Python最佳实践
- 🔧 **完整开发工具链** - 代码格式化、检查、测试等工具
- 🤖 **AI辅助开发** - 内置AI工作流程和指引
- 🐳 **Docker支持** - 开发和生产环境容器化
- ⚡ **自动化CI/CD** - GitHub Actions配置
- 📊 **代码质量监控** - 测试覆盖率、复杂度分析
- 🛡️ **安全检查** - 代码安全扫描

## 🚀 快速开始

### 1. 生成新项目

```bash
python generate_project.py --name MyProject --description "我的项目描述"
```

### 2. 初始化环境

```bash
cd MyProject
make install      # 安装依赖
make env-check    # 检查环境
make test         # 运行测试
```

## 📁 项目结构

```
MyProject/
├── src/myproject/          # 源代码
├── tests/                  # 测试文件
├── docs/                   # 文档
├── .github/workflows/      # CI/CD配置
├── Makefile               # 开发工具链
└── requirements.txt       # 依赖定义
```

## 🔧 开发工具链

```bash
make venv         # 创建虚拟环境
make install      # 安装依赖
make format       # 代码格式化
make lint         # 代码检查
make test         # 运行测试
make ci           # 本地CI检查
make prepush      # 提交前检查
```

## 🤖 AI辅助开发

遵循工具优先原则：
1. `make env-check` - 检查环境
2. `make context` - 加载上下文
3. 开发和测试
4. `make ci` - 质量检查
5. `make prepush` - 完整验证

## 🎉 开始使用

```bash
python generate_project.py --name YourProject
```

祝您开发愉快！ 🚀
