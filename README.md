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

## 🐳 本地模拟CI环境

为确保本地环境与CI环境完全一致，可以使用Docker Compose在本地模拟CI环境：

### 启动完整环境
```bash
docker-compose up --build
```

这将启动以下服务：
- **app**: 主应用服务
- **db**: PostgreSQL数据库（包含健康检查）
- **redis**: Redis缓存服务
- **nginx**: 反向代理服务

### 环境配置
项目包含以下环境配置文件：
- `.env.ci` - CI环境变量配置
- `requirements.lock` - 锁定的依赖版本

### 验证步骤
1. 启动服务：`docker-compose up --build`
2. 检查服务状态：`docker-compose ps`
3. 查看应用日志：`docker-compose logs app`
4. 运行测试：`docker-compose exec app pytest --cov=src --cov-fail-under=80`

这样可以确保本地开发环境与CI环境保持完全一致，避免"在我机器上可以运行"的问题。

## 📋 本地CI验证

在提交代码前，请运行：
```bash
./ci-verify.sh
```

该脚本会执行完整的 CI 验证流程：
1. **虚拟环境重建** - 清理并重新创建虚拟环境，确保依赖一致性
2. **Docker 环境启动** - 启动完整的服务栈（应用、数据库、Redis、Nginx）
3. **测试执行** - 运行所有测试并验证代码覆盖率 >= 78%

如果脚本输出 "🎉 CI 绿灯验证成功！" 则可以安全推送到远程。

### 验证状态说明
- ✅ 绿色表示步骤成功
- ❌ 红色表示步骤失败，需要修复
- ⚠️ 黄色表示警告信息
- ℹ️ 蓝色表示信息提示

### 故障排除
如果脚本失败，请检查：
1. Docker 是否正常运行
2. 依赖包是否有冲突
3. 测试代码覆盖率是否达标
4. 端口是否被占用（5432、6379、80）

## 🎉 开始使用

```bash
python generate_project.py --name YourProject
```

祝您开发愉快！ 🚀
