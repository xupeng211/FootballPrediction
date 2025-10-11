# MyPy 错误修复脚本使用指南

## 概述

`fix_mypy_errors.py` 是一个系统性的 MyPy 类型错误修复脚本，专门设计用于修复最常见的 MyPy 错误类型。

## 功能特性

### 支持修复的错误类型

1. **callable → typing.Callable** - 修复内置 callable 类型错误
2. **缺失的 logger 导入** - 自动添加 logging 模块导入和 logger 初始化
3. **变量类型注解错误** - 智能推断并添加缺失的类型注解
4. **未使用的 type: ignore** - 清理无用的类型忽略注释
5. **no-any-return 错误** - 处理函数返回类型问题
6. **更多错误类型** - 可扩展的修复策略

### 核心功能

- 🔍 **错误分析**: 自动分析 MyPy 错误并按类型分组
- 🛠️ **智能修复**: 基于错误模式应用相应的修复策略
- 📊 **详细报告**: 生成完整的修复报告和统计信息
- 🔒 **试运行模式**: 支持预览修复效果而不修改文件
- 📁 **批量处理**: 高效处理大量文件和错误

## 使用方法

### 基本用法

```bash
# 修复整个 src 目录的 MyPy 错误
python scripts/fix_mypy_errors.py

# 修复特定模块
python scripts/fix_mypy_errors.py --module src/api

# 试运行模式（不修改文件）
python scripts/fix_mypy_errors.py --dry-run

# 指定项目根目录
python scripts/fix_mypy_errors.py --project-root /path/to/project
```

### 命令行参数

- `--module`: 要修复的模块路径（默认: src）
- `--dry-run`: 试运行模式，不修改文件，只显示将要进行的修复
- `--project-root`: 项目根目录路径（默认: 当前目录）

### 使用示例

```bash
# 示例 1: 完整修复流程
python scripts/fix_mypy_errors.py --module src/data

# 示例 2: 试运行查看效果
python scripts/fix_mypy_errors.py --dry-run --module src/monitoring

# 示例 3: 修复特定目录
python scripts/fix_mypy_errors.py --module src/core/prediction
```

## 修复报告

脚本会自动生成详细的修复报告，包含：

- 📊 **统计信息**: 总错误数、已修复数、跳过数、失败数
- 📋 **错误类型分布**: 按错误类型显示数量
- 📁 **修复的文件列表**: 所有被修改的文件路径
- ⏰ **执行时间**: 脚本运行耗时

报告保存在 `scripts/cleanup/mypy_fix_report_YYYYMMDD_HHMMSS.md`

## 工作原理

### 1. 错误收集
- 运行 `mypy` 命令收集错误信息
- 解析错误输出，提取文件路径、行号、错误消息和错误代码

### 2. 错误分类
- 根据错误模式和代码对错误进行分类
- 识别可自动修复的错误类型

### 3. 应用修复策略
- **callable 错误**: 替换为 `typing.Callable` 并确保导入
- **logger 错误**: 添加 logging 导入和初始化
- **类型注解错误**: 智能推断类型并添加注解
- **type: ignore 错误**: 移除未使用的忽略注释
- **no-any-return 错误**: 添加适当的类型注释或忽略标记

### 4. 验证和报告
- 重新运行 MyPy 验证修复效果
- 生成详细的修复报告

## 注意事项

### ✅ 安全特性
- 支持试运行模式，预览修复效果
- 自动备份和报告生成
- 错误处理和回滚机制

### ⚠️ 限制
- 只能修复特定类型的错误
- 复杂的类型推断问题可能需要手动处理
- 某些错误可能需要更深层次的代码重构

### 🔧 建议使用流程
1. 首先使用 `--dry-run` 查看将要修复的错误
2. 检查生成的报告确认修复范围
3. 运行实际修复命令
4. 检查剩余错误并手动处理

## 扩展开发

### 添加新的修复策略

1. 在 `analyze_error_patterns` 方法中添加新的错误类型识别
2. 实现对应的修复方法（如 `fix_new_error_type`）
3. 在 `fix_errors_batch` 中添加新的修复策略

```python
# 示例：添加新的错误类型修复
def fix_new_error_type(self, error: Dict[str, Any]) -> bool:
    """修复新的错误类型"""
    # 实现修复逻辑
    return True
```

### 自定义修复规则

可以通过修改错误匹配模式来定制修复行为，支持正则表达式和复杂的错误条件判断。

## 故障排除

### 常见问题

1. **MyPy 命令未找到**
   ```bash
   pip install mypy
   ```

2. **权限问题**
   ```bash
   chmod +x scripts/fix_mypy_errors.py
   ```

3. **编码问题**
   - 确保文件使用 UTF-8 编码
   - 检查文件路径是否包含特殊字符

### 调试模式

可以在脚本中添加详细的调试输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 相关文件

- `scripts/fix_mypy_errors.py` - 主修复脚本
- `mypy.ini` - MyPy 配置文件
- `scripts/cleanup/` - 修复报告存储目录
- `TECHNICAL_DEBT_KANBAN.md` - 技术债务管理看板

## 维护和更新

建议定期运行此脚本作为代码质量维护的一部分，可以集成到 CI/CD 流程中或作为定期的代码清理任务。
