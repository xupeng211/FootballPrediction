# 🛠️ 开发环境设置指南

## 📋 概述

本文档提供标准化的开发环境设置指南，确保所有团队成员有一致且高效开发体验。

## 🎯 快速开始

### ⚡ 一键设置（推荐）
```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 运行一键设置脚本
make quick-start
# 或者
python3 scripts/setup_development_environment.py

# 验证环境
make env-check
```

### 🐳 Docker环境（最简单）
```bash
# 启动开发环境
make up

# 进入容器
docker-compose exec app bash

# 运行测试
make test.unit
```

## 🔧 环境要求

### 最低要求
- **操作系统**: Linux/macOS/Windows (WSL2)
- **内存**: 8GB RAM (推荐16GB)
- **存储**: 10GB可用空间
- **网络**: 稳定的互联网连接

### 软件依赖
- **Docker**: 20.10+ & Docker Compose 2.0+
- **Python**: 3.11+ (本地开发)
- **Git**: 2.30+
- **Make**: 构建工具

## 🐳 Docker开发环境

### Docker Compose配置
项目提供完整的多环境Docker配置：

#### 开发环境
```yaml
# docker-compose.yml (开发)
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - /app/node_modules
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - DEBUG=true
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 生产环境
```yaml
# docker-compose.production.yml (生产)
version: '3.8'
services:
  app:
    image: football-prediction:latest
    environment:
      - ENV=production
    # 生产配置...
```

### Docker开发命令
```bash
# 启动开发环境
make up

# 查看日志
make logs

# 停止环境
make down

# 重新构建
make rebuild

# 进入容器
docker-compose exec app bash

# 数据库操作
make db-reset
make db-migrate
```

### Docker特性

#### 热重载
- 代码变更自动重启
- 静态文件自动更新
- 数据库变更自动检测

#### 调试支持
- Python调试器支持
- 断点调试功能
- 日志实时查看

#### 依赖管理
- 容器内依赖隔离
- 快速依赖安装
- 版本一致性保证

## 💻 IDE配置

### VSCode配置

#### 推荐扩展
```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.debugpy",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode-remote.remote-containers"
  ]
}
```

#### 编辑器设置
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".coverage": true,
    "htmlcov": true
  },
  "docker.showExplorer": true
}
```

#### 调试配置
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "module": "uvicorn",
      "args": [
        "src.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": false,
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests", "-v"],
      "jinja": true,
      "justMyCode": false,
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm配置

#### 项目设置
1. **Python解释器**: 使用Docker或虚拟环境
2. **代码风格**: 配置Ruff格式化
3. **测试框架**: 配置pytest
4. **调试器**: 启用Python调试

#### 配置步骤
```
File → Settings → Project: FootballPrediction → Python Interpreter
→ Add → Docker Compose → Select service 'app'

File → Settings → Tools → External Tools
→ Add Ruff format, Ruff check

File → Settings → Tools → Python Integrated Tools
→ Testing → pytest
```

### 通用编辑器配置

#### EditorConfig
```ini
# .editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
max_line_length = 88

[*.{yml,yaml}]
indent_size = 2

[*.json]
indent_size = 2

[Makefile]
indent_style = tab
```

#### Git属性
```gitattributes
# .gitattributes
*.py text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.md text eol=lf
*.sh text eol=lf

*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
```

## 🚀 快速启动脚本

### 自动化设置脚本
项目提供完整的环境设置自动化脚本：

```bash
# 运行设置脚本
python3 scripts/setup_development_environment.py

# 或使用Make命令
make quick-start
```

### 脚本功能
- ✅ **环境检查**: 验证系统要求
- ✅ **依赖安装**: 自动安装所需工具
- ✅ **Docker配置**: 设置Docker环境
- ✅ **IDE配置**: 生成IDE配置文件
- ✅ **验证测试**: 运行环境验证

### 设置步骤详解

#### 1. 环境检查
```bash
# 检查系统要求
make env-check

# 检查Docker
docker --version
docker-compose --version

# 检查Python (本地开发)
python --version
```

#### 2. 依赖安装
```bash
# 安装Python依赖
make install

# 启动Docker服务
make up

# 数据库初始化
make db-init
```

#### 3. 配置生成
```bash
# 生成环境配置
cp .env.example .env

# 生成IDE配置
python3 scripts/generate_ide_config.py

# 初始化Git hooks
make init-hooks
```

#### 4. 验证测试
```bash
# 运行完整测试
make test

# 检查代码质量
make lint

# 验证API
make check-api
```

## 🔧 开发工具集成

### 代码质量工具

#### Ruff配置
```toml
# pyproject.toml
[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I", "N", "B", "A", "C4", "UP"]
ignore = ["E501", "B008"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### MyPy配置
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 测试工具配置

#### Pytest配置
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=30
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    critical: Critical tests
```

### 数据库工具

#### DBeaver配置
1. **连接设置**:
   - Host: localhost
   - Port: 5432
   - Database: football_prediction
   - User: postgres
   - Password: postgres

#### Redis工具
```bash
# Redis CLI
docker-compose exec redis redis-cli

# Redis GUI工具
# 推荐使用 RedisInsight
```

### API测试工具

#### Postman集合
项目提供预配置的Postman集合：

```json
// postman_collection.json
{
  "info": {
    "name": "Football Prediction API",
    "description": "API测试集合"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8000"
    }
  ]
}
```

#### 使用方法
1. 导入Postman集合
2. 设置环境变量
3. 运行API测试

## 🔄 开发工作流

### 日常开发流程

#### 1. 开始工作
```bash
# 启动开发环境
make up

# 加载项目上下文
make context

# 检查环境状态
make env-check
```

#### 2. 开发过程
```bash
# 运行测试
make test.unit

# 代码检查
make lint

# 代码格式化
make fmt

# 智能修复
python3 scripts/smart_quality_fixer.py
```

#### 3. 提交前检查
```bash
# 完整验证
make prepush

# 生成覆盖率报告
make coverage

# 安全检查
make security
```

### 热重载开发

#### 文件监听
```bash
# 启动热重载
make dev

# 监控特定文件
make watch-files
```

#### 调试模式
```bash
# 调试模式启动
make debug

# 附加调试器
make attach-debugger
```

## 🚨 常见问题解决

### 环境问题

#### Docker问题
```bash
# Docker权限问题
sudo usermod -aG docker $USER
newgrp docker

# Docker清理
docker system prune -a

# 重新构建镜像
make rebuild
```

#### Python依赖问题
```bash
# 清理虚拟环境
make clean-env

# 重新安装依赖
make clean-install

# 检查依赖冲突
pip check
```

#### 数据库问题
```bash
# 重置数据库
make db-reset

# 查看数据库日志
make db-logs

# 数据库迁移
make db-migrate
```

### 性能问题

#### 内存不足
```bash
# 增加Docker内存限制
# 在Docker Desktop中调整内存设置

# 监控资源使用
docker stats
```

#### 磁盘空间
```bash
# 清理Docker
docker system prune -a

# 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 网络问题

#### 端口冲突
```bash
# 检查端口占用
lsof -i :8000

# 修改端口
# 编辑docker-compose.yml
```

#### 代理问题
```bash
# 配置代理
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

## 📚 进阶配置

### 自定义开发环境

#### 添加新服务
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  app:
    volumes:
      - ./custom:/app/custom
    environment:
      - CUSTOM_CONFIG=true
```

#### 自定义脚本
```bash
# 添加自定义Make命令
# 编辑Makefile
custom-command:
    @echo "Running custom command"
    # your commands
```

### 性能优化

#### 开发环境优化
```yaml
# Docker Compose优化
services:
  app:
    build:
      target: development
    volumes:
      - type: bind
        source: .
        target: /app
        consistency: cached
```

#### 缓存策略
```bash
# 启用Redis缓存
make cache-enable

# 清理缓存
make cache-clear
```

## 🔗 相关文档

- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Git工作流
- [CODE_REVIEW_STANDARDS.md](CODE_REVIEW_STANDARDS.md) - 代码审查规范
- [CLAUDE.md](CLAUDE.md) - 项目开发指南

## 📞 获取帮助

### 社区支持
- **GitHub Issues**: 报告问题和功能请求
- **GitHub Discussions**: 技术讨论和问答
- **团队频道**: 实时技术支持

### 常用命令
```bash
# 查看所有可用命令
make help

# 快速帮助
make quick-help

# 生成诊断报告
make diagnose
```

---

## 🎯 环境验证清单

### ✅ 基础环境检查
- [ ] Docker和Docker Compose已安装
- [ ] 可以访问项目仓库
- [ ] 有足够的磁盘空间和内存

### ✅ 开发环境设置
- [ ] 项目已克隆到本地
- [ ] 开发环境已启动 (`make up`)
- [ ] 所有依赖已安装 (`make install`)
- [ ] 数据库已初始化 (`make db-init`)

### ✅ 工具配置
- [ ] IDE配置已应用
- [ ] Git hooks已初始化
- [ ] 代码质量工具可用
- [ ] 测试框架正常工作

### ✅ 功能验证
- [ ] 可以运行单元测试 (`make test.unit`)
- [ ] 可以访问API端点
- [ ] 热重载功能正常
- [ ] 调试功能可用

---

**记住**: 标准化的开发环境是高效协作的基础！🚀

*文档版本: v1.0 | 最后更新: 2025-11-03*