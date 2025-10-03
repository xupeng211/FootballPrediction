# 测试最佳实践指南

## 📋 目录
1. [测试基本原则](#测试基本原则)
2. [Mock策略指南](#mock策略指南)
3. [测试数据管理](#测试数据管理)
4. [断言最佳实践](#断言最佳实践)
5. [常见反模式](#常见反模式)
6. [测试示例](#测试示例)
7. [持续改进](#持续改进)

## 测试基本原则

### 1. FAST原则
- **Fast** (快速): 测试应该快速执行，单元测试应在毫秒级完成
- **Automated** (自动化): 完全自动化，无需人工干预
- **Self-contained** (自包含): 测试自包含，不依赖外部状态
- **Traceable** (可追踪): 测试失败时能快速定位问题

### 2. 测试金字塔
```
      E2E Tests (10%)
    ──────────────────
   Integration Tests (20%)
  ──────────────────────────
 Unit Tests (70%) - 基础
```

### 3. 测试隔离
```python
# ✅ 好的做法 - 每个测试独立
def test_user_creation():
    user = User(name="Alice")
    assert user.name == "Alice"

def test_user_update():
    user = User(name="Bob")  # 创建新的实例
    user.update(name="Charlie")
    assert user.name == "Charlie"

# ❌ 错误的做法 - 测试间有依赖
user = None
def test_user_creation():
    global user
    user = User(name="Alice")
    assert user.name == "Alice"

def test_user_update():
    user.update(name="Bob")  # 依赖前一个测试
    assert user.name == "Bob"
```

## Mock策略指南

### 1. 何时使用Mock
- **外部依赖**: 数据库、缓存、第三方API
- **不确定因素**: 时间、随机数、文件系统
- **性能考虑**: 网络请求、长时间操作

### 2. Mock层次

#### 单元测试 - 完全Mock
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_prediction_service():
    # Mock所有外部依赖
    with patch('src.services.database.get_async_session') as mock_db, \
         patch('src.services.cache.redis_client') as mock_cache, \
         patch('src.services.mlflow_client') as mock_mlflow:

        # 配置Mock行为
        mock_db.return_value.execute.return_value.scalar_one_or_none.return_value = {
            "id": 1, "match_id": 123
        }

        # 测试业务逻辑
        from src.services.prediction import PredictionService
        service = PredictionService()
        result = await service.predict(123)

        # 验证结果
        assert result is not None
        mock_db.assert_called_once()
```

#### 集成测试 - 部分Mock
```python
@pytest.mark.asyncio
async def test_api_database_integration():
    # 只Mock外部服务，测试API和数据库的集成
    with patch('src.external.payment_gateway') as mock_payment:
        mock_payment.charge.return_value = {"status": "success"}

        # 使用真实数据库
        async with get_async_session() as session:
            # 测试完整流程
            result = await create_order(session, order_data)
            assert result.id is not None
```

#### E2E测试 - 最小Mock
```python
@pytest.mark.e2e
async def test_complete_user_flow():
    # 只Mock不可控的第三方服务
    with patch('src.external.football_api') as mock_api:
        mock_api.get_match_data.return_value = test_match_data

        # 使用真实环境
        response = await client.post("/api/predictions", json=prediction_data)
        assert response.status_code == 200
```

### 3. Mock最佳实践

```python
# ✅ 使用具体的返回值
mock_repository.get_user.return_value = User(id=1, name="Alice")

# ❌ 避免模糊的Mock
mock_repository.get_user.return_value = MagicMock()

# ✅ 验证调用参数
mock_service.process.assert_called_with(user_id=123, options={"fast": True})

# ❌ 不要过度验证内部实现
# mock_service._internal_method.assert_called()  # 不要这样做
```

## 测试数据管理

### 1. 使用工厂模式

```python
# tests/factories.py
import factory
from datetime import datetime

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker('name')
    email = factory.Faker('email')
    created_at = factory.LazyFunction(datetime.now)

class MatchFactory(factory.Factory):
    class Meta:
        model = Match

    id = factory.Sequence(lambda n: n + 1)
    home_team = factory.SubFactory(TeamFactory)
    away_team = factory.SubFactory(TeamFactory)
    status = factory.Iterator(['scheduled', 'live', 'finished'])

    @classmethod
    def finished(cls, **kwargs):
        return cls(status='finished', **kwargs)

    @classmethod
    def with_high_score(cls, **kwargs):
        return cls(home_score=factory.RandomInt(3, 5), **kwargs)
```

### 2. 测试数据构建器

```python
# tests/builders.py
class TestDataBuilder:
    def __init__(self):
        self._data = {}

    def with_user(self, user_id=1, name="Test User"):
        self._data['user'] = {'id': user_id, 'name': name}
        return self

    def with_match(self, match_id=1, status='scheduled'):
        self._data['match'] = {'id': match_id, 'status': status}
        return self

    def build(self):
        return self._data.copy()

# 使用示例
def test_scenario():
    data = (TestDataBuilder()
            .with_user(user_id=123)
            .with_match(status='live')
            .build())
```

### 3. Fixture使用

```python
# tests/conftest.py
import pytest
from factories import UserFactory, MatchFactory

@pytest.fixture
def sample_user():
    """返回一个基础用户"""
    return UserFactory()

@pytest.fixture
def sample_users():
    """返回用户列表"""
    return UserFactory.create_batch(5)

@pytest.fixture
def finished_match():
    """返回已完成的比赛"""
    return MatchFactory.finished()

@pytest.fixture
def live_match_with_players():
    """返回包含球员的直播比赛"""
    match = MatchFactory(status='live')
    match.home_team.players = PlayerFactory.create_batch(11)
    match.away_team.players = PlayerFactory.create_batch(11)
    return match
```

## 断言最佳实践

### 1. 明确的断言

```python
# ✅ 明确断言期望值
def test_calculate_score():
    result = calculate_score([2, 1, 0])
    assert result == 3

# ✅ 断言类型和属性
def test_user_creation():
    user = User(name="Alice")
    assert isinstance(user, User)
    assert user.name == "Alice"
    assert user.created_at is not None

# ❌ 模糊的断言
def test_something():
    result = some_function()
    assert result is not None  # 不够具体
```

### 2. 使用辅助函数

```python
# tests/helpers.py
def assert_valid_prediction(prediction):
    """验证预测对象的结构"""
    assert hasattr(prediction, 'id')
    assert hasattr(prediction, 'match_id')
    assert hasattr(prediction, 'predicted_winner')
    assert prediction.predicted_winner in ['home', 'away', 'draw']
    assert 0 <= prediction.confidence <= 1

def assert_api_response(response, expected_keys):
    """验证API响应格式"""
    assert response.status_code == 200
    data = response.json()
    for key in expected_keys:
        assert key in data, f"Missing key: {key}"
    return data

# 测试中使用
def test_prediction_creation():
    prediction = create_prediction(match_id=123, winner="home")
    assert_valid_prediction(prediction)
```

### 3. 参数化测试

```python
import pytest

@pytest.mark.parametrize("input_data,expected", [
    ([1, 2, 3], 6),
    ([0, 0, 0], 0),
    ([-1, 1, 0], 0),
    ([100, 200, 300], 600),
])
def test_sum_calculator(input_data, expected):
    assert sum(input_data) == expected

@pytest.mark.parametrize("status,expected_state", [
    ("scheduled", "upcoming"),
    ("live", "active"),
    ("finished", "completed"),
    ("cancelled", "cancelled"),
])
def test_match_state_mapping(status, expected_state):
    match = Match(status=status)
    assert match.state == expected_state
```

## 常见反模式

### 1. 测试实现细节

```python
# ❌ 测试私有方法
def test_private_method():
    calculator = Calculator()
    result = calculator._add(2, 3)  # 不要测试私有方法
    assert result == 5

# ✅ 测试公共接口
def test_addition():
    calculator = Calculator()
    result = calculator.calculate("2 + 3")
    assert result == 5
```

### 2. 过度Mock

```python
# ❌ Mock太多东西
def test_overmocked():
    with patch('module.ClassA') as mock_a, \
         patch('module.ClassB') as mock_b, \
         patch('module.ClassC') as mock_c:
        # 测试几乎什么都没测试
        pass

# ✅ 只Mock必要的依赖
def test_focused():
    with patch('module.external_service') as mock_service:
        mock_service.get_data.return_value = test_data
        result = process_data()
        assert result is correct
```

### 3. 脆弱的测试

```python
# ❌ 依赖实现细节
def test_fragile():
    users = User.objects.all()
    assert users[0].name == "Alice"  # 依赖数据库顺序

# ✅ 稳定的测试
def test_stable():
    user = User.objects.get(id=1)
    assert user.name == "Alice"
```

### 4. 测试多个东西

```python
# ❌ 一个测试多个断言
def test_too_much():
    user = User(name="Alice")
    assert user.name == "Alice"
    assert user.email is not None
    assert user.created_at is not None
    assert user.is_active is True
    assert user.can_login() is True

# ✅ 分离关注点
def test_user_name():
    user = User(name="Alice")
    assert user.name == "Alice"

def test_user_email():
    user = User(email="test@example.com")
    assert user.email == "test@example.com"
```

## 测试示例

### 1. API测试示例

```python
# tests/unit/api/test_predictions.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

def test_create_prediction_success(client, sample_prediction_data):
    """测试成功创建预测"""
    response = client.post(
        "/api/predictions",
        json=sample_prediction_data
    )

    assert response.status_code == 201

    data = response.json()
    assert data["match_id"] == sample_prediction_data["match_id"]
    assert data["predicted_winner"] == sample_prediction_data["predicted_winner"]
    assert "id" in data
    assert "created_at" in data

def test_create_prediction_invalid_data(client):
    """测试无效数据"""
    invalid_data = {"match_id": -1}  # 无效的match_id

    response = client.post("/api/predictions", json=invalid_data)

    assert response.status_code == 422
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_get_prediction_with_mock():
    """使用Mock的异步测试"""
    mock_prediction = {
        "id": 1,
        "match_id": 123,
        "predicted_winner": "home",
        "confidence": 0.85
    }

    with patch('src.services.prediction.get_prediction') as mock_get:
        mock_get.return_value = mock_prediction

        from src.api.predictions import get_match_prediction
        result = await get_match_prediction(match_id=123)

        assert result["predicted_winner"] == "home"
        mock_get.assert_called_once_with(match_id=123)
```

### 2. 业务逻辑测试示例

```python
# tests/unit/services/test_prediction_logic.py
import pytest
from datetime import datetime

class TestPredictionLogic:
    def test_home_win_prediction(self):
        """测试主队胜预测逻辑"""
        match = Match(
            home_team=Team(strength=85),
            away_team=Team(strength=70),
            venue="home"
        )

        predictor = PredictionEngine()
        prediction = predictor.predict(match)

        assert prediction.winner == "home"
        assert prediction.confidence > 0.6

    def test_draw_prediction_when_strengths_equal(self):
        """测试实力相同时预测平局"""
        match = Match(
            home_team=Team(strength=75),
            away_team=Team(strength=75)
        )

        predictor = PredictionEngine()
        prediction = predictor.predict(match)

        assert prediction.winner == "draw"
        assert 0.3 <= prediction.confidence <= 0.5

    @pytest.mark.parametrize("home_strength,away_strength,expected", [
        (90, 60, "home"),
        (60, 90, "away"),
        (75, 75, "draw"),
        (85, 84, "home"),  # 主场优势
    ])
    def test_strength_based_prediction(self, home_strength, away_strength, expected):
        """参数化测试基于实力的预测"""
        match = Match(
            home_team=Team(strength=home_strength),
            away_team=Team(strength=away_strength)
        )

        predictor = PredictionEngine()
        prediction = predictor.predict(match)

        assert prediction.winner == expected
```

### 3. 数据库测试示例

```python
# tests/integration/test_database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_and_retrieve_user(async_session: AsyncSession):
    """测试用户创建和检索"""
    # 创建用户
    user = User(name="Alice", email="alice@example.com")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # 检索用户
    retrieved = await async_session.get(User, user.id)

    assert retrieved is not None
    assert retrieved.name == "Alice"
    assert retrieved.email == "alice@example.com"

@pytest.mark.asyncio
async def test_user_relationships(async_session: AsyncSession, sample_user):
    """测试用户关系"""
    # 创建比赛
    match = Match(
        home_team=Team(name="Team A"),
        away_team=Team(name="Team B"),
        predictor=sample_user
    )
    async_session.add(match)
    await async_session.commit()

    # 验证关系
    retrieved_user = await async_session.get(User, sample_user.id)
    assert len(retrieved_user.predictions) == 1
    assert retrieved_user.predictions[0].id == match.id
```

## 持续改进

### 1. 测试覆盖率目标
- **新代码**: 80%+ 覆盖率
- **关键模块**: 60%+ 覆盖率
- **整体项目**: 30%+ 覆盖率

### 2. 代码审查检查清单
- [ ] 每个新功能都有测试
- [ ] 测试覆盖了正常流程
- [ ] 测试覆盖了异常情况
- [ ] Mock使用合理
- [ ] 测试数据独立
- [ ] 测试命名清晰

### 3. 定期维护任务
- **每周**: 检查测试报告，处理失败的测试
- **每月**: 审查低覆盖率模块，制定改进计划
- **每季度**: 评估测试策略，更新最佳实践

### 4. 工具和命令

```bash
# 运行所有测试
make test

# 运行单元测试
make test.unit

# 运行覆盖率检查
make test.coverage

# 生成覆盖率报告
make cov.html

# 运行质量门禁
make test.quality-gate

# 生成质量监控报告
make test.monitor
```

### 5. 故障排查

```python
# 调试失败的测试
def test_failing_example():
    # 添加调试输出
    result = some_function()
    print(f"Debug: result={result}")  # 临时调试

    assert result == expected_value

# 使用pytest调试
pytest -s -v tests/unit/test_file.py::test_function

# 使用pdb调试
pytest --pdb tests/unit/test_file.py::test_function
```

## 总结

良好的测试实践是项目成功的关键。遵循这些最佳实践：

1. **保持简单**: 测试应该简单明了
2. **保持独立**: 每个测试应该独立运行
3. **保持快速**: 测试应该快速执行
4. **保持有意义**: 测试应该有明确的目的
5. **持续改进**: 定期审查和改进测试

记住：测试是代码的用户，良好的测试设计反映了良好的代码设计。

---

**文档版本**: 1.0
**最后更新**: 2025-01-03
**维护者**: 开发团队