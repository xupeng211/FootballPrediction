# MyPy 分层类型检查指南

## 概述

本项目实施分层的 MyPy 类型检查策略，以平衡代码质量与开发效率：

- **核心模块**：严格模式，确保类型安全
- **辅助模块**：宽松模式，允许类型警告
- **非核心模块**：完全忽略，不影响 CI

## 模块分类

### 1. 核心业务模块（严格模式）
- `src/core/` - 核心业务逻辑
- `src/services/` - 业务服务层
- `src/api/` - API 接口层
- `src/domain/` - 领域模型（部分宽松）
- `src/repositories/` - 数据访问层
- `src/database/repositories/` - 数据库仓储

### 2. 辅助模块（宽松模式）
- `src/utils/` - 工具函数
- `src/monitoring/` - 监控组件
- `src/tasks/` - 异步任务
- `src/cache/` - 缓存层
- `src/collectors/` - 数据收集器
- `src/data/` - 数据处理
- `src/features/` - 特征工程
- `src/ml/` - 机器学习
- `src/scheduler/` - 任务调度
- `src/security/` - 安全组件
- `src/models/` - 模型定义

### 3. 非核心模块（完全忽略）
- `src/domain_simple/` - 简化版领域模型
- `src/streaming/*_simple` - 简化版流处理
- `src/adapters/*_simple` - 简化版适配器
- `src/main` - 主入口文件
- `examples/` - 示例代码
- `tests/` - 测试代码

## 使用方法

### 开发阶段

```bash
# 检查所有类型（包括警告）
make typecheck

# 仅检查核心模块（严格模式）
make typecheck-core

# 仅检查辅助模块（宽松模式）
make typecheck-aux

# 检查所有模块（包括非核心）
make typecheck-full
```

### CI/CD 流程

- **pre-push**: 仅运行核心模块严格检查
- **CI**: 运行核心模块严格检查
- **CI-full**: 运行所有类型检查（包括宽松模式）

## 配置说明

### MyPy 配置文件 (`mypy.ini`)

```ini
[mypy]
# 全局宽松配置
disallow_untyped_defs = False
check_untyped_defs = False

# 核心模块严格配置
[mypy-src.core.*]
disallow_untyped_defs = True
check_untyped_defs = True

# 辅助模块宽松配置
[mypy-src.utils.*]
ignore_missing_imports = True
warn_return_any = False

# 非核心模块完全忽略
[mypy-examples.*]
ignore_errors = True
```

## 最佳实践

### 1. 新增代码

- 核心模块必须添加完整类型注解
- 辅助模块建议添加类型注解
- 非核心模块可选择性添加

### 2. 修复类型错误

优先级：
1. 核心模块错误必须修复
2. 辅助模块错误建议修复
3. 非核心模块错误可忽略

### 3. 类型注解技巧

```python
# 推荐的类型注解
from typing import Optional, List, Dict, Any, Union

def process_data(
    data: Dict[str, Any],
    config: Optional[Dict[str, str]] = None
) -> List[str]:
    """处理数据并返回结果列表"""
    pass
```

## 故障排查

### 常见错误

1. **"Source contains parsing errors"**
   - 检查 mypy.ini 语法
   - 确保正则表达式正确

2. **"Missing type parameters for generic type"**
   - 使用具体类型：`Dict[str, int]` 而不是 `Dict`
   - 或使用 `typing.Dict` 的完整形式

3. **"Function is missing a return type annotation"**
   - 添加返回类型：`def func() -> None:`
   - 或在函数体后添加 `# type: ignore`

## 未来改进

1. 逐步提高辅助模块的严格程度
2. 为非核心模块添加基础类型检查
3. 集成更多静态分析工具（如 pyright）
4. 添加类型检查覆盖率报告
