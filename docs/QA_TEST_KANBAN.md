# 📋 足球预测项目测试质量看板

## 📊 项目概况
- **项目名称**: 足球预测系统
- **测试质量负责人**: Claude AI
- **开始日期**: 2025-09-25
- **目标覆盖率**: 80%+

---

## 🎯 任务看板

### Backlog（未准备）

*待信息确认的任务*

### Ready（可开始）

#### Phase 1. 核心业务优先（高优先级）

* `T-101` **PredictionService** 单元测试
  * **目标文件**: `src/models/prediction_service.py`
  * **覆盖**: `predict_match()`、`predict_batch()`、`get_model_info()`、`predict_match_probability()`、`get_prediction_confidence()`
  * **场景**: 输入校验、模型未加载/加载失败、预测异常、边界值、批量空集与大集
  * **测试位置**: `tests/unit/models/test_prediction_service.py`
  * **验收标准**: 覆盖率达到 90%+，包含所有关键路径和异常处理
  * **交付物**: 完整的单元测试文件，包含中文注释
  * **验证命令**: `pytest tests/unit/models/test_prediction_service.py -v --cov=src.models.prediction_service`

* `T-102` **ModelTrainer** 单元测试
  * **目标文件**: `src/models/model_training.py`
  * **覆盖**: `train_model()`、`evaluate_model()`、`save_model()`、`prepare_training_data()`、`validate_model_performance()`
  * **场景**: 数据不足、训练中断、评估失败、超参不当、模型文件损坏
  * **测试位置**: `tests/unit/models/test_model_training.py`
  * **验收标准**: 覆盖率达到 90%+，包含所有训练和验证场景
  * **交付物**: 完整的单元测试文件，包含中文注释
  * **验证命令**: `pytest tests/unit/models/test_model_training.py -v --cov=src.models.model_training`

* `T-103` **FeatureCalculator** 单元测试
  * **目标文件**: `src/features/feature_calculator.py`
  * **覆盖**: `calculate_match_features()`、`calculate_team_features()`、`calculate_advanced_features()`、`validate_feature_consistency()`
  * **场景**: 缺失值、异常值、时间序列边界、特征一致性校验
  * **测试位置**: `tests/unit/features/test_feature_calculator.py`
  * **验收标准**: 覆盖率达到 90%+，包含所有特征计算和验证逻辑
  * **交付物**: 完整的单元测试文件，包含中文注释
  * **验证命令**: `pytest tests/unit/features/test_feature_calculator.py -v --cov=src.features.feature_calculator`

#### Phase 2. 数据处理与存储（中优先级）

* `T-201` **FootballDataCollector**（采集器）测试
  * **目标文件**: `src/data/collectors/football_data_collector.py`
  * **工具**: 使用 `responses`/`requests-mock`
  * **场景**: API 限流、超时、结构变更、错误码与重试
  * **测试位置**: `tests/unit/data/test_football_data_collector.py`
  * **验收标准**: 覆盖率达到 85%+，模拟各种 API 异常情况
  * **交付物**: 完整的单元测试文件，包含 Mock 和异常测试
  * **验证命令**: `pytest tests/unit/data/test_football_data_collector.py -v --cov=src.data.collectors.football_data_collector`

* `T-202` **DataProcessor** 清洗/转换测试
  * **目标文件**: `src/data/processing/data_processor.py`
  * **场景**: 空值、异常值、格式不符、列缺失、类型转换错误
  * **测试位置**: `tests/unit/data/test_data_processor.py`
  * **验收标准**: 覆盖率达到 85%+，包含各种数据异常处理
  * **交付物**: 完整的单元测试文件，包含数据清洗测试
  * **验证命令**: `pytest tests/unit/data/test_data_processor.py -v --cov=src.data.processing.data_processor`

* `T-203` **DatabaseManager** 与 ORM 模型 CRUD/事务测试
  * **目标文件**: `src/database/connection.py` 和 `src/database/models/`
  * **工具**: 使用 sqlite 内存库
  * **场景**: 连接池异常、事务回滚、外键约束、并发（伪并发/事务序列化）
  * **测试位置**: `tests/unit/database/test_connection.py`、`tests/unit/database/test_models.py`
  * **验收标准**: 覆盖率达到 85%+，包含数据库操作和事务测试
  * **交付物**: 完整的数据库测试文件
  * **验证命令**: `pytest tests/unit/database/ -v --cov=src.database`

#### Phase 3. 流与任务（中优先级）

* `T-301` Kafka Producer/Consumer 行为测试
  * **目标文件**: `src/streaming/kafka_producer.py`、`src/streaming/kafka_consumer.py`
  * **工具**: 使用 `aiokafka` mock 或自建接口抽象 + 假实现
  * **场景**: 断线重连、消息积压、重平衡（模拟）、偏移管理
  * **测试位置**: `tests/unit/streaming/test_kafka_producer.py`、`tests/unit/streaming/test_kafka_consumer.py`
  * **验收标准**: 覆盖率达到 80%+，包含各种异常场景
  * **交付物**: 完整的 Kafka 测试文件
  * **验证命令**: `pytest tests/unit/streaming/ -v --cov=src.streaming`

* `T-302` Celery 任务测试
  * **目标文件**: `src/tasks/celery_app.py`、`src/tasks/streaming_tasks.py`
  * **配置**: `CELERY_TASK_ALWAYS_EAGER=True` 或使用 `celery.app.control` mock
  * **场景**: 重试、超时、路由、失败回调
  * **测试位置**: `tests/unit/tasks/test_celery_app.py`、`tests/unit/tasks/test_streaming_tasks.py`
  * **验收标准**: 覆盖率达到 80%+，包含任务调度和异常处理
  * **交付物**: 完整的 Celery 测试文件
  * **验证命令**: `pytest tests/unit/tasks/ -v --cov=src.tasks`

#### Phase 4. 监控与工具（低优先级）

* `T-401` MetricsCollector 指标采集测试
  * **目标文件**: `src/monitoring/metrics_collector.py`
  * **场景**: 系统/业务指标、异常捕获、聚合、后端故障
  * **测试位置**: `tests/unit/monitoring/test_metrics_collector.py`
  * **验收标准**: 覆盖率达到 75%+，包含各种指标采集场景
  * **交付物**: 完整的监控测试文件
  * **验证命令**: `pytest tests/unit/monitoring/ -v --cov=src.monitoring`

* `T-402` utils/config/logging 的健壮性测试
  * **目标文件**: `src/utils/config.py`、`src/utils/logging.py`
  * **场景**: 配置缺失/错误、日志轮转、异常路径
  * **测试位置**: `tests/unit/utils/test_config.py`、`tests/unit/utils/test_logging.py`
  * **验收标准**: 覆盖率达到 75%+，包含各种配置和日志场景
  * **交付物**: 完整的工具函数测试文件
  * **验证命令**: `pytest tests/unit/utils/ -v --cov=src.utils`

#### Phase 5. 质量门禁与 CI

* `T-501` 覆盖率门槛 ≥80%（本地与 CI 一致）
  * **描述**: 在 `pytest.ini`/`pyproject.toml` 开启 `--cov-fail-under=80`；Make 目标 `cov.enforce`
  * **验收标准**: 覆盖率低于 80% 时测试失败，`cov.enforce` 目标可用
  * **交付物**: 更新的配置文件和 Makefile
  * **验证命令**: `make cov.enforce`（当覆盖率≥80%时应通过）

* `T-502` GitHub Actions CI（如已存在则修复）
  * **描述**: 步骤：安装依赖 → 缓存 → 运行 `make test` → 上传 `htmlcov` 为 artifact → 徽章更新
  * **验收标准**: CI 流水线成功，产出覆盖率 artifact
  * **交付物**: 完整的 GitHub Actions 配置
  * **验证命令**: 推送代码后 CI 运行成功

* `T-503` 生成与持续更新测试策略文档
  * **目标文件**: `docs/TESTING_STRATEGY.md`
  * **内容**: 分层策略（unit/integration/e2e）、数据构造规范、Mock/Stub 最佳实践、随机化与 Hypothesis、基准性能、回归套件
  * **验收标准**: 文档完整、可读、可执行，包含足球预测系统的业务上下文
  * **交付物**: 完整的测试策略文档
  * **验证命令**: 文档可通过浏览器正常查看

### In Progress（进行中）

*当前正在执行的任务*

### Blocked（阻塞）

*被阻塞的任务*

### Review（待评审）

*等待评审的任务*

### Done（已完成）

*已完成的任务*

#### Phase 0. 基线与覆盖率恢复 ✅ **已完成**

* `T-001` ✅ **修复 `.coveragerc` 使核心模块纳入统计**
  * **描述**: 当前 0% 因 `.coveragerc` 排除了业务目录。修复后应统计 `src/` 下核心模块：`data/`、`features/`、`models/`、`database/`、`streaming/`、`tasks/`、`monitoring/`、`utils/`。
  * **验收标准**:
    - ✅ `.coveragerc` 配置正确包含所有核心模块
    - ✅ 运行 pytest 后覆盖率不再为 0% (当前: 65.90%)
    - ✅ `htmlcov/index.html` 生成并可查看
  * **交付物**: 更新后的 `.coveragerc`；`pytest` 覆盖率基线报告（终端 + `htmlcov/`）
  * **验证命令**: `pytest --maxfail=1 -q --cov=src --cov-report=term-missing:skip-covered --cov-report=html`

* `T-002` ✅ **创建 `pytest.ini` 统一配置**
  * **描述**: 统一 pytest 配置，设置默认覆盖率参数和测试标记
  * **验收标准**:
    - ✅ 默认使用 `--cov=src --cov-report=term-missing:skip-covered`
    - ✅ 正确收集 `tests/` 目录下的测试
    - ✅ 忽略 `.venv|venv|migrations|.tox` 目录
    - ✅ 增加常用 markers（unit、integration、e2e、slow、db、kafka、celery、ml）
  * **交付物**: 完整的 `pytest.ini` 配置文件
  * **验证命令**: `pytest --help` 确认配置生效

* `T-003` ✅ **建立一键脚本与 Make 目标**
  * **描述**: 创建便捷的测试脚本和 Makefile 目标
  * **验收标准**:
    - ✅ `scripts/test_all.sh` - 运行全部测试 + 覆盖率
    - ✅ `scripts/test_unit.sh` - 仅 unit 测试（`-m unit`）
    - ✅ `scripts/test_integration.sh` - 仅 integration 测试（`-m integration`）
    - ✅ `scripts/gen_cov_html.sh` - 生成 `htmlcov/`
    - ✅ Makefile 目标：`test`、`test.unit`、`test.int`、`cov.html`、`cov.enforce`
  * **交付物**: 可执行的脚本文件和更新的 Makefile
  * **验证命令**: `make test`、`make test.unit`、`make test.int` 等命令都能正常执行

---

## 📝 每日进展日志

### 2025-09-25
- **完成项**:
  - ✅ T-001: 修复 .coveragerc 使核心模块纳入统计 - 移除了排除规则，覆盖率从 0% 提升到 65.90%
  - ✅ T-002: 创建 pytest.ini 统一配置 - 添加了覆盖率默认参数和所需测试标记
  - ✅ T-003: 建立一键脚本与 Make 目标 - 创建了 test_all.sh、test_unit.sh、test_integration.sh、gen_cov_html.sh 脚本和对应的 Makefile 目标
  - ✅ 基线覆盖率测试 - 成功生成覆盖率报告，当前单元测试覆盖率：65.90%
- **问题**:
  - 覆盖率还未达到 80% 目标，需要补充核心模块的测试用例
  - 部分模块覆盖率仍较低，如 data_collection_tasks.py (32%)、stream_processor.py (42%) 等
- **下一步**:
  - 开始 Phase 1: 执行 T-101 PredictionService 单元测试
  - 分析未覆盖的 Top 10 文件并制定补充测试计划

---

## 📈 进度统计

- **总任务数**: 17
- **已完成**: 3
- **进行中**: 0
- **待开始**: 14
- **已阻塞**: 0
- **完成率**: 17.6%
- **当前覆盖率**: 65.90% (单元测试)

---

## 🎯 质量目标

- **代码覆盖率**: ≥80%
- **单元测试覆盖率**: ≥90%
- **集成测试覆盖率**: ≥70%
- **核心业务逻辑覆盖率**: ≥95%
- **测试通过率**: 100%

---

## 📋 注意事项

1. 所有新建/修改文件都带**中文注释**
2. 每完成一个任务：本地验证 → 更新看板列状态 → `git add -A && git commit -m "<task_id> <概要>"`
3. 若缺少依赖，自动新增 `requirements-dev.txt` 并安装
4. 测试文件使用 `arrange-act-assert` 结构
5. 优先使用参数化、`hypothesis` 补充边界测试