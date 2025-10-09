# 高级审计服务 (Advanced Audit Service)

这是一个企业级的审计服务模块，提供了全面的审计功能。

## 功能特性

### 核心功能
- **主审计服务 (service.py, 280行)**: 提供核心的审计功能实现
- **审计上下文 (context.py, 95行)**: 管理审计过程中的上下文信息
- **数据清理器 (sanitizer.py, 120行)**: 处理敏感数据的清理和掩码功能

### 分析器模块
- **数据分析器 (data_analyzer.py, 350行)**: 提供审计数据的深度分析功能
- **模式分析器 (pattern_analyzer.py, 200行)**: 识别和分析审计日志中的行为模式和异常
- **风险分析器 (risk_analyzer.py, 180行)**: 评估审计操作的风险级别和威胁评估

### 日志器模块
- **审计日志器 (audit_logger.py, 200行)**: 提供审计日志的持久化存储和查询功能
- **结构化日志器 (structured_logger.py, 150行)**: 提供标准化的结构化日志格式和输出
- **异步日志器 (async_logger.py, 100行)**: 提供异步批量的高性能日志记录功能

### 报告器模块
- **报告生成器 (report_generator.py, 320行)**: 提供各种审计报告的生成功能
- **模板管理器 (template_manager.py, 150行)**: 管理报告模板的创建、加载和应用
- **导出管理器 (export_manager.py, 120行)**: 管理审计报告的导出功能

### 装饰器模块
- **审计装饰器 (audit_decorators.py, 350行)**: 提供审计功能的装饰器实现
- **性能装饰器 (performance_decorator.py, 150行)**: 提供性能监控和优化的装饰器
- **安全装饰器 (security_decorator.py, 200行)**: 提供安全相关的装饰器实现

## 使用示例

### 基本审计功能

```python
from src.services.audit.advanced import AuditService, AuditContext

# 创建审计服务
audit_service = AuditService()
await audit_service.initialize()

# 创建审计上下文
context = AuditContext(
    user_id="user123",
    username="john_doe",
    user_role="admin",
    ip_address="192.168.1.1"
)

# 记录审计日志
await audit_service.log_operation(
    context=context,
    action="create",
    resource_type="user",
    resource_id="user456",
    description="创建新用户"
)
```

### 使用装饰器

```python
from src.services.audit.advanced import audit_action, monitor_performance, require_permission

@audit_action("delete_user", resource_type="user")
@monitor_performance(threshold=2.0)
@require_permission("user_management")
async def delete_user(user_id: str):
    # 删除用户逻辑
    pass
```

### 生成报告

```python
from src.services.audit.advanced import ReportGenerator

# 创建报告生成器
report_generator = ReportGenerator()

# 生成用户活动报告
report = report_generator.generate_report(
    report_type="user_activity",
    data=audit_data,
    format="html"
)
```

### 数据分析

```python
from src.services.audit.advanced import DataAnalyzer, PatternAnalyzer, RiskAnalyzer

# 创建分析器
data_analyzer = DataAnalyzer()
pattern_analyzer = PatternAnalyzer()
risk_analyzer = RiskAnalyzer()

# 分析数据变更
changes = data_analyzer.analyze_data_changes(old_values, new_values)

# 分析行为模式
patterns = pattern_analyzer.analyze_patterns(audit_logs)

# 评估风险
risk_assessment = risk_analyzer.assess_risk(operation_data)
```

## 向后兼容性

为了保持向后兼容性，原有的接口仍然可用：

```python
from src.services.audit_service_mod import AuditService

# 使用原有接口
audit_service = AuditService()
```

或者使用新的高级功能：

```python
from src.services.audit_service_mod import get_audit_service

# 获取高级审计服务
audit_service = get_audit_service(use_advanced=True)
```

## 配置选项

服务可以通过配置参数进行定制：

- 批量大小和刷新间隔
- 敏感数据处理规则
- 风险评估阈值
- 报告模板
- 导出格式

## 扩展性

该模块设计为高度可扩展：

1. **分析器**: 可以轻松添加新的数据分析器
2. **日志器**: 支持自定义日志格式和存储
3. **报告器**: 可以创建自定义报告模板和格式
4. **装饰器**: 可以组合使用多个装饰器

## 性能优化

- 异步日志处理
- 批量数据操作
- 内存缓存
- 连接池管理

## 安全特性

- 敏感数据自动清理
- 访问控制
- 速率限制
- 入侵检测

该模块提供了企业级的审计解决方案，既保持了向后兼容性，又提供了丰富的高级功能。