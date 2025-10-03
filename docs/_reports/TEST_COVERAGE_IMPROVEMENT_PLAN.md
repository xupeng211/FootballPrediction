# 测试覆盖率提升计划

**创建时间**: 2025-10-03

## 📊 当前状态
- **整体覆盖率**: 16.5% (2,876/14,201行)
- **目标**: 短期提升到25%，中期达到35%

## 🎯 模块选择策略

### 优先级评分标准
1. **业务重要性** (40%) - 核心业务逻辑优先
2. **代码复杂度** (30%) - 复杂模块更需要测试
3. **测试性价比** (20%) - 容易测试且效果明显的
4. **依赖复杂度** (10%) - 依赖少的优先

### 选择的模块（按优先级）

#### 🥇 第一批：高优先级（立即开始）
1. **src/api/predictions.py** - 17.2% (123行)
   - 业务重要性：⭐⭐⭐⭐⭐ 核心预测API
   - 复杂度：中等
   - 预期提升：+40%

2. **src/api/cache.py** - 21.1% (146行)
   - 业务重要性：⭐⭐⭐⭐ 缓存是性能关键
   - 已有基础测试，容易扩展
   - 预期提升：+30%

3. **src/utils/crypto_utils.py** - 25% (67行)
   - 业务重要性：⭐⭐⭐⭐ 安全相关
   - 代码简单，容易测试
   - 预期提升：+50%

4. **src/services/user_profile.py** - 28% (65行)
   - 业务重要性：⭐⭐⭐⭐ 用户功能
   - 代码量适中
   - 预期提升：+40%

#### 🥈 第二批：中优先级
1. **src/data/collectors/base_collector.py** - 19.3% (154行)
2. **src/api/monitoring.py** - 18.7% (177行)
3. **src/cache/init_cache.py** - 18.1% (100行)
4. **src/utils/file_utils.py** - 29% (72行)

#### 🥉 第三批：低优先级
1. **src/monitoring/metrics_collector.py** - 18.5% (253行)
2. **src/features/feature_store.py** - 16.9% (185行)
3. **src/data/processing/** 目录下的文件

## 🛠️ 实施策略

### "Working Test" 方法
1. **直接读取源文件**，避免复杂的导入问题
2. **测试核心逻辑**，而不是外部依赖
3. **使用Mock**隔离外部服务
4. **专注业务规则**，而不是基础设施

### 测试模板
```python
# 标准测试模板
import pytest
from unittest.mock import Mock, patch, AsyncMock

def test_function_name():
    # 1. 读取源文件
    source = read_file('src/module/file.py')

    # 2. 提取函数
    func = extract_function(source, 'function_name')

    # 3. 准备测试数据
    test_input = {...}

    # 4. 执行测试
    result = execute_function(func, test_input)

    # 5. 验证结果
    assert result == expected
```

## 📈 执行计划

### 第1天：核心API测试
- [x] 分析覆盖率
- [ ] 测试 src/api/predictions.py
  - [ ] test_create_prediction
  - [ ] test_get_prediction
  - [ ] test_update_prediction
  - [ ] test_delete_prediction
- [ ] 运行覆盖率验证

### 第2天：缓存和工具测试
- [ ] 测试 src/api/cache.py (扩展现有测试)
  - [ ] test_cache_operations
  - [ ] test_cache_prewarm
  - [ ] test_cache_optimization
- [ ] 测试 src/utils/crypto_utils.py
  - [ ] test_encrypt_decrypt
  - [ ] test_hash_functions
  - [ ] test_token_operations

### 第3天：服务层测试
- [ ] 测试 src/services/user_profile.py
- [ ] 开始第二批模块

## 🎯 预期成果

### 覆盖率目标
- 开始：16.5%
- 第1天后：~20%
- 第2天后：~24%
- 第3天后：~28%

### 质量提升
- 减少生产环境bug
- 提高代码可维护性
- 增强重构信心
- 改善文档质量

## 📝 跟踪机制

### 每日检查
```bash
# 运行此命令查看进度
python scripts/quick_coverage_view.py
```

### 里程碑
- [ ] 覆盖率达到20% ✅
- [ ] 覆盖率达到25%
- [ ] 覆盖率达到30%
- [ ] 核心模块达到50%

## 🚀 开始执行

现在开始第一批模块的测试提升...