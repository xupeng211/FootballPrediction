# 语法错误修复指南

## 📊 错误统计摘要

- **总文件数**: 506个
- **有错误文件**: 107个（21.1%）
- **成功率**: 78.9%
- **主要错误类型**:
  - 括号不匹配: 60个（56.1%）
  - 其他错误: 12个（11.2%）
  - 赋值语法错误: 9个（8.4%）
  - 缺少冒号: 9个（8.4%）

## 🎯 修复优先级

### 优先级1：核心模块（必须先修复）

这些模块是系统运行的基础，必须优先修复：

| 模块 | 错误数 | 重要性 | 建议修复顺序 |
|------|--------|--------|-------------|
| `src/core` | 3个 | ⭐⭐⭐⭐⭐ | 1 |
| `src/api` | 3个 | ⭐⭐⭐⭐⭐ | 2 |
| `src/services` | 12个 | ⭐⭐⭐⭐ | 3 |
| `src/database` | 10个 | ⭐⭐⭐⭐ | 4 |
| `src/domain` | 18个 | ⭐⭐⭐⭐ | 5 |

### 优先级2：业务逻辑模块

| 模块 | 错误数 | 重要性 | 建议修复顺序 |
|------|--------|--------|-------------|
| `src/repositories` | 6个 | ⭐⭐⭐ | 6 |
| `src/adapters` | 0个 | ⭐⭐⭐ | 7 |
| `src/models` | 2个 | ⭐⭐⭐ | 8 |
| `src/cqrs` | 2个 | ⭐⭐ | 9 |

### 优先级3：辅助模块

| 模块 | 错误数 | 重要性 | 建议修复顺序 |
|------|--------|--------|-------------|
| `src/cache` | 5个 | ⭐⭐ | 10 |
| `src/collectors` | 2个 | ⭐⭐ | 11 |
| `src/tasks` | 4个 | ⭐⭐ | 12 |
| `src/streaming` | 4个 | ⭐⭐ | 13 |

## 🔧 常见错误修复方法

### 1. 括号不匹配（56.1%的错误）

**特征**：
- `closing parenthesis ')' does not match opening parenthesis '['`
- `unmatched ']'`
- `closing parenthesis '}' does not match opening parenthesis '['`

**修复方法**：

```python
# 错误示例1
def func(self) -> Dict[str, Any]]:
    return self.data

# 错误示例2
result = self.get_data()[0

# 错误示例3
items = [item for item in data if item['type' == 'A']
```

**批量修复脚本**：
```python
import re

def fix_brackets(content):
    """修复括号不匹配"""
    # 修复常见的类型注解错误
    content = re.sub(r': Dict\[str, Any\]\]\[str, Any\]', ': Dict[str, Any]', content)
    content = re.sub(r': Optional\[Dict\[str, Any\]\]\[str, Any\]', ': Optional[Dict[str, Any]]', content)
    content = re.sub(r': List\[Dict\[str, Any\]\]\[str, Any\]', ': List[Dict[str, Any]]', content)

    # 计算括号平衡
    open_parens = content.count('(') - content.count(')')
    open_brackets = content.count('[') - content.count(']')
    open_braces = content.count('{') - content.count('}')

    # 添加缺失的括号
    if open_parens > 0:
        content += ')' * open_parens
    if open_brackets > 0:
        content += ']' * open_brackets
    if open_braces > 0:
        content += '}' * open_braces

    return content
```

### 2. 未闭合的字符串（6.5%的错误）

**特征**：
- `unterminated string literal`
- `f-string: single '}' is not allowed`

**修复方法**：

```python
# 错误示例
logger.info(f"Processing item {item)

# 修复
logger.info(f"Processing item {item}")
```

**批量修复**：
```python
def fix_unclosed_strings(content):
    """修复未闭合的字符串"""
    lines = content.split('\n')
    in_string = False
    string_char = None

    for i, line in enumerate(lines):
        j = 0
        while j < len(line):
            if line[j] in ['"', "'"] and not in_string:
                # 检查是否转义
                if j == 0 or line[j-1] != '\\':
                    in_string = True
                    string_char = line[j]
            elif line[j] == string_char and in_string:
                # 检查是否转义
                if j == 0 or line[j-1] != '\\':
                    in_string = False
                    string_char = None
            j += 1

        # 如果行结束时字符串未闭合
        if in_string:
            lines[i] += string_char
            in_string = False
            string_char = None

    return '\n'.join(lines)
```

### 3. 缺少冒号（8.4%的错误）

**特征**：
- `expected ':'`

**修复方法**：

```python
# 错误示例
def my_function()
    pass

if condition
    do_something()

for item in items
    process(item)

# 修复
def my_function():
    pass

if condition:
    do_something()

for item in items:
    process(item)
```

**批量修复**：
```python
def add_missing_colons(content):
    """添加缺失的冒号"""
    # 匹配需要冒号但缺少的行
    patterns = [
        r'(def\s+\w+\([^)]*\))(?!\s*:)',
        r'(if\s+[^:]+)(?!\s*:)',
        r'(elif\s+[^:]+)(?!\s*:)',
        r'(else)(?!\s*:)',
        r'(for\s+[^:]+)(?!\s*:)',
        r'(while\s+[^:]+)(?!\s*:)',
        r'(try)(?!\s*:)',
        r'(except\s+[^:]*)(?!\s*:)',
        r'(finally)(?!\s*:)',
        r'(with\s+[^:]+)(?!\s*:)',
        r'(class\s+\w+[^:]*)(?!\s*:)',
    ]

    for pattern in patterns:
        content = re.sub(pattern, r'\1:', content)

    return content
```

### 4. 赋值语法错误（8.4%的错误）

**特征**：
- `cannot assign to subscript here. Maybe you meant '==' instead of '='?`

**修复方法**：

```python
# 错误示例
if data['key'] = 'value':
    process(data)

# 修复
if data['key'] == 'value':
    process(data)

# 或者
data['key'] = 'value'
process(data)
```

### 5. f-string错误

**特征**：
- `f-string: single '}' is not allowed`
- `f-string: expecting '}'`

**修复方法**：

```python
# 错误示例
f"Value: {value"

# 修复
f"Value: {value}"

# 错误示例
f"Value: {value}}"

# 修复
f"Value: {value}"
```

## 📋 修复计划

### 第一天：修复核心模块

1. **src/core**（3个错误）
   - `src/core/logging/advanced_filters.py` - 括号不匹配
   - `src/core/prediction/data_loader.py` - 括号不匹配
   - `src/core/prediction/cache_manager.py` - 括号不匹配

2. **src/api**（3个错误）
   - `src/api/performance.py` - 未闭合的字符串
   - `src/api/facades.py` - 括号不匹配
   - `src/api/monitoring.py` - 意外缩进

### 第二天：修复服务层和数据层

1. **src/services**（12个错误）
   - 重点文件：
     - `src/services/data_processing.py`
     - `src/services/event_prediction_service.py`
     - `src/services/strategy_prediction_service.py`

2. **src/database**（10个错误）
   - 重点文件：
     - `src/database/repositories/base.py`
     - `src/database/repositories/prediction.py`
     - `src/database/query_optimizer.py`

### 第三天：修复领域模型

1. **src/domain**（18个错误）
   - 优先修复模型文件：
     - `src/domain/models/match.py`
     - `src/domain/models/team.py`
     - `src/domain/models/prediction.py`
   - 然后修复策略文件：
     - `src/domain/strategies/base.py`
     - `src/domain/strategies/factory.py`

## 🛠️ 自动化修复脚本

创建一个智能修复脚本：

```python
#!/usr/bin/env python3
"""
自动修复常见语法错误
"""

import ast
import os
import re
from pathlib import Path

class SyntaxErrorFixer:
    def __init__(self):
        self.fixes_applied = 0

    def fix_file(self, file_path):
        """修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # 应用各种修复
            content = self.fix_brackets(content)
            content = self.fix_unclosed_strings(content)
            content = self.add_missing_colons(content)
            content = self.fix_assignment_errors(content)

            # 验证修复
            try:
                ast.parse(content)
                if content != original:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.fixes_applied += 1
                    print(f"✓ 修复: {file_path}")
                return True
            except SyntaxError as e:
                print(f"✗ 仍有错误: {file_path} - {e}")
                return False

        except Exception as e:
            print(f"✗ 处理文件出错 {file_path}: {e}")
            return False

    def fix_brackets(self, content):
        """修复括号不匹配"""
        # 实现括号修复逻辑
        return content

    def fix_unclosed_strings(self, content):
        """修复未闭合的字符串"""
        # 实现字符串修复逻辑
        return content

    def add_missing_colons(self, content):
        """添加缺失的冒号"""
        # 实现冒号添加逻辑
        return content

    def fix_assignment_errors(self, content):
        """修复赋值错误"""
        # 实现赋值修复逻辑
        return content

# 使用示例
if __name__ == "__main__":
    fixer = SyntaxErrorFixer()

    # 修复特定目录
    for py_file in Path('src/core').rglob('*.py'):
        fixer.fix_file(py_file)

    print(f"\n总计修复: {fixer.fixes_applied} 个文件")
```

## ✅ 验证修复

每次修复后，运行以下命令验证：

```bash
# 1. 检查语法
python -m py_compile src/module/file.py

# 2. 运行测试
python -m pytest tests/unit/module/ -v

# 3. 检查覆盖率
python -m pytest tests/unit/module/ --cov=src.module --cov-report=term-missing
```

## 📈 进度跟踪

创建一个简单的进度跟踪文件：

```markdown
# 语法错误修复进度

- [ ] src/core (0/3 完成)
- [ ] src/api (0/3 完成)
- [ ] src/services (0/12 完成)
- [ ] src/database (0/10 完成)
- [ ] src/domain (0/18 完成)

## 每日记录

### Day 1 (2025-XX-XX)
- ✅ 修复了 src/core/logging/advanced_filters.py
- ✅ 修复了 src/core/prediction/data_loader.py
- ⏳ 正在处理 src/core/prediction/cache_manager.py
```

## 💡 最佳实践

1. **备份代码**：修复前先备份或提交到版本控制
2. **逐个修复**：不要一次性修复太多文件
3. **测试验证**：每次修复后立即验证
4. **记录进度**：跟踪修复进度和遇到的问题
5. **寻求帮助**：遇到困难时及时寻求帮助

## 🎯 目标

- **短期目标**（3天）：修复核心模块（core, api, services, database）
- **中期目标**（1周）：修复所有模块，使错误率降到5%以下
- **长期目标**（2周）：建立CI检查，确保新代码无语法错误

---

记住：**质量比速度更重要！** 确保每个修复都经过测试验证。
