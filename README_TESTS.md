# 足球预测系统测试框架

## 概述

本文档描述了FootballPrediction项目的完整测试框架，包含单元测试、集成测试和端到端测试的完整覆盖。

## 测试架构

### 三层测试架构

```
tests/
├── unit/                    # 单元测试 - 测试单个组件
│   ├── test_data_cleaner.py           # 数据清洗器测试
│   ├── test_database_manager.py       # 数据库管理器测试
│   └── test_feature_store.py          # 特征存储测试
├── integration/             # 集成测试 - 测试组件间交互
│   ├── test_data_pipeline.py          # 数据管道集成测试
│   ├── test_scheduler.py              # 任务调度器测试
│   └── test_cache_consistency.py      # 缓存一致性测试
├── e2e/                     # 端到端测试 - 测试完整业务流程
│   ├── test_api_predictions.py        # API预测端到端测试
│   ├── test_lineage_tracking.py       # 数据血缘追踪测试
│   └── test_backtest_accuracy.py      # 回测准确性测试
├── conftest.py              # pytest配置和共享fixtures
├── __init__.py              # 测试模块初始化
└── requirements.txt         # 测试依赖
```

## 核心测试组件

### 1. 单元测试 (Unit Tests)

#### test_data_cleaner.py
- **测试目标**: `FootballDataCleaner`类
- **覆盖范围**:
  - 比赛数据清洗逻辑
  - 赔率数据校验
  - 状态标准化
  - 缺失值处理
  - 异常数据检测和处理
- **关键测试**:
  - 正常数据清洗成功
  - 分数范围验证
  - 赔率概率一致性
  - 批量清洗性能

#### test_database_manager.py
- **测试目标**: `DatabaseManager`类
- **覆盖范围**:
  - 数据库连接池管理
  - 多角色权限控制 (reader/writer/admin)
  - 事务管理
  - 连接异常处理和恢复
  - CRUD操作基础功能
- **关键测试**:
  - 连接池初始化和耗尽处理
  - 角色权限验证
  - 并发操作安全性
  - SQL注入防护

#### test_feature_store.py
- **测试目标**: `FeatureStore`类
- **覆盖范围**:
  - 特征注册和元数据管理
  - 特征读取和查询
  - 特征版本管理
  - 特征组管理
  - 特征血缘追踪
- **关键测试**:
  - 特征注册成功
  - 版本控制机制
  - 数据类型验证
  - 并发特征操作

### 2. 集成测试 (Integration Tests)

#### test_data_pipeline.py
- **测试目标**: Bronze→Silver→Gold→Feature Store→Prediction完整数据流
- **覆盖范围**:
  - 数据层级转换验证
  - 端到端数据流完整性
  - 数据质量保证
  - 管道性能监控
  - 错误处理和恢复机制
- **关键测试**:
  - 完整数据管道流程
  - 数据质量验证管道
  - 管道错误处理和恢复
  - 性能基准测试
  - 并发管道执行

#### test_scheduler.py
- **测试目标**: Celery任务调度、执行、重试机制
- **覆盖范围**:
  - 任务依赖关系和执行顺序
  - 失败重试机制
  - 任务优先级和队列管理
  - 并发执行控制
  - 任务监控和状态跟踪
- **关键测试**:
  - 任务依赖链执行
  - 指数退避重试
  - 任务优先级队列
  - 并发任务处理

#### test_cache_consistency.py
- **测试目标**: Redis与PostgreSQL数据一致性
- **覆盖范围**:
  - 读写延迟一致性
  - 缓存失效策略
  - 缓存预热和更新
  - 数据同步机制
  - 故障恢复一致性
- **关键测试**:
  - 写透缓存一致性
  - 缓存旁路模式
  - TTL失效处理
  - 缓存预热策略

### 3. 端到端测试 (E2E Tests)

#### test_api_predictions.py
- **测试目标**: FastAPI预测接口的完整功能
- **覆盖范围**:
  - API端点响应和状态码
  - 预测结果的概率分布验证
  - 响应格式和数据完整性
  - 错误处理和异常情况
  - 性能和响应时间
- **关键测试**:
  - 概率分布验证(总和为1)
  - 批量预测端点
  - API限流机制
  - 安全测试(SQL注入防护)

#### test_lineage_tracking.py
- **测试目标**: OpenLineage数据血缘追踪完整流程
- **覆盖范围**:
  - 数据流追踪：输入→清洗→特征→预测
  - 血缘关系记录和查询
  - 数据质量监控
  - 血缘可视化数据
  - 影响分析和依赖追踪
- **关键测试**:
  - 完整数据管道血缘
  - 数据集血缘关系查询
  - 影响分析功能
  - OpenLineage标准兼容性

#### test_backtest_accuracy.py
- **测试目标**: 模型预测准确性的历史回测验证
- **覆盖范围**:
  - 历史数据回测流程
  - 预测准确性指标验证
  - 模型性能基准比较
  - 准确性>=基线要求验证
  - 不同时间段的性能稳定性
- **关键测试**:
  - 基础回测执行
  - 准确性基线验证(≥60%)
  - 不同结果类型准确性
  - 性能稳定性分析
  - 基准方法比较

## 配置文件

### pytest.ini
pytest的主配置文件，定义：
- 测试发现模式
- 输出配置
- 测试标记定义
- 警告过滤
- 异步测试支持

### conftest.py
pytest的全局配置和共享fixtures：
- 测试环境设置(数据库、缓存、API)
- 共享fixtures(数据库连接、Redis客户端、API客户端)
- 测试数据工厂
- Mock外部API响应
- 测试工具函数

### requirements.txt
测试环境的完整依赖列表：
- 核心测试框架(pytest, pytest-asyncio)
- 数据库测试(pytest-postgresql, pytest-redis)
- HTTP测试(httpx, fastapi)
- 数据处理(pandas, numpy)
- 机器学习(scikit-learn, mlflow)
- 代码质量工具(black, flake8, mypy)

## 质量目标

### 覆盖率目标
- **总体覆盖率**: ≥80%
- **核心业务逻辑**: ≥95%
- **新增代码**: 100%

### 性能基准
- **API响应时间**: <2秒
- **数据管道吞吐量**: ≥30记录/秒
- **并发测试成功率**: ≥80%
- **预测准确性**: ≥60%

### 测试标记
- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.e2e`: 端到端测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.docker`: 需要Docker环境
- `@pytest.mark.asyncio`: 异步测试

## 使用指南

### 环境准备

1. **安装测试依赖**:
```bash
pip install -r tests/requirements.txt
```

2. **启动依赖服务**(集成测试):
```bash
docker-compose -f docker-compose.test.yml up -d
```

### 运行测试

1. **运行所有测试**:
```bash
pytest tests/
```

2. **按类型运行**:
```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 端到端测试
pytest tests/e2e/
```

3. **按标记运行**:
```bash
# 快速测试(排除慢速测试)
pytest -m "not slow"

# 不需要Docker的测试
pytest -m "not docker"

# 只运行异步测试
pytest -m asyncio
```

4. **生成覆盖率报告**:
```bash
pytest --cov=src --cov-report=html tests/
```

5. **并行执行**:
```bash
pytest -n auto tests/
```

### 开发工作流

1. **编写新功能时**:
   - 先写单元测试
   - 实现功能代码
   - 运行测试确保通过
   - 检查覆盖率

2. **修改现有功能时**:
   - 运行相关测试确保不破坏现有功能
   - 更新或添加测试用例
   - 确保覆盖率不降低

3. **提交前检查**:
```bash
# 运行所有测试
pytest tests/

# 检查代码质量
black tests/
flake8 tests/
mypy tests/

# 生成覆盖率报告
pytest --cov=src --cov-report=term-missing tests/
```

## 测试数据管理

### 测试数据原则
- 使用真实但脱敏的数据结构
- 包含边界条件和异常情况
- 数据量适中，确保测试执行效率
- 测试间数据隔离

### Mock策略
- 外部API调用全部Mock
- 数据库使用内存SQLite或Mock
- Redis使用FakeRedis
- 文件系统操作使用临时目录

### 数据清理
- 每个测试自动清理数据
- 使用fixtures确保环境一致性
- 测试失败时仍能正常清理

## 持续集成

### GitHub Actions配置
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.10
      - name: Install dependencies
        run: |
          pip install -r tests/requirements.txt
      - name: Run tests
        run: |
          pytest tests/ --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 性能监控
- 跟踪测试执行时间
- 监控覆盖率趋势
- 自动化性能回归检测

## 故障排除

### 常见问题

1. **测试依赖缺失**:
   - 确保安装了tests/requirements.txt中的所有依赖
   - 检查系统级依赖(如PostgreSQL开发库)

2. **Docker服务未启动**:
   - 运行集成测试前启动docker-compose.test.yml
   - 检查端口冲突

3. **异步测试问题**:
   - 确保使用@pytest.mark.asyncio装饰器
   - 检查pytest-asyncio配置

4. **覆盖率不足**:
   - 查看覆盖率报告找出未覆盖代码
   - 添加边界条件和异常情况测试

### 调试技巧

1. **使用pytest选项**:
```bash
# 详细输出
pytest -v

# 在第一个失败时停止
pytest -x

# 显示本地变量
pytest -l

# 进入调试器
pytest --pdb
```

2. **使用日志**:
```bash
# 显示日志输出
pytest -s --log-cli-level=DEBUG
```

## 最佳实践

### 测试设计原则
- **独立性**: 每个测试应该独立运行
- **可重复性**: 测试结果应该一致
- **快速执行**: 单元测试应该快速执行
- **清晰命名**: 测试名称应该清楚表达测试内容
- **单一职责**: 每个测试只验证一个功能点

### 代码组织
- 按功能模块组织测试文件
- 使用类组织相关测试方法
- 合理使用fixtures避免重复代码
- 适当的测试数据抽象

### 维护建议
- 定期更新测试依赖
- 保持测试代码质量
- 及时修复失败的测试
- 定期审查测试覆盖率

## 总结

本测试框架提供了完整的测试覆盖，从单个组件的单元测试到完整业务流程的端到端测试。通过三层测试架构，确保了代码质量和系统可靠性。框架设计考虑了可扩展性和可维护性，为项目的长期发展提供了坚实的质量保障。
