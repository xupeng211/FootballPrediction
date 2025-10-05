# 开发者快速入门指南

## 🎯 5分钟快速上手

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd FootballPrediction

# 安装依赖
make install

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

### 2. 运行测试（最重要！）
```bash
# 快速验证环境
make test-quick

# Phase 1 核心功能测试
make test-phase1

# 完整测试（包含覆盖率）
make test
```

### 3. 开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/your-feature

# 2. 开发过程中
make test-quick  # 频繁运行

# 3. 提交前
make prepush

# 4. 推送代码
git push origin feature/your-feature
```

## 📦 项目结构速览

```
FootballPrediction/
├── src/               # 源代码
│   ├── api/          # API 路由
│   ├── database/     # 数据库模型
│   ├── services/     # 业务逻辑
│   └── ...
├── tests/            # 测试文件
│   ├── unit/         # 单元测试 ⭐
│   ├── integration/  # 集成测试
│   └── e2e/         # 端到端测试
├── Makefile         # 构建命令 📜
├── pytest.ini      # 测试配置
└── requirements/    # 依赖管理
```

## 🧪 测试命令速查表

| 场景 | 命令 | 说明 |
|------|------|------|
| **日常开发** | `make test-quick` | 快速单元测试（<30秒） |
| **API 开发** | `make test-api` | 所有 API 测试 |
| **Phase 1** | `make test-phase1` | 核心 API 测试 |
| **提交前** | `make prepush` | 完整检查 |
| **覆盖率** | `make coverage` | 生成覆盖率报告 |

## ⚡ 常见任务

### 添加新的 API 端点
```bash
# 1. 在 src/api/ 创建文件
touch src/api/new_endpoint.py

# 2. 创建测试文件
touch tests/unit/api/test_new_endpoint.py

# 3. 运行测试
pytest tests/unit/api/test_new_endpoint.py -v
```

### 修复 Bug
```bash
# 1. 运行失败的测试
pytest --lf

# 2. 修复代码

# 3. 重新运行测试
pytest tests/unit/api/test_fixed.py -v
```

### 查看覆盖率
```bash
# 生成报告
make coverage

# 查看报告
open htmlcov/index.html
```

## 🚨 重要提醒

### ❌ 不要这样做
```bash
# 单独运行一个文件看整体覆盖率
pytest tests/unit/api/test_health.py --cov=src  # 错误！
```

### ✅ 应该这样做
```bash
# 运行整个目录
pytest tests/unit/api/ --cov=src  # 正确

# 或使用 Makefile
make test-phase1  # 最佳实践
```

## 📚 必读文档

1. **[测试运行指南](../TEST_RUN_GUIDE.md)** - 理解测试运行机制
2. **[测试命令参考](TESTING_COMMANDS.md)** - 所有测试命令
3. **[CLAUDE.md](../CLAUDE.md)** - 项目开发指南
4. **[API 文档](reference/API_REFERENCE.md)** - API 接口说明

## 🆘 遇到问题？

### 测试失败
```bash
# 查看详细错误
pytest tests/unit/api/test_failing.py -v -s --tb=long

# 只运行失败的测试
pytest --lf
```

### 环境问题
```bash
# 检查环境
make env-check

# 重新安装
make clean install
```

### 依赖问题
```bash
# 更新依赖
make lock-deps

# 验证依赖
make verify-deps
```

## 💡 开发技巧

### 1. 使用测试标记
```bash
# 只运行单元测试
pytest -m "unit"

# 排除慢测试
pytest -m "not slow"

# 运行特定类型测试
pytest -m "api"
```

### 2. 并行测试
```bash
# 安装并行测试工具
pip install pytest-xdist

# 并行运行
pytest -n auto
```

### 3. 调试测试
```bash
# 在测试失败时进入调试器
pytest --pdb

# 在第一个失败时停止
pytest -x
```

## 🎉 成功标准

- ✅ 所有测试通过：`make test`
- ✅ 覆盖率达标：`make coverage`（>80%）
- ✅ 代码质量检查：`make lint`
- ✅ 类型检查通过：`make type-check`

记住：**测试第一，代码第二！** 🧪✨