# 模块化代码迁移指南

## 📖 概述

本指南帮助您从旧的代码结构迁移到新的模块化架构。

## 🔄 导入路径映射

### 核心服务模块

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `src.services.audit_service` | `src.services.audit_service_mod` | 审计服务拆分为7个专业模块 |
| `src.services.manager` | `src.services.manager_mod` | 服务管理器 |
| `src.services.data_processing` | `src.services.data_processing_mod` | 数据处理服务 |

### 数据库模块

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `src.database.connection` | `src.database.connection_mod` | 数据库连接管理 |
| `src.database.models` | `src.database.models.*` | 模型按功能分类 |

### 缓存模块

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `src.cache.ttl_cache_improved` | `src.cache.ttl_cache_improved_mod` | TTL缓存实现 |

### 数据处理模块

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `src.data.processing.football_data_cleaner` | `src.data.processing.football_data_cleaner_mod` | 数据清洗 |
| `src.data.quality.exception_handler` | `src.data.quality.exception_handler_mod` | 异常处理 |

### 监控模块

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `src.monitoring.system_monitor` | `src.monitoring.system_monitor_mod` | 系统监控 |
| `src.monitoring.metrics_collector_enhanced` | `src.monitoring.metrics_collector_enhanced_mod` | 指标收集 |

## 📝 迁移步骤

### 1. 立即可用（无需更改）

您的现有代码无需任何更改即可工作，因为我们创建了兼容性垫片：

```python
# 这些导入仍然有效
from src.services.audit_service import AuditService
from src.services.manager import ServiceManager
from src.services.data_processing import DataProcessingService
```

### 2. 逐步迁移到新路径（推荐）

当您准备更新代码时，按照以下步骤：

```python
# 旧代码
from src.services.audit_service import AuditService

# 新代码（推荐）
from src.services.audit_service_mod import AuditService
```

### 3. 使用特定的子模块

对于更精细的控制，您可以直接导入特定的组件：

```python
# 审计服务示例
from src.services.audit_service_mod.service import AuditService
from src.services.audit_service_mod.models import AuditLog, AuditContext
from src.services.audit_service_mod.storage import AuditStorage

# 数据处理示例
from src.services.data_processing_mod.service import DataProcessingService
from src.services.data_processing_mod.validators import DataValidator
```

## 🎯 最佳实践

### 1. 新代码使用新路径
```python
# ✅ 推荐
from src.services.audit_service_mod import AuditService

# ❌ 不推荐（但仍有效）
from src.services.audit_service import AuditService
```

### 2. 按需导入特定功能
```python
# ✅ 只导入需要的功能
from src.services.audit_service_mod.models import AuditContext
from src.services.audit_service_mod.utils import sanitize_data

# ❌ 导入整个模块
from src.services.audit_service_mod import *
```

### 3. 利用新的模块化结构
```python
# 现在可以独立使用各个组件
from src.services.audit_service_mod.storage import AuditStorage
storage = AuditStorage()  # 不需要完整的AuditService
```

## 🛠️ 实用示例

### 示例1：审计日志记录

```python
# 旧方式
from src.services.audit_service import AuditService, AuditContext

# 新方式（推荐）
from src.services.audit_service_mod import AuditService, AuditContext
# 或更具体的导入
from src.services.audit_service_mod.service import AuditService
from src.services.audit_service_mod.models import AuditContext
```

### 示例2：数据处理流水线

```python
# 新的模块化方式允许更灵活的使用
from src.services.data_processing_mod import DataProcessingService
from src.services.data_processing_mod.transformers import DataTransformer
from src.services.data_processing_mod.validators import DataValidator

# 可以独立使用各个组件
validator = DataValidator()
transformer = DataTransformer()
```

## 📋 迁移检查清单

- [ ] 识别使用旧导入路径的文件
- [ ] 逐个文件更新导入语句
- [ ] 运行测试确保功能正常
- [ ] 移除不必要的导入
- [ ] 更新文档和注释

## 🔧 迁移脚本（可选）

您可以创建一个简单的脚本来自动更新导入路径：

```bash
# 查找使用旧导入的文件
grep -r "from src.services.audit_service import" --include="*.py" .
grep -r "from src.services.manager import" --include="*.py" .

# 使用sed批量替换（请谨慎使用）
find . -name "*.py" -type f -exec sed -i 's/from src\.services\.audit_service import/from src.services.audit_service_mod import/g' {} \;
```

## ❓ 常见问题

### Q: 现有代码会停止工作吗？
A: 不会。我们创建了兼容性垫片，确保现有导入路径继续工作。

### Q: 什么时候需要迁移？
A: 您可以选择在任何时间迁移。没有强制的时间表。

### Q: 迁移有什么好处？
A: - 更好的代码组织
- 更清晰的模块边界
- 更容易测试和维护
- 可以只导入需要的功能

### Q: 需要一次性迁移所有代码吗？
A: 不需要。您可以逐步迁移，甚至在同一个文件中混合使用新旧导入。

## 📞 获取帮助

如果在迁移过程中遇到问题，请：
1. 查看各个模块的`__init__.py`文件了解导出的内容
2. 查看模块内的README或文档
3. 创建Issue或Pull Request

---

**注意**: 这是一个渐进式的迁移，不需要立即执行。请在您准备好的时候再进行迁移。