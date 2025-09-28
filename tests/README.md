# 🧪 FootballPrediction 测试框架

本项目采用分层测试架构，配备AI驱动的质量保证系统，确保代码质量和系统可靠性。

## 📁 目录结构

```
tests/
├── conftest.py                   # 全局测试配置和共享fixtures
├── pytest.ini                   # pytest配置文件
├── README.md                     # 本文档
├── __init__.py                   # 测试模块初始化
├── auto_generated/               # 🆕 AI自动生成测试
│   ├── 34个测试文件               # 覆盖所有主要模块
│   ├── test_core_logger.py      # 核心日志系统测试
│   ├── test_models_common.py    # 通用模型测试
│   └── ...                      # 其他自动生成测试
├── unit/                         # 单元测试
│   ├── test_data_cleaner.py      # 数据清洗器测试
│   ├── test_database_manager.py  # 数据库管理器测试
│   └── test_feature_store.py     # 特征存储测试
├── integration/                  # 集成测试
│   ├── test_scheduler.py         # 任务调度器测试
│   └── test_cache_consistency.py # 缓存一致性测试
├── slow/                         # 慢测试集合
│   ├── unit/                     # 慢速单元测试
│   │   ├── test_data_collection_tasks_comprehensive.py
│   │   └── api/
│   │       ├── test_api_health_enhanced_slow.py
│   │       └── test_health_core.py
│   ├── integration/              # 慢速集成测试
│   │   └── test_data_pipeline.py
│   └── e2e/                      # 慢速端到端测试
│       ├── test_api_predictions.py
│       ├── test_lineage_tracking.py
│       ├── test_backtest_accuracy.py
│       └── test_complete_prediction_workflow.py
└── fixtures/                     # 测试数据和工厂
    └── __init__.py               # 测试夹具模块
```

## 🚀 快速开始

### 环境准备

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装测试依赖
pip install -r requirements-dev.txt

# 加载项目上下文
make context
```

### 运行测试

```bash
# 运行所有测试 (包括AI生成测试)
pytest tests/

# 运行特定类型的测试
pytest tests/unit/              # 单元测试
pytest tests/integration/       # 集成测试
pytest tests/e2e/              # 端到端测试
pytest tests/auto_generated/   # 🆕 AI自动生成测试

# 运行特定测试文件
pytest tests/unit/test_data_cleaner.py

# 运行特定测试方法
pytest tests/unit/test_data_cleaner.py::TestFootballDataCleaner::test_clean_match_data_success
```

### 测试标记

```bash
# 跳过需要Docker的测试
pytest -m "not docker"

# 只运行快速测试
pytest tests/unit

# 单独运行慢测试
pytest tests/slow

# 运行特定标记的测试
pytest -m "unit or integration"
```

### 覆盖率报告

```bash
# 生成完整覆盖率报告 (当前: 19.8%)
pytest --cov=src --cov-report=html

# 查看HTML报告
open htmlcov/index.html

# 快速覆盖率检查 (开发用, 阈值20%)
make coverage-fast

# 完整覆盖率检查 (生产目标80%)
make coverage

# 查看质量综合状态
make quality-dashboard
```

## 📊 测试分层说明

### 🔧 单元测试 (Unit Tests)
- **目标**: 测试单个函数、类或模块的功能
- **特点**: 快速执行、独立运行、使用Mock隔离依赖
- **覆盖率要求**: ≥ 80% (当前: 19.8%)
- **AI增强**: 34个自动生成测试文件覆盖主要模块

### 🔗 集成测试 (Integration Tests)
- **目标**: 测试多个模块间的协同工作
- **特点**: 使用真实或接近真实的依赖服务
- **需要**: Docker环境 (PostgreSQL, Redis等)

### 🌐 端到端测试 (E2E Tests)
- **目标**: 验证完整的业务流程
- **特点**: 模拟真实用户场景，验证系统整体功能
- **重点**: API接口、数据血缘、预测准确率

### 🤖 AI自动生成测试 (Auto-generated Tests)
- **目标**: 系统性提升代码覆盖率
- **特点**: 基于覆盖率分析自动生成，Mock外部依赖
- **覆盖范围**: 34个文件，涵盖所有主要系统模块
- **当前贡献**: 从7.7%基线提升至19.8%覆盖率

## ⚙️ 配置说明

### pytest.ini 主要配置

```ini
[tool:pytest]
# 测试发现
testpaths = tests
python_files = test_*.py

# 覆盖率设置（≥ 80%）
addopts = --cov=src --cov-fail-under=80

# 异步测试支持
asyncio_mode = auto

# 标记定义
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    docker: 需要Docker环境
```

### conftest.py 共享Fixtures

- `test_settings`: 测试环境配置
- `test_db_session`: 测试数据库会话
- `test_redis`: 测试Redis客户端
- `test_api_client`: 测试API客户端
- `sample_match_data`: 示例比赛数据
- `mock_external_apis`: 模拟外部API

## 🎯 测试最佳实践

### 1. 测试命名规范
```python
def test_[被测试的功能]_[测试场景]_[预期结果]:
    """测试描述：简明说明测试目的"""
    # Given - 准备测试数据
    # When - 执行被测试的操作
    # Then - 验证结果
```

### 2. 使用合适的断言
```python
# 使用具体的断言方法
assert result.status_code == 200
assert "success" in response_data
assert len(predictions) == 5

# 使用测试工具函数
from tests.conftest import assert_valid_probability_distribution
assert_valid_probability_distribution(prediction_data)
```

### 3. 异步测试
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 4. 参数化测试
```python
@pytest.mark.parametrize("input_value,expected", [
    (1, "home_win"),
    (2, "away_win"),
    (0, "draw")
])
def test_result_mapping(input_value, expected):
    assert map_score_to_result(input_value) == expected
```

## 🐳 Docker集成测试

集成测试需要Docker环境支持：

```bash
# 启动测试服务
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
pytest tests/integration/ --docker

# 清理测试环境
docker-compose -f docker-compose.test.yml down
```

## 📈 持续集成

### GitHub Actions配置示例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest tests/unit/ --cov=src
          pytest tests/integration/
          pytest tests/e2e/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 🎯 质量目标

| 指标 | 目标值 | 当前状态 | 趋势 |
|------|-------|---------|------|
| 代码覆盖率 | ≥ 80% (生产) / 40% (开发) | 🟡 19.8% | 📈 +12.1pp |
| AI自动生成测试 | 50+ 文件 | 🟢 34 文件 | 📈 完成 |
| 单元测试通过率 | 100% | ✅ 达成 | ✅ 稳定 |
| 集成测试通过率 | ≥ 95% | 🎯 目标 | ➡️ 待验证 |
| 测试执行时间 | < 10分钟 | 🎯 目标 | ➡️ 待优化 |
| 质量分数 | 80/100 | 🟡 45.2/100 | 📈 改进中 |

## 🔍 故障排查

### 常见问题

1. **导入错误**: 确保虚拟环境已激活，项目路径正确
2. **数据库连接失败**: 检查Docker服务是否运行
3. **异步测试失败**: 确保使用`@pytest.mark.asyncio`装饰器
4. **覆盖率不足**: 检查是否有未测试的代码路径

### 调试技巧

```bash
# 详细输出
pytest -v -s

# 只运行失败的测试
pytest --lf

# 进入调试模式
pytest --pdb

# 显示最慢的10个测试
pytest --durations=10
```

## 📞 支持

### 🆘 获取帮助
- 📖 **项目文档**: `docs/` - 完整的项目文档
- 📊 **质量系统**: [质量仪表板](../docs/_reports/TEST_COVERAGE_KANBAN.md) - 实时质量状态
- 📖 **质量指南**: [质量系统访问指南](../docs/_reports/REPORTS_ACCESS_GUIDE.md) - 使用说明
- 🐛 **报告问题**: 提交GitHub Issue并标记 `testing` 或 `quality-system` 标签
- 💬 **技术讨论**: 团队Slack频道

### 🤖 AI辅助测试
项目配备AI驱动的测试生成和质量改进系统：
- **自动测试生成**: `scripts/generate_tests.py` - 基于覆盖率分析生成测试
- **质量快照**: `make quality-snapshot` - 生成综合质量报告
- **缺陷追踪**: `docs/_reports/BUGFIX_TODO.md` - AI缺陷发现和修复管理

### 🚀 贡献测试
- **添加新测试**: 遵循现有测试模式和命名规范
- **提高覆盖率**: 重点关注低覆盖率模块
- **改进测试质量**: 添加边界条件和异常情况测试

---

**记住**: 好的测试是代码质量的保证，也是重构的安全网！🛡️
**AI增强**: 智能测试生成 + 质量监控 + 持续改进 = 更可靠的代码质量！🤖
