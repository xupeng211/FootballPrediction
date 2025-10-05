# 测试运行指南

## 🚨 重要说明：为什么我的测试评估是错误的

### 问题根源
1. **pytest.ini 自动配置了覆盖率** - 第54-56行已经配置了 `--cov=src --cov-report=html --cov-report=term-missing`
2. **我使用了错误的命令** - 我单独运行一个测试文件，导致覆盖率不完整
3. **没有使用 Makefile** - 项目已经提供了标准化的测试命令

## ✅ 正确的测试运行方式

### 1. 运行所有单元测试（推荐）
```bash
make test
# 或
make test-full
```

### 2. 运行带覆盖率的测试
```bash
make coverage
# 这会运行：pytest -m "unit" --cov=src --cov-report=term-missing --cov-fail-under=80
```

### 3. 运行特定模块的测试
```bash
# Phase 1 核心模块（正确方式）
pytest tests/unit/api/test_data.py tests/unit/api/test_features.py tests/unit/api/test_predictions.py -v

# 带覆盖率
pytest tests/unit/api/test_data.py tests/unit/api/test_features.py tests/unit/api/test_predictions.py --cov=src --cov-report=term-missing
```

### 4. 按标记运行测试
```bash
# 只运行单元测试
pytest -m "unit"

# 运行API测试
pytest -m "api"

# 运行数据库测试
pytest -m "database"
```

## 📊 实际测试结果（2025-10-05）

### Phase 1 核心模块覆盖率
- `src/api/data.py`: **90%** 覆盖率 ✅ (17个测试)
- `src/api/features.py`: **88%** 覆盖率 ✅ (28个测试)
- `src/api/predictions.py`: **88%** 覆盖率 ✅ (27个测试)
- `src/api/health.py`: **28%** 覆盖率 ⚠️ (5个基础测试)

### 命令示例
```bash
# 获取Phase 1覆盖率报告
pytest tests/unit/api/test_data.py tests/unit/api/test_features.py tests/unit/api/test_predictions.py --cov=src --cov-report=term-missing | grep "src/api/"

# 输出示例：
# src/api/data.py                                   181     15     42      6    90%
# src/api/features.py                               154     20     34      3    88%
# src/api/predictions.py                            141     19     22      0    88%
```

## 🔧 测试配置说明

### pytest.ini 关键配置
- `testpaths`: 自动搜索 tests/unit, tests/integration, tests/e2e
- `markers`: 定义了测试标记（unit, integration, e2e等）
- `addopts`: 默认添加覆盖率参数
- `-m "not legacy"`: 自动排除遗留测试

### Makefile 测试命令
```bash
make test          # 运行基础测试
make test-full     # 运行完整测试套件
make coverage      # 运行覆盖率测试（80%阈值）
make coverage-fast # 快速覆盖率测试
```

## 💡 最佳实践

### 对于新开发者
1. **始终使用 Makefile 命令** - 不要直接运行 pytest
2. **检查测试标记** - 使用 `-m` 参数运行特定类型的测试
3. **查看覆盖率报告** - 运行 `make coverage` 后查看 `htmlcov/index.html`

### 常用命令组合
```bash
# 开发时快速测试
make test-quick

# 提交前完整检查
make prepush

# CI环境验证
make ci

# 只运行失败的测试
pytest --lf

# 并行运行测试（需要pytest-xdist）
pytest -n auto
```

## 🚫 避免的错误

1. **不要单独运行一个测试文件来评估整体覆盖率**
   ```bash
   # 错误 ❌
   pytest tests/unit/api/test_health.py --cov=src
   ```

2. **不要忽略 pytest.ini 的默认配置**
   ```bash
   # 正确 ✅
   pytest tests/unit/api/  # 会自动应用pytest.ini中的覆盖率配置
   ```

3. **不要忘记测试标记**
   ```bash
   # 运行所有单元测试（不包括集成测试）
   pytest -m "unit"
   ```

## 📋 测试文件组织

```
tests/
├── unit/          # 单元测试（标记：unit）
│   ├── api/       # API测试（标记：api）
│   ├── database/  # 数据库测试（标记：database）
│   └── services/  # 服务测试
├── integration/   # 集成测试（标记：integration）
├── e2e/          # 端到端测试（标记：e2e）
└── legacy/       # 遗留测试（默认排除）
```

## 🎯 Phase 覆盖率目标

- **Phase 1** (30%): ✅ 已达成（实际：~85%）
- **Phase 2** (50%): 需要评估服务层测试
- **Phase 3** (65%): 需要评估数据层测试
- **Phase 4** (80%): 最终目标