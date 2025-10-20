# 测试策略文档

> 版本：1.0
> 更新日期：2025-10-17
> 负责人：测试体系总控执行器

## 📋 目录

1. [测试原则](#测试原则)
2. [测试金字塔](#测试金字塔)
3. [测试命名约定](#测试命名约定)
4. [测试数据管理](#测试数据管理)
5. [Mock和Stub策略](#mock和stub策略)
6. [断言最佳实践](#断言最佳实践)
7. [测试执行指南](#测试执行指南)
8. [覆盖率要求](#覆盖率要求)
9. [持续集成](#持续集成)

## 🎯 测试原则

### 1. FAST原则
- **Fast（快速）**：测试应该快速执行
- **Autonomous（自治）**：测试之间不应有依赖
- **Repeatable（可重复）**：测试结果应该一致
- **Self-validating（自验证）**：测试应该有明确的通过/失败结果

### 2. FIRST原则（适用于单元测试）
- **Fast**：快速反馈
- **Independent**：独立测试
- **Repeatable**：可重复执行
- **Self-validating**：自验证
- **Timely**：及时编写

### 3. 测试优先级
1. **Smoke Tests** - 最关键功能，必须通过
2. **Unit Tests** - 单元逻辑，核心业务
3. **Integration Tests** - 模块交互
4. **E2E Tests** - 完整流程

## 📊 测试金字塔

```
        /\
       /  \     E2E Tests (少量)
      /____\
     /      \   Integration Tests (适量)
    /________\
   /          \ Unit Tests (大量)
  /____________\
```

### 各层说明

#### Unit Tests（单元测试）- 70%
- **目标**：测试单个函数/方法/类
- **特点**：快速、独立、精确
- **工具**：pytest + mock + faker
- **示例**：测试预测算法的准确性

#### Integration Tests（集成测试）- 20%
- **目标**：测试模块间交互
- **特点**：测试真实交互，使用测试数据库
- **工具**：pytest + TestContainers
- **示例**：测试API与数据库的交互

#### E2E Tests（端到端测试）- 10%
- **目标**：测试完整业务流程
- **特点**：真实环境、完整流程
- **工具**：Playwright/Selenium
- **示例**：完整的用户注册到预测流程

## 📝 测试命名约定

### 1. 文件命名
```
tests/
├── unit/                          # 单元测试
│   ├── services/
│   │   ├── test_prediction_service.py
│   │   └── test_data_processing_service.py
│   ├── api/
│   │   ├── test_predictions_api.py
│   │   └── test_matches_api.py
│   └── utils/
│       ├── test_validators.py
│       └── test_formatters.py
├── integration/                   # 集成测试
│   ├── test_api_integration.py
│   └── test_database_integration.py
├── e2e/                          # 端到端测试
│   └── test_user_workflows.py
└── smoke/                        # 烟雾测试
    └── test_core_functionality.py
```

### 2. 类命名
```python
class TestPredictionService:        # 测试类
class TestPredictionAPI:
class TestPredictionIntegration:
```

### 3. 方法命名
格式：`test_[功能]_[场景]_[期望结果]`

```python
# ✅ 好的命名
def test_create_prediction_with_valid_data_returns_201(self):
def test_create_prediction_with_invalid_match_id_returns_422(self):
def test_batch_prediction_with_empty_list_returns_422(self):
def test_prediction_calculation_with_extreme_probabilities_returns_error(self):

# ❌ 不好的命名
def test_prediction_1(self):
def test_data(self):
def test_it_works(self):
```

## 🏭 测试数据管理

### 1. 使用Faker生成动态数据
```python
# ✅ 推荐：使用Faker工厂
from tests.factories.fake_data_improved import create_valid_prediction

def test_prediction_creation():
    prediction_data = create_valid_prediction(match_id=123)
    # ... 测试逻辑

# ❌ 避免：硬编码测试数据
def test_prediction_creation():
    prediction_data = {
        "match_id": 123,
        "home_win_prob": 0.5,
        # ... 大量硬编码
    }
```

### 2. 测试数据验证
```python
# 使用Pydantic模型验证
class PredictionData(BaseModel):
    match_id: int
    home_win_prob: float
    # ... 字段定义和验证规则

# 在工厂中使用
try:
    return PredictionData(**data)
except ValidationError as e:
    raise DataValidationError(f"Invalid data: {e}")
```

### 3. 测试数据隔离
```python
@pytest.fixture
def clean_test_data():
    """提供干净的测试数据"""
    return {
        "match_id": 123,
        "model_version": "test_v1.0"
    }
```

## 🎭 Mock和Stub策略

### 1. Mock使用原则
- **最小化Mock**：只在必要时使用
- **精确Patch**：使用精确的路径，避免全局mock
- **真实场景**：Mock应该反映真实场景

### 2. 正确的Mock使用
```python
# ✅ 推荐：精确patch
@patch('src.services.prediction_service.external_api_call')
def test_prediction_with_external_data(self, mock_api):
    mock_api.return_value.json.return_value = {"odds": [1.5, 3.2, 5.8]}
    # ... 测试逻辑

# ❌ 避免：全局mock
# 在conftest.py中全局替换sys.modules["requests"]
```

### 3. Stub vs Mock
- **Stub**：提供预定义的响应，无状态
- **Mock**：记录交互，可验证调用

```python
# Stub示例
def stub_response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"data": "test"}
    return response

# Mock示例
def test_interaction():
    mock_service = Mock()
    result = process_data(mock_service)
    mock_service.process.assert_called_once_with(data)
```

## ✅ 断言最佳实践

### 1. 明确的断言
```python
# ✅ 推荐：明确期望
assert response.status_code == 201, f"Expected 201, got {response.status_code}"

# ❌ 避免：模糊断言
assert response.status_code in [200, 201, 202]
```

### 2. 完整的验证
```python
def test_prediction_response_format(response):
    """验证预测响应格式"""
    required_fields = [
        "match_id", "home_win_prob", "draw_prob", "away_win_prob",
        "predicted_outcome", "confidence", "model_version"
    ]

    data = response.json()
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    # 验证数据范围
    assert 0 <= data["confidence"] <= 1
    assert data["predicted_outcome"] in ["home", "draw", "away"]
```

### 3. 错误消息
```python
# ✅ 提供有用的错误信息
assert user.is_active, f"User {user.id} should be active"

# ❌ 无帮助的错误信息
assert user.is_active
```

## 🚀 测试执行指南

### 1. 本地开发
```bash
# 快速测试（日常开发）
make test-quick          # 60秒超时

# 单元测试
make test-unit           # 只运行单元测试

# 覆盖率检查
make coverage-local      # 25%阈值

# 完整测试（提交前）
make prepush            # ruff + mypy + pytest
```

### 2. 按标记运行
```bash
# 运行特定类型的测试
pytest -m "unit"        # 单元测试
pytest -m "integration" # 集成测试
pytest -m "smoke"       # 烟雾测试
pytest -m "not slow"    # 排除慢测试

# 组合标记
pytest -m "unit and fast"    # 快速单元测试
pytest -m "api or database" # API或数据库测试
```

### 3. 调试测试
```bash
# 详细输出
pytest -v -s test_file.py

# 在第一个失败时停止
pytest -x

# 只运行失败的测试
pytest --lf

# 调试模式
pytest --pdb
```

## 📈 覆盖率要求

### 1. 当前目标
- **总体覆盖率**：≥30%（Phase 3目标）
- **本地开发**：≥25%（最低门槛）
- **关键模块**：
  - config_loader.py: 100%
  - dict_utils.py: 100%
  - validators.py: ≥40%
  - formatters.py: ≥60%

### 2. 覆盖率报告
```bash
# 生成HTML报告
pytest --cov=src --cov-report=html

# 查看未覆盖的行
pytest --cov=src --cov-report=term-missing

# 按模块查看
pytest --cov=src.utils --cov-report=term
```

### 3. 覆盖率优化策略
1. **优先测试核心业务逻辑**
2. **覆盖边界条件**
3. **测试错误处理路径**
4. **忽略第三方库和生成代码**

## 🔄 持续集成

### 1. CI流程
```yaml
# GitHub Actions示例
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: make install
      - name: Run tests
        run: make ci
```

### 2. 质量门禁
- 所有测试必须通过
- 覆盖率必须达标
- 代码质量检查必须通过
- 无新的警告或错误

### 3. 测试报告
- 测试结果自动上报
- 覆盖率趋势追踪
- 失败测试通知

## 📚 最佳实践清单

### ✅ 做什么
- [ ] 使用描述性的测试名称
- [ ] 每个测试只验证一个行为
- [ ] 使用Faker生成测试数据
- [ ] 编写清晰的断言消息
- [ ] 测试边界条件
- [ ] 测试错误处理
- [ ] 保持测试快速执行
- [ ] 定期重构测试代码

### ❌ 不做什么
- [ ] 不要在测试间共享状态
- [ ] 不要测试第三方库
- [ ] 不要使用复杂的Mock设置
- [ ] 不要忽略测试失败
- [ ] 不要提交跳过的测试
- [ ] 不要编写太长的测试方法
- [ ] 不要测试实现细节

## 🛠️ 常见问题

### Q: 测试运行太慢怎么办？
A:
1. 使用pytest-xdist并行执行
2. 减少数据库操作
3. 使用更轻量的Mock
4. 按标记运行部分测试

### Q: 测试不稳定怎么办？
A:
1. 检查测试依赖
2. 使用固定种子
3. 添加等待或重试
4. 检查资源清理

### Q: 如何测试私有方法？
A:
1. 通过公共接口测试
2. 使用继承访问
3. 考虑是否需要测试

### Q: Mock太多怎么办？
A:
1. 使用集成测试
2. 使用TestContainers
3. 创建测试专用服务
4. 重构代码减少依赖

## 📖 参考资料

- [pytest文档](https://docs.pytest.org/)
- [Faker文档](https://faker.readthedocs.io/)
- [测试覆盖率文档](https://coverage.readthedocs.io/)
- [Python测试最佳实践](https://docs.python-guide.org/writing/tests/)

---

**更新记录**：
- 2025-10-17：初始版本，基于Phase 1-3改进总结
