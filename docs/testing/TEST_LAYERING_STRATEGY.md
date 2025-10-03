# 测试分层策略文档

## 概述

本文档定义了FootballPrediction项目的测试分层架构和策略，确保测试金字塔的合理构建和维护。

## 测试金字塔架构

### 1. 单元测试 (Unit Tests) - 70%
**目标**: 快速验证单个函数、类或模块的行为

**特点**:
- 执行速度: < 1秒/测试
- 隔离性: 完全隔离外部依赖
- 覆盖率: 每个函数至少1个测试
- 维护成本: 低

**范围**:
- 业务逻辑函数
- 数据模型验证
- 工具函数
- API端点的核心逻辑

**文件结构**:
```
tests/unit/
├── api/          # API层单元测试
├── core/         # 核心业务逻辑测试
├── database/     # 数据库操作测试
├── utils/        # 工具函数测试
├── models/       # 数据模型测试
└── services/     # 服务层测试
```

### 2. 集成测试 (Integration Tests) - 20%
**目标**: 验证多个组件协同工作的正确性

**特点**:
- 执行速度: 1-10秒/测试
- 集成度: 部分外部依赖
- 覆盖率: 关键集成路径
- 维护成本: 中等

**范围**:
- API与数据库交互
- 缓存系统集成
- 外部服务集成
- 数据流完整性

**文件结构**:
```
tests/integration/
├── api_database/     # API与数据库集成
├── api_cache/        # API与缓存集成
├── database_cache/   # 数据库与缓存集成
├── external_services/ # 外部服务集成
└── end_to_end_flows/  # 端到端流程
```

### 3. 端到端测试 (E2E Tests) - 10%
**目标**: 验证完整用户场景和业务流程

**特点**:
- 执行速度: 10-60秒/测试
- 真实性: 接近生产环境
- 覆盖率: 核心业务场景
- 维护成本: 高

**范围**:
- 完整预测流程
- 用户注册到预测
- 数据处理管道
- 系统健康检查

**文件结构**:
```
tests/e2e/
├── user_workflows/    # 用户工作流
├── prediction_flows/  # 预测流程
├── data_pipelines/    # 数据管道
└── system_health/     # 系统健康
```

## 测试分层原则

### 1. FAST原则
- **Fast**: 测试应该快速执行
- **Automated**: 完全自动化，无需人工干预
- **Self-contained**: 测试自包含，不依赖外部状态
- **Traceable**: 测试失败时能快速定位问题

### 2. 测试隔离原则
- 每个测试独立运行
- 测试之间不共享状态
- 使用Mock/Stub隔离外部依赖
- 测试顺序无关紧要

### 3. 可重复性原则
- 测试结果应该一致
- 不依赖当前时间或随机数据
- 使用固定测试数据
- 环境无关性

## 测试数据管理策略

### 1. 测试数据分类
```python
# 单元测试数据 - 最小化、快速生成
UNIT_TEST_DATA = {
    "minimal_match": {"id": 1, "home_team": "A", "away_team": "B"},
    "simple_prediction": {"match_id": 1, "outcome": "home"}
}

# 集成测试数据 - 真实但可控
INTEGRATION_TEST_DATA = {
    "full_match_data": {...},  # 完整的比赛数据
    "real_prediction_flow": {...}  # 真实的预测流程数据
}

# E2E测试数据 - 接近生产
E2E_TEST_DATA = {
    "production_like_scenarios": [...],  # 生产类场景数据
    "edge_cases": [...]  # 边界情况
}
```

### 2. 数据生命周期管理
- **创建**: 使用Factory模式
- **清理**: 自动化清理机制
- **隔离**: 每个测试使用独立数据
- **复用**: 公共数据模板

## Mock策略分层

### 1. 单元测试Mock策略
```python
# 完全Mock所有外部依赖
@patch('src.database.get_async_session')
@patch('src.cache.redis_client')
@patch('src.mlflow_client')
def test_prediction_logic():
    # 只测试核心逻辑
    pass
```

### 2. 集成测试Mock策略
```python
# 只Mock外部服务，内部组件真实交互
@patch('src.external_payment_api')
def test_payment_integration():
    # 测试内部支付流程集成
    pass
```

### 3. E2E测试Mock策略
```python
# 最小化Mock，使用真实环境
# 只Mock不可控的外部服务（如第三方API）
@patch('src.third_party_football_api')
def test_complete_prediction_flow():
    # 测试完整流程
    pass
```

## 测试执行策略

### 1. 本地开发
```bash
# 快速单元测试
make test-unit

# 集成测试（可选）
make test-integration

# 代码质量检查
make prepush
```

### 2. CI/CD管道
```yaml
# 阶段1: 单元测试（快速失败）
- name: Unit Tests
  run: pytest tests/unit/ --cov --cov-fail-under=20

# 阶段2: 集成测试
- name: Integration Tests
  run: pytest tests/integration/ --cov-append

# 阶段3: E2E测试（仅在发布分支）
- name: E2E Tests
  run: pytest tests/e2e/
  if: github.ref == 'refs/heads/main'
```

### 3. 测试环境管理
```python
# 测试环境配置
TEST_ENVIRONMENTS = {
    "unit": {
        "database": "sqlite:///:memory:",
        "cache": "mock",
        "external_services": "mock"
    },
    "integration": {
        "database": "postgresql://test_user:test_pass@localhost/test_db",
        "cache": "redis://localhost:6379/1",
        "external_services": "mock"
    },
    "e2e": {
        "database": "postgresql://test_user:test_pass@staging-db/test_db",
        "cache": "redis://staging-cache:6379/0",
        "external_services": "staging"
    }
}
```

## 质量标准

### 1. 覆盖率要求
- **单元测试**: 20%+ 基线，新代码80%+
- **集成测试**: 关键路径100%
- **E2E测试**: 核心业务流程100%

### 2. 测试质量指标
- **通过率**: 100%（在CI中）
- **执行时间**: 单元<5分钟，集成<15分钟，E2E<30分钟
- **稳定性**: 测试失败率<1%
- **可维护性**: 测试代码复杂度<业务代码复杂度

### 3. 代码审查标准
- 每个功能至少1个单元测试
- 集成点必须有集成测试
- 重大变更必须有E2E测试
- Mock使用合理性审查

## 测试工具链

### 1. 核心工具
```bash
pytest          # 测试框架
pytest-cov      # 覆盖率
pytest-asyncio  # 异步测试
pytest-mock     # Mock支持
factory-boy     # 测试数据工厂
```

### 2. 质量工具
```bash
black            # 代码格式化
flake8           # 代码检查
mypy             # 类型检查
pre-commit       # Git钩子
```

### 3. 监控工具
```bash
pytest-html      # 测试报告
pytest-benchmark # 性能测试
pytest-xdist     # 并行测试
tox              # 多环境测试
```

## 最佳实践

### 1. 测试命名
```python
# 良好的测试命名
def test_should_return_home_win_when_home_team_strong():
    pass

def test_prediction_creation_with_invalid_data_should_raise_error():
    pass

# 避免的命名
def test_1():
    pass

def test_prediction():
    pass
```

### 2. 测试结构（AAA模式）
```python
def test_prediction_accuracy_calculation():
    # Arrange - 准备测试数据
    prediction = Prediction(outcome="home", confidence=0.8)
    actual_result = MatchResult(home_score=2, away_score=1)

    # Act - 执行操作
    accuracy = prediction.calculate_accuracy(actual_result)

    # Assert - 验证结果
    assert accuracy == 1.0
```

### 3. 测试数据管理
```python
# 使用Factory模式
class MatchFactory(factory.Factory):
    class Meta:
        model = Match

    id = factory.Sequence(lambda n: n + 1)
    home_team = factory.Faker('company')
    away_team = factory.Faker('company')

    @classmethod
    def finished(cls, **kwargs):
        return cls(status='finished', **kwargs)
```

## 实施计划

### 阶段1: 基础建设（1周）
- [ ] 建立测试分层目录结构
- [ ] 配置测试环境和工具链
- [ ] 创建测试数据工厂
- [ ] 建立Mock策略规范

### 阶段2: 单元测试优化（2周）
- [ ] 重构现有单元测试
- [ ] 提升核心模块覆盖率
- [ ] 建立测试质量门禁
- [ ] 优化测试执行速度

### 阶段3: 集成测试实施（2周）
- [ ] 创建集成测试环境
- [ ] 实施关键集成路径测试
- [ ] 建立数据清理机制
- [ ] 配置CI集成

### 阶段4: E2E测试建设（1周）
- [ ] 搭建E2E测试环境
- [ ] 实施核心业务流程测试
- [ ] 建立测试数据管理
- [ ] 配置自动化执行

### 阶段5: 监控和优化（持续）
- [ ] 建立测试质量监控
- [ ] 实施测试报告系统
- [ ] 持续优化测试性能
- [ ] 定期评估和改进

## 成功指标

### 量化指标
- 单元测试覆盖率: 25%+
- 集成测试覆盖率: 60%+
- E2E测试覆盖率: 80%+
- 测试执行时间: 总计<45分钟
- 测试稳定性: 99%+

### 质量指标
- 开发者满意度: 8/10+
- 缺陷发现率: 90%+在测试阶段
- 回归测试效率: 95%+
- 代码审查效率: 提升30%

---

此文档将作为测试实施的指导原则，确保测试质量和效率的持续改进。