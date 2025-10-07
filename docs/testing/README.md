# 测试覆盖率提升指南

## 📋 概述

本指南提供了系统性的测试覆盖率提升方案，帮助团队从当前的16%覆盖率提升到80%的目标。

## 🚀 快速开始

### 1. 运行快速启动脚本

```bash
# 一键分析和生成改进计划
python scripts/testing/quick_start.py
```

该脚本会：
- 检查环境准备情况
- 分析当前覆盖率状况
- 生成优先改进计划
- 创建第一周任务列表

### 2. 查看改进计划

```bash
# 查看详细改进计划
cat test_improvement_plan.json

# 查看本周任务
cat test_week_1_tasks.md
```

### 3. 开始执行

```bash
# 运行测试
make test.unit

# 查看覆盖率
make coverage-local

# 打开详细报告
open htmlcov/index.html
```

## 📚 文档结构

```
docs/testing/
├── README.md                    # 本文件
├── EXECUTION_PLAN.md            # 详细执行计划
├── STRATEGY.md                  # 测试策略（待创建）
├── GUIDE.md                     # 测试编写指南（待创建）
├── MOCK_GUIDE.md                # Mock使用指南（待创建）
└── examples/                    # 示例代码
    ├── test_examples.py
    ├── mock_examples.py
    └── factory_examples.py
```

## 🎯 改进路线图

### 第一阶段：基础设施（目标：20%）
- [x] Docker测试环境
- [x] Mock实现（Kafka、Feast）
- [ ] TestContainers配置
- [ ] CI/CD流水线
- [ ] 依赖问题修复

### 第二阶段：核心模块（目标：35%）
- [ ] API层测试
- [ ] 工具类测试
- [ ] 配置模块测试
- [ ] 服务基类测试

### 第三阶段：服务层（目标：55%）
- [ ] 数据处理服务
- [ ] 缓存服务
- [ ] 数据库层
- [ ] 消息队列

### 第四阶段：端到端（目标：80%）
- [ ] 集成测试
- [ ] E2E测试
- [ ] 性能测试
- [ ] 监控体系

## 🛠️ 工具和框架

### 核心工具
- **pytest**: 测试框架
- **pytest-cov**: 覆盖率工具
- **pytest-mock**: Mock工具
- **TestContainers**: 容器化测试
- **Factory Boy**: 测试数据工厂

### 可选工具
- **pytest-benchmark**: 性能测试
- **pytest-asyncio**: 异步测试
- **pytest-xdist**: 并行测试
- **Hypothesis**: 属性测试

## 📝 测试编写规范

### 1. 测试命名

```python
# 良好的测试命名
def test_user_registration_with_valid_data_returns_success():
    """测试使用有效数据注册用户返回成功"""
    pass

def test_api_health_check_returns_200_when_all_services_healthy():
    """测试健康检查API在所有服务健康时返回200"""
    pass
```

### 2. 测试结构（AAA模式）

```python
def test_calculate_team_form():
    # Arrange - 准备测试数据
    team = Team(name="Test Team")
    matches = [
        Match(result="win"),
        Match(result="draw"),
        Match(result="lose")
    ]

    # Act - 执行操作
    form = calculate_team_form(team, matches)

    # Assert - 验证结果
    assert form == "WDL"
    assert form.win_count == 1
    assert form.draw_count == 1
    assert form.loss_count == 1
```

### 3. 使用Fixtures

```python
@pytest.fixture
def sample_team():
    """创建示例球队"""
    return TeamFactory(name="Sample Team")

@pytest.fixture
def sample_league(sample_team):
    """创建包含球队的联赛"""
    league = LeagueFactory()
    league.teams.append(sample_team)
    return league

def test_league_get_team(league, sample_team):
    """测试联赛获取球队"""
    team = league.get_team(sample_team.id)
    assert team == sample_team
```

### 4. Mock使用原则

```python
# ✅ 好的实践：Mock外部依赖
def test_api_call_with_external_service():
    with patch('services.external_api.Client') as mock_client:
        mock_client.get.return_value = {"status": "ok"}

        result = my_service.call_external_api()

        assert result["status"] == "ok"
        mock_client.get.assert_called_once()

# ❌ 不好的实践：Mock业务逻辑
def test_calculate_price_with_mock():
    with patch('services.pricing.calculate_price') as mock_calc:
        mock_calc.return_value = 100
        # 这不应该Mock，应该测试实际逻辑
```

## 🔧 常见问题解决

### 1. 测试环境问题

```bash
# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 重新安装依赖
pip install -r requirements/dev.lock

# 检查测试配置
python -m pytest --collect-only | head
```

### 2. 覆盖率不提升

```bash
# 检查哪些行未被覆盖
pytest --cov=src --cov-report=html

# 查看HTML报告，找出红色行
open htmlcov/index.html

# 专注于低覆盖率模块
pytest tests/unit/low_coverage_module.py --cov=src.low_coverage_module
```

### 3. 测试太慢

```bash
# 使用并行测试
pytest -n auto

# 只运行变更相关的测试
pytest --diff-cover

# 使用快速测试模式
make test-quick
```

## 📊 覆盖率监控

### 1. 本地监控

```bash
# 生成趋势报告
python scripts/monitor_coverage.py

# 查看覆盖率变化
git diff --stat coverage.json
```

### 2. CI/CD集成

GitHub Actions会自动：
- 运行所有测试
- 检查覆盖率阈值
- 生成覆盖率报告
- 发送到Codecov

### 3. 质量门禁

- PR必须通过所有测试
- 覆盖率不能下降
- 必须通过代码质量检查

## 🎯 最佳实践

### 1. 测试金字塔

```
    E2E Tests (10%)
   ─────────────────
  Integration Tests (20%)
 ─────────────────────────
Unit Tests (70%)
```

### 2. 测试原则

- **FAST**: 测试应该快速运行
- **ISOLATED**: 测试之间相互独立
- **REPEATABLE**: 测试结果应该一致
- **SELF-VALIDATING**: 测试应该有明确的通过/失败结果
- **TIMELY**: 测试应该及时编写

### 3. 代码审查检查点

- [ ] 是否有对应的测试？
- [ ] 测试覆盖了所有边界情况？
- [ ] Mock使用是否合理？
- [ ] 测试数据是否独立？
- [ ] 测试名称是否清晰？

## 🆘 获取帮助

### 文档资源
- [pytest官方文档](https://pytest.org/)
- [TestContainers文档](https://testcontainers-python.readthedocs.io/)
- [Factory Boy文档](https://factoryboy.readthedocs.io/)

### 团队支持
- **技术支持**: @tech-lead
- **工具问题**: @devops
- **测试策略**: @qa-team
- **Slack频道**: #testing

### 常用命令

```bash
# 查看所有测试命令
make help

# 运行特定测试
pytest tests/unit/api/test_health.py -v

# 运行带标记的测试
pytest -m "unit and not slow"

# 调试测试
pytest tests/unit/api/test_health.py -v -s --tb=long

# 只运行失败的测试
pytest --lf

# 生成覆盖率基准
pytest --cov=src --cov-report=json --cov-fail-under=0
```

## 📈 成功案例

### 案例1：API健康检查测试
- **之前**: 15%覆盖率
- **改进**: 添加了全面的健康检查测试
- **之后**: 75%覆盖率
- **耗时**: 2小时

### 案例2：时间工具测试
- **之前**: 71%覆盖率
- **改进**: 添加了边界值和异常测试
- **之后**: 85%覆盖率
- **耗时**: 3小时

### 案例3：配置模块测试
- **之前**: 68%覆盖率
- **改进**: 添加了配置验证和环境测试
- **之后**: 90%覆盖率
- **耗时**: 4小时

---

记住：**持续改进比一次性完美更重要**。每天进步一点点，最终会达到目标！