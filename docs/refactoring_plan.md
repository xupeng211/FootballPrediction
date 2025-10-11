# 文件重构计划

## 目标
将标记为 `# mypy: ignore-errors` 的大文件拆分为更小、更易管理的模块，提高代码质量和可维护性。

## 需要重构的文件列表

### 1. 高优先级（核心业务逻辑）

#### src/services/processing/caching/processing_cache.py (24个错误)
**问题**：文件过长，类型注解不完整
**重构方案**：
- 拆分为：
  - `src/services/processing/caching/base.py` - 基础缓存类
  - `src/services/processing/caching/config.py` - 缓存配置
  - `src/services/processing/caching/manager.py` - 缓存管理器
  - `src/services/processing/caching/utils.py` - 缓存工具函数

#### src/services/event_prediction_service.py (32个错误)
**问题**：动态属性访问，事件系统类型复杂
**重构方案**：
- 拆分为：
  - `src/services/event_prediction/publisher.py` - 事件发布
  - `src/services/event_prediction/updater.py` - 预测更新
  - `src/services/event_prediction/evaluator.py` - 预测评估
  - `src/services/event_prediction/validator.py` - 预测验证

#### src/services/strategy_prediction_service.py (16个错误)
**问题**：策略模式实现复杂
**重构方案**：
- 拆分为：
  - `src/services/strategy_prediction/context.py` - 策略上下文
  - `src/services/strategy_prediction/strategies/` - 各个策略实现
  - `src/services/strategy_prediction/factory.py` - 策略工厂

### 2. 中优先级（数据收集器）

#### src/collectors/scores_collector_improved.py (17个错误)
**重构方案**：
- 拆分为：
  - `src/collectors/scores/collector.py` - 主收集器
  - `src/collectors/scores/websocket.py` - WebSocket处理
  - `src/collectors/sources/api.py` - API数据源
  - `src/collectors/processors/normalizer.py` - 数据标准化

#### src/collectors/fixtures_collector.py (14个错误)
**重构方案**：
- 拆分为：
  - `src/collectors/fixtures/collector.py` - 主收集器
  - `src/collectors/fixtures/sources/` - 各数据源适配器

### 3. 低优先级（辅助功能）

#### src/patterns/facade.py (16个错误)
**重构方案**：
- 拆分为：
  - `src/patterns/facade/base.py` - 基础门面
  - `src/patterns/facade/implementations/` - 具体实现
  - `src/patterns/facade/factory.py` - 门面工厂

#### src/monitoring/metrics_exporter_mod/database_metrics.py (12个错误)
**重构方案**：
- 拆分为：
  - `src/monitoring/metrics/exporters/database.py` - 数据库指标
  - `src/monitoring/metrics/exporters/base.py` - 基础导出器

## 重构步骤

1. **准备阶段**
   - 创建新的目录结构
   - 设计接口和基类
   - 编写单元测试

2. **迁移阶段**
   - 逐个模块迁移
   - 保持原有接口兼容
   - 逐步移除旧代码

3. **验证阶段**
   - 运行完整测试套件
   - 性能基准测试
   - 代码审查

4. **清理阶段**
   - 删除旧文件
   - 更新导入
   - 移除 mypy: ignore-errors

## 预期收益

- **代码质量**：类型安全，更易理解
- **可维护性**：模块化，职责单一
- **可测试性**：小模块易于测试
- **可扩展性**：新功能易于添加

## 时间表

- **第1周**：重构 processing_cache.py 和 event_prediction_service.py
- **第2周**：重构 collectors 相关文件
- **第3周**：重构 patterns 和 monitoring 相关文件
- **第4周**：验证和清理