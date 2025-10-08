# 📈 测试覆盖率提升计划

## 📊 当前状态

- **项目名称**: 足球预测系统
- **源代码文件**: 134个Python文件
- **当前覆盖率**: 40%（基线）
- **目标覆盖率**: 80%
- **测试架构**: 三层架构（unit/legacy/e2e）

## 🎯 Phase 4A: 达到50%（2周）

### 优先级1：核心工具模块（预计+10%）

#### 1. utils模块

- [ ] `src/utils/string_utils.py` - 字符串处理工具
- [ ] `src/utils/dict_utils.py` - 字典处理工具
- [ ] `src/utils/time_utils.py` - 时间处理工具
- [ ] `src/utils/crypto_utils.py` - 加密工具
- [ ] `src/utils/data_validator.py` - 数据验证工具
- [ ] `src/utils/file_utils.py` - 文件操作工具
- [ ] `src/utils/response.py` - 响应格式化工具

#### 2. config模块

- [ ] `src/config/fastapi_config.py` - FastAPI配置

### 优先级2：API模块（预计+5%）

#### 1. 核心API

- [ ] `src/api/health.py` - 健康检查端点
- [ ] `src/api/schemas.py` - API数据模型
- [ ] `src/api/data.py` - 数据管理端点

## 🎯 Phase 4B: 达到60%（3周）

### 优先级3：数据库模块（预计+5%）

#### 1. 数据库模型

- [ ] `src/database/models/` 下的所有模型文件
- [ ] `src/database/migrations/` 迁移相关

#### 2. 数据库工具

- [ ] 数据库连接和会话管理
- [ ] 事务处理工具

### 优先级4：服务层（预计+5%）

#### 1. 核心服务

- [ ] `src/services/prediction_service.py` - 预测服务
- [ ] `src/services/auth_service.py` - 认证服务
- [ ] `src/services/data_service.py` - 数据服务

## 🎯 Phase 4C: 达到70%（3周）

### 优先级5：中间件（预计+5%）

#### 1. 中间件组件

- [ ] 认证中间件
- [ ] 日志中间件
- [ ] 错误处理中间件
- [ ] 限流中间件

### 优先级6：数据处理（预计+5%）

#### 1. 数据收集器

- [ ] `src/data/collectors/` 数据收集器

#### 2. 特征工程

- [ ] `src/data/features/` 特征处理

## 🎯 Phase 4D: 达到80%（4周）

### 优先级7：高级功能（预计+10%）

#### 1. AI模块

- [ ] `src/ai/` AI相关功能

#### 2. 监控模块

- [ ] `src/monitoring/` 监控功能

#### 3. 任务调度

- [ ] `src/scheduler/` 调度器
- [ ] `src/tasks/` 任务处理

#### 4. 缓存模块

- [ ] `src/cache/` 缓存功能

#### 5. 流处理

- [ ] `src/streaming/` 流处理

## 📝 实施指南

### 1. 测试编写原则

```python
# 测试文件命名：test_<module_name>.py
# 测试类命名：Test<ClassName>
# 测试方法命名：test_<function_name>_<scenario>

class TestStringUtils:
    @pytest.fixture
    def sample_data(self):
        return {"test": "data"}

    def test_function_success_case(self, sample_data):
        # Given - 准备测试数据
        # When - 执行操作
        # Then - 验证结果
        assert result is not None
```

### 2. Mock使用指南

```python
# 使用我们已经建立的Mock架构
from tests.helpers import (
    MockRedis,
    create_sqlite_sessionmaker,
    apply_mlflow_mocks,
    apply_kafka_mocks
)
```

### 3. 覆盖率检查

```bash
# 运行特定模块的覆盖率
pytest tests/unit/test_utils.py --cov=src.utils --cov-report=term-missing

# 生成HTML报告
pytest tests/unit --cov=src --cov-report=html

# 查看未覆盖的行
open htmlcov/index.html
```

## 🏆 成功指标

### 每周检查点

- **Week 1**: 覆盖率达到45%
- **Week 2**: 覆盖率达到50%
- **Week 4**: 覆盖率达到55%
- **Week 6**: 覆盖率达到60%
- **Week 9**: 覆盖率达到65%
- **Week 12**: 覆盖率达到70%
- **Week 16**: 覆盖率达到80%

### 质量标准

- 每个测试都有清晰的描述
- 测试覆盖正常、边界和异常情况
- Mock正确使用，不依赖外部服务
- 测试运行速度快（单元测试<1秒）

## 🚀 快速开始

### 第一步：安装依赖

```bash
make install
source .venv/bin/activate
```

### 第二步：查看当前覆盖率

```bash
python scripts/run_full_coverage.py
```

### 第三步：开始编写测试

```bash
# 选择一个模块开始，例如utils
vim tests/unit/utils/test_string_utils.py
```

### 第四步：运行测试验证

```bash
pytest tests/unit/utils/test_string_utils.py -v
```

## 📋 跟踪进度

使用以下命令跟踪进度：

```bash
# 查看覆盖率趋势
python scripts/coverage_trend.py

# 查看未覆盖的文件
python scripts/list_uncovered_files.py

# 生成覆盖率报告
make coverage
```

---

*最后更新：2025-01-04*
*负责人：Claude Code*
