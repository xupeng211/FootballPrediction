# 测试命令参考

## 🎯 快速开始

```bash
# 安装依赖
make install

# 运行所有测试
make test

# 查看测试覆盖率
make coverage
```

## 📋 常用测试命令

### 基础测试
| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `make test` | 运行所有测试 | 日常开发 |
| `make test-quick` | 快速单元测试 | 频繁代码变更 |
| `make test-phase1` | Phase 1 核心测试 | 验证核心功能 |
| `make test-api` | 所有 API 测试 | API 开发 |

### 覆盖率测试
| 命令 | 说明 | 阈值 |
|------|------|------|
| `make coverage` | 完整覆盖率测试 | 80% |
| `make coverage-fast` | 快速覆盖率（排除慢测试） | 80% |
| `make coverage-unit` | 单元测试覆盖率 | - |

### 按类型运行
```bash
# 单元测试
pytest -m "unit"

# 集成测试
pytest -m "integration"

# API 测试
pytest -m "api"

# 数据库测试
pytest -m "database"

# 排除慢测试
pytest -m "not slow"
```

## 🔍 查看测试结果

### HTML 覆盖率报告
```bash
# 生成报告
make coverage

# 查看报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 终端输出示例
```
src/api/data.py                                   181     15     42      6    90%
src/api/features.py                               154     20     34      3    88%
src/api/predictions.py                            141     19     22      0    88%
```

## ⚠️ 常见错误

### 1. 单独文件测试导致覆盖率不完整
```bash
# ❌ 错误
pytest tests/unit/api/test_health.py --cov=src

# ✅ 正确
pytest tests/unit/api/ --cov=src
```

### 2. 忽略测试标记
```bash
# ❌ 错误（可能包含不需要的测试）
pytest tests/

# ✅ 正确
pytest -m "unit"
```

### 3. 没有使用项目配置
```bash
# ❌ 错误（绕过 pytest.ini）
pytest --override-ini="addopts=" tests/

# ✅ 正确（使用项目配置）
pytest tests/
```

## 📊 Phase 测试指南

### Phase 1 - 核心业务逻辑（目标 30%）
```bash
make test-phase1
# 或
pytest tests/unit/api/test_data.py tests/unit/api/test_features.py tests/unit/api/test_predictions.py
```

### Phase 2 - 服务层（目标 50%）
```bash
pytest tests/unit/services/ -v
```

### Phase 3 - 数据层（目标 65%）
```bash
pytest tests/unit/database/ tests/unit/data/ -v
```

### Phase 4 - 集成测试（目标 80%）
```bash
pytest tests/integration/ -v
```

## 🚀 CI/CD 集成

### GitHub Actions
项目已配置自动运行：
- `make test` - 每次推送
- `make coverage` - Pull Request

### 本地预提交检查
```bash
make prepush
```

## 🛠️ 调试测试

### 运行失败的测试
```bash
pytest --lf  # 只运行上次失败的测试
```

### 显示详细输出
```bash
pytest -v -s tests/unit/api/test_health.py::test_health_check_success
```

### 调试模式
```bash
pytest --pdb tests/unit/api/test_health.py
```

### 并行运行
```bash
pytest -n auto  # 需要安装 pytest-xdist
```

## 📝 测试标记说明

| 标记 | 说明 | 用途 |
|------|------|------|
| `unit` | 单元测试 | 快速，隔离测试 |
| `integration` | 集成测试 | 模块间交互 |
| `e2e` | 端到端测试 | 完整流程 |
| `api` | API 测试 | HTTP 接口 |
| `database` | 数据库测试 | 数据持久化 |
| `slow` | 慢速测试 | 耗时操作 |
| `legacy` | 遗留测试 | 旧代码 |

## 💡 最佳实践

1. **开发阶段**
   ```bash
   make test-quick  # 快速反馈
   ```

2. **提交前**
   ```bash
   make prepush  # 完整检查
   ```

3. **PR 前**
   ```bash
   make coverage  # 确保覆盖率达标
   ```

4. **修复 Bug 后**
   ```bash
   pytest --lf -x  # 只运行相关测试
   ```
