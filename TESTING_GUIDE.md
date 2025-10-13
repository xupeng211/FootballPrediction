# 测试选择指南

**更新日期**: 2025年1月13日

## 📋 测试命令速查表

### 日常开发（推荐）

```bash
# 快速测试单个模块
pytest tests/unit/utils/test_config_loader_comprehensive.py --cov=src.utils.config_loader

# 测试特定功能
pytest tests/unit/utils/ -k "test_dict" --cov=src.utils.dict_utils

# 运行已标记的快速测试
pytest -m "unit and fast" --cov=src --cov-report=term-missing
```

### 提交前验证

```bash
# 完整的覆盖率测试（稳定）
make coverage

# 或者使用pytest直接运行
pytest tests/unit --cov=src --cov-report=term-missing --cov-report=html
```

### 针对性测试

```bash
# 测试特定模块
make coverage-targeted MODULE=src.utils.config_loader

# 或使用pytest
pytest tests/unit/utils/test_config_loader_comprehensive.py --cov=src.utils.config_loader
```

### 性能测试

```bash
# 运行性能基准测试
pytest tests/performance/ --benchmark-only

# 生成性能报告
make benchmark-full
```

## 🎯 按场景选择测试

### 1. 开发新功能时

```bash
# 1. 快速单元测试
pytest tests/unit/your/module/ -v

# 2. 检查覆盖率
pytest tests/unit/your/module/ --cov=src.your.module --cov-report=term-missing

# 3. 运行相关测试
pytest tests/unit -k "your_test_keyword" --cov=src.your.module
```

### 2. 修复Bug时

```bash
# 1. 运行失败的测试
pytest --lf -v  # 只运行上次失败的测试

# 2. 运行相关测试
pytest tests/unit -k "bug_related_keyword" -v

# 3. 运行回归测试
pytest -m regression -v
```

### 3. 提交代码前

```bash
# 1. 运行所有单元测试
make test-unit

# 2. 检查覆盖率
make coverage-local  # 本地16%阈值
make coverage        # CI 22%阈值

# 3. 代码质量检查
make prepush  # 包含ruff、mypy、pytest
```

### 4. CI/CD环境

```bash
# 完整测试套件
make ci

# 或者分步执行
make lint
make coverage
make test-integration
```

## 📊 覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 | 状态 |
|------|------------|------------|------|
| config_loader.py | 100% | 100% | ✅ 达成 |
| dict_utils.py | 100% | 100% | ✅ 达成 |
| retry.py | 100% | 100% | ✅ 达成 |
| i18n.py | 87% | 90% | 🔄 接近 |
| warning_filters.py | 71% | 80% | 🔄 进行中 |
| formatters.py | 64% | 70% | 🔄 进行中 |
| response.py | 49% | 60% | 🔄 进行中 |
| helpers.py | 50% | 60% | 🔄 进行中 |
| string_utils.py | 48% | 60% | 🔄 进行中 |
| data_validator.py | 42% | 60% | 🔄 进行中 |
| time_utils.py | 39% | 50% | 🔄 进行中 |
| file_utils.py | 31% | 50% | 🔄 进行中 |
| crypto_utils.py | 25% | 50% | 🔄 进行中 |
| validators.py | 23% | 50% | 🔄 进行中 |

## 🚀 快速命令别名

在 `~/.bashrc` 或 `~/.zshrc` 中添加别名：

```bash
# 项目测试别名
alias ft='pytest tests/unit -v --tb=short'  # 快速测试
alias fc='make coverage-local'              # 快速覆盖率
alias tc='make coverage'                    # 完整覆盖率
alias pt='make prepush'                     # 提交前测试
alias ql='pytest -k "your_keyword"'        # 快速查找测试
```

## 📝 测试最佳实践

### 1. 测试组织

```python
# 测试文件命名
tests/unit/utils/test_config_loader.py  # 单个模块
tests/integration/test_api_integration.py  # 集成测试
tests/e2e/test_user_journey.py  # 端到端测试

# 测试类命名
class TestConfigLoader:
    """测试配置加载器"""

# 测试方法命名
def test_load_json_config_success():
    """测试成功加载JSON配置"""
```

### 2. 使用Fixtures

```python
# 在conftest.py中定义fixtures
@pytest.fixture
def sample_config():
    return {"key": "value", "number": 42}

# 在测试中使用
def test_config_processing(sample_config):
    assert process_config(sample_config)["key"] == "value"
```

### 3. Mock外部依赖

```python
from unittest.mock import patch, Mock

def test_with_mock():
    with patch('src.utils.external_api.get_data') as mock_get:
        mock_get.return_value = {"data": "mocked"}
        result = function_using_api()
        assert result["data"] == "mocked"
```

### 4. 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("test", "TEST"),
    ("Hello", "HELLO"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert uppercase(input) == expected
```

## ⚡ 性能优化技巧

### 1. 选择性运行测试

```bash
# 只运行失败的测试
pytest --lf

# 运行第一个失败的测试
pytest --lf -x

# 基于文件名过滤
pytest tests/unit/utils/test_*.py

# 基于测试名过滤
pytest -k "test_config"
```

### 2. 并行测试（谨慎使用）

```bash
# 使用4个进程
pytest -n 4

# 自动检测CPU核心数
pytest -n auto

# 注意：某些测试可能不支持并行执行
```

### 3. 跳过慢速测试

```bash
# 跳过标记为slow的测试
pytest -m "not slow"

# 只运行快速测试
pytest -m fast

# 跳过集成测试
pytest -m "not integration"
```

## 🔍 调试测试

### 1. 详细输出

```bash
# 显示详细输出
pytest -v

# 显示最详细的输出
pytest -vv

# 显示print语句
pytest -s

# 显示捕获的输出
pytest -ra
```

### 2. 调试模式

```bash
# 在第一个失败时进入pdb
pytest --pdb

# 在所有失败时进入pdb
pytest --pdb --pdb-failures

# 使用traceback
pytest --tb=long
```

### 3. 只运行特定测试

```bash
# 运行单个测试文件
pytest tests/unit/utils/test_dict_utils.py

# 运行单个测试类
pytest tests/unit/utils/test_dict_utils.py::TestDictUtils

# 运行单个测试方法
pytest tests/unit/utils/test_dict_utils.py::TestDictUtils::test_deep_merge
```

## 📋 检查清单

### 提交前检查

- [ ] 单元测试通过 (`make test-unit`)
- [ ] 覆盖率达标 (`make coverage-local`)
- [ ] 代码风格正确 (`make fmt`)
- [ ] 静态检查通过 (`make lint`)
- [ ] 类型检查通过 (`make mypy-check`)
- [ ] 没有未提交的 `.coverage` 文件

### 发布前检查

- [ ] 所有测试通过 (`make ci`)
- [ ] 集成测试通过 (`make test-integration`)
- [ ] 性能测试通过 (`make benchmark-full`)
- [ ] 安全扫描通过
- [ ] 文档已更新

## 🆘 常见问题

### Q: 测试运行太慢怎么办？

A:
1. 使用 `-k` 参数只运行相关测试
2. 跳过慢速测试 (`-m "not slow"`)
3. 使用 `--lf` 只运行失败的测试
4. 考虑使用并行测试（但要注意兼容性）

### Q: 覆盖率报告不准确？

A:
1. 删除旧的覆盖率数据：`rm .coverage`
2. 清理缓存：`rm -rf .pytest_cache`
3. 确保源代码路径正确

### Q: 测试偶尔失败？

A:
1. 检查测试的独立性（不要依赖测试顺序）
2. 使用fixtures确保测试环境一致
3. 检查是否有时间或随机性相关的问题

---

**记住**：快速反馈 > 完美测试。保持测试简单、快速、可靠！