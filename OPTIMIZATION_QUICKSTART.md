# 🚀 优化后的项目快速开始指南

> 本指南帮助您快速上手优化后的项目配置

## 📋 优化亮点一览

✅ **工具链简化**: ruff + mypy（替代 black/isort/flake8）
✅ **覆盖率统一**: CI(80%) / Dev(60%) / Min(50%)
✅ **Docker 优化**: BuildKit 缓存，构建提速 30-50%
✅ **配置规范**: 英文工作流名，完善的 .env.example

---

## 🏃 快速上手（3分钟）

### 1️⃣ 初始化环境

```bash
# 清理旧环境（可选，推荐）
make clean-env

# 安装依赖（使用优化后的配置）
make install

# 验证环境
make env-check
```

### 2️⃣ 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置（填入实际值）
vim .env
# 或使用你喜欢的编辑器
nano .env

# 验证配置
make check-env
```

**最小必需配置**:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction_dev
REDIS_URL=redis://:redis_password@localhost:6379/0
SECRET_KEY=your-secret-key-here-please-change-this
```

### 3️⃣ 运行测试验证

```bash
# 快速测试（开发环境，60% 覆盖率）
make coverage-local

# 完整测试（CI 标准，80% 覆盖率）
make coverage-ci

# 查看覆盖率报告
open htmlcov/index.html  # macOS
# 或
xdg-open htmlcov/index.html  # Linux
```

---

## 🔧 新的开发工作流

### 代码质量检查（使用 Ruff）

```bash
# 运行 Lint（ruff + mypy）
make lint

# 自动格式化代码
make fmt

# 完整质量检查（lint + fmt + test）
make quality
```

**Ruff 优势**:

- ⚡ **速度**: 比 Black 快 10-100 倍
- 🎯 **一体化**: 替代 flake8 + isort + black
- 🔄 **自动修复**: `--fix` 标志自动修复问题

### 覆盖率测试（统一阈值）

```bash
# CI 环境（80% 阈值）
make coverage-ci

# 开发环境（60% 阈值）
make coverage-local

# 自定义阈值
COVERAGE_THRESHOLD=70 make coverage

# 查看覆盖率趋势
make coverage-dashboard
```

### Docker 开发（启用 BuildKit）

```bash
# 方法1: 临时启用
DOCKER_BUILDKIT=1 docker-compose build

# 方法2: 永久启用（推荐）
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
source ~/.bashrc

# 构建并启动
make up

# 查看日志
make logs
```

**BuildKit 优势**:

```
首次构建: 2-3 分钟
重复构建（有缓存）: 30-60 秒（提速 70%）
```

---

## 📊 覆盖率阈值说明

| 环境 | 阈值 | 命令 | 使用场景 |
|------|------|------|----------|
| **CI** | 80% | `make coverage-ci` | 提交代码前、CI/CD 流程 |
| **Dev** | 60% | `make coverage-local` | 本地开发、快速迭代 |
| **Min** | 50% | `COVERAGE_THRESHOLD_MIN=50` | 最低要求、紧急修复 |

### 自定义阈值

```bash
# 临时覆盖 CI 阈值为 85%
COVERAGE_THRESHOLD_CI=85 make coverage-ci

# 临时覆盖开发阈值为 55%
COVERAGE_THRESHOLD_DEV=55 make coverage-local

# 在 ci-verify.sh 中使用自定义阈值
COVERAGE_THRESHOLD=75 ./ci-verify.sh
```

---

## 🎯 常用命令速查

### 环境管理

```bash
make venv           # 创建虚拟环境
make install        # 安装依赖
make env-check      # 检查环境健康
make lock-deps      # 锁定依赖版本
make clean-env      # 清理环境
```

### 代码质量

```bash
make lint           # Lint（ruff + mypy）
make fmt            # 格式化（ruff format）
make quality        # 完整质量检查
make prepush        # 提交前验证
```

### 测试

```bash
make test           # 运行所有测试
make test-quick     # 快速测试（排除慢速）
make coverage-ci    # CI 覆盖率（80%）
make coverage-local # 开发覆盖率（60%）
```

### Docker

```bash
make up             # 启动服务
make down           # 停止服务
make logs           # 查看日志
make deploy         # 部署（带 git-sha 标签）
```

### CI/CD

```bash
make ci             # CI 模拟
make prepush        # 提交前完整验证
./ci-verify.sh      # 本地 CI 验证
```

---

## 🔍 故障排除

### 问题1: Ruff 命令找不到

**症状**:

```
make lint
ruff: command not found
```

**解决**:

```bash
# 重新安装依赖
make clean-env
make install

# 或手动安装 ruff
source .venv/bin/activate
pip install ruff
```

### 问题2: Docker 构建缓存未生效

**症状**: 每次构建都很慢，没有使用缓存

**解决**:

```bash
# 检查 Docker 版本（需要 >= 20.10）
docker --version

# 启用 BuildKit
export DOCKER_BUILDKIT=1

# 或在 daemon.json 中永久启用
sudo vim /etc/docker/daemon.json
{
  "features": {
    "buildkit": true
  }
}
sudo systemctl restart docker
```

### 问题3: 覆盖率阈值失败

**症状**:

```
FAILED: coverage < 80%
```

**解决方案**:

1. **开发环境使用较低阈值**:

   ```bash
   make coverage-local  # 60% 阈值
   ```

2. **查看未覆盖的代码**:

   ```bash
   make coverage
   open htmlcov/index.html
   ```

3. **临时降低阈值（紧急情况）**:

   ```bash
   COVERAGE_THRESHOLD=70 make coverage
   ```

### 问题4: GitHub Actions 工作流未触发

**症状**: 重命名后工作流不执行

**解决**: 检查分支保护规则和工作流引用

```bash
# 检查 .github/workflows/ 中的文件名
ls -la .github/workflows/*.yml

# 确保引用更新（如果有跨文件引用）
grep -r "CI流水线" .github/
```

---

## 📚 深入学习

### Ruff 使用文档

```bash
# 查看所有规则
ruff rule --all

# 检查特定文件
ruff check src/main.py

# 自动修复
ruff check --fix src/

# 格式化
ruff format src/
```

### 覆盖率配置

查看 `pytest.ini` 了解详细配置:

```ini
[coverage:run]
source = src
omit = */tests/*, */legacy/*

[coverage:report]
precision = 2
show_missing = True
```

### Docker BuildKit

了解更多缓存选项:

```dockerfile
# 缓存挂载（pip）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.lock

# 缓存挂载（apt）
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y curl
```

---

## 🎓 推荐阅读

1. **Ruff 官方文档**: <https://docs.astral.sh/ruff/>
2. **Docker BuildKit**: <https://docs.docker.com/build/buildkit/>
3. **pytest-cov 文档**: <https://pytest-cov.readthedocs.io/>
4. **项目优化总结**: 查看 `OPTIMIZATION_SUMMARY.md`

---

## ✅ 验证清单

在开始开发前，确保以下步骤已完成：

- [ ] 已安装依赖 (`make install`)
- [ ] 已配置 `.env` 文件
- [ ] 环境检查通过 (`make env-check`)
- [ ] 能运行测试 (`make test-quick`)
- [ ] 能运行 lint (`make lint`)
- [ ] Docker 服务正常 (`make up`)
- [ ] 已启用 BuildKit (`export DOCKER_BUILDKIT=1`)

---

## 🚀 下一步

1. **开始开发**: `make context` 加载项目上下文
2. **提交前验证**: `make prepush`
3. **本地 CI 验证**: `./ci-verify.sh`
4. **查看所有命令**: `make help`

---

**祝开发愉快！** 🎉

如有问题，请查看：

- 📖 `OPTIMIZATION_SUMMARY.md` - 详细优化报告
- 📖 `README.md` - 项目说明
- 📖 `Makefile` - 所有可用命令（`make help`）
